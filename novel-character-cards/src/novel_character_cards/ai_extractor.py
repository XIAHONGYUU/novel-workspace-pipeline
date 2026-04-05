from __future__ import annotations

from pathlib import Path
import json
import os
from urllib import request

from .chunker import Chunk


API_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-5"

CHARACTER_SCHEMA = {
    "name": "character_extraction",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "chunk_id": {"type": "string"},
            "characters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "aliases": {"type": "array", "items": {"type": "string"}},
                        "identity": {"type": "string"},
                        "faction": {"type": "string"},
                        "status": {"type": "string"},
                        "first_appearance": {"type": "string"},
                        "summary": {"type": "string"},
                        "appearance": {"type": "array", "items": {"type": "string"}},
                        "personality": {"type": "array", "items": {"type": "string"}},
                        "abilities": {"type": "array", "items": {"type": "string"}},
                        "equipment": {"type": "array", "items": {"type": "string"}},
                        "relationships": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "target": {"type": "string"},
                                    "type": {"type": "string"},
                                },
                                "required": ["target", "type"],
                                "additionalProperties": False,
                            },
                        },
                        "timeline": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "stage": {"type": "string"},
                                    "event": {"type": "string"},
                                },
                                "required": ["stage", "event"],
                                "additionalProperties": False,
                            },
                        },
                        "evidence": {"type": "array", "items": {"type": "string"}},
                        "mention_count": {"type": "integer"},
                    },
                    "required": [
                        "name",
                        "aliases",
                        "identity",
                        "faction",
                        "status",
                        "first_appearance",
                        "summary",
                        "appearance",
                        "personality",
                        "abilities",
                        "equipment",
                        "relationships",
                        "timeline",
                        "evidence",
                        "mention_count",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["chunk_id", "characters"],
        "additionalProperties": False,
    },
}


def build_prompt(chunk: Chunk, prompt_template: str) -> str:
    return (
        f"{prompt_template.strip()}\n\n"
        f"Chunk ID: {chunk.chunk_id}\n"
        f"Chapter Title: {chunk.title}\n"
        f"Line Range: {chunk.start_line}-{chunk.end_line}\n\n"
        "Novel chunk:\n"
        f"{chunk.text}\n"
    )


def _extract_response_text(payload: dict) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return content["text"]

    raise ValueError("No structured text found in OpenAI response")


def extract_with_openai(
    chunk: Chunk,
    *,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
    prompt_path: str | Path | None = None,
) -> dict:
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    template_path = Path(prompt_path) if prompt_path else Path(__file__).resolve().parents[2] / "prompts" / "extract_characters.md"
    prompt_template = template_path.read_text(encoding="utf-8")
    prompt = build_prompt(chunk, prompt_template)

    body = {
        "model": model,
        "input": prompt,
        "text": {
            "format": {
                "type": "json_schema",
                **CHARACTER_SCHEMA,
            }
        },
    }

    req = request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with request.urlopen(req) as response:
        payload = json.loads(response.read().decode("utf-8"))

    parsed = json.loads(_extract_response_text(payload))
    parsed["chunk_id"] = chunk.chunk_id
    return parsed
