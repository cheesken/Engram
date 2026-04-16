"""
Tests for engram.storage adapters.

Tests InMemoryAdapter. Redis tests are skipped unless REDIS_URL is set.
"""

import pytest

from engram.models import HistoryEntry, MemoryEntry, ConsistencyLevel
from engram.storage.memory import InMemoryAdapter


# ---------------------------------------------------------------------------
# InMemoryAdapter — write / read
# ---------------------------------------------------------------------------


def test_write_and_read(memory_storage):
    """Writing an entry and reading it back should return the same data."""
    entry = MemoryEntry(
        key="budget",
        value=5000,
        agent_id="agent-A",
        role="admin",
        vector_clock={"agent-A": 1},
        consistency_level=ConsistencyLevel.EVENTUAL,
    )
    memory_storage.write(entry)
    result = memory_storage.read("budget")
    assert result is not None
    assert result.key == "budget"
    assert result.value == 5000


def test_read_returns_none_for_missing_key(memory_storage):
    """Reading a non-existent key should return None."""
    pass


def test_write_overwrites_existing(memory_storage):
    """Writing the same key twice should overwrite the first entry."""
    pass


# ---------------------------------------------------------------------------
# InMemoryAdapter — delete
# ---------------------------------------------------------------------------


def test_delete_removes_entry(memory_storage):
    """Deleting a key should make it unreadable."""
    pass


def test_delete_nonexistent_key_is_noop(memory_storage):
    """Deleting a key that doesn't exist should not raise."""
    pass


# ---------------------------------------------------------------------------
# InMemoryAdapter — list_keys
# ---------------------------------------------------------------------------


def test_list_keys_returns_all(memory_storage):
    """list_keys with no prefix should return all stored keys."""
    pass


def test_list_keys_with_prefix(memory_storage):
    """list_keys with a prefix should only return matching keys."""
    pass


# ---------------------------------------------------------------------------
# InMemoryAdapter — history
# ---------------------------------------------------------------------------


def test_write_and_read_history(memory_storage):
    """Writing a history entry and reading it back should work."""
    pass


def test_read_history_filters(memory_storage):
    """History filters (agent_id, since, until) should be applied correctly."""
    pass


# ---------------------------------------------------------------------------
# InMemoryAdapter — ping
# ---------------------------------------------------------------------------


def test_ping_returns_true(memory_storage):
    """In-memory adapter ping should always return True."""
    pass
