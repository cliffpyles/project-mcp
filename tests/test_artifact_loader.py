"""Unit tests for artifact_loader."""

from pathlib import Path

import pytest

from artifact_loader import (
    get_mime,
    list_artifact_paths,
    list_contexts_and_types,
    read_artifact,
)


def test_get_mime():
    """MIME types are inferred from extension."""
    assert get_mime(Path("x.py")) == "text/x-python"
    assert get_mime(Path("x.json")) == "application/json"
    assert get_mime(Path("x.toml")) == "text/x-toml"
    assert get_mime(Path("x.md")) == "text/markdown"
    assert get_mime(Path("x.unknown")) == "text/plain"
    assert get_mime(Path("x.PY")) == "text/x-python"


def test_read_artifact_file(project_root_env):
    """read_artifact returns file content and MIME for a single file."""
    root = project_root_env
    (root / "ctx" / "snippets").mkdir(parents=True)
    (root / "ctx" / "snippets" / "hello.py").write_text("print(1)")
    content, mime = read_artifact(root, "ctx", "snippets", "hello.py")
    assert content == "print(1)"
    assert mime == "text/x-python"


def test_read_artifact_path_with_slashes(project_root_env):
    """read_artifact accepts path with slashes."""
    root = project_root_env
    (root / "c" / "t" / "sub").mkdir(parents=True)
    (root / "c" / "t" / "sub" / "file.txt").write_text("data")
    content, _ = read_artifact(root, "c", "t", "sub/file.txt")
    assert content == "data"


def test_read_artifact_traversal_raises(project_root_env):
    """Path escaping artifact base raises FileNotFoundError."""
    root = project_root_env
    (root / "ctx" / "type").mkdir(parents=True)
    (root / "ctx" / "type" / "file.txt").write_text("x")
    with pytest.raises(FileNotFoundError) as exc_info:
        read_artifact(root, "ctx", "type", "../../../etc/passwd")
    assert "escapes" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()


def test_read_artifact_missing_raises(project_root_env):
    """Missing artifact raises FileNotFoundError."""
    root = project_root_env
    (root / "ctx" / "type").mkdir(parents=True)
    with pytest.raises(FileNotFoundError):
        read_artifact(root, "ctx", "type", "nonexistent.txt")


def test_read_artifact_dir_returns_readme_if_present(project_root_env):
    """Reading a directory returns README.md content if present."""
    root = project_root_env
    (root / "ctx" / "templates" / "my-app").mkdir(parents=True)
    (root / "ctx" / "templates" / "my-app" / "README.md").write_text("# My App")
    content, mime = read_artifact(root, "ctx", "templates", "my-app")
    assert "# My App" in content
    assert mime == "text/markdown"


def test_read_artifact_dir_no_readme_returns_listing(project_root_env):
    """Reading a directory without README returns concatenated file listing."""
    root = project_root_env
    (root / "ctx" / "t" / "dir").mkdir(parents=True)
    (root / "ctx" / "t" / "dir" / "a.txt").write_text("a")
    (root / "ctx" / "t" / "dir" / "b.txt").write_text("b")
    content, mime = read_artifact(root, "ctx", "t", "dir")
    assert "Artifact:" in content
    assert "a.txt" in content
    assert "b.txt" in content
    assert "a" in content
    assert "b" in content
    assert mime == "text/markdown"


def test_list_contexts_and_types_empty(project_root_env):
    """Empty or missing root returns empty list."""
    root = project_root_env
    assert list_contexts_and_types(root) == []
    assert list_contexts_and_types(root / "nonexistent") == []


def test_list_contexts_and_types(project_root_env):
    """Lists (context, type) for existing dirs; skips hidden."""
    root = project_root_env
    (root / "default" / "configs").mkdir(parents=True)
    (root / "default" / "snippets").mkdir(parents=True)
    (root / "fastapi" / "templates").mkdir(parents=True)
    (root / ".hidden" / "x").mkdir(parents=True)
    (root / "default" / ".hidden").mkdir(parents=True)
    pairs = list_contexts_and_types(root)
    assert ("default", "configs") in pairs
    assert ("default", "snippets") in pairs
    assert ("fastapi", "templates") in pairs
    assert (".hidden", "x") not in pairs
    assert ("default", ".hidden") not in pairs


def test_list_artifact_paths(project_root_env):
    """list_artifact_paths returns relative paths under context/type."""
    root = project_root_env
    (root / "c" / "t" / "sub").mkdir(parents=True)
    (root / "c" / "t" / "sub" / "file.txt").write_text("x")
    (root / "c" / "t" / "top.txt").write_text("y")
    paths = list_artifact_paths(root, "c", "t")
    assert "top.txt" in paths
    assert "sub/file.txt" in paths or "sub\\file.txt" in paths
