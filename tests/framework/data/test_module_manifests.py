"""Every module's __module__.py manifest is valid (context/modules.md)."""

from __future__ import annotations

import re

import pytest

from hh.gateway.registry.module_discovery import load_manifest
from tests.harness.lib import REPO_ROOT, module_names


@pytest.mark.parametrize("module", module_names())
def test_manifest_names_its_folder(module: str) -> None:
    manifest = load_manifest(str(REPO_ROOT / module))
    assert isinstance(manifest, dict), f"{module}/__module__.py has no MODULE dict"
    assert manifest.get("name") == module


@pytest.mark.parametrize("module", module_names())
def test_manifest_has_version_and_description(module: str) -> None:
    manifest = load_manifest(str(REPO_ROOT / module)) or {}
    assert re.fullmatch(r"\d+\.\d+\.\d+", str(manifest.get("version", ""))), manifest.get("version")
    assert str(manifest.get("description", "")).strip()


@pytest.mark.parametrize("module", module_names())
def test_manifest_dependencies_exist(module: str) -> None:
    deps = (load_manifest(str(REPO_ROOT / module)) or {}).get("dependencies") or []
    assert isinstance(deps, list)
    missing = [d for d in deps if d not in module_names()]
    assert not missing, f"{module} depends on modules that do not exist: {missing}"


def test_blacklist_names_real_modules() -> None:
    from ext.deploy.conf.module_blacklist import MODULE_BLACKLIST
    stray = [m for m in MODULE_BLACKLIST if m not in module_names()]
    assert not stray, f"MODULE_BLACKLIST names modules that do not exist: {stray}"


def test_core_modules_are_not_blacklisted() -> None:
    """hh_page and hh_image cannot be turned off yet (REFACTOR_REPORT.md §10, still open)."""
    from ext.deploy.conf.module_blacklist import MODULE_BLACKLIST
    assert not {"hh", "ext", "hh_page", "hh_image"} & set(MODULE_BLACKLIST)
