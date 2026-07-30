from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.data_readiness import (
    _current_valuation_temporal_authority,
    evaluate_runtime_data_readiness,
)
from tests.runtime_v2.test_phase17_ag_day2_sell_planning_integration import (
    BUSINESS_DATE,
    PREVIOUS_TRADING_DATE,
    PROFILE_ID,
    RUN_ID,
    _evidence_root,
    _production_ready_root,
    _runtime_root,
    _write_empty_no_action_pending,
    _write_feature_artifacts,
    _write_json,
    _write_jsonl,
)


PRE_CLOSE_SUBMIT_TIME = datetime.fromisoformat("2026-07-07T08:45:00+09:00")
AFTER_CLOSE_SUBMIT_TIME = datetime.fromisoformat("2026-07-07T16:10:00+09:00")


@pytest.mark.parametrize(
    ("mode", "broker_environment"),
    (
        ("production", "tachibana_production"),
        ("demo", "tachibana_demo"),
        ("historical", "historical_simulated"),
    ),
)
def test_phase17_ba_submit_pre_close_accepts_previous_trading_day_close_for_all_modes(
    tmp_path: Path,
    mode: str,
    broker_environment: str,
) -> None:
    root = _submit_ready_root(tmp_path, mode=mode, valuation_as_of=PREVIOUS_TRADING_DATE)

    result = evaluate_runtime_data_readiness(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode=mode,
        readiness_scope="submit",
        feature_root=_write_feature_artifacts(root),
        broker_environment=broker_environment,
        runtime_test_evidence_root=_evidence_root(tmp_path) if mode == "historical" else None,
        runtime_test_run_id=RUN_ID if mode == "historical" else None,
        runtime_test_profile_id=PROFILE_ID if mode == "historical" else None,
        now=PRE_CLOSE_SUBMIT_TIME,
    )

    assert result.status == "READY"
    assert result.payload["pending_status"] == "READY"
    assert result.payload["pending_slot_status"] == "EMPTY"
    assert result.payload["current_valuation_status"] == "READY"
    assert result.payload["current_valuation_expected_date"] == PREVIOUS_TRADING_DATE
    assert result.payload["current_valuation_expected_date_policy"] == "morning_previous_close_or_same_day"
    assert result.payload["current_valuation_previous_close_carry_allowed"] is True
    assert result.payload["current_valuation_close_confirmed"] is False
    assert result.payload["current_valuation_temporal_reason"] == (
        "previous_trading_day_close_is_latest_available_at_morning_evaluation"
    )
    assert "current_valuation_not_ready" not in result.payload["review_reasons"]


