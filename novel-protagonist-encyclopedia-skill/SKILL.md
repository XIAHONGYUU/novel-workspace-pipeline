---
name: novel-protagonist-encyclopedia
description: Use when the user wants to process a long novel into a protagonist-centered encyclopedia instead of a full cast index. This skill should drive the project past bootstrap and, by default, toward skeleton-complete or system-closed protagonist knowledge outputs.
---

# novel-protagonist-encyclopedia

Use this skill when the user wants to turn a novel into a protagonist-centered knowledge system rather than a flat character list.

## When To Use

Use this skill when the user asks to:

- build a protagonist-centered encyclopedia for a novel
- summarize a long novel around the protagonist's structure
- create protagonist cards, tiered lexicon files, and structural summaries
- process a novel by chunk distillation first, then build the protagonist skeleton
- judge whether a novel project has reached `骨架完成` or `体系闭环完成`
- continue an existing novel workspace until the structure is actually closed

## Default Target

This skill must not stop at bootstrap unless the user explicitly narrows the scope.

Default behavior:

- if the user asks to start a new novel project, aim for at least `骨架完成`
- if the source, focus results, and context are already sufficient, continue to `体系闭环完成（主干闭环版）`
- if the workspace is already skeleton-complete, continue with core overview, full-book essence summary, key L2 files, and completion judgment

In other words:

This skill is successful only when it advances or closes the protagonist system, not when it merely creates folders and first-pass artifacts.

## Output Goal

The target state is not just "some notes exist". The target is a reusable structure with:

- protagonist anchor file
- protagonist final card
- protagonist lexicon index
- stable L1 lexicon files
- key L2 lexicon files
- core system overview
- full-book essence summary
- closure checklist status
- explicit `骨架完成 / 体系闭环完成` judgment

Important:

This skill is not a full-cast card skill.

If other tools are used during the process, they are only allowed to serve:

- chunk distillation
- protagonist-candidate diagnosis
- focus tracking

They are not the product goal.

## Non-Goal Warnings

Do not treat these as final success conditions:

- many character files were generated
- a merged character list exists
- `work/cards/index.md` exists
- the heuristic extractor produced lots of names
- the workspace was initialized successfully

Those are only diagnostic or helper layers.

## Workflow

### 1. Initialize workspace

Run:

- `python3 scripts/init_workspace.py --novel-name "<小说名>" --source "<原始文本路径>"`

This creates:

- workspace directories
- startup checklist
- stage-outline file
- protagonist skeleton placeholder
- README
- copied source text
- Markdown-converted source when the input is `.txt`
- first-pass `novel-character-cards` pipeline artifacts
- optional focus-tracking artifacts when `--focus-name` is provided
- optional closure placeholders when `--focus-name` is provided

### 2. Bootstrap the context layer immediately

The default script now does the first-pass bootstrap automatically:

- copy source into `source/`
- convert `.txt` to Markdown
- run local extraction utilities into `work/` only as an auxiliary context layer
- optionally run a focus pipeline into `focus-<主角名>/`

Use `--skip-bootstrap` only if you intentionally want folders and templates without the first pass.

### 3. Build the context layer first

Do not start from the protagonist card.

After bootstrap, inspect:

- `work/chunks/`
- `work/extractions/`
- `work/merged/characters.json`
- `work/cards/index.md`
- `focus-<主角名>/focus/` when focus tracking was enabled

Treat these as diagnostics, not as the final product.

The first-pass outcome must answer:

- who is most likely the protagonist
- whether the automatic result is noisy
- whether focus should be run immediately

Prefer existing local tools:

- `<repo-root>/text2markdown`
- `<repo-root>/novel-character-cards`

But do not let `novel-character-cards` redefine the workflow into a full-cast project.

### 4. Create coarse book stages during first chunk pass

On the first chunk-distillation pass, always produce a coarse stage split for the whole book.

Use one or both dimensions:

- time / growth stages
- location / map stages

The stage file should answer:

- where each stage starts and ends
- why the split exists
- what the protagonist is mainly doing in that stage
- what the main place / structure / conflict is

### 5. Build protagonist anchors and final card

Stabilize:

- protagonist name
- aliases
- masks / stage identities
- recurring titles

