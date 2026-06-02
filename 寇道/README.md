# 寇道 工作区说明

本目录是《寇道》的独立工作区。正式产物继续保留在根目录，便于现有 validator / orchestrator 直接识别；中间缓存统一收纳到 `work/`。

## 快速入口

- 最新交接：`工作状态-2026-05-23.md`
- 机器状态：`workspace-status.json`
- 根目录索引：`WORKSPACE_FILES.md`
- 差距报告：`workspace-gap-report.md`
- 修复计划：`workspace-repair-plan.md`
- 流程判断：`工作区流程判断报告.md`

## 当前状态摘要

- 主角：`寇立`
- 已达标层：`chapter-distillation, opening, protagonist, outline, highlight`
- 待修层：`supporting-cast`
- 推荐模式：`repair-existing`
- 推荐下一层：`supporting-cast`
- 推荐 skill：`novel-supporting-cast-analysis`
- 当前建议：优先修复 重要配角层，因为该层已存在但尚未达标。

## 目录分层

- `source/`
  原文与转换稿，共 2 个条目。
- `supporting-cast/`
  重要配角分析目录，当前 10 份配角卡。
- `work/`
  中间运行产物、抽取缓存、章节蒸馏续跑状态。
- `focus-<主角名>/`
  主角卡抽取阶段缓存目录：`focus-寇立`。

## 正式产物分层

### 章节蒸馏层
- `chapter-distillation-manifest.json`
- `寇道-校准与验证锚点.md`
- `寇道-章节蒸馏校验报告.md`
- `寇道-章节蒸馏骨架.md`
- `寇道-阶段骨架与换挡草图.md`

### 黄金前三章层
- `寇道-开篇钩子与读者承诺.md`
- `寇道-开篇问题与修改建议.md`
- `寇道-第一章拆解.md`
- `寇道-第三章拆解.md`
- `寇道-第二章拆解.md`
- `寇道-黄金前三章总判断.md`
- `寇道-黄金前三章校验报告.md`

### 主角百科层
- `寇立-最终人物卡.md`
- `寇立-核心体系总览.md`
- `寇立-词条总索引.md`
- `寇道-主角百科校验报告.md`
- `寇道-主角锚点与骨架.md`
- `寇道-全书精华总结.md`
- `寇道-整书粗阶段划分.md`
- `寇道-项目启动清单.md`

### 主角词条资产
- `寇立-世界结构词条总结.md`
- `寇立-九龙龙气与神仙道高位结构词条总结.md`
- `寇立-修行炼体与神仙道高位路线词条总结.md`
- `寇立-势力与局势卷入词条总结.md`
- `寇立-战斗方式词条总结.md`
- `寇立-无字图与核心机缘路线词条总结.md`
- `寇立-武叩仙门与武道路线词条总结.md`
- `寇立-武盟与朝廷格局词条总结.md`
- `寇立-烧身武馆与童子桩词条总结.md`
- `寇立-猛虎拳与拳术入身词条总结.md`
- `寇立-粤州与水龙帮开局词条总结.md`
- `寇立-身份变化词条总结.md`
- `寇立-重要关系网词条总结.md`
- `寇立-重要城市与地域轨迹词条总结.md`

### 重要配角层
- `寇道-重要配角Top10总表.md`
- `寇道-重要配角与主角关系图.md`
- `寇道-重要配角层校验报告.md`
- `寇道-重要配角阶段作用分布.md`
- `supporting-cast/index.md`

### 整书大纲层
- `寇道-主线支线与冲突地图.md`
- `寇道-大纲分析校验报告.md`
- `寇道-大纲总览.md`
- `寇道-时间与地点转折.md`
- `寇道-核心冲突点与爆发点.md`
- `寇道-核心配角与主角关系.md`
- `寇道-结构问题与修改建议.md`
- `寇道-阶段与篇章拆分.md`
- `寇道-高潮节奏与收束诊断.md`

### 剧情高光层
- `寇道-Top10细节逐条拆解.md`
- `寇道-剧情吸引力机制分析.md`
- `寇道-剧情高光改造建议.md`
- `寇道-剧情高光校验报告.md`
- `寇道-最吸引人的十个剧情细节总表.md`
- `寇道-最强爽点痛点悬念点总结.md`
- `寇道-高光桥段分布与节奏判断.md`

### 综合校验与质量门
- `寇道-质量门报告.md`

### 历史诊断文件
- `寇道-首轮诊断报告.md`

### 历史别名文件
- 无

## 状态与交接文件

- `workspace-status.json`
- `workspace-gap-report.md`
- `workspace-repair-plan.md`
- `工作区流程判断报告.md`
- 最新 `工作状态-YYYY-MM-DD.md`：`工作状态-2026-05-23.md`
- `workspace-context-chapter-distillation.md`
- `workspace-context-protagonist.md`

## 中间产物与缓存

- `work/` 下已有 8 个一级条目
- `work/chapter-distillation/` 用于章节蒸馏续跑、批次缓存、备份

## 本次整理动作

- 已刷新 `supporting-cast/README.md`
- 已刷新 `source/README.md`
- 已刷新 `work/README.md`
- 已刷新 `WORKSPACE_FILES.md`

## 文件约定

- 根目录：正式分析产物与状态文件，保持对现有脚本的兼容。
- `source/`：原文和转换稿。
- `supporting-cast/`：配角层专用目录。
- `work/`：所有中间缓存、历史备份、续跑状态。
- `work_backup_heuristic/`：历史备份，不作为当前正式入口。

