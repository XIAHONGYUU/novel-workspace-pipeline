---
name: novel-highlight-scenes-analysis
description: Analyze the most attractive scenes, dramatic beats, and memorable plot moments across a whole novel. Use when the user wants a durable Top 10 high-impact scene package that explains which moments hook readers most, why they work, how they are distributed, and what kind of pleasure, suspense, reversal, or emotional payoff drives them.
---

# Novel Highlight Scenes Analysis

Use this skill when the task is to understand what makes a novel especially hard to put down.

Focus on the whole-book high-attraction layer:

- the most memorable plot moments
- the strongest dramatic beats
- scenes readers are likely to retell
- where the book's strongest suspense, reversal, payoff, pain, or exhilaration comes from
- how those scenes are distributed across the book
- whether the novel's best hooks cluster too early or too late
- what kind of pleasure structure the novel relies on most

Do not drift into protagonist encyclopedia work or whole-book outline diagnosis unless those layers are needed as context.

## Default Output Goal

Unless the user narrows the scope, aim to produce a reusable highlight-analysis package that answers:

- which 10 plot moments are the strongest memory points in the book
- where they happen in the book's stage structure
- why each one works
- what emotional or structural mechanism each one relies on
- whether the novel's attraction mainly comes from suspense, reversal, escalation, relationship payoff, world reveal, or some other engine
- whether the high points are well distributed or structurally uneven
- what the book should protect, amplify, advance, delay, or compress if it wants stronger attraction

Prefer durable files when the user wants reusable output.

## Important Default

This skill should usually be used after a novel workspace already exists.

### 开始前必读文件（按文件名直接打开）

不要凭记忆或猜测——以下文件名是固定的，按模板替换 `<小说名>` 和 `<主角名>` 即可定位：

| 优先级 | 文件名 | 从中提取的信息 |
|---|---|---|
| P0 | `<小说名>-整书粗阶段划分.md` | 五阶段边界——用于定位每个高光桥段的所属阶段 |
| P0 | `<小说名>-主线支线与冲突地图.md`（如有） | 主线/支线结构——用于判断高光的结构功能 |
| P0 | `<主角名>-最终人物卡.md` | 主角身份变化序列——用于标注高光对应的身份含金量 |
| P1 | `<小说名>-高潮节奏与收束诊断.md`（如有） | 高潮分布和收束判断——交叉验证高光判断 |
| P1 | `<小说名>-黄金前三章总判断.md`（如有） | 开篇钩子体系——用于判断全书吸引力机制的延续性 |

**读取方式**：打开文件直接读。写 Top10 总表时，每个高光桥段应能标注它属于全书五阶段的哪一个。如果你不知道阶段边界在哪，说明你还没读粗阶段划分文件。

## What This Skill Is Not

This skill is not:

- `novel-protagonist-encyclopedia`
  - it does not center on a protagonist lexicon
- `novel-outline-analysis`
  - it does not center on whole-book structure alone
- `novel-opening-analysis`
  - it does not stay inside the first three chapters

Its product goal is:

- a whole-book Top 10 highlight package

## Invocation Templates

### Template A: Extend an existing novel workspace

Use this when the novel already has a durable workspace and the goal is to add a high-attraction layer in place.

Default execution shape:

- read the workspace first
- **开始前必读**：`<小说名>-整书粗阶段划分.md`、`<主角名>-最终人物卡.md`、`<小说名>-主线支线与冲突地图.md`（如有）
- initialize highlight-analysis files in the existing workspace
- write the Top 10 highlight file set
- run validator
- write back the validation report and latest handoff state

### Template B: Start a fresh highlight-analysis workspace

Use this when the user wants a standalone high-attraction package for a new novel.

Default execution shape:

- initialize a new workspace with the source file
- normalize the text
- produce the highlight-analysis file set
- run validator
- write back the validation report and latest handoff state

### Template C: Repair or validate an existing highlight-analysis package

Use this when highlight files already exist but are incomplete, placeholder-heavy, or structurally weak.

Default execution shape:

- read existing highlight files first
- run validator or compare against the checklist
- patch only the weak layers
- rerun validator

## Chinese Prompt Examples

### Example 1: Existing workspace

```text
请使用 `novel-highlight-scenes-analysis` skill，在已有小说工作区基础上分析《<小说名>》里最吸引人的十个剧情细节，复用已有上下文，补齐高光剧情文件，跑完 validator，并把校验报告和最新工作状态写回工作区。
```

