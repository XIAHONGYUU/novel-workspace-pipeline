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
)

REQUIRED_KEYS = (
    "top10_table",
    "relation_map",
    "stage_distribution",
    "index",
    "profiles",
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
    if len(placeholders) >= 2 or placeholder_score(text) >= 4:
        return {
            "exists": True,
            "content_ok": False,
            "reason": "placeholder_detected",
            "placeholder_hits": placeholders[:5],
        }
    if not has_keywords(text, keywords, minimum):
        return {"exists": True, "content_ok": False, "reason": "keywords_missing"}
    return {"exists": True, "content_ok": True, "reason": "ok"}


def detect_profile_files(workspace: Path) -> list[Path]:
    return sorted((workspace / "supporting-cast").glob("*-配角分析.md"))


def markdown_report(novel_name: str, workspace: Path, result: dict) -> str:
    lines = [
        f"# 《{novel_name}》重要配角层校验报告",
        "",
        f"- 工作区：`{workspace}`",
        f"- Top10 判断：`{result['top10_status']}`",
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
        "top10_table": workspace / f"{args.novel_name}-重要配角Top10总表.md",
        "relation_map": workspace / f"{args.novel_name}-重要配角与主角关系图.md",
        "stage_distribution": workspace / f"{args.novel_name}-重要配角阶段作用分布.md",
        "index": index_path,
    }

    checks = {
        "project_entry": content_check(files["project_entry"], ["重要配角", "Top10", "supporting-cast"], minimum=2, min_chars=120),
        "handoff": content_check(files["handoff"], ["当前结论", "Top3 配角候选", "一句话交接"], minimum=2, min_chars=160),
        "top10_table": content_check(files["top10_table"], ["Top 10", "综合分", "结构角色", "入选理由"], minimum=3, min_chars=500),
        "relation_map": content_check(files["relation_map"], ["关系线总判断", "与主角关系", "结构角色"], minimum=3, min_chars=500),
        "stage_distribution": content_check(files["stage_distribution"], ["阶段层总判断", "阶段分布", "阶段作用判断"], minimum=3, min_chars=400),
        "index": content_check(files["index"], ["Top10 文件", "Top 1"], minimum=2, min_chars=120),
    }

    profiles_ok = len(profile_files) >= 10
    profiles_text = "\n".join(read_text(path) for path in profile_files[:10])
    checks["profiles"] = {
        "exists": bool(profile_files),
        "content_ok": profiles_ok and has_keywords(profiles_text, ["结构角色", "与主角关系", "关键阶段与事件"], minimum=3),
        "reason": "ok" if profiles_ok else "missing_profiles",
    }
    if profile_files and not checks["profiles"]["content_ok"]:
        checks["profiles"]["reason"] = "keywords_missing"

    top10_ready = checks["top10_table"]["content_ok"] and checks["index"]["content_ok"] and checks["profiles"]["content_ok"]
    relation_ready = checks["relation_map"]["content_ok"]
    stage_ready = checks["stage_distribution"]["content_ok"]

    result = {
        "workspace": str(workspace),
        "novel_name": args.novel_name,
        "top10_status": "重要配角 Top10 已明确" if top10_ready else "重要配角 Top10 仍不足",
        "relation_status": "配角与主角关系已可用" if relation_ready else "配角与主角关系仍不足",
        "stage_status": "配角阶段作用层已可用" if stage_ready else "配角阶段作用层仍不足",
        "profile_count": len(profile_files),
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
