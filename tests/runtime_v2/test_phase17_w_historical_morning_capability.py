import json
from pathlib import Path

import pandas as pd
import pytest

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import _write_morning_manifest_evidence
from ai_fund_lab_v2.runtime_v2.market_refresh.consumer_readiness import CANDIDATE_REQUIRED_COLUMNS, OPPORTUNITY_REQUIRED_COLUMNS
from ai_fund_lab_v2.runtime_v2.planning.models import AIPlanningSignal
from ai_fund_lab_v2.runtime_v2.planning.morning_pipeline import (
    evaluate_morning_capability,
    run_morning_ai_planning_pending_pipeline,
)
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import ManualReviewThreshold, CapitalDeploymentPolicy
from ai_fund_lab_v2.runtime_v2.safety_decision import RuntimeSafetyDecision, safety_allows_action


BUSINESS_DATE = "2026-07-06"


@pytest.mark.parametrize(
    ("override", "failed_check"),
    [
        ({"broker_write": True}, "broker_write_false"),
        ({"external_delivery": True}, "external_delivery_false"),
        ({"tachibana_demo_write": True}, "tachibana_demo_write_false"),
        ({"tachibana_production_write": True}, "tachibana_production_write_false"),
        ({"submit_enabled": True}, "submit_enabled_false"),
        ({"broker_environment": "tachibana_demo"}, "broker_environment_historical_simulated"),
    ],
)
def test_phase17_w_historical_morning_capability_fails_closed(override, failed_check, tmp_path):
    context = {**_historical_context(tmp_path), **override}

    decision = evaluate_morning_capability(mode="historical", context=context)

    assert decision.status == "BLOCKED"
    assert failed_check in decision.failed_checks


def test_phase17_w_historical_morning_capability_does_not_require_runtime_test_identity(tmp_path):
    context = {**_historical_context(tmp_path), "runtime_test_run_id": "", "runtime_test_evidence_root": ""}

    decision = evaluate_morning_capability(mode="historical", context=context)

    assert decision.status == "PASS"


def test_phase17_w_demo_morning_capability_regression_is_unchanged():
    decision = evaluate_morning_capability(mode="demo", context=None)

    assert decision.status == "PASS"
    assert decision.reason == "demo_morning_capability_ready"


def test_phase17_w_historical_safety_allows_replay_planning_and_blocks_submit():
    decision = _historical_safety()

    assert safety_allows_action(decision, action="planning", side="BUY")[0] is True
    assert safety_allows_action(decision, action="submit", side="BUY")[0] is False


def test_phase17_w_morning_evidence_is_run_scoped_even_when_planning_not_reached(tmp_path):
    evidence_root = tmp_path / "reports" / "runtime_tests" / "runs" / "actual-run"
    manifest_path = tmp_path / ".runtime" / "runtime_state" / "run_manifest" / BUSINESS_DATE / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text("{}", encoding="utf-8")
    manifest = {
        "mode": "historical",
        "errors": ["historical_morning_capability_fail_closed:broker_write_false"],
        "warnings": [],
        "prohibited_actions": {
            "demo_submit_executed": False,
            "production_order_executed": False,
            "notification_sent": False,
            "phase9_runtime_called": False,
            "phase9_writer_called": False,
            "mode_rooted_current_used": False,
        },
        "stages": [
            {
                "name": "environment_capability_decision",
                "status": "BLOCKED",
                "message": "capability blocked",
                "details": {"reason": "historical_morning_capability_fail_closed:broker_write_false"},
            }
        ],
    }

    _write_morning_manifest_evidence(
        evidence_root=evidence_root,
        business_date=BUSINESS_DATE,
        manifest_path=manifest_path,
        manifest=manifest,
    )
    morning_dir = evidence_root / "daily" / BUSINESS_DATE / "morning"

    assert (morning_dir / "morning_manifest.json").is_file()
    assert json.loads((morning_dir / "environment_capability_decision.json").read_text())["status"] == "BLOCKED"
    assert json.loads((morning_dir / "planning_evidence.json").read_text())["status"] == "NOT_EXECUTED"
    assert json.loads((morning_dir / "pending_generation_evidence.json").read_text())["status"] == "NOT_EXECUTED"
    assert json.loads((morning_dir / "external_effect_audit.json").read_text())["status"] == "PASS"


def _historical_context(tmp_path: Path) -> dict:
    return {
        "runtime_mode": "historical",
        "broker_environment": "historical_simulated",
        "historical_replay": True,
        "simulation": True,
        "broker_write": False,
        "external_delivery": False,
        "tachibana_demo_write": False,
        "tachibana_production_write": False,
        "submit_enabled": False,
        "runtime_test_run_id": "runtime-test-historical-smoke-fixture",
        "runtime_test_profile_id": "historical-smoke",
        "runtime_test_evidence_root": str(tmp_path / "reports" / "runtime_tests" / "runs" / "runtime-test-historical-smoke-fixture"),
    }


