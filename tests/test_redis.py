# tests/test_redis.py
"""
Comprehensive Redis adapter tests.

Requires a running Redis instance:
    docker compose up -d

Tests are automatically skipped if Redis is unreachable.
Run with:
    pytest tests/test_redis.py -v
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import pytest

from engram.models import ConsistencyLevel, HistoryEntry, MemoryEntry, MemoryStatus, WriteType
from engram.storage.redis_adapter import RedisAdapter

# ---------------------------------------------------------------------------
# Module-scoped fixture — one adapter for the whole file
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def adapter():
    r = RedisAdapter()
    if not r.ping():
        pytest.skip("Redis is not running — start with: docker compose up -d")
    return r


@pytest.fixture(autouse=True)
def flush_test_keys(adapter):
    """Wipe all engram:* keys before AND after every test for isolation."""
    for key in adapter._client.keys("engram:*"):
        adapter._client.delete(key)
    yield
    for key in adapter._client.keys("engram:*"):
        adapter._client.delete(key)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def mem(
    key="budget",
    value: Any = 5000,
    agent="agent-A",
    role="writer",
    clock=None,
    status=MemoryStatus.OK,
) -> MemoryEntry:
    return MemoryEntry(
        key=key,
        value=value,
        agent_id=agent,
        role=role,
        vector_clock=clock or {"agent-A": 1},
        status=status,
        consistency_level=ConsistencyLevel.EVENTUAL,
    )



def hist(
    key="budget",
    value: Any = 5000,
    agent="agent-A",
    role="writer",
    clock=None,
    write_type=WriteType.WRITE,
    rollback_of=None,
    timestamp=None,
) -> HistoryEntry:
    return HistoryEntry(
        write_id=str(uuid4()),
        key=key,
        value=value,
        agent_id=agent,
        role=role,
        vector_clock=clock or {"agent-A": 1},
        write_type=write_type,
        rollback_of=rollback_of,
        timestamp=timestamp or datetime.now(timezone.utc),
    )


# ===========================================================================
# SECTION 1 — Health / connectivity
# ===========================================================================

class TestPing:
    def test_ping_returns_true_when_connected(self, adapter):
        assert adapter.ping() is True

    def test_ping_returns_false_when_unreachable(self, monkeypatch):
        """If the client ping fails, adapter.ping() should return False, not raise."""
        bad = RedisAdapter()

        def _raise_ping_error(*args, **kwargs):
            raise RuntimeError("Redis is unreachable")

        monkeypatch.setattr(bad._client, "ping", _raise_ping_error)
        assert bad.ping() is False


# ===========================================================================
# SECTION 2 — Live memory: write / read
# ===========================================================================

class TestWriteRead:
    def test_write_and_read_roundtrip(self, adapter):
        entry = mem()
        adapter.write(entry)
        result = adapter.read("budget")
        assert result is not None
        assert result.key == "budget"
        assert result.value == 5000
        assert result.agent_id == "agent-A"

    def test_read_missing_key_returns_none(self, adapter):
        assert adapter.read("does-not-exist") is None

    def test_write_overwrites_existing_value(self, adapter):
        adapter.write(mem(value=5000))
        adapter.write(mem(value=9999))
        assert adapter.read("budget").value == 9999

    def test_write_preserves_full_model_fields(self, adapter):
        """All MemoryEntry fields survive the JSON round-trip."""
        entry = mem(
            key="flights",
            value={"origin": "SFO", "destination": "JFK"},
            agent="flight-agent",
            role="flight-writer",
            clock={"flight-agent": 3},
            status=MemoryStatus.CONFLICTED,
        )
        adapter.write(entry)
        result = adapter.read("flights")
        assert result.value == {"origin": "SFO", "destination": "JFK"}
        assert result.role == "flight-writer"
        assert result.vector_clock == {"flight-agent": 3}
        assert result.status == MemoryStatus.CONFLICTED

    def test_write_complex_nested_value(self, adapter):
        """Values can be deeply nested dicts/lists."""
        value = {
            "flights": [{"id": 1, "price": 300}, {"id": 2, "price": 450}],
            "meta": {"searched_at": "2025-01-01"},
        }
        adapter.write(mem(key="search-results", value=value))
        result = adapter.read("search-results")
        assert result.value["flights"][1]["price"] == 450

    def test_write_null_value(self, adapter):
        adapter.write(mem(value=None))
        result = adapter.read("budget")
        assert result is not None
        assert result.value is None

    def test_write_boolean_value(self, adapter):
        adapter.write(mem(value=False))
        result = adapter.read("budget")
        assert result.value is False

    def test_multiple_independent_keys_do_not_interfere(self, adapter):
        adapter.write(mem(key="budget", value=1000))
        adapter.write(mem(key="flights", value=2000))
        assert adapter.read("budget").value == 1000
        assert adapter.read("flights").value == 2000

    def test_key_with_dots_in_name(self, adapter):
        """Keys like 'budget.flights' must be stored and retrieved correctly."""
        adapter.write(mem(key="budget.flights", value=750))
        assert adapter.read("budget.flights").value == 750

    def test_key_with_colons_in_name(self, adapter):
        """Keys with colons must not corrupt the Redis key namespace."""
        adapter.write(mem(key="agent:budget", value=42))
        assert adapter.read("agent:budget").value == 42


# ===========================================================================
# SECTION 3 — Live memory: delete
# ===========================================================================

class TestDelete:
    def test_delete_removes_key(self, adapter):
        adapter.write(mem())
        adapter.delete("budget")
        assert adapter.read("budget") is None

    def test_delete_nonexistent_key_does_not_raise(self, adapter):
        adapter.delete("never-existed")   # must not raise

    def test_delete_only_removes_target_key(self, adapter):
        adapter.write(mem(key="budget", value=1000))
        adapter.write(mem(key="flights", value=2000))
        adapter.delete("budget")
        assert adapter.read("budget") is None
        assert adapter.read("flights").value == 2000   # untouched

    def test_write_after_delete_succeeds(self, adapter):
        adapter.write(mem(value=5000))
        adapter.delete("budget")
        adapter.write(mem(value=3000))
        assert adapter.read("budget").value == 3000


# ===========================================================================
# SECTION 4 — Live memory: list_keys
# ===========================================================================

class TestListKeys:
    def test_list_keys_returns_all_written_keys(self, adapter):
        adapter.write(mem("alpha"))
        adapter.write(mem("beta"))
        adapter.write(mem("gamma"))
        keys = adapter.list_keys()
        assert sorted(keys) == ["alpha", "beta", "gamma"]

    def test_list_keys_empty_store_returns_empty_list(self, adapter):
        assert adapter.list_keys() == []

    def test_list_keys_with_prefix_filters_correctly(self, adapter):
        adapter.write(mem("budget.flights"))
        adapter.write(mem("budget.hotels"))
        adapter.write(mem("other.key"))
        keys = adapter.list_keys(prefix="budget")
        assert "budget.flights" in keys
        assert "budget.hotels" in keys
        assert "other.key" not in keys

    def test_list_keys_with_prefix_returns_empty_when_no_match(self, adapter):
        adapter.write(mem("flights"))
        assert adapter.list_keys(prefix="budget") == []

    def test_list_keys_without_prefix_returns_all(self, adapter):
        for k in ("a", "b.x", "b.y", "c"):
            adapter.write(mem(key=k))
        assert len(adapter.list_keys()) == 4

    def test_list_keys_returns_logical_keys_not_redis_keys(self, adapter):
        """Results must NOT include the 'engram:memory:' namespace prefix."""
        adapter.write(mem("budget"))
        keys = adapter.list_keys()
        for k in keys:
            assert not k.startswith("engram:"), f"Namespace leaked into key: {k!r}"

    def test_list_keys_deleted_key_not_returned(self, adapter):
        adapter.write(mem("budget"))
        adapter.write(mem("flights"))
        adapter.delete("budget")
        assert "budget" not in adapter.list_keys()
        assert "flights" in adapter.list_keys()

    def test_list_keys_result_is_sorted(self, adapter):
        for k in ("zebra", "apple", "mango"):
            adapter.write(mem(key=k))
        keys = adapter.list_keys()
        assert keys == sorted(keys)


# ===========================================================================
# SECTION 5 — History: write_history / read_history
# ===========================================================================

class TestWriteHistory:
    def test_write_history_and_read_back(self, adapter):
        entry = hist()
        adapter.write_history(entry)
        results = adapter.read_history("budget")
        assert len(results) == 1
        assert results[0].write_id == entry.write_id

    def test_history_preserves_all_fields(self, adapter):
        entry = hist(
            key="flights",
            value={"price": 300},
            agent="flight-agent",
            role="flight-writer",
            clock={"flight-agent": 5},
            write_type=WriteType.ROLLBACK,
        )
        adapter.write_history(entry)
        result = adapter.read_history("flights")[0]
        assert result.value == {"price": 300}
        assert result.agent_id == "flight-agent"
        assert result.vector_clock == {"flight-agent": 5}
        assert result.write_type == WriteType.ROLLBACK

    def test_history_is_append_only(self, adapter):
        """Multiple writes to the same key accumulate — they don't overwrite."""
        e1 = hist(value=1000)
        e2 = hist(value=2000)
        e3 = hist(value=3000)
        for e in (e1, e2, e3):
            adapter.write_history(e)
        results = adapter.read_history("budget")
        assert len(results) == 3

    def test_history_is_oldest_first(self, adapter):
        """RPUSH order must be preserved — oldest entry is at index 0."""
        now = datetime.now(timezone.utc)
        e1 = hist(value=1, timestamp=now - timedelta(seconds=20))
        e2 = hist(value=2, timestamp=now - timedelta(seconds=10))
        e3 = hist(value=3, timestamp=now)
        for e in (e1, e2, e3):
            adapter.write_history(e)
        results = adapter.read_history("budget")
        assert [r.value for r in results] == [1, 2, 3]

    def test_history_keys_are_isolated_per_key(self, adapter):
        """History for 'budget' must not bleed into history for 'flights'."""
        adapter.write_history(hist(key="budget", value=5000))
        adapter.write_history(hist(key="flights", value=300))
        assert len(adapter.read_history("budget")) == 1
        assert adapter.read_history("budget")[0].value == 5000
        assert len(adapter.read_history("flights")) == 1

    def test_read_history_empty_key_returns_empty_list(self, adapter):
        assert adapter.read_history("no-such-key") == []


