"""
Tests for engram.history.HistoryLog.

Covers: append, get_history, get_entry, get_snapshot, create_rollback_entry.
"""

from datetime import datetime, timezone

from engram.history import HistoryLog
from engram.models import HistoryEntry, WriteType


# ---------------------------------------------------------------------------
# append / get_entry
# ---------------------------------------------------------------------------


def test_append_and_get_entry(history_log):
    """Appending an entry should make it retrievable by write_id."""
    entry = HistoryEntry(
        key="budget",
        value=5000,
        agent_id="agent-A",
        role="admin",
        vector_clock={"agent-A": 1},
    )
    history_log.append(entry)
    retrieved = history_log.get_entry(entry.write_id)
    assert retrieved is not None
    assert retrieved.key == "budget"
    assert retrieved.value == 5000


def test_get_entry_returns_none_for_unknown(history_log):
    """get_entry should return None for a non-existent write_id."""
    pass


# ---------------------------------------------------------------------------
# get_history
# ---------------------------------------------------------------------------


def test_get_history_returns_chronological_order():
    """Entries should be returned oldest-first."""
    pass


def test_get_history_filters_by_agent_id():
    """Only entries from the specified agent should be returned."""
    pass


def test_get_history_filters_by_since():
    """Only entries with timestamp >= since should be returned."""
    pass


def test_get_history_filters_by_until():
    """Only entries with timestamp <= until should be returned."""
    pass


def test_get_history_empty_for_unknown_key(history_log):
    """Should return empty list for a key with no history."""
    pass


# ---------------------------------------------------------------------------
# get_snapshot
# ---------------------------------------------------------------------------


def test_get_snapshot_returns_most_recent_before():
    """Should return the entry with the latest timestamp that is causally before at_clock."""
    pass


def test_get_snapshot_excludes_concurrent():
    """Concurrent entries should not be returned by get_snapshot."""
    pass


def test_get_snapshot_returns_none_when_no_entries_qualify():
    """Should return None if no entries are before or equal to at_clock."""
    pass


# ---------------------------------------------------------------------------
# create_rollback_entry
# ---------------------------------------------------------------------------


def test_create_rollback_entry_creates_new_entry():
    """Should create a new HistoryEntry with write_type=ROLLBACK."""
    pass


def test_create_rollback_entry_raises_for_unknown_write_id(history_log):
    """Should raise ValueError if the write_id is not found."""
    pass
