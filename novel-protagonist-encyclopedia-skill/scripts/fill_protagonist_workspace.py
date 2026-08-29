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

SYSTEM_PROMPT = """你是资深网文角色编辑，任务是为“主角百科层”生成可直接落盘的正式分析文档。

要求：
1. 只输出 JSON，不要输出 markdown，不要加前言。
2. 必须优先依赖章节蒸馏层、开篇层、大纲层和高光层，而不是只复述原文。
3. 重点是稳定主角的身份底座、成长引擎、质变路线、关系网和核心体系。
4. 必须引用具体角色名、势力名、地点、阶段、关键事件，避免空泛“成长明显/人物立住”。
5. 必须包含因果推理，解释主角为什么成立、为什么会这样成长、为什么这些词条是主干。
6. 索引和完成度判断必须明确写出 `骨架完成` 与 `体系闭环完成` 的当前结论。

返回 JSON 结构：
{
  "meta_summary": {
    "skeleton_judgement": "一句话",
    "system_judgement": "一句话",
    "one_line_handoff": "一句话交接"
  },
  "startup_checklist": {
    "当前已达到": ["3-6条"],
    "首轮执行顺序说明": "100-220字"
  },
  "stage_outline": {
    "阶段_1": {
      "起止 chunk / 章节": "60-140字",
      "划分依据": "80-180字",
      "主角在这个阶段的状态": "80-180字",
      "主要地点 / 场域": "80-180字",
      "主要矛盾": "80-180字",
      "主要抬升": "80-180字"
    },
    "阶段_2": { ... },
    "阶段_3": { ... },
    "阶段_4": { ... }
  },
  "anchor": {
    "本名": "40-120字",
    "常见称谓": "40-120字",
    "化名 / 马甲": "40-120字",
    "易混简称": "40-120字",
    "关键关联名词": "80-180字",
    "从 chunk 蒸馏结果看": "80-180字",
    "从开篇与高光结果看": "80-180字",
    "从阶段划分看": "80-180字",
    "身份底座": "80-180字",
    "成长引擎": "80-180字",
    "质变路线": "80-180字",
    "高位结构": "80-180字"
  },
  "final_card": {
    "基本信息": "100-220字",
    "身份概述": "100-220字",
    "关键物品": "80-180字",
    "关键事件": "100-220字",
    "势力归属": "80-180字",
    "核心能力与成长引擎": "100-220字",
    "成长阶段": "100-220字",
    "战斗风格与行动方式": "80-180字",
    "关键关系方向": "80-180字",
    "活动范围与空间轨迹": "80-180字",
    "阶段总结": "80-180字",
    "人物特征总结": "80-180字",
    "当前一级词条建议": "100-220字",
    "最终结论": "100-220字"
  },
  "index": {
    "人物核心词条": ["3-6条"],
    "力量体系词条": ["3-6条"],
    "世界与高位设定词条": ["3-6条"],
    "结构与关系网络词条": ["3-6条"],
    "核心二级词条": ["4-8条"],
    "整体结构总结": "100-220字",
    "骨架完成判断": "100-220字",
    "体系闭环判断": "100-220字",
    "推荐阅读顺序": ["3-6条"],
    "下一步执行顺序": ["3-6条"]
  },
  "core_overview": {
    "总骨架": "100-220字",
    "人物核心结构": "100-220字",
    "成长引擎": "100-220字",
    "质变路线": "100-220字",
    "世界与高位结构": "100-220字",
    "关键模块关系": "100-220字",
    "阶段性变化": "100-220字",
    "最终结论": "100-220字",
    "主干词条": "80-180字"
  },
  "essence_summary": {
    "一句话定性": "80-180字",
    "这本书最核心写的是什么": "100-220字",
    "主角这条线为什么成立": "100-220字",
    "这本书最强的地方": "100-220字",
    "这本书的结构抬升是怎么完成的": "100-220字",
    "这本书真正的主意象是什么": "80-180字",
    "为什么这本书值得拆成主角全词条百科": "100-220字",
    "这本书真正的精华在哪里": "100-220字",
    "最终结论": "100-220字"
  },
  "next_actions": ["一句具体下一步", "一句具体下一步", "一句具体下一步"]
}
"""

