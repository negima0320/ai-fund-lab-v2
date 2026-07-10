import json
from pathlib import Path

import pandas as pd
import pytest

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import (
    CapitalDeploymentPolicyError,
    load_capital_deployment_policy,
)


def test_phase15h_policy_loader_valid_preserves_policy_source(tmp_path):
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")

    policy = load_capital_deployment_policy(policy_path)

    assert policy.policy_version == "capital_deployment_v1"
    assert policy.policy_source == str(policy_path)
    assert policy.evaluation_capital == 1_000_000
    assert policy.max_positions == 5
    assert policy.max_buy_order_amount is None
    assert policy.manual_review_threshold.buy_amount is None
    assert policy.to_manifest_fields()["capital_deployment_policy_loaded"] is True
    assert policy.to_manifest_fields()["active_max_positions"] == 5
    assert policy.to_manifest_fields()["max_positions_source"] == str(policy_path)


def test_phase15h_policy_loader_missing_does_not_fallback(tmp_path):
    missing_path = tmp_path / "missing_policy.json"

    with pytest.raises(CapitalDeploymentPolicyError, match="missing"):
        load_capital_deployment_policy(missing_path)


def test_phase15h_policy_loader_incomplete_does_not_default(tmp_path):
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    del payload["max_positions"]
    policy_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(CapitalDeploymentPolicyError, match="max_positions"):
        load_capital_deployment_policy(policy_path)


def test_phase15h_cli_manifest_emits_explicit_policy_fields(tmp_path):
    runtime_root = _write_runtime_state(
        tmp_path / ".runtime",
        positions=[_position("3926", quantity=1000, price=351)],
    )
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    opportunity_path, feature_path = _write_pm_inputs(tmp_path, symbols=("3926",))

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

    manifest = _latest_manifest(runtime_root, "2026-07-09")
    policy_stage = next(stage for stage in manifest["stages"] if stage["name"] == "capital_deployment_policy")

    assert exit_code == 0
    assert manifest["capital_deployment_policy_loaded"] is True
    assert manifest["capital_deployment_policy_source"] == str(policy_path)
    assert manifest["capital_deployment_policy_version"] == "capital_deployment_v1"
    assert manifest["evaluation_capital"] == 1_000_000
    assert manifest["target_investment_ratio"] == 0.85
    assert manifest["cash_buffer"] == 0.05
    assert manifest["max_exposure"] == 850_000
    assert manifest["max_position_weight"] == 0.2
    assert manifest["active_max_positions"] == 5
    assert manifest["max_positions_source"] == str(policy_path)
    assert manifest["max_positions_policy_version"] == "capital_deployment_v1"
    assert manifest["max_buy_order_amount"] is None
    assert manifest["max_sell_liquidation_amount"] is None
    assert manifest["buy_notional_policy"] == "derived_from_capital_allocation_and_constraints"
    assert manifest["sell_liquidation_policy"] == "current_owned_available_quantity_policy"
    assert manifest["policy_validation_status"] == "PASS"
    assert manifest["policy_missing"] is False
    assert policy_stage["status"] == "PASS"
    assert policy_stage["details"]["active_max_positions"] == 5


def test_phase15h_cli_missing_policy_stops_runtime_guarded_job(tmp_path):
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
        ]
    )

    manifest = _latest_manifest(runtime_root, "2026-07-09")
    stage_names = {stage["name"] for stage in manifest["stages"]}

    assert exit_code == 20
    assert manifest["final_state"] == "REVIEW_REQUIRED"
    assert manifest["capital_deployment_policy_loaded"] is False
    assert manifest["policy_missing"] is True
    assert manifest["policy_validation_status"] == "POLICY_MISSING:--capital-deployment-policy is required"
    assert "sell_planning_pending_pipeline" not in stage_names


def _write_policy(path: Path) -> Path:
    payload = {
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
    }
    _write_json(path, payload)
    return path


def _write_runtime_state(root: Path, *, positions: list[dict]) -> Path:
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-phase15h",
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
            "pending_plan_id": "pending-phase15h-before",
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
            "run_id": "phase15h-test",
            "state": "CURRENT_STATE_LOADED",
            "environment": "demo",
            "updated_at": "2026-07-09T00:00:00Z",
        },
    )
    for name in ("orders", "executions", "cash", "events", "positions"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    _write_safety_decision(root)
    _write_broker_snapshot(root)
    return root


def _position(symbol: str, *, quantity: float, price: float) -> dict:
    return {
        "symbol": symbol,
        "quantity": quantity,
        "average_price": price,
        "market_value": quantity * price,
        "source": "runtime_v2_runtime_owned_fill_projection",
        "as_of": "2026-07-09",
        "current_price": price,
        "unrealized_pnl": 0.0,
        "holding_days": 12,
        "peak_return": 0.0,
    }


def _latest_manifest(runtime_root: Path, business_date: str):
    manifests = sorted((runtime_root / "runtime_state" / "run_manifest" / business_date).glob("*.json"))
    return json.loads(manifests[-1].read_text(encoding="utf-8"))


def _write_pm_inputs(tmp_path: Path, *, symbols: tuple[str, ...]) -> tuple[Path, Path]:
    opportunity_path = tmp_path / "pm_opportunity.csv"
    feature_path = tmp_path / "pm_feature.csv"
    pd.DataFrame(
        [
            {
                "target_date": "2026-07-09",
                "code": symbol,
                "expected_edge": 0.10,
                "expected_edge_score": 0.10,
                "confidence": 0.90,
                "liquidity_score": 0.80,
                "buy_rank": 999,
                "downside_risk_score": 0.20,
            }
            for symbol in symbols
        ]
    ).to_csv(opportunity_path, index=False)
    pd.DataFrame(
        [
            {
                "target_date": "2026-07-09",
                "code": symbol,
                "atr_20": 10.0,
                "volatility_20d": 0.20,
                "drawdown_20d": -0.02,
                "rsi_14": 55.0,
                "trend_score": 0.70,
                "downside_risk": 0.30,
            }
            for symbol in symbols
        ]
    ).to_csv(feature_path, index=False)
    return opportunity_path, feature_path


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_safety_decision(root: Path) -> Path:
    path = root / "runtime_state" / "safety" / "latest_safety_decision.json"
    _write_json(
        path,
        {
            "safety_decision_id": "safety-phase15h-allow",
            "safety_policy_version": "safety_operation_guard_v1",
            "safety_source": str(path),
            "business_date": "2026-07-09",
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "phase15h fixture safety allow",
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


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
