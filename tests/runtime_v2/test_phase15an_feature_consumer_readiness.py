import json
from pathlib import Path
from typing import Optional

import pandas as pd

from ai_fund_lab_v2.runtime_v2.market_refresh.consumer_readiness import (
    CANDIDATE_REQUIRED_COLUMNS,
    OPPORTUNITY_REQUIRED_COLUMNS,
    validate_feature_consumer_readiness,
)
from ai_fund_lab_v2.runtime_v2.market_refresh.pipeline import run_runtime_v2_market_refresh_pipeline


def test_phase15an_candidate_thirteen_columns_are_consumer_ready(tmp_path, monkeypatch):
    operations_root = tmp_path / ".runtime" / "operations"
    _write_feature_artifacts(operations_root / "feature_artifacts" / "2026-07-10", "2026-07-10")
    _write_current(tmp_path / ".runtime", positions=[])

    readiness = validate_feature_consumer_readiness(
        operations_root=operations_root,
        feature_date="2026-07-10",
    )

    assert readiness.status == "READY"
    assert readiness.consumer_ready is True
    assert readiness.candidate_schema_status == "READY"
    assert readiness.candidate_missing_columns == ()


def test_phase15an_candidate_one_missing_column_requires_review(tmp_path, monkeypatch):
    operations_root = tmp_path / ".runtime" / "operations"
    _write_feature_artifacts(
        operations_root / "feature_artifacts" / "2026-07-10",
        "2026-07-10",
        drop_candidate_column="price_momentum_return_60d",
    )
    _write_current(tmp_path / ".runtime", positions=[])

    result = _run_market_refresh_with_existing_artifacts(monkeypatch, operations_root)

    assert result.status == "REVIEW_REQUIRED"
    assert result.consumer_ready is False
    assert result.candidate_schema_status == "REVIEW_REQUIRED"
    assert result.candidate_missing_columns == ("price_momentum_return_60d",)
    assert "consumer_schema_review_required" in result.reason


def test_phase15an_candidate_rename_mismatch_requires_review(tmp_path):
    operations_root = tmp_path / ".runtime" / "operations"
    _write_feature_artifacts(
        operations_root / "feature_artifacts" / "2026-07-10",
        "2026-07-10",
        drop_candidate_column="missing_flags_insufficient_history",
        extra_candidate_columns={"missing_flags_insufficient_lookback": False},
    )
    _write_current(tmp_path / ".runtime", positions=[])

    readiness = validate_feature_consumer_readiness(
        operations_root=operations_root,
        feature_date="2026-07-10",
    )

    assert readiness.status == "REVIEW_REQUIRED"
    assert readiness.candidate.alias_mismatches == {
        "missing_flags_insufficient_lookback": "missing_flags_insufficient_history"
    }
    assert "missing_flags_insufficient_history" in readiness.candidate_missing_columns


def test_phase15an_opportunity_double_prefix_is_not_consumer_ready(tmp_path):
    operations_root = tmp_path / ".runtime" / "operations"
    _write_feature_artifacts(
        operations_root / "feature_artifacts" / "2026-07-10",
        "2026-07-10",
        extra_opportunity_columns={"feature__price_momentum_return_5d": 0.1},
    )
    _write_current(tmp_path / ".runtime", positions=[])

    readiness = validate_feature_consumer_readiness(
        operations_root=operations_root,
        feature_date="2026-07-10",
    )

    assert readiness.status == "REVIEW_REQUIRED"
    assert readiness.opportunity_schema_status == "REVIEW_REQUIRED"
    assert readiness.opportunity.unexpected_prefixed_columns == ("feature__price_momentum_return_5d",)


def test_phase15an_pm_feature_zero_rows_with_current_positions_requires_review(tmp_path):
    operations_root = tmp_path / ".runtime" / "operations"
    _write_feature_artifacts(
        operations_root / "feature_artifacts" / "2026-07-10",
        "2026-07-10",
        position_rows=[],
    )
    _write_current(tmp_path / ".runtime", positions=[{"symbol": "7203", "quantity": 100}])

    readiness = validate_feature_consumer_readiness(
        operations_root=operations_root,
        feature_date="2026-07-10",
    )

    assert readiness.status == "REVIEW_REQUIRED"
    assert readiness.pm_schema_status == "REVIEW_REQUIRED"
    assert readiness.pm.reason == "position_feature_current_output_mismatch"


