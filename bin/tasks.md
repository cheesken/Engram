# Engram — Task Breakdown

Four groups. Each group owns core project code end-to-end: implementation and tests. All interfaces (method signatures, models, ABCs) are already defined, so groups can work in parallel by coding against the contracts and mocking what they need from other groups.

The demo (`demo/`) is not assigned here — it's a separate effort once the core works.

---

## Group 1 — Conflict Detection Engine

**You own:** Vector clocks and the CRDT. This is how Engram detects and resolves conflicts between concurrent agent writes.

**Your files:**
- `engram/vector_clock.py` — implement all 5 methods
- `engram/crdt.py` — implement all 5 methods/properties
- `tests/test_vector_clock.py` — fill all 12 test stubs
- `tests/test_crdt.py` — fill all 13 test stubs

**No dependencies on other groups.** Your modules only import from `engram/models.py` which is already complete.

### Tasks

- [ ] **VectorClock.increment(agent_id)** — Copy the clock dict, bump the agent's counter by 1 (default 0 if missing), return new VectorClock. Never mutate self.

- [ ] **VectorClock.merge(other)** — For every agent across both clocks, take the max counter. Return new VectorClock.

- [ ] **VectorClock.compare(other)** — This is the most important method in the project. Collect all agent IDs from both clocks. Compare each counter (missing = 0). If all equal → EQUAL. If all of self ≤ other with at least one < → BEFORE. Reverse → AFTER. Otherwise → CONCURRENT.

- [ ] **VectorClock.to_dict() / from_dict()** — Return a copy of the internal dict. Classmethod constructor from a plain dict.

- [ ] **MVRegister.write(value, agent_id, role, clock)** — Compare incoming clock against every existing value's clock. AFTER all existing → replace everything. CONCURRENT with any → keep conflicting values + add new one. BEFORE any existing → discard (stale). Empty register → just add. Return new MVRegister.

- [ ] **MVRegister.merge(other)** — Combine two registers. The result keeps only values that aren't dominated (BEFORE) by any other value across both registers.

- [ ] **MVRegister.resolve(strategy)** — Single value → return it directly. Multiple values: LATEST_CLOCK picks highest clock sum (tie-break by timestamp), LOWEST/HIGHEST_VALUE picks by numeric comparison, UNION returns all as a list, FLAG_FOR_HUMAN returns None + all values as conflicts. Returns `(resolved_value, losing_writes)`.

- [ ] **MVRegister.is_conflicted()** — `len(self._values) >= 2`

- [ ] **MVRegister.values** (property) — Return a copy of `self._values`.

- [ ] **Write all vector clock tests** — increment (new agent, existing agent, preserves others), merge (max values, no mutation, with empty), compare (equal, before, after, concurrent, empty clocks, disjoint agents), to_dict/from_dict roundtrip.

- [ ] **Write all CRDT tests** — write to empty register, supersede when after, concurrent creates conflict, stale discarded, no mutation, merge diverged registers, resolve with each strategy, is_conflicted true/false.

### How to verify you're done

```bash
pytest tests/test_vector_clock.py tests/test_crdt.py -v
```

---

## Group 2 — Permissions & In-Memory Storage

**You own:** The access control system and the in-memory storage backend. Every read and write in the system passes through your permission check, and the default storage adapter that all tests and development run against is yours.

**Your files:**
- `engram/access_control.py` — implement all 5 methods
- `engram/storage/memory.py` — implement all 7 methods
- `tests/test_access_control.py` — fill all 10 test stubs
- `tests/test_storage.py` — fill all 9 test stubs

**No dependencies on other groups.** AccessPolicy uses only `fnmatch` (stdlib). InMemoryAdapter uses only `engram/models.py` and Python dicts.

### Tasks

- [ ] **AccessPolicy.register_role(name, can_read, can_write)** — Store as a `Role` dataclass in `self._roles[name]`. Overwrite if exists.

- [ ] **AccessPolicy.check_read(role, key)** — Lookup role (not found → False). If `"*"` in can_read → True. Otherwise `fnmatch.fnmatch(key, pattern)` for each pattern. Any match → True.

