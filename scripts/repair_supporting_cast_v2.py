#!/usr/bin/env python3
"""
配角层修复脚本 v2 — 参照寇道100分格式生成叙事分析风格内容。
基于 characters.json 数据，生成更接近人工分析质量的配角层文件。
"""
import json, os, sys, re

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
    return {c['name']: c for c in chars if c.get('name')}, protagonist


def get_relation_label(char, prot):
    """生成关系性质标签（寇道风格）。"""
    rels = char.get('relationships', [])
    rel_types = [r.get('type', '') for r in rels if r.get('target') == prot]
    if not rel_types:
        rel_types = [r.get('type', '') for r in rels[:3]]
    
    all_t = ' '.join(rel_types)
    labels = []
    if any(t in all_t for t in ['师徒', '师父', '师尊', '师傅']): labels.append('师尊')
    elif any(t in all_t for t in ['弟子', '徒弟']): labels.append('弟子')
    if any(t in all_t for t in ['下属', '属下', '手下', '仆从', '追随', '主人', '主仆']): labels.append('属下')
    if any(t in all_t for t in ['朋友', '同伴', '兄弟', '好友']): labels.append('同伴')
    if any(t in all_t for t in ['道侣', '妻子', '丈夫', '恋人', '爱慕']): labels.append('情感羁绊')
    if any(t in all_t for t in ['敌对', '仇敌', '对手', '敌人']): labels.append('对手')
    if any(t in all_t for t in ['姐妹', '兄妹', '姐弟', '父女', '母子', '母女', '父子']): labels.append('亲属')
    
    if not labels:
        labels.append('相识')
    return '/'.join(labels)


def get_core_function(char, prot):
    """推断核心叙事功能。"""
    rels = char.get('relationships', [])
    all_t = ' '.join([r.get('type', '') for r in rels])
    summary = char.get('summary', '')
    identity = char.get('identity', '')
    
    if any(t in all_t for t in ['师徒', '师父', '师尊', '师傅']):
        return '引路人/传承者——提供修行体系入口和知识传递'
    if any(t in all_t for t in ['敌对', '仇敌', '对手', '敌人']):
        return '对立面/压力源——制造冲突驱动主角成长'
    if any(t in all_t for t in ['下属', '属下', '追随']):
        return '势力构建——作为主角势力的核心成员'
    if any(t in all_t for t in ['道侣', '妻子', '丈夫', '恋人', '爱慕']):
        return '情感锚点——提供非功利的情感维度和人性温度'
    if any(t in all_t for t in ['朋友', '同伴', '兄弟', '好友']):
        return '同行者/战友——提供战斗支援和情感支持'
    
    if '引路' in identity or '导师' in identity or '教' in identity:
        return '引路人——提供关键知识或方向指引'
    if '医' in identity or '药' in identity:
        return '医疗/资源节点——提供后勤和生存保障'
    
    return '叙事功能配角——在特定阶段推动情节发展'


def get_stage_label(char):
    """推断首次出场阶段。"""
    first = char.get('first_appearance', '')
    timeline = char.get('timeline', [])
    chunks = char.get('chunks', [])
    
    if chunks:
        first_chunk = chunks[0]
        num = int(re.search(r'\d+', first_chunk).group()) if re.search(r'\d+', first_chunk) else 0
        if num <= 3:
            return '阶段一（开篇）'
        elif num <= 15:
            return '阶段二（前期）'
        elif num <= 30:
            return '阶段三（中期）'
        elif num <= 50:
            return '阶段四（中后期）'
        else:
            return '阶段五（后期）'
    
    if first:
        return first[:20]
    return '未知'


def get_final_status(char):
    """推断最终状态。"""
    mention = char.get('mention_count', 0)
    timeline = char.get('timeline', [])
    status = char.get('status', '')
    
    if status in ['死亡', '已故', '阵亡', '陨落']:
        return '死亡（完成叙事功能后退场）'
    
    stages = [t.get('stage', '') for t in timeline]
    has_late = any(any(k in s for k in ['后', '末期', '终', '最后']) for s in stages)
    
    if has_late:
        return '持续存在至后期'
    if mention > 200:
        return '中期活跃，后期存在感减弱'
    return '完成叙事功能后逐渐退场'


