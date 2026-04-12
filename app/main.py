from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.ingest import CsvDataUnavailableError
from app.rag import answer_query
from app.vector_store import get_collection

app = FastAPI(title="smsradar-rag")
web_dir = Path(__file__).resolve().parent.parent / "web"
app.mount("/web", StaticFiles(directory=web_dir), name="web")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=15)


@app.get("/")
def root() -> FileResponse:
    return FileResponse(web_dir / "index.html")


@app.get("/api/health")
def health() -> dict:
    collection = get_collection()
    return {"status": "ok", "collection": collection.name, "count": collection.count()}


@app.post("/api/chat")
def chat(payload: ChatRequest) -> dict:
    question = payload.message.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Message is empty.")
    try:
        return answer_query(question, payload.top_k)
    except CsvDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
