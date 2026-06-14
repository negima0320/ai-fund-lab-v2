from __future__ import annotations

from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.position_management_ai.feature_builder import (
    READY_FOR_PHASE6C_VALIDATION_DESIGN,
    REQUIRED_FEATURE_COLUMNS,
    build_position_features_from_quotes,
    fixture_opportunity_frame,
    fixture_position_scenarios,
    fixture_quote_frame,
    run_phase6b_position_feature_dry_run,
    to_phase6_inference_frame,
)
from ai_fund_lab_v2.position_management_ai.inference import (
    BLOCKED_BY_LEAKAGE_AUDIT,
    audit_position_feature_frame,
)


def test_phase6b_generates_required_position_features() -> None:
    features = build_position_features_from_quotes(
        position_frame=fixture_position_scenarios(),
        quote_frame=fixture_quote_frame(),
        opportunity_frame=fixture_opportunity_frame(),
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert len(features) == 6
    assert set(REQUIRED_FEATURE_COLUMNS).issubset(features.columns)
    assert features["holding_days"].min() > 0
    assert features["unrealized_return"].notna().all()
    assert features["drawdown_from_peak"].notna().all()


def test_phase6b_forbidden_feature_audit_blocks_leakage() -> None:
    features = build_position_features_from_quotes(
        position_frame=fixture_position_scenarios(),
        quote_frame=fixture_quote_frame(),
        opportunity_frame=fixture_opportunity_frame(),
        created_at="2026-06-14T00:00:00+00:00",
    )
    inference_frame = to_phase6_inference_frame(features)
    inference_frame["feature__future_return_20d"] = 0.20

    audit = audit_position_feature_frame(inference_frame, input_holding_count=len(features), created_at="2026-06-14T00:00:00+00:00")

    assert audit["readiness_status"] == BLOCKED_BY_LEAKAGE_AUDIT
    assert audit["leakage_audit_status"] == "ERROR"
    assert "feature__future_return_20d" in audit["forbidden_feature_columns"]


def test_phase6b_add_candidates_are_profit_positions_only(tmp_path: Path) -> None:
    result = run_phase6b_position_feature_dry_run(
        output_csv_path=tmp_path / "phase6b.csv",
        output_json_path=tmp_path / "phase6b.json",
        created_at="2026-06-14T00:00:00+00:00",
    )

    add_rows = result.feature_frame[result.feature_frame["add_candidate"]]
    assert not add_rows.empty
    assert (add_rows["unrealized_return"] > 0).all()
    assert result.summary["add_loss_position_count"] == 0


def test_phase6b_leakage_audit_ok_for_fixture() -> None:
    features = build_position_features_from_quotes(
        position_frame=fixture_position_scenarios(),
        quote_frame=fixture_quote_frame(),
        opportunity_frame=fixture_opportunity_frame(),
        created_at="2026-06-14T00:00:00+00:00",
    )
    inference_frame = to_phase6_inference_frame(features)

    audit = audit_position_feature_frame(inference_frame, input_holding_count=len(features), created_at="2026-06-14T00:00:00+00:00")

    assert audit["leakage_audit_status"] == "OK"
    assert audit["forbidden_feature_column_count"] == 0
    assert audit["future_feature_column_count"] == 0
    assert audit["label_column_count"] == 0


def test_phase6b_small_dry_run_writes_csv_and_json(tmp_path: Path) -> None:
    csv_path = tmp_path / "dry_run.csv"
    json_path = tmp_path / "dry_run.json"

    result = run_phase6b_position_feature_dry_run(
        output_csv_path=csv_path,
        output_json_path=json_path,
        created_at="2026-06-14T00:00:00+00:00",
    )

    assert result.summary["readiness_status"] == READY_FOR_PHASE6C_VALIDATION_DESIGN
    assert result.summary["dry_run_row_count"] == 6
    assert csv_path.is_file()
    assert json_path.is_file()
    written = pd.read_csv(csv_path)
    assert len(written) == 6
    assert set(written["action"]).issubset({"HOLD", "EXIT", "ADD", "REDUCE"})
