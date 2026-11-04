"""Proves the refresh refuses bad data. Run with:  python -m tests.test_guards"""
from datetime import date, datetime, timezone

from pipeline.build import rejected, rejected_bundle
from pipeline.derived import budget_history
from pipeline.registry import BUDGET_OUTCOMES
from pipeline.release_days import SYDNEY, is_due
from tests.health_check import future_dated

GOOD = [["2026-07-31", 4.5], ["2026-08-31", 4.6], ["2026-09-30", 4.7]]
PREVIOUS = {"points": GOOD[:2]}


def test_series() -> None:
    assert rejected({"points": GOOD}, PREVIOUS, (1, 15)) is None, "good data accepted"
    assert rejected({"points": GOOD}, None, (1, 15)) is None, "a new series is accepted"
    assert rejected({"points": []}, PREVIOUS), "empty data refused"
    assert rejected({"points": [["2026-09-30", 470.0]]}, None, (1, 15)), "a value out of range refused (a unit error)"
    assert rejected({"points": GOOD[:1]}, {"points": GOOD * 4}), "a much shorter series refused"
    assert rejected({"points": GOOD[:2]}, {"points": GOOD}), "a latest date going backwards refused"


def test_bundles() -> None:
    items = [{"key": str(i)} for i in range(10)]
    assert rejected_bundle({"items": items}, {"items": items}) is None, "good bundle accepted"
    assert rejected_bundle({"items": []}, None), "empty bundle refused"
    assert rejected_bundle({"items": items[:3]}, {"items": items}), "a bundle that lost most of its items refused"


def test_future_dates() -> None:
    today = date(2026, 11, 3)
    decision = {"freq": "event", "points": [["2026-11-04", 4.85]]}
    assert not future_dated(decision, today), "an RBA decision effective tomorrow is allowed (3 Nov 2026 was held back by this)"
    assert future_dated({"freq": "event", "points": [["2026-11-20", 4.85]]}, today), "a decision weeks ahead refused"
    assert future_dated({"freq": "M", "points": [["2026-11-30", 4.7]]}, today), "a monthly figure dated ahead refused"
    assert not future_dated({"freq": "FY", "forecast_from": "2027-06-30", "points": [["2027-06-30", 1.0]]}, today), "forecasts may be ahead"


def test_release_days() -> None:
    at = lambda day, h, m: datetime(*day, h, m, tzinfo=SYDNEY)  # noqa: E731
    plain, decision = (2026, 11, 5), (2026, 12, 8)
    assert not is_due(at(plain, 11, 0), None), "not due before the 11:30am releases"
    assert is_due(at(plain, 11, 50), None), "due after them"
    assert is_due(at(plain, 11, 50), at((2026, 11, 4), 12, 0)), "yesterday's refresh doesn't count"
    assert not is_due(at(plain, 12, 30), at(plain, 11, 50)), "one refresh a day on a plain day"
    assert not is_due(at(plain, 15, 0), at(plain, 11, 50)), "no afternoon refresh on a plain day"
    assert not is_due(at(decision, 14, 30), at(decision, 11, 50)), "not due before the RBA's update"
    assert is_due(at(decision, 14, 50), at(decision, 11, 50)), "due after the 2:30pm decision"
    assert not is_due(at(decision, 15, 0), at(decision, 14, 50)), "no repeat straight after"
    assert is_due(at(decision, 15, 50), at(decision, 14, 50)), "a second try on decision days"
    assert is_due(at(decision, 22, 0), at(decision, 11, 50)), "a very late run still catches it"
    assert not is_due(at(decision, 22, 30), at(decision, 22, 0)), "and then stops"
    winter = datetime(2027, 6, 22, 4, 50, tzinfo=timezone.utc)  # 2:50pm Sydney in winter (UTC+10)
    assert is_due(winter, datetime(2027, 6, 22, 2, 0, tzinfo=timezone.utc)), "Sydney time holds in winter"


def test_budget_outcome() -> None:
    """Runs on the real Budget tables, so skipped if they can't be reached."""
    try:
        history = {s["id"]: s for s in budget_history()}
    except Exception as e:  # noqa: BLE001
        print(f"  skipped the budget test: {e}"[:120])
        return
    for year_end, outcome in BUDGET_OUTCOMES.items():
        for sid, want in outcome.items():
            if sid == "document":
                continue
            s = history[sid]
            assert (s["forecast_from"] or "9999") > year_end, f"{sid}: {year_end} is no longer a forecast"
            assert dict(map(tuple, s["points"]))[year_end] == want or "Final Budget Outcome" not in s["source"]["dataset"], f"{sid}: outcome applied"


if __name__ == "__main__":
    test_series()
    test_bundles()
    test_future_dates()
    test_release_days()
    test_budget_outcome()
    print("Safeguards work.")
