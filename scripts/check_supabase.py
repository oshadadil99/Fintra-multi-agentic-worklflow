"""Verify the Supabase chat_history table exists and is writable.

Inserts one probe row, reads it back, deletes it.

Usage:  python scripts/check_supabase.py
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from supabase import create_client  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fintra.config import get_settings  # noqa: E402

PROBE_SESSION = "__fintra_smoke_test__"


def main() -> int:
    settings = get_settings()
    client = create_client(settings.supabase_url, settings.supabase_service_role_key)

    try:
        client.table("chat_history").insert(
            {"session_id": PROBE_SESSION, "role": "system", "content": "connectivity probe"}
        ).execute()
        rows = (
            client.table("chat_history")
            .select("id, role, content")
            .eq("session_id", PROBE_SESSION)
            .execute()
        )
        client.table("chat_history").delete().eq("session_id", PROBE_SESSION).execute()
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        print(f"[FAIL] Supabase check: {msg}")
        if "chat_history" in msg and ("does not exist" in msg or "Could not find" in msg):
            print(
                "\nThe chat_history table is missing. Open the Supabase dashboard -> "
                "SQL Editor, paste scripts/bootstrap_supabase.sql, and run it. Then re-run this script."
            )
        return 1

    print(f"[PASS] Supabase chat_history: insert/select/delete OK ({len(rows.data)} probe row).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
