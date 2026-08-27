---
name: comfyui-prompt-optimizer
description: 提示词优化：把用户零散口语化描述按标准方法整理为适合文生图/图生图/文生视频等模型的高质量提示词（英文正向+负向），只输出提示词、不执行生成。隶属 comfyui-suite 组合 skill，生成时会自动内联使用本方法。
---

# 提示词优化（prompt-optimizer）

把用户的零散语句 → 标准化提示词。**本 skill 只产出提示词，不调用 ComfyUI。**
（生成类子 skill 内部会自动执行同样方法；用户只要提示词时单独使用本 skill。）

## 方法

### 1. 判断目标类型与协议

- 图片（文生图/图生图）→ 读 `prompt-guides/image-prompt-guide.md`
- 视频 → 读 `prompt-guides/video-prompt-guide.md`，再按模型能力二选一：
  - 音画一体模型（模板含音频节点）→ **H3 协议**：指令行 +
    `integrated_multimodal_description` / `overall_soundscape` / `non_diegetic_music`
    三字段（完整规范见 `prompt-guides/h3-video-prompt-protocol.md`）；
  - 传统无声模型（Wan2.1/HunyuanVideo/SVD）→ 50–120 词连贯段落。

### 2. 抽取与补全维度

从用户描述中抽取已有维度，缺失维度按场景**合理补全但不违背用户意图**：

| 图片 | 视频（H3 协议） | 视频（传统） |
|---|---|---|
| 主体/细节/场景/构图镜头/光照/风格/色彩 | 任务分型(首/尾帧)/风格/镜头切分与运镜三维/主体动作/台词与说话人/环境音/配乐 | 主体/动作/场景/镜头运动/光照氛围/风格 |

拿不准的关键维度（风格、画幅、有无台词配乐）向用户确认。

### 3. 产出

**图片**：tag 式英文短语串（画质词前置，逗号分隔）+ 负向提示词模板。
**视频（传统）**：50–120 词英文连贯段落 + 负向提示词模板。
**视频（H3 协议）**：指令行（关键帧任务）+ 三个核心字段，逐字段成段；
此时不需要传统负向提示词（音画一体模型不使用 negative prompt）。

### 4. 输出格式（固定）

```
【类型】text-to-image / image-to-image / text-to-video / ...
【正向提示词】
<prompt>
【负向提示词】
<negative>
【建议参数】
width×height / steps / cfg / (denoise | frames+fps) / 说明
【补全说明】  # 哪些维度是 AI 补全的，用户可修正
...
```

## 示例

用户："帮我画一只猫在窗台上晒太阳，日系治愈风"

```
【类型】text-to-image
【正向提示词】
masterpiece, best quality, a fluffy orange cat, lying on a wooden windowsill,
basking in sunlight, eyes closed, content expression, cozy room interior,
potted plants, soft natural lighting through window, warm color palette,
anime style, healing atmosphere, depth of field
【负向提示词】
lowres, bad anatomy, worst quality, low quality, jpeg artifacts, watermark, text
【建议参数】1024×1024, steps 20, cfg 7
【补全说明】橘猫毛色、木质窗台、室内绿植为补全细节，可指定修改。
```

## 注意

- 中文输入一律转英文提示词（模型以英文语料训练）；
- 用户说"就用原话/不要优化"时原样输出，不强行改写；
- 与生成联用时，优化结果直接作为生成命令的 `--prompt/--negative`。
