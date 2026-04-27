---
name: novel-chapter-distillation
description: Distill a long novel chapter by chapter into a reusable skeleton before deeper analysis. Use when the user wants every chapter compressed into core progression, state change, structural function, and hook so later protagonist, opening, outline, and highlight skills can validate against a stable backbone and recalibrate mid-project without drifting too far from the source.
---

# Novel Chapter Distillation

Use this skill when the task is to build a chapter-by-chapter distilled backbone for a novel before deeper analysis begins.

This skill should usually run before:

- `novel-opening-analysis`
- `novel-protagonist-encyclopedia`
- `novel-outline-analysis`
- `novel-highlight-scenes-analysis`

Its job is to produce a stable source-facing skeleton layer that later skills can check against.

## When To Use

Use this skill when the user asks to:

- distill every chapter of a long novel
- build a novel skeleton before deeper analysis
- create a chapter-by-chapter essence file for later verification
- create a correction layer that helps mid-project recalibration
- reduce drift between later analysis files and the original novel

## Default Output Goal

Unless the user narrows the scope, aim to produce a reusable chapter-distillation package that answers:

- what each chapter fundamentally does
- what the protagonist or core viewpoint state is in that chapter
- what new information or structural movement appears
- what relationship or situation changes
- what hook or pressure carries into the next chapter
- where the major stage changes likely occur
- which chapters should be used later as verification anchors

The target is not “some summary exists”.

The target is:

- every chapter has a distilled skeleton entry
- the chapter layer can be used later to verify protagonist, opening, outline, and highlight conclusions
- the project now has a stable calibration file instead of relying on memory

## Important Positioning

This skill is a pre-analysis layer.

It should not try to replace:

- protagonist lexicon work
- opening diagnosis
- whole-book outline diagnosis
- Top 10 highlight analysis

Instead, it should make those later layers safer and more stable.

## What This Skill Is Not

This skill is not:

- a chapter recap dump
- a detailed scene-by-scene commentary layer
- a substitute for whole-book structure analysis
- a character-card workflow

Its main product is:

- a chapter skeleton and calibration anchor layer

## Working Modes

### `fresh`

Use when no durable workspace exists yet.

Rules:

- initialize a new workspace
- normalize source text when needed
- detect chapters
- scaffold the chapter skeleton package
- do not stop after only copying the source if the user asked for real distillation

### `extend-existing`

Use when a novel workspace already exists and the chapter skeleton should be added in place.

Rules:

- treat existing files as reusable context, not duplication targets
- keep this layer source-facing and chapter-facing
- do not rewrite protagonist, outline, opening, or highlight files unless the user explicitly asks

### `repair-existing`

Use when chapter-distillation files already exist but still contain placeholders or weak calibration anchors.

Rules:

- inspect current files first
- patch only the weak layers
- rerun validation before closing

## Invocation Templates

### Template A: Add chapter distillation to an existing workspace

Use this when the novel already has a workspace and the user wants a source-facing skeleton layer added.

Default execution shape:

- read the workspace first
- detect reusable files
- initialize chapter-distillation files in place
- fill the chapter skeleton and calibration files
- run validator
- write back the validation report and latest handoff state

### Template B: Start a fresh chapter-distillation workspace

Use this when the user wants a standalone chapter-distillation package for a new novel.

Default execution shape:

- initialize a new workspace with the source file
- normalize the text
- detect chapters
- create the chapter skeleton file set
- run validator
- write back the validation report and latest handoff state

### Template C: Repair or validate an existing chapter-distillation package

Use this when chapter-distillation files already exist but are incomplete, placeholder-heavy, or inconsistent.

Default execution shape:

- read existing files first
- run validator
- patch only the weak layers
- rerun validator

## Chinese Prompt Examples

### Example 1: Existing workspace

```text
请使用 `novel-chapter-distillation` skill，在已有小说工作区基础上先对《<小说名>》原文做章节蒸馏。

要求：
- 每一个章节都做浓缩精华
- 形成一份可以给后续所有 skill 用来检查和校准的骨架文件
- 最后跑 validator，并把校验报告和最新工作状态写回工作区
```

### Example 2: Fresh workspace

