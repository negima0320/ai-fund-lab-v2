from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.opportunity_ai.policy_finalization import (
    FINAL_OUTPUT_COLUMNS,
    NEEDS_PHASE5J_REVIEW,
    READY_FOR_PHASE5L_COMPLETION_AUDIT,
    finalize_opportunity_policy,
)


def test_phase5k_finalizes_policy_candidates_and_schema(tmp_path: Path) -> None:
    phase5j_dir = tmp_path / "phase5j"
    output_dir = tmp_path / "phase5k"
    _write_phase5j_artifacts(phase5j_dir)

    result = finalize_opportunity_policy(
        phase5j_dir=phase5j_dir,
        output_dir=output_dir,
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert result.summary["readiness_status"] == READY_FOR_PHASE5L_COMPLETION_AUDIT
    assert result.summary["promotion_ready"] is False
    assert result.audit["leakage_status"] == "OK"
    assert result.audit["recommended_policy_name"] == "simple_rule_top5"
    assert result.audit["simple_rule_top5_requires_risk_guard"] is True
    assert result.audit["fixed_top10_finalized_as_buy_count"] is False
    assert result.audit["phase5_decides_purchase_count"] is False
    assert result.output_schema["output_columns"] == FINAL_OUTPUT_COLUMNS
    assert "risk_guard_status" in result.output_schema["columns"]
    assert "calibration_policy_name" in result.output_schema["columns"]
    assert set(["simple_rule_top5", "top10_gap_threshold_policy", "risk_adjusted_model_top5"]).issubset(
        set(result.policy_candidates["policy_name"])
    )
    assert (output_dir / "policy_finalization_summary.json").is_file()
    assert (output_dir / "policy_finalization_audit.json").is_file()
    assert (output_dir / "final_opportunity_output_schema.json").is_file()
    assert (output_dir / "final_policy_candidates.csv").is_file()


def test_phase5k_blocks_when_phase5j_artifacts_missing(tmp_path: Path) -> None:
    result = finalize_opportunity_policy(
        phase5j_dir=tmp_path / "missing_phase5j",
        output_dir=tmp_path / "phase5k",
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert result.summary["readiness_status"] == NEEDS_PHASE5J_REVIEW
    assert result.audit["phase5j_artifacts_loaded"] is False
    assert result.summary["promotion_ready"] is False


def _write_phase5j_artifacts(phase5j_dir: Path) -> None:
    phase5j_dir.mkdir(parents=True, exist_ok=True)
    (phase5j_dir / "calibration_metrics.json").write_text(
        json.dumps({"readiness_status": "READY_FOR_PHASE5K_POLICY_FINALIZATION", "promotion_ready": False}),
        encoding="utf-8",
    )
    (phase5j_dir / "calibration_audit.json").write_text(
        json.dumps(
            {
                "readiness_status": "READY_FOR_PHASE5K_POLICY_FINALIZATION",
                "promotion_ready": False,
                "leakage_status": "OK",
                "forbidden_feature_column_count": 0,
                "future_feature_column_count": 0,
                "trade_result_feature_column_count": 0,
                "portfolio_feature_column_count": 0,
                "backtest_feature_column_count": 0,
                "strategy_count": 29,
            }
        ),
        encoding="utf-8",
    )
    (phase5j_dir / "recommended_policy.json").write_text(
        json.dumps(
            {
                "policy_name": "simple_rule_top5",
                "recommendation_type": "calibration_candidate_not_promoted",
                "promotion_ready": False,
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame(_strategy_rows()).to_csv(phase5j_dir / "calibration_by_strategy.csv", index=False)


def _strategy_rows() -> list[dict[str, object]]:
    strategies = {
        "current_model_top5": (0.04, 0.05, -0.01),
        "current_model_top10": (0.03, 0.04, -0.02),
        "current_model_top20": (0.05, 0.06, -0.01),
        "simple_rule_top5": (0.14, 0.05, 0.08),
        "top10_gap_threshold_policy": (0.06, 0.04, -0.04),
        "risk_adjusted_model_top5": (0.055, 0.07, -0.04),
        "simple_rule_blend_model_top5": (0.09, 0.07, -0.01),
    }
    rows: list[dict[str, object]] = []
    for split in ("validation", "test"):
        for strategy, values in strategies.items():
            mean_return, mean_max_return, downside_delta = values
            rows.append(
                {
                    "split": split,
                    "strategy": strategy,
                    "ranker": "score__fixture",
                    "selection": "top5" if "top5" in strategy else "top10",
                    "selected_row_count": 10,
                    "selected_target_date_count": 2,
                    "mean_future_return_20d": mean_return,
                    "mean_future_max_return_20d": mean_max_return,
                    "top_decile_rate_20d": 0.2,
                    "downside_bad_rate_20d": 0.5 + max(0.0, downside_delta),
                    "mean_future_max_drawdown_20d": -0.1,
                    "win_rate_20d": 0.55,
                    "candidate_top50_mean_future_return_20d": 0.04,
                    "candidate_top50_mean_future_max_return_20d": 0.04,
                    "candidate_top50_downside_bad_rate_20d": 0.5,
                    "lift_vs_candidate_top50_future_return": mean_return - 0.04,
                    "lift_vs_candidate_top50_future_max_return": mean_max_return - 0.04,
                    "downside_bad_delta_vs_candidate_top50": downside_delta,
                }
            )
    return rows
