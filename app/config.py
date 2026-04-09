from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(path: str = ".env") -> None:
    dotenv_path = Path(path)
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


def _env_int(key: str, default: int) -> int:
    value = os.getenv(key)
    return int(value) if value is not None else default


def _env_float(key: str, default: float) -> float:
    value = os.getenv(key)
    return float(value) if value is not None else default


def _env_bool(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str
    openrouter_base_url: str
    openrouter_site_url: str
    openrouter_app_name: str
    embedding_model: str
    chat_model: str
    csv_path: str
    chroma_dir: str
    chroma_collection: str
    ingest_batch_size: int
    top_k: int
    max_context_chars: int
    chat_max_tokens: int
    chat_temperature: float
    vector_max_distance: float
    local_fallback_top_k: int
    use_direct_answer: bool
    direct_answer_min_score: float


def load_settings() -> Settings:
    _load_dotenv()
    return Settings(
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", "").strip(),
        openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        openrouter_site_url=os.getenv("OPENROUTER_SITE_URL", "http://localhost:8000"),
        openrouter_app_name=os.getenv("OPENROUTER_APP_NAME", "smsradar-rag"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-large"),
        chat_model=os.getenv("CHAT_MODEL", "openai/gpt-oss-120b"),
        csv_path=os.getenv("CSV_PATH", "all_questions_clean.csv"),
        chroma_dir=os.getenv("CHROMA_DIR", "./data/chroma"),
        chroma_collection=os.getenv("CHROMA_COLLECTION", "smsradar_qa"),
        ingest_batch_size=max(1, _env_int("INGEST_BATCH_SIZE", 64)),
        top_k=max(1, _env_int("TOP_K", 5)),
        max_context_chars=max(500, _env_int("MAX_CONTEXT_CHARS", 3200)),
        chat_max_tokens=max(64, _env_int("CHAT_MAX_TOKENS", 500)),
        chat_temperature=_env_float("CHAT_TEMPERATURE", 0.2),
        vector_max_distance=_env_float("VECTOR_MAX_DISTANCE", 0.9),
        local_fallback_top_k=max(1, _env_int("LOCAL_FALLBACK_TOP_K", 5)),
        use_direct_answer=_env_bool("USE_DIRECT_ANSWER", True),
        direct_answer_min_score=_env_float("DIRECT_ANSWER_MIN_SCORE", 0.72),
    )


settings = load_settings()
