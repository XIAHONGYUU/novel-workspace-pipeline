#!/usr/bin/env python3
"""Quality Gate — 小说工作区产物质量评估系统。

在现有 validator（只检查文件存在/字数/占位符/关键词）之上，
新增四个维度的质量评估：

1. 结构完整度 — 文件是否有实质内容（不只是模板填充）
2. 跨层一致性 — 不同层之间的关键判断是否互相矛盾
3. 分析深度   — 是否有因果推理而非纯描述
4. 可操作性   — 产物是否能指导下一步行动

用法:
    python3 quality_gate.py --workspace 永恒剑主
    python3 quality_gate.py --workspace 永恒剑主 --json
    python3 quality_gate.py --workspace 永恒剑主 --layer chapter-distillation
"""

from __future__ import annotations

import argparse
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

# ============================================================
# 常量
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SKILL_DIR.parent

LAYER_ORDER = (
    "chapter-distillation",
    "opening",
    "protagonist",
    "supporting-cast",
    "outline",
    "highlight",
)

LAYER_LABELS = {
    "chapter-distillation": "章节蒸馏层",
    "opening": "黄金前三章层",
    "protagonist": "主角百科层",
    "supporting-cast": "重要配角层",
    "outline": "整书大纲层",
    "highlight": "剧情高光层",
}

# 章节蒸馏中每章必含的字段（用于检测是否是模板填充）
CHAPTER_SKELETON_FIELDS = [
    "本章核心推进",
    "主角 / 核心视角状态",
    "关键新信息 / 新设定",
    "关系 / 局势变化",
    "本章结构功能",
    "章末钩子 / 遗留问题",
]

# 模板话术特征模式 — 如果章节蒸馏中出现这些模式，说明是模板填充
TEMPLATE_PATTERNS = [
    r"本章围绕[「「""].*?[」」""]对应事件推进当前主线",
    r"把主角从上一节点推向下一节点",
    r"本章至少会补入与.*?相关的新线索",
    r"会出现细小但明确的变化",
    r"为下一轮局势升级做铺垫",
    r"不只是单章事件，而是连续推进链上的一个节点",
    r"重点体现其在.*?阶段里的判断、试探和应对",
    r"制造本章局部矛盾，并把阅读驱动力稳定输送到下一章",
]

# 因果推理模式 — 用于检测分析的深度
CAUSAL_PATTERNS = [
    r"因为.*所以",
    r"由于.*因此",
    r"导致",
    r"触发",
    r"由此.*进而",
    r"如果.*就",
    r"之所以.*是因为",
    r"这一转变的根源",
    r"其根本原因",
    r"深层逻辑",
]

# 具体锚定模式 — 用于检测分析是否足够具体
SPECIFICITY_PATTERNS = [
    r"第\d+章",           # 章节锚定
    r"\d+万?字",          # 字数锚定
    r"约\d+%",            # 比例锚定
    r"从.*转为|变为|转向", # 变化锚定
    r"与第[一二三四五六七八九十\d]+阶段",  # 阶段锚定
]

# 专有名词模式 — 中文专名（门派、地名、人名等）
PROPER_NOUN_PATTERN = re.compile(
    r'(?<!#\s)(?<!\d\.\s)\b[\u4e00-\u9fff]{2,6}(?:门|派|宗|府|国|界|城|山|谷|剑|刀|法|诀|丹|器|符|阵|兽|族|殿|阁|楼|堂|院|盟|教|帮|会|寺|观|宫|塔|渊|域|星|海|原|林|峰|崖|谷|洞|岛|湖|河|江|川)'
)

# 动作描述词
ACTION_PATTERNS = re.compile(
    r'(击败|击杀|突破|晋升|获得|失去|背叛|结盟|发现|揭露|逃离|闯入|修炼|炼制|拍卖|交易|夺取|抢夺|守护|摧毁|建立|瓦解|反杀|反攻|撤退|追击|渡劫|飞升|觉醒|封印|解封)'
)


# ============================================================
# 工具函数
# ============================================================

