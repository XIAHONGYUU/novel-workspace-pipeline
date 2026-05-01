#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
from datetime import date, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
LAYER_ORDER = (
    "chapter-distillation",
    "opening",
    "protagonist",
    "outline",
    "highlight",
)
LAYER_TO_SKILL = {
    "chapter-distillation": "novel-chapter-distillation",
    "opening": "novel-opening-analysis",
    "protagonist": "novel-protagonist-encyclopedia",
    "outline": "novel-outline-analysis",
    "highlight": "novel-highlight-scenes-analysis",
}
LAYER_LABELS = {
    "chapter-distillation": "章节蒸馏层",
    "opening": "黄金前三章层",
    "protagonist": "主角百科层",
    "outline": "整书大纲层",
    "highlight": "剧情高光层",
}
CHECK_LABELS = {
    "chapter-distillation": {
        "manifest": "章节蒸馏 manifest",
        "chapter_skeleton": "章节蒸馏骨架",
        "stage_skeleton": "阶段骨架与换挡草图",
        "calibration_anchors": "校准与验证锚点",
    },
    "opening": {
        "total_judgment": "黄金前三章总判断",
        "chapter_1": "第一章拆解",
        "chapter_2": "第二章拆解",
        "chapter_3": "第三章拆解",
        "hook_promise": "开篇钩子与读者承诺",
        "issues_revision": "开篇问题与修改建议",
    },
    "protagonist": {
        "startup_checklist": "项目启动清单",
        "anchor": "主角锚点与骨架",
        "stage_outline": "整书粗阶段划分",
        "final_card": "最终人物卡",
        "index": "词条总索引",
        "core_overview": "核心体系总览",
        "essence_summary": "全书精华总结",
    },
    "outline": {
        "protagonist_layer": "主角层承接文件",
        "core_supporting_relations": "核心配角与主角关系",
        "overview": "大纲总览",
        "stages": "阶段与篇章拆分",
        "lines": "主线支线与冲突地图",
        "conflicts": "核心冲突点与爆发点",
        "time_place": "时间与地点转折",
        "climax_pacing": "高潮节奏与收束诊断",
        "issues_revision": "结构问题与修改建议",
        "stage_split": "阶段与篇章拆分",
        "plot_map": "主线支线与冲突地图",
        "climax": "高潮节奏与收束诊断",
        "revision": "结构问题与修改建议",
    },
    "highlight": {
        "top10_table": "最吸引人的十个剧情细节总表",
        "mechanism": "剧情吸引力机制分析",
        "top10_breakdown": "Top10 细节逐条拆解",
        "distribution": "高光桥段分布与节奏判断",
        "pleasure_summary": "最强爽点痛点悬念点总结",
        "revision": "剧情高光改造建议",
    },
}
PLACEHOLDER_TOKENS = (
    "待补充",
    "待确认",
    "待定",
    "待完善",
    "TODO",
    "TBD",
    "占位",
    "placeholder",
)
VALIDATOR_SCRIPTS = {
    "chapter-distillation": REPO_ROOT
    / "novel-chapter-distillation-skill/scripts/validate_chapter_distillation_outputs.py",
    "opening": REPO_ROOT / "novel-opening-analysis-skill/scripts/validate_opening_outputs.py",
    "protagonist": REPO_ROOT / "novel-protagonist-encyclopedia-skill/scripts/validate_protagonist_outputs.py",
    "outline": REPO_ROOT / "novel-outline-analysis-skill/scripts/validate_outline_outputs.py",
    "highlight": REPO_ROOT / "novel-highlight-scenes-analysis-skill/scripts/validate_highlight_outputs.py",
}
INIT_SCRIPTS = {
    "chapter-distillation": REPO_ROOT
    / "novel-chapter-distillation-skill/scripts/init_chapter_distillation_workspace.py",
    "opening": REPO_ROOT / "novel-opening-analysis-skill/scripts/init_opening_workspace.py",
    "protagonist": REPO_ROOT / "novel-protagonist-encyclopedia-skill/scripts/init_workspace.py",
    "outline": REPO_ROOT / "novel-outline-analysis-skill/scripts/init_outline_workspace.py",
    "highlight": REPO_ROOT / "novel-highlight-scenes-analysis-skill/scripts/init_highlight_workspace.py",
}
LAYER_VALIDATED_TAGS = {
    "chapter-distillation": "章节蒸馏层校验通过",
    "opening": "黄金前三章分析层校验通过",
    "outline": "大纲分析层校验通过",
    "highlight": "剧情高光分析层校验通过",
}


