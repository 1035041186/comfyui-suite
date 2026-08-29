# comfyui-suite — ComfyUI 生图/生视频组合技能

一个给 LLM agent 用的**组合技能包**：把用户的**文字描述 / 图片**需求自动路由到 **文生图、
图生图（含图文一起）、文生视频、图生视频、参考生视频** 之一，完成 **提示词标准化 → 调用
ComfyUI API → 取回结果**，最终把生成的图片/视频交给用户。

简单说：**你只要说"画一张…… / 把这张图改成…… / 让这张图动起来"，剩下交给它。**
不需要手写 ComfyUI 的 API JSON，也不需要懂工作流结构——脚本按"字段语义"自动注入参数。

---

## 目录结构

```
comfyui-suite/
├── SKILL.md                        # 总入口：路由规则 + 执行步骤 + 五步调度流程
├── README.md                       # 本文件（使用/安装/配置）
├── references/                     # 按需加载的参考文档
│   ├── guide.md                    # 使用/安装/扩展/配置分层说明
│   ├── models.md                   # 模型目录（用途、更换流程）
│   ├── reporting.md                # 交付报告规范与示例
│   ├── refine.md                   # 图片调整迭代决策表（不满意再改）
│   └── execution-plan.md           # 执行计划模型 + 跨宿主任务清单适配
├── scripts/
│   ├── comfyui_api.py              # 统一调用脚本（纯 Python 标准库，无需 pip）
│   └── install_skills.sh           # 一键挂载 8 个可调用入口
├── workflows/<类型>/*.json         # 各类型工作流模板（ComfyUI 导出，可替换）
├── prompt-guides/                  # 图片/视频提示词标准化参考
├── skills/<类型>/SKILL.md          # 子技能（单类型精细控制）
└── config/comfyui.yaml             # 服务连接配置（地址/超时/输出目录）
```

---

## 前置条件

- **一个可访问的 ComfyUI 服务**，且已装好你要用的模型与插件节点（默认连接地址见下文配置）。
- **Python 3.8+**（脚本纯标准库，不需要 `pip install`）。
- 图生图 / 图生视频 / 参考生视频需要**输入图片**（参考生视频还需一个**参考视频**）。

---

## 一、安装（挂载为可调用的技能）

1. 把 `comfyui-suite/` 目录放到你的项目根下（例如 `<项目根>/comfyui-suite`）。
2. 运行安装脚本，把入口挂到项目级技能目录：

```bash
cd comfyui-suite
bash scripts/install_skills.sh
```

脚本会在 `<项目根>/.dsh/skills/` 下创建 **8 个可调用入口**：

| 入口 | 作用 |
|---|---|
| `/comfyui-suite` | 总入口——自动判断生成类型并路由 |
| `/comfyui-text-to-image` | 文生图 |
| `/comfyui-image-to-image` | 图生图（含图文一起） |
| `/comfyui-text-to-video` | 文生视频 |
| `/comfyui-image-to-video` | 图生视频 |
| `/comfyui-reference-to-video` | 参考生视频 |
| `/comfyui-image-refine` | 图片调整迭代（对已生成图不满意时的多轮调整，不限次数） |
| `/comfyui-prompt-optimizer` | 提示词优化（只优化、不生成） |

> 说明：很多 agent 框架（如 DSH）只扫描技能目录的**一层**，所以脚本用"薄目录 + 软链接"方式
> 挂载，而不是复制文件。重载技能目录后即可用 `/comfyui-suite` 或 `/comfyui-<类型>` 调用。

---

## 二、配置

### 2.1 服务连接（`config/comfyui.yaml`）

这个文件**只管"怎么连上 ComfyUI"**：

```yaml
server:
  protocol: http        # http | https
  host: 10.0.0.1        # 你的 ComfyUI 服务地址（按部署改）
  port: 8188
  api_key: ""           # 若不启用 --api-key 留空

timeouts:
  connect: 10
  queue: 60
  poll_interval: 2
  poll_max: 1800        # 视频任务可调大

output:
  dir: outputs          # 相对会话工作根；最终 <会话根>/outputs/<类型>/
  auto_download: true

generate:
  batch: 1              # 每次任务的默认生成张数；CLI --batch 可覆盖，环境变量 COMFYUI_BATCH 也可
```

- **本仓库默认**连 `10.0.0.1:8188`；如果你没配置、也没读到配置，脚本会回退到 `127.0.0.1:8188`。
- 也可用**环境变量**覆盖，优先级最高：`COMFYUI_HOST`、`COMFYUI_PORT`、`COMFYUI_PROTOCOL`、
  `COMFYUI_API_KEY`、`COMFYUI_OUTPUT_DIR`、`COMFYUI_BATCH`。

### 2.2 生成参数（尺寸/步数/模型名）——**不在配置文件里**

尺寸、步数、cfg、模型名这类生成参数**跟随工作流模板**写在各模板的 `_defaults` 里
（例如 SDXL 模板默认 1024×1024、Wan 视频模板默认 1280×720@16fps）。换模板即换默认值，
避免写进全局配置和模板打架。你想要单次覆盖，直接用 CLI 参数（`--width/--steps/--checkpoint/...`）。

> **唯一例外：`generate.batch`**（每次生成张数）。因为同一部署通常固定出图数量，所以作为全局默认
> 放在配置里，默认 1；需要临时改时用 `--batch N`，优先级 `CLI --batch > generate.batch > 模板值`。

