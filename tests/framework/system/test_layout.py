"""The test tree keeps its shape as it grows (context/testing.md §2).  These fail until a new module or test
file is put where the runner and the slicing expect it."""

from __future__ import annotations

import ast

import pytest

from tests.harness.lib import (EXTRA_SUITES, KINDS, TESTS_ROOT, find_test_files, module_names,
                               suite_names)


def test_every_module_has_a_suite() -> None:
    missing = [m for m in module_names() if not (TESTS_ROOT / m).is_dir()]
    assert not missing, f"add tests/<module>/system/test_imports.py for: {missing} (TS-H02)"


def test_every_module_suite_has_the_import_test() -> None:
    missing = [m for m in module_names() if not (TESTS_ROOT / m / "system" / "test_imports.py").exists()]
    assert not missing, f"copy tests/hh/system/test_imports.py into: {missing} (TS-H03)"


def test_every_suite_is_a_module_or_a_listed_extra() -> None:
    allowed = set(module_names()) | set(EXTRA_SUITES)
    stray = [s for s in suite_names() if s not in allowed]
    assert not stray, f"tests/ folders that are neither a module nor framework/live: {stray} (TS-H02)"


def test_every_test_file_is_a_system_or_data_test() -> None:
    misplaced = []
    for f in find_test_files():
        rel = f.relative_to(TESTS_ROOT)
        if len(rel.parts) < 3 or rel.parts[1] not in KINDS:
            misplaced.append(str(rel))
    assert not misplaced, f"test files must sit under tests/<suite>/system/ or tests/<suite>/data/: {misplaced}"


def test_no_python_files_outside_the_layout() -> None:
    """A helper module next to the tests is fine; a test file named without test_ would never run."""
    stray = []
    for kind in KINDS:
        for f in TESTS_ROOT.glob(f"*/{kind}/**/*.py"):
            if "__pycache__" in f.parts or f.name.startswith(("test_", "_")) or f.name == "conftest.py":
                continue
            stray.append(str(f.relative_to(TESTS_ROOT)))
    assert not stray, f"rename to test_*.py, or to _*.py for a helper: {stray}"


@pytest.mark.parametrize("path", find_test_files(), ids=lambda p: str(p.relative_to(TESTS_ROOT)))
def test_no_skip_calls(path) -> None:
    """TS-H22/TS-H23: a test never skips itself to get a pass.  xfail(strict) is the only way to pin a known bug."""
    tree = ast.parse(path.read_text())
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in ("skip", "skipif", "importorskip"):
            if isinstance(node.value, (ast.Name, ast.Attribute)):
                base = node.value.id if isinstance(node.value, ast.Name) else node.value.attr
                if base in ("pytest", "mark"):
                    bad.append(f"line {node.lineno}: {base}.{node.attr}")
    assert not bad, f"{path.name} skips tests: {bad}"


@pytest.mark.parametrize("path", find_test_files(), ids=lambda p: str(p.relative_to(TESTS_ROOT)))
def test_xfail_is_strict_with_a_reason(path) -> None:
    tree = ast.parse(path.read_text())
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "xfail":
            kw = {k.arg: k.value for k in node.keywords}
            reason = kw.get("reason")
            if not (isinstance(reason, ast.Constant) and str(reason.value).startswith("known bug:")):
                bad.append(f"line {node.lineno}: reason must start with 'known bug:'")
            strict = kw.get("strict")
            if strict is not None and not (isinstance(strict, ast.Constant) and strict.value is True):
                bad.append(f"line {node.lineno}: strict must stay True")
    assert not bad, f"{path.name}: {bad}"