def read_text(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def latest_status_file(workspace: Path) -> Path | None:
    candidates = sorted(workspace.glob("工作状态-*.md"))
    return candidates[-1] if candidates else None


def detect_novel_name(workspace: Path, explicit: str | None = None) -> str:
    if explicit:
        return explicit

    for path in (
        workspace / "README.md",
        latest_status_file(workspace),
        workspace / "项目启动清单.md",
    ):
        text = read_text(path)
        if not text:
            continue
        for pattern in (
            r"#\s*《(.+?)》",
            r"#\s*(.+?)\s*项目启动清单",
            r"#\s*(.+?)\s*工作状态",
        ):
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
    return workspace.name


def detect_protagonist_name(workspace: Path, explicit: str | None = None) -> str | None:
    if explicit:
        return explicit

    final_cards = sorted(workspace.glob("*-最终人物卡.md"))
    if final_cards:
        return final_cards[0].stem.removesuffix("-最终人物卡")

    indexes = sorted(workspace.glob("*-词条总索引.md"))
    if indexes:
        return indexes[0].stem.removesuffix("-词条总索引")
    return None


def find_source_files(workspace: Path) -> list[Path]:
    source_dir = workspace / "source"
    candidates: list[Path] = []
    if source_dir.exists():
        for pattern in ("*.md", "*.txt", "*.markdown", "*.docx"):
            candidates.extend(sorted(source_dir.glob(pattern)))
    return candidates


def preferred_source_file(workspace: Path) -> Path | None:
    files = find_source_files(workspace)
    if not files:
        return None
    suffix_priority = {
        ".md": 0,
        ".markdown": 1,
        ".txt": 2,
        ".docx": 3,
    }
    ranked = sorted(files, key=lambda path: (suffix_priority.get(path.suffix.lower(), 9), path.name))
    return ranked[0]


def estimate_source_size(workspace: Path) -> dict[str, Any]:
    files = find_source_files(workspace)
    total_bytes = sum(path.stat().st_size for path in files if path.exists())
    total_chars = 0
    for path in files:
        if path.suffix.lower() in {".md", ".txt", ".markdown"}:
            total_chars += len(read_text(path))
    is_long = total_chars >= 200_000 or total_bytes >= 800_000
    return {
        "files": [str(path) for path in files],
        "total_bytes": total_bytes,
        "estimated_chars": total_chars,
        "is_long_novel": is_long,
    }


def placeholder_hits(text: str) -> list[str]:
    hits = [token for token in PLACEHOLDER_TOKENS if token.lower() in text.lower()]
    hits.extend(
        line.strip()
        for line in re.findall(r"^\s*[-*]\s*(?:待补充|待确认|待定|待完善|TODO|TBD).*$", text, flags=re.MULTILINE)
    )
    return list(dict.fromkeys(hits))


def has_keywords(text: str, keywords: list[str], minimum: int = 1) -> bool:
    hits = sum(1 for keyword in keywords if keyword in text)
    return hits >= minimum


def content_check(path: Path | None, keywords: list[str], minimum: int = 1, min_chars: int = 120) -> dict[str, Any]:
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
    if keywords and not has_keywords(text, keywords, minimum):
        return {"exists": True, "content_ok": False, "reason": "keywords_missing"}
    return {"exists": True, "content_ok": True, "reason": "ok"}


def validator_result_to_layer_status(
    layer: str,
    result: dict[str, Any],
    workspace: Path,
    report_path: Path | None,
    status_file: Path | None,
) -> dict[str, Any]:
    if layer == "chapter-distillation":
        completion_label = "章节骨架已形成" if result.get("skeleton_status") == "章节骨架已形成" else "章节骨架仍不足"
        validated = (
            result.get("skeleton_status") == "章节骨架已形成"
            and result.get("calibration_status") == "校准锚点已可用"
        )
    elif layer == "opening":
        completion_label = result.get("opening_status", "开篇抓力仍不足")
        validated = (
            result.get("opening_status") == "开篇抓力已明确"
            and result.get("structure_status") == "前三章结构已拆清"
        )
    elif layer == "protagonist":
        completion_label = result.get("system_status") or result.get("skeleton_status") or "体系闭环仍不足"
        validated = result.get("skeleton_status") == "骨架完成"
    elif layer == "outline":
        completion_label = result.get("common_status", "共性标准仍不足")
        validated = result.get("common_status") == "共性标准已覆盖"
    elif layer == "highlight":
        completion_label = result.get("highlight_status", "高光桥段仍不足")
        validated = (
            result.get("highlight_status") == "高光桥段已明确"
            and result.get("mechanism_status") == "剧情吸引力机制已拆清"
        )
    else:
        completion_label = "未知"
        validated = False

    checks = result.get("checks", {})
    has_placeholders = any(bool(value.get("placeholder_hits")) for value in checks.values() if isinstance(value, dict))
    result_files = result.get("files", {})
    files: dict[str, str] = {}
    for key, value in checks.items():
        if not isinstance(value, dict) or not value.get("exists"):
            continue
        if key in result_files:
            files[key] = result_files[key]
            continue
        if key == "project_entry":
            files[key] = str((workspace / "README.md").resolve())
        elif key == "handoff" and status_file:
            files[key] = str(status_file.resolve())
        else:
            files[key] = str((workspace / _infer_layer_file_name(layer, key, result.get("novel_name", ""))).resolve())
    if report_path:
        files["validator_report"] = str(report_path)
    layer_specific_exists = any(
        value.get("exists")
        for key, value in checks.items()
        if isinstance(value, dict) and key not in {"project_entry", "handoff"}
    )
    return {
        "layer": layer,
        "label": LAYER_LABELS[layer],
        "exists": layer_specific_exists,
        "validated": validated,
        "has_placeholders": has_placeholders,
        "completion_label": completion_label,
        "reason": "validator",
        "files": files,
        "checks": checks,
        "validator_report": str(report_path) if report_path else None,
        "validator_summary": {
            key: value
            for key, value in result.items()
            if key
            not in {
                "checks",
                "workspace",
                "report_path",
                "status_file",
            }
        },
    }


def check_label(layer: str, key: str) -> str:
    return CHECK_LABELS.get(layer, {}).get(key, key)


def build_failed_checks(layer: str, item: dict[str, Any]) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    files = item.get("files", {})
    for key, value in item.get("checks", {}).items():
        if not isinstance(value, dict) or value.get("content_ok"):
            continue
        entry = {
            "check": key,
            "label": check_label(layer, key),
            "reason": value.get("reason", "unknown"),
            "file": files.get(key),
        }
        if value.get("placeholder_hits"):
            entry["placeholder_hits"] = value["placeholder_hits"][:5]
        failed.append(entry)
    return failed


def repair_target_for_failure(layer: str, failure: dict[str, Any]) -> str:
    label = failure["label"]
    reason = failure["reason"]
    if reason == "missing":
        return f"补齐 `{label}`，至少先从缺失补到可校验骨架。"
    if reason == "too_short":
        return f"扩写 `{label}`，把当前短骨架补成可判断正文。"
    if reason == "placeholder_detected":
        return f"替换 `{label}` 里的占位内容，补成明确结论和证据。"
    if reason == "keywords_missing":
        return f"补齐 `{label}` 的关键判断字段，避免只有摘要没有结论。"
    if reason == "fallback_exists_only":
        return f"把 `{label}` 从“只有文件存在”补到“内容可验证”。"
    return f"检查并修复 `{label}`，当前原因：`{reason}`。"


def augment_layer_status_for_repair(layer: str, item: dict[str, Any]) -> dict[str, Any]:
    failed_checks = build_failed_checks(layer, item)
    repair_targets = [repair_target_for_failure(layer, failure) for failure in failed_checks]
    repair_targets = list(dict.fromkeys(repair_targets))
    item["failed_checks"] = failed_checks
    item["repair_targets"] = repair_targets
    return item


def _infer_layer_file_name(layer: str, key: str, novel_name: str) -> str:
    if layer == "chapter-distillation":
        mapping = {
            "project_entry": "README.md",
            "handoff": latest_status_file_name(),
            "manifest": "chapter-distillation-manifest.json",
            "chapter_skeleton": f"{novel_name}-章节蒸馏骨架.md",
            "stage_skeleton": f"{novel_name}-阶段骨架与换挡草图.md",
            "calibration_anchors": f"{novel_name}-校准与验证锚点.md",
        }
        return mapping.get(key, key)
    if layer == "opening":
        mapping = {
            "project_entry": "README.md",
            "handoff": latest_status_file_name(),
            "total_judgment": f"{novel_name}-黄金前三章总判断.md",
            "chapter_1": f"{novel_name}-第一章拆解.md",
            "chapter_2": f"{novel_name}-第二章拆解.md",
            "chapter_3": f"{novel_name}-第三章拆解.md",
            "hook_promise": f"{novel_name}-开篇钩子与读者承诺.md",
            "issues_revision": f"{novel_name}-开篇问题与修改建议.md",
        }
        return mapping.get(key, key)
    if layer == "protagonist":
        mapping = {
            "project_entry": "README.md",
            "handoff": latest_status_file_name(),
            "startup_checklist": f"{novel_name}-项目启动清单.md",
            "anchor": f"{novel_name}-主角锚点与骨架.md",
            "stage_outline": f"{novel_name}-整书粗阶段划分.md",
            "essence_summary": f"{novel_name}-全书精华总结.md",
        }
        return mapping.get(key, key)
    if layer == "outline":
        mapping = {
            "project_entry": "README.md",
            "handoff": latest_status_file_name(),
            "protagonist_layer": f"{novel_name}-主角锚点与骨架.md",
            "core_supporting_relations": f"{novel_name}-核心配角与主角关系.md",
            "overview": f"{novel_name}-大纲总览.md",
            "stages": f"{novel_name}-阶段与篇章拆分.md",
            "lines": f"{novel_name}-主线支线与冲突地图.md",
            "conflicts": f"{novel_name}-核心冲突点与爆发点.md",
            "time_place": f"{novel_name}-时间与地点转折.md",
            "climax_pacing": f"{novel_name}-高潮节奏与收束诊断.md",
            "issues_revision": f"{novel_name}-结构问题与修改建议.md",
        }
        return mapping.get(key, key)
    if layer == "highlight":
        mapping = {
            "project_entry": "README.md",
            "handoff": latest_status_file_name(),
            "top10_table": f"{novel_name}-最吸引人的十个剧情细节总表.md",
            "mechanism": f"{novel_name}-剧情吸引力机制分析.md",
            "top10_breakdown": f"{novel_name}-Top10细节逐条拆解.md",
            "distribution": f"{novel_name}-高光桥段分布与节奏判断.md",
            "pleasure_summary": f"{novel_name}-最强爽点痛点悬念点总结.md",
            "revision": f"{novel_name}-剧情高光改造建议.md",
        }
        return mapping.get(key, key)
    return key


def latest_status_file_name() -> str:
    return "工作状态-YYYY-MM-DD.md"


def run_validator(layer: str, workspace: Path, novel_name: str, persist_report: bool = False) -> dict[str, Any] | None:
    script_path = VALIDATOR_SCRIPTS.get(layer)
    if not script_path or not script_path.exists():
        return None
    cmd = ["python3", str(script_path), "--workspace", str(workspace), "--novel-name", novel_name, "--json"]
    if not persist_report:
        cmd.append("--no-write-report")
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return {
            "layer": layer,
            "label": LAYER_LABELS[layer],
            "exists": False,
            "validated": False,
            "has_placeholders": False,
            "completion_label": "validator_failed",
            "reason": f"validator_failed:{proc.returncode}",
            "files": {},
            "checks": {},
            "validator_report": None,
            "validator_error": proc.stderr.strip() or proc.stdout.strip(),
        }
    raw = json.loads(proc.stdout)
    report_path = Path(raw["report_path"]) if raw.get("report_path") else None
    status_file = Path(raw["status_file"]) if raw.get("status_file") else None
    return validator_result_to_layer_status(layer, raw, workspace, report_path, status_file)


def run_command(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "ok": proc.returncode == 0,
    }


def build_layer_init_command(
    layer: str,
    workspace: Path,
    novel_name: str,
    protagonist_name: str | None = None,
    source: Path | None = None,
    force: bool = False,
    bootstrap_protagonist: bool = False,
    project_root: Path | None = None,
    tool_root: Path | None = None,
) -> list[str]:
    script_path = INIT_SCRIPTS.get(layer)
    if not script_path or not script_path.exists():
        raise FileNotFoundError(f"init script not found for layer {layer}: {script_path}")

    if layer == "chapter-distillation":
        cmd = ["python3", str(script_path), "--novel-name", novel_name, "--existing-workspace", str(workspace)]
        if source:
            cmd += ["--source", str(source)]
        if force:
            cmd.append("--force")
        return cmd

    if layer == "opening":
        cmd = ["python3", str(script_path), "--novel-name", novel_name, "--existing-workspace", str(workspace)]
        if source:
            cmd += ["--source", str(source)]
        if protagonist_name:
            cmd += ["--protagonist", protagonist_name]
        if force:
            cmd.append("--force")
        return cmd

    if layer == "highlight":
        cmd = ["python3", str(script_path), "--novel-name", novel_name, "--existing-workspace", str(workspace)]
        if source:
            cmd += ["--source", str(source)]
        if protagonist_name:
            cmd += ["--protagonist", protagonist_name]
        if force:
            cmd.append("--force")
        return cmd

    if layer == "outline":
        if not source:
            raise ValueError("outline init requires a source file")
        cmd = ["python3", str(script_path), "--novel-name", novel_name, "--workspace", str(workspace), "--source", str(source)]
        if protagonist_name:
            cmd += ["--protagonist", protagonist_name]
        if force:
            cmd.append("--force")
        return cmd

    if layer == "protagonist":
        cmd = [
            "python3",
            str(script_path),
            "--novel-name",
            novel_name,
            "--project-root",
            str((project_root or workspace.parent).resolve()),
            "--tool-root",
            str((tool_root or REPO_ROOT).resolve()),
            "--no-update-current-status",
        ]
        if source:
            cmd += ["--source", str(source)]
        if protagonist_name:
            cmd += ["--focus-name", protagonist_name]
        if not bootstrap_protagonist:
            cmd.append("--skip-bootstrap")
        return cmd

    raise ValueError(f"unsupported layer: {layer}")


def execute_layer_init(
    layer: str,
    workspace: Path,
    novel_name: str,
    protagonist_name: str | None = None,
    source: Path | None = None,
    force: bool = False,
    bootstrap_protagonist: bool = False,
    project_root: Path | None = None,
    tool_root: Path | None = None,
) -> dict[str, Any]:
    cmd = build_layer_init_command(
        layer,
        workspace,
        novel_name,
        protagonist_name=protagonist_name,
        source=source,
        force=force,
        bootstrap_protagonist=bootstrap_protagonist,
        project_root=project_root,
        tool_root=tool_root,
    )
    result = run_command(cmd)
    result["action"] = "init"
    result["layer"] = layer
    return result


def heuristic_protagonist_status(
    workspace: Path, novel_name: str, protagonist_name: str | None, status_path: Path | None
) -> dict[str, Any]:
    final_card = next(iter(sorted(workspace.glob("*-最终人物卡.md"))), None)
    index_file = next(iter(sorted(workspace.glob("*-词条总索引.md"))), None)
    core_overview = next(iter(sorted(workspace.glob("*-核心体系总览.md"))), None)
    files = {
        "startup_checklist": workspace / f"{novel_name}-项目启动清单.md",
        "anchor": workspace / f"{novel_name}-主角锚点与骨架.md",
        "stage_outline": workspace / f"{novel_name}-整书粗阶段划分.md",
        "final_card": final_card,
        "index": index_file,
        "core_overview": core_overview,
        "essence_summary": workspace / f"{novel_name}-全书精华总结.md",
    }
    checks = {
        "startup_checklist": content_check(files["startup_checklist"], ["体系闭环 Checklist", "首轮执行顺序"], minimum=2),
        "anchor": content_check(files["anchor"], ["主角锚点", "主角骨架", "身份"], minimum=2, min_chars=180),
        "stage_outline": content_check(
            files["stage_outline"], ["阶段", "主角状态", "主要矛盾"], minimum=3, min_chars=180
        ),
        "final_card": content_check(
            files["final_card"], ["基本信息", "身份概述", "核心能力", "成长阶段"], minimum=3, min_chars=300
        ),
        "index": content_check(files["index"], ["当前判定", "推荐阅读顺序", "一级词条"], minimum=3, min_chars=300),
        "core_overview": content_check(
            files["core_overview"], ["核心体系", "总判断", "最终结论"], minimum=3, min_chars=240
        ),
        "essence_summary": content_check(
            files["essence_summary"], ["一句话定性", "最核心写的是什么", "最终结论"], minimum=3, min_chars=240
        ),
    }

    aggregate_text = "\n".join(
        filter(
            None,
            [
                read_text(files["index"]),
                read_text(files["core_overview"]),
                read_text(files["essence_summary"]),
                read_text(status_path),
                read_text(workspace / "README.md"),
            ],
        )
    )
    skeleton_closed = "骨架完成" in aggregate_text and checks["final_card"]["content_ok"] and checks["index"]["content_ok"]
    system_closed = "体系闭环完成" in aggregate_text and checks["core_overview"]["content_ok"] and checks["essence_summary"]["content_ok"]

    has_placeholders = any(bool(value.get("placeholder_hits")) for value in checks.values())
    existing = any(value["exists"] for value in checks.values())
    completion_label = "未完成"
    if system_closed:
        completion_label = "体系闭环完成（主干闭环版）"
    elif skeleton_closed:
        completion_label = "骨架完成"

    resolved_files = {key: str(path) for key, path in files.items() if path and Path(path).exists()}
    return {
        "layer": "protagonist",
        "label": LAYER_LABELS["protagonist"],
        "exists": existing,
        "validated": skeleton_closed or system_closed,
        "has_placeholders": has_placeholders,
        "completion_label": completion_label,
        "reason": "heuristic",
        "files": resolved_files,
        "checks": checks,
        "validator_report": None,
        "validator_summary": {
            "skeleton_closed": skeleton_closed,
            "system_closed": system_closed,
        },
    }


def heuristic_outline_status(workspace: Path, novel_name: str, status_path: Path | None) -> dict[str, Any]:
    files = {
        "overview": workspace / f"{novel_name}-大纲总览.md",
        "stage_split": workspace / f"{novel_name}-阶段与篇章拆分.md",
        "plot_map": workspace / f"{novel_name}-主线支线与冲突地图.md",
        "climax": workspace / f"{novel_name}-高潮节奏与收束诊断.md",
        "revision": workspace / f"{novel_name}-结构问题与修改建议.md",
    }
    checks = {
        "overview": content_check(
            files["overview"], ["核心 premise", "总判断", "全书总结", "结构"], minimum=2, min_chars=220
        ),
        "stage_split": content_check(
            files["stage_split"], ["阶段", "主要矛盾", "阶段边界", "转折"], minimum=3, min_chars=220
        ),
        "plot_map": content_check(
            files["plot_map"], ["主线", "支线", "冲突", "交汇"], minimum=3, min_chars=220
        ),
        "climax": content_check(
            files["climax"], ["高潮", "转折点", "收束", "结尾"], minimum=3, min_chars=220
        ),
        "revision": content_check(
            files["revision"], ["最强", "最弱", "修改建议"], minimum=2, min_chars=180
        ),
    }
    aggregate_text = "\n".join(filter(None, [read_text(path) for path in files.values()] + [read_text(status_path)]))
    labels = [
        "开篇成立",
        "中段扩张有效",
        "高潮成立",
        "结尾收束完整",
        "主线清晰",
    ]
    label_hits = sum(1 for label in labels if label in aggregate_text)
    validated = all(value["content_ok"] for value in checks.values()) and label_hits >= 2
    completion_label = "大纲分析层已完成并通过启发式检查" if validated else "大纲分析层仍不足"
    return {
        "layer": "outline",
        "label": LAYER_LABELS["outline"],
        "exists": any(value["exists"] for value in checks.values()),
        "validated": validated,
        "has_placeholders": any(bool(value.get("placeholder_hits")) for value in checks.values()),
        "completion_label": completion_label,
        "reason": "heuristic",
        "files": {key: str(path) for key, path in files.items() if path.exists()},
        "checks": checks,
        "validator_report": None,
        "validator_summary": {"label_hits": label_hits},
    }


def detect_layer_status(
    workspace: Path,
    novel_name: str,
    protagonist_name: str | None,
    run_validators: bool = True,
    persist_validator_reports: bool = False,
) -> dict[str, Any]:
    status_path = latest_status_file(workspace)
    result: dict[str, Any] = {}
    for layer in LAYER_ORDER:
        if layer in VALIDATOR_SCRIPTS and run_validators:
            layer_status = run_validator(layer, workspace, novel_name, persist_report=persist_validator_reports)
            if layer_status is not None:
                result[layer] = layer_status
                continue
        if layer == "protagonist":
            result[layer] = heuristic_protagonist_status(workspace, novel_name, protagonist_name, status_path)
        elif layer == "outline":
            result[layer] = heuristic_outline_status(workspace, novel_name, status_path)
        elif layer == "chapter-distillation":
            manifest = workspace / "chapter-distillation-manifest.json"
            skeleton = workspace / f"{novel_name}-章节蒸馏骨架.md"
            stage = workspace / f"{novel_name}-阶段骨架与换挡草图.md"
            anchors = workspace / f"{novel_name}-校准与验证锚点.md"
            checks = {
                "manifest": {"exists": manifest.exists(), "content_ok": manifest.exists(), "reason": "fallback_exists_only"},
                "chapter_skeleton": content_check(skeleton, ["本章核心推进", "章末钩子"], minimum=2, min_chars=240),
                "stage_skeleton": content_check(stage, ["阶段", "换挡"], minimum=2, min_chars=180),
                "calibration_anchors": content_check(anchors, ["锚点", "校准"], minimum=2, min_chars=180),
            }
            result[layer] = {
                "layer": layer,
                "label": LAYER_LABELS[layer],
                "exists": any(v["exists"] for v in checks.values()),
                "validated": False,
                "has_placeholders": any(bool(v.get("placeholder_hits")) for v in checks.values()),
                "completion_label": "章节骨架仍不足",
                "reason": "fallback_heuristic",
                "files": {name: str(path) for name, path in {
                    "manifest": manifest,
                    "chapter_skeleton": skeleton,
                    "stage_skeleton": stage,
                    "calibration_anchors": anchors,
                }.items() if path.exists()},
                "checks": checks,
                "validator_report": None,
                "validator_summary": {},
            }
        elif layer == "opening":
            total = workspace / f"{novel_name}-黄金前三章总判断.md"
            checks = {
                "total_judgment": content_check(total, ["开篇", "结构"], minimum=2, min_chars=180),
            }
            result[layer] = {
                "layer": layer,
                "label": LAYER_LABELS[layer],
                "exists": checks["total_judgment"]["exists"],
                "validated": False,
                "has_placeholders": any(bool(v.get("placeholder_hits")) for v in checks.values()),
                "completion_label": "开篇抓力仍不足",
                "reason": "fallback_heuristic",
                "files": {"total_judgment": str(total)} if total.exists() else {},
                "checks": checks,
                "validator_report": None,
                "validator_summary": {},
            }
        elif layer == "highlight":
            top10 = workspace / f"{novel_name}-最吸引人的十个剧情细节总表.md"
            checks = {
                "top10_table": content_check(top10, ["高光", "总判断"], minimum=2, min_chars=180),
            }
            result[layer] = {
                "layer": layer,
                "label": LAYER_LABELS[layer],
                "exists": checks["top10_table"]["exists"],
                "validated": False,
                "has_placeholders": any(bool(v.get("placeholder_hits")) for v in checks.values()),
                "completion_label": "高光桥段仍不足",
                "reason": "fallback_heuristic",
                "files": {"top10_table": str(top10)} if top10.exists() else {},
                "checks": checks,
                "validator_report": None,
                "validator_summary": {},
            }
    for layer, item in result.items():
        result[layer] = augment_layer_status_for_repair(layer, item)
    return result


def recommend_next_action(layer_status: dict[str, Any], is_long_novel: bool) -> dict[str, Any]:
    existing_layers = [layer for layer in LAYER_ORDER if layer_status[layer]["exists"]]
    validated_layers = [layer for layer in LAYER_ORDER if layer_status[layer]["validated"]]
    optional_backfill_layers: list[str] = []

    for layer in LAYER_ORDER:
        status = layer_status[layer]
        if status["exists"] and not status["validated"]:
            return {
                "recommended_mode": "repair-existing",
                "recommended_next_layer": layer,
                "recommended_skill": LAYER_TO_SKILL[layer],
                "recommended_next_step": f"优先修复 {LAYER_LABELS[layer]}，因为该层已存在但尚未达标。",
                "optional_backfill_layers": optional_backfill_layers,
            }

    for idx, layer in enumerate(LAYER_ORDER):
        if layer_status[layer]["exists"]:
            continue
        later_validated = any(layer_status[later]["validated"] for later in LAYER_ORDER[idx + 1 :])
        if layer == "chapter-distillation":
            if not is_long_novel:
                continue
            if later_validated:
                optional_backfill_layers.append(layer)
                continue
        mode = "fresh" if not existing_layers else "extend-existing"
        return {
            "recommended_mode": mode,
            "recommended_next_layer": layer,
            "recommended_skill": LAYER_TO_SKILL[layer],
            "recommended_next_step": f"下一步建议补 {LAYER_LABELS[layer]}，对应 skill 为 `{LAYER_TO_SKILL[layer]}`。",
            "optional_backfill_layers": optional_backfill_layers,
        }

    if optional_backfill_layers:
        layer = optional_backfill_layers[0]
        return {
            "recommended_mode": "extend-existing",
            "recommended_next_layer": layer,
            "recommended_skill": LAYER_TO_SKILL[layer],
            "recommended_next_step": f"所有主要后层已成立；如需增强校准稳定性，建议回补 {LAYER_LABELS[layer]}。",
            "optional_backfill_layers": optional_backfill_layers,
        }

    return {
        "recommended_mode": "validate-only",
        "recommended_next_layer": None,
        "recommended_skill": None,
        "recommended_next_step": "五层当前都已达成可用状态；建议只做验收、交接或继续深拆项目内容。",
        "optional_backfill_layers": optional_backfill_layers,
    }


def build_repair_plan(status: dict[str, Any]) -> dict[str, Any] | None:
    target_layer = None
    if status["recommended_mode"] == "repair-existing":
        target_layer = status["recommended_next_layer"]
    elif status["incomplete_layers"]:
        target_layer = status["incomplete_layers"][0]
    if not target_layer:
        return None

    item = status["layer_status"][target_layer]
    failed_checks = item.get("failed_checks", [])
    repair_targets = item.get("repair_targets", [])
    context_files = [str(path) for _label, path in _candidate_context_files(status, target_layer)[:6]]
    summary_parts = []
    if failed_checks:
        summary_parts.append(
            "；".join(f"{failure['label']} -> {failure['reason']}" for failure in failed_checks[:4])
        )
    if item.get("has_placeholders"):
        summary_parts.append("检测到占位内容")
    if not summary_parts:
        summary_parts.append(f"{item['label']} 已存在但尚未达标")
    return {
        "required": True,
        "target_layer": target_layer,
        "target_label": item["label"],
        "mode": "repair-existing",
        "reason": "；".join(summary_parts),
        "failed_checks": failed_checks,
        "repair_targets": repair_targets,
        "context_files": context_files,
        "suggested_context_file": str(Path(status["workspace_path"]) / f"workspace-context-{target_layer}.md"),
        "suggested_repair_note": str(Path(status["workspace_path"]) / "workspace-repair-plan.md"),
    }


def collect_workspace_status(
    workspace: Path,
    novel_name: str | None = None,
    protagonist_name: str | None = None,
    run_validators: bool = True,
    persist_validator_reports: bool = False,
) -> dict[str, Any]:
    workspace = workspace.expanduser().resolve()
    novel_name = detect_novel_name(workspace, novel_name)
    protagonist_name = detect_protagonist_name(workspace, protagonist_name)
    source = estimate_source_size(workspace)
    layer_status = detect_layer_status(
        workspace,
        novel_name,
        protagonist_name,
        run_validators=run_validators,
        persist_validator_reports=persist_validator_reports,
    )
    recommendation = recommend_next_action(layer_status, source["is_long_novel"])
    available_layers = [layer for layer in LAYER_ORDER if layer_status[layer]["exists"]]
    completed_layers = [layer for layer in LAYER_ORDER if layer_status[layer]["validated"]]
    incomplete_layers = [layer for layer in LAYER_ORDER if layer_status[layer]["exists"] and not layer_status[layer]["validated"]]
    last_run_layer = completed_layers[-1] if completed_layers else (available_layers[-1] if available_layers else None)
    status = {
        "workspace_path": str(workspace),
        "novel_name": novel_name,
        "protagonist_name": protagonist_name,
        "source_files": source["files"],
        "source_total_bytes": source["total_bytes"],
        "source_estimated_chars": source["estimated_chars"],
        "is_long_novel": source["is_long_novel"],
        "available_layers": available_layers,
        "completed_layers": completed_layers,
        "incomplete_layers": incomplete_layers,
        "last_run_layer": last_run_layer,
        "last_validator_result": {
            layer: layer_status[layer]["completion_label"] for layer in LAYER_ORDER if layer_status[layer]["exists"]
        },
        "recommended_next_layer": recommendation["recommended_next_layer"],
        "recommended_skill": recommendation["recommended_skill"],
        "recommended_mode": recommendation["recommended_mode"],
        "recommended_next_step": recommendation["recommended_next_step"],
        "optional_backfill_layers": recommendation["optional_backfill_layers"],
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "layer_status": layer_status,
    }
    status["repair_plan"] = build_repair_plan(status)
    return status


def summarize_current_judgement(status: dict[str, Any]) -> str:
    parts: list[str] = []
    protagonist_status = status["layer_status"]["protagonist"]
    if protagonist_status["validated"]:
        parts.append(protagonist_status["completion_label"])
    for layer in ("chapter-distillation", "opening", "outline", "highlight"):
        item = status["layer_status"][layer]
        if item["validated"]:
            parts.append(LAYER_VALIDATED_TAGS[layer])
    if not status["incomplete_layers"] and not status["recommended_next_layer"]:
        parts.append("已阶段性收口")
    return " + ".join(parts) if parts else "初始化后待推进"


def derive_project_stage(status: dict[str, Any]) -> str:
    if not status["available_layers"]:
        return "初始化阶段"
    if status["recommended_mode"] == "validate-only" and not status["incomplete_layers"]:
        return "维护阶段"
    if status["layer_status"]["protagonist"]["validated"] or len(status["completed_layers"]) >= 2:
        return "深拆阶段"
    return "推进阶段"


def _prefer_report_or_file(item: dict[str, Any]) -> Path | None:
    report = item.get("validator_report")
    if report:
        return Path(report)
    for preferred_key in ("index", "final_card", "core_overview", "overview", "top10_table", "total_judgment"):
        if preferred_key in item.get("files", {}):
            return Path(item["files"][preferred_key])
    for path in item.get("files", {}).values():
        if isinstance(path, str):
            return Path(path)
    return None


def choose_priority_read_path(status: dict[str, Any], target_layer: str | None = None) -> Path | None:
    if target_layer:
        item = status["layer_status"].get(target_layer)
        if item:
            chosen = _prefer_report_or_file(item)
            if chosen and chosen.exists():
                return chosen
    for layer in reversed(LAYER_ORDER):
        item = status["layer_status"][layer]
        if not item["exists"]:
            continue
        chosen = _prefer_report_or_file(item)
        if chosen and chosen.exists():
            return chosen
    latest = latest_status_file(Path(status["workspace_path"]))
    if latest:
        return latest
    return Path(status["workspace_path"]) / "README.md"


def render_workspace_handoff(
    status: dict[str, Any],
    target_layer: str | None = None,
    executed_mode: str | None = None,
    execution_results: list[dict[str, Any]] | None = None,
    context_path: Path | None = None,
) -> str:
    novel_name = status["novel_name"]
    judgment = summarize_current_judgement(status)
    lines = [
        f"# 《{novel_name}》工作状态 {date.today().isoformat()}",
        "",
        "## 当前结论",
        "",
        f"- 当前整体判断：`{judgment}`",
        f"- 本轮模式：`{executed_mode or status['recommended_mode']}`",
        f"- 本轮目标层：`{target_layer or '无'}`",
        f"- 当前推荐下一层：`{status['recommended_next_layer'] or '无'}`",
        f"- 当前推荐 skill：`{status['recommended_skill'] or '无'}`",
    ]
    if context_path:
        lines.append(f"- 已生成上下文文件：`{context_path.name}`")
    if execution_results:
        lines.extend(["", "## 本轮执行记录", ""])
        for item in execution_results:
            action = item.get("action", "run")
            layer = item.get("layer", "unknown")
            state = "成功" if item.get("ok") else "失败"
            lines.append(f"- `{action}` / `{layer}`：{state}（exit {item.get('returncode', '?')}）")

    lines.extend(["", "## 当前状态判断", ""])
    for layer in LAYER_ORDER:
        item = status["layer_status"][layer]
        if item["validated"]:
            state = "已完成并通过校验"
        elif item["exists"]:
            state = "已存在但仍不足"
        else:
            state = "尚未建立"
        lines.append(f"- `{LAYER_LABELS[layer]}`：{state}；当前标签为 `{item['completion_label']}`")

    lines.extend(
        [
            "",
            "## 当前应如何继续",
            "",
            f"1. {status['recommended_next_step']}",
        ]
    )
    if status["optional_backfill_layers"]:
        lines.append(
            f"2. 可选回补层：`{', '.join(status['optional_backfill_layers'])}`，用于增强前置校准稳定性。"
        )
    priority_read = choose_priority_read_path(status, target_layer)
    lines.extend(
        [
            "",
            "## 下次开始时建议先看",
            "",
            "1. `README.md`",
            f"2. `{priority_read.name if priority_read else 'workspace-gap-report.md'}`",
            "3. `workspace-gap-report.md`",
            "4. 本文件",
            "",
            "## 一句话交接",
            "",
            f"《{novel_name}》当前判断为“{judgment}”；下一步建议 {status['recommended_next_step']}",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _sanitize_table_cell(text: str) -> str:
    return text.replace("|", "/").replace("\n", " ").strip()


def update_repo_current_status(
    project_root: Path,
    status: dict[str, Any],
    target_layer: str | None = None,
    executed_mode: str | None = None,
) -> Path:
    project_root = project_root.expanduser().resolve()
    path = project_root / "CURRENT_STATUS.md"
    novel_name = status["novel_name"]
    stage = derive_project_stage(status)
    judgment = summarize_current_judgement(status)
    mode = executed_mode or status["recommended_mode"]
    workspace = Path(status["workspace_path"])
    latest_status = latest_status_file(workspace)
    latest_status_rel = (
        str(latest_status.relative_to(project_root)) if latest_status and latest_status.is_relative_to(project_root) else latest_status.name if latest_status else "无"
    )
    priority_read = choose_priority_read_path(status, target_layer)
    priority_name = priority_read.name if priority_read else "README.md"
    next_step = _sanitize_table_cell(status["recommended_next_step"])
    row = (
        f"| `{novel_name}` | `{stage}` | `{_sanitize_table_cell(judgment)}` | "
        f"`{latest_status_rel}` | `{priority_name}` | {next_step} |"
    )

    if path.exists():
        content = path.read_text(encoding="utf-8")
    else:
        content = (
            "# 当前工作指针\n\n"
            "## 当前主任务\n\n"
            f"- 当前主项目：`{novel_name}`\n"
            f"- 当前状态：`{judgment}`\n"
            f"- 当前建议模式：`{mode}`\n\n"
            "## 项目总览\n\n"
            "| 项目 | 当前阶段 | 当前判断 | 最近状态文件 | 下次优先看 | 建议下一步 |\n"
            "| --- | --- | --- | --- | --- | --- |\n\n"
            "## 当前活跃项目说明\n\n"
            "待补充\n\n"
            "## 恢复上下文顺序\n\n"
            "1. 先看 `git status --short`\n"
            "2. 再看 `CURRENT_STATUS.md`\n"
            "3. 再进入目标项目目录看最新 `工作状态-YYYY-MM-DD.md`\n"
        )

    content, count = re.subn(r"(?m)^- 当前主项目：`.*`$", f"- 当前主项目：`{novel_name}`", content, count=1)
    if count == 0:
        content = f"## 当前主任务\n\n- 当前主项目：`{novel_name}`\n" + content
    content, count = re.subn(r"(?m)^- 当前状态：`.*`$", f"- 当前状态：`{judgment}`", content, count=1)
    if count == 0:
        content = content.replace(f"- 当前主项目：`{novel_name}`\n", f"- 当前主项目：`{novel_name}`\n- 当前状态：`{judgment}`\n", 1)
    content, count = re.subn(r"(?m)^- 当前建议模式：`.*`$", f"- 当前建议模式：`{mode}`", content, count=1)
    if count == 0:
        content = content.replace(f"- 当前状态：`{judgment}`\n", f"- 当前状态：`{judgment}`\n- 当前建议模式：`{mode}`\n", 1)

    table_header = "| 项目 | 当前阶段 | 当前判断 | 最近状态文件 | 下次优先看 | 建议下一步 |"
    table_divider = "| --- | --- | --- | --- | --- | --- |"
    if table_header not in content:
        insert_block = f"\n## 项目总览\n\n{table_header}\n{table_divider}\n{row}\n"
        marker = "## 当前活跃项目说明"
        content = content.replace(marker, insert_block + "\n" + marker, 1) if marker in content else content + insert_block
    else:
        lines = content.splitlines()
        header_idx = next(i for i, line in enumerate(lines) if line.strip() == table_header)
        table_end = header_idx + 2
        while table_end < len(lines) and lines[table_end].startswith("|"):
            table_end += 1
        replaced = False
        for idx in range(header_idx + 2, table_end):
            if lines[idx].startswith(f"| `{novel_name}` |"):
                lines[idx] = row
                replaced = True
                break
        if not replaced:
            lines.insert(table_end, row)
        content = "\n".join(lines)

    active_section = (
        "## 当前活跃项目说明\n\n"
        f"《{novel_name}》当前判断为 `{judgment}`。\n\n"
        f"- 当前阶段：`{stage}`\n"
        f"- 当前推荐模式：`{mode}`\n"
        f"- 已达标层：`{', '.join(status['completed_layers']) if status['completed_layers'] else '无'}`\n"
        f"- 待修层：`{', '.join(status['incomplete_layers']) if status['incomplete_layers'] else '无'}`\n"
        f"- 下一步建议：{status['recommended_next_step']}\n"
    )
    if "## 当前活跃项目说明" in content and "## 恢复上下文顺序" in content:
        content = re.sub(
            r"## 当前活跃项目说明\s*\n.*?(?=\n## 恢复上下文顺序)",
            active_section.rstrip(),
            content,
            flags=re.DOTALL,
        )
    elif "## 恢复上下文顺序" in content:
        content = content.replace("## 恢复上下文顺序", active_section + "\n## 恢复上下文顺序", 1)
    else:
        content += "\n\n" + active_section

    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return path


def render_gap_report(status: dict[str, Any]) -> str:
    workspace = status["workspace_path"]
    novel_name = status["novel_name"]
    lines = [
        f"# 《{novel_name}》工作区差距报告",
        "",
        f"- 工作区：`{workspace}`",
        f"- 是否长篇：`{'是' if status['is_long_novel'] else '否'}`",
        f"- 已存在层：`{', '.join(status['available_layers']) if status['available_layers'] else '无'}`",
        f"- 已达标层：`{', '.join(status['completed_layers']) if status['completed_layers'] else '无'}`",
        f"- 待修层：`{', '.join(status['incomplete_layers']) if status['incomplete_layers'] else '无'}`",
        f"- 推荐模式：`{status['recommended_mode']}`",
        f"- 推荐下一层：`{status['recommended_next_layer'] or '无'}`",
        f"- 推荐 skill：`{status['recommended_skill'] or '无'}`",
        "",
        "## 当前判断",
        "",
        f"- {status['recommended_next_step']}",
    ]
    if status["optional_backfill_layers"]:
        lines.extend(
            [
                "",
                "## 可选回补层",
                "",
                *[f"- `{layer}`：建议在主流程不阻塞时补上，用于增强后续校准稳定性。" for layer in status["optional_backfill_layers"]],
            ]
        )
    if status.get("repair_plan"):
        repair_plan = status["repair_plan"]
        lines.extend(
            [
                "",
                "## Repair Plan",
                "",
                f"- 目标层：`{repair_plan['target_layer']}` / `{repair_plan['target_label']}`",
                f"- 进入原因：{repair_plan['reason']}",
            ]
        )
        for target in repair_plan["repair_targets"]:
            lines.append(f"- {target}")
    lines.extend(["", "## 分层结果", ""])
    for layer in LAYER_ORDER:
        item = status["layer_status"][layer]
        state = "通过" if item["validated"] else ("仅存在" if item["exists"] else "缺失")
        lines.append(f"### {item['label']} / `{layer}`")
        lines.append("")
        lines.append(f"- 当前状态：`{state}`")
        lines.append(f"- 完成标签：`{item['completion_label']}`")
        lines.append(f"- 判断来源：`{item['reason']}`")
        if item["files"]:
            sample_files = ", ".join(sorted(Path(path).name for path in item["files"].values() if isinstance(path, str)))
            lines.append(f"- 识别到的关键文件：`{sample_files}`")
        failed_checks = []
        for failure in item.get("failed_checks", []):
            failed_checks.append(f"{failure['label']}:{failure['reason']}")
        if failed_checks:
            lines.append(f"- 主要缺口：`{' | '.join(failed_checks[:5])}`")
        if item.get("repair_targets"):
            lines.append(f"- 修复动作：`{' | '.join(item['repair_targets'][:4])}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_repair_plan(status: dict[str, Any]) -> str:
    repair_plan = status.get("repair_plan")
    if not repair_plan:
        return ""
    lines = [
        f"# 《{status['novel_name']}》Repair Plan",
        "",
        f"- 工作区：`{status['workspace_path']}`",
        f"- 目标层：`{repair_plan['target_layer']}` / `{repair_plan['target_label']}`",
        f"- 模式：`{repair_plan['mode']}`",
        f"- 原因：{repair_plan['reason']}",
        "",
        "## 修复动作",
        "",
    ]
    for target in repair_plan["repair_targets"]:
        lines.append(f"- {target}")
    if repair_plan["failed_checks"]:
        lines.extend(["", "## 失败检查项", ""])
        for failure in repair_plan["failed_checks"]:
            line = f"- `{failure['label']}`：`{failure['reason']}`"
            if failure.get("file"):
                line += f"；文件：`{Path(failure['file']).name}`"
            if failure.get("placeholder_hits"):
                line += f"；占位：`{', '.join(failure['placeholder_hits'])}`"
            lines.append(line)
    if repair_plan["context_files"]:
        lines.extend(["", "## 推荐先读", ""])
        for path in repair_plan["context_files"]:
            lines.append(f"- `{Path(path).name}`")
    return "\n".join(lines).rstrip() + "\n"


def _candidate_context_files(status: dict[str, Any], target_layer: str) -> list[tuple[str, Path]]:
    workspace = Path(status["workspace_path"])
    novel_name = status["novel_name"]
    latest_status = latest_status_file(workspace)
    protagonist_files = status["layer_status"]["protagonist"]["files"]
    outline_files = status["layer_status"]["outline"]["files"]

    candidates: list[tuple[str, Path | None]] = [
        ("README", workspace / "README.md"),
        ("latest_status", latest_status),
    ]
    if target_layer == "chapter-distillation":
        candidates.extend([("source", Path(path)) for path in status["source_files"][:2]])
    elif target_layer == "opening":
        candidates.extend(
            [
                ("chapter_manifest", workspace / "chapter-distillation-manifest.json"),
                ("chapter_skeleton", workspace / f"{novel_name}-章节蒸馏骨架.md"),
                ("stage_skeleton", workspace / f"{novel_name}-阶段骨架与换挡草图.md"),
            ]
        )
    elif target_layer == "protagonist":
        candidates.extend(
            [
                ("opening_total", workspace / f"{novel_name}-黄金前三章总判断.md"),
                ("opening_hook", workspace / f"{novel_name}-开篇钩子与读者承诺.md"),
                ("stage_skeleton", workspace / f"{novel_name}-阶段骨架与换挡草图.md"),
                ("chapter_skeleton", workspace / f"{novel_name}-章节蒸馏骨架.md"),
            ]
        )
    elif target_layer == "outline":
        candidates.extend(
            [
                ("protagonist_index", Path(protagonist_files["index"])) if "index" in protagonist_files else ("protagonist_index", None),
                ("final_card", Path(protagonist_files["final_card"])) if "final_card" in protagonist_files else ("final_card", None),
                ("core_overview", Path(protagonist_files["core_overview"])) if "core_overview" in protagonist_files else ("core_overview", None),
                ("essence_summary", Path(protagonist_files["essence_summary"])) if "essence_summary" in protagonist_files else ("essence_summary", None),
                ("opening_total", workspace / f"{novel_name}-黄金前三章总判断.md"),
            ]
        )
    elif target_layer == "highlight":
        candidates.extend(
            [
                ("outline_overview", Path(outline_files["overview"])) if "overview" in outline_files else ("outline_overview", None),
                ("outline_stages", Path(outline_files["stages"])) if "stages" in outline_files else ("outline_stages", None),
                ("outline_lines", Path(outline_files["lines"])) if "lines" in outline_files else ("outline_lines", None),
                ("protagonist_index", Path(protagonist_files["index"])) if "index" in protagonist_files else ("protagonist_index", None),
                ("core_overview", Path(protagonist_files["core_overview"])) if "core_overview" in protagonist_files else ("core_overview", None),
                ("opening_total", workspace / f"{novel_name}-黄金前三章总判断.md"),
            ]
        )
    deduped: list[tuple[str, Path]] = []
    seen: set[Path] = set()
    for label, path in candidates:
        if not path or not path.exists():
            continue
        if path in seen:
            continue
        deduped.append((label, path))
        seen.add(path)
    return deduped


def summarize_path(path: Path, max_lines: int = 18, max_chars: int = 1800) -> str:
    if path.suffix == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
        if isinstance(payload, dict):
            lines = [f"- `{key}`: {type(value).__name__}" for key, value in list(payload.items())[:12]]
            if "chapter_count" in payload:
                lines.insert(0, f"- `chapter_count`: {payload['chapter_count']}")
            if isinstance(payload.get("chapters"), list):
                sample = payload["chapters"][:5]
                chapter_titles = []
                for item in sample:
                    if isinstance(item, dict):
                        chapter_titles.append(str(item.get("title") or item.get("heading") or item.get("name") or item))
                    else:
                        chapter_titles.append(str(item))
                if chapter_titles:
                    lines.append(f"- `sample_chapters`: {' | '.join(chapter_titles)}")
            return "\n".join(lines)[:max_chars]

    text = read_text(path)
    if not text:
        return ""
    non_empty = [line.rstrip() for line in text.splitlines() if line.strip()]
    return "\n".join(non_empty[:max_lines])[:max_chars]


def build_layer_context(status: dict[str, Any], target_layer: str) -> str:
    if target_layer not in LAYER_ORDER:
        raise ValueError(f"unknown target layer: {target_layer}")
    workspace = status["workspace_path"]
    lines = [
        f"# {LAYER_LABELS[target_layer]}复用上下文",
        "",
        f"- 工作区：`{workspace}`",
        f"- 小说名：`{status['novel_name']}`",
        f"- 目标层：`{target_layer}`",
        f"- 推荐原因：{status['recommended_next_step']}",
        "",
        "## 当前全局状态",
        "",
        f"- 已达标层：`{', '.join(status['completed_layers']) if status['completed_layers'] else '无'}`",
        f"- 待修层：`{', '.join(status['incomplete_layers']) if status['incomplete_layers'] else '无'}`",
        "",
    ]
    layer_item = status["layer_status"][target_layer]
    if layer_item.get("repair_targets"):
        lines.extend(
            [
                "## 当前 repair 重点",
                "",
                *[f"- {target}" for target in layer_item["repair_targets"]],
                "",
            ]
        )
    lines.extend(
        [
        "## 选取文件",
        "",
        ]
    )
    for label, path in _candidate_context_files(status, target_layer):
        lines.append(f"### {label}: `{path.name}`")
        lines.append("")
        lines.append(summarize_path(path))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_pipeline_report(
    status: dict[str, Any],
    target_layer: str | None,
    context_path: Path | None,
    execution_results: list[dict[str, Any]] | None = None,
    handoff_path: Path | None = None,
    current_status_path: Path | None = None,
) -> str:
    lines = [
        f"# 《{status['novel_name']}》工作区流程判断报告",
        "",
        f"- 工作区：`{status['workspace_path']}`",
        f"- 推荐模式：`{status['recommended_mode']}`",
        f"- 当前推荐下一层：`{status['recommended_next_layer'] or '无'}`",
        f"- 本轮目标层：`{target_layer or '无'}`",
        f"- 推荐 skill：`{status['recommended_skill'] or '无'}`",
        f"- 上次完成层：`{status['last_run_layer'] or '无'}`",
        "",
        "## 当前建议",
        "",
        f"- {status['recommended_next_step']}",
    ]
    if context_path:
        lines.append(f"- 已生成上下文文件：`{context_path}`")
    if handoff_path:
        lines.append(f"- 已写回工作状态：`{handoff_path}`")
    if current_status_path:
        lines.append(f"- 已更新仓库状态：`{current_status_path}`")
    if status.get("repair_plan"):
        lines.append("- 当前存在 repair plan：`workspace-repair-plan.md`")
    if execution_results:
        lines.extend(["", "## 执行记录", ""])
        for item in execution_results:
            action = item.get("action", "run")
            layer = item.get("layer", "unknown")
            state = "成功" if item.get("ok") else "失败"
            lines.append(f"- `{action}` / `{layer}`：{state}（exit {item.get('returncode', '?')}）")
    if status.get("repair_plan"):
        repair_plan = status["repair_plan"]
        lines.extend(
            [
                "",
                "## Repair Plan",
                "",
                f"- 目标层：`{repair_plan['target_layer']}` / `{repair_plan['target_label']}`",
                f"- 原因：{repair_plan['reason']}",
            ]
        )
        for target in repair_plan["repair_targets"]:
            lines.append(f"- {target}")
    lines.extend(
        [
            "",
            "## 层状态摘要",
            "",
            f"- 已存在层：`{', '.join(status['available_layers']) if status['available_layers'] else '无'}`",
            f"- 已达标层：`{', '.join(status['completed_layers']) if status['completed_layers'] else '无'}`",
            f"- 待修层：`{', '.join(status['incomplete_layers']) if status['incomplete_layers'] else '无'}`",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"
