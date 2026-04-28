# 项目工作流

这个仓库现在已经不只是“小说词条整理记录”，而是一套可持续推进的小说工作区 workflow。

目标是让小说分析不再依赖一次性问答，而是通过工作区持续沉淀：

- 当前做到哪一层
- 哪些产物已经达标
- 下一步最该补什么
- 下次如何快速恢复上下文

## 一、简介

当前 workflow 采用“五层能力 + 总控调度”的结构。

### 五层能力

1. `chapter-distillation`
   章节蒸馏层。负责逐章压骨架，固定每章核心推进、状态变化、结构功能和章末钩子。
2. `opening`
   黄金前三章层。负责判断开篇抓力、主角首亮相、冲突启动、信息释放和章末拉力。
3. `protagonist`
   主角百科层。负责建立主角知识库主干、人物关系、成长路线和核心体系。
4. `outline`
   整书大纲层。负责阶段结构、主线支线、冲突升级、高潮节奏与收束判断。
5. `highlight`
   剧情高光层。负责提炼全书最强记忆点、读者吸引力机制和高光分布判断。

### 总控层

总控 skill 是：

- `novel-workspace-orchestrator`

它不是第六个分析层，而是负责：

- 读取工作区状态
- 判断当前模式
- 决定下一层
- 调用对应层脚本
- 重跑 validator
- 写回工作状态和仓库状态

## 二、当前模式

workflow 默认支持四种模式：

1. `fresh`
   新书刚开始，还没有稳定工作区。
2. `extend-existing`
   工作区已存在，需要补一个缺失层。
3. `repair-existing`
   某层已存在，但 validator 不通过或明显还是占位骨架。
4. `validate-only`
   只检查当前状态，不改内容。

## 三、你通常怎么用

最常见的使用方式分三类。

### 1. 只想判断当前做到哪一步

看工作区状态：

```bash
python3 novel-workspace-orchestrator-skill/scripts/refresh_workspace_status.py --workspace 刀笼 --json
```

看差距报告：

```bash
python3 novel-workspace-orchestrator-skill/scripts/workspace-gap-report.py --workspace 刀笼
```

### 2. 想让总控判断下一步该做什么

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_novel_workspace_pipeline.py --workspace 刀笼
```

它会输出：

- 当前推荐模式
- 当前推荐下一层
- 当前推荐 skill
- 当前建议下一步

### 3. 想让总控实际调用下层脚本

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_novel_workspace_pipeline.py \
  --workspace 永恒剑主 \
  --execute
```

如果你要强制指定目标层：

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_novel_workspace_pipeline.py \
  --workspace 永恒剑主 \
  --target-layer opening \
  --execute
```

执行后会自动做这些事：

1. 调对应层的 init 脚本
2. 重跑 validator
3. 写回 `workspace-status.json`
4. 写回 `workspace-gap-report.md`
5. 写回 `工作区流程判断报告.md`
6. 写回当天 `工作状态-YYYY-MM-DD.md`
7. 更新仓库级 `CURRENT_STATUS.md`

## 四、常用脚本

### 状态刷新

```bash
python3 novel-workspace-orchestrator-skill/scripts/refresh_workspace_status.py --workspace <项目名> --json
```

作用：

- 刷新 `workspace-status.json`
- 查看五层当前达标情况

### 差距报告

```bash
python3 novel-workspace-orchestrator-skill/scripts/workspace-gap-report.py --workspace <项目名>
```

作用：

- 输出当前最缺什么
- 标出哪些层“已存在但仍不足”

### 复用上下文

```bash
python3 novel-workspace-orchestrator-skill/scripts/build_layer_context.py --workspace <项目名> --target-layer outline
```

作用：

- 从已有层抽取后续目标层最值得复用的上下文

### 总控执行

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_novel_workspace_pipeline.py --workspace <项目名> --execute
```

作用：

- 让总控真正调下层脚本，而不是只做判断

### 回归检查

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_workspace_regression.py
```

作用：

- 对固定样书集合跑只读回归
- 检查推荐模式、推荐下一层、已完成层、待修层是否漂移
- 作为 workflow 脚本改动后的最小验收

## 五、每次开始

1. 先看 `git status --short`
2. 再看 `CURRENT_STATUS.md`
3. 再进入当前主项目目录看：
   - `项目启动清单`
   - `词条总索引` 或关键入口文件
   - 最新 `工作状态` 文件
   - `workspace-gap-report.md`

如果当前项目已经接入总控 workflow，优先再跑一次：

```bash
python3 novel-workspace-orchestrator-skill/scripts/run_novel_workspace_pipeline.py --workspace <项目名>
```

## 六、每次结束

1. 确认 `CURRENT_STATUS.md` 已更新
2. 如果当天有阶段性推进，补一份对应项目的 `工作状态-YYYY-MM-DD.md`
3. 确认 `workspace-status.json`、`workspace-gap-report.md`、`workspace-repair-plan.md`、`工作区流程判断报告.md` 已同步
4. 用 Git 提交一次，提交信息尽量写清楚本次推进内容

## 七、推荐提交粒度

- 完成一个正式产物时提交一次
- 完成一轮结构判断时提交一次
- 完成一个 validator / workflow 脚本增强时提交一次
- 修正文档、补互链、补二级词条时可按主题提交

## 八、提交信息建议

- `docs: close yonghengjianzhu skeleton`
- `docs: deepen yonghengjianzhu empire lexicon`
- `docs: add cross-links for yonghengjianzhu`
- `docs: update current status`
- `feat: add novel workspace orchestrator pipeline`

## 九、关键约定

- `CURRENT_STATUS.md` 是全仓库入口
- 各小说目录下的 `项目启动清单` 负责判断完成度
- 各小说目录下的 `词条总索引` 负责阅读顺序和继续扩展方向
- `工作状态-YYYY-MM-DD.md` 只记录阶段性交接，不替代总索引和启动清单
- `workspace-status.json` 是总控脚本共享状态层
- `workspace-gap-report.md` 负责告诉你“现在最该补什么”
- `workspace-repair-plan.md` 负责把 `repair-existing` 拆成可执行修复动作
- `工作区流程判断报告.md` 负责告诉你“当前总控建议怎么走”

## 十、当前边界

当前 workflow 已经能做：

- 工作区识别
- 推荐下一层
- 调下层 init 脚本
- 跑真实 validator
- 自动写回交接

但还不能完全自动做：

- 语义级正文补写
- 高质量 `repair-existing` 内容重构

也就是说，现在它已经是可用 workflow，但还不是全自动写作代理。
