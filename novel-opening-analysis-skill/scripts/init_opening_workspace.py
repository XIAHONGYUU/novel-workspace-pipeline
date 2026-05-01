#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from datetime import date
from pathlib import Path

TEXT_ENCODINGS = ("utf-8", "utf-8-sig", "gb18030", "gbk")
REPO_ROOT = Path(__file__).resolve().parents[2]


def find_first(workspace: Path, patterns: list[str]) -> Path | None:
    for pattern in patterns:
        matches = sorted(workspace.glob(pattern))
        if matches:
            return matches[0]
    return None


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


def detect_existing_context(workspace: Path, protagonist: str | None) -> dict[str, Path]:
    protagonist_patterns = []
    index_patterns = []
    outline_patterns = []
    if protagonist:
        protagonist_patterns.append(f"{protagonist}-最终人物卡.md")
        index_patterns.append(f"{protagonist}-词条总索引.md")
    protagonist_patterns.extend(["*-最终人物卡.md", "*主角结构摘要.md"])
    index_patterns.extend(["*-词条总索引.md", "*-角色总索引.md"])
    outline_patterns.extend(["*-大纲总览.md", "*-阶段与篇章拆分.md"])
    found = {
        "protagonist_file": find_first(workspace, protagonist_patterns),
        "index_file": find_first(workspace, index_patterns),
        "outline_file": find_first(workspace, outline_patterns),
    }
    return {key: value for key, value in found.items() if value}


def discover_existing_source(workspace: Path) -> Path | None:
    source_dir = workspace / "source"
    if source_dir.exists():
        for suffix in (".md", ".txt", ".docx"):
            matches = sorted(source_dir.glob(f"*{suffix}"))
            if matches:
                return matches[0]
    return None


def reused_context_lines(existing_context: dict[str, Path]) -> str:
    if not existing_context:
        return "- 当前未检测到可直接复用的上下文文件\n"
    labels = {
        "protagonist_file": "主角总卡 / 主角摘要",
        "index_file": "词条总索引",
        "outline_file": "大纲层文件",
    }
    lines = []
    for key in ("protagonist_file", "index_file", "outline_file"):
        path = existing_context.get(key)
        if path:
            lines.append(f"- `{path.name}`\n  复用为{labels[key]}")
    return "\n".join(lines) + "\n"


def readme_md(
    novel_name: str,
    protagonist: str | None,
    copied_source: Path,
    md_source: Path | None,
    existing_context: dict[str, Path],
    reusing_workspace: bool,
) -> str:
    protagonist_line = f"- 主角：`{protagonist}`\n" if protagonist else ""
    md_line = ""
    if md_source and md_source.resolve() != copied_source.resolve():
        md_line = f"- `source/{md_source.name}`\n  转换后的 Markdown 原文\n"
    mode_line = (
        "- 当前模式说明：在已有小说工作区基础上扩展黄金前三章分析层。\n"
        if reusing_workspace
        else "- 当前模式说明：当前目录是独立初始化的黄金前三章分析工作区。\n"
    )
    return f"""# {novel_name} 黄金前三章分析工作区说明

本目录是《{novel_name}》的黄金前三章分析工作区。

## 当前结构

- `source/{copied_source.name}`
  原始文本副本
{md_line}- `{novel_name}-黄金前三章总判断.md`
  前三章总判断与继续阅读驱动力判断
- `{novel_name}-第一章拆解.md`
  第一章结构拆解
- `{novel_name}-第二章拆解.md`
  第二章结构拆解
- `{novel_name}-第三章拆解.md`
  第三章结构拆解
- `{novel_name}-开篇钩子与读者承诺.md`
  开篇钩子、题材承诺与读者承诺判断
- `{novel_name}-开篇问题与修改建议.md`
  开篇薄弱点与修改优先级
- `工作状态-{date.today().isoformat()}.md`
  当前项目级交接文件

## 当前入口

- `README.md`
- `工作状态-{date.today().isoformat()}.md`
- `{novel_name}-黄金前三章总判断.md`
- `{novel_name}-第一章拆解.md`
- `{novel_name}-开篇问题与修改建议.md`

## 当前说明

{protagonist_line}- 当前工作区刚初始化完成，以上 opening 文件默认只是占位骨架，不代表分析已完成。
{mode_line}- 默认应把前三章分析得比整书大纲更细。

## 已探测到的可复用上下文文件

{reused_context_lines(existing_context)}- 下一步应先结合这些文件理解主角和后续承诺，再判断前三章有没有把 promise 立住。
"""


def status_md(
    novel_name: str,
    protagonist: str | None,
    existing_context: dict[str, Path],
    reusing_workspace: bool,
) -> str:
    protagonist_line = f"- 当前主角：`{protagonist}`\n" if protagonist else ""
    mode_line = (
        "- 当前工作模式：在已有工作区上扩展黄金前三章分析层\n"
        if reusing_workspace
        else "- 当前工作模式：新建黄金前三章分析工作区骨架\n"
    )
    return f"""# 《{novel_name}》工作状态 {date.today().isoformat()}

## 当前结论

当前仅完成了黄金前三章分析工作区初始化。

- `开篇抓力`：未明确
- `前三章结构`：未拆清
- `修改优先级`：未明确

## 当前不应误判为已完成的部分

- 不应把占位文件当正式成果
- 不应把前三章剧情摘要当结构分析完成
- 不应因为已有主角卡存在，就误判开篇分析已经完成

## 当前应如何继续

1. 判断第一章是否真正抓人
2. 判断主角亮相是否足够快
3. 判断冲突是否在前三章内真正启动
4. 判断信息释放和世界观投喂是否过重
5. 判断每章结尾是否有继续阅读拉力
6. 给出最优先的修改建议

## 下次开始时建议先看

1. `README.md`
2. `{novel_name}-黄金前三章总判断.md`
3. `{novel_name}-开篇问题与修改建议.md`
4. 本文件

## 一句话交接

《{novel_name}》当前只有黄金前三章分析工作区骨架，还没有形成正式的开篇判断。
{protagonist_line if protagonist else ""}
## 当前模式补充

{mode_line}
## 已探测到的可复用文件

{reused_context_lines(existing_context)}"""