### Example 2: Fresh workspace

```text
请使用 `novel-highlight-scenes-analysis` skill 为《<小说名>》建立一套“最吸引人的十个剧情细节”分析工作区。

原文路径：`<原文绝对路径>`
目标工作区：`<工作区绝对路径>`
主角名：`<主角名，可留空>`

要求：
- 找出全书最抓人的 10 个剧情细节
- 分析每个细节为什么成立
- 判断这些高光桥段在整本书里的分布是否合理
- 完成后跑 validator
```

### Example 3: Repair-only

```text
请使用 `novel-highlight-scenes-analysis` skill 检查《<小说名>》现有的剧情高光分析文件。

要求：
- 先读取现有 highlight 文件
- 运行 validator
- 只补缺口，不重写已经成立的内容
- 最后告诉我是否已经达到 `高光桥段已明确` 与 `剧情吸引力机制已拆清`
```

## Working Modes

### `fresh`

Use when no durable highlight-analysis workspace exists yet.

Rules:

- initialize a new workspace
- placeholders are acceptable only as scaffolds
- do not stop after initialization

### `extend-existing`

Use when the novel already has a workspace and the highlight layer should be added in place.

Rules:

- treat protagonist, outline, and opening files as preferred context
- new files should stay focused on high-attraction scenes, not rewrite the whole-book structure

### `repair-existing`

Use when highlight files already exist but still contain placeholders or weak diagnosis.

Rules:

- patch the weakest layers first
- preserve valid analysis where possible
- rerun validation before closing

## 质量标准（Quality Requirements）

**禁止的泛化话术：**
- ❌ "这个情节很爽" → 没说为什么爽、爽在哪个机制（反差/宣泄/翻转/揭露）
- ❌ "读者会追读" → 没有分析追读的具体心理驱动力
- ❌ "高光分布合理" → 没有给出分布的具体数据和判断依据
- ❌ "应该加强这里" → 没有说怎么加强、加强到什么程度

**正确的分析写法：**
- ✅ Top10 每个高光必须写明**吸引力类型**（爽点/痛点/悬念点/反差/翻转/揭露/情绪兑现）
- ✅ 每个高光必须写明**前置铺垫**和**发生后改变**，形成完整的因果链
- ✅ 改造建议必须包含**具体章节目标**和**可执行方案**

**两轮精炼：**
1. 第一轮：生成 Top10 总表和逐条拆解初稿
2. 第二轮：逐条自检——吸引力类型判断是否准确？前置铺垫和后置改变是否成因果链？改造建议是否可执行？
3. 重写不合格部分后再提交 validator

## Scripts

Use the bundled scripts when the task is starting a durable highlight-analysis workspace or when you need deterministic completion checks.

- `scripts/init_highlight_workspace.py`
  **角色**：搭脚手架，不写分析。此脚本只生成文件框架和字段模板——你需要读取已有上下文和原文来填充内容。

- `scripts/validate_highlight_outputs.py`
  Use before closing the task when you want a repeatable check of file coverage and content coverage.

### Validator 关键词速查表

Validator 通过 `has_keywords()` 检查每个文件是否包含特定关键词。请在填充内容时确保覆盖以下关键词：

| 文件 | 需覆盖的关键词（minimum ≥4） |
|---|---|
| `<小说名>-最吸引人的十个剧情细节总表.md` | 总判断、高光细节 1、所在阶段、吸引力类型、主要作用 |
| `<小说名>-剧情吸引力机制分析.md` | 核心判断、反差、悬念、情绪兑现、翻转、揭露 |
| `<小说名>-Top10细节逐条拆解.md` | 细节 1、发生位置、前置铺垫、吸引力为什么成立、改变了什么 |
| `<小说名>-高光桥段分布与节奏判断.md` | 高光分布总判断、前段高光、中段高光、后段高光、节奏判断 |
| `<小说名>-最强爽点痛点悬念点总结.md` | 最强爽点、最强痛点、最强悬念点、综合判断 |
| `<小说名>-剧情高光改造建议.md` | 当前最强高光、当前最弱区段、应该补强什么、应该前移或后移什么、应该压缩或合并什么 |
- `scripts/validate_highlight_outputs.py`
  Use before closing the task when you want a repeatable check of file coverage and content coverage. The validator rejects placeholders and writes a persistent markdown report back into the workspace by default.

