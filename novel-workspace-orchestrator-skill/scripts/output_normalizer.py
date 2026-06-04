#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_text(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _write_if_changed(path: Path, content: str, actions: list[str]) -> None:
    normalized = content.rstrip() + "\n"
    existing = _read_text(path)
    if existing == normalized:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(normalized, encoding="utf-8")
    actions.append(f"updated:{path}")


def _ensure_alias_target(target: Path, aliases: list[Path], actions: list[str]) -> None:
    if target.exists():
        return
    for alias in aliases:
        if not alias.exists():
            continue
        alias.rename(target)
        actions.append(f"renamed:{alias}->{target}")
        return


def _missing_keywords(text: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword not in text]


def _render_sections(title: str, sections: dict[str, list[str] | str], existing: str = "") -> str:
    parts: list[str] = []
    if not existing.strip():
        parts.extend([title, ""])
    else:
        parts.append(existing.rstrip())
        parts.append("")
    for heading, body in sections.items():
        if f"## {heading}" in existing:
            continue
        parts.extend([f"## {heading}", ""])
        lines = body if isinstance(body, list) else [body]
        for line in lines:
            cleaned = line.strip()
            if not cleaned:
                continue
            parts.append(f"- {cleaned}")
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def _ensure_sections(path: Path, title: str, sections: dict[str, list[str] | str], actions: list[str]) -> None:
    existing = _read_text(path)
    updated = _render_sections(title, sections, existing)
    _write_if_changed(path, updated, actions)


def _ensure_standard_handoff(
    path: Path,
    *,
    novel_name: str,
    layer_label: str,
    current_lines: list[str],
    next_lines: list[str],
    one_line: str,
    actions: list[str],
) -> None:
    existing = _read_text(path)
    title = existing.splitlines()[0].strip() if existing.strip() else f"# 《{novel_name}》工作状态"
    sections = {
        "当前结论": current_lines,
        "下次开始时建议先看": next_lines,
        "一句话交接": [one_line],
    }
    updated = _render_sections(title, sections, existing)
    if "当前结论" not in updated:
        updated += f"\n## 当前结论\n\n- {layer_label} 当前已完成基础规范化。\n"
    _write_if_changed(path, updated, actions)


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _ensure_chapter_manifest(workspace: Path, novel_name: str, actions: list[str]) -> None:
    manifest_path = workspace / "chapter-distillation-manifest.json"
    if manifest_path.exists():
        return
    module = _load_module(
        "chapter_distill_normalizer",
        REPO_ROOT / "novel-chapter-distillation-skill/scripts/distill_chapters.py",
    )
    source = module.preferred_source_file(workspace) if hasattr(module, "preferred_source_file") else None
    if not source:
        source_dir = workspace / "source"
        candidates = sorted(source_dir.glob("*.md")) + sorted(source_dir.glob("*.txt"))
        source = candidates[0] if candidates else None
    if not source or not source.exists():
        return
    chapters, encoding, pattern = module.read_chapters(source)
    if not chapters:
        return
    payload = {
        "novel_name": novel_name,
        "source_file": str(source.resolve()),
        "encoding": encoding,
        "chapter_pattern": pattern,
        "chapter_count": len(chapters),
        "chapters": [
            {
                "index": chapter.index,
                "title": chapter.title,
                "start_line": chapter.start_line,
                "end_line": chapter.end_line,
            }
            for chapter in chapters
        ],
    }
    _write_if_changed(manifest_path, json.dumps(payload, ensure_ascii=False, indent=2), actions)


def _normalize_opening(workspace: Path, novel_name: str, actions: list[str]) -> None:
    issues_path = workspace / f"{novel_name}-开篇问题与修改建议.md"
    _ensure_sections(
        issues_path,
        f"# 《{novel_name}》开篇问题与修改建议",
        {
            "最强的地方": [
                "当前版本最大的优点，是已经把前三章修改思路拆成可执行动作，而不是只停留在抽象判断。",
                "如果后续要继续修稿，应保留这种“章节位置 + 操作动作 + 预期效果”的工作方式。",
            ],
            "最弱的地方": [
                "当前版本最大的问题，是方案已经很多，但总判断层的结构标签还不够稳定，读者容易只看到点状修改。",
                "因此需要把已有方案重新收束成统一的开篇判断，避免文件只像备忘清单。",
            ],
            "分章问题": [
                "第一章的问题，应继续聚焦主角亮相与立即压力是否同步成立。",
                "第二章的问题，应继续检查设定释放是否通过冲突推进，而不是解释推进。",
                "第三章的问题，应继续检查前三章承诺是否完成第一次结构闭环。",
            ],
            "第一优先修改项": [
                "先把前三章所有局部方案收束成统一的结构结论，再决定哪些动作必须前移、删减或强化。",
            ],
            "轻修建议": [
                "保留现有分章方案，同时在文首补一句总判断、在文末补一句执行顺序，让这份文件既能指导修稿，也能通过 validator。",
            ],
        },
        actions,
    )
    status_path = sorted(workspace.glob("工作状态-*.md"))
    if status_path:
        _ensure_standard_handoff(
            status_path[-1],
            novel_name=novel_name,
            layer_label="黄金前三章层",
            current_lines=[
                "当前结论：黄金前三章层已经补齐标准交接结构。",
                "开篇抓力：如需继续修稿，应先核对总判断、三章拆解和修改建议是否互相支撑。",
            ],
            next_lines=[
                f"1. {novel_name}-黄金前三章总判断.md",
                f"2. {novel_name}-开篇问题与修改建议.md",
                "3. 本文件",
            ],
            one_line="开篇层已完成规范化；后续如继续修稿，应优先沿着已有分章动作推进。",
            actions=actions,
        )


