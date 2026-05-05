# Engram Visual Architecture Guide

Diagrams and visual explanations for understanding Engram's architecture.

---

## 1. System Architecture (High Level)

```
┌────────────────────────────────────────────────────────────────┐
│                        HTTP Clients                             │
│            (Web, CLI, Other Services, Agents)                  │
└────────────────────┬─────────────────────────────────────────┘
                     │ HTTP (FastAPI)
                     ▼
┌────────────────────────────────────────────────────────────────┐
│                     Engram Middleware                           │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Permission Check (AccessPolicy)            │  │
│  │   Is agent_id:role allowed to read/write this key?      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Vector Clock Increment & Comparison             │  │
│  │    Determine causal order: BEFORE, AFTER, or CONCURRENT │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │      CRDT (Multi-Value Register) Merge & Resolve        │  │
│  │   Store conflicting values, pick winner by strategy     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         History Logging (Append-Only Audit Trail)       │  │
│  │    Every write creates immutable HistoryEntry            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          Storage Adapter (Pluggable)                     │  │
│  │    ┌─────────────────┬──────────────┬─────────────────┐  │  │
│  │    │  Memory         │  Redis       │  Future: Chroma │  │  │
│  │    │  (in-process)   │  (persisted) │  Pinecone       │  │  │
│  │    └─────────────────┴──────────────┴─────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## 2. Write Pipeline (Detailed Flow)

```
                    ┌─────────────┐
                    │POST /write  │
                    │  Request    │
                    └──────┬──────┘
                           │
                           ▼
          ┌────────────────────────────────┐
          │ 1. EXTRACT REQUEST             │
          │ ├─ key: "budget"               │
          │ ├─ value: 5000                 │
          │ ├─ agent_id: "agent_a"         │
          │ ├─ role: "budget-agent"        │
          │ └─ vector_clock: {"a": 1}      │
          └────────┬───────────────────────┘
                   │
                   ▼
          ┌────────────────────────────────┐
          │ 2. PERMISSION CHECK            │
          │ ├─ Lookup role: "budget-agent" │
          │ ├─ Check: can_write["budget.*"]│
          │ └─ Approve or Deny (403)       │
          └────────┬───────────────────────┘
                   │ ✓ Approved
                   ▼
          ┌────────────────────────────────┐
          │ 3. VECTOR CLOCK UPDATE         │
          │ ├─ Old: {"a": 1, "b": 0}       │
          │ ├─ New: {"a": 2, "b": 0}       │
          │ └─ Compare with existing clock │
          └────────┬───────────────────────┘
                   │
                   ▼
          ┌────────────────────────────────┐
          │ 4. LOAD EXISTING VALUE         │
          │ ├─ Read from storage: "budget" │
          │ └─ Get current MVRegister      │
          └────────┬───────────────────────┘
                   │
        ┌──────────┴──────────┐
        │ Empty? OR Existing? │
        └──────────┬──────────┘
        │          │ Existing (has value with old clock)
        │          ▼
        │  ┌────────────────────────────┐
        │  │ 5. CONFLICT DETECTION      │
        │  │ Compare:                   │
        │  │  New:  {"a": 1}            │
        │  │  Old:  {"b": 1}            │
        │  │ Result: CONCURRENT!        │
        │  └────────┬───────────────────┘
        │           │
        └───────┬───┘
                │
                ▼
        ┌────────────────────────────────┐
        │ 6. CRDT MERGE & RESOLUTION     │
        │ ├─ Store both values           │
        │ │  {"a": 1} → 5000             │
        │ │  {"b": 1} → 4200             │
        │ ├─ Apply strategy (LATEST...)  │
        │ └─ Result: resolved_value: X   │
        └────────┬───────────────────────┘
                 │
                 ▼
        ┌────────────────────────────────┐
        │ 7. CREATE MEMORY ENTRY         │
        │ ├─ write_id: uuid              │
        │ ├─ key: "budget"               │
        │ ├─ value: X (resolved)         │
        │ ├─ status: "conflicted"        │
        │ ├─ conflicting_writes: [...]   │
        │ └─ vector_clock: {"a": 1}      │
        └────────┬───────────────────────┘
                 │
                 ▼
        ┌────────────────────────────────┐
        │ 8. HISTORY LOGGING             │
        │ ├─ Create HistoryEntry         │
        │ └─ Append to audit trail       │
        └────────┬───────────────────────┘
                 │
                 ▼
        ┌────────────────────────────────┐
        │ 9. PERSIST TO STORAGE          │
        │ ├─ storage.write(MemoryEntry)  │
        │ └─ Update Redis/Memory/etc.    │
        └────────┬───────────────────────┘
                 │
                 ▼
        ┌────────────────────────────────┐
        │ 10. RETURN HTTP 200            │
        │ {                              │
        │   "status": "conflicted",      │
        │   "value": X,                  │
        │   "conflicting_writes": [...]  │
        │ }                              │
        └────────────────────────────────┘
