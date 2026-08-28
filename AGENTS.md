# AGENTS.md — ComfyUI 生图/生视频项目工作约定

> 本文件由 DSH 默认读取并注入上下文（`AGENTS.md` 优先于 `CLAUDE.md`）。
> 是**本项目基线**，更具体的直接指令可覆盖它。内容保持精炼——越短，留给真实工作的上下文越多。

---

## 一、渐进式披露原则（优先遵守）

对「多文件技能/项目」，**按需加载**，不要全量读。默认只读常驻层，深层次用到再读。

- **层级**：
  - 常驻层：每个 skill 的 `name+description`（触发词）——仅此常驻；
  - 作用时层：被调用的 skill 主文件（`comfyui-suite/SKILL.md` 等）；
  - 按需层：`comfyui-suite/references/`、`prompt-guides/`、`workflows/`、脚本、长规范——用到才读。
- **行为**：
  - 先看 `description`/目录结构判断相关性，不要预先加载长文档；
  - 需要细节再进 `references/`（guide/models/reporting）、`prompt-guides/`；
  - 不为每个任务重读同一份长手册；已读背景保持复用。
- **原则**：靠近常驻层的内容越短越好；参考性内容（规范、示例、目录树）应下沉到
  `references/`，**不要塞进常驻主文件**。

**本项目的按需参考层（用到再读）：**
- `comfyui-suite/references/guide.md` — 使用/安装/扩展/配置分层
- `comfyui-suite/references/models.md` — 模型目录（含 LoRA、用途、更换流程）
- `comfyui-suite/references/reporting.md` — 交付报告规范与示例
- `comfyui-suite/prompt-guides/` — 图片/视频/H3 提示词标准
- `comfyui-suite/workflows/README.md` — 模板机制、H3 注入、多模板路由

---

## 二、ComfyUI 生图/生视频项目注意事项

### 1. 模板、模型、风格三层关系（易错）
- **模板** = 节点接入方式（`CheckpointLoaderSimple` 整包 / `UNETLoader` 分体 / MiniMax-H3），
  **按模型栈分**；模型栈变了必须换模板。
- **模型** = 同一栈内可换，用 `--checkpoint`/`--set` 覆盖；**跨栈不自动换**。
- **风格** = 主要靠提示词 + LoRA（+ 同栈模型），**不是靠换模板**；别为换风格就误换模板。
- 判断"用哪个栈"依赖**工作流文件名语义 + `references/models.md`**，命名要清晰无歧义。

### 2. 模型名必须真实存在于服务端（不可臆造）
- 模型名（checkpoint/unet/vae/clip/lora）要以 `scripts/comfyui_api.py info` 读到的
  combo 列表为准，**绝不使用不在清单里的名字**；
- 用 `validate --type <类型>` 校验模板与模型是否匹配；不匹配时**修正为服务端真实值**或换模板。

### 3. 提示词须转英文
- 扩散模型（*oneObsession / redcraft23 / MiniMax-H3*）以英文语料训练，**最终 prompt 必须英文**：
  中文口语描述先按 `prompt-guides/*.md` 标准化为英文；视频类 H3 用音画一体三字段协议。

### 4. 参数注入靠字段语义，非占位符
- ComfyUI 导出的 JSON 可直接当模板，**无需 `{{}}` 占位符**；脚本按节点字段语义注入
  （prompt→CLIPTextEncode/MiniMaxH3ImageToVideo、seed→KSampler/RandomNoise、模型→加载器…）。
- `--set NODE.INPUT.FIELD=VALUE` 可精确覆盖任意节点输入。

### 5. 交付报告必须完整
- 交付用中文报告，**四块必须齐全**：调用序列（用了哪些子 skill、按什么顺序，含跳过的步骤）+
  调用链（类型→工作流→模型）+ 关键参数 + 结果；参数用代码块精确呈现。
- 规范与示例见 `references/reporting.md`；**不要只丢一个文件路径或一堆 JSON**。

### 6. 同类型多工作流路由
- 默认用 `default_` 前缀模板（`list` 标 `*`）；跨模型栈必须 `--workflow <文件名>` 显式切换，
  不要为了换风格把一个栈硬套到另一个栈。

---

## 三、通用基线

- 只在必要时读长文档；给出要点 + 指明文档位置，不复述冗长原文。
- 修改文件前先读；改完向用户说明改动点与影响文件。
- 能用一件事一个调用完成就不要拆散；减少无谓往返。
