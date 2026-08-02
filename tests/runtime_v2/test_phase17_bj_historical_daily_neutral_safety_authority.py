from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.runtime_v2.data_readiness import evaluate_runtime_data_readiness
from ai_fund_lab_v2.runtime_v2.market_refresh.consumer_readiness import (
    CANDIDATE_REQUIRED_COLUMNS,
    OPPORTUNITY_REQUIRED_COLUMNS,
)


BUSINESS_DATE = "2026-07-08"
PREVIOUS_DATE = "2026-07-07"
RUN_ID = "runtime-test-historical-smoke-fixture-bj"
PROFILE_ID = "historical-smoke"


class FixtureModel:
    pass


def test_phase17_bj_previous_empty_pending_resolves_daily_historical_neutral_safety(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path, mode="historical", pending=_empty_pending(target_date=PREVIOUS_DATE))

    result = _evaluate(tmp_path, root, mode="historical", broker_environment="historical_simulated")

    assert result.status == "READY"
    assert result.payload["pending_status"] == "READY"
    assert result.payload["safety_status"] == "READY"
    assert result.payload["previous_empty_pending_present"] is True
    assert result.payload["previous_empty_pending_ignored_as_safety_authority"] is True
    assert result.payload["historical_neutral_authority_generated_or_resolved"] is True
    assert result.payload["safety_authority_type"] == "HISTORICAL_DAILY_NEUTRAL"
    assert result.payload["safety_authority_business_date"] == BUSINESS_DATE
    safety = result.payload["components"]["safety"]
    assert safety["pending_safety_authority"]["status"] == "REVIEW_REQUIRED"
    assert safety["pending_safety_authority"]["target_session_date"] == PREVIOUS_DATE
    assert safety["historical_safety_temporal_authority"] == "historical_initial_no_external_effect"
    assert safety["broker_write"] is False
    assert safety["external_delivery"] is False
    assert safety["runtime_test_run_id"] == RUN_ID


def test_phase17_bj_same_day_empty_pending_context_still_authorizes_same_day_no_action(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path, mode="historical", pending=_empty_pending(target_date=BUSINESS_DATE))

    result = _evaluate(tmp_path, root, mode="historical", broker_environment="historical_simulated")

    assert result.status == "READY"
    safety = result.payload["components"]["safety"]
    assert result.payload["previous_empty_pending_present"] is False
    assert safety["historical_neutral_authority_generated_or_resolved"] is False
    assert safety["safety_authority_type"] == "HISTORICAL_PENDING_SAFETY_CONTEXT"
    assert safety["safety_authority_business_date"] == BUSINESS_DATE
    assert safety["pending_safety_authority"]["status"] == "READY"
    assert safety["pending_safety_authority"]["reason"] == "historical_no_action_pending_safety_authority_ready"


def test_phase17_bj_active_pending_safety_date_mismatch_remains_review_required(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path, mode="historical", pending=_active_pending(target_date=PREVIOUS_DATE))

    result = _evaluate(tmp_path, root, mode="historical", broker_environment="historical_simulated")

    assert result.status == "REVIEW_REQUIRED"
    assert result.payload["safety_status"] == "REVIEW_REQUIRED"
    assert "historical_safety_temporal_authority_missing" in result.payload["review_reasons"]
    assert result.payload["components"]["safety"]["historical_neutral_authority_generated_or_resolved"] is False
    assert "pending_lifecycle_state" in result.payload["components"]["safety"]["mismatched_fields"]


def test_phase17_bj_approved_pending_safety_mismatch_remains_review_required(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path, mode="historical", pending=_approved_pending(target_date=PREVIOUS_DATE))

    result = _evaluate(tmp_path, root, mode="historical", broker_environment="historical_simulated")

    assert result.status == "REVIEW_REQUIRED"
    assert result.payload["pending_status"] == "REVIEW_REQUIRED"
    assert "stale_approved_pending_exists" in result.payload["review_reasons"]
    assert result.payload["components"]["safety"]["historical_neutral_authority_generated_or_resolved"] is False


