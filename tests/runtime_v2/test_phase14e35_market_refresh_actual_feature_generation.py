import json
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.runtime_v2.cli import run_daily_operation
from ai_fund_lab_v2.runtime_v2.market_refresh import pipeline as market_refresh_pipeline
from ai_fund_lab_v2.runtime_v2.market_refresh.pipeline import run_runtime_v2_market_refresh_pipeline


ARTIFACTS = (
    "candidate_features.parquet",
    "opportunity_feature_input.parquet",
    "position_feature_input.parquet",
    "capital_policy_input.parquet",
)


def test_phase14e35_market_refresh_pipeline_requires_actual_feature_artifacts(tmp_path, monkeypatch):
    def fake_operations_market_refresh(**kwargs):
        feature_dir = Path(kwargs["root"]) / "feature_artifacts" / kwargs["trade_date"]
        feature_dir.mkdir(parents=True, exist_ok=True)
        for name in ARTIFACTS:
            pd.DataFrame([{"target_date": kwargs["trade_date"], "code": "72030"}]).to_parquet(
                feature_dir / name,
                index=False,
            )
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

    result = run_runtime_v2_market_refresh_pipeline(
        business_date="2026-07-08",
        operations_root=tmp_path / ".runtime" / "operations",
        allow_api_fetch=False,
    )

    assert result.status == "PASS"
    assert result.reason == "requested_feature_artifacts_available"
    assert set(result.generated_feature_artifacts) == set(ARTIFACTS)
    assert result.missing_feature_artifacts == ()
    assert result.selected_feature_date == "2026-07-08"
    assert result.carryover_used is False
    assert result.canonical_normalized_updated is True
    assert result.feature_refresh_executed is True


def test_phase14e35_market_refresh_missing_artifacts_is_not_success(tmp_path, monkeypatch):
    def fake_operations_market_refresh(**kwargs):
        feature_dir = Path(kwargs["root"]) / "feature_artifacts" / kwargs["trade_date"]
        feature_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([{"target_date": kwargs["trade_date"], "code": "72030"}]).to_parquet(
            feature_dir / "candidate_features.parquet",
            index=False,
        )
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

    result = run_runtime_v2_market_refresh_pipeline(
        business_date="2026-07-08",
        operations_root=tmp_path / ".runtime" / "operations",
        allow_api_fetch=False,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "feature_artifacts_missing" in result.reason
    assert set(result.missing_feature_artifacts) == set(ARTIFACTS[1:])


def test_phase14e35_cli_market_refresh_records_artifacts_and_blocks_checkpoint_only(tmp_path, monkeypatch):
    monkeypatch.setattr(
        run_daily_operation,
        "run_runtime_v2_market_refresh_pipeline",
        _fake_runtime_market_refresh_pipeline,
    )
    runtime_root = _write_fixed_current(tmp_path / ".runtime")

    exit_code = run_daily_operation.main(
        [
            "--mode",
            "demo",
            "--job",
            "market_refresh",
            "--business-date",
            "2026-07-08",
            "--submit-enabled",
            "false",
            "--notification-mode",
            "payload-only",
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(tmp_path / ".runtime" / "runtime_state" / "run_manifest"),
            "--log-root",
            str(tmp_path / ".runtime" / "runtime_state" / "logs"),
            "--feature-root",
            str(tmp_path / ".runtime" / "operations" / "feature_artifacts"),
        ]
    )
    manifest_path = next((tmp_path / ".runtime" / "runtime_state" / "run_manifest" / "2026-07-08").glob("*.json"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    market_stage = next(stage for stage in manifest["stages"] if stage["name"] == "runtime_v2_market_refresh_pipeline")

    assert exit_code == 0
    assert market_stage["status"] == "PASS"
    assert set(manifest["generated_artifacts"]["feature_artifacts"]) == set(ARTIFACTS)
    assert "runtime_v2_market_refresh_pipeline" in {stage["name"] for stage in manifest["stages"]}


def _fake_runtime_market_refresh_pipeline(**kwargs):
    feature_dir = Path(kwargs["operations_root"]) / "feature_artifacts" / kwargs["business_date"]
    artifacts = {name: str(feature_dir / name) for name in ARTIFACTS}
    return type(
        "MarketRefreshResult",
        (),
        {
            "status": "PASS",
            "reason": "fake market refresh",
            "generated_feature_artifacts": artifacts,
            "feature_artifact_dir": str(feature_dir),
            "to_stage_details": lambda self: {
                "status": "PASS",
                "generated_feature_artifacts": artifacts,
                "feature_artifact_dir": str(feature_dir),
            },
        },
    )()


def _write_fixed_current(root: Path) -> Path:
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-e35",
            "environment": "demo",
            "updated_at": "2026-07-08T00:00:00Z",
            "positions": [],
            "cash": 1000000.0,
            "buying_power": 1000000.0,
            "market_value": 0.0,
            "total_equity": 1000000.0,
            "source": "phase14e8_demo_operation_initial_state",
            "review_required": False,
            "current_state_confirmed_empty": True,
            "cash_confirmed": True,
            "buying_power_confirmed": True,
        },
    )
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"state": "CONSUMED", "items": []})
    _write_json(root / "runtime_state" / "current_state.json", {"state": "CURRENT_STATE_LOADED"})
    for name in ("orders", "executions", "positions", "cash", "events"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    return root


def _write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
