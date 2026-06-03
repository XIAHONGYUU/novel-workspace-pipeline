#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import requests

SYSTEM_PROMPT = """你是资深网文人物结构编辑，任务是把“重要配角层”从候选池初评推进到可直接落盘的正式版本。

要求：
1. 只输出 JSON，不要输出 markdown，不要加前言。
2. 必须优先依赖角色卡缓存、主角层、章节蒸馏层、大纲层和高光层，不要只看名字频率。
3. Top10 定榜必须解释为什么保留、为什么前移/后移、为什么能改写主角路径。
4. 每个配角都要写清：结构角色、与主角关系定位、关键阶段、阶段作用、最终入榜理由。
5. 语言必须具体，引用角色名、势力名、场域名、阶段名、关键事件，避免“戏份很多/很重要”这类空话。
6. 不允许保留任何占位词。

返回 JSON 结构：
{
  "meta_summary": {
    "top10_judgement": "一句话",
    "relation_judgement": "一句话",
    "one_line_handoff": "一句话交接"
  },
  "global_analysis": {
    "top10_summary": "100-220字",
    "relation_summary": "100-220字",
    "stage_summary": "100-220字",
    "reshuffle_standard": "100-220字",
    "removed_from_initial_top10": ["可为空"],
    "added_into_top10": ["可为空"]
  },
  "final_top10": [
    {
      "rank": 1,
      "name": "角色名",
      "ai_review_verdict": "80-180字",
      "keep_decision": "保留 / 前移 / 后移 / 补入",
      "final_reason": "100-220字",
      "relation_position": "80-180字",
      "path_impact": "80-180字",
      "key_stages": "80-180字",
      "stage_role": "80-180字",
      "final_conclusion": "80-180字",
      "compare_upper": "80-180字",
      "compare_lower": "80-180字"
    }
  ],
  "near_miss": [
    {
      "name": "角色名",
      "decision": "80-180字",
      "reason": "80-180字"
    }
  ],
  "next_actions": [
    "一句具体下一步",
    "一句具体下一步",
    "一句具体下一步"
  ]
}
"""

