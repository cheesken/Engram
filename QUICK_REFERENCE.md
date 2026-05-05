# Engram Quick Reference Guide

A cheat sheet for presenting and understanding Engram at a glance.

---

## 🎯 The 30-Second Pitch

**Engram** is a memory middleware for multi-agent AI systems that prevents concurrent write conflicts from silently losing data. It uses **vector clocks** to detect conflicts, **CRDTs** to store all conflicting values, and configurable **resolution strategies** to pick a winner—while maintaining a complete audit trail.

---

## 🔑 Core Concepts

### Vector Clock

A dict mapping agent IDs to counters: `{"agent_a": 3, "agent_b": 1}`

- Determines causal ordering
- If neither clock dominates → **CONCURRENT** (conflict!)

### Concurrent Write

Two writes that don't know about each other (their vector clocks don't have a causal relationship).

### CRDT (Multi-Value Register)

A conflict-free replicated data type that stores ALL concurrent values instead of overwriting.

### Conflict

Multiple values exist for the same key due to concurrent writes.

### Resolution Strategy

How to pick one value from conflicting ones:

- `LATEST_CLOCK`: highest vector sum wins
- `LOWEST_VALUE` / `HIGHEST_VALUE`: numeric comparison
- `UNION`: keep all values
- `FLAG_FOR_HUMAN`: don't resolve, require human review

---

## 📊 The Full Write Pipeline (One Slide)

```
Write Request
    ↓ Permission Check (AccessPolicy)
    ↓ Vector Clock Increment
    ↓ Load Existing Value (Storage)
    ↓ Conflict Detection (compare clocks)
    ↓ Conflict Resolution (apply strategy)
    ↓ History Logging (immutable audit)
    ↓ Persistence (storage.write)
    ↓
Response with Resolved Value
```

---

## 🛡️ Three Pillars

| Pillar                  | What                                   | Why                       |
| ----------------------- | -------------------------------------- | ------------------------- |
| **Conflict Detection**  | Vector clocks detect concurrent writes | No silent data loss       |
| **Conflict Storage**    | CRDTs store all conflicting values     | All data is preserved     |
| **Conflict Resolution** | Configurable strategies + human flag   | Deterministic + auditable |

---

## 🚀 Key Features Checklist

- ✅ Detects concurrent writes (vector clocks)
- ✅ Stores all conflicting values (CRDT)
- ✅ Configurable resolution strategies
- ✅ Role-based access control (fnmatch patterns)
- ✅ Immutable audit trail (history log)
- ✅ Time-travel queries (snapshot at causal point)
- ✅ Storage-agnostic (pluggable adapters)
- ✅ HTTP API (FastAPI)
- ✅ Fully tested (pytest)

---

## 📁 File Structure (The Essentials)

```
engram/
├── models.py          ← Data types (single source of truth)
├── vector_clock.py    ← Causal ordering engine ⭐
├── crdt.py            ← Conflict storage ⭐
├── access_control.py  ← Role-based permissions
├── middleware.py      ← The orchestrator (ties everything together)
├── api.py             ← HTTP routes
├── history.py         ← Audit trail + time-travel
└── storage/           ← Pluggable storage (memory, Redis, etc.)

tests/ ← Comprehensive test suite
demo/  ← Runnable demonstrations
```

---

## 🔌 Key Endpoints

| Endpoint          | Method | Purpose                                   |
| ----------------- | ------ | ----------------------------------------- |
| `/write`          | POST   | Write a value to memory                   |
| `/read/{key}`     | GET    | Read a value (with consistency level)     |
| `/history/{key}`  | GET    | Get write history with optional filters   |
| `/snapshot/{key}` | GET    | Time-travel query: value at clock point X |
| `/roles`          | POST   | Register a role with permissions          |
| `/rollback`       | POST   | Undo a previous write                     |

---

## 💬 Speaking Points

### Opening

> "Imagine two agents managing shared state. Agent A writes `budget = 3500`. Agent B (unaware) writes `budget = 4200` at the same time. In a normal database, one silently overwrites the other—data loss with no warning. Engram detects this."

