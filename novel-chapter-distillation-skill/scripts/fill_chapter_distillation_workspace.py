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


PLACEHOLDER_TOKENS = ("待补充", "待确认", "待定", "待完善")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auto-fill and repair the chapter-distillation layer.")
    parser.add_argument("--workspace", required=True, help="Workspace directory.")
    parser.add_argument("--novel-name", required=True, help="Novel name used in file naming.")
    parser.add_argument("--source", help="Optional source file override.")
    parser.add_argument("--project-root", help="Project root used to load .env.")
    parser.add_argument("--attempt-label", default="draft", help="Artifact label, e.g. draft / repair-1.")
    parser.add_argument("--force", action="store_true", help="Overwrite durable outputs.")
    parser.add_argument("--batch-size", type=int, default=3, help="How many chapters to send per batch when filling missing sections.")
    parser.add_argument("--context-file", action="append", default=[], help="Additional markdown/json files to inject into repair/fill context.")
    parser.add_argument("--response-file", help="Debug override: load chapter batch response from a local text file.")
    return parser.parse_args()


def load_env(project_root: Path) -> None:
    env_path = project_root / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.strip().split("=", 1)
            os.environ[key] = value


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"failed to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_text(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def latest_status_file(workspace: Path) -> Path | None:
    candidates = sorted(workspace.glob("工作状态-*.md"))
    return candidates[-1] if candidates else None


def contains_placeholder(text: str) -> bool:
    return any(token in text for token in PLACEHOLDER_TOKENS)


