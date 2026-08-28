---
name: comfyui-reference-to-video
description: 通过 ComfyUI API 参考生视频：用户提供角色/风格参考图 + 动作/运镜参考视频，想生成"这个角色照这个方式动"的新视频时使用（VACE/Fun 类控制模型）。隶属 comfyui-suite 组合 skill，总入口见 comfyui-suite/SKILL.md。
---

# 参考生视频（reference-to-video）

输入：文字描述 + 参考图片（角色/风格）+ 参考视频（动作/运镜）。输出：视频文件。

典型场景："让这个角色（图）做出这个视频里的动作"、"用这个画风重现这段运镜"。

## 流程

1. **确认两份素材**：参考图与参考视频都必须是本地路径；向用户确认
   "从图里取什么（外观/风格）、从视频里取什么（动作/运镜/深度）"。
2. **提示词标准化**：读取 `prompt-guides/video-prompt-guide.md`——
   音画一体模型按素材数量选 **H3 协议的 I2VA/FL2VA/L2VA**（单参考图→I2VA；
   首+尾帧→FL2VA；仅尾帧→L2VA，指令行与时间戳写法见
   `prompt-guides/h3-video-prompt-protocol.md`）；传统模型写清参考元素与
   生成内容的关系，如
   `keep the character appearance from the reference image, performing the motion from the reference video`。
3. **确认模板**：该类工作流依赖 VACE / Wan-Fun / Control 类自定义节点，
   随模型版本变化最大。**必须**先在 ComfyUI 界面搭建跑通并按
   `workflows/README.md` 导出覆盖 `workflows/reference-to-video/default_wan_vace.json`。
4. **调用**（脚本自动上传图片与视频）：

```bash
cd comfyui-suite
python3 scripts/comfyui_api.py reference-to-video \
    --prompt "keep the character appearance ... performing the motion ..." \
    --image /path/to/character.png \
    --video /path/to/motion_ref.mp4 \
    --frames 49 --fps 16 --steps 30
```

5. **交付**：按 `references/reporting.md` 的交付报告规范汇报——说清调用链（类型→工作流→模型）与
   关键参数（frames 尺寸 lora）与实际命令，`downloaded` 字段即结果路径。

## 参数要点

| 参数 | 说明 |
|---|---|
| `--image` | 角色/风格参考图（**必填**） |
| `--video` | 动作/运镜参考视频（**必填**） |
| `--frames` | 建议与参考视频帧数对齐（模板内 `frame_load_cap` 用它截断） |
| `--set KEY=VALUE` | 控制类模板常有额外占位符（控制强度等），用它覆盖 |

## 默认模板

`workflows/reference-to-video/default_*.json`（你导出的 API JSON）。
**请用你服务端实际跑通的参考生视频导出 JSON 替换**：`--image`/`--video` 上传后写入
`LoadImage.image`/`VHS_LoadVideo.video`。该类模型的控制信号接入（VACE/H3 等）
因部署而异，务必用你跑通的导出 JSON，不要硬套占位符骨架。

## 常见问题

- 参考视频未被使用 → 模板中控制信号链路未接通，回到第 3 步。
- 结果既不像图也不像视频 → 控制权重失衡，调模板中控制强度参数（--set）。
- VHS_LoadVideo 节点不存在 → 需安装 ComfyUI-VideoHelperSuite 自定义节点。
