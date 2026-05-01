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
    outline_patterns = ["*-大纲总览.md", "*-阶段与篇章拆分.md"]
    opening_patterns = ["*-黄金前三章总判断.md", "*-开篇钩子与读者承诺.md"]
    if protagonist:
        protagonist_patterns.append(f"{protagonist}-最终人物卡.md")
        index_patterns.append(f"{protagonist}-词条总索引.md")
    protagonist_patterns.extend(["*-最终人物卡.md", "*主角结构摘要.md"])
    index_patterns.extend(["*-词条总索引.md", "*-角色总索引.md"])
    found = {
        "protagonist_file": find_first(workspace, protagonist_patterns),
        "index_file": find_first(workspace, index_patterns),
        "outline_file": find_first(workspace, outline_patterns),
        "opening_file": find_first(workspace, opening_patterns),
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
        "outline_file": "整书大纲层文件",
        "opening_file": "开篇分析层文件",
    }
    lines = []
    for key in ("protagonist_file", "index_file", "outline_file", "opening_file"):
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
        "- 当前模式说明：在已有小说工作区基础上扩展剧情高光分析层。\n"
        if reusing_workspace
        else "- 当前模式说明：当前目录是独立初始化的剧情高光分析工作区。\n"
    )
    return f"""# {novel_name} 剧情高光分析工作区说明

本目录是《{novel_name}》的剧情高光分析工作区。

## 当前结构

- `source/{copied_source.name}`
  原始文本副本
{md_line}- `{novel_name}-最吸引人的十个剧情细节总表.md`
  全书 Top 10 高光剧情总表
- `{novel_name}-剧情吸引力机制分析.md`
  全书高光桥段的主要吸引力机制
- `{novel_name}-Top10细节逐条拆解.md`
  Top 10 高光细节的逐条拆解
- `{novel_name}-高光桥段分布与节奏判断.md`
  高光桥段在整本书中的分布判断
- `{novel_name}-最强爽点痛点悬念点总结.md`
  读者快感、痛感与悬念的强点总结
- `{novel_name}-剧情高光改造建议.md`
  高光桥段的保护、增强与改造建议
- `工作状态-{date.today().isoformat()}.md`
  当前项目级交接文件

## 当前入口

- `README.md`
- `工作状态-{date.today().isoformat()}.md`
- `{novel_name}-最吸引人的十个剧情细节总表.md`
- `{novel_name}-剧情吸引力机制分析.md`
- `{novel_name}-剧情高光改造建议.md`

## 当前说明

{protagonist_line}- 当前工作区刚初始化完成，以上 highlight 文件默认只是占位骨架，不代表分析已完成。
{mode_line}- 默认应结合主角层、整书层和开篇层来判断哪些桥段是真正的高价值记忆点。

## 已探测到的可复用上下文文件

{reused_context_lines(existing_context)}- 下一步应先用这些文件稳定阶段、人物与 payoff 上下文，再筛选真正的 Top 10 高光桥段。
"""


def status_md(
    novel_name: str,
    protagonist: str | None,
    existing_context: dict[str, Path],
    reusing_workspace: bool,
) -> str:
    protagonist_line = f"- 当前主角：`{protagonist}`\n" if protagonist else ""
    mode_line = (
        "- 当前工作模式：在已有工作区上扩展剧情高光分析层\n"
        if reusing_workspace
        else "- 当前工作模式：新建剧情高光分析工作区骨架\n"
    )
    return f"""# 《{novel_name}》工作状态 {date.today().isoformat()}

## 当前结论

当前仅完成了剧情高光分析工作区初始化。

- `高光桥段`：未明确
- `剧情吸引力机制`：未拆清
- `高光改造优先级`：未明确

## 当前不应误判为已完成的部分

- 不应把占位文件当正式成果
- 不应把“我觉得很爽”当成高光分析完成
- 不应因为已有主角卡或大纲层存在，就误判剧情高光层已经完成

## 当前应如何继续

1. 先建立高信号剧情候选池
2. 再筛出真正的 Top 10 高光桥段
3. 判断每个桥段为什么成立
4. 判断这些桥段在整本书中的分布是否合理
5. 判断这本书最主要依赖哪种读者快感
6. 给出最值得保护和最值得补强的区段

## 下次开始时建议先看

1. `README.md`
2. `{novel_name}-最吸引人的十个剧情细节总表.md`
3. `{novel_name}-剧情吸引力机制分析.md`
4. `{novel_name}-剧情高光改造建议.md`
5. 本文件

## 一句话交接

《{novel_name}》当前只有剧情高光分析工作区骨架，还没有形成正式的 Top 10 高光判断。
{protagonist_line if protagonist else ""}
## 当前模式补充

{mode_line}
## 已探测到的可复用文件

{reused_context_lines(existing_context)}"""


def top10_table_placeholder(novel_name: str) -> str:
    lines = [
        f"# 《{novel_name}》最吸引人的十个剧情细节总表",
        "",
        "## 总判断",
        "",
        "- 待补充",
        "",
        "## Top 10 总表",
        "",
    ]
    for i in range(1, 11):
        lines.extend(
            [
                f"### 高光细节 {i}",
                "",
                "- 事件本身：待补充",
                "- 所在阶段：待补充",
                "- 吸引力类型：待补充",
                "- 主要作用：待补充",
                "",
            ]
        )
    return "\n".join(lines)


