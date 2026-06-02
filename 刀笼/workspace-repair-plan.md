# 《刀笼》Repair Plan

- 工作区：`/home/zuoky/project/刀笼`
- 目标层：`chapter-distillation` / `章节蒸馏层`
- 模式：`repair-existing`
- 原因：章节蒸馏骨架 -> placeholder_detected；阶段骨架与换挡草图 -> placeholder_detected；校准与验证锚点 -> too_short；检测到占位内容

## 修复动作

- 替换 `章节蒸馏骨架` 里的占位内容，补成明确结论和证据。
- 替换 `阶段骨架与换挡草图` 里的占位内容，补成明确结论和证据。
- 扩写 `校准与验证锚点`，把当前短骨架补成可判断正文。

## 失败检查项

- `章节蒸馏骨架`：`placeholder_detected`；文件：`刀笼-章节蒸馏骨架.md`；占位：`待补充`
- `阶段骨架与换挡草图`：`placeholder_detected`；文件：`刀笼-阶段骨架与换挡草图.md`；占位：`待补充, - 待补充`
- `校准与验证锚点`：`too_short`；文件：`刀笼-校准与验证锚点.md`

## 推荐先读

- `README.md`
- `工作状态-2026-05-24.md`
- `DAOLONG.md`
- `刀笼.md`