```

---

## 3. Vector Clock Comparison (The Heart of Conflict Detection)

```
┌──────────────────────────────────────────────────────┐
│  Vector Clock Comparison Logic                       │
└──────────────────────────────────────────────────────┘

Given: clock_a and clock_b

Step 1: Collect all agent IDs from both clocks
Step 2: For each agent, compare counters (missing = 0)
Step 3: Determine relationship:

┌────────────────────────────────────────────────────┐
│ All equal?    → EQUAL                             │
│ a ≤ b (all ≤, at least one <)  → BEFORE         │
│ b ≤ a (all ≤, at least one <)  → AFTER          │
│ Otherwise    → CONCURRENT (incomparable!)        │
└────────────────────────────────────────────────────┘

EXAMPLES:

Clock A: {"x": 1, "y": 0}
Clock B: {"x": 1, "y": 1}
Analysis: A.y < B.y (and A.x = B.x)
Result: A BEFORE B (A is dominated)
Meaning: B's write came AFTER and knows about A

───────────────────────────────────────────────────

Clock A: {"x": 2, "y": 0}
Clock B: {"x": 0, "y": 2}
Analysis: A.x > B.x AND A.y < B.y (incomparable)
Result: CONCURRENT (conflict!)
Meaning: A and B wrote without knowing about each other

───────────────────────────────────────────────────

Clock A: {"x": 1, "y": 1}
Clock B: {"x": 1, "y": 1}
Analysis: All counters equal
Result: EQUAL
Meaning: Same logical point in time

───────────────────────────────────────────────────

Clock A: {"x": 3}
Clock B: {"x": 1, "y": 1}
Analysis: A.x=3 > B.x=1, but A.y=0 < B.y=1
Result: CONCURRENT
Meaning: Neither dominates → conflict!
```

---

## 4. CRDT Write Logic (Multi-Value Register)

```
┌──────────────────────────────────────────────┐
│ MVRegister.write(value, agent_id, clock)    │
└──────────────────────────────────────────────┘

