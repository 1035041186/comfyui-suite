# 模型目录 & 选择指引（按用户需求更换 checkpoint/模型）

> 这是**语义层**：把 `scripts/comfyui_api.py info` 读到的**真实模型文件名**，
> 标注其**常见用途**，供 LLM 根据用户需求 pick 合适的模型，然后
> 用 `--checkpoint <name>`（或模板 `--set MODEL=...`）替换，再用
> `validate` 确认。
>
> **用途标注是我对常见模型家族的判断，供参考**；不确定时向用户确认，
> 不要臆造不在 `info` 清单里的文件名。

## 如何刷新这份目录

每个环境模型不同。运行以下命令获取**当前服务端真实清单**，然后按本文格式
更新各槽位：

```bash
python3 scripts/comfyui_api.py info
```

---

## 生图 checkpoint（`CheckpointLoaderSimple.ckpt_name`）

| 模型文件 | 用途（参考） | 适合需求 |
|---|---|---|
| `majicmixRealistic_v7.safetensors` | 写实/摄影风人像 | "写实人像/摄影/证件照" |
| `facebombmix_v1Bakedvae.safetensors` | 写实人像 | "写实人像/肖像" |
| `xxmix9realistic_v40.safetensors` | 写实/综合 | "写实/日常摄影" |
| `darkSushi25D25D_v40.safetensors` | 二次元/插画 | "二次元/动漫插画" |
| `divingIllustriousReal_v70VAE.safetensors` | 二次元/插画 | "二次元萌系小姐姐" |
| `oneObsession_v23.safetensors` | 二次元/氛围 | "二次元/氛围插画" |
| `animayhemPaleRider_v40LongRider.safetensors` | 动漫/美式 | "动漫/风格化" |
| `stable_cascade_stage_c.safetensors` | 分层级联底模（需配 stage b） | "高质量/复杂构图" |
| `stable_cascade_stage_b.safetensors` | stage B（解码端） | 配套 stage C 使用 |
| `v2-1_768-ema-pruned.safetensors` | 通用 SD2.1 | "通用/兜底" |

**选择规律**：写实 → `majicmixRealistic / facebombmix / xxmix9realistic`；
二次元 → `darkSushi / divingIllustrious / oneObsession`；要风格化 → `animayhem`；
高复杂度 → `stable_cascade`（需同时备 stage b+c）。

## 视频 UNET（`UNETLoader.unet_name`）

> **质量档位判定（重要，勿凭字面猜；已按服务端真实清单核对）**：H3 视频每类各分**两档**——
> `MiniMax-H3_FL2VA-NVFP4` / `MiniMax-H3_Ref2VA-NVFP4` 是**低质量档**（默认、更快、省显存）；
> `minimax_h3_{fl2va,ref2va}_pruned_int8_convrot` 才是**高质量档**。
> 三个视频模板默认绑定**低质量档**；用户对画质不满意时，把 UNET 换成**对应高质量档**重跑即可。

| 模型文件 | 用途（参考） | 质量档位 | 适合需求 |
|---|---|---|---|
| `MiniMax-H3\MiniMax-H3_FL2VA-NVFP4.safetensors` | 首尾帧（FL2VA）生视频，音画一体 | **低质量**（默认，快速） | "给定首帧+尾帧生成视频"；模板默认 |
| `MiniMax-H3\MiniMax-H3_Ref2VA-NVFP4.safetensors` | 参考生视频（Ref2VA），音画一体 | **低质量**（默认，快速） | "参考图/参考视频生成"；模板默认 |
| `MiniMax-H3\minimax_h3_fl2va_pruned_int8_convrot.safetensors` | 首尾帧（FL2VA）生视频 | **高质量** | 画质不满意时切换；"高画质首尾帧" |
| `MiniMax-H3\minimax_h3_ref2va_pruned_int8_convrot.safetensors` | 参考生视频（Ref2VA） | **高质量** | 画质不满意时切换；"高画质参考生视频" |
| `reanimate_v30.safetensors` | 视频重绘/转描 | —— | "改已有视频风格/动作" |
| `redcraft23INT8INT4FP8_30Krea2.safetensors` | Krea 系生图（配 Qwen3VL） | —— | "Krea 风格生图" |

**质量档切换（按任务类型选对应高质量档，覆盖 `UNETLoader.unet_name`）**：
- FL2VA（文生视频/图生视频）→ `--checkpoint "MiniMax-H3\minimax_h3_fl2va_pruned_int8_convrot.safetensors"`
- Ref2VA（参考生视频）→ `--checkpoint "MiniMax-H3\minimax_h3_ref2va_pruned_int8_convrot.safetensors"`

H3 栈配套 CLIP/VAE 不变（`MiniMax-H3\qwen3vl_32b_minimax_h3_nvfp4_awq` +
`MiniMax-H3_VideoVAE` + `MiniMax-H3_AudioVAE`），相关接入以你导出的 H3 工作流为准。

