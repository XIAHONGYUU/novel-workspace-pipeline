from __future__ import annotations

import argparse
from pathlib import Path

from .chunker import chunk_text, write_chunks
from .extractor import write_extractions
from .focus_tracker import build_focus_reports
from .io_utils import decode_text_file, ensure_dir
from .merger import merge_extractions
from .renderer import render_cards


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build Markdown character cards from a novel.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    pipeline = subparsers.add_parser("pipeline", help="Run the full local pipeline.")
    pipeline.add_argument("input", help="Novel source text path")
    pipeline.add_argument("--workdir", required=True, help="Directory for pipeline outputs")
    pipeline.add_argument("--encoding", help="Preferred source encoding")
    pipeline.add_argument("--max-chars", type=int, default=12000, help="Maximum chunk size")
    pipeline.add_argument("--limit-chunks", type=int, help="Only process the first N chunks")
    pipeline.add_argument(
        "--extractor",
        choices=("heuristic", "openai"),
        default="heuristic",
        help="Character extraction backend",
    )
    pipeline.add_argument("--model", default="gpt-5", help="Model name for the OpenAI extractor")
    pipeline.add_argument("--prompt-path", help="Prompt template path for the OpenAI extractor")
    pipeline.add_argument("--focus-name", help="Only track one target character and write checkpoint summaries")
    pipeline.add_argument("--focus-alias", action="append", default=[], help="Additional alias for the focus character")
    pipeline.add_argument("--summary-interval", type=int, default=100, help="Checkpoint interval for focus tracking")

    return parser


def run_pipeline(
    input_path: str,
    workdir: str,
    encoding: str | None,
    max_chars: int,
    limit_chunks: int | None,
    extractor: str,
    model: str,
    prompt_path: str | None,
    focus_name: str | None,
    focus_aliases: list[str],
    summary_interval: int,
) -> None:
    decoded = decode_text_file(input_path, preferred_encoding=encoding)
    ensure_dir(workdir)
    chunks = chunk_text(decoded.text, max_chars=max_chars)
    if limit_chunks is not None:
        chunks = chunks[:limit_chunks]
    write_chunks(chunks, workdir)
    write_extractions(chunks, workdir, extractor_mode=extractor, model=model, prompt_path=prompt_path)
    if focus_name:
        focus_path = build_focus_reports(
            chunks,
            workdir,
            focus_name=focus_name,
            aliases=focus_aliases,
            summary_interval=summary_interval,
        )
        merged_path = None
        index_path = None
    else:
        focus_path = None
        merged_path = merge_extractions(workdir)
        index_path = render_cards(workdir)

    print(f"input: {input_path}")
    print(f"encoding: {decoded.encoding}")
    print(f"chunks: {len(chunks)}")
    print(f"extractor: {extractor}")
    if focus_path is not None:
        print(f"focus: {focus_path}")
        print(f"summary_interval: {summary_interval}")
    else:
        print(f"merged: {merged_path}")
        print(f"index: {index_path}")


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "pipeline":
        run_pipeline(
            args.input,
            args.workdir,
            args.encoding,
            args.max_chars,
            args.limit_chunks,
            args.extractor,
            args.model,
            args.prompt_path,
            args.focus_name,
            args.focus_alias,
            args.summary_interval,
        )


if __name__ == "__main__":
    main()
