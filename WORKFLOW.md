# Workflow Notes

This repository is meant to host the reusable workflow, not a mixed archive of private novels.

## Layers

1. `chapter-distillation`
   Compress chapters into structural skeletons.
2. `opening`
   Analyze the first three chapters for hook, promise, and launch quality.
3. `protagonist`
   Build the protagonist-centered knowledge backbone.
4. `outline`
   Judge stage structure, main/side lines, escalation, climax, and closure.
5. `highlight`
   Extract the highest-impact scenes and attraction mechanisms.

## Orchestrator

`novel-workspace-orchestrator` is the control layer. It can:

- read workspace state
- choose `fresh / extend-existing / repair-existing / validate-only`
- select the next layer
- call layer init scripts
- rerun validators
- update workspace and repo-level handoff files

## Typical Commands

Inspect a workspace:

```bash
python3 novel-workspace-orchestrator-skill/scripts/refresh_workspace_status.py \
  --workspace ./your-workspace \
  --novel-name "Your Novel"
```

Generate a gap report:

```bash
python3 novel-workspace-orchestrator-skill/scripts/workspace-gap-report.py \
  --workspace ./your-workspace
```

Ask for the next recommendation:

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_novel_workspace_pipeline.py \
  --workspace ./your-workspace
```

Execute the chosen layer:

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_novel_workspace_pipeline.py \
  --workspace ./your-workspace \
  --execute
```

Run regression after you add your own fixtures:

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_workspace_regression.py
```

## Publishing Rule

If this repo stays public, keep it focused on:

- skill definitions
- scripts
- validators
- small synthetic or permission-safe examples

Do not commit:

- full raw novel texts unless you have rights to publish them
- large generated workspace dumps
- private reading notes that are not part of the reusable workflow
