---
name: comfyui-text-to-image
description: 通过 ComfyUI API 文生图。用户只有文字描述、想生成图片（海报/插画/头像/壁纸等）时使用。隶属 comfyui-suite 组合 skill，总入口见 comfyui-suite/SKILL.md。
---

# 文生图（text-to-image）

输入：文字描述。输出：图片文件。

## 流程

1. **提示词标准化**：读取 `prompt-guides/image-prompt-guide.md`，把用户描述整理为
   英文正向提示词 + 负向提示词（结构：画质词→主体→细节→场景→构图→光照→风格）。
2. **确认服务**：`python3 scripts/comfyui_api.py health`
3. **调用**：

```bash
cd comfyui-suite
python3 scripts/comfyui_api.py text-to-image \
    --prompt "masterpiece, best quality, ..." \
    --negative "lowres, bad anatomy, ..." \
    --width 1024 --height 1024 --steps 20 --seed 12345
```

4. **交付**：stdout JSON 的 `downloaded` 字段即本地图片路径（默认 `outputs/`）。

## 参数要点

| 参数 | 说明 |
|---|---|
| `--prompt` | 正向提示词（标准化后的英文，必填） |
| `--negative` | 负向提示词（缺省用模板 `_defaults.negative`） |
| `--width/--height` | 缺省用模板 `_defaults`（SDXL 模板为 1024×1024） |
| `--steps` | 缺省用模板 `_defaults`（20）；细节不够可加到 28–35 |
| `--seed` | 固定 seed 可复现结果；缺省随机 |
| `--cfg` | 提示词遵循度，缺省用模板（7）；过高易过饱和 |
| `--checkpoint` | 切换模型（文件名须存在于服务端 models/checkpoints；缺省用模板 `_defaults.checkpoint`） |
| `--workflow` | 换用同目录其他模板（如 flux），其 `_defaults` 随之生效 |
| `--set KEY=VALUE` | 覆盖模板任意占位符，如 LoRA |

> 取值优先级：CLI > 模板 `_defaults`。尺寸/模型不读配置文件。

## 默认模板

`workflows/text-to-image/default_sdxl.json`（SDXL：CheckpointLoader → CLIPTextEncode
×2 → KSampler → VAEDecode → SaveImage）。换模型后按 `workflows/README.md` 重新导出。

## 常见问题

- 结果与描述不符 → 提示词未标准化，回到第 1 步；或调高 `--cfg`。
- 报 model 不存在 → `--checkpoint` 指定的文件名与服务端不一致。
- 想要多张 → 用不同 `--seed` 多次调用。
