"""Tests for the host-environment probes (E2-FEAT-010, `host_env.py`).

`is_python_host` is a deterministic, read-only, bounded probe used only to decide whether an
advisory install note is shown. It never mutates anything and never crashes.
"""
from __future__ import annotations

from pathlib import Path

from sertor_install_kit.host_env import is_python_host


def test_pyproject_marker_makes_host_python(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    assert is_python_host(tmp_path) is True


def test_setup_py_and_setup_cfg_markers(tmp_path: Path):
    (tmp_path / "setup.py").write_text("from setuptools import setup\n", encoding="utf-8")
    assert is_python_host(tmp_path) is True
    other = tmp_path / "cfg"
    other.mkdir()
    (other / "setup.cfg").write_text("[metadata]\n", encoding="utf-8")
    assert is_python_host(other) is True


def test_any_py_file_makes_host_python(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
    assert is_python_host(tmp_path) is True


def test_non_python_host_is_false(tmp_path: Path):
    # A .NET-looking host: no pyproject/setup and no .py sources.
    (tmp_path / "App.sln").write_text("Microsoft Visual Studio Solution File\n", encoding="utf-8")
    (tmp_path / "Foo.csproj").write_text("<Project></Project>\n", encoding="utf-8")
    assert is_python_host(tmp_path) is False


def test_py_only_in_excluded_dirs_does_not_count(tmp_path: Path):
    # A `.py` living only inside installer/VCS/venv dirs must NOT flip the verdict (they are not
    # host sources): the runtime `.sertor/` or a `.venv/` are excluded.
    for excluded in (".sertor", ".venv", ".git"):
        d = tmp_path / excluded
        d.mkdir()
        (d / "buried.py").write_text("x = 1\n", encoding="utf-8")
    assert is_python_host(tmp_path) is False


def test_py_beyond_max_depth_not_found(tmp_path: Path):
    # A `.py` deeper than max_depth is not discovered (bounded traversal).
    deep = tmp_path / "a" / "b" / "c" / "d"
    deep.mkdir(parents=True)
    (deep / "deep.py").write_text("x = 1\n", encoding="utf-8")
    assert is_python_host(tmp_path, max_depth=2) is False
    assert is_python_host(tmp_path, max_depth=5) is True


def test_empty_host_is_not_python(tmp_path: Path):
    assert is_python_host(tmp_path) is False
