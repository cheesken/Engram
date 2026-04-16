"""
Tests for engram.vector_clock.VectorClock.

Covers: increment, merge, compare, to_dict, from_dict.
"""

from engram.models import Ordering
from engram.vector_clock import VectorClock


# ---------------------------------------------------------------------------
# increment
# ---------------------------------------------------------------------------


def test_increment_creates_new_clock():
    """Incrementing a new agent on an empty clock should produce {agent: 1}."""
    vc = VectorClock()
    vc2 = vc.increment("agent-A")
    assert vc2.clock["agent-A"] == 1
    assert vc.clock == {}  # original not mutated


def test_increment_existing_agent():
    """Should increment existing agent counter from 1 to 2."""
    pass


def test_increment_preserves_other_agents():
    """Incrementing agent-B should not change agent-A's counter."""
    pass


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------


def test_merge_takes_max_of_each_agent():
    """Should return component-wise max across both clocks."""
    pass


def test_merge_does_not_mutate_originals():
    """Neither self nor other should be modified after merge."""
    pass


def test_merge_with_empty_clock():
    """Merging with an empty clock should return a copy of the non-empty clock."""
    pass


# ---------------------------------------------------------------------------
# compare
# ---------------------------------------------------------------------------


def test_compare_equal_clocks():
    """Two identical clocks should return EQUAL."""
    pass


def test_compare_before():
    """A clock with strictly lower counters should return BEFORE."""
    pass


def test_compare_after():
    """A clock with strictly higher counters should return AFTER."""
    pass


def test_compare_concurrent():
    """Clocks where neither dominates should return CONCURRENT."""
    pass


def test_compare_two_empty_clocks():
    """Two empty clocks should be EQUAL."""
    pass


def test_compare_disjoint_agents_is_concurrent():
    """VectorClock({'A':1}) vs VectorClock({'B':1}) should be CONCURRENT."""
    pass


# ---------------------------------------------------------------------------
# to_dict / from_dict
# ---------------------------------------------------------------------------


def test_to_dict_returns_copy():
    """to_dict should return a plain dict copy, not the internal reference."""
    pass


def test_from_dict_roundtrip():
    """from_dict(vc.to_dict()) should produce an equivalent VectorClock."""
    pass
