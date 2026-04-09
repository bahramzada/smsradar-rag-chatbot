from __future__ import annotations

from typing import Any

import requests

from app.config import settings


def _headers() -> dict[str, str]:
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required for OpenRouter requests.")
    return {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "HTTP-Referer": settings.openrouter_site_url,
        "X-Title": settings.openrouter_app_name,
        "Content-Type": "application/json",
    }


def embed_texts(texts: list[str], model: str | None = None) -> list[list[float]]:
    model_name = model or settings.embedding_model
    payload = {"model": model_name, "input": texts}
    response = requests.post(
        f"{settings.openrouter_base_url}/embeddings",
        headers=_headers(),
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()["data"]
    return [item["embedding"] for item in data]


def chat_completion(messages: list[dict[str, str]], model: str | None = None) -> str:
    model_name = model or settings.chat_model
    payload: dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "temperature": settings.chat_temperature,
        "max_tokens": settings.chat_max_tokens,
    }
    response = requests.post(
        f"{settings.openrouter_base_url}/chat/completions",
        headers=_headers(),
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()
