#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

GENERIC_NAMES = {
    "对方",
    "还有",
    "引路人",
    "大头目",
    "路人",
    "旁人",
    "众人",
    "某人",
    "此人",
}

AI_PLACEHOLDER = "待AI复核"


def read_text(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def write_file(path: Path, content: str, force: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def find_refresh_status_script() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "novel-workspace-orchestrator-skill/scripts/refresh_workspace_status.py"
        if candidate.exists():
            return candidate
    return None


def refresh_workspace_status(workspace: Path, novel_name: str, protagonist: str | None) -> None:
    script = find_refresh_status_script()
    if not script:
        return
    cmd = ["python3", str(script), "--workspace", str(workspace), "--novel-name", novel_name]
    if protagonist:
        cmd += ["--protagonist-name", protagonist]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        message = proc.stderr.strip() or proc.stdout.strip() or "unknown error"
        print(f"warning: failed to refresh workspace-status.json: {message}")


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


def latest_status_file(workspace: Path) -> Path | None:
    candidates = sorted(workspace.glob("工作状态-*.md"))
    return candidates[-1] if candidates else None


def slugify(name: str) -> str:
    return name.replace("/", "_")


def normalize_name(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def chunk_order(chunk_id: str) -> int:
    match = re.search(r"(\d+)$", chunk_id)
    return int(match.group(1)) if match else 999999


def looks_like_candidate_name(name: str) -> bool:
    stripped = (name or "").strip()
    if not stripped:
        return False
    if stripped in GENERIC_NAMES:
        return False
    if any(ch.isdigit() for ch in stripped):
        return False
    if len(stripped) < 2 or len(stripped) > 12:
        return False
    return True


def parse_card_index(path: Path) -> list[str]:
    names: list[str] = []
    text = read_text(path)
    for line in text.splitlines():
        match = re.search(r"\[\[(.+?)\]\]", line)
        if match:
            names.append(match.group(1).strip())
    return names


def parse_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(line)
    return {key: "\n".join(value).strip() for key, value in sections.items()}


def extract_field(section_text: str, label: str) -> str:
    pattern = rf"^\s*-\s*{re.escape(label)}[:：]\s*(.+?)\s*$"
    match = re.search(pattern, section_text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def extract_bullets(section_text: str) -> list[str]:
    bullets = []
    for line in section_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
    return bullets


def split_abilities_and_equipment(section_text: str) -> tuple[list[str], list[str]]:
    abilities: list[str] = []
    equipment: list[str] = []
    for bullet in extract_bullets(section_text):
        if bullet.startswith("能力："):
            value = bullet.split("：", 1)[1].strip()
            if value:
                abilities.append(value)
        elif bullet.startswith("装备："):
            value = bullet.split("：", 1)[1].strip()
            if value:
                equipment.append(value)
    return abilities, equipment


def clean_summary(section_text: str) -> str:
    lines = [line.strip() for line in section_text.splitlines() if line.strip()]
    return "\n".join(lines)


def unique_keep_order(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def load_merged_characters(path: Path) -> list[dict]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else []


def build_merged_maps(merged: list[dict]) -> tuple[dict[str, dict], dict[str, str]]:
    merged_by_name: dict[str, dict] = {}
    canonical_by_alias: dict[str, str] = {}
    for item in merged:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        merged_by_name[name] = item
        all_names = [name]
        all_names.extend(
            alias.strip()
            for alias in item.get("aliases", [])
            if isinstance(alias, str) and alias.strip()
        )
        for alias in all_names:
            canonical_by_alias[normalize_name(alias)] = name
    return merged_by_name, canonical_by_alias


def protagonist_aliases(merged: list[dict], protagonist: str | None) -> set[str]:
    aliases: set[str] = set()
    if protagonist:
        aliases.add(protagonist)
    for item in merged:
        name = (item.get("name") or "").strip()
        alias_list = [alias.strip() for alias in item.get("aliases", []) if isinstance(alias, str) and alias.strip()]
        if protagonist and (name == protagonist or protagonist in alias_list):
            aliases.add(name)
            aliases.update(alias_list)
    return aliases


def classify_stage_distribution(chunks: list[str], stage_nodes: list[str], max_order: int) -> str:
    if chunks:
        orders = sorted(chunk_order(chunk) for chunk in set(chunks))
        early = len([num for num in orders if num <= max(1, max_order // 3)])
        late_threshold = max(1, (max_order * 2) // 3)
        late = len([num for num in orders if num >= late_threshold])
        if early and late:
            return "横跨前中后段，属于持续承压型配角"
        if early:
            return "主要集中在前中段，更像开局引线或早期压力源"
        if late:
            return "主要集中在中后段，更像抬升局势或终盘压力源"
        return "主要集中在中段，承担阶段换挡或结构承接作用"
    if len(stage_nodes) >= 4:
        return "卡面覆盖多个阶段，明显不是一次性功能配角"
    if len(stage_nodes) >= 2:
        return "至少跨过两个阶段，具备中程结构作用"
    if stage_nodes:
        return "当前卡面只明确到局部阶段，仍需结合原文补判"
    return "暂无稳定阶段信息"


def protagonist_relation_from_card(
    relationships: list[str],
    summary: str,
    events: list[str],
    protagonist_names: set[str],
) -> tuple[str, int]:
    if not protagonist_names:
        return "主角关系待结合人物卡再确认", 0

    normalized_protagonists = {normalize_name(name) for name in protagonist_names if name}
    direct_types: list[str] = []
    direct_hits = 0

    for line in relationships:
        left, _, right = line.partition(":")
        target = normalize_name(left)
        if target in normalized_protagonists:
            relation = right.strip() or "存在直接关系"
            direct_types.append(relation)
            direct_hits += 1

    joined = "\n".join([summary] + events + relationships)
    summary_hits = sum(1 for name in protagonist_names if name and name in joined)
    if direct_types:
        return "；".join(unique_keep_order(direct_types)), max(direct_hits, summary_hits)
    if summary_hits:
        return "卡面内容中与主角有直接交集，但关系类型仍需 AI 精炼", summary_hits
    return "当前 card 未显式写清主角关系，需结合原文补判", 0


def infer_structural_role(
    summary: str,
    relationships: list[str],
    events: list[str],
    faction: str,
    protagonist_relation: str,
    protagonist_hits: int,
    stage_distribution: str,
) -> str:
    combined = "\n".join([summary, protagonist_relation] + relationships + events)
    tags: list[str] = []

    if protagonist_hits >= 3:
        tags.append("主角路径改写点")
    elif protagonist_hits >= 1 or "主角" in protagonist_relation:
        tags.append("主角关系支点")

    if faction:
        tags.append("势力窗口")

    if "横跨前中后段" in stage_distribution or "多个阶段" in stage_distribution:
        tags.append("跨阶段支点")
    elif "两个阶段" in stage_distribution or "中段" in stage_distribution:
        tags.append("阶段换挡触发器")

    if any(keyword in combined for keyword in ("师傅", "师兄", "收徒", "传授", "引路", "指点", "救命恩人")):
        tags.append("引路/传承配角")
    if any(keyword in combined for keyword in ("敌对", "敌人", "追杀", "对手", "死敌", "压制", "背叛")):
        tags.append("压力/对抗配角")
    if any(keyword in combined for keyword in ("朋友", "同行者", "盟友", "合作", "姐妹", "祖孙", "情感")):
        tags.append("联盟/情感支点")

    if not tags:
        tags.append("阶段性关键配角")
    return " / ".join(unique_keep_order(tags))


@dataclass
class Candidate:
    name: str
    source_card_name: str
    card_path: Path
    aliases: list[str]
    identity: str
    faction: str
    status: str
    first_appearance: str
    summary: str
    appearance: list[str]
    personality: list[str]
    abilities: list[str]
    equipment: list[str]
    relationships: list[str]
    events: list[str]
    stage_lines: list[str]
    stage_nodes: list[str]
    evidence: list[str]
    mention_count: int
    chunks: list[str]
    merged_relation_count: int
    merged_timeline_count: int
    initial_score: float
    initial_reason: str
    protagonist_relation: str
    stage_distribution: str
    structural_role: str
    protagonist_hit_count: int
    card_relation_count: int
    card_stage_count: int
    card_event_count: int
    card_completeness: int


def build_candidate_from_card(
    card_name: str,
    card_path: Path,
    canonical_name: str,
    merged_item: dict | None,
    protagonist_names: set[str],
    max_chunk_order: int,
) -> Candidate | None:
    if not looks_like_candidate_name(canonical_name):
        return None

    text = read_text(card_path)
    sections = parse_sections(text)
    if not sections:
        return None

    basic_info = sections.get("基本信息", "")
    summary = clean_summary(sections.get("人物概述", ""))
    appearance = extract_bullets(sections.get("外貌与特征", ""))
    personality = extract_bullets(sections.get("性格与行为", ""))
    abilities, equipment = split_abilities_and_equipment(sections.get("能力体系", ""))
    stage_section = sections.get("身份与阶段变化", "")
    stage_lines = extract_bullets(stage_section)
    stage_nodes = re.findall(r"^###\s+(.+?)\s*$", stage_section, flags=re.MULTILINE)
    if not stage_nodes:
        stage_nodes = unique_keep_order(
            line.split("：", 1)[0].strip() for line in stage_lines if "：" in line
        )
    relationships = extract_bullets(sections.get("关键关系", ""))
    events = extract_bullets(sections.get("关键事件", ""))
    evidence = extract_bullets(sections.get("重要证据", ""))

    name = extract_field(basic_info, "姓名") or canonical_name
    aliases = []
    alias_field = extract_field(basic_info, "别名")
    if alias_field:
        aliases.extend(part.strip() for part in alias_field.split("、") if part.strip())
    if merged_item:
        aliases.extend(
            alias.strip()
            for alias in merged_item.get("aliases", [])
            if isinstance(alias, str) and alias.strip()
        )
    aliases = unique_keep_order(aliases)

    identity = extract_field(basic_info, "身份") or ((merged_item or {}).get("identity") or "").strip()
    faction = extract_field(basic_info, "阵营") or ((merged_item or {}).get("faction") or "").strip()
    status = extract_field(basic_info, "当前状态") or ((merged_item or {}).get("status") or "").strip()
    first_appearance = (
        extract_field(basic_info, "初次登场")
        or ((merged_item or {}).get("first_appearance") or (merged_item or {}).get("first_appearance_text") or "").strip()
    )
    mention_count = 0
    mention_field = extract_field(basic_info, "提及次数")
    if mention_field:
        mention_count = int(re.search(r"\d+", mention_field).group(0)) if re.search(r"\d+", mention_field) else 0
    elif merged_item:
        mention_count = int(merged_item.get("mention_count") or 0)

    chunks = [str(value) for value in (merged_item or {}).get("chunks", []) if value]
    merged_relation_count = len((merged_item or {}).get("relationships") or [])
    merged_timeline_count = len((merged_item or {}).get("timeline") or [])

    protagonist_relation, protagonist_hits = protagonist_relation_from_card(
        relationships,
        summary,
        events,
        protagonist_names,
    )
    stage_distribution = classify_stage_distribution(chunks, stage_nodes, max_chunk_order or 1)
    structural_role = infer_structural_role(
        summary,
        relationships,
        events,
        faction,
        protagonist_relation,
        protagonist_hits,
        stage_distribution,
    )

    card_relation_count = len(relationships)
    card_stage_count = len(stage_nodes) or len(stage_lines)
    card_event_count = len(events)
    card_completeness = sum(
        1
        for value in (
            summary,
            identity,
            faction,
            relationships,
            stage_lines,
            events,
            evidence,
            abilities,
        )
        if value
    )
    summary_bonus = min(12, len(summary) // 36) if summary else 0
    mention_bonus = min(20, mention_count / 12) if mention_count else 0
    chunk_bonus = min(18, len(set(chunks)) * 1.5) if chunks else 0

    initial_score = (
        protagonist_hits * 20
        + card_relation_count * 6
        + card_stage_count * 8
        + card_event_count * 4
        + card_completeness * 5
        + (8 if faction else 0)
        + mention_bonus
        + chunk_bonus
        + min(12, merged_relation_count * 1.5)
        + min(12, merged_timeline_count * 1.5)
        + summary_bonus
    )

    reasons = [
        f"card 关系 `{card_relation_count}` 条",
        f"card 阶段节点 `{card_stage_count}` 个",
        f"card 关键事件 `{card_event_count}` 条",
    ]
    if protagonist_hits:
        reasons.append(f"与主角直接交集 `{protagonist_hits}` 处")
    if mention_count:
        reasons.append(f"merged 提及 `{mention_count}` 次")
    if chunks:
        reasons.append(f"merged 覆盖 `{len(set(chunks))}` 个 chunk")
    if faction:
        reasons.append(f"具备明确势力位 `{faction}`")

    return Candidate(
        name=name,
        source_card_name=card_name,
        card_path=card_path,
        aliases=aliases,
        identity=identity,
        faction=faction,
        status=status,
        first_appearance=first_appearance,
        summary=summary,
        appearance=appearance,
        personality=personality,
        abilities=abilities,
        equipment=equipment,
        relationships=relationships,
        events=events,
        stage_lines=stage_lines,
        stage_nodes=stage_nodes,
        evidence=evidence,
        mention_count=mention_count,
        chunks=chunks,
        merged_relation_count=merged_relation_count,
        merged_timeline_count=merged_timeline_count,
        initial_score=initial_score,
        initial_reason="；".join(reasons),
        protagonist_relation=protagonist_relation,
        stage_distribution=stage_distribution,
        structural_role=structural_role,
        protagonist_hit_count=protagonist_hits,
        card_relation_count=card_relation_count,
        card_stage_count=card_stage_count,
        card_event_count=card_event_count,
        card_completeness=card_completeness,
    )


def build_candidates(
    workspace: Path,
    protagonist: str | None,
) -> tuple[list[Candidate], bool, bool]:
    cards_index = workspace / "work" / "cards" / "index.md"
    card_dir = workspace / "work" / "cards"
    if not cards_index.exists():
        raise SystemExit(f"card index not found: {cards_index}")

    merged_path = workspace / "work" / "merged" / "characters.json"
    merged = load_merged_characters(merged_path)
    merged_by_name, canonical_by_alias = build_merged_maps(merged)

    protagonist_names = protagonist_aliases(merged, protagonist)
    if protagonist:
        protagonist_names.add(protagonist)
    normalized_protagonists = {normalize_name(name) for name in protagonist_names if name}

    max_chunk_order = 0
    for item in merged:
        for chunk in item.get("chunks") or []:
            max_chunk_order = max(max_chunk_order, chunk_order(str(chunk)))

    by_canonical: dict[str, Candidate] = {}
    for card_name in parse_card_index(cards_index):
        if not looks_like_candidate_name(card_name):
            continue
        normalized = normalize_name(card_name)
        canonical_name = canonical_by_alias.get(normalized, card_name)
        if normalize_name(canonical_name) in normalized_protagonists:
            continue
        card_path = card_dir / f"{card_name}.md"
        if not card_path.exists():
            continue
        candidate = build_candidate_from_card(
            card_name,
            card_path,
            canonical_name,
            merged_by_name.get(canonical_name),
            protagonist_names,
            max_chunk_order,
        )
        if not candidate:
            continue
        existing = by_canonical.get(normalize_name(candidate.name))
        if existing is None or candidate.initial_score > existing.initial_score:
            by_canonical[normalize_name(candidate.name)] = candidate

    candidates = sorted(
        by_canonical.values(),
        key=lambda item: (
            -item.initial_score,
            -item.protagonist_hit_count,
            -item.card_relation_count,
            -item.card_event_count,
            -item.mention_count,
            item.name,
        ),
    )
    return candidates, cards_index.exists(), merged_path.exists()


def candidate_pool_md(
    novel_name: str,
    protagonist: str | None,
    candidates: list[Candidate],
    candidate_pool_size: int,
) -> str:
    protagonist_line = protagonist or "待确认"
    lines = [
        f"# 《{novel_name}》Top10候选池初评",
        "",
        "## 当前说明",
        "",
        f"- 当前主角：`{protagonist_line}`",
        "- 这一版候选池以 `work/cards/*.md` 为主要评估面，`merged/characters.json` 只作为辅助证据。",
        "- 该文件只负责把最值得进入 AI 复核的候选池缩出来，不等于最终 Top10 已经定榜。",
        "",
        "## 候选池总表",
        "",
        "| 初评排名 | 配角 | card 初评分 | 与主角交集 | card 关系数 | card 阶段数 | merged 提及 | 初步结构定位 | 初评理由 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for index, item in enumerate(candidates[:candidate_pool_size], start=1):
        lines.append(
            f"| {index} | {item.name} | {item.initial_score:.1f} | {item.protagonist_hit_count} | {item.card_relation_count} | {item.card_stage_count} | {item.mention_count} | {item.structural_role} | {item.initial_reason} |"
        )
    lines.extend(
        [
            "",
            "## 初评使用规则",
            "",
            "- 初评只负责把“值得复核”的人捞出来，不负责最终定榜。",
            "- 如果出现高频但结构可替代的角色，AI 复核时应主动调出 Top10。",
            "- 如果出现提及不算极高、但明显改变主角路径的角色，AI 复核时应主动补入。",
        ]
    )
    return "\n".join(lines)


def ai_review_md(
    novel_name: str,
    protagonist: str | None,
    top_candidates: list[Candidate],
    near_miss_candidates: list[Candidate],
) -> str:
    protagonist_line = protagonist or "待确认"
    lines = [
        f"# 《{novel_name}》重要配角AI复核结论",
        "",
        "## 复核目标",
        "",
        f"- 当前主角：`{protagonist_line}`",
        "- 本文件必须由 AI 读完候选池、主角卡、阶段文件后给出最终定榜判断。",
        "- 不允许仅沿用自动初评顺序。",
        "",
        "## AI复核规则",
        "",
        "1. 先看这个角色是否真实改写主角路径，而不是只看出场频率。",
        "2. 再看这个角色是否承担阶段换挡、阵营窗口、情感支点或高位压力。",
        "3. 如果一个高频角色结构功能可替代，应允许其掉出 Top10。",
        "4. 如果一个中频角色承担关键结构节点，应允许其挤入 Top10。",
        "",
        "## 最终入选 Top10",
        "",
    ]
    for index, item in enumerate(top_candidates, start=1):
        lines.extend(
            [
                f"### Top {index}：{item.name}",
                "",
                f"- 初评位置：`{index}`",
                f"- 初步结构定位：{item.structural_role}",
                f"- 与主角关系：{item.protagonist_relation}",
                f"- AI复核结论：{AI_PLACEHOLDER}",
                f"- 是否保留：{AI_PLACEHOLDER}",
                f"- 最终理由：{AI_PLACEHOLDER}",
                "",
            ]
        )
    lines.extend(
        [
            "## 落选但接近 Top10",
            "",
        ]
    )
    for item in near_miss_candidates[:5]:
        lines.extend(
            [
                f"### {item.name}",
                "",
                f"- 初步结构定位：{item.structural_role}",
                f"- 初评理由：{item.initial_reason}",
                f"- 落选 / 备选判断：{AI_PLACEHOLDER}",
                "",
            ]
        )
    lines.extend(
        [
            "## 调榜说明",
            "",
            f"- 哪些角色被调出：{AI_PLACEHOLDER}",
            f"- 哪些角色被补入：{AI_PLACEHOLDER}",
            f"- 调榜的核心标准：{AI_PLACEHOLDER}",
        ]
    )
    return "\n".join(lines).rstrip()


def top10_table_md(novel_name: str, protagonist: str | None, top_candidates: list[Candidate]) -> str:
    protagonist_line = protagonist or "待确认"
    lines = [
        f"# 《{novel_name}》重要配角Top10总表",
        "",
        "## 当前版本说明",
        "",
        f"- 当前主角：`{protagonist_line}`",
        "- 本表先承接 `work/cards/*.md` 的初评排序，再等待 AI 复核给出最终去留判断。",
        f"- 如果表内仍出现 `{AI_PLACEHOLDER}`，说明 Top10 还没有正式定榜。",
        "",
        "## Top 10 总表",
        "",
        "| 排名 | 配角 | card 初评分 | 结构角色 | 与主角关系 | AI复核结论 | 最终去留 | 入选理由 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for index, item in enumerate(top_candidates, start=1):
        lines.append(
            f"| {index} | {item.name} | {item.initial_score:.1f} | {item.structural_role} | {item.protagonist_relation} | {AI_PLACEHOLDER} | {AI_PLACEHOLDER} | {AI_PLACEHOLDER} |"
        )
    lines.extend(
        [
            "",
            "## 使用说明",
            "",
            "- 先完成 AI 复核结论，再回填本表。",
            "- 本表的最终顺序应以结构重要性为主，不以自动初评顺序为绝对标准。",
            "- 定榜后，再补齐每个 Top10 配角的扩展卡最终结论。",
        ]
    )
    return "\n".join(lines)


def relation_map_md(novel_name: str, protagonist: str | None, top_candidates: list[Candidate]) -> str:
    protagonist_line = protagonist or "待确认"
    lines = [
        f"# 《{novel_name}》重要配角与主角关系图",
        "",
        "## 关系线总判断",
        "",
        f"- 当前主角：`{protagonist_line}`",
        "- 这一层必须回答谁真正改变主角路径，而不是谁只在局部段落里高频出现。",
        f"- 每条关系线的最终关系定位都需要 AI 复核；如果仍出现 `{AI_PLACEHOLDER}`，说明关系层没有真正收口。",
        "",
    ]
    for index, item in enumerate(top_candidates, start=1):
        lines.extend(
            [
                f"### Top {index}：{item.name}",
                "",
                f"- 结构角色：{item.structural_role}",
                f"- 与主角关系：{item.protagonist_relation}",
                f"- 关系定位：{AI_PLACEHOLDER}",
                f"- 如何改写主角路径：{AI_PLACEHOLDER}",
                f"- 当前初评依据：{item.initial_reason}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def stage_distribution_md(novel_name: str, top_candidates: list[Candidate]) -> str:
    lines = [
        f"# 《{novel_name}》重要配角阶段作用分布",
        "",
        "## 阶段层总判断",
        "",
        "- 本文件关注 Top10 配角分别在哪些阶段承担压力、护持、背叛、镜像、换挡或高位窗口作用。",
        f"- 如果每个角色的关键阶段与阶段作用判断仍是 `{AI_PLACEHOLDER}`，说明这一层还只是初评。",
        "",
    ]
    for index, item in enumerate(top_candidates, start=1):
        lines.extend(
            [
                f"### Top {index}：{item.name}",
                "",
                f"- 阶段分布：{item.stage_distribution}",
                f"- 关键阶段：{AI_PLACEHOLDER}",
                f"- 阶段作用判断：{AI_PLACEHOLDER}",
                f"- card 阶段节点：`{item.card_stage_count}` 个",
                f"- 主要事件线索：`{item.card_event_count}` 条",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def supporting_file_md(
    index: int,
    candidate: Candidate,
    protagonist: str | None,
    upper_neighbor: Candidate | None,
    lower_neighbor: Candidate | None,
) -> str:
    protagonist_line = protagonist or "待确认"
    aliases = "、".join(candidate.aliases) if candidate.aliases else "无"
    appearance = "、".join(candidate.appearance[:8]) if candidate.appearance else "待从原文补显著外貌特征"
    personality = "、".join(candidate.personality[:8]) if candidate.personality else "待从原文补行动风格"
    abilities = "、".join(candidate.abilities[:10]) if candidate.abilities else "待从原文补能力结构"
    equipment = "、".join(candidate.equipment[:8]) if candidate.equipment else "待从原文补资源与关键物品"
    stage_summary = "\n".join(f"- {line}" for line in candidate.stage_lines[:10]) or "- 待从原文补阶段变化"
    relation_lines = "\n".join(f"- {line}" for line in candidate.relationships[:10]) or "- 待从原文补关键关系"
    event_lines = "\n".join(f"- {line}" for line in candidate.events[:10]) or "- 待从原文补关键事件"
    evidence_lines = "\n".join(f"- {line}" for line in candidate.evidence[:6]) or "- 待从原文补核心证据"
    activity_range = (
        f"- 初次登场：{candidate.first_appearance or '待补'}\n"
        f"- merged 覆盖 chunk：`{len(set(candidate.chunks))}`\n"
        f"- 代表性 chunk：`{', '.join(candidate.chunks[:8]) if candidate.chunks else '待补'}`"
    )
    upper_name = upper_neighbor.name if upper_neighbor else "无"
    lower_name = lower_neighbor.name if lower_neighbor else "无"

    return f"""# {candidate.name}

## 关键词索引

- **角色定位**：{candidate.structural_role}
- **关系锚点**：{candidate.protagonist_relation}
- **阶段判断**：{candidate.stage_distribution}
- **入榜入口**：Top {index} 初评候选

## 基本信息

- 姓名：{candidate.name}
- 常见称谓：{aliases}
- 当前确认定位：重要配角 Top10 初评候选
- 开篇身份：{candidate.identity or '待补'}
- 身份底座：{candidate.identity or '待补'}

## 身份概述

{candidate.summary or '待从原文与 card 摘要补身份概述。'}

## 身份变化

{stage_summary}

## 与主角关系

- 当前主角：`{protagonist_line}`
- 当前判断：{candidate.protagonist_relation}
- 改写主角路径的节点：{AI_PLACEHOLDER}
- 关系定性：{AI_PLACEHOLDER}

## 关键关系

{relation_lines}

## 力量体系

- 能力 / 手段：{abilities}
- 装备 / 资源：{equipment}
- 结构判断：{AI_PLACEHOLDER}

## 关键物品

- 目前可直接确认的资源 / 物件：{equipment}
- 还需补判的关键物件功能：{AI_PLACEHOLDER}

## 关键事件

{event_lines}

## 活动范围

{activity_range}

## 势力归属

- 当前阵营：{candidate.faction or '待补'}
- 势力窗口判断：{AI_PLACEHOLDER}

## 阶段总结

- card 阶段节点数：`{candidate.card_stage_count}`
- 当前判断：{candidate.stage_distribution}
- 哪一阶段最关键：{AI_PLACEHOLDER}
- 该阶段的结构作用：{AI_PLACEHOLDER}

## 人物特征总结

- 外貌 / 标识：{appearance}
- 性格 / 行动风格：{personality}
- 当前总结：{AI_PLACEHOLDER}

## Top10入选理由

- 初评排名：`{index}`
- 初评依据：{candidate.initial_reason}
- 为什么不是单纯高频：{candidate.structural_role}
- 最终入榜理由：{AI_PLACEHOLDER}

## 与相邻配角比较

- 上一位候选：`{upper_name}`
- 下一位候选：`{lower_name}`
- 为什么比上一位更稳 / 不如上一位：{AI_PLACEHOLDER}
- 为什么比下一位更值得进 Top10：{AI_PLACEHOLDER}

## 最终结论

- 当前版本：`card 初评扩展版`
- AI复核结论：{AI_PLACEHOLDER}
- 是否正式保留在 Top10：{AI_PLACEHOLDER}

## 证据摘录

{evidence_lines}
"""


def index_md(novel_name: str, top_candidates: list[Candidate]) -> str:
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
    for index, item in enumerate(top_candidates, start=1):
        lines.append(f"- Top {index}: [[{item.name}-配角分析]]")
    lines.extend(
        [
            "",
            "## 推荐阅读顺序",
            "",
            "1. 先读候选池初评",
            "2. 再读 AI 复核结论",
            "3. 再看 Top10 总表",
            "4. 最后逐个进入 Top10 配角扩展卡",
        ]
    )
    return "\n".join(lines)


def readme_md(
    novel_name: str,
    protagonist: str | None,
    cards_ready: bool,
    merged_ready: bool,
    top_candidates: list[Candidate],
) -> str:
    protagonist_line = f"- 主角：`{protagonist}`\n" if protagonist else ""
    top_line = "、".join(item.name for item in top_candidates[:5]) if top_candidates else "待生成"
    return f"""# {novel_name} 工作区说明

本目录已接入《{novel_name}》的重要配角分析层。

## 当前结构

- `{novel_name}-重要配角Top10总表.md`
  Top10 最终定榜表，必须在 AI 复核后回填
- `{novel_name}-重要配角AI复核结论.md`
  AI 对 Top10 去留、换榜与最终理由的正式结论
- `{novel_name}-重要配角与主角关系图.md`
  Top10 配角与主角关系的结构收束文件
- `{novel_name}-重要配角阶段作用分布.md`
  Top10 配角的阶段覆盖与换挡作用
- `supporting-cast/Top10候选池初评.md`
  card-first 初评候选池
- `supporting-cast/index.md`
  supporting-cast 入口索引
- `supporting-cast/<角色名>-配角分析.md`
  与主角最终人物卡同构的配角扩展卡
- `工作状态-{date.today().isoformat()}.md`
  当前项目级交接文件

## 当前说明

{protagonist_line}- `work/cards`：`{'已检测到' if cards_ready else '缺失'}`
- `work/merged/characters.json`：`{'已检测到' if merged_ready else '缺失，仅能做 card-first 初评'}`
- 当前 Top5 初评候选：`{top_line}`
- 这一层默认流程是：`cards 初评 -> AI 复核定榜 -> Top10 配角扩展卡落地`
"""


def status_md(
    novel_name: str,
    protagonist: str | None,
    cards_ready: bool,
    merged_ready: bool,
    top_candidates: list[Candidate],
) -> str:
    protagonist_line = protagonist or "待确认"
    top_line = "、".join(item.name for item in top_candidates[:3]) if top_candidates else "待生成"
    return f"""# 《{novel_name}》工作状态 {date.today().isoformat()}

## 当前结论

当前已进入重要配角分析层。

- 当前主角：`{protagonist_line}`
- `work/cards`：`{'已具备' if cards_ready else '缺失'}`
- `merged 辅助证据`：`{'已具备' if merged_ready else '缺失'}`
- Top3 初评候选：`{top_line}`

## 当前不应误判为已完成的部分

- 不应把 card 初评顺序直接等同于最终 Top10
- 不应把 `Top10候选池初评` 当成 AI 复核结论
- 不应把模板化配角扩展卡当成已经完成的实质扩展

## 当前应如何继续

1. 先读 `supporting-cast/Top10候选池初评.md`
2. 再写 `{novel_name}-重要配角AI复核结论.md`
3. 回填 `{novel_name}-重要配角Top10总表.md` 的最终去留与理由
4. 逐个补完 Top10 配角扩展卡的最终结论

## 下次开始时建议先看

1. `supporting-cast/Top10候选池初评.md`
2. `{novel_name}-重要配角AI复核结论.md`
3. `{novel_name}-重要配角Top10总表.md`
4. `supporting-cast/index.md`
5. 本文件

## 一句话交接

《{novel_name}》当前已经完成了 card-first 候选池初评，但还需要经过 AI 复核定榜，并把最终 Top10 配角卡按主角卡标准扩展完成。
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize the Top10 supporting-cast layer from AI-generated character cards.")
    parser.add_argument("--workspace", required=True, help="Workspace directory.")
    parser.add_argument("--novel-name", required=True, help="Novel name used in file naming.")
    parser.add_argument("--protagonist", help="Known protagonist name.")
    parser.add_argument("--top-n", type=int, default=10, help="How many supporting characters to scaffold.")
    parser.add_argument("--candidate-pool-size", type=int, default=18, help="How many candidates to keep in the initial review pool.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing layer files.")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.exists():
        raise SystemExit(f"workspace not found: {workspace}")

    protagonist = detect_protagonist_name(workspace, args.protagonist)
    candidates, cards_ready, merged_ready = build_candidates(workspace, protagonist)
    if not candidates:
        raise SystemExit("no usable supporting-cast candidates found under work/cards")

    top_n = max(1, args.top_n)
    candidate_pool_size = max(top_n, args.candidate_pool_size)
    top_candidates = candidates[:top_n]
    near_miss_candidates = candidates[top_n:candidate_pool_size]

    supporting_dir = workspace / "supporting-cast"

    write_file(workspace / "README.md", readme_md(args.novel_name, protagonist, cards_ready, merged_ready, top_candidates), args.force)
    write_file(supporting_dir / "Top10候选池初评.md", candidate_pool_md(args.novel_name, protagonist, candidates, candidate_pool_size), args.force)
    write_file(
        workspace / f"{args.novel_name}-重要配角AI复核结论.md",
        ai_review_md(args.novel_name, protagonist, top_candidates, near_miss_candidates),
        args.force,
    )
    write_file(
        workspace / f"{args.novel_name}-重要配角Top10总表.md",
        top10_table_md(args.novel_name, protagonist, top_candidates),
        args.force,
    )
    write_file(
        workspace / f"{args.novel_name}-重要配角与主角关系图.md",
        relation_map_md(args.novel_name, protagonist, top_candidates),
        args.force,
    )
    write_file(
        workspace / f"{args.novel_name}-重要配角阶段作用分布.md",
        stage_distribution_md(args.novel_name, top_candidates),
        args.force,
    )
    write_file(supporting_dir / "index.md", index_md(args.novel_name, top_candidates), args.force)

    for index, candidate in enumerate(top_candidates, start=1):
        upper_neighbor = top_candidates[index - 2] if index > 1 else None
        lower_neighbor = top_candidates[index] if index < len(top_candidates) else None
        filename = supporting_dir / f"{slugify(candidate.name)}-配角分析.md"
        write_file(
            filename,
            supporting_file_md(index, candidate, protagonist, upper_neighbor, lower_neighbor),
            args.force,
        )

    status_path = workspace / f"工作状态-{date.today().isoformat()}.md"
    write_file(status_path, status_md(args.novel_name, protagonist, cards_ready, merged_ready, top_candidates), args.force)
    refresh_workspace_status(workspace, args.novel_name, protagonist)

    print(f"workspace: {workspace}")
    print(f"cards_source: {workspace / 'work' / 'cards' / 'index.md'}")
    print(f"merged_source: {workspace / 'work' / 'merged' / 'characters.json' if merged_ready else 'missing'}")
    print(f"top_candidates: {len(top_candidates)}")
    print(f"- {supporting_dir / 'Top10候选池初评.md'}")
    print(f"- {workspace / f'{args.novel_name}-重要配角AI复核结论.md'}")
    print(f"- {workspace / f'{args.novel_name}-重要配角Top10总表.md'}")
    print(f"- {workspace / f'{args.novel_name}-重要配角与主角关系图.md'}")
    print(f"- {workspace / f'{args.novel_name}-重要配角阶段作用分布.md'}")
    print(f"- {supporting_dir / 'index.md'}")
    for candidate in top_candidates[:10]:
        print(f"- {supporting_dir / f'{slugify(candidate.name)}-配角分析.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
