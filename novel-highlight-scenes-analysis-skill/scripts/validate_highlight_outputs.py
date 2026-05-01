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
    "当前仅完成了剧情高光分析工作区初始化",
)

REQUIRED_CORE_KEYS = (
    "project_entry",
    "handoff",
    "top10_table",
    "mechanism",
    "top10_breakdown",
    "distribution",
    "pleasure_summary",
    "revision",
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


def placeholder_score(text: str) -> int:
    score = 0
    for token in PLACEHOLDER_TOKENS:
        score += text.count(token)
    score += len(
        re.findall(r"^\s*[-*]\s*(?:待补充|待确认|待定|待完善).*$", text, flags=re.MULTILINE)
    )
    return score


def content_check(path: Path | None, keywords: list[str], minimum: int = 1, min_chars: int = 120) -> dict:
    if not path or not path.exists():
        return {"exists": False, "content_ok": False, "reason": "missing"}
    text = read_text(path)
    if len(text.strip()) < min_chars:
        return {"exists": True, "content_ok": False, "reason": "too_short"}
    placeholders = placeholder_hits(text)
    if len(placeholders) >= 2 or placeholder_score(text) >= 3:
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
        f"# 《{novel_name}》剧情高光校验报告",
        "",
        f"- 工作区：`{workspace}`",
        f"- 高光桥段判断：`{result['highlight_status']}`",
        f"- 剧情吸引力机制判断：`{result['mechanism_status']}`",
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
    parser = argparse.ArgumentParser(description="Validate durable outputs for a highlight-scenes-analysis workspace.")
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
        "project_entry": content_check(workspace / "README.md", ["剧情高光", "工作区", "当前结构"], minimum=2),
        "handoff": content_check(status_path, ["当前结论", "下次开始时建议先看", "一句话交接"], minimum=2),
        "top10_table": content_check(
            workspace / f"{args.novel_name}-最吸引人的十个剧情细节总表.md",
            ["总判断", "高光细节 1", "所在阶段", "吸引力类型", "主要作用"],
            minimum=4,
        ),
        "mechanism": content_check(
            workspace / f"{args.novel_name}-剧情吸引力机制分析.md",
            ["核心判断", "反差", "悬念", "情绪兑现", "翻转", "揭露"],
            minimum=4,
        ),
        "top10_breakdown": content_check(
            workspace / f"{args.novel_name}-Top10细节逐条拆解.md",
            ["细节 1", "发生位置", "前置铺垫", "吸引力为什么成立", "改变了什么"],
            minimum=4,
        ),
        "distribution": content_check(
            workspace / f"{args.novel_name}-高光桥段分布与节奏判断.md",
            ["高光分布总判断", "前段高光", "中段高光", "后段高光", "节奏判断"],
            minimum=4,
        ),
        "pleasure_summary": content_check(
            workspace / f"{args.novel_name}-最强爽点痛点悬念点总结.md",
            ["最强爽点", "最强痛点", "最强悬念点", "综合判断"],
            minimum=4,
        ),
        "revision": content_check(
            workspace / f"{args.novel_name}-剧情高光改造建议.md",
            ["当前最强高光", "当前最弱区段", "应该补强什么", "应该前移或后移什么", "应该压缩或合并什么"],
            minimum=4,
        ),
    }

    existing_count = sum(1 for value in checks.values() if value["exists"])
    content_ok_count = sum(1 for value in checks.values() if value["content_ok"])
    required_core_ok_count = sum(1 for key in REQUIRED_CORE_KEYS if checks[key]["content_ok"])

    highlight_status = "高光桥段仍不足"
    if (
        checks["top10_table"]["content_ok"]
        and checks["pleasure_summary"]["content_ok"]
        and checks["revision"]["content_ok"]
    ):
        highlight_status = "高光桥段已明确"

    mechanism_status = "剧情吸引力机制仍不足"
    if (
        checks["mechanism"]["content_ok"]
        and checks["top10_breakdown"]["content_ok"]
        and checks["distribution"]["content_ok"]
    ):
        mechanism_status = "剧情吸引力机制已拆清"

    result = {
        "workspace": str(workspace),
        "novel_name": args.novel_name,
        "highlight_status": highlight_status,
        "mechanism_status": mechanism_status,
        "existing_count": existing_count,
        "content_ok_count": content_ok_count,
        "required_core_ok_count": required_core_ok_count,
        "checks": checks,
        "status_file": str(status_path) if status_path else None,
    }

    report_text = markdown_report(args.novel_name, workspace, result)
    report_path = workspace / f"{args.novel_name}-剧情高光校验报告.md"
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
