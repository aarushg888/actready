"""extract_fields tests: per-field confidence -> needs_review flag."""

from __future__ import annotations

import pytest

from app.ml.extract import extract_fields
from app.ml.providers import FakeProvider, NoneProvider
from app.ml.schemas import DEFAULT_REVIEW_THRESHOLD, FieldWithConf


class TestFieldWithConf:
    def test_high_conf_no_review(self) -> None:
        f = FieldWithConf.with_threshold("v", 0.95)
        assert f.needs_review is False

    def test_low_conf_needs_review(self) -> None:
        f = FieldWithConf.with_threshold("v", 0.3)
        assert f.needs_review is True

    def test_custom_threshold(self) -> None:
        f = FieldWithConf.with_threshold("v", 0.5, threshold=0.6)
        assert f.needs_review is True


class TestExtractNoneProvider:
    def test_none_returns_empty_result(self) -> None:
        res = extract_fields("model_card", "some text", provider=NoneProvider())
        assert res.provider == "none"
        assert res.model_card is None
        assert res.incident is None

    def test_unknown_kind_raises(self) -> None:
        with pytest.raises(ValueError):
            extract_fields("bogus", "text", provider=NoneProvider())


class TestExtractFakeProvider:
    def test_fake_cannot_extract(self) -> None:
        # FakeProvider.extract raises; extract_fields degrades to empty result.
        res = extract_fields("model_card", "text", provider=FakeProvider())
        assert res.provider == "fake"
        assert res.kind == "model_card"
        assert res.model_card is None


class TestNeedsReviewCount:
    def test_count_logic(self) -> None:
        # Build a ModelCardFields manually to assert the counter behaviour.
        from app.ml.schemas import ModelCardFields

        mc = ModelCardFields(
            model_name=FieldWithConf.with_threshold("m", 0.9),
            version=FieldWithConf.with_threshold("1.0", 0.9),
            intended_use=FieldWithConf.with_threshold("use", 0.2),  # low -> review
            eval_metrics=[FieldWithConf.with_threshold("acc=0.9", 0.1)],  # low -> review
            data_governance=FieldWithConf.with_threshold("dg", 0.9),
        )
        count = sum(
            1
            for f in [
                mc.model_name,
                mc.version,
                mc.intended_use,
                *mc.eval_metrics,
                mc.data_governance,
            ]
            if f.needs_review
        )
        assert count == 2

    def test_default_threshold_constant(self) -> None:
        assert 0.0 < DEFAULT_REVIEW_THRESHOLD < 1.0
