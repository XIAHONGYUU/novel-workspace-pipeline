#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def latest_status_file(workspace: Path) -> Path | None:
    candidates = sorted(workspace.glob("工作状态-*.md"))
    return candidates[-1] if candidates else None


def find_first(workspace: Path, patterns: list[str]) -> Path | None:
    for pattern in patterns:
        matches = sorted(workspace.glob(pattern))
        if matches:
            return matches[0]
    return None


def read_text(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def has_keywords(text: str, keywords: list[str], minimum: int = 1) -> bool:
    hits = sum(1 for keyword in keywords if keyword in text)
    return hits >= minimum


def content_check(path: Path | None, keywords: list[str], minimum: int = 1, min_chars: int = 80) -> dict:
    if not path:
        return {"exists": False, "content_ok": False, "reason": "missing"}
    text = read_text(path)
    if len(text.strip()) < min_chars:
        return {"exists": True, "content_ok": False, "reason": "too_short"}
    if not has_keywords(text, keywords, minimum):
        return {"exists": True, "content_ok": False, "reason": "keywords_missing"}
    return {"exists": True, "content_ok": True, "reason": "ok"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate durable outputs for a novel outline-analysis workspace.")
    parser.add_argument("--workspace", required=True, help="Workspace directory to validate.")
    parser.add_argument("--novel-name", required=True, help="Novel name used in file naming.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a markdown report.")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.exists():
        raise SystemExit(f"workspace not found: {workspace}")

    status_path = latest_status_file(workspace)
    protagonist_path = find_first(
        workspace,
        [
            "*-最终人物卡.md",
            f"{args.novel_name}-主角结构摘要.md",
            "*主角结构摘要.md",
        ],
    )
    readme_path = workspace / "README.md"
    relation_path = workspace / f"{args.novel_name}-核心配角与主角关系.md"
    overview_path = workspace / f"{args.novel_name}-大纲总览.md"
    stages_path = workspace / f"{args.novel_name}-阶段与篇章拆分.md"
    lines_path = workspace / f"{args.novel_name}-主线支线与冲突地图.md"
    conflicts_path = workspace / f"{args.novel_name}-核心冲突点与爆发点.md"
    transitions_path = workspace / f"{args.novel_name}-时间与地点转折.md"
    climax_path = workspace / f"{args.novel_name}-高潮节奏与收束诊断.md"
    issues_path = workspace / f"{args.novel_name}-结构问题与修改建议.md"

    checks = {
        "project_entry": content_check(readme_path, ["当前结构", "当前入口", "工作区"], minimum=1),
        "handoff": content_check(status_path, ["当前结论", "下次开始时建议先看", "一句话交接"], minimum=2),
        "protagonist_layer": content_check(protagonist_path, ["主角", "结构角色", "终局"], minimum=2),
        "core_supporting_relations": content_check(relation_path, ["核心配角", "关系", "主角"], minimum=2),
        "overview": content_check(overview_path, ["premise", "主线", "总判断"], minimum=2),
        "stages": content_check(stages_path, ["阶段", "边界", "主冲突"], minimum=2),
        "lines": content_check(lines_path, ["主线", "支线", "桥接"], minimum=2),
        "conflicts": content_check(conflicts_path, ["冲突", "爆发", "阶段"], minimum=2),
        "time_place": content_check(transitions_path, ["时间", "地点", "转折"], minimum=2),
        "climax_pacing": content_check(climax_path, ["开篇", "中段", "高潮", "结尾"], minimum=3),
        "issues_revision": content_check(issues_path, ["优点", "问题", "修改"], minimum=2),
    }

    existing_count = sum(1 for value in checks.values() if value["exists"])
    content_ok_count = sum(1 for value in checks.values() if value["content_ok"])

    common_status = "共性标准部分覆盖"
    if content_ok_count >= 10:
        common_status = "共性标准已覆盖"

    specific_modules = []
    overview_text = read_text(overview_path)
    issues_text = read_text(issues_path)
    combined = overview_text + "\n" + issues_text
    candidate_lines = re.findall(r"^- .+$", combined, flags=re.MULTILINE)
    for line in candidate_lines:
        if any(
            token in line
            for token in ["外挂", "阵营", "血脉", "梦魇", "世界石", "规则", "多世界", "终局", "关系", "反派"]
        ):
            specific_modules.append(line.strip()[2:].strip())
    specific_modules = list(dict.fromkeys(specific_modules))
    specific_status = "单书特性仍不足"
    if 2 <= len(specific_modules) <= 8:
        specific_status = "单书特性已明确"

    result = {
        "workspace": str(workspace),
        "novel_name": args.novel_name,
        "common_status": common_status,
        "specific_status": specific_status,
        "existing_count": existing_count,
        "content_ok_count": content_ok_count,
        "checks": checks,
        "specific_module_candidates": specific_modules[:8],
        "status_file": str(status_path) if status_path else None,
        "protagonist_file": str(protagonist_path) if protagonist_path else None,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(f"# 《{args.novel_name}》大纲分析校验报告\n")
    print(f"- 工作区：`{workspace}`")
    print(f"- 共性判断：`{common_status}`")
    print(f"- 单书特性判断：`{specific_status}`")
    print(f"- 已存在层数：`{existing_count}/11`")
    print(f"- 内容达标层数：`{content_ok_count}/11`\n")
    print("## 分项结果\n")
    for name, value in checks.items():
        status = "通过" if value["content_ok"] else ("仅存在" if value["exists"] else "缺失")
        print(f"- `{name}`：{status}（{value['reason']}）")
    print("\n## 单书特性候选\n")
    if specific_modules:
        for item in specific_modules[:8]:
            print(f"- {item}")
    else:
        print("- 未检测到稳定的单书特性候选")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
