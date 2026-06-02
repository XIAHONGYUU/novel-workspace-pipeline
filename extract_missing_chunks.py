#!/usr/bin/env python3
"""Extract only missing chunks for a novel workspace."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).resolve().parent / "novel-character-cards" / "src"))

from novel_character_cards.chunker import Chunk
from novel_character_cards.extractor import write_extractions


def main():
    workspace = Path(sys.argv[1])
    workdir = workspace / "work"

    # Read all chunks
    chunks_json = json.loads((workdir / "chunks.json").read_text(encoding="utf-8"))
    
    # Load existing extractions to find which are missing
    existing = set()
    extractions_dir = workdir / "extractions"
    for f in extractions_dir.glob("chunk-*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            existing.add(d.get("chunk_id", ""))
        except Exception:
            pass

    # Find missing chunk IDs
    all_ids = {c["chunk_id"] for c in chunks_json}
    missing_ids = all_ids - existing

    if not missing_ids:
        print("All chunks already extracted!")
        return

    print(f"Total: {len(all_ids)}, Done: {len(existing)}, Missing: {len(missing_ids)}")
    print(f"Missing: {sorted(missing_ids)[:5]}...{sorted(missing_ids)[-3:]}")

    # Build Chunk objects for missing chunks only
    missing_chunks = []
    for c in chunks_json:
        if c["chunk_id"] in missing_ids:
            chunk_file = workdir / "chunks" / f"{c['chunk_id']}.json"
            if chunk_file.exists():
                chunk_data = json.loads(chunk_file.read_text(encoding="utf-8"))
                missing_chunks.append(Chunk(
                    chunk_id=c["chunk_id"],
                    title=c.get("title", ""),
                    text=chunk_data.get("text", ""),
                    start_line=c.get("start_line", 1),
                    end_line=c.get("end_line", 1),
                ))

    print(f"Processing {len(missing_chunks)} missing chunks...")
    write_extractions(
        missing_chunks,
        str(workdir),
        extractor_mode="deepseek",
        model="deepseek-chat",
    )
    print("Done!")


if __name__ == "__main__":
    main()
