# Novel Workspace Pipeline

把长篇小说分析从一次性问答，变成可续跑、可校验、可交接的工作区流水线。

## 这个项目解决什么问题

大多数小说分析有两个常见问题：

- 只产出一份总结，后续很难继续扩展
- 笔记很多，但没有层次、没有校验、也没有明确下一步

这个仓库的目标不是“再写一份读后感”，而是把每本小说做成一个独立 workspace，让分析过程可以反复推进、回看、修补和交接。

## 核心思路

每本小说都按固定分析层推进：

```text
原文
  -> chapter-distillation
  -> opening
  -> protagonist
  -> outline
  -> highlight
  -> workspace status / gap report / repair plan / handoff files
```

五层能力分别负责：

1. `chapter-distillation`
   逐章压骨架，固定每章推进、状态变化、结构功能和章末钩子。
2. `opening`
   分析前三章的抓力、承诺、冲突启动和章末拉力。
3. `protagonist`
   建立主角知识主干、关系网、成长路线和核心体系。
4. `outline`
   判断整书阶段结构、主线支线、冲突升级和高潮收束。
5. `highlight`
   提炼最强记忆点，分析高光场景为什么有效。

总控层是 [`novel-workspace-orchestrator-skill`](novel-workspace-orchestrator-skill/SKILL.md)，负责：

- 识别当前 workspace 状态
- 判断 `fresh / extend-existing / repair-existing / validate-only`
- 推荐下一层
- 调用对应层脚本
- 重跑 validator
- 写回状态文件和交接产物

## 这个仓库里有什么

- [WORKFLOW.md](WORKFLOW.md)
  面向人的整体工作流说明。
- [CURRENT_STATUS.md](CURRENT_STATUS.md)
  当前主项目、活跃状态和恢复上下文入口。
- [novel-workspace-orchestrator-skill](novel-workspace-orchestrator-skill/SKILL.md)
  总控层和调度脚本。
- [novel-chapter-distillation-skill](novel-chapter-distillation-skill/SKILL.md)
  章节蒸馏层。
- [novel-opening-analysis-skill](novel-opening-analysis-skill/SKILL.md)
  黄金前三章层。
- [novel-protagonist-encyclopedia-skill](novel-protagonist-encyclopedia-skill/SKILL.md)
  主角百科层。
- [novel-outline-analysis-skill](novel-outline-analysis-skill/SKILL.md)
  整书大纲层。
- [novel-highlight-scenes-analysis-skill](novel-highlight-scenes-analysis-skill/SKILL.md)
  剧情高光层。
- [docs/github-promo-copy.md](docs/github-promo-copy.md)
  可直接复用的 GitHub/社群推广文案。

示例工作区：

- `刀笼`
- `寇道`
- `巫师世界`
- `序列大明`
- `我的诡异人生`
- `永恒剑主`
- `玄浑道章`

## 为什么这个仓库值得看

- 它不是单次输出，而是可持续推进的 workspace 系统
- 它不是纯文档堆积，而是带有状态判断、校验和回归
- 它不是“想到哪写到哪”，而是固定五层分析模型
- 它已经在多本长篇小说上反复使用，而不是空壳设计

如果你做的是：

- 长篇网文拆解
- 小说研究笔记体系化
- AI 辅助文学分析工作流
- 可复用的知识工程 / 内容流水线

这个仓库就有可参考价值。

## 快速开始

先看仓库当前状态：

```bash
git status --short
python3 novel-workspace-orchestrator-skill/scripts/run_workspace_regression.py
```

查看某个工作区当前做到哪一步：

```bash
python3 novel-workspace-orchestrator-skill/scripts/refresh_workspace_status.py --workspace 刀笼 --json
python3 novel-workspace-orchestrator-skill/scripts/workspace-gap-report.py --workspace 刀笼
```

让总控推荐下一步：

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_novel_workspace_pipeline.py --workspace 刀笼
```

让总控实际执行目标层：

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_novel_workspace_pipeline.py --workspace 刀笼 --execute
```

## 当前边界

这套 pipeline 现在已经能做：

- 工作区识别
- 真实 validator 校验
- 推荐下一层
- 生成 `workspace-status.json`
- 生成 `workspace-gap-report.md`
- 生成 `workspace-repair-plan.md`
- 跑固定样书回归

它暂时还不能完全自动做：

- 语义级正文补写
- 高质量 `repair-existing` 内容重构

所以它现在更接近一个可用的小说分析 workflow，而不是全自动写作代理。

## 建议阅读顺序

1. [WORKFLOW.md](WORKFLOW.md)
2. [CURRENT_STATUS.md](CURRENT_STATUS.md)
3. 目标小说目录下的最新 `workspace-status.json`
4. 目标小说目录下的 `workspace-gap-report.md` 或 `workspace-repair-plan.md`
5. [docs/github-promo-copy.md](docs/github-promo-copy.md)
