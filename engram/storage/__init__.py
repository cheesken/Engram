"""Storage adapters for Engram memory persistence."""

from engram.storage.base import StorageAdapter
from engram.storage.memory import InMemoryAdapter

__all__ = ["StorageAdapter", "InMemoryAdapter"]
