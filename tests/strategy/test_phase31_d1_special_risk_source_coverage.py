from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.strategy.portfolio_construction import _attach_strategy_intelligence
from ai_fund_lab_v2.strategy.special_risk_coverage_diagnostic import (
    format_special_risk_coverage_summary,
    summarize_special_risk_coverage,
)
from ai_fund_lab_v2.strategy.strategy_intelligence import produce_strategy_intelligence_artifact

from tests.strategy.test_phase30_j_strategy_intelligence import (
    _candidate_summary,
    _current_summary,
    _opportunity_summary,
    _price_volatility_summary,
    _technical_summary,
    _write_json,
)


def test_phase31_d1_complete_source_absent_from_risk_set_is_known_safe(tmp_path: Path) -> None:
    payload = _payload(
        tmp_path,
        symbol_fact={
            "security_code": "11110",
            "business_date": "2022-08-10",
            "coverage_status": "AVAILABLE",
            "event_status": "KNOWN_NO_EVENT",
            "event_types": [],
        },
    )

    row = payload["symbol_intelligence"]["11110"]
    authority = row["eligibility"]["special_risk_authority"]
    assert row["eligibility"]["status"] == "PASS"
    assert authority["coverage_state"] == "KNOWN"
    assert authority["universe_coverage_state"] == "KNOWN_COMPLETE"
    assert authority["negative_evidence_safe_to_use"] is True
    assert authority["risk_state"] == "NORMAL"
    assert authority["eligibility_implication"] == "BUY_ALLOWED"


def test_phase31_d1_complete_source_present_in_risk_set_requires_review(tmp_path: Path) -> None:
    payload = _payload(
        tmp_path,
        symbol_fact={
            "security_code": "11110",
            "business_date": "2022-08-10",
            "coverage_status": "AVAILABLE",
            "event_status": "KNOWN_EVENT",
            "event_types": ["SUPERVISION_STATUS"],
            "event_dates": ["2022-08-10"],
        },
    )

    row = payload["symbol_intelligence"]["11110"]
    assert row["downside_risk"]["event_uncertainty"]["state"] == "SPECIAL_RISK_PRESENT"
    assert row["eligibility"]["status"] == "REVIEW_REQUIRED"
    assert row["eligibility"]["special_risk_authority"]["risk_state"] == "REVIEW_REQUIRED"
    assert row["eligibility"]["special_risk_authority"]["negative_evidence_safe_to_use"] is False


def test_phase31_d1_incomplete_source_absence_is_unknown_not_safe(tmp_path: Path) -> None:
    payload = _payload(
        tmp_path,
        coverage_status="PARTIAL",
        event_absence_authorized=False,
        symbol_fact={
            "security_code": "11110",
            "business_date": "2022-08-10",
            "coverage_status": "PARTIAL",
            "event_status": "UNKNOWN_DUE_TO_MISSING_COVERAGE",
            "event_types": [],
        },
    )

    row = payload["symbol_intelligence"]["11110"]
    authority = row["eligibility"]["special_risk_authority"]
    assert row["eligibility"]["status"] == "REVIEW_REQUIRED"
    assert authority["coverage_state"] == "UNKNOWN"
    assert authority["universe_coverage_state"] == "KNOWN_PARTIAL"
    assert authority["negative_evidence_safe_to_use"] is False
    assert row["eligibility"]["missing_required_authorities"] == ["complete_event_coverage_authority"]


def test_phase31_d1_stale_source_is_not_normal_pass(tmp_path: Path) -> None:
    payload = _payload(
        tmp_path,
        corporate_event_business_date="2022-08-09",
        symbol_fact={
            "security_code": "11110",
            "business_date": "2022-08-09",
            "coverage_status": "AVAILABLE",
            "event_status": "KNOWN_NO_EVENT",
            "event_types": [],
        },
    )

    row = payload["symbol_intelligence"]["11110"]
    assert row["eligibility"]["status"] == "REVIEW_REQUIRED"
    assert row["eligibility"]["special_risk_authority"]["coverage_state"] == "STALE"
    assert row["eligibility"]["missing_required_authorities"] == ["complete_event_coverage_authority"]
    assert row["downside_risk"]["event_uncertainty"]["missing_inputs"] == ["stale_event_coverage_authority"]


