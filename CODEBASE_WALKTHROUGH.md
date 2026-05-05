# Engram Codebase Walkthrough

A comprehensive guide to the Engram memory middleware system for multi-agent AI systems.

---

## 1. HIGH-LEVEL OVERVIEW

### Purpose

**Engram** is a memory middleware service that solves a critical problem in multi-agent AI systems: **conflict detection and resolution when multiple agents read and write to the same shared state**.

In a naive shared dict or key-value store, the **last write wins silently**—Agent A sets `budget = 5000`, Agent B sets `budget = 3000` microseconds later without seeing A's write, and A's value is lost forever with no warning.

Engram detects these concurrent writes using **vector clocks**, stores all conflicting values in a **CRDT (Multi-Value Register)**, and resolves them using configurable strategies or flags them for human review.

### Main Features

1. **Conflict Detection** — Uses vector clocks to detect concurrent writes (writes that happen without knowing about each other)
2. **CRDT Storage** — Multi-Value Register (MVRegister) stores all concurrent values instead of silently overwriting
3. **Configurable Conflict Resolution** — Multiple strategies: latest clock, lowest/highest value, union (keep all), or flag for human
4. **Role-Based Access Control** — Fine-grained permissions with fnmatch wildcard patterns
5. **Immutable Audit Trail** — Complete history log with time-travel queries
6. **Storage Agnostic** — Pluggable storage adapters (in-memory, Redis, future: Chroma, Pinecone)

### Tech Stack

- **Language**: Python 3.11+
- **Web Framework**: FastAPI + Uvicorn
- **Data Format**: Pydantic models
- **Storage Backends**: In-memory, Redis (pluggable architecture)
- **Testing**: pytest, pytest-asyncio
- **Configuration**: pydantic-settings (environment variables)

---

## 2. PROJECT STRUCTURE

```
engram/
├── __init__.py                 # Package entry point
├── models.py                   # Single source of truth for all data types
├── vector_clock.py             # Causal ordering engine
├── crdt.py                     # Multi-Value Register (conflict storage)
├── access_control.py           # Role-based access control (RBAC)
├── middleware.py               # Central wiring (orchestrates full pipeline)
├── api.py                      # FastAPI routes (HTTP endpoints)
├── history.py                  # Append-only audit trail with time-travel
└── storage/
    ├── base.py                 # Abstract storage adapter interface
    ├── memory.py               # In-memory adapter
    ├── redis_adapter.py        # Redis adapter
    ├── chroma_adapter.py       # Vector DB adapter (future)
    └── pinecone_adapter.py     # Vector DB adapter (future)

tests/
├── conftest.py                 # pytest fixtures and configuration
├── test_vector_clock.py        # Vector clock tests
├── test_crdt.py                # CRDT tests
├── test_access_control.py      # Access control tests
├── test_api.py                 # HTTP endpoint tests
├── test_history.py             # History log tests
├── test_storage.py             # Storage adapter tests
├── test_redis.py               # Redis-specific tests
└── test_e2e_budget_conflict.py # End-to-end conflict scenario

demo/
├── run_demo.py                 # Runnable demo script (5 key moments)
├── agents.py                   # Demo agent implementations
└── ui/                         # Simple HTML/JS UI for visualization
    ├── index.html
    └── app.js

Configuration & Deployment:
├── pyproject.toml              # Project metadata and dependencies
├── requirements.txt            # Pip-friendly dependency list
├── docker-compose.yml          # Redis + Engram services
├── .env                        # Environment variables (not in repo)
└── README.md                   # User-facing documentation
```

### Key Folders Explained

**`engram/`** — Core library code

- No dependencies between modules except through `models.py`
- Clean separation: vector clocks, CRDTs, access control, storage are independent
- `middleware.py` is the wiring layer that composes them all

**`storage/`** — Storage abstraction layer

- `base.py` defines the interface that all adapters implement
- Engram never imports Redis/Chroma directly; it only calls adapter methods
- New adapters can be added by extending `StorageAdapter`

**`tests/`** — Comprehensive test suite

- Every module has corresponding tests
- E2E test (`test_e2e_budget_conflict.py`) demonstrates the full pipeline

**`demo/`** — Executable demonstration

- Five separate "moments" to walk through the system
- Each moment focuses on one core concept

