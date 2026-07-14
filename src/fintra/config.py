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

    If GOOGLE_CREDENTIALS_JSON holds the service-account key JSON, write it
    to a temp file and point GOOGLE_APPLICATION_CREDENTIALS at it so the
    Google SDKs pick it up. A real key file path always takes precedence.
    """
    import os
    import tempfile
    from pathlib import Path

    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return
    raw = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
    if not raw:
        return
    path = Path(tempfile.gettempdir()) / "gcp-credentials.json"
    if not path.exists():
        path.write_text(raw, encoding="utf-8")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(path)
