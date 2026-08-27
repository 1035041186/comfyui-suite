# workflows/ — ComfyUI 工作流模板目录

每个子目录对应一种生成类型，与 `skills/` 下的子 skill 一一对应：

| 目录 | 生成类型 | 必需输入 |
|---|---|---|
| `text-to-image/` | 文生图 | 提示词 |
| `image-to-image/` | 图生图 / 图文混合生图 | 提示词 + 输入图片 |
| `text-to-video/` | 文生视频 | 提示词 |
| `image-to-video/` | 图生视频（首帧驱动） | 提示词 + 输入图片 |
| `reference-to-video/` | 参考生视频（角色/姿态参考） | 提示词 + 参考图片 + 参考视频 |

## 模板文件规范

1. **API 格式 JSON**：在 ComfyUI 网页中搭建好工作流后，菜单选择
   **「Save (API Format)」/「导出 API 格式」** 得到的就是 node-id → `{class_type, inputs}` 的 JSON。
2. **占位符**：把需要动态替换的值改为 `{{KEY}}` 形式（字符串值保留引号：
   `"text": "{{PROMPT}}"`；数值直接写 `"seed": {{SEED}}`）。脚本内置占位符：
   `PROMPT / NEGATIVE / SEED / WIDTH / HEIGHT / STEPS / CFG / DENOISE /
   FRAMES / FPS / CHECKPOINT / PREFIX / UPLOADED_IMAGE / UPLOADED_VIDEO`。
   自定义占位符用 `--set KEY=VALUE` 传入（如 LoRA 名）。
3. **`_defaults` 元信息**（可选，顶级字段）：**该模板专属的生成参数默认值**
   —— `checkpoint / width / height / steps / cfg / denoise / frames / fps /
   negative / prefix`。尺寸、帧数、步数、模型名是跟随模型与工作流的属性，
   全部写在这里（**不写进 config/comfyui.yaml**），换模板即换一套默认值。
   提交前脚本会自动剥离 `_defaults`/`_comment`。
4. **默认选择规则**：脚本运行时若未用 `--workflow` 指定，则按文件名排序取
   `default*` 开头的第一个 JSON。同一类型可放多个模板（如
   `default_sdxl.json`、`flux_dev.json`），用 `--workflow` 显式选择。

## 如何新增/替换模板

1. 在 ComfyUI 界面搭好并**手动跑通**工作流；
2. 导出 API 格式 JSON；
3. 把要动态化的字段替换为 `{{占位符}}`，补上 `_defaults`；
4. 放入对应类型目录，文件名以 `default_` 开头作为默认模板；
5. 运行 `python3 scripts/comfyui_api.py <类型> --prompt test --dry-run` 校验渲染结果。

## 如何扩展新类型

1. 新建 `workflows/<new-type>/` 并放入 `default_*.json`；
2. 在 `scripts/comfyui_api.py` 的 `KNOWN_TYPES` 与 `build_parser()` 中注册 `<new-type>`
   （或直接以 `upload` + 通用方式调用，参见脚本内注释）；
3. 新建 `skills/<new-type>/SKILL.md`（复制现有子 skill 修改）；
4. 在根 `SKILL.md` 的路由表中登记新类型。

> ⚠️ 自带模板是**骨架参考**：视频类模型的节点结构（如 Wan、HunyuanVideo、
> LTX-Video）差异较大，请以你实际部署的模型在 ComfyUI 中验证后导出的版本为准。
