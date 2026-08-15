from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest


SCRIPT_PATH = Path("scripts/audits/phase29_l21t_ao_buy_quality_relative_score_forward_outcome_audit.py")


def load_audit_module():
    spec = importlib.util.spec_from_file_location("phase29_l21t_ao_buy_quality_relative_score_forward_outcome_audit", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_forward_return_uses_business_date_adjusted_close_only() -> None:
    audit = load_audit_module()
    bars = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2022-08-10", "2022-08-12", "2022-08-15"]).date,
            "Close": [100.0, 103.0, 98.0],
            "High": [101.0, 104.0, 99.0],
            "Low": [99.0, 102.0, 97.0],
        }
    )

    result = audit.forward_returns({"94320": bars}, "94320", "2022-08-10")

    assert result["decision_close"] == 100.0
    assert result["return_1bd"] == pytest.approx(0.03)


def test_group_keys_separate_buy_quality_score_sign_and_percentile() -> None:
    audit = load_audit_module()

    reduced_negative = audit.group_keys(
        {
            "quality_action": "REDUCED_ALLOCATION_ONLY",
            "runtime_opportunity_score": -0.2,
            "relative_score_percentile": 0.2,
            "relative_score_bucket": "BOTTOM_QUARTILE",
            "actual_buy_new": True,
        }
    )
    full_negative = audit.group_keys(
        {
            "quality_action": "FULL_ALLOCATION_ELIGIBLE",
            "runtime_opportunity_score": -0.1,
            "relative_score_percentile": 0.8,
            "relative_score_bucket": "TOP_QUARTILE",
            "actual_buy_new": False,
        }
    )

    assert "B_REDUCED_ALLOCATION_ONLY" in reduced_negative
    assert "CROSS_REDUCED_score_negative" in reduced_negative
    assert "CROSS_REDUCED_bottom_half" in reduced_negative
    assert "ACTUAL_BUY_NEW" in reduced_negative
    assert "A_FULL_ALLOCATION_ELIGIBLE" in full_negative
    assert "CROSS_FULL_score_negative" in full_negative
    assert "CROSS_FULL_top_half" in full_negative
    assert "ELIGIBLE_NOT_BOUGHT" in full_negative


def test_anchor_counterfactual_does_not_reallocate_removed_notional() -> None:
    audit = load_audit_module()

    result = audit.anchor_counterfactual(
        [
            {
                "actual_buy_new": True,
                "quality_action": "FULL_ALLOCATION_ELIGIBLE",
                "runtime_opportunity_score_sign": "NEGATIVE",
                "actual_notional": 100.0,
                "return_5bd": 0.10,
            },
            {
                "actual_buy_new": True,
                "quality_action": "REDUCED_ALLOCATION_ONLY",
                "runtime_opportunity_score_sign": "NEGATIVE",
                "actual_notional": 100.0,
                "return_5bd": -0.10,
            },
        ]
    )

    assert result["counterfactual_scope"] == "NOTIONAL_HELD_CONSTANT_NO_REALLOCATION_COUNTERFACTUAL"
    assert result["actual_count"] == 2
    assert result["full_only_count"] == 1
    assert result["exclude_reduced_negative_count"] == 1
    assert result["actual_capital_weighted_5bd"] == pytest.approx(0.0)
    assert result["full_only_capital_weighted_5bd"] == pytest.approx(0.10)


def test_audit_script_is_runtime_import_isolated() -> None:
    text = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "ai_fund_lab_v2" not in text
    assert "forward_return_used_only_for_audit" in text
    assert "future_data_used_by_runtime" in text
