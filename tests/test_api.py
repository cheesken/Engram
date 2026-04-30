"""
Tests for engram.api FastAPI endpoints.

Uses the TestClient fixture from conftest.py which injects test middleware.
"""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from engram import __version__


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health_endpoint(client):
    """GET /health should return 200 with status, storage, and version."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["storage"] == "memory"
    assert data["version"] == __version__


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def test_write_endpoint(client):
    """POST /write should create a new memory entry and return it."""
    payload = {
        "key": "budget",
        "value": 5000,
        "agent_id": "agent-A",
        "role": "admin",
        "consistency_level": "eventual",
        "conflict_strategy": "latest_clock",
        "vector_clock": {},
    }
    resp = client.post("/write", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "budget"
    assert data["value"] == 5000
    assert data["agent_id"] == "agent-A"
    assert data["role"] == "admin"
    assert data["status"] == "ok"


def test_write_without_permission(client):
    """POST /write with a read-only role should return 403."""
    payload = {
        "key": "budget",
        "value": 100,
        "agent_id": "agent-A",
        "role": "reader",
        "consistency_level": "eventual",
        "conflict_strategy": "latest_clock",
        "vector_clock": {},
    }
    resp = client.post("/write", json=payload)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


def test_read_endpoint(client):
    """GET /read/{key} should return the stored entry."""
    write_payload = {
        "key": "budget",
        "value": 7500,
        "agent_id": "agent-A",
        "role": "admin",
        "consistency_level": "eventual",
        "conflict_strategy": "latest_clock",
        "vector_clock": {},
    }
    write_resp = client.post("/write", json=write_payload)
    assert write_resp.status_code == 200

    resp = client.get(
        "/read/budget",
        params={
            "agent_id": "agent-B",
            "role": "admin",
            "consistency_level": "eventual",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "budget"
    assert data["value"] == 7500


def test_read_missing_key(client):
    """GET /read/{key} for a non-existent key should return 404."""
    resp = client.get(
        "/read/missing",
        params={"agent_id": "agent-A", "role": "admin"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


def test_history_endpoint(client):
    """GET /history/{key} should return history entries for the key."""
    first = {
        "key": "budget",
        "value": 1000,
        "agent_id": "agent-A",
        "role": "admin",
        "consistency_level": "eventual",
        "conflict_strategy": "latest_clock",
        "vector_clock": {},
    }
    second = {
        "key": "budget",
        "value": 2000,
        "agent_id": "agent-A",
        "role": "admin",
        "consistency_level": "eventual",
        "conflict_strategy": "latest_clock",
        "vector_clock": {"agent-A": 1},
    }
    assert client.post("/write", json=first).status_code == 200
    assert client.post("/write", json=second).status_code == 200

    resp = client.get("/history/budget")
    assert resp.status_code == 200
    data = resp.json()
    assert [entry["value"] for entry in data] == [1000, 2000]


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------


def test_rollback_endpoint(client):
    """POST /rollback/{write_id} should restore a previous value."""
    original_payload = {
        "key": "budget",
        "value": 5000,
        "agent_id": "agent-A",
        "role": "admin",
        "consistency_level": "eventual",
        "conflict_strategy": "latest_clock",
        "vector_clock": {},
    }
    original_resp = client.post("/write", json=original_payload)
    assert original_resp.status_code == 200
    original_id = original_resp.json()["write_id"]

    overwrite_payload = {
        "key": "budget",
        "value": 9000,
        "agent_id": "agent-A",
        "role": "admin",
        "consistency_level": "eventual",
        "conflict_strategy": "latest_clock",
        "vector_clock": {"agent-A": 1},
    }
    assert client.post("/write", json=overwrite_payload).status_code == 200

    rollback_resp = client.post(
        f"/rollback/{original_id}",
        json={"initiating_agent_id": "agent-B", "initiating_role": "admin"},
    )
    assert rollback_resp.status_code == 200
    data = rollback_resp.json()
    assert data["value"] == 5000


def test_rollback_unknown_write_id(client):
    """POST /rollback/{write_id} with unknown ID should return 404."""
    resp = client.post(
        "/rollback/does-not-exist",
        json={"initiating_agent_id": "agent-A", "initiating_role": "admin"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------


def test_register_and_get_role(client):
    """POST /roles then GET /roles/{name} should return the registered role."""
    role_def = {
        "role_name": "auditor",
        "can_read": ["*"],
        "can_write": [],
    }
    resp = client.post("/roles", json=role_def)
    assert resp.status_code == 200
    assert resp.json() == role_def

    get_resp = client.get("/roles/auditor")
    assert get_resp.status_code == 200
    assert get_resp.json() == role_def


def test_get_unknown_role(client):
    """GET /roles/{name} for an unregistered role should return 404."""
    resp = client.get("/roles/not-a-role")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Keys
# ---------------------------------------------------------------------------


def test_list_keys(client):
    """GET /keys should return all stored keys."""
    payloads = [
        {
            "key": "budget",
            "value": 1,
            "agent_id": "agent-A",
            "role": "admin",
            "consistency_level": "eventual",
            "conflict_strategy": "latest_clock",
            "vector_clock": {},
        },
        {
            "key": "flights",
            "value": ["SFO", "LAX"],
            "agent_id": "agent-A",
            "role": "admin",
            "consistency_level": "eventual",
            "conflict_strategy": "latest_clock",
            "vector_clock": {},
        },
    ]
    for payload in payloads:
        assert client.post("/write", json=payload).status_code == 200

    resp = client.get("/keys")
    assert resp.status_code == 200
    assert resp.json() == ["budget", "flights"]


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------


def test_websocket_returns_not_implemented(client):
    """WS /ws/memory should accept, send not_implemented, and close."""
    with client.websocket_connect("/ws/memory") as websocket:
        data = websocket.receive_json()
        assert data == {"status": "not_implemented"}
        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()
