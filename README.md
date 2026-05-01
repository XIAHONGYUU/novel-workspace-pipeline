# Novel Workspace Pipeline

A workflow-oriented repository for long-novel analysis.

This public repo packages the reusable parts of the system:

- `novel-workspace-orchestrator-skill`
- `novel-chapter-distillation-skill`
- `novel-opening-analysis-skill`
- `novel-protagonist-encyclopedia-skill`
- `novel-outline-analysis-skill`
- `novel-highlight-scenes-analysis-skill`
- `text2markdown`
- `novel-character-cards`

It intentionally excludes private novel workspaces, raw source texts, and large generated artifacts.

## What This Repo Does

The pipeline treats each novel as its own workspace and moves it through layered analysis:

1. `chapter-distillation`
2. `opening`
3. `protagonist`
4. `outline`
5. `highlight`

The orchestrator can:

- inspect current workspace state
- recommend the next layer
- initialize missing layers
- rerun validators
- write back status and handoff files

## Repository Layout

- `WORKFLOW.md`
  Human-facing workflow notes and operating conventions.
- `CURRENT_STATUS.md`
  Optional repo-level pointer file. The orchestrator can update it.
- `novel-workspace-orchestrator-skill/`
  Pipeline orchestration, status collection, gap reports, repair plans, and regression harness.
- `novel-*-skill/`
  Layer-specific init scripts, validators, and references.
- `text2markdown/`
  Local `.txt` to `.md` conversion helper.
- `novel-character-cards/`
  Character extraction pipeline used by the protagonist layer bootstrap path.

## Quick Start

Create a workspace status snapshot:

```bash
python3 novel-workspace-orchestrator-skill/scripts/refresh_workspace_status.py \
  --workspace ./your-workspace \
  --novel-name "Your Novel"
```

Inspect the current gap:

```bash
python3 novel-workspace-orchestrator-skill/scripts/workspace-gap-report.py \
  --workspace ./your-workspace
```

Let the orchestrator recommend the next step:

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_novel_workspace_pipeline.py \
  --workspace ./your-workspace
```

Execute the recommended layer init:

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_novel_workspace_pipeline.py \
  --workspace ./your-workspace \
  --execute
```

## Notes

- This repo is the workflow layer, not a public dump of finished novel projects.
- Put your raw novel source files under each workspace's `source/` directory.
- Generated workspace outputs are ignored by default in `.gitignore`.
- The bundled regression cases file is empty by design. Add your own stable fixtures before using `run_workspace_regression.py`.