def test_phase24_ih_same_day_failed_attempt_pending_does_not_block_daily_neutral_safety(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path, mode="historical", pending=_failed_same_day_strategy_pending())

    result = _evaluate(tmp_path, root, mode="historical", broker_environment="historical_simulated")

    assert result.status == "READY"
    safety = result.payload["components"]["safety"]
    pending = result.payload["components"]["pending"]
    retry = safety["failed_attempt_pending_retry"]
    assert safety["historical_neutral_authority_generated_or_resolved"] is True
    assert safety["historical_neutral_safety_resolution_status"] == "READY"
    assert safety["historical_neutral_safety_resolution_reason"] == "historical_daily_neutral_safety_authority_ready"
    assert safety["historical_safety_temporal_authority"] == "historical_initial_no_external_effect"
    assert retry["pending_artifact_retry_eligibility"] == "RETRY_INPUT_INELIGIBLE"
    assert retry["pending_artifact_authority_eligibility"] == "AUTHORITY_INELIGIBLE"
    assert retry["pending_artifact_attempt_status"] == "BLOCKED"
    assert retry["failed_attempt_artifact_quarantined"] is True
    assert pending["failed_attempt_pending_retry"]["reason"] == "failed_attempt_pending_retry_input_ineligible"
    assert "historical_safety_temporal_authority_missing" not in result.payload["review_reasons"]


def test_phase24_ij_same_day_empty_unscoped_review_pending_is_retry_ineligible(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path, mode="historical", pending=_failed_same_day_empty_unscoped_review_pending())

    result = _evaluate(tmp_path, root, mode="historical", broker_environment="historical_simulated")

    assert result.status == "READY"
    safety = result.payload["components"]["safety"]
    pending = result.payload["components"]["pending"]
    retry = pending["failed_attempt_pending_retry"]
    assert pending["status"] == "READY"
    assert pending["reason"] == "failed_attempt_pending_retry_input_ineligible"
    assert safety["historical_neutral_authority_generated_or_resolved"] is True
    assert retry["pending_artifact_retry_eligibility"] == "RETRY_INPUT_INELIGIBLE"
    assert retry["pending_artifact_authority_eligibility"] == "AUTHORITY_INELIGIBLE"
    assert retry["pending_artifact_attempt_status"] == "REVIEW_REQUIRED"
    assert retry["review_required_empty_unscoped_failed_attempt"] is True
    assert retry["safety_context_complete"] is True
    assert retry["planning_authority_complete"] is True
    assert "pending_review_required" not in result.payload["review_reasons"]
    assert "historical_safety_temporal_authority_missing" not in result.payload["review_reasons"]


def test_phase24_ih_blocked_pending_with_items_remains_fail_closed(tmp_path: Path) -> None:
    blocked = _failed_same_day_strategy_pending()
    blocked["items"] = [{"pending_item_id": "blocked-buy-1", "symbol": "81050", "side": "BUY", "quantity": 100}]
    root = _runtime_root(tmp_path, mode="historical", pending=blocked)

    result = _evaluate(tmp_path, root, mode="historical", broker_environment="historical_simulated")

    assert result.status == "REVIEW_REQUIRED"
    assert "historical_safety_temporal_authority_missing" in result.payload["review_reasons"]
    assert result.payload["components"]["safety"]["historical_neutral_authority_generated_or_resolved"] is False


def test_phase17_bj_production_and_demo_missing_safety_still_review_required(tmp_path: Path) -> None:
    for mode, broker_environment in (("production", "production"), ("demo", "demo")):
        root = _runtime_root(tmp_path / mode, mode=mode, pending=_empty_pending(target_date=BUSINESS_DATE, mode=mode))

        result = _evaluate(tmp_path / mode, root, mode=mode, broker_environment=broker_environment)

        assert result.status == "REVIEW_REQUIRED"
        assert result.payload["safety_status"] == "REVIEW_REQUIRED"
        assert result.payload["components"]["safety"]["reason"] == "safety decision evidence missing"
        assert "safety_decision" in result.payload["components"]["safety"]["missing_evidence"]
        assert not result.payload["historical_neutral_authority_generated_or_resolved"]


