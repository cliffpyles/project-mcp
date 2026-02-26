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


def test_read_file(project_root_env):
    """read_file returns file content."""
    root = project_root_env
    (root / "foo.txt").write_text("hello world")
    result = server_module.read_file(path="foo.txt")
    assert result == "hello world"


def test_read_file_traversal_rejected(project_root_env):
    """read_file rejects path traversal."""
    result = server_module.read_file(path="../../../etc/passwd")
    assert "Error" in result
    assert "root" in result.lower()


def test_read_file_not_found(project_root_env):
    """read_file returns error when file does not exist."""
    result = server_module.read_file(path="nonexistent.txt")
    assert "Error" in result
    assert "not found" in result.lower()


def test_read_file_directory_rejected(project_root_env):
    """read_file returns error when path is a directory."""
    root = project_root_env
    (root / "adir").mkdir()
    result = server_module.read_file(path="adir")
    assert "Error" in result
    assert "directory" in result.lower()


def test_list_directory(project_root_env):
    """list_directory returns entries with type and size."""
    root = project_root_env
    (root / "a.txt").write_text("hi")
    (root / "subdir").mkdir()
    result = server_module.list_directory(path=".")
    assert "Path:" in result
    assert "file: a.txt" in result
    assert "dir: subdir" in result


def test_list_directory_traversal_rejected(project_root_env):
    """list_directory rejects path traversal."""
    result = server_module.list_directory(path="../../../etc")
    assert "Error" in result
    assert "root" in result.lower()


def test_list_directory_not_found(project_root_env):
    """list_directory returns error when path does not exist."""
    result = server_module.list_directory(path="nonexistent")
    assert "Error" in result
    assert "not exist" in result.lower()


def test_list_directory_file_rejected(project_root_env):
    """list_directory returns error when path is a file."""
    root = project_root_env
    (root / "f.txt").write_text("x")
    result = server_module.list_directory(path="f.txt")
    assert "Error" in result
    assert "not a directory" in result.lower()


def test_search_files(project_root_env):
    """search_files returns matching lines with path and line number."""
    root = project_root_env
    (root / "a.py").write_text("x = 1\nfoo bar\nx = 2")
    (root / "b.py").write_text("no match")
    result = server_module.search_files(project_path=".", pattern=r"x\s*=")
    assert "a.py:1:" in result
    assert "a.py:3:" in result
    assert "x = 1" in result or "x = 2" in result
    assert "b.py" not in result


def test_search_files_no_matches(project_root_env):
    """search_files returns (no matches) when pattern not found."""
    root = project_root_env
    (root / "a.txt").write_text("hello")
    result = server_module.search_files(project_path=".", pattern="xyz")
    assert "no matches" in result


def test_search_files_include_glob(project_root_env):
    """search_files respects include glob."""
    root = project_root_env
    (root / "a.py").write_text("needle")
    (root / "a.txt").write_text("needle")
    result = server_module.search_files(project_path=".", pattern="needle", include="*.py")
    assert "a.py" in result
    assert "a.txt" not in result


def test_search_files_traversal_rejected(project_root_env):
    """search_files rejects project_path traversal."""
    result = server_module.search_files(project_path="../../../etc", pattern="x")
    assert "Error" in result
    assert "root" in result.lower()


def test_search_files_invalid_regex(project_root_env):
    """search_files returns error for invalid regex."""
    result = server_module.search_files(project_path=".", pattern="[invalid")
    assert "Error" in result
    assert "regex" in result.lower()


def test_edit_file(project_root_env):
    """edit_file replaces old_string with new_string."""
    root = project_root_env
    (root / "f.txt").write_text("hello world")
    result = server_module.edit_file(path="f.txt", old_string="world", new_string="there")
    assert "Replaced" in result
    assert (root / "f.txt").read_text() == "hello there"


def test_edit_file_replace_all(project_root_env):
    """edit_file with replace_all=True replaces every occurrence."""
    root = project_root_env
    (root / "f.txt").write_text("x x x")
    result = server_module.edit_file(path="f.txt", old_string="x", new_string="y", replace_all=True)
    assert "3 occurrence" in result
    assert (root / "f.txt").read_text() == "y y y"


def test_edit_file_replace_first(project_root_env):
    """edit_file with replace_all=False replaces only first."""
    root = project_root_env
    (root / "f.txt").write_text("a a a")
    result = server_module.edit_file(
        path="f.txt", old_string="a", new_string="b", replace_all=False
    )
    assert "1 occurrence" in result
    assert (root / "f.txt").read_text() == "b a a"


def test_edit_file_old_string_not_found(project_root_env):
    """edit_file returns error when old_string not in file."""
    root = project_root_env
    (root / "f.txt").write_text("hello")
    result = server_module.edit_file(path="f.txt", old_string="xyz", new_string="y")
    assert "Error" in result
    assert "not found" in result.lower()
    assert (root / "f.txt").read_text() == "hello"


def test_edit_file_traversal_rejected(project_root_env):
    """edit_file rejects path traversal."""
    result = server_module.edit_file(path="../../../etc/passwd", old_string="x", new_string="y")
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
