"""DecimalMath: penny math on strings (accounting/currency_math.py).

Zero is written as the empty string: `_units_to_string(0)` returns '' on purpose, and the tests pin that.
"""

from __future__ import annotations

import pytest

from accounting.currency_math import DecimalMath as D


@pytest.mark.parametrize("a, b, total", [
    ("1.10", "2.20", "3.3"),
    ("0.01", "0.02", "0.03"),
    ("10", "0.5", "10.5"),
    ("-1.25", "1.25", ""),
    ("-3", "1", "-2"),
    ("1,234.56", "0.44", "1235"),
    ("$5.00", "1", "6"),
])
def test_add(a: str, b: str, total: str) -> None:
    assert D.add(a, b) == total


def test_add_has_no_float_error() -> None:
    total = ""
    for _ in range(10):
        total = D.add(total, "0.1")
    assert total == "1"


@pytest.mark.parametrize("a, b, diff", [("5", "3.5", "1.5"), ("1", "1", ""), ("0.1", "0.3", "-0.2")])
def test_subtract(a: str, b: str, diff: str) -> None:
    assert D.subtract(a, b) == diff


def test_extra_decimals_are_truncated_not_rounded() -> None:
    assert D.add("0.019", "0") == "0.01"
    assert D.round("2.999") == "2.99"


def test_decimal_places() -> None:
    assert D.add("1.0005", "0.0005", decimal_places=4) == "1.001"


def test_aggregates() -> None:
    values = ["1.50", "2.50", "-1"]
    assert D.sum(values) == "3"
    assert D.max(values) == "2.5"
    assert D.min(values) == "-1"
    assert D.sum([]) == ""
    assert D.max([]) == ""
    assert D.min([]) == ""


def test_compare_and_equals() -> None:
    assert D.compare("1.00", "1") == 0
    assert D.compare("0.99", "1") == -1
    assert D.compare("1.01", "1") == 1
    assert D.equals("1.00", "1.01", tolerance_units=1)
    assert not D.equals("1.00", "1.02", tolerance_units=1)


def test_sign_helpers() -> None:
    assert D.is_zero("") and D.is_zero("0.00") and D.is_zero("0.001")
    assert D.is_negative("-0.01") and not D.is_negative("0")
    assert D.is_positive("0.01") and not D.is_positive("-1")
    assert D.abs("-2.5") == "2.5"
    assert D.negate("2.5") == "-2.5"
    assert D.negate("-2.5") == "2.5"


@pytest.mark.parametrize("raw, clean", [
    ("12", "12"),
    (" 12.50 ", "12.5"),
    ("1,234.5", "1234.5"),
    ("-0.07", "-0.07"),
    ("+3", "3"),
])
def test_normalize(raw: str, clean: str) -> None:
    assert D.normalize(raw) == clean


@pytest.mark.parametrize("raw", ["", "   ", "abc", "1.2.3", "--1", "1-", "12$", "1e5"])
def test_normalize_rejects(raw: str) -> None:
    with pytest.raises(ValueError):
        D.normalize(raw)


# TS-H25, Lee's rule for every range: mid-range passes, each limit passes, and twice the margin past each limit
# fails, each a single-item test.  normalize() accepts -999999.99 to 999999.99; the margin is one cent.

def test_normalize_range_mid() -> None:
    assert D.normalize("500000.00") == "500000"


def test_normalize_range_upper_limit() -> None:
    assert D.normalize("999999.99") == "999999.99"


def test_normalize_range_lower_limit() -> None:
    assert D.normalize("-999999.99") == "-999999.99"


def test_normalize_range_past_upper_limit() -> None:
    with pytest.raises(ValueError):
        D.normalize("1000000.01")


def test_normalize_range_past_lower_limit() -> None:
    with pytest.raises(ValueError):
        D.normalize("-1000000.01")
