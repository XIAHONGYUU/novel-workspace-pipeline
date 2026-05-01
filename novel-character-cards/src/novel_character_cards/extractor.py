from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import re

from .chunker import Chunk
from .ai_extractor import extract_with_openai
from .io_utils import ensure_dir


CHINESE_RUN_RE = re.compile(r"[\u4e00-\u9fff·]+")
SENTENCE_RE = re.compile(r"[。！？!?]")
STOP_NAMES = {
    "作者",
    "小说",
    "世界",
    "这个世界",
    "时候",
    "时间",
    "一个",
    "两个",
    "没有",
    "没有任何",
    "自己",
    "这里",
    "那里",
    "什么",
    "怎么",
    "不是",
    "如果",
    "因为",
    "所以",
    "不过",
    "然后",
    "但是",
    "现在",
    "今天",
    "终于",
    "看到",
    "东西",
    "地方",
    "地面",
    "天空",
    "前边",
    "后面",
    "周围",
    "马车",
    "点头",
    "点点头",
    "起来",
    "下来",
    "出来",
    "过去",
    "过来",
    "很快",
    "好了",
    "当然",
    "回答",
    "消失",
    "走吧",
    "该死",
    "一下",
    "知道",
    "那么",
    "对了",
    "所有人",
    "力量",
    "精神力",
    "生物",
}
TRAILING_NOISE_CHARS = set("的了着地得也很将只便就又还都才把向往中上下来去啦啊吗呢呀哦呐")
TRAILING_ACTION_CHARS = set("点看说笑走站坐扫伸皱回拿放冲跳望微轻直缓淡抓摸推拉转停")
TRAILING_VARIANT_CHARS = TRAILING_NOISE_CHARS.union(TRAILING_ACTION_CHARS).union(
    set("脸眼心身手头脚面眉胸背肩发额口鼻耳目双和与在从向将把给对于里外前后一大小高低远近强弱新老黑白红青无不一")
)
TITLE_TOKENS = ("少爷", "小姐", "大人", "男爵", "侍女", "骑士", "学徒", "王子", "公主", "夫人", "老师")


@dataclass
class CharacterObservation:
    name: str
    aliases: list[str]
    identity: str
    faction: str
    status: str
    first_appearance: str
    summary: str
    appearance: list[str]
    personality: list[str]
    abilities: list[str]
    equipment: list[str]
    relationships: list[dict[str, str]]
    timeline: list[dict[str, str]]
    evidence: list[str]
    mention_count: int


def _sentences(text: str) -> list[str]:
    normalized = text.replace("\n", "")
    raw_parts = SENTENCE_RE.split(normalized)
    return [part.strip() for part in raw_parts if part.strip()]


def _candidate_names(text: str) -> Counter:
    raw_counts = Counter()
    for sentence in _sentences(text):
        for run in CHINESE_RUN_RE.findall(sentence):
            token = run.strip("·")
            if not token:
                continue
            if "·" in run:
                raw_counts[run.strip()] += 1
                continue
            if len(token) < 2:
                continue

            max_len = min(4, len(token))
            for size in range(2, max_len + 1):
                raw_counts[token[:size]] += 1

            for title in TITLE_TOKENS:
                search_from = 0
                while True:
                    index = token.find(title, search_from)
                    if index == -1:
                        break
                    candidate = token[max(0, index - 4) : index]
                    if 2 <= len(candidate) <= 4:
                        raw_counts[candidate] += 1
                    search_from = index + len(title)

    counts = Counter()
    for token, count in raw_counts.items():
        token = _normalize_candidate(token, raw_counts)
        if not token or token in STOP_NAMES:
            continue
        if token.startswith("第") and any(ch in token for ch in "章节回卷部集篇幕"):
            continue
        counts[token] += count
    return counts


def _normalize_candidate(token: str, raw_counts: Counter | None = None) -> str:
    cleaned = token.strip()
    if len(cleaned) < 2:
        return ""

    while len(cleaned) >= 3 and cleaned[-1] in TRAILING_VARIANT_CHARS:
        shorter = cleaned[:-1]
        if raw_counts is not None and raw_counts.get(shorter, 0) == 0:
            break
        cleaned = shorter

    if len(cleaned) >= 3 and cleaned[-1] in TRAILING_NOISE_CHARS:
        cleaned = cleaned[:-1]

    if len(cleaned) < 2:
        return ""

    if cleaned in STOP_NAMES:
        return ""

    return cleaned


def heuristic_extract(chunk: Chunk, top_n: int = 12) -> dict:
    counts = _candidate_names(chunk.text)
    sentences = _sentences(chunk.text)
    characters: list[CharacterObservation] = []

    for name, count in counts.most_common(top_n):
        if count < 2:
            continue
        evidence = []
        for sentence in sentences:
            if name in sentence:
                evidence.append(sentence[:120])
            if len(evidence) >= 3:
                break
        summary = evidence[0] if evidence else ""
        characters.append(
            CharacterObservation(
                name=name,
                aliases=[],
                identity="",
                faction="",
                status="登场",
                first_appearance=chunk.title,
                summary=summary,
                appearance=[],
                personality=[],
                abilities=[],
                equipment=[],
                relationships=[],
                timeline=[],
                evidence=evidence,
                mention_count=count,
            )
        )

    return {
        "chunk_id": chunk.chunk_id,
        "title": chunk.title,
        "characters": [asdict(character) for character in characters],
    }


def write_extractions(
    chunks: list[Chunk],
    workdir: str | Path,
    *,
    extractor_mode: str = "heuristic",
    model: str = "gpt-5",
    prompt_path: str | Path | None = None,
) -> Path:
    extraction_dir = ensure_dir(Path(workdir) / "extractions")
    manifest = []

    for chunk in chunks:
        if extractor_mode == "openai":
            payload = extract_with_openai(chunk, model=model, prompt_path=prompt_path)
        else:
            payload = heuristic_extract(chunk)
        path = extraction_dir / f"{chunk.chunk_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest.append({"chunk_id": chunk.chunk_id, "character_count": len(payload["characters"])})

    manifest_path = Path(workdir) / "extractions.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path
