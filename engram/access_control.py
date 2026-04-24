"""
Role-based access control for Engram memory reads and writes.

Developers register roles once at startup. Every read and write is checked
here before touching storage. Wildcard patterns are supported via fnmatch.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Role:
    """A role definition with read/write permission patterns."""

    role_name: str
    can_read: list[str] = field(default_factory=list)
    can_write: list[str] = field(default_factory=list)


class AccessPolicy:
    """
    Enforces role-based access control for all memory reads and writes.

    Developers register roles once at startup. Every read and write is
    checked here before touching storage.

    Wildcard "*" in can_read or can_write grants access to all keys.
    An empty can_write list means the role is read-only.
    """

    def __init__(self) -> None:
        self._roles: dict[str, Role] = {}

    @staticmethod
    def _pattern_allows(pattern: str, key: str) -> bool:
        if pattern == "*":
            return True
        return fnmatch.fnmatch(key, pattern)

    def register_role(
        self, role_name: str, can_read: list[str], can_write: list[str]
    ) -> None:
        """
        Register a role definition.

        If the role already exists, overwrite it. Store as a Role dataclass instance.

        Args:
            role_name: Unique name for this role (e.g. "budget-agent").
            can_read: List of key patterns this role can read. Use "*" for all keys.
                      Supports fnmatch-style wildcards (e.g. "budget.*").
            can_write: List of key patterns this role can write. Use "*" for all keys.
                       An empty list means the role is read-only.
        """
        self._roles[role_name] = Role(
            role_name=role_name,
            can_read=list(can_read),
            can_write=list(can_write),
        )

    def check_read(self, role: str, key: str) -> bool:
        """
        Return True if the given role is allowed to read the given key.

        Logic:
        1. Look up role. If not found, return False.
        2. If can_read contains "*", return True.
        3. Check each pattern in can_read using fnmatch for wildcard support.
           e.g. "budget.*" would match "budget.flights" and "budget.hotels".
        4. If any pattern matches the key, return True. Otherwise False.

        Args:
            role: The role name to check.
            key: The memory key being read.

        Returns:
            True if the read is permitted, False otherwise.
        """
        r = self._roles.get(role)
        if r is None:
            return False
        if "*" in r.can_read:
            return True
        return any(self._pattern_allows(p, key) for p in r.can_read)

    def check_write(self, role: str, key: str) -> bool:
        """
        Return True if the given role is allowed to write the given key.

        Same logic as check_read but against can_write.
        Empty can_write means read-only — always returns False.

        Args:
            role: The role name to check.
            key: The memory key being written.

        Returns:
            True if the write is permitted, False otherwise.
        """
        r = self._roles.get(role)
        if r is None:
            return False
        if not r.can_write:
            return False
        if "*" in r.can_write:
            return True
        return any(self._pattern_allows(p, key) for p in r.can_write)

    def get_role(self, role_name: str) -> Optional[Role]:
        """
        Return the Role for role_name, or None if not registered.

        Args:
            role_name: The role to look up.

        Returns:
            The Role instance, or None if the role does not exist.
        """
        return self._roles.get(role_name)

    def list_roles(self) -> list[str]:
        """
        Return a list of all registered role names.

        Returns:
            A list of role name strings.
        """
        return sorted(self._roles.keys())
