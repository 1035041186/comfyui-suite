---
name: comfyui-suite
description: ComfyUI 本地生图/生视频服务的自动化总入口（组合 skill）。当用户要求"生成图片、画一张图、生成视频、做动画、图生图、图生视频、参考生视频、优化提示词/prompt"且环境中有可访问的 ComfyUI 服务（默认 127.0.0.1:8188）时使用。自动分析用户描述路由到对应类型（文生图/图生图/文生视频/图生视频/参考生视频），执行提示词标准化、调用 ComfyUI API、取回生成结果。
---

# ComfyUI Suite — 自动化总入口

组合 skill：一个总入口（本文件）+ 6 个子 skill + 统一调用脚本 + workflow 模板库 +
提示词标准库 + 配置文件。**本文件只做调度**；使用/安装/扩展/配置分层等参考信息
见 `references/guide.md`（运行时按需读取）。

## 调度流程

### 第 1 步：路由 —— 判断生成类型

按**输入素材 + 用户意图**路由，优先级从上到下：

| 条件 | 类型 | 脚本命令 |
|---|---|---|
| 用户提供了图片 **和** 参考视频，想生成新视频 | reference-to-video | `reference-to-video` |
| 用户提供了图片，意图是生成**视频**（让图动起来） | image-to-video | `image-to-video` |
| 用户提供了图片，意图是**改图/重绘/换风格** | image-to-image | `image-to-image` |
| 无图片，意图是**视频/动画/短片** | text-to-video | `text-to-video` |
| 无图片，意图是**图片/海报/插画/头像**（默认兜底） | text-to-image | `text-to-image` |

判定关键词参考：视频类——"视频、动画、动起来、短片、clip、video、animate"；
图生图——"改、重绘、换成、P 图、以这张图为基础、风格化这张图"；
参考生视频——"参考这个视频的动作/运镜、让这个角色照视频里那样动"。

无法唯一判定时（如"用这张图做点什么"），向用户确认目标类型。

### 第 1.5 步：类型内路由（同类型有多个工作流时）

**一个类型可能有多套工作流模板**（如 `text-to-image` 有 SD 整包 + Krea2 分体）。此时在同一类型内选哪个：

1. **先 `python3 scripts/comfyui_api.py list`**：看该类型下有哪些 JSON；`*` 标的是**默认**。
2. **默认**：用户没提具体模型栈 → 用标 `*` 的默认工作流（不传 `--workflow`）。
3. **换工作流**：仅当用户需求**明确指向非默认栈**时，才 `--workflow <文件名>`。判断依据：
   - 工作流**文件名携带的语义**（如 `default_sd15_base` = SD1.5 整包、`krea2` = Krea2 分体）；
   - `references/models.md` 里各模型栈的用途（`info` 确认服务端真实模型）。
4. **不跨栈自动换**：不同工作流是**不同模型栈**（SD 整包 / Krea2 分体 / MiniMax-H3），节点接入方式不同，**不要**为了换风格就把一个工作流硬套到另一个栈上；跨栈必须换对应工作流。
5. 不确定就用默认工作流，或向用户确认。

> 例：`text-to-image` 下——用户要"SD 写实风" → 默认 `default_sd15_base`；要"Krea2 特有模型" → `--workflow krea2.json`。

### 第 2 步：提示词标准化

用户的口语化描述**不要直接提交**。读取对应标准：
- 图片类 → `prompt-guides/image-prompt-guide.md`
- 视频类 → `prompt-guides/video-prompt-guide.md`（按模型能力二选一：
  音画一体模型用 H3 三字段协议，规范详见 `prompt-guides/h3-video-prompt-protocol.md`；
  传统无声模型用连贯段落写法）

按标准产出英文正向提示词 + 负向提示词（H3 协议无负向提示词）。若用户明确要求跳过优化（"就用原话"），
则直接使用原始输入。