- [ ] **AccessPolicy.check_write(role, key)** — Same as check_read but against can_write. Empty can_write → always False.

- [ ] **AccessPolicy.get_role(name) / list_roles()** — Dict lookup. Return Role or None. List all keys.

- [ ] **InMemoryAdapter.write(entry)** — `with self._lock: self._store[entry.key] = entry`

- [ ] **InMemoryAdapter.read(key)** — `with self._lock: return self._store.get(key)`

- [ ] **InMemoryAdapter.write_history(entry)** — `with self._lock: self._history.append(entry)`

- [ ] **InMemoryAdapter.read_history(key, agent_id, since, until)** — Filter `self._history` by key, then optionally by agent_id, since (>=), until (<=). Return matches in insertion order.

- [ ] **InMemoryAdapter.delete(key)** — `with self._lock: self._store.pop(key, None)`

- [ ] **InMemoryAdapter.list_keys(prefix)** — Return sorted keys from `self._store`, filtered by `key.startswith(prefix)` if prefix given.

- [ ] **InMemoryAdapter.ping()** — Return `True`.

- [ ] **Write all access control tests** — register/get/overwrite roles, check_read with wildcard/specific/fnmatch/unknown role, check_write admin/reader/writer, list_roles.

- [ ] **Write all storage tests** — write/read/overwrite, read missing key, delete, delete nonexistent, list_keys with and without prefix, write/read history with filters, ping.

### How to verify you're done

```bash
pytest tests/test_access_control.py tests/test_storage.py -v
```

---

## Group 3 — History & Redis Persistence

**You own:** The append-only audit trail (including time-travel queries and rollback logic) and the Redis storage backend for production use. You're responsible for everything that makes Engram data durable and recoverable.

**Your files:**
- `engram/history.py` — implement all 5 methods
- `engram/storage/redis_adapter.py` — implement all 7 methods
- `tests/test_history.py` — fill all 10 test stubs
- New: add Redis-specific tests to `tests/test_storage.py` or a new `tests/test_redis.py`

**Dependencies:** `history.py` uses `VectorClock.compare()` and `VectorClock.from_dict()` from Group 1. You can mock these while waiting — they return an `Ordering` enum, easy to stub. `redis_adapter.py` has no dependency on other groups.

### Mocking strategy while waiting

```python
# For get_snapshot, mock VectorClock.compare to return Ordering.BEFORE
# That lets you test the filtering/sorting logic without the real implementation
# Swap in the real VectorClock once Group 1 delivers
```

### Tasks

**History:**

- [ ] **HistoryLog.append(entry)** — `self._log.append(entry)`. If `self._storage` is set, also call `self._storage.write_history(entry)` for persistence.

- [ ] **HistoryLog.get_history(key, agent_id, since, until)** — Filter `self._log`: match key, then optionally agent_id, since (timestamp >=), until (timestamp <=). Return oldest-first.

- [ ] **HistoryLog.get_entry(write_id)** — Linear scan `self._log` for matching write_id. Return entry or None.

- [ ] **HistoryLog.get_snapshot(key, at_clock)** — Filter entries for key. For each, build a VectorClock from the entry's clock and compare against `VectorClock.from_dict(at_clock)`. Keep entries where result is BEFORE or EQUAL. Return the one with latest timestamp. Return None if nothing qualifies.

- [ ] **HistoryLog.create_rollback_entry(write_id, agent_id, role)** — Find original via get_entry (raise ValueError if missing). Build new HistoryEntry: new uuid, same key+value, caller's agent_id+role, copy of original's clock, write_type=ROLLBACK, rollback_of=write_id. Don't append — just return it.

**Redis:**

- [ ] **RedisAdapter.write(entry)** — `SET engram:memory:{entry.key}` with `entry.model_dump_json()`.

- [ ] **RedisAdapter.read(key)** — `GET engram:memory:{key}`. Return `MemoryEntry.model_validate_json(raw)` or None.

- [ ] **RedisAdapter.write_history(entry)** — `RPUSH engram:history:{entry.key}` with `entry.model_dump_json()`.

