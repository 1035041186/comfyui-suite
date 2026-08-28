# 更新日志

所有项目变更都会记录在此文件中。

---

## [v1.4.4] - 2026-08-28 18:54:28

**更新作者**: yiping zhang
**更新类型**: BUG修复

### 更新内容
- 修复 `--prompt/--negative` 在 SDXL 模板（`CLIPTextEncodeSDXL` 双编码器）中未注入的问题：现自动写入 `text_g` 与 `text_l`（此前仅精确匹配 `CLIPTextEncode.text`，导致 SDXL 模板的提示词静默失效）。
- 澄清 `--image/--video` 取值决策表：只有 base64 用 `-`（stdin）；只有文件路径用路径；二者都有且路径一步可取（无需查找/构造）时用路径；并强调 base64 指「作为输入真正存在的 base64」，不是把文件再编码一份去走 base64 通道。

### 影响文件
- `scripts/comfyui_api.py` — 支持 CLIPTextEncodeSDXL 的 text_g/text_l 注入
- `SKILL.md` — `--image/--video` 取值改为三条决策表
- `README.md` — 同步 `--image/--video` 取值说明
- `CHANGELOG.md` — 本条目

---

## [v1.4.3] - 2026-08-28 17:53:28

**更新作者**: yiping zhang
**更新类型**: 需求调整

### 更新内容
- 重写并完善 `README.md`（面向读者）：补充**前置条件 / 安装 / 配置 / 使用 / 重要提示 / 扩展新类型**等章节。
- 明确配置分层：`config/comfyui.yaml` 只管服务连接，生成参数（尺寸/步数/模型名）跟随工作流模板 `_defaults`；默认连接 `10.0.0.1:8188`、未配置时回退 `127.0.0.1:8188`（修正了原 README 与配置文件不一致的表述）。
- 补充 `--image/--video` 输入契约（本地文件路径 / `-`(stdin base64)）、常用参数表、产出目录说明与失败排查。
- 保留对自带的骨干模板（尤其视频类）需按环境重新导出的提醒。

### 影响文件
- `README.md` — 重写完善，补充安装/配置/使用/提示/扩展
- `CHANGELOG.md` — 本条目

---

## [v1.4.2] - 2026-08-28 17:51:33

**更新作者**: yiping zhang
**更新类型**: 需求调整

### 更新内容
- 总入口 `SKILL.md` 新增「执行步骤清单」：把执行流程整理为 **5 个具名步骤**（路由判定 / 提示词标准化 / 服务检查与选模型 / 调用生成 / 交付报告），作为**可移植的计划数据**。
- 增加**宿主无关**的驱动规则：agent 把步骤登记为**宿主自带的任务清单**并随进度更新状态；宿主无任务清单工具时退化为**文本清单**；skill 不依赖、不实现任何宿主专属任务清单调用。
- 新增参考文档 `references/execution-plan.md`：定义可移植计划模型（`steps:[{title,status}]`，整份替换）、宿主无关同步规则、以及 DSH 映射示例（**仅示例，非依赖**），并说明跨 agent 边界。
- 渐进式披露校验与修复：把计划/适配的细节下沉到 `references/`，常驻 `SKILL.md` 只保留精简步骤骨架与外链；`references/guide.md` 目录树同步登记 `execution-plan.md`。

### 影响文件
- `SKILL.md` — 新增执行步骤清单（canonical plan）+ 宿主无关驱动规则 + 指向参考文档
- `references/execution-plan.md` — 新增：可移植计划模型 + 宿主映射示例（非依赖）+ 边界
- `references/guide.md` — references/ 目录树补充 execution-plan.md
- `CHANGELOG.md` — 本条目

---

## [v1.4.1] - 2026-08-28 17:25:04

**更新作者**: yiping zhang
**更新类型**: 需求调整

