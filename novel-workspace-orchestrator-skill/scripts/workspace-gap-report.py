#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from workspace_lib import (
    collect_workspace_status,
    render_gap_report,
    render_repair_plan,
    run_quality_gate_for_workspace,
    write_json,
    LAYER_ORDER,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a workspace gap report for a novel project.")
    parser.add_argument("--workspace", required=True, help="Workspace directory to inspect.")
    parser.add_argument("--novel-name", help="Override detected novel name.")
    parser.add_argument("--protagonist-name", help="Override detected protagonist name.")
    parser.add_argument("--json", action="store_true", help="Emit status JSON instead of only markdown.")
    parser.add_argument("--no-write-status", action="store_true", help="Do not write workspace-status.json.")
    parser.add_argument("--no-write-report", action="store_true", help="Do not write workspace-gap-report.md.")
    parser.add_argument("--no-write-repair-plan", action="store_true", help="Do not write workspace-repair-plan.md.")
    parser.add_argument("--skip-validators", action="store_true", help="Use heuristics only.")
    parser.add_argument("--skip-quality-gate", action="store_true", help="Skip quality gate assessment.")
    parser.add_argument(
        "--persist-validator-reports",
        action="store_true",
        help="Allow lower-layer validators to refresh their persistent markdown reports.",
    )
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    status = collect_workspace_status(
        workspace,
        novel_name=args.novel_name,
        protagonist_name=args.protagonist_name,
        run_validators=not args.skip_validators,
        persist_validator_reports=args.persist_validator_reports,
    )

    # 运行质量门检测（默认开启，用 --skip-quality-gate 跳过）
    if not args.skip_quality_gate:
        try:
            novel_name = status["novel_name"]
            quality_result = run_quality_gate_for_workspace(
                workspace, novel_name, target_layer=None, persist_report=True
            )
            if quality_result and "layer_results" in quality_result:
                for layer in LAYER_ORDER:
                    lr = quality_result["layer_results"].get(layer)
                    if lr:
                        status["layer_status"][layer]["quality"] = {
                            "score": lr["score"],
                            "ok": lr["ok"],
                            "issues": lr["issues"],
                        }
                status["quality_gate"] = {
                    "overall_score": quality_result["overall_score"],
                    "is_quality_pass": quality_result["is_quality_pass"],
                    "issue_count": quality_result["issue_count"],
                    "cross_layer_conflicts": quality_result.get("cross_layer_consistency", {}).get("conflict_count", 0),
                }
        except Exception as e:
            # 质量门失败不应阻塞主流程
            status["quality_gate"] = {
                "overall_score": None,
                "is_quality_pass": False,
                "error": str(e),
            }

    report = render_gap_report(status)
    repair_plan = render_repair_plan(status)
    if not args.no_write_status:
        write_json(workspace / "workspace-status.json", status)
    if not args.no_write_report:
        (workspace / "workspace-gap-report.md").write_text(report, encoding="utf-8")
    if repair_plan and not args.no_write_repair_plan:
        (workspace / "workspace-repair-plan.md").write_text(repair_plan, encoding="utf-8")
    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
    else:
        print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
