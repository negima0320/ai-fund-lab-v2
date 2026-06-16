from pathlib import Path

from ai_fund_lab_v2.paper_trading.model_eligibility import ELIGIBLE, NOT_ELIGIBLE, check_model_eligibility


def test_model_eligibility_ok_without_artifact_path() -> None:
    result = check_model_eligibility(
        {
            "model_version": "v1",
            "train_until": "2026-06-12",
            "data_until": "2026-06-16",
            "feature_schema_hash": "hash",
            "leakage_audit_status": "OK",
            "training_sources": ["J-Quants"],
        },
        decision_for="2026-06-16",
    )
    assert result.status == ELIGIBLE
    assert "artifact_path_not_provided" in result.warnings


def test_model_eligibility_blocks_future_train_until() -> None:
    result = check_model_eligibility(
        {
            "model_version": "v1",
            "train_until": "2026-06-17",
            "data_until": "2026-06-16",
            "feature_schema_hash": "hash",
            "leakage_audit_status": "OK",
        },
        decision_for="2026-06-16",
    )
    assert result.status == NOT_ELIGIBLE
    assert "train_until_after_decision_for" in result.blocked_reasons


def test_model_eligibility_blocks_forbidden_training_source(tmp_path: Path) -> None:
    artifact = tmp_path / "model.pkl"
    artifact.write_text("x", encoding="utf-8")
    result = check_model_eligibility(
        {
            "model_version": "v1",
            "train_until": "2026-06-12",
            "data_until": "2026-06-16",
            "feature_schema_hash": "hash",
            "leakage_audit_status": "OK",
            "artifact_path": str(artifact),
            "training_sources": ["J-Quants", "Paper Ledger"],
        },
        decision_for="2026-06-16",
    )
    assert result.status == NOT_ELIGIBLE
    assert "forbidden_training_source_paper_ledger" in result.blocked_reasons

