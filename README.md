# comfyui-suite — ComfyUI 生图/生视频组合 Skill

面向 LLM agent 的组合 skill：分析用户描述自动路由到 **文生图 / 图生图（含图文一起生图）
/ 文生视频 / 图生视频 / 参考生视频**，完成提示词标准化 → ComfyUI API 调用 → 结果取回。

## 快速开始

```bash
# 1. 配置服务地址（默认 127.0.0.1:8188）
vi config/comfyui.yaml        # 或环境变量 COMFYUI_HOST / COMFYUI_PORT

# 2. 确认服务可用
python3 scripts/comfyui_api.py health
python3 scripts/comfyui_api.py list

# 3. 生成（无任何第三方依赖，python3 ≥ 3.8 直接运行）
python3 scripts/comfyui_api.py text-to-image --prompt "a cat ..." --seed 42
python3 scripts/comfyui_api.py image-to-image --prompt "..." --image in.png --denoise 0.6
python3 scripts/comfyui_api.py text-to-video  --prompt "..." --frames 49 --fps 16
python3 scripts/comfyui_api.py image-to-video --prompt "..." --image first.png
python3 scripts/comfyui_api.py reference-to-video --prompt "..." --image role.png --video ref.mp4
```

## 目录

| 路径 | 作用 |
|---|---|
| `SKILL.md` | **总入口**：路由规则 + 五步调度流程 |
| `references/guide.md` | 使用/安装/扩展/配置分层参考（运行时按需加载） |
| `skills/<type>/SKILL.md` | 6 个子 skill：5 个生成类型 + `prompt-optimizer`（只优化提示词） |
| `scripts/comfyui_api.py` | 统一调用脚本：上传/提交/轮询/下载，纯标准库 |
| `scripts/install_skills.sh` | 一键挂载 7 个可调用入口到 `<项目根>/.dsh/skills` |
| `workflows/<类型>/*.json` | API 格式工作流模板（`{{占位符}}` + `_defaults`），规范见 `workflows/README.md` |
| `prompt-guides/` | 图片/视频提示词标准化参考 |
| `config/comfyui.yaml` | 服务连接配置：地址/超时/输出目录（生成参数在模板 `_defaults`） |

## 使用方式（作为 agent skill）

用 `scripts/install_skills.sh` 把 7 个入口挂到项目级 skills 根 `.dsh/skills/`（DSH 只扫一层）：

```bash
bash scripts/install_skills.sh
```

挂载后 agent 可调用：`/comfyui-suite`（总入口，自动路由）或
`/comfyui-text-to-image`、`/comfyui-image-to-video` 等（单类型子 skill）。

## 重要提醒

- 自带 workflow 模板（尤其视频类）是**骨架参考**：不同部署的模型/节点差异大，
  首次使用请在 ComfyUI 界面验证后重新导出覆盖，方法见 `workflows/README.md`。
- 扩展新类型 = 加 workflow 目录 + 注册脚本命令 + 加子 skill + 登记路由表 + 安装脚本加一行，
  详见 `references/guide.md`「扩展指南」。