Start with existing register (possibly empty)

               ┌─ Is register empty?
               │
        YES ◄──┴──► NO
        │            │
        │            ▼
        │      ┌──────────────────────────┐
        │      │ For each existing value: │
        │      │ Compare new_clock vs     │
        │      │ existing_value.clock     │
        │      └──────┬───────────────────┘
        │             │
        │      ┌──────┴──────────────────────┐
        │      │ Any result?                │
        │      ├─ All BEFORE or EQUAL?      │
        │      ├─ Any CONCURRENT?           │
        │      └─ Any AFTER?                │
        │             │
        ├─────────────┼──────────────────────┐
        │             │                      │
        │      All BEFORE/EQUAL    Any AFTER │
        │             │                  │   │
        │             ▼                  ▼   ▼
        │    ┌─────────────────┐  ┌──────────────┐
        │    │ NEW is AFTER    │  │ NEW is STALE │
        │    │ everything      │  │ Discard it   │
        │    │ Replace all     │  │ Return self  │
        │    └─────────────────┘  │ unchanged    │
        │             │           └──────────────┘
        │             │
        │      Any CONCURRENT?
        │             │
        │       YES ◄─┴─► NO
        │       │         │
        │       │         ▼
        │       │    ┌──────────────────┐
        │       │    │ New replaces all │
        │       │    │ Return: [new]    │
        │       │    └──────────────────┘
        │       │
        │       ▼
        │   ┌───────────────────┐
        │   │ Keep existing     │
        │   │ concurrent values │
        │   │ + add new value   │
        │   │ Return: [old...] +│
        │   │ [new]             │
        │   └───────────────────┘
        │
        ▼
   ┌──────────────────┐
   │ Just add new     │
   │ Return: [new]    │
   └──────────────────┘

RESULT:
- 1 value → status "ok"
- 2+ values → status "conflicted"
```

---

## 5. Conflict Resolution Strategies

```
┌────────────────────────────────────────────┐
│ MVRegister.resolve(strategy)               │
│ → (resolved_value, list_of_losing_writes) │
└────────────────────────────────────────────┘

Check: How many values?

     1 value
         │
         ▼
    Return it directly
    conflicting_writes = []

     2+ values
         │
         ├─► LATEST_CLOCK
         │   ├─ Calculate: sum(clock.values()) for each
         │   ├─ Pick highest sum
         │   ├─ Tie-break by timestamp
         │   └─ Return winner + losers
         │
         ├─► LOWEST_VALUE
         │   ├─ Use min(values)
         │   ├─ Assumes values are comparable
         │   └─ Raise ValueError if not
         │
         ├─► HIGHEST_VALUE
         │   ├─ Use max(values)
         │   ├─ Assumes values are comparable
         │   └─ Raise ValueError if not
         │
         ├─► UNION
         │   ├─ Return all values as a list
         │   ├─ No winner/losers
         │   └─ conflicting_writes = []
         │
         └─► FLAG_FOR_HUMAN
             ├─ Return None (no winner)
             ├─ All values → conflicting_writes
             └─ Entry status = "FLAGGED"

EXAMPLE:

Values: [5000 (agent_a), 4200 (agent_b)]
Strategy: LATEST_CLOCK

Scores:
  agent_a: {"a": 1, "b": 0} → sum = 1
  agent_b: {"a": 0, "b": 1} → sum = 1
  Tie! Use timestamp...
  (Let's say agent_a's timestamp is newer)

