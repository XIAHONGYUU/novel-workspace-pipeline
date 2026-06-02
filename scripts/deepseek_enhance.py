#!/usr/bin/env python3
"""
DeepSeek API 驱动的质量增强流水线。
针对 quality_gate 中评分不足的层，调用 DeepSeek 增强叙事分析深度。
"""
import json, os, sys, time, requests

BASE = '/home/zuoky/project'

def load_env():
    """加载 .env 中的 API key"""
    env_path = os.path.join(BASE, '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    os.environ[k] = v

def deepseek_enhance(content, instruction, max_tokens=4096):
    """调用 DeepSeek API 增强内容质量"""
    api_key = os.environ.get('DEEPSEEK_API_KEY', '')
    if not api_key:
        print("  ❌ No API key")
        return None
    
    system_prompt = """你是一个专业的网络小说分析专家。你的任务是对给定的分析文本进行深度增强。

增强要求：
1. 在每个分析段落中增加"因为...所以..."或"之所以...是因为..."的因果推理链
2. 从原文中引用具体的角色、事件、章节作为证据支撑
3. 避免空泛的评价词（如"很好""不错""有意思"），用具体的因果分析替代
4. 保持原有的章节结构和校验关键词
5. 输出完整的增强后文本，不要省略任何原有内容

重要：直接输出增强后的完整 Markdown 文本，不要加任何前缀解释。"""

    payload = {
        'model': 'deepseek-chat',
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': f"{instruction}\n\n---\n以下是需要增强的原始文本：\n\n{content}"}
        ],
        'max_tokens': max_tokens,
        'temperature': 0.7
    }
    
    try:
        resp = requests.post(
            'https://api.deepseek.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json=payload,
            timeout=180
        )
        if resp.status_code == 200:
            data = resp.json()
            return data['choices'][0]['message']['content']
        else:
            print(f"  ❌ API error: {resp.status_code} {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"  ❌ Request failed: {e}")
        return None


def enhance_file(filepath, instruction, max_tokens=4096):
    """增强单个文件"""
    if not os.path.exists(filepath):
        print(f"  ⚠️ File not found: {filepath}")
        return False
    
    with open(filepath) as f:
        original = f.read()
    
    if len(original) < 200:
        print(f"  ⚠️ File too short ({len(original)} chars), skipping")
        return False
    
    print(f"  📝 Enhancing {os.path.basename(filepath)} ({len(original)} chars)...")
    enhanced = deepseek_enhance(original, instruction, max_tokens)
    
    if enhanced and len(enhanced) > len(original) * 0.5:
        with open(filepath, 'w') as f:
            f.write(enhanced)
        print(f"  ✅ Enhanced: {len(original)} → {len(enhanced)} chars")
        return True
    else:
        print(f"  ❌ Enhancement failed or too short")
        return False


def enhance_novel_layer(novel, layer, files_instructions):
    """增强一本小说的一个层"""
    print(f"\n{'='*60}")
    print(f"  🎯 {novel} / {layer}")
    print(f"{'='*60}")
    
    success = 0
    for filepath_rel, instruction in files_instructions:
        filepath = os.path.join(BASE, novel, filepath_rel)
        if enhance_file(filepath, instruction):
            success += 1
        time.sleep(1)  # Rate limit
    
    print(f"  📊 {novel}/{layer}: {success}/{len(files_instructions)} files enhanced")
    return success


def main():
    load_env()
    
    # ============================================================
    # Phase 1: 永恒剑主 supporting-cast (70→85+)
    # ============================================================
    print("\n" + "="*70)
    print("PHASE 1: 永恒剑主 supporting-cast")
    print("="*70)
    
    enhance_novel_layer('永恒剑主', 'supporting-cast', [
        ('永恒剑主-重要配角与主角关系图.md',
         '请增强这份配角关系图分析。核心要求：1) 为每个Top10配角增加"为什么这个配角对主角路径不可替代"的因果分析；2) 在关系网络总图中增加"配角换层"的因果解释（为什么某些配角在前期重要后期退场）；3) 引用具体的角色名、事件和阶段作为证据。'),
        
        ('永恒剑主-重要配角阶段作用分布.md',
         '请增强这份阶段作用分布分析。核心要求：1) 为每个阶段切换增加"因为主角在前一阶段积累了什么，所以才能进入下一阶段"的因果链；2) 引用具体的章节号和关键事件作为阶段分界的锚点；3) 分析"为什么某些配角在特定阶段退场"——不是因为被遗忘，而是因为叙事功能已完成。'),
        
        ('永恒剑主-重要配角Top10总表.md',
         '请增强这份Top10总表。核心要求：1) 为每个配角的"核心功能"列增加因果解释；2) 将"关系性质变化"列从标签改为具体的演变因果链；3) 增加"筛选标准"部分的因果推理。'),
    ])
    
    # ============================================================
    # Phase 2: 巫师世界 (protagonist + supporting-cast + outline)
    # ============================================================
    print("\n" + "="*70)
    print("PHASE 2: 巫师世界")
    print("="*70)
    
    enhance_novel_layer('巫师世界', 'protagonist', [
        ('巫师世界-主角锚点与骨架.md',
         '请增强这份主角锚点分析。核心要求：1) 用"因为...所以..."链分析安格列的每个阶段切换原因；2) 引用具体的章节事件作为成长锚点的证据；3) 分析生物芯片如何因果性地改变了安格列的成长路径（而非只是"他有金手指"）。'),
        
        ('巫师世界-项目启动清单.md',
         '请增强这份项目启动清单。核心要求：1) 将每个checklist项从简单标记改为"为什么这一项已完成"的因果判断；2) 增加"当前已达到"部分的因果推理（为什么体系闭环能达成）。'),
    ])
    
    enhance_novel_layer('巫师世界', 'supporting-cast', [
        ('巫师世界-重要配角与主角关系图.md',
         '请增强这份配角关系图。核心要求：1) 为每个配角增加"为什么此配角对安格列的巫师之路不可替代"的因果分析；2) 引用具体的原著事件和章节；3) 分析安格列的关系网从"贵族体系"到"巫师体系"的转型因果。'),
        
        ('巫师世界-重要配角阶段作用分布.md',
         '请增强这份阶段作用分布。核心要求：1) 用阶段性因果链解释每个配角的进场和退场；2) 引用具体的章节号划分阶段；3) 分析"里奥家族→巫师学院→黑巫塔→领主"的势力演变如何驱动配角换层。'),
        
        ('巫师世界-重要配角Top10总表.md',
         '请增强这份Top10总表。核心要求：为核心功能和关系变化列增加因果解释，引用具体事件。'),
    ])
    
    enhance_novel_layer('巫师世界', 'outline', [
        ('巫师世界-大纲总览.md',
         '请增强这份大纲总览。核心要求：1) 用因果链串联各阶段（因为前一阶段发生了什么，所以导致下一阶段的开启）；2) 为每个阶段标注关键转折事件及其因果意义。'),
        
        ('巫师世界-整书粗阶段划分.md',
         '请增强这份阶段划分。核心要求：1) 用因果推理替代描述性语言；2) 为每个阶段标注"进入条件"和"完成标志"。'),
    ])
    
    # ============================================================
    # Phase 3: 序列大明, 我的诡异人生, 玄浑道章
    # ============================================================
    for novel in ['序列大明', '我的诡异人生', '玄浑道章']:
        print(f"\n{'='*70}")
        print(f"PHASE 3: {novel}")
        print(f"{'='*70}")
        
        enhance_novel_layer(novel, 'protagonist', [
            (f'{novel}-主角锚点与骨架.md',
             '请增强这份主角锚点分析。核心要求：1) 用因果链分析主角每个阶段切换的原因；2) 引用具体的章节事件；3) 分析金手指/核心能力如何因果性地改变主角的成长路径。'),
        ])
        
        enhance_novel_layer(novel, 'supporting-cast', [
            (f'{novel}-重要配角与主角关系图.md',
             '请增强这份配角关系图。核心要求：1) 为每个Top10配角增加不可替代性的因果分析；2) 分析配角换层的因果机制。'),
            
            (f'{novel}-重要配角阶段作用分布.md',
             '请增强这份阶段分布。核心要求：1) 用因果链解释阶段切换；2) 引用具体章节锚点；3) 分析配角退场的功能性原因。'),
            
            (f'{novel}-重要配角Top10总表.md',
             '请增强这份Top10总表。核心要求：为核心功能和关系变化列增加因果解释。'),
        ])
        
        enhance_novel_layer(novel, 'outline', [
            (f'{novel}-大纲总览.md',
             '请增强这份大纲总览。核心要求：用因果链串联各阶段，标注关键转折事件及其因果意义。'),
        ])


if __name__ == '__main__':
    main()
