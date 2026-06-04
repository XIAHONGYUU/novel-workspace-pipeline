#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from workspace_lib import (
    LAYER_ORDER,
    apply_quality_gate_to_status,
    build_human_escalation,
    build_layer_context,
    collect_workspace_status,
    execute_layer_autofill,
    execute_layer_init,
    execute_output_normalizer,
    preferred_source_file,
    render_gap_report,
    render_pipeline_report,
    render_repair_plan,
    render_workspace_handoff,
    run_quality_gate_for_workspace,
    supports_layer_autofill,
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
    parser.add_argument("--execute-all", action="store_true", help="Automatically cascade through all remaining layers until the workspace closes or a layer still fails after repair.")
    parser.add_argument("--force-init", action="store_true", help="Allow the target layer init script to overwrite scaffold files when supported.")
    parser.add_argument("--no-auto-fill", action="store_true", help="Only scaffold the target layer, skip supported AI fill.")
    parser.add_argument("--repair-attempts", type=int, default=2, help="Automatic repair retries after the first AI fill.")
    parser.add_argument("--max-layer-runs", type=int, default=len(LAYER_ORDER) + 2, help="Safety cap for --execute-all outer-layer iterations.")
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
    parser.add_argument("--skip-quality-gate", action="store_true", help="Skip quality gate assessment (runs by default).")
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
    parser.add_argument("--quiet", action="store_true", help="Write artifacts only; suppress stdout output.")
    parser.add_argument(
        "--human-escalation-exit-code",
        type=int,
        default=0,
        help="Return this exit code when human escalation is triggered after execution. Defaults to 0.",
    )
    parser.add_argument("--json", action="store_true", help="Emit workspace status JSON before the markdown report.")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    project_root = Path(args.project_root).expanduser().resolve() if args.project_root else workspace.parent
    tool_root = Path(args.tool_root).expanduser().resolve() if args.tool_root else None

    def refresh_status(*, persist_reports: bool) -> dict:
        return collect_workspace_status(
            workspace,
            novel_name=args.novel_name,
            protagonist_name=args.protagonist_name,
            run_validators=not args.skip_validators,
            persist_validator_reports=persist_reports,
        )

    def augment_quality(current_status: dict) -> dict:
        if args.skip_quality_gate:
            return current_status
        try:
            quality_result = run_quality_gate_for_workspace(
                workspace,
                args.novel_name or current_status["novel_name"],
                target_layer=None,
                persist_report=True,
            )
            return apply_quality_gate_to_status(current_status, quality_result)
        except Exception as exc:
            current_status["quality_gate"] = {
                "overall_score": None,
                "is_quality_pass": False,
                "error": str(exc),
            }
            return current_status

    status = collect_workspace_status(
        workspace,
        novel_name=args.novel_name,
        protagonist_name=args.protagonist_name,
        run_validators=not args.skip_validators,
        persist_validator_reports=args.persist_validator_reports,
    )
    status = augment_quality(status)
    requested_target_layer = args.target_layer
    target_layer = requested_target_layer or status["recommended_next_layer"]
    execution_results: list[dict] = []
    executed_mode = status["recommended_mode"]
    last_context_path: Path | None = None
    last_executed_target: str | None = None

    def layer_quality_ok(current_status: dict, layer: str) -> bool:
        return args.skip_quality_gate or current_status["layer_status"][layer].get("quality", {}).get("ok", True)

    def determine_executed_mode(current_status: dict, layer: str) -> str:
        layer_state = current_status["layer_status"][layer]
        if layer == current_status["recommended_next_layer"]:
            return current_status["recommended_mode"]
        if layer_state["exists"] and not layer_state["validated"]:
            return "repair-existing"
        return "extend-existing" if current_status["available_layers"] else "fresh"

    def execute_target_layer(current_status: dict, layer: str) -> tuple[dict, list[dict], str, Path | None, bool]:
        source_path = Path(args.source).expanduser().resolve() if args.source else preferred_source_file(workspace)
        layer_results: list[dict] = []
        context_path_for_layer: Path | None = None
        mode_for_layer = determine_executed_mode(current_status, layer)

        init_result = execute_layer_init(
            layer,
            workspace,
            current_status["novel_name"],
            protagonist_name=args.protagonist_name or current_status["protagonist_name"],
            source=source_path,
            force=args.force_init,
            bootstrap_protagonist=args.bootstrap_protagonist,
            project_root=project_root,
            tool_root=tool_root,
        )
        layer_results.append(init_result)
        current_status = refresh_status(persist_reports=True)
        current_status = augment_quality(current_status)

        can_autofill = (
            not args.no_auto_fill
            and init_result.get("ok")
            and supports_layer_autofill(layer)
        )
        if can_autofill:
            fill_result = execute_layer_autofill(
                layer,
                workspace,
                current_status["novel_name"],
                protagonist_name=args.protagonist_name or current_status["protagonist_name"],
                source=source_path,
                project_root=project_root,
                attempt_label="draft",
                force=args.force_init,
            )
            layer_results.append(fill_result)
            if fill_result.get("ok"):
                layer_results.append(
                    execute_output_normalizer(
                        layer,
                        workspace,
                        current_status["novel_name"],
                        protagonist_name=args.protagonist_name or current_status["protagonist_name"],
                    )
                )
            current_status = refresh_status(persist_reports=True)
            current_status = augment_quality(current_status)

            for attempt in range(1, max(args.repair_attempts, 0) + 1):
                if not fill_result.get("ok") and attempt == 1:
                    break
                if current_status["layer_status"][layer]["validated"] and layer_quality_ok(current_status, layer):
                    break
                context_path_for_layer = workspace / f"workspace-context-{layer}.md"
                context_path_for_layer.write_text(build_layer_context(current_status, layer), encoding="utf-8")
                repair_plan_text = render_repair_plan(current_status)
                context_files = [context_path_for_layer]
                if repair_plan_text:
                    repair_plan_path = workspace / "workspace-repair-plan.md"
                    repair_plan_path.write_text(repair_plan_text, encoding="utf-8")
                    context_files.append(repair_plan_path)
                repair_result = execute_layer_autofill(
                    layer,
                    workspace,
                    current_status["novel_name"],
                    protagonist_name=args.protagonist_name or current_status["protagonist_name"],
                    source=source_path,
                    project_root=project_root,
                    attempt_label=f"repair-{attempt}",
                    force=True,
                    context_files=context_files,
                )
                layer_results.append(repair_result)
                if repair_result.get("ok"):
                    layer_results.append(
                        execute_output_normalizer(
                            layer,
                            workspace,
                            current_status["novel_name"],
                            protagonist_name=args.protagonist_name or current_status["protagonist_name"],
                        )
                    )
                current_status = refresh_status(persist_reports=True)
                current_status = augment_quality(current_status)

        layer_closed = current_status["layer_status"][layer]["validated"] and layer_quality_ok(current_status, layer)
        return current_status, layer_results, mode_for_layer, context_path_for_layer, layer_closed

    if (args.execute or args.execute_all) and target_layer:
        pending_target = target_layer
        for outer_attempt in range(1, max(args.max_layer_runs, 1) + 1):
            status, layer_results, mode_for_layer, context_path_for_layer, layer_closed = execute_target_layer(status, pending_target)
            execution_results.extend(layer_results)
            executed_mode = "execute-all" if args.execute_all else mode_for_layer
            last_executed_target = pending_target
            if context_path_for_layer:
                last_context_path = context_path_for_layer
            if not args.execute_all:
                break
            if not layer_closed:
                break
            next_target = status["recommended_next_layer"]
            if not next_target or next_target == pending_target or outer_attempt >= max(args.max_layer_runs, 1):
                break
            pending_target = next_target
        target_layer = last_executed_target or target_layer

    context_path: Path | None = None
    should_write_context = args.write_context or ((args.execute or args.execute_all) and target_layer is not None)
    context_target = status["recommended_next_layer"] if args.execute_all and status["recommended_next_layer"] else target_layer
    if should_write_context and context_target:
        context_path = (
            Path(args.context_output).expanduser().resolve()
            if args.context_output
            else workspace / f"workspace-context-{context_target}.md"
        )
        context_path.write_text(build_layer_context(status, context_target), encoding="utf-8")
    elif last_context_path:
        context_path = last_context_path

    status["human_escalation"] = build_human_escalation(
        status,
        attempted_layer=target_layer if (args.execute or args.execute_all) else None,
        executed_mode=executed_mode,
        execution_results=execution_results or None,
    )

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

    if not args.quiet:
        if args.json:
            print(json.dumps(status, ensure_ascii=False, indent=2))
            print()
        print(pipeline_report, end="")
    if status.get("human_escalation") and args.human_escalation_exit_code:
        return args.human_escalation_exit_code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
