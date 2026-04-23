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
        new_clock = dict(self.clock)             # copy so we never touch self
        new_clock[agent_id] = new_clock.get(agent_id, 0) + 1
        return VectorClock(new_clock)

    def merge(self, other: VectorClock) -> VectorClock:
        all_agents = set(self.clock) | set(other.clock)   # every agent from both
        new_clock = {
            agent: max(self.clock.get(agent, 0), other.clock.get(agent, 0))
            for agent in all_agents
        }
        return VectorClock(new_clock)

    def compare(self, other: VectorClock) -> Ordering:
        all_agents = set(self.clock) | set(other.clock)

        self_less = False    # True if self has at least one counter LESS than other
        other_less = False   # True if other has at least one counter LESS than self

        for agent in all_agents:
            s = self.clock.get(agent, 0)
            o = other.clock.get(agent, 0)

            if s < o:
                self_less = True
            elif s > o:
                other_less = True

        if not self_less and not other_less:
            return Ordering.EQUAL        # every lane is identical
        elif self_less and not other_less:
            return Ordering.BEFORE       # self is strictly older in at least one lane
        elif other_less and not self_less:
            return Ordering.AFTER        # self is strictly newer in at least one lane
        else:
            return Ordering.CONCURRENT   # both have lanes the other doesn't know about

    def to_dict(self) -> dict[str, int]:
        return dict(self.clock)          # copy, never expose the internal dict directly

    @classmethod
    def from_dict(cls, d: dict[str, int]) -> VectorClock:
        return cls(dict(d))              # copy on the way in too