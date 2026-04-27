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

The normal starting point is:

- protagonist layer already exists, or
- outline layer already exists, or
- opening layer already exists, or
- at least the workspace already contains stable project files

That means the first move is usually:

- read the workspace first
- reuse protagonist, outline, and opening context when present
- then build the highlight-analysis layer on top of it

not:

- rebuild the project from zero

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
- detect reusable context such as protagonist card, index, outline files, or opening files
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

## Scripts

Use the bundled scripts when the task is starting a durable highlight-analysis workspace or when you need deterministic completion checks.

- `scripts/init_highlight_workspace.py`
  Use when a new highlight-analysis workspace needs starter files, or when an existing novel workspace needs highlight-analysis files added in place.
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