Then write the protagonist final card from the distilled context layer, not from loose memory.

The final card must pass a field check. It should include at least:

- basic identity
- identity change
- key relationships
- power structure
- key items
- key events
- activity range
- force / organization affiliation
- stage summary

Do not detour into full-cast cleanup before the protagonist skeleton is stable.

### 6. Build L1 lexicon files

Default L1 slots to check first:

- identity change
- core ability / craft / cheat
- combat style
- cultivation / level / higher route
- core resource line
- world structure
- forces and entanglements
- key relationship network
- city / region trajectory

Only keep the slots that truly fit the novel.

Important:

Distinguish between:

- `第一批核心一级词条已齐`
- `一级词条全集已齐`

Do not mark L1 as complete merely because a few files exist. Only mark it complete when the novel's truly applicable core slots are covered.

### 7. Build the index before over-expanding

Once the L1 structure is stable, build the protagonist index.

The index must show:

- entry files
- L1 files
- L2 files
- current completion state
- recommended reading order
- explicit `当前判定：骨架完成 / 未完成`
- explicit `当前判定：体系闭环完成 / 未完成`

If a completion state is marked achieved, provide reasons.

### 8. Close the structure before deep-diving

Before continuing with broad L2 expansion, write:

- core system overview
- full-book essence summary

These two files are mandatory for reaching `体系闭环完成`.

### 9. Choose L2 files selectively

Prefer these L2 patterns first:

- high-density pivots
- stage transition layers
- grouped thematic clusters

Common L2 candidates:

- key stages
- key identity nodes
- key form changes
- key higher-level opponents
- key organizations
- key abnormal spaces
- key experiments / breakthroughs
- key map stages

For the first batch of L2 files, prioritize structure-closing nodes:

- opening foundation nodes
- core weapon / core resource nodes
- mid-stage key cultivation results
- high-level structural bridges
- endgame problem nodes

Do not keep expanding sideways if new files only repeat existing structure.

### 10. Finish with a standardized closure judgment

Do not stop after L2 creation without writing the closure judgment.

At the end, explicitly decide:

- has this project reached `骨架完成`
- has this project reached `体系闭环完成`

Also clarify:

- whether the closure is only "主干闭环版"
- what remaining work, if any, is now best treated as vertical deepening rather than missing core structure

## Completion States

### 骨架完成

Treat the novel as skeleton-complete when most of these are true:

- chunk distillation is done
- coarse stage split is done
- protagonist anchors are stable
- protagonist final card is done
- L1 lexicon files are stable
- protagonist index is usable

### 体系闭环完成

Treat the novel as system-closed when most of these are true:

- `骨架完成`
- core system overview is done
- full-book essence summary is done
- key L2 files are done
- the files explain each other instead of merely accumulating

Important clarification:

`体系闭环完成` means the main structure is self-explanatory.

It does not mean:

- every possible L2 topic has been exhausted
- all details have been fully expanded

After closure, the default next move is vertical deepening, not horizontal sprawl.

## Stop Rule

If the project already explains:

- who the protagonist is
- what keeps the protagonist growing
- where the protagonist undergoes qualitative change
- what world structure the protagonist enters
- how the main files explain each other

then stop broadening and either:

- close the structure
- or deep-dive one high-value L2 cluster

## Recommended Close-Out Order

Use this order unless the user explicitly redirects:

1. protagonist anchors
2. protagonist final card
3. coarse stage split
4. L1 lexicon files
5. protagonist index
6. core system overview
7. full-book essence summary
8. first-batch L2 files
9. final completion judgment

This order reduces false completion signals and keeps checklist state aligned with real structure quality.

## Success Criterion

This skill is successful only when it advances the checklist toward protagonist-system closure.

It is not successful merely because it created:

- many character files
- a large merged character list
- a noisy card index
- only the first-pass workspace

## Script

- `python3 scripts/init_workspace.py --novel-name "<小说名>" [--source "<原始文本路径>"]`
- `python3 scripts/init_workspace.py --novel-name "<小说名>" --source "<原始文本路径>" [--focus-name "<主角名>"] [--focus-alias "<别名>"] [--limit-chunks N] [--extractor heuristic|openai]`

This is the default executable entry for starting a new novel project with this skill.
