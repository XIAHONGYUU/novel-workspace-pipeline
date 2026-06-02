# 《永恒剑主》Repair Plan

- 工作区：`/home/zuoky/project/永恒剑主`
- 目标层：`supporting-cast` / `重要配角层`
- 模式：`repair-existing`
- 原因：ai_review -> placeholder_detected；重要配角Top10总表 -> placeholder_detected；重要配角与主角关系图 -> placeholder_detected；重要配角阶段作用分布 -> placeholder_detected；检测到占位内容

## 修复动作

- 替换 `ai_review` 里的占位内容，补成明确结论和证据。
- 替换 `重要配角Top10总表` 里的占位内容，补成明确结论和证据。
- 替换 `重要配角与主角关系图` 里的占位内容，补成明确结论和证据。
- 替换 `重要配角阶段作用分布` 里的占位内容，补成明确结论和证据。
- 检查并修复 `Top10 配角分析文件`，当前原因：`profile_quality_insufficient`。

## 失败检查项

- `ai_review`：`placeholder_detected`；文件：`永恒剑主-重要配角AI复核结论.md`；占位：`待AI复核`
- `重要配角Top10总表`：`placeholder_detected`；文件：`永恒剑主-重要配角Top10总表.md`；占位：`待AI复核`
- `重要配角与主角关系图`：`placeholder_detected`；文件：`永恒剑主-重要配角与主角关系图.md`；占位：`待AI复核`
- `重要配角阶段作用分布`：`placeholder_detected`；文件：`永恒剑主-重要配角阶段作用分布.md`；占位：`待AI复核`
- `Top10 配角分析文件`：`profile_quality_insufficient`；文件：`supporting-cast`

## 推荐先读

- `README.md`
- `工作状态-2026-05-30.md`
- `characters.json`
- `index.md`
- `林新-词条总索引.md`
- `林新-最终人物卡.md`
