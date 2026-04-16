"""
Abstract base class for all storage adapters.

The rest of Engram never imports Redis, Chroma, or any specific database.
It only ever calls these methods. To add a new storage backend, implement
this class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from engram.models import HistoryEntry, MemoryEntry


class StorageAdapter(ABC):
    """
    Abstract interface that every storage backend must implement.

    The rest of Engram never imports Redis, Chroma, or any specific database.
    It only ever calls these methods. To add a new storage backend,
    implement this class.
    """

    @abstractmethod
    def write(self, entry: MemoryEntry) -> None:
        """
        Persist a MemoryEntry, overwriting any existing entry for the same key.

        Args:
            entry: The MemoryEntry to store.
        """

    @abstractmethod
    def read(self, key: str) -> Optional[MemoryEntry]:
        """
        Read the current MemoryEntry for the given key.

        Args:
            key: The memory key to look up.

        Returns:
            The MemoryEntry if found, or None if the key does not exist.
        """

    @abstractmethod
    def write_history(self, entry: HistoryEntry) -> None:
        """
        Persist a HistoryEntry to the history log.

        Args:
            entry: The HistoryEntry to append.
        """

    @abstractmethod
    def read_history(
        self,
        key: str,
        agent_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> list[HistoryEntry]:
        """
        Read history entries for the given key with optional filters.

        Args:
            key: The memory key to look up history for.
            agent_id: Optional filter by agent ID.
            since: Optional lower bound on timestamp (inclusive).
            until: Optional upper bound on timestamp (inclusive).

        Returns:
            A list of HistoryEntry objects in chronological order.
        """

    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Delete the current MemoryEntry for the given key.

        Args:
            key: The memory key to delete.
        """

    @abstractmethod
    def list_keys(self, prefix: Optional[str] = None) -> list[str]:
        """
        List all keys in storage, optionally filtered by prefix.

        Args:
            prefix: If provided, only return keys that start with this prefix.

        Returns:
            A list of key strings.
        """

    @abstractmethod
    def ping(self) -> bool:
        """
        Check that the storage backend is reachable and functional.

        Returns:
            True if the backend is healthy, False otherwise.
        """
