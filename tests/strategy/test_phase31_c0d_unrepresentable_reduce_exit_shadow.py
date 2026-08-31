from __future__ import annotations

import copy
import json
from pathlib import Path

from ai_fund_lab_v2.strategy.unrepresentable_reduce_exit_shadow import (
    BINARY_MATERIALIZATION_CONTRACT_VERSION,
    MODE,
    PRODUCER,
    SCHEMA_VERSION,
    build_unrepresentable_reduce_exit_shadow_payload,
    materialize_unrepresentable_reduce_exit_shadow_for_day,
    write_unrepresentable_reduce_exit_shadow_artifact,
)


def test_phase31_c0d_one_lot_unrepresentable_reduce_shadow_non_mutating(tmp_path: Path) -> None:
    pm, ps, rp, si, mc = _inputs(action="REDUCE", intensity="LIGHT", quantity=100, final_reduce_sell_quantity=0)
    originals = copy.deepcopy((pm, ps, rp, si, mc))

    payload = build_unrepresentable_reduce_exit_shadow_payload(
        business_date="2022-09-13",
        position_management_payload=pm,
        position_sizing_payload=ps,
        runtime_planning_payload=rp,
        strategy_intelligence_payload=si,
        market_context_payload=mc,
    )
    path = write_unrepresentable_reduce_exit_shadow_artifact(payload, tmp_path / "diagnostic_shadow" / "unrepresentable_reduce_exit_shadow.json")

    decision = payload["decisions"][0]
    assert path.is_file()
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["producer"] == PRODUCER
    assert payload["mode"] == MODE
    assert decision["reduce_unrepresentable_due_to_lot"] is True
    assert decision["desired_reduction_fraction"] == 0.25
    assert decision["actual_reduction_fraction"] == 0.0
    assert decision["representation_error"] == 0.25
    assert payload["binary_materialization_contract_version"] == BINARY_MATERIALIZATION_CONTRACT_VERSION
    assert decision["shadow_only"] is True
    assert decision["historical_outcome_input_used"] is False
    assert payload["actual_trading_path_mutated"] is False
    assert payload["canonical_pm_action_mutated"] is False
    assert (pm, ps, rp, si, mc) == originals


def test_phase31_c0d_representable_multi_lot_reduce_is_not_exit_candidate() -> None:
    payload = build_unrepresentable_reduce_exit_shadow_payload(
        business_date="2022-09-13",
        position_management_payload=_pm("11110", action="REDUCE", intensity="MEDIUM"),
        position_sizing_payload=_ps("11110", quantity=500, ratio=0.33, rounded=100, final=100, semantic=""),
        runtime_planning_payload={"plans": [{"security_code": "11110", "source_pm_action": "REDUCE", "planning_intent": "SELL_REDUCE", "planned_quantity": 100}]},
        strategy_intelligence_payload=_strategy_intelligence("11110"),
        market_context_payload=_market_context(),
    )

    decision = payload["decisions"][0]
    assert decision["reduce_representability_state"] == "REPRESENTABLE"
    assert decision["shadow_state"] == "REPRESENTABLE_REDUCE"
    assert decision["alternative_g_shadow_action"] == "REDUCE"
    assert decision["shadow_binary_decision"] == "SHADOW_NOT_APPLICABLE"
    assert decision["shadow_binary_eligibility_reason"] == "PARTIAL_REDUCE_EXECUTABLE"
    assert decision["branch"] == "NONE"


