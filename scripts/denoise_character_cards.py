#!/usr/bin/env python3
"""
去噪脚本：删除各工作区中的碎片化人物卡，
并同步更新 work/cards/index.md 和 work/merged/characters.json。
"""

import json
import os
import re
import sys
from pathlib import Path

# ============================================================
# 各工作区的碎片卡片列表（已经过人工确认）
# ============================================================
FRAGMENTS = {
    "我的诡异人生": [
        "一个个", "一个接", "不过我", "也是", "事情", "佛本",
        "你死定", "千万", "卧槽", "只是", "只需", "叮咚",
        "可以", "可明", "哈妩漠", "哒哒", "啪嚓", "嗤啦",
        "嘭嘭", "夏季", "奇耻", "如果他", "如果你", "就是",
        "就等", "已经", "已经过", "我明", "我见谅", "或者",
        "拿出", "没有亲", "没有舌", "滚出", "线与", "解不",
        "诡要", "轰隆隆", "还是", "还是为", "雷劈",
    ],
    "玄浑道章": [
        "一个人", "一个年", "不过为", "不过他", "不过她",
        "不过我", "不过现", "不过那", "也是", "但是他",
        "但是现", "但是随", "只是", "只是他", "只是到",
        "可以", "因为他", "因为元", "如果你", "就是",
        "就是为", "就是他", "已经", "或者", "所以他",
        "所以我", "所以最", "所以有", "所以此", "所以现",
        "所以除", "而且", "自己那位", "还是",
    ],
    "刀笼": [
        "一个个", "一个挂", "一个掌灯", "也是", "只是",
        "可以", "可以说是", "就是", "已经", "或者",
        "所以我", "然后他", "然后如", "然后我", "的一",
        "的一声", "而且", "而且他", "而且是", "还是",
        "还是第", "仙气", "厉害", "哗啦", "唧唧",
        "嘎吱", "轰隆", "雷猴", "首领",
    ],
    "序列大明": [
        "一个为", "一个是", "一个跟", "不过他", "不过我",
        "也是", "但是你", "只是", "只是为", "如果你",
        "就是", "已经", "已经过", "或者", "所以你",
        "所以我", "而且", "还是", "还是你",
    ],
    "巫师世界": [
        "只是", "已经", "而且",
    ],
    "永恒剑主": [
        "也是", "只是",
    ],
    "寇道": [
        "而且",
    ],
}

BASE = Path("/home/zuoky/project")


def delete_card_files(workspace: str, fragments: list[str]) -> tuple[int, list[str]]:
    """删除碎片卡片 .md 文件。返回 (成功删除数, 失败列表)。"""
    cards_dir = BASE / workspace / "work" / "cards"
    deleted = []
    failed = []

    for name in fragments:
        filepath = cards_dir / f"{name}.md"
        if filepath.exists():
            try:
                filepath.unlink()
                deleted.append(name)
            except OSError as e:
                failed.append(f"{name}: {e}")
        else:
            failed.append(f"{name}: 文件不存在")

    return len(deleted), failed


def update_index_md(workspace: str, fragments: list[str]) -> bool:
    """从 index.md 中移除碎片卡片的链接行。"""
    index_path = BASE / workspace / "work" / "cards" / "index.md"
    if not index_path.exists():
        print(f"  ⚠ index.md 不存在，跳过")
        return False

    content = index_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    new_lines = []

    for line in lines:
        # 匹配 [[名称]] 格式
        match = re.match(r'^-\s+\[\[(.+)\]\]\s*$', line.strip())
        if match:
            name = match.group(1)
            if name in fragments:
                continue  # 跳过这行
        new_lines.append(line)

    new_content = "\n".join(new_lines)
    if new_content != content:
        index_path.write_text(new_content, encoding="utf-8")
        # 重新添加末尾换行
        if not new_content.endswith("\n"):
            index_path.write_text(new_content + "\n", encoding="utf-8")
        return True
    return False


def update_characters_json(workspace: str, fragments: list[str]) -> bool:
    """从 merged/characters.json 中移除碎片角色条目。"""
    json_path = BASE / workspace / "work" / "merged" / "characters.json"
    if not json_path.exists():
        print(f"  ⚠ characters.json 不存在，跳过")
        return False

    data = json.loads(json_path.read_text(encoding="utf-8"))
    original_count = len(data)

    # data 是一个 list，每个元素有 "name" 字段
    new_data = [entry for entry in data if entry.get("name") not in fragments]

    if len(new_data) < original_count:
        json_path.write_text(
            json.dumps(new_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    return False


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry-run"

    print("=" * 60)
    print(f"小说工作区人物卡去噪 — {'预览模式 (dry-run)' if mode == 'dry-run' else '执行模式 (execute)'}")
    print("=" * 60)

    total_fragments = 0
    total_deleted = 0
    results = []

    for workspace, fragments in FRAGMENTS.items():
        cards_dir = BASE / workspace / "work" / "cards"
        if not cards_dir.exists():
            print(f"\n⚠ {workspace}: work/cards/ 目录不存在，跳过")
            continue

        # 检查哪些碎片文件实际存在
        existing = [f for f in fragments if (cards_dir / f"{f}.md").exists()]

        print(f"\n{'─' * 50}")
        print(f"📁 {workspace}")
        print(f"   碎片总数: {len(fragments)}, 实际存在: {len(existing)}")

        if not existing:
            print("   ✅ 无需清理")
            results.append((workspace, 0, []))
            continue

        total_fragments += len(existing)

        if mode == "dry-run":
            print("   🔍 将要删除的卡片:")
            for name in existing:
                print(f"      - {name}.md")
            results.append((workspace, len(existing), []))
        else:
            # 执行删除
            print("   🗑 正在删除...")
            deleted, failed = delete_card_files(workspace, existing)
            total_deleted += deleted
            print(f"   ✅ 已删除 {deleted} 个文件")
            if failed:
                print(f"   ⚠ 失败: {failed}")

            # 更新 index.md
            index_updated = update_index_md(workspace, existing)
            print(f"   📋 index.md: {'已更新' if index_updated else '无需更新/未找到' if index_updated is False else '无变化'}")

            # 更新 characters.json
            json_updated = update_characters_json(workspace, existing)
            print(f"   📊 characters.json: {'已更新' if json_updated else '无需更新/未找到' if json_updated is False else '无变化'}")

            results.append((workspace, deleted, failed))

    # 总结
    print(f"\n{'=' * 60}")
    if mode == "dry-run":
        print(f"🔍 预览完成 — 共 {total_fragments} 张碎片卡片待删除")
        print(f"   涉及 {sum(1 for _, n, _ in results if n > 0)} 个工作区")
        print(f"\n   要执行清理，请运行:")
        print(f"   python3 {__file__} execute")
    else:
        print(f"✅ 清理完成 — 共删除 {total_deleted} 张碎片卡片")
        print(f"   失败: {sum(len(f) for _, _, f in results)} 个")

        # 重新统计各工作区
        print(f"\n{'─' * 50}")
        print("📊 清理后各工作区人物卡数量:")
        for workspace, deleted, _ in results:
            cards_dir = BASE / workspace / "work" / "cards"
            if cards_dir.exists():
                count = len([f for f in os.listdir(cards_dir) if f.endswith(".md")])
                print(f"   {workspace}: {count} 张 (删除 {deleted} 张)")

    print("=" * 60)


if __name__ == "__main__":
    main()
