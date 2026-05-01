from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


COMMON_ENCODINGS = (
    "utf-8",
    "utf-8-sig",
    "gb18030",
    "gbk",
    "big5",
    "utf-16",
    "latin-1",
)

CHAPTER_RE = re.compile(r"^第[0-9０-９零一二三四五六七八九十百千万两]+[章节回卷部集篇幕].*$")
SEPARATOR_RE = re.compile(r"^[=\-_*~]{6,}$")


@dataclass
class DecodedText:
    text: str
    encoding: str


def decode_text_file(path: str | Path, preferred_encoding: str | None = None) -> DecodedText:
    data = Path(path).read_bytes()
    encodings = [preferred_encoding] if preferred_encoding else []
    encodings.extend(enc for enc in COMMON_ENCODINGS if enc != preferred_encoding)

    for encoding in encodings:
        if not encoding:
            continue
        try:
            return DecodedText(data.decode(encoding), encoding)
        except UnicodeDecodeError:
            continue

    return DecodedText(data.decode("utf-8", errors="replace"), "utf-8-replace")


def build_frontmatter(title: str) -> str:
    return "\n".join(
        [
            "---",
            f"title: {title}",
            "---",
            "",
        ]
    )


def infer_title(lines: list[str], fallback: str) -> str:
    for line in lines:
        cleaned = line.strip().strip("\u3000")
        if not cleaned:
            continue
        if SEPARATOR_RE.fullmatch(cleaned):
            continue
        if "http://" in cleaned or "https://" in cleaned:
            continue
        if len(cleaned) > 40:
            continue
        return cleaned
    return fallback


def normalize_lines(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return [line.rstrip() for line in text.split("\n")]


def convert_text(text: str, *, title: str, frontmatter: bool = False) -> str:
    raw_lines = normalize_lines(text)
    output_lines: list[str] = []
    pending_blank = False

    for index, raw_line in enumerate(raw_lines):
        line = raw_line.strip().strip("\u3000")
        if not line:
            pending_blank = bool(output_lines)
            continue

        if SEPARATOR_RE.fullmatch(line):
            pending_blank = bool(output_lines)
            continue

        if pending_blank and output_lines and output_lines[-1] != "":
            output_lines.append("")
        pending_blank = False

        if index == 0 and line == title:
            continue

        if CHAPTER_RE.match(line):
            if output_lines and output_lines[-1] != "":
                output_lines.append("")
            output_lines.append(f"## {line}")
            output_lines.append("")
            continue

        output_lines.append(line)

    while output_lines and output_lines[-1] == "":
        output_lines.pop()

    parts = []
    if frontmatter:
        parts.append(build_frontmatter(title))
    parts.append(f"# {title}\n")
    if output_lines:
        parts.append("\n".join(output_lines).strip() + "\n")
    return "\n".join(parts).rstrip() + "\n"
