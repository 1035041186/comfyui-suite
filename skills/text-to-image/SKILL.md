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

4. **交付**：按 `references/reporting.md` 的交付报告规范汇报——说清**调用序列**（用了哪些子 skill、顺序）
   与调用链（类型→工作流→模型）、关键参数（seed/尺寸/steps/cfg）与实际命令；
   `downloaded` 字段即本地图片路径（默认 `outputs/`）。

## 参数要点

**模板 = 你导出的 ComfyUI API JSON（无 `{{}}`）；参数由脚本按字段语义注入对应节点**
（详见 `workflows/README.md`）。LLM 只传高级参数，无需懂模板结构。

| 参数 | 注入到 | 说明 |
|---|---|---|
| `--prompt` | 采样器 positive→CLIPTextEncode.text | 正向提示词（标准化后的英文，必填） |
| `--negative` | 采样器 negative→CLIPTextEncode.text | 负向提示词（缺省用模板内已有值） |
| `--width/--height` | 空 latent 节点 | 缺省用模板/导出值；SDXL 建议 1024 起步 |
| `--steps` | KSampler | 缺省用模板值；细节不够可加到 28–35 |
| `--seed` | KSampler | 固定 seed 复现；缺省随机 |
| `--cfg` | KSampler | 提示词遵循度（缺省用模板值）；过高易过饱和 |
| `--checkpoint` | `CheckpointLoaderSimple.ckpt_name` 或 `UNETLoader.unet_name` | 换模型（须存在于服务端 models/） |
| `--workflow` | — | 换用同目录其他模板 |
| `--set NODE.FIELD=VALUE` | 任意节点输入 | 精确覆盖，如 `5.inputs.cfg=5.5`、`10.inputs.lora_name=...` |

> 取值优先级：CLI > 模板/导出硬编码值。尺寸/模型不读配置文件。
> 用 `--dry-run` 查看字段注入结果，`validate` 确认模型匹配服务端。

## 默认模板

`workflows/text-to-image/default_*.json`（你导出的 API JSON）。当前 `default_sdxl.json`
为示例导出产物（Krea/Qwen 分体栈：UNET+CLIP+VAE+Lora），**请用你服务端实际跑通的
导出 JSON 替换**——字段注入器自动识别它是整包还是分体加载。

## 常见问题

- 结果与描述不符 → 提示词未标准化，回到第 1 步；或调高 `--cfg`。
- 报 model 不存在 → `--checkpoint` 指定的文件名与服务端不一致。
- 想要多张 → 用不同 `--seed` 多次调用。
