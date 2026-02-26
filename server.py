"""
Project Development MCP Server.

Exposes predefined artifacts (templates, configs, code) as Resources and
project lifecycle operations as Tools. Use with Cursor or any MCP client.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from fastmcp import FastMCP

from path_util import resolve_file_path, resolve_project_path

# Artifact root: directory containing server.py (project root)
_ARTIFACT_ROOT = Path(__file__).resolve().parent

mcp = FastMCP(
    "ProjectDev",
    instructions=(
        "Use this server to create, update, deploy, debug, test, monitor, and configure "
        "projects. Fetch templates and configs via Resources (project://, config://, "
        "template://, assets://) and run operations via Tools."
    ),
    list_page_size=50,
)


# ---- Resources: predefined artifacts (tags for visibility) ----

@mcp.resource(
    "project://snippets/hello.py",
    tags={"files", "snippets"},
    mime_type="text/x-python",
)
def resource_snippet_hello_py() -> str:
    """Minimal Python hello snippet."""
    path = _ARTIFACT_ROOT / "snippets" / "hello.py"
    return path.read_text() if path.exists() else "# snippet not found"


@mcp.resource(
    "project://snippets/dockerfile",
    tags={"files", "snippets"},
    mime_type="text/plain",
)
def resource_snippet_dockerfile() -> str:
    """Minimal Dockerfile snippet."""
    path = _ARTIFACT_ROOT / "snippets" / "dockerfile"
    return path.read_text() if path.exists() else "# snippet not found"


@mcp.resource(
    "config://default/pyproject",
    tags={"config"},
    mime_type="text/x-toml",
)
def resource_config_pyproject() -> str:
    """Default pyproject.toml config."""
    path = _ARTIFACT_ROOT / "configs" / "pyproject.toml"
    return path.read_text() if path.exists() else ""


@mcp.resource(
    "config://default/tsconfig",
    tags={"config"},
    mime_type="application/json",
)
def resource_config_tsconfig() -> str:
    """Default tsconfig.json config."""
    path = _ARTIFACT_ROOT / "configs" / "tsconfig.json"
    return path.read_text() if path.exists() else "{}"


@mcp.resource(
    "config://default/dockerfile",
    tags={"config"},
    mime_type="text/plain",
)
def resource_config_dockerfile() -> str:
    """Default Dockerfile config."""
    path = _ARTIFACT_ROOT / "configs" / "Dockerfile"
    return path.read_text() if path.exists() else ""


@mcp.resource(
    "assets://placeholder.svg",
    tags={"assets"},
    mime_type="image/svg+xml",
)
def resource_assets_placeholder() -> str:
    """Placeholder SVG asset."""
    path = _ARTIFACT_ROOT / "assets" / "placeholder.svg"
    return path.read_text() if path.exists() else ""


# Resource template: template://{name} — named template content
@mcp.resource(
    "template://{name}",
    tags={"templates"},
    mime_type="text/plain",
)
def resource_template_name(name: str) -> str:
    """Get template content by name (e.g. fastapi-app/main.py, react-component.tsx)."""
    # Support both "fastapi-app" (directory) and "file.ext" (file in templates/)
    base = _ARTIFACT_ROOT / "templates"
    if "/" in name or "\\" in name:
        path = (base / name).resolve()
    else:
        path = (base / name).resolve()
    if not path.exists():
        return f"# Template not found: {name}"
    if path.is_file():
        return path.read_text()
    # Directory: return README if present, else list of files
    readme = path / "README.md"
    if readme.exists():
        return readme.read_text()
    parts = [f"# Template: {name}\n"]
    for p in sorted(path.rglob("*")):
        if p.is_file():
            rel = p.relative_to(path)
            parts.append(f"## {rel}\n```\n{p.read_text()}\n```")
    return "\n".join(parts)


# config://{type} — config by type
@mcp.resource(
    "config://{config_type}",
    tags={"config", "templates"},
    mime_type="text/plain",
)
def resource_config_type(config_type: str) -> str:
    """Get config content by type (pyproject, tsconfig, dockerfile)."""
    known = {"pyproject": "pyproject.toml", "tsconfig": "tsconfig.json", "dockerfile": "Dockerfile"}
    filename = known.get(config_type.lower())
    if not filename:
        return f"# Unknown config type: {config_type}. Known: {list(known)}"
    path = _ARTIFACT_ROOT / "configs" / filename
    return path.read_text() if path.exists() else ""


# ---- Tools: project operations (path-validated, tagged, annotated) ----

@mcp.tool(
    tags={"create", "files"},
    annotations={"destructiveHint": True},
)
def create_project(template_id: str, target_path: str) -> str:
    """Create a new project from a predefined template (e.g. fastapi-app)."""
    try:
        target = resolve_file_path(target_path)
    except ValueError as e:
        return f"Error: {e}"
    template_dir = _ARTIFACT_ROOT / "templates" / template_id
    if not template_dir.is_dir():
        return f"Template not found: {template_id}"
    target.mkdir(parents=True, exist_ok=True)
    for item in template_dir.rglob("*"):
        if item.is_file():
            rel = item.relative_to(template_dir)
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)
    return f"Created project at {target} from template {template_id}"


@mcp.tool(
    tags={"files"},
    annotations={"destructiveHint": True},
)
def write_file(path: str, content: str) -> str:
    """Write or overwrite a file at path (relative to PROJECT_MCP_ROOT or cwd)."""
    try:
        resolved = resolve_file_path(path)
    except ValueError as e:
        return f"Error: {e}"
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return f"Wrote {resolved}"


@mcp.tool(
    tags={"test"},
    annotations={"readOnlyHint": False},
)
def run_tests(
    project_path: str,
    scope: str | None = None,
    extra_args: list[str] | None = None,
) -> str:
    """Run tests in project (pytest for Python, npm test for Node)."""
    try:
        root = resolve_project_path(project_path)
    except ValueError as e:
        return f"Error: {e}"
    extra_args = extra_args or []
    # Prefer pytest if pyproject or setup.cfg or pytest.ini
    if (root / "pyproject.toml").exists() or (root / "pytest.ini").exists():
        cmd = ["pytest", "-v"]
        if scope:
            cmd.extend(["-k", scope])
        cmd.extend(extra_args)
    elif (root / "package.json").exists():
        cmd = ["npm", "test", "--"]
        if scope:
            cmd.append(scope)
        cmd.extend(extra_args)
    else:
        return "No test runner detected (no pyproject.toml/pytest.ini or package.json)"
    try:
        result = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=300,
        )
        out = result.stdout or ""
        if result.stderr:
            out += "\n" + result.stderr
        if result.returncode != 0:
            out += f"\nExit code: {result.returncode}"
        return out.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: test run timed out (300s)"
    except FileNotFoundError:
        return f"Error: command not found ({cmd[0]})"


@mcp.tool(
    tags={"deploy"},
    annotations={"destructiveHint": True, "openWorldHint": True},
)
def deploy(project_path: str, target: str, options: dict | None = None) -> str:
    """Trigger deployment for a project (runs deploy script or make deploy)."""
    try:
        root = resolve_project_path(project_path)
    except ValueError as e:
        return f"Error: {e}"
    options = options or {}
    # Prefer explicit script; else try make deploy or npm run deploy
    if options.get("script"):
        cmd = [options["script"]]
    elif (root / "Makefile").exists():
        cmd = ["make", "deploy"]
    elif (root / "package.json").exists():
        cmd = ["npm", "run", "deploy"]
    else:
        return "No deploy script found (set options.script or add Makefile/package.json deploy target)"
    try:
        result = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=600,
            env={**os.environ, **options.get("env", {})},
        )
        out = result.stdout or ""
        if result.stderr:
            out += "\n" + result.stderr
        if result.returncode != 0:
            out += f"\nExit code: {result.returncode}"
        return f"Target: {target}\n" + (out.strip() or "(no output)")
    except subprocess.TimeoutExpired:
        return "Error: deploy timed out (600s)"
    except FileNotFoundError:
        return f"Error: command not found ({cmd[0]})"


@mcp.tool(
    tags={"debug", "run"},
    annotations={"readOnlyHint": False},
)
def run_command(
    project_path: str,
    command: str,
    env: dict[str, str] | None = None,
) -> str:
    """Run a single command in the project directory (e.g. python main.py, npm start)."""
    try:
        root = resolve_project_path(project_path)
    except ValueError as e:
        return f"Error: {e}"
    allowlist = ("python", "npm", "npx", "uv", "pip", "node", "pytest", "make")
    parts = command.strip().split()
    if not parts or parts[0].lower() not in allowlist:
        return f"Command must start with one of: {allowlist}"
    env_merged = {**os.environ}
    if env:
        env_merged.update(env)
    try:
        result = subprocess.run(
            parts,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=120,
            env=env_merged,
        )
        out = result.stdout or ""
        if result.stderr:
            out += "\n" + result.stderr
        if result.returncode != 0:
            out += f"\nExit code: {result.returncode}"
        return out.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: command timed out (120s)"
    except FileNotFoundError:
        return f"Error: command not found ({parts[0]})"


@mcp.tool(
    tags={"monitor"},
    annotations={"readOnlyHint": True},
)
def status(project_path: str) -> str:
    """Return project status: detected type, key files, and recent dir listing."""
    try:
        root = resolve_project_path(project_path)
    except ValueError as e:
        return f"Error: {e}"
    if not root.exists():
        return "Project path does not exist"
    lines = [f"Path: {root}", "Detected:"]
    if (root / "pyproject.toml").exists():
        lines.append("  - Python (pyproject.toml)")
    if (root / "package.json").exists():
        lines.append("  - Node (package.json)")
    if (root / "Dockerfile").exists():
        lines.append("  - Dockerfile present")
    lines.append("Top-level files:")
    for p in sorted(root.iterdir())[:20]:
        kind = "dir" if p.is_dir() else "file"
        lines.append(f"  {kind}: {p.name}")
    return "\n".join(lines)


@mcp.tool(
    tags={"monitor"},
    annotations={"readOnlyHint": True},
)
def get_logs(project_path: str, source: str = "stdout", lines: int | None = 50) -> str:
    """Read recent log content from project (looks for log files or .log)."""
    try:
        root = resolve_project_path(project_path)
    except ValueError as e:
        return f"Error: {e}"
    n = min(lines or 50, 500)
    log_candidates = list(root.rglob("*.log"))[:5]
    if not log_candidates:
        return "No .log files found in project"
    out_lines = []
    for log_path in log_candidates:
        try:
            content = log_path.read_text(encoding="utf-8", errors="replace")
            tail = content.splitlines()[-n:]
            out_lines.append(f"## {log_path.relative_to(root)}\n" + "\n".join(tail))
        except OSError:
            out_lines.append(f"## {log_path.name} (unreadable)")
    return "\n\n".join(out_lines) if out_lines else "No log content"


@mcp.tool(
    tags={"configure"},
    annotations={"readOnlyHint": True},
)
def get_config(project_path: str, key: str) -> str:
    """Read a config value from project (e.g. pyproject name, package.json name)."""
    try:
        root = resolve_project_path(project_path)
    except ValueError as e:
        return f"Error: {e}"
    key_lower = key.lower()
    if (root / "pyproject.toml").exists():
        text = (root / "pyproject.toml").read_text()
        if key_lower == "name":
            m = re.search(r'\[project\]\s*\n.*?name\s*=\s*["\']([^"\']+)["\']', text, re.DOTALL)
            return m.group(1) if m else ""
        if key_lower == "version":
            m = re.search(r'\[project\]\s*\n.*?version\s*=\s*["\']([^"\']+)["\']', text, re.DOTALL)
            return m.group(1) if m else ""
    if (root / "package.json").exists():
        data = json.loads((root / "package.json").read_text())
        return str(data.get(key_lower, ""))
    return f"Unknown key or no supported config file: {key}"


@mcp.tool(
    tags={"configure"},
    annotations={"destructiveHint": True},
)
def update_config(project_path: str, key: str, value: str) -> str:
    """Update a config key in project (pyproject.toml or package.json). Only name/version supported."""
    try:
        root = resolve_project_path(project_path)
    except ValueError as e:
        return f"Error: {e}"
    key_lower = key.lower()
    if key_lower not in ("name", "version"):
        return "Only name and version are supported for update_config"
    if (root / "pyproject.toml").exists():
        path = root / "pyproject.toml"
        content = path.read_text()
        # Simple line-based replace for [project] name = "..." or version = "..."
        pattern = rf"^(\s*{key_lower}\s*=\s*)[\"'].*?[\"']"
        new_line = re.sub(pattern, rf'\g<1>"{value}"', content, count=1, flags=re.MULTILINE)
        if new_line == content:
            return f"Could not find {key} in pyproject.toml"
        path.write_text(new_line)
        return f"Updated {key}={value} in pyproject.toml"
    if (root / "package.json").exists():
        path = root / "package.json"
        data = json.loads(path.read_text())
        data[key_lower] = value
        path.write_text(json.dumps(data, indent=2) + "\n")
        return f"Updated {key}={value} in package.json"
    return "No pyproject.toml or package.json found"


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "http":
        port = int(os.environ.get("MCP_PORT", "8000"))
        mcp.run(transport="http", host="0.0.0.0", port=port)
    else:
        mcp.run()
