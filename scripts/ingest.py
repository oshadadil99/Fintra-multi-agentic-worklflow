"""Ingest knowledge-base documents into Pinecone namespaces.

Folder convention (folder name IS the namespace):

    data/general-faq/     -> namespace "general-faq"
    data/loan-details/    -> namespace "loan-details"   (loans AND leasing)
    data/saving-details/  -> namespace "saving-details"

Supported formats: .md, .txt, .pdf

Idempotent: vector IDs are deterministic (relative path + chunk index), so
re-running refreshes existing chunks instead of duplicating them.

Usage:
    python scripts/ingest.py                       # ingest all namespaces
    python scripts/ingest.py --namespace loan-details
    python scripts/ingest.py --namespace loan-details --wipe
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "src"))

from langchain_text_splitters import RecursiveCharacterTextSplitter  # noqa: E402

from fintra.retrieval.vectorstore import _pinecone_index, get_vectorstore  # noqa: E402

DATA_DIR = ROOT / "data"
NAMESPACES = ("general-faq", "loan-details", "saving-details")
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def load_text(path: Path) -> str:
    if path.suffix.lower() in (".md", ".txt"):
        return path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        return "\n\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    raise ValueError(f"unsupported format: {path.suffix}")


def ingest_namespace(namespace: str, wipe: bool) -> int:
    folder = DATA_DIR / namespace
    files = sorted(
        p
        for p in folder.rglob("*")
        if p.suffix.lower() in (".md", ".txt", ".pdf") and p.name.lower() != "readme.md"
    )
    if not files:
        print(f"  {namespace}: no documents found in {folder} - skipped.")
        return 0

    if wipe:
        try:
            _pinecone_index().delete(delete_all=True, namespace=namespace)
            print(f"  {namespace}: existing vectors wiped.")
        except Exception:  # noqa: BLE001 - namespace may simply not exist yet
            pass

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    texts: list[str] = []
    ids: list[str] = []
    metadatas: list[dict] = []
    for path in files:
        rel = path.relative_to(DATA_DIR).as_posix()
        chunks = splitter.split_text(load_text(path))
        for i, chunk in enumerate(chunks):
            texts.append(chunk)
            ids.append(f"{rel}#{i}")
            metadatas.append({"source": rel, "chunk": i})
        print(f"  {namespace}: {rel} -> {len(chunks)} chunks")

    get_vectorstore(namespace).add_texts(texts=texts, ids=ids, metadatas=metadatas)
    print(f"  {namespace}: upserted {len(texts)} chunks from {len(files)} file(s).")
    return len(texts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--namespace", choices=NAMESPACES, help="ingest a single namespace")
    parser.add_argument("--wipe", action="store_true", help="clear the namespace(s) first")
    args = parser.parse_args()

    targets = (args.namespace,) if args.namespace else NAMESPACES
    print(f"Ingesting into namespaces: {', '.join(targets)}")
    total = sum(ingest_namespace(ns, args.wipe) for ns in targets)
    print(f"\nDone - {total} chunks embedded and upserted.")
    return 0 if total else 1


if __name__ == "__main__":
    sys.exit(main())
