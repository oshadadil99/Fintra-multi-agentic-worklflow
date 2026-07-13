"""Vertex AI chat-model factories - the only place LLM clients are built."""

from functools import lru_cache

from langchain_google_vertexai import ChatVertexAI

from fintra.config import get_settings


@lru_cache
def orchestrator_llm() -> ChatVertexAI:
    """Fast, deterministic classifier for routing."""
    settings = get_settings()
    return ChatVertexAI(
        model_name=settings.orchestrator_model,
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
        temperature=0,
        max_tokens=1024,  # gemini-2.5 spends thinking tokens before answering
    )


@lru_cache
def agent_llm() -> ChatVertexAI:
    """Accuracy-first model for grounded financial answers."""
    settings = get_settings()
    return ChatVertexAI(
        model_name=settings.agent_model,
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
        temperature=0.2,
        max_tokens=2048,
    )
