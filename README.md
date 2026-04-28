# Novel Workspace Pipeline

一个面向长篇小说分析的分层工作区流水线。

这个仓库的目标不是一次性生成一份“读后总结”，而是把小说分析做成可续跑、可校验、可回归的工作区系统。每本小说都作为一个独立 workspace 推进，逐层沉淀产物、状态和下一步建议。

## 核心结构

当前 workflow 采用“五层能力 + 总控调度”：

1. `chapter-distillation`
   章节蒸馏层，负责逐章压骨架。
2. `opening`
   黄金前三章层，负责开篇抓力和承诺判断。
3. `protagonist`
   主角百科层，负责主角知识库主干。
4. `outline`
   整书大纲层，负责阶段结构、主线支线和高潮收束。
5. `highlight`
   剧情高光层，负责 Top 10 记忆点和吸引力机制。

总控 skill 是 `novel-workspace-orchestrator`，负责：

- 识别当前工作区状态
- 判断 `fresh / extend-existing / repair-existing / validate-only`
- 决定下一层
- 调下层脚本
- 写回状态、gap report、repair plan 和交接文件

## 仓库内容

- [WORKFLOW.md](/home/zuoky/project/WORKFLOW.md:1)
  面向人的 workflow 简介和使用说明。
- [CURRENT_STATUS.md](/home/zuoky/project/CURRENT_STATUS.md:1)
  仓库级当前工作指针。
- [novel-workspace-orchestrator-skill](/home/zuoky/project/novel-workspace-orchestrator-skill/SKILL.md:1)
  总控 skill 和脚本层。
- [novel-chapter-distillation-skill](/home/zuoky/project/novel-chapter-distillation-skill/SKILL.md:1)
  章节蒸馏层。
- [novel-opening-analysis-skill](/home/zuoky/project/novel-opening-analysis-skill/SKILL.md:1)
  黄金前三章层。
- [novel-protagonist-encyclopedia-skill](/home/zuoky/project/novel-protagonist-encyclopedia-skill/SKILL.md:1)
  主角百科层。
- [novel-outline-analysis-skill](/home/zuoky/project/novel-outline-analysis-skill/SKILL.md:1)
  整书大纲层。
- [novel-highlight-scenes-analysis-skill](/home/zuoky/project/novel-highlight-scenes-analysis-skill/SKILL.md:1)
  剧情高光层。

小说工作区示例包括：

- `刀笼`
- `寇道`
- `巫师世界`
- `序列大明`
- `我的诡异人生`
- `永恒剑主`
- `玄浑道章`

## 快速开始

先看当前状态：

```bash
git status --short
python3 novel-workspace-orchestrator-skill/scripts/run_workspace_regression.py
```

看某个工作区当前做到哪一步：

```bash
python3 novel-workspace-orchestrator-skill/scripts/refresh_workspace_status.py --workspace 刀笼 --json
python3 novel-workspace-orchestrator-skill/scripts/workspace-gap-report.py --workspace 刀笼
```

让总控判断下一步：

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_novel_workspace_pipeline.py --workspace 刀笼
```

让总控实际调下层脚本：

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_novel_workspace_pipeline.py --workspace 刀笼 --execute
```

## 当前边界

这套 workflow 现在已经能做：

- 工作区识别
- 真实 validator 校验
- 推荐下一层
- 生成 `workspace-status.json`
- 生成 `workspace-gap-report.md`
- 生成 `workspace-repair-plan.md`
- 跑固定样书回归

但它还不能完全自动做：

- 语义级正文补写
- 高质量 `repair-existing` 内容重构

所以它当前更接近一个 `可用的小说工作区 pipeline`，而不是全自动写作代理。

## 建议阅读顺序

1. [WORKFLOW.md](/home/zuoky/project/WORKFLOW.md:1)
2. [CURRENT_STATUS.md](/home/zuoky/project/CURRENT_STATUS.md:1)
3. 目标小说目录下的最新 `workspace-status.json`
4. 目标小说目录下的 `workspace-gap-report.md` 或 `workspace-repair-plan.md`
