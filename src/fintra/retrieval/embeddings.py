"""Gemini embeddings pinned to the project's dimensionality.

Wraps Vertex AI `gemini-embedding-001` so that every vector - document or
query - comes back at exactly `EMBEDDING_DIM` (768) dimensions, matching the
Pinecone index. Task types are set per call site (documents vs queries),
which measurably improves retrieval quality on asymmetric search.
"""

from langchain_core.embeddings import Embeddings
from langchain_google_vertexai import VertexAIEmbeddings

from fintra.config import get_settings


class GeminiEmbeddings(Embeddings):
    def __init__(self) -> None:
        settings = get_settings()
        self._dim = settings.embedding_dim
        self._client = VertexAIEmbeddings(
            model_name=settings.embedding_model,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._client.embed(
            texts, dimensions=self._dim, embeddings_task_type="RETRIEVAL_DOCUMENT"
        )

    def embed_query(self, text: str) -> list[float]:
        return self._client.embed(
            [text], dimensions=self._dim, embeddings_task_type="RETRIEVAL_QUERY"
        )[0]
