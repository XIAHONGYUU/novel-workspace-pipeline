#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

from output_normalizer import normalize_layer_outputs


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"failed to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def case_bare_numeric_chapters() -> tuple[bool, str]:
    distill = load_module(
        "smoke_distill",
        REPO_ROOT / "novel-chapter-distillation-skill/scripts/distill_chapters.py",
    )
    opening = load_module(
        "smoke_opening",
        REPO_ROOT / "novel-opening-analysis-skill/scripts/fill_opening_workspace.py",
    )
    tempdir = Path(tempfile.mkdtemp(prefix="workspace-smoke-chapters-"))
    try:
        source = tempdir / "bare-number.md"
        write(
            source,
            "\n".join(
                [
                    "1",
                    "第一章内容",
                    "2",
                    "第二章内容",
                    "3",
                    "第三章内容",
                    "4",
                    "第四章内容",
                ]
            )
            + "\n",
        )
        distill_chapters, _, _ = distill.read_chapters(source)
        opening_chapters, _ = opening.read_chapters(source)
        if len(distill_chapters) < 4:
            return False, f"distill parser expected >=4 chapters, got {len(distill_chapters)}"
        if len(opening_chapters) < 3:
            return False, f"opening parser expected >=3 chapters, got {len(opening_chapters)}"
        if distill.chapter_parse_guard(source, distill_chapters) is not None:
            return False, "distill parser unexpectedly failed bare-number guard"
        if opening.chapter_parse_guard(source, opening_chapters) is not None:
            return False, "opening parser unexpectedly failed bare-number guard"
        return True, "bare-number chapter parsing passed"
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)


def case_keyword_normalizer() -> tuple[bool, str]:
    tempdir = Path(tempfile.mkdtemp(prefix="workspace-smoke-normalizer-"))
    try:
        workspace = tempdir / "测试书"
        issues = workspace / "测试书-开篇问题与修改建议.md"
        write(
            issues,
            "# 《测试书》开篇修改建议（旧版）\n\n## 方案一\n\n- 这里只写旧版 prose，没有 validator 需要的标准标题。\n",
        )
        status = workspace / "工作状态-2026-06-04.md"
        write(status, "# 《测试书》工作状态\n")
        result = normalize_layer_outputs("opening", workspace, "测试书")
        text = issues.read_text(encoding="utf-8")
        required = ["最强的地方", "最弱的地方", "分章问题", "第一优先修改项", "轻修建议"]
        missing = [item for item in required if item not in text]
        if missing:
            return False, f"opening normalizer missing headings: {missing}"
        if not result["actions"]:
            return False, "opening normalizer reported no actions on legacy file"
        return True, "opening keyword normalization passed"
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)


def main() -> int:
    cases = [
        ("bare-number-chapters", case_bare_numeric_chapters),
        ("keyword-normalizer", case_keyword_normalizer),
    ]
    failures: list[str] = []
    for name, fn in cases:
        ok, message = fn()
        state = "PASS" if ok else "FAIL"
        print(f"- [{state}] {name}: {message}")
        if not ok:
            failures.append(f"{name}: {message}")
    print(f"smoke regression: {len(cases) - len(failures)}/{len(cases)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
