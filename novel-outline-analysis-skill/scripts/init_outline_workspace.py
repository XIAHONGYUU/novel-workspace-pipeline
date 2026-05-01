#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


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
    if copied.exists() and not force:
        return copied
    shutil.copy2(source, copied)
    return copied


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

    text = copied_source.read_text(encoding="utf-8", errors="ignore")
    md_target.write_text(text, encoding="utf-8")
    return md_target


def readme_md(novel_name: str, protagonist: str | None, copied_source: Path, md_source: Path | None) -> str:
    protagonist_line = f"- 主角：`{protagonist}`\n" if protagonist else ""
    md_line = f"- `source/{md_source.name}`\n  转换后的 Markdown 原文\n" if md_source else ""
    return f"""# {novel_name} 工作区说明

本目录是《{novel_name}》的大纲分析工作区。

## 当前结构

- `source/{copied_source.name}`
  原始文本副本
{md_line}- `{novel_name}-大纲总览.md`
  整本小说的大纲层总判断
- `{novel_name}-阶段与篇章拆分.md`
  整书阶段与篇章边界
- `{novel_name}-主线支线与冲突地图.md`
  主线、支线与桥接线拆分
- `{novel_name}-核心冲突点与爆发点.md`
  核心冲突与关键爆发点
- `{novel_name}-时间与地点转折.md`
  时间与地点换挡分析
- `{novel_name}-高潮节奏与收束诊断.md`
  节奏、高潮与结尾判断
- `{novel_name}-结构问题与修改建议.md`
  结构优缺点与修改方向
- `{novel_name}-核心配角与主角关系.md`
  核心配角与主角的结构关系
- `工作状态-{date.today().isoformat()}.md`
  当前项目级交接文件

## 当前入口

- `README.md`
- `工作状态-{date.today().isoformat()}.md`
- `{novel_name}-大纲总览.md`
- `{novel_name}-阶段与篇章拆分.md`
- `{novel_name}-高潮节奏与收束诊断.md`

## 当前说明

{protagonist_line}- 当前工作区刚初始化完成，以上文件默认只是占位骨架，不代表分析已完成。
- 下一步应先确认主角层、核心配角关系层、阶段层、冲突爆发层、时间地点转折层是否都被实际补齐。
"""


def status_md(novel_name: str, protagonist: str | None) -> str:
    protagonist_line = f"- 当前主角：`{protagonist}`\n" if protagonist else ""
    return f"""# 《{novel_name}》工作状态 {date.today().isoformat()}

## 当前结论

当前仅完成了大纲分析工作区初始化。

- `整书大纲分析层`：未完成
- `共性标准`：未覆盖
- `单书特性`：未明确

## 当前不应误判为已完成的部分

- 不应把占位文件当正式成果
- 不应把原文复制或 txt 转 md 当作分析完成
- 不应把局部剧情摘要当作整书大纲判断

## 当前应如何继续

1. 确认主角与核心配角关系层
2. 完成整书阶段划分
3. 完成主线支线与冲突地图
4. 完成核心冲突点与爆发点
5. 完成时间与地点转折
6. 完成高潮、节奏与结尾判断
7. 识别 `2 到 4` 个单书特性
8. 做共性标准与单书特性自检

## 下次开始时建议先看

1. `README.md`
2. `{novel_name}-阶段与篇章拆分.md`
3. `{novel_name}-核心冲突点与爆发点.md`
4. 本文件

## 一句话交接

《{novel_name}》当前只有大纲分析工作区骨架，还没有形成正式的大纲层结论。
{protagonist_line if protagonist else ""}
"""


def placeholder(title: str, sections: list[str]) -> str:
    body = "\n".join(f"## {section}\n\n- 待补充\n" for section in sections)
    return f"# {title}\n\n{body}"


