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

TEXT_ENCODINGS = ("utf-8", "utf-8-sig", "gb18030", "gbk")
SHARED_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "novel-workspace-orchestrator-skill" / "scripts"
if str(SHARED_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS_DIR))
from shared_api_client import call_chat_completion

CHAPTER_PATTERNS = [
    re.compile(r"^## 第([0-9]+)章\s*(.*)"),
    re.compile(r"^正文 第(.+?)章\s*(.*)"),
    re.compile(r"^## 第(.+?)章\s*(.*)"),
    re.compile(r"^第([0-9]+)章\s*(.*)"),
    re.compile(r"^第?([0-9]+)[章节卷集部]\s*(.*)"),
    re.compile(r"^(?:##\s*)?([0-9]{1,4})\s*$"),
    re.compile(r"^(?:##\s*)?([0-9]{1,4})[-\s:：、.]+(.*)$"),
    re.compile(r"^(?:chapter|Chapter)\s+([0-9]+)\s*(.*)$"),
]
SYSTEM_PROMPT = """你是经验很强的网络小说开篇诊断编辑。

你的任务不是复述剧情，而是为“黄金前三章层”生成可直接交付的分析文档。

硬性要求：
1. 只输出 JSON，不要输出 markdown，不要加前言。
2. 必须优先利用“章节蒸馏层”和“阶段骨架”作为导航，再回到前三章原文核对。
3. 每个字段都要写成可落盘结论，不能写待补充、待确认、可能、大概。
4. 必须大量引用具体角色名、事件、设定、压力点。
5. 必须体现因果推理，多用“因为 / 所以 / 导致 / 触发 / 因此 / 进而”。
6. 修改建议必须具体到章节位置和操作动作，例如“把 X 前移到第1章结尾”“删掉 Y 段解释，改成冲突中带出”。

返回 JSON 结构：
{
  "meta_summary": {
    "opening_judgement": "一句话",
    "structure_judgement": "一句话",
    "one_line_handoff": "一句话交接"
  },
  "total_judgment": {
    "开篇钩子结论": "80-180字",
    "主角亮相结论": "80-180字",
    "冲突启动结论": "80-180字",
    "前三章结构结论": "80-180字",
    "继续阅读驱动力结论": "80-180字"
  },
  "chapter_breakdowns": [
    {
      "chapter_no": 1,
      "本章在开篇结构中的作用": "80-180字",
      "钩子 / 压力点": "80-180字",
      "主角状态与目标": "80-180字",
      "信息释放与世界观投喂": "80-180字",
      "结尾拉力": "80-180字",
      "这一章最该强化或删减的地方": "80-180字"
    },
    {
      "chapter_no": 2,
      "本章在开篇结构中的作用": "80-180字",
      "钩子 / 压力点": "80-180字",
      "主角状态与目标": "80-180字",
      "信息释放与世界观投喂": "80-180字",
      "结尾拉力": "80-180字",
      "这一章最该强化或删减的地方": "80-180字"
    },
    {
      "chapter_no": 3,
      "本章在开篇结构中的作用": "80-180字",
      "钩子 / 压力点": "80-180字",
      "主角状态与目标": "80-180字",
      "信息释放与世界观投喂": "80-180字",
      "结尾拉力": "80-180字",
      "这一章最该强化或删减的地方": "80-180字"
    }
  ],
  "hook_promise": {
    "立即钩子": "80-180字",
    "题材承诺": "80-180字",
    "主角承诺": "80-180字",
    "情绪 / 悬念承诺": "80-180字",
    "三章内的结尾拉力模式": "80-180字"
  },
  "issues_revision": {
    "最强的地方": "80-180字",
    "最弱的地方": "80-180字",
    "分章问题": "80-180字",
    "第一优先修改项": "80-180字",
    "轻修建议": "80-180字"
  },
  "next_actions": [
    "一句具体下一步",
    "一句具体下一步",
    "一句具体下一步"
  ]
}
"""

TOTAL_SECTIONS = [
    "开篇钩子结论",
    "主角亮相结论",
    "冲突启动结论",
    "前三章结构结论",
    "继续阅读驱动力结论",
]
CHAPTER_SECTIONS = [
    "本章在开篇结构中的作用",
    "钩子 / 压力点",
    "主角状态与目标",
    "信息释放与世界观投喂",
    "结尾拉力",
    "这一章最该强化或删减的地方",
]
HOOK_SECTIONS = [
    "立即钩子",
    "题材承诺",
    "主角承诺",
    "情绪 / 悬念承诺",
    "三章内的结尾拉力模式",
]
ISSUE_SECTIONS = [
    "最强的地方",
    "最弱的地方",
    "分章问题",
    "第一优先修改项",
    "轻修建议",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auto-fill the opening analysis layer from source and distillation context.")
    parser.add_argument("--workspace", required=True, help="Workspace directory.")
    parser.add_argument("--novel-name", required=True, help="Novel name used in file naming.")
    parser.add_argument("--source", help="Optional source file override.")
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


def strict_decode_text(path: Path) -> tuple[str, str]:
    for encoding in TEXT_ENCODINGS:
        try:
            return path.read_text(encoding=encoding), encoding
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"unable to decode source: {path}")