def test_phase31_f1a_minimum_notional_reduce_is_separate_unresolved_family() -> None:
    payload = build_unrepresentable_reduce_exit_shadow_payload(
        business_date="2022-09-13",
        position_management_payload=_pm("11120", action="REDUCE", intensity="LIGHT"),
        position_sizing_payload=_ps(
            "11120",
            quantity=500,
            ratio=0.25,
            rounded=100,
            final=0,
            semantic="REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL",
        ),
        runtime_planning_payload={
            "plans": [
                {
                    "security_code": "11120",
                    "source_pm_action": "REDUCE",
                    "planning_intent": "NO_ORDER",
                    "planned_quantity": 0,
                    "no_order_reason": "REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL",
                    "reduce_execution_semantic": "REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL",
                }
            ]
        },
        strategy_intelligence_payload=_strategy_intelligence("11120"),
        market_context_payload=_market_context(),
    )

    decision = payload["decisions"][0]
    assert decision["representability_family"] == "MINIMUM_NOTIONAL"
    assert decision["minimum_notional_flag"] is True
    assert decision["reduce_unrepresentable_due_to_lot"] is False
    assert decision["reduce_unrepresentable_due_to_minimum_notional"] is True
    assert decision["shadow_state"] == "PARAMETER_UNRESOLVED"
    assert decision["alternative_g_shadow_action"] == "PRESERVE"
    assert decision["parameter_resolution_state"] == "MINIMUM_NOTIONAL_POLICY_UNRESOLVED"
    assert decision["shadow_binary_decision"] == "SHADOW_NOT_APPLICABLE"
    assert decision["shadow_binary_eligibility_reason"] == "REPRESENTABILITY_FAMILY:MINIMUM_NOTIONAL"


def test_phase31_c0d_immediate_branch_structural_candidate() -> None:
    payload = build_unrepresentable_reduce_exit_shadow_payload(
        business_date="2022-09-13",
        position_management_payload=_pm("22220", action="REDUCE", intensity="STRONG", reason_codes=["high_downside_risk"]),
        position_sizing_payload=_ps("22220", quantity=100, ratio=0.5, rounded=0, final=0),
        runtime_planning_payload=_rp("22220"),
        strategy_intelligence_payload=_strategy_intelligence("22220", expected_edge_status="DETERIORATING"),
        market_context_payload=_market_context(),
    )

    decision = payload["decisions"][0]
    assert decision["branch"] == "IMMEDIATE"
    assert decision["shadow_state"] == "IMMEDIATE_EXIT_CANDIDATE"
    assert decision["alternative_g_shadow_action"] == "EXIT"
    assert decision["variant_results"]["G1"]["alternative_g_shadow_action"] == "EXIT"
    assert decision["variant_results"]["G3"]["alternative_g_shadow_action"] == "EXIT"


def test_phase31_c0d_persistent_branch_is_parameter_unresolved_and_no_debt() -> None:
    payload = build_unrepresentable_reduce_exit_shadow_payload(
        business_date="2022-09-15",
        position_management_payload=_pm("33330", action="REDUCE", intensity="LIGHT", campaign_id="campaign-33330"),
        position_sizing_payload=_ps("33330", quantity=100, ratio=0.25, rounded=0, final=0),
        runtime_planning_payload=_rp("33330"),
        strategy_intelligence_payload=_strategy_intelligence("33330", expected_edge_status="DETERIORATING"),
        market_context_payload=_market_context(),
        prior_unrepresentable_reduce_events={
            "campaign-33330": [
                {"business_date": "2022-09-13", "baseline_pm_action": "REDUCE", "reduce_unrepresentable_due_to_lot": True},
                {"business_date": "2022-09-14", "baseline_pm_action": "REDUCE", "reduce_unrepresentable_due_to_lot": True},
            ]
        },
    )

    decision = payload["decisions"][0]
    assert decision["branch"] == "PERSISTENT"
    assert decision["structural_shadow_state"] == "PERSISTENT_EXIT_CANDIDATE"
    assert decision["shadow_state"] == "PARAMETER_UNRESOLVED"
    assert decision["parameter_resolved"] is False
    assert decision["persistence_parameter_status"] == "VALIDATION_REQUIRED_UNSET"
    assert payload["hidden_reduce_debt_added"] is False


