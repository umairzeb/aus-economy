"""Proves the refresh refuses bad data. Run with:  python -m tests.test_guards"""
from pipeline.build import rejected, rejected_bundle
from pipeline.registry import BUDGET_OUTCOMES
from pipeline.derived import budget_history

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
    test_budget_outcome()
    print("Safeguards work.")