def total_judgment_placeholder(novel_name: str) -> str:
    return f"""# 《{novel_name}》黄金前三章总判断

## 开篇钩子结论

- 待补充

## 主角亮相结论

- 待补充

## 冲突启动结论

- 待补充

## 前三章结构结论

- 待补充

## 继续阅读驱动力结论

- 待补充
"""


def chapter_placeholder(novel_name: str, chapter_no: int) -> str:
    return f"""# 《{novel_name}》第{chapter_no}章拆解

## 本章在开篇结构中的作用

- 待补充

## 钩子 / 压力点

- 待补充

## 主角状态与目标

- 待补充

## 信息释放与世界观投喂

- 待补充

## 结尾拉力

- 待补充

## 这一章最该强化或删减的地方

- 待补充
"""


def hook_placeholder(novel_name: str) -> str:
    return f"""# 《{novel_name}》开篇钩子与读者承诺

## 立即钩子

- 待补充

## 题材承诺

- 待补充

## 主角承诺

- 待补充

## 情绪 / 悬念承诺

- 待补充

## 三章内的结尾拉力模式

- 待补充
"""


def issues_placeholder(novel_name: str) -> str:
    return f"""# 《{novel_name}》开篇问题与修改建议

## 最强的地方

- 待补充

## 最弱的地方

- 待补充

## 分章问题

- 待补充

## 第一优先修改项

- 待补充

## 轻修建议

- 待补充
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a durable first-three-chapter analysis workspace.")
    parser.add_argument("--novel-name", required=True, help="Novel name used for directory and file names.")
    parser.add_argument("--source", help="Absolute or relative path to the novel source file.")
    parser.add_argument("--workspace", help="Workspace directory. Defaults to ./<小说名>.")
    parser.add_argument(
        "--existing-workspace",
        help="Reuse an existing novel workspace and extend it with opening-analysis files in place.",
    )
    parser.add_argument("--protagonist", help="Known protagonist name.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing starter files.")
    args = parser.parse_args()

    if not args.source and not args.existing_workspace:
        raise SystemExit("either --source or --existing-workspace is required")

    reusing_workspace = bool(args.existing_workspace)
    if reusing_workspace:
        workspace = Path(args.existing_workspace).expanduser().resolve()
    else:
        workspace = Path(args.workspace).expanduser().resolve() if args.workspace else Path.cwd() / args.novel_name
    workspace.mkdir(parents=True, exist_ok=True)

    source = Path(args.source).expanduser().resolve() if args.source else None
    if source and not source.exists():
        raise SystemExit(f"source not found: {source}")

    copied_source = None
    md_source = None
    if source:
        source_dir = workspace / "source"
        copied_source = copy_source(source, source_dir, args.force)
        md_source = convert_source(copied_source, args.force)
    elif reusing_workspace:
        copied_source = discover_existing_source(workspace)
        if not copied_source:
            raise SystemExit("no source file found in existing workspace; provide --source explicitly")
        md_source = copied_source if copied_source.suffix.lower() == ".md" else convert_source(copied_source, args.force)

    if not copied_source:
        raise SystemExit("failed to determine source file for workspace")

    existing_context = detect_existing_context(workspace, args.protagonist)
    write_file(
        workspace / "README.md",
        readme_md(args.novel_name, args.protagonist, copied_source, md_source, existing_context, reusing_workspace),
        args.force,
    )
    write_file(
        workspace / f"工作状态-{date.today().isoformat()}.md",
        status_md(args.novel_name, args.protagonist, existing_context, reusing_workspace),
        args.force,
    )
    write_file(workspace / f"{args.novel_name}-黄金前三章总判断.md", total_judgment_placeholder(args.novel_name), args.force)
    write_file(workspace / f"{args.novel_name}-第一章拆解.md", chapter_placeholder(args.novel_name, 1), args.force)
    write_file(workspace / f"{args.novel_name}-第二章拆解.md", chapter_placeholder(args.novel_name, 2), args.force)
    write_file(workspace / f"{args.novel_name}-第三章拆解.md", chapter_placeholder(args.novel_name, 3), args.force)
    write_file(workspace / f"{args.novel_name}-开篇钩子与读者承诺.md", hook_placeholder(args.novel_name), args.force)
    write_file(workspace / f"{args.novel_name}-开篇问题与修改建议.md", issues_placeholder(args.novel_name), args.force)
    refresh_workspace_status(workspace, args.novel_name, args.protagonist)

    print(f"workspace initialized: {workspace}")
    print(f"source copied: {copied_source}")
    if md_source and md_source.resolve() != copied_source.resolve():
        print(f"markdown source: {md_source}")
    if existing_context:
        for key, path in existing_context.items():
            print(f"reused {key}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
