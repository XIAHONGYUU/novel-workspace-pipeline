#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
import json
import os
import re
import subprocess
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run_cmd(cmd: list[str], env: dict[str, str] | None = None) -> None:
    subprocess.run(cmd, check=True, env=env)


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


STOPWORDS = {
    "只是", "顿时", "此时", "居然", "若是", "仿佛", "忽然", "却是", "直接", "还有",
    "女子", "都是", "无数", "也是", "其中", "而是", "狠狠", "已经", "整个", "你们",
    "或许", "其余", "甚至", "所有", "显然", "而且", "根本", "怕是", "只有", "可以",
    "便是", "里面", "心头", "露出", "一道", "只要", "就是", "还是", "不断", "实际",
    "最后", "瞬间", "自然", "全部", "如同", "对方", "众人", "一切", "巨大", "赶紧",
    "应该", "不知", "其实", "同时", "之后", "几乎", "一路", "仔细", "只能", "大哥",
    "剑刃", "迅速", "画师", "黑影", "强大", "空间", "生命之火", "材料", "火焰",
    "感觉", "渐渐", "可惜", "风暴", "反而", "此事", "为何", "召唤",
}

GENERIC_NAMES = {
    "女子", "老者", "少年", "黑衣人", "红衣女", "女修", "师兄", "师叔", "师祖",
    "胖子", "五叔", "娘亲", "庄主", "道祖", "师尊", "大妖尊",
}


def is_cjk(text: str) -> bool:
    return all("\u4e00" <= ch <= "\u9fff" for ch in text)


def looks_like_person_name(name: str) -> bool:
    name = name.strip()
    if not name:
        return False
    if "http" in name.lower() or "/" in name or ":" in name or "下载" in name:
        return False
    if any(ch.isdigit() for ch in name):
        return False
    if len(name) < 2 or len(name) > 6:
        return False
    if name in STOPWORDS or name in GENERIC_NAMES:
        return False
    if not is_cjk(name):
        return False
    if name.endswith(("一下", "起来", "下去", "起来", "而已")):
        return False
    return True


