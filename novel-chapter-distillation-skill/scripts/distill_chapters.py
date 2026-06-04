#!/usr/bin/env python3
"""
章节蒸馏 — DeepSeek API 自动模式

目标：
1. 中间续跑状态、原始批次结果、备份文件统一放到 work/chapter-distillation/
2. 正式产物 <小说名>-章节蒸馏骨架.md 始终保持可读、按章节顺序重建
3. 不再直接把批次结果尾部追加到正式骨架，避免重复段落和临时内容污染工作区根目录
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

BATCH_SIZE = 3
ENCODINGS = ["utf-8", "utf-8-sig", "gb18030", "gbk"]
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
SYSTEM_PROMPT = """你是专业的网络小说章节分析专家。对每章输出七维度蒸馏分析。

格式（严格遵循）：
---
## 第X章 标题

- **本章核心推进**：一句话
- **主角 / 核心视角状态**：从A到B
- **关键新信息 / 新设定**：角色/设定/世界观
- **关系 / 局势变化**：变化描述
- **本章结构功能**：本章在整段叙事里的作用
- **章末钩子 / 遗留问题**：悬念
- **阶段判断**：阶段名
---

每章200-400字，引用具体角色名和事件。直接输出，不加前言。"""
FIELD_ALIASES = {
    "本章核心推进": ("本章核心推进", "核心推进"),
    "主角 / 核心视角状态": ("主角 / 核心视角状态", "主角状态变化", "主角状态", "核心视角状态"),
    "关键新信息 / 新设定": ("关键新信息 / 新设定", "新增信息", "新信息", "新增设定"),
    "关系 / 局势变化": ("关系 / 局势变化", "关系/局势变化", "局势变化"),
    "本章结构功能": ("本章结构功能", "结构功能", "结构作用", "本章结构作用"),
    "章末钩子 / 遗留问题": ("章末钩子 / 遗留问题", "章末钩子", "遗留问题", "章末悬念"),
    "阶段判断": ("阶段判断",),
}


@dataclass
class Chapter:
    index: int
    title: str
    body: str
    start_line: int
    end_line: int


@dataclass
class DistillPaths:
    workspace: Path
    skeleton: Path
    work_dir: Path
    batches_dir: Path
    sections_dir: Path
    backups_dir: Path
    progress_file: Path
    latest_batch_file: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch distill chapters with DeepSeek and keep outputs workspace-friendly.")
    parser.add_argument("novel_name", help="Novel name / workspace directory name.")
    parser.add_argument("--project-root", default=os.getcwd(), help="Project root. Defaults to current working directory.")
    parser.add_argument("--source", help="Optional source file override.")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="Number of chapters per API batch.")
    return parser.parse_args()


def load_env(project_root: Path) -> None:
    env_path = project_root / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.strip().split("=", 1)
            os.environ[key] = value


def detect_encoding(filepath: Path) -> str:
    for encoding in ENCODINGS:
        try:
            filepath.read_text(encoding=encoding)[:100]
            return encoding
        except (UnicodeDecodeError, LookupError):
            continue
    return "utf-8"


def _split_by_pattern(lines: list[str], pattern: re.Pattern[str]) -> list[Chapter]:
    chapters: list[Chapter] = []
    cur_title = ""
    cur_lines: list[str] = []
    start_line = 1
    in_chapter = False
    for line_no, line in enumerate(lines, start=1):
        matched = pattern.match(line.strip())
        if matched:
            if in_chapter:
                chapters.append(
                    Chapter(
                        index=len(chapters) + 1,
                        title=cur_title,
                        body="".join(cur_lines),
                        start_line=start_line,
                        end_line=line_no - 1,
                    )
                )
            cur_title = line.strip().lstrip("#").strip()
            cur_lines = []
            start_line = line_no
            in_chapter = True
        elif in_chapter:
            cur_lines.append(line)
    if in_chapter:
        chapters.append(
            Chapter(
                index=len(chapters) + 1,
                title=cur_title,
                body="".join(cur_lines),
                start_line=start_line,
                end_line=len(lines),
            )
        )
    return chapters


def read_chapters(source_path: Path) -> tuple[list[Chapter], str, str]:
    encoding = detect_encoding(source_path)
    lines = source_path.read_text(encoding=encoding, errors="ignore").splitlines(keepends=True)
    best_chapters: list[Chapter] = []
    best_pattern = "unmatched"
    for pattern in CHAPTER_PATTERNS:
        chapters = _split_by_pattern(lines, pattern)
        if len(chapters) >= 10:
            return chapters, encoding, pattern.pattern
        if len(chapters) > len(best_chapters):
            best_chapters = chapters
            best_pattern = pattern.pattern
    return best_chapters, encoding, best_pattern


def chapter_parse_guard(source_path: Path, chapters: list[Chapter]) -> str | None:
    if len(chapters) >= 3:
        if source_path.stat().st_size < 200_000 or len(chapters) >= 10:
            return None
    if not chapters:
        return "未检测到足够章节，请检查源文件格式"
    return (
        f"章节识别结果过少：当前只识别到 {len(chapters)} 章。"
        "请检查是否为裸数字章节、英文 Chapter 标题或其他未覆盖格式。"
    )


def resolve_workspace_and_source(project_root: Path, novel_name: str, source_override: str | None) -> tuple[Path, Path]:
    workspace = project_root / novel_name
    if not workspace.is_dir():
        raise SystemExit(f"workspace not found: {workspace}")

    if source_override:
        source = Path(source_override).expanduser().resolve()
        if not source.exists():
            raise SystemExit(f"source not found: {source}")
        return workspace, source

    source_dir = workspace / "source"
    if not source_dir.is_dir():
        raise SystemExit(f"source directory not found: {source_dir}")

    candidates: list[Path] = []
    for suffix in (".md", ".txt"):
        candidates.extend(sorted(source_dir.glob(f"*{suffix}")))
    preferred = None
    for candidate in candidates:
        if candidate.stem == novel_name:
            preferred = candidate
            break
    if not preferred and candidates:
        preferred = candidates[0]
    if not preferred:
        raise SystemExit(f"unable to find source file under: {source_dir}")
    return workspace, preferred


def build_paths(workspace: Path, novel_name: str) -> DistillPaths:
    work_dir = workspace / "work" / "chapter-distillation"
    return DistillPaths(
        workspace=workspace,
        skeleton=workspace / f"{novel_name}-章节蒸馏骨架.md",
        work_dir=work_dir,
        batches_dir=work_dir / "batches",
        sections_dir=work_dir / "sections",
        backups_dir=work_dir / "backups",
        progress_file=work_dir / "progress.json",
        latest_batch_file=work_dir / "latest-batch.json",
    )


def ensure_dirs(paths: DistillPaths) -> None:
    paths.work_dir.mkdir(parents=True, exist_ok=True)
    paths.batches_dir.mkdir(parents=True, exist_ok=True)
    paths.sections_dir.mkdir(parents=True, exist_ok=True)
    paths.backups_dir.mkdir(parents=True, exist_ok=True)


def backup_skeleton(paths: DistillPaths) -> None:
    if not paths.skeleton.exists():
        return
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(paths.skeleton, paths.backups_dir / f"{stamp}-{paths.skeleton.name}")


def load_progress(paths: DistillPaths) -> dict:
    if not paths.progress_file.exists():
        return {}
    try:
        return json.loads(paths.progress_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def infer_next_seq(paths: DistillPaths, total: int) -> int:
    progress = load_progress(paths)
    next_seq = progress.get("next_seq")
    if isinstance(next_seq, int) and next_seq >= 1:
        return min(next_seq, total + 1)
    existing = sorted(paths.sections_dir.glob("*.md"))
    if not existing:
        return 1
    contiguous = 0
    for expected, path in enumerate(existing, start=1):
        if path.stem != f"{expected:04d}":
            break
        contiguous = expected
    return min(contiguous + 1, total + 1)


def save_progress(paths: DistillPaths, total: int, next_seq: int, completed_batches: list[dict]) -> None:
    payload = {
        "total_chapters": total,
        "next_seq": next_seq,
        "last_completed_seq": max(next_seq - 1, 0),
        "completed_batches": completed_batches,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    paths.progress_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def record_latest_batch(paths: DistillPaths, payload: dict) -> None:
    paths.latest_batch_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def bootstrap_from_existing_skeleton(paths: DistillPaths, chapters: list[Chapter]) -> bool:
    if any(paths.sections_dir.glob("*.md")) or not paths.skeleton.exists():
        return False
    text = paths.skeleton.read_text(encoding="utf-8", errors="ignore")
    batch_re = re.compile(r"^> \*\*蒸馏批次\s+\d+\*\*（第(\d+)-(\d+)章）\s*$", flags=re.MULTILINE)
    matches = list(batch_re.finditer(text))
    if not matches:
        return False

    imported_batches: list[dict] = []
    for idx, matched in enumerate(matches):
        first = int(matched.group(1))
        last = int(matched.group(2))
        block_start = matched.end()
        block_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        block_text = text[block_start:block_end].strip()
        batch = [chapter for chapter in chapters if first <= chapter.index <= last]
        if not batch:
            continue
        if not write_batch_artifacts(paths, batch, block_text):
            continue
        imported_batches.append(
            {
                "first": first,
                "last": last,
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "source": "legacy-skeleton-bootstrap",
            }
        )

    if imported_batches:
        next_seq = max(item["last"] for item in imported_batches) + 1
        save_progress(paths, len(chapters), next_seq, imported_batches)
        return True
    return False


def trim_body(body: str) -> str:
    return body[:2500] if len(body) > 3000 else body


def read_context_file(path: Path, limit: int = 2200) -> str:
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return path.read_text(encoding="utf-8", errors="ignore")[:limit]
        return json.dumps(payload, ensure_ascii=False, indent=2)[:limit]
    return path.read_text(encoding="utf-8", errors="ignore")[:limit]


def build_user_prompt(
    batch: list[Chapter],
    batch_size: int,
    extra_contexts: list[tuple[Path, str]] | None = None,
) -> str:
    chapter_blocks: list[str] = []
    for chapter in batch:
        chapter_blocks.append(
            "\n".join(
                [
                    f"## {chapter.title}",
                    f"- 章节序号：第{chapter.index}章",
                    f"- 源文件行号：{chapter.start_line}-{chapter.end_line}",
                    trim_body(chapter.body),
                ]
            )
        )
    extra_sections = [f"### 额外上下文：{path.name}\n{text}" for path, text in extra_contexts or []]
    return "\n\n".join(
        [
            f"任务：分析以下 {batch_size} 章，为每章输出七维度蒸馏分析。",
            "要求：必须引用具体角色、事件、设定和局势变化，不要输出模板化空话。",
            "## 待分析章节",
            "\n\n".join(chapter_blocks),
            "## 额外上下文",
            "\n\n".join(extra_sections) if extra_sections else "（无）",
            "请严格按 system prompt 结构输出。",
        ]
    )


def call_api(
    batch: list[Chapter],
    batch_size: int,
    extra_contexts: list[tuple[Path, str]] | None = None,
) -> str | None:
    try:
        result = call_chat_completion(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_user_prompt(batch, batch_size, extra_contexts),
            model_env_vars=("CHAPTER_DISTILLATION_MODEL",),
            fallback_model_env_vars=("CHAPTER_DISTILLATION_FALLBACK_MODELS",),
            default_model="deepseek-chat",
            temperature=0.5,
            max_tokens=4000,
            timeout=300,
            max_attempts=4,
        )["content"].strip()
    except Exception:
        return None
    if result.startswith("```"):
        result = re.sub(r"^```\w*\n?", "", result)
        result = re.sub(r"\n?```$", "", result)
    return result


def split_result_sections(result: str) -> list[str]:
    sections: list[str] = []
    current: list[str] = []
    for line in result.splitlines():
        if line.strip().startswith("## "):
            if current:
                sections.append("\n".join(current).strip())
            current = [line]
        elif current:
            current.append(line)
    if current:
        sections.append("\n".join(current).strip())
    return sections


def parse_fields(section_text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    current_label: str | None = None
    current_value: list[str] = []
    bullet_re = re.compile(r"^\s*-\s*\*\*(.+?)\*\*[:：]\s*(.*)$")

    def flush() -> None:
        nonlocal current_label, current_value
        if current_label:
            fields[current_label] = sanitize_value(" ".join(piece.strip() for piece in current_value if piece.strip()))
        current_label = None
        current_value = []

    for raw_line in section_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("## "):
            continue
        matched = bullet_re.match(line)
        if matched:
            flush()
            label = matched.group(1).strip()
            value = matched.group(2).strip()
            current_label = label
            current_value = [value] if value else []
        elif current_label:
            current_value.append(line)
    flush()
    return fields


def sanitize_value(value: str) -> str:
    cleaned = value.replace("\u3000", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or "待补充"


def pick_field(fields: dict[str, str], target: str) -> str:
    for alias in FIELD_ALIASES[target]:
        if alias in fields and fields[alias].strip():
            return sanitize_value(fields[alias])
    return "待补充"


def render_chapter_section(chapter: Chapter, fields: dict[str, str]) -> str:
    lines = [
        f"## {chapter.title}",
        "",
        f"- 章节范围：第 {chapter.index} 个章节；源文件行 {chapter.start_line}-{chapter.end_line}",
        f"- 本章核心推进：{pick_field(fields, '本章核心推进')}",
        f"- 主角 / 核心视角状态：{pick_field(fields, '主角 / 核心视角状态')}",
        f"- 关键新信息 / 新设定：{pick_field(fields, '关键新信息 / 新设定')}",
        f"- 关系 / 局势变化：{pick_field(fields, '关系 / 局势变化')}",
        f"- 本章结构功能：{pick_field(fields, '本章结构功能')}",
        f"- 章末钩子 / 遗留问题：{pick_field(fields, '章末钩子 / 遗留问题')}",
    ]
    stage = pick_field(fields, "阶段判断")
    if stage != "待补充":
        lines.append(f"- 阶段判断：{stage}")
    lines.append("")
    return "\n".join(lines)


def write_batch_artifacts(paths: DistillPaths, batch: list[Chapter], raw_result: str) -> bool:
    first = batch[0].index
    last = batch[-1].index
    batch_path = paths.batches_dir / f"batch-{first:04d}-{last:04d}.md"
    batch_header = [
        f"# 蒸馏批次 {first:04d}-{last:04d}",
        "",
        f"- 章节范围：第 {first}-{last} 章",
        f"- 更新时间：{datetime.now().isoformat(timespec='seconds')}",
        "",
        "---",
        "",
        raw_result.strip(),
        "",
    ]
    batch_path.write_text("\n".join(batch_header), encoding="utf-8")

    sections = split_result_sections(raw_result)
    if len(sections) < len(batch):
        return False
    for chapter, section_text in zip(batch, sections):
        fields = parse_fields(section_text)
        normalized = render_chapter_section(chapter, fields)
        (paths.sections_dir / f"{chapter.index:04d}.md").write_text(normalized, encoding="utf-8")
    return True


def placeholder_section(chapter: Chapter) -> str:
    return "\n".join(
        [
            f"## {chapter.title}",
            "",
            f"- 章节范围：第 {chapter.index} 个章节；源文件行 {chapter.start_line}-{chapter.end_line}",
            "- 本章核心推进：待补充",
            "- 主角 / 核心视角状态：待补充",
            "- 关键新信息 / 新设定：待补充",
            "- 关系 / 局势变化：待补充",
            "- 本章结构功能：待补充",
            "- 章末钩子 / 遗留问题：待补充",
            "",
        ]
    )


def rebuild_skeleton(paths: DistillPaths, novel_name: str, chapters: list[Chapter]) -> None:
    lines = [
        f"# 《{novel_name}》章节蒸馏骨架",
        "",
        "> 正式骨架文件。中间批次、续跑进度、备份文件统一收纳在 `work/chapter-distillation/`。",
        "",
    ]
    for chapter in chapters:
        section_path = paths.sections_dir / f"{chapter.index:04d}.md"
        if section_path.exists():
            lines.append(section_path.read_text(encoding="utf-8").rstrip())
        else:
            lines.append(placeholder_section(chapter).rstrip())
        lines.append("")
    paths.skeleton.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    novel_name = args.novel_name
    project_root = Path(args.project_root).expanduser().resolve()

    load_env(project_root)
    workspace, source = resolve_workspace_and_source(project_root, novel_name, args.source)
    paths = build_paths(workspace, novel_name)
    ensure_dirs(paths)

    chapters, encoding, pattern = read_chapters(source)
    parse_error = chapter_parse_guard(source, chapters)
    if parse_error:
        raise SystemExit(parse_error)

    print("=" * 60)
    print("章节蒸馏 (DeepSeek API)")
    print(f"  小说: {novel_name}")
    print(f"  源文件: {source}")
    print(f"  编码: {encoding}")
    print(f"  章节格式: {pattern}")
    print("=" * 60)
    print(f"📖 共 {len(chapters)} 章")

    bootstrapped = bootstrap_from_existing_skeleton(paths, chapters)
    if bootstrapped:
        rebuild_skeleton(paths, novel_name, chapters)
    next_seq = infer_next_seq(paths, len(chapters))
    if next_seq > 1:
        print(f"📌 续跑: 第{next_seq}章")

    pending = [chapter for chapter in chapters if chapter.index >= next_seq]
    if not pending:
        print("✅ 所有章节都已有结构化蒸馏缓存")
        rebuild_skeleton(paths, novel_name, chapters)
        return

    total_batches = (len(pending) + args.batch_size - 1) // args.batch_size
    print(f"📊 待蒸馏: {len(pending)}章 → {total_batches}批")
    print(f"💰 预估: ~${total_batches * 0.005:.2f}")
    print(f"⏱️  预估: ~{total_batches * 25 // 60}分钟\n")

    backup_skeleton(paths)
    progress = load_progress(paths)
    completed_batches = progress.get("completed_batches", []) if isinstance(progress.get("completed_batches"), list) else []

    success = 0
    for i in range(0, len(pending), args.batch_size):
        batch = pending[i : i + args.batch_size]
        batch_no = i // args.batch_size + 1
        first = batch[0].index
        last = batch[-1].index
        print(f"[{batch_no}/{total_batches}] 第{first}-{last}章 ", end="", flush=True)

        result = call_api(batch, args.batch_size)
        if not result:
            print("❌ 失败，进度已保留在结构化缓存目录")
            break

        if not write_batch_artifacts(paths, batch, result):
            print("❌ 返回章节数不足，已保留原始批次结果但未推进正式骨架")
            break
        rebuild_skeleton(paths, novel_name, chapters)
        completed_batches.append({"first": first, "last": last, "saved_at": datetime.now().isoformat(timespec="seconds")})
        save_progress(paths, len(chapters), last + 1, completed_batches)
        record_latest_batch(
            paths,
            {
                "novel_name": novel_name,
                "first": first,
                "last": last,
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "batch_file": str((paths.batches_dir / f"batch-{first:04d}-{last:04d}.md").resolve()),
            },
        )
        preview = result[:50].replace("\n", " ").replace("---", "").strip()
        print(f"✅ {preview}...")
        success += 1
        time.sleep(2)

    print(f"\n{'=' * 60}")
    print(f"🏁 {success}/{total_batches} 批成功")
    print(f"   正式文件: {paths.skeleton}")
    print(f"   中间缓存: {paths.work_dir}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
