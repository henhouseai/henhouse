"""Display labels (@register_label) are registered once.  A second registration of a name warns on every command
and silently replaces the first text."""

from __future__ import annotations

import ast
from collections import defaultdict

from tests.harness.lib import REPO_ROOT, module_names


def _label_sites():
    sites = defaultdict(list)
    for module in module_names():
        for path in sorted((REPO_ROOT / module).rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "register_label"
                        and node.args and isinstance(node.args[0], ast.Constant)):
                    name = str(node.args[0].value).lower()
                    name = name[2:] if name.startswith("l_") else name
                    sites[name].append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")
    return sites


def test_labels_exist() -> None:
    assert len(_label_sites()) > 100


def test_each_label_is_registered_once() -> None:
    dupes = {k: v for k, v in _label_sites().items() if len(v) > 1}
    assert not dupes, f"labels registered more than once: {dupes}"
