# Engram Testing & Verification Guide

How to test Engram, write new tests, and verify core concepts.

---

## 1. Running Tests

### Quick Start

```bash
# Navigate to project root
cd /Users/gayathri/Documents/SJSU/273/Engram

# Activate virtual environment (if not already active)
source .venv/bin/activate

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_crdt.py -v

# Run specific test
pytest tests/test_crdt.py::test_mvregister_write_concurrent -v

# Run with coverage
pytest tests/ --cov=engram --cov-report=html

# Run with output (print debugging)
pytest tests/ -v -s
```

### Test Organization

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures and configuration
├── test_vector_clock.py           # VectorClock unit tests
├── test_crdt.py                   # MVRegister unit tests
├── test_access_control.py         # AccessPolicy unit tests
├── test_api.py                    # HTTP endpoint tests
├── test_history.py                # HistoryLog unit tests
├── test_storage.py                # Storage adapter tests
├── test_redis.py                  # Redis-specific tests
└── test_e2e_budget_conflict.py   # End-to-end scenario test
```

---

## 2. Understanding Test Fixtures

### Key Fixtures (from `conftest.py`)

```python
@pytest.fixture
def vector_clock_a():
    """A sample vector clock for agent A."""
    return VectorClock({"a": 1, "b": 0})

@pytest.fixture
def vector_clock_b():
    """A sample vector clock for agent B."""
    return VectorClock({"a": 0, "b": 1})

@pytest.fixture
def memory_adapter():
    """In-memory storage adapter."""
    return InMemoryAdapter()

@pytest.fixture
def access_policy():
    """AccessPolicy with predefined roles."""
    policy = AccessPolicy()
    policy.register_role("admin", can_read=["*"], can_write=["*"])
    policy.register_role("budget-agent", can_read=["budget.*"], can_write=["budget.*"])
    return policy
```

### Using Fixtures in Tests

```python
def test_vector_clock_increment(vector_clock_a):
    """Test that incrementing works."""
    new_clock = vector_clock_a.increment("a")
    assert new_clock.clock == {"a": 2, "b": 0}
    # Original is unchanged (immutability test)
    assert vector_clock_a.clock == {"a": 1, "b": 0}
```

---

## 3. Unit Test Examples

### Testing Vector Clocks

```python
# test_vector_clock.py

def test_compare_equal(vector_clock_a):
    """Same clock should compare as EQUAL."""
    clock_b = VectorClock({"a": 1, "b": 0})
    assert vector_clock_a.compare(clock_b) == Ordering.EQUAL

def test_compare_before(vector_clock_a):
    """Clock with higher counters should be AFTER."""
    clock_b = VectorClock({"a": 2, "b": 0})
    assert vector_clock_a.compare(clock_b) == Ordering.BEFORE

def test_compare_concurrent():
    """Incomparable clocks should be CONCURRENT."""
    clock_a = VectorClock({"a": 1})
    clock_b = VectorClock({"b": 1})
    assert clock_a.compare(clock_b) == Ordering.CONCURRENT

def test_increment_preserves_immutability(vector_clock_a):
    """Increment should not mutate original."""
    original = dict(vector_clock_a.clock)
    new_clock = vector_clock_a.increment("a")
    assert vector_clock_a.clock == original  # Unchanged
    assert new_clock.clock == {"a": 2, "b": 0}
```

### Testing CRDTs

```python
# test_crdt.py

def test_mvregister_write_to_empty():
    """Writing to empty register should just add the value."""
    mvr = MVRegister()
    clock = VectorClock({"a": 1})

    result = mvr.write(5000, agent_id="a", role="admin", clock=clock)

    assert result.is_conflicted() == False
    assert len(result.values) == 1
    assert result.values[0].value == 5000

