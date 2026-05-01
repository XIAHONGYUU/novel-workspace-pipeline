---
name: novel-outline-analysis
description: Analyze a novel's full outline, stage structure, main and side arcs, conflict escalation, pacing, climax, ending closure, and overall story skeleton. Use when Codex needs to read a full novel, long synopsis, chaptered draft, or completed manuscript and produce outline-level structural analysis, stage splits, plot maps, narrative diagnosis, or revision suggestions focused on the whole-book outline rather than only the protagonist or full cast.
---

# Novel Outline Analysis

Use this skill when the task is to understand a novel at the outline level.

Focus on the whole-book structure:

- premise and hook
- protagonist structural role
- core supporting cast and their relationship to the protagonist
- stage split
- main plot line
- side plot lines
- core conflict and explosion points
- time and place transitions
- conflict escalation
- major turning points
- climax and payoff
- ending closure
- pacing and structural weaknesses

Do not drift into a full-cast card workflow unless the user explicitly asks for it.

## Default Output Goal

Unless the user narrows the scope, aim to produce a reusable outline-analysis package that answers:

- what the novel is fundamentally about
- who the protagonist is and what structural role they serve
- which supporting characters actually pressure the plot
- how the book is divided into major stages
- what the main line is in each stage
- what the important side lines are
- where the core conflicts and explosion points are
- how time jumps and location changes drive stage changes
- where the structure changes gear
- whether the middle and ending actually hold together
- what the biggest structural strengths and weaknesses are
- what is generic to long-novel analysis and what is unique to this specific book

Prefer a file set when the user wants durable results.

## Default Assumption

Unless the user clearly says otherwise, assume this skill is being used after a protagonist-centered workspace already exists.

In other words, the default starting point is not:

- no context
- no protagonist layer
- no prior project files

The default starting point is:

- a novel workspace already exists
- the workspace often already contains protagonist files
- this skill should extend that workspace into a whole-book outline layer

This means the first move is usually:

- read the workspace
- understand the existing protagonist layer
- then build the outline layer on top of it

not:

- regenerate the protagonist workflow from scratch

## Scripts

Use the bundled scripts when the task is starting a fresh workspace or when you need a deterministic completion check.

- `scripts/init_outline_workspace.py`
  Use when a new novel needs a durable outline-analysis workspace with starter files.
- `scripts/validate_outline_outputs.py`
  Use before closing the task when you want a repeatable check of file coverage and content coverage.

## Common Output Standard

Every durable analysis should cover the common layers below. These layers may be satisfied by:

- new files created in this run
- existing project files that already cover the layer
- a mix of both

Do not mark the task complete until every common layer is either:

- completed in new output
- explicitly reused from existing files
- or clearly marked missing / blocked

### Common layers all novels should cover

1. Project entry and handoff
2. Protagonist anchor and protagonist card
3. Core supporting cast and their relationship to the protagonist
4. Whole-book stage split
5. Core conflict points and explosion points
6. Main line / side line / bridge line map
7. Time and place transitions
8. Climax, pacing, and ending closure
9. Structural strengths, weaknesses, and revision advice
10. Next-step deep-dive directions

### Recommended durable file set

- `<小说名>-大纲总览.md`
- `<小说名>-阶段与篇章拆分.md`
- `<小说名>-主线支线与冲突地图.md`
- `<小说名>-核心冲突点与爆发点.md`
- `<小说名>-时间与地点转折.md`
- `<小说名>-高潮节奏与收束诊断.md`
- `<小说名>-结构问题与修改建议.md`

Also check whether the project already has, or should now add:

- `<主角名>-最终人物卡.md` or an equivalent protagonist summary
- `<小说名>-核心配角与主角关系.md` or an equivalent relationship summary
- `README.md`
- `工作状态-YYYY-MM-DD.md`

If protagonist files already exist from `novel-character-cards` or `novel-protagonist-encyclopedia`, reuse and link them instead of regenerating a duplicate.

## Genre Reference Map