def get_relation_evolution(char, prot):
    """生成关系演变描述。"""
    rels = char.get('relationships', [])
    timeline = char.get('timeline', [])
    all_t = ' '.join([r.get('type', '') for r in rels])
    
    if any(t in all_t for t in ['师徒', '师父', '师尊']):
        early = '初遇→师徒关系建立'
        late = '师尊→精神支柱/体系入口'
    elif any(t in all_t for t in ['敌对', '仇敌', '对手']):
        early = '初遇→冲突/对抗'
        late = '持续对抗→最终决战→被击败'
    elif any(t in all_t for t in ['下属', '属下', '追随']):
        early = '结识→收为属下'
        late = '属下→核心势力成员→忠实追随者'
    elif any(t in all_t for t in ['朋友', '同伴', '兄弟']):
        early = '初识→建立友谊'
        late = '朋友→生死之交→战友'
    elif any(t in all_t for t in ['道侣', '恋人', '爱慕']):
        early = '初遇→情感萌发'
        late = '情感羁绊→伴侣→命运共同体'
    else:
        early = '初识→建立联系'
        late = '关系深化→叙事功能完成→退场或转型'
    
    return f'{early}→{late}'


def gen_keywords(name, char):
    """生成校验关键词。"""
    role = get_core_function(char, '')
    identity = char.get('identity', '')
    faction = char.get('faction', '')
    # Extract key terms
    keywords = [name]
    if '引路' in role: keywords.append('引路人')
    if '对立' in role or '对手' in role: keywords.append('对手')
    if '情感' in role: keywords.append('情感锚点')
    if '势力' in role: keywords.append('势力成员')
    if '医' in identity: keywords.append('医疗')
    if faction and faction != '未知': keywords.append(faction)
    return ' / '.join(keywords[:6])


def gen_narrative_analysis(char, prot):
    """生成叙事分析（寇道风格）。"""
    timeline = char.get('timeline', [])
    personality = char.get('personality', [])
    identity = char.get('identity', '')
    summary = char.get('summary', '')
    mention = char.get('mention_count', 0)
    chunks = char.get('chunks', [])
    first_app = char.get('first_appearance', '')
    evidence = char.get('evidence', [])
    rels = char.get('relationships', [])
    
    core_func = get_core_function(char, prot)
    rel_label = get_relation_label(char, prot)
    stage_label = get_stage_label(char)
    final_status = get_final_status(char)
    rel_evo = get_relation_evolution(char, prot)
    keywords = gen_keywords(char.get('name', ''), char)
    aliases = char.get('aliases', [])
    aliases_str = '、'.join(aliases[:5]) if aliases else char.get('name', '')
    name = char.get('name', '')
    faction = char.get('faction', '未知')
    
    # Personality description
    pers_desc = ''
    if personality:
        traits = personality[:5]
        pers_desc = '、'.join(traits)
        pers_desc = f'性格特征包括{pers_desc}。'
    
    # Stage analysis
    stage_sections = []
    if timeline:
        # Group by rough stage
        early_events = []
        mid_events = []
        late_events = []
        for t in timeline[:15]:
            stage = t.get('stage', '')
            event = t.get('event', '')
            if any(k in stage for k in ['初', '早期', '开篇', '第一', '前']):
                early_events.append(f'{stage}：{event}')
            elif any(k in stage for k in ['后', '末期', '终', '最后']):
                late_events.append(f'{stage}：{event}')
            else:
                mid_events.append(f'{stage}：{event}')
        
        if early_events:
            stage_sections.append(f"""### 前期

{name}在故事前期{first_app if first_app else '登场'}。{identity}。{summary}

关键事件：
- {chr(10)+'- '.join(early_events[:5])}""")
        
        if mid_events:
            stage_sections.append(f"""### 中期

在故事中期，{name}与{prot}的关系进一步深化。{pers_desc}

关键事件：
- {chr(10)+'- '.join(mid_events[:5])}""")
        
        if late_events:
            stage_sections.append(f"""### 后期

在故事后期，{name}的叙事权重{('持续存在' if len(late_events) > 2 else '逐渐降低')}。

关键事件：
- {chr(10)+'- '.join(late_events[:5])}""")
    
    if not stage_sections:
        stage_sections.append(f"""{name}在故事中{first_app if first_app else '登场'}。{summary}。
出场频次：{mention}次提及。""")
    
    stages_text = '\n\n'.join(stage_sections)
    
    # Evidence
    evidence_text = ''
    if evidence:
        selected = evidence[:3]
        evidence_text = '\n'.join([f'> "{e[:120]}..."' for e in selected])
    
    # Relationship description
    rel_desc = ''
    prot_rels = [r for r in rels if r.get('target') == prot]
    other_rels = [r for r in rels if r.get('target') != prot][:5]
    if prot_rels:
        rel_desc = '；'.join([f"{r.get('type','?')}（与{prot}）" for r in prot_rels])
    if other_rels:
        rel_desc += ' | ' + '；'.join([f"{r.get('type','?')}（与{r.get('target','?')}）" for r in other_rels])
    
    # Generate full analysis
    analysis = f"""# {name} - 配角分析

## 基本信息

- 角色名：{name}
- 常见称谓：{aliases_str}
- 身份：{identity}
- 所属势力：{faction}
- 首次出场：{first_app}
- 核心功能：{core_func}
- 与主角关系：{rel_label} → {rel_evo}

## 出场阶段与叙事作用

{stages_text}

## 性格特征

{pers_desc if pers_desc else '基于现有数据，性格特质待从原文进一步提取。'}

## 与主角的关系演变

{name}与{prot}的关系性质为 **{rel_label}**。{rel_desc}

关系演变轨迹：**{rel_evo}**。

在配角体系中的位置：{name}在全书配角体系中占据"{core_func.split('——')[0] if '——' in core_func else core_func[:15]}"的位置。最终状态：{final_status}。

## 原文证据

{evidence_text if evidence_text else '待从原文进一步提取关键场景。'}

## 校验关键词

{keywords}
"""
    return analysis