def test_mvregister_write_concurrent():
    """Concurrent writes should both be stored."""
    mvr = MVRegister()

    # First write
    clock_a = VectorClock({"a": 1, "b": 0})
    mvr1 = mvr.write(5000, agent_id="a", role="admin", clock=clock_a)

    # Concurrent write
    clock_b = VectorClock({"a": 0, "b": 1})
    mvr2 = mvr1.write(4200, agent_id="b", role="admin", clock=clock_b)

    assert mvr2.is_conflicted() == True
    assert len(mvr2.values) == 2

def test_mvregister_resolve_latest_clock(mvr_with_conflict):
    """LATEST_CLOCK strategy should pick highest vector sum."""
    resolved_value, losers = mvr_with_conflict.resolve(ConflictStrategy.LATEST_CLOCK)

    # Should pick one of the values
    assert resolved_value in [5000, 4200]
    # Should have one loser
    assert len(losers) == 1

def test_mvregister_resolve_union(mvr_with_conflict):
    """UNION strategy should return all values."""
    resolved_value, losers = mvr_with_conflict.resolve(ConflictStrategy.UNION)

    # Result is a list of all values
    assert isinstance(resolved_value, list)
    assert set(resolved_value) == {5000, 4200}
    # No losers (all kept)
    assert len(losers) == 0
```

### Testing Access Control

```python
# test_access_control.py

def test_check_write_wildcard(access_policy):
    """Wildcard '*' should allow all keys."""
    assert access_policy.check_write("admin", "anything") == True
    assert access_policy.check_write("admin", "some.key") == True

def test_check_write_pattern(access_policy):
    """Pattern should match according to fnmatch."""
    assert access_policy.check_write("budget-agent", "budget.flights") == True
    assert access_policy.check_write("budget-agent", "budget.hotels") == True
    assert access_policy.check_write("budget-agent", "audit.log") == False

def test_check_write_nonexistent_role(access_policy):
    """Non-existent role should be denied."""
    assert access_policy.check_write("unknown-role", "any.key") == False

def test_read_only_role(access_policy):
    """Role with empty can_write should be read-only."""
    policy = AccessPolicy()
    policy.register_role("auditor", can_read=["*"], can_write=[])

    assert policy.check_read("auditor", "budget") == True
    assert policy.check_write("auditor", "budget") == False
```

---

## 4. Integration Tests

### Testing the Middleware Pipeline

```python
# test_api.py or custom integration tests

def test_full_write_pipeline(middleware):
    """Test complete write from HTTP request to storage."""
    request = WriteRequest(
        key="budget",
        value=5000,
        agent_id="agent_a",
        role="admin",
        vector_clock={"agent_a": 1}
    )

    entry = middleware.write(request)

    assert entry.key == "budget"
    assert entry.value == 5000
    assert entry.status == MemoryStatus.OK

def test_concurrent_writes_detected(middleware):
    """Test that concurrent writes are detected."""
    # First write
    req1 = WriteRequest(
        key="counter",
        value=100,
        agent_id="a",
        role="admin",
        vector_clock={"a": 1, "b": 0}
    )
    entry1 = middleware.write(req1)
    assert entry1.status == MemoryStatus.OK

    # Concurrent write
    req2 = WriteRequest(
        key="counter",
        value=200,
        agent_id="b",
        role="admin",
        vector_clock={"a": 0, "b": 1}
    )
    entry2 = middleware.write(req2)
    assert entry2.status == MemoryStatus.CONFLICTED
    assert len(entry2.conflicting_writes) > 0
```

### Testing History

```python
# test_history.py

def test_history_append_and_retrieve(history_log):
    """Test appending to and reading from history."""
    entry1 = HistoryEntry(
        write_id="uuid-1",
        key="budget",
        value=5000,
        agent_id="a",
        role="admin",
        vector_clock={"a": 1},
        write_type=WriteType.WRITE
    )

    history_log.append(entry1)

    history = history_log.get_history(key="budget")
    assert len(history) == 1
    assert history[0].value == 5000

