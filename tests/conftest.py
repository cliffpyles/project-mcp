"""Pytest fixtures for project-mcp tests."""

import pytest


@pytest.fixture(autouse=True)
def project_root_env(tmp_path, monkeypatch):
    """Set PROJECT_MCP_ROOT to a temp directory so path_util and tools use it."""
    monkeypatch.setenv("PROJECT_MCP_ROOT", str(tmp_path))
    # Clear any cached root by reloading path_util behavior (get_root reads env each time)
    return tmp_path