- [ ] **RedisAdapter.read_history(key, agent_id, since, until)** — `LRANGE engram:history:{key} 0 -1`. Deserialize each element. Apply filters in Python.

- [ ] **RedisAdapter.delete(key)** — `DEL engram:memory:{key}`.

- [ ] **RedisAdapter.list_keys(prefix)** — `KEYS engram:memory:{prefix}*`. Strip the `engram:memory:` prefix from results.

- [ ] **RedisAdapter.ping()** — `self._client.ping()` in a try/except. Return True/False.

- [ ] **Write all history tests** — append/get_entry, get_history with filters (agent_id, since, until, empty), get_snapshot (before, concurrent excluded, none qualify), create_rollback_entry (success, unknown write_id raises).

- [ ] **Write Redis tests** — Same scenarios as InMemoryAdapter tests but against Redis. Use `pytest.mark.skipif` to skip when Redis isn't running. Needs `docker compose up -d` first.

### How to verify you're done

```bash
pytest tests/test_history.py -v
docker compose up -d && pytest tests/test_redis.py -v
```

---

## Group 4 — Middleware & API Integration

**You own:** The middleware pipeline that wires every component together, and the API-level tests that prove the whole system works end-to-end. Without your `write()`, `read()`, and `rollback()` methods, the API routes return nothing. You are the integration point where Groups 1, 2, and 3 come together.

**Your files:**
- `engram/middleware.py` — implement `write()`, `read()`, `rollback()`
- `tests/test_api.py` — fill all 12 test stubs

**Dependencies:** You call into everything — VectorClock, MVRegister, AccessPolicy, StorageAdapter, HistoryLog. You can mock all of them while Groups 1-3 are working. The interfaces are fully defined. Swap in real implementations as they deliver.

### Mocking strategy while waiting

```python
# Mock AccessPolicy.check_write → return True
# Mock VectorClock.compare → return Ordering.BEFORE (no conflict case)
# Mock InMemoryAdapter with a real instance (Group 2's is simple enough
#   that you can implement a minimal version yourself for testing)
# Mock HistoryLog.append → no-op
# This lets you build and test the pipeline structure before the real parts land
```

### Tasks

- [ ] **EngramMiddleware.write(request)** — The most complex method in the project. Full pipeline:
  1. `access_policy.check_write(role, key)` → 403 if denied
  2. Build `VectorClock.from_dict(request.vector_clock)`
  3. `clock.increment(request.agent_id)`
  4. `storage.read(key)` to get existing entry
  5. If existing: `VectorClock(existing.vector_clock).compare(incoming_clock)`
     - BEFORE or EQUAL → safe to overwrite
     - AFTER → stale write → raise HTTPException(409)
     - CONCURRENT → conflict:
       - Build MVRegister, add both values
       - Call `resolve(request.conflict_strategy)`
       - Set `status=CONFLICTED` if values remain
       - Set `status=FLAGGED` if strategy is FLAG_FOR_HUMAN
  6. Merge clocks: `incoming.merge(VectorClock(existing.vector_clock))`
  7. Build final `MemoryEntry`
  8. Build `HistoryEntry`, call `history_log.append()`
  9. Call `storage.write(entry)`
  10. Return `MemoryEntry`

- [ ] **EngramMiddleware.read(key, request)** — Pipeline:
  1. `access_policy.check_read(role, key)` → 403 if denied
  2. `storage.read(key)` → 404 if None
  3. If consistency is EVENTUAL → return immediately
  4. If CAUSAL → raise NotImplementedError (with docstring explaining what it would do)
  5. If STRONG → raise NotImplementedError (with docstring explaining what it would do)

- [ ] **EngramMiddleware.rollback(write_id, request)** — Pipeline:
  1. `history_log.get_entry(write_id)` → 404 if None
  2. `access_policy.check_write(role, original_entry.key)` → 403 if denied
  3. `history_log.create_rollback_entry(write_id, agent_id, role)` → builds new HistoryEntry
  4. `history_log.append(rollback_entry)`
  5. Build new `MemoryEntry` from rollback entry's value and metadata
  6. `storage.write(new_entry)`
  7. Return new `MemoryEntry`

