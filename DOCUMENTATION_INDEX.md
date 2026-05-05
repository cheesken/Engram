# Engram Documentation Index

Quick navigation to all Engram project documentation.

---

## 📚 Documentation Files

### 1. **CODEBASE_WALKTHROUGH.md**

**Best for**: Deep understanding, technical presentations, onboarding

- High-level project overview
- Project structure explanation
- Step-by-step core logic walkthrough
- Setup and running instructions
- Complete demo presentation script
- Optional improvements and refactoring ideas

👉 **Start here** if you want to understand the entire system from scratch.

---

### 2. **QUICK_REFERENCE.md**

**Best for**: Quick lookups, talking points, elevator pitches

- 30-second pitch
- Core concepts summary
- Key features checklist
- File structure at a glance
- Quick test commands
- FAQ with quick answers
- Talking points by audience type

👉 **Use this** before presentations or when you need a quick fact.

---

### 3. **VISUAL_GUIDE.md**

**Best for**: Understanding architecture visually, documentation

- System architecture diagram
- Write pipeline (detailed flow)
- Vector clock comparison logic
- CRDT write logic
- Conflict resolution strategies
- Access control flow
- History & time-travel queries
- Storage adapter architecture
- Complete request-response cycle
- Conflict scenario matrix

👉 **Use this** when you want to see how things work visually.

---

### 4. **TESTING_GUIDE.md**

**Best for**: Writing tests, verifying functionality, debugging

- How to run tests
- Test organization
- Unit test examples
- Integration test examples
- End-to-end scenario tests
- How to write new tests
- Debugging techniques
- Verifying core concepts
- Test coverage information
- Common issues & solutions

👉 **Use this** when you need to test, debug, or verify functionality.

---

### 5. **demo/demo_presentation.py**

**Best for**: Live demonstrations, showing features in action

- Fully executable demo script
- 5 key moments:
  1. Problem setup
  2. Conflict detection
  3. History & time-travel
  4. Access control
  5. Summary
- Uses real HTTP calls to the API
- Self-contained and well-commented

👉 **Run this** to see Engram in action (3–5 minutes).

---

## 🚀 Quick Start Paths

### Path 1: "I want to understand the project quickly"

1. Read: [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) — 5 minutes
2. Read: [VISUAL_GUIDE.md](./VISUAL_GUIDE.md) — 10 minutes (skim diagrams)
3. Run: `python demo/demo_presentation.py` — 5 minutes (after starting API)

**Total**: ~20 minutes

### Path 2: "I need to present this to technical people"

1. Review: [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) — Speaking points
2. Study: [VISUAL_GUIDE.md](./VISUAL_GUIDE.md) — Diagrams for slides
3. Practice: Run demo script
4. Reference: [CODEBASE_WALKTHROUGH.md](./CODEBASE_WALKTHROUGH.md) — For Q&A

**Total**: ~1 hour preparation

### Path 3: "I need to understand the code deeply"

1. Read: [CODEBASE_WALKTHROUGH.md](./CODEBASE_WALKTHROUGH.md) — Full walkthrough
2. Study: [VISUAL_GUIDE.md](./VISUAL_GUIDE.md) — Visual explanations
3. Explore: Read source files in order:
   - `engram/models.py` (data types)
   - `engram/vector_clock.py` (causal ordering)
   - `engram/crdt.py` (conflict storage)
   - `engram/access_control.py` (permissions)
   - `engram/middleware.py` (orchestration)
   - `engram/api.py` (HTTP routes)
4. Reference: [TESTING_GUIDE.md](./TESTING_GUIDE.md) — Write tests to verify understanding

**Total**: ~3-4 hours

### Path 4: "I need to extend or debug the system"

1. Reference: [TESTING_GUIDE.md](./TESTING_GUIDE.md) — How to verify changes
2. Reference: [CODEBASE_WALKTHROUGH.md](./CODEBASE_WALKTHROUGH.md) — Architecture overview
3. Reference: [VISUAL_GUIDE.md](./VISUAL_GUIDE.md) — For tracing data flow
4. Read source code for the specific module you're modifying

**Total**: As needed

---

## 🎯 Find Information By Topic

