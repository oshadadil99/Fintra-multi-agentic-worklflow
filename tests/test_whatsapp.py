"""WhatsApp webhook tests - Meta payloads simulated, nothing external called."""

from fastapi.testclient import TestClient

import fintra.api.whatsapp as whatsapp
from fintra.api.app import app
from fintra.api.whatsapp import extract_text_messages
from fintra.config import get_settings

client = TestClient(app)


def _configure_verify_token(monkeypatch, token="secret-verify"):
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", token)
    get_settings.cache_clear()


# --- GET /webhook: Meta's verification handshake ---


def test_verification_succeeds_with_correct_token(monkeypatch):
    _configure_verify_token(monkeypatch)
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "secret-verify",
            "hub.challenge": "1158201444",
        },
    )
    assert response.status_code == 200
    assert response.text == "1158201444"


def test_verification_rejects_wrong_token(monkeypatch):
    _configure_verify_token(monkeypatch)
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong",
            "hub.challenge": "x",
        },
    )
    assert response.status_code == 403


def test_verification_rejects_when_unconfigured(monkeypatch):
    _configure_verify_token(monkeypatch, token="")
    response = client.get(
        "/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "", "hub.challenge": "x"},
    )
    assert response.status_code == 403


# --- payload parsing ---

INBOUND_TEXT = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "123",
            "changes": [
                {
                    "field": "messages",
                    "value": {
                        "messaging_product": "whatsapp",
                        "messages": [
                            {
                                "from": "94771234567",
                                "id": "wamid.xyz",
                                "type": "text",
                                "text": {"body": "What are your FD rates?"},
                            }
                        ],
                    },
                }
            ],
        }
    ],
}

STATUS_ONLY = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "123",
            "changes": [
                {
                    "field": "messages",
                    "value": {
                        "messaging_product": "whatsapp",
                        "statuses": [{"id": "wamid.xyz", "status": "delivered"}],
                    },
                }
            ],
        }
    ],
}


def test_extract_parses_inbound_text():
    assert extract_text_messages(INBOUND_TEXT) == [
        {"id": "wamid.xyz", "from": "94771234567", "text": "What are your FD rates?"}
    ]


def test_extract_ignores_status_callbacks():
    assert extract_text_messages(STATUS_ONLY) == []


# --- POST /webhook: end-to-end with the pipeline mocked ---


def test_inbound_message_gets_answered_and_replied(monkeypatch):
    calls = {}
    monkeypatch.setattr("fintra.memory.history.claim_message", lambda mid: True)

    def fake_answer_query(session_id, message):
        calls["query"] = (session_id, message)
        return {"session_id": session_id, "route": "saving", "answer": "1-48 months.", "sources": []}

    monkeypatch.setattr("fintra.service.answer_query", fake_answer_query)
    monkeypatch.setattr(
        whatsapp, "send_whatsapp_message", lambda to, body: calls.setdefault("sent", (to, body))
    )

    response = client.post("/webhook", json=INBOUND_TEXT)
    assert response.status_code == 200
    assert calls["query"] == ("94771234567", "What are your FD rates?")
    assert calls["sent"] == ("94771234567", "1-48 months.")


def test_status_callback_triggers_nothing(monkeypatch):
    monkeypatch.setattr(
        whatsapp, "process_message", lambda *a: (_ for _ in ()).throw(AssertionError)
    )
    response = client.post("/webhook", json=STATUS_ONLY)
    assert response.status_code == 200


def test_failed_processing_still_returns_200(monkeypatch):
    monkeypatch.setattr("fintra.memory.history.claim_message", lambda mid: True)

    def boom(session_id, message):
        raise RuntimeError("pinecone down")

    monkeypatch.setattr("fintra.service.answer_query", boom)
    response = client.post("/webhook", json=INBOUND_TEXT)
    assert response.status_code == 200  # Meta must not retry-storm us


def test_duplicate_delivery_is_ignored(monkeypatch):
    """Meta redelivers on slow responses - the same message id must not answer twice."""
    monkeypatch.setattr("fintra.memory.history.claim_message", lambda mid: False)
    monkeypatch.setattr(
        whatsapp, "process_message", lambda *a: (_ for _ in ()).throw(AssertionError)
    )
    response = client.post("/webhook", json=INBOUND_TEXT)
    assert response.status_code == 200