def test_phase17_bj_historical_external_effects_fail_closed(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path, mode="historical", pending=_empty_pending(target_date=PREVIOUS_DATE))

    result = _evaluate(
        tmp_path,
        root,
        mode="historical",
        broker_environment="historical_simulated",
        broker_write=True,
    )

    assert result.status == "HALT"
    assert result.payload["safety_status"] == "REVIEW_REQUIRED"
    assert result.payload["historical_neutral_authority_generated_or_resolved"] is False
    assert "historical_external_effect_forbidden" in result.payload["halt_reasons"]


def _evaluate(
    tmp_path: Path,
    root: Path,
    *,
    mode: str,
    broker_environment: str,
    broker_write: bool = False,
    external_delivery: bool = False,
):
    return evaluate_runtime_data_readiness(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode=mode,
        readiness_scope="morning",
        feature_root=root / "operations" / "feature_artifacts",
        feature_date=BUSINESS_DATE,
        candidate_model_path=_write_model(tmp_path / "candidate.pkl"),
        opportunity_model_path=_write_model(tmp_path / "opportunity.pkl"),
        broker_environment=broker_environment,
        runtime_test_evidence_root=_evidence_root(tmp_path),
        runtime_test_run_id=RUN_ID,
        runtime_test_profile_id=PROFILE_ID,
        broker_write=broker_write,
        external_delivery=external_delivery,
    )


