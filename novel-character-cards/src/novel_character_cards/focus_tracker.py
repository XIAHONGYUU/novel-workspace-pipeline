from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections import Counter
import json
import re

from .chunker import Chunk
from .io_utils import ensure_dir


SENTENCE_RE = re.compile(r"[^。！？!?]*[。！？!?]?")
NAME_RE = re.compile(r"[\u4e00-\u9fff]{2,6}")
FULL_NAME_RE = re.compile(r"安格列·[\u4e00-\u9fff]{1,4}")
TITLE_NAME_RE = re.compile(r"([\u4e00-\u9fff]{2,4})(男爵|骑士|小姐|夫人|老师|学徒)")
PLACE_RE = re.compile(r"([\u4e00-\u9fff]{2,4})(家族|学院|城堡|小镇|村庄|王国|公国|帝国|船队|商队)")
ITEM_KEYWORDS = (
    "芯片",
    "马鞍",
    "长剑",
    "弓",
    "骑士教程",
    "战斗训练",
    "巫师之书",
    "死魂草",
    "龙鳞花",
    "药剂",
    "冥想",
)
EVENT_KEYWORDS = (
    "穿越",
    "学习",
    "训练",
    "比赛",
    "战斗",
    "激战",
    "猎杀",
    "拍卖",
    "审问",
    "前往",
    "离开",
    "上船",
    "晋级",
    "定居",
    "邀请",
)
NOISE_TERMS = {
    "父亲",
    "但是",
    "学徒",
    "您醒了",
    "战斗力",
    "包括五个",
    "确认了这",
    "方法不论",
    "以及远房",
    "来投奔里",
    "道父亲里",
    "土包括三",
    "男爵拍拍",
    "我在倾听",
}
NOISE_FRAGMENTS = {
    "安格列在",
    "安格列和",
    "包括",
    "了这",
    "愿的",
    "是以前",
    "这些",
    "看着",
    "父亲里",
    "安格列·里奥收",
    "安格列·里奥大人",
    "安格列·里奥的乡",
}
NAME_NOISE_CHARS = set("的是了着往在和与及并把被向从对给跟让将里上下来去前后左右上下大小男女老新黑白红蓝黄灰金银一二三四五六七八九十个名位只种次么拿还虽回到格列所以独自速朝快步我们没有穿能抵达还能遇到")
PLACE_PREFIX_NOISE = ("凝重", "顺着", "前的", "继续", "处的", "正是", "通往", "速地", "慢慢", "都是", "次问", "就是", "直接", "走向", "投奔", "赶出", "才投奔", "回到", "独自", "快步", "虽然", "就能", "还能", "也没有", "拿起", "不怕", "不比", "理会", "控制", "进入")
RELATION_NOISE_WORDS = ("学徒", "骑士人物", "父辈人物")


@dataclass
class FocusCheckpoint:
    checkpoint_id: str
    chunk_end: int
    mention_count_total: int
    mention_count_interval: int
    chapter_titles: list[str]
    snippets: list[str]
    context_entries: dict[str, list[str]]


def _keyword_set(focus_name: str, aliases: list[str] | None = None) -> list[str]:
    keywords = [focus_name]
    for alias in aliases or []:
        if alias and alias not in keywords:
            keywords.append(alias)
    return keywords


def _sentences_with_keywords(text: str, keywords: list[str]) -> list[str]:
    snippets: list[str] = []
    for raw_sentence in SENTENCE_RE.findall(text.replace("\n", "")):
        sentence = raw_sentence.strip()
        if not sentence:
            continue
        if any(keyword in sentence for keyword in keywords):
            snippets.append(sentence[:160])
    return snippets


def _chunk_mentions(chunk: Chunk, keywords: list[str]) -> tuple[int, list[str]]:
    pattern = re.compile("|".join(re.escape(keyword) for keyword in sorted(keywords, key=len, reverse=True)))
    mention_count = len(pattern.findall(chunk.text))
    snippets = _sentences_with_keywords(chunk.text, keywords)
    return mention_count, snippets


def _empty_context_counters() -> dict[str, Counter]:
    return {
        "identity_titles": Counter(),
        "relationships": Counter(),
        "places_factions": Counter(),
        "items_abilities": Counter(),
        "events": Counter(),
    }


def _update_counter(counter: Counter, value: str) -> None:
    cleaned = value.strip("，。！？!?：:；;、“”\"'()（）[]【】 ")
    if len(cleaned) < 2:
        return
    if cleaned in NOISE_TERMS:
        return
    if any(fragment in cleaned for fragment in NOISE_FRAGMENTS):
        return
    if cleaned.endswith(("家", "里", "这", "愿", "乡", "收")):
        return
    counter[cleaned] += 1


