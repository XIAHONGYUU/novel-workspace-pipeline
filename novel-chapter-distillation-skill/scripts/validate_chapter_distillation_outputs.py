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
    "当前仅完成了章节蒸馏骨架工作区初始化",
)

REQUIRED_CORE_KEYS = (
    "project_entry",
    "handoff",
    "manifest",
    "chapter_skeleton",
    "stage_skeleton",
    "calibration_anchors",
)

CHAPTER_SECTION_RE = re.compile(r"^##\s+(.+)$", flags=re.MULTILINE)


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


def manifest_check(path: Path | None) -> dict:
    if not path or not path.exists():
        return {"exists": False, "content_ok": False, "reason": "missing"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"exists": True, "content_ok": False, "reason": "invalid_json"}

    chapter_count = payload.get("chapter_count")
    chapters = payload.get("chapters")
    if not isinstance(chapter_count, int) or chapter_count < 1:
        return {"exists": True, "content_ok": False, "reason": "invalid_chapter_count"}
    if not isinstance(chapters, list) or len(chapters) != chapter_count:
        return {"exists": True, "content_ok": False, "reason": "chapter_list_mismatch"}
    return {"exists": True, "content_ok": True, "reason": "ok", "chapter_count": chapter_count}


def chapter_skeleton_check(path: Path | None, manifest: dict) -> dict:
    if not path or not path.exists():
        return {"exists": False, "content_ok": False, "reason": "missing"}
    text = read_text(path)
    if len(text.strip()) < 300:
        return {"exists": True, "content_ok": False, "reason": "too_short"}

    placeholders = placeholder_hits(text)
    if len(placeholders) >= 2 or placeholder_score(text) >= 3:
        return {
            "exists": True,
            "content_ok": False,
            "reason": "placeholder_detected",
            "placeholder_hits": placeholders[:5],
        }

    expected_count = manifest.get("chapter_count")
    section_titles = CHAPTER_SECTION_RE.findall(text)
    if not isinstance(expected_count, int) or expected_count < 1:
        return {"exists": True, "content_ok": False, "reason": "manifest_missing"}
    if len(section_titles) < expected_count:
        return {
            "exists": True,
            "content_ok": False,
            "reason": f"chapter_coverage_insufficient:{len(section_titles)}/{expected_count}",
        }

    required_fields = [
        "本章核心推进",
        "主角 / 核心视角状态",
        "关键新信息 / 新设定",
        "关系 / 局势变化",
        "本章结构功能",
        "章末钩子 / 遗留问题",
    ]
    if not has_keywords(text, required_fields, minimum=6):
        return {"exists": True, "content_ok": False, "reason": "fields_missing"}
    return {"exists": True, "content_ok": True, "reason": "ok", "chapter_sections": len(section_titles)}


def markdown_report(novel_name: str, workspace: Path, result: dict) -> str:
    lines = [
        f"# 《{novel_name}》章节蒸馏校验报告",
        "",
        f"- 工作区：`{workspace}`",
        f"- 章节骨架判断：`{result['skeleton_status']}`",
        f"- 校准锚点判断：`{result['calibration_status']}`",
        f"- 已存在层数：`{result['existing_count']}/6`",
        f"- 内容达标层数：`{result['content_ok_count']}/6`",
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
    parser = argparse.ArgumentParser(description="Validate durable outputs for a chapter-distillation workspace.")
    parser.add_argument("--workspace", required=True, help="Workspace directory to validate.")
    parser.add_argument("--novel-name", required=True, help="Novel name used in file naming.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a markdown report.")
    parser.add_argument("--no-write-report", action="store_true", help="Do not persist the markdown report.")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.exists():
        raise SystemExit(f"workspace not found: {workspace}")

    status_path = latest_status_file(workspace)
    manifest = manifest_check(workspace / "chapter-distillation-manifest.json")
    checks = {
        "project_entry": content_check(workspace / "README.md", ["章节蒸馏", "工作区", "当前结构"], minimum=2),
        "handoff": content_check(status_path, ["当前结论", "下次开始时建议先看", "一句话交接"], minimum=2),
        "manifest": manifest,
        "chapter_skeleton": chapter_skeleton_check(workspace / f"{args.novel_name}-章节蒸馏骨架.md", manifest),
        "stage_skeleton": content_check(
            workspace / f"{args.novel_name}-阶段骨架与换挡草图.md",
            ["总判断", "阶段 1", "阶段 2", "换挡理由"],
            minimum=4,
            min_chars=180,
        ),
        "calibration_anchors": content_check(
            workspace / f"{args.novel_name}-校准与验证锚点.md",
            ["开篇承诺锚点", "第一次重大换挡锚点", "中段校准锚点", "后续 skill 应如何复用"],
            minimum=4,
            min_chars=180,
        ),
    }

    existing_count = sum(1 for value in checks.values() if value["exists"])
    content_ok_count = sum(1 for value in checks.values() if value["content_ok"])
    required_core_ok_count = sum(1 for key in REQUIRED_CORE_KEYS if checks[key]["content_ok"])

    skeleton_status = "章节骨架仍不足"
    if checks["manifest"]["content_ok"] and checks["chapter_skeleton"]["content_ok"]:
        skeleton_status = "章节骨架已形成"

    calibration_status = "校准锚点仍不足"
    if checks["stage_skeleton"]["content_ok"] and checks["calibration_anchors"]["content_ok"]:
        calibration_status = "校准锚点已可用"

    result = {
        "workspace": str(workspace),
        "novel_name": args.novel_name,
        "skeleton_status": skeleton_status,
        "calibration_status": calibration_status,
        "existing_count": existing_count,
        "content_ok_count": content_ok_count,
        "required_core_ok_count": required_core_ok_count,
        "checks": checks,
        "status_file": str(status_path) if status_path else None,
    }

    report_text = markdown_report(args.novel_name, workspace, result)
    report_path = workspace / f"{args.novel_name}-章节蒸馏校验报告.md"
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