def count_text_mentions(text: str, name: str) -> int:
    return text.count(name)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_first_pass_report(workspace: Path, novel_name: str, source_text: str) -> Path:
    work_dir = workspace / "work"
    merged_path = work_dir / "merged" / "characters.json"
    index_path = work_dir / "cards" / "index.md"
    extractions_dir = work_dir / "extractions"
    chunks_dir = work_dir / "chunks"
    report_path = workspace / f"{novel_name}-首轮诊断报告.md"

    merged = load_json(merged_path) if merged_path.exists() else []
    candidates = []
    invalid_count = 0
    for item in merged:
        if not isinstance(item, dict):
            continue
        name = (item.get("name") or "").strip()
        if not name:
            continue
        score = item.get("mention_count") or count_text_mentions(source_text, name)
        if looks_like_person_name(name):
            candidates.append((name, int(score), item.get("aliases") or []))
        else:
            invalid_count += 1

    candidates.sort(key=lambda x: (-x[1], x[0]))
    top_candidates = candidates[:10]

    index_names = []
    if index_path.exists():
        for line in index_path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"- \[\[(.+?)\]\]", line.strip())
            if m:
                index_names.append(m.group(1))
    index_sample = index_names[:100]
    invalid_in_index = [name for name in index_sample if not looks_like_person_name(name)]
    index_noise_ratio = (len(invalid_in_index) / len(index_sample)) if index_sample else 1.0

    extraction_sample = []
    preface_noise = False
    for path in sorted(extractions_dir.glob("chunk-*.json"))[:3]:
        data = load_json(path)
        title = data.get("title", "")
        names = [c.get("name", "") for c in data.get("characters", []) if isinstance(c, dict)]
        extraction_sample.append((path.name, title, names[:5]))
        if title in {"前言", "序章", "楔子"} and any(not looks_like_person_name(name) for name in names[:5]):
            preface_noise = True

    chunk_titles = []
    for path in sorted(chunks_dir.glob("chunk-*.json"))[:12]:
        data = load_json(path)
        chunk_titles.append(data.get("title", ""))

    recommendation = "建议立即跑 focus"
    if not top_candidates:
        recommendation = "首轮结果不足，建议先人工确认主角再跑 focus"
    elif index_noise_ratio > 0.35 or preface_noise:
        recommendation = f"heuristic 噪声较高，但主角候选最像 `{top_candidates[0][0]}`，建议立即对其跑 focus"

    status_lines = [
        "- [x] 整书 chunk 蒸馏已完成",
        "- [ ] 整书阶段划分已完成",
        "- [ ] 主角锚点已稳定",
        "- [ ] 主角总卡已完成",
        "- [ ] 一级词条已齐",
        "- [ ] 总索引已完成",
        "- [ ] 核心体系总览已完成",
        "- [ ] 全书精华总结已完成",
        "- [ ] 最关键的一批二级词条已完成",
    ]

    top_lines = "\n".join(
        f"- `{name}`：文本粗提及约 `{score}` 次；别称：{', '.join(aliases) if aliases else '无'}"
        for name, score, aliases in top_candidates
    ) or "- 暂无稳定候选"

    extraction_lines = "\n".join(
        f"- `{fname}` / `{title}` -> {', '.join(names) if names else '无候选'}"
        for fname, title, names in extraction_sample
    ) or "- 无"

    quality = "较差"
    if index_noise_ratio < 0.15 and not preface_noise:
        quality = "可用"
    elif index_noise_ratio < 0.35:
        quality = "一般"

    content = f"""# 《{novel_name}》首轮诊断报告

## 一、结论

这轮自动执行已经完成了工作区初始化、`txt -> md` 和首轮 heuristic pipeline，但首轮人物抽取结果的可用性需要单独判断。

当前判断：`{quality}`

下一步建议：{recommendation}

## 二、主角候选 Top 10

{top_lines}

## 三、heuristic 质量检查

- 合并后候选总数：`{len(merged)}`
- 过滤后较像人名的候选数：`{len(candidates)}`
- 前 100 个索引项中的疑似噪声比例：`{index_noise_ratio:.0%}`
- 是否检测到前言 / 序章污染：`{'是' if preface_noise else '否'}`

## 四、前几个抽取块的直接样本

{extraction_lines}

## 五、前 12 个 chunk 标题

{chr(10).join(f"- {title}" for title in chunk_titles) if chunk_titles else '- 无'}

## 六、当前 checklist 状态

{chr(10).join(status_lines)}

## 七、解释

这轮首要问题通常出在两处：

- `heuristic` 会把副词、泛称、前言噪声一起当成人名候选
- 首轮自动结果虽然能摸到主角候选，但还不能直接代替主角骨架判断

所以首轮真正的价值应该是：

- 判断主角最可能是谁
- 判断结果噪声是否可接受
- 决定是否立刻进入 `focus` 阶段
"""
    write_file(report_path, content)
    return report_path


def checklist_md(novel_name: str) -> str:
    return f"""# {novel_name} 项目启动清单

## 目标

将《{novel_name}》建立为一套以主角为中心的全词条百科资料，而不是平铺式人物索引。

## 体系闭环 Checklist

- [ ] 整书 chunk 蒸馏已完成
- [ ] 整书阶段划分已完成
- [ ] 主角锚点已稳定
- [ ] 主角总卡已完成
- [ ] 一级词条已齐
- [ ] 总索引已完成
- [ ] 核心体系总览已完成
- [ ] 全书精华总结已完成
- [ ] 最关键的一批二级词条已完成
- [ ] 索引中已区分一级、二级和当前完成度
- [ ] 现有词条之间已能互相解释

## 首轮执行顺序

1. 确认原文文件与工作区路径
2. 完成 txt -> md 转换
3. 完成 chunk 蒸馏与基础抽取
4. 产出整书粗阶段划分
5. 确认主角锚点
6. 写主角锚点与骨架
7. 写主角最终人物卡
8. 提炼一级词条并建立总索引
9. 判断是否达到“骨架完成”
10. 写核心体系总览
11. 写全书精华总结
12. 补关键二级词条并判断是否达到“体系闭环完成”
"""


def stage_outline_md(novel_name: str) -> str:
    return f"""# 《{novel_name}》整书粗阶段划分

## 说明

本文件用于在第一轮 chunk 蒸馏时，同步给整本书做粗粒度阶段划分。

阶段划分可以同时按两种维度做：

- 时间 / 成长阶段
- 地点 / 地图阶段

## 阶段模板

### 阶段 1：待定

- 起止 chunk / 章节：
- 划分依据：
- 主角在这个阶段的状态：
- 主要地点 / 场域：
- 主要矛盾：
- 主要抬升：

### 阶段 2：待定

- 起止 chunk / 章节：
- 划分依据：
- 主角在这个阶段的状态：
- 主要地点 / 场域：
- 主要矛盾：
- 主要抬升：

### 阶段 3：待定

- 起止 chunk / 章节：
- 划分依据：
- 主角在这个阶段的状态：
- 主要地点 / 场域：
- 主要矛盾：
- 主要抬升：

### 阶段 4：待定

- 起止 chunk / 章节：
- 划分依据：
- 主角在这个阶段的状态：
- 主要地点 / 场域：
- 主要矛盾：
- 主要抬升：
"""