---

## 3. CORE LOGIC WALKTHROUGH

### The Big Picture: Full Write Pipeline

When a client calls `POST /write`, here's what happens inside `EngramMiddleware.write()`:

```
HTTP Request → POST /write
    ↓
1. PERMISSION CHECK
    └─→ AccessPolicy.check_write(role, key)
        └─→ Returns 403 Forbidden if role lacks write permission
    ↓
2. VECTOR CLOCK INCREMENT
    └─→ VectorClock.increment(agent_id)
        └─→ Creates new clock with agent's counter bumped by 1
    ↓
3. LOAD EXISTING VALUE
    └─→ storage.read(key)
        └─→ Returns current MVRegister or None if key doesn't exist
    ↓
4. CONFLICT DETECTION & MERGING
    └─→ MVRegister.write(new_value, agent_id, role, new_clock)
        ├─→ Compare new clock vs. existing clock
        ├─→ AFTER all existing → Replace all (new is authoritative)
        ├─→ CONCURRENT with any → Keep both (conflict!)
        ├─→ BEFORE any existing → Discard (stale write)
        └─→ Return new MVRegister
    ↓
5. CONFLICT RESOLUTION
    └─→ MVRegister.resolve(strategy)
        ├─→ Single value → return as-is
        ├─→ Multiple values → apply strategy
        │   ├─→ LATEST_CLOCK: pick highest vector sum
        │   ├─→ LOWEST_VALUE: pick numerically smallest
        │   ├─→ HIGHEST_VALUE: pick numerically largest
        │   ├─→ UNION: return all as list
        │   └─→ FLAG_FOR_HUMAN: return None, mark entry as FLAGGED
        └─→ Returns (resolved_value, list_of_losing_writes)
    ↓
6. HISTORY LOGGING
    └─→ HistoryLog.append(HistoryEntry)
        └─→ Appends immutable record; never deletes or mutates
    ↓
7. STORAGE PERSISTENCE
    └─→ storage.write(MemoryEntry)
        └─→ Saves to Redis/memory/etc.
    ↓
HTTP Response ← MemoryEntry with resolved value
```

### Read Pipeline (Simpler)

```
HTTP Request → GET /read/{key}?agent_id=A&role=admin
    ↓
1. PERMISSION CHECK
    └─→ AccessPolicy.check_read(role, key)
        └─→ Returns 403 Forbidden if denied
    ↓
2. STORAGE LOOKUP
    └─→ storage.read(key)
        └─→ Returns MemoryEntry or None
    ↓
3. CONSISTENCY LEVEL ENFORCEMENT
    ├─→ EVENTUAL: return immediately (default)
    ├─→ CAUSAL: (not yet implemented) would wait until read is causally consistent
    └─→ STRONG: (not yet implemented) would require quorum
    ↓
HTTP Response ← MemoryEntry with resolved value
```

### Key Data Structures

#### VectorClock — The Causal Order Engine

```python
VectorClock({"A": 3, "B": 1, "C": 2})  # Agent A has done 3 writes, B has done 1, etc.
```

**Compare Logic** (the heart of conflict detection):

- **EQUAL**: All counters match exactly
- **BEFORE**: One clock dominates (all counters ≤, with at least one <)
- **AFTER**: Reverse of BEFORE
- **CONCURRENT**: Neither dominates (e.g., {"A": 2} vs {"B": 1} — incomparable)

**Mutation**: Never mutate. Every operation returns a new VectorClock.

#### MVRegister — The Conflict Storage (CRDT)

```python
mvr = MVRegister()
mvr._values = [
    ConflictingWrite(agent_id="A", value=5000, vector_clock={"A": 1}, ...),
    ConflictingWrite(agent_id="B", value=3000, vector_clock={"B": 1}, ...),
]
mvr.is_conflicted()  # → True (two values exist)
```

**When concurrent writes arrive:**

- Write 1 comes in with clock {"A": 1}
- Write 2 arrives with clock {"B": 1} — these are CONCURRENT (neither dominates)
- **Result**: Both values stored in the register. Status is `CONFLICTED`.
- When read: apply resolution strategy to pick one (or keep all with UNION strategy)

#### MemoryEntry — The Resolved Record

