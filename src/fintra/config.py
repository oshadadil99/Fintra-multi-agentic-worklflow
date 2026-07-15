"""Central configuration - every tunable lives in .env, nothing is hardcoded."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Google Cloud / Vertex AI (the only paid service - burns GCP credits)
    google_cloud_project: str
    google_cloud_location: str = "us-central1"
    orchestrator_model: str = "gemini-2.5-flash"
    agent_model: str = "gemini-2.5-pro"
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768

    # Pinecone (free Starter tier - one index, partitioned by namespaces)
    pinecone_api_key: str
    pinecone_index: str = "fintra-kb"

    # Supabase (free tier - chat history store)
    supabase_url: str
    supabase_service_role_key: str

    # WhatsApp Cloud API (Meta) - filled in when the webhook goes live
    whatsapp_verify_token: str = ""
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""

    # Upstash Redis (optional read-through history cache) - empty disables caching
    upstash_redis_rest_url: str = ""
    upstash_redis_rest_token: str = ""

    # Behaviour
    memory_window: int = 10
    retrieval_k: int = 4
    retrieval_fetch_k: int = 10
    retrieval_lambda: float = 0.5


@lru_cache
def get_settings() -> Settings:
    return Settings()


def ensure_gcp_credentials() -> None:
    """Support serverless hosts (Vercel) where secrets are env-var-only.

    If GOOGLE_CREDENTIALS_JSON holds the service-account key JSON (raw or
    base64-encoded), write it to a temp file and point
    GOOGLE_APPLICATION_CREDENTIALS at it so the Google SDKs pick it up.
    A real key file path always takes precedence.
    """
    import base64
    import json
    import logging
    import os
    import tempfile
    from pathlib import Path

    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return
    raw = os.environ.get("GOOGLE_CREDENTIALS_JSON", "").strip()
    if not raw:
        return

    # tolerate values pasted with surrounding quotes
    if len(raw) > 1 and raw[0] in "'\"" and raw[-1] == raw[0]:
        raw = raw[1:-1].strip()
    # tolerate base64-encoded keys
    if not raw.startswith("{"):
        try:
            raw = base64.b64decode(raw, validate=True).decode("utf-8").strip()
        except Exception:  # noqa: BLE001 - fall through to the clear error below
            pass

    try:
        json.loads(raw)
    except json.JSONDecodeError:
        logging.getLogger("fintra.config").error(
            "GOOGLE_CREDENTIALS_JSON is not valid JSON (starts with %r). "
            "Paste the full CONTENTS of the service-account key file - it must "
            "start with '{' - not the file path, and without wrapping quotes.",
            raw[:12],
        )
        return

    path = Path(tempfile.gettempdir()) / "gcp-credentials.json"
    path.write_text(raw, encoding="utf-8")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(path)
