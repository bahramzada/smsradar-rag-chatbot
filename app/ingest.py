from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, TypeVar

from app.config import settings
from app.openrouter import embed_texts
from app.vector_store import get_collection


@dataclass
class DocumentRow:
    doc_id: str
    content: str
    metadata: dict[str, str]


class CsvDataUnavailableError(FileNotFoundError):
    """Raised when the configured CSV source file cannot be found."""


def _make_id(user_id: str, date: str, question: str, reply: str) -> str:
    raw = f"{user_id}|{date}|{question}|{reply}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def _resolve_csv_path(path: str | None) -> Path:
    configured = (path or settings.csv_path).strip()
    if not configured:
        configured = "all_questions_clean.csv"
    project_root = Path(__file__).resolve().parent.parent

    raw_candidate = Path(configured).expanduser()
    candidates: list[Path] = []
    if raw_candidate.is_absolute():
        candidates.append(raw_candidate)
    else:
        candidates.append(raw_candidate)
        candidates.append(project_root / raw_candidate)

    fallback_name = "all_questions_clean.csv"
    can_use_legacy_fallback = raw_candidate.name == "all_questions.csv"
    if can_use_legacy_fallback:
        candidates.append(Path(fallback_name))
        candidates.append(project_root / fallback_name)

    unique_candidates: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_candidates.append(candidate)

    for candidate in unique_candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    tried = ", ".join(str(candidate) for candidate in unique_candidates)
    raise CsvDataUnavailableError(
        f"CSV file not found. Check CSV_PATH. Tried: {tried}"
    )


def load_documents_from_csv(path: str | None = None) -> list[DocumentRow]:
    csv_path = _resolve_csv_path(path)
    docs: list[DocumentRow] = []
    with open(csv_path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            user_id = (row.get("user_id") or "").strip()
            question = (row.get("question") or "").strip()
            reply = (row.get("reply") or "").strip()
            date = (row.get("date") or "").strip()
            if not question or not reply:
                continue
            content = f"Sual: {question}\nCavab: {reply}"
            docs.append(
                DocumentRow(
                    doc_id=_make_id(user_id, date, question, reply),
                    content=content,
                    metadata={"user_id": user_id, "date": date, "question": question},
                )
            )
    return docs


T = TypeVar("T")


def _chunks(items: list[T], size: int) -> Iterator[list[T]]:
    for idx in range(0, len(items), size):
        yield items[idx : idx + size]


def run_ingestion(path: str | None = None) -> dict[str, int]:
    documents = load_documents_from_csv(path)
    collection = get_collection()

    total = len(documents)
    inserted = 0
    skipped = 0
    batch_size = max(1, settings.ingest_batch_size)

    for batch in _chunks(documents, batch_size):
        ids = [doc.doc_id for doc in batch]
        existing = collection.get(ids=ids, include=[])
        existing_ids = set(existing.get("ids", []))
        new_docs = [doc for doc in batch if doc.doc_id not in existing_ids]
        skipped += len(batch) - len(new_docs)
        if not new_docs:
            continue

        texts = [doc.content for doc in new_docs]
        vectors = embed_texts(texts)
        collection.add(
            ids=[doc.doc_id for doc in new_docs],
            documents=texts,
            metadatas=[doc.metadata for doc in new_docs],
            embeddings=vectors,
        )
        inserted += len(new_docs)

    return {"total": total, "inserted": inserted, "skipped_existing": skipped}
