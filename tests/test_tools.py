"""Integration tests for MCP tools."""

import json
from pathlib import Path

import pytest

# Import after env is set so path_util.get_root() sees PROJECT_MCP_ROOT
import server as server_module


def test_create_project(project_root_env):
    """create_project copies template files to target_path."""
    root = project_root_env
    artifact_root = Path(server_module.__file__).resolve().parent / "artifacts"
    # Use existing fastapi template
    template_dir = artifact_root / "fastapi" / "templates" / "fastapi-app"
    if not template_dir.is_dir():
        pytest.skip("fastapi-app template not found")
    result = server_module.create_project(
        template_id="fastapi-app",
        target_path="my-api",
        context="fastapi",
    )
    assert "Created" in result
    assert (root / "my-api" / "main.py").exists()
    assert "FastAPI" in (root / "my-api" / "main.py").read_text()


def test_create_project_template_not_found(project_root_env):
    """create_project returns error when template does not exist."""
    result = server_module.create_project(
        template_id="nonexistent",
        target_path="out",
        context="default",
    )
    assert "not found" in result.lower() or "Error" in result


def test_create_project_with_variables(project_root_env):
    """create_project substitutes {{key}} in text files when variables provided."""
    root = project_root_env
    artifact_root = Path(server_module.__file__).resolve().parent / "artifacts"
    if not (artifact_root / "default" / "templates" / "var-test").is_dir():
        pytest.skip("var-test template not found")
    result = server_module.create_project(
        template_id="var-test",
        target_path="out-vars",
        context="default",
        variables={"project_name": "MyApp", "version": "1.0"},
    )
    assert "Created" in result
    out_file = root / "out-vars" / "greet.txt"
    assert out_file.exists()
    assert "MyApp" in out_file.read_text()
    assert "1.0" in out_file.read_text()


def test_write_file(project_root_env):
    """write_file creates file with content."""
    root = project_root_env
    result = server_module.write_file(path="foo/bar.txt", content="hello")
    assert "Wrote" in result
    assert (root / "foo" / "bar.txt").read_text() == "hello"


def test_write_file_traversal_rejected(project_root_env):
    """write_file rejects path traversal."""
    result = server_module.write_file(path="../../../etc/evil", content="x")
    assert "Error" in result
    assert "root" in result.lower()


def test_status(project_root_env):
    """status returns detected type and listing."""
    root = project_root_env
    (root / "pyproject.toml").write_text('[project]\nname = "p"\nversion = "0.1.0"')
    result = server_module.status(project_path=".")
    assert "Path:" in result
    assert "Python" in result
    assert "pyproject.toml" in result


def test_status_nonexistent(project_root_env):
    """status for nonexistent path returns message."""
    result = server_module.status(project_path="nonexistent-dir-xyz")
    assert "does not exist" in result or "Path" in result


def test_get_config_name(project_root_env):
    """get_config returns name from pyproject.toml."""
    root = project_root_env
    (root / "pyproject.toml").write_text('[project]\nname = "my-app"\nversion = "1.0.0"')
    result = server_module.get_config(project_path=".", key="name")
    assert result == "my-app"


def test_get_config_version(project_root_env):
    """get_config returns version from pyproject.toml."""
    root = project_root_env
    (root / "pyproject.toml").write_text('[project]\nname = "my-app"\nversion = "1.0.0"')
    result = server_module.get_config(project_path=".", key="version")
    assert result == "1.0.0"


def test_get_config_package_json(project_root_env):
    """get_config returns key from package.json."""
    root = project_root_env
    (root / "package.json").write_text('{"name": "my-node-app", "version": "2.0.0"}')
    result = server_module.get_config(project_path=".", key="name")
    assert result == "my-node-app"


def test_update_config_pyproject(project_root_env):
    """update_config updates name in pyproject.toml."""
    root = project_root_env
    (root / "pyproject.toml").write_text('[project]\nname = "old"\nversion = "0.1.0"')
    result = server_module.update_config(project_path=".", key="name", value="new-name")
    assert "Updated" in result
    text = (root / "pyproject.toml").read_text()
    assert "new-name" in text


def test_update_config_rejects_unsupported_key(project_root_env):
    """update_config rejects keys other than name/version."""
    root = project_root_env
    (root / "pyproject.toml").write_text('[project]\nname = "p"')
    result = server_module.update_config(project_path=".", key="dependencies", value="[]")
    assert "Only" in result or "supported" in result.lower()


def test_run_tests_no_runner(project_root_env):
    """run_tests returns message when no test runner detected."""
    root = project_root_env
    (root / "empty").mkdir()
    result = server_module.run_tests(project_path="empty")
    assert "No test runner" in result or "detected" in result.lower()


def test_run_tests_pytest(project_root_env):
    """run_tests runs pytest when pyproject.toml present with pytest."""
    root = project_root_env
    pyproject = (
        '[project]\nname = "p"\nversion = "0.1.0"\n\n'
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]'
    )
    (root / "pyproject.toml").write_text(pyproject)
    (root / "tests").mkdir()
    (root / "tests" / "test_foo.py").write_text("def test_ok(): assert True")
    result = server_module.run_tests(project_path=".")
    assert "passed" in result.lower() or "PASSED" in result or "no output" in result


def test_run_command_allowlist(project_root_env):
    """run_command rejects command not in allowlist."""
    result = server_module.run_command(project_path=".", command="curl http://evil.com")
    ok = (
        "must start with" in result.lower()
        or "allowlist" in result.lower()
        or "one of" in result.lower()
    )
    assert ok


def test_run_command_valid(project_root_env):
    """run_command runs allowed command."""
    result = server_module.run_command(project_path=".", command='python -c "print(42)"')
    assert "42" in result or "no output" in result


def test_deploy_no_script(project_root_env):
    """deploy returns message when no Makefile or npm deploy."""
    root = project_root_env
    (root / "empty").mkdir()
    result = server_module.deploy(project_path="empty", target="prod")
    assert "No deploy script" in result or "not found" in result.lower()


def test_get_logs_no_logs(project_root_env):
    """get_logs returns message when no .log files."""
    result = server_module.get_logs(project_path=".", lines=10)
    assert "No .log" in result or "not found" in result.lower()


def test_list_artifacts_returns_json(project_root_env):
    """list_artifacts returns JSON array of artifact entries with uri."""
    result = server_module.list_artifacts()
    data = json.loads(result)
    assert isinstance(data, list)
    for item in data[:3]:
        assert "context" in item
        assert "type" in item
        assert "path" in item
        assert "uri" in item
        assert item["uri"].startswith("artifact://")


def test_list_artifacts_filter_by_context(project_root_env):
    """list_artifacts with context filter returns only that context."""
    result = server_module.list_artifacts(context="default")
    data = json.loads(result)
    for item in data:
        assert item["context"] == "default"
