"""
Shared pytest fixtures for the Engram test suite.
"""

import pytest
from fastapi.testclient import TestClient

from engram.access_control import AccessPolicy
from engram.api import app
from engram.history import HistoryLog
from engram.middleware import EngramMiddleware, Settings
from engram.storage.memory import InMemoryAdapter


@pytest.fixture
def memory_storage() -> InMemoryAdapter:
    """Provide a fresh InMemoryAdapter for each test."""
    return InMemoryAdapter()


@pytest.fixture
def access_policy() -> AccessPolicy:
    """
    Provide an AccessPolicy pre-configured with three roles:

    - admin: can read and write everything (wildcard "*").
    - reader: can read everything, cannot write anything.
    - writer: can read and write only "budget" keys.
    """
    policy = AccessPolicy()
    policy.register_role("admin", can_read=["*"], can_write=["*"])
    policy.register_role("reader", can_read=["*"], can_write=[])
    policy.register_role("writer", can_read=["budget"], can_write=["budget"])
    return policy


@pytest.fixture
def history_log() -> HistoryLog:
    """Provide a fresh HistoryLog for each test."""
    return HistoryLog()


@pytest.fixture
def middleware(memory_storage, access_policy, history_log) -> EngramMiddleware:
    """Provide a fully wired EngramMiddleware with in-memory storage."""
    return EngramMiddleware(memory_storage, access_policy, history_log)


@pytest.fixture
def client(middleware) -> TestClient:
    """
    Provide a FastAPI TestClient with the test middleware injected.

    Overrides app.state.middleware so that routes use the test fixtures
    instead of a real lifespan-initialized middleware.
    """
    app.state.settings = Settings(storage_adapter="memory")
    app.state.storage = middleware.storage
    app.state.access_policy = middleware.access_policy
    app.state.history_log = middleware.history_log
    app.state.middleware = middleware
    return TestClient(app)
