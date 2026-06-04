#!/usr/bin/env python3
from __future__ import annotations

import os
import time
from typing import Any, Iterable

import requests


RETRIABLE_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
DEFAULT_BASE_URL = "https://api.deepseek.com/v1/chat/completions"


def _first_env(keys: Iterable[str]) -> str:
    for key in keys:
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return ""


def _parse_csv_env(keys: Iterable[str]) -> list[str]:
    raw = _first_env(keys)
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = item.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def call_chat_completion(
    *,
    system_prompt: str,
    user_prompt: str,
    model_env_vars: Iterable[str],
    default_model: str,
    fallback_model_env_vars: Iterable[str] = (),
    api_key_env_vars: Iterable[str] = ("NOVEL_AI_API_KEY", "DEEPSEEK_API_KEY"),
    base_url_env_vars: Iterable[str] = ("NOVEL_AI_BASE_URL", "DEEPSEEK_BASE_URL"),
    response_format: dict[str, Any] | None = None,
    temperature: float = 0.35,
    max_tokens: int = 4000,
    timeout: int = 300,
    max_attempts: int = 4,
) -> dict[str, Any]:
    api_key = _first_env(api_key_env_vars)
    if not api_key:
        raise RuntimeError(
            "missing API key; tried env vars: " + ", ".join(api_key_env_vars)
        )

    base_url = _first_env(base_url_env_vars) or DEFAULT_BASE_URL
    primary_model = _first_env(model_env_vars) or default_model
    fallback_models = _parse_csv_env(fallback_model_env_vars)
    fallback_models.extend(_parse_csv_env(("NOVEL_AI_FALLBACK_MODELS",)))
    models = _unique([primary_model, *fallback_models, default_model])

    last_error = "chat completion failed without details"
    for model in models:
        for attempt in range(1, max_attempts + 1):
            payload: dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if response_format:
                payload["response_format"] = response_format

            try:
                response = requests.post(
                    base_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=timeout,
                )
            except requests.RequestException as exc:
                last_error = f"request failed via {base_url} using model {model}: {exc}"
                if attempt < max_attempts:
                    time.sleep(min(2 ** attempt, 12))
                    continue
                break

            if 200 <= response.status_code < 300:
                try:
                    raw_payload = response.json()
                    content = raw_payload["choices"][0]["message"]["content"]
                except (ValueError, KeyError, IndexError, TypeError) as exc:
                    last_error = f"invalid completion payload for model {model}: {exc}"
                    if attempt < max_attempts:
                        time.sleep(min(2 ** attempt, 12))
                        continue
                    break
                return {
                    "raw_api": raw_payload,
                    "content": content,
                    "model": model,
                    "base_url": base_url,
                }

            body = response.text.strip()
            last_error = (
                f"HTTP {response.status_code} via {base_url} using model {model}: {body[:400]}"
            )
            if response.status_code not in RETRIABLE_STATUS_CODES or attempt >= max_attempts:
                break
            time.sleep(min(2 ** attempt, 12))

    raise RuntimeError(last_error)
