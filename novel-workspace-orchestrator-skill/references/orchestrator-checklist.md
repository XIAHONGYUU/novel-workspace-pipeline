# Orchestrator Checklist

Use this checklist before declaring orchestration complete.

## Workspace Read Pass

- [ ] `README.md` was checked when present
- [ ] latest `工作状态-YYYY-MM-DD.md` was checked when present
- [ ] repo-level `CURRENT_STATUS.md` was checked when relevant
- [ ] source files were identified

## Layer Detection Pass

- [ ] chapter-distillation layer status is known
- [ ] opening layer status is known
- [ ] protagonist layer status is known
- [ ] outline layer status is known
- [ ] highlight layer status is known

## Routing Pass

- [ ] mode was chosen: `fresh` or `extend-existing` or `repair-existing` or `validate-only`
- [ ] next layer was chosen explicitly
- [ ] if a weak existing layer exists, repair priority was considered before creating a later layer
- [ ] lower-layer skill selection was explicit rather than improvised

## Handoff Pass

- [ ] validator result was checked when available
- [ ] latest handoff state was written back
- [ ] next recommended layer is explicit
- [ ] resume reading order is explicit

## Stop Rule

Do not declare orchestration complete only because one file was updated.

Only stop when both are true:

- the next layer decision is explicit
- the workspace handoff state is clearer than before