def test_phase31_c0d_recovery_blocks_stale_escalation() -> None:
    payload = build_unrepresentable_reduce_exit_shadow_payload(
        business_date="2022-09-15",
        position_management_payload=_pm("44440", action="REDUCE", intensity="LIGHT", campaign_id="campaign-44440"),
        position_sizing_payload=_ps("44440", quantity=100, ratio=0.25, rounded=0, final=0),
        runtime_planning_payload=_rp("44440"),
        strategy_intelligence_payload=_strategy_intelligence(
            "44440",
            expected_edge_status="ADEQUATE",
            entry_state="HEALTHY_CONTINUATION_ENTRY",
            admission_action="ADD_ALLOWED",
            trend_state="SUPPORTIVE",
        ),
        market_context_payload=_market_context(),
        prior_unrepresentable_reduce_events={
            "campaign-44440": [
                {"business_date": "2022-09-13", "baseline_pm_action": "REDUCE", "reduce_unrepresentable_due_to_lot": True}
            ]
        },
    )

    decision = payload["decisions"][0]
    assert decision["shadow_state"] == "RECOVERY_BLOCKED"
    assert decision["alternative_g_shadow_action"] == "PRESERVE"
    assert decision["recovery_state"] == "RECOVERY_PRESENT"
    assert "RECOVERY_BLOCKED_ESCALATION" in decision["reason_codes"]


def test_phase31_c0d_existing_pm_exit_is_not_interfered_with() -> None:
    payload = build_unrepresentable_reduce_exit_shadow_payload(
        business_date="2022-09-13",
        position_management_payload=_pm("55550", action="EXIT", intensity="NONE"),
        position_sizing_payload={"positions": [{"security_code": "55550", "pm_action": "EXIT", "current_quantity": 100, "target_quantity_candidate": 0}]},
        runtime_planning_payload={"plans": [{"security_code": "55550", "source_pm_action": "EXIT", "planning_intent": "SELL_EXIT", "planned_quantity": 100}]},
        strategy_intelligence_payload=_strategy_intelligence("55550", expected_edge_status="INSUFFICIENT"),
        market_context_payload=_market_context(),
    )

    decision = payload["decisions"][0]
    assert decision["baseline_pm_action"] == "EXIT"
    assert decision["shadow_state"] == "NOT_APPLICABLE"
    assert decision["alternative_g_shadow_action"] == "BASELINE"
    assert decision["shadow_binary_decision"] == "SHADOW_NOT_APPLICABLE"
    assert payload["canonical_pm_action_mutated"] is False


def test_phase31_c0d_future_dated_evidence_fails_pit_proof() -> None:
    si = _strategy_intelligence("66660", expected_edge_status="DETERIORATING")
    si["feature_date"] = "2022-09-16"
    payload = build_unrepresentable_reduce_exit_shadow_payload(
        business_date="2022-09-15",
        position_management_payload=_pm("66660", action="REDUCE", intensity="STRONG"),
        position_sizing_payload=_ps("66660", quantity=100, ratio=0.5, rounded=0, final=0),
        runtime_planning_payload=_rp("66660"),
        strategy_intelligence_payload=si,
        market_context_payload=_market_context(),
    )

    decision = payload["decisions"][0]
    assert decision["pit_validation_state"] == "FAIL_FUTURE_DATED_EVIDENCE"
    assert decision["shadow_state"] == "EVIDENCE_INSUFFICIENT"
    assert decision["shadow_binary_decision"] == "SHADOW_INSUFFICIENT_EVIDENCE"
    assert decision["shadow_binary_authority_status"] == "FAIL_CLOSED"
    assert decision["future_information_used"] is False


