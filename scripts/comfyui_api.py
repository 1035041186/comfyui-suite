#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ComfyUI 统一 API 调用脚本（仅依赖 Python 3.8+ 标准库，无需 pip 安装）。

功能：
  1. 读取 config/comfyui.yaml（或 --config 指定），环境变量优先覆盖；
  2. 上传图片（/upload/image）供图生图 / 图生视频 / 参考生视频使用；
  3. 将 workflow 模板（API 格式 JSON，含 {{占位符}}）与参数合并；
  4. 提交任务（POST /prompt），轮询 /history/{prompt_id} 直至完成；
  5. 通过 /view 下载结果文件（图片 / 视频）到输出目录。

典型用法：
  python3 scripts/comfyui_api.py text-to-image --prompt "a cat" --seed 42
  python3 scripts/comfyui_api.py image-to-image --prompt "..." --image in.png --denoise 0.6
  python3 scripts/comfyui_api.py text-to-video --prompt "..." --frames 49 --fps 16
  python3 scripts/comfyui_api.py image-to-video --prompt "..." --image first.png
  python3 scripts/comfyui_api.py reference-to-video --prompt "..." --image role.png --video ref.mp4

退出码：0 成功；2 参数/配置错误；3 网络或服务错误；4 任务执行失败/超时。
"""
import argparse
import json
import mimetypes
import os
import random
import re
import sys
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(SKILL_ROOT, "config", "comfyui.yaml")

KNOWN_TYPES = ("text-to-image", "image-to-image", "text-to-video",
               "image-to-video", "reference-to-video")


# ---------------------------------------------------------------- 配置读取

def _parse_scalar(value):
    v = value.strip()
    if not v:
        return ""
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    low = v.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def load_yaml_minimal(path):
    """极简 YAML 子集解析：支持两级缩进的 key: value 与注释（够用且零依赖）。
    若环境已安装 PyYAML，则优先使用完整解析。"""
    try:
        import yaml  # type: ignore
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except ImportError:
        pass
    root = {}
    stack = [(-1, root)]
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(line.lstrip(" "))
            if ":" not in stripped:
                continue
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.split(" #", 1)[0].strip()
            while stack and indent <= stack[-1][0]:
                stack.pop()
            parent = stack[-1][1]
            if val == "":
                node = {}
                parent[key] = node
                stack.append((indent, node))
            else:
                parent[key] = _parse_scalar(val)
    return root


def deep_merge(base, override):
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def env_overrides(cfg):
    """支持环境变量覆盖：COMFYUI_HOST / COMFYUI_PORT / COMFYUI_PROTOCOL /
    COMFYUI_API_KEY / COMFYUI_OUTPUT_DIR / COMFYUI_POLL_MAX"""
    mapping = {
        "COMFYUI_HOST": ("server", "host"),
        "COMFYUI_PORT": ("server", "port"),
        "COMFYUI_PROTOCOL": ("server", "protocol"),
        "COMFYUI_API_KEY": ("server", "api_key"),
        "COMFYUI_OUTPUT_DIR": ("output", "dir"),
        "COMFYUI_POLL_MAX": ("timeouts", "poll_max"),
    }
    out = {}
    for env_key, (sec, name) in mapping.items():
        if os.environ.get(env_key) not in (None, ""):
            raw = os.environ[env_key]
            out.setdefault(sec, {})[name] = _parse_scalar(raw)
    return deep_merge(cfg, out)


def load_config(path):
    cfg = load_yaml_minimal(path)
    cfg = env_overrides(cfg)
    server = cfg.setdefault("server", {})
    server.setdefault("protocol", "http")
    server.setdefault("host", "127.0.0.1")
    server.setdefault("port", 8188)
    cfg.setdefault("timeouts", {})
    cfg.setdefault("output", {})
    return cfg


def base_url(cfg):
    s = cfg["server"]
    return "{}://{}:{}".format(s["protocol"], s["host"], s["port"])


# ---------------------------------------------------------------- HTTP 工具

def _request(cfg, method, path, data=None, headers=None, timeout=60, binary=None):
    url = base_url(cfg) + path
    hdrs = dict(headers or {})
    api_key = cfg["server"].get("api_key") or ""
    if api_key:
        hdrs["Authorization"] = "Bearer " + api_key
    body = binary if binary is not None else (
        json.dumps(data).encode("utf-8") if data is not None else None)
    if data is not None and binary is None:
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:2000]
        raise RuntimeError("HTTP {} {} -> {}: {}".format(method, path, e.code, detail))
    except urllib.error.URLError as e:
        raise RuntimeError("无法连接 ComfyUI ({}): {}".format(url, e.reason))


def _encode_multipart(field_file, file_path, extra_fields):
    boundary = uuid.uuid4().hex
    crlf = b"\r\n"
    parts = []
    for k, v in extra_fields.items():
        parts.append(b"--" + boundary.encode() + crlf)
        parts.append(('Content-Disposition: form-data; name="{}"'.format(k)).encode() + crlf + crlf)
        parts.append(str(v).encode() + crlf)
    fname = os.path.basename(file_path)
    ctype = mimetypes.guess_type(fname)[0] or "application/octet-stream"
    parts.append(b"--" + boundary.encode() + crlf)
    parts.append(('Content-Disposition: form-data; name="{}"; filename="{}"'.format(
        field_file, fname)).encode() + crlf)
    parts.append(("Content-Type: " + ctype).encode() + crlf + crlf)
    with open(file_path, "rb") as f:
        parts.append(f.read() + crlf)
    parts.append(b"--" + boundary.encode() + b"--" + crlf)
    return b"".join(parts), "multipart/form-data; boundary=" + boundary


# ---------------------------------------------------------------- ComfyUI API

def check_health(cfg):
    """返回 True 表示服务可用。"""
    try:
        status, _ = _request(cfg, "GET", "/system_stats", timeout=cfg["timeouts"].get("connect", 10))
        return status == 200
    except RuntimeError as e:
        print("[warn] 健康检查失败: {}".format(e), file=sys.stderr)
        return False


def upload_image(cfg, file_path):
    """上传本地图片到 ComfyUI input 目录，返回服务端文件名。"""
    if not os.path.isfile(file_path):
        raise RuntimeError("输入文件不存在: " + file_path)
    payload, ctype = _encode_multipart("image", file_path, {"overwrite": "true"})
    _, raw = _request(cfg, "POST", "/upload/image",
                      headers={"Content-Type": ctype}, binary=payload, timeout=120)
    info = json.loads(raw.decode("utf-8"))
    name = info.get("name")
    if not name:
        raise RuntimeError("上传响应异常: " + raw.decode("utf-8", "replace")[:500])
    return name


def queue_prompt(cfg, prompt_graph, client_id):
    _, raw = _request(cfg, "POST", "/prompt",
                      data={"prompt": prompt_graph, "client_id": client_id},
                      timeout=cfg["timeouts"].get("queue", 60))
    resp = json.loads(raw.decode("utf-8"))
    pid = resp.get("prompt_id")
    if not pid:
        raise RuntimeError("提交失败: " + raw.decode("utf-8", "replace")[:1000])
    return pid


def poll_history(cfg, prompt_id):
    interval = cfg["timeouts"].get("poll_interval", 2)
    deadline = time.time() + cfg["timeouts"].get("poll_max", 1800)
    while time.time() < deadline:
        _, raw = _request(cfg, "GET", "/history/" + prompt_id, timeout=30)
        hist = json.loads(raw.decode("utf-8"))
        if prompt_id in hist:
            entry = hist[prompt_id]
            status = entry.get("status", {})
            if status.get("completed"):
                return entry
            if status.get("status_str") == "error":
                msgs = status.get("messages", [])
                raise RuntimeError("任务执行出错: " + json.dumps(msgs, ensure_ascii=False)[:2000])
        time.sleep(interval)
    raise TimeoutError("等待超时（{}s），任务未完成".format(cfg["timeouts"].get("poll_max", 1800)))


def collect_outputs(entry):
    """从 history 条目中收集所有输出文件元数据。"""
    files = []
    for node_id, node_out in (entry.get("outputs") or {}).items():
        for kind in ("images", "gifs", "videos", "audio"):
            for item in node_out.get(kind, []) or []:
                item = dict(item)
                item["_kind"] = kind
                item["_node"] = node_id
                files.append(item)
    return files


def _session_cwd():
    """稳定解析「会话工作目录」作为输出锚点：
    优先从 DSH_SESSION_JSONL 解出会话记录的 cwd（真正跟会话走、不随 bash cd 漂移），
    解析失败才回退到 os.getcwd()。返回可供路径拼接的绝对路径。"""
    path = os.environ.get("DSH_SESSION_JSONL") or ""
    if path and os.path.isfile(path):
        try:
            import subprocess as _sp
            raw = _sp.run(["zstd", "-dc", path], capture_output=True, text=True).stdout
            for line in raw.splitlines():
                if not line.strip():
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                if o.get("type") == "session" and o.get("cwd"):
                    return o["cwd"]
        except Exception:
            pass
    return os.getcwd()


def _makedirs(path):
    """创建目录；失败（只读/无权限）抛出带明确路径的 RuntimeError，由 main 统一报错定位。
    不做任何"换路径"试探——只报错，说明稳定输出路径是哪个、为何建不出来。"""
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as e:
        raise RuntimeError("无法创建输出目录 {}（只读/无权限）：{}。"
                           "请确认会话工作目录可写，或用 --output 指定可写的绝对路径。".format(path, e))


def download_file(cfg, meta, out_dir):
    params = urllib.parse.urlencode({
        "filename": meta["filename"],
        "subfolder": meta.get("subfolder", ""),
        "type": meta.get("type", "output"),
    })
    _, raw = _request(cfg, "GET", "/view?" + params, timeout=300)
    os.makedirs(out_dir, exist_ok=True)
    # 所有生成文件统一带时间戳前缀，避免覆盖、便于按时间回溯
    stamp = time.strftime("%Y%m%d_%H%M%S")
    fname = "{}_{}".format(stamp, meta["filename"])
    path = os.path.join(out_dir, fname)
    with open(path, "wb") as f:
        f.write(raw)
    return path


# ---------------------------------------------------------------- 工作流渲染

_PLACEHOLDER = re.compile(r'"\{\{\s*([A-Z0-9_]+)\s*\}\}"|\{\{\s*([A-Z0-9_]+)\s*\}\}')

# 需转为 JSON 数字的占位符
NUMERIC_KEYS = {"SEED", "WIDTH", "HEIGHT", "STEPS", "CFG", "DENOISE",
                "FRAMES", "FPS", "VIDEO_LENGTH", "LORA_STRENGTH_MODEL",
                "LORA_STRENGTH_CLIP"}

# 可由 CLI 覆盖的生成参数 -> (CLI 属性名, _defaults 键)
# 生成参数的取值优先级：CLI 显式指定 > workflow _defaults > 随机(seed)/None(报错)
_CLI_OVERRIDES = (
    ("prompt", "prompt"), ("negative", "negative"), ("width", "width"),
    ("height", "height"), ("steps", "steps"), ("cfg", "cfg"),
    ("denoise", "denoise"), ("frames", "frames"), ("fps", "fps"),
    ("checkpoint", "checkpoint"), ("prefix", "prefix"),
)


def extract_defaults(template_text):
    """从模板文本中提取顶级 "_defaults" 对象。模板含未加引号的 {{数值占位符}}，
    整体不是合法 JSON，因此用大括号配对手工截取该字段后单独解析。"""
    m = re.search(r'"_defaults"\s*:\s*\{', template_text)
    if not m:
        return {}
    start = m.end() - 1
    depth, in_str, esc = 0, False, False
    for i in range(start, len(template_text)):
        ch = template_text[i]
        if esc:
            esc = False
            continue
        if ch == "\\" and in_str:
            esc = True
        elif ch == '"':
            in_str = not in_str
        elif not in_str:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(template_text[start:i + 1])
                    except json.JSONDecodeError:
                        return {}
    return {}


def find_workflow(gen_type, explicit=None):
    if explicit:
        if not os.path.isfile(explicit):
            raise RuntimeError("指定的 workflow 不存在: " + explicit)
        return explicit
    folder = os.path.join(SKILL_ROOT, "workflows", gen_type)
    if not os.path.isdir(folder):
        raise RuntimeError("workflow 目录不存在: " + folder)
    candidates = sorted(f for f in os.listdir(folder) if f.endswith(".json"))
    if not candidates:
        raise RuntimeError("{} 目录下没有 workflow JSON，请先按 workflows/README.md 导出".format(folder))
    # 默认模板：优先 default_ 开头；没有则取第一个。
    # 无论是否含 {{}} 均可——字段注入器对"导出 JSON（无占位符）"同样支持。
    defaults = [f for f in candidates if f.startswith("default")]
    return os.path.join(folder, defaults[0] if defaults else candidates[0])


def render_workflow(template_text, values):
    """替换 {{KEY}} 占位符；兼容带引号（"{{KEY}}"）与不带引号两种写法。
    数值型占位符输出 JSON 数字，其余输出 JSON 字符串（自带引号）。"""
    def _sub(m):
        key = m.group(1) or m.group(2)
        if key not in values or values[key] is None:
            raise RuntimeError("模板占位符 {{{{%s}}}} 缺少对应参数" % key)
        v = values[key]
        if key in NUMERIC_KEYS:
            return str(float(v)).rstrip("0").rstrip(".") if isinstance(v, float) else str(v)
        return json.dumps(str(v), ensure_ascii=False)
    return _PLACEHOLDER.sub(_sub, template_text)


def build_values(args, cfg, defaults):
    """组装占位符取值。生成参数只来自两处：CLI 显式参数、workflow _defaults。
    配置文件不含生成参数（尺寸/步数/模型跟随工作流，不跟随服务）。"""
    values = {}
    for attr, key in _CLI_OVERRIDES:
        v = getattr(args, attr, None)
        if v is None:
            v = defaults.get(key)
        # prompt/negative 缺省给空串，保证占位符路径不报缺参；其它字段缺省置空不注入
        if v is None and key in ("prompt", "negative"):
            v = ""
        if v is not None:
            values[key.upper()] = v
    # LoRA 占位符：--lora 支持 "NODE:文件"，取纯文件名注入 {{LORA}}
    loras = getattr(args, "lora", None)
    if loras:
        first = loras[0]
        fname = first.split(":", 1)[-1].strip() if ":" in first and not first.lower().startswith("strength") else first
        if not fname.lower().startswith("strength"):
            values["LORA"] = fname
    if getattr(args, "lora_strength_model", None) is not None:
        values["LORA_STRENGTH_MODEL"] = args.lora_strength_model
    if getattr(args, "lora_strength_clip", None) is not None:
        values["LORA_STRENGTH_CLIP"] = args.lora_strength_clip
    values["SEED"] = args.seed if args.seed is not None else random.randint(0, 2 ** 31 - 1)
    values["UPLOADED_IMAGE"] = getattr(args, "_uploaded_image", None)
    values["UPLOADED_VIDEO"] = getattr(args, "_uploaded_video", None)
    if args.set:
        for pair in args.set:
            if "=" not in pair:
                raise RuntimeError("--set 参数格式应为 KEY=VALUE: " + pair)
            k, v = pair.split("=", 1)
            k = k.strip().upper()
            values[k] = _parse_scalar(v) if k in NUMERIC_KEYS else v
    return values


# ---------------------------------------------------------------- 命令实现

def cmd_list(args, cfg):
    print("服务: {}".format(base_url(cfg)))
    print("可用生成类型与 workflow（`*` 为不传 --workflow 时的默认选中）：")
    for t in KNOWN_TYPES:
        folder = os.path.join(SKILL_ROOT, "workflows", t)
        files = sorted(f for f in os.listdir(folder) if f.endswith(".json")) if os.path.isdir(folder) else []
        if not files:
            print("  {:<20} (无，请用 ComfyUI「Save (API Format)」导出后放入)".format(t))
            continue
        # 默认选中的：default_ 前缀第一个；无 default_ 则第一个
        default = None
        for f in files:
            if f.startswith("default"):
                default = f
                break
        default = default or files[0]
        annotations = []
        for f in files:
            mark = "*" if f == default else " "
            ph = " (占位符)" if "{{" in open(os.path.join(folder, f), encoding="utf-8").read(4096) else ""
            annotations.append("{}{}{}".format(mark, f, ph))
        print("  {:<20} {}".format(t, ", ".join(annotations)))
    extra = [d for d in sorted(os.listdir(os.path.join(SKILL_ROOT, "workflows")))
             if d not in KNOWN_TYPES and os.path.isdir(os.path.join(SKILL_ROOT, "workflows", d))]
    if extra:
        print("  扩展类型: " + ", ".join(extra))
    print("\n提示: 不传 --workflow 即用 `*` 模板；要换用其它的传 --workflow <文件名>。")
    return 0


def cmd_health(args, cfg):
    ok = check_health(cfg)
    print("{} {}".format(base_url(cfg), "OK" if ok else "UNREACHABLE"))
    return 0 if ok else 3


def cmd_upload(args, cfg):
    name = upload_image(cfg, args.file)
    print(json.dumps({"uploaded_name": name}, ensure_ascii=False))
    return 0


def _find_nodes(graph, class_type=None, has_input=None):
    """按 class_type 或"是否存在某输入字段"定位节点，返回 node_id 列表。"""
    out = []
    for nid, node in graph.items():
        if not isinstance(node, dict):
            continue
        if class_type and node.get("class_type") != class_type:
            continue
        if has_input and has_input not in (node.get("inputs") or {}):
            continue
        out.append(str(nid))
    return out


_SAMPLER_CLASSES = ("KSampler", "KSamplerAdvanced")


def _find_sampler(graph):
    """找一个采样器节点（KSampler 类，优先含 positive/negative 输入的）。"""
    for nid, node in graph.items():
        if not isinstance(node, dict):
            continue
        if node.get("class_type") in _SAMPLER_CLASSES:
            return str(nid), node
    return None, None


_H3_VIDEO_NODE = "MiniMaxH3ImageToVideo"

def _is_h3_video(graph):
    """探测该 graph 是否为 MiniMax-H3 音画视频范式（存在 MiniMaxH3ImageToVideo 节点）。"""
    return any(isinstance(n, dict) and n.get("class_type") == _H3_VIDEO_NODE
               for n in graph.values())


def _find_nodes_by_class(graph, *class_types):
    """按 class_type 集合找节点，返回 [node_id]。"""
    return [str(nid) for nid, node in graph.items()
            if isinstance(node, dict) and node.get("class_type") in class_types]


def _resolve_ref(graph, ref):
    """把一个 [node_id, output_index] 引用解析为 (node_id, node)，非列表或非法则 (None, None)。"""
    if isinstance(ref, list) and len(ref) >= 1:
        nid = str(ref[0])
        node = graph.get(nid)
        if isinstance(node, dict):
            return nid, node
    return None, None


def apply_field_overrides(graph, args):
    """在已渲染的 graph 上做字段级语义注入（供导出 JSON 直接使用，无需 {{}}）。
    按范式分两条路：SD/通用（KSampler 定位）与 MiniMax-H3 视频（专属节点定位）。

    == SD / 通用范式 ==
    - prompt/negative -> 沿 KSampler.positive/negative 追溯 CLIPTextEncode.text
    - seed/steps/cfg/denoise -> KSampler 对应输入
    - 图片/视频上传名 -> LoadImage.image / VHS_LoadVideo.video
    - checkpoint -> CheckpointLoaderSimple.ckpt_name / UNETLoader.unet_name
    - width/height/frames -> 各类 Empty*Latent* 空 latent 节点
    - prefix -> SaveImage.filename_prefix / SaveAnimatedWEBP.filename_prefix

    == MiniMax-H3 视频范式（存在 MiniMaxH3ImageToVideo 节点）==
    - prompt -> MiniMaxH3ImageToVideo.prompt
    - seed -> RandomNoise.noise_seed
    - width/height -> ResolutionSelector 或 MiniMaxH3ImageToVideo.width/height
    - frames -> 帧数表达式链（PrimitiveFloat 值）
    - lora -> LoraLoaderModelOnly.lora_name

    返回 (graph, 已写入的字段列表)。"""
    written = []

    def _set(node_ids, input_key, value):
        if value is None:
            return
        for nid in node_ids:
            node = graph.setdefault(nid, {})
            inputs = node.setdefault("inputs", {})
            inputs[input_key] = value
            written.append((nid, input_key, value))

    # ================= 范式探测 =================
    if _is_h3_video(graph):
        return _apply_h3_overrides(graph, args, written)

    # ================= SD / 通用范式 =================
    sid, sampler = _find_sampler(graph)
    if sampler:
        for ref_attr, prompt_attr in (("positive", "prompt"), ("negative", "negative")):
            ref = (sampler.get("inputs") or {}).get(ref_attr)
            nid, node = _resolve_ref(graph, ref)
            val = getattr(args, prompt_attr, None)
            if val is not None and node and node.get("class_type") == "CLIPTextEncode":
                _set([nid], "text", val)

    # ---- 采样器参数：seed/steps/cfg/denoise ----
    if sampler and sid:
        for attr, field in (("seed", "seed"), ("steps", "steps"),
                            ("cfg", "cfg"), ("denoise", "denoise")):
            v = getattr(args, attr, None)
            if v is not None:
                _set([sid], field, v)

    # ---- 上传资源 ----
    if getattr(args, "_uploaded_image", None):
        _set(_find_nodes(graph, class_type="LoadImage"), "image", args._uploaded_image)
    if getattr(args, "_uploaded_video", None):
        _set(_find_nodes(graph, class_type="VHS_LoadVideo"), "video", args._uploaded_video)

    # ---- 模型：checkpoint -> 整包 或 UNET 分体 ----
    if args.checkpoint:
        ptr = False
        for nid, node in graph.items():
            if not isinstance(node, dict):
                continue
            ins = node.get("inputs") or {}
            if node.get("class_type") == "CheckpointLoaderSimple" and "ckpt_name" in ins:
                ins["ckpt_name"] = args.checkpoint
                written.append((nid, "ckpt_name", args.checkpoint))
                ptr = True
            elif node.get("class_type") == "UNETLoader" and "unet_name" in ins:
                ins["unet_name"] = args.checkpoint
                written.append((nid, "unet_name", args.checkpoint))
                ptr = True
        if not ptr:
            print("[warn] 未找到可写入 checkpoint 的节点（既无 CheckpointLoaderSimple 也无 UNETLoader）",
                  file=sys.stderr)

    # ---- LoRA：--lora NODE:文件 / 直接文件名 -> LoraLoader.lora_name ----
    lora_nodes = [nid for nid, node in graph.items()
                  if isinstance(node, dict) and node.get("class_type") == "LoraLoader"]
    if getattr(args, "lora", None):
        present = len(lora_nodes)
        for i, spec in enumerate(args.lora):
            # 支持 "NODE:文件名" 指定节点；否则按 LoraLoader 顺序（缺省取第一个）
            target_files = lora_nodes
            if ":" in spec and not spec.startswith("strength"):
                node_id, _, fname = spec.partition(":")
                node_id = node_id.strip()
                if node_id in graph:
                    target_files = [node_id]
                else:
                    print("[warn] --lora 指定的节点 '{}' 不存在，回退到第一个 LoraLoader".format(node_id), file=sys.stderr)
                    fname = spec
            else:
                fname = spec
            tids = target_files if target_files else lora_nodes
            if not tids:
                print("[warn] 未找到 LoraLoader 节点，--lora 忽略", file=sys.stderr)
                break
            nid = tids[min(i, len(tids) - 1)]
            graph.setdefault(nid, {}).setdefault("inputs", {})["lora_name"] = fname
            written.append((nid, "lora_name", fname))
        if present == 0:
            print("[warn] 模板中没有 LoraLoader 节点，--lora 未生效", file=sys.stderr)
    # LoRA 权重（作用于所有 LoraLoader）
    if lora_nodes:
        for nid in lora_nodes:
            ins = graph.setdefault(nid, {}).setdefault("inputs", {})
            if getattr(args, "lora_strength_model", None) is not None:
                ins["strength_model"] = args.lora_strength_model
                written.append((nid, "strength_model", args.lora_strength_model))
            if getattr(args, "lora_strength_clip", None) is not None:
                ins["strength_clip"] = args.lora_strength_clip
                written.append((nid, "strength_clip", args.lora_strength_clip))

    # ---- 空 latent 尺寸 / 帧数 ----
    if args.width or args.height or args.frames or args.batch:
        for nid, node in graph.items():
            if not isinstance(node, dict):
                continue
            cls = node.get("class_type") or ""
            if not cls.startswith("Empty") or "Latent" not in cls:
                continue
            ins = node.setdefault("inputs", {})
            if args.width:
                ins["width"] = args.width
                written.append((nid, "width", args.width))
            if args.height:
                ins["height"] = args.height
                written.append((nid, "height", args.height))
            if args.frames:
                key = "length" if "length" in ins else ("frames" if "frames" in ins else None)
                if key:
                    ins[key] = args.frames
                    written.append((nid, key, args.frames))
            if args.batch:
                if "batch_size" in ins:
                    ins["batch_size"] = args.batch
                    written.append((nid, "batch_size", args.batch))

    # ---- 输出前缀 ----
    for nid, node in graph.items():
        if not isinstance(node, dict):
            continue
        ins = node.get("inputs") or {}
        if (node.get("class_type") or "").startswith("Save") and "filename_prefix" in ins:
            if args.prefix:
                ins["filename_prefix"] = args.prefix
                written.append((nid, "filename_prefix", args.prefix))
    return graph, written


def _apply_h3_overrides(graph, args, written):
    """MiniMax-H3 音画视频范式的字段注入。该范式无 KSampler，注入点独立：
    - prompt -> MiniMaxH3ImageToVideo.prompt
    - seed   -> RandomNoise.noise_seed
    - width/height -> ResolutionSelector.aspect_ratio/megapixels（或直接写节点宽高）
    - frames -> 帧数表达式链里的输入值（ComfyMathExpression 上游的数字）
    - lora   -> LoraLoaderModelOnly.lora_name（+strength_model）
    - checkpoint -> UNETLoader.unet_name / VAELoader / CLIPLoader
    未识别的字段写入会通过首层 _set 辅助函数记录。"""
    def _setn(node_ids, key, value):
        for nid in node_ids:
            ins = graph.setdefault(nid, {}).setdefault("inputs", {})
            ins[key] = value
            written.append((nid, key, value))

    # ---- prompt -> MiniMaxH3ImageToVideo.prompt ----
    if args.prompt:
        _setn(_find_nodes_by_class(graph, "MiniMaxH3ImageToVideo"), "prompt", args.prompt)

    # ---- seed -> RandomNoise.noise_seed ----
    if args.seed is not None:
        _setn(_find_nodes_by_class(graph, "RandomNoise"), "noise_seed", args.seed)

    # ---- 尺寸：ResolutionSelector（推荐，保留宽高比逻辑）----
    if args.width or args.height:
        sel = _find_nodes_by_class(graph, "ResolutionSelector")
        if sel:
            # ResolutionSelector 用 aspect_ratio/megapixels 控制，宽高非直接可写
            if args.width and args.height:
                ratio = "16:9" if args.width >= args.height else "9:16"
                # megapixels 近似：按长边估算
                mp = round((args.width * args.height) / 1e6, 2)
                _setn(sel, "aspect_ratio", "{} (Widescreen)".format(ratio))
                _setn(sel, "megapixels", mp)
                for nid in sel:
                    # 部分实现允许直接写 width/height；作兜底
                    pass
        else:
            # 无 ResolutionSelector 则直接写 MiniMaxH3ImageToVideo 的宽高（若其 inputs 允许）
            _setn(_find_nodes_by_class(graph, "MiniMaxH3ImageToVideo"), "width", args.width)
            _setn(_find_nodes_by_class(graph, "MiniMaxH3ImageToVideo"), "height", args.height)

    # ---- 帧数：ComfyMathExpression 上游的数值输入（PrimitiveFloat/PrimitiveInt）----
    if args.frames:
        # H3 帧数由表达式计算，难以直接设；尝试写帧表达式链条里的首个数字节点
        for nid, node in graph.items():
            if isinstance(node, dict) and node.get("class_type") in ("ComfyMathExpression",):
                # 找到其 values.a 指向的数字节点
                vals = node.get("inputs") or {}
                for k, v in vals.items():
                    if isinstance(v, list) and v:
                        target = str(v[0])
                        tgt_node = graph.get(target)
                        if isinstance(tgt_node, dict) and tgt_node.get("class_type") in (
                                "PrimitiveFloat", "PrimitiveInt"):
                            tgt_node.setdefault("inputs", {})["value"] = args.frames
                            written.append((target, "value", args.frames))
                            break

    # ---- lora -> LoraLoaderModelOnly ----
    lora_nodes = _find_nodes_by_class(graph, "LoraLoaderModelOnly", "LoraLoader")
    for i, spec in enumerate(getattr(args, "lora", []) or []):
        fname = spec.split(":", 1)[-1].strip() if ":" in spec else spec
        if not lora_nodes:
            break
        nid = lora_nodes[min(i, len(lora_nodes) - 1)]
        _setn([nid], "lora_name", fname)
    if getattr(args, "lora_strength_model", None) is not None:
        for nid in lora_nodes:
            _setn([nid], "strength_model", args.lora_strength_model)
    if getattr(args, "lora_strength_clip", None) is not None:
        for nid in lora_nodes:
            _setn([nid], "strength_clip", args.lora_strength_clip)

    # ---- checkpoint -> UNETLoader / VAELoader / CLIPLoader ----
    if args.checkpoint:
        for cls, field in (("UNETLoader", "unet_name"), ("VAELoader", "vae_name"),
                           ("CLIPLoader", "clip_name")):
            _setn(_find_nodes_by_class(graph, cls), field, args.checkpoint)

    return graph, written


def cmd_run(args, cfg):
    needs_image = args.command in ("image-to-image", "image-to-video", "reference-to-video")
    if needs_image and not args.image:
        print("错误: {} 需要 --image <本地图片路径>".format(args.command), file=sys.stderr)
        return 2
    if args.command == "reference-to-video" and not args.video:
        print("错误: reference-to-video 需要 --video <本地参考视频路径>", file=sys.stderr)
        return 2

    wf_path = find_workflow(args.command, args.workflow)
    with open(wf_path, "r", encoding="utf-8") as f:
        template_text = f.read()
    defaults = extract_defaults(template_text)

    if args.image:
        print("[1/4] 上传图片 ...", file=sys.stderr)
        args._uploaded_image = upload_image(cfg, args.image)
    if getattr(args, "video", None):
        print("[1/4] 上传参考视频 ...", file=sys.stderr)
        args._uploaded_video = upload_image(cfg, args.video)

    values = build_values(args, cfg, defaults)
    try:
        rendered = render_workflow(template_text, values)
        graph = json.loads(rendered)
    except (RuntimeError, json.JSONDecodeError) as e:
        print("错误: workflow 渲染失败: {}".format(e), file=sys.stderr)
        return 2
    graph.pop("_defaults", None)

    # 字段级语义注入：导出 JSON 无 {{}} 时，也能按参数定位并写入对应节点输入
    graph, field_written = apply_field_overrides(graph, args)
    # --set 支持 NODE.FIELD=value（定位任意节点输入）与 KEY=value（占位符兼容）
    if args.set:
        for pair in args.set:
            if "=" not in pair:
                print("错误: --set 参数格式应为 KEY=VALUE 或 NODE.FIELD=VALUE: " + pair, file=sys.stderr)
                return 2
            k, v = pair.split("=", 1)
            k = k.strip(); v = _parse_scalar(v.strip())
            if "." in k:
                # 支持 NODE.INPUT.FIELD ... 逐点定位：node_id 为第一段，其余沿路径下钻
                parts = k.split(".")
                node_id = parts[0]
                cur = graph.setdefault(node_id, {})
                for seg in parts[1:-1]:
                    cur = cur.setdefault(seg, {})
                cur[parts[-1]] = v
                field_written.append((node_id, parts[1:], v))
            else:
                # 无节点前缀：写入 graph 中所有匹配该字段名的节点输入（字段语义兜底）
                for nid, node in graph.items():
                    if isinstance(node, dict) and k in (node.get("inputs") or {}):
                        node["inputs"][k] = v
                        field_written.append((nid, k, v))

    if args.dry_run:
        print(json.dumps({"prompt_graph": graph, "values": values,
                          "field_overrides": field_written}, ensure_ascii=False, indent=2))
        return 0

    if not check_health(cfg):
        return 3
    print("[2/4] 提交任务 (workflow: {}) ...".format(os.path.basename(wf_path)), file=sys.stderr)
    client_id = uuid.uuid4().hex
    try:
        pid = queue_prompt(cfg, graph, client_id)
        print("[3/4] prompt_id={} 等待执行 ...".format(pid), file=sys.stderr)
        entry = poll_history(cfg, pid)
    except (RuntimeError, TimeoutError) as e:
        print("错误: {}".format(e), file=sys.stderr)
        return 4

    files = collect_outputs(entry)
    print("[4/4] 完成，输出 {} 个文件".format(len(files)), file=sys.stderr)
    # 输出目录：以当前工作目录(cwd)为基础，而非 skill 根
    #  - --output 绝对路径：直接用，不追加类型/时间戳子目录
    #  - 否则：<cwd>/<config.dir 或 ./outputs>/<类型>/<时间戳>/   （按类型+时间戳分区，避免覆盖）
    # 输出目录：以当前工作目录(cwd)为基础，而非 skill 根
    #  - --output 绝对路径：直接用，不追加类型子目录
    # 输出目录：无论相对(基于 cwd)或绝对(--output)路径，都追加 <生成类型>/ 子目录，
    # 再在 download_file 内给文件名加时间戳。保证「按类型分区 + 时间戳文件名」一致。
    # 输出目录：稳定落在「会话工作目录」下的 outputs，按生成类型分区。
    #  - 默认：<会话工作目录>/outputs/<类型>/   （锚点从 DSH 会话记录解析，跟会话走、不随 bash cd 漂移）
    #  - --output：作为产出根（相对则基于会话工作目录），仍追加 <类型>/ 子目录
    # 不做任何"试探换路径"：只写这个位置；若只读/无权则明确报错定位，不引导切换。
    out_root = args.output or cfg["output"].get("dir", "./outputs")
    if not os.path.isabs(out_root):
        out_root = os.path.join(_session_cwd(), out_root)
    out_dir = os.path.join(out_root, args.command)  # args.command 即生成类型
    _makedirs(out_dir)  # 不存在则建；建立失败会抛出 OSError（含只读/无权限），交给外层统一报错定位
    downloaded, meta_list = [], []
    for meta in files:
        item = {k: meta[k] for k in ("filename", "subfolder", "type", "_kind") if k in meta}
        if cfg["output"].get("auto_download", True) and not args.no_download:
            try:
                item["local_path"] = download_file(cfg, meta, out_dir)
                downloaded.append(item["local_path"])
            except RuntimeError as e:
                item["download_error"] = str(e)
        meta_list.append(item)
    print(json.dumps({
        "prompt_id": pid,
        "seed": values.get("SEED"),
        "files": meta_list,
        "downloaded": downloaded,
    }, ensure_ascii=False, indent=2))
    return 0


# ---------------------------------------------------------------- 服务端发现

# 加载器节点 -> 对应"可下载模型槽位"的输入字段名（这些字段在 /object_info 中
# 是 combo 类型，其选项列表即服务端 models/ 下实际存在的文件名）
MODEL_SLOTS = {
    "CheckpointLoaderSimple": "ckpt_name",
    "UNETLoader": "unet_name",
    "LoraLoader": "lora_name",
    "VAELoader": "vae_name",
    "CLIPLoader": "clip_name",
    "CLIPVisionLoader": "clip_name",
    "ControlNetLoader": "control_net_name",
    "LoraLoaderModelOnly": "lora_name",       # MiniMax-H3 系（仅加载器）
}


def get_object_info(cfg):
    """GET /object_info -> {节点类名: 输入规格}（含自定义节点）。"""
    _, raw = _request(cfg, "GET", "/object_info", timeout=cfg["timeouts"].get("connect", 30))
    return json.loads(raw.decode("utf-8"))


def _combo_options(spec):
    """从输入规格里提取 combo 字段的选项列表（若存在）。"""
    if not isinstance(spec, dict):
        return None
    for section in ("required", "optional"):
        for field, detail in (spec.get(section) or {}).items():
            if isinstance(detail, list) and detail and isinstance(detail[0], list):
                yield field, [str(x) for x in detail[0]]


def cmd_info(args, cfg):
    """列出服务端可用的节点类与各加载器槽位的实际模型名。"""
    if not check_health(cfg):
        return 3
    info = get_object_info(cfg)
    print("服务端: {}  (节点类型 {} 个)".format(base_url(cfg), len(info)))
    print("自定义/可用节点（前 40 个）:")
    names = sorted(info)
    for n in names[:40]:
        print("  - " + n)
    if len(names) > 40:
        print("  ... 共 {} 个".format(len(names)))
    print("\n模型槽位（combo 列表 = 服务端真实可用的文件名）:")
    for cls, field in MODEL_SLOTS.items():
        spec = info.get(cls)
        if not spec:
            continue
        found = None
        for f, options in _combo_options(spec.get("input", {})):
            if f == field:
                found = options
                break
        if found is None:
            print("  [{}] {}: (未能从 combo 读取)".format(cls, field))
            continue
        print("  [{}] {}:  {} 个".format(cls, field, len(found)))
        for opt in found:
            print("      - " + opt)
    print("\n提示: 用这些槽位名核对模板 _defaults 里的模型名；用 `validate` 校验模板匹配度。")
    return 0


def cmd_validate(args, cfg):
    """校验某个 workflow 模板在服务端能否跑通：
    1) 依赖的节点 class_type 是否都已安装；
    2) 加载器字段引用的模型名是否在服务端 combo 里（仅对模板 _defaults/渲染值可解析的）。"""
    if not check_health(cfg):
        return 3
    gen_type = getattr(args, "type", None) or args.command
    wf_path = find_workflow(gen_type, args.workflow)
    with open(wf_path, "r", encoding="utf-8") as f:
        template_text = f.read()
    defaults = extract_defaults(template_text)
    info = get_object_info(cfg)

    # 渲染出 graph 以便校验（校验不真正生成：图片类无需上传，注入占位；审核模板结构）
    values = build_values(args, cfg, defaults)
    if not values.get("UPLOADED_IMAGE"):
        values["UPLOADED_IMAGE"] = "_placeholder_.png"
    if not values.get("UPLOADED_VIDEO"):
        values["UPLOADED_VIDEO"] = "_placeholder_.mp4"
    try:
        graph = json.loads(render_workflow(template_text, values))
    except (RuntimeError, json.JSONDecodeError) as e:
        print("错误: 模板渲染失败: {}".format(e), file=sys.stderr)
        return 2
    graph.pop("_defaults", None)

    # 与生成一致：叠加字段级注入，让 --checkpoint/--width 等在校验时也生效
    graph, _ = apply_field_overrides(graph, args)

    issues = []
    missing_nodes = []
    for node_id, node in graph.items():
        if not isinstance(node, dict):
            continue
        cls = node.get("class_type")
        if cls not in info:
            missing_nodes.append("节点 {}: class_type '{}' 未安装".format(node_id, cls))
            continue
        # 仅校验"加载器节点"的模型字段（ckpt/unet/lora/vae/clip/controlnet）；
        # 其它 combo 字段（如 LoadImage.image、VHS_LoadVideo.video 列出的是运行时
        # 上传的文件/资源名）属于运行期输入，不在此校验。
        model_field = MODEL_SLOTS.get(cls)
        if not model_field:
            continue
        for f, options in _combo_options(info[cls].get("input", {})):
            if f != model_field:
                continue
            val = (node.get("inputs") or {}).get(f)
            if isinstance(val, str) and val and options and val not in options:
                issues.append("节点 {}: {} = '{}' 不在服务端可用列表".format(node_id, f, val))
                print("    可用: " + ", ".join(options[:6]) + (" ..." if len(options) > 6 else ""))

    print("校验 workflow: {}  (服务端 {})".format(os.path.basename(wf_path), base_url(cfg)))
    print("  渲染后节点数: {} 个".format(len(graph)))
    if missing_nodes:
        print("  ❌ 缺失节点:")
        for m in missing_nodes:
            print("     - " + m)
    else:
        print("  ✅ 全部节点 class_type 已安装")
    if issues:
        print("  ❌ 模型名不匹配:")
        for i in issues:
            print("     - " + i)
    else:
        print("  ✅ 引用的模型名均可用")
    return 1 if (missing_nodes or issues) else 0


# ---------------------------------------------------------------- CLI

def build_parser():
    p = argparse.ArgumentParser(
        prog="comfyui_api.py",
        description="ComfyUI 统一 API 调用脚本（标准库实现）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="生成类型: " + ", ".join(KNOWN_TYPES) + "\n"
               "更多说明见 skills/ 下各子 skill 与 workflows/README.md")
    p.add_argument("--config", default=DEFAULT_CONFIG, help="配置文件路径（默认 config/comfyui.yaml）")
    p.add_argument("--server", help="覆盖服务地址，如 192.168.1.10:8188")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="列出服务地址与各类型可用 workflow")
    sub.add_parser("health", help="检查 ComfyUI 服务是否可达")
    sub.add_parser("info", help="发现服务端已安装节点与可用模型名（/object_info）")
    # validate 复用与生成类型一致的参数集，便于渲染模板后校验
    pv = sub.add_parser("validate", help="校验 workflow 模板在服务端能否跑通（节点/模型名匹配）")
    pv.add_argument("--type", choices=KNOWN_TYPES, help="生成类型（决定默认 workflow 目录）")
    add_gen_args(pv)

    pu = sub.add_parser("upload", help="上传图片到 ComfyUI input 目录")
    pu.add_argument("file", help="本地文件路径")

    for t in KNOWN_TYPES:
        sp = sub.add_parser(t, help="执行 {} 任务".format(t))
        add_gen_args(sp)
    return p


def add_gen_args(sp):
    """为生成/校验命令添加统一的可变参数集。"""
    sp.add_argument("--prompt", default=None, help="正向提示词（缺省用模板 _defaults/导出值）")
    sp.add_argument("--negative", default=None, help="负向提示词（默认取 workflow _defaults）")
    sp.add_argument("--image", help="输入图片本地路径（图生图/图生视频/参考生视频必填）")
    sp.add_argument("--video", help="参考视频本地路径（reference-to-video 用）")
    sp.add_argument("--seed", type=int, help="随机种子（缺省随机）")
    sp.add_argument("--width", type=int, help="宽度")
    sp.add_argument("--height", type=int, help="高度")
    sp.add_argument("--steps", type=int, help="采样步数")
    sp.add_argument("--cfg", type=float, help="CFG scale")
    sp.add_argument("--denoise", type=float, help="重绘幅度 0~1（图生图常用）")
    sp.add_argument("--frames", type=int, help="视频帧数")
    sp.add_argument("--fps", type=int, help="视频帧率")
    sp.add_argument("--checkpoint", help="模型文件名（覆盖配置）")
    sp.add_argument("--lora", action="append", metavar="NODE:FILE",
                    help="LoRA 名，可多次使用；格式 NODE:文件 或 直接文件名（写到 LoraLoader）。"
                         "如 --lora 10:svi-shot.safetensors --lora strength=1.2")
    sp.add_argument("--lora-strength-model", type=float, help="LoRA 模型权重 strength_model")
    sp.add_argument("--lora-strength-clip", type=float, help="LoRA CLIP 权重 strength_clip")
    sp.add_argument("--batch", type=int, help="一次生成的张数（写 Empty*Latent* 的 batch_size，默认取模板）")
    sp.add_argument("--prefix", help="输出文件名前缀")
    sp.add_argument("--workflow", help="指定 workflow JSON 路径（默认取 workflows/<类型>/default*.json）")
    sp.add_argument("--set", action="append", metavar="NODE.FIELD=VALUE",
                    help="按字段覆盖任意节点输入，如 5.inputs.cfg=5.5；也可用 FIELD=VALUE 匹配同名输入")
    sp.add_argument("--output", help="结果目录；绝对路径用该路径（不追加类型/时间戳），相对路径为 <cwd>/<该路径>/<类型>/<时间戳>/")
    sp.add_argument("--no-download", action="store_true", help="只生成不下载")
    sp.add_argument("--dry-run", action="store_true", help="只打印最终提交的 prompt JSON，不执行")


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not os.path.isfile(args.config):
        print("错误: 配置文件不存在: " + args.config, file=sys.stderr)
        return 2
    cfg = load_config(args.config)
    if args.server:
        if ":" in args.server:
            host, _, port = args.server.partition(":")
            cfg["server"]["host"], cfg["server"]["port"] = host, _parse_scalar(port)
        else:
            cfg["server"]["host"] = args.server
    try:
        if args.command == "list":
            return cmd_list(args, cfg)
        if args.command == "health":
            return cmd_health(args, cfg)
        if args.command == "info":
            return cmd_info(args, cfg)
        if args.command == "validate":
            return cmd_validate(args, cfg)
        if args.command == "upload":
            return cmd_upload(args, cfg)
        return cmd_run(args, cfg)
    except RuntimeError as e:
        print("错误: {}".format(e), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