### 更新内容
- `--image/--video` 输入收敛为两种、职责分明：`-`（从 stdin 读 base64，跨 agent / 不落盘 / 无命令行 argv 上限）或 本地文件路径（用户上传 / 显式给路径 / agent 一步直接拿到的文件）。
- **移除**内联 base64 与 `@文件`：消除"值到底是路径还是 base64"的歧义，也避免耦合 DSH 专属文件路径。base64 只经 stdin 通道进入。
- base64 解码后新增**图片合法性校验**：用魔数识别图片格式，识别不出（非法/非图片数据）即明确报错，防止把错误数据当图上传；同时扩展识别 tiff/avif/heic。
- 明确 agent 选择规则：base64 与文件路径都可用、且文件路径能**一步直接拿到**（无需查找/构造）时**优先文件路径**；否则（如粘贴图）走 `--image -`（stdin base64）。

### 影响文件
- `scripts/comfyui_api.py` — 输入收敛、移除内联/`@文件`、新增合法性校验、帮助与文档更新
- `SKILL.md` — `--image/--video` 取值与选择规则
- `skills/image-to-image/SKILL.md` — `--image` 支持 路径 / stdin(base64)
- `skills/image-to-video/SKILL.md` — 同上
- `skills/reference-to-video/SKILL.md` — 同上
- `CHANGELOG.md` — 本条目

---

## [v1.4.0] - 2026-08-28 16:06:28

**更新作者**: yiping zhang
**更新类型**: 需求新增

### 更新内容
- `--image`/`--video` 新增支持 base64 输入（`data:image/...;base64,` 与 `base64:` 前缀），脚本自动解码为字节后直接上传，全程**不落盘**临时文件。
- 重构上传为「字节归一化 → 统一 multipart 上传」：新增 `_resolve_bytes`（识别 data URI / `base64:` / 本地路径）、`_sniff_image`（按 magic bytes 定扩展名与 Content-Type）、`_encode_multipart_bytes`（由字节构造 multipart 体）、`_upload_bytes`；`upload_image` 改为薄封装，对原调用方保持兼容。
- 支持"粘贴到会话里的图直接使用"：可直接把该图的 base64 传给 `--image`，无需先落盘成文件（替代此前"读 agent 临时/附件文件"或"先写文件再上传"的步骤）。
- 同步更新 docstring、`--image` help 与相关子 skill 文档的 base64 说明。

### 影响文件
- `scripts/comfyui_api.py` — 新增 base64 输入、字节归一化+统一上传重构、帮助文本与 docstring
- `SKILL.md` — 调用示例与 `--image/--video` 的 base64 取值说明
- `skills/image-to-image/SKILL.md` — `--image` 支持 base64
- `skills/image-to-video/SKILL.md` — `--image` 支持 base64
- `skills/reference-to-video/SKILL.md` — `--image` 支持 base64
- `CHANGELOG.md` — 本条目

---

## [v1.3.1] - 2026-08-28 14:18:19

**更新作者**: yiping zhang
**更新类型**: BUG修复

### 更新内容
- 修复 config/comfyui.yaml 早期被整文件覆盖时误删的 `server`（host/port/api_key）与 `timeouts` 两节，恢复为完整服务连接配置。
- 恢复后脚本正确连到 `10.0.0.1:8188`（此前因缺 server.host 回退到默认 127.0.0.1 导致 health 失败）。
- 保留 output.dir=outputs（相对会话根）的当前设计。

### 影响文件
- `config/comfyui.yaml` — 补回 server/timeouts 节
- `CHANGELOG.md` — 本条目

---

## [v1.3.0] - 2026-08-28 14:06:07

**更新作者**: yiping zhang
**更新类型**: 需求新增（功能增强）

