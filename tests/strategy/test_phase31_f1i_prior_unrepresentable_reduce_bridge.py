from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.strategy import position_management
from ai_fund_lab_v2.strategy import shadow_runtime
from ai_fund_lab_v2.strategy import strategy_intelligence
from ai_fund_lab_v2.strategy.sell_semantic_state import (
    ESCALATION_REASON_CODE,
    HEALTHY_OR_RECOVERING,
    PERSISTENT_DETERIORATION,
    WEAKENING_BUT_INTACT,
)


def test_phase31_f1i_83060_prior_unrepresentable_reduce_bridge_enables_persistent_exit(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_prior_campaign(run_dir, "2022-08-16", "83060", "campaign-83060")
    _write_pm(run_dir, "2022-08-16", [_pm_row("83060", "campaign-83060", action="REDUCE")])

    campaign = _materialized_campaign(run_dir, "2022-08-17", "83060")
    summary = strategy_intelligence._campaign_history_summary(campaign)["prior_unrepresentable_reduce_summary"]

    assert summary["event_count"] == 1
    assert summary["prior_unrepresentable_reduce_dates"] == ["2022-08-16"]
    assert campaign["events"] == [{"business_date": "2022-08-15", "side": "BUY", "stage": "BUY", "quantity": 100}]
    assert campaign["pm_decision_evidence_events"][0]["decision_evidence_not_execution"] is True
    assert campaign["pm_decision_evidence_events"][0]["fake_execution_event_created"] is False

    positions, reasons = position_management._apply_canonical_sell_semantics(
        [_position("83060", "campaign-83060", prior_summary=summary)],
        business_date="2022-08-17",
    )

    row = positions[0]
    evidence = row["canonical_sell_semantic_evidence"]
    assert reasons == [ESCALATION_REASON_CODE]
    assert row["canonical_sell_state"] == PERSISTENT_DETERIORATION
    assert row["action"] == "EXIT"
    assert evidence["prior_unrepresentable_reduce_count"] == 1
    assert evidence["escalation_decision"] == "PM_EXIT"


def test_phase31_f1i_same_day_current_reduce_is_not_counted(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_prior_campaign(run_dir, "2022-08-16", "83060", "campaign-83060")
    _write_pm(run_dir, "2022-08-17", [_pm_row("83060", "campaign-83060", action="REDUCE")])

    campaign = _materialized_campaign(run_dir, "2022-08-17", "83060")
    summary = strategy_intelligence._campaign_history_summary(campaign)["prior_unrepresentable_reduce_summary"]

    assert summary["event_count"] == 0
    positions, reasons = position_management._apply_canonical_sell_semantics(
        [_position("83060", "campaign-83060", prior_summary=summary)],
        business_date="2022-08-17",
    )
    assert reasons == []
    assert positions[0]["action"] == "REDUCE"
    assert positions[0]["canonical_sell_state"] == WEAKENING_BUT_INTACT


def test_phase31_f1i_54010_recovery_reset_clears_old_unrepresentable_history(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_prior_campaign(run_dir, "2022-08-18", "54010", "campaign-54010")
    _write_pm(
        run_dir,
        "2022-08-16",
        [_pm_row("54010", "campaign-54010", action="REDUCE")],
    )
    _write_pm(
        run_dir,
        "2022-08-18",
        [_pm_row("54010", "campaign-54010", action="HOLD", state=HEALTHY_OR_RECOVERING, recovery=True)],
    )

    campaign = _materialized_campaign(run_dir, "2022-08-19", "54010")
    summary = strategy_intelligence._campaign_history_summary(campaign)["prior_unrepresentable_reduce_summary"]

    assert summary["event_count"] == 0
    assert summary["last_recovery_reset_date"] == "2022-08-18"
    positions, reasons = position_management._apply_canonical_sell_semantics(
        [_position("54010", "campaign-54010", prior_summary=summary)],
        business_date="2022-08-19",
    )
    assert reasons == []
    assert positions[0]["action"] == "REDUCE"
    assert positions[0]["canonical_sell_state"] == WEAKENING_BUT_INTACT


def test_phase31_f1i_61750_second_discrete_reduce_reaches_existing_f1f_gate(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_prior_campaign(run_dir, "2022-09-13", "61750", "campaign-61750")
    _write_pm(run_dir, "2022-09-13", [_pm_row("61750", "campaign-61750", action="REDUCE")])

    campaign = _materialized_campaign(run_dir, "2022-09-14", "61750")
    summary = strategy_intelligence._campaign_history_summary(campaign)["prior_unrepresentable_reduce_summary"]
    positions, reasons = position_management._apply_canonical_sell_semantics(
        [_position("61750", "campaign-61750", prior_summary=summary)],
        business_date="2022-09-14",
    )

    assert summary["event_count"] == 1
    assert reasons == [ESCALATION_REASON_CODE]
    assert positions[0]["action"] == "EXIT"
    assert positions[0]["canonical_sell_state"] == PERSISTENT_DETERIORATION


def test_phase31_f1i_minimum_notional_is_excluded_from_prior_history(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_prior_campaign(run_dir, "2022-08-16", "11110", "campaign-11110")
    _write_pm(
        run_dir,
        "2022-08-16",
        [
            _pm_row(
                "11110",
                "campaign-11110",
                action="REDUCE",
                family="MINIMUM_NOTIONAL",
                minimum_notional=True,
            )
        ],
    )

    campaign = _materialized_campaign(run_dir, "2022-08-17", "11110")
    summary = strategy_intelligence._campaign_history_summary(campaign)["prior_unrepresentable_reduce_summary"]

    assert summary["event_count"] == 0
    assert summary["minimum_notional_excluded"] is True


def test_phase31_f1i_campaign_history_isolated_by_campaign_id(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_prior_campaign(run_dir, "2022-08-16", "83060", "campaign-83060-new")
    _write_pm(run_dir, "2022-08-16", [_pm_row("83060", "campaign-83060-old", action="REDUCE")])

    campaign = _materialized_campaign(run_dir, "2022-08-17", "83060")
    summary = strategy_intelligence._campaign_history_summary(campaign)["prior_unrepresentable_reduce_summary"]

    assert campaign["position_campaign_id"] == "campaign-83060-new"
    assert "pm_decision_evidence_events" not in campaign
    assert summary["event_count"] == 0


def test_phase31_f1i_count_only_does_not_exit_without_current_discrete_gate() -> None:
    positions, reasons = position_management._apply_canonical_sell_semantics(
        [
            _position(
                "83060",
                "campaign-83060",
                prior_summary={"event_count": 3, "last_reduce_date": "2022-08-18"},
                current_quantity=1000,
            )
        ],
        business_date="2022-08-19",
    )

    row = positions[0]
    assert reasons == []
    assert row["action"] == "REDUCE"
    assert row["canonical_sell_state"] == WEAKENING_BUT_INTACT
    assert row["canonical_sell_semantic_evidence"]["representability_family"] == "REPRESENTABLE"


def _materialized_campaign(run_dir: Path, business_date: str, symbol: str) -> dict:
    result = shadow_runtime._materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=None,
        business_date=business_date,
        current={
            "rows": [
                {
                    "security_code": symbol,
                    "quantity": 100,
                    "average_price": 100.0,
                    "market_value": 10000.0,
                    "quantity_basis": "PIT",
                    "valuation_price_basis": "PIT",
                }
            ],
            "source_ref": "",
            "source_hash": "",
            "business_date": business_date,
        },
        as_of=f"{business_date}T00:00:00+00:00",
    )
    payload = json.loads(Path(result["artifact_path"]).read_text(encoding="utf-8"))
    return next(row for row in payload["position_campaigns"] if row["security_code"] == symbol)


def _write_prior_campaign(run_dir: Path, business_date: str, symbol: str, campaign_id: str) -> None:
    _write_json(
        run_dir / "daily" / business_date / "positions" / "position_campaigns.json",
        {
            "schema_version": "position_campaign_observability.v1",
            "business_date": business_date,
            "position_campaigns": [
                {
                    "security_code": symbol,
                    "symbol": symbol,
                    "position_campaign_id": campaign_id,
                    "campaign_status": "OPEN",
                    "opened_business_date": "2022-08-15",
                    "current_quantity": 100,
                    "average_price": 100.0,
                    "quantity_basis": "PIT",
                    "valuation_price_basis": "PIT",
                    "events": [{"business_date": "2022-08-15", "side": "BUY", "stage": "BUY", "quantity": 100}],
                }
            ],
        },
    )


def _write_pm(run_dir: Path, business_date: str, rows: list[dict]) -> None:
    _write_json(
        run_dir / "daily" / business_date / "strategy" / "position_management.json",
        {"schema_version": "position_management.v1", "business_date": business_date, "positions": rows},
    )


def _pm_row(
    symbol: str,
    campaign_id: str,
    *,
    action: str,
    state: str = WEAKENING_BUT_INTACT,
    family: str = "DISCRETE_LOT",
    minimum_notional: bool = False,
    recovery: bool = False,
) -> dict:
    final_quantity = 0 if family in {"DISCRETE_LOT", "MINIMUM_NOTIONAL"} else 100
    return {
        "security_code": symbol,
        "position_campaign_id": campaign_id,
        "action": action,
        "intensity": "NONE" if action in {"HOLD", "EXIT"} else "LIGHT",
        "reason_codes": ["risk_increased_but_trend_not_broken"] if action == "REDUCE" else ["structured_hold_worthiness_pass"],
        "canonical_sell_state": state,
        "canonical_sell_semantic_contract_version": "phase31_f1f_pm_canonical_sell_semantic_integration_v1",
        "canonical_sell_semantic_evidence": {
            "contract_version": "phase31_f1f_pm_canonical_sell_semantic_integration_v1",
            "business_date": "PIT",
            "symbol": symbol,
            "campaign_id": campaign_id,
            "original_pm_action": action,
            "final_pm_action": action,
            "original_pm_reasons": ["risk_increased_but_trend_not_broken"] if action == "REDUCE" else ["structured_hold_worthiness_pass"],
            "canonical_sell_state": state,
            "representability_family": family,
            "current_quantity": 100,
            "trading_unit": 100,
            "raw_reduce_quantity": 25,
            "rounded_reduce_quantity": final_quantity,
            "final_reduce_quantity": final_quantity,
            "minimum_notional_flag": minimum_notional,
            "recovery_state": "RECOVERY_PRESENT" if recovery else "NO_RECOVERY",
            "recovery_dimensions": {"recovery_present": recovery, "reset_policy": "RESET" if recovery else "PRESERVE"},
            "pit_proof": {"pit_validation_state": "PASS"},
            "parameter_resolution_status": "RESET" if recovery else "CANONICAL_EXISTING",
        },
    }


def _position(
    symbol: str,
    campaign_id: str,
    *,
    prior_summary: dict,
    current_quantity: int = 100,
) -> dict:
    return {
        "position_id": f"pm-{symbol}",
        "security_code": symbol,
        "position_campaign_id": campaign_id,
        "action": "REDUCE",
        "intensity": "LIGHT",
        "confidence": 0.7,
        "reason_codes": ["risk_increased_but_trend_not_broken"],
        "adapter_source_contract": {
            "business_date": "2022-08-17",
            "position_state_as_of": "2022-08-17",
            "valuation_date": "2022-08-17",
            "quantity": current_quantity,
        },
        "strategy_intelligence_profit_protection_evidence": {
            "status": "OBSERVED",
            "continuation_deterioration_connection": ["WEAK"],
            "downside_risk_rise_connection": ["ELEVATED_RISK"],
            "future_information_used": False,
        },
        "strategy_intelligence_hold_worthiness_evidence": {
            "status": "PASS",
            "campaign_identity_authority_status": "COMPLETE",
            "reduce_history_summary": {"event_count": 0},
            "prior_unrepresentable_reduce_summary": prior_summary,
            "reason_codes": [],
            "future_information_used": False,
        },
        "strategy_intelligence_add_worthiness_evidence": {
            "status": "NO_ADD",
            "campaign_identity_authority_status": "COMPLETE",
            "reduce_history_summary": {"event_count": 0},
            "prior_unrepresentable_reduce_summary": prior_summary,
            "reason_codes": [],
            "future_information_used": False,
        },
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
