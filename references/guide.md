# ComfyUI Suite 参考文档（使用 / 安装 / 扩展）

> 本文件是运行时**按需加载**的参考信息。总入口 `SKILL.md` 只负责调度（路由 + 五步流程），
> 需要以下内容时再读本文件。架构说明见 `README.md`。

## 1. 如何被调用（8 个入口）

本套件注册了 **8 个独立可调用**的 skill（供 LLM 通过 `/` 或自动触发），都挂在项目级
skills 根 `<项目根>/.dsh/skills/`。DSH 扫描只认**一层目录**，子 skill 用
"平铺目录 + softlink 指向源文件"挂载：

```
.dsh/skills/
├── comfyui-suite              -> 总入口（自动路由）
├── comfyui-text-to-image      -> 文生图
├── comfyui-image-to-image     -> 图生图（含图文一起）
├── comfyui-text-to-video      -> 文生视频
├── comfyui-image-to-video     -> 图生视频
├── comfyui-reference-to-video -> 参考生视频
├── comfyui-image-refine       -> 图片调整迭代（不满意再改）
└── comfyui-prompt-optimizer   -> 提示词优化（只优化不生成）
```

- **总入口**：默认收敛到 `/comfyui-suite`，由它自动路由到具体类型；
- **子 skill**：也可显式调用 `/comfyui-text-to-image` 等，绕开路由、只做单一类型；
- **图片调整迭代**：`/comfyui-image-refine` 是**编排层**（非生成类型，无独立 workflow/`comfyui_api.py`
  子命令），对已生成图不满意时复用 `text-to-image`/`image-to-image` 做多轮调整（不限次数），
  "少动/大动"判定与"症状→杠杆"决策表见 `references/refine.md`；
- **安装**：`bash scripts/install_skills.sh` 自动生成这些入口（幂等）。

## 2. 源码目录结构

```
comfyui-suite/
├── SKILL.md                        # 总入口：路由 + 五步调度流程
├── README.md                       # 架构与快速开始
├── config/comfyui.yaml             # 服务连接配置（地址/端口/超时/输出目录）
├── scripts/comfyui_api.py          # 统一调用脚本（纯标准库，python3 直接运行）
├── scripts/install_skills.sh       # 一键挂载 8 个入口到 <项目根>/.dsh/skills
├── workflows/<类型>/default_*.json # 各类型工作流模板（API 格式，{{占位符}} + _defaults）
├── prompt-guides/                  # 提示词标准化参考
│   ├── image-prompt-guide.md       # 图片（tag 式）
│   ├── video-prompt-guide.md       # 视频：H3 消化版 + 传统写法
│   └── h3-video-prompt-protocol.md # H3 音画一体协议完整规范（权威参考）
├── references/                     # 按需加载的参考文档
│   ├── guide.md                    # 使用/安装/扩展/配置分层（本文件）
│   ├── models.md                   # 模型目录（含 LoRA、用途、更换流程）
│   ├── reporting.md                # 交付报告规范与示例
│   ├── refine.md                   # 图片调整迭代决策表（不满意再改）
│   └── execution-plan.md           # 可移植执行计划 + 宿主任务清单适配（跨 agent）
└── skills/<类型>/SKILL.md          # 子 skill（单类型精细控制）
```

## 3. 配置与参数分层

**三层取值优先级：CLI 显式参数 > workflow `_defaults` > 报错缺参**（seed 缺省随机）。

- `config/comfyui.yaml`：**只管服务连接**——地址（默认 `127.0.0.1:8188`）、
  api_key、超时、输出目录。环境变量优先：
  `COMFYUI_HOST / COMFYUI_PORT / COMFYUI_PROTOCOL / COMFYUI_API_KEY / COMFYUI_OUTPUT_DIR`。
- 尺寸/帧数/步数/cfg/模型名：**跟随模型与工作流**，写在各模板 `_defaults` 里
  （如 SDXL 模板 1024×1024、Wan 模板 1280×720@16fps），换模板即换默认值，
  不写进配置文件，避免全局配置与模板打架。
- CLI（`--width/--steps/--checkpoint/...`）仅当次覆盖，不改任何文件。

## 4. 扩展指南

**新增一种生成类型**（如"视频生视频"、"局部重绘"）：
1. `workflows/<new-type>/default_*.json` 放入模板（规范见 `workflows/README.md`）；
2. `scripts/comfyui_api.py` 的 `KNOWN_TYPES` 和 `build_parser()` 注册新命令；
3. `skills/<new-type>/SKILL.md` 复制最近似的子 skill 修改；
4. 总入口 `SKILL.md` 第 1 步路由表加一行；
5. `scripts/install_skills.sh` 的 `link_skill` 列表加一行，重跑即挂载到
   `<项目根>/.dsh/skills/comfyui-<new-type>`。

**更换模型/风格**：同类型目录可放多个模板（`default_sdxl.json`、`flux_dev.json`），
每个模板自带一套 `_defaults`（尺寸/步数/模型名），调用时 `--workflow` 指定即可。

## 5. 注意事项

- 生成结果、提示词原文与 seed 应一并向用户说明，便于复现（同 seed + 同提示词 ≈ 同结果）。
- 视频类模板是骨架（不同视频模型节点差异大），首次使用务必在 ComfyUI 界面
  验证并重新导出，见 `workflows/README.md`。
- 图片/视频路径必须是 agent 可访问的本地路径；用户给的 URL 需先下载。
