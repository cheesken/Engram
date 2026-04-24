"""
Redis-backed storage adapter for Engram.

Requires a running Redis instance at the configured REDIS_URL.
Serializes all Pydantic models to JSON for storage.

Key schema:
- Live memory: "engram:memory:{key}"
- History entries: stored as a Redis List at "engram:history:{key}"
"""

from __future__ import annotations

from ast import pattern
from datetime import datetime
import os
from typing import Optional, cast

import redis

from engram.models import HistoryEntry, MemoryEntry
from engram.storage.base import StorageAdapter
from dotenv import load_dotenv

# Load variables from .env into the environment
load_dotenv()

_MEMORY_PREFIX = "engram:memory:"
_HISTORY_PREFIX = "engram:history:"

class RedisAdapter(StorageAdapter):

    def __init__(self):
        # Get the URL from the environment, provide a fallback if missing
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        # Use from_url to parse the connection string automatically
        self._client = redis.from_url(redis_url, decode_responses=True)


    def write(self, entry: MemoryEntry) -> None:
        self._client.set(
                    f"{_MEMORY_PREFIX}{entry.key}",
                    entry.model_dump_json(),
                )
 
    def read(self, key: str) -> Optional[MemoryEntry]:
        raw = self._client.get(f"{_MEMORY_PREFIX}{key}")
        if raw is None:
            return None
        if not isinstance(raw, (str, bytes, bytearray)):
            return None
        return MemoryEntry.model_validate_json(cast(str | bytes | bytearray, raw))
    
    def write_history(self, entry: HistoryEntry) -> None:
        self._client.rpush(
            f"{_HISTORY_PREFIX}{entry.key}",
            entry.model_dump_json(),
        )

    def read_history(
        self,
        key: str,
        agent_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> list[HistoryEntry]:
        raw_list = cast(list[str], self._client.lrange(f"{_HISTORY_PREFIX}{key}", 0, -1))
        entries = [HistoryEntry.model_validate_json(raw) for raw in raw_list]

        if agent_id is not None:
            entries = [e for e in entries if e.agent_id == agent_id]
        if since is not None:
            entries = [e for e in entries if e.timestamp >= since]
        if until is not None:
            entries = [e for e in entries if e.timestamp <= until]

        return entries  # already in insertion (oldest-first) order

    def delete(self, key: str) -> None:
        self._client.delete(f"{_MEMORY_PREFIX}{key}")

    def list_keys(self, prefix: Optional[str] = None) -> list[str]:
        pattern = f"{_MEMORY_PREFIX}{prefix or ''}*"
        raw_keys = cast(list[str], self._client.keys(pattern))
        stripped = [k.removeprefix(_MEMORY_PREFIX) for k in raw_keys]
        return sorted(stripped)

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except Exception:
            return False
