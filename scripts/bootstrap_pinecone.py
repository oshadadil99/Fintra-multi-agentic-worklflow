"""Create the Fintra Pinecone index (idempotent).

Serverless index on the free Starter tier: 768 dims (matches
gemini-embedding-001 output), cosine metric, AWS us-east-1.

Usage:  python scripts/bootstrap_pinecone.py
"""

import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from pinecone import Pinecone, ServerlessSpec  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fintra.config import get_settings  # noqa: E402

NAMESPACES = ("general-faq", "loan-details", "saving-details")


def main() -> int:
    settings = get_settings()
    pc = Pinecone(api_key=settings.pinecone_api_key)
    name = settings.pinecone_index

    if pc.has_index(name):
        print(f"Index '{name}' already exists - nothing to create.")
    else:
        print(f"Creating serverless index '{name}' ({settings.embedding_dim}d, cosine) ...")
        pc.create_index(
            name=name,
            dimension=settings.embedding_dim,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        while not pc.describe_index(name).status["ready"]:
            time.sleep(2)
        print("Index created and ready.")

    desc = pc.describe_index(name)
    if desc.dimension != settings.embedding_dim:
        print(
            f"[FAIL] Index dimension is {desc.dimension}, but EMBEDDING_DIM={settings.embedding_dim}. "
            "Delete the index in the Pinecone console and re-run this script."
        )
        return 1

    stats = pc.Index(name).describe_index_stats()
    print(f"Index '{name}': dimension={desc.dimension}, metric={desc.metric}")
    print(f"Total vectors: {stats.get('total_vector_count', 0)}")
    for ns in NAMESPACES:
        count = stats.get("namespaces", {}).get(ns, {}).get("vector_count", 0)
        print(f"  namespace {ns!r}: {count} vectors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
