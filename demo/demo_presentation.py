"""
Engram demo script — Five key moments.

An executable walkthrough of Engram's core features: conflict detection,
vector clocks, CRDTs, access control, and audit trails.

Run with:
    # Terminal 1: Start the API
    uvicorn engram.api:app --reload

    # Terminal 2: Run this script
    python demo/demo_presentation.py

Requires Engram API to be running at http://localhost:8000.
"""

import json
import time
from datetime import datetime

import httpx

ENGRAM_URL = "http://localhost:8000"
CLIENT = httpx.Client(base_url=ENGRAM_URL, timeout=10.0)


# ============================================================================
# SETUP: Register roles
# ============================================================================


def setup_roles() -> None:
    """Register roles needed for the demo."""
    print("\n[SETUP] Registering roles...")

    roles = [
        {
            "role_name": "budget-agent",
            "can_read": ["budget.*"],
            "can_write": ["budget.*"],
        },
        {
            "role_name": "summarizer",
            "can_read": ["*"],
            "can_write": [],
        },
        {"role_name": "admin", "can_read": ["*"], "can_write": ["*"]},
    ]

    for role in roles:
        try:
            response = CLIENT.post("/roles", json=role)
            if response.status_code == 200:
                print(f"  ✓ Registered role: {role['role_name']}")
            else:
                print(f"  ✗ Failed to register {role['role_name']}: {response.text}")
        except Exception as e:
            print(f"  ✗ Error registering role: {e}")


# ============================================================================
# MOMENT 0: Problem Setup
# ============================================================================


def moment_0_problem_setup() -> None:
    """Explain the problem without Engram."""
    print("\n" + "=" * 70)
    print("MOMENT 0: THE PROBLEM (Without Engram)")
    print("=" * 70)

    print("""
Imagine two AI agents managing a shared budget:
  • Agent A (NYC): Reads budget = $5000, analyzes for 5 hours
  • Agent B (Tokyo): Reads budget = $5000, analyzes in parallel

After analysis:
  • Agent A wants to write: budget = $3500
  • Agent B wants to write: budget = $4200

These writes are CONCURRENT (they don't know about each other).

In a naive shared dict or database:
""")

    # Simulate the problem
    shared_memory = {"budget": 5000}
    print(f"  Initial state: {shared_memory}")
    print()

    shared_memory["budget"] = 3500
    print(f"  Agent A writes: {shared_memory}")

    shared_memory["budget"] = 4200
    print(f"  Agent B writes: {shared_memory}")

    print()
    print("  ⚠️  PROBLEM: Agent A's write ($3500) is GONE!")
    print("  ⚠️  No error, no warning, no audit trail.")
    print("  ⚠️  THIS IS THE PROBLEM ENGRAM SOLVES.")
    print()


# ============================================================================
# MOMENT 1: Conflict Detection
# ============================================================================


def moment_1_conflict_detection() -> None:
    """Demonstrate conflict detection with Engram."""
    print("\n" + "=" * 70)
    print("MOMENT 1: CONFLICT DETECTION WITH ENGRAM")
    print("=" * 70)

    print("""
Now the same scenario WITH Engram.

Engram uses VECTOR CLOCKS to detect concurrent writes:
  • Agent A's clock: {"agent_a": 1, "agent_b": 0}  (A has written 1 time)
  • Agent B's clock: {"agent_a": 0, "agent_b": 1}  (B has written 1 time)

These clocks are CONCURRENT (neither dominates).
Engram detects this and stores BOTH values.
""")

    # Step 1: Agent A writes
    print("\n[Step 1] Agent A writes budget = $3500")
    payload_a = {
        "key": "budget",
        "value": 3500,
        "agent_id": "agent_a",
        "role": "budget-agent",
        "vector_clock": {"agent_a": 1, "agent_b": 0},
    }
    try:
        response = CLIENT.post("/write", json=payload_a)
        if response.status_code == 200:
            entry = response.json()
            print(f"  ✓ Write succeeded")
            print(f"    Status: {entry.get('status')}")
            print(f"    Value: {entry.get('value')}")
            print(f"    Vector Clock: {entry.get('vector_clock')}")
        else:
            print(f"  ✗ Write failed: {response.text}")
            return
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return

    time.sleep(0.5)

    # Step 2: Agent B writes (concurrent)
    print("\n[Step 2] Agent B writes budget = $4200 (CONCURRENT with A's write)")
    payload_b = {
        "key": "budget",
        "value": 4200,
        "agent_id": "agent_b",
        "role": "budget-agent",
        "vector_clock": {"agent_a": 0, "agent_b": 1},
    }
    try:
        response = CLIENT.post("/write", json=payload_b)
        if response.status_code == 200:
            entry = response.json()
            print(f"  ✓ Write succeeded")
            print(f"    Status: {entry.get('status')}")
            print(f"    Value: {entry.get('value')}")
            print(f"    Vector Clock: {entry.get('vector_clock')}")
            print(f"    Conflicting Writes: {len(entry.get('conflicting_writes', []))}")
        else:
            print(f"  ✗ Write failed: {response.text}")
            return
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return

    # Step 3: Read the value
    print("\n[Step 3] Read the budget value")
    try:
        response = CLIENT.get(
            "/read/budget",
            params={
                "agent_id": "agent_a",
                "role": "budget-agent",
                "consistency_level": "eventual",
            },
        )
        if response.status_code == 200:
            entry = response.json()
            print(f"  ✓ Read succeeded")
            print(f"    Status: {entry.get('status')}")
            print(f"    Resolved Value: {entry.get('value')}")
            print(f"    Conflicting Writes: {entry.get('conflicting_writes')}")
            print()
            print("  ✓ KEY INSIGHT: Both values are stored!")
            print("    Engram detected the conflict and kept both.")
            print("    Nothing is lost.")
        else:
            print(f"  ✗ Read failed: {response.text}")
    except Exception as e:
        print(f"  ✗ Error: {e}")


# ============================================================================
# MOMENT 2: History & Time-Travel
# ============================================================================


def moment_2_history_and_time_travel() -> None:
    """Demonstrate audit trail and time-travel queries."""
    print("\n" + "=" * 70)
    print("MOMENT 2: HISTORY & TIME-TRAVEL QUERIES")
    print("=" * 70)

    print("""
Engram maintains an immutable audit trail of every write.
You can query: "What was this key's value at point in causal time X?"
""")

    # Step 1: Get full history
    print("[Step 1] Get the complete history for 'budget'")
    try:
        response = CLIENT.get("/history/budget")
        if response.status_code == 200:
            entries = response.json()
            print(f"  ✓ Found {len(entries)} history entries:")
            for i, entry in enumerate(entries, 1):
                print(f"    {i}. Agent: {entry['agent_id']}, Value: {entry['value']}, Clock: {entry['vector_clock']}")
        else:
            print(f"  ✗ Request failed: {response.text}")
            return
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return

    # Step 2: Time-travel query
    print("\n[Step 2] Time-travel: Get budget value when agent_a had written 1 time and agent_b had written 0")
    try:
        snapshot_clock = json.dumps({"agent_a": 1, "agent_b": 0})
        response = CLIENT.get("/snapshot/budget", params={"at_clock": snapshot_clock})
        if response.status_code == 200:
            entry = response.json()
            print(f"  ✓ Snapshot retrieved")
            print(f"    Value at that point in time: {entry['value']}")
            print(f"    Agent: {entry['agent_id']}")
            print()
            print("  ✓ KEY INSIGHT: Complete causal history!")
            print("    You can query any point in time.")
            print("    Perfect for debugging and auditing.")
        else:
            print(f"  ✗ Request failed: {response.text}")
    except Exception as e:
        print(f"  ✗ Error: {e}")


# ============================================================================
# MOMENT 3: Access Control
# ============================================================================


