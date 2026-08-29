---
name: comfyui-suite
description: ComfyUI 本地生图/生视频服务的自动化总入口（组合 skill）。当用户要求"生成图片、画一张图、生成视频、做动画、图生图、图生视频、参考生视频、优化提示词/prompt"，或**对已生成的图片不满意要去修/调整/再改/重画一张**（图片修复迭代路径）时使用；后者自动路由到 `image-refine` 的调整路径。环境中有可访问的 ComfyUI 服务（默认 127.0.0.1:8188）时，自动分析用户描述路由到对应类型（文生图/图生图/文生视频/图生视频/参考生视频/图片修复迭代），执行提示词标准化、调用 ComfyUI API、取回生成结果。
---

# ComfyUI Suite — 自动化总入口

本文件=**调度器**：路由 + 五步计划。类型级执行细节在**子 skill**（`skills/<类型>/SKILL.md`），
配置分层在 `references/guide.md`，报告规范在 `references/reporting.md`，提示词标准在
`prompt-guides/`，模板/字段注入机制在 `workflows/README.md` —— **用到再读，不要全量加载**。

## 执行纪律（减少 LLM 往返）

1. **一次推理完成「路由 + 提示词」**：第 1、2 步同一轮做完——先定类型，顺手产出标准化提示词，别拆成两次 LLM 往返。
2. **合并独立检查**：`health`/`list`/`info` 用一条 shell 命令串起来跑（`&&`），不要三次独立调用。
3. **按需才 `validate` 与重读**：换模型/栈、或不确定时才 `validate`；已读文档直接复用，不重读同一份。

## 执行步骤清单（可移植计划，随进度同步宿主任务清单）

| # | 步骤 | 说明 |
|---|---|---|
| 1 | 路由判定 | 按输入素材+意图确定生成类型（同类型多工作流时选默认 / `--workflow`） |
| 2 | 提示词标准化 | 读对应 `prompt-guides/*`，产出英文正/负向提示词 |
| 3 | 服务检查与选模型 | `health/list/info`（一条命令）+ 依 `references/models.md` 选 `--checkpoint`（`validate` 确认） |
| 4 | 调用生成 | 定输出目录 + 注入参数 + 上传图 + 提交/轮询/取回 |
| 5 | 交付报告 | 调用链/参数/结果（完整规范见 `references/reporting.md`） |

> 计划数据/宿主映射规范见 `references/execution-plan.md`。

> **调整迭代（多次/多轮，不限次数）**：首次生成走上面五步；用户对结果不满意要再改时，
> **先问"这张该不该留作基准"**——完全不喜欢 → 回到文生图**重新生成**（不基于旧图）；
> 骨架满意 → 基于上一轮输出迭代。迭代时**复用此计划但额外携带"迭代上下文"**（第 N 轮、
> 基准图=上一轮输出、固化 seed 除变化轴外不动）并只动一个主导轴。判定与"症状→杠杆"表见
> `references/refine.md` 与 `skills/image-refine/SKILL.md`（编排层，非独立生成类型）。

## 第 1 步：路由

按**输入素材 + 意图**路由（优先级从上到下）：

| 条件 | 类型 | 子 skill / 脚本 |
|---|---|---|
| 有参考图（首/尾帧、角色/风格）或参考视频，想生成新视频 | reference-to-video | `reference-to-video` |
| 有图片，意图是**视频** | image-to-video | `image-to-video` |
| 有图片，意图是**改图/重绘/换风格** | image-to-image | `image-to-image` |
| 无图片，意图是**视频/动画** | text-to-video | `text-to-video` |
| 无图片，意图是**图片**（默认兜底） | text-to-image | `text-to-image` |
| **上一轮已成图，对其不满意再调整** | image-refine | `image-refine` |

关键词：视频类——"视频/动画/短片/clip/video/animate"；图生图——"改/重绘/换成/P图/风格化"；
参考生视频——"参考这张图的角色/风格"、"参考首尾帧"、"参考这个视频的动作/运镜"；
**调整迭代**——"不满意/再改/重画一版/这版不行/换成另一种风格/细节不够"。
无法唯一判定时，向用户确认目标类型。

> **迭代优先**：上一轮已生成一张图、用户对其不满意要求"再调整"时，**优先路由到 `image-refine`**
> （它是编排层：先定基准取舍——完全不喜欢→重生成、不基于旧图；骨架满意→基于上一张迭代；再定少动/大动）。
> **而不是**简单重新走 `text-to-image` 一次照画。
> 「基准取舍 + 少动/大动」判定与"症状→杠杆"决策表见 `references/refine.md`。

### 类型内路由（同类型有多个工作流）

一个类型可有多套模板（如 `text-to-image` 有 SD 整包 + Krea2 分体）。选哪个：

1. 先 `python3 scripts/comfyui_api.py list` 看该类型有哪些 JSON（`*`=默认）。
2. **默认**：用户没指定模型栈 → 用标 `*` 的（不传 `--workflow`）。
3. **换栈**：仅当需求**明确指向非默认栈**才 `--workflow <文件名>`，依据是**文件名语义**
   （如 `default_sd15_base`=SD1.5 整包、`krea2`=Krea2 分体）+ `references/models.md`。
4. **不跨栈自动换**：不同工作流=不同模型栈、节点接入不同；换栈必须换对应工作流，别把 A 栈硬套到 B。
5. 不确定就用默认，或问用户。

> 例：要"SD 写实" → 默认 `default_sd15_base`；要"Krea2 特有模型" → `--workflow krea2.json`。

### 类型资源查表（按类型调用对应子 skill / 提示词标准）