STAGE_FIELDS = ["起止 chunk / 章节", "划分依据", "主角在这个阶段的状态", "主要地点 / 场域", "主要矛盾", "主要抬升"]
ANCHOR_FIELDS = [
    "本名", "常见称谓", "化名 / 马甲", "易混简称", "关键关联名词",
    "从 chunk 蒸馏结果看", "从开篇与高光结果看", "从阶段划分看",
    "身份底座", "成长引擎", "质变路线", "高位结构",
]
FINAL_CARD_FIELDS = [
    "基本信息", "身份概述", "关键物品", "关键事件", "势力归属",
    "核心能力与成长引擎", "成长阶段", "战斗风格与行动方式",
    "关键关系方向", "活动范围与空间轨迹", "阶段总结", "人物特征总结",
    "当前一级词条建议", "最终结论",
]
CORE_OVERVIEW_FIELDS = [
    "总骨架", "人物核心结构", "成长引擎", "质变路线",
    "世界与高位结构", "关键模块关系", "阶段性变化", "最终结论", "主干词条",
]
ESSENCE_FIELDS = [
    "一句话定性", "这本书最核心写的是什么", "主角这条线为什么成立", "这本书最强的地方",
    "这本书的结构抬升是怎么完成的", "这本书真正的主意象是什么",
    "为什么这本书值得拆成主角全词条百科", "这本书真正的精华在哪里", "最终结论",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auto-fill the protagonist encyclopedia layer from distilled and upper-layer context.")
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


def protagonist_work_dir(workspace: Path) -> Path:
    return workspace / "work" / "protagonist-analysis"


def ensure_dirs(workspace: Path) -> tuple[Path, Path]:
    work_dir = protagonist_work_dir(workspace)
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


def infer_protagonist_name(workspace: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    final_card = first_existing(workspace, ["*-最终人物卡.md"])
    if final_card:
        return final_card.stem.removesuffix("-最终人物卡")
    index_file = first_existing(workspace, ["*-词条总索引.md"])
    if index_file:
        return index_file.stem.removesuffix("-词条总索引")
    focus_dir = first_existing(workspace, ["focus-*"])
    if focus_dir:
        return focus_dir.name.removeprefix("focus-")
    return "主角待定"


def context_candidates(workspace: Path, novel_name: str) -> list[tuple[str, Path, int]]:
    candidates: list[tuple[str, Path | None, int]] = [
        ("latest_status", latest_status_file(workspace), 2200),
        ("chapter_manifest", workspace / "chapter-distillation-manifest.json", 1800),
        ("stage_skeleton", workspace / f"{novel_name}-阶段骨架与换挡草图.md", 2600),
        ("calibration_anchors", workspace / f"{novel_name}-校准与验证锚点.md", 2400),
        ("chapter_skeleton", workspace / f"{novel_name}-章节蒸馏骨架.md", 5200),
        ("distill_section_0001", workspace / "work" / "chapter-distillation" / "sections" / "0001.md", 1200),
        ("distill_section_0002", workspace / "work" / "chapter-distillation" / "sections" / "0002.md", 1200),
        ("distill_section_0003", workspace / "work" / "chapter-distillation" / "sections" / "0003.md", 1200),
        ("opening_total", workspace / f"{novel_name}-黄金前三章总判断.md", 2200),
        ("opening_hook", workspace / f"{novel_name}-开篇钩子与读者承诺.md", 1800),
        ("outline_overview", workspace / f"{novel_name}-大纲总览.md", 2400),
        ("outline_stages", workspace / f"{novel_name}-阶段与篇章拆分.md", 2400),
        ("outline_lines", workspace / f"{novel_name}-主线支线与冲突地图.md", 2200),
        ("highlight_top10", workspace / f"{novel_name}-最吸引人的十个剧情细节总表.md", 2200),
        ("highlight_mechanism", workspace / f"{novel_name}-剧情吸引力机制分析.md", 2000),
        ("supporting_top10", workspace / f"{novel_name}-重要配角Top10总表.md", 2200),
        ("supporting_relations", workspace / f"{novel_name}-重要配角与主角关系图.md", 1800),
        ("merged_characters", workspace / "work" / "merged" / "characters.json", 2200),
        ("cards_index", workspace / "work" / "cards" / "index.md", 2200),
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
    protagonist_name: str,
    contexts: list[tuple[str, Path, int]],
    extra_contexts: list[tuple[Path, str]],
) -> str:
    context_sections = [
        f"### {label}: {path.name}\n{read_context_file(path, limit)}"
        for label, path, limit in contexts
    ]
    extra_sections = [f"### 额外上下文：{path.name}\n{text}" for path, text in extra_contexts]
    return "\n\n".join(
        [
            f"小说名：{novel_name}",
            f"目标主角：{protagonist_name}",
            "任务：构建主角百科层正式产物，稳定主角骨架、阶段成长、主干词条与体系闭环判断。",
            "注意：必须优先依赖章节蒸馏层和上游分析，不要把内容写成纯人物简介。",
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
        model_env_vars=("PROTAGONIST_ANALYSIS_MODEL",),
        fallback_model_env_vars=("PROTAGONIST_ANALYSIS_FALLBACK_MODELS",),
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


def normalize_list(value: Any, minimum: int = 3, prefix: str = "条目") -> list[str]:
    if not isinstance(value, list):
        value = [value] if value else []
    items = [sanitize_text(item) for item in value if sanitize_text(item)]
    while len(items) < minimum:
        items.append(f"{prefix}补充项 {len(items) + 1}")
    return items


def normalize_stage_block(data: dict[str, Any]) -> dict[str, str]:
    return {key: sanitize_text(data.get(key, "")) for key in STAGE_FIELDS}


def normalize_response(payload: dict[str, Any]) -> dict[str, Any]:
    meta_summary = payload.get("meta_summary", {}) if isinstance(payload.get("meta_summary"), dict) else {}
    return {
        "meta_summary": {
            "skeleton_judgement": sanitize_text(meta_summary.get("skeleton_judgement", "")),
            "system_judgement": sanitize_text(meta_summary.get("system_judgement", "")),
            "one_line_handoff": sanitize_text(meta_summary.get("one_line_handoff", "")),
        },
        "startup_checklist": {
            "当前已达到": normalize_list((payload.get("startup_checklist") or {}).get("当前已达到", []) if isinstance(payload.get("startup_checklist"), dict) else [], minimum=4, prefix="已达到"),
            "首轮执行顺序说明": sanitize_text((payload.get("startup_checklist") or {}).get("首轮执行顺序说明", "")) if isinstance(payload.get("startup_checklist"), dict) else sanitize_text(""),
        },
        "stage_outline": {
            "阶段_1": normalize_stage_block((payload.get("stage_outline") or {}).get("阶段_1", {}) if isinstance((payload.get("stage_outline") or {}).get("阶段_1", {}), dict) else {}),
            "阶段_2": normalize_stage_block((payload.get("stage_outline") or {}).get("阶段_2", {}) if isinstance((payload.get("stage_outline") or {}).get("阶段_2", {}), dict) else {}),
            "阶段_3": normalize_stage_block((payload.get("stage_outline") or {}).get("阶段_3", {}) if isinstance((payload.get("stage_outline") or {}).get("阶段_3", {}), dict) else {}),
            "阶段_4": normalize_stage_block((payload.get("stage_outline") or {}).get("阶段_4", {}) if isinstance((payload.get("stage_outline") or {}).get("阶段_4", {}), dict) else {}),
        },
        "anchor": normalize_section_map(payload.get("anchor", {}), ANCHOR_FIELDS) if isinstance(payload.get("anchor"), dict) else normalize_section_map({}, ANCHOR_FIELDS),
        "final_card": normalize_section_map(payload.get("final_card", {}), FINAL_CARD_FIELDS) if isinstance(payload.get("final_card"), dict) else normalize_section_map({}, FINAL_CARD_FIELDS),
        "index": {
            "人物核心词条": normalize_list((payload.get("index") or {}).get("人物核心词条", []) if isinstance(payload.get("index"), dict) else [], minimum=3, prefix="人物核心词条"),
            "力量体系词条": normalize_list((payload.get("index") or {}).get("力量体系词条", []) if isinstance(payload.get("index"), dict) else [], minimum=3, prefix="力量体系词条"),
            "世界与高位设定词条": normalize_list((payload.get("index") or {}).get("世界与高位设定词条", []) if isinstance(payload.get("index"), dict) else [], minimum=3, prefix="世界与高位设定词条"),
            "结构与关系网络词条": normalize_list((payload.get("index") or {}).get("结构与关系网络词条", []) if isinstance(payload.get("index"), dict) else [], minimum=3, prefix="结构关系词条"),
            "核心二级词条": normalize_list((payload.get("index") or {}).get("核心二级词条", []) if isinstance(payload.get("index"), dict) else [], minimum=4, prefix="核心二级词条"),
            "整体结构总结": sanitize_text((payload.get("index") or {}).get("整体结构总结", "")) if isinstance(payload.get("index"), dict) else sanitize_text(""),
            "骨架完成判断": sanitize_text((payload.get("index") or {}).get("骨架完成判断", "")) if isinstance(payload.get("index"), dict) else sanitize_text(""),
            "体系闭环判断": sanitize_text((payload.get("index") or {}).get("体系闭环判断", "")) if isinstance(payload.get("index"), dict) else sanitize_text(""),
            "推荐阅读顺序": normalize_list((payload.get("index") or {}).get("推荐阅读顺序", []) if isinstance(payload.get("index"), dict) else [], minimum=3, prefix="推荐阅读顺序"),
            "下一步执行顺序": normalize_list((payload.get("index") or {}).get("下一步执行顺序", []) if isinstance(payload.get("index"), dict) else [], minimum=3, prefix="下一步执行顺序"),
        },
        "core_overview": normalize_section_map(payload.get("core_overview", {}), CORE_OVERVIEW_FIELDS) if isinstance(payload.get("core_overview"), dict) else normalize_section_map({}, CORE_OVERVIEW_FIELDS),
        "essence_summary": normalize_section_map(payload.get("essence_summary", {}), ESSENCE_FIELDS) if isinstance(payload.get("essence_summary"), dict) else normalize_section_map({}, ESSENCE_FIELDS),
        "next_actions": normalize_list(payload.get("next_actions", []), minimum=3, prefix="下一步"),
    }


def write_file(path: Path, content: str, force: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        existing = path.read_text(encoding="utf-8", errors="ignore")
        if existing.strip() and "待补充" not in existing and "当前仅完成了主角百科工作区初始化" not in existing:
            return
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def render_stage_outline_md(novel_name: str, normalized: dict[str, Any]) -> str:
    lines = [f"# 《{novel_name}》整书粗阶段划分", "", "## 说明", "", "- 本文件由主角百科自动填充，用于稳定主角成长阶段与整书阶段映射。", "", "## 阶段模板", ""]
    for idx in (1, 2, 3, 4):
        stage = normalized["stage_outline"][f"阶段_{idx}"]
        lines.extend([f"### 阶段 {idx}", ""])
        for field in STAGE_FIELDS:
            lines.append(f"- {field}：{stage[field]}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_anchor_md(novel_name: str, protagonist_name: str, normalized: dict[str, Any]) -> str:
    data = normalized["anchor"]
    lines = [
        f"# 《{novel_name}》主角锚点与骨架",
        "",
        "## 说明",
        "",
        "本文件用于在正式拆主角人物卡和词条之前，先稳定确认主角锚点与主梁结构。",
        "",
        "## 主角锚点",
        "",
        f"- 本名：{data['本名']}",
        f"- 常见称谓：{data['常见称谓']}",
        f"- 化名 / 马甲：{data['化名 / 马甲']}",
        f"- 易混简称：{data['易混简称']}",
        f"- 关键关联名词：{data['关键关联名词']}",
        "",
        "## 当前确认依据",
        "",
        f"- 从 chunk 蒸馏结果看：{data['从 chunk 蒸馏结果看']}",
        f"- 从开篇与高光结果看：{data['从开篇与高光结果看']}",
        f"- 从阶段划分看：{data['从阶段划分看']}",
        "",
        "## 主角骨架",
        "",
        f"- {protagonist_name} 的主角骨架由身份底座、成长引擎、质变路线和高位结构四条主梁组成；因为这四条线分别回答他从哪里来、靠什么升级、如何换挡、最终要和什么秩序对抗，所以后续词条都应围着这四根主梁展开。",
        "",
        "## 身份底座",
        "",
        f"- {data['身份底座']}",
        "",
        "## 成长引擎",
        "",
        f"- {data['成长引擎']}",
        "",
        "## 质变路线",
        "",
        f"- {data['质变路线']}",
        "",
        "## 高位结构",
        "",
        f"- {data['高位结构']}",
        "",
        "## 当前最值得拆的一级词条",
        "",
        "- 身份变化",
        "- 核心能力 / 核心手艺 / 核心外挂",
        "- 战斗方式",
        "- 修行 / 等级 / 高位路线",
        "- 世界结构",
        "- 势力与局势卷入",
        "- 关系网",
        "- 地域轨迹",
        "",
    ]
    return "\n".join(lines)


def render_final_card_md(protagonist_name: str, normalized: dict[str, Any]) -> str:
    data = normalized["final_card"]
    lines = [f"# {protagonist_name}", ""]
    for field in FINAL_CARD_FIELDS:
        lines.extend([f"## {field}", "", f"- {data[field]}", ""])
    return "\n".join(lines).rstrip() + "\n"


def render_index_md(novel_name: str, protagonist_name: str, normalized: dict[str, Any]) -> str:
    data = normalized["index"]
    lines = [
        f"# {protagonist_name}词条总索引",
        "",
        "## 说明",
        "",
        "本索引用于汇总当前已经为主角建立的核心入口文件，并固定后续词条扩展方向。",
        "",
        "## 一、主人物卡",
        "",
        f"- [{protagonist_name}-最终人物卡.md]({protagonist_name}-最终人物卡.md)",
        "",
        "## 二、核心总览文件",
        "",
        f"- [{novel_name}-主角锚点与骨架.md]({novel_name}-主角锚点与骨架.md)",
        f"- [{novel_name}-整书粗阶段划分.md]({novel_name}-整书粗阶段划分.md)",
        f"- [{protagonist_name}-核心体系总览.md]({protagonist_name}-核心体系总览.md)",
        f"- [{novel_name}-全书精华总结.md]({novel_name}-全书精华总结.md)",
        "",
        "## 三、当前已完成的一级词条",
        "",
        "### 1. 人物核心词条",
        "",
        *[f"- {item}" for item in data["人物核心词条"]],
        "",
        "### 2. 力量体系词条",
        "",
        *[f"- {item}" for item in data["力量体系词条"]],
        "",
        "### 3. 世界与高位设定词条",
        "",
        *[f"- {item}" for item in data["世界与高位设定词条"]],
        "",
        "### 4. 结构与关系网络词条",
        "",
        *[f"- {item}" for item in data["结构与关系网络词条"]],
        "",
        "## 四、当前已完成的核心二级词条",
        "",
        *[f"- {item}" for item in data["核心二级词条"]],
        "",
        "## 五、当前整体结构总结",
        "",
        f"- {data['整体结构总结']}",
        "",
        "## 六、当前完成度判断",
        "",
        "### 当前判定：骨架完成",
        "",
        "- 当前判断：`骨架完成`",
        f"- 理由：{data['骨架完成判断']}",
        "",
        "### 当前判定：体系闭环完成",
        "",
        "- 当前判断：`体系闭环完成`",
        f"- 理由：{data['体系闭环判断']}",
        "",
        "## 七、推荐阅读顺序",
        "",
        *[f"- {item}" for item in data["推荐阅读顺序"]],
        "",
        "## 八、下一步执行顺序",
        "",
        *[f"{idx}. {item}" for idx, item in enumerate(data["下一步执行顺序"], start=1)],
        "",
    ]
    return "\n".join(lines)


def render_core_overview_md(protagonist_name: str, normalized: dict[str, Any]) -> str:
    data = normalized["core_overview"]
    lines = [f"# {protagonist_name}核心体系总览", ""]
    for field in CORE_OVERVIEW_FIELDS:
        lines.extend([f"## {field}", "", f"- {data[field]}", ""])
    return "\n".join(lines).rstrip() + "\n"


def render_essence_md(novel_name: str, normalized: dict[str, Any]) -> str:
    data = normalized["essence_summary"]
    lines = [f"# 《{novel_name}》全书精华总结", ""]
    for field in ESSENCE_FIELDS:
        lines.extend([f"## {field}", "", f"- {data[field]}", ""])
    return "\n".join(lines).rstrip() + "\n"


def render_status_md(novel_name: str, protagonist_name: str, normalized: dict[str, Any]) -> str:
    actions = normalized["next_actions"] or [
        "回看主角阶段划分是否和章节蒸馏层的主要换挡保持一致。",
        "检查主角索引中的一级词条与二级词条是否已经能覆盖后续深拆主线。",
        "核对全书精华总结是否真正解释了主角线为什么成立。",
    ]
    return "\n".join(
        [
            f"# 《{novel_name}》工作状态 {date.today().isoformat()}",
            "",
            "## 当前结论",
            "",
            f"- `主角骨架`：{normalized['meta_summary']['skeleton_judgement']}",
            f"- `体系闭环`：{normalized['meta_summary']['system_judgement']}",
            f"- `当前主角候选`：`{protagonist_name}`",
            "",
            "## 当前已经具备的文件骨架",
            "",
            "- 项目启动清单",
            "- 整书粗阶段划分",
            "- 主角锚点与骨架",
            "- 主角最终人物卡",
            "- 主角词条总索引",
            "- 主角核心体系总览",
            "- 全书精华总结",
            "",
            "## 当前不应误判为已完成的部分",
            "",
            "- 不应把人物简介误判成主角骨架闭环。",
            "- 不应让主角层脱离章节蒸馏层和大纲层单独成立。",
            "- 不应只有总卡，没有词条总索引与体系解释。",
            "",
            "## 下一步建议",
            "",
            *[f"{idx}. {item}" for idx, item in enumerate(actions[:5], start=1)],
            "",
            "## 一句话交接",
            "",
            normalized["meta_summary"]["one_line_handoff"],
            "",
        ]
    )


def render_checklist_md(novel_name: str, normalized: dict[str, Any]) -> str:
    reached = normalized["startup_checklist"]["当前已达到"]
    lines = [
        f"# {novel_name} 项目启动清单",
        "",
        "## 目标",
        "",
        f"将《{novel_name}》建立为一套以主角为中心的全词条百科资料，而不是平铺式人物索引。",
        "",
        "## 体系闭环 Checklist",
        "",
        "- [x] 整书 chunk 蒸馏已完成",
        "- [x] 整书阶段划分已完成",
        "- [x] 主角锚点已稳定",
        "- [x] 主角总卡已完成",
        "- [x] 一级词条已齐",
        "- [x] 总索引已完成",
        "- [x] 核心体系总览已完成",
        "- [x] 全书精华总结已完成",
        "- [ ] 最关键的一批二级词条已完成",
        "- [x] 索引中已区分一级、二级和当前完成度",
        "- [x] 现有词条之间已能互相解释",
        "",
        "## 当前已达到",
        "",
        *[f"- {item}" for item in reached],
        "",
        "## 首轮执行顺序",
        "",
        "1. 确认原文文件与工作区路径",
        "2. 完成 txt -> md 转换",
        "3. 完成 chunk 蒸馏与基础抽取",
        "4. 产出整书粗阶段划分",
        "5. 确认主角锚点",
        "6. 写主角锚点与骨架",
        "7. 写主角最终人物卡",
        "8. 提炼一级词条并建立总索引",
        "9. 判断是否达到“骨架完成”",
        "10. 写核心体系总览",
        "11. 写全书精华总结",
        "12. 补关键二级词条并判断是否达到“体系闭环完成”",
        "",
        "## 首轮执行顺序说明",
        "",
        f"- {normalized['startup_checklist']['首轮执行顺序说明']}",
        "",
    ]
    return "\n".join(lines)


def persist_outputs(workspace: Path, novel_name: str, protagonist_name: str, normalized: dict[str, Any], force: bool) -> list[str]:
    written: list[str] = []
    checklist_path = workspace / f"{novel_name}-项目启动清单.md"
    write_file(checklist_path, render_checklist_md(novel_name, normalized), force)
    written.append(str(checklist_path))

    stage_outline_path = workspace / f"{novel_name}-整书粗阶段划分.md"
    write_file(stage_outline_path, render_stage_outline_md(novel_name, normalized), force)
    written.append(str(stage_outline_path))

    anchor_path = workspace / f"{novel_name}-主角锚点与骨架.md"
    write_file(anchor_path, render_anchor_md(novel_name, protagonist_name, normalized), force)
    written.append(str(anchor_path))

    final_card_path = workspace / f"{protagonist_name}-最终人物卡.md"
    write_file(final_card_path, render_final_card_md(protagonist_name, normalized), force)
    written.append(str(final_card_path))

    index_path = workspace / f"{protagonist_name}-词条总索引.md"
    write_file(index_path, render_index_md(novel_name, protagonist_name, normalized), force)
    written.append(str(index_path))

    core_path = workspace / f"{protagonist_name}-核心体系总览.md"
    write_file(core_path, render_core_overview_md(protagonist_name, normalized), force)
    written.append(str(core_path))

    essence_path = workspace / f"{novel_name}-全书精华总结.md"
    write_file(essence_path, render_essence_md(novel_name, normalized), force)
    written.append(str(essence_path))

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
    protagonist_name = infer_protagonist_name(workspace, args.protagonist)

    contexts = context_candidates(workspace, args.novel_name)
    extra_contexts: list[tuple[Path, str]] = []
    for raw_path in args.context_file:
        path = Path(raw_path).expanduser().resolve()
        if path.exists():
            extra_contexts.append((path, read_context_file(path)))

    prompt = build_prompt(args.novel_name, protagonist_name, contexts, extra_contexts)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    prompt_path = attempts_dir / f"{stamp}-{args.attempt_label}-prompt.md"
    prompt_path.write_text(prompt.rstrip() + "\n", encoding="utf-8")

    debug_response_file = args.response_file or os.environ.get("PROTAGONIST_ANALYSIS_RESPONSE_FILE", "").strip()
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

    written = persist_outputs(workspace, args.novel_name, protagonist_name, normalized, args.force)
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
