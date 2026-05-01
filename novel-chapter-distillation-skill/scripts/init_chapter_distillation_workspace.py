#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

TEXT_ENCODINGS = ("utf-8", "utf-8-sig", "gb18030", "gbk")
CHAPTER_RE = re.compile(r"^(?:##\s*)?第[0-9０-９零一二三四五六七八九十百千万两]+[章节回卷部集篇幕].*$")
REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Chapter:
    index: int
    title: str
    start_line: int
    end_line: int


def write_file(path: Path, content: str, force: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return
    path.write_text(content, encoding="utf-8")


def run_cmd(cmd: list[str], env: dict[str, str] | None = None) -> bool:
    try:
        subprocess.run(cmd, check=True, env=env)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def find_refresh_status_script() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "novel-workspace-orchestrator-skill/scripts/refresh_workspace_status.py"
        if candidate.exists():
            return candidate
    return None


def refresh_workspace_status(workspace: Path, novel_name: str) -> None:
    script = find_refresh_status_script()
    if not script:
        return
    proc = subprocess.run(
        ["python3", str(script), "--workspace", str(workspace), "--novel-name", novel_name],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        message = proc.stderr.strip() or proc.stdout.strip() or "unknown error"
        print(f"warning: failed to refresh workspace-status.json: {message}")


def copy_source(source: Path, target_dir: Path, force: bool) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    copied = target_dir / source.name
    if copied.exists() and copied.resolve() == source.resolve():
        return copied
    if copied.exists() and not force:
        return copied
    shutil.copy2(source, copied)
    return copied


def strict_decode_text(path: Path) -> tuple[str, str] | None:
    for encoding in TEXT_ENCODINGS:
        try:
            return path.read_text(encoding=encoding), encoding
        except UnicodeDecodeError:
            continue
    return None


def convert_source(copied_source: Path, force: bool) -> Path | None:
    if copied_source.suffix.lower() != ".txt":
        return None

    md_target = copied_source.with_suffix(".md")
    if md_target.exists() and not force:
        return md_target

    text2markdown_src = REPO_ROOT / "text2markdown" / "src"
    if text2markdown_src.exists():
        env = os.environ.copy()
        env["PYTHONPATH"] = str(text2markdown_src)
        ok = run_cmd(
            [
                "python3",
                "-m",
                "text2markdown.cli",
                str(copied_source),
                "-o",
                str(md_target),
            ],
            env=env,
        )
        if ok and md_target.exists():
            return md_target

    decoded = strict_decode_text(copied_source)
    if not decoded:
        raise RuntimeError(
            f"unable to decode txt source: {copied_source} "
            "(tried utf-8, utf-8-sig, gb18030, gbk)"
        )
    text, _encoding = decoded
    md_target.write_text(text, encoding="utf-8")
    return md_target


def discover_existing_source(workspace: Path) -> Path | None:
    source_dir = workspace / "source"
    if source_dir.exists():
        for suffix in (".md", ".txt", ".docx"):
            matches = sorted(source_dir.glob(f"*{suffix}"))
            if matches:
                return matches[0]
    return None


def normalize_lines(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return [line.rstrip() for line in text.split("\n")]


def is_probable_title_line(line: str) -> bool:
    cleaned = line.lstrip("#").strip()
    if not cleaned:
        return False
    if CHAPTER_RE.match(cleaned):
        return False
    return len(cleaned) <= 40


def parse_chapters(path: Path) -> list[Chapter]:
    lines = normalize_lines(path.read_text(encoding="utf-8", errors="ignore"))
    chapters: list[Chapter] = []
    current_title = "前言"
    start_line = 1
    seen_heading = False
    prefix_nonempty: list[str] = []

    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if CHAPTER_RE.match(line):
            title = line[2:].strip() if line.startswith("##") else line
            if seen_heading:
                chapters.append(
                    Chapter(
                        index=len(chapters) + 1,
                        title=current_title,
                        start_line=start_line,
                        end_line=line_no - 1,
                    )
                )
            elif prefix_nonempty and any(not is_probable_title_line(item) for item in prefix_nonempty):
                chapters.append(
                    Chapter(
                        index=1,
                        title=current_title,
                        start_line=1,
                        end_line=line_no - 1,
                    )
                )
            current_title = title
            start_line = line_no
            seen_heading = True
        elif not seen_heading and line:
            prefix_nonempty.append(line)

    if seen_heading:
        chapters.append(
            Chapter(
                index=len(chapters) + 1,
                title=current_title,
                start_line=start_line,
                end_line=len(lines),
            )
        )
    else:
        chapters.append(Chapter(index=1, title="全文", start_line=1, end_line=len(lines)))

    if chapters and chapters[0].title == "前言":
        prefix_lines = [line.strip() for line in lines[: chapters[0].end_line] if line.strip()]
        if prefix_lines and all(is_probable_title_line(line) for line in prefix_lines):
            chapters = chapters[1:]
            chapters = [
                Chapter(
                    index=idx,
                    title=chapter.title,
                    start_line=chapter.start_line,
                    end_line=chapter.end_line,
                )
                for idx, chapter in enumerate(chapters, start=1)
            ]

    return chapters


def detect_existing_context(workspace: Path) -> dict[str, Path]:
    patterns = {
        "protagonist_file": ["*-最终人物卡.md", "*主角结构摘要.md"],
        "index_file": ["*-词条总索引.md", "*-角色总索引.md"],
        "outline_file": ["*-大纲总览.md", "*-阶段与篇章拆分.md"],
        "opening_file": ["*-黄金前三章总判断.md", "*-开篇钩子与读者承诺.md"],
        "highlight_file": ["*-最吸引人的十个剧情细节总表.md", "*-剧情吸引力机制分析.md"],
    }
    found: dict[str, Path] = {}
    for key, variants in patterns.items():
        for pattern in variants:
            matches = sorted(workspace.glob(pattern))
            if matches:
                found[key] = matches[0]
                break
    return found


def reused_context_lines(existing_context: dict[str, Path]) -> str:
    if not existing_context:
        return "- 当前未检测到需要复用的后续分析层文件\n"
    labels = {
        "protagonist_file": "主角层文件",
        "index_file": "词条索引文件",
        "outline_file": "整书层文件",
        "opening_file": "开篇层文件",
        "highlight_file": "高光层文件",
    }
    lines = []
    for key in ("protagonist_file", "index_file", "outline_file", "opening_file", "highlight_file"):
        path = existing_context.get(key)
        if path:
            lines.append(f"- `{path.name}`\n  已检测到{labels[key]}")
    return "\n".join(lines) + "\n"


def manifest_payload(chapters: list[Chapter], source_path: Path) -> dict:
    return {
        "source_file": str(source_path),
        "chapter_count": len(chapters),
        "chapters": [asdict(chapter) for chapter in chapters],
    }


def chapter_skeleton_placeholder(novel_name: str, chapters: list[Chapter]) -> str:
    lines = [f"# 《{novel_name}》章节蒸馏骨架", ""]
    for chapter in chapters:
        lines.extend(
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
    return "\n".join(lines)


def stage_skeleton_placeholder(novel_name: str, chapter_count: int) -> str:
    return f"""# 《{novel_name}》阶段骨架与换挡草图

## 总判断

- 待补充

## 阶段 1

- 章节范围：待补充（当前总章节数：{chapter_count}）
- 阶段功能：待补充
- 换挡理由：待补充

## 阶段 2

- 章节范围：待补充
- 阶段功能：待补充
- 换挡理由：待补充

## 阶段 3

- 章节范围：待补充
- 阶段功能：待补充
- 换挡理由：待补充

## 阶段 4

- 章节范围：待补充
- 阶段功能：待补充
- 换挡理由：待补充
"""


def calibration_placeholder(novel_name: str) -> str:
    return f"""# 《{novel_name}》校准与验证锚点

## 开篇承诺锚点

- 待补充

## 第一次重大换挡锚点

- 待补充

## 中段校准锚点

- 待补充

## 扩边 / 升阶锚点

- 待补充

## 高潮压缩锚点

- 待补充

## 终局 / 落点锚点

- 待补充

## 后续 skill 应如何复用

- 待补充
"""


def readme_md(
    novel_name: str,
    copied_source: Path,
    md_source: Path | None,
    chapters: list[Chapter],
    existing_context: dict[str, Path],
    reusing_workspace: bool,
) -> str:
    md_line = ""
    if md_source and md_source.resolve() != copied_source.resolve():
        md_line = f"- `source/{md_source.name}`\n  转换后的 Markdown 原文\n"
    mode_line = (
        "- 当前模式说明：在已有小说工作区基础上补前置章节蒸馏层。\n"
        if reusing_workspace
        else "- 当前模式说明：当前目录是独立初始化的章节蒸馏骨架工作区。\n"
    )
    return f"""# {novel_name} 章节蒸馏工作区说明

本目录是《{novel_name}》的章节蒸馏骨架工作区。

## 当前结构

- `source/{copied_source.name}`
  原始文本副本
{md_line}- `chapter-distillation-manifest.json`
  当前识别出的章节清单与源文件锚点
- `{novel_name}-章节蒸馏骨架.md`
  每一章的浓缩精华与结构字段
- `{novel_name}-阶段骨架与换挡草图.md`
  阶段换挡的第一版草图
- `{novel_name}-校准与验证锚点.md`
  后续 skill 用来检查漂移和回看的锚点
- `工作状态-{date.today().isoformat()}.md`
  当前项目级交接文件

## 当前入口

- `README.md`
- `工作状态-{date.today().isoformat()}.md`
- `{novel_name}-章节蒸馏骨架.md`
- `{novel_name}-阶段骨架与换挡草图.md`
- `{novel_name}-校准与验证锚点.md`

## 当前说明

- 当前已识别章节数：`{len(chapters)}`
- 当前工作区刚初始化完成，以上蒸馏文件默认只是占位骨架，不代表章节蒸馏已完成。
{mode_line}- 这一层默认应先于主角层、开篇层、整书层和高光层使用。

## 已探测到的可复用上下文文件

{reused_context_lines(existing_context)}- 下一步应先把每一章压成稳定骨架，再让后续 skill 在这层之上做更高阶判断。
"""


def status_md(novel_name: str, chapter_count: int, existing_context: dict[str, Path], reusing_workspace: bool) -> str:
    mode_line = (
        "- 当前工作模式：在已有工作区上扩展章节蒸馏层\n"
        if reusing_workspace
        else "- 当前工作模式：新建章节蒸馏骨架工作区\n"
    )
    return f"""# 《{novel_name}》工作状态 {date.today().isoformat()}

## 当前结论

当前仅完成了章节蒸馏骨架工作区初始化。

- `章节骨架`：未形成
- `校准锚点`：未可用
- `当前识别章节数`：`{chapter_count}`

## 当前不应误判为已完成的部分

- 不应把章节清单当成章节蒸馏完成
- 不应把剧情摘要当成可验证骨架
- 不应因为后续分析层已存在，就误判章节蒸馏层已经完成

## 当前应如何继续

1. 逐章写出核心推进
2. 逐章判断主角或核心视角状态
3. 逐章记录新信息和局势变化
4. 标记关键换挡章节
5. 补齐后续校准和验证锚点

## 下次开始时建议先看

1. `README.md`
2. `{novel_name}-章节蒸馏骨架.md`
3. `{novel_name}-校准与验证锚点.md`
4. 本文件

## 一句话交接

《{novel_name}》当前只有章节蒸馏骨架工作区框架，还没有形成正式可校准的章节骨架。

## 当前模式补充

{mode_line}
## 已探测到的可复用文件

{reused_context_lines(existing_context)}"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize a durable chapter-distillation workspace.")
    parser.add_argument("--novel-name", required=True, help="Novel name used in file naming.")
    parser.add_argument("--workspace", help="Workspace directory to create or update.")
    parser.add_argument("--existing-workspace", help="Existing workspace directory to extend in place.")
    parser.add_argument("--source", help="Source text path. Optional when the workspace already has source files.")
    parser.add_argument("--force", action="store_true", help="Overwrite scaffold files when they already exist.")
    args = parser.parse_args()
    if not args.workspace and not args.existing_workspace:
        parser.error("one of --workspace or --existing-workspace is required")
    return args


def main() -> int:
    args = parse_args()
    reusing_workspace = bool(args.existing_workspace)
    workspace = Path(args.existing_workspace or args.workspace).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    source = Path(args.source).expanduser().resolve() if args.source else discover_existing_source(workspace)
    if not source or not source.exists():
        raise SystemExit("source not found; provide --source or ensure the workspace has a source/ file")

    copied_source = copy_source(source, workspace / "source", force=args.force)
    md_source = convert_source(copied_source, force=args.force)
    normalized_source = md_source or copied_source
    chapters = parse_chapters(normalized_source)
    existing_context = detect_existing_context(workspace)
    today = date.today().isoformat()

    manifest = manifest_payload(chapters, normalized_source)
    write_file(
        workspace / "chapter-distillation-manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        force=args.force,
    )
    write_file(
        workspace / "README.md",
        readme_md(args.novel_name, copied_source, md_source, chapters, existing_context, reusing_workspace),
        force=args.force,
    )
    write_file(
        workspace / f"工作状态-{today}.md",
        status_md(args.novel_name, len(chapters), existing_context, reusing_workspace),
        force=args.force,
    )
    write_file(
        workspace / f"{args.novel_name}-章节蒸馏骨架.md",
        chapter_skeleton_placeholder(args.novel_name, chapters),
        force=args.force,
    )
    write_file(
        workspace / f"{args.novel_name}-阶段骨架与换挡草图.md",
        stage_skeleton_placeholder(args.novel_name, len(chapters)),
        force=args.force,
    )
    write_file(
        workspace / f"{args.novel_name}-校准与验证锚点.md",
        calibration_placeholder(args.novel_name),
        force=args.force,
    )
    refresh_workspace_status(workspace, args.novel_name)
    print(f"initialized chapter-distillation workspace: {workspace}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
