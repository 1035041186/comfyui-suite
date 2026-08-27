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


def download_file(cfg, meta, out_dir):
    params = urllib.parse.urlencode({
        "filename": meta["filename"],
        "subfolder": meta.get("subfolder", ""),
        "type": meta.get("type", "output"),
    })
    _, raw = _request(cfg, "GET", "/view?" + params, timeout=300)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, meta["filename"])
    with open(path, "wb") as f:
        f.write(raw)
    return path


# ---------------------------------------------------------------- 工作流渲染

_PLACEHOLDER = re.compile(r'"\{\{\s*([A-Z0-9_]+)\s*\}\}"|\{\{\s*([A-Z0-9_]+)\s*\}\}')

# 需转为 JSON 数字的占位符
NUMERIC_KEYS = {"SEED", "WIDTH", "HEIGHT", "STEPS", "CFG", "DENOISE",
                "FRAMES", "FPS", "VIDEO_LENGTH"}

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
    default = [f for f in candidates if f.startswith("default")]
    return os.path.join(folder, default[0] if default else candidates[0])


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
        if v is not None:
            values[key.upper()] = v
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
    print("可用生成类型与 workflow：")
    for t in KNOWN_TYPES:
        folder = os.path.join(SKILL_ROOT, "workflows", t)
        files = sorted(f for f in os.listdir(folder) if f.endswith(".json")) if os.path.isdir(folder) else []
        print("  {:<20} {}".format(t, ", ".join(files) if files else "(无，请导出添加)"))
    extra = [d for d in sorted(os.listdir(os.path.join(SKILL_ROOT, "workflows")))
             if d not in KNOWN_TYPES and os.path.isdir(os.path.join(SKILL_ROOT, "workflows", d))]
    if extra:
        print("  扩展类型: " + ", ".join(extra))
    return 0


def cmd_health(args, cfg):
    ok = check_health(cfg)
    print("{} {}".format(base_url(cfg), "OK" if ok else "UNREACHABLE"))
    return 0 if ok else 3


def cmd_upload(args, cfg):
    name = upload_image(cfg, args.file)
    print(json.dumps({"uploaded_name": name}, ensure_ascii=False))
    return 0


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

    if args.dry_run:
        print(json.dumps({"prompt_graph": graph, "values": values}, ensure_ascii=False, indent=2))
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
    out_dir = args.output or cfg["output"].get("dir", "./outputs")
    if not os.path.isabs(out_dir):
        out_dir = os.path.join(SKILL_ROOT, out_dir)
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

    pu = sub.add_parser("upload", help="上传图片到 ComfyUI input 目录")
    pu.add_argument("file", help="本地文件路径")

    for t in KNOWN_TYPES:
        sp = sub.add_parser(t, help="执行 {} 任务".format(t))
        sp.add_argument("--prompt", default="", help="正向提示词")
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
        sp.add_argument("--prefix", help="输出文件名前缀")
        sp.add_argument("--workflow", help="指定 workflow JSON 路径（默认取 workflows/<类型>/default*.json）")
        sp.add_argument("--set", action="append", metavar="KEY=VALUE",
                        help="覆盖模板任意占位符，可多次使用，如 --set LORA=my.safetensors")
        sp.add_argument("--output", help="结果下载目录（覆盖配置 output.dir）")
        sp.add_argument("--no-download", action="store_true", help="只生成不下载")
        sp.add_argument("--dry-run", action="store_true", help="只打印最终提交的 prompt JSON，不执行")
    return p


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
        if args.command == "upload":
            return cmd_upload(args, cfg)
        return cmd_run(args, cfg)
    except RuntimeError as e:
        print("错误: {}".format(e), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
