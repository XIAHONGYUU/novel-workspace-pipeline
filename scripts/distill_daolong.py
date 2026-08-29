#!/usr/bin/env python3
"""兼容入口：统一转发到官方章节蒸馏脚本。"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "novel-chapter-distillation-skill/scripts/distill_chapters.py"
    cmd = ["python3", str(script), "刀笼", "--project-root", str(repo_root)]
    return subprocess.run(cmd, check=False, env={**os.environ, "PYTHONUNBUFFERED": "1"}).returncode


if __name__ == "__main__":
    raise SystemExit(main())