**说明**：`MiniMax-H3\...` 是**音画一体**视频栈，对应 H3 提示词协议
（`prompt-guides/h3-video-prompt-protocol.md`）。换视频模型务必同时核对
配套 CLIP/VAE 与音频节点，相关接入以你导出的 H3 工作流为准。

## 视频/生图 VAE（`VAELoader.vae_name`）

| 模型文件 | 配套 |
|---|---|
| `MiniMax-H3\MiniMax-H3_VideoVAE-FP16.safetensors` | H3 视频（视频 VAE） |
| `MiniMax-H3\MiniMax-H3_AudioVAE-FP32.safetensors` | H3 音画一体（音频 VAE） |
| `qwen_image_vae.safetensors` | Qwen-Image / Krea 生图 |
| `wan_2.1_vae.safetensors` | Wan 视频 |
| `vae-ft-mse-840000-ema-pruned.safetensors` | SD1.5/SD2.1 生图 |
| `pixel_space` | 特殊/像素空间 |

## CLIP（`CLIPLoader.clip_name`）

| 模型文件 | 用途 |
|---|---|
| `MiniMax-H3\qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | MiniMax-H3 文本编码（H3 工作流使用） |
| `qwen3vl_4b_fp8_scaled.safetensors` | Qwen / 轻量文本编码 |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | Wan 视频 |
| `t5xxl_fp8_e4m3fn.safetensors` | SD3 / Flux |
| `clip_l.safetensors` | 通用 |
| `CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` | CLIP ViT |

## LoRA（`LoraLoader.lora_name`）

> LoRA 需配合**匹配的底模**使用；换 LoRA 时同步确认 `_defaults`/`--set` 里的
> `lora_name` 与 `strength_model`/`strength_clip` 权重。

| 模型文件 | 用途（参考） | 适用的底模/场景 |
|---|---|---|
| `MiniMax-H3\minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors` | H3 FL2VA 涡轮加速 | MiniMax-H3 视频（8 步加速） |
| `MiniMax-H3\minimax_h3_turbo_4step_ckpt500.safetensors` | H3 4 步涡轮 | MiniMax-H3 视频（快速出片） |
| `wan2.2_i2v_A14b_high_noise_lora_rank64_lightx2v_4step_1022.safetensors` | Wan2.2 I2V 高噪加速 | Wan 2.2 图生视频 |
| `CelestialSkin_ANI_SP_epoch_9.safetensors` | 二次元皮肤/质感 | 二次元生图（如 darkSushi） |
| `MoriiMee_Gothic_Realistic.safetensors` | 哥特写实 | 写实/哥特风格生图 |
| `svi-shot.safetensors` | 特定镜头/氛围 | 按需（动画/电影感） |
| `y2b_v2-1.safetensors` | 视频重绘/转描 | 视频动效 |
| `Hentai_Pussy_inspection2_Anima_V01.safetensors` | ⚠️ 明确不建议使用的违规内容 | ——（此文件在导出产物中被引用，建议清理底模时不使用） |

**选择规律**：视频加速 LoRA（MiniMax-H3 / Wan）配对应 UNET；生图风格 LoRA 配对应 checkpoint；
务必核对 LoRA 与底模**同范式**，否则 ComfyUI 会报输入不匹配。

---

## 更换流程（LLM 在收到用户需求后执行）

1. **看需求**：是生图还是生视频；写实还是二次元；是否音画一体。
2. **从本目录挑候选**：匹配上方"适合需求"列，得到模型文件名。
3. **选质量档（视频）**：H3 生视频默认**低质量档**（NVFP4，快、省显存）。若用户对画质不满意
   → 按任务类型换**对应高质量档**重跑（配套 CLIP/VAE 不变）：
   - 文生视频/图生视频（FL2VA）→ `MiniMax-H3\minimax_h3_fl2va_pruned_int8_convrot.safetensors`
   - 参考生视频（Ref2VA）→ `MiniMax-H3\minimax_h3_ref2va_pruned_int8_convrot.safetensors`
4. **求证**：用 `python3 scripts/comfyui_api.py validate --type <类型> --checkpoint <候选>`
   确认该模型在服务端存在（validate 会列出 combo 可用项）。
5. **替换**：`--checkpoint <文件名>` 或模板 `--set CHECKPOINT=<文件名>`
   （模板内 `_defaults.checkpoint` 可被覆盖）。
6. **不确定/多选**：向用户展示候选（来自 `info` 的真实清单）让其选择，不臆造。

> ⚠️ **多模型联动**：若换的是视频 UNET，需同步换匹配的 VAE + CLIP（如
> `MiniMax-H3\...` 视频帧 → `MiniMax-H3_VideoVAE` + H3 CLIP），否则
> ComfyUI 会报节点输入不匹配。这点务必核对你的导出 H3 工作流。