class TestReadHistoryFilters:
    def test_filter_by_agent_id(self, adapter):
        adapter.write_history(hist(agent="agent-A"))
        adapter.write_history(hist(agent="agent-B"))
        adapter.write_history(hist(agent="agent-A"))
        results = adapter.read_history("budget", agent_id="agent-A")
        assert len(results) == 2
        assert all(r.agent_id == "agent-A" for r in results)

    def test_filter_by_agent_id_no_match_returns_empty(self, adapter):
        adapter.write_history(hist(agent="agent-A"))
        assert adapter.read_history("budget", agent_id="agent-Z") == []

    def test_filter_since_excludes_older_entries(self, adapter):
        now = datetime.now(timezone.utc)
        old   = hist(value=100, timestamp=now - timedelta(hours=3))
        mid   = hist(value=200, timestamp=now - timedelta(hours=1))
        recent = hist(value=300, timestamp=now)
        for e in (old, mid, recent):
            adapter.write_history(e)
        results = adapter.read_history("budget", since=now - timedelta(hours=2))
        values = [r.value for r in results]
        assert 100 not in values
        assert 200 in values
        assert 300 in values

    def test_filter_until_excludes_newer_entries(self, adapter):
        now = datetime.now(timezone.utc)
        old    = hist(value=100, timestamp=now - timedelta(hours=3))
        recent = hist(value=300, timestamp=now)
        for e in (old, recent):
            adapter.write_history(e)
        results = adapter.read_history("budget", until=now - timedelta(hours=1))
        values = [r.value for r in results]
        assert 100 in values
        assert 300 not in values

    def test_filter_since_and_until_together(self, adapter):
        now = datetime.now(timezone.utc)
        entries = [
            hist(value=i, timestamp=now - timedelta(hours=4 - i))
            for i in range(5)   # timestamps: -4h, -3h, -2h, -1h, now
        ]
        for e in entries:
            adapter.write_history(e)
        results = adapter.read_history(
            "budget",
            since=now - timedelta(hours=3, minutes=30),
            until=now - timedelta(minutes=30),
        )
        values = [r.value for r in results]
        # Only values 1, 2, 3 fall within the window
        assert 0 not in values   # too old
        assert 4 not in values   # too recent
        assert values == [1, 2, 3]

    def test_filter_by_agent_id_and_since_combined(self, adapter):
        now = datetime.now(timezone.utc)
        adapter.write_history(hist(agent="agent-A", value=1, timestamp=now - timedelta(hours=2)))
        adapter.write_history(hist(agent="agent-A", value=2, timestamp=now))
        adapter.write_history(hist(agent="agent-B", value=3, timestamp=now))
        results = adapter.read_history(
            "budget",
            agent_id="agent-A",
            since=now - timedelta(hours=1),
        )
        assert len(results) == 1
        assert results[0].value == 2

    def test_rollback_entries_stored_and_retrieved_correctly(self, adapter):
        original_id = str(uuid4())
        rollback = hist(
            value=5000,
            write_type=WriteType.ROLLBACK,
            rollback_of=original_id,
        )
        adapter.write_history(rollback)
        results = adapter.read_history("budget")
        assert len(results) == 1
        assert results[0].write_type == WriteType.ROLLBACK
        assert results[0].rollback_of == original_id