### The Problem

> "Multi-agent systems have inherent concurrency. Agents don't always see each other's writes before they write their own. 'Last write wins' leads to silent data loss."

### The Solution

> "Engram uses vector clocks to detect when two writes are concurrent (conflict). It stores both values in a CRDT instead of overwriting. When you need a value, it applies a resolution strategy—or flags it for a human to decide."

### The Benefit

> "You get data integrity (no silent loss), auditability (complete history), and flexibility (multiple resolution strategies). All without needing a global ordering service."

### Use Cases

- Multi-agent AI systems (LLM orchestration, autonomous agents)
- Collaborative editing (like Google Docs)
- Eventually consistent distributed systems (where you need to detect conflicts, not hide them)
- Audit-critical applications (complete traceability)

---

## 🎬 The 5 Moments (Executive Summary)

| Moment    | What                                                | Duration     |
| --------- | --------------------------------------------------- | ------------ |
| **0**     | Problem Setup (two agents, concurrent writes)       | 30s          |
| **1**     | Conflict Detection (vector clocks + CRDT)           | 2m           |
| **2**     | History & Time-Travel (audit trail, causal queries) | 1m           |
| **3**     | Access Control (role-based permissions)             | 30s          |
| **4**     | Consistency Levels (eventual, causal, strong)       | 1m           |
| **5**     | Summary (recap + value proposition)                 | 1m           |
| **Total** |                                                     | ~5-6 minutes |

---

## 🧪 Quick Test Commands

### Start API

```bash
uvicorn engram.api:app --reload
```

### Run Demo

```bash
python demo/demo_presentation.py
```

### Run All Tests

```bash
pytest tests/ -v
```

### Write a Value

```bash
curl -X POST http://localhost:8000/write \
  -H "Content-Type: application/json" \
  -d '{
    "key": "budget",
    "value": 5000,
    "agent_id": "agent_a",
    "role": "admin",
    "vector_clock": {"agent_a": 1}
  }'
```

### Read a Value

```bash
curl 'http://localhost:8000/read/budget?agent_id=agent_a&role=admin'
```

### Get History

```bash
curl 'http://localhost:8000/history/budget'
```

---

## 🎓 Conflict Scenarios (Examples)

### Scenario 1: Sequential Writes (NO Conflict)

```
A writes: clock {"A": 1, "B": 0} → value: 100
B reads history, sees A's clock
B writes: clock {"A": 1, "B": 1} → value: 200

Result: NO CONFLICT (B's clock dominates A's)
Status: "ok"
Value: 200
```

### Scenario 2: Concurrent Writes (CONFLICT!)

```
A writes: clock {"A": 1, "B": 0} → value: 100
B writes: clock {"A": 0, "B": 1} → value: 200
  (B never saw A's write)

Result: CONFLICT (neither clock dominates)
Status: "conflicted"
Values: [100, 200]
Resolved: 100 or 200 (depends on strategy)
```

### Scenario 3: Stale Write (IGNORED)

```
A writes: clock {"A": 2, "B": 0} → value: 100
B writes: clock {"A": 1, "B": 0} → value: 50
  (B's clock is BEFORE A's)

Result: IGNORED (stale write)
Status: "ok"
Value: 100 (B's write discarded)
```

---

## 🔍 Comparison Matrix

| Feature             | Engram                 | Plain Dict   | Regular DB             |
| ------------------- | ---------------------- | ------------ | ---------------------- |
| Conflict Detection  | ✅ Yes (vector clocks) | ❌ No        | ❌ Last write wins     |
| Stores All Values   | ✅ CRDT                | ❌ Last only | ❌ Last only           |
| Access Control      | ✅ RBAC                | ❌ No        | ✅ Yes                 |
| Audit Trail         | ✅ Complete history    | ❌ No        | Depends                |
| Time-Travel Queries | ✅ Via vector clock    | ❌ No        | Depends                |
| Multi-Agent Ready   | ✅ Yes                 | ❌ No        | ❌ Not designed for it |