def detect_source_file(workspace: Path, override: str | None) -> Path:
    if override:
        source = Path(override).expanduser().resolve()
        if not source.exists():
            raise SystemExit(f"source not found: {source}")
        return source
    source_dir = workspace / "source"
    if not source_dir.exists():
        raise SystemExit(f"source directory not found: {source_dir}")
    candidates: list[Path] = []
    for suffix in (".md", ".txt"):
        candidates.extend(sorted(source_dir.glob(f"*{suffix}")))
    if not candidates:
        raise SystemExit(f"unable to find source file under: {source_dir}")
    suffix_priority = {".md": 0, ".txt": 1}
    return sorted(candidates, key=lambda path: (suffix_priority.get(path.suffix.lower(), 9), path.name))[0]


def _split_by_pattern(lines: list[str], pattern: re.Pattern[str]) -> list[dict[str, Any]]:
    chapters: list[dict[str, Any]] = []
    cur_title = ""
    cur_lines: list[str] = []
    start_line = 1
    in_chapter = False
    for line_no, line in enumerate(lines, start=1):
        matched = pattern.match(line.strip())
        if matched:
            if in_chapter:
                chapters.append(
                    {
                        "index": len(chapters) + 1,
                        "title": cur_title,
                        "body": "".join(cur_lines),
                        "start_line": start_line,
                        "end_line": line_no - 1,
                    }
                )
            cur_title = line.strip().lstrip("#").strip()
            cur_lines = []
            start_line = line_no
            in_chapter = True
        elif in_chapter:
            cur_lines.append(line)
    if in_chapter:
        chapters.append(
            {
                "index": len(chapters) + 1,
                "title": cur_title,
                "body": "".join(cur_lines),
                "start_line": start_line,
                "end_line": len(lines),
            }
        )
    return chapters


def read_chapters(source_path: Path) -> tuple[list[dict[str, Any]], str]:
    text, encoding = strict_decode_text(source_path)
    lines = text.splitlines(keepends=True)
    best: list[dict[str, Any]] = []
    for pattern in CHAPTER_PATTERNS:
        chapters = _split_by_pattern(lines, pattern)
        if len(chapters) >= 3:
            return chapters, encoding
        if len(chapters) > len(best):
            best = chapters
    return best, encoding


def chapter_parse_guard(source_path: Path, chapters: list[dict[str, Any]]) -> str | None:
    if len(chapters) >= 3:
        if source_path.stat().st_size < 120_000 or len(chapters) >= 6:
            return None
    if not chapters:
        return "未检测到足够章节，请检查源文件格式"
    return (
        f"前三章解析失败：当前只识别到 {len(chapters)} 章。"
        "请检查源文是否使用裸数字章节、英文 Chapter 标题或其他未覆盖格式。"
    )


def latest_status_file(workspace: Path) -> Path | None:
    candidates = sorted(workspace.glob("工作状态-*.md"))
    return candidates[-1] if candidates else None


def opening_work_dir(workspace: Path) -> Path:
    return workspace / "work" / "opening-analysis"


def ensure_dirs(workspace: Path) -> tuple[Path, Path]:
    work_dir = opening_work_dir(workspace)
    attempts_dir = work_dir / "attempts"
    attempts_dir.mkdir(parents=True, exist_ok=True)
    return work_dir, attempts_dir


def trim(text: str, limit: int) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "\n...[truncated]"


def read_context_file(path: Path, limit: int = 2400) -> str:
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return trim(read_text(path), limit)
        return trim(json.dumps(payload, ensure_ascii=False, indent=2), limit)
    return trim(read_text(path), limit)


