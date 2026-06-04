#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

SHARED_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "novel-workspace-orchestrator-skill" / "scripts"
if str(SHARED_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS_DIR))
from shared_api_client import call_chat_completion

SYSTEM_PROMPT = """你是资深网文结构编辑，任务是为“整书大纲层”生成可直接落盘的正式分析文档。

要求：
1. 只输出 JSON，不要输出 markdown，不要加前言。
2. 必须优先依赖章节蒸馏层、阶段骨架、开篇层、主角层、重要配角层来做整书结构判断。
3. 不是复述剧情，而是判断阶段、主线、支线、冲突升级、高潮收束和结构问题。
4. 必须引用具体角色名、势力名、阶段名、关键节点，避免空泛“节奏不错/结构完整”。
5. 必须写出因果：为什么这样分阶段、为什么冲突在此处爆发、为什么某段拖沓或有效。
6. 修改建议必须可执行，明确“前移/后移/压缩/合并/补强”的对象。

返回 JSON 结构：
{
  "meta_summary": {
    "common_judgement": "一句话",
    "feature_judgement": "一句话",
    "one_line_handoff": "一句话交接"
  },
  "overview": {
    "核心 premise": "100-220字",
    "结构类型": "100-220字",
    "全书主线一句话": "100-220字",
    "整书总判断": "100-220字",
    "单书特性": [
      {"title": "特性 1", "body": "80-180字"},
      {"title": "特性 2", "body": "80-180字"}
    ]
  },
  "stages": {
    "阶段划分说明": "100-220字",
    "阶段_1": {
      "阶段边界成立原因": "80-180字",
      "阶段主冲突": "80-180字",
      "主要时间 / 地点转折": "80-180字",
      "阶段作用": "80-180字"
    },
    "阶段_2": { ... },
    "阶段_3": { ... },
    "阶段总评": "100-220字"
  },
  "lines": {
    "核心主线": "100-220字",
    "重要支线": "100-220字",
    "桥接线": "100-220字",
    "主线支线总判断": "100-220字"
  },
  "conflicts": {
    "根本主冲突": "100-220字",
    "阶段性冲突": "100-220字",
    "关键爆发点": "100-220字",
    "冲突层总判断": "100-220字"
  },
  "time_place": {
    "时间转折": "100-220字",
    "地点转折": "100-220字",
    "时间与地点联合判断": "100-220字"
  },
  "climax_pacing": {
    "开篇判断": "80-180字",
    "中段判断": "80-180字",
    "高潮判断": "80-180字",
    "结尾判断": "80-180字",
    "整书节奏标签": "80-180字",
    "总诊断": "100-220字"
  },
  "issues_revision": {
    "结构优点": "100-220字",
    "结构问题": "100-220字",
    "第一优先修改项": "100-220字",
    "轻修建议": "100-220字",
    "总建议": "100-220字"
  },
  "core_supporting_relations": {
    "核心配角清单": "100-220字",
    "关键关系类型": "100-220字",
    "关系线总判断": "100-220字",
    "阶段作用": "100-220字"
  },
  "next_actions": [
    "一句具体下一步",
    "一句具体下一步",
    "一句具体下一步"
  ]
}
"""

