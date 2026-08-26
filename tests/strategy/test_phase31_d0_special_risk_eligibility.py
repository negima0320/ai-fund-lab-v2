from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.runtime_v2.market_status.buy_eligibility import evaluate_buy_eligibility
from ai_fund_lab_v2.strategy.portfolio_construction import _attach_strategy_intelligence
from ai_fund_lab_v2.strategy.strategy_intelligence import build_strategy_intelligence_payload, produce_strategy_intelligence_artifact

from tests.strategy.test_phase30_j_strategy_intelligence import (
    _candidate_summary,
    _current_summary,
    _opportunity_summary,
    _price_volatility_summary,
    _technical_summary,
    _write_json,
)


def test_phase31_d0_buy_eligibility_known_safe_special_risk_authority_passes() -> None:
    result = evaluate_buy_eligibility(
        symbol="11110",
        business_date="2022-08-10",
        mode="historical",
        listed_info={
            "Code": "11110",
            "Date": "2022-08-10",
            "current_listed": True,
            "MktNm": "Prime",
            "ProdCat": "011",
            "special_risk_coverage_state": "KNOWN",
            "special_risk_state": "NORMAL",
            "special_risk_eligibility": "BUY_ALLOWED",
        },
    )

    assert result.status == "PASS"
    assert result.buy_eligibility == "ELIGIBLE"
    assert result.special_risk_coverage_state == "KNOWN"
    assert result.special_risk_state == "NORMAL"
    assert result.special_risk_eligibility == "BUY_ALLOWED"


