#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import requests

SYSTEM_PROMPT = """你是资深网文编辑，任务是为“剧情高光层”生成可直接落盘的正式分析文档。

要求：
1. 只输出 JSON，不要输出 markdown，不要加前言。
2. 高光筛选必须优先参考章节蒸馏层、阶段骨架和大纲层，不要只凭零散印象。
3. Top10 必须覆盖整书，不要把前段连续三四个近似桥段都塞进榜单。
4. 每个高光都要说明：事件是什么、打中什么快感、为什么成立、改变了什么。
5. 语言必须具体，引用角色名、势力名、阶段名、事件节点，避免“很精彩/很爽”这种空话。
6. 修改建议必须可执行，明确“前移/后移/压缩/补强/合并”的对象。

返回 JSON 结构：
{
  "meta_summary": {
    "highlight_judgement": "一句话",
    "mechanism_judgement": "一句话",
    "one_line_handoff": "一句话交接"
  },
  "top10_table": {
    "总判断": "100-220字",
    "highlights": [
      {
        "rank": 1,
        "label": "高光细节 1",
        "事件本身": "60-140字",
        "所在阶段": "60-140字",
        "吸引力类型": "60-140字",
        "主要作用": "60-140字"
      }
    ]
  },
  "mechanism": {
    "核心判断": "100-220字",
    "1. 反差": "80-180字",
    "2. 悬念": "80-180字",
    "3. 情绪兑现": "80-180字",
    "4. 身份翻转 / 局势翻转": "80-180字",
    "5. 世界揭露 / 规则揭露": "80-180字",
    "机制换挡点": "80-180字"
  },
  "top10_breakdown": [
    {
      "rank": 1,
      "发生位置": "60-140字",
      "事件本身": "60-140字",
      "前置铺垫": "60-140字",
      "吸引力为什么成立": "80-180字",
      "打中的读者快感": "60-140字",
      "改变了什么": "60-140字",
      "是否属于可复述型名场面": "60-140字"
    }
  ],
  "distribution": {
    "高光分布总判断": "100-220字",
    "前段高光": "80-180字",
    "中段高光": "80-180字",
    "后段高光": "80-180字",
    "节奏判断": "80-180字"
  },
  "pleasure_summary": {
    "最强爽点": "80-180字",
    "最强痛点": "80-180字",
    "最强悬念点": "80-180字",
    "综合判断": "80-180字"
  },
  "revision": {
    "当前最强高光": "80-180字",
    "当前最弱区段": "80-180字",
    "应该补强什么": "80-180字",
    "应该前移或后移什么": "80-180字",
    "应该压缩或合并什么": "80-180字"
  },
  "next_actions": [
    "一句具体下一步",
    "一句具体下一步",
    "一句具体下一步"
  ]
}
"""

TOP10_HEAD = "总判断"
TOP10_FIELDS = ["事件本身", "所在阶段", "吸引力类型", "主要作用"]
MECHANISM_FIELDS = [
    "核心判断",
    "1. 反差",
    "2. 悬念",
    "3. 情绪兑现",
    "4. 身份翻转 / 局势翻转",
    "5. 世界揭露 / 规则揭露",
    "机制换挡点",
]
BREAKDOWN_FIELDS = [
    "发生位置",
    "事件本身",
    "前置铺垫",
    "吸引力为什么成立",
    "打中的读者快感",
    "改变了什么",
    "是否属于可复述型名场面",
]
DISTRIBUTION_FIELDS = ["高光分布总判断", "前段高光", "中段高光", "后段高光", "节奏判断"]
PLEASURE_FIELDS = ["最强爽点", "最强痛点", "最强悬念点", "综合判断"]
REVISION_FIELDS = ["当前最强高光", "当前最弱区段", "应该补强什么", "应该前移或后移什么", "应该压缩或合并什么"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auto-fill the highlight analysis layer from distilled and upper-layer context.")
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


def highlight_work_dir(workspace: Path) -> Path:
    return workspace / "work" / "highlight-analysis"


def ensure_dirs(workspace: Path) -> tuple[Path, Path]:
    work_dir = highlight_work_dir(workspace)
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


def context_candidates(workspace: Path, novel_name: str) -> list[tuple[str, Path, int]]:
    candidates: list[tuple[str, Path, int]] = [
        ("latest_status", latest_status_file(workspace), 2200),
        ("chapter_manifest", workspace / "chapter-distillation-manifest.json", 1800),
        ("chapter_skeleton", workspace / f"{novel_name}-章节蒸馏骨架.md", 5000),
        ("stage_skeleton", workspace / f"{novel_name}-阶段骨架与换挡草图.md", 2600),
        ("calibration_anchors", workspace / f"{novel_name}-校准与验证锚点.md", 2200),
        ("distill_section_0001", workspace / "work" / "chapter-distillation" / "sections" / "0001.md", 1200),
        ("distill_section_0002", workspace / "work" / "chapter-distillation" / "sections" / "0002.md", 1200),
        ("distill_section_0003", workspace / "work" / "chapter-distillation" / "sections" / "0003.md", 1200),
        ("opening_total", workspace / f"{novel_name}-黄金前三章总判断.md", 2200),
        ("opening_hook", workspace / f"{novel_name}-开篇钩子与读者承诺.md", 1800),
        ("protagonist_anchor", workspace / f"{novel_name}-主角锚点与骨架.md", 2600),
        ("protagonist_index", next(iter(sorted(workspace.glob("*-词条总索引.md"))), None), 2200),
        ("protagonist_card", next(iter(sorted(workspace.glob("*-最终人物卡.md"))), None), 2200),
        ("core_overview", next(iter(sorted(workspace.glob("*-核心体系总览.md"))), None), 2200),
        ("outline_overview", workspace / f"{novel_name}-大纲总览.md", 2400),
        ("outline_stages", workspace / f"{novel_name}-阶段与篇章拆分.md", 2400),
        ("outline_lines", workspace / f"{novel_name}-主线支线与冲突地图.md", 2200),
        ("outline_conflicts", workspace / f"{novel_name}-核心冲突点与爆发点.md", 2200),
        ("supporting_top10", workspace / f"{novel_name}-重要配角Top10总表.md", 2000),
        ("supporting_relations", workspace / f"{novel_name}-重要配角与主角关系图.md", 1800),
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
            protagonist_line + "任务：构建剧情高光层正式产物，筛出全书 Top 10 高光并解释它们为什么成立。",
            "注意：必须优先依赖章节蒸馏层和阶段骨架来做全书扫描，再结合 opening / protagonist / outline / supporting-cast 做筛选和解释。",
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
    model = os.environ.get("HIGHLIGHT_ANALYSIS_MODEL", "deepseek-chat").strip() or "deepseek-chat"
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
            "max_tokens": 5000,
        },
        timeout=300,
    )
    response.raise_for_status()
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    return {"raw_api": payload, "content": content}


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


