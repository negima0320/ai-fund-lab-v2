from __future__ import annotations

import json
import pickle
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.opportunity_ai.design_compliance import (
    PHASE5_DESIGN_COMPLIANT_WITH_KNOWN_GAPS,
    PHASE5_DESIGN_NON_COMPLIANT,
    run_design_compliance_review,
)
from ai_fund_lab_v2.opportunity_ai.policy_finalization import FINAL_OUTPUT_COLUMNS


def test_phase5m_design_compliance_passes_with_known_gaps(tmp_path: Path) -> None:
    fixture = _write_fixture(tmp_path)

    result = run_design_compliance_review(
        dataset_path=fixture["dataset"],
        model_path=fixture["model"],
        phase5l_summary_path=fixture["phase5l_summary"],
        phase5l_audit_path=fixture["phase5l_audit"],
        phase5i_audit_path=fixture["phase5i_audit"],
        phase5k_schema_path=fixture["phase5k_schema"],
        phase5k_audit_path=fixture["phase5k_audit"],
        phase5j_audit_path=fixture["phase5j_audit"],
        output_dir=tmp_path / "phase5m",
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert result.review["readiness_status"] == PHASE5_DESIGN_COMPLIANT_WITH_KNOWN_GAPS
    assert result.review["promotion_ready"] is False
    assert result.audit["actual_feature_count"] == 16
    assert result.audit["forbidden_feature_audit"]["forbidden_feature_compliant"] is True
    assert result.audit["label_compliance_audit"]["expected_edge_label_20d_present"] is True
    assert result.audit["output_schema_audit"]["risk_guard_status_present"] is True
    assert result.audit["full_history_audit"]["monthly_only_completion"] is False
    assert result.audit["known_gaps"]["unused_feature_count"] > 0
    assert "Fundamental" in set(result.feature_coverage["category"])
    assert (tmp_path / "phase5m" / "design_compliance_review.json").is_file()
    assert (tmp_path / "phase5m" / "design_compliance_feature_coverage.csv").is_file()
    assert (tmp_path / "phase5m" / "design_compliance_audit.json").is_file()


def test_phase5m_detects_forbidden_feature(tmp_path: Path) -> None:
    fixture = _write_fixture(tmp_path, include_forbidden_feature=True)

    result = run_design_compliance_review(
        dataset_path=fixture["dataset"],
        model_path=fixture["model"],
        phase5l_summary_path=fixture["phase5l_summary"],
        phase5l_audit_path=fixture["phase5l_audit"],
        phase5i_audit_path=fixture["phase5i_audit"],
        phase5k_schema_path=fixture["phase5k_schema"],
        phase5k_audit_path=fixture["phase5k_audit"],
        phase5j_audit_path=fixture["phase5j_audit"],
        output_dir=tmp_path / "phase5m",
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert result.review["readiness_status"] == PHASE5_DESIGN_NON_COMPLIANT
    assert result.audit["forbidden_feature_audit"]["forbidden_feature_column_count"] == 1


def _write_fixture(tmp_path: Path, *, include_forbidden_feature: bool = False) -> dict[str, Path]:
    dataset = _dataset(include_forbidden_feature=include_forbidden_feature)
    dataset_path = tmp_path / "dataset.parquet"
    model_path = tmp_path / "model.pkl"
    dataset.to_parquet(dataset_path, index=False)
    feature_columns = [column for column in dataset.columns if column.startswith("feature__")]
    with model_path.open("wb") as handle:
        pickle.dump({"feature_columns": feature_columns, "model": object()}, handle)

    phase5l_summary = tmp_path / "phase5l_summary.json"
    phase5l_audit = tmp_path / "phase5l_audit.json"
    phase5i_audit = tmp_path / "phase5i_audit.json"
    phase5k_schema = tmp_path / "phase5k_schema.json"
    phase5k_audit = tmp_path / "phase5k_audit.json"
    phase5j_audit = tmp_path / "phase5j_audit.json"
    phase5l_summary.write_text(
        json.dumps(
            {
                "readiness_status": "PHASE5_COMPLETE_WITH_PROMOTION_DISABLED",
                "phase5_complete": True,
                "phase6_handoff_ready": True,
                "promotion_ready": False,
                "full_history_ready": True,
            }
        ),
        encoding="utf-8",
    )
    phase5l_audit.write_text(
        json.dumps(
            {
                "scope_boundary_audit": {
                    "scope_ok": True,
                    "ranks_candidate_top50": True,
                    "does_not_extract_candidates": True,
                    "does_not_manage_positions": True,
                    "does_not_allocate_capital": True,
                    "does_not_place_orders": True,
                    "does_not_decide_purchase_count": True,
                },
                "safety_boundary_audit": {
                    "safety_ok": True,
                    "broker_api_executed": False,
                    "paper_trading_executed": False,
                    "order_executed": False,
                    "capital_allocation_executed": False,
                    "promotion_performed": False,
                    "reader_switch_performed": False,
                },
            }
        ),
        encoding="utf-8",
    )
    phase5i_audit.write_text(
        json.dumps(
            {
                "target_date_count": 10,
                "candidate_rows": 500,
                "dataset_rows": 480,
                "train_rows": 300,
                "validation_rows": 100,
                "test_rows": 80,
                "leakage_status": "OK",
                "model_unique_score_count": 20,
                "all_same_score": False,
            }
        ),
        encoding="utf-8",
    )
    phase5k_schema.write_text(json.dumps({"output_columns": FINAL_OUTPUT_COLUMNS}), encoding="utf-8")
    phase5k_audit.write_text(
        json.dumps(
            {
                "policy_candidate_count": 7,
                "top6_10_tail_dilution_status": "TAIL_DILUTION_CONFIRMED",
                "simple_rule_top5_requires_risk_guard": True,
                "fixed_top10_finalized_as_buy_count": False,
                "phase5_decides_purchase_count": False,
                "forbidden_feature_column_count": 0,
                "future_feature_column_count": 0,
            }
        ),
        encoding="utf-8",
    )
    phase5j_audit.write_text(
        json.dumps(
            {
                "strategy_count": 29,
                "forbidden_feature_column_count": 0,
                "future_feature_column_count": 0,
            }
        ),
        encoding="utf-8",
    )
    return {
        "dataset": dataset_path,
        "model": model_path,
        "phase5l_summary": phase5l_summary,
        "phase5l_audit": phase5l_audit,
        "phase5i_audit": phase5i_audit,
        "phase5k_schema": phase5k_schema,
        "phase5k_audit": phase5k_audit,
        "phase5j_audit": phase5j_audit,
    }


def _dataset(*, include_forbidden_feature: bool) -> pd.DataFrame:
    row = {
        "target_date": "2026-01-31",
        "code": "1000",
        "split": "train",
        "feature__candidate_rank": 1,
        "feature__candidate_reason": "momentum",
        "feature__candidate_score": 0.9,
        "feature__liquidity_avg_volume_20d": 100000.0,
        "feature__missing_flags_insufficient_history": False,
        "feature__missing_flags_price": False,
        "feature__missing_flags_volume": False,
        "feature__price_momentum_return_20d": 0.1,
        "feature__price_momentum_return_5d": 0.03,
        "feature__price_momentum_return_60d": 0.2,
        "feature__trend_close_over_ma_20d": 0.05,
        "feature__trend_ma_20_60_ratio": 1.02,
        "feature__trend_ma_5_20_ratio": 1.01,
        "feature__volatility_return_std_20d": 0.04,
        "feature__volume_momentum_ratio_1d_20d": 1.2,
        "feature__volume_momentum_ratio_5d": 1.1,
        "label__expected_edge_label_20d": 0.1,
        "label__future_return_20d": 0.1,
        "label__future_max_return_20d": 0.2,
        "label__future_max_drawdown_20d": -0.05,
        "label__downside_bad_20d": False,
        "label__top_decile_20d": True,
    }
    if include_forbidden_feature:
        row["feature__future_return_20d"] = 0.1
    return pd.DataFrame([row])
