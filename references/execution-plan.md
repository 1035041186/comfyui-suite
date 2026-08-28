# 执行计划模型 & 宿主任务清单适配（可移植）

> 本文件是**按需加载**的参考信息。总入口 `SKILL.md` 的「执行步骤清单」只做概述并指向本文件。
>
> 目的：让 skill 的执行步骤能在**任意 agent** 里以"任务清单"呈现，而 **skill 本身不耦合任何宿主的
> 任务清单机制**。skill 只暴露一份**可移植的计划数据**，具体渲染交给"那个宿主里的 agent"用它自己的
> 任务清单工具完成。

## 1. 可移植计划模型

```jsonc
// 计划（plan）—— 整份替换，不做局部编辑
{
  "steps": [
    { "title": "路由判定",       "status": "pending"     },
    { "title": "提示词标准化",   "status": "in_progress" },
    { "title": "服务检查与选模型", "status": "pending"     },
    { "title": "调用生成",       "status": "pending"     },
    { "title": "交付报告",       "status": "pending"     }
  ]
}
```

- **`steps`**：`[{ title: string, status: "pending" | "in_progress" | "completed" }]`；
- **status 语义**：`pending`＝未开始、`in_progress`＝正在做、`completed`＝已完成；
- **整份替换**：每推进一次就发送**完整**列表（同常见 todo 工具语义），不用部分更新；
- **来源**：本 skill 的 5 个具名步骤（见 `SKILL.md`「执行步骤清单」）就是这份计划的**种子**。
  子 skill（单类型）若有更细步骤，直接替换/细分对应项即可，模型不变。

## 2. 宿主无关的同步规则

驱动本 skill 时，agent 按此规则把计划映射到宿主：

1. 把每个 `step.title` 映射为宿主任务清单**一项的描述**，`step.status` 映射为该项状态；
2. 随进度更新：开始时置 `in_progress`，完成即置 `completed`；
3. **优先**使用宿主原生任务清单工具；宿主无任务清单工具时，打印一份**文本清单**（同样的
   步骤 + 状态）；
4. **不要**在 skill 里硬编码任何宿主工具名 —— 映射是"知道宿主"的 agent 的职责。

## 3. 按宿主的适配示例（示例，非依赖）

下列映射**只是说明性示例**，帮助"知道宿主"的 agent 照猫画虎；**skill 不依赖它们**。

### 3.1 DSH 示例（仅说明用）

DSH 提供 `todo_write` 工具，入参为 `{ todos: [{ content, status }] }`。映射：

```ts
// 计划 -> DSH todo_write
const todos = plan.steps.map((s) => ({ content: s.title, status: s.status }))
// 调用（示意）：todo_write({ todos })
```

DSH 客户端会通过 session-projection 把 `todo_write` 的 `todo/write` 事件投影成 `todos`
状态，并在输入区渲染成任务清单（`TodoDock`）。**这只是 DSH 的呈现方式，不是本 skill 的义务。**

### 3.2 其它 agent / 兜底

- 其它现代 agent 通常也有 to-do 类工具，把同一个计划 `steps` 映射过去即可（工具名/字段名不同，
  由该 agent 自己解析）；
- 无任务清单工具时，直接打印：

```text
[进行中] 提示词标准化
[待处理] 服务检查与选模型
[待处理] 调用生成
[待处理] 交付报告
```

## 4. 边界（诚实说明）

"在任意 agent 里都显示为任务清单"依赖两个前提：**该宿主有任务清单工具**，且**该 agent 会把
`steps` 映射过去**。若宿主只有文本能力，则退化为文本清单。skill 只保证提供**标准、可移植的
`steps` 数据**，不保证宿主必然渲染 —— 渲染属宿主工作机制。
