# workflows/ — ComfyUI 工作流模板目录

每个子目录对应一种生成类型，与 `skills/` 下的子 skill 一一对应：

| 目录 | 生成类型 | 必需输入 |
|---|---|---|
| `text-to-image/` | 文生图 | 提示词 |
| `image-to-image/` | 图生图 / 图文混合生图 | 提示词 + 输入图片 |
| `text-to-video/` | 文生视频 | 提示词 |
| `image-to-video/` | 图生视频（首帧驱动） | 提示词 + 输入图片 |
| `reference-to-video/` | 参考生视频（角色/姿态参考） | 提示词 + 参考图片 + 参考视频 |

## 各类型当前模板状态（如实标注，避免误用）

| 类型 | 默认模板 | 模型栈 | 状态 |
|---|---|---|---|
| `text-to-image` | `default_sd15_base.json` | SD 整包 | ✅ 真实可跑 |
| `text-to-image`（备选） | `krea2.json` | Krea2 分体 | ✅ 真实可跑（需 `--workflow krea2.json`） |
| `image-to-image` | `default_img2img_sdx.json` | SD（整包+VAEEncode） | ✅ 真实可跑 |
| `text-to-video` | `default_minimax_h3_t2v.json` | MiniMax-H3 音画（T2VA） | ✅ 真实可跑 |
| `image-to-video` | `default_minimax_h3_i2v.json` | MiniMax-H3 音画（I2VA 首帧） | ✅ 真实可跑 |
| `reference-to-video` | `default_minimax_h3_r2v.json` | MiniMax-H3 音画（Ref2VA/FL2VA 双参考图） | ✅ 真实可跑 |

> 生视频三类型均为 **MiniMax-H3 音画一体**，提示词按 `prompt-guides/h3-video-prompt-protocol.md`。
> 其中 `reference-to-video` 是**两帧参考图**（首帧→`ref_image_0`、尾帧→`ref_image_1`）驱动，**不是参考视频**；
> 对应 CLI 用 `--image`（首帧）+ `--image2`（尾帧）。

## 核心思想：导出即模板（主路径，无需手工改）

**把 ComfyUI 导出的 API JSON 直接放进对应目录就能用**，脚本按「字段语义」自动把
参数注入到正确节点，**模板里不需要任何 `{{}}` 占位符**。

- **模板文件 = ComfyUI「Save (API Format)」导出的原样 JSON**（node-id →
  `{class_type, inputs}`），零手工改动；
- **参数注入**由 `scripts/comfyui_api.py` 的字段注入器完成，按节点字段语义定位：

| CLI 参数 | 注入到哪个节点 |
|---|---|
| `--prompt` | 沿 KSampler 的 `positive` 引用追溯到 CLIPTextEncode 的 `text` |
| `--negative` | 沿 KSampler 的 `negative` 引用追溯的 CLIPTextEncode 的 `text` |
| `--seed/--steps/--cfg/--denoise` | KSampler 对应输入 |
| `--checkpoint` | `CheckpointLoaderSimple.ckpt_name` 或 `UNETLoader.unet_name` |
| `--width/--height/--frames` | `Empty*Latent*` 空 latent 节点的 `width/height/length` |
| `--lora <NODE:文件名>` | `LoraLoader.lora_name`（`NODE:` 可指定节点，缺省取第一个） |
| `--lora-strength-model/clip` | 所有 `LoraLoader` 的 `strength_model` / `strength_clip` |
| `--image/--video` | 上传后的文件名为 `LoadImage.image` / `VHS_LoadVideo.video` |
| `--prefix` | `Save*` 节点的 `filename_prefix` |
| `--set NODE.FIELD=VALUE` | **任意**节点的任意输入字段（精确兜底，如 `5.inputs.cfg=5.5`） |

**MiniMax-H3 音画视频范式**（模板含 `MiniMaxH3ImageToVideo` 或
`MiniMaxH3ReferenceToVideo` 节点时自动切换注入方式，无 KSampler，落点独立）：

