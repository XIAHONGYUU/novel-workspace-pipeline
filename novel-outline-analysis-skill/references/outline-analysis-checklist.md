# Outline Analysis Checklist

Use this checklist when writing a whole-novel outline analysis.

Do not finish the task until you have checked both:

- the common layers every novel should cover
- the book-specific structural modules unique to this novel

Default assumption:

- this skill often runs after a protagonist-centered workspace already exists
- existing protagonist files should be read and reused first
- the outline layer should grow on top of the protagonist layer, not ignore it

Recommended execution order:

1. read existing workspace files
2. convert existing protagonist knowledge into outline understanding
3. split the whole book by stages / regions / time / place
4. analyze core supporting characters through those stages and regions
5. cover common layers, then extract book-specific traits
6. compare outputs against the checklist until the stop condition is met

## A. Common Coverage Checklist

### 1. Project entry and handoff

Check whether the project has:

- `README.md` or equivalent entry note
- `工作状态-YYYY-MM-DD.md` or equivalent handoff note

If these do not exist, either create them or explicitly mark them missing.

### 2. Protagonist layer

Check whether the analysis can answer:

1. Who is the protagonist?
2. What is the protagonist's structural role?
3. What is the protagonist's core drive?
4. What is the protagonist's growth spine?
5. What is the protagonist's rough ending position?

Also check whether the project already has, or should now add:

- protagonist anchor / skeleton
- final protagonist card or concise protagonist summary

If existing protagonist files already cover this layer, reuse them instead of duplicating.

### 3. Core supporting cast and protagonist relations

Check whether the analysis identifies the supporting characters who genuinely pressure the plot.

For each core supporting character, verify you can answer:

1. How do they enter the protagonist's story?
2. What relationship type do they have with the protagonist?
3. What structural function does this relationship serve?
4. In which stage is the relationship most important?
5. How does the relationship close?

### 4. Stage split

Check whether the analysis answers:

1. How many real structural stages does the novel have?
2. Where does each stage begin and end?
3. What is each stage doing?
4. What is the main conflict of each stage?
5. Why is each boundary real?

Avoid:

- mechanical chapter slicing
- only saying early / middle / late

### 5. Core conflict points and explosion points

Check whether the analysis identifies:

1. The root long-term conflict
2. Stage-level conflicts
3. The major explosion points

At minimum, name:

- opening hook explosion point
- first major upgrade or loss
- midpoint shift
- pre-climax compression point
- climax explosion point
- ending settlement

For each explosion point, explain:

- what changes
- why it is structural
- what it pays off

### 6. Main line / side line map

Check whether the analysis clearly distinguishes:

- core main line
- major side lines
- temporary incident lines
- structural bridge lines

For each important line, answer:

1. What starts it?
2. What keeps it alive?
3. Where does it peak?
4. Does it close?

### 7. Time and place transitions

Check whether the analysis maps:

- opening time anchor
- major growth periods
- important time jumps
- stable accumulation periods
- structural acceleration periods
- starting location
- first major expansion location
- middle-stage main arenas
- late-stage or final arenas

Also check whether it explains:

- which stage changes are driven by time
- which are driven by place
- which depend on both time and place together

### 8. Climax, pacing, and ending closure

Check whether the analysis gives direct judgments on:

- opening strength
- middle expansion vs drift
- climax preparation
- ending closure quality

Useful labels include:

- `开篇成立`
- `主线清晰`
- `中段扩张有效`
- `中段局部重复`
- `中段松散`
- `高潮成立`
- `高潮准备不足`
- `结尾收束完整`
- `结尾收束偏弱`
- `结构收束强于情绪收束`

### 9. Structural strengths, weaknesses, and revision advice

Check whether the analysis directly states:

1. strongest structural strengths
2. biggest structural weaknesses
3. first-priority revision advice
4. best light-touch revision options

Prefer outline-level actions such as:

- merge weak side lines
- compress a dragging middle
- move a reveal earlier or later
- seed ending payoff earlier
- strengthen key relationship echoes

### 10. Next-step deep-dive directions

Check whether the analysis leaves `3 to 5` next-step directions, such as:

- high-value relationship lines
- high-value power or system modules
- high-value faction lines
- final-arc problems
- cross-link targets

## B. Book-Specific Structural Modules

Do not stop at generic structure coverage.

Identify `2 to 4` book-specific structural modules.

These must be actual structural engines, not vague qualities.

Bad examples:

- the setting is big
- the pacing is good
- there is a lot of growth

Good examples:

- 外挂系统
- 血脉质变
- 阵营博弈
- 规则恐怖
- 多世界扩边
- 终局位格抬升
- 关键关系回环
- 反派功能结构

For each book-specific module, verify you can answer:

1. How does it start the main line?
2. How does it expand in the middle?
3. Where does it become a stage boundary?
4. Where does it peak?
5. Does it close?

If the novel needs extra sections or files to make these modules explicit, add them.

## C. Minimum Durable File Expectations

### Core outline files

- `<小说名>-大纲总览.md`
- `<小说名>-阶段与篇章拆分.md`
- `<小说名>-主线支线与冲突地图.md`
- `<小说名>-核心冲突点与爆发点.md`
- `<小说名>-时间与地点转折.md`
- `<小说名>-高潮节奏与收束诊断.md`
- `<小说名>-结构问题与修改建议.md`

### Reuse or add when needed

- protagonist card or equivalent protagonist summary
- core supporting cast / protagonist relation summary
- `README.md`
- `工作状态-YYYY-MM-DD.md`

These can be newly created or satisfied by existing project files, but they must be checked explicitly.

## D. Final Completion Gate

Before you say the task is done, explicitly confirm:

1. `共性标准已覆盖` or `共性标准部分覆盖`
2. `单书特性已明确` or `单书特性仍不足`
3. which common layers were newly created
4. which common layers were satisfied by existing project files
5. which layers remain missing or should be the next step

If the result was written into a durable workspace, prefer running:

- `scripts/validate_outline_outputs.py --workspace "<工作区路径>" --novel-name "<小说名>"`

and use the validation result as part of the final completion judgment.

## Non-Goals

Do not let the analysis collapse into:

- character-card output for everyone
- worldbuilding encyclopedia output
- sentence-level prose critique
- line-by-line copy editing

Those may be follow-up tasks, but they are not the core job of this skill.
