from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

from ai_fund_lab_v2.strategy.canonical_sell_semantic_shadow import (
    AGGREGATE_PASS_SEMANTICS,
    EXIT_GRADE,
    HEALTHY_OR_RECOVERING,
    PERSISTENT_DETERIORATION,
    SCHEMA_VERSION,
    UNRESOLVED,
    WEAKENING_BUT_INTACT,
    build_canonical_sell_semantic_shadow_payload,
    materialize_canonical_sell_semantic_shadow_for_day,
    write_canonical_sell_semantic_shadow_artifact,
)


TARGET_RUN = Path("reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260820T120909096218Z")


def test_phase31_f1d_pass_is_not_health_signal_for_reduce() -> None:
    payload = build_canonical_sell_semantic_shadow_payload(
        business_date="2022-09-13",
        position_management_payload=_pm("61750", action="REDUCE", reasons=["risk_increased_but_trend_not_broken"]),
        position_sizing_payload=_ps("61750", quantity=100, rounded=0, final=0),
        strategy_intelligence_payload=_si("61750", continuation_status="PASS", downside_status="PASS"),
    )

    decision = payload["decisions"][0]
    assert decision["aggregate_pass_semantics"] == AGGREGATE_PASS_SEMANTICS
    assert decision["continuation_quality_status"] == "PASS"
    assert decision["downside_risk_status"] == "PASS"
    assert decision["canonical_sell_state"] == WEAKENING_BUT_INTACT


def test_phase31_f1d_hold_add_recovery_maps_to_healthy_or_recovering() -> None:
    payload = build_canonical_sell_semantic_shadow_payload(
        business_date="2022-09-13",
        position_management_payload=_pm("54010", action="HOLD", intensity="NONE", reasons=["structured_hold_worthiness_pass", "trend_continuation"]),
        position_sizing_payload={"positions": [{"security_code": "54010", "current_quantity": 100, "trading_unit": 100}]},
        strategy_intelligence_payload=_si("54010", entry_state="HEALTHY_CONTINUATION_ENTRY", admission_action="ADD_ALLOWED"),
    )

    decision = payload["decisions"][0]
    assert decision["canonical_sell_state"] == HEALTHY_OR_RECOVERING
    assert decision["recovery_dimensions"]["recovery_present"] is True
    assert decision["parameter_resolution_status"] == "RESET"


def test_phase31_f1d_persistent_deterioration_uses_campaign_prior_and_no_exit_mutation() -> None:
    payload = build_canonical_sell_semantic_shadow_payload(
        business_date="2022-09-14",
        position_management_payload=_pm("61750", action="REDUCE", campaign_id="campaign-61750", reasons=["risk_increased_but_trend_not_broken"]),
        position_sizing_payload=_ps("61750", quantity=100, rounded=0, final=0),
        strategy_intelligence_payload=_si("61750"),
        prior_campaign_events={
            "campaign-61750": [
                {"business_date": "2022-09-13", "current_pm_action": "REDUCE", "reduce_unrepresentable": True}
            ]
        },
    )

    decision = payload["decisions"][0]
    assert decision["canonical_sell_state"] == PERSISTENT_DETERIORATION
    assert decision["parameter_resolution_status"] == "UNRESOLVED_FOR_EXIT"
    assert decision["alternative_g_join"]["alternative_g_persistent_exit_candidate"] is True
    assert decision["actual_pm_action_mutated"] is False
    assert payload["canonical_pm_action_mutated"] is False


def test_phase31_f1d_recovery_reset_blocks_persistent_state() -> None:
    payload = build_canonical_sell_semantic_shadow_payload(
        business_date="2022-09-15",
        position_management_payload=_pm("44440", action="HOLD", intensity="NONE", campaign_id="campaign-44440", reasons=["trend_continuation"]),
        position_sizing_payload={"positions": [{"security_code": "44440", "current_quantity": 100, "trading_unit": 100}]},
        strategy_intelligence_payload=_si("44440", entry_state="HEALTHY_CONTINUATION_ENTRY", admission_action="ADD_ALLOWED"),
        prior_campaign_events={
            "campaign-44440": [
                {"business_date": "2022-09-13", "current_pm_action": "REDUCE", "reduce_unrepresentable": True},
                {"business_date": "2022-09-14", "current_pm_action": "REDUCE", "reduce_unrepresentable": True},
            ]
        },
    )

    decision = payload["decisions"][0]
    assert decision["canonical_sell_state"] == HEALTHY_OR_RECOVERING
    assert decision["alternative_g_join"]["alternative_g_persistent_exit_candidate"] is False


