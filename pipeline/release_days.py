"""Decides whether a scheduled run should refresh the data now.

GitHub starts scheduled runs late, sometimes by hours, so the workflow wakes a few times a day
and asks this module whether a refresh is due. A refresh is due when a key moment has passed
in Sydney today and nothing has been attempted since:

- every day at 11:45am, after the ABS's 11:30am releases, so any release day is covered
- on RBA decision days at 2:45pm and 3:45pm too, after the 2:30pm announcement

Standard library only: this runs before any packages are installed.
"""
from __future__ import annotations

import os
from datetime import date, datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SYDNEY = ZoneInfo("Australia/Sydney")
LAST_ATTEMPT = Path(__file__).with_name("last_attempt.txt")

# The day each decision is announced, from https://www.rba.gov.au/schedules-events/board-meeting-schedules.html
# Add each new year's dates when the RBA publishes them. The health check fails if they run out.
RBA_DECISIONS = [date.fromisoformat(d) for d in (
    "2026-12-08",
    "2027-02-09", "2027-03-23", "2027-05-04", "2027-06-22", "2027-08-10", "2027-09-28", "2027-11-02", "2027-12-14",
)]
DAILY_MOMENT = time(11, 45)
DECISION_MOMENTS = (time(14, 45), time(15, 45))


def moments(day: date) -> list[datetime]:
    """Today's key moments in Sydney time, earliest first."""
    times = [DAILY_MOMENT, *(DECISION_MOMENTS if day in RBA_DECISIONS else ())]
    return [datetime.combine(day, t, SYDNEY) for t in times]


def is_due(now: datetime, last_attempt: datetime | None) -> bool:
    passed = [m for m in moments(now.astimezone(SYDNEY).date()) if m <= now]
    return bool(passed) and (last_attempt is None or last_attempt < passed[-1])


def read_last_attempt() -> datetime | None:
    try:
        return datetime.fromisoformat(LAST_ATTEMPT.read_text(encoding="utf-8").strip().replace("Z", "+00:00"))
    except (FileNotFoundError, ValueError):
        return None


def main() -> None:
    due = is_due(datetime.now(timezone.utc), read_last_attempt())
    print(f"Refresh due: {due}")
    if out := os.environ.get("GITHUB_OUTPUT"):
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"due={'true' if due else 'false'}\n")


if __name__ == "__main__":
    main()
