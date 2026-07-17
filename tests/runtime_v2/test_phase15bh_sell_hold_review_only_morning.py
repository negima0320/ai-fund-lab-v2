from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from tests.runtime_v2.test_phase15aq_runtime_data_readiness_gate import (
    BUSINESS_DATE,
    _load_json,
    _write_feature_inputs,
    _runtime_root,
    _write_broker_snapshot,
    _write_json,
    _write_policy,
)
from tests.runtime_v2.feature_date_contract_helpers import materialize_feature_date_contract
from tests.runtime_v2.test_phase15bg_human_safety_review_4591 import (
    _write_feature_readiness,
    _write_high_risk_safety_decision,
    _write_human_review,
    _write_safety_report,
)


def test_phase15bh_cli_generates_sell_hold_review_only_outputs_without_buy_submit_or_broker_write(tmp_path):
    runtime_root = _review_only_runtime_with_4591(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment.json")
    before_pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "sell_hold_review_only_morning",
            "--business-date",
            BUSINESS_DATE,
            "--feature-date",
            BUSINESS_DATE,
            "--feature-root",
            str(runtime_root / "operations" / "feature_artifacts"),
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

    manifest = _latest_manifest(runtime_root, BUSINESS_DATE)
    stage_names = {stage["name"] for stage in manifest["stages"]}
    pending_after = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    review_output = _load_json(Path(manifest["review_output_path"]))
    review_pending = _load_json(Path(manifest["review_pending_path"]))

    assert exit_code == 0
    assert "candidate_opportunity_ai_runtime_producer" not in stage_names
    assert "morning_ai_planning_pending_pipeline" not in stage_names
    assert "runtime_v2_submit_pipeline" not in stage_names
    assert "sell_hold_review_only_morning" in stage_names
    assert pending_after == before_pending
    assert review_output["status"] == "READY"
    assert review_output["issue_code"] == "4591"
    assert review_output["prohibited_actions"]["buy_inference_executed"] is False
    assert review_output["prohibited_actions"]["submit_executed"] is False
    assert review_output["prohibited_actions"]["broker_write_performed"] is False
    assert review_pending["pending_type"] == "SELL_HOLD_REVIEW_ONLY"
    assert review_pending["submit_allowed"] is False
    assert review_pending["broker_write_allowed"] is False
    assert review_pending["authoritative_submit_pending"] is False


def test_phase15bh_pm_ai_marks_4591_as_review_sell_candidate(tmp_path):
    runtime_root = _review_only_runtime_with_4591(tmp_path)

    from ai_fund_lab_v2.runtime_v2.review_only.sell_hold_morning import run_sell_hold_review_only_morning

    result = run_sell_hold_review_only_morning(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        feature_date=BUSINESS_DATE,
    )
    review_output = _load_json(Path(result.review_output_path))

    assert result.status == "PASS"
    assert review_output["pm_status"] == "PASS"
    assert any(item["issue_code"] == "4591" for item in review_output["sell_candidates"])
    candidate_4591 = next(item for item in review_output["sell_candidates"] if item["issue_code"] == "4591")
    assert candidate_4591["pm_decision"] == "EXIT"
    assert candidate_4591["runtime_sell_quantity"] == 5000
    assert review_output["safety"]["action_permissions"]["sell_planning"] == "ALLOWED_FOR_REVIEW"
    assert review_output["safety"]["action_permissions"]["broker_write"] == "BLOCKED"


def _review_only_runtime_with_4591(tmp_path: Path) -> Path:
    runtime_root = _runtime_root(
        tmp_path,
        business_date=BUSINESS_DATE,
        current_as_of=BUSINESS_DATE,
        positions=[
            {
                "symbol": "4591",
                "quantity": 5000,
                "average_price": 101,
                "current_price": 74,
                "market_value": 370000,
                "unrealized_pnl": -135000,
                "source": "runtime_v2_runtime_owned_fill_projection",
                "as_of": BUSINESS_DATE,
                "holding_days": 1,
                "peak_return": 0.0,
            }
        ],
    )
    _write_broker_snapshot(runtime_root)
    _write_feature_inputs(runtime_root / "operations" / "feature_artifacts", feature_date=BUSINESS_DATE)
    pd.DataFrame(
        [
            {
                "target_date": BUSINESS_DATE,
                "position_state_as_of": BUSINESS_DATE,
                "entry_date": BUSINESS_DATE,
                "code": "4591",
                "broker_issue_code": "4591",
                "holding_days": 1,
                "average_price": 101.0,
                "current_price": 74.0,
                "unrealized_return": -0.26732673267326734,
                "quantity": 5000,
                "feature_version": "runtime_v2_pm_review_only_feature_context_v1",
                "data_until": BUSINESS_DATE,
                "created_at": BUSINESS_DATE + "T00:00:00Z",
                "no_position_reason": "",
            }
        ]
    ).to_parquet(
        runtime_root / "operations" / "feature_artifacts" / BUSINESS_DATE / "position_feature_input.parquet",
        index=False,
    )
    _write_feature_readiness(runtime_root)
    _write_json(
        runtime_root / "operations" / "feature_consumer_readiness" / f"{BUSINESS_DATE}.json",
        {
            "schema_version": "runtime_v2_feature_contract_v1",
            "feature_date": BUSINESS_DATE,
            "consumer_ready": True,
            "status": "READY",
            "reason": "consumer_feature_schema_ready",
            "candidate_schema_status": "READY",
            "opportunity_schema_status": "READY",
            "pm_schema_status": "READY",
        },
    )
    materialize_feature_date_contract(runtime_root, business_date=BUSINESS_DATE, selected_feature_date=BUSINESS_DATE)
    _write_high_risk_safety_decision(runtime_root)
    _write_safety_report(tmp_path, event_id="safety-event-4591")
    _write_human_review(runtime_root, event_id="safety-event-4591", expires_at="2026-12-31T00:00:00+00:00")
    _write_json(
        runtime_root / "operations" / "feature_artifacts" / BUSINESS_DATE / "position_feature_input.parquet.placeholder.json",
        {"note": "review-only runner builds normalized PM contexts from Current"},
    )
    return runtime_root


def _latest_manifest(runtime_root: Path, business_date: str) -> dict:
    manifests = sorted((runtime_root / "runtime_state" / "run_manifest" / business_date).glob("*.json"))
    return _load_json(manifests[-1])
