# Novel Workspace Pipeline

A reusable workflow for turning long-novel analysis into a structured, replayable workspace instead of a one-off chat output.

## Why This Exists

Most novel analysis workflows break down in one of two ways:

- they produce a single summary that cannot be extended cleanly
- they create a pile of notes with no validation, no layering, and no stable next step

This repository takes a different approach. Each novel becomes its own workspace, and the workspace moves through a fixed analysis pipeline with validators, handoff files, an orchestration layer, and an explicit AI-writing step between scaffolding and final validation.

## What You Get

- A five-layer analysis model for long novels
- An orchestrator that inspects workspace state and recommends the next step
- Layer init scripts that scaffold missing outputs
- A documented AI fill step that turns scaffold files into real analysis
- Validators that distinguish real progress from placeholders
- Status, gap-report, and repair-plan generation
- Local helpers for `.txt -> .md` conversion and character extraction

## Pipeline Overview

```text
source text
  -> chapter-distillation
  -> opening
  -> protagonist
  -> outline
  -> highlight
  -> reusable workspace state + handoff files
```

### Layers

1. `chapter-distillation`
   Compress each chapter into structural skeletons and stage-change anchors.
2. `opening`
   Judge the first three chapters for hook, promise, launch quality, and chapter-end pull.
3. `protagonist`
   Build the protagonist-centered knowledge backbone.
4. `outline`
   Judge stage structure, conflict escalation, side lines, climax, and closure.
5. `highlight`
   Extract the most memorable scenes and the mechanisms that make them attractive.

### Orchestrator

`novel-workspace-orchestrator-skill` is the control layer. It can:

- inspect a workspace
- choose `fresh`, `extend-existing`, `repair-existing`, or `validate-only`
- recommend the next layer
- run layer init scripts
- refresh validators and handoff artifacts after init
- rerun validators
- write back status and handoff artifacts

## Repository Layout

```text
.
├── README.md
├── WORKFLOW.md
├── CONTRIBUTING.md
├── docs/
├── novel-workspace-orchestrator-skill/
├── novel-chapter-distillation-skill/
├── novel-opening-analysis-skill/
├── novel-protagonist-encyclopedia-skill/
├── novel-outline-analysis-skill/
├── novel-highlight-scenes-analysis-skill/
├── text2markdown/
└── novel-character-cards/
```

## Quick Start

### 1. Prepare a workspace

Create a directory for a novel and place source files under `source/`.

```text
your-workspace/
└── source/
    └── YourNovel.txt
```

### 2. Inspect the current state

```bash
python3 novel-workspace-orchestrator-skill/scripts/refresh_workspace_status.py \
  --workspace ./your-workspace \
  --novel-name "Your Novel"
```

### 3. Generate a gap report

```bash
python3 novel-workspace-orchestrator-skill/scripts/workspace-gap-report.py \
  --workspace ./your-workspace
```

### 4. Ask the orchestrator for the next move

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_novel_workspace_pipeline.py \
  --workspace ./your-workspace
```

### 5. Run layer init and refresh workflow state

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_novel_workspace_pipeline.py \
  --workspace ./your-workspace \
  --execute
```

What this actually does:

- runs the target layer's init/scaffolding command
- refreshes workspace status
- reruns validators when available
- writes handoff and gap-report artifacts

What this does not do by itself:

- read the novel like a human analyst
- fill analysis sections with evidence-backed conclusions
- convert placeholders into final content

### 6. Fill the target layer with AI

After `--execute`, open the generated context file and the scaffold files for the target layer, then use your AI assistant to write the actual analysis content.

The standard loop is:

1. `--execute` to scaffold the layer and refresh status.
2. Open `workspace-context-<layer>.md` plus the target layer files.
3. Ask the AI to read the source text and fill the target files with concrete evidence, names, events, and conclusions.
4. Rerun validators and inspect `workspace-gap-report.md`.
5. Repair anything still marked as placeholder-heavy or incomplete.

See [docs/ai-fill-step.md](docs/ai-fill-step.md) for the standard prompt shape and review loop.

Optional shortcut:

```bash
python3 novel-workspace-orchestrator-skill/scripts/prepare_ai_fill.py \
  --workspace ./your-workspace
```

This writes both `workspace-context-<layer>.md` and `workspace-ai-fill-<layer>.md` for the current target layer.

## Common Workflows

Initialize protagonist scaffolding only:

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_novel_workspace_pipeline.py \
  --workspace ./your-workspace \
  --target-layer protagonist \
  --execute
```

This initializes protagonist-layer files and refreshes reports. It does not replace the later AI fill pass.

Run validators and persist reports:

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_novel_workspace_pipeline.py \
  --workspace ./your-workspace \
  --persist-validator-reports
```

Run regression with your own fixtures:

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_workspace_regression.py \
  --cases ./docs/regression-cases.example.json
```

## Documentation

- [WORKFLOW.md](WORKFLOW.md)
  High-level operating model and workflow conventions.
- [LICENSE](LICENSE)
  MIT license for reuse, modification, and redistribution.
- [SECURITY.md](SECURITY.md)
  Security reporting policy for the public repository.
- [CHANGELOG.md](CHANGELOG.md)
  Release-oriented change history for the public repository.
- [docs/getting-started.md](docs/getting-started.md)
  First-run setup and a minimal end-to-end path.
- [docs/workspace-lifecycle.md](docs/workspace-lifecycle.md)
  How a workspace moves from empty to layered.
- [docs/ai-fill-step.md](docs/ai-fill-step.md)
  The standard scaffold -> AI fill -> validator repair loop.
- [docs/prompt-templates/](docs/prompt-templates)
  Layer-specific prompt starters for the AI fill pass.
- [docs/repository-map.md](docs/repository-map.md)
  What each top-level directory is responsible for.
- [docs/regression-cases.example.json](docs/regression-cases.example.json)
  Example shape for custom regression cases.
- [docs/github-promo-copy.md](docs/github-promo-copy.md)
  Reusable copy for GitHub, forums, and community posts.
- [fixtures/README.md](fixtures/README.md)
  Public synthetic workspaces for demos and regression.
- [CONTRIBUTING.md](CONTRIBUTING.md)
  Practical contribution rules for keeping the repo clean.

## Design Principles

- Prefer durable workspace state over one-shot summaries
- Treat validators as guardrails, not decorations
- Keep the AI writing step explicit instead of pretending scaffolding equals analysis
- Separate reusable workflow code from private novel content
- Make the next step explicit after every run
- Keep generated outputs out of the public repository by default

## Scope And Boundaries

This repository is the workflow layer. It is not intended to be:

- a public dump of full raw novels
- a giant archive of generated workspace artifacts
- a fully autonomous writing agent
- a promise that `--execute` alone completes the analysis layer

It is best understood as a structured analysis pipeline with orchestration, validation, and repeatable workspace management.
