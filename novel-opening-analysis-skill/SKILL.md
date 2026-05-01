---
name: novel-opening-analysis
description: Analyze a novel's opening, especially the first three chapters, to judge hook strength, protagonist debut efficiency, conflict startup, information release, chapter-end pull, genre promise, and revision priorities. Use when the user wants a durable first-three-chapter diagnostic rather than a whole-book outline or protagonist encyclopedia.
---

# Novel Opening Analysis

Use this skill when the task is to understand whether a novel's first three chapters actually work.

Focus on:

- opening hook
- protagonist debut efficiency
- first conflict startup
- information-release rhythm
- first-three-chapter structure
- chapter-end pull
- genre and reader promise
- pacing drag or over-exposition
- concrete revision priorities

Do not drift into whole-book outline analysis unless the user explicitly asks for it.

## Default Output Goal

Unless the user narrows the scope, aim to produce a reusable opening-analysis package that answers:

- what the novel is promising in the first three chapters
- whether the hook is strong enough
- whether the protagonist becomes clear fast enough
- whether conflict truly starts or only background is dumped
- whether the worldbuilding is feeding the story or stalling it
- whether each chapter ending creates forward pull
- why a reader would or would not continue
- what should be revised first if the opening is weak

Prefer durable files when the user wants reusable output.

## Important Default

Because the first three chapters are short compared with a whole novel, this skill should analyze in more detail by default.

That means:

- chapter-by-chapter breakdown is expected
- paragraph or beat-level comments are allowed when useful
- do not stop at a broad summary if a more precise structural diagnosis is possible

In other words:

This skill should usually be more detailed than `novel-outline-analysis`, not less.

## Invocation Templates

### Template A: Analyze opening inside an existing novel workspace

Use this when the user already has a novel workspace and wants an opening-layer package added in place.

Default execution shape:

- read the workspace first
- detect reusable context such as protagonist card, index, or outline files
- initialize opening-analysis files in the existing workspace
- write the first-three-chapter analysis file set
- run validator
- write back the validation report and latest handoff state

### Template B: Start a fresh opening-analysis workspace

Use this when the user wants a standalone opening-analysis package for a new novel.

Default execution shape:

- initialize a new workspace with the source file
- normalize the text
- produce the opening-analysis file set
- run validator
- write back the validation report and latest handoff state

### Template C: Repair or validate an existing opening-analysis package

Use this when opening-analysis files already exist but are incomplete, placeholder-heavy, or inconsistent.

Default execution shape:

- read existing opening files first
- run validator or compare against the checklist
- patch only the weak layers
- rerun validator

## Chinese Prompt Examples

### Example 1: Existing workspace

```text
请使用 `novel-opening-analysis` skill，在已有小说工作区基础上分析《<小说名>》的黄金前三章，复用已有上下文，补齐前三章分析文件，跑完 validator，并把校验报告和最新工作状态写回工作区。
```

### Example 2: Fresh workspace

```text
请使用 `novel-opening-analysis` skill 为《<小说名>》建立一套黄金前三章分析工作区。

原文路径：`<原文绝对路径>`
目标工作区：`<工作区绝对路径>`
主角名：`<主角名，可留空>`

要求分析尽可能细，至少覆盖每一章的钩子、冲突、信息释放、结尾拉力和修改建议。
```

### Example 3: Repair-only

```text
请使用 `novel-opening-analysis` skill 检查《<小说名>》现有的前三章分析文件。

要求：
- 先读取现有 opening 文件
- 运行 validator
- 只补缺口，不重写已经成立的内容
- 最后告诉我是否已经达到 `开篇抓力已明确` 与 `前三章结构已拆清`
```

## Working Modes

### `fresh`

Use when no durable opening-analysis workspace exists yet.

Rules:

- initialize a new workspace
- placeholders are acceptable only as scaffolds
- do not stop after initialization

### `extend-existing`

Use when the novel already has a workspace and opening analysis should be added in place.

Rules:

- treat existing protagonist or outline files as context, not duplication targets
- new files should stay focused on the opening, not rewrite the whole-book analysis

### `repair-existing`

Use when opening files already exist but still contain placeholders or weak diagnosis.

Rules:

- patch the weakest files first
- preserve valid analysis where possible
- rerun validation before closing

## Scripts

Use the bundled scripts when the task is starting a durable opening-analysis workspace or when you need deterministic completion checks.

- `scripts/init_opening_workspace.py`
  Use when a new opening-analysis workspace needs starter files, or when an existing novel workspace needs opening-analysis files added in place.
- `scripts/validate_opening_outputs.py`
  Use before closing the task when you want a repeatable check of file coverage and content coverage. The validator rejects placeholders and writes a persistent markdown report back into the workspace by default.

## Common Output Standard

Every durable opening analysis should cover these common layers:

1. Project entry and handoff
2. Opening total judgment
3. Chapter 1 breakdown
4. Chapter 2 breakdown
5. Chapter 3 breakdown
6. Hook and reader promise judgment
7. Opening problems and revision advice

### Recommended durable file set

- `<小说名>-黄金前三章总判断.md`
- `<小说名>-第一章拆解.md`
- `<小说名>-第二章拆解.md`
- `<小说名>-第三章拆解.md`
- `<小说名>-开篇钩子与读者承诺.md`
- `<小说名>-开篇问题与修改建议.md`

