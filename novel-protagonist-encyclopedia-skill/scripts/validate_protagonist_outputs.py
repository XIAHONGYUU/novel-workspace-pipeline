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
    "当前仅完成了主角百科工作区初始化",
)

REQUIRED_SKELETON_KEYS = (
    "startup_checklist",
    "anchor",
    "stage_outline",
    "final_card",
    "index",
)

REQUIRED_SYSTEM_KEYS = (
    "core_overview",
    "essence_summary",
)


def latest_status_file(workspace: Path) -> Path | None:
    candidates = sorted(workspace.glob("工作状态-*.md"))
    return candidates[-1] if candidates else None


def read_text(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def detect_protagonist_name(workspace: Path) -> str | None:
    final_cards = sorted(workspace.glob("*-最终人物卡.md"))
    if final_cards:
        return final_cards[0].stem.removesuffix("-最终人物卡")
    indexes = sorted(workspace.glob("*-词条总索引.md"))
    if indexes:
        return indexes[0].stem.removesuffix("-词条总索引")
    return None


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
        f"# 《{novel_name}》主角百科校验报告",
        "",
        f"- 工作区：`{workspace}`",
        f"- 主角名：`{result['protagonist_name'] or '未识别'}`",
        f"- 骨架判断：`{result['skeleton_status']}`",
        f"- 体系闭环判断：`{result['system_status']}`",
        f"- 已存在层数：`{result['existing_count']}/9`",
        f"- 内容达标层数：`{result['content_ok_count']}/9`",
        f"- 骨架关键项：`{result['required_skeleton_ok_count']}/{len(REQUIRED_SKELETON_KEYS)}`",
        f"- 体系关键项：`{result['required_system_ok_count']}/{len(REQUIRED_SYSTEM_KEYS)}`",
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
    parser = argparse.ArgumentParser(description="Validate durable outputs for a protagonist-encyclopedia workspace.")
    parser.add_argument("--workspace", required=True, help="Workspace directory to validate.")
    parser.add_argument("--novel-name", required=True, help="Novel name used in file naming.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a markdown report.")
    parser.add_argument("--no-write-report", action="store_true", help="Do not persist the markdown report.")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.exists():
        raise SystemExit(f"workspace not found: {workspace}")

    protagonist_name = detect_protagonist_name(workspace)
    status_path = latest_status_file(workspace)

    files = {
        "project_entry": workspace / "README.md",
        "handoff": status_path,
        "startup_checklist": workspace / f"{args.novel_name}-项目启动清单.md",
        "anchor": workspace / f"{args.novel_name}-主角锚点与骨架.md",
        "stage_outline": workspace / f"{args.novel_name}-整书粗阶段划分.md",
        "final_card": workspace / f"{protagonist_name}-最终人物卡.md" if protagonist_name else None,
        "index": workspace / f"{protagonist_name}-词条总索引.md" if protagonist_name else None,
        "core_overview": workspace / f"{protagonist_name}-核心体系总览.md" if protagonist_name else None,
        "essence_summary": workspace / f"{args.novel_name}-全书精华总结.md",
    }

    checks = {
        "project_entry": content_check(files["project_entry"], ["主角", "工作区", "当前结构"], minimum=2),
        "handoff": content_check(files["handoff"], ["当前结论", "下次开始时建议先看", "一句话交接"], minimum=2),
        "startup_checklist": content_check(
            files["startup_checklist"],
            ["体系闭环 Checklist", "当前已达到", "首轮执行顺序"],
            minimum=3,
            min_chars=180,
        ),
        "anchor": content_check(
            files["anchor"],
            ["主角锚点", "骨架", "身份", "成长"],
            minimum=3,
            min_chars=220,
        ),
        "stage_outline": content_check(
            files["stage_outline"],
            ["阶段", "主角状态", "主要矛盾", "地点"],
            minimum=3,
            min_chars=220,
        ),
        "final_card": content_check(
            files["final_card"],
            ["基本信息", "身份概述", "核心能力", "成长阶段", "最终结论"],
            minimum=4,
            min_chars=320,
        ),
        "index": content_check(
            files["index"],
            ["当前判定", "推荐阅读顺序", "一级词条", "已完成的核心二级词条"],
            minimum=4,
            min_chars=400,
        ),
        "core_overview": content_check(
            files["core_overview"],
            ["核心体系", "总判断", "最终结论", "主干词条"],
            minimum=3,
            min_chars=260,
        ),
        "essence_summary": content_check(
            files["essence_summary"],
            ["一句话定性", "最核心写的是什么", "精华", "最终结论"],
            minimum=3,
            min_chars=260,
        ),
    }

    aggregate_text = "\n".join(read_text(path) for path in files.values() if path)
    skeleton_ready = all(checks[key]["content_ok"] for key in REQUIRED_SKELETON_KEYS)
    system_ready = skeleton_ready and all(checks[key]["content_ok"] for key in REQUIRED_SYSTEM_KEYS)

    if "骨架完成" not in aggregate_text:
        skeleton_ready = False
    if "体系闭环完成" not in aggregate_text:
        system_ready = False

    skeleton_status = "骨架完成" if skeleton_ready else "骨架仍不足"
    system_status = "体系闭环完成（主干闭环版）" if system_ready else "体系闭环仍不足"

    result = {
        "workspace": str(workspace),
        "novel_name": args.novel_name,
        "protagonist_name": protagonist_name,
        "skeleton_status": skeleton_status,
        "system_status": system_status,
        "existing_count": sum(1 for value in checks.values() if value["exists"]),
        "content_ok_count": sum(1 for value in checks.values() if value["content_ok"]),
        "required_skeleton_ok_count": sum(1 for key in REQUIRED_SKELETON_KEYS if checks[key]["content_ok"]),
        "required_system_ok_count": sum(1 for key in REQUIRED_SYSTEM_KEYS if checks[key]["content_ok"]),
        "checks": checks,
        "status_file": str(status_path) if status_path else None,
        "files": {key: str(path.resolve()) for key, path in files.items() if path and path.exists()},
    }

    report_text = markdown_report(args.novel_name, workspace, result)
    report_path = workspace / f"{args.novel_name}-主角百科校验报告.md"
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
