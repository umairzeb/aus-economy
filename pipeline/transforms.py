"""Pure functions over point lists ([[iso_date, value], ...], sorted by date)."""
from __future__ import annotations


def _r(v: float, nd: int = 2) -> float:
    return round(v, nd)


def pct_change(points: list[list], lag: int, nd: int = 2) -> list[list]:
    """Percentage change over `lag` observations (12 for monthly y/y, 4 for quarterly)."""
    return [[d, _r((v / points[i - lag][1] - 1) * 100, nd)]
            for i, (d, v) in enumerate(points) if i >= lag and points[i - lag][1]]


def rolling_sum(points: list[list], n: int) -> list[list]:
    return [[points[i][0], _r(sum(v for _, v in points[i - n + 1:i + 1]), 2)]
            for i in range(n - 1, len(points))]


def subtract(a: list[list], b: list[list], nd: int = 2) -> list[list]:
    """a - b on matching dates."""
    bm = dict(map(tuple, b))
    return [[d, _r(v - bm[d], nd)] for d, v in a if d in bm]


def diff(points: list[list], lag: int = 1, nd: int = 2) -> list[list]:
    return [[d, _r(v - points[i - lag][1], nd)] for i, (d, v) in enumerate(points) if i >= lag]


def splice(old: list[list], new: list[list]) -> list[list]:
    """Old history up to where the new series starts, then the new series."""
    if not new:
        return old
    start = new[0][0]
    return [p for p in old if p[0] < start] + new


def scale(points: list[list], factor: float, nd: int = 2) -> list[list]:
    return [[d, _r(v * factor, nd)] for d, v in points]


def since(points: list[list], start: str) -> list[list]:
    return [p for p in points if p[0] >= start]


def value_at_or_before(points: list[list], d: str):
    best = None
    for pd_, v in points:
        if pd_ <= d:
            best = v
        else:
            break
    return best
