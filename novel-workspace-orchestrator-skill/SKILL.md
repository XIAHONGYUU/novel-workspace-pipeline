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
- `novel-supporting-cast-analysis`
- `novel-outline-analysis`
- `novel-highlight-scenes-analysis`

Instead, it coordinates them.

## Core Layers

Treat the workspace as a six-layer system:

1. `chapter-distillation`
2. `opening`
3. `protagonist`
4. `supporting-cast`
5. `outline`
6. `highlight`

Default interpretation:

- chapter distillation fixes the source-facing backbone
- opening fixes the first-three-chapter promise
- protagonist fixes the character-centered knowledge backbone
- supporting-cast fixes the Top 10 secondary-character pressure map
- outline fixes whole-book structure
- highlight fixes the strongest attraction layer

## Default Order

Unless the workspace state gives a strong reason to do otherwise, use this default order:

1. `novel-chapter-distillation`
2. `novel-opening-analysis`
3. `novel-protagonist-encyclopedia`
4. `novel-supporting-cast-analysis`
5. `novel-outline-analysis`
6. `novel-highlight-scenes-analysis`

Reasoning:

- long novels drift without a chapter skeleton
- opening should usually come before deeper interpretation because it fixes the book's entry promise
- protagonist and supporting-cast become safer once the opening judgment exists
- outline becomes safer once protagonist and supporting-cast context already exist
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
- **rerun quality gate** before closing — a layer is not truly "done" until both validator AND quality gate pass
- a quality gate score ≥ 75 qualifies as "quality pass"

### `validate-only`

Use when the user wants an audit without content rewriting.

Rules:

- inspect the workspace
- determine completed vs incomplete layers
- report the next best step
- do not rewrite content unless the user changes scope

## Routing Logic

When this skill triggers, decide in this order:

### 0. 核心理念：这不是自动化流水线，而是 AI 指挥协作系统

**Workflow 从设计之初就不是一个全自动闭环。** 它是一个"脚本管理状态 + AI 生成内容"的人机协作系统。

| 角色 | 负责 | 不负责 | 为什么这样设计 |
|---|---|---|---|
| init 脚本 | 创建目录、生成文件框架、搭好字段模板 | 不读原文、不蒸馏内容、不写分析 | 脚本无法理解小说——能理解小说的只有 AI |
| validator 脚本 | 检查文件存在/长度/关键词/占位符 | 不判断分析质量 | 规则可编码，但"这个分析写得好不好"不可编码 |
| AI（你） | 读原文、理解结构、填框架、写具体分析 | 不能凭记忆编造、不能跳过原文 | 这是唯一能做内容生成的环节 |

**init → validator → AI 填充 → validator 通过的循环是设计意图，不是 bug。**

这个循环的本质是一个**质量闸门**：
- init 生成占位符（"阶段一：待定"）→ 这是正常的起点
- validator 报告 `keywords_missing` → 这是在告诉 AI "你还没填"
- AI 读原文并填充 → 这是 AI 的职责
- validator 再次检查 → 这是在确认"填到位了"
- 如果还没通过 → 继续填充，直到通过

**关键原则**：脚本不会替你写内容——也设计上不应该替你写。validator 不会说"写得不好"——它只说"缺了关键词"或"还有占位符"。内容质量的判断（"这个分析有深度吗？""这个结论有证据吗？"）是 AI 的职责，不是脚本的职责。

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
- else if no supporting-cast layer exists, choose `supporting-cast`
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
- `supporting-cast` -> `novel-supporting-cast-analysis`
- `outline` -> `novel-outline-analysis`
- `highlight` -> `novel-highlight-scenes-analysis`

Read the target skill before executing the target layer.

## 标准执行流程

当一个层被选中推进时，AI 应按以下顺序执行：

### Step 1：运行 init 脚本

```bash
python3 <对应层>/scripts/init_*_workspace.py --workspace <项目名> ...
```

init 脚本会生成文件框架和字段模板。**此时文件内容为空壳或占位符——这是正常的。**

### Step 2：读取上下文文件

Pipeline 在 `--execute` 后已经自动生成了跨层桥接上下文文件：

```
<项目名>/workspace-context-<目标层>.md
```