def test_phase32_bl_lot_blocked_reduce_shadow_full_exit_from_current_pit_risk_evidence() -> None:
    payload = build_unrepresentable_reduce_exit_shadow_payload(
        business_date="2022-09-13",
        run_id="runtime-test-current",
        profile_id="historical-extended-smoke",
        position_management_payload=_pm("62280", action="REDUCE", intensity="LIGHT", reason_codes=["risk_increased_but_trend_not_broken"]),
        position_sizing_payload=_ps("62280", quantity=100, ratio=0.25, rounded=0, final=0),
        runtime_planning_payload=_rp("62280"),
        strategy_intelligence_payload=_strategy_intelligence(
            "62280",
            expected_edge_status="DETERIORATING",
            trend_state="MIXED",
            relative_strength_state="MIXED",
            participation_quality_state="WEAK",
            exhaustion_risk_state="ELEVATED_RISK",
            current_campaign_relative_return=-0.01,
            run_id="runtime-test-current",
            profile_id="historical-extended-smoke",
        ),
        market_context_payload=_market_context(),
        source_artifacts={"strategy_intelligence": "reports/runtime_tests/runs/runtime-test-current/daily/2022-09-13/strategy/strategy_intelligence.json"},
    )

    decision = payload["decisions"][0]
    assert decision["shadow_binary_decision"] == "SHADOW_FULL_EXIT"
    assert decision["shadow_binary_eligibility_status"] == "PASS"
    assert decision["production_actual_action"] == "NO_ORDER"
    assert decision["production_actual_quantity"] == 0
    assert decision["shadow_order_authority"] is False
    assert decision["action_score_decisive_authority"] is False
    assert decision["historical_outcome_input_used"] is False
    assert any(item["signal"] == "exhaustion_risk" for item in decision["exit_side_evidence"])


def test_phase32_bl_lot_blocked_reduce_shadow_hold_from_current_pit_continuation_evidence() -> None:
    payload = build_unrepresentable_reduce_exit_shadow_payload(
        business_date="2022-09-13",
        position_management_payload=_pm("67310", action="REDUCE", intensity="LIGHT"),
        position_sizing_payload=_ps("67310", quantity=100, ratio=0.25, rounded=0, final=0),
        runtime_planning_payload=_rp("67310"),
        strategy_intelligence_payload=_strategy_intelligence(
            "67310",
            expected_edge_status="ADEQUATE",
            trend_state="SUPPORTIVE",
            relative_strength_state="SUPPORTIVE",
            participation_quality_state="SUPPORTIVE",
            exhaustion_risk_state="MANAGEABLE",
            persistence_state="SUPPORTIVE",
            strong_medium_term_structure=True,
            current_campaign_relative_return=0.08,
        ),
        market_context_payload=_market_context(),
    )

    decision = payload["decisions"][0]
    assert decision["shadow_binary_decision"] == "SHADOW_HOLD"
    assert decision["shadow_binary_eligibility_status"] == "PASS"
    assert decision["production_actual_action"] == "NO_ORDER"
    assert any(item["signal"] == "relative_strength" for item in decision["hold_side_evidence"])
    assert decision["decisive_semantic_rationale"].startswith("multiple current PIT continuation")


def test_phase32_bl_lot_blocked_reduce_shadow_mixed_evidence_remains_insufficient() -> None:
    payload = build_unrepresentable_reduce_exit_shadow_payload(
        business_date="2022-09-13",
        position_management_payload=_pm("74270", action="REDUCE", intensity="LIGHT"),
        position_sizing_payload=_ps("74270", quantity=100, ratio=0.25, rounded=0, final=0),
        runtime_planning_payload=_rp("74270"),
        strategy_intelligence_payload=_strategy_intelligence(
            "74270",
            expected_edge_status="DETERIORATING",
            trend_state="SUPPORTIVE",
            relative_strength_state="SUPPORTIVE",
            exhaustion_risk_state="ELEVATED_RISK",
            current_campaign_relative_return=0.03,
        ),
        market_context_payload=_market_context(),
    )

    decision = payload["decisions"][0]
    assert decision["shadow_binary_decision"] == "SHADOW_INSUFFICIENT_EVIDENCE"
    assert decision["shadow_binary_eligibility_status"] == "PASS"
    assert decision["production_actual_action"] == "NO_ORDER"