Result:
  resolved_value: 5000
  conflicting_writes: [agent_b's 4200]
```

---

## 6. Access Control (Role-Based with Wildcards)

```
┌─────────────────────────────────────────┐
│ AccessPolicy.check_write(role, key)    │
└─────────────────────────────────────────┘

Step 1: Look up role
        ├─ If not found → return False (403)
        └─ If found → continue

Step 2: Get can_write list for this role
        ├─ Empty list → return False (read-only)
        └─ Has entries → continue

Step 3: Check each pattern
        ├─ If pattern == "*" → return True (all keys)
        └─ Otherwise → fnmatch(key, pattern)

Step 4: Return True if any pattern matches

EXAMPLE:

Role: "budget-agent"
can_write: ["budget.*", "transaction.*"]

Checks:
  budget.flights     → matches "budget.*" → ✓ ALLOWED
  budget.hotels      → matches "budget.*" → ✓ ALLOWED
  transaction.log    → matches "transaction.*" → ✓ ALLOWED
  audit.report       → no match → ✗ DENIED

───────────────────────────────────────

Role: "admin"
can_write: ["*"]

Checks: (everything) → matches "*" → ✓ ALWAYS ALLOWED

───────────────────────────────────────

Role: "auditor"
can_write: []

Checks: (anything) → no patterns → ✗ ALWAYS DENIED (read-only)
```

---

## 7. History Log & Time-Travel

```
┌──────────────────────────────────────────────┐
│ All Writes to Key "budget" Over Time        │
└──────────────────────────────────────────────┘

Timeline (not physical time, but causal order):

T1: Agent A writes 5000
    vector_clock: {"a": 1, "b": 0}
    timestamp: 2026-05-01 10:00:00

T2: Agent B writes 4200
    vector_clock: {"a": 0, "b": 1}
    timestamp: 2026-05-01 10:00:01
    (B didn't see A's write)

T3: Agent A writes 3500
    vector_clock: {"a": 2, "b": 0}
    timestamp: 2026-05-01 10:00:02
    (A didn't see B's write)

T4: Agent B learns about A's history
    and writes 4500
    vector_clock: {"a": 2, "b": 2}
    timestamp: 2026-05-01 10:00:03
    (B now knows about both A's writes)

───────────────────────────────────────

TIME-TRAVEL QUERY:
"What was budget at the point when A had 1 write, B had 0?"

Query: get_snapshot(key="budget", at_clock={"a": 1, "b": 0})

Find all entries where entry_clock ≤ at_clock:
  ✓ T1: {"a": 1, "b": 0} ≤ {"a": 1, "b": 0} (EQUAL)
  ✗ T2: {"a": 0, "b": 1} CONCURRENT with target (not BEFORE)
  ✗ T3: {"a": 2, "b": 0} > target (AFTER)
  ✗ T4: {"a": 2, "b": 2} > target (AFTER)

Candidates: [T1]
Return: T1's value (5000)

───────────────────────────────────────

Another query:
"What was budget at the point when A had 2 writes, B had 2 writes?"

Query: get_snapshot(key="budget", at_clock={"a": 2, "b": 2})

Find all entries where entry_clock ≤ at_clock:
  ✓ T1: {"a": 1, "b": 0} ≤ {"a": 2, "b": 2} (BEFORE)
  ✓ T2: {"a": 0, "b": 1} ≤ {"a": 2, "b": 2} (BEFORE)
  ✓ T3: {"a": 2, "b": 0} ≤ {"a": 2, "b": 2} (BEFORE)
  ✓ T4: {"a": 2, "b": 2} ≤ {"a": 2, "b": 2} (EQUAL)

Candidates: [T1, T2, T3, T4]
Return: Most recent among candidates (T4's value: 4500)
```

---

## 8. Storage Adapter Architecture (Pluggable)

```
┌────────────────────────────────────────────┐
│ StorageAdapter (Abstract Base Class)       │
├────────────────────────────────────────────┤
│ ├─ write(entry) → None                     │
│ ├─ read(key) → Optional[MemoryEntry]       │
│ ├─ write_history(entry) → None             │
│ ├─ read_history(key, ...) → list           │
│ ├─ delete(key) → None                      │
│ ├─ list_keys(prefix) → list[str]           │
│ └─ ping() → bool                           │
└────────────────────────────────────────────┘

            ▲
            │ implements

┌───────────────────────────────┐
│   InMemoryAdapter             │
├───────────────────────────────┤
│ ├─ _memory: dict[str, ...]    │
│ ├─ _history: list[...]        │
│ └─ Fast, single-process only  │
└───────────────────────────────┘

┌───────────────────────────────┐
│   RedisAdapter                │
├───────────────────────────────┤
│ ├─ _redis: Redis client       │
│ ├─ Persistent, distributed    │
│ └─ Requires Redis server      │
└───────────────────────────────┘

┌───────────────────────────────┐
│   Future: ChromaAdapter       │
├───────────────────────────────┤
│ ├─ Vector embeddings          │
│ ├─ Semantic search            │
│ └─ For AI-native queries      │
└───────────────────────────────┘

┌───────────────────────────────┐
│   Future: PineconeAdapter     │
├───────────────────────────────┤
│ ├─ Vector DB in cloud         │
│ ├─ Scalable embeddings        │
│ └─ For enterprise deployments │
└───────────────────────────────┘

MIDDLEWARE USES:
  storage.read(key)
  storage.write(entry)
  storage.read_history(key)
  storage.write_history(entry)

ENGRAM NEVER IMPORTS REDIS/CHROMA DIRECTLY!
Only calls the adapter interface.
```

---

## 9. Complete Request-Response Cycle

```
CLIENT                      ENGRAM MIDDLEWARE              STORAGE
  │                              │                            │
  ├─ POST /write ─────────────►  │                            │
  │ {                            │                            │
  │   "key": "budget",           │                            │
  │   "value": 5000,             │                            │
  │   "agent_id": "a",           │                            │
  │   "role": "admin",           │                            │
  │   "vector_clock": {...}      │                            │
  │ }                            │                            │
  │                              ├─ Check permission         │
  │                              ├─ Increment vector clock  │
  │                              ├─ read(key) ──────────────►│
  │                              │                           │
  │                              │◄────────────────────────  │
  │                              │ (returns existing entry)   │
  │                              ├─ Detect conflict         │
  │                              ├─ Merge CRDTs             │
  │                              ├─ Resolve conflict        │
  │                              ├─ Create HistoryEntry    │
  │                              ├─ write(entry) ──────────►│
  │                              │                           │
  │                              │◄────────────────────────  │
  │                              │ (persisted)               │
  │                              ├─ write_history(entry) ──►│
  │                              │                           │
  │                              │◄────────────────────────  │
  │                              │ (audit logged)            │
  │◄──────── 200 OK ────────────  │                            │
  │ {                            │                            │
  │   "key": "budget",           │                            │
  │   "value": 5000,             │                            │
  │   "status": "ok",            │                            │
  │   "write_id": "uuid-123",    │                            │
  │   ...                        │                            │
  │ }                            │                            │
  │                              │                            │

NEXT CONCURRENT REQUEST FROM ANOTHER AGENT:

CLIENT 2                    ENGRAM MIDDLEWARE              STORAGE
  │                              │                            │
  ├─ POST /write ─────────────►  │                            │
  │ {                            │                            │
  │   "key": "budget",           │                            │
  │   "value": 4200,             │                            │
  │   "agent_id": "b",           │ ✓ Permission OK            │
  │   "role": "admin",           │ ✓ Vector clock increment  │
  │   "vector_clock": {...}      │                            │
  │ }                            ├─ read(key) ──────────────►│
  │                              │                           │
  │                              │◄──── (gets client 1's)    │
  │                              │ entry with clock {"a":1} │
  │                              │                           │
  │                              ├─ Compare:                │
  │                              │  New:  {"b": 1}          │
  │                              │  Old:  {"a": 1}          │
  │                              │  Result: CONCURRENT ⚠️  │
  │                              │                           │
  │                              ├─ Merge MVRegisters       │
  │                              │  (store both values)     │
  │                              │                           │
  │                              ├─ Resolve (pick one)      │
  │                              ├─ write(entry) ──────────►│
  │                              │                           │
  │                              │◄──────────────────────    │
  │◄──────── 200 OK ────────────  │                            │
  │ {                            │                            │
  │   "status": "conflicted", ⚠️  │                            │
  │   "value": 5000,             │                            │
  │   "conflicting_writes": [    │                            │
  │     {"value": 4200, ...}     │                            │
  │   ]                          │                            │
  │ }                            │                            │
```

---

## 10. Conflict Scenario Matrix

```
┌────────────────────────────────────────────────────────────┐
│ Vector Clock Comparison Results & Meanings                │
└────────────────────────────────────────────────────────────┘

COMPARISON    MEANING                    RESULT
─────────────────────────────────────────────────────────────
EQUAL         Same point in time         Duplicate write
              (probably error)            → Overwrite

BEFORE        New is after existing      Causal ordering
              Existing knows about new   → Replace all
                                          (new supersedes)

AFTER         Existing is newer          Stale write
              Existing doesn't know      → Discard
              about new                   (ignore)

CONCURRENT    Neither dominates          CONFLICT! ⚠️
              They didn't know           → Store both
              about each other            → Resolve by strategy

─────────────────────────────────────────────────────────────

EXAMPLE SCENARIOS:

Scenario A: Sequential Writes
  Write 1: Agent A, clock {"a": 1}
  Write 2: Agent A, clock {"a": 2}
  Comparison: {"a": 1} BEFORE {"a": 2}
  Result: Sequential, no conflict

Scenario B: Concurrent Writes (Same Agent)
  Write 1: Agent A, clock {"a": 1}
  Write 2: Agent A, clock {"a": 1}
  Comparison: EQUAL
  Result: Duplicate (overwrite)

Scenario C: Concurrent Writes (Different Agents)
  Write 1: Agent A, clock {"a": 1, "b": 0}
  Write 2: Agent B, clock {"a": 0, "b": 1}
  Comparison: CONCURRENT
  Result: CONFLICT (store both)

Scenario D: Causal Chain
  Write 1: Agent A, clock {"a": 1}
  Write 2: Agent B, clock {"a": 1, "b": 1}  (B saw A's write)
  Comparison: {"a": 1} BEFORE {"a": 1, "b": 1}
  Result: Sequential, no conflict

Scenario E: Stale Write
  Write 1: Agent A, clock {"a": 2}
  Write 2: Agent A, clock {"a": 1}  (old clock)
  Comparison: {"a": 1} BEFORE {"a": 2}
  Result: Stale (discard, keep the newer one)
```

---

## Summary: The Three Layers

```
┌─────────────────────────────────────────────────────────┐
│                  APPLICATION LAYER                      │
│        (HTTP API, Clients, External Systems)            │
└─────────────────────────────────────────────────────────┘
                          ▲ │
                          │ ▼
┌─────────────────────────────────────────────────────────┐
│               ORCHESTRATION LAYER                        │
│ EngramMiddleware: Wires everything together             │
│ ├─ Permission checks (AccessPolicy)                    │
│ ├─ Vector clock logic (VectorClock)                    │
│ ├─ Conflict detection & merge (MVRegister/CRDT)        │
│ ├─ History & time-travel (HistoryLog)                  │
│ └─ Storage abstraction (StorageAdapter)                │
└─────────────────────────────────────────────────────────┘
                          ▲ │
                          │ ▼
┌─────────────────────────────────────────────────────────┐
│                  PERSISTENCE LAYER                       │
│ ├─ Memory (in-process)                                 │
│ ├─ Redis (distributed)                                 │
│ └─ Future: Vector DBs, etc.                            │
└─────────────────────────────────────────────────────────┘
```

---

## Key Takeaways (Visual Summary)

```
WITHOUT ENGRAM:
  Shared Dict
  │
  ├─ Agent A writes → value = 5000
  ├─ Agent B writes → value = 4200 (overwrites silently!)
  │
  └─ Result: Agent A's write is GONE 💥

WITH ENGRAM:
  Shared State
  │
  ├─ Agent A writes → clock {"a": 1}
  ├─ Agent B writes → clock {"b": 1} (concurrent!)
  ├─ Vector clocks compare → CONCURRENT (conflict detected!)
  ├─ CRDT stores both: [5000, 4200]
  ├─ Resolve by strategy → pick winner
  │
  └─ Result: Both values preserved, conflict tracked ✓

ENGRAM = Conflict Detection + CRDT + Resolution + History
```

---

**Diagrams created for version 0.1.0 (May 2026)**
