"""Module discovery and the blacklist (hh/deploy/deploy_utils.py, context/modules.md)."""

from __future__ import annotations

import pytest

from hh.deploy import deploy_utils
from tests.harness.lib import module_names


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    """Point the module cache at a temp folder so the tests neither read nor leave a stale modules.json."""
    monkeypatch.setattr(deploy_utils, "_MODULE_CACHE_DIR", tmp_path)
    return tmp_path


def test_all_modules_are_found(isolated_cache) -> None:
    found = sorted(m.name for m in deploy_utils.get_all_modules(force_regenerate=True))
    assert found == module_names()


def test_active_modules_leave_out_the_blacklist(isolated_cache) -> None:
    from ext.deploy.conf.module_blacklist import MODULE_BLACKLIST
    active = {m.name for m in deploy_utils.get_active_modules(force_regenerate=True)}
    assert active == set(module_names()) - set(MODULE_BLACKLIST)


def test_is_module_active(isolated_cache) -> None:
    from ext.deploy.conf.module_blacklist import MODULE_BLACKLIST
    deploy_utils.get_active_modules(force_regenerate=True)
    assert deploy_utils.is_module_active("hh_page")
    for name in MODULE_BLACKLIST:
        assert not deploy_utils.is_module_active(name)
    assert not deploy_utils.is_module_active("no_such_module")


def test_module_info_carries_the_manifest(isolated_cache) -> None:
    info = {m.name: m for m in deploy_utils.get_all_modules(force_regenerate=True)}
    assert info["hh"].version == "1.0.0"
    assert info["hh_page"].path == "hh_page"
