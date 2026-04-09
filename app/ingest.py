from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from typing import Iterator, TypeVar

from app.config import settings
from app.openrouter import embed_texts
from app.vector_store import get_collection


@dataclass
class DocumentRow:
    doc_id: str
    content: str
    metadata: dict[str, str]


def _make_id(user_id: str, date: str, question: str, reply: str) -> str:
    raw = f"{user_id}|{date}|{question}|{reply}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def load_documents_from_csv(path: str | None = None) -> list[DocumentRow]:
    csv_path = path or settings.csv_path
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
