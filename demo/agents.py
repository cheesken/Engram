"""
Demo agent classes for Engram.

Each agent is a thin HTTP client wrapping requests to the Engram API.
Used by run_demo.py to demonstrate the five key moments.
"""

from __future__ import annotations

from typing import Any

import httpx


class EngramClient:
    """
    Base client for interacting with the Engram API.

    All demo agents inherit from this class. Provides write, read,
    get_history, and rollback operations via HTTP.
    """

    def __init__(self, base_url: str, agent_id: str, role: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.agent_id = agent_id
        self.role = role
        self._client = httpx.Client(base_url=self.base_url, timeout=10.0)

    def write(
        self,
        key: str,
        value: Any,
        consistency_level: str = "eventual",
        vector_clock: dict[str, int] | None = None,
    ) -> dict:
        """
        Write a value to Engram shared memory.

        Args:
            key: The memory key to write to.
            value: The value to store.
            consistency_level: One of "eventual", "causal", "strong".
            vector_clock: Optional vector clock dict for causal ordering.

        Returns:
            The response JSON as a dict (MemoryEntry).
        """
        payload = {
            "key": key,
            "value": value,
            "agent_id": self.agent_id,
            "role": self.role,
            "consistency_level": consistency_level,
            "vector_clock": vector_clock or {},
        }
        resp = self._client.post("/write", json=payload)
        resp.raise_for_status()
        return resp.json()

    def read(self, key: str, consistency_level: str = "eventual") -> dict:
        """
        Read a value from Engram shared memory.

        Args:
            key: The memory key to read.
            consistency_level: One of "eventual", "causal", "strong".

        Returns:
            The response JSON as a dict (MemoryEntry).
        """
        params = {
            "agent_id": self.agent_id,
            "role": self.role,
            "consistency_level": consistency_level,
        }
        resp = self._client.get(f"/read/{key}", params=params)
        resp.raise_for_status()
        return resp.json()

    def get_history(self, key: str) -> list:
        """
        Get the write history for a key.

        Args:
            key: The memory key to get history for.

        Returns:
            A list of HistoryEntry dicts.
        """
        resp = self._client.get(f"/history/{key}")
        resp.raise_for_status()
        return resp.json()

    def rollback(self, write_id: str) -> dict:
        """
        Roll back to a previous write.

        Args:
            write_id: The write_id to roll back to.

        Returns:
            The response JSON as a dict (MemoryEntry).
        """
        payload = {
            "initiating_agent_id": self.agent_id,
            "initiating_role": self.role,
        }
        resp = self._client.post(f"/rollback/{write_id}", json=payload)
        resp.raise_for_status()
        return resp.json()


class FlightAgent(EngramClient):
    """Agent responsible for searching and storing flight information."""

    def __init__(self, base_url: str, agent_id: str = "flight-agent-1") -> None:
        super().__init__(base_url, agent_id, role="flight-agent")

    def search_flights(self, destination: str, dates: dict) -> dict:
        """
        Search for flights and write results to the 'flights' key.

        TODO: Implement demo logic.
        - Simulate a flight search (e.g., hardcoded results).
        - Write the results to Engram under the 'flights' key.
        - Return the MemoryEntry from the write.

        Args:
            destination: The destination city/airport.
            dates: A dict with 'departure' and 'return' date strings.

        Returns:
            The MemoryEntry dict from the write.
        """
        raise NotImplementedError("TODO: implement flight search demo logic")


class HotelAgent(EngramClient):
    """Agent responsible for searching and storing hotel information."""

    def __init__(self, base_url: str, agent_id: str = "hotel-agent-1") -> None:
        super().__init__(base_url, agent_id, role="hotel-agent")

    def search_hotels(self, destination: str, dates: dict) -> dict:
        """
        Search for hotels and write results to the 'hotels' key.

        TODO: Implement demo logic.
        - Simulate a hotel search (e.g., hardcoded results).
        - Write the results to Engram under the 'hotels' key.
        - Return the MemoryEntry from the write.

        Args:
            destination: The destination city.
            dates: A dict with 'checkin' and 'checkout' date strings.

        Returns:
            The MemoryEntry dict from the write.
        """
        raise NotImplementedError("TODO: implement hotel search demo logic")


class BudgetAgent(EngramClient):
    """Agent responsible for managing the shared travel budget."""

    def __init__(self, base_url: str, agent_id: str = "budget-agent-1") -> None:
        super().__init__(base_url, agent_id, role="budget-agent")

    def set_budget(self, amount: float) -> dict:
        """
        Write the budget value to the 'budget' key.

        TODO: Implement demo logic.
        - Write the given amount to Engram under the 'budget' key.
        - Return the MemoryEntry from the write.

        Args:
            amount: The budget amount in dollars.

        Returns:
            The MemoryEntry dict from the write.
        """
        raise NotImplementedError("TODO: implement budget set demo logic")


class Summarizer(EngramClient):
    """Agent that reads all keys and produces a summary. Read-only role."""

    def __init__(self, base_url: str, agent_id: str = "summarizer-1") -> None:
        super().__init__(base_url, agent_id, role="summarizer")

    def summarize(self) -> dict:
        """
        Read all keys and print a summary of the current memory state.

        TODO: Implement demo logic.
        - Read 'flights', 'hotels', and 'budget' keys.
        - Print a formatted summary to stdout.
        - Return a dict with all the read values.

        Returns:
            A dict mapping key names to their current values.
        """
        raise NotImplementedError("TODO: implement summarize demo logic")

    def attempt_write(self) -> dict:
        """
        Intentionally try to write to 'budget' to demo the 403 block.

        The summarizer role should be read-only. This method demonstrates
        that Engram correctly denies the write and returns HTTP 403.

        Expected to raise an httpx.HTTPStatusError with status 403.

        Returns:
            Should not return — expected to raise.
        """
        raise NotImplementedError("TODO: implement access violation demo logic")
