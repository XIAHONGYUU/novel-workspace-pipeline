#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path


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


def normalize_relation_target(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def chunk_order(chunk_id: str) -> int:
    match = re.search(r"(\d+)$", chunk_id)
    return int(match.group(1)) if match else 999999


@dataclass
class Candidate:
    name: str
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
    relationships: list[dict[str, str]]
    timeline: list[dict[str, str]]
    evidence: list[str]
    mention_count: int
    chunks: list[str]
    first_seen_chunk: str
    first_seen_title: str
    score: float
    rank_reason: str
    protagonist_relation: str
    stage_distribution: str
    structural_role: str


def load_merged_characters(path: Path) -> list[dict]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else []


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


def classify_stage_distribution(chunks: list[str], max_order: int) -> str:
    if not chunks:
        return "暂无稳定阶段信息"
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


def infer_protagonist_relation(item: dict, protagonist_names: set[str]) -> str:
    if not protagonist_names:
        return "主角关系待结合人物卡再确认"
    relationships = item.get("relationships", [])
    direct = []
    for rel in relationships:
        target = normalize_relation_target(rel.get("target", ""))
        if target in {normalize_relation_target(name) for name in protagonist_names}:
            direct.append(rel.get("type", "").strip() or "存在直接关系")
    if direct:
        return "；".join(dict.fromkeys(direct))
    joined = "\n".join(
        [item.get("summary", "")] + item.get("evidence", []) + item.get("summaries", [])
    )
    if any(name and name in joined for name in protagonist_names):
        return "文本摘要中与主角有直接交集，但关系类型仍需精炼"
    return "当前结构化抽取里未显式标出主角关系，需结合原文补判"


def infer_structural_role(item: dict, relation_text: str, stage_text: str) -> str:
    mention_count = int(item.get("mention_count") or 0)
    timeline_count = len(item.get("timeline") or [])
    relation_count = len(item.get("relationships") or [])
    ability_count = len(item.get("abilities") or []) + len(item.get("equipment") or [])
    faction = (item.get("faction") or "").strip()

    tags: list[str] = []
    if "直接关系" in relation_text or "主角" in relation_text:
        tags.append("主角关系支点")
    if faction:
        tags.append("势力窗口")
    if timeline_count >= 3:
        tags.append("阶段换挡触发器")
    if ability_count >= 3:
        tags.append("能力体系承压点")
    if mention_count >= 25 or relation_count >= 4:
        tags.append("主线承压配角")
    if "横跨前中后段" in stage_text:
        tags.append("跨阶段支点")
    if not tags:
        tags.append("阶段性关键配角")
    return " / ".join(tags)


def importance_score(item: dict, protagonist_names: set[str], max_chunk_order: int) -> tuple[float, str, str, str]:
    mention_count = int(item.get("mention_count") or 0)
    chunks = list(dict.fromkeys(item.get("chunks") or []))
    chunk_span = len(chunks)
    relationships = item.get("relationships") or []
    relation_count = len(relationships)
    timeline_count = len(item.get("timeline") or [])
    abilities = len(item.get("abilities") or [])
    equipment = len(item.get("equipment") or [])
    evidence = len(item.get("evidence") or [])
    first_seen = chunk_order(str(item.get("first_seen_chunk") or ""))
    early_bonus = max(0, 10 - min(10, first_seen // 8)) if first_seen < 999999 else 0

    protagonist_relation = infer_protagonist_relation(item, protagonist_names)
    protagonist_bonus = 18 if "主角" in protagonist_relation or "直接关系" in protagonist_relation else 0
    stage_distribution = classify_stage_distribution(chunks, max_chunk_order)
    structural_role = infer_structural_role(item, protagonist_relation, stage_distribution)

    score = (
        mention_count * 1.5
        + chunk_span * 4
        + relation_count * 5
        + timeline_count * 4
        + abilities * 2
        + equipment * 1.5
        + evidence
        + early_bonus
        + protagonist_bonus
    )

    reasons = [
        f"提及 `{mention_count}` 次",
        f"覆盖 `{chunk_span}` 个 chunk",
    ]
    if relation_count:
        reasons.append(f"显式关系 `{relation_count}` 条")
    if timeline_count:
        reasons.append(f"阶段事件 `{timeline_count}` 条")
    if protagonist_bonus:
        reasons.append("与主角存在直接承压关系")
    reason_text = "；".join(reasons)
    return score, reason_text, protagonist_relation, structural_role


def build_candidates(merged: list[dict], protagonist: str | None) -> list[Candidate]:
    protagonist_names = protagonist_aliases(merged, protagonist)
    max_chunk_order = 0
    for item in merged:
        for chunk in item.get("chunks") or []:
            max_chunk_order = max(max_chunk_order, chunk_order(chunk))

    candidates: list[Candidate] = []
    normalized_protagonists = {normalize_relation_target(name) for name in protagonist_names if name}
    for item in merged:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        if normalize_relation_target(name) in normalized_protagonists:
            continue
        if len(name) < 2:
            continue
        score, rank_reason, protagonist_relation, structural_role = importance_score(
            item,
            protagonist_names,
            max_chunk_order or 1,
        )
        candidates.append(
            Candidate(
                name=name,
                aliases=[alias for alias in item.get("aliases", []) if isinstance(alias, str) and alias.strip()],
                identity=(item.get("identity") or "").strip(),
                faction=(item.get("faction") or "").strip(),
                status=(item.get("status") or "").strip(),
                first_appearance=(item.get("first_appearance") or item.get("first_appearance_text") or "").strip(),
                summary=(item.get("summary") or "").strip(),
                appearance=[value for value in item.get("appearance", []) if isinstance(value, str) and value.strip()],
                personality=[value for value in item.get("personality", []) if isinstance(value, str) and value.strip()],
                abilities=[value for value in item.get("abilities", []) if isinstance(value, str) and value.strip()],
                equipment=[value for value in item.get("equipment", []) if isinstance(value, str) and value.strip()],
                relationships=[value for value in item.get("relationships", []) if isinstance(value, dict)],
                timeline=[value for value in item.get("timeline", []) if isinstance(value, dict)],
                evidence=[value for value in item.get("evidence", []) if isinstance(value, str) and value.strip()],
                mention_count=int(item.get("mention_count") or 0),
                chunks=[str(value) for value in item.get("chunks", []) if value],
                first_seen_chunk=str(item.get("first_seen_chunk") or ""),
                first_seen_title=str(item.get("first_seen_title") or ""),
                score=score,
                rank_reason=rank_reason,
                protagonist_relation=protagonist_relation,
                stage_distribution=classify_stage_distribution(
                    [str(value) for value in item.get("chunks", []) if value],
                    max_chunk_order or 1,
                ),
                structural_role=structural_role,
            )
        )

    candidates.sort(
        key=lambda item: (
            -item.score,
            -item.mention_count,
            -len(set(item.chunks)),
            item.name,
        )
    )
    return candidates


def top10_table_md(novel_name: str, protagonist: str | None, top_candidates: list[Candidate]) -> str:
    protagonist_line = protagonist or "待确认"
    lines = [
        f"# 《{novel_name}》重要配角Top10总表",
        "",
        "## 总判断",
        "",
        f"- 当前主角：`{protagonist_line}`",
        "- 本表基于全角色 AI 抽取结果生成，不接受 heuristic 候选直接入榜。",
        "- 排名综合考虑提及频率、跨阶段覆盖、关系密度、主角承压关系与结构事件密度。",
        "",
        "## Top 10 总表",
        "",
        "| 排名 | 配角 | 综合分 | 提及次数 | 覆盖 chunk | 结构角色 | 入选理由 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for index, item in enumerate(top_candidates, start=1):
        lines.append(
            f"| {index} | {item.name} | {item.score:.1f} | {item.mention_count} | {len(set(item.chunks))} | {item.structural_role} | {item.rank_reason} |"
        )
    lines.extend(
        [
            "",
            "## 使用说明",
            "",
            "- 这个 Top 10 只解决“谁最值得深拆”。",
            "- 不代表每个配角戏份都平均；它强调的是结构承压价值，而不是纯出场数量。",
            "- 如果个别角色明显误入，需要先回看 `work/merged/characters.json` 和对应 chunk 原文，再决定是否调榜。",
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
        "- 重点看谁真正改变主角路径，而不是谁只在局部段落里高频出现。",
        "",
        "## Top10 关系摘要",
        "",
    ]
    for index, item in enumerate(top_candidates, start=1):
        lines.extend(
            [
                f"### Top {index}：{item.name}",
                "",
                f"- 结构角色：{item.structural_role}",
                f"- 与主角关系：{item.protagonist_relation}",
                f"- 阶段分布：{item.stage_distribution}",
                f"- 关系判断：{item.name} 更像 `{item.structural_role}`，后续应重点核对其在哪个阶段把主角推向下一轮局势。",
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
        "- 本文件关注 Top10 配角分别在哪些阶段承担压力、护持、背叛、镜像或势力窗口作用。",
        "",
    ]
    for index, item in enumerate(top_candidates, start=1):
        lines.extend(
            [
                f"### Top {index}：{item.name}",
                "",
                f"- 阶段分布：{item.stage_distribution}",
                f"- 关键事件密度：`{len(item.timeline)}` 条",
                f"- 主要 chunk：`{', '.join(item.chunks[:8]) if item.chunks else '待补充'}`",
                f"- 阶段作用判断：{item.name} 当前可先按 `{item.structural_role}` 进入后续整书结构判断。",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def supporting_file_md(index: int, candidate: Candidate, protagonist: str | None) -> str:
    protagonist_line = protagonist or "待确认"
    abilities = "、".join(candidate.abilities) if candidate.abilities else "暂无稳定抽取"
    equipment = "、".join(candidate.equipment) if candidate.equipment else "暂无稳定抽取"
    appearance = "、".join(candidate.appearance[:4]) if candidate.appearance else "暂无稳定抽取"
    personality = "、".join(candidate.personality[:4]) if candidate.personality else "暂无稳定抽取"
    aliases = "、".join(candidate.aliases) if candidate.aliases else "无"
    relations = []
    for rel in candidate.relationships[:8]:
        target = rel.get("target", "").strip()
        rel_type = rel.get("type", "").strip()
        if target or rel_type:
            relations.append(f"- {target or '对象待补'}：{rel_type or '关系待补'}")
    if not relations:
        relations = ["- 待结合原文补主角关系与外围关系"]

    timeline_lines = []
    for item in candidate.timeline[:8]:
        stage = item.get("stage", "").strip() or "阶段待判"
        event = item.get("event", "").strip() or "事件待补"
        timeline_lines.append(f"- {stage}：{event}")
    if not timeline_lines:
        timeline_lines = ["- 待结合 chunk 原文补关键阶段事件"]

    evidence_lines = [f"- {line}" for line in candidate.evidence[:5]] or ["- 待回原文补关键证据"]

    return "\n".join(
        [
            f"# {candidate.name} 配角分析",
            "",
            "## 入选结论",
            "",
            f"- Top10 排名：`{index}`",
            f"- 综合分：`{candidate.score:.1f}`",
            f"- 当前主角：`{protagonist_line}`",
            f"- 核心判断：{candidate.name} 进入 Top10，不是因为单纯高频，而是因为 `{candidate.rank_reason}`。",
            f"- 结构角色：{candidate.structural_role}",
            "",
            "## 基本信息",
            "",
            f"- 姓名：{candidate.name}",
            f"- 别名：{aliases}",
            f"- 身份：{candidate.identity or '待补'}",
            f"- 阵营：{candidate.faction or '待补'}",
            f"- 当前状态：{candidate.status or '待补'}",
            f"- 初次登场：{candidate.first_appearance or candidate.first_seen_title or '待补'}",
            f"- 提及次数：`{candidate.mention_count}`",
            f"- 覆盖 chunk：`{len(set(candidate.chunks))}`",
            "",
            "## 与主角关系",
            "",
            f"- 当前判断：{candidate.protagonist_relation}",
            f"- 为什么重要：{candidate.name} 对主角更像 `{candidate.structural_role}`，需要结合原文确认其真正改写主角路径的节点。",
            "",
            "## 剧情功能",
            "",
            f"- 阶段分布：{candidate.stage_distribution}",
            f"- 第一判断：{candidate.name} 更像承担 `{candidate.structural_role}` 的关键配角，而不是一次性功能人物。",
            f"- 进一步要补的判断：需要明确其最强作用究竟是推动、阻碍、镜像、背叛、继承还是世界观窗口。",
            "",
            "## 外貌与性格",
            "",
            f"- 外貌 / 标识：{appearance}",
            f"- 性格 / 行动风格：{personality}",
            "",
            "## 能力与资源",
            "",
            f"- 能力：{abilities}",
            f"- 装备 / 资源：{equipment}",
            "",
            "## 关键关系清单",
            "",
            *relations,
            "",
            "## 关键阶段与事件",
            "",
            *timeline_lines,
            "",
            "## 证据摘录",
            "",
            *evidence_lines,
            "",
            "## 后续深拆重点",
            "",
            f"- 明确 {candidate.name} 在哪一阶段对主角路径造成最大改写",
            f"- 判断 {candidate.name} 与相邻高频角色相比，为什么更应进入 Top10",
            f"- 把 {candidate.name} 放回整书阶段图里，看其是否承担稳定的结构压力",
        ]
    )


def index_md(top_candidates: list[Candidate]) -> str:
    lines = [
        "# 重要配角分析索引",
        "",
        "## Top10 文件",
        "",
    ]
    for index, item in enumerate(top_candidates, start=1):
        lines.append(f"- Top {index}: [[{item.name}-配角分析]]")
    return "\n".join(lines)


def readme_md(
    novel_name: str,
    protagonist: str | None,
    merged_exists: bool,
    top_candidates: list[Candidate],
) -> str:
    protagonist_line = f"- 主角：`{protagonist}`\n" if protagonist else ""
    merged_line = "已检测到 `work/merged/characters.json`，可直接推进 Top10 配角层。" if merged_exists else "尚未检测到 `work/merged/characters.json`，当前只生成了层骨架。"
    top_line = "、".join(item.name for item in top_candidates[:5]) if top_candidates else "待生成"
    return f"""# {novel_name} 工作区说明

本目录已接入《{novel_name}》的重要配角分析层。

## 当前结构

- `{novel_name}-重要配角Top10总表.md`
  Top10 排名与入选理由
- `{novel_name}-重要配角与主角关系图.md`
  Top10 配角与主角的结构关系
- `{novel_name}-重要配角阶段作用分布.md`
  Top10 配角的阶段覆盖与换挡作用
- `supporting-cast/index.md`
  配角分析索引
- `supporting-cast/<角色名>-配角分析.md`
  Top10 配角逐个分析文件
- `工作状态-{date.today().isoformat()}.md`
  当前项目级交接文件

## 当前说明

{protagonist_line}- {merged_line}
- 当前 Top5 候选预览：`{top_line}`
- 这一层默认承接 AI 全角色抽取结果，不应回退到 heuristic 名单。
"""


def status_md(
    novel_name: str,
    protagonist: str | None,
    merged_exists: bool,
    top_candidates: list[Candidate],
) -> str:
    protagonist_line = protagonist or "待确认"
    top_line = "、".join(item.name for item in top_candidates[:3]) if top_candidates else "待生成"
    merged_line = "已具备" if merged_exists else "缺失"
    return f"""# 《{novel_name}》工作状态 {date.today().isoformat()}

## 当前结论

当前已进入重要配角分析层。

- 当前主角：`{protagonist_line}`
- 全角色 AI 抽取：`{merged_line}`
- Top3 配角候选：`{top_line}`

## 当前不应误判为已完成的部分

- 不应把“高频出现”直接等同于“结构上最重要”
- 不应把 Top10 总表当成配角层已经完全闭环
- 不应在缺少 AI 全角色抽取时直接相信启发式名单

## 当前应如何继续

1. 核对 Top10 排名是否有明显误入角色
2. 深化每个配角的结构角色判断
3. 明确谁真正改变主角路径
4. 把 Top10 配角放回整书阶段图里核对承压位置

## 下次开始时建议先看

1. `{novel_name}-重要配角Top10总表.md`
2. `{novel_name}-重要配角与主角关系图.md`
3. `supporting-cast/index.md`
4. 本文件

## 一句话交接

《{novel_name}》当前已经生成重要配角 Top10 层，但还需要继续确认排名、关系与阶段作用是否真正成立。
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize and rank the Top 10 supporting-cast layer for a novel workspace.")
    parser.add_argument("--workspace", required=True, help="Workspace directory.")
    parser.add_argument("--novel-name", required=True, help="Novel name used in file naming.")
    parser.add_argument("--protagonist", help="Known protagonist name.")
    parser.add_argument("--top-n", type=int, default=10, help="How many supporting characters to keep.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing layer files.")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.exists():
        raise SystemExit(f"workspace not found: {workspace}")

    protagonist = detect_protagonist_name(workspace, args.protagonist)
    merged_path = workspace / "work" / "merged" / "characters.json"
    merged = load_merged_characters(merged_path)
    candidates = build_candidates(merged, protagonist)
    top_candidates = candidates[: max(1, args.top_n)]

    supporting_dir = workspace / "supporting-cast"
    write_file(workspace / "README.md", readme_md(args.novel_name, protagonist, merged_path.exists(), top_candidates), args.force)
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
    write_file(supporting_dir / "index.md", index_md(top_candidates), args.force)

    for index, candidate in enumerate(top_candidates, start=1):
        filename = supporting_dir / f"{slugify(candidate.name)}-配角分析.md"
        write_file(filename, supporting_file_md(index, candidate, protagonist), args.force)

    status_path = workspace / f"工作状态-{date.today().isoformat()}.md"
    write_file(status_path, status_md(args.novel_name, protagonist, merged_path.exists(), top_candidates), args.force)
    refresh_workspace_status(workspace, args.novel_name, protagonist)

    print(f"workspace: {workspace}")
    print(f"merged_source: {merged_path if merged_path.exists() else 'missing'}")
    print(f"top_candidates: {len(top_candidates)}")
    print(f"- {workspace / f'{args.novel_name}-重要配角Top10总表.md'}")
    print(f"- {workspace / f'{args.novel_name}-重要配角与主角关系图.md'}")
    print(f"- {workspace / f'{args.novel_name}-重要配角阶段作用分布.md'}")
    print(f"- {supporting_dir / 'index.md'}")
    for candidate in top_candidates[:10]:
        print(f"- {supporting_dir / f'{slugify(candidate.name)}-配角分析.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
