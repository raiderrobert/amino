import pytest
from amino.runtime.matcher import Matcher, MatchResult


def _results(matched_ids: list, all_ids: list) -> list[tuple]:
    """Build fake rule results: (rule_id, bool)."""
    matched = set(matched_ids)
    return [(rid, rid in matched) for rid in all_ids]


ALL_IDS = ["r1", "r2", "r3"]


def test_all_mode():
    m = Matcher({"mode": "all"})
    r = m.process("d1", _results(["r1", "r3"], ALL_IDS), {}, [])
    assert r.matched == ["r1", "r3"]
    assert r.excluded == []


def test_first_mode_by_ordering():
    m = Matcher({"mode": "first", "key": "ordering", "order": "asc"})
    metadata = {"r1": {"ordering": 3}, "r2": {"ordering": 1}, "r3": {"ordering": 2}}
    results = _results(["r1", "r2", "r3"], ALL_IDS)
    r = m.process("d1", results, metadata, [])
    assert r.matched == ["r2"]  # lowest ordering


def test_first_mode_no_match():
    m = Matcher({"mode": "first", "key": "ordering", "order": "asc"})
    r = m.process("d1", _results([], ALL_IDS), {}, [])
    assert r.matched == []


def test_inverse_mode():
    m = Matcher({"mode": "inverse"})
    r = m.process("d1", _results(["r1"], ALL_IDS), {}, [])
    assert r.excluded == ["r2", "r3"]
    assert r.matched == []


def test_score_mode_sum():
    m = Matcher({"mode": "score", "aggregate": "sum"})
    # r1 returns True (1.0), r2 returns 0.7, r3 returns False (0.0)
    results = [("r1", True), ("r2", 0.7), ("r3", False)]
    r = m.process("d1", results, {}, [])
    assert abs(r.score - 1.7) < 0.001


def test_score_mode_threshold():
    m = Matcher({"mode": "score", "aggregate": "sum", "threshold": 2.0})
    results = [("r1", True), ("r2", 0.7)]
    r = m.process("d1", results, {}, [])
    assert r.score == pytest.approx(1.7)
    # score below threshold → matched is empty
    assert r.matched == []


def test_warnings_propagated():
    m = Matcher({"mode": "all"})
    r = m.process("d1", _results([], ALL_IDS), {}, ["field x missing"])
    assert "field x missing" in r.warnings


def test_decision_id_on_result():
    m = Matcher({"mode": "all"})
    r = m.process("my-decision", _results([], ALL_IDS), {}, [])
    assert r.id == "my-decision"
