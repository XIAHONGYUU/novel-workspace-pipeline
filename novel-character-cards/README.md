# novel-character-cards

Convert a long novel into structured character data and Markdown character cards.

## Scope

This first version provides:

- text decoding for common Windows Chinese encodings
- chapter-aware chunking
- heuristic offline character extraction for initial validation
- optional OpenAI Responses API extraction with structured JSON output
- JSON merge pipeline
- Markdown card rendering
- prompt template for future AI extraction

## Project layout

```text
novel-character-cards/
  prompts/
  src/novel_character_cards/
  tests/
```

## Quick start

```bash
PYTHONPATH=src python3 -m novel_character_cards.cli pipeline \
  ./example.txt \
  --workdir ./demo-run
```

Run a small sample first:

```bash
PYTHONPATH=src python3 -m novel_character_cards.cli pipeline \
  ./example.txt \
  --workdir ./demo-run \
  --limit-chunks 5
```

Use the AI extractor when `OPENAI_API_KEY` is available:

```bash
PYTHONPATH=src OPENAI_API_KEY=... python3 -m novel_character_cards.cli pipeline \
  ./example.txt \
  --workdir ./demo-run-ai \
  --extractor openai \
  --model gpt-5 \
  --limit-chunks 5
```

Artifacts will be created under the selected workdir:

- `chunks/`
- `extractions/`
- `merged/characters.json`
- `cards/`
- `cards/index.md`
