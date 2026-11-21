"""What a fresh install -> init-db -> add-db-users -> deploy leaves behind (REFACTOR_REPORT.md §9 and §10)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from tests.harness.lib import REPO_ROOT, module_names

from tests.live.system._live import PROJECT, PROJECT_NAME, http_get, mcp, sql

TIERS = ("guest", "verified", "admin", "root")


def _active_modules():
    from ext.deploy.conf.module_blacklist import MODULE_BLACKLIST
    return [m for m in module_names() if m not in MODULE_BLACKLIST]


def _schema_tables(module: str, filename: str):
    path = REPO_ROOT / module / "deploy" / "db" / filename
    if not path.exists():
        return []
    text = re.sub(r"--[^\n]*", "", path.read_text())
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.findall(r"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?`?(\w+)`?", text, flags=re.I)


def test_web_home_page_returns_200() -> None:
    status, body = http_get("/")
    assert status == 200, body[:500]


def test_mcp_lists_tools() -> None:
    tools = mcp("tools/list")["result"]["tools"]
    assert any(t["name"] == "get_page" for t in tools)


def test_home_page_is_page_1() -> None:
    rows = sql("SELECT id, parent, name FROM pages WHERE id = 1")
    assert rows == [{"id": 1, "parent": 0, "name": PROJECT_NAME}]


@pytest.mark.parametrize("tier", TIERS)
def test_tier_db_user_exists(tier: str) -> None:
    rows = sql("SELECT user FROM mysql.user WHERE user = %s", (f"{PROJECT_NAME}_{tier}",), database="mysql")
    assert rows, f"no MySQL user {PROJECT_NAME}_{tier}"


def test_owner_db_user_exists() -> None:
    owner = PROJECT.owner()
    assert sql("SELECT user FROM mysql.user WHERE user = %s", (owner,), database="mysql"), owner


@pytest.mark.parametrize("tier", TIERS)
def test_tier_flask_daemon_runs(tier: str) -> None:
    out = subprocess.run(["pgrep", "-f", f"/srv/{PROJECT_NAME}/{PROJECT_NAME}_{tier}.py"], capture_output=True)
    assert out.returncode == 0, f"the {tier} Flask daemon is not running"


@pytest.mark.parametrize("module", _active_modules())
def test_module_main_tables_exist(module: str) -> None:
    expected = set(_schema_tables(module, "schema.sql"))
    have = {r["TABLE_NAME"] for r in sql(
        "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s", (PROJECT_NAME,))}
    assert expected <= have, f"{module}: missing tables {sorted(expected - have)}"


@pytest.mark.parametrize("module", _active_modules())
def test_module_cache_tables_exist(module: str) -> None:
    expected = set(_schema_tables(module, "schema_cache.sql"))
    have = {r["TABLE_NAME"] for r in sql(
        "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s", (f"{PROJECT_NAME}_cache",),
        database=f"{PROJECT_NAME}_cache")}
    assert expected <= have, f"{module}: missing cache tables {sorted(expected - have)}"


def test_deployed_tree_has_no_tests_folder() -> None:
    """The test tree is never deployed: deploy copies whitelisted module folders only."""
    assert not (Path("/srv") / PROJECT_NAME / "tests").exists()
