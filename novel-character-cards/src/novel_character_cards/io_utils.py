from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


COMMON_ENCODINGS = (
    "utf-8",
    "utf-8-sig",
    "gb18030",
    "gbk",
    "big5",
    "utf-16",
    "latin-1",
)


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


def ensure_dir(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory
