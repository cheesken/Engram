"""
Engram demo script — five key moments.

Run with:
    python demo/run_demo.py

Requires Engram API to be running at http://localhost:8000.
Start it with:
    uvicorn engram.api:app --reload
"""

from __future__ import annotations

ENGRAM_URL = "http://localhost:8000"


def moment_1_conflict_without_engram() -> None:
    """
    Moment 1: What happens WITHOUT Engram.

    Demonstrate two agents writing to the same key without conflict detection.
    In a naive shared dict, the last write wins silently — data is lost.

    This section prints a simulation of the problem (no API calls needed).
    """
    print("=" * 60)
    print("MOMENT 1: Conflict WITHOUT Engram")
    print("=" * 60)
    print("TODO: implement moment 1")
    print("  - Simulate two agents writing to a plain shared dict")
    print("  - Show how the second write silently overwrites the first")
    print("  - Highlight the data loss problem")
    print()


def moment_2_conflict_with_engram() -> None:
    """
    Moment 2: The same conflict WITH Engram.

    Demonstrate two agents writing concurrent values to the same key.
    Engram detects the conflict via vector clocks, stores both values
    in the MVRegister, and resolves using the configured strategy.

    Steps:
    - Register roles via POST /roles
    - Agent A writes budget = 5000 with clock {"A": 1}
    - Agent B writes budget = 3000 with clock {"B": 1} (concurrent!)
    - Show that Engram detected the conflict
    - Show the resolved value based on the conflict strategy
    """
    print("=" * 60)
    print("MOMENT 2: Conflict WITH Engram (CRDT + Vector Clocks)")
    print("=" * 60)
    print("TODO: implement moment 2")
    print("  - Register agent roles")
    print("  - Have two agents write concurrently to 'budget'")
    print("  - Show conflict detection and resolution")
    print()


def moment_3_consistency_levels() -> None:
    """
    Moment 3: Consistency levels.

    Demonstrate the difference between EVENTUAL, CAUSAL, and STRONG reads.

    Steps:
    - Write a value with EVENTUAL consistency
    - Read it back with EVENTUAL (should work)
    - Attempt CAUSAL read (should raise NotImplementedError for now)
    - Attempt STRONG read (should raise NotImplementedError for now)
    """
    print("=" * 60)
    print("MOMENT 3: Consistency Levels")
    print("=" * 60)
    print("TODO: implement moment 3")
    print("  - Write with EVENTUAL consistency")
    print("  - Read with different consistency levels")
    print("  - Show the behavior differences")
    print()


def moment_4_access_violation() -> None:
    """
    Moment 4: Access control enforcement.

    Demonstrate that a read-only agent (summarizer) cannot write to memory.

    Steps:
    - Register summarizer as read-only role
    - Summarizer reads successfully
    - Summarizer attempts to write -> 403 Forbidden
    """
    print("=" * 60)
    print("MOMENT 4: Access Control Violation")
    print("=" * 60)
    print("TODO: implement moment 4")
    print("  - Register summarizer with read-only permissions")
    print("  - Show successful read")
    print("  - Show blocked write (HTTP 403)")
    print()


def moment_5_rollback() -> None:
    """
    Moment 5: Time-travel rollback.

    Demonstrate rolling back to a previous write using the history log.

    Steps:
    - Write budget = 5000
    - Write budget = 9999 (accidental overwrite)
    - Get history, find the write_id of the 5000 entry
    - POST /rollback/{write_id} to restore budget = 5000
    - Verify the rollback in history (new entry with write_type=ROLLBACK)
    """
    print("=" * 60)
    print("MOMENT 5: Rollback / Time-Travel")
    print("=" * 60)
    print("TODO: implement moment 5")
    print("  - Write initial budget value")
    print("  - Overwrite with a bad value")
    print("  - Roll back to the original")
    print("  - Verify via history that the rollback is recorded")
    print()


def main() -> None:
    """Run all five demo moments in sequence."""
    print()
    print("ENGRAM DEMO — Memory Middleware for Multi-Agent AI Systems")
    print("=" * 60)
    print()

    moment_1_conflict_without_engram()
    moment_2_conflict_with_engram()
    moment_3_consistency_levels()
    moment_4_access_violation()
    moment_5_rollback()

    print("=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
