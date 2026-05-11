# GitHub 推广文案模板

这份文案是给 `Novel Workspace Pipeline` 用的，目的是让别人一眼看懂这不是普通读后总结仓库，而是一套可复用的小说分析工作流。

## 一句话介绍

把长篇小说分析从一次性问答，做成可续跑、可校验、可交接的 workspace pipeline。

## 仓库副标题

一个面向长篇小说分析的分层工作区流水线，支持五层分析、状态判断、缺口报告和回归校验。

## 简短介绍

我把长篇小说分析整理成了一套可复用的工作区流水线。它不是只生成一份总结，而是把每本小说做成独立 workspace，按章节蒸馏、开篇分析、主角百科、整书大纲、剧情高光五层持续推进，并通过 orchestrator 判断下一步、补状态、跑校验。

## 社群 / 朋友圈短文案

最近把自己做小说分析的方法整理成了一个公开仓库：`Novel Workspace Pipeline`。  
它不是普通的“读后总结”，而是把每本小说当成一个 workspace，按五层分析持续推进，并且有状态判断、gap report、repair plan 和回归校验。  
如果你也在做网文拆解、小说研究、AI 辅助内容分析，可能会有参考价值。  

## GitHub / 论坛稍长文案

我公开了一个自己在用的小说分析 workflow：`Novel Workspace Pipeline`。

这个项目想解决的不是“怎么快速生成一份总结”，而是“怎么把长篇小说分析做成一个可以反复推进、可以校验、可以交接的工作区系统”。

核心做法是把每本小说拆成独立 workspace，再按固定五层推进：

- chapter-distillation：逐章蒸馏骨架
- opening：分析黄金前三章
- protagonist：建立主角知识主干
- outline：判断整书结构和冲突升级
- highlight：提炼最强剧情高光

此外还有一个 orchestrator 负责判断当前模式、推荐下一层、调用脚本、重跑 validator，并写回状态文件。

这个仓库更适合下面几类人：

- 做长篇网文拆解的人
- 做小说知识整理和结构研究的人
- 想把 AI 文学分析做成可复用流程的人
- 对内容工程、知识工程、workspace workflow 感兴趣的人

仓库地址：

`https://github.com/XIAHONGYUU/novel-workspace-pipeline`

## 英文简版

I open-sourced a workflow called `Novel Workspace Pipeline`.

Instead of generating one-off novel summaries, it turns each long novel into a structured workspace with layered analysis, validator-backed status checks, gap reports, repair plans, and an orchestrator that recommends the next step.

If you work on web novel analysis, AI-assisted literary research, or reusable content workflows, this repo may be useful.

## 适合发帖时搭配的标题

- 我把长篇小说分析做成了一套可复用的 workspace pipeline
- 一个不是“读后总结”，而是可续跑小说分析系统的 GitHub 仓库
- 用五层分析 + orchestrator 管理长篇小说工作区
- 把网文拆解流程工程化：Novel Workspace Pipeline

## 建议补充的仓库 Topics

- `novel-analysis`
- `workflow`
- `knowledge-management`
- `ai-workflow`
- `literary-analysis`
- `content-pipeline`
- `text-analysis`
- `writing-tools`

## 发布时建议一起做的事

- 在 `README.md` 顶部放一句话价值说明
- 在首屏展示五层模型，而不是先讲内部细节
- 发帖时附一张工作区结构图或示例目录截图
- 选 1 到 2 个代表性样例，展示输入和最终产物长什么样
