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
    "当前仅完成了大纲分析工作区初始化",
)

REQUIRED_CORE_KEYS = (
    "protagonist_layer",
    "overview",
    "stages",
    "lines",
    "conflicts",
    "climax_pacing",
    "issues_revision",
)

FEATURE_SECTION_RE = re.compile(r"^##\s+单书特性\s*$", flags=re.MULTILINE)
FEATURE_ITEM_RE = re.compile(r"^###\s+(.+)$", flags=re.MULTILINE)


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


def extract_feature_items(path: Path | None) -> tuple[bool, list[str]]:
    text = read_text(path)
    if not text or not FEATURE_SECTION_RE.search(text):
        return False, []
    items = [item.strip() for item in FEATURE_ITEM_RE.findall(text)]
    return True, items[:8]


def markdown_report(novel_name: str, workspace: Path, result: dict) -> str:
    lines = [
        f"# 《{novel_name}》大纲分析校验报告",
        "",
        f"- 工作区：`{workspace}`",
        f"- 共性判断：`{result['common_status']}`",
        f"- 单书特性判断：`{result['feature_status']}`",
        f"- 已存在层数：`{result['existing_count']}/11`",
        f"- 内容达标层数：`{result['content_ok_count']}/11`",
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
    if result["feature_items"]:
        lines.extend(
            [
                "",
                "## 单书特性结构",
                "",
                f"- 检测到 `## 单书特性` 的文件：{Path(result['feature_file']).name}",
            ]
        )
        lines.extend(f"- {item}" for item in result["feature_items"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate durable outputs for an outline-analysis workspace.")
    parser.add_argument("--workspace", required=True, help="Workspace directory to validate.")
    parser.add_argument("--novel-name", required=True, help="Novel name used in file naming.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a markdown report.")
    parser.add_argument("--no-write-report", action="store_true", help="Do not persist the markdown report.")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.exists():
        raise SystemExit(f"workspace not found: {workspace}")

    status_path = latest_status_file(workspace)
    files = {
        "project_entry": workspace / "README.md",
        "handoff": status_path,
        "protagonist_layer": workspace / f"{args.novel_name}-主角锚点与骨架.md",
        "core_supporting_relations": workspace / f"{args.novel_name}-核心配角与主角关系.md",
        "overview": workspace / f"{args.novel_name}-大纲总览.md",
        "stages": workspace / f"{args.novel_name}-阶段与篇章拆分.md",
        "lines": workspace / f"{args.novel_name}-主线支线与冲突地图.md",
        "conflicts": workspace / f"{args.novel_name}-核心冲突点与爆发点.md",
        "time_place": workspace / f"{args.novel_name}-时间与地点转折.md",
        "climax_pacing": workspace / f"{args.novel_name}-高潮节奏与收束诊断.md",
        "issues_revision": workspace / f"{args.novel_name}-结构问题与修改建议.md",
    }

    checks = {
        "project_entry": content_check(files["project_entry"], ["大纲", "工作区", "当前结构"], minimum=2),
        "handoff": content_check(files["handoff"], ["当前结论", "下次开始时建议先看", "一句话交接"], minimum=2),
        "protagonist_layer": content_check(
            files["protagonist_layer"],
            ["主角锚点", "身份", "成长", "阶段"],
            minimum=3,
            min_chars=220,
        ),
        "core_supporting_relations": content_check(
            files["core_supporting_relations"],
            ["核心配角", "主角关系", "作用", "阶段"],
            minimum=3,
            min_chars=180,
        ),
        "overview": content_check(
            files["overview"],
            ["核心 premise", "结构类型", "全书主线一句话", "整书总判断"],
            minimum=4,
            min_chars=260,
        ),
        "stages": content_check(
            files["stages"],
            ["阶段", "阶段边界成立原因", "阶段主冲突", "主要时间 / 地点转折"],
            minimum=4,
            min_chars=260,
        ),
        "lines": content_check(
            files["lines"],
            ["核心主线", "重要支线", "桥接线", "主线支线总判断"],
            minimum=4,
            min_chars=240,
        ),
        "conflicts": content_check(
            files["conflicts"],
            ["根本主冲突", "阶段性冲突", "关键爆发点", "冲突层总判断"],
            minimum=4,
            min_chars=180,
        ),
        "time_place": content_check(
            files["time_place"],
            ["时间转折", "地点转折", "联合判断"],
            minimum=3,
            min_chars=180,
        ),
        "climax_pacing": content_check(
            files["climax_pacing"],
            ["开篇判断", "中段判断", "高潮判断", "结尾判断", "总诊断"],
            minimum=4,
            min_chars=240,
        ),
        "issues_revision": content_check(
            files["issues_revision"],
            ["结构优点", "结构问题", "第一优先修改项", "轻修建议", "总建议"],
            minimum=4,
            min_chars=220,
        ),
    }

    feature_found, feature_items = extract_feature_items(files["overview"])
    feature_status = "单书特性已明确" if feature_found and feature_items else "单书特性仍不足"
    common_status = "共性标准已覆盖" if all(checks[key]["content_ok"] for key in REQUIRED_CORE_KEYS) else "共性标准仍不足"

    result = {
        "workspace": str(workspace),
        "novel_name": args.novel_name,
        "common_status": common_status,
        "feature_status": feature_status,
        "existing_count": sum(1 for value in checks.values() if value["exists"]),
        "content_ok_count": sum(1 for value in checks.values() if value["content_ok"]),
        "required_core_ok_count": sum(1 for key in REQUIRED_CORE_KEYS if checks[key]["content_ok"]),
        "checks": checks,
        "status_file": str(status_path) if status_path else None,
        "feature_file": str(files["overview"].resolve()) if feature_found else None,
        "feature_items": feature_items,
        "files": {key: str(path.resolve()) for key, path in files.items() if path and path.exists()},
    }

    report_text = markdown_report(args.novel_name, workspace, result)
    report_path = workspace / f"{args.novel_name}-大纲分析校验报告.md"
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
