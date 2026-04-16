"""
Redis-backed storage adapter for Engram.

Requires a running Redis instance at the configured REDIS_URL.
Serializes all Pydantic models to JSON for storage.

Key schema:
- Live memory: "engram:memory:{key}"
- History entries: stored as a Redis List at "engram:history:{key}"
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import redis

from engram.models import HistoryEntry, MemoryEntry
from engram.storage.base import StorageAdapter


class RedisAdapter(StorageAdapter):
    """
    Redis-backed storage adapter.

    Requires Redis running at REDIS_URL. Serializes all models to JSON
    using model.model_dump_json(). Deserializes using model.model_validate_json().

    Key schema:
    - Live memory: "engram:memory:{key}"
    - History entries: stored as a Redis List at "engram:history:{key}"
    """

    def __init__(self, redis_url: str) -> None:
        """
        Initialize the Redis client from the given URL.

        Args:
            redis_url: Redis connection URL (e.g. "redis://localhost:6379/0").
        """
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    def write(self, entry: MemoryEntry) -> None:
        """
        Store the MemoryEntry as a JSON string using Redis SET.

        Key: "engram:memory:{entry.key}"
        Value: entry.model_dump_json()

        Uses SET command to overwrite any existing value for this key.

        Args:
            entry: The MemoryEntry to store.
        """
        raise NotImplementedError

    def read(self, key: str) -> Optional[MemoryEntry]:
        """
        Read the MemoryEntry from Redis using GET.

        Key: "engram:memory:{key}"

        If the key does not exist in Redis (GET returns None), return None.
        Otherwise deserialize with MemoryEntry.model_validate_json(raw).

        Args:
            key: The memory key to look up.

        Returns:
            The MemoryEntry if found, or None.
        """
        raise NotImplementedError

    def write_history(self, entry: HistoryEntry) -> None:
        """
        Append a HistoryEntry to a Redis List using RPUSH.

        Key: "engram:history:{entry.key}"
        Value: entry.model_dump_json()

        RPUSH appends to the end of the list, preserving chronological order.

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
        Read all history entries for the given key from a Redis List using LRANGE.

        Key: "engram:history:{key}"
        Command: LRANGE key 0 -1  (returns all elements)

        Deserialize each element with HistoryEntry.model_validate_json().
        Apply optional filters (agent_id, since, until) in Python after retrieval.

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
        Delete the MemoryEntry from Redis using DEL.

        Key: "engram:memory:{key}"

        No-op if the key does not exist (Redis DEL handles this gracefully).

        Args:
            key: The memory key to delete.
        """
        raise NotImplementedError

    def list_keys(self, prefix: Optional[str] = None) -> list[str]:
        """
        List all memory keys in Redis using KEYS.

        Pattern: "engram:memory:{prefix}*" if prefix is provided,
                 "engram:memory:*" otherwise.

        Strip the "engram:memory:" prefix from each result before returning.

        Note: KEYS is O(N) and should not be used in production with large
        datasets. Consider SCAN for production use.

        Args:
            prefix: If provided, only return keys that start with this prefix.

        Returns:
            A list of key strings (without the "engram:memory:" prefix).
        """
        raise NotImplementedError

    def ping(self) -> bool:
        """
        Check Redis connectivity using the PING command.

        Returns:
            True if Redis responds to PING, False if an exception occurs.
        """
        raise NotImplementedError
