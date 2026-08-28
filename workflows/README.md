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
| `text-to-image` | `default_sdx15_base.json` | SD 整包 | ✅ 真实可跑 |
| `text-to-image`（备选） | `krea2.json` | Krea2 分体 | ✅ 真实可跑（需 `--workflow krea2.json`） |
| `image-to-image` | `default_img2img_sdx.json` | SD（整包+VAEEncode） | ✅ 真实可跑 |
| `text-to-video` | `default_minimax_h3_t2v.json` | MiniMax-H3 音画 | ✅ 真实可跑 |
| `image-to-video` | `default_wan_i2v.json` | Wan | ⚠️ **骨架参考，绑定 wan 模型；若服务端无 wan 需替换导出 JSON** |
| `reference-to-video` | `default_wan_vace.json` | Wan | ⚠️ **骨架参考，绑定 wan；需替换真实导出 JSON** |

> ⚠️ `image-to-video` / `reference-to-video` 目前是**占位骨架**（绑定了服务端不存在的 wan 模型），
> 请用你环境实际跑通的导出 JSON 替换（`validate` 会提示模型名不匹配）。

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

**MiniMax-H3 音画视频范式**（模板含 `MiniMaxH3ImageToVideo` 节点时自动切换注入方式，
无 KSampler，落点独立）：

| CLI 参数 | 注入到哪个节点 |
|---|---|
| `--prompt` | `MiniMaxH3ImageToVideo.prompt`（H3 无单独 negative，负向内容在 prompt 内写） |
| `--seed` | `RandomNoise.noise_seed` |
| `--width/--height` | `ResolutionSelector`（`aspect_ratio`/`megapixels`）或 `MiniMaxH3ImageToVideo` |
| `--frames` | 帧数表达式链上游的 `PrimitiveFloat/Int.value` |
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
