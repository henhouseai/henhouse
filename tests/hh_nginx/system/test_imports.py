"""Every Python file of the hh_nginx module imports cleanly from a plain checkout (no MySQL, no install)."""

import pytest

from tests.harness.lib import import_dotted, module_python_files


@pytest.mark.parametrize("dotted", module_python_files("hh_nginx"))
def test_imports(dotted: str) -> None:
    import_dotted(dotted)