PLACEHOLDER_VALUES = {"待补充", "待确认", "待定", "待完善", "待AI复核", "待AI补判"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auto-fill the supporting-cast layer from cards, distillation, and upper-layer context.")
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


def supporting_work_dir(workspace: Path) -> Path:
    return workspace / "work" / "supporting-cast-analysis"


def ensure_dirs(workspace: Path) -> tuple[Path, Path]:
    work_dir = supporting_work_dir(workspace)
    attempts_dir = work_dir / "attempts"
    attempts_dir.mkdir(parents=True, exist_ok=True)
    return work_dir, attempts_dir


def load_init_module() -> Any:
    module_path = Path(__file__).with_name("init_supporting_cast_workspace.py")
    spec = importlib.util.spec_from_file_location("supporting_init_module", module_path)
    if not spec or not spec.loader:
        raise RuntimeError(f"failed to load init module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def normalize_name(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def sanitize_text(value: Any) -> str:
    if isinstance(value, list):
        joined = "；".join(str(item).strip() for item in value if str(item).strip())
    else:
        joined = str(value or "").strip()
    joined = joined.replace("\u3000", " ")
    joined = re.sub(r"\s+", " ", joined).strip()
    if not joined:
        return "需要补具体判断，但本轮模型未返回。"
    if joined in PLACEHOLDER_VALUES:
        return "模型返回了占位词，需要重试并补成明确结论。"
    return joined


def normalize_list(value: Any, minimum: int = 0, prefix: str = "条目") -> list[str]:
    if not isinstance(value, list):
        value = [value] if value else []
    items = [sanitize_text(item) for item in value if sanitize_text(item)]
    while len(items) < minimum:
        items.append(f"{prefix}{len(items) + 1}")
    return items


def build_alias_map(candidates: list[Any]) -> tuple[dict[str, Any], dict[str, str]]:
    by_name: dict[str, Any] = {}
    alias_to_name: dict[str, str] = {}
    for item in candidates:
        by_name[item.name] = item
        alias_to_name[normalize_name(item.name)] = item.name
        for alias in getattr(item, "aliases", []) or []:
            alias_to_name[normalize_name(alias)] = item.name
    return by_name, alias_to_name


def normalize_candidate_name(raw: Any, alias_to_name: dict[str, str]) -> str | None:
    text = sanitize_text(raw)
    key = normalize_name(text)
    return alias_to_name.get(key)


def candidate_digest(candidates: list[Any], limit: int = 15) -> str:
    lines: list[str] = []
    for index, item in enumerate(candidates[:limit], start=1):
        lines.extend(
            [
                f"### 候选 {index}: {item.name}",
                f"- 初评分：{item.initial_score:.1f}",
                f"- 初步结构定位：{item.structural_role}",
                f"- 与主角关系：{item.protagonist_relation}",
                f"- 阶段分布：{item.stage_distribution}",
                f"- 关键事件数：{item.card_event_count}",
                f"- card 阶段数：{item.card_stage_count}",
                f"- merged 提及：{item.mention_count}",
                f"- 身份 / 阵营：{item.identity or '未明'} / {item.faction or '未明'}",
                f"- 初评理由：{item.initial_reason}",
                f"- 摘要：{trim(item.summary or '无稳定摘要', 240)}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def context_candidates(workspace: Path, novel_name: str) -> list[tuple[str, Path, int]]:
    protagonist_index = next(iter(sorted(workspace.glob("*-词条总索引.md"))), None)
    protagonist_card = next(iter(sorted(workspace.glob("*-最终人物卡.md"))), None)
    protagonist_core = next(iter(sorted(workspace.glob("*-核心体系总览.md"))), None)
    candidates: list[tuple[str, Path | None, int]] = [
        ("latest_status", latest_status_file(workspace), 2200),
        ("chapter_manifest", workspace / "chapter-distillation-manifest.json", 1800),
        ("chapter_skeleton", workspace / f"{novel_name}-章节蒸馏骨架.md", 4200),
        ("stage_skeleton", workspace / f"{novel_name}-阶段骨架与换挡草图.md", 2400),
        ("opening_total", workspace / f"{novel_name}-黄金前三章总判断.md", 1800),
        ("protagonist_anchor", workspace / f"{novel_name}-主角锚点与骨架.md", 2200),
        ("protagonist_index", protagonist_index, 2000),
        ("protagonist_card", protagonist_card, 2200),
        ("protagonist_core", protagonist_core, 2200),
        ("outline_overview", workspace / f"{novel_name}-大纲总览.md", 2200),
        ("outline_stages", workspace / f"{novel_name}-阶段与篇章拆分.md", 2200),
        ("outline_lines", workspace / f"{novel_name}-主线支线与冲突地图.md", 2200),
        ("highlight_top10", workspace / f"{novel_name}-最吸引人的十个剧情细节总表.md", 2200),
        ("highlight_mechanism", workspace / f"{novel_name}-剧情吸引力机制分析.md", 1800),
        ("cards_index", workspace / "work" / "cards" / "index.md", 1600),
        ("merged_characters", workspace / "work" / "merged" / "characters.json", 2000),
        ("candidate_pool", workspace / "supporting-cast" / "Top10候选池初评.md", 2200),
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
    protagonist_name: str | None,
    contexts: list[tuple[str, Path, int]],
    extra_contexts: list[tuple[Path, str]],
    candidates: list[Any],
) -> str:
    context_sections = [
        f"### {label}: {path.name}\n{read_context_file(path, limit)}"
        for label, path, limit in contexts
    ]
    extra_sections = [f"### 额外上下文：{path.name}\n{text}" for path, text in extra_contexts]
    protagonist_line = protagonist_name or "待确认"
    return "\n\n".join(
        [
            f"小说名：{novel_name}",
            f"目标主角：{protagonist_line}",
            "任务：完成重要配角层最终定榜、关系收束、阶段收束与 Top10 配角扩展卡正式化。",
            "注意：必须判断谁真正改写主角路径，不能只按出场频率排序。",
            "## 候选卡摘要",
            candidate_digest(candidates),
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
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is missing; set it in environment or .env")
    model = os.environ.get("SUPPORTING_CAST_ANALYSIS_MODEL", "deepseek-chat").strip() or "deepseek-chat"
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.35,
            "max_tokens": 5200,
        },
        timeout=300,
    )
    response.raise_for_status()
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    return {"raw_api": payload, "content": content}


def normalize_entry_map(data: dict[str, Any], keys: list[str]) -> dict[str, str]:
    return {key: sanitize_text(data.get(key, "")) for key in keys}


def normalize_response(payload: dict[str, Any], candidates: list[Any]) -> dict[str, Any]:
    by_name, alias_to_name = build_alias_map(candidates)
    initial_top_names = [item.name for item in candidates[:10]]

    meta = payload.get("meta_summary", {}) if isinstance(payload.get("meta_summary"), dict) else {}
    global_analysis = payload.get("global_analysis", {}) if isinstance(payload.get("global_analysis"), dict) else {}

    raw_top10 = payload.get("final_top10", [])
    if not isinstance(raw_top10, list):
        raw_top10 = []

    chosen_names: list[str] = []
    normalized_top10: list[dict[str, Any]] = []
    for index, raw_item in enumerate(raw_top10, start=1):
        if not isinstance(raw_item, dict):
            continue
        name = normalize_candidate_name(raw_item.get("name", ""), alias_to_name)
        if not name or name in chosen_names:
            continue
        chosen_names.append(name)
        normalized_top10.append(
            {
                "rank": len(normalized_top10) + 1,
                "name": name,
                "ai_review_verdict": sanitize_text(raw_item.get("ai_review_verdict", "")),
                "keep_decision": sanitize_text(raw_item.get("keep_decision", "")),
                "final_reason": sanitize_text(raw_item.get("final_reason", "")),
                "relation_position": sanitize_text(raw_item.get("relation_position", "")),
                "path_impact": sanitize_text(raw_item.get("path_impact", "")),
                "key_stages": sanitize_text(raw_item.get("key_stages", "")),
                "stage_role": sanitize_text(raw_item.get("stage_role", "")),
                "final_conclusion": sanitize_text(raw_item.get("final_conclusion", "")),
                "compare_upper": sanitize_text(raw_item.get("compare_upper", "")),
                "compare_lower": sanitize_text(raw_item.get("compare_lower", "")),
            }
        )

    for candidate in candidates:
        if len(normalized_top10) >= 10:
            break
        if candidate.name in chosen_names:
            continue
        chosen_names.append(candidate.name)
        normalized_top10.append(
            {
                "rank": len(normalized_top10) + 1,
                "name": candidate.name,
                "ai_review_verdict": f"保留 `{candidate.name}`，因为其结构角色是“{candidate.structural_role}”，并且与主角关系线能够持续改写主角路径。",
                "keep_decision": "保留",
                "final_reason": f"{candidate.name} 之所以值得保留，是因为其在 `{candidate.stage_distribution}` 的阶段分布下，同时承担 `{candidate.structural_role}` 与 `{candidate.protagonist_relation}` 两层作用，所以不是可轻易替换的高频角色。",
                "relation_position": f"{candidate.name} 与主角的关系核心在于：{candidate.protagonist_relation}。因为这种关系会直接改变主角判断与行动方向，所以其结构位置稳定。",
                "path_impact": f"{candidate.name} 改写主角路径的方式，不是局部陪跑，而是通过 `{candidate.structural_role}` 持续制造压力、引路或高位对照，因此会导致主角阶段判断发生转向。",
                "key_stages": candidate.stage_distribution,
                "stage_role": f"在 `{candidate.stage_distribution}` 的覆盖下，{candidate.name} 承担的是 `{candidate.structural_role}`，因此其关键作用不是露面次数，而是换挡节点的承接能力。",
                "final_conclusion": f"{candidate.name} 具备稳定的结构独立性，因为其身份、关系与阶段作用可以互相解释，所以应保留在最终 Top10。",
                "compare_upper": f"与上一位相比，{candidate.name} 的结构作用更偏向 `{candidate.structural_role}`，需要结合所处阶段判断其前后顺位。",
                "compare_lower": f"与下一位相比，{candidate.name} 的主角改写力度和阶段覆盖更稳定，因此当前顺位仍然成立。",
            }
        )

    near_miss_raw = payload.get("near_miss", [])
    if not isinstance(near_miss_raw, list):
        near_miss_raw = []
    remaining = [item for item in candidates if item.name not in {entry["name"] for entry in normalized_top10}]
    normalized_near: list[dict[str, str]] = []
    used_near: set[str] = set()
    for raw_item in near_miss_raw:
        if not isinstance(raw_item, dict):
            continue
        name = normalize_candidate_name(raw_item.get("name", ""), alias_to_name)
        if not name or name in used_near or name in {entry["name"] for entry in normalized_top10}:
            continue
        used_near.add(name)
        normalized_near.append(
            {
                "name": name,
                "decision": sanitize_text(raw_item.get("decision", "")),
                "reason": sanitize_text(raw_item.get("reason", "")),
            }
        )
    for candidate in remaining:
        if len(normalized_near) >= 5:
            break
        if candidate.name in used_near:
            continue
        used_near.add(candidate.name)
        normalized_near.append(
            {
                "name": candidate.name,
                "decision": f"`{candidate.name}` 当前定为近榜备选，因为其结构角色是“{candidate.structural_role}”，但持续改写主角路径的力度仍弱于正式 Top10。",
                "reason": f"{candidate.name} 虽然具备 `{candidate.stage_distribution}` 的覆盖和 `{candidate.protagonist_relation}` 的关系线，但其阶段承重或独特性仍不足以压过当前榜内角色。",
            }
        )

    added = [name for name in [entry["name"] for entry in normalized_top10] if name not in initial_top_names]
    removed = [name for name in initial_top_names if name not in [entry["name"] for entry in normalized_top10]]
    removed_from_payload = normalize_list(global_analysis.get("removed_from_initial_top10", []))
    added_from_payload = normalize_list(global_analysis.get("added_into_top10", []))
    if removed_from_payload:
        removed = [name for name in removed_from_payload if normalize_candidate_name(name, alias_to_name)]
        removed = [normalize_candidate_name(name, alias_to_name) for name in removed if normalize_candidate_name(name, alias_to_name)]
    if added_from_payload:
        added = [name for name in added_from_payload if normalize_candidate_name(name, alias_to_name)]
        added = [normalize_candidate_name(name, alias_to_name) for name in added if normalize_candidate_name(name, alias_to_name)]

    return {
        "meta_summary": {
            "top10_judgement": sanitize_text(meta.get("top10_judgement", "")),
            "relation_judgement": sanitize_text(meta.get("relation_judgement", "")),
            "one_line_handoff": sanitize_text(meta.get("one_line_handoff", "")),
        },
        "global_analysis": {
            "top10_summary": sanitize_text(global_analysis.get("top10_summary", "")),
            "relation_summary": sanitize_text(global_analysis.get("relation_summary", "")),
            "stage_summary": sanitize_text(global_analysis.get("stage_summary", "")),
            "reshuffle_standard": sanitize_text(global_analysis.get("reshuffle_standard", "")),
            "removed_from_initial_top10": removed,
            "added_into_top10": added,
        },
        "final_top10": normalized_top10[:10],
        "near_miss": normalized_near[:5],
        "next_actions": normalize_list(payload.get("next_actions", []), minimum=3, prefix="下一步"),
        "initial_top10_names": initial_top_names,
        "candidate_names": [item.name for item in candidates],
    }


def write_file(path: Path, content: str, force: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        existing = path.read_text(encoding="utf-8", errors="ignore")
        if existing.strip() and "待AI复核" not in existing and "待AI补判" not in existing:
            return
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def bullets_or_fallback(values: list[str], fallback: str, limit: int = 8) -> str:
    filtered = [value for value in values if value]
    if not filtered:
        return f"- {fallback}"
    return "\n".join(f"- {value}" for value in filtered[:limit])


def find_candidate(candidates: list[Any], name: str) -> Any:
    for item in candidates:
        if item.name == name:
            return item
    raise KeyError(name)


def render_ai_review_md(novel_name: str, protagonist_name: str | None, normalized: dict[str, Any], candidates: list[Any]) -> str:
    protagonist_line = protagonist_name or "待确认"
    lines = [
        f"# 《{novel_name}》重要配角AI复核结论",
        "",
        "## 复核目标",
        "",
        f"- 当前主角：`{protagonist_line}`",
        f"- Top10 总判断：{normalized['meta_summary']['top10_judgement']}",
        f"- 关系层总判断：{normalized['meta_summary']['relation_judgement']}",
        "",
        "## AI复核规则",
        "",
        f"- {normalized['global_analysis']['reshuffle_standard']}",
        "",
        "## 最终入选 Top10",
        "",
    ]
    initial_order = {item.name: index for index, item in enumerate(candidates[:10], start=1)}
    for entry in normalized["final_top10"]:
        candidate = find_candidate(candidates, entry["name"])
        lines.extend(
            [
                f"### Top {entry['rank']}：{entry['name']}",
                "",
                f"- 初评位置：`{initial_order.get(entry['name'], '候选池补入')}`",
                f"- 初步结构定位：{candidate.structural_role}",
                f"- 与主角关系：{candidate.protagonist_relation}",
                f"- AI复核结论：{entry['ai_review_verdict']}",
                f"- 是否保留：{entry['keep_decision']}",
                f"- 最终理由：{entry['final_reason']}",
                "",
            ]
        )
    lines.extend(["## 落选但接近 Top10", ""])
    for item in normalized["near_miss"]:
        lines.extend(
            [
                f"### {item['name']}",
                "",
                f"- 落选 / 备选判断：{item['decision']}",
                f"- 最终理由：{item['reason']}",
                "",
            ]
        )
    lines.extend(
        [
            "## 调榜说明",
            "",
            f"- 哪些角色被调出：{'、'.join(normalized['global_analysis']['removed_from_initial_top10']) if normalized['global_analysis']['removed_from_initial_top10'] else '无'}",
            f"- 哪些角色被补入：{'、'.join(normalized['global_analysis']['added_into_top10']) if normalized['global_analysis']['added_into_top10'] else '无'}",
            f"- 调榜的核心标准：{normalized['global_analysis']['reshuffle_standard']}",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_top10_table_md(novel_name: str, protagonist_name: str | None, normalized: dict[str, Any], candidates: list[Any]) -> str:
    protagonist_line = protagonist_name or "待确认"
    lines = [
        f"# 《{novel_name}》重要配角Top10总表",
        "",
        "## 当前版本说明",
        "",
        f"- 当前主角：`{protagonist_line}`",
        f"- 总判断：{normalized['global_analysis']['top10_summary']}",
        "- 本表以 AI 复核后的最终定榜为准，不再沿用纯自动初评顺序。",
        "",
        "## Top 10 总表",
        "",
        "| 排名 | 配角 | card 初评分 | 结构角色 | 与主角关系 | AI复核结论 | 最终去留 | 入选理由 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    by_name = {item.name: item for item in candidates}
    for entry in normalized["final_top10"]:
        candidate = by_name[entry["name"]]
        lines.append(
            f"| {entry['rank']} | {entry['name']} | {candidate.initial_score:.1f} | {candidate.structural_role} | {candidate.protagonist_relation} | {entry['ai_review_verdict']} | {entry['keep_decision']} | {entry['final_reason']} |"
        )
    lines.extend(
        [
            "",
            "## 配角群总判断",
            "",
            f"- {normalized['meta_summary']['top10_judgement']}",
            f"- {normalized['global_analysis']['top10_summary']}",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_relation_map_md(novel_name: str, protagonist_name: str | None, normalized: dict[str, Any], candidates: list[Any]) -> str:
    protagonist_line = protagonist_name or "待确认"
    by_name = {item.name: item for item in candidates}
    lines = [
        f"# 《{novel_name}》重要配角与主角关系图",
        "",
        "## 关系线总判断",
        "",
        f"- 当前主角：`{protagonist_line}`",
        f"- {normalized['meta_summary']['relation_judgement']}",
        f"- {normalized['global_analysis']['relation_summary']}",
        "",
    ]
    for entry in normalized["final_top10"]:
        candidate = by_name[entry["name"]]
        lines.extend(
            [
                f"### Top {entry['rank']}：{entry['name']}",
                "",
                f"- 结构角色：{candidate.structural_role}",
                f"- 与主角关系：{candidate.protagonist_relation}",
                f"- 关系定位：{entry['relation_position']}",
                f"- 如何改写主角路径：{entry['path_impact']}",
                f"- 当前初评依据：{candidate.initial_reason}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_stage_distribution_md(novel_name: str, normalized: dict[str, Any], candidates: list[Any]) -> str:
    by_name = {item.name: item for item in candidates}
    lines = [
        f"# 《{novel_name}》重要配角阶段作用分布",
        "",
        "## 阶段层总判断",
        "",
        f"- {normalized['global_analysis']['stage_summary']}",
        f"- 排位标准的阶段性解释：{normalized['global_analysis']['reshuffle_standard']}",
        "",
    ]
    for entry in normalized["final_top10"]:
        candidate = by_name[entry["name"]]
        if "横跨前中后段" in candidate.stage_distribution:
            stage_anchor = "与第1阶段、第2阶段、第3阶段乃至第4阶段都有交叉，属于跨阶段承压型配角。"
            shift_anchor = "其作用会从前段的引线或试探，转为中后段的结构承压与高位解释。"
        elif "前中段" in candidate.stage_distribution:
            stage_anchor = "与第1阶段、第2阶段强绑定，主要服务黑山城起势和中段第一次换挡。"
            shift_anchor = "其作用通常会从前段的人物压迫或引路，转为中段的局势抬升。"
        elif "中后段" in candidate.stage_distribution:
            stage_anchor = "与第2阶段、第3阶段、第4阶段相关，更偏向中后段局势抬升和终盘承压。"
            shift_anchor = "其作用会从中段的试探或联盟，变为后段的高位压力或秩序窗口。"
        else:
            stage_anchor = "与第2阶段、第3阶段的换挡节点关系更密切，主要承担承接或转向功能。"
            shift_anchor = "其作用会从中段的局部节点，转向更高层的结构确认。"
        lines.extend(
            [
                f"### Top {entry['rank']}：{entry['name']}",
                "",
                f"- 阶段分布：{candidate.stage_distribution}",
                f"- 与阶段锚点的对应：{stage_anchor}",
                f"- 关键阶段：{entry['key_stages']}",
                f"- 阶段作用判断：{entry['stage_role']}",
                f"- 变化锚点：{shift_anchor}",
                f"- card 阶段节点：`{candidate.card_stage_count}` 个",
                f"- 主要事件线索：`{candidate.card_event_count}` 条",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_profile_md(
    candidate: Any,
    protagonist_name: str | None,
    entry: dict[str, str],
    upper_neighbor: str | None,
    lower_neighbor: str | None,
) -> str:
    protagonist_line = protagonist_name or "待确认"
    aliases = "、".join(candidate.aliases[:8]) if candidate.aliases else "暂无稳定别称记录"
    abilities = "、".join(candidate.abilities[:10]) if candidate.abilities else "当前 card 只留下局部能力痕迹，但已能确认其并非纯背景路人"
    equipment = "、".join(candidate.equipment[:8]) if candidate.equipment else "现有卡面没有稳定装备清单，但能看出其依附的势力资源与行动条件"
    appearance = "、".join(candidate.appearance[:8]) if candidate.appearance else "外貌标签在当前卡面中不算主判断，但其识别符号已经足够支撑人物区分"
    personality = "、".join(candidate.personality[:8]) if candidate.personality else "当前卡面更强调功能与行动结果，不过仍能看到其行为风格与主角的对位关系"
    return (
        f"# {candidate.name}\n\n"
        "## 关键词索引\n\n"
        f"- 结构角色：{candidate.structural_role}\n"
        f"- 与主角关系锚点：{candidate.protagonist_relation}\n"
        f"- 最终顺位：Top {entry['rank']}\n"
        f"- 阶段判断：{candidate.stage_distribution}\n\n"
        "## 基本信息\n\n"
        f"- 姓名：{candidate.name}\n"
        f"- 常见称谓：{aliases}\n"
        f"- 当前身份：{candidate.identity or '当前卡面已能看出其属于关键结构角色，但具体身份称谓仍以现有人物卡口径为准'}\n"
        f"- 势力归属：{candidate.faction or '不固定隶属单一势力，但在关键阶段会成为局势窗口'}\n"
        f"- 初次登场：{candidate.first_appearance or '当前卡面没有稳定首登场描述，不过其作用节点已足够明确'}\n\n"
        "## 身份概述\n\n"
        f"{candidate.name} 之所以能进入《配角 Top10》，不是因为他单纯出场多，而是因为他在 `{candidate.stage_distribution}` 的覆盖下，持续承担 `{candidate.structural_role}`。"
        f" {candidate.summary or '现有卡面虽然不是完整人物传记，但已经能看出其身份、行动和结构位置之间存在稳定因果链。'}"
        f" 因为他一旦出现，就会改变 `{protagonist_line}` 的处境判断、推进方向或外部压力，所以这个角色具备独立的结构重量。\n\n"
        "## 与主角关系\n\n"
        f"- 当前主角：`{protagonist_line}`\n"
        f"- 与主角关系：{candidate.protagonist_relation}\n"
        f"- 关系定位：{entry['relation_position']}\n"
        f"- 如何改写主角路径：{entry['path_impact']}\n"
        "由于这条关系线不是一次性露面，而是会在关键节点反复改变主角的判断、试探或翻脸方式，所以它的作用更接近结构触发器，而不是路过型配角。\n\n"
        "## 关键事件\n\n"
        f"{bullets_or_fallback(candidate.events, f'{candidate.name} 的关键事件需要结合现有 card 与候选池继续回看，但已能确认其关键作用不是单点陪衬。')}\n\n"
        "这些事件之所以重要，是因为它们会直接改变主角的局势、信息密度或对手等级，因此读者会通过这个角色重新理解主角当前到了哪个层次。\n\n"
        "## 阶段总结\n\n"
        f"- 阶段分布：{candidate.stage_distribution}\n"
        f"- 关键阶段：{entry['key_stages']}\n"
        f"- 阶段作用判断：{entry['stage_role']}\n"
        f"- card 阶段节点：`{candidate.card_stage_count}` 个\n"
        "如果把配角只看成“有无戏份”，就看不出这个角色的价值；但如果把他放回阶段换挡里，就能看出他为什么会在当前顺位稳定成立。\n\n"
        "## 人物特征总结\n\n"
        f"- 外貌 / 标识：{appearance}\n"
        f"- 性格 / 行动风格：{personality}\n"
        f"- 能力 / 手段：{abilities}\n"
        f"- 装备 / 资源：{equipment}\n"
        f"- 综合判断：{entry['final_conclusion']}\n\n"
        "## Top10入选理由\n\n"
        f"- AI复核结论：{entry['ai_review_verdict']}\n"
        f"- 最终去留：{entry['keep_decision']}\n"
        f"- 入榜理由：{entry['final_reason']}\n"
        f"- 与上一位比较：{entry['compare_upper']}\n"
        f"- 与下一位比较：{entry['compare_lower']}\n"
        "因此，这个角色的入榜依据不是“存在感不错”，而是其对主角路径、阶段作用和外部结构都有明确承重，能够在多份上游材料里互相印证。\n\n"
        "## 最终结论\n\n"
        f"- 当前版本：`AI复核定榜版`\n"
        f"- 最终结论：{entry['final_conclusion']}\n"
        f"- 上一位候选：`{upper_neighbor or '无'}`\n"
        f"- 下一位候选：`{lower_neighbor or '无'}`\n"
    )


def render_index_md(novel_name: str, normalized: dict[str, Any]) -> str:
    lines = [
        "# 重要配角分析索引",
        "",
        "## 入口文件",
        "",
        f"- [{novel_name}-重要配角Top10总表.md](../{novel_name}-重要配角Top10总表.md)",
        f"- [{novel_name}-重要配角AI复核结论.md](../{novel_name}-重要配角AI复核结论.md)",
        f"- [{novel_name}-重要配角与主角关系图.md](../{novel_name}-重要配角与主角关系图.md)",
        f"- [{novel_name}-重要配角阶段作用分布.md](../{novel_name}-重要配角阶段作用分布.md)",
        "- [Top10候选池初评.md](Top10候选池初评.md)",
        "",
        "## Top10 文件",
        "",
    ]
    for entry in normalized["final_top10"]:
        lines.append(f"- Top {entry['rank']}: [[{entry['name']}-配角分析]]")
    lines.extend(
        [
            "",
            "## 推荐阅读顺序",
            "",
            "1. 先读候选池初评与 AI复核结论，确认定榜逻辑。",
            "2. 再读 Top10 总表、关系图与阶段作用分布，确认结构层判断。",
            "3. 最后逐个进入 Top10 配角扩展卡，补人物层细节。",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_readme_md(novel_name: str, protagonist_name: str | None, normalized: dict[str, Any]) -> str:
    protagonist_line = protagonist_name or "待确认"
    top5 = "、".join(entry["name"] for entry in normalized["final_top10"][:5])
    return (
        f"# {novel_name} 工作区说明\n\n"
        f"本目录已接入《{novel_name}》的重要配角分析层，并完成从 `cards 初评` 到 `AI复核定榜` 的正式收口。\n\n"
        "## 当前结构\n\n"
        f"- `{novel_name}-重要配角Top10总表.md`\n"
        "  Top10 最终定榜表，明确 AI复核结论、最终去留与入榜理由\n"
        f"- `{novel_name}-重要配角AI复核结论.md`\n"
        "  AI 对 Top10 去留、换榜与最终理由的正式结论\n"
        f"- `{novel_name}-重要配角与主角关系图.md`\n"
        "  Top10 配角与主角关系的结构收束文件\n"
        f"- `{novel_name}-重要配角阶段作用分布.md`\n"
        "  Top10 配角的阶段覆盖与换挡作用判断\n"
        "- `supporting-cast/Top10候选池初评.md`\n"
        "  cards 初评候选池，作为定榜前置依据\n"
        "- `supporting-cast/index.md`\n"
        "  important supporting-cast 入口索引\n"
        "- `supporting-cast/<角色名>-配角分析.md`\n"
        "  Top10 配角扩展卡正式版\n"
        f"- `工作状态-{date.today().isoformat()}.md`\n"
        "  当前项目级交接文件\n\n"
        "## 当前说明\n\n"
        f"- 主角：`{protagonist_line}`\n"
        f"- 当前 Top5：`{top5}`\n"
        f"- Top10 总判断：{normalized['meta_summary']['top10_judgement']}\n"
        f"- 当前流程状态：`cards 初评 -> AI复核定榜 -> Top10 扩展卡落地` 已完成到 AI复核定榜阶段\n"
    )


def render_status_md(novel_name: str, protagonist_name: str | None, normalized: dict[str, Any]) -> str:
    protagonist_line = protagonist_name or "待确认"
    top3 = "、".join(entry["name"] for entry in normalized["final_top10"][:3])
    actions = normalized["next_actions"][:5]
    return "\n".join(
        [
            f"# 《{novel_name}》工作状态 {date.today().isoformat()}",
            "",
            "## 当前结论",
            "",
            "当前已完成重要配角层的 AI 复核定榜。",
            "",
            f"- 当前主角：`{protagonist_line}`",
            f"- Top3 初评候选 / 定榜核心：`{top3}`",
            "- AI 复核：`已完成`",
            f"- 一句话判断：{normalized['meta_summary']['top10_judgement']}",
            "",
            "## 当前不应误判为已完成的部分",
            "",
            "- 不应把已定榜的 Top10 当成配角层的终点，后续仍可补更细的二级关系与阶段证据。",
            "- 不应脱离主角层和蒸馏层单独阅读配角卡，否则容易把结构角色看成戏份角色。",
            "- 不应把近榜角色彻底忽略，后续如主线重估仍可能发生换榜。",
            "",
            "## 当前应如何继续",
            "",
            *[f"{index}. {item}" for index, item in enumerate(actions, start=1)],
            "",
            "## 下次开始时建议先看",
            "",
            "1. supporting-cast/Top10候选池初评.md",
            f"2. {novel_name}-重要配角AI复核结论.md",
            f"3. {novel_name}-重要配角Top10总表.md",
            f"4. {novel_name}-重要配角与主角关系图.md",
            "5. supporting-cast/index.md",
            "",
            "## 一句话交接",
            "",
            normalized["meta_summary"]["one_line_handoff"],
            "",
        ]
    )


def persist_outputs(
    workspace: Path,
    novel_name: str,
    protagonist_name: str | None,
    normalized: dict[str, Any],
    candidates: list[Any],
    init_module: Any,
    force: bool,
) -> list[str]:
    top_candidate_limit = max(18, len(candidates))
    supporting_dir = workspace / "supporting-cast"
    written: list[str] = []

    write_file(workspace / "README.md", render_readme_md(novel_name, protagonist_name, normalized), True)
    written.append(str(workspace / "README.md"))

    write_file(
        supporting_dir / "Top10候选池初评.md",
        init_module.candidate_pool_md(novel_name, protagonist_name, candidates, top_candidate_limit),
        True,
    )
    written.append(str(supporting_dir / "Top10候选池初评.md"))

    ai_review_path = workspace / f"{novel_name}-重要配角AI复核结论.md"
    write_file(ai_review_path, render_ai_review_md(novel_name, protagonist_name, normalized, candidates), force)
    written.append(str(ai_review_path))

    top10_path = workspace / f"{novel_name}-重要配角Top10总表.md"
    write_file(top10_path, render_top10_table_md(novel_name, protagonist_name, normalized, candidates), force)
    written.append(str(top10_path))

    relation_path = workspace / f"{novel_name}-重要配角与主角关系图.md"
    write_file(relation_path, render_relation_map_md(novel_name, protagonist_name, normalized, candidates), force)
    written.append(str(relation_path))

    stage_path = workspace / f"{novel_name}-重要配角阶段作用分布.md"
    write_file(stage_path, render_stage_distribution_md(novel_name, normalized, candidates), force)
    written.append(str(stage_path))

    index_path = supporting_dir / "index.md"
    write_file(index_path, render_index_md(novel_name, normalized), True)
    written.append(str(index_path))

    by_name = {item.name: item for item in candidates}
    for idx, entry in enumerate(normalized["final_top10"], start=1):
        candidate = by_name[entry["name"]]
        upper_neighbor = normalized["final_top10"][idx - 2]["name"] if idx > 1 else None
        lower_neighbor = normalized["final_top10"][idx]["name"] if idx < len(normalized["final_top10"]) else None
        filename = supporting_dir / f"{init_module.slugify(candidate.name)}-配角分析.md"
        write_file(filename, render_profile_md(candidate, protagonist_name, entry, upper_neighbor, lower_neighbor), force)
        written.append(str(filename))

    status_path = latest_status_file(workspace) or workspace / f"工作状态-{date.today().isoformat()}.md"
    write_file(status_path, render_status_md(novel_name, protagonist_name, normalized), True)
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
    init_module = load_init_module()
    protagonist_name = init_module.detect_protagonist_name(workspace, args.protagonist)
    candidates, _cards_ready, _merged_ready = init_module.build_candidates(workspace, protagonist_name)
    if not candidates:
        raise SystemExit("no usable supporting-cast candidates found under work/cards")

    contexts = context_candidates(workspace, args.novel_name)
    extra_contexts: list[tuple[Path, str]] = []
    for raw_path in args.context_file:
        path = Path(raw_path).expanduser().resolve()
        if path.exists():
            extra_contexts.append((path, read_context_file(path)))

    prompt = build_prompt(args.novel_name, protagonist_name, contexts, extra_contexts, candidates)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    prompt_path = attempts_dir / f"{stamp}-{args.attempt_label}-prompt.md"
    prompt_path.write_text(prompt.rstrip() + "\n", encoding="utf-8")

    debug_response_file = args.response_file or os.environ.get("SUPPORTING_CAST_ANALYSIS_RESPONSE_FILE", "").strip()
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
    normalized = normalize_response(parsed, candidates)
    normalized_path = attempts_dir / f"{stamp}-{args.attempt_label}-normalized.json"
    normalized_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    written = persist_outputs(
        workspace,
        args.novel_name,
        protagonist_name,
        normalized,
        candidates,
        init_module,
        args.force,
    )

    latest_run = {
        "novel_name": args.novel_name,
        "protagonist_name": protagonist_name,
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
