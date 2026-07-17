from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from ai_fund_lab_v2.runtime_v2.position_management.producer import (
    ARTIFACT_SCHEMA_VERSION,
    load_sell_exit_decisions_from_pm_artifact,
    produce_position_management_decisions,
)
from ai_fund_lab_v2.runtime_v2.report.public_report_writer import generate_public_report_from_current


BUSINESS_DATE = "2026-07-09"


def test_phase15af_pm_artifact_generation_and_sell_planning_reads_it(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522", quantity=100, average_price=1000, current_price=850)])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522",), expected_edge=-0.05, downside=0.8)

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = json.loads(Path(result.artifact_path).read_text(encoding="utf-8"))
    decisions = load_sell_exit_decisions_from_pm_artifact(result.artifact_path)

    assert result.status == "PASS"
    assert artifact["schema_version"] == ARTIFACT_SCHEMA_VERSION
    assert artifact["model_version"] == "position_management_policy_phase6a_v1"
    assert artifact["decision_count"] == 1
    assert artifact["exit_count"] == 1
    assert artifact["decisions"][0]["decision"] == "EXIT"
    assert decisions[0].symbol == "6522"
    assert decisions[0].quantity == 100


def test_phase15af_cli_sell_planning_uses_pm_artifact_not_current_liquidation(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522", quantity=100, average_price=1000, current_price=1100)])
    policy_path = _write_policy(tmp_path / "capital_deployment.json")
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522",), expected_edge=0.10, downside=0.3, buy_rank=999)

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "sell_planning",
            "--business-date",
            BUSINESS_DATE,
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
    manifest = _latest_manifest(runtime_root)
    pending = json.loads((runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))

    pm_artifact = json.loads(Path(manifest["pm_artifact_path"]).read_text(encoding="utf-8"))

    assert exit_code == 0
    assert manifest["pm_decision_count"] == 1
    assert manifest["pm_hold_count"] == 1
    assert manifest["pm_exit_count"] == 0
    assert pm_artifact["decisions"][0]["decision"] == "HOLD"
    assert pending["items"] == []
    assert "runtime_v2_sell_planning_current_position_exit" not in json.dumps(manifest)


def test_phase15af_current_liquidation_and_pm_decision_are_not_mixed(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522", quantity=100, average_price=1000, current_price=1100)])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522",), expected_edge=0.10, downside=0.3, buy_rank=999)

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = json.loads(Path(result.artifact_path).read_text(encoding="utf-8"))

    assert artifact["current_liquidation_contract"].startswith("Runtime cleanup")
    assert artifact["decisions"][0]["decision"] == "HOLD"
    assert artifact["decisions"][0]["runtime_sell_quantity"] == 0


def test_phase15af_cli_requires_pm_artifact_and_does_not_sell_from_current_only(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522", quantity=100, average_price=1000, current_price=850)])
    policy_path = _write_policy(tmp_path / "capital_deployment.json")

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "sell_planning",
            "--business-date",
            BUSINESS_DATE,
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
        ]
    )
    manifest = _latest_manifest(runtime_root)
    pending = json.loads((runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))
    stage_names = {stage["name"] for stage in manifest["stages"]}

    assert exit_code == 20
    assert manifest["final_state"] == "REVIEW_REQUIRED"
    assert manifest["pm_status"] == "REVIEW_REQUIRED"
    assert "position_management_ai_runtime_producer" not in stage_names
    assert "sell_planning_pending_pipeline" not in stage_names
    assert pending["items"] == []


