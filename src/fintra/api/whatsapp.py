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
                    messages.append(
                        {
                            "id": msg.get("id", ""),
                            "from": msg["from"],
                            "text": msg["text"]["body"],
                        }
                    )
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


def mark_as_read(message_id: str) -> None:
    """Blue ticks + a typing indicator while the answer is being generated.

    Purely cosmetic, so failures are logged and ignored - a missing tick
    must never cost a customer their answer.
    """
    settings = get_settings()
    try:
        httpx.post(
            f"{GRAPH_API}/{settings.whatsapp_phone_number_id}/messages",
            headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
            json={
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id,
                "typing_indicator": {"type": "text"},
            },
            timeout=10,
        ).raise_for_status()
    except Exception:  # noqa: BLE001
        logger.warning("mark-as-read failed (id=%s)", message_id)


def process_message(sender: str, text: str, message_id: str = "") -> None:
    from fintra.service import answer_query

    try:
        if message_id:
            mark_as_read(message_id)  # blue ticks + "typing..." appear immediately
        result = answer_query(sender, text)
        send_whatsapp_message(sender, result["answer"])
        logger.info("replied to %s (route=%s)", sender, result["route"])
    except Exception:  # noqa: BLE001 - one bad message must not break the batch
        logger.exception("failed to handle WhatsApp message from %s", sender)


@router.post("/webhook")
async def receive_webhook(request: Request) -> dict:
    from fintra.memory.history import claim_message

    payload = await request.json()
    for message in extract_text_messages(payload):
        # Meta redelivers when we respond slowly (cold starts) - only the
        # delivery that claims the message id first gets processed
        if message["id"] and not claim_message(message["id"]):
            logger.info("duplicate delivery ignored (id=%s)", message["id"])
            continue
        process_message(message["from"], message["text"], message["id"])
    # always 200 - Meta retries aggressively on errors, which would duplicate replies
    return {"status": "received"}
