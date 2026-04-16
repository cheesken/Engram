"""
Shared data models and enums for the Engram project.

This is the single source of truth for all types used across the codebase.
Every other module imports from here. No type definitions should exist elsewhere.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ConsistencyLevel(str, Enum):
    """Determines how strictly a read or write must be coordinated."""

    STRONG = "strong"
    CAUSAL = "causal"
    EVENTUAL = "eventual"


class ConflictStrategy(str, Enum):
    """Strategy applied when concurrent writes to the same key are detected."""

    LOWEST_VALUE = "lowest_value"
    HIGHEST_VALUE = "highest_value"
    LATEST_CLOCK = "latest_clock"
    UNION = "union"
    FLAG_FOR_HUMAN = "flag_for_human"


class Ordering(str, Enum):
    """Result of comparing two vector clocks."""

    BEFORE = "before"
    AFTER = "after"
    CONCURRENT = "concurrent"
    EQUAL = "equal"


class WriteType(str, Enum):
    """Distinguishes regular writes from rollback entries in the history log."""

    WRITE = "write"
    ROLLBACK = "rollback"


class MemoryStatus(str, Enum):
    """Current status of a memory entry."""

    OK = "ok"
    CONFLICTED = "conflicted"
    FLAGGED = "flagged"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def _uuid_str() -> str:
    """Return a new UUID4 as a string."""
    return str(uuid4())


# ---------------------------------------------------------------------------
# Domain Models
# ---------------------------------------------------------------------------


class ConflictingWrite(BaseModel):
    """Represents a single conflicting value stored in an MVRegister."""

    write_id: str
    agent_id: str
    role: str
    value: Any
    vector_clock: dict[str, int]
    timestamp: datetime


class MemoryEntry(BaseModel):
    """A single key-value pair in Engram shared memory."""

    write_id: str = Field(default_factory=_uuid_str)
    key: str
    value: Any
    agent_id: str
    role: str
    vector_clock: dict[str, int]
    consistency_level: ConsistencyLevel
    conflict_strategy: ConflictStrategy = ConflictStrategy.LATEST_CLOCK
    status: MemoryStatus = MemoryStatus.OK
    conflicting_writes: list[ConflictingWrite] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=_utcnow)


class HistoryEntry(BaseModel):
    """An immutable record of a write or rollback in the history log."""

    write_id: str = Field(default_factory=_uuid_str)
    key: str
    value: Any
    agent_id: str
    role: str
    vector_clock: dict[str, int]
    timestamp: datetime = Field(default_factory=_utcnow)
    write_type: WriteType = WriteType.WRITE
    rollback_of: str | None = None


class RoleDefinition(BaseModel):
    """Defines the read/write permissions for a named role."""

    role_name: str
    can_read: list[str]
    can_write: list[str]


class KeyConfig(BaseModel):
    """Per-key configuration for conflict strategy and consistency defaults."""

    key: str
    conflict_strategy: ConflictStrategy = ConflictStrategy.LATEST_CLOCK
    default_consistency: ConsistencyLevel = ConsistencyLevel.EVENTUAL


# ---------------------------------------------------------------------------
# API Request / Response Models
# ---------------------------------------------------------------------------


class WriteRequest(BaseModel):
    """Request body for POST /write."""

    key: str
    value: Any
    agent_id: str
    role: str
    consistency_level: ConsistencyLevel = ConsistencyLevel.EVENTUAL
    conflict_strategy: ConflictStrategy = ConflictStrategy.LATEST_CLOCK
    vector_clock: dict[str, int] = Field(default_factory=dict)


class ReadRequest(BaseModel):
    """Query parameters for GET /read/{key}."""

    agent_id: str
    role: str
    consistency_level: ConsistencyLevel = ConsistencyLevel.EVENTUAL


class RollbackRequest(BaseModel):
    """Request body for POST /rollback/{write_id}."""

    initiating_agent_id: str
    initiating_role: str


class HealthResponse(BaseModel):
    """Response body for GET /health."""

    status: str
    storage: str
    version: str