When the novel clearly fits one of these dominant modes, read the matching reference before finalizing the structure judgment:

- `references/progression.md`
  For upgrade-flow, cultivation-flow, system-flow, or power-ladder novels
- `references/politics.md`
  For faction, court, institution, empire, or war/power-shift novels
- `references/horror.md`
  For horror, folklore, taboo, ritual, or rules-based dread novels
- `references/multiverse.md`
  For multiworld, higher-realm, cross-boundary, or endgame-elevation novels
- `references/ensemble.md`
  For strong relationship, group-dynamic, or antagonist-function-heavy novels

Read only the references that actually fit the book.

## Per-Book Specificity Requirement

This skill must not stop at generic structure labels.

For every novel, explicitly identify `2 to 4` book-specific structural modules and explain how they shape the outline.

These must be real structural engines, not vague labels.

Bad examples:

- worldbuilding is rich
- pacing is fast
- the setting is big
- the protagonist grows a lot

Good examples:

- 外挂机制
- 升级路线
- 阵营博弈
- 规则恐怖系统
- 多世界扩边
- 终局位格抬升
- 关键关系回环
- 反派功能结构

For each identified book-specific module, answer:

- how it starts the main line
- how it expands in the middle
- where it becomes a stage boundary
- where it peaks
- whether it closes cleanly

If needed, create extra book-specific files or sections for these modules.

## Workflow

### 1. Enter the workspace and read existing files first

Before doing fresh analysis, inspect the current workspace and build a whole-book baseline from files that already exist.

Prioritize:

- `README.md`
- `工作状态-YYYY-MM-DD.md`
- protagonist final card
- protagonist index
- core system overview
- previous stage files
- existing topic summaries

The goal of step 1 is to answer:

- what this book already has
- what the protagonist layer already explains
- what is still missing from the outline layer

Do not skip this step when the workspace already exists.

### 2. Confirm the source and normalize the text

Identify the novel source first.

If this is a fresh project and the user wants durable results, initialize the workspace with:

- `scripts/init_outline_workspace.py --novel-name "<小说名>" --source "<原文路径>" [--protagonist "<主角名>"]`

If the source is `.txt` or messy plain text, use local conversion tools before analysis:

- `<repo-root>/text2markdown`

If the novel is very long, do not try to reason from raw memory.

Build a usable text layer first:

- chapter headings
- volume headings
- visible arc boundaries
- recurring place names
- recurring force names

### 3. Build the context layer before writing conclusions

Read enough of the text to answer the structural questions, not just the first chapters.

Prefer these anchors:

- opening hook
- first irreversible change
- first major expansion of the world
- middle-stage direction shift
- major climax pivot
- ending and final state

If the novel is chaptered, use chapter titles and checkpoints to reconstruct stages.

If the chapter numbering resets by volume, rely on content transitions rather than bare numbering.

If the workspace is fresh, the init script should already create starter files. Treat those as placeholders, not finished outputs.

### 4. Reuse the protagonist layer and convert it into outline understanding

Do not treat the protagonist as optional context.

Confirm:

- who the protagonist is
- what structural role they serve
- what their growth spine is
- whether the protagonist is the absolute main axis or one axis among several
- how the protagonist's route maps onto the whole-book structure

Important:

If the workspace already has a protagonist card, do not rewrite it unless necessary.

Instead:

- reuse it
- extract the protagonist's structural role from it
- convert protagonist knowledge into outline-layer understanding

If no durable protagonist summary exists, produce a concise one or point out that this common layer is still missing.

### 5. Split the whole book by stages, regions, time, and place

Before analyzing core supporting characters, first stabilize the whole-book map.

Produce the stage split before writing the high-level diagnosis.

Each stage should answer:

- where the stage starts and ends
- why it is a real stage boundary
- what the protagonist is mainly doing
- what the central conflict is
- what new structural layer opens there
- whether time shift, place shift, or both drive the boundary

Use one or both dimensions:

- growth / time stages
- map / location / organization stages

