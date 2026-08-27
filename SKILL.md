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

### 第 2 步：提示词标准化

用户的口语化描述**不要直接提交**。读取对应标准：
- 图片类 → `prompt-guides/image-prompt-guide.md`
- 视频类 → `prompt-guides/video-prompt-guide.md`（按模型能力二选一：
  音画一体模型用 H3 三字段协议，规范详见 `prompt-guides/h3-video-prompt-protocol.md`；
  传统无声模型用连贯段落写法）

按标准产出英文正向提示词 + 负向提示词（H3 协议无负向提示词）。若用户明确要求跳过优化（"就用原话"），
则直接使用原始输入。

### 第 3 步：检查服务与参数

```bash
python3 scripts/comfyui_api.py health      # 确认服务可达
python3 scripts/comfyui_api.py list        # 查看各类型可用 workflow
```

服务不可达时：提示用户检查 ComfyUI 是否启动、地址是否正确
（`config/comfyui.yaml` 或 `--server host:port` 或环境变量 `COMFYUI_HOST/PORT`）。

### 第 4 步：调用生成

```bash
cd comfyui-suite
python3 scripts/comfyui_api.py <类型> \
    --prompt "<标准化后的正向提示词>" \
    --negative "<负向提示词>" \
    [--image <本地图片>] [--video <参考视频>] \
    [--seed N] [--width W --height H] [--steps N] \
    [--workflow <模板路径>] [--set KEY=VALUE]
```

- 先 `--dry-run` 校验最终 JSON（排障时使用）；
- 脚本自动上传图片 → 提交 → 轮询 → 下载结果到 `outputs/`，
  stdout 输出含 `local_path` 的 JSON；
- 详细参数见 `scripts/comfyui_api.py --help` 与各子 skill。
- 参数取值优先级：CLI 显式 > workflow `_defaults` > 报错缺参（seed 缺省随机）。

### 第 5 步：交付结果

向用户展示生成文件的本地路径；失败时根据 stderr 报错判断：
- 连接失败 → 配置/服务问题；
- 任务 error → workflow 与模型不匹配（提示按 `workflows/README.md` 重新导出模板）；
- 超时 → 调大 `config/comfyui.yaml` 的 `timeouts.poll_max`。
