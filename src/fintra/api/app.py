"""HTTP interface for the Morgan Treasuries assistant.

The /chat contract (session_id + message) is deliberately identical to what
the future WhatsApp webhook will forward - the sender's phone number becomes
the session_id and nothing else changes.

Run:  uvicorn fintra.api.app:app --reload
"""

import logging
from pathlib import Path

from dotenv import load_dotenv

# resolve .env from the repo root regardless of the uvicorn working directory
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

from fastapi import FastAPI, HTTPException  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from fintra import __version__  # noqa: E402

logger = logging.getLogger("fintra.api")

app = FastAPI(
    title="Fintra - Morgan Treasuries Assistant",
    description="Multi-agent RAG assistant (LangGraph hub-and-spoke on Vertex AI).",
    version=__version__,
)


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=50, examples=["94771234567"])
    message: str = Field(min_length=1, max_length=2000, examples=["What are your FD rates?"])


class ChatResponse(BaseModel):
    session_id: str
    route: str
    answer: str
    sources: list[str]


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    from fintra.service import answer_query  # deferred: keeps app import light

    try:
        result = answer_query(request.session_id, request.message)
    except Exception:  # noqa: BLE001
        logger.exception("chat turn failed (session_id=%s)", request.session_id)
        raise HTTPException(
            status_code=500,
            detail="The assistant is temporarily unavailable. Please try again shortly.",
        ) from None
    return ChatResponse(**result)
