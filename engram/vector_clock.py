"""
Vector clock implementation for causal ordering of writes.

A vector clock is a dict mapping agent IDs to monotonically increasing counters.
By comparing two vector clocks, we can determine if one write causally precedes
another, or if they are concurrent (a conflict).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from engram.models import Ordering


@dataclass(frozen=True)
class VectorClock:
    """
    Immutable vector clock.

    All mutation methods return a new VectorClock instance.
    The underlying dict is never modified after construction.
    """

    clock: dict[str, int] = field(default_factory=dict)

    def increment(self, agent_id: str) -> VectorClock:
        """
        Return a NEW VectorClock with agent_id's counter incremented by 1.

        Must NOT mutate self. If agent_id is not in the clock, treat its
        current value as 0.

        Example:
            VectorClock({"A": 1}).increment("A") -> VectorClock({"A": 2})
            VectorClock({"A": 1}).increment("B") -> VectorClock({"A": 1, "B": 1})

        Args:
            agent_id: The agent whose counter should be incremented.

        Returns:
            A new VectorClock with the updated counter.
        """
        raise NotImplementedError

    def merge(self, other: VectorClock) -> VectorClock:
        """
        Return a NEW VectorClock that is the component-wise maximum of self and other.

        For each agent_id that appears in either clock, the result contains
        max(self.clock.get(id, 0), other.clock.get(id, 0)).

        Must NOT mutate self or other.

        Example:
            merge({"A": 1, "B": 2}, {"A": 3, "C": 1}) -> {"A": 3, "B": 2, "C": 1}

        Args:
            other: The VectorClock to merge with.

        Returns:
            A new VectorClock representing the merged state.
        """
        raise NotImplementedError

    def compare(self, other: VectorClock) -> Ordering:
        """
        Determine the causal relationship between self and other.

        Rules:
        - EQUAL: self.clock == other.clock (identical counters for all agents).
        - BEFORE: every counter in self is <= the corresponding counter in other,
                  AND at least one counter in self is strictly < other.
                  Meaning: self happened causally before other.
        - AFTER: every counter in other is <= self, AND at least one is strictly <.
                 Meaning: self happened causally after other.
        - CONCURRENT: neither clock dominates the other.
                      Meaning: these writes happened without knowledge of each other.
                      This is a conflict.

        Edge cases:
        - An agent present in one clock but not the other is treated as 0
          in the clock where it is absent.
        - Two empty clocks are EQUAL.
        - VectorClock({"A": 1}) vs VectorClock({"B": 1}) is CONCURRENT.

        Args:
            other: The VectorClock to compare against.

        Returns:
            An Ordering enum value describing the causal relationship.
        """
        raise NotImplementedError

    def to_dict(self) -> dict[str, int]:
        """
        Return a plain dict copy of the clock.

        Returns:
            A new dict with the same agent_id -> counter mappings.
        """
        raise NotImplementedError

    @classmethod
    def from_dict(cls, d: dict[str, int]) -> VectorClock:
        """
        Construct a VectorClock from a plain dict.

        Args:
            d: A dict mapping agent IDs to integer counters.

        Returns:
            A new VectorClock instance.
        """
        raise NotImplementedError
