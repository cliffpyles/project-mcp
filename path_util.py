"""
Path validation and resolution for project-mcp tools.

All project_path, target_path, and file path arguments must resolve under
a configurable root to prevent path traversal.
"""

import os
from pathlib import Path


def get_root() -> Path:
    """Return the allowed root for project paths (e.g. workspace)."""
    root = os.environ.get("PROJECT_MCP_ROOT")
    if root:
        return Path(root).resolve()
    return Path.cwd().resolve()


def resolve_project_path(project_path: str) -> Path:
    """
    Resolve and validate project_path under the configured root.
    Raises ValueError if the path escapes the root.
    """
    root = get_root()
    path = (root / project_path).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise ValueError(f"Path must be under root {root}: {project_path}")
    return path


def resolve_file_path(path_str: str, base: Path | None = None) -> Path:
    """
    Resolve and validate a file path under the configured root (or base).
    Raises ValueError if the path escapes.
    """
    root = base or get_root()
    path = (root / path_str).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise ValueError(f"Path must be under root {root}: {path_str}")
    return path
