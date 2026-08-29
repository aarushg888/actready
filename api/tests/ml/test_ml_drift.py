"""Classical SPC drift detector tests (always-on, pure function)."""

from __future__ import annotations

import pytest

from app.ml.drift import detect_drift, flag_drift


class TestDriftBasics:
    def test_constant_series_no_drift(self) -> None:
        rep = detect_drift([1.0, 1.0, 1.0, 1.0, 1.0])
        assert rep.any_drift is False
        assert rep.std == 0.0

    def test_single_point_no_drift(self) -> None:
        rep = detect_drift([0.5])
        assert rep.any_drift is False

    def test_empty_series(self) -> None:
        rep = detect_drift([])
        assert rep.any_drift is False

    def test_outlier_flagged(self) -> None:
        # 10 stable points then one huge spike.
        series = [0.90, 0.91, 0.89, 0.92, 0.90, 0.91, 0.90, 0.89, 0.91, 0.90, 0.30]
        rep = detect_drift(series)
        assert rep.any_drift is True
        out = [p for p in rep.points if p.out_of_control]
        assert len(out) >= 1
        # the spike (last point) is the offender
        assert rep.points[-1].out_of_control is True

    def test_flag_drift_convenience(self) -> None:
        assert flag_drift([1, 1, 1, 1, 5]) is True
        assert flag_drift([1, 1, 1, 1, 1]) is False

    def test_limits_shape(self) -> None:
        rep = detect_drift([0.8, 0.85, 0.82, 0.79, 0.83])
        assert rep.upper_limit > rep.mean > rep.lower_limit

    def test_moving_range_detects_shift(self) -> None:
        # gradual step that is within X limits but breaks MR consistency
        series = [0.9] * 8 + [0.5] * 4
        rep = detect_drift(series, use_moving_range=True)
        assert rep.mr_limit is not None
        assert rep.any_drift is True

    def test_no_moving_range_flagging_when_disabled(self) -> None:
        series = [0.9] * 8 + [0.5] * 4
        rep = detect_drift(series, use_moving_range=False)
        # With MR off, the step is within 3-sigma of the whole-series mean.
        assert rep.any_drift is False
