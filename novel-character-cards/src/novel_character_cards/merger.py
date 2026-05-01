from __future__ import annotations

from pathlib import Path
import json

from .io_utils import ensure_dir


FORBIDDEN_SUBSTRINGS = {
    "这个",
    "那个",
    "这是",
    "似乎",
    "请问",
    "什么",
    "如何",
    "要是",
    "在那",
    "身上",
    "一会",
    "点头",
    "男孩",
    "小女孩",
    "白色",
    "羽毛",
    "视",
    "一种",
    "时候",
    "世界",
    "能力",
    "地方",
    "东西",
    "下来",
    "起来",
    "过来",
    "过去",
    "出来",
    "进去",
    "请问",
    "什么",
    "是的",
    "好的",
    "更多",
    "下载",
    "小说",
    "作者",
    "分析",
    "普通",
    "家族",
    "生物",
    "记忆",
    "马车",
    "羽毛",
    "衣服",
    "下载",
    "精校",
    "尽在",
    "瘦一些",
    "站起",
    "和奥",
    "素质",
    "我们",
    "两人",
    "三人",
    "一边",
    "一条",
    "上面",
    "看上",
    "连忙",
    "身材",
    "安静",
    "就算",
    "虽然",
    "再加",
    "卧室",
    "敏捷",
    "城堡",
    "瘦一",
}

FORBIDDEN_SUFFIXES = {
    "的",
    "了",
    "着",
    "地",
    "得",
    "点",
    "看",
    "说",
    "笑",
    "走",
    "站",
    "坐",
    "扫",
    "伸",
    "皱",
    "回",
    "拿",
    "放",
    "冲",
    "跳",
    "望",
    "微",
    "轻",
    "直",
    "缓",
    "淡",
    "忽",
    "将",
    "只",
    "脸",
    "眼",
    "心",
    "身",
    "手",
    "二",
    "少",
    "起",
    "这",
    "奥",
    "质",
}

ALLOWED_TITLES = ("少爷", "小姐", "大人", "男爵", "侍女", "骑士", "学徒", "王子", "公主")
GENERIC_ROLE_NAMES = {
    "少爷",
    "小姐",
    "大人",
    "男爵",
    "骑士",
    "学徒",
    "王子",
    "公主",
    "夫人",
    "老师",
    "男孩",
    "女孩",
    "小女孩",
    "男子",
    "女人",
    "少女",
}
PERSON_CONTEXT_TOKENS = (
    "少爷",
    "小姐",
    "大人",
    "男爵",
    "侍女",
    "骑士",
    "学徒",
    "王子",
    "公主",
    "男子",
    "女人",
    "少女",
    "女孩",
    "男孩",
    "父亲",
    "母亲",
    "儿子",
    "女儿",
    "夫人",
    "老师",
)


def is_person_like(name: str, mention_count: int, evidence: list[str]) -> bool:
    if len(name) < 2 or len(name) > 6:
        return False

    if name in GENERIC_ROLE_NAMES:
        return False

    if any(part in name for part in FORBIDDEN_SUBSTRINGS):
        return False

    if "和" in name and not name.endswith(ALLOWED_TITLES):
        return False

    if name.endswith(("家族", "世界", "能力", "衣服", "记忆", "马车", "羽")):
        return False

    if name.startswith(("这", "那", "请", "什", "要", "在", "似", "他", "她", "们")):
        return False

    if name.endswith(tuple(FORBIDDEN_SUFFIXES)) and not name.endswith(ALLOWED_TITLES):
        return False

    evidence_text = "".join(evidence)
    has_person_context = any(token in name for token in ALLOWED_TITLES) or any(token in evidence_text for token in PERSON_CONTEXT_TOKENS)
    if "·" not in name and mention_count < 3 and not has_person_context:
        return False

    if "·" not in name and mention_count < 2:
        return False

    if any(token in evidence_text for token in ("下载", "小说", "作者", "http://", "https://")):
        return False

    return True


def _pick_canonical_name(name: str, characters: dict[str, dict]) -> str:
    candidates: list[tuple[int, int, str]] = []
    current = characters[name]
    current_evidence = "".join(current.get("evidence", []))

    for other_name, other in characters.items():
        if other_name == name:
            continue
        if not other_name.startswith(name):
            continue
        if len(other_name) - len(name) > 2:
            continue
        if other.get("mention_count", 0) < current.get("mention_count", 0):
            continue

        other_evidence = "".join(other.get("evidence", []))
        if other_name not in current_evidence and other_name not in other_evidence:
            continue

        candidates.append((other.get("mention_count", 0), len(other_name), other_name))

    if not candidates:
        return name

    return max(candidates)[2]


