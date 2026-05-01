from __future__ import annotations

from pathlib import Path
import json

from .io_utils import ensure_dir


def slugify(name: str) -> str:
    return name.replace("/", "_")


def render_cards(workdir: str | Path) -> Path:
    merged_path = Path(workdir) / "merged" / "characters.json"
    cards_dir = ensure_dir(Path(workdir) / "cards")
    characters = json.loads(merged_path.read_text(encoding="utf-8"))

    for old_card in cards_dir.glob("*.md"):
        old_card.unlink()

    index_lines = ["# 人物卡索引", ""]
    for character in characters:
        filename = f"{slugify(character['name'])}.md"
        path = cards_dir / filename
        lines = [
            "---",
            f"title: {character['name']}",
            "tags:",
            "  - 人物卡",
            "---",
            "",
            f"# {character['name']}",
            "",
            "## 基本信息",
            "",
            f"- 姓名：{character['name']}",
            f"- 别名：{'、'.join(character['aliases']) if character['aliases'] else ''}",
            f"- 身份：{character['identity']}",
            f"- 阵营：{character['faction']}",
            f"- 初次登场：{character['first_appearance']}",
            f"- 当前状态：{character['status']}",
            f"- 提及次数：{character['mention_count']}",
        ]

        if character["summary"]:
            lines.extend(["", "## 人物概述", "", character["summary"]])

        lines.extend(["", "## 外貌与特征", ""])
        if character["appearance"]:
            lines.extend([f"- {item}" for item in character["appearance"]])
        else:
            lines.append("- ")

        lines.extend(["", "## 性格与行为", ""])
        if character["personality"]:
            lines.extend([f"- {item}" for item in character["personality"]])
        else:
            lines.append("- ")

        lines.extend(["", "## 能力体系", ""])
        if character["abilities"]:
            lines.extend([f"- 能力：{item}" for item in character["abilities"]])
        else:
            lines.append("- 能力：")
        if character["equipment"]:
            lines.extend([f"- 装备：{item}" for item in character["equipment"]])
        else:
            lines.append("- 装备：")

        lines.extend(["", "## 身份与阶段变化", ""])
        if character["timeline"]:
            for item in character["timeline"]:
                stage = item.get("stage", "")
                event = item.get("event", "")
                lines.append(f"### {stage or '阶段'}")
                lines.append("")
                lines.append(f"- {event}")
                lines.append("")
            if lines[-1] == "":
                lines.pop()
        else:
            lines.extend(["### 早期", "", "- "])

        if character["relationships"]:
            lines.extend(["", "## 关键关系", ""])
            for rel in character["relationships"]:
                target = rel.get("target", "")
                rel_type = rel.get("type", "")
                if target or rel_type:
                    lines.append(f"- {target}: {rel_type}".rstrip(": "))
        else:
            lines.extend(["", "## 关键关系", "", "- "])

        lines.extend(["", "## 关键事件", ""])
        if character["timeline"]:
            for item in character["timeline"]:
                stage = item.get("stage", "")
                event = item.get("event", "")
                lines.append(f"- {stage}: {event}".rstrip(": "))
        else:
            lines.append("- ")

        if character["evidence"]:
            lines.extend(["", "## 重要证据", ""])
            lines.extend([f"- {snippet}" for snippet in character["evidence"]])

        lines.extend(["", "## 备注", "", "- "])

        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        index_lines.append(f"- [[{character['name']}]]")

    index_path = cards_dir / "index.md"
    index_path.write_text("\n".join(index_lines).rstrip() + "\n", encoding="utf-8")
    return index_path