- [ ] **Write all API tests** — Use the `client` fixture from conftest.py. These are integration tests that exercise the full stack:
  - POST /write → creates entry, returns MemoryEntry
  - POST /write with read-only role → 403
  - GET /read/{key} → returns stored entry
  - GET /read/{key} for missing key → 404
  - GET /history/{key} → returns history list
  - POST /rollback/{write_id} → restores previous value
  - POST /rollback with unknown write_id → 404
  - POST /roles → registers role
  - GET /roles/{name} → returns role
  - GET /roles/{name} for unknown → 404
  - GET /keys → returns all keys
  - GET /health → returns status with storage type and version
  - WS /ws/memory → accepts and returns not_implemented

### After middleware lands: Demo & Live Dashboard

Once your middleware methods work and the other groups have merged, you also own the demo and real-time layer. The demo agents make real HTTP calls through your middleware — this is integration, not a mockup.

**WebSocket server (`engram/api.py`):**

- [ ] **Build `ConnectionManager` class** — A `set` of active WebSocket connections. Methods: `connect(ws)`, `disconnect(ws)`, `broadcast(data: dict)` sends JSON to all connected clients.

- [ ] **Replace `/ws/memory` stub** — Accept connection via manager. Keep alive in a loop. On disconnect, remove from manager.

- [ ] **Wire broadcast into POST /write route** — After `middleware.write()` returns, call `manager.broadcast(entry.model_dump())`.

**Agent clients (`demo/agents.py`):**

- [ ] **FlightAgent.search_flights(destination, dates)** — Hardcode flight results, call `self.write("flights", results)`.

- [ ] **HotelAgent.search_hotels(destination, dates)** — Hardcode hotel results, call `self.write("hotels", results)`.

- [ ] **BudgetAgent.set_budget(amount)** — Call `self.write("budget", amount)`.

- [ ] **Summarizer.summarize()** — Read all keys via `self.read()`, print formatted summary.

- [ ] **Summarizer.attempt_write()** — Call `self.write("budget", 0)`. Will get 403.

**Demo script (`demo/run_demo.py`):**

- [ ] **`main()` glue** — Register all roles via POST /roles at startup. Handle server-not-running gracefully.

- [ ] **Moment 1** — No API. Plain dict, show last-write-wins data loss.

- [ ] **Moment 2** — Two agents, concurrent clocks, show conflict detection.

- [ ] **Moment 3** — EVENTUAL works, CAUSAL/STRONG error with explanation.

- [ ] **Moment 4** — Read-only role blocked from writing (403).

- [ ] **Moment 5** — Write, overwrite, rollback, show history trail.

**Dashboard (`demo/ui/`):**

- [ ] **app.js — connectWebSocket()** — Uncomment existing code.

- [ ] **app.js — updateMemoryTable(entry)** — Find row by key, update or create. Apply status badge CSS class.

- [ ] **app.js — appendWriteLog(entry)** — Create log entry div, prepend to write log.

- [ ] **index.html** — Remove hardcoded placeholder rows. Tables start empty, fill via WebSocket.

### How to verify you're done

```bash
# Middleware + API tests
pytest tests/test_api.py -v

# Full demo (once all groups have merged)
uvicorn engram.api:app --reload
python demo/run_demo.py
open demo/ui/index.html   # dashboard updates in real time
```

---

## Who Blocks Whom

```
Group 1 (Conflict Engine)       ──┐
                                  ├──→ Group 4 (Middleware & Integration)
Group 2 (Permissions & Storage) ──┤
                                  │
Group 3 (History & Redis)       ──┘
```

- **Groups 1, 2, 3** — fully parallel from day one
- **Group 4** — can start with mocks immediately, swaps in real code as other groups deliver
- All groups converge at integration: `pytest -v` runs everything together

---

## Integration Checklist

Once all groups are done:

```bash
# All tests pass
pytest -v

# Server starts and responds
uvicorn engram.api:app --reload
curl http://localhost:8000/health

# Redis mode works
docker compose up -d
STORAGE_ADAPTER=redis uvicorn engram.api:app --reload
curl http://localhost:8000/health
```