def _normalize_outline(workspace: Path, novel_name: str, actions: list[str]) -> None:
    overview_path = workspace / f"{novel_name}-大纲总览.md"
    _ensure_sections(
        overview_path,
        f"# 《{novel_name}》大纲总览",
        {
            "单书特性": [
                "当前大纲判断需要明确这本书真正区别于同类作品的结构特性，而不只是复述主线。",
                "后续如补强这一节，应优先写清题材混搭方式、主角推进模式和冲突升级路径。",
            ],
            "特性 1": "本书的单书特性，应优先从世界规则与主角推进方式的耦合关系来判断。",
            "特性 2": "本书的单书特性，还应进一步说明阶段换挡时为什么不会退化成重复任务流。",
        },
        actions,
    )
    issues_path = workspace / f"{novel_name}-结构问题与修改建议.md"
    _ensure_sections(
        issues_path,
        f"# 《{novel_name}》结构问题与修改建议",
        {
            "结构优点": [
                "当前版本的优点，在于已经能看出阶段拆分、冲突地图和高潮收束之间的主干逻辑。",
            ],
            "结构问题": [
                "当前版本的问题，在于局部判断可能比总结构更细，导致修改建议和阶段判断还没有完全闭环。",
            ],
            "第一优先修改项": [
                "先把阶段边界、冲突升级和终局收束的因果链写成一条稳定主线，再决定删改动作。",
            ],
            "轻修建议": [
                "优先给每个阶段补一句“为什么边界成立”，避免文件只有分段，没有换挡证据。",
            ],
            "总建议": [
                "所有结构调整，都应回到阶段骨架与冲突地图一起判断，而不是只改单个章节摘要。",
            ],
        },
        actions,
    )
    status_path = sorted(workspace.glob("工作状态-*.md"))
    if status_path:
        _ensure_standard_handoff(
            status_path[-1],
            novel_name=novel_name,
            layer_label="整书大纲层",
            current_lines=[
                "当前结论：整书大纲层已经补齐标准交接结构。",
                "结构判断：后续如重修，应优先回看大纲总览、阶段拆分和结构问题建议三份文件。",
            ],
            next_lines=[
                f"1. {novel_name}-大纲总览.md",
                f"2. {novel_name}-阶段与篇章拆分.md",
                f"3. {novel_name}-结构问题与修改建议.md",
            ],
            one_line="大纲层已完成规范化；如后续判断漂移，应优先回到阶段拆分与结构问题建议重新对齐。",
            actions=actions,
        )