def test_phase32_bo_profit_alone_cannot_force_hold() -> None:
    payload = build_unrepresentable_reduce_exit_shadow_payload(
        business_date="2022-09-13",
        position_management_payload=_pm("62310", action="REDUCE", intensity="LIGHT"),
        position_sizing_payload=_ps("62310", quantity=100, ratio=0.25, rounded=0, final=0),
        runtime_planning_payload=_rp("62310"),
        strategy_intelligence_payload=_strategy_intelligence(
            "62310",
            expected_edge_status="ADEQUATE",
            trend_state="MIXED",
            relative_strength_state="MIXED",
            participation_quality_state="MIXED",
            exhaustion_risk_state="MIXED",
            participation_risk_state="MANAGEABLE",
            current_campaign_relative_return=0.25,
        ),
        market_context_payload=_market_context(),
    )

    decision = payload["decisions"][0]
    assert decision["shadow_binary_decision"] == "SHADOW_INSUFFICIENT_EVIDENCE"
    assert "profit_cushion" not in {item["signal"] for item in decision["hold_side_evidence"]}
    assert decision["semantic_evidence_used"]["profit_cushion_standalone_hold_authority"] is False


def test_phase32_bo_profit_alone_cannot_force_sell() -> None:
    payload = build_unrepresentable_reduce_exit_shadow_payload(
        business_date="2022-09-13",
        position_management_payload=_pm("74770", action="REDUCE", intensity="LIGHT"),
        position_sizing_payload=_ps("74770", quantity=100, ratio=0.25, rounded=0, final=0),
        runtime_planning_payload=_rp("74770"),
        strategy_intelligence_payload=_strategy_intelligence(
            "74770",
            expected_edge_status="ADEQUATE",
            trend_state="",
            relative_strength_state="",
            participation_quality_state="",
            exhaustion_risk_state="",
            participation_risk_state="MANAGEABLE",
            current_campaign_relative_return=0.25,
        ),
        market_context_payload=_market_context(),
    )

    decision = payload["decisions"][0]
    assert decision["shadow_binary_decision"] == "SHADOW_INSUFFICIENT_EVIDENCE"
    assert decision["semantic_evidence_used"]["profit_cushion_context"][0]["state"] == "PRESENT_CONTEXT_ONLY"


def test_phase32_bo_profit_plus_strong_continuation_supports_hold() -> None:
    payload = build_unrepresentable_reduce_exit_shadow_payload(
        business_date="2022-09-13",
        position_management_payload=_pm("62280", action="REDUCE", intensity="LIGHT"),
        position_sizing_payload=_ps("62280", quantity=100, ratio=0.25, rounded=0, final=0),
        runtime_planning_payload=_rp("62280"),
        strategy_intelligence_payload=_strategy_intelligence(
            "62280",
            expected_edge_status="ADEQUATE",
            trend_state="SUPPORTIVE",
            relative_strength_state="SUPPORTIVE",
            participation_quality_state="SUPPORTIVE",
            exhaustion_risk_state="MANAGEABLE",
            persistence_state="SUPPORTIVE",
            strong_medium_term_structure=True,
            current_campaign_relative_return=0.1,
        ),
        market_context_payload=_market_context(),
    )

    decision = payload["decisions"][0]
    assert decision["shadow_binary_decision"] == "SHADOW_HOLD"
    assert decision["semantic_evidence_used"]["profit_cushion_context"][0]["state"] == "CONTEXTUAL_HOLD_SUPPORT"


def test_phase32_bo_profit_plus_deterioration_not_blocked_from_exit_by_profit() -> None:
    payload = build_unrepresentable_reduce_exit_shadow_payload(
        business_date="2022-09-13",
        position_management_payload=_pm("67310", action="REDUCE", intensity="LIGHT"),
        position_sizing_payload=_ps("67310", quantity=100, ratio=0.25, rounded=0, final=0),
        runtime_planning_payload=_rp("67310"),
        strategy_intelligence_payload=_strategy_intelligence(
            "67310",
            expected_edge_status="ADEQUATE",
            trend_state="WEAK",
            relative_strength_state="WEAK",
            participation_quality_state="WEAK",
            exhaustion_risk_state="MIXED",
            current_campaign_relative_return=0.5,
        ),
        market_context_payload=_market_context(),
    )

    decision = payload["decisions"][0]
    assert decision["shadow_binary_decision"] == "SHADOW_FULL_EXIT"
    assert "profit_cushion" not in {item["signal"] for item in decision["hold_side_evidence"]}
    assert decision["semantic_evidence_used"]["profit_cushion_context"][0]["state"] == "PROFIT_AT_RISK"