def _runtime_root(tmp_path: Path, *, mode: str, pending: dict[str, Any]) -> Path:
    root = tmp_path / ".runtime"
    pending = dict(pending)
    safety_context = dict(pending.get("safety_context") or {})
    if safety_context:
        safety_context["runtime_test_evidence_root"] = str(_evidence_root(tmp_path))
        pending["safety_context"] = safety_context
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "runtime_v2_current_temporal_v1",
            "temporal_schema_version": "runtime_v2_current_temporal_v1",
            "environment": mode,
            "business_date": PREVIOUS_DATE,
            "position_state_as_of": PREVIOUS_DATE,
            "valuation_as_of": PREVIOUS_DATE,
            "source_market_date": PREVIOUS_DATE,
            "positions": [{"symbol": "81050", "quantity": 100, "average_price": 100}],
            "cash": 900000,
            "buying_power": 900000,
            "market_value": 10000,
            "total_equity": 910000,
            "review_required": False,
            "current_state_confirmed_empty": False,
            "current_positions_unknown": False,
        },
    )
    _write_json(
        root / "runtime_state" / "current_state.json",
        {
            "schema_version": "runtime_v2_operation_state_v1",
            "role": "authoritative_runtime_operation_state",
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T08:00:00+09:00",
            "updated_at": BUSINESS_DATE + "T08:00:00+09:00",
            "environment": mode,
            "runtime_mode": mode,
            "state": "CURRENT_STATE_LOADED",
            "safety_state": "NORMAL",
            "current_safety_state": "NORMAL",
            "source": "runtime_v2_runtime_state_producer",
            "asset_state_is_authoritative_here": False,
            "pending_state_is_authoritative_here": False,
        },
    )
    _write_json(
        root / "runtime_state" / "market" / BUSINESS_DATE / "market_evidence.json",
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "business_date": BUSINESS_DATE,
            "runtime_business_date": BUSINESS_DATE,
            "market_date": BUSINESS_DATE,
            "as_of": BUSINESS_DATE,
            "market_status": "READY",
            "quote_status": "READY",
            "quote_count": 1,
            "market_summary": {"status": "READY"},
        },
    )
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", pending)
    _write_calendar(root)
    _write_feature_inputs(root / "operations" / "feature_artifacts")
    for name in ("orders", "executions", "cash", "events", "positions"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    return root


def _empty_pending(*, target_date: str, mode: str = "historical") -> dict[str, Any]:
    return {
        "schema_version": "runtime_v2_pending_slot_v1",
        "state": "EMPTY",
        "status": "EMPTY",
        "active_pending": False,
        "environment": mode,
        "target_session_date": target_date,
        "no_action_reason": "NO_SIGNAL:exit_ai_no_sell_signal",
        "items": [],
        "safety_context": _safety_context(target_date),
    }


def _active_pending(*, target_date: str) -> dict[str, Any]:
    payload = _approved_pending(target_date=target_date)
    payload["state"] = "PENDING_APPROVAL"
    payload["status"] = "PENDING_APPROVAL"
    payload["approval"] = {}
    return payload


def _approved_pending(*, target_date: str) -> dict[str, Any]:
    return {
        "schema_version": "runtime_v2_pending_slot_v1",
        "state": "APPROVED",
        "status": "APPROVED",
        "active_pending": True,
        "environment": "historical",
        "target_session_date": target_date,
        "pending_policy_hash": "policy-hash",
        "approval": {"approval_status": "APPROVED", "pending_policy_hash": "policy-hash"},
        "items": [{"symbol": "81050", "side": "BUY", "quantity": 100}],
        "safety_context": _safety_context(target_date),
    }


def _failed_same_day_strategy_pending() -> dict[str, Any]:
    return {
        "schema_version": "1",
        "pending_plan_id": f"pending-strategy-review-{BUSINESS_DATE}",
        "state": "BLOCKED",
        "environment": "historical",
        "created_at": BUSINESS_DATE,
        "updated_at": BUSINESS_DATE,
        "plan_created_date": BUSINESS_DATE,
        "intended_submit_date": BUSINESS_DATE,
        "target_session_date": BUSINESS_DATE,
        "source_order_plan": {
            "order_plan_id": f"strategy-review-{BUSINESS_DATE}",
            "path": f".runtime/runtime_state/strategy_planning/{BUSINESS_DATE}/order_plan.json",
            "artifact_hash": "failed-attempt-order-plan-hash",
        },
        "approved_item_ids": [],
        "items": [],
        "consume": {"consumed": False},
        "safety_context": None,
        "safety_decision_id": "",
        "safety_policy_version": "",
        "planning_authority_hash": "",
        "planning_authority_source": "",
        "planning_authority_version": "",
        "review_scope": "",
        "sell_continuation_allowed": False,
    }


def _failed_same_day_empty_unscoped_review_pending() -> dict[str, Any]:
    authority_hash = "0e6035a7ca90974b5c890ed314fcd853ddab74bc19c02554515dd5b95421a475"
    return {
        "schema_version": "1",
        "pending_plan_id": f"pending-strategy-plan-historical-{BUSINESS_DATE}-0e6035a7ca90974b",
        "state": "REVIEW_REQUIRED",
        "environment": "historical",
        "created_at": BUSINESS_DATE,
        "updated_at": BUSINESS_DATE,
        "plan_created_date": BUSINESS_DATE,
        "intended_submit_date": BUSINESS_DATE,
        "target_session_date": BUSINESS_DATE,
        "source_order_plan": {
            "order_plan_id": f"strategy-plan-historical-{BUSINESS_DATE}-0e6035a7ca90974b",
            "path": f".runtime/runtime_state/strategy_planning/{BUSINESS_DATE}/order_plan.json",
            "artifact_hash": authority_hash,
        },
        "items": [],
        "consume": {"consumed": False},
        "safety_context": _safety_context(BUSINESS_DATE),
        "safety_decision_id": f"historical-neutral-safety:{BUSINESS_DATE}",
        "safety_policy_version": "historical_replay_neutral_safety_v1",
        "planning_authority_hash": authority_hash,
        "planning_authority_source": f"strategy-plan-historical-{BUSINESS_DATE}-0e6035a7ca90974b",
        "planning_authority_version": "phase22_strategy_runtime_planning",
        "review_scope": "",
        "sell_continuation_allowed": False,
        "approved_item_ids": [],
    }


def _safety_context(safety_date: str) -> dict[str, Any]:
    return {
        "safety_authority": "historical_initial_no_external_effect",
        "safety_decision_id": f"historical-neutral-safety:{safety_date}",
        "safety_decision": "NEUTRAL",
        "safety_policy_version": "historical_replay_neutral_safety_v1",
        "safety_source": "data_readiness_historical_temporal_authority",
        "safety_business_date": safety_date,
        "temporal_authority_business_date": safety_date,
        "runtime_test_run_id": RUN_ID,
        "runtime_test_profile_id": PROFILE_ID,
        "runtime_test_evidence_root": str(_evidence_root(Path("/tmp/phase17-bj-fixture"))),
    }


def _write_calendar(root: Path) -> None:
    rows = [
        {"Date": PREVIOUS_DATE, "HolidayDivision": "1"},
        {"Date": BUSINESS_DATE, "HolidayDivision": "1"},
    ]
    _write_jsonl(root / "operations" / "jquants" / "raw" / "jquants" / "trading_calendar" / "data.jsonl", rows)


def _write_feature_inputs(feature_root: Path) -> None:
    feature_dir = feature_root / BUSINESS_DATE
    feature_dir.mkdir(parents=True, exist_ok=True)
    candidate = {column: _value_for_column(column) for column in CANDIDATE_REQUIRED_COLUMNS}
    opportunity = {column: _value_for_column(column) for column in OPPORTUNITY_REQUIRED_COLUMNS}
    pd.DataFrame([candidate]).to_parquet(feature_dir / "candidate_features.parquet", index=False)
    pd.DataFrame([opportunity]).to_parquet(feature_dir / "opportunity_feature_input.parquet", index=False)
    pd.DataFrame([{"target_date": BUSINESS_DATE, "code": "__POLICY_INPUT__"}]).to_parquet(
        feature_dir / "capital_policy_input.parquet",
        index=False,
    )
    pd.DataFrame(
        [
            {
                "target_date": BUSINESS_DATE,
                "position_state_as_of": PREVIOUS_DATE,
                "entry_date": PREVIOUS_DATE,
                "code": "81050",
                "broker_issue_code": "81050",
                "holding_days": 1,
                "average_price": 100.0,
                "current_price": 101.0,
                "unrealized_return": 0.01,
                "quantity": 100.0,
                "feature_version": "runtime_v2_pm_feature_input_v1",
                "data_until": BUSINESS_DATE,
                "created_at": BUSINESS_DATE + "T08:00:00+09:00",
                "no_position_reason": "",
            }
        ]
    ).to_parquet(feature_dir / "position_feature_input.parquet", index=False)
    contract_path = feature_root.parent / "feature_date_contract" / f"{BUSINESS_DATE}.json"
    _write_json(
        contract_path,
        {
            "schema_version": "runtime_v2_feature_contract_v2",
            "status": "PASS",
            "reason": "requested_feature_artifacts_available",
            "requested_feature_date": BUSINESS_DATE,
            "selected_feature_date": BUSINESS_DATE,
            "latest_available_market_date": BUSINESS_DATE,
            "carryover_used": False,
            "feature_artifact_dir": str(feature_dir),
            "generated_feature_artifacts": {
                "candidate_features.parquet": str(feature_dir / "candidate_features.parquet"),
                "opportunity_feature_input.parquet": str(feature_dir / "opportunity_feature_input.parquet"),
                "position_feature_input.parquet": str(feature_dir / "position_feature_input.parquet"),
                "capital_policy_input.parquet": str(feature_dir / "capital_policy_input.parquet"),
            },
            "missing_feature_artifacts": [],
            "requested_feature_artifact_dir": str(feature_dir),
            "requested_missing_feature_artifacts": [],
            "price_source_alignment": "selected_feature_date",
            "consumer_ready": True,
            "candidate_schema_status": "READY",
            "candidate_missing_columns": [],
            "opportunity_schema_status": "READY",
            "pm_schema_status": "READY",
            "consumer_readiness_artifact_path": str(feature_root.parent / "feature_consumer_readiness" / f"{BUSINESS_DATE}.json"),
            "contract_artifact_path": str(contract_path),
        },
    )


def _value_for_column(column: str) -> Any:
    if column == "target_date":
        return BUSINESS_DATE
    if column == "code":
        return "81050"
    if column.startswith("missing_flags_"):
        return False
    if column.endswith("_flag") or column.endswith("_context"):
        return False
    return 1.0


def _write_model(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump({"model": FixtureModel(), "feature_columns": ["feature__price_momentum_return_20d"]}, handle)
    return path


def _evidence_root(tmp_path: Path) -> Path:
    return tmp_path / "reports" / "runtime_tests" / "runs" / RUN_ID


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows), encoding="utf-8")