def _historical_safety() -> RuntimeSafetyDecision:
    return RuntimeSafetyDecision(
        safety_decision_id="",
        safety_policy_version="historical_replay_neutral_safety_v1",
        safety_source="data_readiness_historical_temporal_authority",
        business_date=BUSINESS_DATE,
        runtime_mode="historical",
        decision="ALLOW",
        reason="historical_neutral_no_event_safety_ready",
        review_required=False,
        block_buy=False,
        block_sell=False,
        block_submit=True,
        halt_runtime=False,
        emergency_stop=False,
        generated_at="",
        expires_at="",
        safety_status="PASS",
        action_permissions={
            "buy_planning": "ALLOWED_FOR_REPLAY",
            "buy_submit": "BLOCKED",
            "broker_write": "BLOCKED",
        },
        human_review_artifact_refs=[],
        artifact_path="",
    )


def _policy(tmp_path: Path) -> CapitalDeploymentPolicy:
    return CapitalDeploymentPolicy(
        policy_version="capital_deployment_v1",
        policy_source=str(tmp_path / "policy.json"),
        evaluation_capital=1_000_000,
        max_positions=5,
        min_order_amount=0,
        max_buy_order_amount=None,
        max_sell_liquidation_amount=None,
        buy_notional_policy="derived_from_capital_allocation_and_constraints",
        sell_liquidation_policy="current_owned_available_quantity_policy",
        manual_review_threshold=ManualReviewThreshold(buy_amount=None, sell_liquidation_amount=None),
        loaded_from=str(tmp_path / "policy.json"),
    )


def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-phase17w",
            "environment": "historical",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": BUSINESS_DATE,
            "business_date": BUSINESS_DATE,
            "positions": [],
            "cash": 1_000_000,
            "buying_power": 1_000_000,
            "market_value": 0,
            "total_equity": 1_000_000,
            "review_required": False,
            "current_state_confirmed_empty": True,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
        },
    )
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"state": "CONSUMED", "environment": "historical", "items": []})
    return root


def _feature_root(runtime_root: Path, feature_date: str) -> Path:
    feature_root = runtime_root / "operations" / "feature_artifacts"
    feature_dir = feature_root / feature_date
    feature_dir.mkdir(parents=True)
    candidate = {column: _value(column, feature_date) for column in CANDIDATE_REQUIRED_COLUMNS}
    opportunity = {column: _value(column, feature_date) for column in OPPORTUNITY_REQUIRED_COLUMNS}
    pd.DataFrame([candidate]).to_parquet(feature_dir / "candidate_features.parquet", index=False)
    pd.DataFrame([opportunity]).to_parquet(feature_dir / "opportunity_feature_input.parquet", index=False)
    pd.DataFrame(columns=["target_date", "code", "no_position_reason"]).to_parquet(
        feature_dir / "position_feature_input.parquet",
        index=False,
    )
    pd.DataFrame([{"target_date": feature_date, "code": "__POLICY_INPUT__"}]).to_parquet(
        feature_dir / "capital_policy_input.parquet",
        index=False,
    )
    _write_json(
        runtime_root / "operations" / "feature_date_contract" / f"{feature_date}.json",
        {
            "status": "PASS",
            "reason": "requested_feature_artifacts_available",
            "requested_feature_date": feature_date,
            "selected_feature_date": feature_date,
            "latest_available_market_date": feature_date,
            "carryover_used": False,
            "carryover_reason": "",
            "freshness_lag_business_days": 0,
            "freshness_limit_business_days": 1,
            "feature_artifact_dir": str(feature_dir),
            "generated_feature_artifacts": {},
            "missing_feature_artifacts": [],
            "requested_feature_artifact_dir": str(feature_dir),
            "requested_missing_feature_artifacts": [],
            "price_source_alignment": "selected_feature_date",
            "consumer_ready": True,
            "schema_version": "runtime_v2_feature_contract_v2",
            "candidate_schema_status": "READY",
            "candidate_missing_columns": [],
            "opportunity_schema_status": "READY",
            "pm_schema_status": "READY",
        },
    )
    price_dir = runtime_root / "operations" / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily"
    price_dir.mkdir(parents=True)
    pd.DataFrame([{"Code": "7203", "Date": feature_date, "Close": 1000.0, "PriceSource": "fixture"}]).to_parquet(
        price_dir / "data.parquet",
        index=False,
    )
    return feature_root


def _value(column: str, feature_date: str):
    if column == "target_date":
        return feature_date
    if column == "code":
        return "7203"
    if column.startswith("missing_flags_") or column.endswith("_flag") or column.endswith("_context"):
        return False
    return 1.0


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
