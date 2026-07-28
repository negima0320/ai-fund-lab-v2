import json
from pathlib import Path

import pandas as pd
from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main


def test_phase14e50_sell_planning_cli_writes_sell_pending_from_pm_ai_artifact(tmp_path):
    runtime_root = _write_runtime_state(
        tmp_path / ".runtime",
        positions=[
            _position("3926", quantity=1000, price=351),
            _position("6897", quantity=500, price=676),
        ],
    )
    _write_jsonl(
        runtime_root / "persistent_ledger" / "positions.jsonl",
        [
            {
                "record_type": "position",
                "symbol": "9001",
                "quantity": 100,
                "source": "broker_readonly_evidence_only",
            }
        ],
    )
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    opportunity_path, feature_path = _write_pm_inputs(tmp_path, symbols=("3926", "6897"))

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "sell_planning",
            "--business-date",
            "2026-07-09",
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
            str(runtime_root / "runtime_state" / "run_manifest"),
            "--log-root",
            str(runtime_root / "runtime_state" / "logs"),
            "--capital-deployment-policy",
            str(policy_path),
            "--pm-opportunity-path",
            str(opportunity_path),
            "--pm-feature-path",
            str(feature_path),
        ]
    )

    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    manifests = sorted((runtime_root / "runtime_state" / "run_manifest" / "2026-07-09").glob("*.json"))
    manifest = _load_json(manifests[-1])
    stage_names = {stage["name"] for stage in manifest["stages"]}
    symbols = {item["symbol"] for item in pending["items"]}

    assert exit_code == 0
    assert manifest["job"] == "sell_planning"
    assert "sell_planning_pending_pipeline" in stage_names
    assert "position_management_ai_runtime_producer" in stage_names
    assert manifest["submit_enabled"] is False
    assert manifest["prohibited_actions"]["demo_submit_executed"] is False
    assert manifest["pm_exit_count"] == 2
    assert manifest["pm_artifact_path"]
    assert pending["state"] == "APPROVED"
    assert {item["side"] for item in pending["items"]} == {"SELL"}
    assert symbols == {"3926", "6897"}
    assert "9001" not in symbols
    assert pending["approval"]["approval_status"] == "APPROVED"
    assert (tmp_path / "reports" / "public" / "runtime_v2" / "latest.md").exists()
    assert "runtime_v2_sell_planning_current_position_exit" not in json.dumps(manifest)


def test_phase14e50_sell_planning_cli_blocks_submit_enabled_true(tmp_path):
    runtime_root = _write_runtime_state(
        tmp_path / ".runtime",
        positions=[_position("3926", quantity=1000, price=351)],
    )

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "sell_planning",
            "--business-date",
            "2026-07-09",
            "--submit-enabled",
            "true",
            "--notification-mode",
            "payload-only",
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(runtime_root / "runtime_state" / "run_manifest"),
            "--log-root",
            str(runtime_root / "runtime_state" / "logs"),
        ]
    )

    assert exit_code == 40