def read_distillation_context(workspace: Path, novel_name: str) -> str:
    parts: list[str] = []
    section_dir = workspace / "work" / "chapter-distillation" / "sections"
    if section_dir.exists():
        for idx in range(1, 4):
            path = section_dir / f"{idx:04d}.md"
            if path.exists():
                parts.append(f"### 蒸馏层第{idx}章\n{trim(read_text(path), 1800)}")
    stage_path = workspace / f"{novel_name}-阶段骨架与换挡草图.md"
    if stage_path.exists():
        parts.append(f"### 阶段骨架\n{trim(read_text(stage_path), 2200)}")
    anchor_path = workspace / f"{novel_name}-校准与验证锚点.md"
    if anchor_path.exists():
        parts.append(f"### 校准锚点\n{trim(read_text(anchor_path), 2000)}")
    skeleton_path = workspace / f"{novel_name}-章节蒸馏骨架.md"
    if not parts and skeleton_path.exists():
        parts.append(f"### 章节蒸馏骨架（节选）\n{trim(read_text(skeleton_path), 3200)}")
    return "\n\n".join(parts)


def build_prompt(
    novel_name: str,
    protagonist: str | None,
    chapters: list[dict[str, Any]],
    source_path: Path,
    encoding: str,
    distillation_context: str,
    extra_contexts: list[tuple[Path, str]],
) -> str:
    chapter_blocks: list[str] = []
    for chapter in chapters[:3]:
        chapter_blocks.append(
            "\n".join(
                [
                    f"## 源文第{chapter['index']}章：{chapter['title']}",
                    f"- 源文件行号：{chapter['start_line']}-{chapter['end_line']}",
                    trim(chapter["body"], 7000),
                ]
            )
        )
    protagonist_line = f"- 主角名（如已知）：{protagonist}\n" if protagonist else ""
    extra_sections = []
    for path, text in extra_contexts:
        extra_sections.append(f"### 额外上下文：{path.name}\n{text}")
    return "\n\n".join(
        [
            f"小说名：{novel_name}",
            protagonist_line + f"- 源文件：{source_path.name}\n- 编码：{encoding}",
            "任务：基于前三章原文做 opening 层正式分析，并强绑定章节蒸馏层的导航信息。",
            "要求：结论必须具体，必须引用角色名、事件名、压力点和因果逻辑；不要只写剧情摘要。",
            "## 章节蒸馏与校准上下文",
            distillation_context or "（当前没有可复用的蒸馏上下文，只能直接依赖前三章原文。）",
            "## 前三章原文",
            "\n\n".join(chapter_blocks),
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
        model_env_vars=("OPENING_ANALYSIS_MODEL",),
        fallback_model_env_vars=("OPENING_ANALYSIS_FALLBACK_MODELS",),
        default_model="deepseek-chat",
        response_format={"type": "json_object"},
        temperature=0.35,
        max_tokens=4000,
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
    normalized: dict[str, str] = {}
    for key in keys:
        normalized[key] = sanitize_text(data.get(key, ""))
    return normalized


def normalize_response(payload: dict[str, Any]) -> dict[str, Any]:
    chapter_items = payload.get("chapter_breakdowns", [])
    chapter_map: dict[int, dict[str, str]] = {}
    if isinstance(chapter_items, list):
        for item in chapter_items:
            if not isinstance(item, dict):
                continue
            try:
                chapter_no = int(item.get("chapter_no"))
            except (TypeError, ValueError):
                continue
            chapter_map[chapter_no] = normalize_section_map(item, CHAPTER_SECTIONS)
    meta_summary = payload.get("meta_summary", {}) if isinstance(payload.get("meta_summary"), dict) else {}
    next_actions = payload.get("next_actions", [])
    if not isinstance(next_actions, list):
        next_actions = [str(next_actions)]
    return {
        "meta_summary": {
            "opening_judgement": sanitize_text(meta_summary.get("opening_judgement", "")),
            "structure_judgement": sanitize_text(meta_summary.get("structure_judgement", "")),
            "one_line_handoff": sanitize_text(meta_summary.get("one_line_handoff", "")),
        },
        "total_judgment": normalize_section_map(payload.get("total_judgment", {}), TOTAL_SECTIONS)
        if isinstance(payload.get("total_judgment"), dict)
        else normalize_section_map({}, TOTAL_SECTIONS),
        "chapter_breakdowns": {
            chapter_no: chapter_map.get(chapter_no, normalize_section_map({}, CHAPTER_SECTIONS))
            for chapter_no in (1, 2, 3)
        },
        "hook_promise": normalize_section_map(payload.get("hook_promise", {}), HOOK_SECTIONS)
        if isinstance(payload.get("hook_promise"), dict)
        else normalize_section_map({}, HOOK_SECTIONS),
        "issues_revision": normalize_section_map(payload.get("issues_revision", {}), ISSUE_SECTIONS)
        if isinstance(payload.get("issues_revision"), dict)
        else normalize_section_map({}, ISSUE_SECTIONS),
        "next_actions": [sanitize_text(item) for item in next_actions[:5] if sanitize_text(item)],
    }


def write_file(path: Path, content: str, force: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        existing = path.read_text(encoding="utf-8", errors="ignore")
        if existing.strip() and "待补充" not in existing and "当前仅完成了黄金前三章分析工作区初始化" not in existing:
            return
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def render_markdown(title: str, sections: dict[str, str]) -> str:
    lines = [title, ""]
    for header, body in sections.items():
        lines.extend([f"## {header}", "", f"- {body}", ""])
    return "\n".join(lines).rstrip() + "\n"


def render_status_md(novel_name: str, normalized: dict[str, Any]) -> str:
    actions = normalized["next_actions"] or [
        "回看前三章是否已经把核心冲突和继续阅读驱动力真正立住。",
        "核对开篇问题与修改建议是否已经能直接指导改稿。",
        "确认蒸馏层、opening 层对前三章的判断没有出现明显冲突。",
    ]
    return "\n".join(
        [
            f"# 《{novel_name}》工作状态 {date.today().isoformat()}",
            "",
            "## 当前结论",
            "",
            f"- `开篇抓力`：{normalized['meta_summary']['opening_judgement']}",
            f"- `前三章结构`：{normalized['meta_summary']['structure_judgement']}",
            f"- `修改优先级`：{normalized['issues_revision']['第一优先修改项']}",
            "",
            "## 当前不应误判为已完成的部分",
            "",
            "- 不应把前三章的剧情复述误判成结构判断。",
            "- 不应只看总判断文件，而忽略三章拆解与修改建议是否互相支撑。",
            "- 不应让 opening 层结论脱离章节蒸馏层的前3章骨架。",
            "",
            "## 当前应如何继续",
            "",
            *[f"{idx}. {item}" for idx, item in enumerate(actions[:5], start=1)],
            "",
            "## 下次开始时建议先看",
            "",
            "1. `README.md`",
            f"2. `{novel_name}-黄金前三章总判断.md`",
            f"3. `{novel_name}-开篇问题与修改建议.md`",
            "4. 本文件",
            "",
            "## 一句话交接",
            "",
            normalized["meta_summary"]["one_line_handoff"],
            "",
        ]
    )


def persist_outputs(workspace: Path, novel_name: str, normalized: dict[str, Any], force: bool) -> list[str]:
    written: list[str] = []
    total_path = workspace / f"{novel_name}-黄金前三章总判断.md"
    write_file(total_path, render_markdown(f"# 《{novel_name}》黄金前三章总判断", normalized["total_judgment"]), force)
    written.append(str(total_path))

    chapter_name_map = {1: "第一章", 2: "第二章", 3: "第三章"}
    for chapter_no in (1, 2, 3):
        title = f"# 《{novel_name}》第{chapter_no}章拆解"
        content = render_markdown(title, normalized["chapter_breakdowns"][chapter_no])
        chapter_path_cn = workspace / f"{novel_name}-{chapter_name_map[chapter_no]}拆解.md"
        chapter_path_num = workspace / f"{novel_name}-第{chapter_no}章拆解.md"
        write_file(chapter_path_cn, content, force)
        write_file(chapter_path_num, content, force)
        written.extend([str(chapter_path_cn), str(chapter_path_num)])

    hook_path = workspace / f"{novel_name}-开篇钩子与读者承诺.md"
    write_file(hook_path, render_markdown(f"# 《{novel_name}》开篇钩子与读者承诺", normalized["hook_promise"]), force)
    written.append(str(hook_path))

    issues_path = workspace / f"{novel_name}-开篇问题与修改建议.md"
    write_file(issues_path, render_markdown(f"# 《{novel_name}》开篇问题与修改建议", normalized["issues_revision"]), force)
    written.append(str(issues_path))

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
    source_path = detect_source_file(workspace, args.source)
    chapters, encoding = read_chapters(source_path)
    parse_error = chapter_parse_guard(source_path, chapters)
    if parse_error:
        raise SystemExit(parse_error)

    distillation_context = read_distillation_context(workspace, args.novel_name)
    extra_contexts: list[tuple[Path, str]] = []
    for raw_path in args.context_file:
        path = Path(raw_path).expanduser().resolve()
        if path.exists():
            extra_contexts.append((path, read_context_file(path)))

    prompt = build_prompt(
        args.novel_name,
        args.protagonist,
        chapters[:3],
        source_path,
        encoding,
        distillation_context,
        extra_contexts,
    )

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    prompt_path = attempts_dir / f"{stamp}-{args.attempt_label}-prompt.md"
    prompt_path.write_text(prompt.rstrip() + "\n", encoding="utf-8")

    debug_response_file = args.response_file or os.environ.get("OPENING_ANALYSIS_RESPONSE_FILE", "").strip()
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
        "source_file": str(source_path),
        "written_files": written,
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
