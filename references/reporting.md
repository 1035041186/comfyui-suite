# 交付报告规范

> 本文件是"交付时向用户汇报"的**详细规范与示例**，按需加载。
> 总入口 `SKILL.md` 第 5 步只做概述并指向本文件；生成类子 skill 交付时也参考本文件。

向用户交付时，**用一段可读的中文说明**，清楚交代「我用了哪个类型、哪套工作流、哪个模型、
哪些关键参数」，同时把命令与参数放在代码块里承载精确值。**不要只丢一个文件路径或一堆 JSON**。

## 报告结构

按此组织，描述自然、参数精确；语气可灵活，但**调用序列 + 调用链 + 参数 + 结果四块必须齐全**：

```
【调用序列】（按实际执行顺序列出用过的子 skill / 命令，含先后）
> 1. 判断类型 → 路由（本次用 /comfyui-suite 总入口，或直接子 skill）
> 2. prompt-optimizer（优化提示词；若用户要求"就用原话"则跳过）
> 3. list（看可用模板）+ info（查服务端真实模型）
> 4. validate（确认模板/模型匹配）
> 5. <生成子 skill 命令>（真正生成）
> 6. 交付报告（本文件）

【调用链】类型 → 工作流 → 模型
> 判定：为什么路由到这个类型（输入素材 + 用户意图）
> 工作流：default_sd15_base（SD 整包）/ krea2（Krea2 分体）/ ...；默认 or --workflow 显式
> 模型：oneObsession_v23（默认）或依据 info/models.md 换成了 xxx

【关键参数】
> 提示词摘要：<一句话概括正向/负向内容，别整段贴>
> seed / width / height / steps / cfg / denoise / frames / lora 逐个列出

【实际命令】（代码块）
python3 scripts/comfyui_api.py <类型> --prompt "..." --seed N --width W --height H ...

【结果】
> 预览（图片用 Markdown 内联显示，URL 直接取自脚本输出里的 `preview_url`）：
>   ![生成图](<preview_url>)
>   非图片产物（视频/GIF）不内联，改为直接链接：<preview_url>
> 文件路径：`outputs/text-to-image/20260828_1143_t2i_xxx.png`（inline code 引用，可点击打开）
> 校验：validate 是否通过（模型名/节点匹配）｜失败原因
```

### 预览图（`preview_url`）约定

生成命令的结果 JSON 里，每个产物都带一个 `preview_url`，形如
`http://<host>:<port>/view?filename=<原文件名>&subfolder=<子目录>&type=output`。

- **host/port/protocol 由脚本从 `config/comfyui.yaml` 动态读取**（环境变量与 `--server` 覆盖后与请求所用
  地址一致），**不要**在报告里写死 `127.0.0.1:8188`——直接粘贴 `preview_url` 即可，保证和服务地址一致。
- `filename/subfolder/type` 是 ComfyUI history 的**原始元数据**；本地下载名带时间戳前缀
  （`<时间戳>_<原文件名>`），**只能**用作上面的本地路径 inline code，**不能**放进 `/view` URL，否则 404。
- 浏览器需能访问到该 host（用户查看端与服务同机/同网段）；图片在 Markdown 里用 `![alt](URL)` 内联显示，
  视频/GIF 建议直接放链接。

### 调用序列写法说明

- 按**实际发生顺序**列，**有先后的编号**，不要只罗列用过的；即使某个可选步骤被跳过
  （如 prompt-optimizer 被跳过），也要标注（如"（跳过：用户要求用原话）"），反映真实路径；
- 目的是让用户**看到 agent 走没走完整流程**：是否先查 `info`/`list`、是否 `validate`、
  是否按顺序路由→优化→生成；
- 若内部用 `--set`/`--lora`/`--checkpoint` 等做了额外参数调整，也在对应步骤里标注；
- 若中途出错回退（如某模板 validate 失败后换模板），也要在序列里说明。

## 要点

- 调用链与参数**必须写具体值**（模型名、seed、尺寸、lora），这是判断"用没用对"的依据；
- 描述用**自然语言**，参数用**代码块精确呈现**，二者结合，避免整段命令/JSON 堆砌；
- 若执行失败，同样按此格式呈现，并说明失败阶段（连接/渲染/任务 error/超时）与依据
  （`validate` 提示、stderr 报错）。

---

## 完整示例

> 以下是一个"文生图、SD 写实、换了模型"的完整报告示例，展示如何把调用路径与参数写成
> 可读又不失精确的说明。

【调用序列】
> 1. /comfyui-suite 总入口：判定该为「文生图」（用户只有文字、无图片）。
> 2. prompt-optimizer：把"写实人像"口语描述优化为英文正向+负向提示词。
> 3. list + info：确认 text-to-image 有 default_sd15_base / krea2 两套模板，并查服务端真实模型。
> 4. validate --type text-to-image：确认模板节点、模型名存在。
> 5. text-to-image 生成（见下方实际命令），用 --checkpoint 换成写实模型。
> 6. 本交付报告。

【调用链】文生图 → SD 整包（default_sd15_base）→ 模型 majicmixRealistic_v7

> **为什么是文生图**：用户只给了文字描述，没有图片，是"画一张图"的意图。
> **工作流**：该类型有两套——默认 `default_sd15_base`（SD 整包）与 `krea2`（Krea2 分体）。
> 用户要的是"写实人像"，读 `references/models.md` 发现 SD 整包里的写实模型更契合，
> 但默认模板的 `oneObsession_v23` 偏二次元，所以换成写实的 `majicmixRealistic_v7`。
> 模型栈不变（仍是 SD 整包），故沿用默认工作流，只换 `--checkpoint`。

【关键参数】
> 正向提示词：写实人像 + 柔和光照 + 浅景深（完整英文见下方命令）
> 负向提示词：模糊、瑕疵、水印
> seed=42 ｜ width/height=1024×1024 ｜ steps=30 ｜ cfg=7 ｜ denoise=1.0 ｜ 无 LoRA

【实际命令】
```bash
python3 scripts/comfyui_api.py text-to-image \
    --prompt "a realistic portrait, soft cinematic lighting, shallow depth of field, 8k" \
    --negative "blurry, bad anatomy, watermark" \
    --seed 42 --width 1024 --height 1024 --steps 30 --cfg 7 \
    --checkpoint majicmixRealistic_v7.safetensors
```

【结果】
> 预览：![生成图](http://10.0.0.1:8188/view?filename=84f1a2.webp&subfolder=&type=output)
>   （`preview_url` 由脚本从 `config/comfyui.yaml` 读取 host/port 生成；浏览器需能访问 10.0.0.1:8188）
> 文件：`outputs/text-to-image/20260828_1143_t2i_84f1a2.webp`（inline code 引用，可点击打开）
> 校验：`validate --type text-to-image --checkpoint majicmixRealistic_v7.safetensors`
> 通过（模型名存在于服务端、节点已安装）。
