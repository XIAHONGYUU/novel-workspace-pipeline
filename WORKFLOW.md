# 项目工作流

这个仓库现在用于记录小说词条项目的实际进度，避免每次都靠回忆恢复上下文。

## 每次开始

1. 先看 `git status --short`
2. 再看 `CURRENT_STATUS.md`
3. 再进入当前主项目目录看：
   - `项目启动清单`
   - `词条总索引`
   - 最新 `工作状态` 文件

## 每次结束

1. 更新 `CURRENT_STATUS.md`
2. 如果当天有阶段性推进，补一份对应项目的 `工作状态-YYYY-MM-DD.md`
3. 用 Git 提交一次，提交信息尽量写清楚本次推进内容

## 推荐提交粒度

- 完成一个正式产物时提交一次
- 完成一轮结构判断时提交一次
- 修正文档、补互链、补二级词条时可按主题提交

## 提交信息建议

- `docs: close yonghengjianzhu skeleton`
- `docs: deepen yonghengjianzhu empire lexicon`
- `docs: add cross-links for yonghengjianzhu`
- `docs: update current status`

## 约定

- `CURRENT_STATUS.md` 是全仓库入口
- 各小说目录下的 `项目启动清单` 负责判断完成度
- 各小说目录下的 `词条总索引` 负责阅读顺序和继续扩展方向
- `工作状态-YYYY-MM-DD.md` 只记录阶段性交接，不替代总索引和启动清单

