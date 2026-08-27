# 图片提示词编写标准（文生图 / 图生图）

目标：把用户零散口语化描述，转成结构完整、可直接喂给扩散模型的英文提示词。

## 标准结构（按此顺序组织）

```
[画质词], [主体], [主体细节/动作/表情/服饰], [场景/环境], [构图/镜头], [光照], [风格/媒介], [色彩氛围]
```

各部分写法：

1. **画质词**（前置，权重高）：`masterpiece, best quality, ultra detailed, 8k`
2. **主体**：明确的可数名词 + 数量，如 `1girl, a fluffy orange cat`
3. **细节**：动作 (`sitting, looking at viewer`)、表情 (`smiling, closed eyes`)、
   服饰 (`white dress, red ribbon`)
4. **场景**：`in a sunlit forest, cyberpunk city street at night`
5. **构图/镜头**：`close-up / full body / cowboy shot, from above, rule of thirds, depth of field, bokeh`
6. **光照**：`soft lighting, golden hour, rim light, neon lights, volumetric lighting`
7. **风格/媒介**：`photorealistic / anime style / oil painting / watercolor / 3d render, octane render / pixel art`
8. **色彩氛围**：`warm color palette, pastel colors, moody, dreamy atmosphere`

## 规则

- 用**英文短语**、逗号分隔；不写完整句子（写实模型）——自然语言长句仅用于
  SD3/Flux 等 T5 编码器模型，此时用一段连贯描述。
- 权重强调：`(keyword:1.2)` 加强、`(keyword:0.8)` 减弱（SD1.5/SDXL 语法）。
- 用户没提的维度按场景合理补全，**不要**编造与用户意图冲突的内容。
- 中文描述一律翻译为英文（二次元 tag 体系可用 Danbooru tag）。
- 最终同时输出：正向提示词 + 负向提示词（见下方模板）。

## 负向提示词通用模板

- 写实：`lowres, bad anatomy, bad hands, missing fingers, extra fingers, deformed, blurry, worst quality, watermark, text, signature`
- 二次元：`lowres, bad anatomy, bad hands, extra digits, cropped, worst quality, low quality, jpeg artifacts, watermark, text`

## 示例

用户输入："帮我画一只猫在窗台上晒太阳，日系治愈风"

输出：
- prompt: `masterpiece, best quality, a fluffy orange cat, lying on a wooden windowsill, basking in sunlight, eyes closed, content expression, cozy room interior, potted plants, soft natural lighting through window, warm color palette, anime style, healing atmosphere, depth of field`
- negative: `lowres, bad anatomy, worst quality, low quality, jpeg artifacts, watermark, text`

## 图生图补充

- 提示词聚焦"要改成什么"，与输入图一致的部分不必重复描述；
- 配合 `--denoise`：微调 0.3–0.45 / 风格迁移 0.5–0.7 / 大改 0.75–0.9；
- 保留构图：denoise ≤ 0.5，并在提示词中重申关键构图元素。
