"""
Project Development MCP Server.

Exposes predefined artifacts (templates, configs, code) as Resources and
project lifecycle operations as Tools. Use with Cursor or any MCP client.
"""

import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from artifact_loader import (
    list_artifact_paths,
    list_contexts_and_types,
    read_artifact,
)
from path_util import resolve_file_path, resolve_project_path

# Root for client-facing artifacts: artifacts/{context}/{type}/...
_ARTIFACT_ROOT = Path(__file__).resolve().parent / "artifacts"

# Logging: level from env (default INFO)
_log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, _log_level, logging.INFO))
logger = logging.getLogger(__name__)

mcp = FastMCP(
    "ProjectDev",
    instructions=(
        "Use this server to create, update, deploy, debug, test, monitor, and configure "
        "projects. Fetch artifacts via Resources: artifact://{context}/{type}/{path} "
        "(e.g. artifact://default/configs/pyproject.toml, "
        "artifact://fastapi/templates/fastapi-app). "
        "Context: flexible grouping chosen by the maintainer (technology, project type, etc.). "
        "Examples: default (generic), fastapi, react, internal-admin, data-pipeline. "
        "Type: templates, configs, snippets, assets, components, iac."
    ),
    list_page_size=50,
)


# ---- Resources: unified artifact:// context/type/path (context-first layout) ----


@mcp.resource(
    "artifact://{context}/{type}/{path*}",
    tags={"artifacts"},
    mime_type="text/plain",
)
def resource_artifact(context: str, type: str, path: str) -> str:
    """Read artifact by context, type, path (e.g. default/templates/fastapi-app)."""
    if isinstance(path, list):
        path = "/".join(path)
    try:
        content, _ = read_artifact(_ARTIFACT_ROOT, context, type, path)
        return content
    except FileNotFoundError:
        logger.warning("Artifact not found: %s/%s/%s", context, type, path)
        return f"Error: Artifact not found: {context}/{type}/{path}"


# ---- Tools: project operations (path-validated, tagged, annotated) ----


@mcp.tool(
    tags={"artifacts", "discovery"},
    annotations={"readOnlyHint": True},
)
def list_artifacts(
    context: str | None = None,
    type: str | None = None,
) -> str:
    """List artifacts; filter by context/type. Returns JSON with uri per artifact."""
    pairs = list_contexts_and_types(_ARTIFACT_ROOT)
    if context is not None:
        pairs = [(c, t) for c, t in pairs if c == context]
    if type is not None:
        pairs = [(c, t) for c, t in pairs if t == type]
    result: list[dict] = []
    for c, t in pairs:
        paths = list_artifact_paths(_ARTIFACT_ROOT, c, t)
        for p in paths:
            result.append({"context": c, "type": t, "path": p, "uri": f"artifact://{c}/{t}/{p}"})
    return json.dumps(result, indent=2)


@mcp.custom_route("/health", methods=["GET"])
async def health(_request: Request) -> Response:
    """Health check for load balancers and k8s probes."""
    return JSONResponse({"status": "ok"})


@mcp.tool(
    tags={"create", "files"},
    annotations={"destructiveHint": True},
)
def _substitute_vars(text: str, variables: dict[str, str]) -> str:
    """Replace {{key}} with variables[key] in text. Leaves {{key}} if key missing."""
    for key, value in variables.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def create_project(
    template_id: str,
    target_path: str,
    context: str = "default",
    variables: dict[str, str] | None = None,
) -> str:
    """Create a project from a template. Use variables for {{key}} substitution."""
    logger.info(
        "create_project template_id=%s target_path=%s context=%s",
        template_id,
        target_path,
        context,
    )
    try:
        target = resolve_file_path(target_path)
    except ValueError as e:
        logger.warning("create_project path error: %s", e)
        return f"Error: {e}"
    template_dir = _ARTIFACT_ROOT / context / "templates" / template_id
    if not template_dir.is_dir():
        logger.warning("Template not found: %s/%s", context, template_id)
        return f"Template not found: {context}/{template_id}"
    vars_map = variables or {}
    target.mkdir(parents=True, exist_ok=True)
    for item in template_dir.rglob("*"):
        if item.is_file():
            rel = item.relative_to(template_dir)
            rel_str = str(rel).replace("\\", "/")
            if vars_map:
                rel_str = _substitute_vars(rel_str, vars_map)
            dest = target / rel_str
            dest.parent.mkdir(parents=True, exist_ok=True)
            if vars_map and item.suffix in (
                ".py",
                ".ts",
                ".tsx",
                ".js",
                ".jsx",
                ".json",
                ".toml",
                ".yaml",
                ".yml",
                ".md",
                ".html",
                ".css",
                ".sh",
                ".txt",
                ".cfg",
                ".ini",
            ):
                try:
                    content = item.read_text(encoding="utf-8", errors="replace")
                    content = _substitute_vars(content, vars_map)
                    dest.write_text(content, encoding="utf-8")
                except OSError:
                    shutil.copy2(item, dest)
            else:
                shutil.copy2(item, dest)
    return f"Created project at {target} from template {context}/{template_id}"


@mcp.tool(
    tags={"files"},
    annotations={"destructiveHint": True},
)
def write_file(path: str, content: str) -> str:
    """Write or overwrite a file at path (relative to PROJECT_MCP_ROOT or cwd)."""
    logger.info("write_file path=%s", path)
    try:
        resolved = resolve_file_path(path)
    except ValueError as e:
        logger.warning("write_file path error: %s", e)
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
        return (
            "No deploy script found (set options.script or add Makefile/package.json deploy target)"
        )
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
    """Update name or version in pyproject.toml or package.json."""
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


def main() -> None:
    """Entry point for the project-mcp CLI."""
    transport = os.environ.get("MCP_TRANSPORT", "http")
    if transport == "http":
        port = int(os.environ.get("MCP_PORT", "8000"))
        mcp.run(transport="http", host="0.0.0.0", port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