def test_snapshot_at_clock(history_log):
    """Test time-travel query."""
    # Append multiple entries
    entry1 = HistoryEntry(..., write_id="1", value=100, vector_clock={"a": 1})
    entry2 = HistoryEntry(..., write_id="2", value=200, vector_clock={"a": 2})

    history_log.append(entry1)
    history_log.append(entry2)

    # Query at clock {"a": 1}
    snapshot = history_log.get_snapshot("budget", at_clock={"a": 1})
    assert snapshot.value == 100
```

---

## 5. End-to-End Scenario Tests

### The Budget Conflict Scenario

```python
# test_e2e_budget_conflict.py

def test_budget_conflict_scenario():
    """
    Reproduce the classic scenario:
    Two agents writing to the same budget key concurrently.
    Engram should detect the conflict and store both values.
    """
    # Setup
    storage = InMemoryAdapter()
    access_policy = AccessPolicy()
    access_policy.register_role("budget-agent",
                                 can_read=["budget.*"],
                                 can_write=["budget.*"])
    history_log = HistoryLog(storage=storage)
    middleware = EngramMiddleware(storage, access_policy, history_log)

    # Agent A writes (time 10:00)
    req_a = WriteRequest(
        key="budget",
        value=5000,
        agent_id="agent_a",
        role="budget-agent",
        vector_clock={"agent_a": 1, "agent_b": 0}
    )
    entry_a = middleware.write(req_a)
    print(f"Agent A writes: {entry_a.value}")
    assert entry_a.status == MemoryStatus.OK

    # Agent B writes concurrently (time 10:00:01, but didn't see A's write)
    req_b = WriteRequest(
        key="budget",
        value=4200,
        agent_id="agent_b",
        role="budget-agent",
        vector_clock={"agent_a": 0, "agent_b": 1}
    )
    entry_b = middleware.write(req_b)
    print(f"Agent B writes: {entry_b.value}")
    assert entry_b.status == MemoryStatus.CONFLICTED  # ← CONFLICT DETECTED!

    # Read the value
    read_req = ReadRequest(
        agent_id="agent_a",
        role="budget-agent"
    )
    entry_read = middleware.read("budget", read_req)
    print(f"Read result: {entry_read.value}, conflicts: {len(entry_read.conflicting_writes)}")
    assert entry_read.status == MemoryStatus.CONFLICTED

    # Check history
    history = history_log.get_history("budget")
    print(f"History has {len(history)} entries")
    assert len(history) == 2

    # Time-travel query
    snapshot = history_log.get_snapshot("budget", at_clock={"agent_a": 1, "agent_b": 0})
    print(f"At agent_a=1, agent_b=0: value was {snapshot.value}")
    assert snapshot.value == 5000
```

---

## 6. How to Write New Tests

### Test Template

```python
# tests/test_new_feature.py

import pytest
from engram.models import ...
from engram.some_module import SomeClass


class TestSomeFeature:
    """Test suite for SomeFeature."""

    @pytest.fixture
    def setup(self):
        """Setup for this test class."""
        obj = SomeClass()
        yield obj
        # Teardown if needed

    def test_basic_behavior(self, setup):
        """Test that basic behavior works."""
        result = setup.some_method()
        assert result == expected_value

    def test_edge_case(self, setup):
        """Test an edge case."""
        # Edge case setup
        result = setup.some_method(edge_case_input)
        assert result == expected_value

    def test_no_mutation(self, setup):
        """Ensure immutability where expected."""
        original_state = dict(setup.state)
        setup.some_method()
        assert setup.state == original_state  # Unchanged

    @pytest.mark.parametrize("input,expected", [
        (1, 2),
        (2, 4),
        (3, 6),
    ])
    def test_parametrized(self, setup, input, expected):
        """Test multiple inputs with parametrize."""
        result = setup.double(input)
        assert result == expected
