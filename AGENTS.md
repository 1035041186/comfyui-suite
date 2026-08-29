# AGENTS.md — ComfyUI 生图/生视频项目工作约定

> 本文件由 DSH 默认读取并注入上下文，是**本项目基线**（更具体的直接指令可覆盖它）。
> 保持精炼：细节规则归 `SKILL.md` 与 `references/`，本文件只留跨场景底线。

## 1. 渐进式披露（优先）

多文件技能按需加载，不要全量读。默认只读常驻层（skill 的 `name+description`），
用到再读 `references/`、`prompt-guides/`、`workflows/`、脚本、长规范。参考性内容下沉，
不要塞进常驻主文件；读过即复用，不重读同一份长手册。

**本项目按需参考层（用到再读）：**
- `comfyui-suite/references/guide.md` — 使用/安装/扩展/配置分层
- `comfyui-suite/references/models.md` — 模型目录（用途/更换流程）
- `comfyui-suite/references/reporting.md` — 交付报告规范与示例
- `comfyui-suite/prompt-guides/` — 图片/视频/H3 提示词标准
- `comfyui-suite/workflows/README.md` — 模板机制、字段注入、多模板路由

## 2. 关键红线（细节见 `SKILL.md` 与 `references/`）

- **提示词必须英文**：扩散模型以英文语料训练，中文描述按 `prompt-guides/*` 标准化为英文。
- **模型名必须真实**：模型名以 `scripts/comfyui_api.py info` 读到的 combo 清单为准，绝不臆造；用 `validate` 确认匹配。
- **交付报告四要素齐全**：调用序列 + 调用链（类型→工作流→模型）+ 关键参数 + 结果（规范见 `references/reporting.md`）。
- **模板/模型/风格三层关系**：模板按模型栈分（跨栈必须换模板）；模型同栈内换；风格靠提示词+LoRA，不靠换模板。

## 3. 通用基线

- 只在必要时读长文档；给要点 + 指明位置，不复述冗长原文。
- 修改文件前先读；改完向用户说明改动点与影响文件。
- 能用一件事一个调用完成就不要拆散；减少无谓往返。

**流程与执行细节（五步调度、类型内路由、字段注入、生成命令）见 `comfyui-suite/SKILL.md`。**
