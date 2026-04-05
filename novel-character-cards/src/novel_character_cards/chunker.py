from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import re

from .io_utils import ensure_dir


CHAPTER_RE = re.compile(r"^\s*第[0-9０-９零一二三四五六七八九十百千万两]+[章节回卷部集篇幕].*$")


@dataclass
class Chunk:
    chunk_id: str
    title: str
    start_line: int
    end_line: int
    text: str


def normalize_text(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return [line.rstrip() for line in text.split("\n")]


def chunk_text(text: str, max_chars: int = 12000) -> list[Chunk]:
    lines = normalize_text(text)
    sections: list[tuple[str, list[str], int, int]] = []
    current_title = "前言"
    current_lines: list[str] = []
    section_start = 1

    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if CHAPTER_RE.match(line):
            if current_lines:
                sections.append((current_title, current_lines, section_start, line_no - 1))
            current_title = line
            current_lines = [line]
            section_start = line_no
        else:
            current_lines.append(raw_line)

    if current_lines:
        sections.append((current_title, current_lines, section_start, len(lines)))

    chunks: list[Chunk] = []
    counter = 1
    for title, section_lines, start_line, end_line in sections:
        buffer: list[str] = []
        current_start = start_line
        for offset, line in enumerate(section_lines):
            trial = "\n".join(buffer + [line]).strip()
            if buffer and len(trial) > max_chars:
                chunk_id = f"chunk-{counter:04d}"
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        title=title,
                        start_line=current_start,
                        end_line=start_line + offset - 1,
                        text="\n".join(buffer).strip(),
                    )
                )
                counter += 1
                buffer = [line]
                current_start = start_line + offset
            else:
                buffer.append(line)

        if buffer:
            chunk_id = f"chunk-{counter:04d}"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    title=title,
                    start_line=current_start,
                    end_line=end_line,
                    text="\n".join(buffer).strip(),
                )
            )
            counter += 1

    return chunks


def write_chunks(chunks: list[Chunk], workdir: str | Path) -> Path:
    chunk_dir = ensure_dir(Path(workdir) / "chunks")
    manifest_path = Path(workdir) / "chunks.json"
    manifest = []

    for chunk in chunks:
        path = chunk_dir / f"{chunk.chunk_id}.json"
        payload = asdict(chunk)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest.append({k: payload[k] for k in ("chunk_id", "title", "start_line", "end_line")})

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path
