from __future__ import annotations

import argparse
from pathlib import Path

from .converter import convert_text, decode_text_file, infer_title, normalize_lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert a text file into Markdown.")
    parser.add_argument("input", help="Source .txt file path")
    parser.add_argument("-o", "--output", help="Output .md file path")
    parser.add_argument("--title", help="Markdown title to use")
    parser.add_argument("--encoding", help="Preferred input encoding")
    parser.add_argument(
        "--frontmatter",
        action="store_true",
        help="Add simple YAML frontmatter to the Markdown output",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix(".md")

    decoded = decode_text_file(input_path, preferred_encoding=args.encoding)
    lines = normalize_lines(decoded.text)
    title = args.title or infer_title(lines, fallback=input_path.stem)
    markdown = convert_text(decoded.text, title=title, frontmatter=args.frontmatter)

    output_path.write_text(markdown, encoding="utf-8")
    print(f"input: {input_path}")
    print(f"output: {output_path}")
    print(f"encoding: {decoded.encoding}")
    print(f"title: {title}")


if __name__ == "__main__":
    main()
