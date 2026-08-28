---
name: comfyui-image-to-image
description: 通过 ComfyUI API 图生图（含图文一起生图）：用户提供图片并要求修改、重绘、换风格、扩图、以图为基础创作时使用。隶属 comfyui-suite 组合 skill，总入口见 comfyui-suite/SKILL.md。
---

# 图生图（image-to-image，含图文一起生图）

输入：本地图片 + 文字描述（文字描述改什么、改成什么样）。输出：图片文件。

## 流程

1. **确认输入图**：必须是 agent 可访问的本地路径；URL 先下载。向用户确认
   "保留什么、改变什么"。
2. **提示词标准化**：读取 `prompt-guides/image-prompt-guide.md`（末尾有图生图专节）。
   提示词聚焦"目标状态"，保留构图时重申关键构图元素。
3. **确定 denoise（重绘幅度）**——图生图最关键参数：
   - 0.3–0.45：微调（修瑕疵、小幅美化、提升质感）
   - 0.5–0.7：风格迁移、换季节/光照、换材质
   - 0.75–0.9：大幅改动，仅保留大致构图
4. **调用**（脚本自动先把图片上传到服务端 input 目录）：

```bash
cd comfyui-suite
python3 scripts/comfyui_api.py image-to-image \
    --prompt "..." --negative "..." \
    --image /path/to/input.png \
    --denoise 0.6 --seed 12345
```

5. **交付**：按 `references/reporting.md` 的交付报告规范汇报——说清**调用序列**（用了哪些子 skill、顺序）
   与调用链（类型→工作流→模型）、关键参数（denoise/seed/尺寸）与实际命令，`downloaded` 字段即结果路径。

## 参数要点

| 参数 | 说明 |
|---|---|
| `--image` | 输入图片本地路径（**必填**） |
| `--denoise` | 重绘幅度 0–1，默认 0.6；越低越贴近原图 |
| `--prompt` | 目标画面描述；留空则仅按噪声重绘（不推荐） |
| `--seed` | 调参对比时固定 seed，只变 denoise |
| 其余 | 同 text-to-image（width/height 默认跟随输入图 latent，模板内不显式缩放） |

## 默认模板

`workflows/image-to-image/default_*.json`（你导出的 API JSON）。
**请用你服务端实际跑通的导出 JSON 替换**——`--image` 上传后由脚本写入
`LoadImage.image`，`--denoise` 写入 KSampler；字段注入器自动识别节点结构。
"图文一起生图"（文+图共同条件）默认即覆盖；需 IP-Adapter/ControlNet 等可控生成时，
用含相应节点的导出 JSON，并以 `--workflow` 指定。

## 常见问题

- 改得不像/没变化 → denoise 太低；改得面目全非 → denoise 太高。
- 输出分辨率 = 输入图分辨率；想放大请先生成再走放大工作流。
- 上传失败 → 确认图片格式为 png/jpg/webp 且文件未损坏。
