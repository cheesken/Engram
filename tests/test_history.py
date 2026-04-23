"""
Tests for engram.history.HistoryLog.

Covers: append, get_history, get_entry, get_snapshot, create_rollback_entry.
"""

from datetime import datetime, timezone

import pytest

from engram.history import HistoryLog
from engram.models import HistoryEntry, WriteType


# ---------------------------------------------------------------------------
# helpers — reusable entry builders
# ---------------------------------------------------------------------------

def make_entry(key="budget", value=1000, agent_id="agent-A",
               clock=None, ts=None):
    """Build a HistoryEntry with sensible defaults."""
    return HistoryEntry(
        key=key,
        value=value,
        agent_id=agent_id,
        role="admin",
        vector_clock=clock or {"agent-A": 1},
        timestamp=ts or datetime.now(timezone.utc),
    )


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
    result = history_log.get_entry("this-id-does-not-exist")
    assert result is None


# ---------------------------------------------------------------------------
# get_history
# ---------------------------------------------------------------------------


def test_get_history_returns_chronological_order():
    """Entries should be returned oldest-first."""
    log = HistoryLog()

    # make two entries with explicit timestamps so order is guaranteed
    old = make_entry(
        value=1000,
        ts=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    )
    new = make_entry(
        value=2000,
        ts=datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
    )

    # append in order — log preserves insertion order
    log.append(old)
    log.append(new)

    results = log.get_history("budget")
    assert len(results) == 2
    assert results[0].value == 1000   # old came first
    assert results[1].value == 2000   # new came second


def test_get_history_filters_by_agent_id():
    """Only entries from the specified agent should be returned."""
    log = HistoryLog()

    entry_a = make_entry(agent_id="agent-A", value=100)
    entry_b = make_entry(agent_id="agent-B", value=200)

    log.append(entry_a)
    log.append(entry_b)

    results = log.get_history("budget", agent_id="agent-A")
    assert len(results) == 1
    assert results[0].agent_id == "agent-A"
    assert results[0].value == 100


def test_get_history_filters_by_since():
    """Only entries with timestamp >= since should be returned."""
    log = HistoryLog()

    early = make_entry(
        value=111,
        ts=datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
    )
    late = make_entry(
        value=222,
        ts=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    )

    log.append(early)
    log.append(late)

    cutoff = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    results = log.get_history("budget", since=cutoff)

    assert len(results) == 1
    assert results[0].value == 222   # only the late entry qualifies


def test_get_history_filters_by_until():
    """Only entries with timestamp <= until should be returned."""
    log = HistoryLog()

    early = make_entry(
        value=111,
        ts=datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
    )
    late = make_entry(
        value=222,
        ts=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    )

    log.append(early)
    log.append(late)

    cutoff = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    results = log.get_history("budget", until=cutoff)

    assert len(results) == 1
    assert results[0].value == 111   # only the early entry qualifies


def test_get_history_empty_for_unknown_key(history_log):
    """Should return empty list for a key with no history."""
    result = history_log.get_history("key-that-was-never-written")
    assert result == []


# ---------------------------------------------------------------------------
# get_snapshot
# ---------------------------------------------------------------------------


def test_get_snapshot_returns_most_recent_before():
    """Should return the entry with the latest timestamp causally before at_clock."""
    log = HistoryLog()

    # write 1: agent-A's first write — clock {"agent-A": 1}
    entry_v1 = make_entry(
        value=100,
        clock={"agent-A": 1},
        ts=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    )
    # write 2: agent-A's second write — clock {"agent-A": 2}
    entry_v2 = make_entry(
        value=200,
        clock={"agent-A": 2},
        ts=datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
    )

    log.append(entry_v1)
    log.append(entry_v2)

    # ask: what was budget at clock {"agent-A": 2}?
    # both v1 (clock 1) and v2 (clock 2) are BEFORE or EQUAL to {"agent-A": 2}
    # v2 has the latest timestamp so it wins
    result = log.get_snapshot("budget", at_clock={"agent-A": 2})
    assert result is not None
    assert result.value == 200


def test_get_snapshot_excludes_concurrent():
    """Concurrent entries should not be returned by get_snapshot."""
    log = HistoryLog()

    # agent-A wrote with clock {"agent-A": 1}
    # agent-B wrote with clock {"agent-B": 1}
    # these are CONCURRENT — neither knew about the other
    entry_a = make_entry(
        agent_id="agent-A",
        value=999,
        clock={"agent-A": 1},
    )
    log.append(entry_a)

    # now ask for snapshot at {"agent-B": 1}
    # entry_a's clock {"agent-A": 1} vs target {"agent-B": 1}
    # → CONCURRENT (each wins a different lane) → excluded
    result = log.get_snapshot("budget", at_clock={"agent-B": 1})
    assert result is None


def test_get_snapshot_returns_none_when_no_entries_qualify():
    """Should return None if no entries are before or equal to at_clock."""
    log = HistoryLog()

    # write at clock {"agent-A": 5} — this is AFTER the snapshot point
    entry = make_entry(
        clock={"agent-A": 5},
        ts=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    )
    log.append(entry)

    # ask for snapshot at an earlier clock {"agent-A": 2}
    # entry's clock {"agent-A": 5} is AFTER {"agent-A": 2} → excluded
    result = log.get_snapshot("budget", at_clock={"agent-A": 2})
    assert result is None


# ---------------------------------------------------------------------------
# create_rollback_entry
# ---------------------------------------------------------------------------


def test_create_rollback_entry_creates_new_entry():
    """Should create a new HistoryEntry with write_type=ROLLBACK."""
    log = HistoryLog()

    original = make_entry(value=5000, clock={"agent-A": 1})
    log.append(original)

    rollback = log.create_rollback_entry(
        write_id=original.write_id,
        initiating_agent_id="agent-B",
        initiating_role="admin",
    )

    # it's a brand new entry — different write_id
    assert rollback.write_id != original.write_id

    # but restores the original value and key
    assert rollback.key == original.key
    assert rollback.value == original.value

    # stamped correctly
    assert rollback.write_type == WriteType.ROLLBACK
    assert rollback.rollback_of == original.write_id
    assert rollback.agent_id == "agent-B"

    # NOT appended yet — log still only has the original
    assert len(log._log) == 1


def test_create_rollback_entry_raises_for_unknown_write_id(history_log):
    """Should raise ValueError if the write_id is not found."""
    with pytest.raises(ValueError):
        history_log.create_rollback_entry(
            write_id="ghost-id-that-does-not-exist",
            initiating_agent_id="agent-A",
            initiating_role="admin",
        )