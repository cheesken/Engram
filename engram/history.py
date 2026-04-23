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

    def __init__(self, storage=None) -> None:
        self._log: list[HistoryEntry] = []
        self._storage = storage

    def append(self, entry: HistoryEntry) -> None:
        self._log.append(entry)
        if self._storage is not None:
            self._storage.write_history(entry)

    def get_history(
        self,
        key: str,
        agent_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> list[HistoryEntry]:
        results = []

        for entry in self._log:
            # must match the key
            if entry.key != key:
                continue

            # optional filters — skip if condition not met
            if agent_id is not None and entry.agent_id != agent_id:
                continue
            if since is not None and entry.timestamp < since:
                continue
            if until is not None and entry.timestamp > until:
                continue

            results.append(entry)

        # _log is already in insertion order (oldest first) so no sort needed
        return results

    def get_entry(self, write_id: str) -> Optional[HistoryEntry]:
        for entry in self._log:
            if entry.write_id == write_id:
                return entry
        return None

    def get_snapshot(
        self, key: str, at_clock: dict[str, int]
    ) -> Optional[HistoryEntry]:
        target = VectorClock.from_dict(at_clock)
        candidates = []

        for entry in self._log:
            if entry.key != key:
                continue

            entry_clock = VectorClock.from_dict(entry.vector_clock)
            ordering = entry_clock.compare(target)

            # only keep entries that causally came before or are equal to at_clock
            # CONCURRENT means "happened in parallel without knowing about each other"
            # — that is NOT the same as "before", so we exclude it
            if ordering in (Ordering.BEFORE, Ordering.EQUAL):
                candidates.append(entry)

        if not candidates:
            return None

        # return the most recent among the qualifying entries
        return max(candidates, key=lambda e: e.timestamp)

    def create_rollback_entry(
        self,
        write_id: str,
        initiating_agent_id: str,
        initiating_role: str,
    ) -> HistoryEntry:
        original = self.get_entry(write_id)

        if original is None:
            raise ValueError(f"No entry found with write_id '{write_id}'")

        return HistoryEntry(
            write_id=str(uuid.uuid4()),          # brand new ID
            key=original.key,                    # same key
            value=original.value,                # same value being restored
            agent_id=initiating_agent_id,        # whoever triggered the rollback
            role=initiating_role,
            vector_clock=dict(original.vector_clock),  # copy of original's clock
            write_type=WriteType.ROLLBACK,
            rollback_of=write_id,                # points back at original
            timestamp=datetime.now(timezone.utc),
        )
    

 # Method by method
#append — simplest one. Add the entry to the list. If there's a storage adapter plugged in, also send it there.
#get_history — read the whole notebook for one key, then filter down by whatever optional criteria were passed in (agent, time range). Return oldest first.
#get_entry — scan every page looking for one specific write_id. Return it or None.
##get_snapshot — the time-travel one. "What did this key look like at clock point X?" Filter to entries that are BEFORE or EQUAL to the given clock, then return the most recent of those. CONCURRENT entries are excluded because concurrent means "we didn't know about each other" — that's not the same as "before".
#create_rollback_entry — find the original entry, build a brand new entry copying its key and value, but stamp it as WriteType.ROLLBACK and point back at the original. Don't append it — just hand it back to the caller.