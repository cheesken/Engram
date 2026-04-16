"""
Append-only history log for all writes to Engram memory.

Never deletes or mutates entries. Rollbacks are new entries, not deletions
of old ones. This is the complete audit trail.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from engram.models import HistoryEntry, Ordering, WriteType
from engram.vector_clock import VectorClock


class HistoryLog:
    """
    Append-only log of every write ever made to Engram memory.

    Never deletes or mutates entries. Rollbacks are new entries, not
    deletions of old ones. This is the complete audit trail.

    Maintains an in-memory log for fast queries (get_snapshot, get_entry)
    and delegates to an optional StorageAdapter for persistence. If no
    storage is provided, history lives only in memory (suitable for tests
    and development, but lost on restart).
    """

    def __init__(self, storage=None) -> None:
        """
        Args:
            storage: Optional StorageAdapter for persistent history.
                     If provided, append() also calls storage.write_history()
                     so history survives restarts. If None, history is in-memory only.
        """
        self._log: list[HistoryEntry] = []
        self._storage = storage

    def append(self, entry: HistoryEntry) -> None:
        """
        Append a new entry to the in-memory log and persist to storage if available.

        Entries must be stored in the order they are appended.
        Do not allow mutation of existing entries.

        If self._storage is set, also call self._storage.write_history(entry)
        to persist the entry for durability.

        Args:
            entry: The HistoryEntry to append.
        """
        raise NotImplementedError

    def get_history(
        self,
        key: str,
        agent_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> list[HistoryEntry]:
        """
        Return all history entries for the given key, in chronological order
        (oldest first).

        Filters (all optional, apply all that are provided):
        - agent_id: only return entries written by this agent.
        - since: only return entries with timestamp >= since.
        - until: only return entries with timestamp <= until.

        Return empty list if no entries match.

        Args:
            key: The memory key to look up history for.
            agent_id: Optional filter by agent ID.
            since: Optional lower bound on timestamp (inclusive).
            until: Optional upper bound on timestamp (inclusive).

        Returns:
            A list of HistoryEntry objects in chronological order.
        """
        raise NotImplementedError

    def get_entry(self, write_id: str) -> Optional[HistoryEntry]:
        """
        Look up a single history entry by its write_id.

        Args:
            write_id: The unique write ID to search for.

        Returns:
            The HistoryEntry if found, or None if not found.
        """
        raise NotImplementedError

    def get_snapshot(
        self, key: str, at_clock: dict[str, int]
    ) -> Optional[HistoryEntry]:
        """
        Time-travel query: return the most recent write to key whose vector
        clock is BEFORE or EQUAL to at_clock.

        This answers: "what was the value of key at this point in causal time?"

        Logic:
        1. Filter all entries for this key.
        2. For each entry, compare its vector_clock to at_clock using
           VectorClock.compare().
        3. Keep only entries where the result is BEFORE or EQUAL.
        4. Among those, return the one with the latest timestamp.
        5. Return None if no entries qualify.

        Note: CONCURRENT entries are excluded — a concurrent write did not
        causally precede at_clock.

        Args:
            key: The memory key to look up.
            at_clock: A dict representing the vector clock point in causal time.

        Returns:
            The HistoryEntry representing the value at that point in time,
            or None if no entries qualify.
        """
        raise NotImplementedError

    def create_rollback_entry(
        self,
        write_id: str,
        initiating_agent_id: str,
        initiating_role: str,
    ) -> HistoryEntry:
        """
        Create and return a new HistoryEntry that represents a soft rollback.

        Logic:
        1. Find the original entry with the given write_id.
           Raise ValueError if not found.
        2. Create a new HistoryEntry with:
           - write_id: new uuid4
           - key: same as original
           - value: same as original (this is the value being restored)
           - agent_id: initiating_agent_id
           - role: initiating_role
           - vector_clock: copy of original entry's vector_clock
           - write_type: WriteType.ROLLBACK
           - rollback_of: the original write_id
           - timestamp: now (utcnow)
        3. Do NOT append to the log here — the caller (middleware) does that.
        4. Return the new entry.

        Important: this does not delete or modify the original entry.
        History is immutable.

        Args:
            write_id: The write_id of the entry to roll back to.
            initiating_agent_id: The agent requesting the rollback.
            initiating_role: The role of the agent requesting the rollback.

        Returns:
            A new HistoryEntry with write_type=ROLLBACK.

        Raises:
            ValueError: If the original write_id is not found in the log.
        """
        raise NotImplementedError
