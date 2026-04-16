"""
Tests for engram.api FastAPI endpoints.

Uses the TestClient fixture from conftest.py which injects test middleware.
"""

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health_endpoint(client):
    """GET /health should return 200 with status, storage, and version."""
    pass


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def test_write_endpoint(client):
    """POST /write should create a new memory entry and return it."""
    pass


def test_write_without_permission(client):
    """POST /write with a read-only role should return 403."""
    pass


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


def test_read_endpoint(client):
    """GET /read/{key} should return the stored entry."""
    pass


def test_read_missing_key(client):
    """GET /read/{key} for a non-existent key should return 404."""
    pass


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


def test_history_endpoint(client):
    """GET /history/{key} should return history entries for the key."""
    pass


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------


def test_rollback_endpoint(client):
    """POST /rollback/{write_id} should restore a previous value."""
    pass


def test_rollback_unknown_write_id(client):
    """POST /rollback/{write_id} with unknown ID should return 404."""
    pass


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------


def test_register_and_get_role(client):
    """POST /roles then GET /roles/{name} should return the registered role."""
    pass


def test_get_unknown_role(client):
    """GET /roles/{name} for an unregistered role should return 404."""
    pass


# ---------------------------------------------------------------------------
# Keys
# ---------------------------------------------------------------------------


def test_list_keys(client):
    """GET /keys should return all stored keys."""
    pass


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------


def test_websocket_returns_not_implemented(client):
    """WS /ws/memory should accept, send not_implemented, and close."""
    pass
