"""Unit tests for path_util."""

import os

import pytest

from path_util import get_root, resolve_file_path, resolve_project_path


def test_get_root_uses_cwd_when_env_unset(monkeypatch):
    """When PROJECT_MCP_ROOT is unset, get_root returns cwd."""
    monkeypatch.delenv("PROJECT_MCP_ROOT", raising=False)
    root = get_root()
    assert str(root.resolve()) == os.path.realpath(os.getcwd())


def test_get_root_uses_env_when_set(monkeypatch, tmp_path):
    """When PROJECT_MCP_ROOT is set, get_root returns that path resolved."""
    monkeypatch.setenv("PROJECT_MCP_ROOT", str(tmp_path))
    assert get_root() == tmp_path.resolve()


def test_resolve_project_path_under_root(project_root_env):
    """Valid relative path under root resolves correctly."""
    root = project_root_env
    (root / "foo").mkdir()
    path = resolve_project_path("foo")
    assert path == (root / "foo").resolve()
    path2 = resolve_project_path(".")
    assert path2 == root


def test_resolve_project_path_traversal_raises(project_root_env):
    """Path traversal (..) outside root raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        resolve_project_path("../etc/passwd")
    assert "must be under root" in str(exc_info.value)
    with pytest.raises(ValueError) as exc_info2:
        resolve_project_path("foo/../../etc")
    assert "must be under root" in str(exc_info2.value)


def test_resolve_file_path_under_root(project_root_env):
    """Valid file path under root resolves."""
    root = project_root_env
    path = resolve_file_path("bar/baz.txt")
    assert path == (root / "bar" / "baz.txt").resolve()


def test_resolve_file_path_with_base(project_root_env):
    """resolve_file_path with base uses base instead of get_root()."""
    root = project_root_env
    sub = root / "sub"
    sub.mkdir()
    path = resolve_file_path("x.txt", base=sub)
    assert path == (sub / "x.txt").resolve()


def test_resolve_file_path_traversal_raises(project_root_env):
    """File path escaping root raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        resolve_file_path("../../../etc/passwd")
    assert "must be under root" in str(exc_info.value)