| Topic               | Document             | Section                                   |
| ------------------- | -------------------- | ----------------------------------------- |
| Project purpose     | CODEBASE_WALKTHROUGH | High-level overview                       |
| System architecture | VISUAL_GUIDE         | System architecture diagram               |
| Vector clocks       | CODEBASE_WALKTHROUGH | Vector Clocks section                     |
|                     | VISUAL_GUIDE         | Vector clock comparison logic             |
| CRDTs               | CODEBASE_WALKTHROUGH | Multi-Value Register (CRDT)               |
|                     | VISUAL_GUIDE         | CRDT Write Logic                          |
| Conflict detection  | CODEBASE_WALKTHROUGH | Core Logic Walkthrough                    |
|                     | VISUAL_GUIDE         | Write pipeline + Conflict scenario matrix |
| Conflict resolution | CODEBASE_WALKTHROUGH | Core Logic Walkthrough                    |
|                     | VISUAL_GUIDE         | Conflict Resolution Strategies            |
| Access control      | CODEBASE_WALKTHROUGH | Access Control                            |
|                     | VISUAL_GUIDE         | Access Control flow                       |
| History & audit     | CODEBASE_WALKTHROUGH | History & Time-Travel                     |
|                     | VISUAL_GUIDE         | History Log & Time-Travel                 |
| Storage adapters    | CODEBASE_WALKTHROUGH | Storage Adapter Architecture              |
|                     | VISUAL_GUIDE         | Storage Adapter Architecture              |
| API endpoints       | CODEBASE_WALKTHROUGH | Key Endpoints                             |
| Setup & run         | CODEBASE_WALKTHROUGH | Setup and Running Instructions            |
| Demo script         | demo_presentation.py | Full executable demo                      |
| Running tests       | TESTING_GUIDE        | Running Tests section                     |
| Writing tests       | TESTING_GUIDE        | How to Write New Tests                    |
| Test examples       | TESTING_GUIDE        | Unit Test Examples                        |
| Debugging           | TESTING_GUIDE        | Debugging Tests section                   |
| File structure      | CODEBASE_WALKTHROUGH | Project Structure                         |
|                     | QUICK_REFERENCE      | File Structure                            |
| Quick facts         | QUICK_REFERENCE      | Everything is concise                     |
| Improvements        | CODEBASE_WALKTHROUGH | Optional Improvements                     |
| FAQ                 | QUICK_REFERENCE      | FAQ section                               |

---

## 📋 Checklist: Before Presentations

### 1-2 Hours Before

- [ ] Review [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) — especially your audience section
- [ ] Review [VISUAL_GUIDE.md](./VISUAL_GUIDE.md) — pick out key diagrams
- [ ] Make sure API is running: `uvicorn engram.api:app --reload`
- [ ] Test the demo script: `python demo/demo_presentation.py`

### During Presentation

- [ ] Use [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) for talking points
- [ ] Reference [VISUAL_GUIDE.md](./VISUAL_GUIDE.md) diagrams on slides
- [ ] Run demo script if showing live (5 minutes)
- [ ] Have [CODEBASE_WALKTHROUGH.md](./CODEBASE_WALKTHROUGH.md) ready for Q&A

### After Presentation

- [ ] Share links to all documentation
- [ ] Have people read [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) first
- [ ] Point to [CODEBASE_WALKTHROUGH.md](./CODEBASE_WALKTHROUGH.md) for deep dives
- [ ] Recommend running demo script

---

## 🔧 Developer Workflow

### Understanding a Specific Module

1. **Read the docstring** at the top of the `.py` file
2. **Look up in [CODEBASE_WALKTHROUGH.md](./CODEBASE_WALKTHROUGH.md)** — Key Functions & Classes section
3. **Check [VISUAL_GUIDE.md](./VISUAL_GUIDE.md)** — Is there a diagram?
4. **Read the tests** — `tests/test_<module>.py`
5. **Reference [TESTING_GUIDE.md](./TESTING_GUIDE.md)** if tests are unclear

### Adding a New Feature

1. **Check [CODEBASE_WALKTHROUGH.md](./CODEBASE_WALKTHROUGH.md)** — Optional Improvements section
2. **Understand the flow** — Use [VISUAL_GUIDE.md](./VISUAL_GUIDE.md) diagrams
3. **Write tests first** — Follow [TESTING_GUIDE.md](./TESTING_GUIDE.md) patterns
4. **Implement feature**
5. **Verify with tests** — Run `pytest tests/ -v`
6. **Update tests if needed** — Document in [TESTING_GUIDE.md](./TESTING_GUIDE.md)

