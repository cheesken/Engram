# What's Going On — Developer Reference

## Table of Contents

- [What Is Engram?](#what-is-engram)
- [How A Write Works](#how-a-write-works)
- [How A Read Works](#how-a-read-works)
- [How A Rollback Works](#how-a-rollback-works)
- [Understanding Vector Clock Comparisons](#understanding-vector-clock-comparisons)
- [What Each File Does and What Needs Implementing](#what-each-file-does-and-what-needs-implementing)
  - [models.py](#engrammodelspy--done)
  - [vector_clock.py](#engramvector_clockpy--needs-implementing)
  - [access_control.py](#engramaccess_controlpy--needs-implementing)
  - [storage/memory.py](#engramstoragememorypy--needs-implementing)
  - [history.py](#engramhistorypy--needs-implementing)
  - [crdt.py](#engramcrdtpy--needs-implementing)
  - [middleware.py](#engrammiddlewarepy--partially-done)
  - [storage/redis_adapter.py](#engramstorageredis_adapterpy--needs-implementing-phase-2)
  - [api.py](#engramapipy--done)
  - [tests/](#tests--needs-implementing)
- [The Live Demo](#the-live-demo--what-needs-to-happen)
  - [Agent Clients](#demoagentspy--agent-http-clients)
  - [Demo Script](#demorun_demopy--the-five-moments)
  - [Browser Dashboard](#demoui--browser-dashboard)
- [Implementation Order](#implementation-order)
- [Quick Commands](#quick-commands)

---

## What Is Engram?

Engram is shared memory for AI agents. Multiple agents read and write to the same keys — like a shared whiteboard. The problem is: if two agents update the same key at the same time without knowing about each other's changes, one silently gets erased.

Engram prevents that. Every write carries a **vector clock** that tracks what each agent has seen. When two writes happen independently, Engram knows they conflict and handles it — either auto-resolving or flagging for review. Every write is logged forever, so you can roll back or time-travel to any point.

---

## How A Write Works

Say `budget-agent-1` wants to write `budget = 5000`. Here's what happens step by step, and which file handles each step.

### Step 1: The request hits the API

The agent sends `POST /write` with a JSON body. **`engram/api.py`** receives it, parses it into a `WriteRequest`, and passes it to the middleware.

### Step 2: Permission check

**`engram/middleware.py`** → `write()` calls **`engram/access_control.py`** → `check_write("budget-agent", "budget")`.

AccessPolicy looks up the role, checks if any of its `can_write` patterns match the key (using fnmatch — so `"budget.*"` matches `"budget.flights"`). If no match, the agent gets a 403 and the write stops here.

### Step 3: Vector clock update

**`engram/middleware.py`** builds a `VectorClock` from the request and calls **`engram/vector_clock.py`** → `increment("budget-agent-1")`. This bumps the agent's counter by 1. The clock now represents "budget-agent-1 has made this many writes."

### Step 4: Check for conflicts

**`engram/middleware.py`** reads the existing entry for this key from **`engram/storage/`**. If there's already a value stored, it compares the two vector clocks to figure out the relationship.

This is where it gets interesting. See [Understanding Vector Clock Comparisons](#understanding-vector-clock-comparisons) below.

### Step 5: If conflict, resolve it

If the clocks are **concurrent** (a conflict), **`engram/middleware.py`** uses **`engram/crdt.py`** → `MVRegister` to store both values, then calls `resolve(strategy)` to pick a winner based on the chosen strategy (e.g., highest value, latest clock, or flag for human).

### Step 6: Log it forever

**`engram/middleware.py`** creates a `HistoryEntry` and appends it to **`engram/history.py`** → `HistoryLog`. This log is append-only — entries are never modified or deleted. Rollbacks are new entries that point back to the old one.

### Step 7: Persist it

**`engram/middleware.py`** calls **`engram/storage/`** → `write(entry)` to save the final `MemoryEntry`. The storage adapter could be an in-memory dict, Redis, or anything that implements the interface.

### Step 8: Return the result

The `MemoryEntry` goes back through **`engram/api.py`** to the agent as JSON.

---

## How A Read Works

Say `summarizer-1` wants to read the `budget` key.

### Step 1: The request hits the API

The agent sends `GET /read/budget?agent_id=summarizer-1&role=summarizer`. **`engram/api.py`** parses the query params into a `ReadRequest` and passes it to the middleware.

### Step 2: Permission check

**`engram/middleware.py`** → `read()` calls **`engram/access_control.py`** → `check_read("summarizer", "budget")`. Same fnmatch logic as writes. If the role can't read this key → 403.

### Step 3: Fetch from storage

**`engram/middleware.py`** calls **`engram/storage/`** → `read("budget")`. If the key doesn't exist → 404.

### Step 4: Apply consistency level

This is where the three consistency levels differ:

- **EVENTUAL** — Just return what's in storage. No extra checks. This is the default and the simplest to implement.

- **CAUSAL** — Before returning, verify that the stored entry's vector clock doesn't violate causal ordering relative to what this agent has already seen. If agent A read a value at clock `{"A": 3}` and now storage returns clock `{"A": 2}`, that's a causal violation — the agent would be going backwards in time. *Not yet implemented — raises NotImplementedError.*

- **STRONG** — Coordinate with all agents/nodes to confirm no pending writes exist for this key before returning. Guarantees the latest value globally, not just locally. *Not yet implemented — raises NotImplementedError.*

### Step 5: Return the result

The `MemoryEntry` goes back through **`engram/api.py`** to the agent as JSON. If the entry has `status: "conflicted"`, the response includes `conflicting_writes` so the agent can see all the concurrent values.

---

## How A Rollback Works

Say `budget-agent-1` accidentally wrote `budget = 9999` and wants to go back to the previous value of `5000`. Rollback doesn't delete anything — it creates a *new* write that restores an old value.

### Step 1: The request hits the API

The agent sends `POST /rollback/{write_id}` where `write_id` is the ID of the *original* entry they want to restore (the one that had `budget = 5000`). The body contains `initiating_agent_id` and `initiating_role`.

### Step 2: Find the original entry

**`engram/middleware.py`** → `rollback()` calls **`engram/history.py`** → `get_entry(write_id)` to find the original history entry. If the write_id doesn't exist in history → 404.

### Step 3: Permission check

**`engram/middleware.py`** calls **`engram/access_control.py`** → `check_write(role, original_entry.key)`. The agent needs write permission on the key they're rolling back, not just read. If denied → 403.

### Step 4: Create the rollback entry

**`engram/middleware.py`** calls **`engram/history.py`** → `create_rollback_entry(write_id, agent_id, role)`. This builds a *new* `HistoryEntry` that:
- Has a brand new `write_id`
- Copies the `key` and `value` from the original entry (the value being restored)
- Sets `write_type = ROLLBACK`
- Sets `rollback_of = original_write_id` (a pointer back)
- Sets the `agent_id` and `role` to whoever initiated the rollback
- Gets a fresh timestamp

The original entry is **never touched**. History is immutable.

### Step 5: Append to history

**`engram/middleware.py`** appends the new rollback entry to the history log. Now the log shows: original write → bad write → rollback pointing to original.

### Step 6: Update live storage

**`engram/middleware.py`** builds a new `MemoryEntry` from the rollback entry's value and writes it to **`engram/storage/`**. The live key now holds the restored value.

### Step 7: Return the result

The new `MemoryEntry` (with the restored value) goes back to the agent.

### What the history looks like after a rollback

```
1. HistoryEntry: write_id="abc", key="budget", value=5000, write_type=WRITE
2. HistoryEntry: write_id="def", key="budget", value=9999, write_type=WRITE
3. HistoryEntry: write_id="ghi", key="budget", value=5000, write_type=ROLLBACK, rollback_of="abc"
```

Entry 3 is a new record. Entries 1 and 2 are untouched. The live value of `budget` is now `5000` again.

---

## Understanding Vector Clock Comparisons

This is the core concept. If it clicks, everything else makes sense.

A vector clock is just a dict: `{"agent-A": 3, "agent-B": 1}`. It means "I've seen 3 writes from agent-A and 1 write from agent-B."

When you compare two clocks, you're asking: **did one of these writers know about the other's work?**

### Scenario 1 — Agent B saw Agent A's write, then wrote after

```
Agent A writes budget = 5000   clock: {"A": 1}
Agent B reads, sees A's write, then writes budget = 3000
                               clock: {"A": 1, "B": 1}
```

B's clock contains everything A's clock has, plus more. So A's write is **BEFORE** B's write. B knew about A's work when it wrote. This is safe — B intentionally overwrote A. Let it through.

### Scenario 2 — Agent B has stale data

```
Agent A has written 5 times    clock: {"A": 5}
Agent B tries to write with    clock: {"A": 2, "B": 1}
```

B's clock says it only saw A up to write 2, but A is already at 5. B is working with outdated info. From the perspective of B's incoming write, the existing entry (A's) is **AFTER** B — meaning B is trying to overwrite something newer than what it knows about. Reject with 409.

### Scenario 3 — Neither agent saw the other

```
Agent A writes budget = 5000   clock: {"A": 1}
Agent B writes budget = 3000   clock: {"B": 1}
```

A doesn't know about B. B doesn't know about A. Neither clock contains the other. This is **CONCURRENT** — a genuine conflict. Both values are real, neither is stale. This is what the CRDT handles.

### Scenario 4 — Same clock

```
clock: {"A": 1, "B": 2}  vs  clock: {"A": 1, "B": 2}
```

Identical. **EQUAL**. Same causal point in time.

### The Rule

Compare every agent's counter in both clocks (missing agent = 0):
- All of mine ≤ all of yours, at least one less → I'm **BEFORE** you
- All of yours ≤ all of mine, at least one less → I'm **AFTER** you
- Some of mine higher AND some of yours higher → **CONCURRENT** (conflict)
- All equal → **EQUAL**

---

## What Each File Does and What Needs Implementing

### `engram/models.py` — DONE

Defines every data type in the project. Nothing to implement.

Other files import `MemoryEntry`, `HistoryEntry`, `WriteRequest`, `ReadRequest`, `ConflictStrategy`, `Ordering`, etc. from here. If you need to understand what fields an object has, look here.

---

### `engram/vector_clock.py` — NEEDS IMPLEMENTING

Every write carries a vector clock. The middleware uses it to detect conflicts. The history module uses it for time-travel queries.

**What to implement:**

- **`increment(agent_id)`** — Return a new clock with that agent's counter +1. Don't touch `self`. Agent not in clock yet → starts at 0 then becomes 1.

- **`merge(other)`** — Return a new clock taking the max of each agent's counter across both clocks. Used when combining clocks after resolving a conflict.

- **`compare(other)`** — Return an `Ordering` enum. See the comparison rules above. This is the most important method in the project.

- **`to_dict()` / `from_dict()`** — Serialization helpers.

**Depends on:** `engram.models.Ordering`
**Used by:** `crdt.py`, `history.py`, `middleware.py`

---

### `engram/access_control.py` — NEEDS IMPLEMENTING

Agents have roles. A summarizer shouldn't change the budget. Every read/write goes through here first.

**What to implement:**

- **`register_role(name, can_read, can_write)`** — Store a `Role`. Overwrite if exists.

- **`check_read(role, key)` / `check_write(role, key)`** — Look up role, check if any pattern matches the key using `fnmatch.fnmatch()`. `"*"` matches everything. `"budget.*"` matches `"budget.flights"`. Unknown role → deny. Empty `can_write` → always deny writes.

- **`get_role(name)`** — Return `Role` or `None`.

- **`list_roles()`** — Return all registered role names.

**Depends on:** `engram.models.RoleDefinition`
**Used by:** `middleware.py`

---

### `engram/storage/memory.py` — NEEDS IMPLEMENTING

Default storage backend. Python dict + threading lock. No external dependencies. This is what tests and demos run against.

**What to implement:**

All 7 `StorageAdapter` methods — `write`, `read`, `write_history`, `read_history`, `delete`, `list_keys`, `ping`. Each is dict/list operations wrapped in `with self._lock:`. `ping()` just returns `True`.

**Depends on:** `engram.storage.base.StorageAdapter`
**Used by:** `middleware.py` via `get_storage_adapter()`

---

### `engram/history.py` — NEEDS IMPLEMENTING

Immutable audit trail. Every write is recorded. Supports time-travel queries and rollback.

`HistoryLog` takes an optional `storage` argument. If provided, `append()` also calls `storage.write_history(entry)` to persist history for durability. If `None` (tests, dev), history lives only in memory. The middleware doesn't need to think about this — it just calls `history_log.append()` and persistence is handled internally.

**What to implement:**

- **`append(entry)`** — Add to `self._log`. If `self._storage` is set, also call `self._storage.write_history(entry)`.

- **`get_history(key, agent_id?, since?, until?)`** — Filter `self._log` by key, then optionally by agent_id / timestamp range. Return oldest-first.

- **`get_entry(write_id)`** — Find by write_id. Return `None` if missing.

- **`get_snapshot(key, at_clock)`** — Time-travel. Find entries for this key whose clock is `BEFORE` or `EQUAL` to `at_clock`. Return the one with the latest timestamp. Uses `VectorClock.compare()`.

- **`create_rollback_entry(write_id, agent_id, role)`** — Find the original entry, build a new `HistoryEntry` copying its value but with `write_type=ROLLBACK` and `rollback_of=original_write_id`. Don't append — the middleware does that.

**Depends on:** `vector_clock.py`, `engram.models`
**Used by:** `middleware.py`, `api.py`

---

### `engram/crdt.py` — NEEDS IMPLEMENTING

When two agents write the same key concurrently, the MVRegister holds both values until resolution.

**What to implement:**

- **`write(value, agent_id, role, clock)`** — Compare incoming clock against every existing value's clock. AFTER all → replace everything. CONCURRENT with any → keep both. BEFORE any → discard. Return new `MVRegister`.

- **`merge(other)`** — Combine two registers. Keep only values not dominated by any other.

- **`resolve(strategy)`** — Apply strategy, return `(winner, losers)`:
  - `LATEST_CLOCK` → highest sum of counters, tie-break by timestamp
  - `LOWEST_VALUE` / `HIGHEST_VALUE` → numeric comparison
  - `UNION` → keep everything as a list
  - `FLAG_FOR_HUMAN` → return `None`, all values as conflicts

  If only one value exists, return it directly regardless of strategy.

- **`is_conflicted()`** — `len(self._values) >= 2`

- **`values`** (property) — Copy of `self._values`.

**Depends on:** `vector_clock.py`, `engram.models`
**Used by:** `middleware.py`

---

### `engram/middleware.py` — PARTIALLY DONE

The brain. Wires everything together.

**Already done:** `Settings`, `get_storage_adapter()`, `__init__()`.

**What to implement:**

- **`write(request)`** — The full write pipeline described in [How A Write Works](#how-a-write-works).

- **`read(key, request)`** — The full read pipeline described in [How A Read Works](#how-a-read-works). `CAUSAL`/`STRONG` raise `NotImplementedError` for now.

- **`rollback(write_id, request)`** — The full rollback pipeline described in [How A Rollback Works](#how-a-rollback-works).

**Depends on:** everything
**Used by:** `api.py`

---

### `engram/storage/redis_adapter.py` — NEEDS IMPLEMENTING (Phase 2)

Same interface as `InMemoryAdapter` but backed by Redis. Keys: `engram:memory:{key}` for live data, `engram:history:{key}` for history lists. Serialize with `model_dump_json()`, deserialize with `model_validate_json()`.

---

### `engram/api.py` — DONE

All routes wired. Nothing to implement unless adding new endpoints. The WebSocket `/ws/memory` is a stub — see the [Browser Dashboard](#demoui--browser-dashboard) section below.

---

### `tests/` — NEEDS IMPLEMENTING

`conftest.py` has 5 ready fixtures: `memory_storage`, `access_policy` (admin/reader/writer), `history_log`, `middleware`, `client` (FastAPI TestClient).

Each test file has one working example test and 5-12 stubs with docstrings explaining what to assert — except `test_api.py`, which is all stubs (12 total, no example). Fill them in following the examples in the other test files.

---

## The Live Demo — What Needs To Happen

The demo has three parts: a script, agent clients, and a browser dashboard. All three are stubbed.

### `demo/agents.py` — Agent HTTP Clients

`EngramClient` is the base class — it's **already fully implemented**. It wraps `httpx` calls to `POST /write`, `GET /read/{key}`, `GET /history/{key}`, and `POST /rollback/{write_id}`.

Four agents inherit from it. Each has demo methods that need implementing:

- **`FlightAgent.search_flights(destination, dates)`** — Simulate a flight search (hardcoded results are fine). Write results to the `"flights"` key using `self.write()`.

- **`HotelAgent.search_hotels(destination, dates)`** — Same idea but for hotels, writes to `"hotels"` key.

- **`BudgetAgent.set_budget(amount)`** — Write the amount to the `"budget"` key.

- **`Summarizer.summarize()`** — Read `"flights"`, `"hotels"`, `"budget"` keys and print a formatted summary.

- **`Summarizer.attempt_write()`** — Try to write to `"budget"`. This should fail with 403 because the summarizer role is read-only. The point is to show access control working.

### `demo/run_demo.py` — The Five Moments

This script runs against a live Engram server (`uvicorn engram.api:app`). Each moment is a function that demonstrates a capability. They run in order.

**Moment 1: `moment_1_conflict_without_engram()`**
No API calls. Just simulate two agents writing to a plain Python dict to show how the last write silently erases the first. This is the "before" picture.

**Moment 2: `moment_2_conflict_with_engram()`**
The same scenario but through Engram. Register roles via `POST /roles`. Have two agents write to `"budget"` with concurrent clocks (`{"A": 1}` and `{"B": 1}`). Show that Engram detected the conflict and resolved it.

**Moment 3: `moment_3_consistency_levels()`**
Write a value with `EVENTUAL` consistency. Read it back with `EVENTUAL` (works). Try `CAUSAL` and `STRONG` reads (should error for now). Show the difference.

**Moment 4: `moment_4_access_violation()`**
Register the summarizer as read-only. Show a successful read. Then attempt a write and show the 403 rejection.

**Moment 5: `moment_5_rollback()`**
Write `budget = 5000`. Then overwrite with `budget = 9999` (simulating a mistake). Get history, find the write_id of the 5000 entry. Call `POST /rollback/{write_id}`. Read back budget and confirm it's 5000 again. Show the history now has a ROLLBACK entry.

### `demo/ui/` — Browser Dashboard

A static HTML page (`index.html`) + vanilla JS (`app.js`). Three panels:

- **Live Memory** (left) — table showing key, value, agent, status
- **Write Log** (center) — scrolling list of write events
- **Agent Status** (right) — four agents with green/red status dots

Currently shows **hardcoded placeholder data**. To make it live, two things need to happen:

**Server side — `engram/api.py` → `/ws/memory`:**

The WebSocket endpoint currently accepts a connection and immediately closes. It needs to:
1. Maintain a set of connected clients (connection manager pattern — a class that tracks active WebSocket connections)
2. When `middleware.write()` completes, broadcast the resulting `MemoryEntry` as JSON to every connected client
3. Handle client disconnect gracefully (remove from the set, don't crash)

The broadcast hook needs to be wired into `middleware.write()` — either the middleware calls a callback after each write, or the API route does it after calling `middleware.write()`.

**Client side — `demo/ui/app.js`:**

Three functions need implementing:

- **`connectWebSocket()`** — The code is already written but commented out. Uncomment it. It opens a WebSocket to `ws://localhost:8000/ws/memory`, toggles the status dot green/red, and auto-reconnects after 3 seconds on disconnect.

- **`updateMemoryTable(entry)`** — Receives a `MemoryEntry` JSON from the WebSocket. Find the `<tr>` in `#memory-table` where the key column matches `entry.key`. If found, update value/agent/status cells. If not found, create a new row. Apply the right CSS class: `status-ok`, `status-conflicted`, or `status-flagged`.

- **`appendWriteLog(entry)`** — Create a `.log-entry` div with the timestamp, action label (WRITE / CONFLICT / ROLLBACK / DENIED based on `entry.status` and `entry.write_type`), and detail text. Prepend it to `#write-log` so newest entries appear at top.

---

## Implementation Order

Each step depends on the ones before it.

```
 1. vector_clock.py              ← everything depends on this
 2. access_control.py            ← simple, no deps on other engram modules
 3. storage/memory.py            ← needed to test anything
 4. history.py                   ← depends on vector_clock
 5. crdt.py                      ← depends on vector_clock
 6. middleware.py (write/read/rollback) ← wires 1-5 together
 7. tests/                       ← validate everything above
 8. storage/redis_adapter.py     ← production storage
 9. demo/agents.py + run_demo.py ← demo script
10. api.py websocket + demo/ui/  ← live dashboard
```

After each step, run `pytest` on the relevant test file to validate.

---

## Quick Commands

```bash
uvicorn engram.api:app --reload          # start server (in-memory)
docker compose up -d                     # start Redis
pytest                                   # run all tests
pytest tests/test_vector_clock.py -v     # run one test file
python demo/run_demo.py                  # run demo (server must be running)
open demo/ui/index.html                  # open dashboard in browser
```
