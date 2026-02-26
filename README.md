# Project Development MCP Server

A [FastMCP](https://gofastmcp.com/) server that exposes predefined artifacts (templates, configs, code snippets, assets) as **Resources** and project lifecycle operations as **Tools**. Use it from [Cursor](https://cursor.com/) or any MCP client to create, update, deploy, debug, test, monitor, and configure projects with minimal token usage.

**Recommended: HTTP transport.** Run the server once; all clients (Cursor, other IDEs, CLIs) connect to the same URL. One process, shared use, no per-client spawn.

## Setup

### Option A: Nix + devenv (recommended)

With [Nix](https://nixos.org/) and [devenv](https://devenv.sh/) installed:

```bash
cd project-mcp
devenv up
```

This installs Python and uv, runs `uv sync`, and starts the MCP server on **HTTP** at `http://localhost:8000/mcp`. Leave it running; point Cursor and other clients at that URL. Use `direnv allow` if you use direnv (optional for `devenv up`).

### Option B: uv only

- Python 3.10+
- [uv](https://github.com/astral-sh/uv)
- [FastMCP](https://gofastmcp.com/) 3.x (installed via uv)

```bash
cd project-mcp
uv sync
```

## Running the server

**HTTP (recommended)** — one server for all clients:

```bash
# With devenv (starts HTTP server)
devenv up

# Or with uv only (HTTP is the default)
uv run python server.py
```

Server base URL: **`http://localhost:8000/mcp`** (port 8000 unless you set `MCP_PORT`). Connect Cursor and other clients to this URL; no need for each client to run the server.

**Stdio (alternative)** — Cursor or another client runs the server as a subprocess (one process per client). Set `MCP_TRANSPORT=stdio` or use the fastmcp CLI:

```bash
MCP_TRANSPORT=stdio uv run python server.py
# or
uv run fastmcp run fastmcp.json
```

Use stdio if you prefer zero “run the server” step and only one client.

### Configuration

- **`PROJECT_MCP_ROOT`** — Root directory for project paths (default: current working directory). Paths in tools must resolve under this root.
- **`MCP_TRANSPORT`** — `http` (default) or `stdio`.
- **`MCP_PORT`** — Port for HTTP (default: `8000`).

## Cursor integration

**HTTP (recommended):** Run the server once (e.g. `devenv up` or the HTTP command above), then add the server in Cursor by URL. Example MCP config (e.g. in Cursor Settings → MCP or `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "project-dev": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

If your Cursor version uses a different shape (e.g. `transport: "sse"` with a separate `url`), see [Cursor + FastMCP](https://gofastmcp.com/integrations/cursor). Use your actual host/port if not localhost. All Cursor windows and other clients can use the same running server.

**Stdio (alternative):** Cursor runs the server itself. In MCP settings use a **command** instead of a URL:

```json
{
  "mcpServers": {
    "project-dev": {
      "command": "uv",
      "args": ["run", "fastmcp", "run", "fastmcp.json"],
      "cwd": "/absolute/path/to/project-mcp"
    }
  }
}
```

Replace `/absolute/path/to/project-mcp` with the real path.

## Artifacts and URI scheme

Predefined content is organized by **context** first (folder under `artifacts/`), then **type** (folder under each context). **Context** is a flexible grouping—maintainers choose the strategy that fits their needs (e.g. by technology, project type, or other axes).

**URI pattern:** `artifact://{context}/{type}/{path}`

| Part      | Purpose | Examples |
| --------- | ------- | -------- |
| `context` | Grouping chosen by maintainer | `default` (generic), `fastapi`, `react`, `internal-admin`, `data-pipeline` |
| `type`    | Kind of artifact under that context | `templates`, `configs`, `snippets`, `assets`, `components`, `iac` |
| `path`    | Relative path under context/type | `fastapi-app`, `pyproject.toml`, `Button.tsx` |

**Context examples:**
- By technology: `fastapi`, `react`, `aws`, `gcp`
- By project type: `internal-admin`, `data-pipeline`, `research-notebook`, `app-documentation`
- `default`: generic, stack-agnostic artifacts only

**URI examples:**

- `artifact://default/configs/pyproject.toml` — generic Python config
- `artifact://default/snippets/hello.py` — generic hello snippet
- `artifact://fastapi/templates/fastapi-app` — FastAPI app template
- `artifact://react/templates/react-component.tsx` — React component template
- `artifact://data-pipeline/configs/dag.yaml` — data pipeline config (when added)

Add new contexts by adding a folder under `artifacts/`; add new types by adding a folder under a context. No server code changes required. Use **Resources** to read these URIs on demand so the LLM does not hold large blobs in context.

## Tools

| Tool             | Description                                                       |
| ---------------- | ----------------------------------------------------------------- |
| `create_project` | Create project from a template; use `context` to pick the group (e.g. fastapi, react). |
| `write_file`     | Write or overwrite a file under the project root.                 |
| `run_tests`      | Run tests (pytest or npm test).                                   |
| `deploy`         | Run deploy (Makefile, npm run deploy, or custom script).          |
| `run_command`    | Run an allowed command in project dir (python, npm, uv, etc.).    |
| `status`         | Project status and detected type.                                 |
| `get_logs`       | Recent log content from `.log` files.                             |
| `get_config`     | Read config key (e.g. name, version) from pyproject/package.json. |
| `update_config`  | Update name or version in pyproject.toml or package.json.         |

All paths are validated against `PROJECT_MCP_ROOT` to prevent path traversal.

## Project layout

```
project-mcp/
├── server.py           # FastMCP app and registration
├── path_util.py        # Path validation helpers
├── artifact_loader.py  # Artifact discovery and read (type/context/path)
├── fastmcp.json        # FastMCP project config
├── devenv.nix          # Nix + devenv (packages, process)
├── devenv.yaml         # Devenv inputs
├── .envrc              # direnv: use devenv
├── pyproject.toml
└── artifacts/          # Client-facing content: artifact://{context}/{type}/{path}
    ├── default/       # generic, stack-agnostic only
    │   ├── configs/   # pyproject.toml, tsconfig.json, Dockerfile
    │   ├── snippets/  # hello.py
    │   └── assets/    # placeholder.svg
    ├── fastapi/       # context: technology
    │   └── templates/ # fastapi-app
    ├── react/         # context: technology
    │   └── templates/ # react-component.tsx
    # Add contexts as needed: internal-admin/, data-pipeline/, aws/, gcp/, etc.
```

## License

MIT.