```python
MemoryEntry(
    write_id="uuid-123",
    key="budget",
    value=5000,  # resolved value after applying strategy
    agent_id="A",
    role="budget-agent",
    vector_clock={"A": 1},
    status="ok",  # or "conflicted" or "flagged"
    conflicting_writes=[...],  # list of non-winning ConflictingWrite objects
)
```

#### HistoryEntry — The Audit Trail

```python
HistoryEntry(
    write_id="uuid-456",
    key="budget",
    value=5000,
    agent_id="A",
    vector_clock={"A": 1},
    timestamp=datetime.now(timezone.utc),
    write_type="write",  # or "rollback"
    rollback_of=None,  # if it's a rollback, points to original write_id
)
```

### Important Functions & Classes

#### AccessPolicy (Role-Based Access Control)

```python
policy = AccessPolicy()

# Register roles at startup
policy.register_role("admin", can_read=["*"], can_write=["*"])
policy.register_role("budget-agent", can_read=["budget.*"], can_write=["budget.*"])
policy.register_role("auditor", can_read=["*"], can_write=[])  # read-only

# Every request checks permissions
if not policy.check_write("budget-agent", "budget.flights"):
    raise PermissionError()  # fnmatch pattern doesn't match
```

#### EngramMiddleware (The Orchestrator)

Central class that wires together all components:

- `write(request)` — Full write pipeline
- `read(key, request)` — Full read pipeline
- `rollback(request)` — Undo a previous write

#### HistoryLog (Append-Only Audit Trail)

```python
history = HistoryLog(storage=redis_adapter)

# Append an entry
history.append(entry)

# Query by key with optional filters
entries = history.get_history(key="budget", agent_id="A", since=datetime(...))

# Time-travel query: what was this key's value at clock point X?
snapshot = history.get_snapshot(key="budget", at_clock={"A": 1})
```

---

## 4. SETUP AND RUNNING INSTRUCTIONS

### Prerequisites

- **Python 3.11+** (check with `python --version`)
- **Redis** (optional; in-memory adapter works without it)
- **pip** or **Poetry** for dependency management

### Installation Steps

1. **Clone the repository** (or navigate to the workspace):

   ```bash
   cd /Users/gayathri/Documents/SJSU/273/Engram
   ```

2. **Create a virtual environment**:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   # Or for dev (includes pytest, ruff):
   pip install -e ".[dev]"
   ```

4. **(Optional) Start Redis** (if using Redis adapter):

   ```bash
   docker-compose up -d redis
   # Or with Docker Desktop already running:
   docker compose up -d
   ```

5. **Verify installation**:
   ```bash
   pytest tests/ -v  # Should see all tests pass (or be marked as TODO)
   ```

### Running the Project Locally

#### Option 1: Start the API Server (Default: In-Memory)

```bash
# Terminal 1: Start Engram API
uvicorn engram.api:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Test a write request
curl -X POST http://localhost:8000/write \
  -H "Content-Type: application/json" \
  -d '{
    "key": "budget",
    "value": 5000,
    "agent_id": "agent_a",
    "role": "budget-agent",
    "vector_clock": {"agent_a": 1}
  }'

# Get the value back
curl http://localhost:8000/read/budget?agent_id=agent_a&role=budget-agent
```

#### Option 2: Use Redis Backend

```bash
# Create .env file
echo "STORAGE_ADAPTER=redis" > .env

# Start Redis and API
docker-compose up  # Starts both Redis and Engram

# Or manually:
docker run -d -p 6379:6379 redis:7.2-alpine
uvicorn engram.api:app --reload
```

#### Option 3: Run Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_crdt.py -v

# With coverage
pytest tests/ --cov=engram --cov-report=html
```

#### Option 4: Run the Demo Script

```bash
# Requires API running at http://localhost:8000
uvicorn engram.api:app &  # Start in background
python demo/run_demo.py    # Run demo moments
```

### Configuration

Edit `.env` file to customize:

```bash
STORAGE_ADAPTER=memory  # or "redis"
REDIS_URL=redis://localhost:6379/0
ENGRAM_HOST=0.0.0.0
ENGRAM_PORT=8000
LOG_LEVEL=INFO
```

---

## 5. DEMO SCRIPT (3–5 Minutes)

### Setup Before Demo

