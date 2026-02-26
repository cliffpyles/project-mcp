# Project Development MCP Server

A [FastMCP](https://gofastmcp.com/) server that exposes predefined artifacts (templates, configs, code snippets, assets) as **Resources** and project lifecycle operations as **Tools**. Use it from [Cursor](https://cursor.com/) or any MCP client to create, update, deploy, debug, test, monitor, and configure projects with minimal token usage.

## Setup

### Dependencies

- Python 3.10+
- [uv](https://github.com/astral-sh/uv)
- [FastMCP](https://gofastmcp.com/) 3.x (installed via uv)

```bash
cd project-mcp
uv sync
```

### Configuration

Optional environment variables:

- **`PROJECT_MCP_ROOT`** — Root directory for all project paths (default: current working directory). Paths passed to tools must resolve under this root.
- **`MCP_TRANSPORT`** — `stdio` (default) or `http`.
- **`MCP_PORT`** — Port for HTTP transport (default: `8000`).

## Running the server

**Stdio (default, for Cursor):**

```bash
# From project root (uses fastmcp from project venv)
uv run fastmcp run fastmcp.json

# Or run server module directly
uv run python server.py
```

**HTTP (remote):**

```bash
MCP_TRANSPORT=http MCP_PORT=8000 uv run python server.py
# Server at http://localhost:8000/mcp
```

## Cursor integration

Add the server to Cursor’s MCP settings (e.g. **Settings → MCP** or `.cursor/mcp.json`). Use `uv` so the server runs with the project’s virtualenv (the `fastmcp` CLI is not on PATH outside the project).

**Using `uv run fastmcp run` (recommended):**

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

**Using `uv run python`:**

```json
{
  "mcpServers": {
    "project-dev": {
      "command": "uv",
      "args": ["run", "python", "server.py"],
      "cwd": "/absolute/path/to/project-mcp"
    }
  }
}
```

Replace `/absolute/path/to/project-mcp` with the real path. For more options see [Cursor + FastMCP](https://gofastmcp.com/integrations/cursor).

## URI schemes (Resources)

Fetch predefined content by URI instead of loading it into context:

| Scheme        | Example                          | Description                          |
|---------------|-----------------------------------|--------------------------------------|
| `project://` | `project://snippets/hello.py`     | Code/snippet files                   |
| `config://`  | `config://default/pyproject`      | Default configs (pyproject, tsconfig, dockerfile) |
| `config://`  | `config://pyproject`              | Config by type (template: `config://{config_type}`) |
| `template://`| `template://fastapi-app`          | Named template (dir or file; template: `template://{name}`) |
| `assets://`  | `assets://placeholder.svg`        | Static assets                        |

Use **Resources** to read these URIs on demand so the LLM does not need to hold large blobs in context.

## Tools

| Tool            | Description |
|-----------------|-------------|
| `create_project`| Create project from a template (e.g. `fastapi-app`). |
| `write_file`    | Write or overwrite a file under the project root. |
| `run_tests`     | Run tests (pytest or npm test). |
| `deploy`        | Run deploy (Makefile, npm run deploy, or custom script). |
| `run_command`   | Run an allowed command in project dir (python, npm, uv, etc.). |
| `status`        | Project status and detected type. |
| `get_logs`      | Recent log content from `.log` files. |
| `get_config`    | Read config key (e.g. name, version) from pyproject/package.json. |
| `update_config` | Update name or version in pyproject.toml or package.json. |

All paths are validated against `PROJECT_MCP_ROOT` to prevent path traversal.

## Project layout

```
project-mcp/
├── server.py          # FastMCP app and registration
├── path_util.py       # Path validation helpers
├── fastmcp.json       # FastMCP project config
├── pyproject.toml
├── templates/         # Predefined project templates
│   ├── fastapi-app/
│   └── react-component.tsx
├── configs/           # Default config files
│   ├── pyproject.toml
│   ├── tsconfig.json
│   └── Dockerfile
├── snippets/          # Code snippets
└── assets/            # Static assets
```

## License

MIT.