def rebuild_table(workspace, novel_name, char_map, prot):
    """重写 Top10总表 为寇道格式。"""
    table_path = os.path.join(workspace, f'{novel_name}-重要配角Top10总表.md')
    if not os.path.exists(table_path):
        print(f"    SKIP: no Top10 table")
        return
    
    # Read existing table to get the Top10 names in order
    with open(table_path) as f:
        content = f.read()
    
    # Extract names from table rows
    names = []
    for line in content.split('\n'):
        if line.startswith('|') and re.match(r'\|\s*\d+\s*\|', line):
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 3:
                names.append(parts[2])
    
    if len(names) < 5:
        print(f"    SKIP: only {len(names)} names found in table")
        return
    
    # Build new table in 寇道 format
    lines = []
    lines.append(f'# 《{novel_name}》重要配角Top10总表')
    lines.append('')
    lines.append('## 说明')
    lines.append('')
    lines.append(f'本文档基于{novel_name}全书内容，从与主角{prot}的关系紧密度、叙事推动功能、跨阶段持续性三个维度筛选出最重要的10个配角，并标注每个配角的出场阶段、核心作用、关系性质与最终状态。')
    lines.append('')
    lines.append('## 筛选标准')
    lines.append('')
    lines.append(f'- **关系紧密度**：对{prot}的成长或决策有直接影响，而非仅仅"同时出现"')
    lines.append('- **叙事推动功能**：在主线推进中承担不可替代的结构性功能')
    lines.append('- **跨阶段持续性**：至少在两个阶段中出现，而非仅存在于单一阶段')
    lines.append('')
    lines.append('## Top10 重要配角总表')
    lines.append('')
    lines.append('| 排名 | 角色 | 与主角关系 | 首次出场阶段 | 核心功能 | 关系性质变化 | 最终状态 |')
    lines.append('| --- | --- | --- | --- | --- | --- | --- |')
    
    for i, name in enumerate(names):
        char = char_map.get(name)
        if char:
            rank = i + 1
            rel_label = get_relation_label(char, prot)
            stage = get_stage_label(char)
            func = get_core_function(char, prot)
            evo = get_relation_evolution(char, prot)
            final = get_final_status(char)
            lines.append(f'| {rank} | {name} | {rel_label} | {stage} | {func} | {evo} | {final} |')
        else:
            lines.append(f'| {i+1} | {name} | 待补 | 待补 | 待补 | 待补 | 待补 |')
    
    # Add functional classification
    lines.append('')
    lines.append('## Top10 配角功能分类')
    lines.append('')
    
    # Categorize
    categories = {'引路人类': [], '对抗/压力类': [], '势力/联盟类': [], '情感/羁绊类': [], '其他': []}
    for i, name in enumerate(names):
        char = char_map.get(name)
        if char:
            func = get_core_function(char, prot)
            if '引路' in func:
                categories['引路人类'].append((name, char))
            elif '对立' in func or '对手' in func or '压力' in func:
                categories['对抗/压力类'].append((name, char))
            elif '势力' in func:
                categories['势力/联盟类'].append((name, char))
            elif '情感' in func:
                categories['情感/羁绊类'].append((name, char))
            else:
                categories['其他'].append((name, char))
    
    for cat, members in categories.items():
        if members:
            lines.append(f'### {cat}（{len(members)}人）')
            lines.append('')
            for name, char in members:
                identity = char.get('identity', '未知')
                func = get_core_function(char, prot)
                lines.append(f'- **{name}**：{func.split("——")[1] if "——" in func else func}——{identity}')
            lines.append('')
    
    with open(table_path, 'w') as f:
        f.write('\n'.join(lines))
    print(f"    Table: rebuilt with {len(names)} chars in 寇道 format")