def test_phase31_d1_future_dated_source_is_rejected_not_consumed_as_safe(tmp_path: Path) -> None:
    payload = _payload(
        tmp_path,
        corporate_event_business_date="2022-08-11",
        symbol_fact={
            "security_code": "11110",
            "business_date": "2022-08-11",
            "coverage_status": "AVAILABLE",
            "event_status": "KNOWN_NO_EVENT",
            "event_types": [],
        },
    )

    row = payload["symbol_intelligence"]["11110"]
    assert payload["producer_result_status"] == "BLOCK"
    assert "corporate_event_future_feature_date" in payload["reason_codes"]
    assert row["eligibility"]["status"] == "REVIEW_REQUIRED"
    assert row["eligibility"]["special_risk_authority"]["coverage_state"] == "STALE"
    assert row["eligibility"]["future_information_used"] is False


def test_phase31_d1_authoritative_resolution_can_return_to_known_safe(tmp_path: Path) -> None:
    payload = _payload(
        tmp_path,
        symbol_fact={
            "security_code": "11110",
            "business_date": "2022-08-10",
            "coverage_status": "AVAILABLE",
            "event_status": "KNOWN_NO_EVENT",
            "event_types": [],
            "reason_codes": ["supervision_status_removed_by_complete_daily_source"],
        },
    )

    row = payload["symbol_intelligence"]["11110"]
    assert row["eligibility"]["status"] == "PASS"
    assert row["eligibility"]["special_risk_state"] == "NORMAL"


def test_phase31_d1_buy_add_uses_same_source_authority(tmp_path: Path) -> None:
    payload = _payload(
        tmp_path,
        action="ADD",
        held=True,
        symbol_fact={
            "security_code": "11110",
            "business_date": "2022-08-10",
            "coverage_status": "PARTIAL",
            "event_status": "UNKNOWN_DUE_TO_MISSING_COVERAGE",
            "event_types": [],
        },
    )

    row = payload["symbol_intelligence"]["11110"]
    assert row["entry_admission"]["lifecycle_intent"] == "BUY_ADD"
    assert row["entry_admission"]["admission_action"] == "REVIEW_REQUIRED"
    assert row["entry_admission"]["admission_action"] != "ADD_ALLOWED"


def test_phase31_d1_buy_authority_outage_preserves_exit_context(tmp_path: Path) -> None:
    payload = _payload(
        tmp_path,
        action="EXIT",
        held=True,
        coverage_status="MISSING",
        event_absence_authorized=False,
        symbol_fact={
            "security_code": "11110",
            "business_date": "2022-08-10",
            "coverage_status": "PARTIAL",
            "event_status": "UNKNOWN_DUE_TO_MISSING_COVERAGE",
            "event_types": [],
        },
    )

    row = payload["symbol_intelligence"]["11110"]
    assert row["eligibility"]["status"] == "REVIEW_REQUIRED"
    assert row["current_decision"]["pm_action"] == "EXIT"
    assert row["strategy_intelligence_interpretation"]["current_action_preserved"] is True
    assert row["strategy_intelligence_interpretation"]["interpretation_summary"]["reduce_exit_authority_preservation"] is True


def test_phase31_d1_source_conflict_is_review_not_permissive(tmp_path: Path) -> None:
    payload = _payload(
        tmp_path,
        source_authority_status="AUTHORITY_CONFLICT",
        reason_codes=["source_authority_conflict"],
        symbol_fact={
            "security_code": "11110",
            "business_date": "2022-08-10",
            "coverage_status": "AVAILABLE",
            "event_status": "KNOWN_NO_EVENT",
            "event_types": [],
            "reason_codes": ["source_authority_conflict"],
        },
    )

    row = payload["symbol_intelligence"]["11110"]
    assert row["eligibility"]["status"] == "REVIEW_REQUIRED"
    assert row["eligibility"]["special_risk_authority"]["coverage_state"] == "CONFLICT"
    assert row["downside_risk"]["event_uncertainty"]["missing_inputs"] == ["conflicting_event_coverage_authority"]


def test_phase31_d1_portfolio_construction_blocks_reviewed_new_buy_before_b10(tmp_path: Path) -> None:
    path = _artifact(
        tmp_path,
        symbol_fact={
            "security_code": "11110",
            "business_date": "2022-08-10",
            "coverage_status": "PARTIAL",
            "event_status": "UNKNOWN_DUE_TO_MISSING_COVERAGE",
            "event_types": [],
        },
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
        strategy_intelligence_artifact_path=path,
        business_date="2022-08-10",
    )

    assert reasons == []
    assert members[0]["target_membership"] is False
    assert members[0]["quality_action"] == "BUY_REVIEW_REQUIRED"
    assert "strategy_intelligence_eligibility_not_pass" in members[0]["reason_codes"]