def normalize_top10_items(items: Any) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    if not isinstance(items, list):
        items = []
    for rank in range(1, 11):
        source = next(
            (
                item for item in items
                if isinstance(item, dict) and str(item.get("rank", "")).strip() == str(rank)
            ),
            {},
        )
        row = {"label": f"高光细节 {rank}"}
        for key in TOP10_FIELDS:
            row[key] = sanitize_text(source.get(key, ""))
        normalized.append(row)
    return normalized


def normalize_breakdowns(items: Any) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    if not isinstance(items, list):
        items = []
    for rank in range(1, 11):
        source = next(
            (
                item for item in items
                if isinstance(item, dict) and str(item.get("rank", "")).strip() == str(rank)
            ),
            {},
        )
        row = {}
        for key in BREAKDOWN_FIELDS:
            row[key] = sanitize_text(source.get(key, ""))
        normalized.append(row)
    return normalized


def normalize_response(payload: dict[str, Any]) -> dict[str, Any]:
    meta_summary = payload.get("meta_summary", {}) if isinstance(payload.get("meta_summary"), dict) else {}
    top10_payload = payload.get("top10_table", {}) if isinstance(payload.get("top10_table"), dict) else {}
    next_actions = payload.get("next_actions", [])
    if not isinstance(next_actions, list):
        next_actions = [str(next_actions)]
    return {
        "meta_summary": {
            "highlight_judgement": sanitize_text(meta_summary.get("highlight_judgement", "")),
            "mechanism_judgement": sanitize_text(meta_summary.get("mechanism_judgement", "")),
            "one_line_handoff": sanitize_text(meta_summary.get("one_line_handoff", "")),
        },
        "top10_table": {
            TOP10_HEAD: sanitize_text(top10_payload.get(TOP10_HEAD, "")),
            "highlights": normalize_top10_items(top10_payload.get("highlights", [])),
        },
        "mechanism": normalize_section_map(payload.get("mechanism", {}), MECHANISM_FIELDS)
        if isinstance(payload.get("mechanism"), dict)
        else normalize_section_map({}, MECHANISM_FIELDS),
        "top10_breakdown": normalize_breakdowns(payload.get("top10_breakdown", [])),
        "distribution": normalize_section_map(payload.get("distribution", {}), DISTRIBUTION_FIELDS)
        if isinstance(payload.get("distribution"), dict)
        else normalize_section_map({}, DISTRIBUTION_FIELDS),
        "pleasure_summary": normalize_section_map(payload.get("pleasure_summary", {}), PLEASURE_FIELDS)
        if isinstance(payload.get("pleasure_summary"), dict)
        else normalize_section_map({}, PLEASURE_FIELDS),
        "revision": normalize_section_map(payload.get("revision", {}), REVISION_FIELDS)
        if isinstance(payload.get("revision"), dict)
        else normalize_section_map({}, REVISION_FIELDS),
        "next_actions": [sanitize_text(item) for item in next_actions[:5] if sanitize_text(item)],
    }


