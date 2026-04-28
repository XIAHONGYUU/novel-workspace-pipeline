#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from workspace_lib import LAYER_ORDER, build_layer_context, collect_workspace_status, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Build reusable layer context from an existing novel workspace.")
    parser.add_argument("--workspace", required=True, help="Workspace directory to inspect.")
    parser.add_argument("--target-layer", required=True, choices=LAYER_ORDER, help="Layer that needs reusable context.")
    parser.add_argument("--novel-name", help="Override detected novel name.")
    parser.add_argument("--protagonist-name", help="Override detected protagonist name.")
    parser.add_argument("--output", help="Write the context markdown to this file.")
    parser.add_argument("--json", action="store_true", help="Emit workspace status JSON before the markdown.")
    parser.add_argument("--skip-validators", action="store_true", help="Use heuristics only.")
    parser.add_argument("--no-write-status", action="store_true", help="Do not write workspace-status.json.")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    status = collect_workspace_status(
        workspace,
        novel_name=args.novel_name,
        protagonist_name=args.protagonist_name,
        run_validators=not args.skip_validators,
    )
    context = build_layer_context(status, args.target_layer)
    if not args.no_write_status:
        write_json(workspace / "workspace-status.json", status)
    if args.output:
        Path(args.output).expanduser().resolve().write_text(context, encoding="utf-8")
    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
        print()
    print(context, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