**直接打开这个文件**。它聚合了底层所有产物的关键信息，你不需要去翻七八个分散文件。读完这个文件后，你对整书结构、主角身份、已有分析结论就有一个完整的底图。

如果上下文文件不存在（首次 init 时），则按对应层 SKILL.md 中的"开始前必读文件"列表逐个打开。

### Step 3：阅读原文并填充内容

**这是最关键的一步，也是区分"占位符"和"可用产物"的分水岭。**

AI 必须：
- 打开原文，阅读相关章节
- 将具体信息（人名、事件、章节号、时间线、功法名称）填入框架
- 避免写"这个很重要"式的元分析——写具体内容而非内容的重要性

### Step 4：自检

对照对应层的 SKILL.md 中的质量标准（"禁止的泛化话术" vs "正确的分析写法"）做一轮自检。

### Step 5：运行 validator

```bash
python3 <对应层>/scripts/validate_*_outputs.py --workspace <项目名> --novel-name <小说名>
```

观察 `keywords_missing`、`placeholder_detected`、`too_short` 等报错，针对性修正。

### Step 6：写回状态

运行总控 pipeline 写回所有状态文件：

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_novel_workspace_pipeline.py --workspace <项目名> --persist-validator-reports
```

## 跨层桥接规则

当推进一个"上层"时，必须先读取"下层"已建立的产物作为上下文。

### 桥接的本质

脚本无法控制 AI 读什么文件。桥接的有效性取决于**AI 是否能通过稳定的文件名找到并打开正确文件**。因此，桥接的实现方式是：

1. **文件名可预测**——每个产物文件的命名规则固定（`<小说名>-xxx.md` / `<主角名>-xxx.md`）
2. **SKILL.md 直接列出文件名**——不写"reuse protagonist context"，写"打开 `<主角名>-最终人物卡.md`"
3. **AI 按表索骥**——读到文件名后自己打开文件读取

### 各层的必读文件清单

| 当前层 | 必读文件（按文件名模板） | 用途 |
|---|---|---|
| opening | `<主角名>-最终人物卡.md`、`<小说名>-主角锚点与骨架.md`、`<小说名>-整书粗阶段划分.md` | 了解主角定位和全书阶段背景 |
| protagonist | `<小说名>-黄金前三章总判断.md`（如有）、`<小说名>-章节蒸馏骨架.md`（如有） | 开篇判断和原文校验底稿 |
| supporting-cast | `work/merged/characters.json`、`work/cards/index.md`、`<主角名>-最终人物卡.md`（如有） | 以 AI 全角色抽取为基础筛选 Top10 配角 |
| outline | `<小说名>-主角锚点与骨架.md`、`<主角名>-最终人物卡.md`、`<主角名>-词条总索引.md`、`<小说名>-重要配角Top10总表.md`（如有）、`<小说名>-黄金前三章总判断.md`（如有） | 人物主梁、配角压力与入口判断 |
| highlight | `<小说名>-整书粗阶段划分.md`、`<小说名>-主线支线与冲突地图.md`（如有）、`<小说名>-重要配角Top10总表.md`（如有）、`<主角名>-最终人物卡.md` | 阶段位置、结构背景和人物上下文 |

### build_layer_context.py 的作用

此脚本将跨层信息压缩到一个文件中，减少 AI 需要打开的文件数量：

```bash
python3 novel-workspace-orchestrator-skill/scripts/build_layer_context.py --workspace <项目名> --target-layer <目标层>
```

生成的 `workspace-context-<layer>.md` 不是控制 AI 的指令，而是**减少 AI 查找负担的信息聚合文件**。建议在 init 之后自动运行本脚本。

## Default Output Goal

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

If `--execute` or `--execute-all` stalls, prefer this stop rule:

- write back `workspace-status.json`, `工作状态-YYYY-MM-DD.md`, and `工作区流程判断报告.md`
- mark `human_escalation` with the blocked layer, reason, and resume file
- stop silently after handoff instead of pretending the loop closed

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
- 再决定 opening / protagonist / supporting-cast / outline / highlight 的推进顺序
- 每推进一层都尽量复用已有结果
- 最后给出当前做到哪一层、下一层建议是什么
```

### Example 3: Validation and routing only

```text
请使用 `novel-workspace-orchestrator` skill 只检查当前工作区，不直接重写内容。

要求：
- 判断六层里哪些已经完成
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
