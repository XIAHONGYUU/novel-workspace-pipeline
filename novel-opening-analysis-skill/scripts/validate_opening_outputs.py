#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PLACEHOLDER_TOKENS = (
    "待补充",
    "待确认",
    "待定",
    "待完善",
    "TODO",
    "TBD",
    "当前仅完成了黄金前三章分析工作区初始化",
)

REQUIRED_CORE_KEYS = (
    "project_entry",
    "handoff",
    "total_judgment",
    "chapter_1",
    "chapter_2",
    "chapter_3",
    "hook_promise",
    "issues_revision",
)


def latest_status_file(workspace: Path) -> Path | None:
    candidates = sorted(workspace.glob("工作状态-*.md"))
    return candidates[-1] if candidates else None


def read_text(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def has_keywords(text: str, keywords: list[str], minimum: int = 1) -> bool:
    hits = sum(1 for keyword in keywords if keyword in text)
    return hits >= minimum


def placeholder_hits(text: str) -> list[str]:
    hits = [token for token in PLACEHOLDER_TOKENS if token in text]
    hits.extend(
        line.strip()
        for line in re.findall(r"^\s*[-*]\s*(?:待补充|待确认|待定|待完善).*$", text, flags=re.MULTILINE)
    )
    return list(dict.fromkeys(hits))


def content_check(path: Path | None, keywords: list[str], minimum: int = 1, min_chars: int = 120) -> dict:
    if not path or not path.exists():
        return {"exists": False, "content_ok": False, "reason": "missing"}
    text = read_text(path)
    if len(text.strip()) < min_chars:
        return {"exists": True, "content_ok": False, "reason": "too_short"}
    placeholders = placeholder_hits(text)
    if len(placeholders) >= 2:
        return {
            "exists": True,
            "content_ok": False,
            "reason": "placeholder_detected",
            "placeholder_hits": placeholders[:5],
        }
    if not has_keywords(text, keywords, minimum):
        return {"exists": True, "content_ok": False, "reason": "keywords_missing"}
    return {"exists": True, "content_ok": True, "reason": "ok"}


def markdown_report(novel_name: str, workspace: Path, result: dict) -> str:
    lines = [
        f"# 《{novel_name}》黄金前三章校验报告",
        "",
        f"- 工作区：`{workspace}`",
        f"- 开篇抓力判断：`{result['opening_status']}`",
        f"- 前三章结构判断：`{result['structure_status']}`",
        f"- 已存在层数：`{result['existing_count']}/8`",
        f"- 内容达标层数：`{result['content_ok_count']}/8`",
        f"- 关键必过项：`{result['required_core_ok_count']}/{len(REQUIRED_CORE_KEYS)}`",
        "",
        "## 分项结果",
        "",
    ]
    for name, value in result["checks"].items():
        status = "通过" if value["content_ok"] else ("仅存在" if value["exists"] else "缺失")
        detail = value["reason"]
        if value.get("placeholder_hits"):
            detail += f"; 占位痕迹: {', '.join(value['placeholder_hits'])}"
        lines.append(f"- `{name}`：{status}（{detail}）")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate durable outputs for a first-three-chapter analysis workspace.")
    parser.add_argument("--workspace", required=True, help="Workspace directory to validate.")
    parser.add_argument("--novel-name", required=True, help="Novel name used in file naming.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a markdown report.")
    parser.add_argument("--no-write-report", action="store_true", help="Do not persist the markdown report.")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.exists():
        raise SystemExit(f"workspace not found: {workspace}")

    status_path = latest_status_file(workspace)
    checks = {
        "project_entry": content_check(workspace / "README.md", ["前三章", "工作区", "当前结构"], minimum=2),
        "handoff": content_check(status_path, ["当前结论", "下次开始时建议先看", "一句话交接"], minimum=2),
        "total_judgment": content_check(
            workspace / f"{args.novel_name}-黄金前三章总判断.md",
            ["开篇钩子", "主角亮相", "冲突", "结构", "继续阅读"],
            minimum=4,
        ),
        "chapter_1": content_check(
            workspace / f"{args.novel_name}-第一章拆解.md",
            ["本章在开篇结构中的作用", "钩子", "主角", "信息释放", "结尾拉力"],
            minimum=4,
        ),
        "chapter_2": content_check(
            workspace / f"{args.novel_name}-第二章拆解.md",
            ["本章在开篇结构中的作用", "钩子", "主角", "信息释放", "结尾拉力"],
            minimum=4,
        ),
        "chapter_3": content_check(
            workspace / f"{args.novel_name}-第三章拆解.md",
            ["本章在开篇结构中的作用", "钩子", "主角", "信息释放", "结尾拉力"],
            minimum=4,
        ),
        "hook_promise": content_check(
            workspace / f"{args.novel_name}-开篇钩子与读者承诺.md",
            ["立即钩子", "题材承诺", "主角承诺", "情绪", "结尾拉力"],
            minimum=4,
        ),
        "issues_revision": content_check(
            workspace / f"{args.novel_name}-开篇问题与修改建议.md",
            ["最强", "最弱", "分章问题", "第一优先修改项", "轻修建议"],
            minimum=4,
        ),
    }

    existing_count = sum(1 for value in checks.values() if value["exists"])
    content_ok_count = sum(1 for value in checks.values() if value["content_ok"])
    required_core_ok_count = sum(1 for key in REQUIRED_CORE_KEYS if checks[key]["content_ok"])

    opening_status = "开篇抓力仍不足"
    if checks["total_judgment"]["content_ok"] and checks["hook_promise"]["content_ok"] and checks["issues_revision"]["content_ok"]:
        opening_status = "开篇抓力已明确"

    structure_status = "前三章结构仍不足"
    if checks["chapter_1"]["content_ok"] and checks["chapter_2"]["content_ok"] and checks["chapter_3"]["content_ok"]:
        structure_status = "前三章结构已拆清"

    result = {
        "workspace": str(workspace),
        "novel_name": args.novel_name,
        "opening_status": opening_status,
        "structure_status": structure_status,
        "existing_count": existing_count,
        "content_ok_count": content_ok_count,
        "required_core_ok_count": required_core_ok_count,
        "checks": checks,
        "status_file": str(status_path) if status_path else None,
    }

    report_text = markdown_report(args.novel_name, workspace, result)
    report_path = workspace / f"{args.novel_name}-黄金前三章校验报告.md"
    result["report_path"] = str(report_path)
    if not args.no_write_report:
        report_path.write_text(report_text, encoding="utf-8")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(report_text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
