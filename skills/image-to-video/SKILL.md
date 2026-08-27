---
name: comfyui-image-to-video
description: 通过 ComfyUI API 图生视频：用户提供一张图片，想让它动起来（作为首帧/主体生成视频）时使用。隶属 comfyui-suite 组合 skill，总入口见 comfyui-suite/SKILL.md。
---

# 图生视频（image-to-video）

输入：本地图片（首帧/主体）+ 文字描述（描述**运动**）。输出：视频文件。

## 流程

1. **确认输入图**：本地路径；图片内容即视频首帧/主体，先向用户确认想保留的主体。
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

4. **交付**：`downloaded` 字段为结果路径。

## 参数要点

| 参数 | 说明 |
|---|---|
| `--image` | 首帧图片本地路径（**必填**） |
| `--frames/--fps` | 同 text-to-video；动作幅度小可用 33 帧 |
| `--width/--height` | 建议与输入图比例一致，避免拉伸 |
| 其余 | 同 text-to-video |

## 默认模板

`workflows/image-to-video/default_wan_i2v.json`（Wan2.1 I2V 骨架：LoadImage →
CLIPVisionEncode 提供图像条件 → KSampler → VAEDecode → SaveAnimatedWEBP）。
不同 I2V 模型（SVD、Wan-I2V、HunyuanVideo-I2V）节点不同，务必按实际部署重新导出。

## 常见问题

- 主体跑偏/换人 → 提示词中重申主体关键特征；降低 cfg。
- 几乎不动 → 运动描述太弱，明确写动作动词和镜头运动。
- 输入图比例与 width/height 不一致 → 画面拉伸，先裁剪图片或调整尺寸参数。
