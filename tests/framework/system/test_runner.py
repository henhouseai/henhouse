"""The runner's own pieces: slicing, reading results files, finding the last one."""

from __future__ import annotations

from tests.harness import results
from tests.harness.run_suite import parse_target, shard


def test_parse_target() -> None:
    assert parse_target("hh") == ("hh", None)
    assert parse_target("hh/tp") == ("hh", "tp")


def test_shards_cover_every_file_once(monkeypatch) -> None:
    monkeypatch.setattr(results, "load_timings", lambda: {})
    files = [f"tests/x/system/test_{i}.py" for i in range(23)]
    slices = [shard(files, k, 5) for k in range(1, 6)]
    flat = [f for s in slices for f in s]
    assert sorted(flat) == sorted(files)
    assert max(len(s) for s in slices) - min(len(s) for s in slices) <= 1


def test_shards_balance_on_recorded_times(monkeypatch) -> None:
    times = {"a": 600.0, "b": 300.0, "c": 300.0, "d": 10.0}
    monkeypatch.setattr(results, "load_timings", lambda: times)
    slices = [shard(list(times), k, 2) for k in (1, 2)]
    loads = sorted(sum(times[f] for f in s) for s in slices)
    assert loads == [600.0, 610.0]


def test_shard_is_deterministic(monkeypatch) -> None:
    monkeypatch.setattr(results, "load_timings", lambda: {})
    files = [f"f{i}" for i in range(10)]
    assert shard(files, 2, 3) == shard(list(reversed(files)), 2, 3)


def test_read_lines_and_selection(tmp_path) -> None:
    p = tmp_path / "2026-01-01_000000_hh.md"
    p.write_text(
        "# Test results: hh\n\n- Selection: `{\"target\": \"hh\", \"paths\": [\"a\"]}`\n\n## Tests\n\n"
        "PASS tests/hh/system/test_a.py::test_one (0.01s)\n"
        "FAIL tests/hh/system/test_a.py::test_two[x-1] (0.02s)\n\n```\ntrace\n```\n\n"
        "SKIP tests/hh/system/test_a.py::test_three (0.00s) -- why\n"
    )
    assert results.read_lines(p) == [
        ("PASS", "tests/hh/system/test_a.py::test_one"),
        ("FAIL", "tests/hh/system/test_a.py::test_two[x-1]"),
        ("SKIP", "tests/hh/system/test_a.py::test_three"),
    ]
    assert results.read_selection(p) == {"target": "hh", "paths": ["a"]}


def test_latest_results_path_matches_the_label_only(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(results, "RESULTS_DIR", tmp_path)
    for name in ("2026-01-01_000000_hh.md", "2026-01-02_000000_hh.md", "2026-01-03_000000_hh_page.md",
                 "2026-01-03_000000_hh-data.md"):
        (tmp_path / name).write_text("")
    assert results.latest_results_path("hh").name == "2026-01-02_000000_hh.md"
    assert results.latest_results_path("hh_page").name == "2026-01-03_000000_hh_page.md"
    assert results.latest_results_path("work") is None
