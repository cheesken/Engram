"""
Tests for engram.access_control.AccessPolicy.

Covers: register_role, check_read, check_write, get_role, list_roles.
"""

from engram.access_control import AccessPolicy


# ---------------------------------------------------------------------------
# register_role / get_role
# ---------------------------------------------------------------------------


def test_register_and_get_role(access_policy):
    """Registering a role should make it retrievable via get_role."""
    role = access_policy.get_role("admin")
    assert role is not None
    assert role.role_name == "admin"
    assert role.can_read == ["*"]
    assert role.can_write == ["*"]


def test_register_role_overwrites_existing():
    """Re-registering a role with the same name should overwrite it."""
    policy = AccessPolicy()
    policy.register_role("admin", can_read=["*"], can_write=["*"])
    policy.register_role("admin", can_read=["budget"], can_write=["budget"])
    role = policy.get_role("admin")
    assert role is not None
    assert role.can_read == ["budget"]
    assert role.can_write == ["budget"]


def test_get_role_returns_none_for_unknown():
    """get_role should return None for an unregistered role."""
    policy = AccessPolicy()
    assert policy.get_role("not-a-role") is None


def test_list_roles(access_policy):
    """list_roles should return all registered role names."""
    assert access_policy.list_roles() == ["admin", "reader", "writer"]


# ---------------------------------------------------------------------------
# check_read
# ---------------------------------------------------------------------------


def test_check_read_wildcard_allows_any_key(access_policy):
    """A role with can_read=['*'] should be able to read any key."""
    assert access_policy.check_read("admin", "inventory.stock") is True
    assert access_policy.check_read("reader", "anything") is True


def test_check_read_specific_pattern(access_policy):
    """A role with can_read=['budget'] should only read 'budget' keys."""
    assert access_policy.check_read("writer", "budget") is True
    assert access_policy.check_read("writer", "flights") is False


def test_check_read_unknown_role_returns_false():
    """An unregistered role should be denied all reads."""
    policy = AccessPolicy()
    assert policy.check_read("unknown", "budget") is False


def test_check_read_fnmatch_pattern():
    """Patterns like 'budget.*' should match 'budget.flights'."""
    policy = AccessPolicy()
    policy.register_role("scoped", can_read=["budget.*"], can_write=[])
    assert policy.check_read("scoped", "budget.flights") is True
    assert policy.check_read("scoped", "inventory.flights") is False


# ---------------------------------------------------------------------------
# check_write
# ---------------------------------------------------------------------------


def test_check_write_admin_can_write_anything(access_policy):
    """Admin role with can_write=['*'] should write any key."""
    assert access_policy.check_write("admin", "inventory.stock") is True


def test_check_write_reader_denied(access_policy):
    """Reader role with can_write=[] should be denied all writes."""
    assert access_policy.check_write("reader", "budget") is False
    assert access_policy.check_write("reader", "anything") is False


def test_check_write_writer_limited_to_budget(access_policy):
    """Writer role should only write to 'budget' keys."""
    assert access_policy.check_write("writer", "budget") is True
    assert access_policy.check_write("writer", "flights") is False