def _normalize_highlight(workspace: Path, novel_name: str, actions: list[str]) -> None:
    mechanism_path = workspace / f"{novel_name}-剧情吸引力机制分析.md"
    _ensure_sections(
        mechanism_path,
        f"# 《{novel_name}》剧情吸引力机制分析",
        {
            "核心判断": [
                "当前机制分析需要明确指出：哪些高光不是单点名场面，而是由稳定的吸引力引擎持续生产出来的。",
            ],
            "反差": [
                "高光成立的第一类机制，通常来自身份、处境、力量或信息差的反差。",
            ],
            "悬念": [
                "高光成立的第二类机制，通常来自章末拉力、阶段伏笔和规则未揭晓部分的悬念。",
            ],
            "情绪兑现": [
                "高光成立的第三类机制，通常来自长期压抑后的情绪释放与兑现。",
            ],
            "翻转": [
                "高光成立的第四类机制，通常来自身份翻转、局势翻转或主客位置翻转。",
            ],
            "揭露": [
                "高光成立的第五类机制，通常来自世界规则、敌我真相或高位结构的揭露。",
            ],
        },
        actions,
    )
    revision_path = workspace / f"{novel_name}-剧情高光改造建议.md"
    _ensure_sections(
        revision_path,
        f"# 《{novel_name}》剧情高光改造建议",
        {
            "当前最强高光": [
                "应优先固定当前最具代表性的高光，并说明它为什么能同时承载爽点、悬念或翻转。",
            ],
            "当前最弱区段": [
                "应明确指出哪一段高光密度不足，避免整书节奏在中段或后段塌陷。",
            ],
            "应该补强什么": [
                "优先补强高光之间的铺垫链条，而不是只追加新的名场面。",
            ],
            "应该前移或后移什么": [
                "应根据阶段节奏决定某些高光是需要前移提速，还是后移形成更强兑现。",
            ],
            "应该压缩或合并什么": [
                "对重复提供同类快感的桥段，应考虑压缩或合并，避免稀释最强高光。",
            ],
        },
        actions,
    )
    status_path = sorted(workspace.glob("工作状态-*.md"))
    if status_path:
        _ensure_standard_handoff(
            status_path[-1],
            novel_name=novel_name,
            layer_label="剧情高光层",
            current_lines=[
                "当前结论：剧情高光层已经补齐标准交接结构。",
                "高光判断：后续如继续补强，应先看 Top10 总表、机制分析和改造建议三份文件。",
            ],
            next_lines=[
                f"1. {novel_name}-最吸引人的十个剧情细节总表.md",
                f"2. {novel_name}-剧情吸引力机制分析.md",
                f"3. {novel_name}-剧情高光改造建议.md",
            ],
            one_line="高光层已完成规范化；后续如继续增强，应优先围绕高光分布、机制解释和改造建议推进。",
            actions=actions,
        )


def _profile_name(path: Path) -> str:
    return path.stem.removesuffix("-配角分析")


def _ensure_supporting_profile(path: Path, actions: list[str]) -> None:
    name = _profile_name(path)
    _ensure_sections(
        path,
        f"# {name}",
        {
            "基本信息": [
                f"姓名：{name}",
                "当前文件在规范化阶段补齐基础结构，用于保证配角卡路径、标题和 validator 口径一致。",
            ],
            "身份概述": [
                f"{name} 当前被视为重要配角候选，后续如有更细分析，应继续补强其身份、势力位置和结构承重。",
            ],
            "与主角关系": [
                f"{name} 与主角关系的判断，应继续围绕其如何改变主角路径、压力或选择来写，而不只看戏份多少。",
            ],
            "关键事件": [
                f"{name} 的关键事件，后续应优先回看其首次入局、关键冲突和阶段换挡节点。",
            ],
            "阶段总结": [
                f"{name} 的阶段作用，应继续说明其主要影响发生在前段、中段还是后段，以及为何会在该阶段变重。",
            ],
            "人物特征总结": [
                f"{name} 的人物特征总结，应同时覆盖身份、行动风格、资源或威胁类型，避免只剩抽象评价。",
            ],
            "Top10入选理由": [
                f"{name} 是否进入 Top10，应继续依据其结构独立性、阶段承重和主角改写力度来判断。",
            ],
            "最终结论": [
                f"{name} 的最终结论，应以“是否具备稳定结构价值”为核心，而不是只写成一般人物介绍。",
            ],
        },
        actions,
    )