def test_phase31_d0_buy_eligibility_unknown_special_risk_coverage_requires_review() -> None:
    result = evaluate_buy_eligibility(
        symbol="11110",
        business_date="2022-08-10",
        mode="historical",
        listed_info={
            "Code": "11110",
            "Date": "2022-08-10",
            "current_listed": True,
            "special_risk_coverage_state": "UNKNOWN",
        },
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.buy_eligibility == "REVIEW_REQUIRED"
    assert result.eligible is False
    assert result.reason_code == "special_risk_coverage_review_required:UNKNOWN"


def test_phase31_d0_buy_eligibility_rejects_future_authority_without_consuming_it() -> None:
    result = evaluate_buy_eligibility(
        symbol="11110",
        business_date="2022-08-10",
        mode="historical",
        listed_info={
            "Code": "11110",
            "Date": "2022-08-11",
            "current_listed": True,
            "special_risk_coverage_state": "KNOWN",
            "special_risk_state": "NORMAL",
        },
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason_code == "market_status_future_authority_rejected"
    assert result.future_authority_used is False


def test_phase31_d0_strategy_intelligence_unknown_event_coverage_cannot_pass(tmp_path: Path) -> None:
    payload = _build_payload_with_event_status(
        tmp_path,
        event_status={"coverage_status": "UNKNOWN", "event_facts": []},
        action="BUY_NEW",
        held=False,
    )

    row = payload["symbol_intelligence"]["11110"]
    authority = row["eligibility"]["special_risk_authority"]
    assert row["downside_risk"]["event_uncertainty"]["state"] == "EVENT_COVERAGE_INCOMPLETE"
    assert row["eligibility"]["status"] == "REVIEW_REQUIRED"
    assert row["entry_admission"]["admission_action"] == "REVIEW_REQUIRED"
    assert "EVENT_COVERAGE_INCOMPLETE" in {
        item["fact_type"] for item in row["eligibility"]["review_required_facts"]
    }
    assert authority["authority_type"] == "SPECIAL_RISK_ELIGIBILITY_AUTHORITY"
    assert authority["coverage_state"] == "UNKNOWN"
    assert authority["eligibility_implication"] == "REVIEW_REQUIRED"
    assert row["eligibility"]["missing_required_authorities"] == ["complete_event_coverage_authority"]


def test_phase31_d0_strategy_intelligence_known_no_event_control_still_passes(tmp_path: Path) -> None:
    payload = _build_payload_with_event_status(
        tmp_path,
        event_status={"coverage_status": "AVAILABLE", "event_status": "KNOWN_NO_EVENT", "event_facts": []},
        action="BUY_NEW",
        held=False,
    )

    row = payload["symbol_intelligence"]["11110"]
    assert row["downside_risk"]["event_uncertainty"]["state"] == "MANAGEABLE"
    assert row["eligibility"]["status"] == "PASS"
    assert row["eligibility"]["special_risk_authority"]["coverage_state"] == "KNOWN"
    assert row["eligibility"]["special_risk_authority"]["risk_state"] == "NORMAL"
    assert row["eligibility"]["special_risk_authority"]["eligibility_implication"] == "BUY_ALLOWED"


def test_phase31_d0_strategy_intelligence_known_special_risk_requires_review(tmp_path: Path) -> None:
    payload = _build_payload_with_event_status(
        tmp_path,
        event_status={
            "coverage_status": "AVAILABLE",
            "event_status": "EVENT_PRESENT",
            "event_facts": [{"event_type": "SUPERVISION_STATUS", "event_status": "ANNOUNCED"}],
        },
        action="BUY_NEW",
        held=False,
    )

    row = payload["symbol_intelligence"]["11110"]
    assert row["downside_risk"]["event_uncertainty"]["state"] == "SPECIAL_RISK_PRESENT"
    assert row["eligibility"]["status"] == "REVIEW_REQUIRED"
    assert row["eligibility"]["special_risk_state"] == "REVIEW_REQUIRED"
    assert "SPECIAL_RISK_PRESENT" in {
        item["fact_type"] for item in row["eligibility"]["review_required_facts"]
    }


def test_phase31_d0_existing_position_exit_context_is_sell_independent(tmp_path: Path) -> None:
    payload = _build_payload_with_event_status(
        tmp_path,
        event_status={"coverage_status": "UNKNOWN", "event_facts": []},
        action="EXIT",
        held=True,
    )

    row = payload["symbol_intelligence"]["11110"]
    assert row["eligibility"]["status"] == "REVIEW_REQUIRED"
    assert row["current_decision"]["pm_action"] == "EXIT"
    assert row["entry_admission"]["sell_independent"] is True
    interpretation = row["strategy_intelligence_interpretation"]
    assert interpretation["current_action_preserved"] is True
    assert interpretation["reason_evidence"]["current_pm_action"] == "EXIT"
    assert interpretation["interpretation_summary"]["reduce_exit_authority_preservation"] is True


def test_phase31_d0_buy_add_requires_same_special_risk_authority(tmp_path: Path) -> None:
    payload = _build_payload_with_event_status(
        tmp_path,
        event_status={"coverage_status": "UNKNOWN", "event_facts": []},
        action="ADD",
        held=True,
    )

    row = payload["symbol_intelligence"]["11110"]
    assert row["eligibility"]["status"] == "REVIEW_REQUIRED"
    assert row["entry_admission"]["lifecycle_intent"] == "BUY_ADD"
    assert row["entry_admission"]["admission_action"] == "REVIEW_REQUIRED"
    assert row["entry_admission"]["admission_action"] != "ADD_ALLOWED"
    assert row["strategy_intelligence_interpretation"]["state"] == "ADD_WORTHINESS_EVIDENCE_SHADOW"
    assert row["strategy_intelligence_interpretation"]["current_action_preserved"] is True


def test_phase31_d0_portfolio_construction_blocks_new_buy_before_b10_priority(tmp_path: Path) -> None:
    paths = _write_source_artifacts(
        tmp_path,
        business_date="2022-08-10",
        event_status={"coverage_status": "UNKNOWN", "event_facts": []},
        action="BUY_NEW",
    )
    result = produce_strategy_intelligence_artifact(
        business_date="2022-08-10",
        candidate_summary=_candidate_summary("2022-08-10"),
        opportunity_summary=_opportunity_summary("2022-08-10"),
        current_summary=_current_summary("2022-08-10", held=False),
        technical_feature_summary=_technical_summary("2022-08-10"),
        price_volatility_summary=_price_volatility_summary("2022-08-10"),
        output_path=tmp_path / "strategy_intelligence.json",
        as_of="2022-08-10T00:00:00+00:00",
        production_consumer_connected=True,
        consumer_stage="PORTFOLIO_CONSTRUCTION",
        **paths,
    )
    members, reasons = _attach_strategy_intelligence(
        [
            {
                "security_code": "11110",
                "membership_intent": "BUY_NEW",
                "target_membership": True,
                "weight_intent": "TARGET",
                "current_position": False,
                "reason_codes": [],
            }
        ],
        strategy_intelligence_artifact_path=Path(result.artifact_path),
        business_date="2022-08-10",
    )

    assert members[0]["membership_intent"] == "UNRESOLVED"
    assert members[0]["target_membership"] is False
    assert members[0]["quality_action"] == "BUY_REVIEW_REQUIRED"
    assert "strategy_intelligence_eligibility_not_pass" in members[0]["reason_codes"]
    assert reasons == []


def _build_payload_with_event_status(
    tmp_path: Path,
    *,
    event_status: dict,
    action: str,
    held: bool,
) -> dict:
    paths = _write_source_artifacts(tmp_path, business_date="2022-08-10", event_status=event_status, action=action)
    payload, _ = build_strategy_intelligence_payload(
        business_date="2022-08-10",
        candidate_summary=_candidate_summary("2022-08-10"),
        opportunity_summary=_opportunity_summary("2022-08-10"),
        current_summary=_current_summary("2022-08-10", held=held),
        technical_feature_summary=_technical_summary("2022-08-10"),
        price_volatility_summary=_price_volatility_summary("2022-08-10"),
        as_of="2022-08-10T00:00:00+00:00",
        **paths,
    )
    return payload


def _write_source_artifacts(tmp_path: Path, *, business_date: str, event_status: dict, action: str) -> dict[str, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    market_context = _write_json(
        tmp_path / "market_context.json",
        {
            "schema_version": "market_context.v1",
            "business_date": business_date,
            "market_regime": "BULL",
            "artifact_hash": "market-hash",
        },
    )
    corporate_event = _write_json(
        tmp_path / "corporate_event.json",
        {
            "schema_version": "corporate_event.v1",
            "business_date": business_date,
            "coverage_status": "AVAILABLE",
            "symbol_event_facts": {"11110": event_status},
            "artifact_hash": "event-hash",
        },
    )
    buy_quality = _write_json(
        tmp_path / "buy_quality_decisions.json",
        {
            "schema_version": "buy_quality.v1",
            "business_date": business_date,
            "decisions": [{"security_code": "11110", "quality_action": action, "quality_band": "OBSERVED"}],
            "artifact_hash": "bq-hash",
        },
    )
    portfolio_construction = _write_json(
        tmp_path / "portfolio_construction.json",
        {
            "schema_version": "portfolio_construction.v1",
            "business_date": business_date,
            "portfolio_members": [
                {
                    "security_code": "11110",
                    "membership_intent": action,
                    "semantic_buy_type": "BUY_NEW",
                    "weight_intent": 0.1,
                    "runtime_opportunity_score": 0.72,
                    "current_position": action in {"ADD", "HOLD", "REDUCE", "EXIT"},
                }
            ],
            "artifact_hash": "pc-hash",
        },
    )
    position_sizing = _write_json(
        tmp_path / "position_sizing.json",
        {
            "schema_version": "position_sizing.v1",
            "business_date": business_date,
            "position_sizing": [{"security_code": "11110", "target_notional": 100000}],
            "artifact_hash": "ps-hash",
        },
    )
    position_management = _write_json(
        tmp_path / "position_management.json",
        {
            "schema_version": "position_management.v1",
            "business_date": business_date,
            "positions": [{"security_code": "11110", "action": action}],
            "artifact_hash": "pm-hash",
        },
    )
    runtime_planning = _write_json(
        tmp_path / "runtime_planning.json",
        {
            "schema_version": "runtime_planning.v1",
            "business_date": business_date,
            "plans": [{"security_code": "11110", "planning_intent": action, "planned_quantity": 100}],
            "artifact_hash": "rp-hash",
        },
    )
    return {
        "market_context_artifact_path": market_context,
        "corporate_event_artifact_path": corporate_event,
        "buy_quality_artifact_path": buy_quality,
        "portfolio_construction_artifact_path": portfolio_construction,
        "position_sizing_artifact_path": position_sizing,
        "position_management_artifact_path": position_management,
        "runtime_planning_artifact_path": runtime_planning,
    }
