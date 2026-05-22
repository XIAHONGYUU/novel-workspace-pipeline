from __future__ import annotations

from pathlib import Path
import json
import os
import re
from urllib import request, error as urllib_error

from .chunker import Chunk


API_URL = "https://api.openai.com/v1/responses"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-5"
DEEPSEEK_DEFAULT_MODEL = "deepseek-chat"

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
    with request.urlopen(req, timeout=120) as response:
        payload = json.loads(response.read().decode("utf-8"))

    parsed = json.loads(_extract_response_text(payload))
    parsed["chunk_id"] = chunk.chunk_id
    return parsed


def _schema_to_description() -> str:
    """Convert CHARACTER_SCHEMA to a human-readable description for system prompts."""
    props = CHARACTER_SCHEMA["schema"]["properties"]["characters"]["items"]["properties"]
    required = CHARACTER_SCHEMA["schema"]["properties"]["characters"]["items"]["required"]

    lines = [
        "你必须返回一个 JSON 对象，结构如下：",
        "",
        "```json",
        "{",
        '  "chunk_id": "字符串，从用户消息中获取",'
        '  "characters": [',

        "    {",
    ]
    for field in required:
        field_type = props[field].get("type", "string")
        if field_type == "array":
            items = props[field].get("items", {})
            if isinstance(items, dict) and items.get("type") == "object":
                sub_props = items.get("properties", {})
                sub_required = items.get("required", [])
                sub_lines = [f'      "{field}": [', "        {"]
                for sub_field in sub_required:
                    sub_lines.append(f'          "{sub_field}": "字符串"')
                sub_lines.append("        }")
                sub_lines.append("      ]")
                lines.extend(sub_lines)
            else:
                lines.append(f'      "{field}": ["字符串数组"]')
        elif field == "mention_count":
            lines.append(f'      "{field}": 整数')
        else:
            lines.append(f'      "{field}": "字符串"')
    lines.extend([
        "    }",
        "  ]",
        "}",
        "```",
        "",
        "注意：",
        "- 只返回 JSON，不要有任何其他文字",
        "- 如果某章没有人物，characters 返回空数组 []",
        "- 所有必填字段都必须存在，如果没有信息则用空字符串或空数组",
    ])
    return "\n".join(lines)


DEEPSEEK_SYSTEM_PROMPT_TEMPLATE = """你是一个小说人物信息抽取助手。你的任务是从小说文本片段中抽取所有出场人物的结构化信息卡。

{json_instructions}

抽取规则：
1. 只抽取在当前片段中实际出场或提及的人物
2. 人物名以原文为准，如果只有姓氏或简称，也作为别名列出
3. mention_count 是当前片段中该人物被提及的大致次数
4. evidence 列出原文中能支持该人物信息的 1-3 句原文
5. 别称 (aliases) 包括化名、尊称、简称、绰号等"""


def _extract_deepseek_json(text: str) -> str:
    """Extract JSON from DeepSeek response, handling markdown code blocks and truncated JSON."""
    text = text.strip()
    # Try to extract from markdown code block
    code_block = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if code_block:
        return code_block.group(1).strip()
    # Try to find the outermost JSON object
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        return text[brace_start:brace_end + 1]
    return text


def _repair_truncated_json(text: str) -> str:
    """Attempt to repair truncated JSON by closing open brackets and strings."""
    # Count open/close braces and brackets
    open_braces = text.count("{") - text.count("}")
    open_brackets = text.count("[") - text.count("]")

    # Check if the last non-whitespace char looks like an incomplete string or value
    stripped = text.rstrip()
    if stripped.endswith(","):
        # Remove trailing comma before closing
        stripped = stripped[:-1]

    # Close any open structures
    repaired = stripped
    repaired += "]" * open_brackets
    repaired += "}" * open_braces
    return repaired


def extract_with_deepseek(
    chunk: Chunk,
    *,
    model: str = DEEPSEEK_DEFAULT_MODEL,
    api_key: str | None = None,
    prompt_path: str | Path | None = None,
) -> dict:
    """Extract characters from a novel chunk using DeepSeek API.

    Uses the DeepSeek Chat Completions API (OpenAI-compatible).
    Requires DEEPSEEK_API_KEY environment variable or explicit api_key parameter.
    """
    key = api_key or os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set. Set it via environment variable or pass api_key parameter.")

    template_path = Path(prompt_path) if prompt_path else Path(__file__).resolve().parents[2] / "prompts" / "extract_characters.md"
    prompt_template = template_path.read_text(encoding="utf-8")

    json_instructions = _schema_to_description()
    system_prompt = DEEPSEEK_SYSTEM_PROMPT_TEMPLATE.format(json_instructions=json_instructions)

    user_message = (
        f"{prompt_template.strip()}\n\n"
        f"Chunk ID: {chunk.chunk_id}\n"
        f"Chapter Title: {chunk.title}\n"
        f"Line Range: {chunk.start_line}-{chunk.end_line}\n\n"
        "Novel chunk:\n"
        f"{chunk.text}\n"
    )

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
        "max_tokens": 8192,
    }

    req = request.Request(
        DEEPSEEK_API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore") if exc.fp else ""
        raise RuntimeError(
            f"DeepSeek API request failed (HTTP {exc.code}): {error_body[:500]}"
        ) from exc
    except urllib_error.URLError as exc:
        raise RuntimeError(f"DeepSeek API connection failed: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"DeepSeek API request failed (timeout or unexpected): {exc}") from exc

    choices = payload.get("choices", [])
    if not choices:
        raise ValueError(f"No choices in DeepSeek response: {json.dumps(payload, ensure_ascii=False)[:500]}")

    message = choices[0].get("message", {})
    content = message.get("content", "")
    if not content:
        raise ValueError(f"Empty content in DeepSeek response: {json.dumps(payload, ensure_ascii=False)[:500]}")

    json_text = _extract_deepseek_json(content)
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        # Attempt to repair truncated JSON
        repaired = _repair_truncated_json(json_text)
        try:
            parsed = json.loads(repaired)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Failed to parse DeepSeek JSON response even after repair. "
                f"Raw content (first 500 chars): {content[:500]}"
            ) from exc

    parsed["chunk_id"] = chunk.chunk_id
    return parsed
