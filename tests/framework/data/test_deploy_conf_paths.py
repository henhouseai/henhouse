"""Every path a module's deploy whitelists name exists in the checkout, so deploy copies what it means to."""

from __future__ import annotations

import runpy
from pathlib import Path
from typing import Iterator, List, Tuple

import pytest

from tests.harness.lib import REPO_ROOT


def _whitelist_files() -> List[Path]:
    return sorted(REPO_ROOT.glob("*/deploy/conf/*_whitelist.py"))


def _string_entries(value) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _string_entries(item)


def _repo_paths(path: Path) -> List[Tuple[str, str]]:
    found = []
    for name, value in runpy.run_path(str(path)).items():
        if not name.isupper():
            continue
        for entry in _string_entries(value):
            if "/" in entry and not entry.startswith(("/", "http", ".")) and not any(c in entry for c in "*?{"):
                found.append((name, entry))
    return found


@pytest.mark.parametrize("conf", _whitelist_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_whitelisted_paths_exist(conf: Path) -> None:
    missing = [f"{name}: {entry}" for name, entry in _repo_paths(conf) if not (REPO_ROOT / entry).exists()]
    assert not missing, f"{conf.relative_to(REPO_ROOT)} names paths that do not exist: {missing}"