def anchor_md(novel_name: str) -> str:
    return f"""# 《{novel_name}》主角锚点与骨架

## 说明

本文件用于在正式拆主角人物卡和词条之前，先稳定确认主角锚点与主角骨架。

## 一、主角锚点

- 本名：
- 常见称谓：
- 化名 / 马甲：
- 易混简称：
- 关键关联名词：

## 二、当前确认依据

- 从 chunk 蒸馏结果看：
- 从 focus 追踪结果看：
- 从阶段划分看：

## 三、主角骨架草稿

### 1. 身份底座

### 2. 成长引擎

### 3. 质变路线

### 4. 高位结构

## 四、当前最值得拆的一级词条

- 身份变化
- 核心能力 / 核心手艺 / 核心外挂
- 战斗方式
- 修行 / 等级 / 高位路线
- 世界结构
- 势力与局势卷入
- 关系网
- 地域轨迹
"""


def final_card_md(protagonist_name: str) -> str:
    return f"""# {protagonist_name}

## 基本信息

- 姓名：
- 常见称谓：
- 当前确认定位：
- 开篇身份：
- 身份底座：

## 身份概述

## 关键物品

## 关键事件

## 势力归属

## 核心能力与成长引擎

## 成长阶段

## 战斗风格与行动方式

## 关键关系方向

## 活动范围与空间轨迹

## 阶段总结

## 人物特征总结

## 当前一级词条建议

## 最终结论
"""


def index_md(novel_name: str, protagonist_name: str) -> str:
    return f"""# {protagonist_name}词条总索引

## 说明

本索引用于汇总当前已经为主角建立的核心入口文件，并固定后续词条扩展方向。

当前阶段的目标，不是把所有词条一次性铺满，而是先把主梁、一级词条和第一批高价值二级词条钉稳。

## 一、主人物卡

- [{protagonist_name}-最终人物卡.md]({protagonist_name}-最终人物卡.md)

## 二、核心总览文件

- [{novel_name}-主角锚点与骨架.md]({novel_name}-主角锚点与骨架.md)
- [{novel_name}-整书粗阶段划分.md]({novel_name}-整书粗阶段划分.md)
- [{protagonist_name}-核心体系总览.md]({protagonist_name}-核心体系总览.md)
- [{novel_name}-全书精华总结.md]({novel_name}-全书精华总结.md)

## 三、当前已完成的一级词条

当前已经落地、可以直接作为骨架使用的一级词条如下：

### 1. 人物核心词条

- 待补

### 2. 力量体系词条

- 待补

### 3. 世界与高位设定词条

- 待补

### 4. 结构与关系网络词条

- 待补

## 四、当前已完成的核心二级词条

当前我认为最值得优先补完的一批二级词条，已经先落下这几条：

- 待补

## 五、当前整体结构总结

按照目前已经确认的信息，这条主角线可以先按四层理解：

- 第一层：他是谁
- 第二层：他靠什么成长
- 第三层：他变成了什么
- 第四层：他身处什么结构里

## 六、当前完成度判断

当前可以明确判断为：

- 主角锚点：待判断
- 主角总卡：待判断
- 整书粗阶段划分：待判断
- 第一批核心一级词条：待判断
- 一级词条全集：待判断
- 总索引：已建立模板
- 核心体系总览：待判断
- 全书精华总结：已建立模板
- 关键二级词条：待判断

### 当前判定：骨架完成

- 当前判断：`未完成`
- 理由：
  - 主角总卡、一级词条和总索引闭环还需补实
  - 当前只是完成了索引模板和结构入口

### 当前判定：体系闭环完成

- 当前判断：`未完成`
- 理由：
  - 核心体系总览、全书精华总结和关键二级词条还未补齐
  - 当前还不能判断主干体系已经自洽解释

## 七、推荐阅读顺序

- {novel_name}-主角锚点与骨架.md
- {novel_name}-整书粗阶段划分.md
- {protagonist_name}-最终人物卡.md
- 再按词条完成情况继续往下读

## 八、下一步执行顺序

1. 先补主角最终人物卡
2. 再补整书粗阶段划分
3. 再从人物卡反推第一批一级词条
4. 再补核心体系总览与全书精华总结
5. 最后判断是否达到骨架完成 / 体系闭环完成
"""