| 类型 | 子 skill | 提示词标准 | 默认模板 |
|---|---|---|---|
| text-to-image | `skills/text-to-image/SKILL.md` | `image-prompt-guide.md` | `default_sd15_base.json` |
| image-to-image | `skills/image-to-image/SKILL.md` | `image-prompt-guide.md` | `default_sd15_img2img.json` |
| text-to-video | `skills/text-to-video/SKILL.md` | `video-prompt-guide.md`（H3→`h3-video-prompt-protocol.md`） | `default_minimax_h3_t2v.json` |
| image-to-video | `skills/image-to-video/SKILL.md` | `video-prompt-guide.md`（H3→`h3-video-prompt-protocol.md` I2VA） | `default_minimax_h3_i2v.json` |
| reference-to-video | `skills/reference-to-video/SKILL.md` | `video-prompt-guide.md`（H3→`h3-video-prompt-protocol.md`，按素材选 I2VA/FL2VA/L2VA） | `default_minimax_h3_r2v.json` |

## 第 2 步：提示词标准化

用户的口语化描述**不要直接提交**。按类型读对应标准，产出英文正向 + 负向提示词（H3 无负向）：

- 图片类 → `prompt-guides/image-prompt-guide.md`
- 视频类 → `prompt-guides/video-prompt-guide.md`（音画一体模型用 **H3 三字段协议**，规范见
  `prompt-guides/h3-video-prompt-protocol.md`；传统无声模型用连贯段落写法）

用户明确要求跳过优化（"就用原话"）才直接用原始输入。
> 提示词注入落点因工作流而异（SD/Krea2→`CLIPTextEncode.text`、MiniMax-H3→`MiniMaxH3ImageToVideo.prompt`），
> 脚本按范式自动定位，LLM 无需关心落点。

## 第 3 步：服务检查与选模型

```bash
# 一条命令合并（减少往返）：
python3 scripts/comfyui_api.py health && python3 scripts/comfyui_api.py list && python3 scripts/comfyui_api.py info
```

**选模型**（模板 `_defaults.checkpoint` 只是兜底，按用户需求覆盖）：
1. 读 `references/models.md`，按需求（生图/生视频、写实/二次元、音画一体）挑候选模型名；
2. 用 `validate --type <类型> --checkpoint <候选>` 确认候选在服务端存在；
3. 用 `--checkpoint <文件名>`（或 `--set CHECKPOINT=<文件名>`）替换模板默认模型；
4. 多模型联动（换视频 UNET 需同步换匹配的 VAE/CLIP，如 `MiniMax-H3\...` 配 `MiniMax-H3_VideoVAE`）：
   以你**导出并跑通的 H3 工作流**为准，不臆造节点/模型名；不确定时向用户展示 `info` 的真实清单。

服务不可达 → 提示用户检查 ComfyUI 是否启动、地址是否正确（`config/comfyui.yaml` / `--server host:port` / 环境变量 `COMFYUI_HOST/PORT`）。

> **H3 生视频质量档**：模板默认绑定**低质量档**（快）。用户对画质不满意 → 换**对应高质量档**重跑
> （FL2VA / Ref2VA 各有一档；具体文件名与切换命令见 `references/models.md`「质量档位」）。

## 第 4 步：调用生成

**先定产出目录，不要猜**：`pwd` 取会话工作根，再用
`python3 scripts/comfyui_api.py output-path --root <会话根> --type <类型>` 显式求出
（<会话根>/`outputs`/`<类型>`/）；覆盖产出根用 `--output <绝对路径>`（仍追加 `<类型>/`）。

模板 = 你导出的 ComfyUI API JSON（无 `{{}}`），参数由脚本**按字段语义**注入，LLM 传高级参数即可：

```bash
cd comfyui-suite
python3 scripts/comfyui_api.py <类型> \
    --root <会话工作根> --prompt "<英文正向>" --negative "<英文负向>" \
    [--image <本地路径或base64>] [--image2 <第二张参考图, 尾帧>] \
    [--seed N] [--width W --height H] [--steps N] [--cfg C] [--denoise D] \
    [--checkpoint <模型名>] [--lora <NODE:文件名>] [--lora-strength-model 1.2 --lora-strength-clip 0.9] \
    [--workflow <模板路径>] [--set NODE.INPUT.FIELD=VALUE]
```

- **字段注入映射 / H3 范式 / 多模板路由 / 模板放置**：见 `workflows/README.md`；各类型入参细节见对应**子 skill**。
- **`--image`/`--video`（base64 与路径二选一）**：只有 base64 → 用 `-`（stdin 读，不落盘、无 argv 上限）；已能一步拿到文件路径 → 直接用路径（**不要**把磁盘文件再编码成 base64 走 base64 通道）；二者都有且路径能一步拿到 → 用路径。全程只有 `-` 代表 base64。
- `--workflow` 默认用该类型 `default_` 前缀模板（不传即默认）；换模板先 `list`。
- 先 `--dry-run` 校验注入；优先级 `CLI 显式 > 模板硬编码`；默认张数 `CLI --batch > config generate.batch(1) > 模板值`，默认不一次出多张。

## 第 5 步：交付报告

用一段**可读的中文说明**交代**调用序列**（用了哪些子 skill、按什么顺序，含跳过的步骤）、
**调用链**（类型→工作流→模型）、**关键参数**、**结果**；参数用代码块精确呈现，描述用自然语言，
**不要只丢一个文件路径或一堆 JSON**。完整规范与示例见 **`references/reporting.md`**（交付前按需参考）。

失败按阶段定位：连接失败 → 配置/服务问题；任务 error → workflow 与模型不匹配（按 `workflows/README.md` 重新导出模板）；超时 → 调大 `config/comfyui.yaml` 的 `timeouts.poll_max`。