def read_text(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def latest_status_file(workspace: Path) -> Path | None:
    candidates = sorted(workspace.glob("工作状态-*.md"))
    return candidates[-1] if candidates else None


def detect_novel_name(workspace: Path) -> str:
    for path in (
        workspace / "README.md",
        latest_status_file(workspace),
    ):
        text = read_text(path)
        if not text:
            continue
        for pattern in (
            r"#\s*《(.+?)》",
            r"#\s*(.+?)\s*工作状态",
        ):
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
    return workspace.name


# ============================================================
# 维度一：结构完整度 / 模板检测
# ============================================================

def detect_template_content(text: str) -> dict[str, Any]:
    """检测文本中是否存在模板话术填充。

    返回模板行数、模板密度等信息。
    """
    lines = text.split("\n")
    template_lines: list[tuple[int, str, str]] = []

    for i, line in enumerate(lines, start=1):
        for pattern in TEMPLATE_PATTERNS:
            if re.search(pattern, line):
                template_lines.append((i, line.strip(), pattern))
                break

    template_density = len(template_lines) / max(len(lines), 1)

    return {
        "template_line_count": len(template_lines),
        "template_density": round(template_density, 4),
        "is_template_heavy": template_density > 0.15,
        "sample_template_lines": [
            {"line": ln, "text": txt[:120]} for ln, txt, _ in template_lines[:8]
        ],
    }


def check_chapter_uniqueness(skeleton_path: Path) -> dict[str, Any]:
    """检测章节蒸馏骨架中每章的独特性。

    提取每章的"核心推进"字段，比较描述是否每章都有独立内容。
    会自动剥离模板话术中的章节名占位，防止因章节名不同而误判为独特。
    """
    text = read_text(skeleton_path)
    if not text:
        return {"ok": False, "reason": "file_missing"}

    # 提取每章的"本章核心推进"行
    core_progressions = re.findall(
        r'-\s*\*{0,2}本章核心推进\*{0,2}[：:]\s*(.+?)(?=\n-|\n##|\n\n\S|\Z)',
        text,
        re.DOTALL,
    )

    if not core_progressions:
        return {"ok": False, "reason": "no_core_progressions_found"}

    # 清理模板噪音：去除章节名占位和常见模板前缀
    def normalize_progression(text: str) -> str:
        """去除模板噪音，只保留核心描述部分。"""
        # 去除 "本章围绕"xxx"对应事件推进当前主线" 这类模板前缀
        # 支持中英文引号："" '' 「」 "" 
        text = re.sub(
            r'本章围绕[\"\'\'\u201c\u201d\u300c\u300d].*?[\"\'\'\u201c\u201d\u300c\u300d]对应事件推进当前主线[，,]*\s*',
            '',
            text,
        )
        # 去除 "把主角从上一节点推向下一节点" 这类模板连接词
        text = re.sub(r'把主角从上一节点推向下一节点[，,]*\s*', '', text)
        text = re.sub(r'并为后续冲突或收益做承接[。.]*\s*', '', text)
        return text.strip()

    cleaned = [normalize_progression(p.strip()) for p in core_progressions]

    # 过滤掉完全空的描述（全是模板话术被剥离后）
    non_empty = [c for c in cleaned if c and len(c) >= 10]
    unique = list(dict.fromkeys(non_empty))
    uniqueness_ratio = len(unique) / max(len(non_empty), 1)

    # 检测相邻章节相似度（使用清理后的文本）
    high_sim_pairs = []
    for i in range(len(non_empty) - 1):
        sim = SequenceMatcher(None, non_empty[i], non_empty[i + 1]).ratio()
        if sim > 0.70:
            high_sim_pairs.append({
                "chapter_index": i + 1,
                "similarity": round(sim, 3),
            })

    return {
        "ok": uniqueness_ratio >= 0.70,
        "reason": "ok" if uniqueness_ratio >= 0.70 else "low_uniqueness",
        "total_chapters": len(non_empty),
        "unique_descriptions": len(unique),
        "uniqueness_ratio": round(uniqueness_ratio, 3),
        "high_similarity_pairs": len(high_sim_pairs),
        "high_sim_sample": high_sim_pairs[:5],
        "empty_after_normalize": len(core_progressions) - len(non_empty),
    }


def check_specificity_density(text: str) -> dict[str, Any]:
    """检测文本中具体锚定内容的密度。

    模板填充的文本通常具体锚定词密度极低。
    """
    if not text:
        return {"ok": False, "reason": "empty"}

    total_chars = len(text)

    proper_nouns = len(PROPER_NOUN_PATTERN.findall(text))
    actions = len(ACTION_PATTERNS.findall(text))

    casual_count = 0
    for pattern in CAUSAL_PATTERNS:
        casual_count += len(re.findall(pattern, text))

    specificity_count = 0
    for pattern in SPECIFICITY_PATTERNS:
        specificity_count += len(re.findall(pattern, text))

    total_markers = proper_nouns + actions + casual_count + specificity_count

    # 每千字的锚定词密度
    density_per_1k = (total_markers / max(total_chars, 1)) * 1000

    return {
        "ok": density_per_1k >= 8.0,
        "reason": "ok" if density_per_1k >= 8.0 else "low_specificity",
        "total_chars": total_chars,
        "proper_nouns": proper_nouns,
        "action_words": actions,
        "causal_phrases": casual_count,
        "specificity_markers": specificity_count,
        "total_markers": total_markers,
        "density_per_1000_chars": round(density_per_1k, 2),
    }


def check_structural_completeness(path: Path, required_sections: list[tuple[str, str]], min_chars_per_section: int = 80) -> dict[str, Any]:
    """检查文件是否按预期结构组织，且每段有实质内容。

    required_sections: [(section_title_pattern, human_label), ...]
    """
    text = read_text(path)
    if not text:
        return {"ok": False, "reason": "file_missing"}

    results = []
    for pattern, label in required_sections:
        match = re.search(pattern, text)
        if not match:
            results.append({"section": label, "found": False, "adequate": False, "reason": "not_found"})
            continue

        # 提取该 section 之后的内容直到下一个同级 section 或文件末尾
        start = match.end()
        next_section = re.search(r"^##\s+", text[start:], re.MULTILINE)
        section_content = text[start:start + next_section.start()] if next_section else text[start:]
        content_len = len(section_content.strip())

        results.append({
            "section": label,
            "found": True,
            "adequate": content_len >= min_chars_per_section,
            "content_length": content_len,
            "reason": "ok" if content_len >= min_chars_per_section else f"too_short:{content_len}chars",
        })

    all_ok = all(r["found"] and r["adequate"] for r in results)
    return {
        "ok": all_ok,
        "sections": results,
        "total_sections": len(required_sections),
        "ok_sections": sum(1 for r in results if r["found"] and r["adequate"]),
    }


# ============================================================
# 维度二：跨层一致性
# ============================================================

def extract_chapter_events(skeleton_text: str) -> list[dict[str, Any]]:
    """从章节蒸馏骨架中提取每章的关键事件节点。"""
    sections = re.split(r"\n##\s+", skeleton_text)
    events = []
    for section in sections[1:]:  # 跳过前言
        lines = section.strip().split("\n")
        chapter_title = lines[0].strip() if lines else "未知章节"
        event = {
            "chapter": chapter_title,
            "core_progression": "",
            "new_info": "",
            "hook": "",
        }
        for line in lines:
            if "本章核心推进" in line:
                event["core_progression"] = line.split("：", 1)[-1].split(":", 1)[-1].strip()
            elif "关键新信息" in line:
                event["new_info"] = line.split("：", 1)[-1].split(":", 1)[-1].strip()
            elif "章末钩子" in line:
                event["hook"] = line.split("：", 1)[-1].split(":", 1)[-1].strip()
        events.append(event)
    return events


def check_cross_layer_consistency(workspace: Path, novel_name: str) -> dict[str, Any]:
    """跨层一致性检查。

    检查章节蒸馏层、主角百科层、大纲层之间的关键节点是否一致。
    """
    conflicts = []

    # --- 检查 1：章节蒸馏层 vs 阶段骨架 ---
    skeleton_path = workspace / f"{novel_name}-章节蒸馏骨架.md"
    stage_path = workspace / f"{novel_name}-阶段骨架与换挡草图.md"

    skeleton_text = read_text(skeleton_path)
    stage_text = read_text(stage_path)

    if skeleton_text and stage_text:
        # 提取阶段骨架中的章节范围
        stage_ranges = re.findall(
            r'(?:阶段\s*\d|阶段\s*[一二三四五六七八九十]).*?第\s*(\d+)\s*章.*?第\s*(\d+)\s*章',
            stage_text,
        )
        if stage_ranges:
            # 检查阶段边界是否有重叠或间隙
            for i, (start, end) in enumerate(stage_ranges):
                if i > 0:
                    prev_end = int(stage_ranges[i - 1][1])
                    curr_start = int(start)
                    if curr_start <= prev_end:
                        conflicts.append({
                            "type": "stage_boundary_overlap",
                            "detail": f"阶段 {i} 的起始章({curr_start})与阶段 {i} 的结束章({prev_end})重叠",
                            "severity": "medium",
                        })
                    elif curr_start > prev_end + 5:
                        conflicts.append({
                            "type": "stage_boundary_gap",
                            "detail": f"阶段 {i - 1} 结束于第{prev_end}章，阶段 {i} 开始于第{curr_start}章，中间有{curr_start - prev_end - 1}章的间隙",
                            "severity": "low",
                        })

    # --- 检查 2：章节骨架字段完整性 ---
    if skeleton_text:
        chapter_sections = re.findall(r"^##\s+(.+)", skeleton_text, re.MULTILINE)
        # 检测连续多章缺少具体内容的情况
        generic_count = 0
        for section_title in chapter_sections[1:]:  # 跳过"前言"
            # 在章节内容中找对应的核心推进
            section_pattern = re.escape(section_title)
            match = re.search(
                rf"##\s+{section_pattern}\n(.*?)(?=\n##\s+|\Z)",
                skeleton_text,
                re.DOTALL,
            )
            if match:
                section_content = match.group(1)
                # 检查是否有模板话术
                template_hits = sum(
                    1 for p in TEMPLATE_PATTERNS if re.search(p, section_content)
                )
                if template_hits >= 3:
                    generic_count += 1

        if generic_count > max(len(chapter_sections) * 0.3, 10):
            conflicts.append({
                "type": "widespread_template_content",
                "detail": f"{generic_count}/{len(chapter_sections)} 章的蒸馏内容存在明显模板痕迹",
                "severity": "high",
            })

    # --- 检查 3：主角百科 vs 大纲层主角判断 ---
    anchor_path = workspace / f"{novel_name}-主角锚点与骨架.md"
    overview_path = workspace / f"{novel_name}-大纲总览.md"

    anchor_text = read_text(anchor_path)
    overview_text = read_text(overview_path)

    if anchor_text and overview_text:
        # 提取主角成长阶段数
        anchor_stages = len(re.findall(r'阶段\s*\d|第[一二三四五六七八九十\d]+阶段', anchor_text))
        overview_stages = len(re.findall(r'阶段\s*\d|第[一二三四五六七八九十\d]+阶段', overview_text))

        if anchor_stages > 0 and overview_stages > 0 and abs(anchor_stages - overview_stages) > 2:
            conflicts.append({
                "type": "stage_count_mismatch",
                "detail": f"主角百科层识别到 {anchor_stages} 个阶段，大纲层识别到 {overview_stages} 个阶段，差异较大",
                "severity": "medium",
            })

    return {
        "ok": len(conflicts) == 0,
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "high_severity_count": sum(1 for c in conflicts if c["severity"] == "high"),
        "medium_severity_count": sum(1 for c in conflicts if c["severity"] == "medium"),
    }


# ============================================================
# 维度三：分析深度
# ============================================================

def check_analytical_depth(text: str) -> dict[str, Any]:
    """检测分析深度：因果推理 vs 纯描述的比例。"""
    if not text:
        return {"ok": False, "reason": "empty"}

    lines = [l for l in text.split("\n") if l.strip() and not l.strip().startswith("#")]
    total_lines = len(lines)

    causal_lines = 0
    for line in lines:
        for pattern in CAUSAL_PATTERNS:
            if re.search(pattern, line):
                causal_lines += 1
                break

    # 检测纯描述行（以"第X章"开头但无因果词的行）
    descriptive_lines = 0
    for line in lines:
        if re.match(r"第[一二三四五六七八九十\d]+章", line) or re.match(r"^\d+\.\s", line):
            has_causal = any(re.search(p, line) for p in CAUSAL_PATTERNS)
            if not has_causal:
                descriptive_lines += 1

    causal_ratio = causal_lines / max(total_lines, 1)
    descriptive_ratio = descriptive_lines / max(total_lines, 1)

    return {
        "ok": causal_ratio >= 0.08,
        "reason": "ok" if causal_ratio >= 0.08 else "low_causal_density",
        "total_lines": total_lines,
        "causal_lines": causal_lines,
        "descriptive_lines": descriptive_lines,
        "causal_ratio": round(causal_ratio, 3),
        "descriptive_ratio": round(descriptive_ratio, 3),
    }


# ============================================================
# 维度四：可操作性
# ============================================================

def check_actionability(path: Path, action_keywords: list[str]) -> dict[str, Any]:
    """检查修改建议类文件的可操作性。

    检测是否包含具体的、可执行的建议，而非泛化评论。
    """
    text = read_text(path)
    if not text:
        return {"ok": False, "reason": "file_missing"}

    hits = {}
    for keyword in action_keywords:
        hits[keyword] = len(re.findall(re.escape(keyword), text))

    total_hits = sum(hits.values())

    # 检查是否有具体的修改方案（不是"需要改进"这类空话）
    has_concrete_plan = bool(re.search(
        r'(建议.*第\d+章|具体.*修改|优先.*第[一二三四五六七八九十\d]+|应该.*压缩|应该.*扩写|应该.*前移|应该.*后移)',
        text,
    ))

    return {
        "ok": total_hits >= 3 and has_concrete_plan,
        "reason": "ok" if (total_hits >= 3 and has_concrete_plan) else "low_actionability",
        "keyword_hits": hits,
        "total_hits": total_hits,
        "has_concrete_plan": has_concrete_plan,
    }


# ============================================================
# 逐层质量检查
# ============================================================

def quality_check_chapter_distillation(workspace: Path, novel_name: str) -> dict[str, Any]:
    """章节蒸馏层的质量检查。"""
    skeleton_path = workspace / f"{novel_name}-章节蒸馏骨架.md"
    stage_path = workspace / f"{novel_name}-阶段骨架与换挡草图.md"

    skeleton_text = read_text(skeleton_path)
    stage_text = read_text(stage_path)

    template_result = detect_template_content(skeleton_text)
    uniqueness_result = check_chapter_uniqueness(skeleton_path)
    specificity_result = check_specificity_density(skeleton_text)
    depth_result = check_analytical_depth(skeleton_text)

    # 阶段骨架的结构完整度
    stage_structure = check_structural_completeness(
        stage_path,
        [
            (r"##\s+总判断", "总判断"),
            (r"##\s+阶段\s*1", "阶段 1"),
            (r"##\s+阶段\s*2", "阶段 2"),
            (r"##\s+阶段\s*3", "阶段 3"),
        ],
    )

    issues = []
    if template_result["is_template_heavy"]:
        issues.append(f"模板话术密度过高 ({template_result['template_density']:.1%})，疑似大面积模板填充")
    if not uniqueness_result.get("ok"):
        reason = uniqueness_result.get("reason", "unknown")
        if reason == "file_missing":
            issues.append("章节蒸馏骨架文件缺失")
        elif reason == "no_core_progressions_found":
            issues.append("章节蒸馏骨架中未找到核心推进字段")
        else:
            ratio = uniqueness_result.get("uniqueness_ratio", 0)
            issues.append(f"章节独特性不足，唯一描述比 {ratio:.1%}")
    if not specificity_result.get("ok"):
        density = specificity_result.get("density_per_1000_chars", 0)
        issues.append(f"具体锚定密度过低 ({density:.1f}/千字)")
    if not depth_result.get("ok"):
        ratio = depth_result.get("causal_ratio", 0)
        issues.append(f"分析深度不足，因果推理密度 {ratio:.1%}")

    score = 100
    if template_result["is_template_heavy"]:
        score -= 30
    if not uniqueness_result.get("ok"):
        score -= 20
    if not specificity_result.get("ok"):
        score -= 15
    if not depth_result.get("ok"):
        score -= 10
    score = max(0, min(100, score))

    return {
        "layer": "chapter-distillation",
        "label": LAYER_LABELS["chapter-distillation"],
        "score": score,
        "issues": issues,
        "ok": len(issues) == 0,
        "details": {
            "template": template_result,
            "uniqueness": uniqueness_result,
            "specificity": specificity_result,
            "depth": depth_result,
            "stage_structure": stage_structure,
        },
    }


def quality_check_opening(workspace: Path, novel_name: str) -> dict[str, Any]:
    """黄金前三章层的质量检查。"""
    checks = {}
    issues = []

    # 支持阿拉伯数字和中文数字两种命名方式
    ch_num_map = {1: ["1", "一"], 2: ["2", "二"], 3: ["3", "三"]}

    for ch_num in [1, 2, 3]:
        ch_text = ""
        for suffix in ch_num_map[ch_num]:
            ch_path = workspace / f"{novel_name}-第{suffix}章拆解.md"
            text = read_text(ch_path)
            if text:
                ch_text = text
                break

        if ch_text:
            specificity = check_specificity_density(ch_text)
            depth = check_analytical_depth(ch_text)
            checks[f"chapter_{ch_num}"] = {
                "specificity": specificity,
                "depth": depth,
            }
            if not specificity["ok"]:
                issues.append(f"第{ch_num}章拆解具体锚定密度不足 ({specificity['density_per_1000_chars']:.1f}/千字)")
            if not depth["ok"]:
                issues.append(f"第{ch_num}章拆解分析深度不足")
        else:
            checks[f"chapter_{ch_num}"] = {"exists": False}
            issues.append(f"第{ch_num}章拆解文件缺失")

    # 开篇问题与修改建议的可操作性
    revision_path = workspace / f"{novel_name}-开篇问题与修改建议.md"
    action_result = check_actionability(
        revision_path,
        ["第一优先修改项", "修改建议", "具体", "调整", "增加", "删除", "重写"],
    )
    checks["revision_actionability"] = action_result
    if not action_result["ok"]:
        issues.append("开篇修改建议可操作性不足（缺少具体章节目标和可执行方案）")

    # 总判断的深度
    total_path = workspace / f"{novel_name}-黄金前三章总判断.md"
    total_depth = check_analytical_depth(read_text(total_path))
    checks["total_depth"] = total_depth

    score = 100
    score -= len([c for c in checks if isinstance(checks[c], dict) and not checks[c].get("specificity", {}).get("ok", True)]) * 10
    score -= len([c for c in checks if isinstance(checks[c], dict) and not checks[c].get("depth", {}).get("ok", True)]) * 8
    if not action_result["ok"]:
        score -= 15
    score = max(0, min(100, score))

    return {
        "layer": "opening",
        "label": LAYER_LABELS["opening"],
        "score": score,
        "issues": issues,
        "ok": len(issues) == 0,
        "details": checks,
    }


def quality_check_protagonist(workspace: Path, novel_name: str) -> dict[str, Any]:
    """主角百科层的质量检查。"""
    checks = {}
    issues = []

    # 主角锚点与骨架
    anchor_path = workspace / f"{novel_name}-主角锚点与骨架.md"
    anchor_text = read_text(anchor_path)
    if anchor_text:
        struct = check_structural_completeness(
            anchor_path,
            [
                (r"##\s+主角锚点", "主角锚点"),
                (r"##\s+.*骨架", "骨架"),
                (r"##\s+.*身份", "身份"),
                (r"##\s+.*成长", "成长"),
            ],
        )
        checks["anchor_structure"] = struct
        if not struct["ok"]:
            issues.append("主角锚点文件结构不完整")
    else:
        issues.append("主角锚点文件缺失")

    # 全书精华总结
    essence_path = workspace / f"{novel_name}-全书精华总结.md"
    essence_text = read_text(essence_path)
    if essence_text:
        depth = check_analytical_depth(essence_text)
        checks["essence_depth"] = depth
        if not depth["ok"]:
            issues.append("全书精华总结因果推理密度不足")
    else:
        issues.append("全书精华总结缺失")

    # 检测主角卡的具体性
    final_cards = sorted(workspace.glob("*-最终人物卡.md"))
    if final_cards:
        card_text = read_text(final_cards[0])
        specificity = check_specificity_density(card_text)
        checks["card_specificity"] = specificity
        if not specificity["ok"]:
            issues.append(f"主角最终人物卡具体锚定密度不足 ({specificity['density_per_1000_chars']:.1f}/千字)")
    else:
        issues.append("主角最终人物卡缺失")

    score = 100
    if not checks.get("anchor_structure", {}).get("ok", False):
        score -= 20
    if not checks.get("essence_depth", {}).get("ok", False):
        score -= 15
    if not checks.get("card_specificity", {}).get("ok", False):
        score -= 15
    score = max(0, min(100, score))

    return {
        "layer": "protagonist",
        "label": LAYER_LABELS["protagonist"],
        "score": score,
        "issues": issues,
        "ok": len(issues) == 0,
        "details": checks,
    }


def quality_check_supporting_cast(workspace: Path, novel_name: str) -> dict[str, Any]:
    """重要配角层的质量检查。"""
    checks = {}
    issues = []

    top10_path = workspace / f"{novel_name}-重要配角Top10总表.md"
    top10_text = read_text(top10_path)
    if top10_text:
        specificity = check_specificity_density(top10_text)
        checks["top10_specificity"] = specificity
        if not specificity["ok"]:
            issues.append(f"重要配角 Top10 总表具体锚定密度不足 ({specificity['density_per_1000_chars']:.1f}/千字)")
    else:
        issues.append("重要配角 Top10 总表缺失")

    relation_path = workspace / f"{novel_name}-重要配角与主角关系图.md"
    relation_text = read_text(relation_path)
    if relation_text:
        relation_depth = check_analytical_depth(relation_text)
        checks["relation_depth"] = relation_depth
        if not relation_depth["ok"]:
            issues.append("配角与主角关系图因果推理密度不足")
    else:
        issues.append("重要配角与主角关系图缺失")

    stage_path = workspace / f"{novel_name}-重要配角阶段作用分布.md"
    stage_text = read_text(stage_path)
    if stage_text:
        stage_specificity = check_specificity_density(stage_text)
        checks["stage_specificity"] = stage_specificity
        if not stage_specificity["ok"]:
            issues.append("重要配角阶段作用分布的具体锚定密度不足")
    else:
        issues.append("重要配角阶段作用分布缺失")

    profile_files = sorted((workspace / "supporting-cast").glob("*-配角分析.md"))
    checks["profile_count"] = {"ok": len(profile_files) >= 10, "count": len(profile_files)}
    if len(profile_files) < 10:
        issues.append(f"重要配角分析文件不足 10 份（当前 {len(profile_files)}）")

    score = 100
    if not checks.get("top10_specificity", {}).get("ok", False):
        score -= 20
    if not checks.get("relation_depth", {}).get("ok", False):
        score -= 15
    if not checks.get("stage_specificity", {}).get("ok", False):
        score -= 15
    if not checks["profile_count"]["ok"]:
        score -= 20
    score = max(0, min(100, score))

    return {
        "layer": "supporting-cast",
        "label": LAYER_LABELS["supporting-cast"],
        "score": score,
        "issues": issues,
        "ok": len(issues) == 0,
        "details": checks,
    }


def quality_check_outline(workspace: Path, novel_name: str) -> dict[str, Any]:
    """整书大纲层的质量检查。"""
    checks = {}
    issues = []

    # 大纲总览
    overview_path = workspace / f"{novel_name}-大纲总览.md"
    overview_text = read_text(overview_path)
    if overview_text:
        overview_depth = check_analytical_depth(overview_text)
        checks["overview_depth"] = overview_depth
        if not overview_depth["ok"]:
            issues.append("大纲总览分析深度不足")
    else:
        issues.append("大纲总览缺失")

    # 阶段与篇章拆分
    stages_path = workspace / f"{novel_name}-阶段与篇章拆分.md"
    stages_text = read_text(stages_path)
    if stages_text:
        stages_specificity = check_specificity_density(stages_text)
        checks["stages_specificity"] = stages_specificity
        if not stages_specificity["ok"]:
            issues.append("阶段拆分的具体锚定密度不足")
    else:
        issues.append("阶段与篇章拆分缺失")

    # 结构问题与修改建议的可操作性
    revision_path = workspace / f"{novel_name}-结构问题与修改建议.md"
    action_result = check_actionability(
        revision_path,
        ["修改建议", "具体", "调整", "压缩", "扩写", "前移", "后移", "合并"],
    )
    checks["revision_actionability"] = action_result
    if not action_result["ok"]:
        issues.append("结构修改建议可操作性不足")

    score = 100
    if not checks.get("overview_depth", {}).get("ok", False):
        score -= 20
    if not checks.get("stages_specificity", {}).get("ok", False):
        score -= 15
    if not action_result["ok"]:
        score -= 15
    score = max(0, min(100, score))

    return {
        "layer": "outline",
        "label": LAYER_LABELS["outline"],
        "score": score,
        "issues": issues,
        "ok": len(issues) == 0,
        "details": checks,
    }


def quality_check_highlight(workspace: Path, novel_name: str) -> dict[str, Any]:
    """剧情高光层的质量检查。"""
    checks = {}
    issues = []

    # Top10 总表
    top10_path = workspace / f"{novel_name}-最吸引人的十个剧情细节总表.md"
    top10_text = read_text(top10_path)
    if top10_text:
        specificity = check_specificity_density(top10_text)
        checks["top10_specificity"] = specificity
        if not specificity["ok"]:
            issues.append(f"Top10 总表具体锚定密度不足 ({specificity['density_per_1000_chars']:.1f}/千字)")
    else:
        issues.append("Top10 总表缺失")

    # 剧情吸引力机制分析
    mechanism_path = workspace / f"{novel_name}-剧情吸引力机制分析.md"
    mechanism_text = read_text(mechanism_path)
    if mechanism_text:
        depth = check_analytical_depth(mechanism_text)
        checks["mechanism_depth"] = depth
        if not depth["ok"]:
            issues.append("吸引力机制分析因果推理密度不足")
    else:
        issues.append("吸引力机制分析缺失")

    # 高光改造建议的可操作性
    revision_path = workspace / f"{novel_name}-剧情高光改造建议.md"
    action_result = check_actionability(
        revision_path,
        ["应该补强", "应该前移", "应该后移", "应该压缩", "应该扩写", "具体", "建议"],
    )
    checks["revision_actionability"] = action_result
    if not action_result["ok"]:
        issues.append("高光改造建议可操作性不足")

    score = 100
    if not checks.get("top10_specificity", {}).get("ok", False):
        score -= 20
    if not checks.get("mechanism_depth", {}).get("ok", False):
        score -= 15
    if not action_result["ok"]:
        score -= 15
    score = max(0, min(100, score))

    return {
        "layer": "highlight",
        "label": LAYER_LABELS["highlight"],
        "score": score,
        "issues": issues,
        "ok": len(issues) == 0,
        "details": checks,
    }


# ============================================================
# 综合质量门
# ============================================================

def run_quality_gate(workspace: Path, novel_name: str, target_layer: str | None = None) -> dict[str, Any]:
    """运行完整的质量门检查。"""
    layer_results = {}

    layers_to_check = [target_layer] if target_layer else list(LAYER_ORDER)

    for layer in layers_to_check:
        if layer == "chapter-distillation":
            layer_results[layer] = quality_check_chapter_distillation(workspace, novel_name)
        elif layer == "opening":
            layer_results[layer] = quality_check_opening(workspace, novel_name)
        elif layer == "protagonist":
            layer_results[layer] = quality_check_protagonist(workspace, novel_name)
        elif layer == "supporting-cast":
            layer_results[layer] = quality_check_supporting_cast(workspace, novel_name)
        elif layer == "outline":
            layer_results[layer] = quality_check_outline(workspace, novel_name)
        elif layer == "highlight":
            layer_results[layer] = quality_check_highlight(workspace, novel_name)

    # 跨层一致性（只在全量检查时运行）
    cross_layer = {}
    if target_layer is None:
        cross_layer = check_cross_layer_consistency(workspace, novel_name)

    # 计算综合评分
    scores = [r["score"] for r in layer_results.values()]
    overall_score = round(sum(scores) / max(len(scores), 1), 1) if scores else 0

    all_issues = []
    for layer, result in layer_results.items():
        for issue in result["issues"]:
            all_issues.append(f"[{LAYER_LABELS[layer]}] {issue}")
    if cross_layer.get("conflicts"):
        for conflict in cross_layer["conflicts"]:
            all_issues.append(f"[跨层] {conflict['detail']} (严重度: {conflict['severity']})")

    return {
        "workspace": str(workspace),
        "novel_name": novel_name,
        "target_layer": target_layer,
        "overall_score": overall_score,
        "layer_results": layer_results,
        "cross_layer_consistency": cross_layer,
        "all_issues": all_issues,
        "issue_count": len(all_issues),
        "high_severity_issues": sum(
            1 for c in cross_layer.get("conflicts", []) if c.get("severity") == "high"
        ),
        "is_quality_pass": overall_score >= 75 and not any(
            r["score"] < 60 for r in layer_results.values()
        ),
    }


# ============================================================
# 报告生成
# ============================================================

def render_quality_report(result: dict[str, Any]) -> str:
    """生成 Markdown 格式的质量门报告。"""
    novel_name = result["novel_name"]
    overall = result["overall_score"]
    passed = result["is_quality_pass"]

    lines = [
        f"# 《{novel_name}》质量门报告",
        "",
        f"- 工作区：`{result['workspace']}`",
        f"- 目标层：`{result['target_layer'] or '全部六层'}`",
        f"- **综合质量评分：{overall}/100** {'✅ 通过' if passed else '⚠️ 未通过'}",
        f"- 问题总数：{result['issue_count']}",
        "",
        "## 各层质量评分",
        "",
        "| 层 | 评分 | 状态 | 主要问题 |",
        "| --- | --- | --- | --- |",
    ]

    for layer in LAYER_ORDER:
        lr = result["layer_results"].get(layer)
        if not lr:
            lines.append(f"| {LAYER_LABELS[layer]} | N/A | 未检查 | — |")
            continue
        score = lr["score"]
        status = "✅" if lr["ok"] else ("⚠️" if score >= 60 else "❌")
        top_issue = lr["issues"][0][:60] + "..." if lr["issues"] else "—"
        lines.append(f"| {LAYER_LABELS[layer]} | {score}/100 | {status} | {top_issue} |")

    lines.append("")

    # 跨层一致性
    cross = result.get("cross_layer_consistency", {})
    if cross and cross.get("conflicts"):
        lines.extend([
            "## 跨层一致性冲突",
            "",
            f"- 冲突总数：{cross['conflict_count']}",
            f"- 高严重度：{cross.get('high_severity_count', 0)}",
            f"- 中严重度：{cross.get('medium_severity_count', 0)}",
            "",
        ])
        for c in cross["conflicts"]:
            severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(c["severity"], "⚪")
            lines.append(f"- {severity_icon} [{c['severity']}] {c['detail']}")
        lines.append("")

    # 逐层详情
    lines.append("## 逐层质量详情")
    lines.append("")

    for layer in LAYER_ORDER:
        lr = result["layer_results"].get(layer)
        if not lr:
            continue

        lines.append(f"### {LAYER_LABELS[layer]}（{lr['score']}/100）")
        lines.append("")

        if lr["issues"]:
            lines.append("**发现的问题：**")
            for issue in lr["issues"]:
                lines.append(f"- ⚠️ {issue}")
            lines.append("")

        # 关键指标摘要
        details = lr.get("details", {})
        if layer == "chapter-distillation":
            tmpl = details.get("template", {})
            uniq = details.get("uniqueness", {})
            spec = details.get("specificity", {})
            if tmpl:
                lines.append(f"- 模板话术密度：{tmpl.get('template_density', 'N/A')}")
            if uniq:
                lines.append(f"- 章节独特性比：{uniq.get('uniqueness_ratio', 'N/A')} ({uniq.get('unique_descriptions', 0)}/{uniq.get('total_chapters', 0)} 唯一描述)")
            if spec:
                lines.append(f"- 具体锚定密度：{spec.get('density_per_1000_chars', 'N/A')}/千字")
                lines.append(f"- 因果推理密度：{details.get('depth', {}).get('causal_ratio', 'N/A')}")
        elif layer == "protagonist":
            card_spec = details.get("card_specificity", {})
            if card_spec:
                lines.append(f"- 主角卡具体密度：{card_spec.get('density_per_1000_chars', 'N/A')}/千字")
        elif layer == "supporting-cast":
            top10_spec = details.get("top10_specificity", {})
            if top10_spec:
                lines.append(f"- Top10 总表具体密度：{top10_spec.get('density_per_1000_chars', 'N/A')}/千字")
            relation_depth = details.get("relation_depth", {})
            if relation_depth:
                lines.append(f"- 关系图因果密度：{relation_depth.get('causal_ratio', 'N/A')}")
            profile_count = details.get("profile_count", {})
            if profile_count:
                lines.append(f"- 配角分析文件数：{profile_count.get('count', 'N/A')}")
        elif layer == "outline":
            ov_depth = details.get("overview_depth", {})
            if ov_depth:
                lines.append(f"- 大纲总览因果密度：{ov_depth.get('causal_ratio', 'N/A')}")
        elif layer == "highlight":
            mech_depth = details.get("mechanism_depth", {})
            if mech_depth:
                lines.append(f"- 吸引力分析因果密度：{mech_depth.get('causal_ratio', 'N/A')}")
        lines.append("")

    # 质量改进建议
    if not passed:
        lines.extend([
            "## 质量改进优先级",
            "",
        ])
        # 按评分排序，优先修复低分层
        sorted_layers = sorted(
            [(layer, result["layer_results"][layer])
             for layer in LAYER_ORDER
             if layer in result["layer_results"]],
            key=lambda x: x[1]["score"],
        )
        for i, (layer, lr) in enumerate(sorted_layers, 1):
            if lr["ok"]:
                continue
            lines.append(f"{i}. **{LAYER_LABELS[layer]}**（{lr['score']}/100）")
            for issue in lr["issues"][:3]:
                lines.append(f"   - {issue}")
            lines.append("")

    lines.extend([
        "---",
        "",
        f"*报告由 quality_gate.py 自动生成*",
    ])

    return "\n".join(lines) + "\n"


# ============================================================
# CLI
# ============================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="小说工作区产物质量评估系统 — 在 validator 之上评估产物质量"
    )
    parser.add_argument("--workspace", required=True, help="工作区目录路径")
    parser.add_argument("--novel-name", help="小说名（自动检测）")
    parser.add_argument("--layer", help="只检查指定层（chapter-distillation/opening/protagonist/supporting-cast/outline/highlight）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--no-write-report", action="store_true", help="不写入质量门报告文件")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.exists():
        raise SystemExit(f"工作区不存在: {workspace}")

    novel_name = args.novel_name or detect_novel_name(workspace)
    target_layer = args.layer

    result = run_quality_gate(workspace, novel_name, target_layer)
    report_text = render_quality_report(result)

    report_path = workspace / f"{novel_name}-质量门报告.md"
    result["report_path"] = str(report_path)

    if not args.no_write_report:
        report_path.write_text(report_text, encoding="utf-8")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(report_text, end="")

    return 0 if result["is_quality_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