### 更新内容
- 新增 `output-path` 命令：确定性计算最终产出目录 = `<会话工作根>/<config.output.dir>/<生成类型>/`，供流程显式引用，不再依赖脚本"猜测当前目录"。
- `config.output.dir` 改为 `outputs`（去 `./`），注明是**相对路径、相对于会话工作根**。
- 流程约定：生成前先 `pwd`（或读系统声明 working directory）确定会话根，再用 `output-path` 求产出目录才调用生成；产出路径稳定为 `<会话工作根>/outputs/<类型>/<时间戳>_<名>`。
- 新增 `--root` 参数（传入会话工作根），生成命令与 output-path 均支持；`--output` 绝对路径可覆盖产出根（仍追加 `<类型>/`）。
- 统一路径拼接函数 `resolve_session_root`/`resolve_output_path`。

### 影响文件
- `scripts/comfyui_api.py` — 新增 output-path 命令、--root 参数、统一路径函数
- `config/comfyui.yaml` — output.dir 改为 outputs + 相对会话根注释
- `SKILL.md` — 第 4 步加「确定性求会话根→output-path 求路径」流程
- `CHANGELOG.md` — 本条目

---

## [v1.2.6] - 2026-08-28 13:12:11

**更新作者**: yiping zhang
**更新类型**: 需求调整

### 更新内容
- 输出锚点改为「纯跨 agent 通用」：`_session_cwd()` 用通用环境变量 `PWD`（任何 shell/agent 都有）而非 DSH 专有的 `DSH_SESSION_JSONL`/`zstd`。
- 移除对 DSH 的耦合：换到其他 agent（Claude Code 等）同样生效，输出稳定落到「当前工作目录」下的 `outputs/<类型>/`。
- 清理相关注释。

### 影响文件
- `scripts/comfyui_api.py` — `_session_cwd()` 改为 PWD 通用锚点，去除 DSH/zstd 依赖
- `CHANGELOG.md` — 本条目

---

## [v1.2.5] - 2026-08-28 13:08:19

**更新作者**: yiping zhang
**更新类型**: BUG修复

### 更新内容
- 输出目录改为「稳定跟会话工作目录走」：产出根锚点从 DSH 会话记录（`DSH_SESSION_JSONL`）解析会话 cwd，而非依赖运行时 `os.getcwd()`（避免被 bash cd 扰动），稳定落到 `<会话工作目录>/outputs/<类型>/`。
- 移除上一轮的"可写检查 + 提示换路径"试探逻辑：只写稳定位置，只读/无权限时明确报错定位，不引导切换路径。
- 建立失败抛出带明确路径的报错，由 main 统一处理。

### 影响文件
- `scripts/comfyui_api.py` — 新增 `_session_cwd()` 稳定锚点；out_dir 改用该锚点；`_makedirs` 报错定位；移除试探逻辑
- `CHANGELOG.md` — 本条目

---

## [v1.2.4] - 2026-08-28 13:01:47

**更新作者**: yiping zhang
**更新类型**: BUG修复

### 更新内容
- 修复输出目录「绝对路径不按类型分区」：`--output` 绝对路径改为同样追加 `<生成类型>/` 子目录，图片/视频各自归档。
- 下载前增加产出目录可写检查：只读/无权限时 fail-fast 并提示用 `--output <可写绝对路径>` 或环境变量 `COMFYUI_OUTPUT_DIR`，避免 LLM 反复试路径。
- 统一：无论相对(基于 cwd)或绝对(`--output`)路径，最终均为 `<产出根>/<生成类型>/<时间戳>_<原名>`。

### 影响文件
- `scripts/comfyui_api.py` — 输出路径统一追加类型分区 + 可写检查
- `config/comfyui.yaml` — output.dir 注释同步（绝对路径也分区）
- `CHANGELOG.md` — 本条目

---

## [v1.2.3] - 2026-08-28 12:44:51

**更新作者**: yiping zhang
**更新类型**: 需求调整