def _write_runtime_state(root: Path, *, positions: list[dict]) -> Path:
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-e50",
            "environment": "demo",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": "2026-07-09",
            "updated_at": "2026-07-09T00:00:00Z",
            "positions": positions,
            "cash": 140500.0,
            "buying_power": 140500.0,
            "market_value": sum(float(item["market_value"]) for item in positions),
            "total_equity": 140500.0 + sum(float(item["market_value"]) for item in positions),
            "review_required": False,
            "current_state_confirmed_empty": False,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
        },
    )
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "1",
            "pending_plan_id": "pending-e50-before",
            "state": "CONSUMED",
            "environment": "demo",
            "items": [],
        },
    )
    _write_json(
        root / "runtime_state" / "current_state.json",
        {
            "schema_version": "1",
            "runtime_id": "runtime-v2-demo",
            "run_id": "phase14e50-test",
            "state": "CURRENT_STATE_LOADED",
            "environment": "demo",
            "updated_at": "2026-07-09T00:00:00Z",
        },
    )
    for name in ("orders", "executions", "cash", "events"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    _write_jsonl(root / "persistent_ledger" / "positions.jsonl", [])
    _write_safety_decision(root)
    _write_broker_snapshot(root)
    _write_market_evidence(root)
    return root


def _write_policy(path: Path) -> Path:
    _write_json(
        path,
        {
            "policy_version": "capital_deployment_v1",
            "policy_source": str(path),
            "evaluation_capital": 1_000_000,
            "target_investment_ratio": 0.85,
            "cash_buffer": 0.05,
            "max_exposure": 850_000,
            "max_position_weight": 0.2,
            "max_positions": 5,
            "min_order_amount": 0,
            "max_buy_order_amount": None,
            "max_sell_liquidation_amount": None,
            "buy_notional_policy": "derived_from_capital_allocation_and_constraints",
            "sell_liquidation_policy": "current_owned_available_quantity_policy",
            "manual_review_threshold": {
                "buy_amount": None,
                "sell_liquidation_amount": None,
            },
        },
    )
    return path


def _position(symbol: str, *, quantity: float, price: float) -> dict:
    return {
        "symbol": symbol,
        "quantity": quantity,
        "average_price": price,
        "current_price": price,
        "market_value": quantity * price,
        "unrealized_pnl": 0.0,
        "holding_days": 12,
        "peak_return": 0.0,
        "source": "runtime_v2_runtime_owned_fill_projection",
        "as_of": "2026-07-09",
    }


def _write_pm_inputs(tmp_path: Path, *, symbols: tuple[str, ...]) -> tuple[Path, Path]:
    opportunity_path = tmp_path / "pm_opportunity.csv"
    pd.DataFrame(
        [
            {
                "target_date": "2026-07-09",
                "code": symbol,
                "expected_edge_score": -0.05,
                "buy_rank": 999,
                "downside_risk_score": 0.8,
                "risk_guard_status": "high_risk",
                "candidate_score": 0.1,
                "candidate_rank": 999,
                "buy_reason": "",
                "no_buy_reason": "",
                "calibration_policy_name": "phase14e50_pm_fixture",
            }
            for symbol in symbols
        ]
    ).to_csv(opportunity_path, index=False)
    feature_path = tmp_path / "pm_feature.csv"
    required_features = json.dumps(
        [
            "price_momentum_return_5d",
            "price_momentum_return_20d",
            "trend_close_over_ma_20d",
            "trend_ma_5_20_ratio",
            "volume_momentum_ratio_5d",
            "volatility_return_std_20d",
        ]
    )
    pd.DataFrame(
        [
            {
                "target_date": "2026-07-09",
                "as_of_date": "2026-07-09",
                "feature_as_of_date": "2026-07-09",
                "data_until": "2026-07-09",
                "code": symbol,
                "feature_version": "runtime_v2_pm_feature_input_v2_technical_complete",
                "price_momentum_return_5d": -0.05,
                "price_momentum_return_20d": -0.05,
                "trend_close_over_ma_20d": 0.95,
                "trend_ma_5_20_ratio": 0.95,
                "volume_momentum_ratio_5d": 1.0,
                "volatility_return_std_20d": 0.03,
                "feature_source_artifact": "phase14e50_fixture_candidate_features.parquet",
                "feature_source_hash": "phase14e50-fixture-feature-source-hash",
                "required_features": required_features,
                "optional_features": json.dumps(["no_position_reason"]),
                "missing_features": "[]",
                "defaulted_features": "[]",
                "temporal_validation_status": "PASS",
                "created_at": "2026-07-09T00:00:00Z",
            }
            for symbol in symbols
        ]
    ).to_csv(feature_path, index=False)
    return opportunity_path, feature_path


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_safety_decision(root: Path) -> Path:
    path = root / "runtime_state" / "safety" / "latest_safety_decision.json"
    _write_json(
        path,
        {
            "safety_decision_id": "safety-phase14e50-allow",
            "safety_policy_version": "safety_operation_guard_v1",
            "safety_source": str(path),
            "business_date": "2026-07-09",
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "phase14e50 fixture safety allow",
            "review_required": False,
            "block_buy": False,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": "2026-07-09T00:00:00+09:00",
            "expires_at": "2026-07-10T00:00:00+09:00",
        },
    )
    return path


def _write_broker_snapshot(root: Path) -> None:
    _write_json(
        root / "runtime_state" / "broker_readonly" / "2026-07-09" / "snapshot.json",
        {
            "schema_version": "runtime_v2_broker_readonly_snapshot_v1",
            "business_date": "2026-07-09",
            "generated_at": "2026-07-09T00:00:00Z",
            "broker_mode": "demo",
            "production_equivalent": False,
            "review_required": False,
            "positions": [],
            "orders": [],
            "executions": [],
        },
    )


def _write_market_evidence(root: Path) -> None:
    _write_json(
        root / "runtime_state" / "market" / "2026-07-09" / "market_evidence.json",
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "business_date": "2026-07-09",
            "generated_at": "2026-07-09T00:00:00Z",
            "market_summary": {"quote_count": 2},
            "quote_count": 2,
        },
    )


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
