"""API contract tests - answer_query is mocked, no graph or services run."""

from fastapi.testclient import TestClient

import fintra.service
from fintra.api.app import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_contract(monkeypatch):
    monkeypatch.setattr(
        fintra.service,
        "answer_query",
        lambda session_id, message: {
            "session_id": session_id,
            "route": "saving",
            "answer": "stub",
            "sources": [],
        },
    )
    response = client.post("/chat", json={"session_id": "94771234567", "message": "FD rates?"})
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "session_id": "94771234567",
        "route": "saving",
        "answer": "stub",
        "sources": [],
    }


def test_chat_rejects_empty_message():
    response = client.post("/chat", json={"session_id": "x", "message": ""})
    assert response.status_code == 422


def test_chat_rejects_oversized_session_id():
    # DB column is VARCHAR(50) - the API must refuse before the DB would
    response = client.post("/chat", json={"session_id": "x" * 51, "message": "hi"})
    assert response.status_code == 422


def test_chat_hides_internal_errors(monkeypatch):
    def boom(session_id, message):
        raise RuntimeError("pinecone exploded: secret-internals")

    monkeypatch.setattr(fintra.service, "answer_query", boom)
    response = client.post("/chat", json={"session_id": "x", "message": "hi"})
    assert response.status_code == 500
    assert "secret-internals" not in response.text