```bash
# Terminal 1: Start API
uvicorn engram.api:app --reload

# Terminal 2: Run demo (or use curl/Postman to call endpoints manually)
python demo/run_demo.py
```

### Presentation Script — "The 5 Moments of Engram"

#### **Moment 0: Problem Setup (30 seconds)**

> "Imagine we have two AI agents managing a shared budget. Agent A is in New York, Agent B is in Tokyo. They're both looking at the same memory key: `budget`.
>
> Agent A reads it: `budget = 5000`
> Agent B reads it: `budget = 5000`
>
> Agent A runs for 5 hours analyzing costs, then writes back: `budget = 3500`
> At almost the same time, Agent B finishes processing and writes: `budget = 4200`
>
> These writes are **concurrent**—they didn't know about each other.
>
> In a regular database, one silently overwrites the other. Gone forever. No warning."

---

#### **Moment 1: The Problem WITHOUT Engram (1 minute)**

Show a simulation (no API calls):

```python
# Naive shared dict
shared_memory = {"budget": 5000}

# Agent A writes
shared_memory["budget"] = 3500
print(f"Agent A writes: {shared_memory}")  # → {"budget": 3500}

# Agent B writes (didn't see A's write)
shared_memory["budget"] = 4200
print(f"Agent B writes: {shared_memory}")  # → {"budget": 4200}

# Agent A's write is GONE. No trace. No audit trail.
print("Agent A's write: LOST!")
```

**Key Point**: "Last write wins. Silently. No error. This is the problem Engram solves."

---

#### **Moment 2: The SAME Conflict WITH Engram (2 minutes)**

**Step 1: Register roles**

```bash
curl -X POST http://localhost:8000/roles \
  -H "Content-Type: application/json" \
  -d '{
    "role_name": "budget-agent",
    "can_read": ["budget.*"],
    "can_write": ["budget.*"]
  }'
```

**Step 2: Agent A writes**

```bash
curl -X POST http://localhost:8000/write \
  -H "Content-Type: application/json" \
  -d '{
    "key": "budget",
    "value": 3500,
    "agent_id": "agent_a",
    "role": "budget-agent",
    "vector_clock": {"agent_a": 1, "agent_b": 0}
  }'
```

**Response shows**: ✅ `status: "ok"`, `value: 3500`

**Step 3: Agent B writes concurrently**

```bash
curl -X POST http://localhost:8000/write \
  -H "Content-Type: application/json" \
  -d '{
    "key": "budget",
    "value": 4200,
    "agent_id": "agent_b",
    "role": "budget-agent",
    "vector_clock": {"agent_a": 0, "agent_b": 1}
  }'
```

**Response shows**: ⚠️ `status: "conflicted"`, `conflicting_writes: [3500, 4200]`

**Step 4: Read the value**

```bash
curl http://localhost:8000/read/budget?agent_id=agent_a&role=budget-agent
```

**Response shows**: Both values stored. Engram chose one based on conflict strategy (e.g., LATEST_CLOCK). But the other is still visible in `conflicting_writes`.

**Key Point**: "Engram detected the conflict, stored both values, and applied a resolution strategy. Nothing is lost. Everything is auditable."

---

#### **Moment 3: History & Time-Travel (1 minute)**

> "Let's look at the complete audit trail."

```bash
curl http://localhost:8000/history/budget
```

**Output**: Complete list of all writes to `budget` in causal order, with timestamps, agent IDs, and vector clocks.

> "Now let's time-travel. What was `budget` at the point when Agent A had done 1 write and Agent B had done 0?"

```bash
curl 'http://localhost:8000/snapshot/budget?at_clock={"agent_a":1,"agent_b":0}'
```

