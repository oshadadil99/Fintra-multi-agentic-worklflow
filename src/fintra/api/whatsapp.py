"""WhatsApp Cloud API webhook.

Meta calls two endpoints on this router:

  GET  /webhook  - one-time verification handshake when you register the
                   webhook URL in the Meta developer console.
  POST /webhook  - message delivery. Processing is synchronous: on
                   serverless hosts (Vercel) execution freezes once the
                   response is returned, so background tasks are unreliable.
                   A full turn takes 2-5s, well inside Meta's retry window.

The sender's phone number becomes the session_id - which is why the memory
layer was keyed on session_id from day one.
"""

import logging

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from fintra.config import get_settings

logger = logging.getLogger("fintra.whatsapp")

router = APIRouter(tags=["whatsapp"])

GRAPH_API = "https://graph.facebook.com/v20.0"


@router.get("/webhook")
def verify_webhook(
    mode: str = Query(default="", alias="hub.mode"),
    token: str = Query(default="", alias="hub.verify_token"),
    challenge: str = Query(default="", alias="hub.challenge"),
) -> PlainTextResponse:
    settings = get_settings()
    if (
        mode == "subscribe"
        and settings.whatsapp_verify_token  # refuse if not configured
        and token == settings.whatsapp_verify_token
    ):
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="verification failed")


def extract_text_messages(payload: dict) -> list[dict]:
    """Pull inbound text messages out of Meta's envelope.

    Ignores status callbacks (sent/delivered/read) and non-text message
    types - those arrive on the same endpoint.
    """
    messages = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for msg in change.get("value", {}).get("messages", []):
                if msg.get("type") == "text":
                    messages.append({"from": msg["from"], "text": msg["text"]["body"]})
    return messages


def send_whatsapp_message(to: str, body: str) -> None:
    settings = get_settings()
    response = httpx.post(
        f"{GRAPH_API}/{settings.whatsapp_phone_number_id}/messages",
        headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
        json={
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body},
        },
        timeout=30,
    )
    response.raise_for_status()


def process_message(sender: str, text: str) -> None:
    from fintra.service import answer_query

    try:
        result = answer_query(sender, text)
        send_whatsapp_message(sender, result["answer"])
        logger.info("replied to %s (route=%s)", sender, result["route"])
    except Exception:  # noqa: BLE001 - one bad message must not break the batch
        logger.exception("failed to handle WhatsApp message from %s", sender)


@router.post("/webhook")
async def receive_webhook(request: Request) -> dict:
    payload = await request.json()
    for message in extract_text_messages(payload):
        process_message(message["from"], message["text"])
    # always 200 - Meta retries aggressively on errors, which would duplicate replies
    return {"status": "received"}
