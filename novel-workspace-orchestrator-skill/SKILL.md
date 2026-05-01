---
name: novel-workspace-orchestrator
description: Coordinate a novel workspace across chapter distillation, opening analysis, protagonist encyclopedia, outline analysis, and highlight-scene analysis. Use when the user wants one entry point that inspects the current workspace, decides what layer should run next, chooses fresh or extend-existing or repair-existing or validate-only mode, and writes back handoff state instead of manually picking each skill one by one.
---

# Novel Workspace Orchestrator

Use this skill when the user wants a single controller for a novel workspace rather than asking for one analysis layer in isolation.

This skill is not a sixth analysis layer.

Its job is to:

- inspect the workspace first
- decide which layer should run next
- choose the right mode
- route work to the correct lower-layer skill
- write back status, validation result, and next-step handoff

It should not replace:

- `novel-chapter-distillation`
- `novel-opening-analysis`
- `novel-protagonist-encyclopedia`
- `novel-outline-analysis`
- `novel-highlight-scenes-analysis`

Instead, it coordinates them.

## Core Layers

Treat the workspace as a five-layer system:

1. `chapter-distillation`
2. `opening`
3. `protagonist`
4. `outline`
5. `highlight`

Default interpretation:

- chapter distillation fixes the source-facing backbone
- opening fixes the first-three-chapter promise
- protagonist fixes the character-centered knowledge backbone
- outline fixes whole-book structure
- highlight fixes the strongest attraction layer

## Default Order

Unless the workspace state gives a strong reason to do otherwise, use this default order:

1. `novel-chapter-distillation`
2. `novel-opening-analysis`
3. `novel-protagonist-encyclopedia`
4. `novel-outline-analysis`
5. `novel-highlight-scenes-analysis`

Reasoning:

- long novels drift without a chapter skeleton
- opening should usually come before deeper interpretation because it fixes the book's entry promise
- protagonist and outline become safer once the opening judgment exists
- highlight analysis works best after structure and character context are already stable

## Important Exception Rules

Do not force the default order blindly.

Use these exceptions:

- if the user explicitly asks for only one layer, respect that scope
- if a later layer already exists and is clearly valid, do not rebuild it just because an earlier layer is missing
- if the workspace already has protagonist outputs but lacks opening outputs, usually add opening next without rewriting protagonist files
- if the workspace already has outline outputs and the user only wants highlight analysis, go directly to highlight
- if a layer exists but failed validation, prioritize `repair-existing` for that layer before starting a brand-new later layer
- if the novel is short and the user wants only an opening diagnosis, chapter distillation is optional

## Working Modes

### `fresh`

Use when no durable workspace exists yet.

Rules:

- initialize the workspace
- detect source files
- decide whether chapter distillation should run first
- do not stop after scaffolding if the user asked for real progress

### `extend-existing`

Use when the workspace already exists and the goal is to add one or more missing layers.

Rules:

- read existing files first
- reuse valid context
- only add the missing layer or layers
- preserve stable older outputs

### `repair-existing`

Use when a layer already exists but is incomplete, placeholder-heavy, or contradicted by its validator report.

Rules:

- patch the weak layer first
- do not rewrite unrelated valid layers
- rerun the relevant validator before closing

### `validate-only`

Use when the user wants an audit without content rewriting.

Rules:

- inspect the workspace
- determine completed vs incomplete layers
- report the next best step
- do not rewrite content unless the user changes scope

## Routing Logic

When this skill triggers, decide in this order:

### 1. Inspect the workspace

Read at minimum:

- `README.md`
- `CURRENT_STATUS.md` when the workspace is part of the current repository workflow
- latest `工作状态-YYYY-MM-DD.md`
- the project index or protagonist index when present

Then identify:

- source file availability
- which layers already exist
- whether any layer has a validator report
- whether any layer looks placeholder-heavy

### 2. Determine the current mode

Use:

- `fresh` when the workspace does not meaningfully exist
- `extend-existing` when the workspace exists and is missing layers
- `repair-existing` when files exist but are weak
- `validate-only` when the user asked only for checking