def core_overview_md(protagonist_name: str) -> str:
    return f"""# {protagonist_name}核心体系总览

## 说明

## 一、总骨架

## 二、人物核心结构

## 三、成长引擎

## 四、质变路线

## 五、世界与高位结构

## 六、关键模块关系

## 七、阶段性变化

## 八、最终结论
"""


def full_book_essence_md(novel_name: str) -> str:
    return f"""# 《{novel_name}》全书精华总结

## 一句话定性

## 一、这本书最核心写的是什么

## 二、主角这条线为什么成立

## 三、这本书最强的地方

## 四、这本书的结构抬升是怎么完成的

## 五、这本书真正的主意象是什么

## 六、为什么这本书值得拆成主角全词条百科

## 七、这本书真正的精华在哪里

## 最终结论
"""


def readme_md(novel_name: str, source_name: str | None) -> str:
    source_line = f"- `source/{source_name}`\n  原始文本副本" if source_name else "- `source/`\n  原始文本目录"
    return f"""# {novel_name} 工作区说明

本目录是《{novel_name}》的独立工作区。

## 当前结构

{source_line}
- `source/`
  原文与转换稿目录
- `work/`
  chunk、抽取、合并与 focus 产物目录
- `{novel_name}-项目启动清单.md`
  当前项目 checklist
- `{novel_name}-整书粗阶段划分.md`
  第一轮 chunk 蒸馏时使用的阶段划分文件
- `{novel_name}-主角锚点与骨架.md`
  主角骨架入口
- `工作状态-YYYY-MM-DD.md`
  当前项目阶段性交接文件

## 建议顺序

1. 放入原文
2. txt 转 md
3. 跑 chunk / heuristic / focus
4. 写阶段划分
5. 写主角骨架
6. 写主角总卡
7. 拆一级词条
8. 补核心体系总览与全书精华总结
"""


def workspace_status_md(novel_name: str, protagonist_name: str | None, created_focus: bool, report_created: bool, today: date) -> str:
    protagonist_line = protagonist_name or "待确认"
    report_line = "已生成首轮诊断报告" if report_created else "尚未生成首轮诊断报告"
    focus_line = "已建立主角 focus 入口" if created_focus else "尚未建立主角 focus 入口"
    return f"""# 《{novel_name}》工作状态 {today.isoformat()}

## 当前结论

《{novel_name}》当前处于初始化后的首轮推进阶段。

当前已知：

- 当前主角候选：`{protagonist_line}`
- {report_line}
- {focus_line}

## 当前已经具备的文件骨架

- 项目启动清单
- 整书粗阶段划分
- 主角锚点与骨架
- 全书精华总结模板
{"- 主角最终人物卡模板\n- 主角词条总索引模板\n- 主角核心体系总览模板" if protagonist_name else ""}

## 当前不应误判为已完成的部分

- 还不能因为工作区已初始化，就判断为 `骨架完成`
- 还不能因为有 heuristic 结果，就判断为 `体系闭环完成`
- 还不能把 `work/cards/index.md` 当作正式成果

## 下一步建议

1. 先读首轮诊断报告，确认主角候选是否稳定
2. 补整书粗阶段划分
3. 写主角最终人物卡
4. 从人物卡反推一级词条并建立总索引闭环

## 一句话交接

《{novel_name}》当前已经有工作区和闭环模板，但还需要继续从首轮诊断推进到主角骨架和正式词条体系。
"""


def current_status_template(active_project: str, known_projects: list[str]) -> str:
    project_lines = "\n".join(f"- `{name}`" for name in known_projects) or "- 待补"
    return f"""# 当前工作指针

## 当前主任务

- 当前主项目：`{active_project}`
- 当前状态：`初始化后待推进`
- 当前建议模式：`先完成首轮诊断，再推进主角骨架`

## 已有项目级检查点

{project_lines}

## 上次停下的位置

- `{active_project}` 已建立工作区模板和项目级状态文件
- 其余项目如已有独立 checkpoint，也应在本节补充

## 下次开始时先看

1. `git status --short`
2. `CURRENT_STATUS.md`
3. 当前项目目录下的 `项目启动清单`
4. 当前项目目录下最新的 `工作状态-YYYY-MM-DD.md`

## 下一步优先级

1. 先确认首轮诊断结论
2. 再补主角总卡
3. 再补一级词条与总索引闭环

## 更新规则

- 每次任务结束时，只更新这四项：
  - 当前主项目
  - 当前状态
  - 上次停下的位置
  - 下一步优先级
- 如果任务已经收尾，就把“当前建议模式”改成“维护 / 深拆 / 新项目”
"""


