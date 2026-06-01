#!/usr/bin/env python3
"""用 characters.json 数据自动修复配角层文件中的占位符。"""
import json, os, sys

BASE = '/home/zuoky/project'

def load_characters(workspace):
    merged_path = os.path.join(workspace, 'work', 'merged', 'characters.json')
    if not os.path.exists(merged_path):
        return {}, ''
    with open(merged_path) as f:
        chars = json.load(f)
    status_path = os.path.join(workspace, 'workspace-status.json')
    protagonist = ''
    if os.path.exists(status_path):
        with open(status_path) as f:
            protagonist = json.load(f).get('protagonist_name', '')
    char_map = {c['name']: c for c in chars if c.get('name')}
    return char_map, protagonist


def classify_role(char):
    roles = []
    rels = char.get('relationships', [])
    timeline = char.get('timeline', [])
    all_rels = ' '.join([r.get('type', '') for r in rels])

    if any(t in all_rels for t in ['师徒', '师父', '师尊', '师傅', '弟子', '徒弟']):
        roles.append('引路/传承配角')
    if any(t in all_rels for t in ['敌对', '仇敌', '对手', '敌人', '追杀']):
        roles.append('压力/对抗配角')
    if any(t in all_rels for t in ['道侣', '妻子', '丈夫', '恋人', '情侣', '爱慕', '伴侣']):
        roles.append('联盟/情感支点')
    if any(t in all_rels for t in ['朋友', '同伴', '兄弟', '姐妹', '好友', '闺蜜']):
        roles.append('联盟/情感支点')
    if any(t in all_rels for t in ['下属', '属下', '手下', '仆从', '追随', '主人-', '主仆']):
        roles.append('势力窗口')

    stages = [t.get('stage', '') for t in timeline]
    stage_set = set()
    for s in stages:
        if any(k in s for k in ['初', '早期', '开篇', '第一']):
            stage_set.add('early')
        if any(k in s for k in ['中']):
            stage_set.add('mid')
        if any(k in s for k in ['后', '末期', '终', '最后']):
            stage_set.add('late')
    if len(stage_set) >= 2:
        roles.append('跨阶段支点')

    if char.get('mention_count', 0) > 500:
        roles.insert(0, '主角路径改写点')

    if not roles:
        roles.append('势力窗口')
    return ' / '.join(roles[:3])


def gen_review(char):
    m = char.get('mention_count', 0)
    tc = len(char.get('timeline', []))
    rc = len(char.get('relationships', []))
    identity = char.get('identity', '')
    personality = char.get('personality', [])

    if m >= 200 and tc >= 3:
        dec, conf = '确认入选', '高'
    elif m >= 50:
        dec, conf = '确认入选', '中'
    else:
        dec, conf = '建议观察', '低'

    review = f'[自动复核|置信度:{conf}] {dec}。提及{m}次，关键事件{tc}个，关系{rc}条。'
    if personality:
        review += f'性格：{"、".join(personality[:3])}。'
    review += f'身份：{identity}。角色：{classify_role(char)}。'
    return review


def gen_reason(char, rank):
    m = char.get('mention_count', 0)
    summary = char.get('summary', '')
    parts = []
    if m > 500:
        parts.append(f'出场频次极高({m}次提及)')
    elif m > 100:
        parts.append(f'出场频次高({m}次提及)')
    parts.append(f'结构角色：{classify_role(char)}')
    if summary:
        parts.append(f'核心作用：{summary[:50]}')
    return '；'.join(parts) if parts else f'Top{rank}入选'


def repair_table(workspace, novel_name, char_map):
    table_path = os.path.join(workspace, f'{novel_name}-重要配角Top10总表.md')
    if not os.path.exists(table_path):
        print(f"    SKIP: Top10 table not found")
        return

    with open(table_path) as f:
        lines = f.readlines()

    new_lines = []
    updated = 0
    for line in lines:
        if line.startswith('|') and '待AI复核' in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 9:
                name = parts[2].strip()
                char = char_map.get(name)
                if char:
                    review = gen_review(char)
                    reason = gen_reason(char, '')
                    parts[-3] = review
                    parts[-2] = '确认入选'
                    parts[-1] = reason
                    new_line = '| ' + ' | '.join(parts[1:-1]) + ' |\n'
                    new_lines.append(new_line)
                    updated += 1
                    print(f"    OK {name}")
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    with open(table_path, 'w') as f:
        f.writelines(new_lines)
    print(f"    Table: {updated} rows updated")