### 2.3 模型与工作流

- **模型名必须真实存在于你的服务端**。用 `python3 scripts/comfyui_api.py info` 查看服务端
  真实可用模型清单；`references/models.md` 记录各模型的常见用途。
- **工作流模板** = 你在 ComfyUI 里「Save (API Format)」导出的 JSON，直接放进对应类型目录即可，
  **模板里不需要任何 `{{}}` 占位符**，参数由脚本按字段语义自动注入。

---

## 三、使用

### 方式一：当作 Agent 技能用（推荐）

直接对 agent 描述需求，它会自动分步执行（并以任务清单展示进度）：

```
"画一张夏日海边写实图"
"用这张图当背景，加一个奔跑的女孩"
"让这张风景图动起来"
"参考这个角色的图 + 这段运镜的视频，生成新视频"
```

### 方式二：直接命令行调用（脚本）

```bash
cd comfyui-suite

# 0) 先确认服务与可用模板
python3 scripts/comfyui_api.py health     # 服务可达？
python3 scripts/comfyui_api.py list       # 各类型有哪些 workflow（* 为默认）

# 1) 文生图
python3 scripts/comfyui_api.py text-to-image \
    --prompt "a cute cat sitting on a windowsill, warm light" --seed 42

# 2) 图生图（保留构图、改风格/加东西）
python3 scripts/comfyui_api.py image-to-image \
    --prompt "a young woman running" --image in.png --denoise 0.6

# 3) 文生视频
python3 scripts/comfyui_api.py text-to-video \
    --prompt "the ocean waves roll gently" --frames 49 --fps 16

# 4) 图生视频（首帧驱动）
python3 scripts/comfyui_api.py image-to-video \
    --prompt "the camera slowly pans right" --image first.png

# 5) 参考生视频（角色图 + 运镜参考视频）
python3 scripts/comfyui_api.py reference-to-video \
    --prompt "keep the character, perform this motion" \
    --image role.png --video ref.mp4
```

### 输入图片/视频的取值

`--image` / `--video` 接受两种来源（职责分明）：

| 取值 | 说明 |
|---|---|
| **本地文件路径** | 用户上传、显式给路径、或 agent 定位/拼接得到的原图路径，如 `--image in.png` |
| **`-`** | 从**标准输入**读 **base64**（`data:image/...;base64,` 或裸 base64），不落盘、无命令行长度限制 |

> 决策：**只有 base64 用 `-`；只有文件路径用路径；二者都有且路径能一步直接拿到（无需查找/构造）用路径。**
> 关键：base64 指**作为输入真正存在的 base64**——别把磁盘文件再编码成 base64 去走 base64 通道；已能拿到路径就用路径。
> 全程只有 `-` 代表 base64，其它一律按文件路径处理。脚本会对 base64 做图片格式校验，识别不出就报错。

### 常用参数

| 参数 | 作用 |
|---|---|
| `--seed` | 随机种子（复现；缺省随机） |
| `--width/--height/--frames/--fps` | 尺寸 / 帧数 / 帧率 |
| `--steps/--cfg` | 采样步数 / CFG |
| `--denoise` | 重绘幅度 0–1（图生图用；越低越贴近原图） |
| `--checkpoint` | 替换模型文件（覆盖模板默认） |
| `--lora` | 加 LoRA（`NODE:文件名`） |
| `--set NODE.FIELD=VALUE` | 精确覆盖任意节点输入（如 `5.inputs.cfg=5.5`） |
| `--workflow <文件>` | 指定用哪套模板（默认用该类型 `default_` 那套） |
| `--dry-run` | 只打印最终提交的 JSON，不真生成（校验用） |

**产出目录**：脚本会自动落到 `<会话工作根>/outputs/<生成类型>/`。想先确定路径，可运行
`python3 scripts/comfyui_api.py output-path --root <会话根> --type <类型>`。

---

## 四、重要提示

- **模板先验证再使用**：自带的 workflow（尤其**视频类**）是**骨架参考**——不同部署的模型
  与节点差异很大。首次使用请在你的 ComfyUI 界面搭好并跑通，再用「Save (API Format)」
  导出覆盖对应目录，方法见 `workflows/README.md`。
- **跨模型栈不要硬套**：不同模板对应不同模型栈（SD 整包 / Krea2 分体 / MiniMax-H3 / Wan），
  节点接入方式不同。换栈请换对应模板，不要为了换风格把一个栈套到另一个栈。
- **模型名以服务端为准**：不要臆造不在 `info` 清单里的文件名。
- **失败排查**：连不上 → 配置/服务问题；任务 error → 模板与模型不匹配（按 `workflows/README.md`
  重新导出）；超时 → 调大 `config/comfyui.yaml` 的 `timeouts.poll_max`。

---

## 五、扩展新类型

新增一种生成类型（如"视频生视频"、"局部重绘"）：

1. 在 `workflows/<new-type>/` 放入导出的模板 JSON（规范见 `workflows/README.md`）；
2. 在 `scripts/comfyui_api.py` 的 `KNOWN_TYPES` 与 `build_parser()` 注册新命令；
3. 新建 `skills/<new-type>/SKILL.md`（复制最近似的子技能修改）；
4. 总入口 `SKILL.md` 的路由表加一行；
5. `scripts/install_skills.sh` 的 `link_skill` 列表加一行，重跑即挂载。

详见 `references/guide.md`「扩展指南」。
