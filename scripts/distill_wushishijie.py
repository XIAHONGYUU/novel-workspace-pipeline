#!/usr/bin/env python3
"""巫师世界 全书章节蒸馏 — 3章/批 DeepSeek API"""
import os, sys, time, re, requests, shutil

BASE = '/home/zuoky/project'
NOVEL = '巫师世界'
SOURCE = os.path.join(BASE, NOVEL, 'source', '巫师世界.md')
SKELETON = os.path.join(BASE, NOVEL, f'{NOVEL}-章节蒸馏骨架.md')
PROGRESS = os.path.join(BASE, NOVEL, '.distill_progress')
BATCH_SIZE = 3

def load_env():
    with open(os.path.join(BASE, '.env')) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k] = v

def read_chapters():
    """UTF-8 源文件，按 '## 第XXX章' 分割"""
    with open(SOURCE, encoding='utf-8') as f:
        lines = f.readlines()
    
    chapters = []
    cur_title, cur_lines = '', []
    in_chapter = False
    
    for line in lines:
        m = re.match(r'^## 第(\d+)章\s*(.*)', line.strip())
        if m:
            if in_chapter:
                chapters.append((len(chapters)+1, cur_title.strip(), ''.join(cur_lines)))
            cur_title = f"第{m.group(1)}章 {m.group(2).strip()}"
            cur_lines = []
            in_chapter = True
        elif in_chapter:
            cur_lines.append(line)
    
    if in_chapter:
        chapters.append((len(chapters)+1, cur_title.strip(), ''.join(cur_lines)))
    
    return chapters

def call_api(batch):
    """蒸馏一批章节"""
    api_key = os.environ.get('DEEPSEEK_API_KEY', '')
    if not api_key: return None
    
    # 构建源文本（每章截断到2500字）
    src = ""
    for seq, title, body in batch:
        b = body[:2500] if len(body) > 3000 else body
        src += f"\n{title}\n{b}\n"
    
    system = """你是专业的网络小说章节分析专家。对每章输出六维度蒸馏分析。

格式（严格遵循）：
---
## 第X章 标题

- **本章核心推进**：一句话
- **主角状态变化**：从A到B
- **新增信息**：角色/设定/世界观
- **关系/局势变化**：变化描述
- **章末钩子**：悬念
- **阶段判断**：阶段名
---

每章200-400字，引用具体角色名和事件。直接输出，不加前言。"""
    
    prompt = f"分析以下{BATCH_SIZE}章：\n{src}"
    
    for attempt in range(3):
        try:
            resp = requests.post(
                'https://api.deepseek.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                json={'model': 'deepseek-chat', 'messages': [
                    {'role': 'system', 'content': system},
                    {'role': 'user', 'content': prompt}
                ], 'max_tokens': 3500, 'temperature': 0.5},
                timeout=300
            )
            if resp.status_code == 200:
                result = resp.json()['choices'][0]['message']['content'].strip()
                if result.startswith('```'):
                    result = re.sub(r'^```\w*\n?', '', result)
                    result = re.sub(r'\n?```$', '', result)
                return result
            time.sleep(5 * (attempt + 1))
        except Exception as e:
            time.sleep(10 * (attempt + 1))
    return None

def main():
    load_env()
    
    print("=" * 60)
    print(f"巫师世界 全书章节蒸馏")
    print(f"策略: {BATCH_SIZE}章/批 | DeepSeek API")
    print("=" * 60)
    
    chapters = read_chapters()
    total = len(chapters)
    print(f"📖 共 {total} 章（UTF-8）")
    
    # 备份
    if os.path.exists(SKELETON):
        shutil.copy(SKELETON, SKELETON + '.bak')
        print("📋 已备份骨架文件")
    else:
        # 创建初始文件
        with open(SKELETON, 'w') as f:
            f.write(f'# 《{NOVEL}》章节蒸馏骨架\n\n> 自动蒸馏，3章/批，DeepSeek API\n\n')
    
    # 续跑
    start_seq = 1
    if os.path.exists(PROGRESS):
        with open(PROGRESS) as f:
            for line in f:
                if line.startswith('next_seq='):
                    start_seq = int(line.split('=')[1])
        print(f"📌 续跑: 从第 {start_seq} 章开始")
    
    pending = [(s, t, b) for s, t, b in chapters if s >= start_seq]
    total_batches = (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE
    
    print(f"📊 待蒸馏: {len(pending)}章 → {total_batches}批")
    print(f"💰 预估: ~${total_batches * 0.005:.2f}")
    print(f"⏱️  预估: ~{total_batches * 25 // 60}分钟")
    print()
    
    success = 0
    for i in range(0, len(pending), BATCH_SIZE):
        batch = pending[i:i+BATCH_SIZE]
        batch_no = i // BATCH_SIZE + 1
        first, last = batch[0][0], batch[-1][0]
        
        print(f"[{batch_no}/{total_batches}] 第{first}-{last}章 ", end='', flush=True)
        
        result = call_api(batch)
        
        if result:
            header = f"\n> **蒸馏批次 {batch_no}**（第{first}-{last}章）\n\n"
            with open(SKELETON, 'a') as f:
                f.write(header + result + '\n')
            
            success += 1
            with open(PROGRESS, 'w') as f:
                f.write(f"next_seq={last+1}\ntotal={total}\nbatch={batch_no}\ntime={time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            preview = result[:60].replace('\n',' ').replace('---','').strip()
            print(f"✅ {preview}...")
        else:
            print(f"❌ 失败! 进度已保存(第{first}章)")
            break
        
        time.sleep(2)
    
    print(f"\n{'='*60}")
    print(f"🏁 {success}/{total_batches} 批成功")
    print(f"   文件: {SKELETON}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