def repair_profile(workspace, novel_name, char_map):
    sc_dir = os.path.join(workspace, 'supporting-cast')
    if not os.path.exists(sc_dir):
        return

    count = 0
    for fname in os.listdir(sc_dir):
        if not fname.endswith('-配角分析.md'):
            continue
        name = fname.replace('-配角分析.md', '')
        char = char_map.get(name)
        if not char:
            continue

        fpath = os.path.join(sc_dir, fname)
        with open(fpath) as f:
            content = f.read()

        if '待AI复核' not in content and 'placeholder' not in content.lower():
            continue

        aliases = char.get('aliases', [])
        aliases_str = '、'.join(aliases[:5]) if aliases else name
        personality = char.get('personality', [])
        pers_str = '、'.join(personality[:5]) if personality else '待补充'
        abilities = char.get('abilities', [])
        abil_str = '；'.join(abilities[:5]) if abilities else '待补充'
        timeline = char.get('timeline', [])
        rels = char.get('relationships', [])
        rel_strs = [f"{r.get('type','?')}({r.get('target','?')})" for r in rels[:8]]
        rel_summary = '；'.join(rel_strs) if rel_strs else '待补充'

        role = classify_role(char)
        mention = char.get('mention_count', 0)
        tc = len(timeline)

        stages = [t.get('stage', '') for t in timeline]
        has_early = any(any(k in s for k in ['初','早期','开篇','第一','前']) for s in stages)
        has_late = any(any(k in s for k in ['后','末期','终','最后']) for s in stages)
        if has_early and has_late:
            stage_judge = f'横跨前中后段({tc}个关键事件)，贯穿型配角'
        elif has_early:
            stage_judge = f'集中前中段({tc}个关键事件)，前期关键配角'
        else:
            stage_judge = f'分布较均匀({tc}个关键事件)，持续型配角'

        importance = '核心配角' if mention >= 200 else '重要配角' if mention >= 50 else '次要配角'

        new_content = f"""# {name}

## 关键词索引

- **角色定位**：{role}
- **关系锚点**：{rel_summary}
- **阶段判断**：{stage_judge}
- **入榜入口**：自动评估(提及{mention}次)

## 基本信息

- 姓名：{name}
- 常见称谓：{aliases_str}
- 当前确认定位：{importance}
- 开篇身份：{char.get('first_appearance', '未知')}
- 身份底座：{char.get('identity', '未知')}
- 所属势力：{char.get('faction', '未知')}

## 身份概述

{char.get('summary', '待从原文提取')}

## 性格特质

{pers_str}

## 能力体系

{abil_str}

## 身份变化

"""
        for t in timeline[:12]:
            new_content += f"- {t.get('stage', '?')}：{t.get('event', '?')}\n"

        new_content += f"""
## 与主角关系

{rel_summary}

## 结构角色分析

- **主角色**：{role.split(' / ')[0] if ' / ' in role else role}
- **阶段分布**：{stage_judge}
- **重要性评估**：基于{mention}次提及和{tc}个关键事件，判定为{importance}

## 生成标记

- 数据来源：characters.json 自动提取
- 复核状态：数据驱动自动填充
- 备注：建议基于原文进一步人工精修
"""
        with open(fpath, 'w') as f:
            f.write(new_content)
        count += 1

    if count:
        print(f"    Profiles: {count} files updated")


def main():
    novels = sys.argv[1:] if len(sys.argv) > 1 else [
        '永恒剑主', '序列大明', '巫师世界', '我的诡异人生', '玄浑道章'
    ]

    for novel in novels:
        workspace = os.path.join(BASE, novel)
        if not os.path.exists(workspace):
            print(f"SKIP {novel}: not found")
            continue

        char_map, prot = load_characters(workspace)
        if not char_map:
            print(f"SKIP {novel}: no character data")
            continue

        print(f"\n=== {novel} ({len(char_map)} chars, prot={prot}) ===")
        repair_table(workspace, novel, char_map)
        repair_profile(workspace, novel, char_map)


if __name__ == '__main__':
    main()