def write_file(path: Path, content: str, force: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        existing = path.read_text(encoding="utf-8", errors="ignore")
        if existing.strip() and "待补充" not in existing and "当前仅完成了剧情高光分析工作区初始化" not in existing:
            return
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def render_section_markdown(title: str, sections: dict[str, str]) -> str:
    lines = [title, ""]
    for header, body in sections.items():
        lines.extend([f"## {header}", "", f"- {body}", ""])
    return "\n".join(lines).rstrip() + "\n"


def render_top10_markdown(novel_name: str, normalized: dict[str, Any]) -> str:
    lines = [f"# 《{novel_name}》最吸引人的十个剧情细节总表", "", "## 总判断", "", f"- {normalized['top10_table'][TOP10_HEAD]}", "", "## Top 10 总表", ""]
    for idx, item in enumerate(normalized["top10_table"]["highlights"], start=1):
        lines.extend([f"### 高光细节 {idx}", ""])
        for field in TOP10_FIELDS:
            lines.append(f"- {field}：{item[field]}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_breakdown_markdown(novel_name: str, normalized: dict[str, Any]) -> str:
    lines = [f"# 《{novel_name}》Top10细节逐条拆解", ""]
    for idx, item in enumerate(normalized["top10_breakdown"], start=1):
        lines.extend([f"## 细节 {idx}", ""])
        for field in BREAKDOWN_FIELDS:
            lines.append(f"- {field}：{item[field]}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_status_md(novel_name: str, normalized: dict[str, Any]) -> str:
    actions = normalized["next_actions"] or [
        "回看 Top10 是否已经覆盖前中后段，而不是只集中在一小段。",
        "检查剧情吸引力机制分析是否真的解释了高光为何成立，而不是只列出名场面。",
        "检查剧情高光改造建议是否已经指向具体区段和具体操作。",
    ]
    return "\n".join(
        [
            f"# 《{novel_name}》工作状态 {date.today().isoformat()}",
            "",
            "## 当前结论",
            "",
            f"- `高光桥段`：{normalized['meta_summary']['highlight_judgement']}",
            f"- `剧情吸引力机制`：{normalized['meta_summary']['mechanism_judgement']}",
            f"- `高光改造优先级`：{normalized['revision']['应该补强什么']}",
            "",
            "## 当前不应误判为已完成的部分",
            "",
            "- 不应把记忆点名单误判成高光机制分析。",
            "- 不应让 Top10 完全脱离阶段骨架和章节蒸馏层。",
            "- 不应只看爽点，而忽略痛点、悬念点和高光分布节奏。",
            "",
            "## 当前应如何继续",
            "",
            *[f"{idx}. {item}" for idx, item in enumerate(actions[:5], start=1)],
            "",
            "## 下次开始时建议先看",
            "",
            "1. `README.md`",
            f"2. `{novel_name}-最吸引人的十个剧情细节总表.md`",
            f"3. `{novel_name}-剧情吸引力机制分析.md`",
            f"4. `{novel_name}-剧情高光改造建议.md`",
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
    top10_path = workspace / f"{novel_name}-最吸引人的十个剧情细节总表.md"
    write_file(top10_path, render_top10_markdown(novel_name, normalized), force)
    written.append(str(top10_path))

    mechanism_path = workspace / f"{novel_name}-剧情吸引力机制分析.md"
    write_file(mechanism_path, render_section_markdown(f"# 《{novel_name}》剧情吸引力机制分析", normalized["mechanism"]), force)
    written.append(str(mechanism_path))

    breakdown_path = workspace / f"{novel_name}-Top10细节逐条拆解.md"
    write_file(breakdown_path, render_breakdown_markdown(novel_name, normalized), force)
    written.append(str(breakdown_path))

    distribution_path = workspace / f"{novel_name}-高光桥段分布与节奏判断.md"
    write_file(distribution_path, render_section_markdown(f"# 《{novel_name}》高光桥段分布与节奏判断", normalized["distribution"]), force)
    written.append(str(distribution_path))

    pleasure_path = workspace / f"{novel_name}-最强爽点痛点悬念点总结.md"
    write_file(pleasure_path, render_section_markdown(f"# 《{novel_name}》最强爽点痛点悬念点总结", normalized["pleasure_summary"]), force)
    written.append(str(pleasure_path))

    revision_path = workspace / f"{novel_name}-剧情高光改造建议.md"
    write_file(revision_path, render_section_markdown(f"# 《{novel_name}》剧情高光改造建议", normalized["revision"]), force)
    written.append(str(revision_path))

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

    debug_response_file = args.response_file or os.environ.get("HIGHLIGHT_ANALYSIS_RESPONSE_FILE", "").strip()
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