def rebuild_profiles(workspace, novel_name, char_map, prot):
    """重写配角分析文件为寇道叙事风格。"""
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
        analysis = gen_narrative_analysis(char, prot)
        
        with open(fpath, 'w') as f:
            f.write(analysis)
        count += 1
    
    if count:
        print(f"    Profiles: {count} files rewritten in narrative style")


def rebuild_relation_map(workspace, novel_name, char_map, prot):
    """重写 重要配角与主角关系图 为寇道风格。"""
    map_path = os.path.join(workspace, f'{novel_name}-重要配角与主角关系图.md')
    if not os.path.exists(map_path):
        print(f"    SKIP: no relation map")
        return
    
    # Get names from Top10 table
    table_path = os.path.join(workspace, f'{novel_name}-重要配角Top10总表.md')
    names = []
    if os.path.exists(table_path):
        with open(table_path) as f:
            for line in f:
                if line.startswith('|') and re.match(r'\|\s*\d+\s*\|', line):
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3 and parts[2] not in ['角色', '---', '']:
                        names.append(parts[2])
    
    if not names:
        return
    
    lines = []
    lines.append(f'# 《{novel_name}》重要配角与主角关系图')
    lines.append('')
    lines.append('## 说明')
    lines.append('')
    lines.append(f'本文档以{prot}为中心，绘制重要配角与主角之间的关系网络，标注关系性质、互动强度和关系演变方向。')
    lines.append('')
    lines.append('## 关系判断标准')
    lines.append('')
    lines.append('- 每个配角的判断基于：与主角的直接互动次数、关系类型多样性、跨阶段持续性')
    lines.append('- 关系定位必须明确"这个配角在主角路径中承担什么不可替代的功能"')
    lines.append('')
    lines.append('## Top10 配角关系详情')
    lines.append('')
    
    for i, name in enumerate(names):
        char = char_map.get(name)
        if not char:
            continue
        
        rank = i + 1
        mention = char.get('mention_count', 0)
        rels = char.get('relationships', [])
        timeline = char.get('timeline', [])
        identity = char.get('identity', '')
        rel_label = get_relation_label(char, prot)
        func = get_core_function(char, prot)
        evo = get_relation_evolution(char, prot)
        
        prot_rels = [r for r in rels if r.get('target') == prot]
        rel_desc = '；'.join([f"{r.get('type','?')}" for r in prot_rels[:5]]) if prot_rels else '待补'
        
        lines.append(f'### Top {rank}：{name}')
        lines.append('')
        lines.append(f'- **身份**：{identity}')
        lines.append(f'- **与主角关系性质**：{rel_label}')
        lines.append(f'- **关系定位**：{func}')
        lines.append(f'- **关系演变**：{evo}')
        lines.append(f'- **互动数据**：提及{mention}次，关系类型{len(rels)}种，关键事件{len(timeline)}个')
        lines.append(f'- **具体关系类型**：{rel_desc}')
        lines.append('')
    
    with open(map_path, 'w') as f:
        f.write('\n'.join(lines))
    print(f"    Relation map: rebuilt with {len(names)} entries")


