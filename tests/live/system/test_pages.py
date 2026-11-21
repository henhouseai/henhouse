"""Page commands against the sandbox: add, show, modify text, move, delete, and a work tree."""

from __future__ import annotations

import uuid

import pytest

from tests.live.system._live import hen, mcp_tool, page_id_from, sql


@pytest.fixture
def name() -> str:
    return f"live-{uuid.uuid4().hex[:10]}"


@pytest.fixture
def cleanup():
    made: list[int] = []
    yield made
    for page_id in reversed(made):
        if sql("SELECT id FROM pages WHERE id = %s", (page_id,)):
            hen("delete-page", "-id", str(page_id), "-confirm")


def test_add_page_under_home(name: str, cleanup) -> None:
    page_id = page_id_from(hen("add-page", "-name", name, "-target_page", "1"))
    cleanup.append(page_id)
    assert sql("SELECT name, parent, class FROM pages WHERE id = %s", (page_id,)) == [
        {"name": name, "parent": 1, "class": "page"}]


def test_add_page_target_page_0_is_not_read_as_missing(name: str, cleanup) -> None:
    """`-target_page 0` used to read as missing and fall back to a default parent (REFACTOR_REPORT.md §9)."""
    out = hen("add-page", "-name", name, "-target_page", "0", expect_ok=None)
    assert not sql("SELECT id FROM pages WHERE name = %s AND parent <> 0", (name,)), out[-1000:]
    for row in sql("SELECT id FROM pages WHERE name = %s", (name,)):
        cleanup.append(row["id"])


def test_get_page_over_mcp(name: str, cleanup) -> None:
    page_id = page_id_from(hen("add-page", "-name", name, "-target_page", "1"))
    cleanup.append(page_id)
    data = mcp_tool("get_page", id=page_id)
    assert data["page"]["id"] == page_id
    assert data["page"]["name"] == name
    assert [p["id"] for p in data["page"]["path"]] == [1, page_id]


def test_modify_text(name: str, cleanup) -> None:
    page_id = page_id_from(hen("add-page", "-name", name, "-target_page", "1"))
    cleanup.append(page_id)
    hen("modify-text", "-id", str(page_id), "-text", "Hello from the live suite")
    assert mcp_tool("get_page", id=page_id)["page"]["text"] == "Hello from the live suite"


def test_delete_needs_confirm(name: str, cleanup) -> None:
    page_id = page_id_from(hen("add-page", "-name", name, "-target_page", "1"))
    cleanup.append(page_id)
    hen("delete-page", "-id", str(page_id), expect_ok=False)
    assert sql("SELECT id FROM pages WHERE id = %s", (page_id,))


def test_delete_page(name: str) -> None:
    page_id = page_id_from(hen("add-page", "-name", name, "-target_page", "1"))
    hen("delete-page", "-id", str(page_id), "-confirm")
    assert not sql("SELECT id FROM pages WHERE id = %s", (page_id,))


def test_children_count_on_show_page(name: str, cleanup) -> None:
    parent = page_id_from(hen("add-page", "-name", name, "-target_page", "1"))
    cleanup.append(parent)
    for i in range(3):
        cleanup.append(page_id_from(hen("add-page", "-name", f"{name}-{i}", "-target_page", str(parent))))
    out = hen("show-page", "-id", str(parent))
    assert "Children:" in out and "│ 3" in out.split("Children:", 1)[1].splitlines()[0]


def test_work_tree(name: str, cleanup) -> None:
    """docket -> ask -> task -> step, each its own page class (context/work-page-protocol.md)."""
    parent = "1"
    for cls in ("work_docket", "ask", "task", "step"):
        page_id = page_id_from(hen("add-page", "-name", f"{name}-{cls}", "-target_page", parent, "-class", cls))
        cleanup.append(page_id)
        assert sql("SELECT class FROM pages WHERE id = %s", (page_id,)) == [{"class": cls}]
        parent = str(page_id)
    hen("modify-work-status", "-page_id", parent, "-status", "doing")
