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
> 产物：脚本 `files[]` 里的**每一个**都要展示，**一个都不漏**（批量/多张约定见下方「多张产物约定」）。
> 预览（图片用 Markdown 内联显示，URL 直接取自脚本输出里的 `preview_url`）：
>   ![生成图](<preview_url>)
>   多张时逐张一行：![生成图1](<preview_url_1>) ／ ![生成图2](<preview_url_2>) ……
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

### 多张产物约定（批量必读）

- 脚本返回的 `files[]` **即全部产物**（如 `--batch N` 时就是 N 张）；交付时**必须把 `files[]` 里的每一个
  都展示出来**——**只展示其中一张、只挑一部分、或截断剩余的，都属于漏交付**。
- **多张图片**：逐张内联，每张一行 `![生成图i](<preview_url_i>)`；多张非图片（视频/GIF）逐张放链接，
  各自一行。
- **不要因为"太多"就只贴几张或改贴链接**：要么全列，要么先说明"共 N 张"后**仍全列**；
  文件路径（本地 `outputs/...`）同样**逐个**用 inline code 列出，与预览一一对应。
- 若某张产物在 `files[]` 中带 `download_error`（下载失败），也要在结果里如实标注该张失败，
  而不是静默省略它。

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

## 迭代版报告（第 N 轮调整，**不限轮数**）

当本次是**对上一轮已生成图片的多次调整**时，报告在四要素基础上**额外交代迭代属性**，
这是与首次生成的关键区别（判定见 `references/refine.md`，编排见 `skills/image-refine/SKILL.md`）：

```
【调用序列】...（同首次，但注明是"第 N 轮调整"）
【调用链】类型 → 工作流 → 模型
> 判定：<为什么这一轮走 image-refine；**基准取舍**——完全不喜欢→重生成(不基于旧图)，骨架满意→基于旧图迭代；相对上一轮"少动/大动"——少动=同实例换一版，大动=换方向/改词/换风格>
> 基准：第 N-1 轮的输出图（outputs/<类型>/<时间戳>_xxx.png）
> 工作流 / 模型：同首次或本轮更换（换模型须 validate）
【关键参数】... + 迭代上下文
> 本轮改动：<改了什么轴，为什么动它>
> 固化项：seed=<上轮> 固定（A/B）｜除变化轴外其余参数不变
> 基线对照：上轮 prompt / seed / denoise / steps / cfg
【实际命令】
python3 scripts/comfyui_api.py image-to-image --image <上轮输出> --seed <上轮> --denoise 0.4 --prompt "..."
【结果】
> 第 N 轮输出：![生成图](<preview_url>)
> 文件：`outputs/<类型>/<时间戳>_xxx.png`
> 回滚提示：若不满意可用上轮固化 seed/参数复现第 N-1 版。
```

> 要求：**明确标注"这是第 N 轮"**、**说清"相对上一轮改了哪个轴、为什么"**、**列出上一轮基线参数**
> 作为对照，而不是从头复述一整轮生成（那是首次交付的写法）。

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