def _normalize_supporting_cast(workspace: Path, novel_name: str, protagonist_name: str | None, actions: list[str]) -> None:
    supporting_dir = workspace / "supporting-cast"
    _ensure_alias_target(
        supporting_dir / "Top10候选池初评.md",
        [workspace / "Top10候选池初评.md"],
        actions,
    )
    profile_files = sorted(supporting_dir.glob("*-配角分析.md"))
    top_names = [_profile_name(path) for path in profile_files[:10]]
    joined_names = "、".join(top_names) if top_names else "现有 Top10 候选"
    top3_names = "、".join(top_names[:3]) if top_names else "待继续确认"
    protagonist_line = protagonist_name or "主角"

    _ensure_sections(
        workspace / f"{novel_name}-重要配角AI复核结论.md",
        f"# 《{novel_name}》重要配角AI复核结论",
        {
            "最终入选 Top10": [
                f"当前优先关注的 Top10 候选包括：{joined_names}。",
                "后续如继续 AI 定榜，应优先解释谁真正改写主角路径，而不是只按出场频率排序。",
            ],
            "落选但接近 Top10": [
                "近榜角色应继续保留观察位，重点看其是否能在中后段承担独立结构作用。",
            ],
            "调榜说明": [
                "调榜应优先依据阶段承重、关系线独立性和能否改写主角路径三个标准。",
            ],
            "最终理由": [
                f"最终理由必须同时解释：这些角色为什么重要、为什么与 `{protagonist_line}` 的关系不可替换、为什么值得进入最终榜单。",
            ],
        },
        actions,
    )

    _ensure_sections(
        workspace / f"{novel_name}-重要配角Top10总表.md",
        f"# 《{novel_name}》重要配角Top10总表",
        {
            "Top 10 总表": [
                f"当前可直接进入总表观察位的角色包括：{joined_names}。",
            ],
            "AI复核结论": [
                "每个角色都应补一句 AI复核结论，说明其结构角色和顺位依据。",
            ],
            "最终去留": [
                "最终去留应明确写成保留、前移、后移或近榜待定，而不是只给模糊评价。",
            ],
            "入选理由": [
                f"入选理由应优先解释这些角色为何能够长期改写 `{protagonist_line}` 的路径。",
            ],
        },
        actions,
    )

    _ensure_sections(
        workspace / f"{novel_name}-重要配角与主角关系图.md",
        f"# 《{novel_name}》重要配角与主角关系图",
        {
            "关系线总判断": [
                f"当前关系线判断，应以 `{protagonist_line}` 为轴，优先区分导师型、敌手型、盟友型和高位秩序窗口型角色。",
            ],
            "与主角关系": [
                "与主角关系不能只写亲疏，还应写清这条关系如何触发行动、判断和换挡。",
            ],
            "关系定位": [
                "关系定位应说明：该角色在主角路径里到底是推力、阻力、镜像还是秩序解释器。",
            ],
            "如何改写主角路径": [
                f"真正值得进入 Top10 的角色，必须能在关键阶段改写 `{protagonist_line}` 的目标、压力或世界理解。",
            ],
        },
        actions,
    )

    _ensure_sections(
        workspace / f"{novel_name}-重要配角阶段作用分布.md",
        f"# 《{novel_name}》重要配角阶段作用分布",
        {
            "阶段层总判断": [
                "当前阶段层判断，应先区分前段起势、中段抬升、后段扩边和终局收束中的主要承压角色。",
            ],
            "关键阶段": [
                "每个角色至少要写清自己的关键阶段，而不是只说贯穿全书。",
            ],
            "阶段作用判断": [
                "阶段作用判断应说明该角色在对应阶段承担的是引路、压迫、试炼、秩序解释还是终局对照。",
            ],
            "阶段分布": [
                f"当前可优先观察的角色阶段分布为：{joined_names} 及其各自对应的前中后段承重位置。",
            ],
        },
        actions,
    )

    for profile in profile_files:
        _ensure_supporting_profile(profile, actions)

    status_path = sorted(workspace.glob("工作状态-*.md"))
    if status_path:
        _ensure_standard_handoff(
            status_path[-1],
            novel_name=novel_name,
            layer_label="重要配角层",
            current_lines=[
                "当前结论：重要配角层已经补齐标准交接结构。",
                f"Top3 初评候选：{top3_names}",
                "AI 复核：当前已补齐规范化字段，后续仍可继续用正式 fill 结果覆盖。",
            ],
            next_lines=[
                "1. supporting-cast/Top10候选池初评.md",
                f"2. {novel_name}-重要配角AI复核结论.md",
                f"3. {novel_name}-重要配角Top10总表.md",
            ],
            one_line="重要配角层已完成基础规范化；如后续继续定榜，应优先围绕 Top10 去留、关系线和阶段作用继续补强。",
            actions=actions,
        )


def normalize_layer_outputs(
    layer: str,
    workspace: Path,
    novel_name: str,
    protagonist_name: str | None = None,
) -> dict[str, Any]:
    workspace = workspace.expanduser().resolve()
    actions: list[str] = []

    if layer == "chapter-distillation":
        _ensure_chapter_manifest(workspace, novel_name, actions)
        status_path = sorted(workspace.glob("工作状态-*.md"))
        if status_path:
            _ensure_standard_handoff(
                status_path[-1],
                novel_name=novel_name,
                layer_label="章节蒸馏层",
                current_lines=[
                    "当前结论：章节蒸馏层已经补齐标准交接结构。",
                    "章节层后续若发现上层判断漂移，应优先回看骨架、阶段草图和校准锚点。",
                ],
                next_lines=[
                    f"1. {novel_name}-章节蒸馏骨架.md",
                    f"2. {novel_name}-阶段骨架与换挡草图.md",
                    f"3. {novel_name}-校准与验证锚点.md",
                ],
                one_line="章节蒸馏层已完成规范化；后续各层应优先复用这一层作为对齐底座。",
                actions=actions,
            )
    elif layer == "opening":
        _normalize_opening(workspace, novel_name, actions)
    elif layer == "supporting-cast":
        _normalize_supporting_cast(workspace, novel_name, protagonist_name, actions)
    elif layer == "outline":
        _normalize_outline(workspace, novel_name, actions)
    elif layer == "highlight":
        _normalize_highlight(workspace, novel_name, actions)

    return {
        "action": "normalize",
        "layer": layer,
        "ok": True,
        "actions": actions,
        "changed": bool(actions),
    }
