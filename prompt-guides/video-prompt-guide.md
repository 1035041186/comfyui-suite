# 视频提示词编写标准（文生视频 / 图生视频 / 参考生视频）

本目录有两套视频提示词标准，**按目标模型的能力选用**：

| 标准 | 适用模型 | 输出形态 |
|---|---|---|
| **H3 音画一体协议**（首选） | 支持音频生成的新一代视频模型（音画同步、台词、配乐） | 指令行 + 三字段结构化段落 |
| 传统无声视频提示词（降级） | Wan2.1 / HunyuanVideo / SVD 等纯视觉模型 | 一段 50–120 词英文连贯描述 |

判断方法：workflow 模板中含音频节点（SaveAudio / 音轨合成 / 带 sound 的模型名）
→ 用 H3 协议；否则用传统写法。不确定时用传统写法（兼容性最好）。
H3 协议的**完整权威规范见同目录 `h3-video-prompt-protocol.md`**，本文是可执行的消化版。

---

# 第一部分：H3 音画一体协议（首选）

## 1. 任务分型（先判定，再动笔）

| 类型 | 输入 | 核心写法 |
|---|---|---|
| **T2VA**（文生音视频） | 纯文字 | 直接写三字段时间线 |
| **I2VA**（首帧生音视频） | 首帧图 + 文字 | 首帧锚定指令 + 从图向前发展 |
| **FL2VA**（首尾帧生音视频） | 首帧图 + 尾帧图 + 文字 | 双图对齐指令 + 补全首→尾的连续路径 |
| **L2VA**（尾帧生音视频） | 尾帧图 + 文字 | 尾帧对齐指令 + 从合理前态收敛到图 |

对应本 suite：text-to-video→T2VA，image-to-video→I2VA（只有首帧），
reference-to-video 按素材数选 I2VA/FL2VA/L2VA。

## 2. 最终提示词 = 指令行 + 三个核心字段

**指令行（首帧/尾帧任务必须是第一行，后空一行）：**

- I2VA 固定句式：
  `For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.`
- FL2VA 固定句式：
  `How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot N) aligns with the S.SS-second mark of the target video.`
- L2VA 固定句式：
  `How the reference pictures align with the target video — <Picture 1> (from [Shot N]) aligns with the S.SS-second mark of the target video.`

  其中 `N` = 实际最后一个镜头编号，`S.SS` = 视频有效时长（保留两位小数）。
  T2VA 无指令行，直接进入字段。

**三个核心字段（顺序固定，字段间空一行）：**

```text
integrated_multimodal_description: [Shot 1] ... [Shot 2] ...

overall_soundscape: ...

non_diegetic_music: ...
```

## 3. integrated_multimodal_description（主体，沿时间线展开）

一切细节必须"可见或可闻"：风格、构图、主体外观与位置、场景道具、动作反应、
镜头切换、台词、同步的环境音。

### 3.1 镜头切分

- `[Shot 1]` **不加时间戳**；后续镜头用严格递增的切换时间开头：
  `[Shot 2] At 00:03.500, the camera cuts to ...`
- 切换用语：`the camera cuts to / the shot cuts to / transitions to / changes to /
  switches to`；用户明确要求时才用 cross-dissolve / fade / wipe。
- 一次切换必须带来新信息（主体/空间/状态/视角/时间）；只改距离或角度时用运镜，不要切镜。
- Shot 1 开头先定**整体风格与初始构图**，风格从参考图（关键帧任务）或用户文字
  （T2VA）中确定：`Cinematic / live-action / 2D-animated / 3D CG / claymation /
  watercolor / vintage film`。

### 3.2 运镜 = 类型 + 幅度 + 速度（三维写全）

| 维度 | 可用表达 |
|---|---|
| 类型 | `Zoom In/Out`、`Push In/Pull Out`、`Pan Left/Right`、`Truck Left/Right`、`Tilt Up/Down`、`Pedestal Up/Down`、`Arc Shot`、`Tracking Shot`、`Static Shot`、`Shake Slightly/Strongly`、`POV`、`Roll Clockwise/Counterclockwise` |
| 幅度 | `with small amplitude` / `with large amplitude`（中等幅度省略） |
| 速度 | `at slow speed` / `at fast speed`（常速省略） |

运镜写成**镜头内的自然英文动作句**，不要在句尾堆标签：

```text
The camera pushes in with small amplitude at slow speed toward the folded letter in her hands.
The camera pans right with large amplitude at fast speed, revealing the open doorway.
```

### 3.3 说话人、台词、歌唱

- 发声主体用稳定 ID：`(S1)`、`(S2)`；多人齐声用 `(S1,S2)`；ID 跨镜头保持不变；
  不发声的角色不给 ID。
- 首次出现时用外观/音色信息建立身份（年龄、性别、音高、音色、语速、口音、是否入镜）。
- 身份描述、ID、动作、语气放在 `<d>` **外面**；`<d>` 内只放语言标签 + 用户给的
  原话，**逐字保留、不翻译不改写**：

