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
    vc = VectorClock({"agent-A": 1})
    vc2 = vc.increment("agent-A")
    assert vc2.clock["agent-A"] == 2
    # original still at 1, not touched
    assert vc.clock["agent-A"] == 1


def test_increment_preserves_other_agents():
    """Incrementing agent-B should not change agent-A's counter."""
    vc = VectorClock({"agent-A": 3, "agent-B": 1})
    vc2 = vc.increment("agent-B")
    assert vc2.clock["agent-B"] == 2   # B went up
    assert vc2.clock["agent-A"] == 3   # A untouched


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------


def test_merge_takes_max_of_each_agent():
    """Should return component-wise max across both clocks."""
    a = VectorClock({"Bus": 3, "Truck": 1})
    b = VectorClock({"Bus": 1, "Truck": 4, "Van": 2})
    merged = a.merge(b)
    assert merged.clock["Bus"]   == 3   # 3 beats 1
    assert merged.clock["Truck"] == 4   # 4 beats 1
    assert merged.clock["Van"]   == 2   # only in b, still included


def test_merge_does_not_mutate_originals():
    """Neither self nor other should be modified after merge."""
    a = VectorClock({"Bus": 1})
    b = VectorClock({"Truck": 5})
    _ = a.merge(b)
    assert a.clock == {"Bus": 1}      # a unchanged
    assert b.clock == {"Truck": 5}    # b unchanged


def test_merge_with_empty_clock():
    """Merging with an empty clock should return a copy of the non-empty clock."""
    a = VectorClock({"Bus": 2, "Truck": 1})
    empty = VectorClock()
    merged = a.merge(empty)
    assert merged.clock == {"Bus": 2, "Truck": 1}


# ---------------------------------------------------------------------------
# compare
# ---------------------------------------------------------------------------


def test_compare_equal_clocks():
    """Two identical clocks should return EQUAL."""
    a = VectorClock({"Bus": 2, "Truck": 1})
    b = VectorClock({"Bus": 2, "Truck": 1})
    assert a.compare(b) == Ordering.EQUAL


def test_compare_before():
    """A clock with strictly lower counters should return BEFORE."""
    # a is the older write — every lane is less than or equal to b
    # and at least one is strictly less
    a = VectorClock({"Bus": 1, "Truck": 1})
    b = VectorClock({"Bus": 2, "Truck": 1})
    assert a.compare(b) == Ordering.BEFORE


def test_compare_after():
    """A clock with strictly higher counters should return AFTER."""
    # a is the newer write — it wins every lane
    a = VectorClock({"Bus": 3, "Truck": 2})
    b = VectorClock({"Bus": 1, "Truck": 2})
    assert a.compare(b) == Ordering.AFTER


def test_compare_concurrent():
    """Clocks where neither dominates should return CONCURRENT."""
    # Bus: a wins (2 > 1). Truck: b wins (3 > 1). Each wins a lane → conflict
    a = VectorClock({"Bus": 2, "Truck": 1})
    b = VectorClock({"Bus": 1, "Truck": 3})
    assert a.compare(b) == Ordering.CONCURRENT


def test_compare_two_empty_clocks():
    """Two empty clocks should be EQUAL."""
    assert VectorClock().compare(VectorClock()) == Ordering.EQUAL


def test_compare_disjoint_agents_is_concurrent():
    """VectorClock({'Bus':1}) vs VectorClock({'Truck':1}) should be CONCURRENT.

    Bus lane:   a=1, b=0  → a wins  → other_less = True
    Truck lane: a=0, b=1  → b wins  → self_less  = True
    Both flags on → CONCURRENT.
    Missing agent treated as 0, which is the key rule here.
    """
    a = VectorClock({"Bus": 1})
    b = VectorClock({"Truck": 1})
    assert a.compare(b) == Ordering.CONCURRENT


# ---------------------------------------------------------------------------
# to_dict / from_dict
# ---------------------------------------------------------------------------


def test_to_dict_returns_copy():
    """to_dict should return a plain dict copy, not the internal reference."""
    vc = VectorClock({"Bus": 2, "Truck": 1})
    d = vc.to_dict()

    # it's a real dict
    assert isinstance(d, dict)
    assert d == {"Bus": 2, "Truck": 1}

    # mutating the returned dict does not affect the clock
    d["Bus"] = 999
    assert vc.clock["Bus"] == 2  # original untouched


def test_from_dict_roundtrip():
    """from_dict(vc.to_dict()) should produce an equivalent VectorClock."""
    original = VectorClock({"Bus": 3, "Truck": 2, "Van": 1})
    restored = VectorClock.from_dict(original.to_dict())
    assert restored.clock == original.clock