#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from workspace_lib import (
    LAYER_ORDER,
    ai_fill_brief_path,
    build_ai_fill_brief,
    build_layer_context,
    collect_workspace_status,
    write_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare AI-fill artifacts for a target novel-workspace layer.")
    parser.add_argument("--workspace", required=True, help="Workspace directory to inspect.")
    parser.add_argument("--target-layer", choices=LAYER_ORDER, help="Layer to prepare. Defaults to the recommended next layer.")
    parser.add_argument("--novel-name", help="Override detected novel name.")
    parser.add_argument("--protagonist-name", help="Override detected protagonist name.")
    parser.add_argument("--skip-validators", action="store_true", help="Use heuristics only.")
    parser.add_argument(
        "--persist-validator-reports",
        action="store_true",
        help="Allow lower-layer validators to refresh their persistent markdown reports.",
    )
    parser.add_argument("--no-write-status", action="store_true", help="Do not write workspace-status.json.")
    parser.add_argument("--context-output", help="Custom output path for the context markdown.")
    parser.add_argument("--output", help="Custom output path for the AI fill markdown.")
    parser.add_argument("--json", action="store_true", help="Emit workspace status JSON before the markdown summary.")
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
    if not target_layer:
        raise SystemExit("no target layer available; the workspace appears fully covered or validate-only")

    context_path = (
        Path(args.context_output).expanduser().resolve()
        if args.context_output
        else workspace / f"workspace-context-{target_layer}.md"
    )
    ai_fill_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else ai_fill_brief_path(workspace, target_layer)
    )
    context_path.write_text(build_layer_context(status, target_layer), encoding="utf-8")
    ai_fill_path.write_text(build_ai_fill_brief(status, target_layer, context_path=context_path), encoding="utf-8")
    if not args.no_write_status:
        write_json(workspace / "workspace-status.json", status)

    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
        print()
    print(f"context: {context_path}")
    print(f"ai_fill: {ai_fill_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
