# Getting Started

## Prerequisites

- Python 3.10+
- A local clone of this repository
- A novel workspace directory with a `source/` folder

## Minimal Workspace

```text
my-novel/
└── source/
    └── MyNovel.txt
```

The workflow expects each novel to live in its own workspace directory.

## First Commands

Refresh workspace status:

```bash
python3 novel-workspace-orchestrator-skill/scripts/refresh_workspace_status.py \
  --workspace ./my-novel \
  --novel-name "My Novel"
```

Generate a gap report:

```bash
python3 novel-workspace-orchestrator-skill/scripts/workspace-gap-report.py \
  --workspace ./my-novel
```

Ask the orchestrator what to do next:

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_novel_workspace_pipeline.py \
  --workspace ./my-novel
```

Execute the recommended layer:

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_novel_workspace_pipeline.py \
  --workspace ./my-novel \
  --execute
```

## Typical Outputs

After a run, you will usually see some of these files:

- `workspace-status.json`
- `workspace-gap-report.md`
- `workspace-repair-plan.md`
- `工作区流程判断报告.md`
- `工作状态-YYYY-MM-DD.md`

## Important Rule

Do not commit raw source files or bulky generated outputs to a public repository unless you have the rights and a clear reason to do so.