def mechanism_placeholder(novel_name: str) -> str:
    return f"""# 《{novel_name}》剧情吸引力机制分析

## 核心判断

- 待补充

## 主要吸引力机制

### 1. 反差

- 待补充

### 2. 悬念

- 待补充

### 3. 情绪兑现

- 待补充

### 4. 身份翻转 / 局势翻转

- 待补充

### 5. 世界揭露 / 规则揭露

- 待补充

## 机制换挡点

- 待补充
"""


def breakdown_placeholder(novel_name: str) -> str:
    lines = [f"# 《{novel_name}》Top10细节逐条拆解", ""]
    for i in range(1, 11):
        lines.extend(
            [
                f"## 细节 {i}",
                "",
                "- 发生位置：待补充",
                "- 事件本身：待补充",
                "- 前置铺垫：待补充",
                "- 吸引力为什么成立：待补充",
                "- 打中的读者快感：待补充",
                "- 改变了什么：待补充",
                "- 是否属于可复述型名场面：待补充",
                "",
            ]
        )
    return "\n".join(lines)


def distribution_placeholder(novel_name: str) -> str:
    return f"""# 《{novel_name}》高光桥段分布与节奏判断

## 高光分布总判断

- 待补充

## 前段高光

- 待补充

## 中段高光

- 待补充

## 后段高光

- 待补充

## 节奏判断

- 待补充
"""


def pleasure_placeholder(novel_name: str) -> str:
    return f"""# 《{novel_name}》最强爽点痛点悬念点总结

## 最强爽点

- 待补充

## 最强痛点

- 待补充

## 最强悬念点

- 待补充

## 综合判断

- 待补充
"""


def revision_placeholder(novel_name: str) -> str:
    return f"""# 《{novel_name}》剧情高光改造建议

## 当前最强高光

- 待补充

## 当前最弱区段

- 待补充

## 应该补强什么

- 待补充

## 应该前移或后移什么

- 待补充

## 应该压缩或合并什么

- 待补充
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize a durable highlight-scenes-analysis workspace.")
    parser.add_argument("--novel-name", required=True, help="Novel name used in file naming.")
    parser.add_argument("--workspace", help="Workspace directory to create or update.")
    parser.add_argument("--existing-workspace", help="Existing workspace directory to extend in place.")
    parser.add_argument("--source", help="Source text path. Optional when the workspace already has source files.")
    parser.add_argument("--protagonist", help="Known protagonist name.")
    parser.add_argument("--force", action="store_true", help="Overwrite scaffold files when they already exist.")
    args = parser.parse_args()
    if not args.workspace and not args.existing_workspace:
        parser.error("one of --workspace or --existing-workspace is required")
    return args


def main() -> int:
    args = parse_args()
    reusing_workspace = bool(args.existing_workspace)
    workspace_arg = args.existing_workspace or args.workspace
    workspace = Path(workspace_arg).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    source = Path(args.source).expanduser().resolve() if args.source else discover_existing_source(workspace)
    if not source or not source.exists():
        raise SystemExit("source not found; provide --source or ensure the workspace has a source/ file")

    copied_source = copy_source(source, workspace / "source", force=args.force)
    md_source = convert_source(copied_source, force=args.force)
    existing_context = detect_existing_context(workspace, args.protagonist)
    today = date.today().isoformat()

    write_file(
        workspace / "README.md",
        readme_md(args.novel_name, args.protagonist, copied_source, md_source, existing_context, reusing_workspace),
        force=args.force,
    )
    write_file(
        workspace / f"工作状态-{today}.md",
        status_md(args.novel_name, args.protagonist, existing_context, reusing_workspace),
        force=args.force,
    )
    write_file(
        workspace / f"{args.novel_name}-最吸引人的十个剧情细节总表.md",
        top10_table_placeholder(args.novel_name),
        force=args.force,
    )
    write_file(
        workspace / f"{args.novel_name}-剧情吸引力机制分析.md",
        mechanism_placeholder(args.novel_name),
        force=args.force,
    )
    write_file(
        workspace / f"{args.novel_name}-Top10细节逐条拆解.md",
        breakdown_placeholder(args.novel_name),
        force=args.force,
    )
    write_file(
        workspace / f"{args.novel_name}-高光桥段分布与节奏判断.md",
        distribution_placeholder(args.novel_name),
        force=args.force,
    )
    write_file(
        workspace / f"{args.novel_name}-最强爽点痛点悬念点总结.md",
        pleasure_placeholder(args.novel_name),
        force=args.force,
    )
    write_file(
        workspace / f"{args.novel_name}-剧情高光改造建议.md",
        revision_placeholder(args.novel_name),
        force=args.force,
    )
    refresh_workspace_status(workspace, args.novel_name, args.protagonist)
    print(f"initialized highlight-scenes workspace: {workspace}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