> 提示词注入落点因工作流而异：SD/Krea2 模板 → `CLIPTextEncode.text`（`--negative` 写 CLIPTextEncode）；
> MiniMax-H3 视频模板 → `MiniMaxH3ImageToVideo.prompt`（无单独 negative，负向内容写进 prompt 内）。
> 脚本按范式自动定位，LLM 无需关心落点。

### 第 3 步：检查服务并选择模型

```bash
python3 scripts/comfyui_api.py health      # 确认服务可达
python3 scripts/comfyui_api.py list        # 查看各类型可用 workflow
python3 scripts/comfyui_api.py info        # 查看服务端已装节点 + 各槽位真实模型
```

**选择模型**（模板 `_defaults.checkpoint` 只是兜底，按用户需求覆盖）：
1. 读 `references/models.md`，按需求（生图/生视频、写实/二次元、是否音画一体）
   挑候选模型名；
2. 用 `validate --type <类型> --checkpoint <候选>` 确认候选在服务端存在；
3. 用 `--checkpoint <文件名>`（或 `--set CHECKPOINT=<文件名>`）替换模板默认模型；
4. 多模型联动（换视频 UNET 需同步换匹配的 VAE/CLIP，如 `MiniMax-H3\...`
   要配 `MiniMax-H3_VideoVAE`）：这些联动以你**导出并跑通的 H3 工作流**为准，
   不要臆造节点/模型名；不确定时向用户展示 `info` 的真实清单让其选择。

服务不可达时：提示用户检查 ComfyUI 是否启动、地址是否正确
（`config/comfyui.yaml` 或 `--server host:port` 或环境变量 `COMFYUI_HOST/PORT`）。

### 第 4 步：调用生成

**模板 = 你导出的 ComfyUI API JSON（无 `{{}}`），参数由脚本按字段语义注入**。
LLM 只需传高级参数，代码负责定位并写入正确节点，无需懂模板结构：

```bash
cd comfyui-suite
python3 scripts/comfyui_api.py <类型> \
    --prompt "<标准化后的正向提示词>" \
    --negative "<负向提示词>" \
    [--image <本地图片>] [--video <参考视频>] \
    [--seed N] [--width W --height H] [--steps N] [--cfg C] [--denoise D] \
    [--checkpoint <模型名>] [--lora <NODE:文件名>] [--lora-strength-model 1.2 --lora-strength-clip 0.9] \
    [--workflow <模板路径>] [--set NODE.INPUT.FIELD=VALUE]
```

**`--workflow` 的选择规则（LLM 自主判断，无需用户明确指定）：**
- 默认：**不传** `--workflow`，脚本自动用该类型 `default_` 前缀（无则第一个）模板；
- 换模板：先跑 `python3 scripts/comfyui_api.py list`，看该类型下有哪些 JSON（`*` 是默认）；
- 何时显式指定 `--workflow`：仅当用户要求**特定风格/尺寸/模型栈**、或 **list 显示该类型
  有多个模板**且默认那个明显不匹配用户的生成意图时，才传 `--workflow <文件名>`；
- 用户没提具体模板时，**一律不传** `--workflow`，交给默认模板。

字段注入对应关系（详见 `workflows/README.md`）：
- `--prompt/--negative` → 沿采样器 `positive/negative` 引用追溯到 CLIPTextEncode；
- `--seed/--steps/--cfg/--denoise` → KSampler；
- `--checkpoint` → `CheckpointLoaderSimple.ckpt_name` 或 `UNETLoader.unet_name`；
- `--lora <NODE:文件名>` → `LoraLoader.lora_name`；`--lora-strength-model/clip` → 对应权重；
- `--width/--height/--frames` → 空 latent 节点；`--image/--video` → 上传后文件名；
- `--set NODE.FIELD=VALUE` → 精确覆盖任意节点输入（如 `5.inputs.cfg=5.5`）。

- 先 `--dry-run` 校验最终 JSON（能正确注入、排除错误时使用）；
- 脚本自动上传图片 → 提交 → 轮询 → 下载结果到 `outputs/`，stdout 输出含 `local_path`；
- 详细参数见 `scripts/comfyui_api.py --help` 与各子 skill；
- 参数取值优先级：**CLI 显式 > workflow 自带硬编码值**（`--dry-run` 看注入结果确认）。

