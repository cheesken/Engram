"""
ChromaDB storage adapter — NOT YET IMPLEMENTED.

TODO: Implement vector-based memory storage using ChromaDB.
This enables semantic search across agent memory — e.g. finding all
memories related to "budget constraints" without knowing the exact key.

ChromaDB docs: https://docs.trychroma.com
Install: pip install chromadb

Suggested approach:
- One Chroma collection per Engram app
- Store value as document text, metadata includes all other MemoryEntry fields
- Use collection.query() for semantic reads
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from engram.models import HistoryEntry, MemoryEntry
from engram.storage.base import StorageAdapter


class ChromaAdapter(StorageAdapter):
    """
    ChromaDB storage adapter — NOT YET IMPLEMENTED.

    TODO: Implement vector-based memory storage using ChromaDB.
    This enables semantic search across agent memory — e.g. finding all
    memories related to "budget constraints" without knowing the exact key.

    ChromaDB docs: https://docs.trychroma.com
    Install: pip install chromadb

    Suggested approach:
    - One Chroma collection per Engram app
    - Store value as document text, metadata includes all other MemoryEntry fields
    - Use collection.query() for semantic reads
    """

    def __init__(self) -> None:
        """
        TODO: Initialize ChromaDB client and collection.

        Suggested:
            import chromadb
            self._client = chromadb.Client()
            self._collection = self._client.get_or_create_collection("engram")
        """
        raise NotImplementedError("ChromaAdapter is not yet implemented")

    def write(self, entry: MemoryEntry) -> None:
        """
        TODO: Upsert a MemoryEntry into the Chroma collection.

        Suggested: Use collection.upsert() with entry.key as the ID,
        entry.value as the document, and all other fields as metadata.
        """
        raise NotImplementedError("ChromaAdapter.write is not yet implemented")

    def read(self, key: str) -> Optional[MemoryEntry]:
        """
        TODO: Query the Chroma collection by ID (key).

        Suggested: Use collection.get(ids=[key]) and reconstruct MemoryEntry
        from the document and metadata.
        """
        raise NotImplementedError("ChromaAdapter.read is not yet implemented")

    def write_history(self, entry: HistoryEntry) -> None:
        """
        TODO: Store a HistoryEntry in a separate Chroma collection or as metadata.

        Suggested: Use a separate collection "engram_history" with write_id as ID.
        """
        raise NotImplementedError("ChromaAdapter.write_history is not yet implemented")

    def read_history(
        self,
        key: str,
        agent_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> list[HistoryEntry]:
        """
        TODO: Query history entries from Chroma with metadata filters.

        Suggested: Use collection.get() with where filters on key, agent_id,
        and timestamp range.
        """
        raise NotImplementedError("ChromaAdapter.read_history is not yet implemented")

    def delete(self, key: str) -> None:
        """
        TODO: Delete a document from the Chroma collection by ID.

        Suggested: Use collection.delete(ids=[key]).
        """
        raise NotImplementedError("ChromaAdapter.delete is not yet implemented")

    def list_keys(self, prefix: Optional[str] = None) -> list[str]:
        """
        TODO: List all document IDs in the collection, optionally filtered by prefix.

        Suggested: Use collection.get() and filter IDs by prefix in Python.
        """
        raise NotImplementedError("ChromaAdapter.list_keys is not yet implemented")

    def ping(self) -> bool:
        """
        TODO: Check that ChromaDB is reachable.

        Suggested: Try collection.count() and return True if no exception.
        """
        raise NotImplementedError("ChromaAdapter.ping is not yet implemented")
