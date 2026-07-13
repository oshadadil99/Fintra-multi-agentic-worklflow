"""Pinecone vector store access - one index, partitioned by namespaces.

Retrieval strategy (locked in PLAN.md): cosine similarity with Maximal
Marginal Relevance re-ranking, so the k returned chunks are both relevant
and non-redundant (coherent context, no semantic overlap).
"""

from functools import lru_cache

from langchain_core.vectorstores import VectorStoreRetriever
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

from fintra.config import get_settings
from fintra.retrieval.embeddings import GeminiEmbeddings


@lru_cache
def _pinecone_index():
    settings = get_settings()
    return Pinecone(api_key=settings.pinecone_api_key).Index(settings.pinecone_index)


@lru_cache
def get_vectorstore(namespace: str) -> PineconeVectorStore:
    return PineconeVectorStore(
        index=_pinecone_index(),
        embedding=GeminiEmbeddings(),
        namespace=namespace,
        text_key="text",
    )


def get_retriever(namespace: str) -> VectorStoreRetriever:
    settings = get_settings()
    return get_vectorstore(namespace).as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": settings.retrieval_k,
            "fetch_k": settings.retrieval_fetch_k,
            "lambda_mult": settings.retrieval_lambda,
        },
    )