```text
The young woman with a quiet, breathy voice (S1) says: <d>[English] I get off at the next station.</d>
The two children (S1,S2) shout together, <d>[English] Wait for us!</d>
```

- 画外音：固定短语 `says in an off-screen voiceover`，且每个画外音 `<d>` 块后
  紧跟一句"对应入镜角色嘴唇保持闭合"：
  `... <d>[English] I still remember that road.</d> while his lips remain completely closed.`
- 台词跨切镜：两段连接处加 `<scenetrans>` 并声明音频延续
  （`continues seamlessly across the cut` 等）；被结尾截断用 `<cutoff>`。

### 3.4 画面文字

实际可见的招牌/横幅/字幕/霓虹文字放英文双引号内，原文逐字保留不翻译：
`A red neon sign reading "营业中" glows above the doorway.`

## 4. overall_soundscape（环境音总览，1–4 句一段）

总结全片的**环境声、动作物理声、非语言人声**：风雨、车流、脚步、衣物摩擦、
撞击、呼吸、笑声、喘息。台词/歌唱/有声源音乐已属于主体字段，不要重复。
用户明确要求全片静音才写 `N/A`。

## 5. non_diegetic_music（配乐，1–3 句）

只描述**角色听不到、观众能听到**的配乐：乐器、速度、节奏、动态变化；
**不用抽象情绪词**、不解释配乐的情感功能。角色能听到的音乐（收音机、现场演奏）
是有声源事件，归主体字段。无配乐写 `N/A`。

## 6. 各任务型的组织路径

- **I2VA**：首帧锚定 → 动作起始 → 连续发展 → 结果/反应。先锁定图中风格、主体、
  构图、场景锚点，人物身份/服装/颜色/关键道具/空间关系保持一致。
- **FL2VA**：首帧状态 → 可观察的中间变化 → 差异逐步收窄 → 尾帧状态。
  一般**单镜头**（便于连续插值），用户明确要求才多镜头；尾帧必须由最后
  `[Shot N]` 在结尾精确到达。主体字段不要复述两张静态图，而是补运动路径。
- **L2VA**：合理的前态 → 明确的动作与过渡路径 → 末镜头逐步收敛 → 落图。
  图只属于最后的 `[Shot N]`，不天然属于 Shot 1。

## 7. 完整示例

四种类型的完整范例见 `h3-video-prompt-protocol.md` 第 5 节（Case 1–4），
生成前应对照其格式自查：指令行位置、Shot 编号与时间戳、运镜三维、
`<d>` 块、两个声音字段是否齐备。

---

# 第二部分：传统无声视频提示词（降级兼容）

适用于 Wan2.1 / HunyuanVideo / SVD 等纯视觉模型。输出**一段 50–120 词英文
连贯描述**，按维度组织：

```
[主体] + [动作/运动] + [场景] + [镜头语言] + [光照/氛围] + [风格]
```

1. **主体**：谁/什么，外观关键特征一句话；
2. **动作**：视频核心，具体、单一、可执行（"walks slowly toward the camera"），
   避免多个复杂连续动作；
3. **场景**：时间、地点、环境、天气；
4. **镜头语言**：`static shot / camera slowly pans left / tracking shot /
   drone shot rising / close-up zoom in / handheld shaking`——描述运镜，不描述剪辑；
5. **光照氛围**：`golden hour sunlight, foggy morning, neon reflections, cinematic lighting`；
6. **风格**：`cinematic, film grain, 35mm / anime / realistic footage, documentary style`。

## 规则

- 帧数短时（≤3 秒）只安排一个简单动作；动作幅度与帧率匹配；
- **图生视频**：不重复描述图中已有静态内容，重点写运动——谁怎么动、镜头怎么动、
  环境怎么变；
- **参考生视频**：写清参考元素与生成内容的关系，如
  `keep the character appearance from the reference image, performing the motion from the reference video`；
- 负向提示词通用模板：
  `blurry, low quality, distorted, morphing, flickering, watermark, text, static, inconsistent`

## 示例

用户输入："一个女孩在樱花树下，花瓣飘落，想要电影感"

文生视频（T2V）：
- prompt: `A young woman in a light spring dress stands beneath a blooming cherry blossom tree, pink petals drifting down around her in the gentle breeze. She slowly raises her hand to catch a falling petal. Camera slowly pushes in from a medium shot to a close-up of her face. Soft golden afternoon sunlight filters through the branches, creating a dreamy warm atmosphere. Cinematic, shallow depth of field, film grain, 35mm.`
- negative: `blurry, low quality, distorted, morphing, flickering, watermark, text, static`

图生视频（I2V，已有人物图）：
- prompt: `The woman gently raises her hand to catch falling cherry blossom petals, her hair and dress swaying softly in the breeze. Camera slowly pushes in toward her face. Petals drift continuously through the frame. Soft cinematic lighting, film grain.`

## 参数速查

- 帧数 `frames`：取 8n+1（17/33/49/81），49 帧 @16fps ≈ 3 秒；
- 分辨率：贴近模型训练分辨率，默认 1280×720（16:9）或 720×1280（竖屏）；
- 动作越复杂，`steps` 适当调高（30–40）。