def protagonist_summary_placeholder(novel_name: str, protagonist: str | None) -> str:
    title = f"《{novel_name}》主角结构摘要"
    protagonist_line = f"- 主角名：`{protagonist}`\n" if protagonist else "- 主角名：待确认\n"
    return f"""# {title}

## 基本信息

{protagonist_line}- 结构角色：待补充
- 核心驱动：待补充
- 成长主梁：待补充
- 终局落点：待补充

## 说明

- 如果工作区已经有更完整的主角总卡，可用它替代本文件
- 如果没有，则至少把主角在整书结构中的作用补到可用状态
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a durable novel outline analysis workspace.")
    parser.add_argument("--novel-name", required=True, help="Novel name used for directory and file names.")
    parser.add_argument("--source", required=True, help="Absolute or relative path to the novel source file.")
    parser.add_argument("--workspace", help="Workspace directory. Defaults to ./<小说名>.")
    parser.add_argument("--protagonist", help="Known protagonist name.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing starter files.")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    if not source.exists():
        raise SystemExit(f"source not found: {source}")

    workspace = Path(args.workspace).expanduser().resolve() if args.workspace else Path.cwd() / args.novel_name
    workspace.mkdir(parents=True, exist_ok=True)

    source_dir = workspace / "source"
    copied_source = copy_source(source, source_dir, args.force)
    md_source = convert_source(copied_source, args.force)

    write_file(workspace / "README.md", readme_md(args.novel_name, args.protagonist, copied_source, md_source), args.force)
    write_file(workspace / f"工作状态-{date.today().isoformat()}.md", status_md(args.novel_name, args.protagonist), args.force)
    write_file(
        workspace / f"{args.novel_name}-大纲总览.md",
        placeholder(
            f"《{args.novel_name}》大纲总览",
            ["核心 premise", "结构类型", "全书主线一句话", "整书总判断"],
        ),
        args.force,
    )
    write_file(
        workspace / f"{args.novel_name}-阶段与篇章拆分.md",
        placeholder(
            f"《{args.novel_name}》阶段与篇章拆分",
            ["阶段划分说明", "阶段 1", "阶段 2", "阶段 3", "阶段总评"],
        ),
        args.force,
    )
    write_file(
        workspace / f"{args.novel_name}-主线支线与冲突地图.md",
        placeholder(
            f"《{args.novel_name}》主线支线与冲突地图",
            ["核心主线", "重要支线", "桥接线", "主线支线总判断"],
        ),
        args.force,
    )
    write_file(
        workspace / f"{args.novel_name}-核心冲突点与爆发点.md",
        placeholder(
            f"《{args.novel_name}》核心冲突点与爆发点",
            ["根本主冲突", "阶段性冲突", "关键爆发点", "冲突层总判断"],
        ),
        args.force,
    )
    write_file(
        workspace / f"{args.novel_name}-时间与地点转折.md",
        placeholder(
            f"《{args.novel_name}》时间与地点转折",
            ["时间转折", "地点转折", "时间与地点联合判断"],
        ),
        args.force,
    )
    write_file(
        workspace / f"{args.novel_name}-高潮节奏与收束诊断.md",
        placeholder(
            f"《{args.novel_name}》高潮节奏与收束诊断",
            ["开篇判断", "中段判断", "高潮判断", "结尾判断", "整书节奏标签"],
        ),
        args.force,
    )
    write_file(
        workspace / f"{args.novel_name}-结构问题与修改建议.md",
        placeholder(
            f"《{args.novel_name}》结构问题与修改建议",
            ["结构优点", "结构问题", "第一优先修改项", "轻修建议"],
        ),
        args.force,
    )
    write_file(
        workspace / f"{args.novel_name}-核心配角与主角关系.md",
        placeholder(
            f"《{args.novel_name}》核心配角与主角关系",
            ["核心配角清单", "关键关系类型", "关系线总判断"],
        ),
        args.force,
    )
    write_file(
        workspace / f"{args.novel_name}-主角结构摘要.md",
        protagonist_summary_placeholder(args.novel_name, args.protagonist),
        args.force,
    )
    refresh_workspace_status(workspace, args.novel_name, args.protagonist)

    print(f"workspace initialized: {workspace}")
    print(f"source copied: {copied_source}")
    if md_source:
        print(f"markdown source: {md_source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
