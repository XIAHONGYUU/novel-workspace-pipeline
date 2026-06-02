---
name: novel-supporting-cast-analysis
description: Use when the user wants to identify the ten most important supporting characters from AI-generated character cards, rerank them with an AI judgment pass, and expand each chosen supporting character into a protagonist-style durable card package.
---

# novel-supporting-cast-analysis

Use this skill when the user wants a real supporting-cast layer instead of stopping at protagonist analysis or raw full-cast extraction.

## When To Use

Use this skill when the user asks to:

- identify the ten most important supporting characters in a long novel
- review `work/cards/*.md` and decide which supporting characters truly deserve Top10 treatment
- add a reusable supporting-cast layer into an existing novel workspace
- expand important supporting characters into durable cards that feel closer to a protagonist card than to a raw extraction dump

## Core Rule

This layer is now `card-first`, not `merged-json-first`.

Primary input:

- `work/cards/index.md`
- `work/cards/<角色名>.md`

Auxiliary evidence:

- `work/merged/characters.json`
- protagonist files
- stage / outline files

Important:

- do not rank Top10 only from `mention_count`
- do not treat heuristic name extraction as acceptable upstream input
- do not stop after a formula picks ten names

The final Top10 must be confirmed by an AI judgment pass that reads the candidate cards in context.

## Output Goal

The target is not just “a list of names exists”.

This layer should leave behind:

- `<小说名>-重要配角Top10总表.md`
- `<小说名>-重要配角AI复核结论.md`
- `<小说名>-重要配角与主角关系图.md`
- `<小说名>-重要配角阶段作用分布.md`
- `supporting-cast/index.md`
- `supporting-cast/Top10候选池初评.md`
- `supporting-cast/<角色名>-配角分析.md` for the final Top10
- a fresh `工作状态-YYYY-MM-DD.md`

## Workflow

### 1. Confirm upstream inputs

Read first:

- `work/cards/index.md`
- the most likely Top20 candidate cards under `work/cards/`
- `work/merged/characters.json` when present
- `<主角名>-最终人物卡.md` when present
- `<小说名>-主角锚点与骨架.md` when present
- `<小说名>-整书粗阶段划分.md` when present
- latest `工作状态-YYYY-MM-DD.md`

If the workspace does not have usable AI-generated `work/cards/*.md`, stop and rebuild the card layer first.

### 2. Run the init script

Run:

- `python3 scripts/init_supporting_cast_workspace.py --workspace "<工作区>" --novel-name "<小说名>" [--protagonist "<主角名>"]`

This script will:

- read `work/cards/*.md` as the primary ranking surface
- use `work/merged/characters.json` only as auxiliary evidence
- exclude the protagonist from ranking
- build a candidate pool and initial card-first ranking
- write `Top10候选池初评`
- write AI review scaffolds
- write protagonist-style supporting-card scaffolds for the current Top10
- refresh `workspace-status.json` when the orchestrator helper exists

Important:

The init script only creates an initial candidate pool and expansion scaffolds.

It does **not** complete the AI rerank or the final card expansion by itself.

### 3. Review the candidate pool from cards, not from raw counts

Use the candidate pool to judge:

- who repeatedly changes the protagonist’s path
- who carries stage transitions
- who represents a force, institution, worldview, or relationship pressure that the book truly depends on
- who is only high-frequency but structurally replaceable

The ranking should be based on card-level structure such as:

- relationship density
- stage / event coverage
- role in the protagonist’s route
- force / faction importance
- repeated pressure on turning points

Raw counts are only supporting evidence.

### 4. Run an AI rerank pass before finalizing Top10

Before treating the Top10 as final, perform a real AI judgment pass.

That pass should answer:

- which 10 names truly deserve final expansion
- which names should be dropped even if they scored high initially
- which near-miss candidates should replace weak initial picks
- why each final Top10 character matters more than adjacent candidates

Write the conclusion into:

- `<小说名>-重要配角AI复核结论.md`

Do not leave this file as a placeholder.

### 5. Expand the final Top10 with protagonist-style cards

Once the final Top10 is confirmed, expand each chosen supporting character using a structure close to the protagonist card.

The supporting card should usually cover:

- basic identity
- identity overview
- identity / stage change
- relationship to the protagonist
- key relationships
- ability / resource structure
- key events
- faction position
- activity range
- stage summary
- character-feature summary
- why this person enters Top10
- final conclusion

The expansion standard is:

- not a raw extraction dump
- not only a bullet list of traits
- not only “this character is important”

It should feel like a durable role card.

### 6. Validate

Run:

- `python3 scripts/validate_supporting_cast_outputs.py --workspace "<工作区>" --novel-name "<小说名>"`

The validator should pass only when the layer has:

- a usable candidate-pool file
- a real AI rerank conclusion
- a Top10 table that reflects final keep / drop judgments
- usable protagonist-relation summaries
- stage-distribution judgment
- a real index and ten expanded supporting files

## Quality Standard

Reject these weak outputs:

- “这个角色很重要”
- “戏份很多所以进 Top 10”
- “与主角关系密切”
- “先按自动排序保留”
- “这张卡已经有很多字段了”

Acceptable output must instead say:

- what exact structural role this person plays
- which stage they dominate or redirect
- how they alter the protagonist’s path
- why they matter more than adjacent secondary characters
- what is already stable and what still needs deeper vertical expansion

## Success Criterion

This skill is successful only when it completes the chain below:

1. `cards` 初评
2. AI 复核定榜
3. Top10 配角扩展卡落地
4. supporting-cast layer validator passes

It is not successful merely because:

- a formula produced ten names
- some skeleton files were created
- the per-character files copied card bullets into a new folder
