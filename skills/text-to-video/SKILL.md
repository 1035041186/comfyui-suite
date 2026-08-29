---
name: comfyui-text-to-video
description: 通过 ComfyUI API 文生视频。用户只有文字描述、想生成视频/动画/短片时使用。隶属 comfyui-suite 组合 skill，总入口见 comfyui-suite/SKILL.md。
---

# 文生视频（text-to-video）

输入：文字描述。输出：视频文件（默认 webp 动图，可换 SaveVideo/CombineVideo 节点输出 mp4）。

## 流程

1. **提示词标准化**：读取 `prompt-guides/video-prompt-guide.md` 选协议——
   模板含音频节点（音画一体模型）用 **H3 三字段协议**（规范见
   `prompt-guides/h3-video-prompt-protocol.md`）；传统无声模型（Wan/HunyuanVideo）
   整理为一段 50–120 词英文连贯描述（主体+动作+场景+镜头+光照+风格）。
2. **确认服务与模板**：视频模型节点差异大，首次使用前确认
   `workflows/text-to-video/default_minimax_h3_t2v.json`（MiniMax-H3 T2VA 音画一体）
   已在 ComfyUI 界面验证可用（见 `workflows/README.md`）。
3. **调用**：

```bash
cd comfyui-suite
python3 scripts/comfyui_api.py text-to-video \
    --prompt "A young woman ... camera slowly pushes in ..." \
    --negative "blurry, low quality, distorted, ..." \
    --width 1280 --height 720 --frames 49 --fps 16 --steps 30
```

4. **交付**：按 `references/reporting.md` 的交付报告规范汇报——说清**调用序列**（用了哪些子 skill、顺序）
   与调用链（类型→工作流→模型）、关键参数（frames/fps/尺寸）。结果用两条并给出：`preview_url`
   （host/port 从 `config/comfyui.yaml` 读取，与服务地址一致；视频不能内联成 `<img>`，直接放链接即可）；
   `downloaded`/`local_path` 即本地结果路径，用 inline code 引用告诉用户文件存放位置。视频任务耗时长，必要时调大
   `config/comfyui.yaml` 的 `timeouts.poll_max`（默认 1800s）。

## 参数要点

| 参数 | 说明 |
|---|---|
| `--frames` | 帧数，取 8n+1（17/33/49/81）；49 帧 @16fps ≈ 3 秒 |
| `--fps` | 默认 16（Wan 系）；MiniMax-H3 模板用 24（`CreateVideo.fps`，脚本不改写，需改用时 `--set`） |
| `--width/--height` | 须贴近模型训练分辨率：1280×720（横）/ 720×1280（竖） |
| `--steps` | 视频默认建议 30–40 |
| `--cfg` | 视频模型通常 5–6，过高易变形 |

> **质量档**：默认**低质量档**（快）；画质不满意 → 换**高质量档**重跑，配套 CLIP/VAE 不变
> （FL2VA 具体切换命令见 `references/models.md`「质量档位」）。

## 默认模板

`workflows/text-to-video/default_minimax_h3_t2v.json`（MiniMax-H3 T2VA 音画一体，你导出的 API JSON）。
H3 范式注入点独立：`--prompt` 写入 H3 音画节点 `.prompt`，`--width/--height` 写入
`ResolutionSelector`，`--frames` 写帧数表达式链，`--checkpoint` 写入 `UNETLoader.unet_name`。
H3 无单独 negative（负向内容写在 prompt 内）。视频模型节点结构差异大（Wan/HunyuanVideo/H3），
务必用对应导出 JSON。

## 常见问题

- 动作变形/闪烁 → 动作描述太复杂，拆成单一动作；提高 steps；检查 negative 是否含 morphing/flickering。
- 超时 → poll_max 调大，或减少 frames / 分辨率。
- 节点不存在错误 → 模板与部署模型不匹配，重新导出模板。