Also make time and place transitions explicit:

- which boundaries are mostly time-driven
- which are mostly place-driven
- which are caused by both

When useful, region or arena changes should be treated as a first-class structure layer, not as background scenery.

### 6. Analyze core supporting characters through stages and regions

Once stages and regions are stable, analyze supporting characters in that structure, not in the abstract.

Focus on:

- which supporting characters matter in which stage
- which region or arena makes them structurally important
- how they pressure, support, redirect, betray, or complete the protagonist's path

Do not treat this as a flat character list.

The goal is to explain:

- which supporting characters actually carry plot pressure
- which ones are only local figures
- which relationships are structure-bearing

### 7. Separate the main line from the side lines

Do not call everything a main plot.

Explicitly distinguish:

- core main line
- major side lines
- temporary incident lines
- structural bridge lines that only matter because they connect two larger arcs

For each important line, answer:

- what starts it
- what keeps it alive
- where it peaks
- whether it closes cleanly

### 8. Map conflicts, explosion points, and transitions

Always identify the highest-signal structural pressure points.

Minimum checkpoints to name:

- opening hook
- first major commitment
- first large expansion
- midpoint shift
- pre-climax compression
- climax
- ending settlement

For each turning point, explain:

- what explodes or changes
- why the old status quo cannot continue
- whether the payoff matches the setup

Also map:

- the core long-term conflict
- stage-level conflicts
- time jumps that change structure
- location changes that change rules, factions, or stakes

### 9. Diagnose common layers first, then extract book-specific traits

Do not jump too early to "what makes this book unique."

First make sure the common layers are actually covered:

- protagonist structure
- core supporting relations
- stages
- conflicts and explosion points
- time and place transitions
- climax and closure

Then identify `2 to 4` book-specific structural modules.

This order matters:

- common structure first
- specific structure second

because early "specificity" guesses are often just impressions.

### 10. Diagnose pacing and structural integrity

After the stage split and line map are stable, evaluate:

- whether the opening is strong enough
- whether the middle expands or drifts
- whether the plot upgrades are earned
- whether side lines support or dilute the book
- whether the climax is structurally prepared
- whether the ending closes enough of the book's promises

Be explicit when something is only partially closed.

### 11. Generate outputs and iterate against the checklist until the stop standard is met

Do not stop just because several files now exist.

The required loop is:

1. generate outputs
2. compare them against the checklist
3. fill the missing layers
4. repeat until the end condition is reached or a real blocker remains

End with a direct structural judgment only after this loop.

At minimum, state:

- strongest structural strengths
- biggest structural weaknesses
- whether the novel's outline is already self-consistent
- what should be revised first if the user wants to improve it
- which book-specific structural modules define this particular novel

Before closing the task, run the checklist in:

- [references/outline-analysis-checklist.md](references/outline-analysis-checklist.md)

If the task produced durable files in a workspace, also run:

- `scripts/validate_outline_outputs.py --workspace "<工作区路径>" --novel-name "<小说名>"`

Your final completion judgment should explicitly say whether the result is:

- `共性标准已覆盖`
- `共性标准部分覆盖`
- `单书特性已明确`
- `单书特性仍不足`

Also state:

- which layers came from existing workspace files
- which layers were produced in this run
- whether the stop condition was reached by checklist comparison rather than by impression

## Quality Bar

Do not stop at:

- a plot summary
- a chapter list
- a protagonist-only summary
- isolated theme talk without structure
- generic labels without book-specific modules

The output is only complete when it can explain the novel as a structure and show both:

- the common analysis layers every novel should have
- the specific structural engines unique to this book

## References

Read this file when you need the fixed analysis checklist and section expectations:

- [references/outline-analysis-checklist.md](references/outline-analysis-checklist.md)
- [references/progression.md](references/progression.md)
- [references/politics.md](references/politics.md)
- [references/horror.md](references/horror.md)
- [references/multiverse.md](references/multiverse.md)
- [references/ensemble.md](references/ensemble.md)