def merge_extractions(workdir: str | Path) -> Path:
    extraction_dir = Path(workdir) / "extractions"
    merged_dir = ensure_dir(Path(workdir) / "merged")
    characters: dict[str, dict] = {}

    for path in sorted(extraction_dir.glob("chunk-*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        chunk_id = payload["chunk_id"]
        chunk_title = payload.get("title", "")
        for character in payload.get("characters", []):
            raw_name = character["name"]
            name = raw_name
            existing = characters.setdefault(
                name,
                {
                    "name": name,
                    "aliases": set(),
                    "identities": [],
                    "faction": "",
                    "status": "",
                    "first_appearance_text": "",
                    "summaries": [],
                    "appearance": set(),
                    "personality": set(),
                    "abilities": set(),
                    "equipment": set(),
                    "relationships": [],
                    "timeline": [],
                    "evidence": [],
                    "chunks": [],
                    "mention_count": 0,
                    "first_seen_chunk": chunk_id,
                    "first_seen_title": chunk_title,
                },
            )
            existing["aliases"].update(character.get("aliases", []))
            if character.get("identity"):
                existing["identities"].append(character["identity"])
            if character.get("faction") and not existing["faction"]:
                existing["faction"] = character["faction"]
            if character.get("status") and not existing["status"]:
                existing["status"] = character["status"]
            if character.get("first_appearance") and not existing["first_appearance_text"]:
                existing["first_appearance_text"] = character["first_appearance"]
            if character.get("summary"):
                existing["summaries"].append(character["summary"])
            existing["appearance"].update(character.get("appearance", []))
            existing["personality"].update(character.get("personality", []))
            existing["abilities"].update(character.get("abilities", []))
            existing["equipment"].update(character.get("equipment", []))
            existing["relationships"].extend(character.get("relationships", []))
            existing["timeline"].extend(character.get("timeline", []))
            existing["evidence"].extend(character.get("evidence", []))
            existing["chunks"].append(chunk_id)
            existing["mention_count"] += character.get("mention_count", 0)

    if characters:
        remapped: dict[str, dict] = {}
        canonical_map = {name: _pick_canonical_name(name, characters) for name in characters}

        for original_name, data in characters.items():
            canonical_name = canonical_map[original_name]
            target = remapped.setdefault(
                canonical_name,
                {
                    "name": canonical_name,
                    "aliases": set(),
                    "identities": [],
                    "faction": "",
                    "status": "",
                    "first_appearance_text": "",
                    "summaries": [],
                    "appearance": set(),
                    "personality": set(),
                    "abilities": set(),
                    "equipment": set(),
                    "relationships": [],
                    "timeline": [],
                    "evidence": [],
                    "chunks": [],
                    "mention_count": 0,
                    "first_seen_chunk": data["first_seen_chunk"],
                    "first_seen_title": data["first_seen_title"],
                },
            )

            if original_name != canonical_name:
                target["aliases"].add(original_name)

            target["aliases"].update(data["aliases"])
            target["identities"].extend(data["identities"])
            if data["faction"] and not target["faction"]:
                target["faction"] = data["faction"]
            if data["status"] and not target["status"]:
                target["status"] = data["status"]
            if data["first_appearance_text"] and not target["first_appearance_text"]:
                target["first_appearance_text"] = data["first_appearance_text"]
            target["summaries"].extend(data["summaries"])
            target["appearance"].update(data["appearance"])
            target["personality"].update(data["personality"])
            target["abilities"].update(data["abilities"])
            target["equipment"].update(data["equipment"])
            target["relationships"].extend(data["relationships"])
            target["timeline"].extend(data["timeline"])
            target["evidence"].extend(data["evidence"])
            target["chunks"].extend(data["chunks"])
            target["mention_count"] += data["mention_count"]

            if data["first_seen_chunk"] < target["first_seen_chunk"]:
                target["first_seen_chunk"] = data["first_seen_chunk"]
                target["first_seen_title"] = data["first_seen_title"]

        characters = remapped

    sorted_items = sorted(characters.items(), key=lambda item: item[1]["mention_count"], reverse=True)
    merged = []
    kept_names: list[tuple[str, int]] = []
    for name, data in sorted_items:
        evidence = list(dict.fromkeys(data["evidence"]))[:10]
        if not is_person_like(name, data["mention_count"], evidence):
            continue
        if any(
            longer_name.startswith(name) and len(longer_name) - len(name) <= 2 and longer_count >= data["mention_count"] * 2
            for longer_name, longer_count in kept_names
        ):
            continue
        merged.append(
            {
                "name": name,
                "aliases": sorted(data["aliases"]),
                "identity": data["identities"][0] if data["identities"] else "",
                "faction": data["faction"],
                "status": data["status"] or "登场",
                "first_appearance": data["first_appearance_text"] or data["first_seen_title"],
                "summary": data["summaries"][0] if data["summaries"] else "",
                "appearance": sorted(data["appearance"]),
                "personality": sorted(data["personality"]),
                "abilities": sorted(data["abilities"]),
                "equipment": sorted(data["equipment"]),
                "relationships": data["relationships"][:20],
                "timeline": data["timeline"][:20],
                "evidence": evidence,
                "chunks": list(dict.fromkeys(data["chunks"])),
                "mention_count": data["mention_count"],
                "first_seen_chunk": data["first_seen_chunk"],
                "first_seen_title": data["first_seen_title"],
            }
        )
        kept_names.append((name, data["mention_count"]))

    path = merged_dir / "characters.json"
    path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
