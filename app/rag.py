from __future__ import annotations

import re
import math
from collections import Counter
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Any

from app.config import settings
from app.ingest import load_documents_from_csv
from app.openrouter import chat_completion, embed_texts
from app.vector_store import get_collection

SLANG_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bm\s*protiv\b", " əks yola "),
    (r"\bprotiv\b", " əks yola "),
    (r"\bvstr(?:ec|eç|ech|esh|eş)?n?(?:i|iy|yy)?\b", " əks yola "),
    (r"\bqirmizi\b", " qırmızı "),
    (r"\bsvetafor\b", " işıqfor "),
    (r"\bshtraf\b", " cərimə "),
)


def _build_context(documents: list[str], max_chars: int) -> str:
    blocks: list[str] = []
    used = 0
    for i, text in enumerate(documents, start=1):
        block = f"[Mənbə {i}]\n{text.strip()}\n"
        if used + len(block) > max_chars:
            break
        blocks.append(block)
        used += len(block)
    return "\n".join(blocks)


def _extract_reply_from_doc(content: str) -> str:
    marker = "\nCavab:"
    if marker in content:
        return content.split(marker, 1)[1].strip()
    return content.strip()


def _tokenize(text: str) -> set[str]:
    return set(_tokenize_list(text))


def _normalize_text(text: str) -> str:
    normalized = text.lower()
    for pattern, replacement in SLANG_PATTERNS:
        normalized = re.sub(pattern, replacement, normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _normalize_token(token: str) -> str:
    normalized = token.lower()
    suffixes = (
        "larının",
        "lərinin",
        "ların",
        "lərin",
        "larına",
        "lərinə",
        "lardan",
        "lərdən",
        "ların",
        "lərin",
        "nin",
        "nın",
        "nun",
        "nün",
        "ın",
        "in",
        "un",
        "ün",
        "na",
        "nə",
        "ya",
        "yə",
        "da",
        "də",
        "dan",
        "dən",
        "dir",
        "dır",
        "dur",
        "dür",
        "tir",
        "tır",
        "tur",
        "tür",
        "lar",
        "lər",
    )
    for suffix in suffixes:
        if normalized.endswith(suffix) and len(normalized) - len(suffix) >= 3:
            normalized = normalized[: -len(suffix)]
            break
    return normalized


def _tokenize_list(text: str) -> list[str]:
    cleaned = _normalize_text(text)
    tokens = [_normalize_token(t) for t in re.findall(r"\w+", cleaned)]
    return [t for t in tokens if len(t) > 2]


@lru_cache(maxsize=1)
def _local_index() -> tuple[list[dict[str, Any]], dict[str, int], float]:
    docs = load_documents_from_csv()
    rows: list[dict[str, Any]] = []
    doc_frequency: Counter[str] = Counter()
    total_doc_len = 0
    for doc in docs:
        question = doc.metadata.get("question", "")
        normalized_question = _normalize_text(question)
        question_tokens = _tokenize_list(normalized_question)
        token_counts = Counter(question_tokens)
        unique_tokens = set(question_tokens)
        doc_frequency.update(unique_tokens)
        total_doc_len += len(question_tokens)
        rows.append(
            {
                "content": doc.content,
                "question": question,
                "normalized_question": normalized_question,
                "reply": _extract_reply_from_doc(doc.content),
                "user_id": doc.metadata.get("user_id", ""),
                "date": doc.metadata.get("date", ""),
                "token_counts": token_counts,
                "doc_len": len(question_tokens),
            }
        )
    avg_doc_len = total_doc_len / max(1, len(rows))
    return rows, dict(doc_frequency), avg_doc_len


def _local_search(query: str, limit: int) -> list[dict[str, Any]]:
    q = query.strip()
    normalized_q = _normalize_text(q)
    q_tokens = _tokenize_list(normalized_q)
    q_unique = set(q_tokens)
    if not q_unique:
        return []
    rows, df_map, avg_doc_len = _local_index()
    n_docs = len(rows)
    k1 = 1.2
    b = 0.75
    scored: list[dict[str, Any]] = []
    for row in rows:
        token_counts: Counter[str] = row["token_counts"]
        doc_len = max(1, row["doc_len"])
        bm25 = 0.0
        matched_tokens = 0
        for token in q_unique:
            tf = token_counts.get(token, 0)
            if tf == 0:
                continue
            matched_tokens += 1
            df = df_map.get(token, 0)
            idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1)
            denom = tf + k1 * (1 - b + b * doc_len / max(1.0, avg_doc_len))
            bm25 += idf * (tf * (k1 + 1)) / denom
        fuzzy_score = SequenceMatcher(None, normalized_q, row["normalized_question"]).ratio()
        overlap_ratio = matched_tokens / max(1, len(q_unique))
        confidence = 0.65 * overlap_ratio + 0.35 * fuzzy_score
        rank_score = bm25 + 0.25 * fuzzy_score
        if rank_score <= 0:
            continue
        scored.append({**row, "score": rank_score, "confidence": confidence})
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:limit]


