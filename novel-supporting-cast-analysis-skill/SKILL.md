---
name: novel-supporting-cast-analysis
description: Use when the user wants to automatically identify the ten most important supporting characters from full-cast extraction results and build durable supporting-cast analysis outputs for a novel workspace.
---

# novel-supporting-cast-analysis

Use this skill when the user wants a dedicated supporting-cast layer instead of stopping after protagonist analysis.

## When To Use

Use this skill when the user asks to:

- identify the most important supporting characters in a long novel
- build a Top 10 supporting-cast package from full-cast extraction artifacts
- analyze how supporting characters pressure the protagonist or carry stage transitions
- add a reusable supporting-cast layer into an existing novel workspace

## Core Rule

This layer depends on `work/merged/characters.json` or equivalent full-cast extraction artifacts.

That extraction must come from an AI extractor such as `openai` or `deepseek`.

Do not treat heuristic name extraction as acceptable upstream input for this layer.

## Output Goal

The target is not just “a list of names exists”.

This layer should leave behind:

- `<小说名>-重要配角Top10总表.md`
- `<小说名>-重要配角与主角关系图.md`
- `<小说名>-重要配角阶段作用分布.md`
- `supporting-cast/index.md`
- `supporting-cast/<角色名>-配角分析.md` for the Top 10 candidates
- a fresh `工作状态-YYYY-MM-DD.md`

## Workflow

### 1. Confirm upstream inputs

Read first:

- `work/merged/characters.json`
- `work/cards/index.md`
- `<主角名>-最终人物卡.md` when present
- `<小说名>-主角锚点与骨架.md` when present
- latest `工作状态-YYYY-MM-DD.md`

If the workspace only has heuristic extractions, stop and rebuild the full-cast layer with AI extraction first.

### 2. Run the init script

Run:

- `python3 scripts/init_supporting_cast_workspace.py --workspace "<工作区>" --novel-name "<小说名>" [--protagonist "<主角名>"]`

This script will:

- read merged full-cast artifacts
- score candidates
- exclude the protagonist from ranking
- pick Top 10 supporting characters
- write summary files and per-character analysis skeletons
- refresh `workspace-status.json` when the orchestrator helper exists

### 3. Review the ranking logic

The automatic Top 10 must be judged by structural importance, not by raw mention count alone.

Check whether the ranking roughly reflects:

- stage coverage
- relation density
- direct pressure on the protagonist
- force / faction representation
- repeated impact on turning points

If the ranking overweights one-off NPCs or noisy names, fix the upstream extraction or patch the ranking result.

### 4. Deepen the per-character analysis

For each Top 10 file, make sure the analysis answers:

- why this person enters Top 10 instead of being only “high frequency”
- what structural role they play
- in which stage they matter most
- how they change the protagonist’s path
- what pressure, mirror, alliance, betrayal, inheritance, or worldview function they carry

### 5. Validate

Run:

- `python3 scripts/validate_supporting_cast_outputs.py --workspace "<工作区>" --novel-name "<小说名>"`

The validator should pass only when the layer has:

- a direct Top 10 judgment
- usable protagonist-relation summaries
- stage-distribution judgment
- a real index and ten supporting files

## Quality Standard

Reject these weak outputs:

- “这个角色很重要”
- “戏份很多所以进 Top 10”
- “与主角关系密切”

Acceptable output must instead say:

- what exact role this person plays
- which stage they dominate
- how they alter conflict direction
- why they matter more than adjacent secondary characters