def test_phase31_f1d_exit_grade_maps_existing_pm_exit() -> None:
    payload = build_canonical_sell_semantic_shadow_payload(
        business_date="2022-09-13",
        position_management_payload=_pm("55550", action="EXIT", intensity="NONE", reasons=["trend_and_opportunity_broken"]),
        position_sizing_payload={"positions": [{"security_code": "55550", "current_quantity": 100, "trading_unit": 100}]},
        strategy_intelligence_payload=_si("55550"),
    )

    decision = payload["decisions"][0]
    assert decision["canonical_sell_state"] == EXIT_GRADE
    assert decision["parameter_resolution_status"] == "CANONICAL_EXISTING"


def test_phase31_f1d_one_lot_alone_does_not_exit() -> None:
    payload = build_canonical_sell_semantic_shadow_payload(
        business_date="2022-09-13",
        position_management_payload=_pm("11110", action="REDUCE", reasons=["risk_increased_but_trend_not_broken"]),
        position_sizing_payload=_ps("11110", quantity=100, rounded=0, final=0),
        strategy_intelligence_payload=_si("11110"),
    )

    decision = payload["decisions"][0]
    assert decision["one_lot_flag"] is True
    assert decision["canonical_sell_state"] == WEAKENING_BUT_INTACT
    assert decision["canonical_sell_state"] != EXIT_GRADE


def test_phase31_f1d_minimum_notional_stays_unresolved_family() -> None:
    payload = build_canonical_sell_semantic_shadow_payload(
        business_date="2022-09-13",
        position_management_payload=_pm("11120", action="REDUCE", reasons=["risk_increased_but_trend_not_broken"]),
        position_sizing_payload=_ps(
            "11120",
            quantity=500,
            rounded=100,
            final=0,
            semantic="REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL",
        ),
        strategy_intelligence_payload=_si("11120"),
    )

    decision = payload["decisions"][0]
    assert decision["representability_family"] == "MINIMUM_NOTIONAL"
    assert decision["canonical_sell_state"] == UNRESOLVED
    assert decision["parameter_resolution_status"] == "MINIMUM_NOTIONAL_POLICY_UNRESOLVED"


def test_phase31_f1d_future_dated_evidence_rejects_pit_proof() -> None:
    si = _si("66660")
    si["feature_date"] = "2022-09-16"
    payload = build_canonical_sell_semantic_shadow_payload(
        business_date="2022-09-15",
        position_management_payload=_pm("66660", action="REDUCE", reasons=["risk_increased_but_trend_not_broken"]),
        position_sizing_payload=_ps("66660", quantity=100, rounded=0, final=0),
        strategy_intelligence_payload=si,
    )

    decision = payload["decisions"][0]
    assert decision["pit_proof"]["pit_validation_state"] == "FAIL_FUTURE_DATED_EVIDENCE"
    assert decision["canonical_sell_state"] == UNRESOLVED
    assert decision["future_information_used"] is False


def test_phase31_f1d_materialization_writes_only_diagnostic_shadow(tmp_path: Path) -> None:
    source_day = TARGET_RUN / "daily" / "2022-09-13"
    run_root = tmp_path / "run"
    day_root = run_root / "daily" / "2022-09-13"
    shutil.copytree(source_day / "strategy", day_root / "strategy")
    (run_root / "run_state.json").write_text(json.dumps({"completed_business_days": ["2022-09-13"]}), encoding="utf-8")
    before = {
        "pm": (day_root / "strategy" / "position_management.json").read_bytes(),
        "ps": (day_root / "strategy" / "position_sizing.json").read_bytes(),
        "si": (day_root / "strategy" / "strategy_intelligence.json").read_bytes(),
    }

    payload = materialize_canonical_sell_semantic_shadow_for_day(run_root=run_root, business_date="2022-09-13")

    output_path = Path(payload["artifact_path"])
    assert output_path == day_root / "diagnostic_shadow" / "canonical_sell_semantic_shadow.json"
    assert output_path.is_file()
    assert payload["schema_version"] == SCHEMA_VERSION
    assert (day_root / "strategy" / "position_management.json").read_bytes() == before["pm"]
    assert (day_root / "strategy" / "position_sizing.json").read_bytes() == before["ps"]
    assert (day_root / "strategy" / "strategy_intelligence.json").read_bytes() == before["si"]
    assert payload["production_consumer_count"] == 0


