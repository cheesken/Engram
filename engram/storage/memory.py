"""
In-memory storage adapter using plain Python dicts.

Zero external dependencies. Thread-safe via threading.Lock.
Default adapter for testing and demo day.
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Optional

from engram.models import HistoryEntry, MemoryEntry
from engram.storage.base import StorageAdapter


class InMemoryAdapter(StorageAdapter):
    """
    In-memory storage using plain Python dicts.
    Zero external dependencies. Thread-safe.
    Default adapter for testing and demo day.
    """

    def __init__(self) -> None:
        self._store: dict[str, MemoryEntry] = {}
        self._history: list[HistoryEntry] = []
        self._lock = threading.Lock()

    def write(self, entry: MemoryEntry) -> None:
        """
        Store the MemoryEntry in the in-memory dict, keyed by entry.key.

        Thread-safe: acquires self._lock before mutating self._store.
        Overwrites any existing entry for the same key.

        Args:
            entry: The MemoryEntry to store.
        """
        raise NotImplementedError

    def read(self, key: str) -> Optional[MemoryEntry]:
        """
        Look up the MemoryEntry for the given key in self._store.

        Thread-safe: acquires self._lock before reading.

        Args:
            key: The memory key to look up.

        Returns:
            The MemoryEntry if found, or None if the key does not exist.
        """
        raise NotImplementedError

    def write_history(self, entry: HistoryEntry) -> None:
        """
        Append a HistoryEntry to self._history.

        Thread-safe: acquires self._lock before mutating self._history.

        Args:
            entry: The HistoryEntry to append.
        """
        raise NotImplementedError

    def read_history(
        self,
        key: str,
        agent_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> list[HistoryEntry]:
        """
        Filter self._history for entries matching the given key and optional filters.

        Thread-safe: acquires self._lock before reading self._history.

        Filters (all optional, apply all that are provided):
        - agent_id: only return entries written by this agent.
        - since: only return entries with timestamp >= since.
        - until: only return entries with timestamp <= until.

        Returns entries in chronological order (oldest first, which is insertion order).

        Args:
            key: The memory key to look up history for.
            agent_id: Optional filter by agent ID.
            since: Optional lower bound on timestamp (inclusive).
            until: Optional upper bound on timestamp (inclusive).

        Returns:
            A list of HistoryEntry objects matching the filters.
        """
        raise NotImplementedError

    def delete(self, key: str) -> None:
        """
        Remove the MemoryEntry for the given key from self._store.

        Thread-safe: acquires self._lock before mutating.
        No-op if the key does not exist (do not raise).

        Args:
            key: The memory key to delete.
        """
        raise NotImplementedError

    def list_keys(self, prefix: Optional[str] = None) -> list[str]:
        """
        Return all keys in self._store, optionally filtered by prefix.

        Thread-safe: acquires self._lock before reading.

        Args:
            prefix: If provided, only return keys that start with this prefix.

        Returns:
            A sorted list of key strings.
        """
        raise NotImplementedError

    def ping(self) -> bool:
        """
        Always returns True for the in-memory adapter.

        Returns:
            True (in-memory storage is always available).
        """
        raise NotImplementedError
