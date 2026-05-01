# Workspace Lifecycle

## Core Idea

A workspace is not "done" because files exist. It is only meaningfully advanced when a layer is both present and validated.

## Modes

### `fresh`

Used when the workspace has not been meaningfully initialized.

### `extend-existing`

Used when the workspace already has value and the next missing layer should be added.

### `repair-existing`

Used when a layer exists but is still skeletal, incomplete, or validator-failing.

### `validate-only`

Used when you want to inspect current state without changing content.

## Layer Progression

```text
source
  -> chapter-distillation
  -> opening
  -> protagonist
  -> outline
  -> highlight
```

This order is not a moral law, but it is the default progression encoded into the orchestrator.

## What "Good State" Looks Like

- the next recommended action is explicit
- placeholder files are not mistaken for completed analysis
- validator output matches the actual workspace condition
- handoff files tell the next operator where to resume

## What Usually Goes Wrong

- source text exists, but no layer has real analysis content
- layer files exist, but still contain placeholders
- repo-level docs drift away from actual script behavior
- raw source or generated artifacts get mixed into the public code repository
