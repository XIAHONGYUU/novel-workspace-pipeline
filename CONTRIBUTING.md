# Contributing

## Goal

Keep this repository focused on reusable workflow infrastructure.

Good contributions usually improve one of these areas:

- orchestration
- validators
- layer init scripts
- documentation
- safe synthetic examples
- developer ergonomics

## Do Contribute

- script fixes that make the pipeline more portable
- validator improvements that reduce false positives
- docs that make the workflow easier to understand
- small permission-safe fixtures for tests or regression
- clearer handoff or status formats

## Do Not Contribute

- full copyrighted novel texts unless you have explicit rights
- giant generated workspace dumps
- private reading notes that are not part of the reusable workflow
- repo-wide formatting churn with no functional value

## Change Guidelines

- Keep edits narrow and purposeful.
- Preserve the layer model unless you are intentionally proposing a workflow change.
- Prefer repository-relative paths over machine-specific absolute paths.
- Keep generated outputs ignored by default.
- When changing validation behavior, document the expected before/after effect.

## Before Opening A PR

1. Run the relevant scripts you changed.
2. Check that public docs still match actual CLI behavior.
3. Confirm that no raw source text or large generated outputs were added.
4. If you changed regression behavior, update or add fixture cases explicitly.

## Suggested Areas For Future Work

- synthetic demo workspaces
- better repair flows for `repair-existing`
- stronger sample regression fixtures
- packaging and automation around frequent commands
