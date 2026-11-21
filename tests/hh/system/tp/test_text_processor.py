"""TextProcessor parsing and pure decorators (hh/tp/tp.py, context/text_processor.md).

Page and image lookups need the database; the tests replace them with in-memory fakes, so these run anywhere.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import hh.tp.tp as tp_mod
from hh.tp.tp import TextProcessor

PAGES = {5: SimpleNamespace(id=5, parent=1, name="Barn"), 7: SimpleNamespace(id=7, parent=5, name="Coop")}


@pytest.fixture(autouse=True)
def fake_pages(monkeypatch):
    by_name = {p.name.lower(): p for p in PAGES.values()}
    monkeypatch.setattr(tp_mod, "get_page", lambda page_id, with_subpath=False: PAGES.get(int(page_id)))
    monkeypatch.setattr(tp_mod, "find_page", lambda link, with_subpath=False: by_name.get(str(link).lower()))
    monkeypatch.setattr(tp_mod, "get_image", lambda *a, **k: None)


def pre(text: str):
    proc = TextProcessor()
    return proc.preprocess(text), proc._parse_errors


def test_plain_text_is_one_text_element() -> None:
    elements, errors = pre("hello world")
    assert elements == [{"type": "text", "content": "hello world"}]
    assert errors == []


def test_empty_text() -> None:
    elements, errors = pre("")
    assert errors == []
    assert all(e.get("content", "") == "" for e in elements or [])


@pytest.mark.parametrize("text, decorators", [
    ("@pi(5)", [{"name": "pi", "args": {"arg0": 5}}]),
    ("@echo('Hello')", [{"name": "echo", "args": {"arg0": "Hello"}}]),
    ("@mcp @pi(5)", [{"name": "mcp", "args": {}}, {"name": "pi", "args": {"arg0": 5}}]),
])
def test_decorator_chain_is_parsed_left_to_right(text: str, decorators) -> None:
    elements, errors = pre(text)
    assert errors == []
    assert len(elements) == 1 and elements[0]["type"] == "custom"
    assert json.loads(elements[0]["value"]) == decorators


def test_text_around_a_decorator_is_kept() -> None:
    elements, _ = pre("a  @pi(3) tail")
    assert elements[0] == {"type": "text", "content": "a  "}
    assert elements[1]["type"] == "custom"
    assert elements[2] == {"type": "text", "content": " tail"}


@pytest.mark.parametrize("text, value", [("@pi(5)", "3.14159"), ("@pi(2)", "3.14"), ("@echo('Hello')", "Hello")])
def test_pure_decorators_json_output(text: str, value: str) -> None:
    assert json.loads(TextProcessor().process(text)) == {"type": "custom", "value": value}


def test_parser_final_decorator_changes_the_output_format() -> None:
    out = TextProcessor(final_decorator="parser").process("@pi(3)")
    assert "3.142" in out
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)


def test_link_by_id() -> None:
    elements, errors = pre("[[5]]")
    assert errors == []
    assert elements == [{"type": "page_link", "resolved_page": {"id": 5, "parent": 1, "name": "Barn"}}]


def test_link_by_name_with_display_text() -> None:
    elements, errors = pre("see [[Coop][the coop]] now")
    assert errors == []
    assert elements[0] == {"type": "text", "content": "see "}
    link = elements[1]["resolved_page"]
    assert (link["id"], link["name"], link.get("name_override")) == (7, "Coop", "the coop")
    assert elements[2] == {"type": "text", "content": " now"}


def test_link_to_a_missing_page_is_reported_not_raised() -> None:
    elements, errors = pre("[[999]]")
    assert elements[0]["type"] == "page_link"
    assert errors, "a link to a page that does not exist should leave a parse error"


def test_image_element() -> None:
    elements, _ = pre("x {{Barn}} y")
    assert [e["type"] for e in elements] == ["text", "image", "text"]