def test_phase31_f1d_write_artifact_is_non_mutating(tmp_path: Path) -> None:
    pm = _pm("61750", action="REDUCE", reasons=["risk_increased_but_trend_not_broken"])
    ps = _ps("61750", quantity=100, rounded=0, final=0)
    si = _si("61750")
    originals = copy.deepcopy((pm, ps, si))

    payload = build_canonical_sell_semantic_shadow_payload(
        business_date="2022-09-13",
        position_management_payload=pm,
        position_sizing_payload=ps,
        strategy_intelligence_payload=si,
    )
    path = write_canonical_sell_semantic_shadow_artifact(payload, tmp_path / "diagnostic_shadow" / "canonical_sell_semantic_shadow.json")

    assert path.is_file()
    assert (pm, ps, si) == originals
    assert payload["actual_trading_path_mutated"] is False


def _pm(
    symbol: str,
    *,
    action: str,
    intensity: str = "LIGHT",
    campaign_id: str | None = None,
    reasons: list[str] | None = None,
) -> dict:
    return {
        "positions": [
            {
                "security_code": symbol,
                "position_campaign_id": campaign_id or f"campaign-{symbol}",
                "action": action,
                "intensity": intensity,
                "confidence": 0.7,
                "reason_codes": reasons or [],
            }
        ]
    }


def _ps(
    symbol: str,
    *,
    quantity: int,
    rounded: int,
    final: int,
    semantic: str = "REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT",
) -> dict:
    return {
        "positions": [
            {
                "security_code": symbol,
                "current_quantity": quantity,
                "trading_unit": 100,
                "target_reduce_ratio": 0.25,
                "raw_reduce_quantity": quantity * 0.25,
                "rounded_reduce_quantity": rounded,
                "reduce_final_sell_quantity": final,
                "reduce_execution_semantic": semantic,
            }
        ]
    }


def _si(
    symbol: str,
    *,
    continuation_status: str = "PASS",
    downside_status: str = "PASS",
    entry_state: str = "CONTINUATION_WITH_CAUTION",
    admission_action: str = "ADD_REDUCED_ONLY",
) -> dict:
    return {
        "business_date": "2022-09-13",
        "feature_date": "2022-09-13",
        "symbol_intelligence": {
            symbol: {
                "continuation_quality": {
                    "status": continuation_status,
                    "trend_health": {"state": "SUPPORTIVE", "as_of_date": "2022-09-13"},
                    "persistence": {"state": "MIXED", "as_of_date": "2022-09-13"},
                    "acceleration_state": {"state": "DECELERATING", "as_of_date": "2022-09-13"},
                    "participation_quality": {"state": "WEAK", "as_of_date": "2022-09-13"},
                },
                "downside_risk": {
                    "status": downside_status,
                    "participation_risk": {"state": "ELEVATED_RISK", "as_of_date": "2022-09-13"},
                },
                "entry_admission": {
                    "entry_state": entry_state,
                    "admission_action": admission_action,
                },
                "profit_protection_evidence": {
                    "status": "OBSERVED",
                    "continuation_deterioration_connection": ["WEAK"],
                    "downside_risk_rise_connection": ["ELEVATED_RISK"],
                    "future_information_used": False,
                },
                "lifecycle_context": {
                    "position_campaign_id": f"campaign-{symbol}",
                    "current_campaign_relative_return": 0.01,
                    "observed_campaign_mfe": 0.02,
                    "observed_giveback": 0.01,
                },
            }
        },
    }
