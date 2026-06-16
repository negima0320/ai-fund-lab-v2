from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.paper_trading.policy_manifest import build_policy_manifest, write_policy_manifest


def test_policy_manifest_generation(tmp_path: Path) -> None:
    manifest = build_policy_manifest(
        ai_name="capital",
        policy_name="CAP5",
        policy_version="phase7d_realistic_execution_constraints_v1/CAP5",
        implementation_ref="src/ai_fund_lab_v2/capital_allocation_ai/phase7d_execution_constraints_validation.py",
        data_until="2026-06-15",
        decision_for="2026-06-15",
        feature_schema_hash="abc123",
        source_data_refs={"normalized_daily_quotes": ".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet"},
    )
    path = write_policy_manifest(manifest, tmp_path / "manifests")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["train_until_required"] is False
    assert payload["label_horizon_required"] is False
    assert payload["broker_api_executed"] is False
    assert payload["paper_ledger_training_used"] is False
    assert payload["backtest_result_training_used"] is False
    assert payload["public_confidence_training_used"] is False
    assert payload["model_retraining_executed"] is False
    assert payload["inference_executed"] is False