| CLI 参数 | 注入到哪个节点 |
|---|---|
| `--prompt` | H3 音画节点 `.prompt`（ImageToVideo / ReferenceToVideo 均适用；H3 无单独 negative，负向内容在 prompt 内写） |
| `--seed` | `RandomNoise.noise_seed` |
| `--width/--height` | `ResolutionSelector`（`aspect_ratio`/`megapixels`）或 H3 音画节点 |
| `--frames` | 帧数表达式链上游的 `PrimitiveFloat/Int.value` |
| `--image` | I2VA→驱动 `first_frame` 的 `LoadImage`；Ref2VA/FL2VA→`ref_image_0` |
| `--image2` | Ref2VA/FL2VA→`ref_image_1`（尾帧参考；缺省复用 `--image`） |
| `--lora` | `LoraLoaderModelOnly.lora_name` + `strength_model` |
| `--checkpoint` | `UNETLoader.unet_name` 等 |

因此 LLM **无需懂模板结构**：只传高级参数（`--prompt/--checkpoint/--width/--seed`…），
代码定位并写入。这是本套件绕开「强 LLM 依赖」的关键。

## 两种模板形态（都支持）

| 形态 | 说明 | 注入方式 |
|---|---|---|
| **导出 JSON**（推荐） | ComfyUI 原样导出，无 `{{}}` | 字段语义注入 |
| **占位符模板**（可增强） | 手动加 `{{PROMPT}}` 等 | 渲染前文本替换 + 字段注入 |

两种形态脚本都会先渲染（占位符），再叠字段注入，兼容并存。

## 同类型多模板：实际路由与命名建议

一个类型目录可放多套不同**模型栈**的工作流（如 `text-to-image` 有 SD 整包 + Krea2 分体）。
路由规则：

- **默认**：用户没指定 → 用 `default_` 前缀的工作流（`list` 里标 `*`）；
- **选其它**：`--workflow <文件名>`；
- **跨栈不自动换**：不同工作流=不同模型栈（节点接入不同），LLM 判断"该用哪个栈"靠
  工作流**文件名语义** + `references/models.md`，不要把一个栈硬套到另一个。

**命名建议（让 LLM 能可靠路由，避免歧义）**：
- `default_<栈>_<用途>.json`：栈语义用无歧义词，如 `default_sd15_base`（SD1.5 整包）、
  `default_minimax_h3_t2v`（MiniMax-H3 文生视频）；
- 非默认模板用 `default_` 之外的前缀，如 `krea2.json`（需 `--workflow` 显式选）；
- 避免 `sdx15`/`x1` 这类易被误读为别的栈的名字；栈名后缀规范：
  `sd15`（SD1.5）、`sdxl`（SDXL）、`krea2`、`minimax_h3`（MiniMax-H3）。

> ⚠️ 命名是路由的"眼睛"：`list` 只能显示文件名，LLM 靠文件名 + models.md 判断用哪个栈。
> 命名模糊会让多模板场景下选错工作流。

## 模板放置与默认选择

- 每个类型目录放导出的 JSON，文件名以 `default_` 开头作为**默认模板**；
- 同类多份时（`default_sdxl.json`、`flux_dev.json`），用 `--workflow <文件>` 显式指定；
- 脚本未指定 `--workflow` 时取 `default_` 开头第一个。
- 可选顶级字段 `_defaults`：约定该模板的默认值
  （`checkpoint/width/height/steps/cfg/frames/negative/prefix`），提交前脚本自动剥离。
  **导出 JSON 无需 `_defaults`**——它已自带硬编码值，字段注入只覆盖你显式传的 CLI 参数。

## 如何替换/新增一个 workflow（给你）

1. 在 ComfyUI 界面搭好并**手动跑通**该类型工作流；
2. **「Save (API Format)」导出 API JSON**；
3. 直接放到 `workflows/<类型>/default_<名字>.json`；
4. 用 `python3 scripts/comfyui_api.py <类型> --prompt test --dry-run` 校验能正确注入；
5. 交付前跑 `python3 scripts/comfyui_api.py validate --type <类型>` 确认节点/模型匹配。

## 如何扩展新类型

1. 新建 `workflows/<new-type>/` 放入导出的 JSON；
2. 在 `scripts/comfyui_api.py` 的 `KNOWN_TYPES` 与 `build_parser()` 注册 `<new-type>`；
3. 新建 `skills/<new-type>/SKILL.md`（复制现有子 skill 修改）；
4. 在根 `SKILL.md` 的路由表登记新类型。

> ⚠️ 不同模型栈（SD 整包 / Krea·Qwen 分体 / Wan / MiniMax-H3）的**节点接入方式不同**，
> 一份模板只对一种接入栈有效。更换模型栈时请用**对应栈导出的 JSON** 替换，不要硬套。
> 字段注入器能处理「同一栈内的参数变化」，不能让一种栈直接兼容另一种栈。