def normalize_line_value(value: str) -> str:
    cleaned = value.replace("\u3000", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or "待补充"


def extract_line_field(section_text: str, label: str) -> str:
    pattern = rf"^\s*-\s*{re.escape(label)}[:：]\s*(.+?)\s*$"
    matched = re.search(pattern, section_text, flags=re.MULTILINE)
    return normalize_line_value(matched.group(1)) if matched else "待补充"


def load_section_payloads(paths: Any, chapters: list[Any]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for chapter in chapters:
        section_path = paths.sections_dir / f"{chapter.index:04d}.md"
        section_text = read_text(section_path) if section_path.exists() else ""
        payloads.append(
            {
                "chapter": chapter,
                "path": section_path,
                "text": section_text,
                "core": extract_line_field(section_text, "本章核心推进"),
                "state": extract_line_field(section_text, "主角 / 核心视角状态"),
                "new_info": extract_line_field(section_text, "关键新信息 / 新设定"),
                "relation": extract_line_field(section_text, "关系 / 局势变化"),
                "function": extract_line_field(section_text, "本章结构功能"),
                "hook": extract_line_field(section_text, "章末钩子 / 遗留问题"),
                "stage": extract_line_field(section_text, "阶段判断"),
            }
        )
    return payloads


def missing_or_placeholder_chapters(section_payloads: list[dict[str, Any]]) -> list[Any]:
    missing: list[Any] = []
    for item in section_payloads:
        text = item["text"]
        if not text.strip() or contains_placeholder(text):
            missing.append(item["chapter"])
    return missing


def batch_iter(chapters: list[Any], batch_size: int) -> list[list[Any]]:
    return [chapters[i : i + batch_size] for i in range(0, len(chapters), batch_size)]


def ensure_attempt_dirs(paths: Any) -> Path:
    attempts_dir = paths.work_dir / "attempts"
    attempts_dir.mkdir(parents=True, exist_ok=True)
    return attempts_dir


def load_debug_response(args: argparse.Namespace) -> str | None:
    raw = args.response_file or os.environ.get("CHAPTER_DISTILLATION_RESPONSE_FILE", "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"response file not found: {path}")
    return path.read_text(encoding="utf-8")


def fill_missing_sections(
    distill_module: Any,
    paths: Any,
    chapters: list[Any],
    batch_size: int,
    extra_contexts: list[tuple[Path, str]],
    debug_response: str | None,
    attempts_dir: Path,
    attempt_label: str,
) -> list[dict[str, Any]]:
    missing = missing_or_placeholder_chapters(load_section_payloads(paths, chapters))
    if not missing:
        return []

    completed_batches: list[dict[str, Any]] = []
    for batch_index, batch in enumerate(batch_iter(missing, batch_size), start=1):
        if debug_response is not None:
            raw_result = debug_response
        else:
            raw_result = distill_module.call_api(batch, len(batch), extra_contexts)
        if not raw_result:
            raise RuntimeError(f"chapter distillation API failed for batch starting at chapter {batch[0].index}")
        ok = distill_module.write_batch_artifacts(paths, batch, raw_result)
        if not ok:
            raise RuntimeError(f"chapter distillation returned insufficient sections for batch starting at chapter {batch[0].index}")
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        (attempts_dir / f"{stamp}-{attempt_label}-batch-{batch_index:02d}.txt").write_text(raw_result.rstrip() + "\n", encoding="utf-8")
        completed_batches.append(
            {
                "first": batch[0].index,
                "last": batch[-1].index,
                "batch_index": batch_index,
                "saved_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
    return completed_batches


def render_readme(novel_name: str, source_path: Path, chapter_count: int) -> str:
    return (
        f"# {novel_name} 章节蒸馏工作区说明\n\n"
        f"本目录是《{novel_name}》的章节蒸馏骨架工作区。\n\n"
        "## 当前结构\n\n"
        f"- `source/{source_path.name}`\n"
        "  原始文本副本\n"
        "- `chapter-distillation-manifest.json`\n"
        "  章节清单与章节边界\n"
        f"- `{novel_name}-章节蒸馏骨架.md`\n"
        "  正式章节骨架文件\n"
        f"- `{novel_name}-阶段骨架与换挡草图.md`\n"
        "  阶段切分与换挡判断\n"
        f"- `{novel_name}-校准与验证锚点.md`\n"
        "  给后续各层复用的校准锚点\n"
        "- `work/chapter-distillation/`\n"
        "  中间续跑状态、批次缓存和重建产物\n\n"
        "## 当前说明\n\n"
        f"- 当前总章节数：`{chapter_count}`\n"
        "- 当前工作区已经进入正式章节蒸馏阶段，不再只是初始化骨架。\n"
        "- 后续 opening / protagonist / outline / highlight 都应优先复用这一层的骨架与校准锚点。\n"
    )


def split_stage_ranges(section_payloads: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    labeled: list[tuple[str, list[dict[str, Any]]]] = []
    for item in section_payloads:
        stage = item["stage"]
        if stage in PLACEHOLDER_TOKENS or not stage.strip():
            continue
        if labeled and labeled[-1][0] == stage:
            labeled[-1][1].append(item)
        else:
            labeled.append((stage, [item]))
    if len(labeled) >= 3:
        return labeled[:4]

    total = len(section_payloads)
    if total == 0:
        return []
    boundaries = [0, max(1, total // 4), max(2, total // 2), max(3, (total * 3) // 4), total]
    grouped: list[tuple[str, list[dict[str, Any]]]] = []
    for idx in range(4):
        start = boundaries[idx]
        end = boundaries[idx + 1]
        if start >= total:
            break
        chunk = section_payloads[start:end] or section_payloads[start : start + 1]
        grouped.append((f"阶段 {idx + 1}", chunk))
    return grouped


def summarise_items(items: list[str], minimum: int = 2) -> str:
    filtered = [normalize_line_value(item) for item in items if item and item not in PLACEHOLDER_TOKENS]
    filtered = [item for item in filtered if item != "待补充"]
    if not filtered:
        return "当前章节骨架已经覆盖这一段，但仍需要回看原文补更精确的结构总结。"
    unique = list(dict.fromkeys(filtered))
    head = "；".join(unique[:minimum])
    return head


def render_stage_skeleton(novel_name: str, section_payloads: list[dict[str, Any]]) -> str:
    grouped = split_stage_ranges(section_payloads)
    if not grouped:
        grouped = [("阶段 1", section_payloads[:1])] if section_payloads else []
    overall = (
        "整书阶段判断应优先跟随章节骨架的连续换挡，而不是按字数机械等分。"
        "因为前段承诺、中段抬升、后段扩边和终局收束在章节功能上会表现出明显差异，所以阶段骨架要围绕换挡节点来写。"
    )
    lines = [
        f"# 《{novel_name}》阶段骨架与换挡草图",
        "",
        "## 总判断",
        "",
        f"- {overall}",
        "",
    ]
    for idx in range(4):
        if idx < len(grouped):
            stage_name, items = grouped[idx]
        else:
            stage_name, items = (f"阶段 {idx + 1}", grouped[-1][1] if grouped else [])
        if not items:
            continue
        first = items[0]["chapter"].index
        last = items[-1]["chapter"].index
        functions = summarise_items([item["function"] for item in items], minimum=2)
        hook = summarise_items([item["hook"] for item in items], minimum=2)
        relation = summarise_items([item["relation"] for item in items], minimum=2)
        lines.extend(
            [
                f"## 阶段 {idx + 1}",
                "",
                f"- 章节范围：第{first}章-第{last}章（当前命名参考：{stage_name}）",
                f"- 阶段功能：这一段的主功能是 {functions}。因为这些章节会持续把局势从上一节点推向下一节点，所以可以视为相对稳定的阶段块。",
                f"- 换挡理由：当叙事开始从“{relation}”转向“{hook}”时，说明章节驱动力已经发生质变，因此这里应视为一次换挡。",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def pick_anchor(section_payloads: list[dict[str, Any]], index: int) -> dict[str, Any]:
    if not section_payloads:
        return {}
    index = max(0, min(index, len(section_payloads) - 1))
    return section_payloads[index]


def anchor_sentence(item: dict[str, Any], prefix: str) -> str:
    if not item:
        return "当前尚未抽出可用章节锚点，但应回到章节骨架先补齐关键章节。"
    chapter = item["chapter"]
    return (
        f"{prefix}可先回看 `{chapter.title}`。因为该章的核心推进是“{item['core']}”，"
        f"并且主角状态从“{item['state']}”发生位移，最后又以“{item['hook']}”把压力送往下一节点，"
        f"所以它适合作为后续分析层的复核入口。"
    )


def render_calibration_anchors(novel_name: str, section_payloads: list[dict[str, Any]]) -> str:
    total = len(section_payloads)
    opening = pick_anchor(section_payloads, 0)
    first_shift = pick_anchor(section_payloads, max(1, total // 4))
    middle = pick_anchor(section_payloads, max(1, total // 2))
    expansion = pick_anchor(section_payloads, max(1, (total * 3) // 4))
    climax = pick_anchor(section_payloads, max(1, total - 2))
    ending = pick_anchor(section_payloads, total - 1)
    return "\n".join(
        [
            f"# 《{novel_name}》校准与验证锚点",
            "",
            "## 开篇承诺锚点",
            "",
            f"- {anchor_sentence(opening, '开篇承诺锚点')}",
            "",
            "## 第一次重大换挡锚点",
            "",
            f"- {anchor_sentence(first_shift, '第一次重大换挡')}",
            "",
            "## 中段校准锚点",
            "",
            f"- {anchor_sentence(middle, '中段校准锚点')}",
            "",
            "## 扩边 / 升阶锚点",
            "",
            f"- {anchor_sentence(expansion, '扩边 / 升阶锚点')}",
            "",
            "## 高潮压缩锚点",
            "",
            f"- {anchor_sentence(climax, '高潮压缩锚点')}",
            "",
            "## 终局 / 落点锚点",
            "",
            f"- {anchor_sentence(ending, '终局 / 落点锚点')}",
            "",
            "## 后续 skill 应如何复用",
            "",
            "- opening 层应优先回看开篇承诺锚点，确认前三章 promise 和后续实际兑现是否一致。",
            "- protagonist / outline / highlight 层应先看第一次重大换挡锚点和中段校准锚点，因为这两处最能暴露人物与结构判断是否漂移。",
            "- 如果后续层的高位判断和章节骨架冲突，应回看扩边 / 升阶锚点、高潮压缩锚点与终局 / 落点锚点，再决定是否重写上层分析。",
            "",
        ]
    )


def render_status(novel_name: str, section_payloads: list[dict[str, Any]]) -> str:
    completed = sum(1 for item in section_payloads if item["text"].strip() and not contains_placeholder(item["text"]))
    total = len(section_payloads)
    return "\n".join(
        [
            f"# 《{novel_name}》工作状态 {date.today().isoformat()}",
            "",
            "## 当前结论",
            "",
            f"- 当前章节骨架：已覆盖 `{completed}/{total}` 章，并已重建正式骨架文件。",
            "- 当前阶段骨架与校准锚点：已根据章节骨架自动重建，可继续供后续各层复用。",
            "",
            "## 当前不应误判为已完成的部分",
            "",
            "- 不应把 manifest 存在误判成章节蒸馏已完成，真正的完成标准是正式骨架、阶段骨架和校准锚点都可用。",
            "- 不应让后续层绕开这一层直接重写人物或大纲判断，否则会继续放大与原文的漂移。",
            "",
            "## 下次开始时建议先看",
            "",
            f"1. {novel_name}-章节蒸馏骨架.md",
            f"2. {novel_name}-阶段骨架与换挡草图.md",
            f"3. {novel_name}-校准与验证锚点.md",
            "4. 本文件",
            "",
            "## 一句话交接",
            "",
            "章节层已经进入可复用状态；后续如发现上层判断漂移，应先回到章节骨架和校准锚点重新对齐。",
            "",
        ]
    )


def build_manifest_payload(novel_name: str, source_path: Path, chapters: list[Any]) -> dict[str, Any]:
    return {
        "novel_name": novel_name,
        "source_file": str(source_path.resolve()),
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

    distill_module = load_module("chapter_distill_module", Path(__file__).with_name("distill_chapters.py"))
    workspace_resolved, source_path = distill_module.resolve_workspace_and_source(project_root, args.novel_name, args.source)
    if workspace_resolved != workspace:
        raise SystemExit(f"workspace mismatch: expected {workspace}, resolved {workspace_resolved}")
    paths = distill_module.build_paths(workspace, args.novel_name)
    distill_module.ensure_dirs(paths)
    attempts_dir = ensure_attempt_dirs(paths)

    chapters, _encoding, _pattern = distill_module.read_chapters(source_path)
    if not chapters:
        raise SystemExit("未检测到足够章节，请检查源文件格式")

    distill_module.bootstrap_from_existing_skeleton(paths, chapters)
    debug_response = load_debug_response(args)
    extra_contexts: list[tuple[Path, str]] = []
    for raw_path in args.context_file:
        path = Path(raw_path).expanduser().resolve()
        if path.exists():
            extra_contexts.append((path, distill_module.read_context_file(path)))
    completed_batches = fill_missing_sections(
        distill_module,
        paths,
        chapters,
        max(1, args.batch_size),
        extra_contexts,
        debug_response,
        attempts_dir,
        args.attempt_label,
    )
    distill_module.rebuild_skeleton(paths, args.novel_name, chapters)
    section_payloads = load_section_payloads(paths, chapters)

    (workspace / "chapter-distillation-manifest.json").write_text(
        json.dumps(build_manifest_payload(args.novel_name, source_path, chapters), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (workspace / "README.md").write_text(render_readme(args.novel_name, source_path, len(chapters)), encoding="utf-8")
    (workspace / f"{args.novel_name}-阶段骨架与换挡草图.md").write_text(
        render_stage_skeleton(args.novel_name, section_payloads), encoding="utf-8"
    )
    (workspace / f"{args.novel_name}-校准与验证锚点.md").write_text(
        render_calibration_anchors(args.novel_name, section_payloads), encoding="utf-8"
    )
    status_path = latest_status_file(workspace) or workspace / f"工作状态-{date.today().isoformat()}.md"
    status_path.write_text(render_status(args.novel_name, section_payloads), encoding="utf-8")

    progress = distill_module.load_progress(paths)
    history = progress.get("completed_batches", []) if isinstance(progress.get("completed_batches"), list) else []
    history.extend(completed_batches)
    next_seq = max((item["chapter"].index for item in section_payloads if item["text"].strip() and not contains_placeholder(item["text"])), default=0) + 1
    distill_module.save_progress(paths, len(chapters), min(next_seq, len(chapters) + 1), history)

    latest_run = {
        "novel_name": args.novel_name,
        "attempt_label": args.attempt_label,
        "written_files": [
            str((workspace / "README.md").resolve()),
            str((workspace / "chapter-distillation-manifest.json").resolve()),
            str((workspace / f"{args.novel_name}-章节蒸馏骨架.md").resolve()),
            str((workspace / f"{args.novel_name}-阶段骨架与换挡草图.md").resolve()),
            str((workspace / f"{args.novel_name}-校准与验证锚点.md").resolve()),
            str(status_path.resolve()),
        ],
        "completed_batches": completed_batches,
        "context_files": [str(Path(p).expanduser().resolve()) for p in args.context_file if Path(p).expanduser().exists()],
        "response_file": args.response_file or os.environ.get("CHAPTER_DISTILLATION_RESPONSE_FILE", "").strip(),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    (paths.work_dir / "latest-fill-run.json").write_text(json.dumps(latest_run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(latest_run, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