def test_phase32_bo_profit_plus_mixed_relative_does_not_full_exit_winner_control() -> None:
    payload = build_unrepresentable_reduce_exit_shadow_payload(
        business_date="2022-09-13",
        position_management_payload=_pm("74270", action="REDUCE", intensity="LIGHT"),
        position_sizing_payload=_ps("74270", quantity=100, ratio=0.25, rounded=0, final=0),
        runtime_planning_payload=_rp("74270"),
        strategy_intelligence_payload=_strategy_intelligence(
            "74270",
            expected_edge_status="ADEQUATE",
            trend_state="WEAK",
            relative_strength_state="MIXED",
            participation_quality_state="WEAK",
            exhaustion_risk_state="MIXED",
            participation_risk_state="ELEVATED_RISK",
            current_campaign_relative_return=0.35,
        ),
        market_context_payload=_market_context(),
    )

    decision = payload["decisions"][0]
    assert decision["shadow_binary_decision"] == "SHADOW_INSUFFICIENT_EVIDENCE"
    assert decision["semantic_evidence_used"]["profit_cushion_context"][0]["state"] == "PROFIT_AT_RISK"
    assert decision["semantic_evidence_used"]["profit_cushion_standalone_hold_authority"] is False


def test_phase32_bo_profit_plus_mild_deterioration_does_not_full_exit_winner_control() -> None:
    payload = build_unrepresentable_reduce_exit_shadow_payload(
        business_date="2022-09-13",
        position_management_payload=_pm("83040", action="REDUCE", intensity="LIGHT"),
        position_sizing_payload=_ps("83040", quantity=100, ratio=0.25, rounded=0, final=0),
        runtime_planning_payload=_rp("83040"),
        strategy_intelligence_payload=_strategy_intelligence(
            "83040",
            expected_edge_status="ADEQUATE",
            trend_state="WEAK",
            relative_strength_state="MIXED",
            participation_quality_state="MIXED",
            exhaustion_risk_state="MIXED",
            participation_risk_state="MANAGEABLE",
            current_campaign_relative_return=0.2,
        ),
        market_context_payload=_market_context(),
    )

    decision = payload["decisions"][0]
    assert decision["shadow_binary_decision"] == "SHADOW_INSUFFICIENT_EVIDENCE"
    assert decision["semantic_evidence_used"]["profit_cushion_context"][0]["state"] == "PROFIT_AT_RISK"
    assert decision["semantic_evidence_used"]["profit_cushion_standalone_hold_authority"] is False


def test_phase32_bl_non_reduce_actions_do_not_invoke_binary_shadow() -> None:
    for action in ("BUY", "HOLD", "EXIT"):
        payload = build_unrepresentable_reduce_exit_shadow_payload(
            business_date="2022-09-13",
            position_management_payload=_pm("72140", action=action, intensity="NONE"),
            position_sizing_payload=_ps("72140", quantity=100, ratio=0.25, rounded=0, final=0),
            runtime_planning_payload=_rp("72140"),
            strategy_intelligence_payload=_strategy_intelligence("72140"),
            market_context_payload=_market_context(),
        )
        decision = payload["decisions"][0]
        assert decision["shadow_binary_decision"] == "SHADOW_NOT_APPLICABLE"
        assert decision["shadow_binary_eligibility_status"] == "NOT_APPLICABLE"


def test_phase32_bl_missing_campaign_provenance_fails_closed_for_binary_shadow() -> None:
    pm = _pm("83040", action="REDUCE", intensity="LIGHT", campaign_id="")
    pm["positions"][0]["position_campaign_id"] = ""
    payload = build_unrepresentable_reduce_exit_shadow_payload(
        business_date="2022-09-13",
        position_management_payload=pm,
        position_sizing_payload=_ps("83040", quantity=100, ratio=0.25, rounded=0, final=0),
        runtime_planning_payload=_rp("83040"),
        strategy_intelligence_payload=_strategy_intelligence("83040"),
        market_context_payload=_market_context(),
    )

    decision = payload["decisions"][0]
    assert decision["shadow_binary_decision"] == "SHADOW_INSUFFICIENT_EVIDENCE"
    assert decision["shadow_binary_authority_status"] == "FAIL_CLOSED"
    assert "MISSING_CAMPAIGN_ID" in decision["shadow_binary_eligibility_reason"]