def _sources_from_local(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for i, row in enumerate(rows, start=1):
        sources.append(
            {
                "rank": i,
                "distance": round(1 - row["score"], 4),
                "user_id": row.get("user_id", ""),
                "date": row.get("date", ""),
                "question": row.get("question", ""),
                "preview": row.get("content", "")[:240],
            }
        )
    return sources


def _sources_from_vector(docs: list[str], metas: list[dict[str, Any]], distances: list[float]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances), start=1):
        sources.append(
            {
                "rank": i,
                "distance": dist,
                "user_id": (meta or {}).get("user_id", ""),
                "date": (meta or {}).get("date", ""),
                "question": (meta or {}).get("question", ""),
                "preview": (doc or "")[:240],
            }
        )
    return sources


def _build_messages(context: str, user_question: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "Sən Azərbaycan dilində yol hərəkəti qaydaları köməkçisisən. "
                "Cavabı qısa, dəqiq ver. Verilən kontekstə əsaslan. "
                "Kontekst çatmırsa bunu açıq şəkildə bildir."
            ),
        },
        {"role": "user", "content": f"Kontekst:\n{context}\n\nSual: {user_question}"},
    ]


def _is_context_intent(text: str) -> bool:
    q = text.lower()
    return "konteks" in q or "kontekst" in q


def _format_context_overview(sources: list[dict[str, Any]]) -> str:
    if not sources:
        return "Hazırda cavab üçün istifadə olunan kontekst tapılmadı."
    lines = ["Hazırkı cavab üçün istifadə olunan kontekst mənbələri:"]
    for src in sources[:5]:
        lines.append(f"- #{src['rank']}: {src.get('question', '')} ({src.get('date', '-')})")
    return "\n".join(lines)


def answer_query(user_question: str, top_k: int | None = None) -> dict[str, Any]:
    k = top_k or settings.top_k
    docs: list[str] = []
    metas: list[dict[str, Any]] = []
    distances: list[float] = []

    collection = get_collection()
    collection_count = collection.count()

    has_api_key = bool(settings.openrouter_api_key)

    if collection_count > 0 and has_api_key:
        query_vector = embed_texts([user_question])[0]
        result = collection.query(
            query_embeddings=[query_vector],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        docs = result["documents"][0] if result.get("documents") else []
        metas = result["metadatas"][0] if result.get("metadatas") else []
        distances = result["distances"][0] if result.get("distances") else []

    has_good_vector_results = bool(docs) and min(distances or [10.0]) <= settings.vector_max_distance

    if not has_good_vector_results:
        local_hits = _local_search(user_question, settings.local_fallback_top_k)
        if not local_hits:
            return {
                "answer": (
                    "Bu sual üçün uyğun məlumat tapılmadı. "
                    "Sualı bir az daha konkret yazın və ya fərqli ifadə edin."
                ),
                "sources": [],
                "mode": "no-result",
            }
        top_hit = local_hits[0]
        sources = _sources_from_local(local_hits)
        if _is_context_intent(user_question):
            return {"answer": _format_context_overview(sources), "sources": sources, "mode": "context-local"}
        if (not has_api_key) or (
            settings.use_direct_answer and top_hit.get("confidence", 0.0) >= settings.direct_answer_min_score
        ):
            return {"answer": top_hit["reply"], "sources": sources, "mode": "direct-local"}
        context = _build_context([item["content"] for item in local_hits], settings.max_context_chars)
        answer = chat_completion(_build_messages(context, user_question))
        return {"answer": answer, "sources": sources, "mode": "local-rag"}

    if not has_api_key:
        return {
            "answer": "OPENROUTER_API_KEY təyin edilməyib. LLM cavabı üçün əvvəlcə env dəyişənini əlavə edin.",
            "sources": _sources_from_vector(docs, metas, distances),
            "mode": "vector-no-key",
        }

    vector_sources = _sources_from_vector(docs, metas, distances)
    if _is_context_intent(user_question):
        return {"answer": _format_context_overview(vector_sources), "sources": vector_sources, "mode": "context-vector"}

    context = _build_context(docs, settings.max_context_chars)
    answer = chat_completion(_build_messages(context, user_question))
    return {"answer": answer, "sources": vector_sources, "mode": "vector-rag"}