## Common Output Standard

Every durable highlight analysis should cover these common layers:

1. Project entry and handoff
2. Top 10 highlight summary table
3. Attraction-mechanism analysis
4. Scene-by-scene Top 10 breakdown
5. Highlight distribution and pacing judgment
6. Strongest pleasure / pain / suspense summary
7. High-attraction revision advice

### Recommended durable file set

- `<小说名>-最吸引人的十个剧情细节总表.md`
- `<小说名>-剧情吸引力机制分析.md`
- `<小说名>-Top10细节逐条拆解.md`
- `<小说名>-高光桥段分布与节奏判断.md`
- `<小说名>-最强爽点痛点悬念点总结.md`
- `<小说名>-剧情高光改造建议.md`

Also check whether the project already has, or should now add:

- `README.md`
- `工作状态-YYYY-MM-DD.md`

## Minimum File Completion Standard

### `<小说名>-最吸引人的十个剧情细节总表.md`

Must include:

- a direct overall judgment
- 10 distinct highlight entries
- stage or position for each entry
- attraction type for each entry
- brief note on what each entry does

Must not be:

- only a list of favorite scenes with no explanation

### `<小说名>-剧情吸引力机制分析.md`

Must include:

- the book's major attraction engines
- which mechanism appears most often
- how the book combines suspense, reversal, payoff, escalation, emotion, or reveal
- where the mechanism changes gear

### `<小说名>-Top10细节逐条拆解.md`

Each entry should explain:

- where the scene happens
- what setup exists beforehand
- why the moment explodes at that specific point
- what kind of reader pleasure it triggers
- what relationship, status, or structural layer changes because of it
- whether it is a reusable retellable scene

### `<小说名>-高光桥段分布与节奏判断.md`

Must include:

- where the strongest highlights cluster
- whether the front, middle, and late book all have enough energy
- whether the book peaks too early, too late, or repeatedly
- what that means for reading momentum

### `<小说名>-最强爽点痛点悬念点总结.md`

Must include:

- strongest exhilaration point
- strongest pain point
- strongest suspense point
- what kind of pleasure the book relies on most overall

### `<小说名>-剧情高光改造建议.md`

Must include:

- strongest current highlights worth protecting
- weaker ranges worth repairing
- what should be strengthened
- what should be advanced or delayed
- what should be compressed or merged

Must not be:

- only praise
- only vague language such as “could be stronger”

## Workflow

### 1. Enter the workspace and read existing files first

Before writing anything new, inspect the current workspace and answer:

- what already exists
- whether protagonist files already explain why some scenes matter
- whether outline files already explain stage changes and payoff structure
- whether opening files already identify the first major promise
- what the highlight-analysis layer still lacks

Prioritize:

- `README.md`
- latest `工作状态-YYYY-MM-DD.md`
- protagonist final card when present
- protagonist index when present
- outline overview when present
- opening total judgment when present

### 2. Build a candidate scene pool before picking the Top 10

Do not jump straight into the final list.

First identify a wider candidate pool of strong scenes, then narrow it by asking:

- is this moment actually memorable
- does it shift something real
- does it compress multiple reader pleasures into one point
- would readers naturally retell it
- does it represent the novel's strongest attraction engine

### 3. Keep the Top 10 structurally varied when the novel supports it

Avoid selecting 10 scenes that all do the same thing unless the book truly has only one attraction engine.

Prefer a mix of:

- early promise scenes
- mid-book reversals
- relationship payoffs
- identity reveals
- power breakthroughs
- world or rule reveals
- late-book compression points

### 4. Explain why each scene works, not just that it is cool

For each selected scene, analyze:

- setup
- timing
- contrast
- pressure
- payoff
- consequence

The key question is:

- why does this moment hit this hard here

### 5. Compare the highlights against the whole-book rhythm

Once the Top 10 is stable, judge:

- whether the strongest scenes are too front-loaded
- whether the middle loses energy
- whether late-book highlights are genuine payoffs or just scale inflation
- whether the novel's memory points align with its structural peaks

### 6. Finish with a standardized closure judgment

Do not stop after listing strong scenes.

At the end, explicitly decide:

- has the project reached `高光桥段已明确`
- has the project reached `剧情吸引力机制已拆清`

## Reference

Use `references/highlight-scenes-checklist.md` before declaring the package complete.
