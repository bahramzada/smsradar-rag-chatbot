from __future__ import annotations

import os

import chromadb
from chromadb.api.models.Collection import Collection

from app.config import settings


def get_collection() -> Collection:
    os.makedirs(settings.chroma_dir, exist_ok=True)
    client = chromadb.PersistentClient(path=settings.chroma_dir)
    return client.get_or_create_collection(
        name=settings.chroma_collection,
        metadata={"hnsw:space": "cosine"},
    )
