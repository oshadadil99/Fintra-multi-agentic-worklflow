"""Vertex AI smoke test.

Verifies that all three paid model endpoints used by Fintra are reachable
with the configured GCP credentials, before any real code depends on them:

  1. Orchestrator chat model  (gemini-2.5-flash)
  2. Agent chat model         (gemini-2.5-pro)
  3. Embedding model          (gemini-embedding-001 @ 768 dims)

Usage:  python scripts/smoke_vertex.py
Exits non-zero if any check fails.
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
ORCHESTRATOR_MODEL = os.environ.get("ORCHESTRATOR_MODEL", "gemini-2.5-flash")
AGENT_MODEL = os.environ.get("AGENT_MODEL", "gemini-2.5-pro")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "gemini-embedding-001")
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "768"))

PASS = "  [PASS]"
FAIL = "  [FAIL]"
failures = 0


def check(label: str, fn):
    global failures
    start = time.perf_counter()
    try:
        detail = fn()
        elapsed = time.perf_counter() - start
        print(f"{PASS} {label} ({elapsed:.1f}s) {detail}")
    except Exception as exc:  # noqa: BLE001 - a smoke test reports everything
        failures += 1
        print(f"{FAIL} {label}: {type(exc).__name__}: {exc}")


def chat_check(model_name: str):
    from langchain_google_vertexai import ChatVertexAI

    def run():
        llm = ChatVertexAI(
            model_name=model_name,
            project=PROJECT,
            location=LOCATION,
            temperature=0,
            # generous cap: gemini-2.5 spends "thinking" tokens before answering
            max_tokens=1024,
        )
        reply = llm.invoke("Reply with exactly one word: OK")
        return f"-> reply: {reply.content.strip()!r}"

    return run


def embedding_check():
    from langchain_google_vertexai import VertexAIEmbeddings

    emb = VertexAIEmbeddings(
        model_name=EMBEDDING_MODEL, project=PROJECT, location=LOCATION
    )
    try:
        vector = emb.embed(
            texts=["Morgan Treasuries fixed deposit rates"],
            dimensions=EMBEDDING_DIM,
            embeddings_task_type="RETRIEVAL_QUERY",
        )[0]
    except TypeError:
        # older langchain-google-vertexai without dimensions kwarg
        vector = emb.embed_query("Morgan Treasuries fixed deposit rates")
    if len(vector) != EMBEDDING_DIM:
        raise ValueError(
            f"expected {EMBEDDING_DIM} dims, got {len(vector)} - "
            "Pinecone index dimension must match"
        )
    return f"-> {len(vector)} dims"


def main() -> int:
    print(f"Vertex AI smoke test  (project={PROJECT}, location={LOCATION})")
    if not PROJECT:
        print(f"{FAIL} GOOGLE_CLOUD_PROJECT is not set in .env")
        return 1
    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds and not Path(creds).is_file():
        print(f"{FAIL} GOOGLE_APPLICATION_CREDENTIALS points to a missing file: {creds}")
        return 1

    check(f"chat: {ORCHESTRATOR_MODEL}", chat_check(ORCHESTRATOR_MODEL))
    check(f"chat: {AGENT_MODEL}", chat_check(AGENT_MODEL))
    check(f"embeddings: {EMBEDDING_MODEL} @ {EMBEDDING_DIM}d", embedding_check)

    if failures:
        print(f"\n{failures} check(s) failed.")
        return 1
    print("\nAll Vertex AI checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
