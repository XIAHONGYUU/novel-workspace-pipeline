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
    "待AI复核",
    "待AI补判",
    "card 初评扩展版",
    "TODO",
    "TBD",
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
        for line in re.findall(
            r"^\s*[-*]\s*(?:待补充|待确认|待定|待完善|待AI复核|待AI补判).*$",
            text,
            flags=re.MULTILINE,
        )
    )
    return list(dict.fromkeys(hits))


def placeholder_score(text: str) -> int:
    score = 0
    for token in PLACEHOLDER_TOKENS:
        score += text.count(token)
    score += len(
        re.findall(
            r"^\s*[-*]\s*(?:待补充|待确认|待定|待完善|待AI复核|待AI补判).*$",
            text,
            flags=re.MULTILINE,
        )
    )
    return score


def content_check(path: Path | None, keywords: list[str], minimum: int = 1, min_chars: int = 120) -> dict:
    if not path or not path.exists():
        return {"exists": False, "content_ok": False, "reason": "missing"}
    text = read_text(path)
    if len(text.strip()) < min_chars:
        return {"exists": True, "content_ok": False, "reason": "too_short"}
    placeholders = placeholder_hits(text)
    if len(placeholders) >= 1 or placeholder_score(text) >= 2:
        return {
            "exists": True,
            "content_ok": False,
            "reason": "placeholder_detected",
            "placeholder_hits": placeholders[:6],
        }
    if not has_keywords(text, keywords, minimum):
        return {"exists": True, "content_ok": False, "reason": "keywords_missing"}
    return {"exists": True, "content_ok": True, "reason": "ok"}


def detect_profile_files(workspace: Path) -> list[Path]:
    return sorted((workspace / "supporting-cast").glob("*-配角分析.md"))


def validate_profiles(profile_files: list[Path]) -> tuple[dict, list[str]]:
    if len(profile_files) < 10:
        return (
            {
                "exists": bool(profile_files),
                "content_ok": False,
                "reason": "missing_profiles",
            },
            [],
        )

    failures: list[str] = []
    for path in profile_files[:10]:
        result = content_check(
            path,
            [
                "基本信息",
                "身份概述",
                "与主角关系",
                "关键事件",
                "阶段总结",
                "人物特征总结",
                "Top10入选理由",
                "最终结论",
            ],
            minimum=7,
            min_chars=1000,
        )
        if not result["content_ok"]:
            failures.append(f"{path.name}:{result['reason']}")

    return (
        {
            "exists": True,
            "content_ok": not failures,
            "reason": "ok" if not failures else "profile_quality_insufficient",
        },
        failures,
    )


def markdown_report(novel_name: str, workspace: Path, result: dict) -> str:
    lines = [
        f"# 《{novel_name}》重要配角层校验报告",
        "",
        f"- 工作区：`{workspace}`",
        f"- Top10 判断：`{result['top10_status']}`",
        f"- AI复核层判断：`{result['ai_review_status']}`",
        f"- 关系层判断：`{result['relation_status']}`",
        f"- 阶段层判断：`{result['stage_status']}`",
        f"- 分析文件数：`{result['profile_count']}`",
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
    if result["profile_failures"]:
        lines.extend(
            [
                "",
                "## 配角卡未达标项",
                "",
            ]
        )
        for item in result["profile_failures"]:
            lines.append(f"- `{item}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate durable outputs for the supporting-cast layer.")
    parser.add_argument("--workspace", required=True, help="Workspace directory to validate.")
    parser.add_argument("--novel-name", required=True, help="Novel name used in file naming.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    parser.add_argument("--no-write-report", action="store_true", help="Do not persist the markdown report.")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.exists():
        raise SystemExit(f"workspace not found: {workspace}")

    status_path = latest_status_file(workspace)
    profile_files = detect_profile_files(workspace)
    index_path = workspace / "supporting-cast" / "index.md"

    files = {
        "project_entry": workspace / "README.md",
        "handoff": status_path,
        "candidate_pool": workspace / "supporting-cast" / "Top10候选池初评.md",
        "ai_review": workspace / f"{args.novel_name}-重要配角AI复核结论.md",
        "top10_table": workspace / f"{args.novel_name}-重要配角Top10总表.md",
        "relation_map": workspace / f"{args.novel_name}-重要配角与主角关系图.md",
        "stage_distribution": workspace / f"{args.novel_name}-重要配角阶段作用分布.md",
        "index": index_path,
    }

    checks = {
        "project_entry": content_check(files["project_entry"], ["重要配角", "AI复核", "cards 初评"], minimum=2, min_chars=180),
        "handoff": content_check(files["handoff"], ["当前结论", "Top3 初评候选", "AI 复核"], minimum=2, min_chars=180),
        "candidate_pool": content_check(files["candidate_pool"], ["候选池总表", "card 初评分", "初步结构定位", "初评理由"], minimum=4, min_chars=900),
        "ai_review": content_check(files["ai_review"], ["最终入选 Top10", "落选但接近 Top10", "调榜说明", "最终理由"], minimum=4, min_chars=900),
        "top10_table": content_check(files["top10_table"], ["Top 10 总表", "AI复核结论", "最终去留", "入选理由"], minimum=4, min_chars=700),
        "relation_map": content_check(files["relation_map"], ["关系线总判断", "与主角关系", "关系定位", "如何改写主角路径"], minimum=4, min_chars=700),
        "stage_distribution": content_check(files["stage_distribution"], ["阶段层总判断", "关键阶段", "阶段作用判断", "阶段分布"], minimum=4, min_chars=650),
        "index": content_check(files["index"], ["Top10 文件", "候选池初评", "AI复核结论", "推荐阅读顺序"], minimum=4, min_chars=220),
    }

    checks["profiles"], profile_failures = validate_profiles(profile_files)

    top10_ready = (
        checks["candidate_pool"]["content_ok"]
        and checks["ai_review"]["content_ok"]
        and checks["top10_table"]["content_ok"]
        and checks["index"]["content_ok"]
        and checks["profiles"]["content_ok"]
    )
    ai_review_ready = checks["ai_review"]["content_ok"]
    relation_ready = checks["relation_map"]["content_ok"]
    stage_ready = checks["stage_distribution"]["content_ok"]

    result = {
        "workspace": str(workspace),
        "novel_name": args.novel_name,
        "top10_status": "重要配角 Top10 已完成 AI 定榜" if top10_ready else "重要配角 Top10 仍不足",
        "ai_review_status": "AI 复核结论已可用" if ai_review_ready else "AI 复核结论仍不足",
        "relation_status": "配角与主角关系已可用" if relation_ready else "配角与主角关系仍不足",
        "stage_status": "配角阶段作用层已可用" if stage_ready else "配角阶段作用层仍不足",
        "profile_count": len(profile_files),
        "profile_failures": profile_failures,
        "checks": checks,
        "status_file": str(status_path) if status_path else None,
        "files": {
            **{key: str(path.resolve()) for key, path in files.items() if path and path.exists()},
            "profiles": str((workspace / "supporting-cast").resolve()) if profile_files else "",
        },
    }

    report_text = markdown_report(args.novel_name, workspace, result)
    report_path = workspace / f"{args.novel_name}-重要配角层校验报告.md"
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
