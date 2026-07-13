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

    # Behaviour
    memory_window: int = 10
    retrieval_k: int = 4
    retrieval_fetch_k: int = 10
    retrieval_lambda: float = 0.5


@lru_cache
def get_settings() -> Settings:
    return Settings()