# ===========================================================================
# SECTION 6 — Data integrity & Redis key namespace
# ===========================================================================

class TestDataIntegrity:
    def test_memory_and_history_keys_are_separate_namespaces(self, adapter):
        """
        Writing live data must not pollute the history namespace and vice versa.
        """
        adapter.write(mem(key="budget", value=5000))
        adapter.write_history(hist(key="budget", value=9999))
        # Live read should return the MemoryEntry, not the HistoryEntry
        live = adapter.read("budget")
        assert live.value == 5000
        # History should return the HistoryEntry
        history = adapter.read_history("budget")
        assert history[0].value == 9999

    def test_write_history_does_not_affect_live_read(self, adapter):
        adapter.write_history(hist(value=7777))
        assert adapter.read("budget") is None   # history write ≠ live write

    def test_delete_removes_live_entry_not_history(self, adapter):
        adapter.write(mem(value=5000))
        adapter.write_history(hist(value=5000))
        adapter.delete("budget")
        assert adapter.read("budget") is None                  # live gone
        assert len(adapter.read_history("budget")) == 1        # history intact

    def test_list_keys_does_not_include_history_keys(self, adapter):
        """list_keys() must only return live memory keys, not history keys."""
        adapter.write_history(hist(key="budget"))   # history only — no live entry
        keys = adapter.list_keys()
        assert "budget" not in keys

    def test_overwrite_does_not_corrupt_history(self, adapter):
        """
        Overwriting a live key must not touch the history list for that key.
        """
        e1 = hist(value=1000)
        e2 = hist(value=2000)
        adapter.write_history(e1)
        adapter.write(mem(value=9999))     # overwrite live entry
        adapter.write_history(e2)
        history = adapter.read_history("budget")
        assert len(history) == 2
        assert [r.value for r in history] == [1000, 2000]

    def test_vector_clock_survives_roundtrip(self, adapter):
        clock = {"agent-A": 3, "agent-B": 7, "agent-C": 1}
        adapter.write(mem(clock=clock))
        result = adapter.read("budget")
        assert result.vector_clock == clock

    def test_many_history_entries_all_retrieved(self, adapter):
        """Bulk insert 50 history entries and verify all 50 come back."""
        entries = [hist(value=i) for i in range(50)]
        for e in entries:
            adapter.write_history(e)
        results = adapter.read_history("budget")
        assert len(results) == 50
        assert [r.value for r in results] == list(range(50))