def test_phase15af_exit_flows_to_sell_pending(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522", quantity=100, average_price=1000, current_price=850)])
    policy_path = _write_policy(tmp_path / "capital_deployment.json")
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522",), expected_edge=-0.05, downside=0.8)

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "sell_planning",
            "--business-date",
            BUSINESS_DATE,
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
    pending = json.loads((runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert pending["items"][0]["symbol"] == "6522"
    assert pending["items"][0]["side"] == "SELL"
    assert pending["items"][0]["quantity"] == 100


def test_phase15af_report_and_notification_include_position_management_summary(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522", quantity=100, average_price=1000, current_price=850)])
    policy_path = _write_policy(tmp_path / "capital_deployment.json")
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522",), expected_edge=-0.05, downside=0.8)
    main(
        [
            "--mode",
            "demo",
            "--job",
            "sell_planning",
            "--business-date",
            BUSINESS_DATE,
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

    result = generate_public_report_from_current(
        runtime_root=runtime_root,
        runtime_output_dir=tmp_path / "reports" / "runtime_v2" / BUSINESS_DATE,
        public_output_dir=tmp_path / "reports" / "public" / "runtime_v2" / BUSINESS_DATE,
        business_date=BUSINESS_DATE,
    )
    runtime_report = Path(result["runtime_report_md"]).read_text(encoding="utf-8")
    payload = json.loads(Path(result["notification_payload_json"]).read_text(encoding="utf-8"))

    assert "## Position Management Decision" in runtime_report
    assert "## Why HOLD" in runtime_report
    assert "## Why EXIT" in runtime_report
    assert "EXIT 1, HOLD 0" in runtime_report
    assert payload["position_management_summary"].startswith("EXIT 1, HOLD 0")


def _runtime_root(tmp_path: Path, *, positions: list[dict]) -> Path:
    root = tmp_path / ".runtime"
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-phase15af",
            "environment": "demo",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": BUSINESS_DATE,
            "updated_at": BUSINESS_DATE + "T00:00:00Z",
            "positions": positions,
            "cash": 500000,
            "buying_power": 500000,
            "market_value": sum(float(item["market_value"]) for item in positions),
            "total_equity": 500000 + sum(float(item["market_value"]) for item in positions),
            "review_required": False,
            "current_state_confirmed_empty": False,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
        },
    )
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"state": "CONSUMED", "environment": "demo", "items": []})
    _write_json(
        root / "runtime_state" / "current_state.json",
        {
            "schema_version": "1",
            "runtime_id": "runtime-v2-demo",
            "run_id": "phase15af-test",
            "state": "CURRENT_STATE_LOADED",
            "environment": "demo",
            "updated_at": BUSINESS_DATE + "T00:00:00Z",
        },
    )
    for name in ("orders", "executions", "cash", "events", "positions"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    _write_safety_decision(root)
    _write_broker_snapshot(root)
    _write_market_evidence(root)
    return root


def _position(symbol: str, *, quantity: float, average_price: float, current_price: float) -> dict:
    return {
        "symbol": symbol,
        "quantity": quantity,
        "average_price": average_price,
        "current_price": current_price,
        "market_value": quantity * current_price,
        "holding_days": 12,
        "peak_return": max((current_price / average_price) - 1.0, 0.0),
        "source": "runtime_v2_runtime_owned_fill_projection",
        "as_of": BUSINESS_DATE,
    }


def _pm_inputs(
    tmp_path: Path,
    *,
    symbols: tuple[str, ...],
    expected_edge: float,
    downside: float,
    buy_rank: int = 999,
) -> tuple[Path, Path]:
    rows = [
        {
            "target_date": BUSINESS_DATE,
            "code": symbol,
            "expected_edge_score": expected_edge,
            "buy_rank": buy_rank,
            "downside_risk_score": downside,
            "risk_guard_status": "ok" if downside < 0.7 else "high_risk",
            "candidate_score": 0.5,
            "candidate_rank": buy_rank,
            "buy_reason": "",
            "no_buy_reason": "",
            "calibration_policy_name": "fixture",
        }
        for symbol in symbols
    ]
    opportunity_path = tmp_path / "pm_opportunity.csv"
    pd.DataFrame(rows).to_csv(opportunity_path, index=False)
    feature_path = tmp_path / "pm_feature.csv"
    pd.DataFrame(
        [
            {
                "target_date": BUSINESS_DATE,
                "as_of_date": BUSINESS_DATE,
                "code": symbol,
                "feature_version": "position_management_feature_v1",
                "return_5d": expected_edge,
                "return_20d": expected_edge,
                "close_over_ma_20d": expected_edge,
                "ma_5_20_ratio": 1.0 + expected_edge,
                "volume_ratio_5d": 1.0,
                "volatility_20d": 0.02,
            }
            for symbol in symbols
        ]
    ).to_csv(feature_path, index=False)
    return opportunity_path, feature_path


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
            "manual_review_threshold": {"buy_amount": None, "sell_liquidation_amount": None},
        },
    )
    return path


def _write_safety_decision(root: Path) -> Path:
    path = root / "runtime_state" / "safety" / "latest_safety_decision.json"
    _write_json(
        path,
        {
            "safety_decision_id": "safety-phase15af-allow",
            "safety_policy_version": "safety_operation_guard_v1",
            "safety_source": str(path),
            "business_date": BUSINESS_DATE,
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "phase15af fixture safety allow",
            "review_required": False,
            "block_buy": False,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": BUSINESS_DATE + "T00:00:00+09:00",
            "expires_at": "2026-07-10T00:00:00+09:00",
        },
    )
    return path


def _write_broker_snapshot(root: Path) -> None:
    _write_json(
        root / "runtime_state" / "broker_readonly" / BUSINESS_DATE / "snapshot.json",
        {
            "schema_version": "runtime_v2_broker_readonly_snapshot_v1",
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T00:00:00Z",
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
        root / "runtime_state" / "market" / BUSINESS_DATE / "market_evidence.json",
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T00:00:00Z",
            "market_summary": {"quote_count": 1},
            "quote_count": 1,
        },
    )


def _latest_manifest(runtime_root: Path) -> dict:
    manifests = sorted((runtime_root / "runtime_state" / "run_manifest" / BUSINESS_DATE).glob("*.json"))
    return json.loads(manifests[-1].read_text(encoding="utf-8"))


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")
