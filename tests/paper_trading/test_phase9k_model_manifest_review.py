from __future__ import annotations

from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.paper_trading.model_manifest_review import (
    FEATURE_SCHEMA_MISMATCH,
    FORBIDDEN_SOURCE_DETECTED,
    MANIFEST_METADATA_INCOMPLETE,
    MODEL_ELIGIBLE,
    POLICY_MANIFEST_REQUIRED,
    RETRAIN_REQUIRED,
    review_model_manifest,
)


def test_policy_manifest_can_be_eligible(tmp_path: Path) -> None:
    calendar = _calendar(tmp_path)
    manifest = {
        "policy_name": "CAP5",
        "policy_version": "phase7d_realistic_execution_constraints_v1/CAP5",
        "data_until": "2026-06-15",
        "feature_schema_hash": "hash1",
        "train_until_required": False,
        "leakage_audit_status": "OK",
        "forbidden_source_audit_status": "OK",
        "source_data_refs": {"normalized": ".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet"},
    }

    result = review_model_manifest(
        ai_name="capital",
        manifest=manifest,
        manifest_path=tmp_path / "capital.json",
        expected_feature_schema_hash="hash1",
        data_until="2026-06-15",
        trading_calendar_path=calendar,
    )

    assert result.status == MODEL_ELIGIBLE
    assert result.retrain_required is False


def test_forbidden_source_detected(tmp_path: Path) -> None:
    calendar = _calendar(tmp_path)
    manifest = _model_manifest(source_data_refs={"paper_ledger": ".runtime/phase9/ledger/latest.json"})

    result = review_model_manifest(
        ai_name="opportunity",
        manifest=manifest,
        manifest_path=tmp_path / "m.json",
        expected_feature_schema_hash="hash1",
        data_until="2026-06-15",
        trading_calendar_path=calendar,
    )

    assert result.status == FORBIDDEN_SOURCE_DETECTED
    assert "forbidden_source_detected" in result.blocked_reasons


def test_feature_schema_mismatch_detected(tmp_path: Path) -> None:
    calendar = _calendar(tmp_path)
    manifest = _model_manifest(feature_schema_hash="old")

    result = review_model_manifest(
        ai_name="opportunity",
        manifest=manifest,
        manifest_path=tmp_path / "m.json",
        expected_feature_schema_hash="new",
        data_until="2026-06-15",
        trading_calendar_path=calendar,
    )

    assert result.status == FEATURE_SCHEMA_MISMATCH


def test_train_until_after_safe_train_until_blocked(tmp_path: Path) -> None:
    calendar = _calendar(tmp_path)
    manifest = _model_manifest(train_until="2026-06-15")

    result = review_model_manifest(
        ai_name="opportunity",
        manifest=manifest,
        manifest_path=tmp_path / "m.json",
        expected_feature_schema_hash="hash1",
        data_until="2026-06-15",
        trading_calendar_path=calendar,
    )

    assert result.status == RETRAIN_REQUIRED
    assert "train_until_after_safe_train_until" in result.blocked_reasons


def test_missing_manifest_blocked() -> None:
    result = review_model_manifest(
        ai_name="position",
        manifest=None,
        manifest_path=None,
        expected_feature_schema_hash="hash1",
        data_until="2026-06-15",
    )

    assert result.status == POLICY_MANIFEST_REQUIRED


def test_missing_label_horizon_blocked(tmp_path: Path) -> None:
    calendar = _calendar(tmp_path)
    manifest = _model_manifest()
    manifest.pop("label_horizon")

    result = review_model_manifest(
        ai_name="opportunity",
        manifest=manifest,
        manifest_path=tmp_path / "m.json",
        expected_feature_schema_hash="hash1",
        data_until="2026-06-15",
        trading_calendar_path=calendar,
    )

    assert result.status == MANIFEST_METADATA_INCOMPLETE
    assert "missing_label_horizon" in result.blocked_reasons


def test_non_jquants_source_blocked(tmp_path: Path) -> None:
    calendar = _calendar(tmp_path)
    manifest = _model_manifest(source_data_refs={"csv": "/tmp/local/manual.csv"})

    result = review_model_manifest(
        ai_name="opportunity",
        manifest=manifest,
        manifest_path=tmp_path / "m.json",
        expected_feature_schema_hash="hash1",
        data_until="2026-06-15",
        trading_calendar_path=calendar,
    )

    assert "source_data_refs_not_jquants_only" in result.blocked_reasons


def _model_manifest(
    *,
    train_until: str = "2026-05-15",
    feature_schema_hash: str = "hash1",
    source_data_refs=None,
) -> dict:
    return {
        "model_version": "opportunity_model_phase5e_v1",
        "artifact_path": __file__,
        "train_until": train_until,
        "data_until": "2026-06-15",
        "label_horizon": 20,
        "feature_schema_hash": feature_schema_hash,
        "leakage_audit_status": "OK",
        "forbidden_source_audit_status": "OK",
        "source_data_refs": source_data_refs or {"normalized": ".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet"},
    }


def _calendar(tmp_path: Path) -> Path:
    path = tmp_path / "jquants/calendar.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    dates = pd.bdate_range("2026-04-01", "2026-06-15").strftime("%Y-%m-%d").tolist()
    pd.DataFrame({"Date": dates, "HolDiv": ["1"] * len(dates)}).to_parquet(path, index=False)
    return path
