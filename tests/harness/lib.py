"""Shared helpers for the henhouse test suites (see context/testing.md).

Everything here works from the checkout alone: no MySQL, no install, no daemons.
"""

from __future__ import annotations

import importlib
from functools import lru_cache
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = REPO_ROOT / "tests"

# Folders under tests/ that are not suites.
NON_SUITE_DIRS = {"harness", "__pycache__"}

# Suites that are not named after a module (TS-H02).
EXTRA_SUITES = ("framework", "live")

# The two kinds of test (TS-H04).  Every test file sits under <suite>/system/ or <suite>/data/.
KINDS = ("system", "data")


@lru_cache(maxsize=None)
def module_names() -> List[str]:
    """Every folder at the repo root with a __module__.py manifest, sorted.  Blacklisted modules included."""
    return sorted(p.parent.name for p in REPO_ROOT.glob("*/__module__.py"))


@lru_cache(maxsize=None)
def module_python_files(module: str) -> List[str]:
    """Dotted names of every .py file in a module folder, sorted."""
    base = REPO_ROOT / module
    names = []
    for path in sorted(base.rglob("*.py")):
        rel = path.relative_to(REPO_ROOT)
        if "__pycache__" in rel.parts or "node_modules" in rel.parts:
            continue
        parts = list(rel.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        names.append(".".join(parts))
    return names


def import_dotted(name: str) -> None:
    """Import a module by dotted name and fail with the real error if it does not import."""
    importlib.import_module(name)


def suite_names() -> List[str]:
    """Every suite folder under tests/, sorted."""
    return sorted(
        p.name for p in TESTS_ROOT.iterdir()
        if p.is_dir() and p.name not in NON_SUITE_DIRS and not p.name.startswith(".")
    )


def find_test_files(suite: str | None = None) -> List[Path]:
    """Every test_*.py file of one suite (or of all suites), sorted."""
    roots = [TESTS_ROOT / suite] if suite else [TESTS_ROOT / s for s in suite_names()]
    files: List[Path] = []
    for root in roots:
        files.extend(p for p in root.rglob("test_*.py") if "__pycache__" not in p.parts)
    return sorted(files)
