#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from workspace_lib import collect_workspace_status


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_CASES = SKILL_DIR / "references" / "workspace-regression-cases.json"


@dataclass
class RegressionCase:
    name: str
    workspace: str
    expected_mode: str
    expected_next_layer: str | None
    expected_completed_layers: list[str]
    expected_incomplete_layers: list[str]
    expected_repair_target: str | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run read-only regression checks against your own stable workspace fixtures."
    )
    parser.add_argument(
        "--cases",
        default=str(DEFAULT_CASES),
        help="JSON file listing regression cases. Defaults to the bundled example fixture file.",
    )
    parser.add_argument(
        "--project-root",
        default=str(SKILL_DIR.parent),
        help="Repository root used to resolve relative workspace paths.",
    )
    parser.add_argument(
        "--case",
        action="append",
        dest="case_names",
        help="Only run the named case. Can be repeated.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable regression results after the text summary.",
    )
    return parser.parse_args()


def load_cases(path: Path) -> list[RegressionCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases: list[RegressionCase] = []
    for item in raw:
        cases.append(
            RegressionCase(
                name=item["name"],
                workspace=item["workspace"],
                expected_mode=item["expected_mode"],
                expected_next_layer=item.get("expected_next_layer"),
                expected_completed_layers=list(item.get("expected_completed_layers", [])),
                expected_incomplete_layers=list(item.get("expected_incomplete_layers", [])),
                expected_repair_target=item.get("expected_repair_target"),
            )
        )
    return cases


def compare_sequence(actual: list[str], expected: list[str], label: str) -> list[str]:
    if actual == expected:
        return []
    return [f"{label} mismatch: expected {expected}, got {actual}"]


def run_case(project_root: Path, case: RegressionCase) -> dict[str, Any]:
    workspace = (project_root / case.workspace).resolve()
    status = collect_workspace_status(workspace, run_validators=True, persist_validator_reports=False)
    failures: list[str] = []

    if status["recommended_mode"] != case.expected_mode:
        failures.append(
            f"mode mismatch: expected {case.expected_mode}, got {status['recommended_mode']}"
        )
    if status["recommended_next_layer"] != case.expected_next_layer:
        failures.append(
            f"next layer mismatch: expected {case.expected_next_layer}, got {status['recommended_next_layer']}"
        )

    failures.extend(compare_sequence(status["completed_layers"], case.expected_completed_layers, "completed_layers"))
    failures.extend(compare_sequence(status["incomplete_layers"], case.expected_incomplete_layers, "incomplete_layers"))

    repair_plan = status.get("repair_plan")
    actual_repair_target = repair_plan.get("target_layer") if repair_plan else None
    if actual_repair_target != case.expected_repair_target:
        failures.append(
            f"repair target mismatch: expected {case.expected_repair_target}, got {actual_repair_target}"
        )

    if case.expected_repair_target:
        layer_state = status["layer_status"][case.expected_repair_target]
        if not layer_state.get("failed_checks"):
            failures.append(f"{case.expected_repair_target} should expose failed_checks, but none were found")
        if not layer_state.get("repair_targets"):
            failures.append(f"{case.expected_repair_target} should expose repair_targets, but none were found")

    return {
        "name": case.name,
        "workspace": str(workspace),
        "ok": not failures,
        "failures": failures,
        "status_summary": {
            "recommended_mode": status["recommended_mode"],
            "recommended_next_layer": status["recommended_next_layer"],
            "completed_layers": status["completed_layers"],
            "incomplete_layers": status["incomplete_layers"],
            "repair_target": actual_repair_target,
        },
    }


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve()
    cases_path = Path(args.cases).expanduser().resolve()
    cases = load_cases(cases_path)

    if args.case_names:
        wanted = set(args.case_names)
        cases = [case for case in cases if case.name in wanted]

    results = [run_case(project_root, case) for case in cases]
    failures = [result for result in results if not result["ok"]]

    print(f"workspace regression: {len(results) - len(failures)}/{len(results)} passed")
    for result in results:
        summary = result["status_summary"]
        state = "PASS" if result["ok"] else "FAIL"
        print(
            f"- [{state}] {result['name']}: "
            f"{summary['recommended_mode']} -> {summary['recommended_next_layer']} | "
            f"completed={summary['completed_layers']} | incomplete={summary['incomplete_layers']}"
        )
        for failure in result["failures"]:
            print(f"  - {failure}")

    if args.json:
        print()
        print(json.dumps(results, ensure_ascii=False, indent=2))

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
