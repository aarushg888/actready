"""Classical SPC drift detector (always-on, no provider / no flag).

Consumes a time series of eval scores (accuracy / faithfulness / robustness —
Art. 15, A.6 V&V) that the deterministic engine already ingests. Computes
mean + control limits (mean +/- 3*sigma, Shewhart individuals) and flags points
outside the limits. Also supports an I-MR style moving-range check.

This is CORE ENGINE BEHAVIOR, not an ML feature (ml-plan §1). It runs with zero
configuration and no network access. Pure functions, heavily testable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DriftPoint:
    """One observation with its drift verdict."""

    index: int
    value: float
    z_score: float
    out_of_control: bool
    moving_range: float | None = None
    mr_out_of_control: bool = False


@dataclass
class DriftReport:
    """Result of an SPC evaluation over a series."""

    mean: float
    std: float
    upper_limit: float
    lower_limit: float
    points: list[DriftPoint]
    any_drift: bool
    # I-MR: moving-range mean + limit (None if <2 points)
    mr_mean: float | None = None
    mr_limit: float | None = None


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: list[float], mean: float) -> float:
    if len(xs) < 2:
        return 0.0
    var = sum((x - mean) ** 2 for x in xs) / (len(xs) - 1)
    return var ** 0.5


def detect_drift(
    series: list[float],
    sigma: float = 3.0,
    use_moving_range: bool = True,
) -> DriftReport:
    """Run Shewhart individuals (X) + optional moving-range (MR) SPC on `series`.

    A point is out-of-control when |value - mean| > sigma * std (X chart) or when
    its moving range exceeds the MR limit (D4 = 3.267 for n=2). Always returns a
    report; an empty/short series yields no flags.
    """
    n = len(series)
    mean = _mean(series)
    std = _std(series, mean)
    upper = mean + sigma * std
    lower = mean - sigma * std

    # Moving range series (|x_i - x_{i-1}|) — only used when enabled.
    mr: list[float] = [abs(series[i] - series[i - 1]) for i in range(1, n)] if use_moving_range else []
    mr_mean = _mean(mr) if mr else None
    # D4 for subgroup size 2 (individuals) = 3.267
    mr_limit = (3.267 * mr_mean) if (use_moving_range and mr_mean is not None) else None

    points: list[DriftPoint] = []
    any_drift = False
    for i, v in enumerate(series):
        z = (v - mean) / std if std > 0 else 0.0
        ooc = std > 0 and abs(v - mean) > sigma * std
        mrv = mr[i - 1] if (use_moving_range and i >= 1) else None
        mr_ooc = mrv is not None and mr_limit is not None and mrv > mr_limit
        if ooc or mr_ooc:
            any_drift = True
        points.append(
            DriftPoint(
                index=i,
                value=v,
                z_score=z,
                out_of_control=ooc,
                moving_range=mrv,
                mr_out_of_control=mr_ooc,
            )
        )

    return DriftReport(
        mean=mean,
        std=std,
        upper_limit=upper,
        lower_limit=lower,
        points=points,
        any_drift=any_drift,
        mr_mean=mr_mean,
        mr_limit=mr_limit,
    )


def flag_drift(series: list[float], sigma: float = 3.0) -> bool:
    """Convenience: True if any point is out of control."""
    return detect_drift(series, sigma=sigma).any_drift


__all__ = ["DriftPoint", "DriftReport", "detect_drift", "flag_drift"]
