"""
Tests for engram.storage adapters.

Tests InMemoryAdapter. Redis tests are skipped unless REDIS_URL is set.
"""

from datetime import datetime, timedelta, timezone

from engram.models import ConsistencyLevel, HistoryEntry, MemoryEntry
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
    assert memory_storage.read("missing") is None


def test_write_overwrites_existing(memory_storage):
    """Writing the same key twice should overwrite the first entry."""
    first = MemoryEntry(
        key="budget",
        value=100,
        agent_id="a1",
        role="admin",
        vector_clock={"a1": 1},
        consistency_level=ConsistencyLevel.EVENTUAL,
    )
    second = MemoryEntry(
        key="budget",
        value=200,
        agent_id="a1",
        role="admin",
        vector_clock={"a1": 2},
        consistency_level=ConsistencyLevel.EVENTUAL,
    )
    memory_storage.write(first)
    memory_storage.write(second)
    out = memory_storage.read("budget")
    assert out is not None
    assert out.value == 200
    assert out.vector_clock == {"a1": 2}


# ---------------------------------------------------------------------------
# InMemoryAdapter — delete
# ---------------------------------------------------------------------------


def test_delete_removes_entry(memory_storage):
    """Deleting a key should make it unreadable."""
    entry = MemoryEntry(
        key="k",
        value=1,
        agent_id="a",
        role="admin",
        vector_clock={"a": 1},
        consistency_level=ConsistencyLevel.EVENTUAL,
    )
    memory_storage.write(entry)
    memory_storage.delete("k")
    assert memory_storage.read("k") is None


def test_delete_nonexistent_key_is_noop(memory_storage):
    """Deleting a key that doesn't exist should not raise."""
    memory_storage.delete("nope")


# ---------------------------------------------------------------------------
# InMemoryAdapter — list_keys
# ---------------------------------------------------------------------------


def test_list_keys_returns_all(memory_storage):
    """list_keys with no prefix should return all stored keys."""
    for key in ("zebra", "apple", "mango"):
        memory_storage.write(
            MemoryEntry(
                key=key,
                value=1,
                agent_id="a",
                role="admin",
                vector_clock={"a": 1},
                consistency_level=ConsistencyLevel.EVENTUAL,
            )
        )
    assert memory_storage.list_keys() == ["apple", "mango", "zebra"]


def test_list_keys_with_prefix(memory_storage):
    """list_keys with a prefix should only return matching keys."""
    for key in ("budget", "budget.flights", "flights"):
        memory_storage.write(
            MemoryEntry(
                key=key,
                value=1,
                agent_id="a",
                role="admin",
                vector_clock={"a": 1},
                consistency_level=ConsistencyLevel.EVENTUAL,
            )
        )
    assert memory_storage.list_keys("budget") == ["budget", "budget.flights"]


# ---------------------------------------------------------------------------
# InMemoryAdapter — history
# ---------------------------------------------------------------------------


def test_write_and_read_history(memory_storage):
    """Writing a history entry and reading it back should work."""
    h1 = HistoryEntry(
        key="budget",
        value=10,
        agent_id="a1",
        role="admin",
        vector_clock={"a1": 1},
    )
    h2 = HistoryEntry(
        key="budget",
        value=20,
        agent_id="a2",
        role="admin",
        vector_clock={"a2": 1},
    )
    memory_storage.write_history(h1)
    memory_storage.write_history(h2)
    log = memory_storage.read_history("budget")
    assert len(log) == 2
    assert log[0].value == 10
    assert log[1].value == 20


def test_read_history_filters(memory_storage):
    """History filters (agent_id, since, until) should be applied correctly."""
    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    e1 = HistoryEntry(
        key="k",
        value=1,
        agent_id="alice",
        role="admin",
        vector_clock={"alice": 1},
        timestamp=base,
    )
    e2 = HistoryEntry(
        key="k",
        value=2,
        agent_id="bob",
        role="admin",
        vector_clock={"bob": 1},
        timestamp=base + timedelta(hours=1),
    )
    e3 = HistoryEntry(
        key="k",
        value=3,
        agent_id="alice",
        role="admin",
        vector_clock={"alice": 2},
        timestamp=base + timedelta(hours=2),
    )
    memory_storage.write_history(e1)
    memory_storage.write_history(e2)
    memory_storage.write_history(e3)

    by_agent = memory_storage.read_history("k", agent_id="alice")
    assert [x.value for x in by_agent] == [1, 3]

    window = memory_storage.read_history(
        "k", since=base + timedelta(minutes=30), until=base + timedelta(hours=1, minutes=30)
    )
    assert [x.value for x in window] == [2]


# ---------------------------------------------------------------------------
# InMemoryAdapter — ping
# ---------------------------------------------------------------------------


def test_ping_returns_true(memory_storage):
    """In-memory adapter ping should always return True."""
    assert memory_storage.ping() is True