OVERVIEW_FIELDS = ["核心 premise", "结构类型", "全书主线一句话", "整书总判断"]
STAGE_FIELDS = ["阶段边界成立原因", "阶段主冲突", "主要时间 / 地点转折", "阶段作用"]
LINES_FIELDS = ["核心主线", "重要支线", "桥接线", "主线支线总判断"]
CONFLICT_FIELDS = ["根本主冲突", "阶段性冲突", "关键爆发点", "冲突层总判断"]
TIME_PLACE_FIELDS = ["时间转折", "地点转折", "时间与地点联合判断"]
CLIMAX_FIELDS = ["开篇判断", "中段判断", "高潮判断", "结尾判断", "整书节奏标签", "总诊断"]
ISSUE_FIELDS = ["结构优点", "结构问题", "第一优先修改项", "轻修建议", "总建议"]
RELATION_FIELDS = ["核心配角清单", "关键关系类型", "关系线总判断", "阶段作用"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auto-fill the outline analysis layer from distilled and upper-layer context.")
    parser.add_argument("--workspace", required=True, help="Workspace directory.")
    parser.add_argument("--novel-name", required=True, help="Novel name used in file naming.")
    parser.add_argument("--protagonist", help="Known protagonist name.")
    parser.add_argument("--project-root", help="Project root used to load .env.")
    parser.add_argument("--attempt-label", default="draft", help="Artifact label, e.g. draft / repair-1.")
    parser.add_argument("--force", action="store_true", help="Overwrite durable outputs.")
    parser.add_argument("--context-file", action="append", default=[], help="Additional markdown/json files to inject into the prompt.")
    parser.add_argument("--response-file", help="Debug override: load model response from a local JSON file.")
    return parser.parse_args()


def load_env(project_root: Path) -> None:
    env_path = project_root / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.strip().split("=", 1)
            os.environ[key] = value


def read_text(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def latest_status_file(workspace: Path) -> Path | None:
    candidates = sorted(workspace.glob("工作状态-*.md"))
    return candidates[-1] if candidates else None


def outline_work_dir(workspace: Path) -> Path:
    return workspace / "work" / "outline-analysis"


def ensure_dirs(workspace: Path) -> tuple[Path, Path]:
    work_dir = outline_work_dir(workspace)
    attempts_dir = work_dir / "attempts"
    attempts_dir.mkdir(parents=True, exist_ok=True)
    return work_dir, attempts_dir


def trim(text: str, limit: int) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "\n...[truncated]"


def read_context_file(path: Path, limit: int = 2600) -> str:
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return trim(read_text(path), limit)
        return trim(json.dumps(payload, ensure_ascii=False, indent=2), limit)
    return trim(read_text(path), limit)


def first_existing(workspace: Path, patterns: list[str]) -> Path | None:
    for pattern in patterns:
        matches = sorted(workspace.glob(pattern))
        if matches:
            return matches[0]
    return None


def context_candidates(workspace: Path, novel_name: str) -> list[tuple[str, Path, int]]:
    candidates: list[tuple[str, Path | None, int]] = [
        ("latest_status", latest_status_file(workspace), 2200),
        ("chapter_manifest", workspace / "chapter-distillation-manifest.json", 1800),
        ("stage_skeleton", workspace / f"{novel_name}-阶段骨架与换挡草图.md", 2800),
        ("calibration_anchors", workspace / f"{novel_name}-校准与验证锚点.md", 2400),
        ("chapter_skeleton", workspace / f"{novel_name}-章节蒸馏骨架.md", 5200),
        ("distill_section_0001", workspace / "work" / "chapter-distillation" / "sections" / "0001.md", 1200),
        ("distill_section_0002", workspace / "work" / "chapter-distillation" / "sections" / "0002.md", 1200),
        ("distill_section_0003", workspace / "work" / "chapter-distillation" / "sections" / "0003.md", 1200),
        ("opening_total", workspace / f"{novel_name}-黄金前三章总判断.md", 2200),
        ("opening_hook", workspace / f"{novel_name}-开篇钩子与读者承诺.md", 1800),
        ("protagonist_anchor", workspace / f"{novel_name}-主角锚点与骨架.md", 2600),
        ("protagonist_index", first_existing(workspace, ["*-词条总索引.md"]), 2400),
        ("protagonist_card", first_existing(workspace, ["*-最终人物卡.md"]), 2200),
        ("core_overview", first_existing(workspace, ["*-核心体系总览.md"]), 2200),
        ("essence_summary", workspace / f"{novel_name}-全书精华总结.md", 2200),
        ("supporting_top10", workspace / f"{novel_name}-重要配角Top10总表.md", 2200),
        ("supporting_relations", workspace / f"{novel_name}-重要配角与主角关系图.md", 2000),
        ("supporting_stage", workspace / f"{novel_name}-重要配角阶段作用分布.md", 1800),
    ]
    result: list[tuple[str, Path, int]] = []
    seen: set[Path] = set()
    for label, path, limit in candidates:
        if not path or not path.exists() or path in seen:
            continue
        result.append((label, path, limit))
        seen.add(path)
    return result


def build_prompt(
    novel_name: str,
    protagonist: str | None,
    contexts: list[tuple[str, Path, int]],
    extra_contexts: list[tuple[Path, str]],
) -> str:
    protagonist_line = f"- 主角名（如已知）：{protagonist}\n" if protagonist else ""
    context_sections = [
        f"### {label}: {path.name}\n{read_context_file(path, limit)}"
        for label, path, limit in contexts
    ]
    extra_sections = [f"### 额外上下文：{path.name}\n{text}" for path, text in extra_contexts]
    return "\n\n".join(
        [
            f"小说名：{novel_name}",
            protagonist_line + "任务：构建整书大纲层正式产物，判断阶段结构、主线支线、冲突升级、高潮收束与结构问题。",
            "注意：必须优先依赖章节蒸馏层来判断全书阶段和剧情换挡，再用 opening / protagonist / supporting-cast 来校准人物与承诺。",
            "## 主上下文",
            "\n\n".join(context_sections) if context_sections else "（无主上下文）",
            "## 额外上下文",
            "\n\n".join(extra_sections) if extra_sections else "（无）",
            "请按 system prompt 的 JSON 结构返回。",
        ]
    )


def extract_json_blob(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        return match.group(0)
    return cleaned


def call_api(prompt: str) -> dict[str, Any]:
    result = call_chat_completion(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=prompt,
        model_env_vars=("OUTLINE_ANALYSIS_MODEL",),
        fallback_model_env_vars=("OUTLINE_ANALYSIS_FALLBACK_MODELS",),
        default_model="deepseek-chat",
        response_format={"type": "json_object"},
        temperature=0.35,
        max_tokens=5200,
        timeout=300,
        max_attempts=4,
    )
    return {"raw_api": result["raw_api"], "content": result["content"]}


def sanitize_text(value: Any) -> str:
    if isinstance(value, list):
        joined = "；".join(str(item).strip() for item in value if str(item).strip())
    else:
        joined = str(value or "").strip()
    joined = joined.replace("\u3000", " ")
    joined = re.sub(r"\s+", " ", joined).strip()
    if not joined:
        return "需要补具体判断，但本轮模型未返回。"
    if joined in {"待补充", "待确认", "待定", "待完善"}:
        return "模型返回了占位词，需要重试并补成明确结论。"
    return joined


def normalize_section_map(data: dict[str, Any], keys: list[str]) -> dict[str, str]:
    return {key: sanitize_text(data.get(key, "")) for key in keys}


def normalize_stage_block(data: dict[str, Any]) -> dict[str, str]:
    return {key: sanitize_text(data.get(key, "")) for key in STAGE_FIELDS}


def normalize_features(items: Any) -> list[dict[str, str]]:
    if not isinstance(items, list):
        items = []
    normalized: list[dict[str, str]] = []
    for idx, item in enumerate(items[:4], start=1):
        if isinstance(item, dict):
            title = sanitize_text(item.get("title", f"特性 {idx}"))
            body = sanitize_text(item.get("body", ""))
        else:
            title = f"特性 {idx}"
            body = sanitize_text(item)
        normalized.append({"title": title, "body": body})
    return normalized


def normalize_response(payload: dict[str, Any]) -> dict[str, Any]:
    meta_summary = payload.get("meta_summary", {}) if isinstance(payload.get("meta_summary"), dict) else {}
    overview_payload = payload.get("overview", {}) if isinstance(payload.get("overview"), dict) else {}
    stages_payload = payload.get("stages", {}) if isinstance(payload.get("stages"), dict) else {}
    next_actions = payload.get("next_actions", [])
    if not isinstance(next_actions, list):
        next_actions = [str(next_actions)]
    return {
        "meta_summary": {
            "common_judgement": sanitize_text(meta_summary.get("common_judgement", "")),
            "feature_judgement": sanitize_text(meta_summary.get("feature_judgement", "")),
            "one_line_handoff": sanitize_text(meta_summary.get("one_line_handoff", "")),
        },
        "overview": {
            **normalize_section_map(overview_payload, OVERVIEW_FIELDS),
            "单书特性": normalize_features(overview_payload.get("单书特性", [])),
        },
        "stages": {
            "阶段划分说明": sanitize_text(stages_payload.get("阶段划分说明", "")),
            "阶段_1": normalize_stage_block(stages_payload.get("阶段_1", {}) if isinstance(stages_payload.get("阶段_1"), dict) else {}),
            "阶段_2": normalize_stage_block(stages_payload.get("阶段_2", {}) if isinstance(stages_payload.get("阶段_2"), dict) else {}),
            "阶段_3": normalize_stage_block(stages_payload.get("阶段_3", {}) if isinstance(stages_payload.get("阶段_3"), dict) else {}),
            "阶段总评": sanitize_text(stages_payload.get("阶段总评", "")),
        },
        "lines": normalize_section_map(payload.get("lines", {}), LINES_FIELDS)
        if isinstance(payload.get("lines"), dict)
        else normalize_section_map({}, LINES_FIELDS),
        "conflicts": normalize_section_map(payload.get("conflicts", {}), CONFLICT_FIELDS)
        if isinstance(payload.get("conflicts"), dict)
        else normalize_section_map({}, CONFLICT_FIELDS),
        "time_place": normalize_section_map(payload.get("time_place", {}), TIME_PLACE_FIELDS)
        if isinstance(payload.get("time_place"), dict)
        else normalize_section_map({}, TIME_PLACE_FIELDS),
        "climax_pacing": normalize_section_map(payload.get("climax_pacing", {}), CLIMAX_FIELDS)
        if isinstance(payload.get("climax_pacing"), dict)
        else normalize_section_map({}, CLIMAX_FIELDS),
        "issues_revision": normalize_section_map(payload.get("issues_revision", {}), ISSUE_FIELDS)
        if isinstance(payload.get("issues_revision"), dict)
        else normalize_section_map({}, ISSUE_FIELDS),
        "core_supporting_relations": normalize_section_map(payload.get("core_supporting_relations", {}), RELATION_FIELDS)
        if isinstance(payload.get("core_supporting_relations"), dict)
        else normalize_section_map({}, RELATION_FIELDS),
        "next_actions": [sanitize_text(item) for item in next_actions[:5] if sanitize_text(item)],
    }


def write_file(path: Path, content: str, force: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        existing = path.read_text(encoding="utf-8", errors="ignore")
        if existing.strip() and "待补充" not in existing and "当前仅完成了大纲分析工作区初始化" not in existing:
            return
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def render_section_markdown(title: str, sections: dict[str, str]) -> str:
    lines = [title, ""]
    for header, body in sections.items():
        lines.extend([f"## {header}", "", f"- {body}", ""])
    return "\n".join(lines).rstrip() + "\n"


def render_overview_markdown(novel_name: str, normalized: dict[str, Any]) -> str:
    lines = [f"# 《{novel_name}》大纲总览", ""]
    for field in OVERVIEW_FIELDS:
        lines.extend([f"## {field}", "", f"- {normalized['overview'][field]}", ""])
    lines.extend(["## 单书特性", ""])
    for item in normalized["overview"]["单书特性"]:
        lines.extend([f"### {item['title']}", "", f"- {item['body']}", ""])
    return "\n".join(lines).rstrip() + "\n"


def render_stages_markdown(novel_name: str, normalized: dict[str, Any]) -> str:
    lines = [f"# 《{novel_name}》阶段与篇章拆分", "", "## 阶段划分说明", "", f"- {normalized['stages']['阶段划分说明']}", ""]
    for idx in (1, 2, 3):
        lines.extend([f"## 阶段 {idx}", ""])
        stage = normalized["stages"][f"阶段_{idx}"]
        for field in STAGE_FIELDS:
            lines.append(f"- {field}：{stage[field]}")
        lines.append("")
    lines.extend(["## 阶段总评", "", f"- {normalized['stages']['阶段总评']}", ""])
    return "\n".join(lines).rstrip() + "\n"


def render_status_md(novel_name: str, normalized: dict[str, Any]) -> str:
    actions = normalized["next_actions"] or [
        "回看阶段边界是否都有明确的冲突或规则换挡依据，而不是平均切段。",
        "检查结构问题与修改建议是否已经落到具体区段和具体操作动作。",
        "核对大纲层判断是否与蒸馏层、开篇层和主角层保持一致。",
    ]
    return "\n".join(
        [
            f"# 《{novel_name}》工作状态 {date.today().isoformat()}",
            "",
            "## 当前结论",
            "",
            f"- `整书大纲分析层`：{normalized['meta_summary']['common_judgement']}",
            f"- `单书特性`：{normalized['meta_summary']['feature_judgement']}",
            f"- `结构修改优先级`：{normalized['issues_revision']['第一优先修改项']}",
            "",
            "## 当前不应误判为已完成的部分",
            "",
            "- 不应把剧情摘要误判成阶段结构判断。",
            "- 不应让大纲层脱离章节蒸馏层与主角层单独成立。",
            "- 不应只有问题判断而没有可执行的结构改法。",
            "",
            "## 当前应如何继续",
            "",
            *[f"{idx}. {item}" for idx, item in enumerate(actions[:5], start=1)],
            "",
            "## 下次开始时建议先看",
            "",
            "1. `README.md`",
            f"2. `{novel_name}-大纲总览.md`",
            f"3. `{novel_name}-阶段与篇章拆分.md`",
            f"4. `{novel_name}-结构问题与修改建议.md`",
            "5. 本文件",
            "",
            "## 一句话交接",
            "",
            normalized["meta_summary"]["one_line_handoff"],
            "",
        ]
    )


def persist_outputs(workspace: Path, novel_name: str, normalized: dict[str, Any], force: bool) -> list[str]:
    written: list[str] = []
    overview_path = workspace / f"{novel_name}-大纲总览.md"
    write_file(overview_path, render_overview_markdown(novel_name, normalized), force)
    written.append(str(overview_path))

    stages_path = workspace / f"{novel_name}-阶段与篇章拆分.md"
    write_file(stages_path, render_stages_markdown(novel_name, normalized), force)
    written.append(str(stages_path))

    lines_path = workspace / f"{novel_name}-主线支线与冲突地图.md"
    write_file(lines_path, render_section_markdown(f"# 《{novel_name}》主线支线与冲突地图", normalized["lines"]), force)
    written.append(str(lines_path))

    conflicts_path = workspace / f"{novel_name}-核心冲突点与爆发点.md"
    write_file(conflicts_path, render_section_markdown(f"# 《{novel_name}》核心冲突点与爆发点", normalized["conflicts"]), force)
    written.append(str(conflicts_path))

    time_place_path = workspace / f"{novel_name}-时间与地点转折.md"
    write_file(time_place_path, render_section_markdown(f"# 《{novel_name}》时间与地点转折", normalized["time_place"]), force)
    written.append(str(time_place_path))

    climax_path = workspace / f"{novel_name}-高潮节奏与收束诊断.md"
    write_file(climax_path, render_section_markdown(f"# 《{novel_name}》高潮节奏与收束诊断", normalized["climax_pacing"]), force)
    written.append(str(climax_path))

    issues_path = workspace / f"{novel_name}-结构问题与修改建议.md"
    write_file(issues_path, render_section_markdown(f"# 《{novel_name}》结构问题与修改建议", normalized["issues_revision"]), force)
    written.append(str(issues_path))

    relations_path = workspace / f"{novel_name}-核心配角与主角关系.md"
    write_file(relations_path, render_section_markdown(f"# 《{novel_name}》核心配角与主角关系", normalized["core_supporting_relations"]), force)
    written.append(str(relations_path))

    status_path = latest_status_file(workspace) or workspace / f"工作状态-{date.today().isoformat()}.md"
    write_file(status_path, render_status_md(novel_name, normalized), True)
    written.append(str(status_path))
    return written


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.exists():
        raise SystemExit(f"workspace not found: {workspace}")

    project_root = (
        Path(args.project_root).expanduser().resolve()
        if args.project_root
        else Path(__file__).resolve().parents[2]
    )
    load_env(project_root)
    work_dir, attempts_dir = ensure_dirs(workspace)

    contexts = context_candidates(workspace, args.novel_name)
    extra_contexts: list[tuple[Path, str]] = []
    for raw_path in args.context_file:
        path = Path(raw_path).expanduser().resolve()
        if path.exists():
            extra_contexts.append((path, read_context_file(path)))

    prompt = build_prompt(args.novel_name, args.protagonist, contexts, extra_contexts)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    prompt_path = attempts_dir / f"{stamp}-{args.attempt_label}-prompt.md"
    prompt_path.write_text(prompt.rstrip() + "\n", encoding="utf-8")

    debug_response_file = args.response_file or os.environ.get("OUTLINE_ANALYSIS_RESPONSE_FILE", "").strip()
    if debug_response_file:
        response_path = Path(debug_response_file).expanduser().resolve()
        raw_text = response_path.read_text(encoding="utf-8")
        raw_payload = {"debug_response_file": str(response_path)}
    else:
        api_result = call_api(prompt)
        raw_text = api_result["content"]
        raw_payload = api_result["raw_api"]

    raw_response_path = attempts_dir / f"{stamp}-{args.attempt_label}-response.txt"
    raw_response_path.write_text(raw_text.rstrip() + "\n", encoding="utf-8")
    raw_payload_path = attempts_dir / f"{stamp}-{args.attempt_label}-api.json"
    raw_payload_path.write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    parsed = json.loads(extract_json_blob(raw_text))
    normalized = normalize_response(parsed)
    normalized_path = attempts_dir / f"{stamp}-{args.attempt_label}-normalized.json"
    normalized_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    written = persist_outputs(workspace, args.novel_name, normalized, args.force)
    latest_run = {
        "novel_name": args.novel_name,
        "attempt_label": args.attempt_label,
        "written_files": written,
        "context_files": [str(path) for _label, path, _limit in contexts],
        "prompt_file": str(prompt_path),
        "response_file": str(raw_response_path),
        "normalized_file": str(normalized_path),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    (work_dir / "latest-run.json").write_text(json.dumps(latest_run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(latest_run, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