**Output**: `3500` (because that was A's write at that moment in causal time).

**Key Point**: "Complete immutable history. You can query any point in causal time. Perfect for auditing and debugging."

---

#### **Moment 4: Access Control (30 seconds)**

> "Now let's see access control in action. We have a 'summarizer' role that's read-only."

```bash
# Register summarizer (read-only)
curl -X POST http://localhost:8000/roles \
  -H "Content-Type: application/json" \
  -d '{
    "role_name": "summarizer",
    "can_read": ["*"],
    "can_write": []
  }'

# Summarizer tries to read (succeeds)
curl http://localhost:8000/read/budget?agent_id=summarizer&role=summarizer
# → 200 OK ✅

# Summarizer tries to write (fails)
curl -X POST http://localhost:8000/write \
  -H "Content-Type: application/json" \
  -d '{
    "key": "budget",
    "value": 999,
    "agent_id": "summarizer",
    "role": "summarizer",
    "vector_clock": {}
  }'
# → 403 Forbidden ❌
```

**Key Point**: "Fine-grained role-based access control. Wildcard patterns. Enforced at every read and write."

---

### Summary Slide (30 seconds)

> "What did we see?
>
> 1. **Problem**: Concurrent writes cause silent data loss in regular stores.
> 2. **Vector Clocks**: Engram detects concurrency using causal timestamps.
> 3. **CRDTs**: Stores all conflicting values instead of overwriting.
> 4. **Resolution**: Configurable strategies pick a winner (or flag for human).
> 5. **History**: Complete immutable audit trail with time-travel.
> 6. **Access Control**: Role-based permissions with wildcards.
>
> Engram is the middleware that sits between agents and shared state, preventing data loss and providing complete auditability."

---

## 6. OPTIONAL IMPROVEMENTS

### Short-term (Easy Wins)

1. **Complete the Demo Script** — `demo/run_demo.py` has TODO stubs. Implement all 5 moments with real HTTP calls using `httpx` or `requests`.

2. **Implement Missing Consistency Levels** — CAUSAL and STRONG reads are not yet implemented. Would require quorum-like coordination.

3. **Better Error Messages** — More specific error codes (e.g., `INSUFFICIENT_PERMISSIONS`, `CONFLICTED_VALUE`, `STALE_WRITE`).

4. **OpenAPI Schema** — FastAPI already generates it at `/docs`, but adding more detailed descriptions would help clients.

### Medium-term (Architectural)

1. **Merge Resolution Strategies** — Currently only works on single keys. Consider merging two MVRegisters without immediately resolving—useful for Byzantine agreement scenarios.

2. **Vector DB Integration** — The `chroma_adapter.py` and `pinecone_adapter.py` are placeholders. Implement semantic search on memory keys.

3. **Distributed Consensus** — Current system is single-node. Multi-node would require Raft or Paxos to coordinate vector clocks.

4. **Compression** — History log grows unbounded. Implement snapshotting: "at clock X, all keys had these values, discard earlier history."

5. **Batch Writes** — `/write` currently handles one at a time. A `/write-batch` endpoint could atomically write multiple keys.

### Long-term (Advanced)

1. **Causal Consistency at Read-Level** — If Agent A writes then Agent B reads, B should see A's write even if they're on different replicas. Requires tracking "must-have-seen" clocks.

2. **Eventual Consistency Guarantees** — Add monotonic reads, read-your-writes. Useful for agents that want weaker but more performant semantics.

3. **Garbage Collection for Conflicts** — Auto-resolve old conflicts if they haven't been touched in N days (configurable).

4. **Conflict Resolution Callbacks** — Allow agents to register custom resolution functions instead of just built-in strategies.

5. **Webhooks / Subscriptions** — Agents could subscribe to changes on specific keys. Useful for reactive updates.

### Code Quality

1. **Type Hints** — Some functions use `Any`. More specific types would improve IDE support.

2. **Logging** — Add structured logging (e.g., with `structlog`) for debugging and observability.

3. **Benchmarks** — Add timing tests to catch performance regressions. Profile the hot paths (vector clock comparison, CRDT merge).

4. **Documentation** — Add docstring examples showing how to use each class in realistic scenarios.

5. **Edge Case Tests** — Test with thousands of concurrent values, very old clocks, clocks with hundreds of agents, etc.

---

## Quick Reference: Key Concepts

| Concept               | Definition                                                                                          | Example                                                                              |
| --------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| **Vector Clock**      | Dict of agent IDs to counters. Determines causal order.                                             | `{"A": 3, "B": 1}` — Agent A has written 3 times, B once.                            |
| **Concurrent Writes** | Writes that didn't know about each other (neither vector clock dominates).                          | A has `{"A": 1}`, B has `{"B": 1}`. Neither is before the other.                     |
| **CRDT**              | Data structure that merges without requiring coordination. MVRegister stores all concurrent values. | Instead of picking A or B's value, store both and resolve later.                     |
| **Conflict**          | Multiple values exist for the same key due to concurrent writes.                                    | `budget` has both `3500` (from A) and `4200` (from B).                               |
| **Resolution**        | Strategy to pick one value when a conflict exists.                                                  | LATEST_CLOCK, LOWEST_VALUE, UNION, etc.                                              |
| **History Log**       | Immutable append-only record of all writes.                                                         | Every write creates a HistoryEntry; rollbacks don't delete, they create new entries. |
| **Time-Travel Query** | Read the value of a key at any point in causal time.                                                | "What was `budget` when A's clock was 1 and B's was 0?"                              |
| **Access Policy**     | Role-based permissions with fnmatch patterns.                                                       | `"budget-agent"` can read/write `"budget.*"` but not other keys.                     |

---

## File-by-File Summary

| File                       | Purpose                                          | Lines  | Key Methods                                                 |
| -------------------------- | ------------------------------------------------ | ------ | ----------------------------------------------------------- |
| `models.py`                | Data types (MemoryEntry, ConflictingWrite, etc.) | ~150   | Enums: Ordering, ConflictStrategy, WriteType                |
| `vector_clock.py`          | Causal ordering                                  | ~70    | `compare()`, `increment()`, `merge()`                       |
| `crdt.py`                  | Conflict storage                                 | ~180   | `write()`, `merge()`, `resolve()`, `is_conflicted()`        |
| `access_control.py`        | Role-based permissions                           | ~80    | `check_read()`, `check_write()`, `register_role()`          |
| `middleware.py`            | Orchestration                                    | ~150   | `write()`, `read()`, `rollback()`                           |
| `api.py`                   | HTTP routes                                      | ~120   | `POST /write`, `GET /read`, `GET /history`, `GET /snapshot` |
| `history.py`               | Audit trail                                      | ~90    | `append()`, `get_history()`, `get_snapshot()`               |
| `storage/base.py`          | Storage interface                                | ~70    | Abstract methods: `read()`, `write()`, `read_history()`     |
| `storage/memory.py`        | In-memory adapter                                | ~60    | Simple dict-based storage                                   |
| `storage/redis_adapter.py` | Redis adapter                                    | ~100   | Redis-backed persistence                                    |
| `tests/*.py`               | Comprehensive test suite                         | ~1000+ | Tests for each module                                       |

---

## Running the Examples

### Example 1: Simple Write and Read

```bash
# Start API (if not running)
uvicorn engram.api:app &

# Write
curl -X POST http://localhost:8000/write \
  -H "Content-Type: application/json" \
  -d '{
    "key": "greeting",
    "value": "hello",
    "agent_id": "agent1",
    "role": "admin",
    "vector_clock": {"agent1": 1}
  }'

# Read
curl 'http://localhost:8000/read/greeting?agent_id=agent1&role=admin'
```

### Example 2: Trigger a Conflict

```bash
# Register role
curl -X POST http://localhost:8000/roles \
  -H "Content-Type: application/json" \
  -d '{"role_name": "agent", "can_read": ["*"], "can_write": ["*"]}'

# Agent A writes with clock {"a": 1, "b": 0}
curl -X POST http://localhost:8000/write \
  -H "Content-Type: application/json" \
  -d '{
    "key": "counter",
    "value": 100,
    "agent_id": "a",
    "role": "agent",
    "vector_clock": {"a": 1, "b": 0}
  }'

# Agent B writes with clock {"a": 0, "b": 1} (concurrent!)
curl -X POST http://localhost:8000/write \
  -H "Content-Type: application/json" \
  -d '{
    "key": "counter",
    "value": 200,
    "agent_id": "b",
    "role": "agent",
    "vector_clock": {"a": 0, "b": 1}
  }'

# Read will show status: "conflicted" with both values
curl 'http://localhost:8000/read/counter?agent_id=a&role=agent'
```

---

## Conclusion

**Engram** is a sophisticated memory middleware that brings **CRDT conflict resolution**, **causal ordering**, and **access control** to multi-agent systems. It eliminates silent data loss by detecting concurrent writes, storing all conflicting values, and providing configurable resolution strategies—all while maintaining an immutable audit trail for complete traceability.

The architecture is **modular, extensible, and storage-agnostic**, making it suitable for production multi-agent systems that require reliability and auditability.
