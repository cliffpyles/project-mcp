"""
Artifact discovery and loading for the project-mcp server.

Artifacts are organized under artifacts/{context}/{type}/ so that:
- context: default, react, angular, aws, gcp, ... (folder = context)
- type: templates, configs, snippets, assets, components, iac, ... (under each context)

Adding new contexts or types is done by adding directories; no server code changes.
"""

from pathlib import Path

# MIME types by extension (extend as needed)
_MIME = {
    ".py": "text/x-python",
    ".tsx": "text/tsx",
    ".ts": "text/typescript",
    ".js": "text/javascript",
    ".jsx": "text/jsx",
    ".json": "application/json",
    ".toml": "text/x-toml",
    ".yaml": "text/yaml",
    ".yml": "text/yaml",
    ".md": "text/markdown",
    ".svg": "image/svg+xml",
    ".html": "text/html",
    ".css": "text/css",
    ".sh": "text/x-shellscript",
}


def get_mime(path: Path) -> str:
    """Infer MIME type from file extension."""
    return _MIME.get(path.suffix.lower(), "text/plain")


def read_artifact(artifact_root: Path, context: str, type_name: str, path_str: str) -> tuple[str, str]:
    """
    Read artifact content from artifact_root/context/type/path.
    path_str may contain slashes (e.g. fastapi-app/main.py).
    Returns (content, mime_type). Raises FileNotFoundError if not found or escapes root.
    """
    base = artifact_root / context / type_name
    base = base.resolve()
    if not base.is_dir():
        raise FileNotFoundError(f"Artifact not found: {context}/{type_name}")
    full = (base / path_str).resolve()
    try:
        full.relative_to(base)
    except ValueError:
        raise FileNotFoundError(f"Path escapes artifact root: {path_str}")
    if not full.exists():
        raise FileNotFoundError(f"Artifact not found: {context}/{type_name}/{path_str}")
    if full.is_dir():
        readme = full / "README.md"
        if readme.exists():
            return readme.read_text(encoding="utf-8"), "text/markdown"
        parts = [f"# Artifact: {context}/{type_name}/{path_str}\n"]
        for p in sorted(full.rglob("*")):
            if p.is_file():
                rel = p.relative_to(full)
                parts.append(f"## {rel}\n```\n{p.read_text(encoding='utf-8', errors='replace')}\n```")
        return "\n".join(parts), "text/markdown"
    return full.read_text(encoding="utf-8", errors="replace"), get_mime(full)


def list_contexts_and_types(artifact_root: Path) -> list[tuple[str, str]]:
    """List (context, type) pairs that exist under artifact_root."""
    out: list[tuple[str, str]] = []
    if not artifact_root.is_dir():
        return out
    for context_dir in sorted(artifact_root.iterdir()):
        if not context_dir.is_dir() or context_dir.name.startswith("."):
            continue
        for type_dir in sorted(context_dir.iterdir()):
            if type_dir.is_dir() and not type_dir.name.startswith("."):
                out.append((context_dir.name, type_dir.name))
    return out