```text
请使用 `novel-chapter-distillation` skill 为《<小说名>》建立一套章节蒸馏骨架工作区。

原文路径：`<原文绝对路径>`
目标工作区：`<工作区绝对路径>`

要求：
- 先识别章节
- 再把每一章压成精华骨架
- 再补阶段换挡草图和校准锚点
- 完成后跑 validator
```

### Example 3: Repair-only

```text
请使用 `novel-chapter-distillation` skill 检查《<小说名>》当前的章节蒸馏骨架文件。

要求：
- 先读取现有 chapter distillation 文件
- 运行 validator
- 只补缺口，不重写已经成立的内容
- 最后告诉我是否已经达到 `章节骨架已形成` 与 `校准锚点已可用`
```

## Scripts

Use the bundled scripts when the task is starting a durable chapter-distillation workspace or when you need deterministic completion checks.

- `scripts/init_chapter_distillation_workspace.py`
  Use when a new chapter-distillation workspace needs starter files, or when an existing novel workspace needs chapter-distillation files added in place.
- `scripts/validate_chapter_distillation_outputs.py`
  Use before closing the task when you want a repeatable check of file coverage and content coverage. The validator rejects placeholders, checks chapter-count coverage, and writes a persistent markdown report back into the workspace by default.

## Common Output Standard

Every durable chapter distillation should cover these common layers:

1. Project entry and handoff
2. Chapter manifest
3. Chapter-by-chapter distilled skeleton
4. Stage skeleton and gear-shift draft
5. Calibration and verification anchors

### Recommended durable file set

- `chapter-distillation-manifest.json`
- `<小说名>-章节蒸馏骨架.md`
- `<小说名>-阶段骨架与换挡草图.md`
- `<小说名>-校准与验证锚点.md`

Also check whether the project already has, or should now add:

- `README.md`
- `工作状态-YYYY-MM-DD.md`

## Minimum File Completion Standard

### `chapter-distillation-manifest.json`

Must include:

- chapter count
- chapter titles
- line ranges or source anchors

### `<小说名>-章节蒸馏骨架.md`

Must include every detected chapter and, for each chapter:

- chapter range or title
- core progression
- protagonist or viewpoint state
- key new information
- relationship or situation change
- structural function
- chapter-end hook

Must not be:

- only a directory of chapter names
- only recap prose without structural fields

### `<小说名>-阶段骨架与换挡草图.md`

Must include:

- provisional stage grouping
- likely gear-shift chapters or ranges
- what changes at each shift
- why those shifts matter later for verification

### `<小说名>-校准与验证锚点.md`

Must include:

- opening promise anchor
- first major shift anchor
- mid-book correction anchor
- expansion or scale-jump anchor
- climax-pressure anchor
- ending or terminal anchor
- later skills should verify against what

## Workflow

### 1. Normalize the source before distilling

Before writing anything else:

- ensure the source is copied into the workspace
- convert `.txt` to Markdown when needed
- detect chapter headings from the normalized source

Prefer reusing local chapter-aware tools and regex behavior already used elsewhere in the workspace system.

### 2. Distill every chapter into structural fields

Do not write “chapter summaries” in loose prose.

Each chapter should be reduced into a stable structural unit that later skills can check against.

At minimum, every chapter entry should answer:

- what actually moves here
- what state the protagonist or key viewpoint is in
- what new information appears
- what relationship or situation changes
- what this chapter structurally does
- what pulls the reader onward

### 3. Keep the chapter layer source-facing

This layer should stay close to the source.

Do not over-interpret too early.

Prefer:

- chapter facts
- clear structural movement
- stable anchors

Over:

- large thematic conclusions
- speculative full-book judgments

### 4. Build a later-use calibration file

This skill should always leave behind a file that later skills can use for checking drift.

That file should answer:

- which chapters must be revisited when later judgments are made
- where the novel first promises its main direction
- where the book changes gear
- where the middle should be checked for looseness
- where the ending setup begins to compress

### 5. Finish with a standardized closure judgment

Do not stop after chapter sections exist.

At the end, explicitly decide:

- has the project reached `章节骨架已形成`
- has the project reached `校准锚点已可用`

## Reference

Use `references/chapter-distillation-checklist.md` before declaring the package complete.