### Debugging an Issue

1. **Check [TESTING_GUIDE.md](./TESTING_GUIDE.md)** — Common Test Issues section
2. **Write a test that reproduces the issue**
3. **Use [VISUAL_GUIDE.md](./VISUAL_GUIDE.md)** to trace the data flow
4. **Reference [CODEBASE_WALKTHROUGH.md](./CODEBASE_WALKTHROUGH.md)** — Core Logic section
5. **Use debugger** — `pytest tests/ --pdb`

---

## 🎬 Demo Script Guide

The demo script (`demo_presentation.py`) walks through 5 moments:

### Before Running Demo

```bash
# Terminal 1: Start API
uvicorn engram.api:app --reload

# Terminal 2: Run demo
python demo/demo_presentation.py
```

### What Each Moment Shows

| Moment | Duration | What It Demonstrates                                |
| ------ | -------- | --------------------------------------------------- |
| 0      | 30s      | The problem without Engram                          |
| 1      | 2m       | Conflict detection & storage (vector clocks + CRDT) |
| 2      | 1m       | History log & time-travel queries                   |
| 3      | 30s      | Access control (role-based permissions)             |
| 4      | 1m       | Consistency levels                                  |
| 5      | 1m       | Summary & value proposition                         |

**Total**: ~5-6 minutes

### Customizing the Demo

The demo script is well-commented and easy to modify:

- Add new moments or skip existing ones
- Test different conflict resolution strategies
- Add more complex scenarios (3+ agents, etc.)

---

## 📖 Recommended Reading Order

### For Managers/Product People

1. [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) — 30-second pitch
2. [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) — For Managers section
3. [CODEBASE_WALKTHROUGH.md](./CODEBASE_WALKTHROUGH.md) — Optional Improvements (for roadmap)

### For Software Engineers

1. [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) — Core concepts & speaking points
2. [VISUAL_GUIDE.md](./VISUAL_GUIDE.md) — Skim all diagrams
3. [CODEBASE_WALKTHROUGH.md](./CODEBASE_WALKTHROUGH.md) — Full 6-section walkthrough
4. Source code (`engram/*.py`)
5. [TESTING_GUIDE.md](./TESTING_GUIDE.md) — Verify understanding with tests

### For Data Scientists / ML Engineers

1. [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) — For Data Scientists section
2. [CODEBASE_WALKTHROUGH.md](./CODEBASE_WALKTHROUGH.md) — Core concepts
3. [CODEBASE_WALKTHROUGH.md](./CODEBASE_WALKTHROUGH.md) — Optional Improvements → Resolution strategies
4. [demo_presentation.py](./demo/demo_presentation.py) — See it in action

### For DevOps/Platform Engineers

1. [CODEBASE_WALKTHROUGH.md](./CODEBASE_WALKTHROUGH.md) — Setup and Running
2. [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) — Configuration section
3. [VISUAL_GUIDE.md](./VISUAL_GUIDE.md) — Storage Adapter Architecture

---

## 💡 Key Concepts at a Glance

| Concept            | What It Is                             | Why It Matters                                |
| ------------------ | -------------------------------------- | --------------------------------------------- |
| **Vector Clock**   | Dict mapping agents to counters        | Detects if writes are concurrent              |
| **CRDT**           | Data structure for distributed systems | Stores all conflicting values automatically   |
| **Conflict**       | Multiple values from concurrent writes | Would be silent data loss in normal systems   |
| **Resolution**     | Picking one value from conflicts       | Can be automatic (strategy) or human-reviewed |
| **Immutability**   | Never delete history entries           | Complete audit trail for compliance           |
| **Access Control** | Role-based permissions                 | Prevents unauthorized reads/writes            |
| **Time-Travel**    | Query state at past clock points       | Debug agent decisions historically            |

---

## ❓ FAQ (Quick Answers)

**Q: Where do I start?**
A: Read [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) (5 min), then [CODEBASE_WALKTHROUGH.md](./CODEBASE_WALKTHROUGH.md) (20 min).

