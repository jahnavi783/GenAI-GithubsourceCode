import os
import env_loader  # noqa: F401 — loads .env with absolute path
from datetime import datetime
from typing import cast, Any

import chromadb

from vectordb.embeddings import get_embedding_fn


client = chromadb.PersistentClient(path=os.getenv("CHROMA_PATH", "./chroma_db"))


def _build_collection():
    try:
        return client.get_or_create_collection(
            name="commit_docs",
            embedding_function=cast(Any, get_embedding_fn()),
        )
    except Exception as error:
        # Fallback keeps startup resilient if embedding dependency is unavailable.
        print(f"Embedding function unavailable, using default collection config: {error}")
        return client.get_or_create_collection(name="commit_docs")


collection = _build_collection()


def commit_exists(sha: str) -> bool:
    existing = collection.get(ids=[sha], include=[])
    return bool(existing and existing.get("ids"))


def store_commit(sha: str, diff: str, documentation: str, author: str):
    collection.upsert(
        documents=[diff],
        metadatas=[
            {
                "sha": sha,
                "author": author,
                "documentation": documentation,
                "timestamp": str(datetime.now()),
            }
        ],
        ids=[sha],
    )
    print(f"Stored commit {sha[:7]} in ChromaDB")


def retrieve_similar(diff: str, top_k: int = 3) -> list:
    results = collection.query(query_texts=[diff], n_results=top_k)
    if not results or not results.get("metadatas") or not results["metadatas"]:
        return []
    return [
        {"documentation": metadata.get("documentation", "")}
        for metadata in results["metadatas"][0]
    ]
