# 《寇道》Repair Plan

- 工作区：`/home/zuoky/project/寇道`
- 目标层：`supporting-cast` / `重要配角层`
- 模式：`repair-existing`
- 原因：project_entry -> keywords_missing；handoff -> keywords_missing；candidate_pool -> missing；ai_review -> missing

## 修复动作

- 补齐 `project_entry` 的关键判断字段，避免只有摘要没有结论。
- 补齐 `handoff` 的关键判断字段，避免只有摘要没有结论。
- 补齐 `candidate_pool`，至少先从缺失补到可校验骨架。
- 补齐 `ai_review`，至少先从缺失补到可校验骨架。
- 补齐 `重要配角Top10总表` 的关键判断字段，避免只有摘要没有结论。
- 补齐 `重要配角与主角关系图` 的关键判断字段，避免只有摘要没有结论。
- 补齐 `重要配角阶段作用分布` 的关键判断字段，避免只有摘要没有结论。
- 补齐 `配角分析索引`，至少先从缺失补到可校验骨架。
- 检查并修复 `Top10 配角分析文件`，当前原因：`profile_quality_insufficient`。

## 失败检查项

- `project_entry`：`keywords_missing`；文件：`README.md`
- `handoff`：`keywords_missing`；文件：`工作状态-2026-05-23.md`
- `candidate_pool`：`missing`
- `ai_review`：`missing`
- `重要配角Top10总表`：`keywords_missing`；文件：`寇道-重要配角Top10总表.md`
- `重要配角与主角关系图`：`keywords_missing`；文件：`寇道-重要配角与主角关系图.md`
- `重要配角阶段作用分布`：`keywords_missing`；文件：`寇道-重要配角阶段作用分布.md`
- `配角分析索引`：`missing`
- `Top10 配角分析文件`：`profile_quality_insufficient`；文件：`supporting-cast`

## 推荐先读

- `README.md`
- `工作状态-2026-05-23.md`
- `characters.json`
- `index.md`
- `寇立-词条总索引.md`
- `寇立-最终人物卡.md`
