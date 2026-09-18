"""C-VEC wrapper -- Chroma, embedded/persistent-local (platform decision PLA-2).

One collection, `embedded_content`, per DATA-MODEL-conversational-crm-T-1-v2.0.md
Section 2.1. Real chromadb usage, runs fully locally -- no cloud dependency,
genuinely exercised by this backend's test suite.
"""
from __future__ import annotations

import chromadb

from app.config import get_settings

_COLLECTION_NAME = "embedded_content"
_client = None
_collection = None


def get_collection():
    global _client, _collection
    if _collection is None:
        settings = get_settings()
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        _collection = _client.get_or_create_collection(name=_COLLECTION_NAME)
    return _collection


def reset_for_tests(persist_dir: str):
    """Test-only helper: point the module-level singleton at a fresh temp dir."""
    global _client, _collection
    _client = chromadb.PersistentClient(path=persist_dir)
    _collection = _client.get_or_create_collection(name=_COLLECTION_NAME)
    return _collection


def upsert_interaction_chunk(interaction_id: str, account_id: str | None, text: str, embedding: list[float], embedded_at: str):
    """DATA-MODEL Section 2.2/2.3: one chunk per interaction (no chunking split
    in this scope's implementation -- semantic chunking of longer documents is
    only relevant to adapter-sourced content, which this scope's stub adapters
    never actually produce). account_id may be a sentinel when unmatched.
    """
    collection = get_collection()
    doc_id = f"interaction:{interaction_id}:0"
    collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[text],
        metadatas=[{
            "account_id": account_id or "__unassigned__",
            "source_type": "interaction",
            "source_id": interaction_id,
            "chunk_index": 0,
            "embedded_at": embedded_at,
        }],
    )
    return doc_id


def update_chunk_account(interaction_id: str, new_account_id: str):
    """Metadata-only upsert on customer resolution (DATA-MODEL Section 2.3) --
    does NOT recompute the embedding vector, since the underlying text is
    unchanged (decision DAT-2).
    """
    collection = get_collection()
    doc_id = f"interaction:{interaction_id}:0"
    existing = collection.get(ids=[doc_id], include=["embeddings", "documents", "metadatas"])
    if not existing["ids"]:
        return
    metadata = dict(existing["metadatas"][0])
    metadata["account_id"] = new_account_id
    collection.upsert(
        ids=[doc_id],
        embeddings=[existing["embeddings"][0]],
        documents=[existing["documents"][0]],
        metadatas=[metadata],
    )


def query_by_account(account_id: str, query_embedding: list[float], n_results: int = 5) -> list[str]:
    collection = get_collection()
    if collection.count() == 0:
        return []
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, collection.count()),
        where={"account_id": account_id},
    )
    docs = result.get("documents") or [[]]
    return docs[0]
