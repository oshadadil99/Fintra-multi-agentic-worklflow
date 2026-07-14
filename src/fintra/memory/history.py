"""Per-session chat history on Supabase.

`session_id` is the conversation key - today the CLI/API caller supplies it;
in the WhatsApp phase it becomes the sender's phone number, unchanged.
"""

from functools import lru_cache

from supabase import Client, create_client

from fintra.config import get_settings

TABLE = "chat_history"


@lru_cache
def _client() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def load_history(session_id: str, limit: int | None = None) -> list[dict]:
    """Last `limit` messages for the session, oldest first."""
    limit = limit or get_settings().memory_window
    rows = (
        _client()
        .table(TABLE)
        .select("role, content")
        .eq("session_id", session_id)
        .order("id", desc=True)
        .limit(limit)
        .execute()
    )
    return list(reversed(rows.data))


def claim_message(message_id: str) -> bool:
    """Claim a webhook message id; False means a duplicate delivery (skip it).

    WhatsApp retries deliveries that respond slowly (e.g. cold starts), which
    would produce duplicate replies. The insert-if-absent on the primary key
    is atomic, so concurrent retries can't both claim the same message.
    On any storage error we choose at-least-once over silence and process.
    """
    try:
        result = (
            _client()
            .table("processed_messages")
            .upsert({"message_id": message_id}, on_conflict="message_id", ignore_duplicates=True)
            .execute()
        )
        return bool(result.data)
    except Exception:  # noqa: BLE001
        return True


def append_turn(session_id: str, query: str, answer: str) -> None:
    _client().table(TABLE).insert(
        [
            {"session_id": session_id, "role": "user", "content": query},
            {"session_id": session_id, "role": "assistant", "content": answer},
        ]
    ).execute()
