# AI Fill Step

## Why This Step Exists

This workflow is not a fully autonomous analysis engine.

The scripts are responsible for:

- scaffolding files
- collecting status
- building bridge context
- running validators
- writing handoff artifacts

The AI is responsible for:

- reading source text and upstream workspace outputs
- deciding what the current layer actually concludes
- replacing placeholders with concrete, evidence-backed content
- revising weak sections until validators and human judgment both pass

Without this step, the workflow only has structure. It does not yet have usable analysis.

## Standard Loop

Use this loop whenever you advance or repair a layer.

1. Run `run_novel_workspace_pipeline.py --execute` for the target layer.
2. Open `workspace-context-<layer>.md`.
3. Open the scaffold files created for that layer.
4. Read the source text or relevant source ranges.
5. Ask the AI to fill the target files with concrete analysis.
6. Rerun validators and inspect `workspace-gap-report.md`.
7. Repair any remaining placeholder-heavy or validator-failing sections.

## What Good AI Fill Looks Like

- cites concrete names, events, stages, conflicts, or chapter facts
- writes conclusions, not just meta-commentary
- reuses existing lower-layer outputs instead of rebuilding them from scratch
- leaves the workspace in a state that the next operator can continue from

## What Bad AI Fill Looks Like

- repeats the scaffold headings with no real content
- writes generic statements that could fit any novel
- ignores `workspace-context-<layer>.md`
- skips source reading and relies on memory
- stops after init and treats validator failures as unexpected

## Recommended Prompt Shape

Use a prompt in this shape with your AI assistant:

```text
You are filling the `<target-layer>` layer of a novel workspace.

Read these first:
- `workspace-context-<target-layer>.md`
- the target layer scaffold files
- the relevant source text or source ranges

Your job:
- replace placeholders with concrete analysis
- reuse upstream layer facts instead of rebuilding them
- write evidence-backed conclusions, not generic commentary
- preserve existing valid content

Before finishing:
- check the target files for placeholders
- make sure the required judgment fields are actually filled
- leave the workspace ready for validator rerun
```

## Operational Rule

Treat `--execute` as the beginning of the layer-writing loop, not the end of it.
