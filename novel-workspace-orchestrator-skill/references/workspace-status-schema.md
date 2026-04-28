# Workspace Status Schema

Use this reference when you want a stable machine-readable view of a novel workspace.

## File

- `workspace-status.json`

## Top-Level Fields

- `workspace_path`
- `novel_name`
- `protagonist_name`
- `source_files`
- `source_total_bytes`
- `source_estimated_chars`
- `is_long_novel`
- `available_layers`
- `completed_layers`
- `incomplete_layers`
- `last_run_layer`
- `last_validator_result`
- `recommended_next_layer`
- `recommended_skill`
- `recommended_mode`
- `recommended_next_step`
- `optional_backfill_layers`
- `repair_plan`
- `updated_at`
- `layer_status`

## `layer_status.<layer>`

Each layer entry should contain:

- `layer`
- `label`
- `exists`
- `validated`
- `has_placeholders`
- `completion_label`
- `reason`
- `files`
- `checks`
- `failed_checks`
- `repair_targets`
- `validator_report`
- `validator_summary`

## `repair_plan`

Present when the current workspace should enter `repair-existing`.

- `required`
- `target_layer`
- `target_label`
- `mode`
- `reason`
- `failed_checks`
- `repair_targets`
- `context_files`
- `suggested_context_file`
- `suggested_repair_note`

## Current Layer Keys

- `chapter-distillation`
- `opening`
- `protagonist`
- `outline`
- `highlight`

## Design Notes

- `exists` means the layer has visible artifacts.
- `validated` means the layer passed either a real validator or a configured heuristic completion rule.
- `has_placeholders` flags likely unfinished files.
- `recommended_next_layer` is the orchestration recommendation, not an irreversible truth.
- `optional_backfill_layers` exists for cases where a later layer is already valid but an earlier calibration layer is still worth补.