def test_phase31_d1_read_only_coverage_diagnostic_counts_known_safe(tmp_path: Path) -> None:
    payload = _payload(
        tmp_path,
        symbol_fact={
            "security_code": "11110",
            "business_date": "2022-08-10",
            "coverage_status": "AVAILABLE",
            "event_status": "KNOWN_NO_EVENT",
            "event_types": [],
        },
    )

    summary = summarize_special_risk_coverage(payload)
    text = format_special_risk_coverage_summary(summary)
    assert summary["total_symbols"] == 1
    assert summary["known_safe"] == 1
    assert summary["coverage_rate"] == 1.0
    assert "DATE        TOTAL_SYMBOLS" in text
    assert "2022-08-10" in text


def _payload(
    tmp_path: Path,
    *,
    symbol_fact: dict,
    coverage_status: str = "AVAILABLE",
    event_absence_authorized: bool = True,
    corporate_event_business_date: str = "2022-08-10",
    source_authority_status: str = "PASS",
    reason_codes: list[str] | None = None,
    action: str = "BUY_NEW",
    held: bool = False,
) -> dict:
    path = _artifact(
        tmp_path,
        symbol_fact=symbol_fact,
        coverage_status=coverage_status,
        event_absence_authorized=event_absence_authorized,
        corporate_event_business_date=corporate_event_business_date,
        source_authority_status=source_authority_status,
        reason_codes=reason_codes,
        action=action,
        held=held,
    )
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def _artifact(
    tmp_path: Path,
    *,
    symbol_fact: dict,
    coverage_status: str = "AVAILABLE",
    event_absence_authorized: bool = True,
    corporate_event_business_date: str = "2022-08-10",
    source_authority_status: str = "PASS",
    reason_codes: list[str] | None = None,
    action: str = "BUY_NEW",
    held: bool = False,
) -> Path:
    paths = _write_source_artifacts(
        tmp_path,
        business_date="2022-08-10",
        corporate_event_business_date=corporate_event_business_date,
        symbol_fact=symbol_fact,
        coverage_status=coverage_status,
        event_absence_authorized=event_absence_authorized,
        source_authority_status=source_authority_status,
        reason_codes=reason_codes or [],
        action=action,
    )
    result = produce_strategy_intelligence_artifact(
        business_date="2022-08-10",
        candidate_summary=_candidate_summary("2022-08-10"),
        opportunity_summary=_opportunity_summary("2022-08-10"),
        current_summary=_current_summary("2022-08-10", held=held),
        technical_feature_summary=_technical_summary("2022-08-10"),
        price_volatility_summary=_price_volatility_summary("2022-08-10"),
        output_path=tmp_path / "strategy_intelligence.json",
        as_of="2022-08-10T00:00:00+00:00",
        production_consumer_connected=True,
        consumer_stage="PORTFOLIO_CONSTRUCTION",
        **paths,
    )
    return Path(result.artifact_path)


def _write_source_artifacts(
    tmp_path: Path,
    *,
    business_date: str,
    corporate_event_business_date: str,
    symbol_fact: dict,
    coverage_status: str,
    event_absence_authorized: bool,
    source_authority_status: str,
    reason_codes: list[str],
    action: str,
) -> dict[str, Path]:
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
            "business_date": corporate_event_business_date,
            "feature_date": corporate_event_business_date,
            "coverage_status": coverage_status,
            "overall_coverage_status": coverage_status,
            "source_authority_status": source_authority_status,
            "producer_result_status": "PASS" if source_authority_status == "PASS" else "REVIEW_REQUIRED",
            "coverage_contract": {"event_absence_authorized": event_absence_authorized},
            "source_coverage_semantics": "FULL" if event_absence_authorized else "PARTIAL",
            "symbol_event_facts": [symbol_fact],
            "known_no_event_symbols": ["11110"] if symbol_fact.get("event_status") == "KNOWN_NO_EVENT" else [],
            "unknown_symbols": ["11110"] if str(symbol_fact.get("event_status") or "").startswith("UNKNOWN") else [],
            "known_event_symbols": ["11110"] if symbol_fact.get("event_status") == "KNOWN_EVENT" else [],
            "reason_codes": reason_codes,
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
                    "semantic_buy_type": "BUY_ADD" if action == "ADD" else "BUY_NEW",
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