### 更新内容
- 去除各 workflow 中写死的敏感/特定提示词，替换为中性通用版本：
  - `text-to-image/default_sd15_base.json`、`krea2.json`：成人色情正向提示词 → 「a professional portrait photo, high quality, detailed, soft natural lighting, shallow depth of field」，负向 → 通用负面词。
  - `text-to-video/default_minimax_h3_t2v.json`：1647 字符的特定动作脚本 → 254 字符通用电影镜头提示词。
  - `image-to-image/default_img2img_sdx.json`：中性但具体的「young man smiling」→ 通用人像提示词。
- 保留字段注入能力：默认用中性提示词，传 `--prompt` 覆盖。

### 影响文件
- `workflows/text-to-image/default_sd15_base.json` — 替换敏感/负向提示词
- `workflows/text-to-image/krea2.json` — 同上
- `workflows/text-to-video/default_minimax_h3_t2v.json` — 替换特定动作脚本 prompt
- `workflows/image-to-image/default_img2img_sdx.json` — 替换具体人像提示词
- `CHANGELOG.md` — 本条目

---

## [v1.2.1] - 2026-08-28 11:52:10

**更新作者**: yiping zhang
**更新类型**: 需求调整

### 更新内容
- 时间戳范围明确限定：**仅 ComfyUI API 生成的产物**（图片/视频/音频/gif 等）文件名加时间戳前缀；其他文件（workflow/config/文档/脚本等）不受影响。
- 产物目录改为按「生成类型」分区（去掉目录级时间戳，避免与文件名时间戳重复），文件名统一 `<YYYYMMDD_HHMMSS>_<原名>`。

### 影响文件
- `scripts/comfyui_api.py` — download_file 内文件名时间戳；out_dir 去掉目录级时间戳、保留类型分区
- `references/reporting.md` — 路径示例同步
- `CHANGELOG.md` — 本条目

---

## [v1.2.2] - 2026-08-28 12:41:52

**更新作者**: yiping zhang
**更新类型**: BUG修复

### 更新内容
- 回退「在对话中显示图片/视频」的探索性改动：交付报告【结果】段改为简洁通用展示——用 inline code 引用生成文件路径 + 校验结果，移除 read_image、可点击预览、markdown 图片语法等反复横跳的说明。
- 保留上一轮的产物路径/时间戳/按类型分区（cwd 基准、`<类型>/<时间戳>_<名>`）改动不变。
- 修复 CHANGELOG 缺失 v1.2.0 标题头的错乱。

### 影响文件
- `references/reporting.md` — 【结果】段回退为简洁通用版本，删除 read_image/可点击/预览说明
- `SKILL.md` — 第 5 步「结果可查看」条目回退为简洁表述
- `CHANGELOG.md` — 本条目

---

## [v1.2.0] - 2026-08-28 11:50:13

**更新作者**: yiping zhang
**更新类型**: 需求新增（功能增强）

### 更新内容
- 输出目录改为以「当前工作目录 cwd」为基准（不再拼到 skill 根），更符合直觉。
- 结果目录按「生成类型」分区：`<cwd>/<output.dir>/<类型>/`；**每个 API 产物文件名统一加时间戳前缀** `<YYYYMMDD_HHMMSS>_<原名>`（图片/视频/音频等所有生成文件），避免覆盖、便于回溯。
- `--output` 绝对路径时直接使用，但文件名仍带时间戳（download_file 统一处理）。
- config/comfyui.yaml 的 output.dir 注释与帮助文本同步；交付报告示例更新为「类型目录 + 时间戳文件名」形态。

### 影响文件
- `scripts/comfyui_api.py` — out_dir 解析改为 cwd 基准 + 类型分区 + 产物文件名时间戳 + --output help
- `config/comfyui.yaml` — output.dir 注释说明
- `references/reporting.md` — 结果路径示例更新
- `CHANGELOG.md` — 本条目

---

**更新作者**: yiping zhang
**更新类型**: BUG修复

### 更新内容
- 修正交付报告"文件可查看"方式：改为图片用 `read_image` 读入直接显示到对话。
- 更正此前误导："inline code 可点击"仅对 write/edit 文本产物有效，bash 生成的图片/视频不被记录为可点击。
- 视频/动图无 read_image 预览，改为正文 inline code 引用路径 + 文字说明。

