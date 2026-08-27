# 更新日志

所有项目变更都会记录在此文件中。

---

## [v1.0.0] - 2026-08-27 18:15:01

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
