#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path


DEFAULT_WORKSPACES = (
    "刀笼",
    "寇道",
    "巫师世界",
    "序列大明",
    "我的诡异人生",
    "永恒剑主",
    "玄浑道章",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Organize workspace files without breaking validator/orchestrator paths.")
    parser.add_argument(
        "--project-root",
        default=Path(__file__).resolve().parents[1],
        help="Project root. Defaults to repo root.",
    )
    parser.add_argument(
        "--workspaces",
        nargs="*",
        default=list(DEFAULT_WORKSPACES),
        help="Workspace names to organize.",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def latest_status_file(workspace: Path) -> Path | None:
    candidates = sorted(workspace.glob("工作状态-*.md"))
    return candidates[-1] if candidates else None


def detect_protagonist_name(workspace: Path, status: dict) -> str | None:
    name = status.get("protagonist_name")
    if name:
        return str(name)
    cards = sorted(workspace.glob("*-最终人物卡.md"))
    if cards:
        return cards[0].stem.removesuffix("-最终人物卡")
    return None


def parse_legacy_progress(path: Path) -> dict:
    payload: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        payload[key.strip()] = value.strip()
    return payload


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def migrate_distillation_artifacts(workspace: Path) -> list[str]:
    notes: list[str] = []
    chapter_work = workspace / "work" / "chapter-distillation"
    backups_dir = chapter_work / "backups"
    ensure_dir(backups_dir)

    legacy_progress = workspace / ".distill_progress"
    if legacy_progress.exists():
        target = chapter_work / "legacy-progress.txt"
        if not target.exists() or target.read_text(encoding="utf-8", errors="ignore") != legacy_progress.read_text(
            encoding="utf-8", errors="ignore"
        ):
            shutil.move(str(legacy_progress), str(target))
        else:
            legacy_progress.unlink()

        progress_json = chapter_work / "progress.json"
        if not progress_json.exists():
            parsed = parse_legacy_progress(target)
            next_seq = int(parsed.get("next_seq", "1") or "1")
            total = int(parsed.get("total", parsed.get("total_chapters", "0")) or "0")
            payload = {
                "total_chapters": total,
                "next_seq": next_seq,
                "last_completed_seq": max(next_seq - 1, 0),
                "completed_batches": [],
                "updated_at": datetime.now().isoformat(timespec="seconds"),
                "legacy_snapshot": parsed,
            }
            progress_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        notes.append("已迁移 `.distill_progress` 到 `work/chapter-distillation/`")

    for backup in sorted(workspace.glob("*章节蒸馏骨架.md.bak*")):
        target = backups_dir / backup.name
        if target.exists():
            backup.unlink()
        else:
            shutil.move(str(backup), str(target))
        notes.append(f"已迁移 `{backup.name}` 到 `work/chapter-distillation/backups/`")

    root_source_copies = []
    for candidate in sorted(workspace.glob("*.md")) + sorted(workspace.glob("*.txt")):
        if candidate.name == "README.md":
            continue
        source_match = workspace / "source" / candidate.name
        if source_match.exists():
            legacy_dir = workspace / "source" / "legacy-root-copies"
            ensure_dir(legacy_dir)
            target = legacy_dir / candidate.name
            if target.exists():
                candidate.unlink()
            else:
                shutil.move(str(candidate), str(target))
            root_source_copies.append(candidate.name)
    if root_source_copies:
        notes.append(
            "已把根目录重复原文副本迁入 `source/legacy-root-copies/`："
            + "、".join(root_source_copies)
        )

    return notes


def sorted_names(paths: list[Path]) -> list[str]:
    return sorted(path.name for path in paths)


def list_layer_files(workspace: Path, novel_name: str, protagonist_name: str | None) -> dict[str, list[str]]:
    layer_files: dict[str, list[str]] = {}
    layer_files["chapter_distillation"] = sorted_names(
        [
            path
            for path in [
                workspace / "chapter-distillation-manifest.json",
                workspace / f"{novel_name}-章节蒸馏骨架.md",
                workspace / f"{novel_name}-阶段骨架与换挡草图.md",
                workspace / f"{novel_name}-校准与验证锚点.md",
                workspace / f"{novel_name}-章节蒸馏校验报告.md",
            ]
            if path.exists()
        ]
    )
    layer_files["opening"] = sorted_names(
        [
            path
            for path in [
                workspace / f"{novel_name}-黄金前三章总判断.md",
                workspace / f"{novel_name}-第一章拆解.md",
                workspace / f"{novel_name}-第二章拆解.md",
                workspace / f"{novel_name}-第三章拆解.md",
                workspace / f"{novel_name}-开篇钩子与读者承诺.md",
                workspace / f"{novel_name}-开篇问题与修改建议.md",
                workspace / f"{novel_name}-黄金前三章校验报告.md",
            ]
            if path.exists()
        ]
    )
    protagonist_candidates = [
        workspace / f"{novel_name}-项目启动清单.md",
        workspace / f"{novel_name}-主角锚点与骨架.md",
        workspace / f"{novel_name}-主角结构摘要.md",
        workspace / f"{novel_name}-整书粗阶段划分.md",
        workspace / f"{novel_name}-主角百科校验报告.md",
        workspace / f"{novel_name}-全书精华总结.md",
    ]
    if protagonist_name:
        protagonist_candidates.extend(
            [
                workspace / f"{protagonist_name}-最终人物卡.md",
                workspace / f"{protagonist_name}-核心体系总览.md",
                workspace / f"{protagonist_name}-词条总索引.md",
            ]
        )
    layer_files["protagonist"] = sorted_names([path for path in protagonist_candidates if path.exists()])
    layer_files["protagonist_lexicon"] = sorted_names(sorted(workspace.glob(f"{protagonist_name}-*词条总结.md"))) if protagonist_name else []
    layer_files["supporting_cast"] = sorted_names(
        [
            path
            for path in [
                workspace / f"{novel_name}-重要配角Top10总表.md",
                workspace / f"{novel_name}-重要配角AI复核结论.md",
                workspace / f"{novel_name}-重要配角与主角关系图.md",
                workspace / f"{novel_name}-重要配角阶段作用分布.md",
                workspace / f"{novel_name}-重要配角层校验报告.md",
            ]
            if path.exists()
        ]
    )
    layer_files["outline"] = sorted_names(
        [
            path
            for path in [
                workspace / f"{novel_name}-大纲总览.md",
                workspace / f"{novel_name}-阶段与篇章拆分.md",
                workspace / f"{novel_name}-主线支线与冲突地图.md",
                workspace / f"{novel_name}-核心冲突点与爆发点.md",
                workspace / f"{novel_name}-时间与地点转折.md",
                workspace / f"{novel_name}-核心配角与主角关系.md",
                workspace / f"{novel_name}-高潮节奏与收束诊断.md",
                workspace / f"{novel_name}-结构问题与修改建议.md",
                workspace / f"{novel_name}-大纲分析校验报告.md",
            ]
            if path.exists()
        ]
    )
    layer_files["highlight"] = sorted_names(
        [
            path
            for path in [
                workspace / f"{novel_name}-最吸引人的十个剧情细节总表.md",
                workspace / f"{novel_name}-剧情吸引力机制分析.md",
                workspace / f"{novel_name}-Top10细节逐条拆解.md",
                workspace / f"{novel_name}-高光桥段分布与节奏判断.md",
                workspace / f"{novel_name}-最强爽点痛点悬念点总结.md",
                workspace / f"{novel_name}-剧情高光改造建议.md",
                workspace / f"{novel_name}-剧情高光校验报告.md",
            ]
            if path.exists()
        ]
    )
    return layer_files


def format_list(items: list[str]) -> list[str]:
    return [f"- `{item}`" for item in items] if items else ["- 无"]


def write_source_readme(workspace: Path, novel_name: str) -> bool:
    source_dir = workspace / "source"
    if not source_dir.exists():
        return False
    files = sorted(path.name for path in source_dir.iterdir() if path.name != "README.md")
    md_files = [name for name in files if name.lower().endswith(".md")]
    txt_files = [name for name in files if name.lower().endswith(".txt")]
    canonical = f"{novel_name}.md" if (source_dir / f"{novel_name}.md").exists() else (md_files[0] if md_files else (txt_files[0] if txt_files else None))
    lines = [
        f"# 《{novel_name}》source 目录说明",
        "",
        "本目录用于存放原文、转换稿和历史副本。",
        "",
        f"- 当前推荐主入口：`{canonical}`" if canonical else "- 当前推荐主入口：未识别",
        f"- Markdown 文件数：`{len(md_files)}`",
        f"- 纯文本文件数：`{len(txt_files)}`",
        "",
        "## 文件列表",
        "",
    ]
    lines.extend(format_list(files))
    lines.extend(
        [
            "",
            "## 约定",
            "",
            "- 优先使用 `<小说名>.md` 作为统一分析入口。",
            "- 历史副本或平台导出稿可以保留，但不应作为默认引用入口。",
            "- `legacy-root-copies/` 用于收纳从工作区根目录迁回的旧原文副本。",
            "",
        ]
    )
    (source_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return True


def write_work_readme(workspace: Path, novel_name: str) -> bool:
    work_dir = workspace / "work"
    if not work_dir.exists():
        return False
    entries = sorted(path.name for path in work_dir.iterdir() if path.name != "README.md")
    lines = [
        f"# 《{novel_name}》work 目录说明",
        "",
        "本目录存放中间缓存、抽取结果和可重建产物，不作为正式阅读入口。",
        "",
        "## 当前条目",
        "",
    ]
    lines.extend(format_list(entries))
    lines.extend(
        [
            "",
            "## 约定",
            "",
            "- `chapter-distillation/`：章节蒸馏续跑状态、批次缓存、备份。",
            "- `chunks.json` / `chunks/`：原文切块结果。",
            "- `extractions.json` / `extractions/`：角色或信息抽取中间结果。",
            "- `cards/`、`merged/`：角色卡流水线的中间或导出结果。",
            "- 本目录内容允许重建，不应替代根目录正式分析文件。",
            "",
        ]
    )
    (work_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return True


def write_supporting_cast_readme(workspace: Path, novel_name: str) -> bool:
    sc_dir = workspace / "supporting-cast"
    if not sc_dir.exists():
        return False

    entries = sorted(path.name for path in sc_dir.iterdir() if path.name != "README.md")
    profile_names = sorted(path.stem for path in sc_dir.glob("*-配角分析.md") if path.is_file())
    lines = [
        f"# 《{novel_name}》supporting-cast 目录说明",
        "",
        "本目录存放重要配角层的目录化产物，便于把 Top10 配角卡与关系材料集中阅读。",
        "",
        "- 推荐入口：`index.md`" if (sc_dir / "index.md").exists() else "- 推荐入口：`index.md` 当前缺失",
        f"- 配角分析卡数：`{len(profile_names)}`",
        "",
        "## 当前条目",
        "",
    ]
    lines.extend(format_list(entries))
    lines.extend(
        [
            "",
            "## 约定",
            "",
            "- `index.md` 作为本目录总入口，优先从这里进入。",
            "- `*-配角分析.md` 为单个配角分析卡。",
            "- `Top10候选池初评.md` 等文件用于候选池或筛选过程记录。",
            "- 根目录中的 `《小说名》-重要配角*.md` 仍然是正式交付产物。",
            "",
        ]
    )
    (sc_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return True


def latest_status_name(workspace: Path) -> str:
    latest = latest_status_file(workspace)
    return latest.name if latest else "无"


def count_glob(workspace: Path, pattern: str) -> int:
    return len(list(workspace.glob(pattern)))


def build_workspace_files_index(workspace: Path, status: dict) -> str:
    novel_name = status.get("novel_name") or workspace.name
    protagonist_name = detect_protagonist_name(workspace, status)
    layer_files = list_layer_files(workspace, novel_name, protagonist_name)
    quality_files = sorted_names(sorted(workspace.glob("*质量门报告.md")))
    diagnostic_files = sorted_names(sorted(workspace.glob("*首轮诊断报告.md")))
    legacy_alias_files = []
    if (workspace / "全书精华总结.md").exists() and (workspace / f"{novel_name}-全书精华总结.md").exists():
        legacy_alias_files.append("全书精华总结.md")

    structural_dirs = [name for name in ("source", "supporting-cast", "work") if (workspace / name).exists()]
    historical_dirs = []
    if (workspace / "work_backup_heuristic").exists():
        historical_dirs.append("work_backup_heuristic")
    historical_dirs.extend(sorted(path.name for path in workspace.glob("focus-*") if path.is_dir()))
    historical_dirs.extend(sorted(path.name for path in workspace.glob("novel-run*") if path.is_dir()))

    status_files = [
        name
        for name in [
            "workspace-status.json",
            "workspace-gap-report.md",
            "workspace-repair-plan.md",
            "工作区流程判断报告.md",
        ]
        if (workspace / name).exists()
    ]
    status_files.extend(sorted_names(sorted(workspace.glob("工作状态-*.md"))))
    status_files.extend(sorted_names(sorted(workspace.glob("workspace-context-*.md"))))
    status_files = sorted(set(status_files))

    known_root_files = {"README.md", "WORKSPACE_FILES.md"}
    for items in layer_files.values():
        known_root_files.update(items)
    known_root_files.update(quality_files)
    known_root_files.update(diagnostic_files)
    known_root_files.update(legacy_alias_files)
    known_root_files.update(status_files)

    other_root_files = sorted(
        path.name
        for path in workspace.iterdir()
        if path.is_file() and path.name not in known_root_files
    )
    other_root_dirs = sorted(
        path.name
        for path in workspace.iterdir()
        if path.is_dir() and path.name not in set(structural_dirs) | set(historical_dirs)
    )

    lines = [
        f"# {novel_name} 根目录文件索引",
        "",
        "本索引用于把工作区根目录下的正式产物、状态文件、目录入口和历史目录分开查看。",
        "",
        "## 目录入口",
        "",
    ]
    lines.extend(format_list(structural_dirs))
    lines.extend(
        [
            "",
            "## 正式产物",
            "",
            "### 章节蒸馏层",
            *format_list(layer_files["chapter_distillation"]),
            "",
            "### 黄金前三章层",
            *format_list(layer_files["opening"]),
            "",
            "### 主角百科层",
            *format_list(layer_files["protagonist"]),
            "",
            "### 主角词条资产",
            *format_list(layer_files["protagonist_lexicon"]),
            "",
            "### 重要配角层",
            *format_list(layer_files["supporting_cast"]),
            "",
            "### 整书大纲层",
            *format_list(layer_files["outline"]),
            "",
            "### 剧情高光层",
            *format_list(layer_files["highlight"]),
            "",
            "## 综合校验与质量门",
            "",
            *format_list(quality_files),
            "",
            "## 状态与交接文件",
            "",
        ]
    )
    lines.extend(format_list(status_files))
    if diagnostic_files:
        lines.extend(
            [
                "",
                "## 历史诊断文件",
                "",
            ]
        )
        lines.extend(format_list(diagnostic_files))
    if legacy_alias_files:
        lines.extend(
            [
                "",
                "## 历史别名文件",
                "",
            ]
        )
        lines.extend(format_list(legacy_alias_files))
    lines.extend(
        [
            "",
            "## 历史目录与中间目录",
            "",
        ]
    )
    lines.extend(format_list(historical_dirs))
    if other_root_dirs:
        lines.extend(
            [
                "",
                "## 其他根目录目录",
                "",
            ]
        )
        lines.extend(format_list(other_root_dirs))
    if other_root_files:
        lines.extend(
            [
                "",
                "## 其他根目录文件",
                "",
            ]
        )
        lines.extend(format_list(other_root_files))
    lines.extend(
        [
            "",
            "## 说明",
            "",
            "- `README.md` 负责工作区说明与分层导航。",
            "- `WORKSPACE_FILES.md` 负责根目录文件归类，不替代正式内容本身。",
            "- 未被纳入正式产物分层的根目录文件，会保留在“其他根目录文件/目录”里，便于后续继续清理。",
            "",
        ]
    )
    return "\n".join(lines)


def build_readme(workspace: Path, status: dict, migration_notes: list[str]) -> str:
    novel_name = status.get("novel_name") or workspace.name
    protagonist_name = detect_protagonist_name(workspace, status)
    layer_files = list_layer_files(workspace, novel_name, protagonist_name)
    quality_files = sorted_names(sorted(workspace.glob("*质量门报告.md")))
    diagnostic_files = sorted_names(sorted(workspace.glob("*首轮诊断报告.md")))
    legacy_alias_files = []
    if (workspace / "全书精华总结.md").exists() and (workspace / f"{novel_name}-全书精华总结.md").exists():
        legacy_alias_files.append("全书精华总结.md")
    completed = ", ".join(status.get("completed_layers", [])) or "无"
    incomplete = ", ".join(status.get("incomplete_layers", [])) or "无"
    recommended_mode = status.get("recommended_mode", "未知")
    recommended_layer = status.get("recommended_next_layer", "未知")
    recommended_skill = status.get("recommended_skill", "未知")
    recommended_step = status.get("recommended_next_step", "未知")
    latest = latest_status_file(workspace)
    context_files = sorted_names(sorted(workspace.glob("workspace-context-*.md")))
    source_files = (
        sorted(path.name for path in (workspace / "source").iterdir() if path.name != "README.md")
        if (workspace / "source").exists()
        else []
    )
    supporting_profiles = count_glob(workspace / "supporting-cast", "*-配角分析.md") if (workspace / "supporting-cast").exists() else 0

    lines = [
        f"# {novel_name} 工作区说明",
        "",
        f"本目录是《{novel_name}》的独立工作区。正式产物继续保留在根目录，便于现有 validator / orchestrator 直接识别；中间缓存统一收纳到 `work/`。",
        "",
        "## 快速入口",
        "",
        f"- 最新交接：`{latest.name}`" if latest else "- 最新交接：无",
        "- 机器状态：`workspace-status.json`",
        "- 根目录索引：`WORKSPACE_FILES.md`",
        "- 差距报告：`workspace-gap-report.md`",
        "- 修复计划：`workspace-repair-plan.md`",
        "- 流程判断：`工作区流程判断报告.md`",
        "",
        "## 当前状态摘要",
        "",
        f"- 主角：`{protagonist_name or '未识别'}`",
        f"- 已达标层：`{completed}`",
        f"- 待修层：`{incomplete}`",
        f"- 推荐模式：`{recommended_mode}`",
        f"- 推荐下一层：`{recommended_layer}`",
        f"- 推荐 skill：`{recommended_skill}`",
        f"- 当前建议：{recommended_step}",
        "",
        "## 目录分层",
        "",
        "- `source/`",
        f"  原文与转换稿，共 {len(source_files)} 个条目。",
        "- `supporting-cast/`",
        f"  重要配角分析目录，当前 {supporting_profiles} 份配角卡。",
        "- `work/`",
        "  中间运行产物、抽取缓存、章节蒸馏续跑状态。",
    ]
    if (workspace / "work_backup_heuristic").exists():
        lines.extend(
            [
                "- `work_backup_heuristic/`",
                "  历史启发式抽取备份，保留但不作为正式入口。",
            ]
        )
    focus_dirs = sorted(path.name for path in workspace.glob("focus-*") if path.is_dir())
    if focus_dirs:
        lines.extend(
            [
                "- `focus-<主角名>/`",
                f"  主角卡抽取阶段缓存目录：`{', '.join(focus_dirs)}`。",
            ]
        )
    lines.extend(
        [
            "",
            "## 正式产物分层",
            "",
            "### 章节蒸馏层",
            *format_list(layer_files["chapter_distillation"]),
            "",
            "### 黄金前三章层",
            *format_list(layer_files["opening"]),
            "",
            "### 主角百科层",
            *format_list(layer_files["protagonist"]),
            "",
            "### 主角词条资产",
            *format_list(layer_files["protagonist_lexicon"]),
            "",
            "### 重要配角层",
            *format_list(layer_files["supporting_cast"]),
            "- `supporting-cast/index.md`" if (workspace / "supporting-cast/index.md").exists() else "- `supporting-cast/` 目录索引缺失",
            "",
            "### 整书大纲层",
            *format_list(layer_files["outline"]),
            "",
            "### 剧情高光层",
            *format_list(layer_files["highlight"]),
            "",
            "### 综合校验与质量门",
            *format_list(quality_files),
            "",
            "### 历史诊断文件",
            *format_list(diagnostic_files),
            "",
            "### 历史别名文件",
            *format_list(legacy_alias_files),
            "",
            "## 状态与交接文件",
            "",
            "- `workspace-status.json`",
            "- `workspace-gap-report.md`" if (workspace / "workspace-gap-report.md").exists() else "- `workspace-gap-report.md` 缺失",
            "- `workspace-repair-plan.md`" if (workspace / "workspace-repair-plan.md").exists() else "- `workspace-repair-plan.md` 缺失",
            "- `工作区流程判断报告.md`" if (workspace / "工作区流程判断报告.md").exists() else "- `工作区流程判断报告.md` 缺失",
            f"- 最新 `工作状态-YYYY-MM-DD.md`：`{latest_status_name(workspace)}`",
            *format_list(context_files),
            "",
            "## 中间产物与缓存",
            "",
            f"- `work/` 下已有 {count_glob(workspace / 'work', '*') if (workspace / 'work').exists() else 0} 个一级条目",
            "- `work/chapter-distillation/` 用于章节蒸馏续跑、批次缓存、备份" if (workspace / "work/chapter-distillation").exists() else "- `work/chapter-distillation/` 当前未建立",
        ]
    )
    root_run_dirs = sorted(path.name for path in workspace.glob("novel-run*") if path.is_dir())
    if root_run_dirs:
        lines.append(f"- 根目录历史运行目录：`{', '.join(root_run_dirs)}`")
    if migration_notes:
        lines.extend(["", "## 本次整理动作", ""])
        lines.extend([f"- {note}" for note in migration_notes])
    lines.extend(
        [
            "",
            "## 文件约定",
            "",
            "- 根目录：正式分析产物与状态文件，保持对现有脚本的兼容。",
            "- `source/`：原文和转换稿。",
            "- `supporting-cast/`：配角层专用目录。",
            "- `work/`：所有中间缓存、历史备份、续跑状态。",
            "- `work_backup_heuristic/`：历史备份，不作为当前正式入口。",
            "",
        ]
    )
    return "\n".join(lines)


def build_workspace_index(entries: list[dict]) -> str:
    lines = [
        "# 工作区总览",
        "",
        "按统一目录约定整理后的工作区入口索引。",
        "",
        "| 工作区 | 主角 | 已达标层 | 待修层 | 推荐下一层 | 最新工作状态 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for entry in entries:
        lines.append(
            f"| `{entry['workspace']}` | `{entry['protagonist']}` | `{entry['completed']}` | `{entry['incomplete']}` | `{entry['next_layer']}` | `{entry['latest_status']}` |"
        )
    lines.extend(
        [
            "",
            "## 目录约定",
            "",
            "- 根目录保留正式产物，便于现有 workflow 脚本识别。",
            "- `source/` 保留原文与转换稿。",
            "- `supporting-cast/` 保留配角层目录化产物。",
            "- `work/` 统一收纳抽取缓存、章节蒸馏续跑状态与备份。",
            "",
        ]
    )
    return "\n".join(lines)


def ensure_supporting_cast_index(workspace: Path, novel_name: str) -> bool:
    sc_dir = workspace / "supporting-cast"
    if not sc_dir.exists():
        return False
    index_path = sc_dir / "index.md"
    if index_path.exists():
        return False

    profile_names = sorted(
        path.stem
        for path in sc_dir.glob("*-配角分析.md")
        if path.is_file()
    )
    lines = [
        "# 重要配角分析索引",
        "",
        "## 入口文件",
        "",
    ]
    for name in (
        f"{novel_name}-重要配角Top10总表.md",
        f"{novel_name}-重要配角与主角关系图.md",
        f"{novel_name}-重要配角阶段作用分布.md",
        f"{novel_name}-重要配角层校验报告.md",
    ):
        if (workspace / name).exists():
            lines.append(f"- [{name}](../{name})")
    if (sc_dir / "Top10候选池初评.md").exists():
        lines.append("- [Top10候选池初评.md](Top10候选池初评.md)")

    lines.extend(["", "## 配角卡列表", ""])
    if profile_names:
        lines.extend(f"- [[{name}]]" for name in profile_names)
    else:
        lines.append("- 暂无配角卡")

    lines.extend(
        [
            "",
            "## 推荐阅读顺序",
            "",
            "1. 先看候选池或 Top10 总表",
            "2. 再看关系图与阶段作用分布",
            "3. 最后逐个进入配角分析卡",
            "",
        ]
    )
    index_path.write_text("\n".join(lines), encoding="utf-8")
    return True


def organize_workspace(workspace: Path) -> dict:
    status = read_json(workspace / "workspace-status.json")
    novel_name = status.get("novel_name") or workspace.name
    migration_notes = migrate_distillation_artifacts(workspace)
    if ensure_supporting_cast_index(workspace, novel_name):
        migration_notes.append("已补齐 `supporting-cast/index.md`")
    if write_supporting_cast_readme(workspace, novel_name):
        migration_notes.append("已刷新 `supporting-cast/README.md`")
    if write_source_readme(workspace, novel_name):
        migration_notes.append("已刷新 `source/README.md`")
    if write_work_readme(workspace, novel_name):
        migration_notes.append("已刷新 `work/README.md`")
    (workspace / "WORKSPACE_FILES.md").write_text(build_workspace_files_index(workspace, status) + "\n", encoding="utf-8")
    migration_notes.append("已刷新 `WORKSPACE_FILES.md`")
    readme = build_readme(workspace, status, migration_notes)
    (workspace / "README.md").write_text(readme + "\n", encoding="utf-8")

    protagonist = detect_protagonist_name(workspace, status) or "未识别"
    return {
        "workspace": workspace.name,
        "protagonist": protagonist,
        "completed": ", ".join(status.get("completed_layers", [])) or "无",
        "incomplete": ", ".join(status.get("incomplete_layers", [])) or "无",
        "next_layer": status.get("recommended_next_layer", "未知"),
        "latest_status": latest_status_name(workspace),
    }


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve()
    summaries: list[dict] = []

    for name in args.workspaces:
        workspace = project_root / name
        if not workspace.is_dir():
            continue
        summaries.append(organize_workspace(workspace))

    (project_root / "docs" / "WORKSPACE_INDEX.md").write_text(
        build_workspace_index(summaries) + "\n",
        encoding="utf-8",
    )
    print(f"organized {len(summaries)} workspaces")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
