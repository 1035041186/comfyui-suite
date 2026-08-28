---
name: comfyui-image-to-video
description: 通过 ComfyUI API 图生视频：用户提供一张图片，想让它动起来（作为首帧/主体生成视频）时使用。隶属 comfyui-suite 组合 skill，总入口见 comfyui-suite/SKILL.md。
---

# 图生视频（image-to-video）

输入：本地图片（首帧/主体）+ 文字描述（描述**运动**）。输出：视频文件。

## 流程

1. **确认输入图**：本地路径，或经 stdin 传 base64（`--image -`，跨 agent / 不落盘 / 无 argv 上限）；图片内容即视频首帧/主体，先向用户确认想保留的主体。
2. **提示词标准化**：读取 `prompt-guides/video-prompt-guide.md` 选协议——
   音画一体模型用 **H3 协议的 I2VA 写法**（首帧锚定指令行 + 三字段，
   "首帧锚定 → 动作起始 → 连续发展 → 结果/反应"）；传统无声模型则
   **不要重复描述图中已有静态内容，重点写运动**：谁怎么动、镜头怎么动、环境怎么变。
3. **调用**（脚本自动上传图片）：

```bash
cd comfyui-suite
python3 scripts/comfyui_api.py image-to-video \
    --prompt "The woman gently raises her hand ... camera slowly pushes in ..." \
    --image /path/to/first_frame.png \
    --width 1280 --height 720 --frames 49 --fps 16 --steps 30
```

4. **交付**：按 `references/reporting.md` 的交付报告规范汇报——说清**调用序列**（用了哪些子 skill、顺序）
   与调用链（类型→工作流→模型）、关键参数（frames/fps/尺寸）与实际命令。结果用两条并给出：`preview_url`
   （host/port 从 `config/comfyui.yaml` 读取，与服务地址一致；视频不能内联成 `<img>`，直接放链接即可）；
   `downloaded`/`local_path` 即本地结果路径，用 inline code 引用告诉用户文件存放位置。

## 参数要点

| 参数 | 说明 |
|---|---|
| `--image` | 首帧图片：本地文件路径 或 `-`（stdin 读 base64）（**必填**） |
| `--frames/--fps` | 同 text-to-video；动作幅度小可用 33 帧 |
| `--width/--height` | 建议与输入图比例一致，避免拉伸 |
| 其余 | 同 text-to-video |

## 默认模板

`workflows/image-to-video/default_*.json`（你导出的 API JSON）。
**请用你服务端实际跑通的 I2V 导出 JSON 替换**：`--image` 上传后写入 `LoadImage.image`，
提示词写入 CLIPTextEncode，`--frames/--width/--height` 写入空 latent 节点。
不同 I2V 模型（Wan/SVD/HunyuanVideo/H3）节点接入不同，务必用对应导出 JSON。

## 常见问题

- 主体跑偏/换人 → 提示词中重申主体关键特征；降低 cfg。
- 几乎不动 → 运动描述太弱，明确写动作动词和镜头运动。
- 输入图比例与 width/height 不一致 → 画面拉伸，先裁剪图片或调整尺寸参数。