def _is_stable_identity(value: str) -> bool:
    if value in {"少爷", "哥哥", "次子", "二少爷", "男爵次子", "里奥家族次子"}:
        return True
    if value.startswith("安格列·") and 4 <= len(value) <= 6:
        return True
    return False


def _is_stable_relationship(value: str) -> bool:
    if value in {
        "凯尔男爵:父亲",
        "奥迪斯:骑士导师",
        "西莉儿:妹妹",
        "玛姬:亲近的家族女孩",
        "凯萨琳:贵族女孩",
        "里奥男爵:父辈人物",
    }:
        return True
    if ":" not in value:
        return False
    left, right = value.split(":", 1)
    if not (2 <= len(left) <= 5):
        return False
    if any(ch in NAME_NOISE_CHARS for ch in left):
        return False
    if right in RELATION_NOISE_WORDS:
        return False
    return False


def _is_stable_place(value: str) -> bool:
    if any(value.startswith(prefix) for prefix in PLACE_PREFIX_NOISE):
        return False
    if any(fragment in value for fragment in ("赶出", "进入", "离开", "回到")):
        return False
    if not value.endswith(("家族", "学院", "城堡", "小镇", "王国", "公国", "帝国", "船队", "商队")):
        return False
    suffix_len = 2
    prefix = value[:-suffix_len]
    if len(prefix) < 2 or len(prefix) > 4:
        return False
    if any(ch in NAME_NOISE_CHARS for ch in prefix):
        return False
    return True


def _is_stable_item(value: str) -> bool:
    return value in {
        "芯片",
        "生物芯片",
        "安格列的记忆",
        "长剑",
        "冥想",
        "药剂",
        "死魂草",
        "龙鳞花",
        "拍卖",
        "巫师之书",
        "骑士教程",
        "马鞍",
        "战斗训练",
    }


def _is_stable_event(value: str) -> bool:
    return value in {
        "穿越",
        "学习",
        "训练",
        "比赛",
        "战斗",
        "激战",
        "猎杀",
        "拍卖",
        "审问",
        "前往",
        "离开",
        "上船",
        "晋级",
        "定居",
        "邀请",
    }


def _extract_context_entries(sentences: list[str], focus_name: str, keywords: list[str]) -> dict[str, Counter]:
    context = _empty_context_counters()
    focus_pattern = re.compile("|".join(re.escape(keyword) for keyword in sorted(keywords, key=len, reverse=True)))

    for sentence in sentences:
        if not focus_pattern.search(sentence):
            continue

        for title in ("二少爷", "少爷", "哥哥", "次子", "男爵次子", "里奥家族次子"):
            if title in sentence:
                _update_counter(context["identity_titles"], title)

        for match in FULL_NAME_RE.findall(sentence):
            _update_counter(context["identity_titles"], match)

        for name, title in TITLE_NAME_RE.findall(sentence):
            if name == focus_name or name in keywords:
                continue
            if title == "男爵":
                _update_counter(context["relationships"], f"{name}{title}:父辈人物")
            elif title == "骑士":
                _update_counter(context["relationships"], f"{name}{title}:骑士人物")
            else:
                _update_counter(context["relationships"], f"{name}{title}")

        for prefix, suffix in PLACE_RE.findall(sentence):
            if prefix in {"五个", "三个", "这个", "那个", "其中"}:
                continue
            _update_counter(context["places_factions"], f"{prefix}{suffix}")

        for keyword in ITEM_KEYWORDS:
            if keyword in sentence:
                _update_counter(context["items_abilities"], keyword)

        for keyword in EVENT_KEYWORDS:
            if keyword in sentence:
                _update_counter(context["events"], keyword)

        if "记忆" in sentence:
            _update_counter(context["items_abilities"], "安格列的记忆")
        if "芯片" in sentence and "生物" in sentence:
            _update_counter(context["items_abilities"], "生物芯片")
        if "凯尔男爵" in sentence or ("父亲" in sentence and "男爵" in sentence):
            _update_counter(context["relationships"], "凯尔男爵:父亲")
        if "奥迪斯" in sentence and ("训练" in sentence or "学习" in sentence or "骑士" in sentence):
            _update_counter(context["relationships"], "奥迪斯:骑士导师")
        if "西莉儿" in sentence and "妹妹" in sentence:
            _update_counter(context["relationships"], "西莉儿:妹妹")
        if "玛姬" in sentence:
            _update_counter(context["relationships"], "玛姬:亲近的家族女孩")
        if "凯萨琳" in sentence:
            _update_counter(context["relationships"], "凯萨琳:贵族女孩")

    return context


