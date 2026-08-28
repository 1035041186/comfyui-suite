# 更新日志

所有项目变更都会记录在此文件中。

---

## [v1.1.1] - 2026-08-28 10:52:00

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