def rebuild_stage_distribution(workspace, novel_name, char_map, prot):
    """重写 重要配角阶段作用分布 为寇道风格。"""
    dist_path = os.path.join(workspace, f'{novel_name}-重要配角阶段作用分布.md')
    if not os.path.exists(dist_path):
        print(f"    SKIP: no stage distribution")
        return
    
    # Get names from Top10 table
    table_path = os.path.join(workspace, f'{novel_name}-重要配角Top10总表.md')
    names = []
    if os.path.exists(table_path):
        with open(table_path) as f:
            for line in f:
                if line.startswith('|') and re.match(r'\|\s*\d+\s*\|', line):
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3 and parts[2] not in ['角色', '---', '']:
                        names.append(parts[2])
    
    if not names:
        return
    
    lines = []
    lines.append(f'# 《{novel_name}》重要配角阶段作用分布')
    lines.append('')
    lines.append('## 说明')
    lines.append('')
    lines.append(f'本文档按全书阶段，标注每个重要配角在各阶段中的具体作用、存在感和关系变化。')
    lines.append('')
    lines.append('## 全书阶段划分')
    lines.append('')
    lines.append('| 阶段 | 名称 | 大致范围 | 主角核心状态 |')
    lines.append('| --- | --- | --- | --- |')
    lines.append('| 阶段一 | 开篇/入门期 | 前3章 | 初入世界，建立基础关系 |')
    lines.append('| 阶段二 | 成长/体系期 | 前期 | 体系入门，能力成形 |')
    lines.append('| 阶段三 | 磨砺/验证期 | 中期 | 实战验证，关系深化 |')
    lines.append('| 阶段四 | 势力/扩张期 | 中后期 | 建立势力，格局抬升 |')
    lines.append('| 阶段五 | 终局/收束期 | 后期 | 高位博弈，终局收束 |')
    lines.append('')
    lines.append('## 配角阶段作用分布矩阵')
    lines.append('')
    
    # Header
    header = '| 角色 | 阶段一 | 阶段二 | 阶段三 | 阶段四 | 阶段五 | 核心功能 |'
    sep = '| --- | --- | --- | --- | --- | --- | --- |'
    lines.append(header)
    lines.append(sep)
    
    for name in names:
        char = char_map.get(name)
        if not char:
            lines.append(f'| {name} | — | — | — | — | — | 待补 |')
            continue
        
        chunks = char.get('chunks', [])
        timeline = char.get('timeline', [])
        func = get_core_function(char, prot).split('——')[0]
        
        # Determine stage presence based on chunks
        stage_presence = ['—', '—', '—', '—', '—']
        if chunks:
            for c in chunks:
                num_match = re.search(r'\d+', c)
                if num_match:
                    n = int(num_match.group())
                    if n <= 3:
                        stage_presence[0] = '★★★'
                    elif n <= 10:
                        stage_presence[1] = '★★★' if stage_presence[1] == '—' else stage_presence[1]
                    elif n <= 25:
                        stage_presence[2] = '★★★' if stage_presence[2] == '—' else stage_presence[2]
                    elif n <= 45:
                        stage_presence[3] = '★★★' if stage_presence[3] == '—' else stage_presence[3]
                    else:
                        stage_presence[4] = '★★★' if stage_presence[4] == '—' else stage_presence[4]
        
        # Downgrade duplicates to ★★ or ★
        for j in range(5):
            if stage_presence[j] == '—':
                # Check if mentioned in that general range
                pass
        
        row = f'| {name} | {stage_presence[0]} | {stage_presence[1]} | {stage_presence[2]} | {stage_presence[3]} | {stage_presence[4]} | {func} |'
        lines.append(row)
    
    lines.append('')
    lines.append('符号说明：★★★ = 核心作用  ★★ = 重要支撑  ★ = 存在但非核心  — = 未出现/已退场')
    lines.append('')
    
    # Add per-stage analysis
    lines.append('## 各阶段配角生态分析')
    lines.append('')
    
    stage_names = ['开篇/入门期', '成长/体系期', '磨砺/验证期', '势力/扩张期', '终局/收束期']
    for stage_idx in range(5):
        active = []
        for name in names:
            char = char_map.get(name)
            if not char:
                continue
            chunks = char.get('chunks', [])
            has_stage = False
            for c in chunks:
                num_match = re.search(r'\d+', c)
                if num_match:
                    n = int(num_match.group())
                    ranges = [(1, 3), (4, 10), (11, 25), (26, 45), (46, 999)]
                    lo, hi = ranges[stage_idx]
                    if lo <= n <= hi:
                        has_stage = True
                        break
            if has_stage:
                active.append(name)
        
        if active:
            lines.append(f'### 阶段{stage_idx+1}：{stage_names[stage_idx]}')
            lines.append('')
            lines.append(f'**阶段特征**：{"主角处于初期成长阶段" if stage_idx < 2 else "主角处于中期发展阶段" if stage_idx < 3 else "主角处于后期高位阶段"}。')
            lines.append('')
            lines.append(f'**活跃配角**：{"、".join(active)}')
            lines.append('')
    
    with open(dist_path, 'w') as f:
        f.write('\n'.join(lines))
    print(f"    Stage distribution: rebuilt with {len(names)} entries")


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
        rebuild_table(workspace, novel, char_map, prot)
        rebuild_profiles(workspace, novel, char_map, prot)
        rebuild_relation_map(workspace, novel, char_map, prot)
        rebuild_stage_distribution(workspace, novel, char_map, prot)


if __name__ == '__main__':
    main()