### 影响文件
- `references/reporting.md` — 结果呈现规则改为 read_image，更正可点击说明
- `SKILL.md` — 第 5 步结果可查看表述更正
- `CHANGELOG.md` — 本条目

---

**更新作者**: yiping zhang
**更新类型**: 需求调整

### 更新内容
- 交付报告结果呈现增强：生成文件用 inline code 引用（图片/视频均可点击）；图片另加 markdown 图片语法 `![结果](路径)` 尽量触发对话内预览。
- 交付报告规范（references/reporting.md）新增「结果呈现规则」，根 SKILL.md 第 5 步同步提及。
- 新增项目级 `AGENTS.md`（渐进式披露 + 项目注意事项），纳入 git。

### 影响文件
- `references/reporting.md` — 结果呈现规则、示例补图片预览
- `SKILL.md` — 第 5 步补「结果文件要可查看」
- `AGENTS.md` — 项目级工作约定（新增）
- `CHANGELOG.md` — 本条目

---

**更新作者**: yiping zhang
**更新类型**: 需求调整

### 更新内容
- 交付报告新增「调用序列」字段：按实际顺序列出用过的子 skill / 命令（含被跳过的步骤），体现 agent 使用流程的先后与是否走完整。
- `references/reporting.md` 报告结构含调用序列 + 写法说明 + 示例补调用序列段。
- 根 `SKILL.md` 第 5 步概述与 5 个生成类子 skill 交付引用同步补调用序列。

### 影响文件
- `references/reporting.md` — 报告结构、调用序列写法说明、示例
- `SKILL.md` — 第 5 步概述补调用序列
- `skills/*/SKILL.md` — 交付引用补调用序列
- `CHANGELOG.md` — 本条目

---

**更新作者**: yiping zhang
**更新类型**: 需求调整

### 更新内容
- 交付报告详细规范与完整示例从总入口下沉到 `references/reporting.md`，根 SKILL.md 第 5 步精简为概述并指向该文件。
- 5 个生成类子 skill 交付引用改为指向 `references/reporting.md`。
- 修正 `references/guide.md` 目录结构（补 references/ 下各文档），根 SKILL.md 从 188 → 131 行，更符合渐进式披露。

### 影响文件
- `SKILL.md` — 第 5 步精简，删除示例段
- `references/reporting.md` — 交付报告规范+示例（新增）
- `references/guide.md` — 目录结构更新
- `skills/*/SKILL.md` — 交付引用改指向 reporting.md
- `CHANGELOG.md` — 本条目

---

**更新作者**: yiping zhang
**更新类型**: 需求调整

### 更新内容
- 新增「交付报告」规范：交付时用可读中文说明调用链（类型→工作流→模型）、关键参数与实际命令，参数以代码块精确呈现。
- 新增完整交付报告示例，供 LLM 模仿格式。
- 5 个生成类子 skill 交付步骤统一改为参考此规范。

### 影响文件
- `SKILL.md` — 第 5 步升级为交付报告规范 + 示例
- `skills/*/SKILL.md` — 交付步骤引用报告规范
- `CHANGELOG.md` — 本条目

---

**更新作者**: yiping zhang
**更新类型**: 需求调整

### 更新内容
- 明确"类型内多工作流路由"规则：同类型多栈模板时，默认用 `default_` 前缀，跨栈需显式 `--workflow`。
- 修正文生图默认模板命名 `default_sdx15_base` → `default_sd15_base`（消除 SD 命名歧义）。
- `workflows/README.md` 补命名规范与多模板路由说明。

### 影响文件
- `SKILL.md` — 新增「第 1.5 步：类型内路由」规则
- `workflows/README.md` — 多模板路由与命名规范
- `workflows/text-to-image/default_sd15_base.json` — 改名（原 default_sdx15_base）
- `CHANGELOG.md` — 本条目