```

### Common Test Patterns

**Pattern 1: Immutability**

```python
def test_immutability(mvr):
    """Ensure operations don't mutate the original."""
    original_values = list(mvr._values)

    new_mvr = mvr.write(...)

    # Original unchanged
    assert mvr._values == original_values
    # New is different
    assert new_mvr._values != original_values
```

**Pattern 2: State Verification**

```python
def test_state_after_operation(obj):
    """Verify internal state after an operation."""
    obj.do_something()

    assert obj.internal_state == expected_state
    assert len(obj.items) == expected_count
```

**Pattern 3: Error Handling**

```python
def test_error_on_invalid_input():
    """Verify error handling."""
    with pytest.raises(ValueError):
        obj.method(invalid_input)
```

**Pattern 4: Comparing Values**

```python
def test_ordering_comparison():
    """Verify comparison logic."""
    clock_a = VectorClock({"a": 1})
    clock_b = VectorClock({"a": 2})

    assert clock_a.compare(clock_b) == Ordering.BEFORE
    assert clock_b.compare(clock_a) == Ordering.AFTER
```

---

## 7. Debugging Tests

### Running Tests with Print Output

```bash
# Show print statements
pytest tests/test_crdt.py::test_name -v -s

# Show all local variables in failures
pytest tests/ -v -l

# Drop into debugger on failure
pytest tests/ --pdb
```

### Adding Debug Output

```python
def test_something(mvr):
    """Debug test."""
    clock_a = VectorClock({"a": 1})
    print(f"Clock A: {clock_a.clock}")  # Will show with -s flag

    mvr2 = mvr.write(100, "a", "admin", clock_a)
    print(f"Register values: {len(mvr2.values)}")

    assert mvr2.is_conflicted() == False
```

### Using `pdb` (Python Debugger)

```python
def test_something():
    """Test with debugger."""
    import pdb; pdb.set_trace()  # Execution pauses here

    # You can now inspect variables, step through code, etc.
    result = some_operation()
```

---

## 8. Verifying Core Concepts

### Verify: Vector Clocks Detect Causality

```bash
# Create test_verify_vector_clocks.py

import pytest
from engram.vector_clock import VectorClock
from engram.models import Ordering

def test_verify_causality_detection():
    """Verify vector clocks correctly detect causal relationships."""

    # Sequential writes (causal)
    clock_1 = VectorClock({"a": 1})
    clock_2 = VectorClock({"a": 2})
    assert clock_1.compare(clock_2) == Ordering.BEFORE
    print("✓ Sequential writes detected correctly")

    # Concurrent writes (non-causal)
    clock_a = VectorClock({"a": 1, "b": 0})
    clock_b = VectorClock({"a": 0, "b": 1})
    assert clock_a.compare(clock_b) == Ordering.CONCURRENT
    print("✓ Concurrent writes detected correctly")

    # One writer "catching up"
    clock_old_a = VectorClock({"a": 1})
    clock_new_both = VectorClock({"a": 1, "b": 1})
    assert clock_old_a.compare(clock_new_both) == Ordering.BEFORE
    print("✓ Causal 'catching up' detected correctly")
```

### Verify: CRDTs Store All Conflicting Values

```python
def test_verify_crdt_stores_conflicts():
    """Verify CRDT stores all conflicting values."""
    from engram.crdt import MVRegister

    mvr = MVRegister()

    # Write 1
    mvr1 = mvr.write(100, "a", "admin", VectorClock({"a": 1}))
    assert len(mvr1.values) == 1

    # Write 2 (concurrent)
    mvr2 = mvr1.write(200, "b", "admin", VectorClock({"b": 1}))
    assert len(mvr2.values) == 2  # ← Both stored!
    assert not mvr1.is_conflicted()
    assert mvr2.is_conflicted()

    print("✓ CRDT stores all conflicting values")
