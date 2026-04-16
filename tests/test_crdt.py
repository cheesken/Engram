"""
Tests for engram.crdt.MVRegister.

Covers: write, merge, resolve, is_conflicted, values.
"""

from engram.crdt import MVRegister
from engram.models import ConflictStrategy
from engram.vector_clock import VectorClock


# ---------------------------------------------------------------------------
# write
# ---------------------------------------------------------------------------


def test_write_to_empty_register():
    """Writing to an empty register should store exactly one value."""
    reg = MVRegister()
    vc = VectorClock({"A": 1})
    reg2 = reg.write("hello", "agent-A", "admin", vc)
    assert len(reg2.values) == 1
    assert reg2.values[0].value == "hello"
    assert len(reg.values) == 0  # original not mutated


def test_write_supersedes_when_after():
    """A write with a strictly later clock should replace all existing values."""
    pass


def test_write_concurrent_creates_conflict():
    """Two writes with concurrent clocks should both be stored."""
    pass


def test_write_stale_is_discarded():
    """A write with a clock BEFORE existing values should be discarded."""
    pass


def test_write_does_not_mutate_original():
    """The original MVRegister must remain unchanged after write."""
    pass


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------


def test_merge_two_diverged_registers():
    """Merging two registers with concurrent values should keep both."""
    pass


def test_merge_dominated_values_removed():
    """Values dominated by a newer value in the other register should be dropped."""
    pass


# ---------------------------------------------------------------------------
# resolve
# ---------------------------------------------------------------------------


def test_resolve_single_value_returns_it():
    """If only one value exists, resolve should return it regardless of strategy."""
    pass


def test_resolve_latest_clock():
    """LATEST_CLOCK should pick the value with the highest clock sum."""
    pass


def test_resolve_lowest_value():
    """LOWEST_VALUE should pick the numerically smallest value."""
    pass


def test_resolve_highest_value():
    """HIGHEST_VALUE should pick the numerically largest value."""
    pass


def test_resolve_union():
    """UNION should return a list of all values with no conflicts."""
    pass


def test_resolve_flag_for_human():
    """FLAG_FOR_HUMAN should return None and list all values as conflicts."""
    pass


# ---------------------------------------------------------------------------
# is_conflicted
# ---------------------------------------------------------------------------


def test_is_conflicted_with_single_value():
    """A register with one value should not be conflicted."""
    pass


def test_is_conflicted_with_concurrent_writes():
    """A register with concurrent writes should be conflicted."""
    pass