def _merge_context(target: dict[str, Counter], source: dict[str, Counter]) -> None:
    for key, counter in source.items():
        target[key].update(counter)


def _format_context_entries(context: dict[str, Counter], limit: int = 12) -> dict[str, list[str]]:
    filters = {
        "identity_titles": _is_stable_identity,
        "relationships": _is_stable_relationship,
        "places_factions": _is_stable_place,
        "items_abilities": _is_stable_item,
        "events": _is_stable_event,
    }
    formatted: dict[str, list[str]] = {}
    for key, counter in context.items():
        allowed = [value for value, _count in counter.most_common(limit * 3) if filters[key](value)]
        if allowed:
            formatted[key] = allowed[:limit]
    return formatted


def _changed_context_entries(
    current: dict[str, list[str]],
    previous: dict[str, list[str]] | None,
) -> dict[str, list[str]]:
    if not previous:
        return current

    changed: dict[str, list[str]] = {}
    for key, values in current.items():
        previous_values = set(previous.get(key, []))
        new_values = [value for value in values if value not in previous_values]
        if new_values:
            changed[key] = new_values
    return changed


def build_focus_reports(
    chunks: list[Chunk],
    workdir: str | Path,
    *,
    focus_name: str,
    aliases: list[str] | None = None,
    summary_interval: int = 100,
) -> Path:
    focus_dir = ensure_dir(Path(workdir) / "focus")
    checkpoints_dir = ensure_dir(focus_dir / "checkpoints")
    keywords = _keyword_set(focus_name, aliases)

    checkpoint_payloads: list[dict] = []
    total_mentions = 0
    interval_mentions = 0
    seen_titles: list[str] = []
    interval_titles: list[str] = []
    total_snippets: list[str] = []
    interval_snippets: list[str] = []
    total_context = _empty_context_counters()
    interval_context = _empty_context_counters()
    processed_chunks = 0
    seen_checkpoint_entries: dict[str, set[str]] = {}

    for index, chunk in enumerate(chunks, start=1):
        mentions, snippets = _chunk_mentions(chunk, keywords)
        if mentions > 0:
            total_mentions += mentions
            interval_mentions += mentions
            if chunk.title not in seen_titles:
                seen_titles.append(chunk.title)
            if chunk.title not in interval_titles:
                interval_titles.append(chunk.title)
            total_snippets.extend(snippets)
            interval_snippets.extend(snippets)
            context_entries = _extract_context_entries(snippets, focus_name, keywords)
            _merge_context(total_context, context_entries)
            _merge_context(interval_context, context_entries)

        processed_chunks = index
        should_flush = index % summary_interval == 0 or index == len(chunks)
        if not should_flush:
            continue

        interval_entries = _format_context_entries(interval_context)
        changed_entries = {
            key: [value for value in values if value not in seen_checkpoint_entries.get(key, set())]
            for key, values in interval_entries.items()
        }
        changed_entries = {key: values for key, values in changed_entries.items() if values}

        checkpoint = FocusCheckpoint(
            checkpoint_id=f"checkpoint-{index:04d}",
            chunk_end=index,
            mention_count_total=total_mentions,
            mention_count_interval=interval_mentions,
            chapter_titles=interval_titles[:],
            snippets=list(dict.fromkeys(interval_snippets))[:15],
            context_entries=changed_entries,
        )
        payload = {
            "checkpoint_id": checkpoint.checkpoint_id,
            "focus_name": focus_name,
            "keywords": keywords,
            "chunk_end": checkpoint.chunk_end,
            "mention_count_total": checkpoint.mention_count_total,
            "mention_count_interval": checkpoint.mention_count_interval,
            "chapter_titles": checkpoint.chapter_titles,
            "snippets": checkpoint.snippets,
            "context_entries": checkpoint.context_entries,
        }
        checkpoint_payloads.append(payload)

        checkpoint_path = checkpoints_dir / f"{checkpoint.checkpoint_id}.md"
        lines = [
            f"# {focus_name} 追踪总结 {index}",
            "",
            f"- 统计范围：前 {index} 个 chunk",
            f"- 本阶段提及次数：{checkpoint.mention_count_interval}",
            f"- 累计提及次数：{checkpoint.mention_count_total}",
            f"- 涉及章节数：{len(checkpoint.chapter_titles)}",
        ]
        if checkpoint.chapter_titles:
            lines.extend(["", "## 本阶段涉及章节", ""])
            lines.extend([f"- {title}" for title in checkpoint.chapter_titles[:20]])
        if checkpoint.snippets:
            lines.extend(["", "## 关键片段", ""])
            lines.extend([f"- {snippet}" for snippet in checkpoint.snippets])
        if checkpoint.context_entries:
            lines.extend(["", "## 相关词条", ""])
            if checkpoint.context_entries.get("identity_titles"):
                lines.append(f"- 身份称谓：{'、'.join(checkpoint.context_entries['identity_titles'])}")
            if checkpoint.context_entries.get("relationships"):
                lines.append(f"- 关系人物：{'、'.join(checkpoint.context_entries['relationships'])}")
            if checkpoint.context_entries.get("places_factions"):
                lines.append(f"- 地点势力：{'、'.join(checkpoint.context_entries['places_factions'])}")
            if checkpoint.context_entries.get("items_abilities"):
                lines.append(f"- 物品能力：{'、'.join(checkpoint.context_entries['items_abilities'])}")
            if checkpoint.context_entries.get("events"):
                lines.append(f"- 关键事件：{'、'.join(checkpoint.context_entries['events'])}")
        checkpoint_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        for key, values in interval_entries.items():
            seen_checkpoint_entries.setdefault(key, set()).update(values)

        interval_mentions = 0
        interval_titles = []
        interval_snippets = []
        interval_context = _empty_context_counters()

    manifest_path = focus_dir / "checkpoints.json"
    manifest_path.write_text(json.dumps(checkpoint_payloads, ensure_ascii=False, indent=2), encoding="utf-8")

    report_lines = [
        f"# {focus_name} 人物卡",
        "",
        f"- 统计 chunk 数：{processed_chunks}",
        f"- 累计提及次数：{total_mentions}",
        f"- 涉及章节数：{len(seen_titles)}",
        f"- 检查点数量：{len(checkpoint_payloads)}",
        f"- 关键词：{'、'.join(keywords)}",
    ]
    total_context_entries = _format_context_entries(total_context)
    latest_context_entries = checkpoint_payloads[-1]["context_entries"] if checkpoint_payloads else {}
    if total_context_entries:
        report_lines.extend(["", "## 累计词条", ""])
        if total_context_entries.get("identity_titles"):
            report_lines.append(f"- 身份称谓：{'、'.join(total_context_entries['identity_titles'])}")
        if total_context_entries.get("relationships"):
            report_lines.append(f"- 关系人物：{'、'.join(total_context_entries['relationships'])}")
        if total_context_entries.get("places_factions"):
            report_lines.append(f"- 地点势力：{'、'.join(total_context_entries['places_factions'])}")
        if total_context_entries.get("items_abilities"):
            report_lines.append(f"- 物品能力：{'、'.join(total_context_entries['items_abilities'])}")
        if total_context_entries.get("events"):
            report_lines.append(f"- 关键事件：{'、'.join(total_context_entries['events'])}")
    if latest_context_entries:
        report_lines.extend(["", "## 最近一次更新词条", ""])
        if latest_context_entries.get("identity_titles"):
            report_lines.append(f"- 身份称谓：{'、'.join(latest_context_entries['identity_titles'])}")
        if latest_context_entries.get("relationships"):
            report_lines.append(f"- 关系人物：{'、'.join(latest_context_entries['relationships'])}")
        if latest_context_entries.get("places_factions"):
            report_lines.append(f"- 地点势力：{'、'.join(latest_context_entries['places_factions'])}")
        if latest_context_entries.get("items_abilities"):
            report_lines.append(f"- 物品能力：{'、'.join(latest_context_entries['items_abilities'])}")
        if latest_context_entries.get("events"):
            report_lines.append(f"- 关键事件：{'、'.join(latest_context_entries['events'])}")
    if seen_titles:
        report_lines.extend(["", "## 涉及章节", ""])
        report_lines.extend([f"- {title}" for title in seen_titles[:100]])
    deduped_total_snippets = list(dict.fromkeys(total_snippets))[:40]
    if deduped_total_snippets:
        report_lines.extend(["", "## 累计关键片段", ""])
        report_lines.extend([f"- {snippet}" for snippet in deduped_total_snippets])
    if checkpoint_payloads:
        report_lines.extend(["", "## 检查点", ""])
        for item in checkpoint_payloads:
            report_lines.append(f"- [前 {item['chunk_end']} 个 chunk](checkpoints/{item['checkpoint_id']}.md)")

    report_path = focus_dir / f"{focus_name}.md"
    report_path.write_text("\n".join(report_lines).rstrip() + "\n", encoding="utf-8")
    return report_path
