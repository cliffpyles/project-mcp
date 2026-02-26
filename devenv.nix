{ pkgs, ... }: {
  packages = [
    pkgs.python3
    pkgs.uv
  ];

  enterShell = ''
    uv sync
  '';

  # HTTP transport: one server for all clients at http://localhost:8000/mcp
  processes.mcp.exec = "uv sync && uv run python server.py";
}
