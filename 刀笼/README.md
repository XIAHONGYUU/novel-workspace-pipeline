# 刀笼工作区说明

本目录是《刀笼》的独立工作区。

## 当前结构

- `source/DAOLONG.txt`
  Windows 桌面原始文本副本
- `source/刀笼.md`
  由 `text2markdown` 转换得到的 Markdown 版
- `work/chunks/`
  小说切分后的 chunk 文件
- `work/extractions/`
  每个 chunk 的启发式抽取结果
- `work/merged/characters.json`
  合并后的角色候选数据
- `work/cards/`
  渲染出的 Markdown 卡片
- `work/cards/index.md`
  卡片索引
- `刀笼-主角锚点与骨架.md`
  当前主角确认与骨架草稿入口
- `戚笼-最终人物卡.md`
  当前主角总卡
- `戚笼-词条总索引.md`
  当前词条总索引骨架

## 已完成

- 已建立独立工作区
- 已复制原始小说文本
- 已完成 txt -> md 转换
- 已运行第一轮 `novel-character-cards` heuristic 流水线

## 当前观察

第一轮 heuristic 结果可用于摸底，但噪声较高，`cards/index.md` 中混入了不少非人物词条。

这说明下一轮更适合做以下事情之一：

- 只聚焦主角做 `focus_name` 跟踪
- 改进启发式规则
- 使用 OpenAI 抽取器生成更干净的人物卡

## 建议下一步

优先建议先做“主角聚焦”版本，确认《刀笼》的主角骨架，再决定是否做全人物卡。

当前这一步已经完成，可直接从 `刀笼-主角锚点与骨架.md` 继续往下做主角总卡。

现在主角总卡和总索引骨架也已建立，后续可以直接按 `戚笼-词条总索引.md` 的顺序拆一级词条。
