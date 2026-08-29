---
name: comfyui-reference-to-video
description: 通过 ComfyUI API 参考生视频：用户提供两张参考图（首帧/尾帧或角色/风格），想生成"以这些参考为锚点的音画一体新视频"时使用（MiniMax-H3 Ref2VA/FL2VA 音画模型）。隶属 comfyui-suite 组合 skill，总入口见 comfyui-suite/SKILL.md。
---

# 参考生视频（reference-to-video）

输入：文字描述 + 两张参考图（首帧/尾帧，或角色/风格）。输出：视频+音频一体文件。

典型场景："用这张图当开头、那张图当结尾，补出中间动作并配音"、"让角色（图）以该画风动起来"。

> 当前默认模板是 **MiniMax-H3 Ref2VA/FL2VA**（音画一体），用**两帧参考图**驱动：
> `--image`（首帧→`ref_image_0`）+ `--image2`（尾帧→`ref_image_1`）。若你换用旧
> Wan/VACE 视频控制类模板，才用 `--image`(角色) + `--video`(运镜)，见"参数要点"。

## 流程

1. **确认素材**：两张参考图，本地路径（也可经 stdin 传 base64，`--image -`；
   两张都用 `-` 时仅一张可行，第二张请给文件路径）。向用户确认
   "首帧取什么、尾帧取什么、中间要补的运动/叙事"。
2. **提示词标准化**：读取 `prompt-guides/video-prompt-guide.md`，选 **H3 协议**——按素材数量用
   FL2VA（首+尾帧）或 I2VA/L2VA（单参考图），指令行 + 三字段写法见
   `prompt-guides/h3-video-prompt-protocol.md`；提示词内写清 `<Picture 1>`/`<Picture 2>`
   与目标视频的锚定时刻。
3. **确认模板**：`workflows/reference-to-video/default_minimax_h3_r2v.json`
   需是你用 ComfyUI「Save (API Format)」导出并跑通的 H3 导出 JSON
   （依赖 MiniMax-H3 自定义节点与配套 CLIP / 双 VAE）。
4. **调用**（脚本自动上传两张图）：

```bash
cd comfyui-suite
python3 scripts/comfyui_api.py reference-to-video \
    --prompt "How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark ..." \
    --image /path/to/first_frame.png \
    --image2 /path/to/last_frame.png
```

5. **交付**：按 `references/reporting.md` 的交付报告规范汇报——说清**调用序列**（用了哪些子 skill、顺序）
   与调用链（类型→工作流→模型）、关键参数（frames 尺寸 lora）与实际命令。结果用两条并给出：`preview_url`
   （host/port 从 `config/comfyui.yaml` 读取，与服务地址一致；视频不能内联成 `<img>`，直接放链接即可）；
   `downloaded`/`local_path` 即本地结果路径，用 inline code 引用告诉用户文件存放位置。

## 参数要点

| 参数 | 说明 |
|---|---|
| `--image` | 首帧/起始参考图（**必填**）：本地路径 或 `-`（stdin 读 base64，仅一张可走此通道） |
| `--image2` | 尾帧/结束参考图：本地路径；缺省复用 `--image`（两张相同，用于单参考锚定） |
| `--video` | 旧 Wan/VACE 视频控制类才需要；H3 Ref2VA/FL2VA 工作流会忽略（脚本有警告） |
| `--frames` | H3 帧数由表达式链推算；需变时长改模板里 `PrimitiveFloat/Int.value` 或用 `--set` |
| `--set KEY=VALUE` | 控制类模板额外参数（控制强度等）用它覆盖 |

> **质量档**：默认**低质量档**（快）；画质不满意 → 换**高质量档**重跑，配套 CLIP/VAE 不变
> （Ref2VA 具体切换命令见 `references/models.md`「质量档位」）。

## 默认模板

`workflows/reference-to-video/default_minimax_h3_r2v.json`（你导出的 H3 API JSON）。
H3 范式：`--prompt` 写入 H3 音画节点 `.prompt`，`--image/--image2` 分别写入 `ref_image_0/1`
所驱动的 `LoadImage`，`--seed` 写入 `RandomNoise.noise_seed`。务必用你跑通的 H3 导出 JSON，
不要硬套旧 Wan/VACE 骨架。

## 常见问题

- 参考图未被使用 → 模板中 `ref_images.*` 链路未接通，回到第 3 步重新导出。
- 结果既不像首帧也不像尾帧 → 提示词的锚定时刻/运动路径写得不够，或控制权重失衡（`--set`）。
- 节点类不存在（`MiniMaxH3ReferenceToVideo`/`MiniMaxH3ImageToVideo`）→ 需安装 MiniMax-H3 自定义节点。