---

**更新作者**: yiping zhang
**更新类型**: 需求新增（功能增强）

### 更新内容
- 新增「导出即模板 + 字段语义注入」机制：ComfyUI 导出的 API JSON 无需 `{{}}` 占位符即可直接使用，脚本按节点字段语义定位并写入参数。
- 字段注入器支持 SD 通用范式（KSampler/CLIPTextEncode 定位）与 MiniMax-H3 音画视频范式（MiniMaxH3ImageToVideo/RandomNoise/LoraLoaderModelOnly 定位）。
- 新增 `info`（发现服务端节点+模型）、`validate`（校验模板匹配度）命令，支持按真实服务端 combo 列表校验模型名。
- 新增 `--lora`/`--lora-strength-*` 快捷参数，`--set NODE.INPUT.FIELD=VALUE` 精确覆盖。
- 录入 4 个用户环境真实可用的工作流为模板：SD 整包文生图、Krea2 文生图、SD 图生图、MiniMax-H3 音画文生视频；修正模型名为服务端真实值。
- 新增 `references/models.md`（模型目录含 LoRA、用途标注与更换流程）。
- 删除绑定 wan/sdxl 且含违规内容的旧骨架模板；`image-to-video`/`reference-to-video` 标注为待替换骨架。

### 影响文件
- `scripts/comfyui_api.py` — 字段注入器（SD+H3 双范式）、info/validate、--lora、--set 字段级
- `workflows/<类型>/default_*.json` — 4 个真实可跑模板（SD/Krea2/SD图生图/MiniMax-H3）
- `workflows/README.md` — 模板机制、H3 注入、各类型状态标注
- `references/models.md` — 模型目录（新增）
- `SKILL.md`、`skills/*/SKILL.md` — 字段注入与模型选择说明
- `CHANGELOG.md` — 本条目

---

**更新作者**: yiping zhang
**更新类型**: 需求新增

### 更新内容
- 搭建 ComfyUI 生图/生视频组合 skill（comfyui-suite），提供文生图、图生图（含图文）、文生视频、图生视频、参考生视频五种生成类型，由总入口自动路由。
- 编写统一调用脚本 `scripts/comfyui_api.py`：上传图片、提交任务、轮询历史、下载结果，纯标准库零依赖。
- 建立可扩展的 workflow 模板库（`workflows/<类型>/default_*.json`），采用 API 格式 JSON + `{{占位符}}` + `_defaults` 参数分层。
- 编写提示词标准库：图片 tag 式、视频 H3 音画一体协议（消化版 + 权威规范）、传统无声视频写法。
- 提供服务连接配置 `config/comfyui.yaml`（仅含服务地址/超时/输出目录等连接项，生成参数随模板，遵循 CLI > _defaults 优先级）。
- 编写 `scripts/install_skills.sh` 挂载 7 个可调用入口，并处理 DSH 单层扫描限制（平铺 + softlink）。
- 根 `SKILL.md` 按渐进式披露精修为纯调度器，使用/安装/扩展等下沉至 `references/guide.md`。

### 影响文件
- `SKILL.md` — 组合 skill 总入口：路由表 + 五步调度流程
- `README.md` — 架构说明与快速开始
- `references/guide.md` — 使用/安装/扩展/配置分层参考（按需加载）
- `config/comfyui.yaml` — 服务连接配置
- `scripts/comfyui_api.py` — 统一 ComfyUI API 调用脚本
- `scripts/install_skills.sh` — 7 个 skill 入口挂载脚本
- `workflows/<类型>/default_*.json` — 5 类工作流模板
- `workflows/README.md` — 模板规范与扩展方法
- `prompt-guides/*.md` — 图片/视频提示词标准与 H3 权威规范
- `skills/<类型>/SKILL.md` — 6 个子 skill
- `.gitignore` — 排除运行产物

---
