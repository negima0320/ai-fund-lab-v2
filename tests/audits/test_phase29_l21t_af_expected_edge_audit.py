from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest


SCRIPT_PATH = Path("scripts/audits/phase29_l21t_af_expected_edge_audit.py")


def load_audit_module():
    spec = importlib.util.spec_from_file_location("phase29_l21t_af_expected_edge_audit", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_forward_return_is_posthoc_close_to_future_close() -> None:
    audit = load_audit_module()
    bars = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                [
                    "2022-10-05",
                    "2022-10-06",
                    "2022-10-07",
                    "2022-10-11",
                    "2022-10-12",
                    "2022-10-13",
                ]
            ).date,
            "Close": [100.0, 101.0, 99.0, 105.0, 108.0, 110.0],
            "High": [100.0, 103.0, 100.0, 106.0, 109.0, 111.0],
            "Low": [100.0, 98.0, 97.0, 104.0, 107.0, 109.0],
        }
    )

    result = audit.forward_returns({"12340": bars}, "12340", "2022-10-05")

    assert result["decision_close"] == 100.0
    assert result["return_5bd"] == pytest.approx(0.10)
    assert result["mfe_5bd"] == pytest.approx(0.11)
    assert result["mae_5bd"] == pytest.approx(-0.03)


def test_cohort_classification_keeps_required_groups() -> None:
    audit = load_audit_module()

    assert (
        audit.classify_cohort(
            {
                "buy_quality_status": "PASS",
                "buy_allocated": True,
                "expected_edge_score": 0.1,
                "lot_safety_blocked": False,
                "opportunity_no_buy_reason": "",
                "exclusion_zero_allocation_reason": "",
                "ranking_top20_exclusion": False,
            }
        )
        == "A_QUALITY_PASS_POSITIVE_EDGE_BUY_ALLOCATED"
    )
    assert (
        audit.classify_cohort(
            {
                "buy_quality_status": "PASS",
                "buy_allocated": False,
                "expected_edge_score": -0.01,
                "lot_safety_blocked": False,
                "opportunity_no_buy_reason": "non_positive_expected_edge_score",
                "exclusion_zero_allocation_reason": "",
                "ranking_top20_exclusion": False,
            }
        )
        == "B_QUALITY_PASS_NON_POSITIVE_EXPECTED_EDGE_ZERO_BUY"
    )
    assert audit.classify_cohort({"buy_quality_status": "REJECT", "buy_allocated": False}) == "E_QUALITY_REJECTED"


def test_audit_script_is_runtime_import_isolated() -> None:
    text = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "ai_fund_lab_v2" not in text
    assert "forward_return_used_only_for_audit" in text
    assert "future_data_used_by_runtime" in text
