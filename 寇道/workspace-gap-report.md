# 《寇道》工作区差距报告

- 工作区：`/home/zuoky/project/寇道`
- 是否长篇：`是`
- 已存在层：`chapter-distillation, opening, protagonist, supporting-cast, outline, highlight`
- 已达标层：`chapter-distillation, opening, protagonist, outline, highlight`
- 待修层：`supporting-cast`
- 推荐模式：`repair-existing`
- 推荐下一层：`supporting-cast`
- 推荐 skill：`novel-supporting-cast-analysis`

## 当前判断

- 优先修复 重要配角层，因为该层已存在但尚未达标。

## Repair Plan

- 目标层：`supporting-cast` / `重要配角层`
- 进入原因：project_entry -> keywords_missing；handoff -> keywords_missing；candidate_pool -> missing；ai_review -> missing
- 补齐 `project_entry` 的关键判断字段，避免只有摘要没有结论。
- 补齐 `handoff` 的关键判断字段，避免只有摘要没有结论。
- 补齐 `candidate_pool`，至少先从缺失补到可校验骨架。
- 补齐 `ai_review`，至少先从缺失补到可校验骨架。
- 补齐 `重要配角Top10总表` 的关键判断字段，避免只有摘要没有结论。
- 补齐 `重要配角与主角关系图` 的关键判断字段，避免只有摘要没有结论。
- 补齐 `重要配角阶段作用分布` 的关键判断字段，避免只有摘要没有结论。
- 补齐 `配角分析索引`，至少先从缺失补到可校验骨架。
- 检查并修复 `Top10 配角分析文件`，当前原因：`profile_quality_insufficient`。

## 分层结果

### 章节蒸馏层 / `chapter-distillation`

- 当前状态：`通过` | 质量评分：✅ 100/100
- 完成标签：`章节骨架已形成`
- 判断来源：`validator`
- 识别到的关键文件：`README.md, chapter-distillation-manifest.json, 寇道-校准与验证锚点.md, 寇道-章节蒸馏校验报告.md, 寇道-章节蒸馏骨架.md, 寇道-阶段骨架与换挡草图.md, 工作状态-2026-05-23.md`

### 黄金前三章层 / `opening`

- 当前状态：`通过` | 质量评分：✅ 100/100
- 完成标签：`开篇抓力已明确`
- 判断来源：`validator`
- 识别到的关键文件：`README.md, 寇道-开篇钩子与读者承诺.md, 寇道-开篇问题与修改建议.md, 寇道-第一章拆解.md, 寇道-第三章拆解.md, 寇道-第二章拆解.md, 寇道-黄金前三章总判断.md, 寇道-黄金前三章校验报告.md, 工作状态-2026-05-23.md`

### 主角百科层 / `protagonist`

- 当前状态：`通过` | 质量评分：✅ 100/100
- 完成标签：`体系闭环完成（主干闭环版）`
- 判断来源：`validator`
- 识别到的关键文件：`README.md, 寇立-最终人物卡.md, 寇立-核心体系总览.md, 寇立-词条总索引.md, 寇道-主角百科校验报告.md, 寇道-主角锚点与骨架.md, 寇道-全书精华总结.md, 寇道-整书粗阶段划分.md, 寇道-项目启动清单.md, 工作状态-2026-05-23.md`

### 重要配角层 / `supporting-cast`

- 当前状态：`仅存在` | 质量评分：✅ 100/100
- 完成标签：`重要配角 Top10 仍不足`
- 判断来源：`validator`
- 识别到的关键文件：`README.md, supporting-cast, 寇道-重要配角Top10总表.md, 寇道-重要配角与主角关系图.md, 寇道-重要配角层校验报告.md, 寇道-重要配角阶段作用分布.md, 工作状态-2026-05-23.md`
- 主要缺口：`project_entry:keywords_missing | handoff:keywords_missing | candidate_pool:missing | ai_review:missing | 重要配角Top10总表:keywords_missing`
- 修复动作：`补齐 `project_entry` 的关键判断字段，避免只有摘要没有结论。 | 补齐 `handoff` 的关键判断字段，避免只有摘要没有结论。 | 补齐 `candidate_pool`，至少先从缺失补到可校验骨架。 | 补齐 `ai_review`，至少先从缺失补到可校验骨架。`

### 整书大纲层 / `outline`

- 当前状态：`通过` | 质量评分：✅ 100/100
- 完成标签：`共性标准已覆盖`
- 判断来源：`validator`
- 识别到的关键文件：`README.md, 寇道-主线支线与冲突地图.md, 寇道-主角锚点与骨架.md, 寇道-大纲分析校验报告.md, 寇道-大纲总览.md, 寇道-时间与地点转折.md, 寇道-核心冲突点与爆发点.md, 寇道-核心配角与主角关系.md, 寇道-结构问题与修改建议.md, 寇道-阶段与篇章拆分.md, 寇道-高潮节奏与收束诊断.md, 工作状态-2026-05-23.md`

### 剧情高光层 / `highlight`

- 当前状态：`通过` | 质量评分：✅ 100/100
- 完成标签：`高光桥段已明确`
- 判断来源：`validator`
- 识别到的关键文件：`README.md, 寇道-Top10细节逐条拆解.md, 寇道-剧情吸引力机制分析.md, 寇道-剧情高光改造建议.md, 寇道-剧情高光校验报告.md, 寇道-最吸引人的十个剧情细节总表.md, 寇道-最强爽点痛点悬念点总结.md, 寇道-高光桥段分布与节奏判断.md, 工作状态-2026-05-23.md`
