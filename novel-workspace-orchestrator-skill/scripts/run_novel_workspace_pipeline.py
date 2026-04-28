#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from workspace_lib import (
    LAYER_ORDER,
    build_layer_context,
    collect_workspace_status,
    execute_layer_init,
    preferred_source_file,
    render_gap_report,
    render_pipeline_report,
    render_repair_plan,
    render_workspace_handoff,
    update_repo_current_status,
    write_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a novel workspace and produce orchestration artifacts.")
    parser.add_argument("--workspace", required=True, help="Workspace directory to inspect.")
    parser.add_argument("--novel-name", help="Override detected novel name.")
    parser.add_argument("--protagonist-name", help="Override detected protagonist name.")
    parser.add_argument("--target-layer", choices=LAYER_ORDER, help="Force the pipeline to prepare a specific next layer.")
    parser.add_argument("--source", help="Optional source file override used when initializing a lower layer.")
    parser.add_argument("--execute", action="store_true", help="Actually call the lower-layer init entrypoint before re-validating.")
    parser.add_argument("--force-init", action="store_true", help="Allow the target layer init script to overwrite scaffold files when supported.")
    parser.add_argument(
        "--bootstrap-protagonist",
        action="store_true",
        help="Allow protagonist init to run its heavier bootstrap pipeline instead of scaffold-only mode.",
    )
    parser.add_argument(
        "--project-root",
        help="Project root used when updating CURRENT_STATUS.md and when routing protagonist init.",
    )
    parser.add_argument(
        "--tool-root",
        help="Tool root passed to protagonist init. Defaults to the repository root.",
    )
    parser.add_argument("--skip-validators", action="store_true", help="Use heuristics only.")
    parser.add_argument(
        "--persist-validator-reports",
        action="store_true",
        help="Allow lower-layer validators to refresh their persistent markdown reports.",
    )
    parser.add_argument("--no-write-status", action="store_true", help="Do not write workspace-status.json.")
    parser.add_argument("--no-write-gap-report", action="store_true", help="Do not write workspace-gap-report.md.")
    parser.add_argument("--no-write-repair-plan", action="store_true", help="Do not write workspace-repair-plan.md.")
    parser.add_argument("--no-write-pipeline-report", action="store_true", help="Do not write 工作区流程判断报告.md.")
    parser.add_argument(
        "--write-context",
        action="store_true",
        help="Write a reusable context file for the chosen target layer.",
    )
    parser.add_argument("--context-output", help="Custom output path for the context markdown.")
    parser.add_argument("--no-write-workspace-handoff", action="store_true", help="Do not write 工作状态-YYYY-MM-DD.md.")
    parser.add_argument("--no-write-current-status", action="store_true", help="Do not update the repository CURRENT_STATUS.md.")
    parser.add_argument("--json", action="store_true", help="Emit workspace status JSON before the markdown report.")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    status = collect_workspace_status(
        workspace,
        novel_name=args.novel_name,
        protagonist_name=args.protagonist_name,
        run_validators=not args.skip_validators,
        persist_validator_reports=args.persist_validator_reports,
    )
    target_layer = args.target_layer or status["recommended_next_layer"]
    execution_results: list[dict] = []
    executed_mode = status["recommended_mode"]

    if args.execute and target_layer:
        layer_state = status["layer_status"][target_layer]
        if target_layer == status["recommended_next_layer"]:
            executed_mode = status["recommended_mode"]
        elif layer_state["exists"] and not layer_state["validated"]:
            executed_mode = "repair-existing"
        else:
            executed_mode = "extend-existing" if status["available_layers"] else "fresh"

        source_path = Path(args.source).expanduser().resolve() if args.source else preferred_source_file(workspace)
        init_result = execute_layer_init(
            target_layer,
            workspace,
            status["novel_name"],
            protagonist_name=args.protagonist_name or status["protagonist_name"],
            source=source_path,
            force=args.force_init,
            bootstrap_protagonist=args.bootstrap_protagonist,
            project_root=Path(args.project_root).expanduser().resolve() if args.project_root else workspace.parent,
            tool_root=Path(args.tool_root).expanduser().resolve() if args.tool_root else None,
        )
        execution_results.append(init_result)
        status = collect_workspace_status(
            workspace,
            novel_name=args.novel_name or status["novel_name"],
            protagonist_name=args.protagonist_name or status["protagonist_name"],
            run_validators=not args.skip_validators,
            persist_validator_reports=True,
        )

    context_path: Path | None = None
    should_write_context = args.write_context or (args.execute and target_layer is not None)
    if should_write_context and target_layer:
        context_path = (
            Path(args.context_output).expanduser().resolve()
            if args.context_output
            else workspace / f"workspace-context-{target_layer}.md"
        )
        context_path.write_text(build_layer_context(status, target_layer), encoding="utf-8")

    gap_report = render_gap_report(status)
    repair_plan = render_repair_plan(status)
    handoff_path: Path | None = None
    if not args.no_write_workspace_handoff:
        handoff_path = workspace / f"工作状态-{date.today().isoformat()}.md"
        handoff_path.write_text(
            render_workspace_handoff(
                status,
                target_layer=target_layer,
                executed_mode=executed_mode,
                execution_results=execution_results or None,
                context_path=context_path,
            ),
            encoding="utf-8",
        )

    current_status_path: Path | None = None
    if not args.no_write_current_status:
        project_root = Path(args.project_root).expanduser().resolve() if args.project_root else workspace.parent
        current_status_path = update_repo_current_status(
            project_root,
            status,
            target_layer=target_layer,
            executed_mode=executed_mode,
        )

    pipeline_report = render_pipeline_report(
        status,
        target_layer,
        context_path,
        execution_results=execution_results or None,
        handoff_path=handoff_path,
        current_status_path=current_status_path,
    )

    if not args.no_write_status:
        write_json(workspace / "workspace-status.json", status)
    if not args.no_write_gap_report:
        (workspace / "workspace-gap-report.md").write_text(gap_report, encoding="utf-8")
    if repair_plan and not args.no_write_repair_plan:
        (workspace / "workspace-repair-plan.md").write_text(repair_plan, encoding="utf-8")
    if not args.no_write_pipeline_report:
        (workspace / "工作区流程判断报告.md").write_text(pipeline_report, encoding="utf-8")

    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
        print()
    print(pipeline_report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