```

### Verify: Access Control Enforces Permissions

```python
def test_verify_access_control_enforced():
    """Verify access control prevents unauthorized access."""
    from engram.access_control import AccessPolicy

    policy = AccessPolicy()

    # Admin can write anything
    policy.register_role("admin", can_read=["*"], can_write=["*"])
    assert policy.check_write("admin", "anything") == True

    # Budget agent can only write to budget.*
    policy.register_role("budget-agent", can_read=["budget.*"], can_write=["budget.*"])
    assert policy.check_write("budget-agent", "budget.flights") == True
    assert policy.check_write("budget-agent", "audit.log") == False

    # Auditor is read-only
    policy.register_role("auditor", can_read=["*"], can_write=[])
    assert policy.check_read("auditor", "anything") == True
    assert policy.check_write("auditor", "anything") == False

    print("✓ Access control enforced correctly")
```

### Verify: History Log is Immutable

```python
def test_verify_history_immutable():
    """Verify history log is append-only."""
    from engram.history import HistoryLog
    from engram.models import HistoryEntry, WriteType

    history = HistoryLog()

    entry1 = HistoryEntry(
        write_id="1", key="k", value=100, agent_id="a",
        role="r", vector_clock={}, write_type=WriteType.WRITE
    )

    history.append(entry1)
    assert len(history.get_history("k")) == 1

    # Can't delete (no method provided)
    # Can only append
    entry2 = HistoryEntry(...)
    history.append(entry2)
    assert len(history.get_history("k")) == 2

    print("✓ History log is append-only (immutable)")
```

---

## 9. Test Coverage

### Generate Coverage Report

```bash
# Generate coverage
pytest tests/ --cov=engram --cov-report=html

# Open report
open htmlcov/index.html
```

### Coverage Goals

```
Target coverage: 80%+

Current coverage (approximate):
├─ vector_clock.py     95%  ✅ Well tested
├─ crdt.py              90%  ✅ Well tested
├─ models.py            70%  ⚠️  Dataclasses are mostly covered
├─ access_control.py    85%  ✅ Well tested
├─ middleware.py        75%  ⚠️  Some error paths untested
├─ api.py               70%  ⚠️  Some endpoints partially tested
├─ history.py           80%  ✅ Well tested
└─ storage/             75%  ⚠️  Some adapters need work
```

---

## 10. Common Test Issues & Solutions

### Issue: Tests Pass Locally but Fail in CI

**Solution**:

- Check for timezone differences
- Check for timing assumptions (use mocks for time)
- Ensure all fixtures are properly isolated

### Issue: Tests Mutate Each Other

**Solution**:

- Use fixtures that reset state
- Don't rely on test execution order
- Use `@pytest.fixture(scope="function")` (default) not `scope="module"`

### Issue: Vector Clock Tests Fail

**Solution**:

- Remember: missing agents default to 0
- CONCURRENT means neither dominates (not "unknown")
- Check all combinations

### Issue: Redis Tests Fail

**Solution**:

```bash
# Make sure Redis is running
docker run -d -p 6379:6379 redis:7.2-alpine

# Or skip Redis tests
pytest tests/ -k "not redis"
```

---

## Quick Test Commands Reference

```bash
# Run all tests
pytest tests/ -v

# Run single file
pytest tests/test_crdt.py -v

# Run single test
pytest tests/test_crdt.py::test_mvregister_write_concurrent -v

# Run tests matching a pattern
pytest tests/ -k "concurrent" -v

# Run with coverage
pytest tests/ --cov=engram --cov-report=term-missing

# Run with verbose output (show print statements)
pytest tests/ -v -s

# Run and drop to debugger on failure
pytest tests/ --pdb

# Run only failures from last run
pytest tests/ --lf

# Run failed tests first, then others
pytest tests/ --ff

# Stop after first failure
pytest tests/ -x

# Stop after N failures
pytest tests/ --maxfail=3

# Show local variables on failure
pytest tests/ -l

# Benchmark tests (if installed)
pytest tests/ --benchmark-only
```

---

**Last Updated**: May 2026