### 3. Pick the next layer

Default next-layer rules:

- if no chapter skeleton exists and the novel is long, choose `chapter-distillation`
- else if no opening layer exists, choose `opening`
- else if no protagonist layer exists, choose `protagonist`
- else if no outline layer exists, choose `outline`
- else if no highlight layer exists, choose `highlight`
- else choose `validate-only` plus handoff update

Repair override:

- if any existing layer has a failed validator or obvious placeholders, repair that layer before adding a later layer

### 4. Route to the right lower-layer skill

Use the matching lower-layer skill instructions instead of improvising a replacement workflow:

- `chapter-distillation` -> `novel-chapter-distillation`
- `opening` -> `novel-opening-analysis`
- `protagonist` -> `novel-protagonist-encyclopedia`
- `outline` -> `novel-outline-analysis`
- `highlight` -> `novel-highlight-scenes-analysis`

Read the target skill before executing the target layer.

## Default Output Goal

Unless the user narrows the scope, aim to leave the workspace in a clearer, more resumable state.

That means:

- the next layer has been correctly chosen
- the right mode was used
- relevant validator checks were run when available
- the latest handoff state was written back
- the user can resume without rereading the whole project from scratch

Prefer durable outputs such as:

- updated layer files
- validator reports
- latest `工作状态-YYYY-MM-DD.md`
- `CURRENT_STATUS.md` when the repo-level pointer should change
- `workspace-status.json`
- `workspace-gap-report.md`
- `workspace-repair-plan.md` when the workspace should enter `repair-existing`
- `工作区流程判断报告.md`

## Scripts

Use the bundled scripts when you want repeatable routing and judgment instead of ad hoc inspection.

- `scripts/refresh_workspace_status.py`
  Refresh or print `workspace-status.json` for the current workspace.
- `scripts/workspace-gap-report.py`
  Generate a markdown gap report plus a fresh status snapshot.
- `scripts/build_layer_context.py`
  Build reusable context for a target layer from the existing workspace.
- `scripts/run_novel_workspace_pipeline.py`
  Produce a top-level pipeline decision, optional context file, and orchestration report.
- `scripts/run_workspace_regression.py`
  Run the fixed seven-workspace regression suite and check that routing decisions did not drift.

These scripts are meant to support this skill, not replace the lower-layer analysis skills.

## Chinese Prompt Examples

### Example 1: Full orchestration on an existing workspace

```text
请使用 `novel-workspace-orchestrator` skill 检查这个小说工作区，判断现在已经完成了哪些层、还缺哪些层，并按默认顺序决定下一步该跑哪个 skill。

要求：
- 先读工作区，不要凭记忆判断
- 如果已有层成立，就复用，不要重写
- 如果某层已经存在但不达标，优先修这一层
- 跑完后把最新工作状态写回工作区
```

### Example 2: Fresh project kickoff

```text
请使用 `novel-workspace-orchestrator` skill 为《<小说名>》建立工作区，并按默认顺序推进。

要求：
- 先判断是否应该先做章节蒸馏
- 再决定 opening / protagonist / outline / highlight 的推进顺序
- 每推进一层都尽量复用已有结果
- 最后给出当前做到哪一层、下一层建议是什么
```

### Example 3: Validation and routing only

```text
请使用 `novel-workspace-orchestrator` skill 只检查当前工作区，不直接重写内容。

要求：
- 判断五层里哪些已经完成
- 哪些层还没做
- 哪些层虽然有文件但仍不达标
- 明确告诉我下一步最该跑哪个 skill
```

## Minimal Handoff Standard

Before closing, make sure the workspace now answers:

- current mode used
- current layer completed or repaired
- next recommended layer
- whether validator passed or still failed
- what the user should read first when resuming

Do not close with only a vague statement like “workspace updated”.

## References

Read this checklist when you need a fast completion and routing audit:

- [references/orchestrator-checklist.md](references/orchestrator-checklist.md)

Read this schema note when you want the machine-readable state fields:

- [references/workspace-status-schema.md](references/workspace-status-schema.md)