def update_root_current_status(project_root: Path, novel_name: str) -> Path:
    path = project_root / "CURRENT_STATUS.md"
    if not path.exists():
        write_file(path, current_status_template(novel_name, [novel_name]))
        return path

    content = path.read_text(encoding="utf-8")
    content, active_count = re.subn(
        r"(?m)^- 当前主项目：`.*`$",
        f"- 当前主项目：`{novel_name}`",
        content,
        count=1,
    )
    if active_count == 0:
        content = current_status_template(novel_name, [novel_name]) + "\n"

    if f"- `{novel_name}`" not in content:
        marker = "## 已有项目级检查点\n"
        if marker in content:
            content = content.replace(marker, marker + f"\n- `{novel_name}`\n", 1)
        else:
            content += f"\n## 已有项目级检查点\n\n- `{novel_name}`\n"

    write_file(path, content)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize and optionally bootstrap a protagonist-encyclopedia novel workspace.")
    parser.add_argument("--novel-name", required=True, help="Novel workspace name, for example DemoNovel")
    parser.add_argument("--source", help="Optional source text file to copy into source/")
    parser.add_argument(
        "--project-root",
        default=str(REPO_ROOT),
        help="Project root where the workspace will be created",
    )
    parser.add_argument(
        "--tool-root",
        default=str(REPO_ROOT),
        help="Tool project root containing text2markdown and novel-character-cards",
    )
    parser.add_argument(
        "--skip-bootstrap",
        action="store_true",
        help="Only initialize files and folders, skip txt->md conversion and pipeline runs",
    )
    parser.add_argument(
        "--extractor",
        choices=("heuristic", "openai"),
        default="heuristic",
        help="Extractor for novel-character-cards pipeline",
    )
    parser.add_argument("--model", default="gpt-5", help="Model for the OpenAI extractor")
    parser.add_argument("--encoding", help="Preferred source encoding")
    parser.add_argument("--max-chars", type=int, default=12000, help="Maximum chunk size")
    parser.add_argument("--limit-chunks", type=int, help="Only process the first N chunks")
    parser.add_argument("--focus-name", help="Optional protagonist focus name for a focus-tracking pass")
    parser.add_argument("--focus-alias", action="append", default=[], help="Additional alias for the focus name")
    parser.add_argument("--summary-interval", type=int, default=80, help="Checkpoint interval for focus tracking")
    parser.add_argument(
        "--no-update-current-status",
        action="store_true",
        help="Do not create or update the project-root CURRENT_STATUS.md entry",
    )
    args = parser.parse_args()

    project_root = Path(args.project_root).expanduser().resolve()
    tool_root = Path(args.tool_root).expanduser().resolve()
    workspace = project_root / args.novel_name
    source_dir = workspace / "source"
    work_dir = workspace / "work"
    today = date.today()
    source_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    copied_name = None
    if args.source:
        src = Path(args.source).expanduser().resolve()
        if not src.exists():
            raise SystemExit(f"source file not found: {src}")
        copied_name = src.name
        shutil.copy2(src, source_dir / src.name)

    write_file(workspace / f"{args.novel_name}-项目启动清单.md", checklist_md(args.novel_name))
    write_file(workspace / f"{args.novel_name}-整书粗阶段划分.md", stage_outline_md(args.novel_name))
    write_file(workspace / f"{args.novel_name}-主角锚点与骨架.md", anchor_md(args.novel_name))
    write_file(workspace / "README.md", readme_md(args.novel_name, copied_name))
    if args.focus_name:
        write_file(workspace / f"{args.focus_name}-最终人物卡.md", final_card_md(args.focus_name))
        write_file(workspace / f"{args.focus_name}-词条总索引.md", index_md(args.novel_name, args.focus_name))
        write_file(workspace / f"{args.focus_name}-核心体系总览.md", core_overview_md(args.focus_name))
    write_file(workspace / f"{args.novel_name}-全书精华总结.md", full_book_essence_md(args.novel_name))

    generated_md = None
    if copied_name and not args.skip_bootstrap:
        copied_path = source_dir / copied_name
        source_text = ""
        if copied_path.suffix.lower() == ".txt":
            generated_md = source_dir / f"{args.novel_name}.md"
            text2markdown_env = os.environ.copy()
            text2markdown_env["PYTHONPATH"] = str(tool_root / "text2markdown" / "src")
            run_cmd(
                [
                    "python3",
                    "-m",
                    "text2markdown.cli",
                    str(copied_path),
                    "-o",
                    str(generated_md),
                    "--title",
                    args.novel_name,
                ]
                + (["--encoding", args.encoding] if args.encoding else []),
                env=text2markdown_env,
            )
            if generated_md.exists():
                source_text = generated_md.read_text(encoding="utf-8", errors="ignore")
        if not source_text:
            source_text = copied_path.read_text(encoding="utf-8", errors="ignore")

        pipeline_env = os.environ.copy()
        pipeline_env["PYTHONPATH"] = str(tool_root / "novel-character-cards" / "src")
        run_cmd(
            [
                "python3",
                "-m",
                "novel_character_cards.cli",
                "pipeline",
                str(copied_path),
                "--workdir",
                str(work_dir),
                "--extractor",
                args.extractor,
                "--model",
                args.model,
                "--max-chars",
                str(args.max_chars),
            ]
            + (["--encoding", args.encoding] if args.encoding else [])
            + (["--limit-chunks", str(args.limit_chunks)] if args.limit_chunks is not None else []),
            env=pipeline_env,
        )

        if args.focus_name:
            focus_workdir = workspace / f"focus-{args.focus_name}"
            focus_cmd = [
                "python3",
                "-m",
                "novel_character_cards.cli",
                "pipeline",
                str(copied_path),
                "--workdir",
                str(focus_workdir),
                "--extractor",
                args.extractor,
                "--model",
                args.model,
                "--max-chars",
                str(args.max_chars),
                "--focus-name",
                args.focus_name,
                "--summary-interval",
                str(args.summary_interval),
            ]
            if args.encoding:
                focus_cmd += ["--encoding", args.encoding]
            if args.limit_chunks is not None:
                focus_cmd += ["--limit-chunks", str(args.limit_chunks)]
            for alias in args.focus_alias:
                focus_cmd += ["--focus-alias", alias]
            run_cmd(focus_cmd, env=pipeline_env)

        report_path = build_first_pass_report(workspace, args.novel_name, source_text)
    else:
        report_path = None

    status_path = workspace / f"工作状态-{today.isoformat()}.md"
    write_file(
        status_path,
        workspace_status_md(
            args.novel_name,
            args.focus_name,
            created_focus=bool(args.focus_name),
            report_created=report_path is not None,
            today=today,
        ),
    )
    current_status_path = None
    if not args.no_update_current_status:
        current_status_path = update_root_current_status(project_root, args.novel_name)
    refresh_workspace_status(workspace, args.novel_name, args.focus_name)

    print(f"workspace: {workspace}")
    print("created:")
    print(f"- {workspace / 'README.md'}")
    print(f"- {workspace / f'{args.novel_name}-项目启动清单.md'}")
    print(f"- {workspace / f'{args.novel_name}-整书粗阶段划分.md'}")
    print(f"- {workspace / f'{args.novel_name}-主角锚点与骨架.md'}")
    print(f"- {workspace / f'{args.novel_name}-全书精华总结.md'}")
    print(f"- {status_path}")
    if args.focus_name:
        print(f"- {workspace / f'{args.focus_name}-最终人物卡.md'}")
        print(f"- {workspace / f'{args.focus_name}-词条总索引.md'}")
        print(f"- {workspace / f'{args.focus_name}-核心体系总览.md'}")
    if current_status_path is not None:
        print(f"- {current_status_path}")
    if copied_name:
        print(f"- {source_dir / copied_name}")
    if generated_md is not None and generated_md.exists():
        print(f"- {generated_md}")
    if not args.skip_bootstrap and copied_name:
        print(f"- {work_dir / 'chunks'}")
        print(f"- {work_dir / 'extractions'}")
        print(f"- {work_dir / 'merged' / 'characters.json'}")
        print(f"- {work_dir / 'cards' / 'index.md'}")
        if report_path is not None:
            print(f"- {report_path}")
        if args.focus_name:
            print(f"- {workspace / f'focus-{args.focus_name}' / 'focus'}")


if __name__ == "__main__":
    main()