def test_phase15an_feature_refresh_manifest_records_consumer_ready(tmp_path, monkeypatch):
    operations_root = tmp_path / ".runtime" / "operations"
    _write_feature_artifacts(operations_root / "feature_artifacts" / "2026-07-10", "2026-07-10")
    _write_current(tmp_path / ".runtime", positions=[])

    result = _run_market_refresh_with_existing_artifacts(monkeypatch, operations_root)
    contract = json.loads((operations_root / "feature_date_contract" / "2026-07-10.json").read_text())
    readiness = json.loads(Path(result.consumer_readiness_artifact_path).read_text())

    assert result.status == "PASS"
    assert result.consumer_ready is True
    assert result.candidate_schema_status == "READY"
    assert result.opportunity_schema_status == "READY"
    assert result.pm_schema_status == "READY"
    assert contract["consumer_ready"] is True
    assert readiness["consumer_ready"] is True


def _run_market_refresh_with_existing_artifacts(monkeypatch, operations_root: Path):
    from ai_fund_lab_v2.runtime_v2.market_refresh import pipeline as market_refresh_pipeline

    def fake_operations_market_refresh(**kwargs):
        return {
            "status": "PASS",
            "blocked_reasons": [],
            "jquants_api_fetch_executed": False,
            "canonical_normalized_updated": True,
            "feature_refresh_executed": True,
            "feature_refresh_status": "FEATURES_READY",
            "latest_available_market_date": kwargs["trade_date"],
            "data_quality_status": "PASS",
            "feature_freshness_status": "FEATURE_READY",
        }

    monkeypatch.setattr(market_refresh_pipeline, "_run_operations_market_refresh", fake_operations_market_refresh)
    return run_runtime_v2_market_refresh_pipeline(
        business_date="2026-07-10",
        operations_root=operations_root,
        allow_api_fetch=False,
    )


def _write_feature_artifacts(
    feature_dir: Path,
    feature_date: str,
    *,
    drop_candidate_column: str = "",
    extra_candidate_columns: Optional[dict] = None,
    extra_opportunity_columns: Optional[dict] = None,
    position_rows: Optional[list[dict]] = None,
) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    row = {column: _value_for_column(column, feature_date) for column in CANDIDATE_REQUIRED_COLUMNS}
    candidate = dict(row)
    if drop_candidate_column:
        candidate.pop(drop_candidate_column)
    candidate.update(extra_candidate_columns or {})
    opportunity = {column: _value_for_column(column, feature_date) for column in OPPORTUNITY_REQUIRED_COLUMNS}
    opportunity.update(extra_opportunity_columns or {})
    pd.DataFrame([candidate]).to_parquet(feature_dir / "candidate_features.parquet", index=False)
    pd.DataFrame([opportunity]).to_parquet(feature_dir / "opportunity_feature_input.parquet", index=False)
    if position_rows is None:
        position_rows = []
    position_columns = [
        "target_date",
        "position_state_as_of",
        "entry_date",
        "code",
        "broker_issue_code",
        "holding_days",
        "average_price",
        "current_price",
        "unrealized_return",
        "quantity",
        "feature_version",
        "data_until",
        "created_at",
        "no_position_reason",
    ]
    if position_rows:
        position_frame = pd.DataFrame(position_rows, columns=position_columns)
    else:
        position_frame = pd.DataFrame(columns=position_columns)
    position_frame.to_parquet(
        feature_dir / "position_feature_input.parquet",
        index=False,
    )
    pd.DataFrame([{"target_date": feature_date, "code": "__POLICY_INPUT__"}]).to_parquet(
        feature_dir / "capital_policy_input.parquet",
        index=False,
    )


def _value_for_column(column: str, feature_date: str):
    if column == "target_date":
        return feature_date
    if column == "code":
        return "72030"
    if column.startswith("missing_flags_"):
        return False
    return 1.0


def _write_current(runtime_root: Path, *, positions: list[dict]) -> None:
    path = runtime_root / "persistent_ledger" / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "asset_state_id": "asset-phase15an",
                "environment": "demo",
                "business_date": "2026-07-10",
                "as_of": "2026-07-10",
                "updated_at": "2026-07-10T00:00:00Z",
                "positions": positions,
                "cash": 1_000_000,
                "buying_power": 1_000_000,
                "market_value": 0,
                "total_equity": 1_000_000,
                "current_state_confirmed_empty": not bool(positions),
                "current_positions_unknown": False,
                "cash_unknown": False,
                "buying_power_unknown": False,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