def test_phase32_bl_cross_run_strategy_evidence_fails_closed() -> None:
    payload = build_unrepresentable_reduce_exit_shadow_payload(
        business_date="2022-09-13",
        run_id="runtime-test-current",
        position_management_payload=_pm("69730", action="REDUCE", intensity="LIGHT"),
        position_sizing_payload=_ps("69730", quantity=100, ratio=0.25, rounded=0, final=0),
        runtime_planning_payload=_rp("69730"),
        strategy_intelligence_payload=_strategy_intelligence("69730", run_id="runtime-test-other"),
        market_context_payload=_market_context(),
        source_artifacts={"strategy_intelligence": "reports/runtime_tests/runs/runtime-test-other/daily/2022-09-13/strategy/strategy_intelligence.json"},
    )

    decision = payload["decisions"][0]
    assert decision["pit_validation_state"] == "FAIL_STALE_OR_CROSS_RUN_EVIDENCE"
    assert decision["shadow_binary_decision"] == "SHADOW_INSUFFICIENT_EVIDENCE"
    assert decision["shadow_binary_authority_status"] == "FAIL_CLOSED"


def test_phase31_c0d_materialization_writes_only_diagnostic_shadow(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    day_root = run_root / "daily" / "2022-09-13"
    strategy_root = day_root / "strategy"
    strategy_root.mkdir(parents=True)
    (strategy_root / "position_management.json").write_text(json.dumps(_pm("61750", action="REDUCE", intensity="LIGHT")), encoding="utf-8")
    (strategy_root / "position_sizing.json").write_text(json.dumps(_ps("61750", quantity=100, ratio=0.25, rounded=0, final=0)), encoding="utf-8")
    (strategy_root / "runtime_planning.json").write_text(json.dumps(_rp("61750")), encoding="utf-8")
    (strategy_root / "strategy_intelligence.json").write_text(json.dumps(_strategy_intelligence("61750")), encoding="utf-8")
    (strategy_root / "market_context.json").write_text(json.dumps(_market_context()), encoding="utf-8")
    (run_root / "run_state.json").write_text(
        json.dumps({"run_id": "run", "profile": "historical-extended-smoke", "completed_business_days": ["2022-09-13"]}),
        encoding="utf-8",
    )
    before = {
        "pm": (day_root / "strategy" / "position_management.json").read_bytes(),
        "ps": (day_root / "strategy" / "position_sizing.json").read_bytes(),
        "rp": (day_root / "strategy" / "runtime_planning.json").read_bytes(),
    }

    payload = materialize_unrepresentable_reduce_exit_shadow_for_day(run_root=run_root, business_date="2022-09-13")

    output_path = Path(payload["artifact_path"])
    assert output_path == day_root / "diagnostic_shadow" / "unrepresentable_reduce_exit_shadow.json"
    assert output_path.is_file()
    assert (day_root / "strategy" / "position_management.json").read_bytes() == before["pm"]
    assert (day_root / "strategy" / "position_sizing.json").read_bytes() == before["ps"]
    assert (day_root / "strategy" / "runtime_planning.json").read_bytes() == before["rp"]
    assert payload["actual_trading_path_mutated"] is False
    assert payload["production_consumer_count"] == 0


def _inputs(*, action: str, intensity: str, quantity: int, final_reduce_sell_quantity: int):
    symbol = "61750"
    ratio = {"LIGHT": 0.25, "MEDIUM": 0.33, "STRONG": 0.5}.get(intensity, 0.25)
    return (
        _pm(symbol, action=action, intensity=intensity),
        _ps(symbol, quantity=quantity, ratio=ratio, rounded=final_reduce_sell_quantity, final=final_reduce_sell_quantity),
        _rp(symbol),
        _strategy_intelligence(symbol, expected_edge_status="DETERIORATING"),
        _market_context(),
    )


def _pm(symbol: str, *, action: str, intensity: str, campaign_id: str | None = None, reason_codes: list[str] | None = None) -> dict:
    return {
        "positions": [
            {
                "security_code": symbol,
                "position_campaign_id": campaign_id or f"campaign-{symbol}",
                "action": action,
                "intensity": intensity,
                "confidence": 0.7,
                "reason_codes": reason_codes or ["risk_increased_but_trend_not_broken"],
            }
        ]
    }


def _ps(symbol: str, *, quantity: int, ratio: float, rounded: int, final: int, semantic: str = "REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT") -> dict:
    return {
        "positions": [
            {
                "security_code": symbol,
                "pm_action": "REDUCE",
                "current_quantity": quantity,
                "trading_unit": 100,
                "target_reduce_ratio": ratio,
                "raw_reduce_quantity": quantity * ratio,
                "rounded_reduce_quantity": rounded,
                "reduce_final_sell_quantity": final,
                "reduce_execution_semantic": semantic,
            }
        ]
    }


def _rp(symbol: str) -> dict:
    return {
        "plans": [
            {
                "security_code": symbol,
                "source_pm_action": "REDUCE",
                "planning_intent": "NO_ORDER",
                "planned_quantity": 0,
                "no_order_reason": "REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT",
                "reduce_execution_semantic": "REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT",
            }
        ]
    }


def _strategy_intelligence(
    symbol: str,
    *,
    expected_edge_status: str = "DETERIORATING",
    entry_state: str = "CONTINUATION_WITH_CAUTION",
    admission_action: str = "ADD_REDUCED_ONLY",
    trend_state: str = "MIXED",
    relative_strength_state: str = "MIXED",
    participation_quality_state: str = "WEAK",
    exhaustion_risk_state: str = "ELEVATED_RISK",
    participation_risk_state: str = "ELEVATED_RISK",
    persistence_state: str = "MIXED",
    strong_medium_term_structure: bool | None = None,
    current_campaign_relative_return: float | None = None,
    run_id: str = "",
    profile_id: str = "",
) -> dict:
    return {
        "business_date": "2022-09-13",
        "feature_date": "2022-09-13",
        "run_id": run_id,
        "profile_id": profile_id,
        "future_information_used": False,
        "symbol_intelligence": {
            symbol: {
                "expected_edge": {"status": expected_edge_status, "future_information_used": False, "not_action_authority": True},
                "entry_admission": {
                    "entry_state": entry_state,
                    "admission_action": admission_action,
                    "future_information_used": False,
                    "consumed_evidence": {"strong_medium_term_structure": strong_medium_term_structure},
                },
                "continuation_quality": {
                    "status": "PASS",
                    "trend_health": {"state": trend_state, "as_of_date": "2022-09-13"},
                    "persistence": {"state": persistence_state, "as_of_date": "2022-09-13"},
                    "participation_quality": {"state": participation_quality_state, "as_of_date": "2022-09-13"},
                    "relative_strength": {"state": relative_strength_state, "as_of_date": "2022-09-13"},
                    "exhaustion_risk": {"state": exhaustion_risk_state, "as_of_date": "2022-09-13"},
                    "future_information_used": False,
                },
                "downside_risk": {"status": "PASS", "participation_risk": {"state": participation_risk_state, "as_of_date": "2022-09-13"}},
                "lifecycle_context": {
                    "position_campaign_id": f"campaign-{symbol}",
                    "campaign_identity_authority_status": "COMPLETE",
                    "campaign_age_business_days": 10,
                    "current_campaign_relative_return": current_campaign_relative_return,
                    "reduce_history_summary": {},
                },
            }
        },
    }


def _market_context() -> dict:
    return {"business_date": "2022-09-13", "feature_date": "2022-09-13", "regime_state": "RECOVERY", "trend_regime": "RECOVERY"}