---

## 💡 Key Insights

1. **Vector clocks determine causality** — Not physical time, but "who knows about whom"
2. **Concurrent = conflicting** — If clocks don't have a causal relationship, writes might conflict
3. **CRDT = all values stored** — Nothing is thrown away; resolution is deferred
4. **Audit trail = trust** — Every write is logged immutably; complete traceability
5. **Access control + conflict resolution** — Both are first-class citizens, not afterthoughts

---

## ❓ FAQ (Quick Answers)

**Q: Why vector clocks instead of timestamps?**
A: Timestamps are about physical time. Vector clocks are about causal relationships. Two writes can have any timestamp order but still be concurrent (neither caused the other).

**Q: What if I don't want to handle conflicts?**
A: Use the `FLAG_FOR_HUMAN` strategy to mark conflicts for manual review.

**Q: Is Engram a database?**
A: No, it's a middleware. It sits between your agents and any storage backend (memory, Redis, etc.).

**Q: Can Engram handle distributed deployments?**
A: Currently single-node. Multi-node would require consensus (Raft/Paxos) for vector clock coordination.

**Q: What's the performance impact?**
A: Vector clock comparison is O(N) where N = number of agents. CRDT merge is O(M) where M = number of conflicting values. Fast in practice for typical scenarios.

**Q: How do I debug conflicts?**
A: Use `/history/{key}` to see all writes and `/snapshot/{key}?at_clock=...` to see state at any point.

---

## 🎯 Talking Points by Audience

### For Managers

- Prevents data loss in distributed systems
- Complete audit trail for compliance
- Deterministic conflict resolution reduces support tickets
- Pluggable architecture means you can start simple and scale

### For Engineers

- Vector clocks + CRDTs = proven distributed systems concepts
- Clean separation of concerns (storage, access control, history)
- Fully tested with comprehensive suite
- FastAPI = easy to integrate, good performance
- Pluggable storage = future-proof

### For Data Scientists / AI Teams

- Agents can write concurrently without coordination
- Conflicts are detected and preserved, not hidden
- You decide how to resolve conflicts (latest, highest, union, etc.)
- Complete history for debugging agent decisions

---

## 📚 Further Reading

- See [CODEBASE_WALKTHROUGH.md](./CODEBASE_WALKTHROUGH.md) for detailed architecture
- See [README.md](./README.md) for user-facing documentation
- See [tests/](./tests/) for comprehensive examples and edge cases
- See [demo/demo_presentation.py](./demo/demo_presentation.py) for runnable demo

---

## 🚦 Status Legend

✅ = Working & tested
⚠️ = Partial or in progress
❌ = Not implemented
ⓘ = Not yet, but planned

---

## 📞 Support

**Problem**: API won't start
**Solution**: Make sure Redis is running (if using redis adapter) or switch to memory adapter

**Problem**: Tests fail
**Solution**: Ensure Python 3.11+, run `pip install -r requirements.txt`

**Problem**: Conflicts appear unexpectedly
**Solution**: Check vector clocks. If neither dominates, it's concurrent (expected behavior).

**Problem**: Access denied on reads
**Solution**: Register your role and ensure it has `can_read` permissions for the key pattern

---

## ⏱️ Timing for Different Presentations

- **Elevator Pitch (2 min)**: Use "The 30-Second Pitch" + Problem/Solution
- **Technical Talk (20 min)**: Full walkthrough + code walkthrough + Q&A
- **Demo (5 min)**: Run demo_presentation.py, show the 5 moments
- **Workshop (2 hours)**: Full deep dive into code, write tests, extend features

---

## 🎓 Learning Path

1. **Beginner**: Read this quick reference + the "30-second pitch"
2. **Intermediate**: Run the demo (`demo_presentation.py`)
3. **Advanced**: Read CODEBASE_WALKTHROUGH.md + review code
4. **Expert**: Write custom resolution strategies + storage adapters

---

**Last Updated**: May 2026
**Project**: Engram v0.1.0