**Q: How do I run the demo?**
A: Start API (`uvicorn engram.api:app`), then run `python demo/demo_presentation.py`.

**Q: How do I run tests?**
A: Run `pytest tests/ -v`. See [TESTING_GUIDE.md](./TESTING_GUIDE.md) for details.

**Q: Where are the diagrams?**
A: All in [VISUAL_GUIDE.md](./VISUAL_GUIDE.md) (ASCII art format).

**Q: What does the system do?**
A: Prevents data loss when multiple AI agents write to shared state concurrently.

**Q: How does it prevent data loss?**
A: Uses vector clocks to detect concurrent writes, stores all conflicting values in a CRDT, and applies a resolution strategy.

**Q: Is it production-ready?**
A: v0.1.0 is a reference implementation. See [CODEBASE_WALKTHROUGH.md](./CODEBASE_WALKTHROUGH.md) — Optional Improvements for production checklist.

**Q: Can I extend it?**
A: Yes! It's modular with pluggable storage adapters and configurable conflict resolution. See [CODEBASE_WALKTHROUGH.md](./CODEBASE_WALKTHROUGH.md) for extension ideas.

---

## 📞 Support & Troubleshooting

### API won't start

See [CODEBASE_WALKTHROUGH.md](./CODEBASE_WALKTHROUGH.md) — Running the Project Locally

### Tests fail

See [TESTING_GUIDE.md](./TESTING_GUIDE.md) — Common Test Issues

### Understanding a concept

See [VISUAL_GUIDE.md](./VISUAL_GUIDE.md) for diagrams or [CODEBASE_WALKTHROUGH.md](./CODEBASE_WALKTHROUGH.md) for text

### Presenting the project

Use [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) for talking points and demo script for live demo

---

## 🗂️ File Organization

```
Engram/ (project root)
│
├─ Documentation (READ THESE FIRST!)
│  ├─ README.md                     (user-facing)
│  ├─ CODEBASE_WALKTHROUGH.md       ← Start here
│  ├─ QUICK_REFERENCE.md            ← Quick facts
│  ├─ VISUAL_GUIDE.md               ← Diagrams
│  ├─ TESTING_GUIDE.md              ← How to test
│  └─ DOCUMENTATION_INDEX.md        ← You are here
│
├─ Source Code
│  └─ engram/
│     ├─ models.py
│     ├─ vector_clock.py
│     ├─ crdt.py
│     ├─ access_control.py
│     ├─ middleware.py
│     ├─ api.py
│     ├─ history.py
│     └─ storage/
│
├─ Tests
│  └─ tests/
│     ├─ test_vector_clock.py
│     ├─ test_crdt.py
│     └─ ... (more tests)
│
├─ Demo
│  └─ demo/
│     ├─ demo_presentation.py  ← Run this for live demo
│     └─ ui/
│
└─ Configuration
   ├─ pyproject.toml
   ├─ requirements.txt
   ├─ docker-compose.yml
   └─ .env
```

---

## ✅ Project Health Checklist

- [ ] All documentation files exist
- [ ] Demo script runs without errors
- [ ] All tests pass: `pytest tests/ -v`
- [ ] API starts: `uvicorn engram.api:app`
- [ ] Redis (optional) can connect
- [ ] Code coverage >80%
- [ ] No linting errors: `ruff check engram/`

---

**Last Updated**: May 2026
**Version**: 0.1.0
**Status**: Complete documentation package

---

## 🚀 Getting Started Right Now

### Fastest Path (5 minutes)

```bash
# Terminal 1
uvicorn engram.api:app --reload

# Terminal 2
python demo/demo_presentation.py

# Then open README.md or QUICK_REFERENCE.md
```

### Most Thorough Path (2-3 hours)

1. Read [CODEBASE_WALKTHROUGH.md](./CODEBASE_WALKTHROUGH.md)
2. Read [VISUAL_GUIDE.md](./VISUAL_GUIDE.md)
3. Read source code in `engram/` directory
4. Run tests: `pytest tests/ -v`
5. Run demo: `python demo/demo_presentation.py`

### You're Ready When...

- [ ] You can explain what vector clocks do
- [ ] You can explain what a CRDT is
- [ ] You can trace a write request through the system
- [ ] You can run the demo script
- [ ] You can run and understand the tests

---

**Questions? Start with [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) → FAQ section**