def test_phase17_ba_submit_after_close_requires_business_date_close(tmp_path: Path) -> None:
    root = _submit_ready_root(tmp_path, mode="production", valuation_as_of=PREVIOUS_TRADING_DATE)

    result = evaluate_runtime_data_readiness(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="production",
        readiness_scope="submit",
        feature_root=_write_feature_artifacts(root),
        broker_environment="tachibana_production",
        now=AFTER_CLOSE_SUBMIT_TIME,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.payload["current_valuation_status"] == "REVIEW_REQUIRED"
    assert result.payload["current_valuation_expected_date"] == BUSINESS_DATE
    assert result.payload["current_valuation_expected_date_policy"] == "business_date_close"
    assert result.payload["current_valuation_close_confirmed"] is True
    assert result.payload["current_valuation_temporal_reason"] == "current_valuation_not_business_date_close"
    assert "current_valuation_not_ready" in result.payload["review_reasons"]


def test_phase17_ba_submit_temporal_fail_closed_cases() -> None:
    ready_monday = _authority(
        business_date="2026-07-06",
        previous_trading_date="2026-07-03",
        valuation_as_of="2026-07-03",
        source_market_date="2026-07-03",
        evaluation_time="2026-07-06T08:45:00+09:00",
    )
    ready_after_holiday = _authority(
        business_date="2026-07-21",
        previous_trading_date="2026-07-17",
        valuation_as_of="2026-07-17",
        source_market_date="2026-07-17",
        evaluation_time="2026-07-21T08:45:00+09:00",
    )
    future = _authority(valuation_as_of="2026-07-08", source_market_date="2026-07-08")
    stale = _authority(valuation_as_of="2026-07-03", source_market_date="2026-07-03")
    mismatch = _authority(valuation_as_of="2026-07-06", source_market_date="2026-07-05")
    missing_time = _authority(evaluation_time=None)
    missing_calendar = _authority(previous_trading_date="")

    assert ready_monday["status"] == "READY"
    assert ready_monday["previous_close_carry_allowed"] is True
    assert ready_after_holiday["status"] == "READY"
    assert ready_after_holiday["previous_close_carry_allowed"] is True
    assert future["status"] == "HALT"
    assert future["reason"] == "current_valuation_future_date"
    assert stale["status"] == "REVIEW_REQUIRED"
    assert stale["reason"] == "current_valuation_older_than_previous_trading_day"
    assert mismatch["status"] == "REVIEW_REQUIRED"
    assert mismatch["reason"] == "current_valuation_source_market_date_mismatch"
    assert missing_time["status"] == "REVIEW_REQUIRED"
    assert missing_time["reason"] == "current_valuation_evaluation_time_missing"
    assert missing_calendar["status"] == "REVIEW_REQUIRED"
    assert missing_calendar["reason"] == "current_valuation_previous_trading_date_missing"


def test_phase17_ba_current_valuation_scope_uses_refresh_precondition_contract() -> None:
    authority = _current_valuation_temporal_authority(
        readiness_scope="current_valuation",
        business_date=BUSINESS_DATE,
        previous_trading_date=PREVIOUS_TRADING_DATE,
        valuation_as_of=PREVIOUS_TRADING_DATE,
        source_market_date=PREVIOUS_TRADING_DATE,
        evaluation_time=PRE_CLOSE_SUBMIT_TIME,
    )

    assert authority["status"] == "READY"
    assert authority["expected_date"] == BUSINESS_DATE
    assert authority["expected_date_policy"] == "current_valuation_refresh_precondition"
    assert authority["reason"] == "previous_trading_day_close_ready_for_current_valuation_refresh"


def test_phase17_ba_submit_next_day_evaluation_requires_business_date_close() -> None:
    authority = _authority(evaluation_time="2026-07-08T08:45:00+09:00")

    assert authority["status"] == "REVIEW_REQUIRED"
    assert authority["close_confirmed"] is True
    assert authority["expected_date"] == BUSINESS_DATE
    assert authority["reason"] == "current_valuation_not_business_date_close"


def _authority(
    *,
    readiness_scope: str = "submit",
    business_date: str = BUSINESS_DATE,
    previous_trading_date: str = PREVIOUS_TRADING_DATE,
    valuation_as_of: str = PREVIOUS_TRADING_DATE,
    source_market_date: str = PREVIOUS_TRADING_DATE,
    evaluation_time: str | None = "2026-07-07T08:45:00+09:00",
) -> dict:
    return _current_valuation_temporal_authority(
        readiness_scope=readiness_scope,
        business_date=business_date,
        previous_trading_date=previous_trading_date,
        valuation_as_of=valuation_as_of,
        source_market_date=source_market_date,
        evaluation_time=datetime.fromisoformat(evaluation_time) if evaluation_time else None,
    )


def _submit_ready_root(tmp_path: Path, *, mode: str, valuation_as_of: str) -> Path:
    if mode == "production":
        return _production_ready_root(tmp_path, valuation_as_of=valuation_as_of)
    root = _runtime_root(tmp_path, mode=mode, valuation_as_of=valuation_as_of)
    if mode == "historical":
        _write_historical_calendar_authority(tmp_path)
        _write_empty_no_action_pending(root, tmp_path)
    else:
        _write_json(
            root / "pending_order_plan" / "pending_order_plan.json",
            {
                "schema_version": "1",
                "pending_plan_id": "pending-order-plan-demo-no-signal-2026-07-07",
                "state": "EMPTY",
                "status": "EMPTY",
                "active_pending": False,
                "environment": "demo",
                "target_session_date": BUSINESS_DATE,
                "items": [],
                "consume": {"consumed": False},
                "no_action_reason": "NO_SIGNAL:demo_fixture",
            },
        )
        _write_json(
            root / "runtime_state" / "safety" / "latest_safety_decision.json",
            {
                "safety_decision_id": "demo-safety-pass",
                "safety_policy_version": "runtime_safety_v1",
                "safety_source": "demo_safety_gate",
                "business_date": BUSINESS_DATE,
                "runtime_mode": "demo",
                "decision": "ALLOW",
                "reason": "demo_safety_pass",
                "review_required": False,
                "block_buy": False,
                "block_sell": False,
                "block_submit": False,
                "halt_runtime": False,
                "emergency_stop": False,
                "generated_at": BUSINESS_DATE + "T08:00:00+09:00",
                "expires_at": BUSINESS_DATE + "T15:00:00+09:00",
                "safety_status": "PASS",
            },
        )
    return root


def _write_historical_calendar_authority(tmp_path: Path) -> None:
    evidence_root = _evidence_root(tmp_path)
    calendar_path = evidence_root / "daily" / BUSINESS_DATE / "market_refresh" / "inputs" / "historical_asof" / BUSINESS_DATE / "raw" / "jquants" / "trading_calendar" / "data.jsonl"
    _write_jsonl(
        calendar_path,
        [
            {"Date": PREVIOUS_TRADING_DATE, "target_date": PREVIOUS_TRADING_DATE, "HolDiv": "1"},
            {"Date": BUSINESS_DATE, "target_date": BUSINESS_DATE, "HolDiv": "1"},
        ],
    )
    _write_json(
        evidence_root
        / "daily"
        / BUSINESS_DATE
        / "market_refresh"
        / "inputs"
        / "historical_asof"
        / BUSINESS_DATE
        / "logical_input_manifest.json",
        {
            "schema_version": "runtime_historical_logical_input_manifest_v1",
            "status": "PASS",
            "business_date": BUSINESS_DATE,
            "logical_cutoff": BUSINESS_DATE,
            "logical_paths": {"trading_calendar": str(calendar_path)},
        },
    )