Also check whether the project already has, or should now add:

- `README.md`
- `工作状态-YYYY-MM-DD.md`

## Minimum File Completion Standard

### `<小说名>-黄金前三章总判断.md`

Must include:

- opening hook judgment
- protagonist debut judgment
- conflict startup judgment
- first-three-chapter structure judgment
- continue-reading drive judgment

Must not be:

- a plot recap only

### `<小说名>-第一章拆解.md` / `第二章拆解.md` / `第三章拆解.md`

Each chapter file should explain:

- what the chapter is structurally doing
- what hook or pressure exists
- what the protagonist learns, wants, or loses
- what information is released
- whether the ending creates forward pull
- what should be strengthened or cut

Because the context is small enough, more detail is preferred here.

### `<小说名>-开篇钩子与读者承诺.md`

Must include:

- immediate hook
- genre promise
- protagonist promise
- emotional or suspense promise
- chapter-end pull pattern

### `<小说名>-开篇问题与修改建议.md`

Must include:

- strongest parts
- weakest parts
- chapter-specific issues
- first-priority revision direction
- light revision suggestions

Must not be:

- only praise
- only vague “can be improved” language

## Workflow

### 1. Enter the workspace and read existing files first

Before writing anything new, inspect the current workspace and answer:

- what already exists
- whether the protagonist layer already clarifies the hero's role
- whether outline files already explain later payoffs that help opening diagnosis
- what the opening-analysis layer still lacks

Prioritize:

- `README.md`
- latest `工作状态-YYYY-MM-DD.md`
- protagonist final card when present
- protagonist index when present
- whole-book outline overview when present

### 2. Confirm the source and normalize the text

Identify the novel source first.

If this is a fresh project and durable results are wanted, initialize the workspace with:

- `scripts/init_opening_workspace.py --novel-name "<小说名>" --source "<原文路径>" [--protagonist "<主角名>"]`

If an existing workspace already exists and the goal is to add opening analysis on top of it, prefer:

- `scripts/init_opening_workspace.py --novel-name "<小说名>" --existing-workspace "<工作区路径>" [--source "<原文路径>"] [--protagonist "<主角名>"]`

If the source is `.txt` or messy plain text, use local conversion tools before analysis:

- `<repo-root>/text2markdown`

Do not silently accept undecodable text.

### 3. Build a precise three-chapter context layer

Read the first three chapters carefully enough to answer not just what happens, but how the opening works.

At minimum, identify:

- first hook beat
- protagonist first clear signal
- first clear pressure or danger
- first irreversible choice or commitment
- first meaningful worldbuilding delivery
- each chapter's closing pull

Because the context is small, default to detailed analysis rather than rough overview.

### 4. Judge the opening as reader experience, not only as summary

For each chapter, ask:

- why would a reader continue
- what confusion is productive
- what confusion is merely muddy
- what information is delayed too long
- what arrives too early without payoff

Do not stop at “this chapter introduces X.”

### 5. Separate hook, promise, and actual progression

Distinguish:

- what the text uses as the immediate hook
- what longer-term promise it makes about genre or story engine
- whether the first three chapters actually progress toward that promise

### 6. Diagnose pacing and information-release density

Always judge:

- whether exposition is too dense
- whether the protagonist acts quickly enough
- whether scene goals are clear enough
- whether chapter endings are strong enough

### 7. Produce outputs in durable form

Do not stop after loose notes.

Write:

- total judgment
- chapter 1 breakdown
- chapter 2 breakdown
- chapter 3 breakdown
- hook and promise file
- problems and revision file

### 8. Validate before closing

Before closing, run:

- `scripts/validate_opening_outputs.py --workspace "<工作区路径>" --novel-name "<小说名>"`

Your final completion judgment should explicitly say whether the result is:

- `开篇抓力已明确`
- `开篇抓力仍不足`
- `前三章结构已拆清`
- `前三章结构仍不足`

Also state:

- which files were reused as context
- which files were produced in this run
- whether the stop condition was reached by checklist comparison / validator rather than by impression

## Final Response Contract

When closing a durable workspace task, the final response should explicitly include:

- which working mode was used: `fresh`, `extend-existing`, or `repair-existing`
- which existing files were reused
- which files were newly produced or materially updated
- whether validator was run
- the final status using the required labels
- the strongest reason the opening works or fails
- the first revision priority if the opening is weak

## Quality Bar

Do not stop at:

- a plot summary
- a “first three chapters are okay” verdict without evidence
- broad genre talk without chapter structure
- generic advice not tied to specific chapters

The output is only complete when it can explain both:

- how the first three chapters function structurally
- why a reader would or would not continue

## Non-Goals and Hard Do-Nots

Do not:

- drift into whole-book outline analysis unless explicitly requested
- rewrite an existing protagonist card as an opening-analysis file
- treat placeholders as completed analysis
- replace chapter diagnosis with only a storyline recap
- declare success because files exist without validator confirmation

## References

Read this file when you need the fixed checklist and section expectations:

- [references/opening-analysis-checklist.md](references/opening-analysis-checklist.md)