### 第 5 步：交付报告

向用户交付时，**用一段可读的中文说明**，清楚交代「我用了哪个类型、哪套工作流、哪个模型、
哪些关键参数」，同时把命令与参数放在代码块里承载精确值。**不要只丢一个文件路径或一堆 JSON**。

报告结构（按此组织，描述自然，参数精确）：

```
【调用链】类型 → 工作流 → 模型
> 判定：为什么路由到这个类型（输入素材 + 用户意图）
> 工作流：default_sd15_base（SD 整包）/ krea2（Krea2 分体）/ ...；默认 or --workflow 显式
> 模型：oneObsession_v23（默认）或依据 info/models.md 换成了 xxx

【关键参数】
> 提示词摘要：<一句话概括正向/负向内容，别整段贴>
> seed / width / height / steps / cfg / denoise / frames / lora 逐个列出

【实际命令】（代码块）
python3 scripts/comfyui_api.py <类型> --prompt "..." --seed N --width W --height H ...

【结果】
> 文件：<本地路径>（outputs/ 下）
> 校验：validate 是否通过（模型名/节点匹配）｜失败原因
```

**要点**
- 调用链与参数**必须写具体值**（模型名、seed、尺寸、lora），这是判断"用没用对"的依据；
- 描述用**自然语言**，参数用**代码块精确呈现**，二者结合，避免整段命令/JSON 堆砌；
- 以上小标题的字段属建议，语气可灵活，但**调用链 + 参数 + 结果三块必须齐全**；
- 若执行失败，同样按报告格式呈现，并说明失败阶段（连接/渲染/任务 error/超时）与依据
  （`validate` 提示、stderr 报错）。

### 失败排查（第 5 步附）

向用户展示生成文件的本地路径；失败时根据 stderr 报错判断：
- 连接失败 → 配置/服务问题；
- 任务 error → workflow 与模型不匹配（提示按 `workflows/README.md` 重新导出模板）；
- 超时 → 调大 `config/comfyui.yaml` 的 `timeouts.poll_max`。

---

## 交付报告示例（照此格式模仿）

> 以下是一个"文生图、SD 写实、换了模型"的完整报告示例，展示如何把调用路径与参数写成
> 可读又不失精确的说明。

【调用链】文生图 → SD 整包（default_sd15_base）→ 模型 majicmixRealistic_v7

> **为什么是文生图**：用户只给了文字描述，没有图片，是"画一张图"的意图。
> **工作流**：该类型有两套——默认 `default_sd15_base`（SD 整包）与 `krea2`（Krea2 分体）。
> 用户要的是"写实人像"，读 `references/models.md` 发现 SD 整包里的写实模型更契合，
> 但默认模板的 `oneObsession_v23` 偏二次元，所以换成写实的 `majicmixRealistic_v7`。
> 模型栈不变（仍是 SD 整包），故沿用默认工作流，只换 `--checkpoint`。

【关键参数】
> 正向提示词：写实人像 + 柔和光照 + 浅景深（完整英文见下方命令）
> 负向提示词：模糊、瑕疵、水印
> seed=42 ｜ width/height=1024×1024 ｜ steps=30 ｜ cfg=7 ｜ denoise=1.0 ｜ 无 LoRA

【实际命令】
```bash
python3 scripts/comfyui_api.py text-to-image \
    --prompt "a realistic portrait, soft cinematic lighting, shallow depth of field, 8k" \
    --negative "blurry, bad anatomy, watermark" \
    --seed 42 --width 1024 --height 1024 --steps 30 --cfg 7 \
    --checkpoint majicmixRealistic_v7.safetensors
```

【结果】
> 文件：`outputs/t2i_84f1a2.webp`（可通过 `list` + `info` 反查该模板的模型栈）
> 校验：`validate --type text-to-image --checkpoint majicmixRealistic_v7.safetensors`
> 通过（模型名存在于服务端、节点已安装）。