def moment_3_access_control() -> None:
    """Demonstrate role-based access control."""
    print("\n" + "=" * 70)
    print("MOMENT 3: ACCESS CONTROL (Role-Based Permissions)")
    print("=" * 70)

    print("""
We registered a 'summarizer' role that's read-only.
It can read any key but cannot write.

Let's test both scenarios.
""")

    # Step 1: Successful read
    print("[Step 1] Summarizer reads 'budget' (should succeed)")
    try:
        response = CLIENT.get(
            "/read/budget",
            params={
                "agent_id": "summarizer",
                "role": "summarizer",
                "consistency_level": "eventual",
            },
        )
        if response.status_code == 200:
            entry = response.json()
            print(f"  ✓ Read permitted")
            print(f"    Value: {entry.get('value')}")
        else:
            print(f"  ✗ Read denied: {response.status_code} {response.text}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Step 2: Blocked write
    print("\n[Step 2] Summarizer attempts to write 'budget' (should fail with 403)")
    payload = {
        "key": "budget",
        "value": 9999,
        "agent_id": "summarizer",
        "role": "summarizer",
        "vector_clock": {"summarizer": 1},
    }
    try:
        response = CLIENT.post("/write", json=payload)
        if response.status_code == 403:
            print(f"  ✓ Write blocked (403 Forbidden)")
            print(f"    Error: {response.json().get('detail', 'Permission denied')}")
        else:
            print(f"  ✗ Unexpected status: {response.status_code}")
            print(f"    Response: {response.text}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    print()
    print("  ✓ KEY INSIGHT: Fine-grained access control!")
    print("    Roles can be scoped to specific key patterns.")
    print("    E.g., 'budget-agent' can only touch 'budget.*' keys.")


# ============================================================================
# MOMENT 4: Consistency Levels
# ============================================================================


def moment_4_consistency_levels() -> None:
    """Demonstrate different consistency levels."""
    print("\n" + "=" * 70)
    print("MOMENT 4: CONSISTENCY LEVELS")
    print("=" * 70)

    print("""
Engram supports three consistency models:
  • EVENTUAL (default): Return immediately, might be stale
  • CAUSAL: Ensure read respects causal ordering (not yet implemented)
  • STRONG: Full consistency via quorum (not yet implemented)
""")

    # Write a value
    print("[Step 1] Write with admin role")
    payload = {
        "key": "counter",
        "value": 42,
        "agent_id": "admin",
        "role": "admin",
        "vector_clock": {"admin": 1},
    }
    try:
        response = CLIENT.post("/write", json=payload)
        if response.status_code == 200:
            print(f"  ✓ Write succeeded, value: 42")
        else:
            print(f"  ✗ Write failed: {response.text}")
            return
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return

    # Read with EVENTUAL (should work)
    print("\n[Step 2] Read with EVENTUAL consistency (should work)")
    try:
        response = CLIENT.get(
            "/read/counter",
            params={
                "agent_id": "admin",
                "role": "admin",
                "consistency_level": "eventual",
            },
        )
        if response.status_code == 200:
            entry = response.json()
            print(f"  ✓ Read succeeded, value: {entry['value']}")
        else:
            print(f"  ✗ Read failed: {response.text}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Read with CAUSAL (not yet implemented)
    print("\n[Step 3] Read with CAUSAL consistency (not yet implemented)")
    try:
        response = CLIENT.get(
            "/read/counter",
            params={
                "agent_id": "admin",
                "role": "admin",
                "consistency_level": "causal",
            },
        )
        if response.status_code == 200:
            entry = response.json()
            print(f"  ✓ Read succeeded, value: {entry['value']}")
        elif response.status_code == 501:
            print(f"  ⓘ Causal consistency not yet implemented (expected 501)")
        else:
            print(f"  ! Status: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    print()
    print("  ✓ KEY INSIGHT: Multiple consistency models!")
    print("    Eventual is fast but might be stale.")
    print("    Causal and Strong will be stronger but slower.")


# ============================================================================
# MOMENT 5: Summary
# ============================================================================


def moment_5_summary() -> None:
    """Wrap up the demo."""
    print("\n" + "=" * 70)
    print("MOMENT 5: SUMMARY")
    print("=" * 70)

    print("""
What Engram gives you:

  1. CONFLICT DETECTION
     Concurrent writes are detected via vector clocks.
     All conflicting values are preserved.

  2. DATA NEVER SILENTLY LOST
     Instead of "last write wins", you get:
       • All conflicting values stored
       • Resolved value + conflicting_writes list
       • Status: "conflicted", "flagged", "ok"

  3. CONFIGURABLE RESOLUTION
     Multiple strategies:
       • LATEST_CLOCK: highest vector sum wins
       • LOWEST_VALUE: smallest value wins
       • HIGHEST_VALUE: largest value wins
       • UNION: keep all values
       • FLAG_FOR_HUMAN: don't resolve, require human review

  4. COMPLETE AUDIT TRAIL
     Every write is logged immutably.
     Query history or time-travel to any point.

  5. ACCESS CONTROL
     Role-based permissions with fnmatch patterns.
     Enforce permission at read/write time.

  6. MULTI-AGENT READY
     Built for systems where agents:
       • Don't always know about each other
       • May be geographically distributed
       • Need to detect conflicts, not hide them

Engram is the middleware layer that prevents data loss in
multi-agent systems while keeping everything auditable.
""")


# ============================================================================
# Main
# ============================================================================


def main() -> None:
    """Run all demo moments in sequence."""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║      ENGRAM DEMO: Conflict Detection for AI Agents      ║
    ║      (5 Key Moments)                                     ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    print("Checking API connection...")
    try:
        response = CLIENT.get("/docs")
        if response.status_code == 200:
            print("✓ Engram API is running at", ENGRAM_URL)
        else:
            print("✗ Unexpected response from API")
            return
    except Exception as e:
        print(f"✗ Cannot connect to Engram API at {ENGRAM_URL}")
        print(f"  Error: {e}")
        print(f"  Make sure to start the API first:")
        print(f"    uvicorn engram.api:app --reload")
        return

    # Run the demo
    setup_roles()
    moment_0_problem_setup()
    time.sleep(1)

    moment_1_conflict_detection()
    time.sleep(1)

    moment_2_history_and_time_travel()
    time.sleep(1)

    moment_3_access_control()
    time.sleep(1)

    moment_4_consistency_levels()
    time.sleep(1)

    moment_5_summary()

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print("""
To explore further:
  • Visit http://localhost:8000/docs for the interactive API docs
  • Read CODEBASE_WALKTHROUGH.md for detailed architecture
  • Check tests/ for comprehensive examples
  • Modify demo_presentation.py to add custom scenarios
    """)


if __name__ == "__main__":
    main()
