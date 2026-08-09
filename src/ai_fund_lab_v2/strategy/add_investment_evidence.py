from __future__ import annotations

import math
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "add_investment_evidence.v1"
ARTIFACT_SCHEMA_VERSION = "add_investment_evidence_artifact.v1"
PRODUCER_VERSION = "phase28_d55_a_add_investment_evidence_resolver.v1"


def resolve_add_investment_evidence(
    *,
    row: Mapping[str, Any],
    members: list[dict[str, Any]],
    business_date: str,
) -> dict[str, Any]:
    symbol = str(row.get("security_code") or row.get("symbol") or "")
    campaign = _resolve_campaign_continuation(row)
    expected_edge = _resolve_expected_edge(row, business_date=business_date)
    opportunity_cost = _resolve_opportunity_cost(row=row, members=members)
    no_loss = _resolve_no_loss_averaging(row)
    incremental_value = _resolve_incremental_value(
        row,
        expected_edge=expected_edge,
        campaign=campaign,
        opportunity_cost=opportunity_cost,
        no_loss=no_loss,
    )
    checks = {
        "campaign_continuation": campaign["status"],
        "expected_edge": expected_edge["status"],
        "incremental_value": incremental_value["status"],
        "opportunity_cost": opportunity_cost["status"],
        "no_loss_averaging": no_loss["status"],
    }
    reason_codes = sorted(
        {
            reason
            for section in (campaign, expected_edge, incremental_value, opportunity_cost, no_loss)
            for reason in section.get("reason_codes", [])
        }
    )
    final_pass = all(status == "PASS" for status in checks.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "producer_version": PRODUCER_VERSION,
        "producer_result_status": "PASS" if final_pass else "REVIEW_REQUIRED",
        "business_date": business_date,
        "symbol": symbol,
        "pm_action": str(row.get("pm_action") or ""),
        "position_campaign_id": campaign.get("position_campaign_id") or "",
        "campaign_continuation": campaign,
        "expected_edge": expected_edge,
        "incremental_value": incremental_value,
        "opportunity_cost": opportunity_cost,
        "no_loss_averaging": no_loss,
        "final_add_eligibility": "PASS" if final_pass else "FAIL_CLOSED",
        "eligibility_checks": checks,
        "temporal_authority": {
            "business_date": business_date,
            "point_in_time": expected_edge["temporal_authority"]["status"] != "FAIL",
            "future_evidence_used": expected_edge["temporal_authority"].get("future_evidence_used") is True,
            "baseline_temporally_valid": expected_edge["temporal_authority"].get("baseline_temporally_valid") is True,
            "implicit_latest_fallback_used": False,
        },
        "source_lineage": _source_lineage(row),
        "reason_codes": reason_codes,
    }


def build_add_investment_evidence_payload(
    *,
    business_date: str,
    member_rows: list[Mapping[str, Any]],
) -> dict[str, Any]:
    evidence_rows = [
        resolve_add_investment_evidence(row=row, members=[dict(item) for item in member_rows], business_date=business_date)
        for row in member_rows
        if bool(row.get("current_position")) and str(row.get("pm_action") or "").upper() == "ADD"
    ]
    pass_count = sum(1 for row in evidence_rows if row["final_add_eligibility"] == "PASS")
    fail_count = sum(1 for row in evidence_rows if row["final_add_eligibility"] != "PASS")
    payload = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "producer_version": PRODUCER_VERSION,
        "business_date": business_date,
        "producer_result_status": "PASS" if fail_count == 0 else "REVIEW_REQUIRED",
        "evidence_schema_version": SCHEMA_VERSION,
        "pm_add_count": len(evidence_rows),
        "pass_count": pass_count,
        "fail_closed_count": fail_count,
        "evidence": evidence_rows,
        "reason_codes": sorted({reason for row in evidence_rows for reason in row.get("reason_codes", [])}),
        "temporal_safety": {
            "point_in_time": all((row.get("temporal_authority") or {}).get("future_evidence_used") is not True for row in evidence_rows),
            "future_leakage_used": any((row.get("temporal_authority") or {}).get("future_evidence_used") is True for row in evidence_rows),
            "implicit_latest_fallback_used": False,
        },
    }
    payload["artifact_hash"] = stable_payload_hash(payload)
    return payload


def produce_add_investment_evidence_artifact(
    *,
    business_date: str,
    member_rows: list[Mapping[str, Any]],
    output_path: Path | str,
) -> dict[str, Any]:
    payload = build_add_investment_evidence_payload(business_date=business_date, member_rows=member_rows)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def stable_payload_hash(payload: Any) -> str:
    clean = {key: value for key, value in payload.items() if key != "artifact_hash"} if isinstance(payload, dict) else payload
    encoded = json.dumps(clean, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _resolve_campaign_continuation(row: Mapping[str, Any]) -> dict[str, Any]:
    explicit = _status_value(row, ("campaign_continuation_status", "add_campaign_continuation_status"))
    current_campaign = _first_text(
        row,
        (
            "current_position_campaign_id",
            "pm_position_campaign_id",
            "position_campaign_id",
            "campaign_id",
            "lifecycle_reference",
        ),
    )
    opportunity_campaign = _first_text(
        row,
        (
            "opportunity_position_campaign_id",
            "opportunity_campaign_id",
            "add_position_campaign_id",
        ),
    )
    if explicit:
        status = "PASS" if explicit == "PASS" else "FAIL_CLOSED"
        return {
            "status": status,
            "state": explicit,
            "position_campaign_id": current_campaign or opportunity_campaign,
            "current_campaign_id": current_campaign,
            "opportunity_campaign_id": opportunity_campaign,
            "authority": "explicit_add_campaign_continuation_status",
            "reason_codes": [] if status == "PASS" else ["ADD_CAMPAIGN_CONTINUATION_FAIL"],
        }
    if current_campaign and opportunity_campaign and current_campaign == opportunity_campaign:
        return {
            "status": "PASS",
            "state": "PASS",
            "position_campaign_id": current_campaign,
            "current_campaign_id": current_campaign,
            "opportunity_campaign_id": opportunity_campaign,
            "authority": "same_campaign_identity_match",
            "reason_codes": [],
        }
    return {
        "status": "FAIL_CLOSED",
        "state": "UNKNOWN" if not current_campaign or not opportunity_campaign else "MISMATCH",
        "position_campaign_id": current_campaign or opportunity_campaign,
        "current_campaign_id": current_campaign,
        "opportunity_campaign_id": opportunity_campaign,
        "authority": "campaign_identity_required",
        "reason_codes": ["ADD_CAMPAIGN_CONTINUATION_FAIL"],
    }


def _resolve_expected_edge(row: Mapping[str, Any], *, business_date: str) -> dict[str, Any]:
    current_score = _finite_number(row.get("expected_edge_current_score", row.get("runtime_opportunity_score")))
    baseline_score = _finite_number(
        row.get(
            "expected_edge_baseline_score",
            row.get("previous_expected_edge_score", row.get("entry_expected_edge_baseline_score")),
        )
    )
    baseline_date = _first_text(
        row,
        (
            "expected_edge_baseline_business_date",
            "previous_expected_edge_business_date",
            "entry_expected_edge_baseline_business_date",
            "add_expected_edge_baseline_business_date",
        ),
    )
    baseline_campaign_id = _first_text(
        row,
        (
            "expected_edge_baseline_campaign_id",
            "position_campaign_id",
            "campaign_id",
        ),
    )
    explicit_state = str(row.get("expected_edge_improvement_state") or row.get("add_expected_edge_improvement_state") or "").upper()
    temporal = _baseline_temporal_authority(baseline_date=baseline_date, business_date=business_date)
    if temporal["status"] == "FAIL":
        state = "UNKNOWN"
    elif explicit_state in {"IMPROVING", "STABLE_ADEQUATE", "WEAKENING", "INSUFFICIENT"} and current_score is not None and baseline_score is not None:
        state = explicit_state
    elif current_score is not None and baseline_score is not None and temporal["baseline_temporally_valid"]:
        state = "IMPROVING" if current_score > baseline_score else ("STABLE_ADEQUATE" if current_score == baseline_score else "WEAKENING")
    elif explicit_state == "UNKNOWN":
        state = "UNKNOWN"
    else:
        state = "UNKNOWN"
    pass_state = state == "IMPROVING" or (
        state == "STABLE_ADEQUATE"
        and str(row.get("stable_adequate_opportunity_cost_superior") or "").upper() == "PASS"
    )
    reasons: list[str] = []
    if not pass_state:
        reasons.append("ADD_EXPECTED_EDGE_UNKNOWN_FAIL_CLOSED" if state == "UNKNOWN" else f"ADD_EXPECTED_EDGE_{state}")
    return {
        "status": "PASS" if pass_state else "FAIL_CLOSED",
        "state": state,
        "current_score": current_score,
        "baseline_score": baseline_score,
        "baseline_type": str(row.get("expected_edge_baseline_type") or ("same_campaign_latest_accepted_pm_decision" if baseline_score is not None else "UNKNOWN")),
        "baseline_business_date": baseline_date,
        "baseline_campaign_id": baseline_campaign_id,
        "current_business_date": business_date,
        "comparison_status": "PASS" if pass_state else "FAIL_CLOSED",
        "temporal_authority": temporal,
        "unknown_fail_closed": state == "UNKNOWN",
        "reason_codes": reasons,
    }


def _resolve_incremental_value(
    row: Mapping[str, Any],
    *,
    expected_edge: Mapping[str, Any],
    campaign: Mapping[str, Any],
    opportunity_cost: Mapping[str, Any],
    no_loss: Mapping[str, Any],
) -> dict[str, Any]:
    explicit = str(row.get("incremental_investment_value_state") or row.get("add_incremental_investment_value_state") or "").upper()
    if explicit in {"POSITIVE", "NEUTRAL", "NEGATIVE"}:
        state = explicit
    elif (
        expected_edge.get("status") == "PASS"
        and campaign.get("status") == "PASS"
        and opportunity_cost.get("status") == "PASS"
        and no_loss.get("status") == "PASS"
    ):
        state = "POSITIVE"
    elif explicit == "UNKNOWN":
        state = "UNKNOWN"
    else:
        state = "UNKNOWN"
    status = "PASS" if state == "POSITIVE" else "FAIL_CLOSED"
    return {
        "status": status,
        "state": state,
        "authority": "explicit_incremental_investment_value_state" if explicit else "existing_pc_expected_edge_cascade_contract",
        "reason_codes": [] if status == "PASS" else [f"ADD_INCREMENTAL_VALUE_{state}"],
    }


def _resolve_opportunity_cost(*, row: Mapping[str, Any], members: list[dict[str, Any]]) -> dict[str, Any]:
    explicit = str(row.get("opportunity_cost_status") or row.get("add_opportunity_cost_status") or "").upper()
    score = _finite_number(row.get("runtime_opportunity_score"))
    new_scores = [
        _finite_number(member.get("runtime_opportunity_score"))
        for member in members
        if not member.get("current_position") and str(member.get("membership_intent") or "") == "ADD_CANDIDATE"
    ]
    comparable = [value for value in new_scores if value is not None]
    best_new = max(comparable) if comparable else None
    if explicit in {"PASS", "FAIL", "UNKNOWN"}:
        status = "PASS" if explicit == "PASS" else "FAIL_CLOSED"
        state = explicit
    elif score is None:
        status = "FAIL_CLOSED"
        state = "UNKNOWN"
    elif best_new is not None and best_new > score:
        status = "FAIL_CLOSED"
        state = "NEW_BUY_SUPERIOR"
    else:
        status = "PASS"
        state = "PASS"
    return {
        "status": status,
        "state": state,
        "candidate_type": "EXISTING_POSITION_ADD",
        "candidate_symbol": str(row.get("security_code") or row.get("symbol") or ""),
        "candidate_score": score,
        "best_new_buy_score": best_new,
        "comparison_result": state,
        "authority": "explicit_opportunity_cost_status" if explicit else "portfolio_construction_same_day_score_competition",
        "reason_codes": [] if status == "PASS" else ["ADD_OPPORTUNITY_COST_FAIL"],
    }


def _resolve_no_loss_averaging(row: Mapping[str, Any]) -> dict[str, Any]:
    explicit = _status_value(row, ("no_loss_averaging_status", "add_no_loss_averaging_status"))
    reasons = [str(reason) for reason in row.get("source_pm_reason_codes") or row.get("reason_codes") or []]
    lowered = {reason.lower() for reason in reasons}
    if explicit:
        status = "PASS" if explicit == "PASS" else "FAIL_CLOSED"
        state = explicit
        authority = "explicit_no_loss_averaging_status"
    elif "no_loss_averaging" in lowered:
        status = "PASS"
        state = "PASS"
        authority = "pm_reason_code:no_loss_averaging"
    elif "loss_averaging_violation" in lowered or "averaging_down_block" in lowered:
        status = "FAIL_CLOSED"
        state = "FAIL"
        authority = "pm_reason_code:loss_averaging_violation"
    else:
        status = "FAIL_CLOSED"
        state = "UNKNOWN"
        authority = "no_loss_averaging_evidence_required"
    return {
        "status": status,
        "state": state,
        "authority": authority,
        "source_pm_reason_codes": reasons,
        "reason_codes": [] if status == "PASS" else ["ADD_NO_LOSS_AVERAGING_FAIL"],
    }


def _baseline_temporal_authority(*, baseline_date: str, business_date: str) -> dict[str, Any]:
    if not baseline_date:
        return {
            "status": "FAIL_CLOSED",
            "baseline_temporally_valid": False,
            "future_evidence_used": False,
            "reason": "baseline_business_date_required",
        }
    if baseline_date > business_date:
        return {
            "status": "FAIL",
            "baseline_temporally_valid": False,
            "future_evidence_used": True,
            "reason": "future_baseline_forbidden",
        }
    return {
        "status": "PASS",
        "baseline_temporally_valid": True,
        "future_evidence_used": False,
        "reason": "baseline_business_date_lte_current_business_date",
    }


def _status_value(row: Mapping[str, Any], fields: tuple[str, ...]) -> str:
    for field in fields:
        value = str(row.get(field) or "").upper()
        if value in {"PASS", "FAIL", "UNKNOWN", "BLOCK", "REVIEW_REQUIRED", "FAIL_CLOSED"}:
            return "PASS" if value == "PASS" else value
    return ""


def _first_text(row: Mapping[str, Any], fields: tuple[str, ...]) -> str:
    for field in fields:
        value = str(row.get(field) or "").strip()
        if value:
            return value
    return ""


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    if not math.isfinite(numeric):
        return None
    return numeric


def _source_lineage(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "opportunity_reference": str(row.get("opportunity_reference") or ""),
        "position_management_reference": str(row.get("position_management_reference") or row.get("source_pm_decision_ref") or ""),
        "current_position_reference": str(row.get("current_position_reference") or ""),
        "runtime_opportunity_score_authority": dict(row.get("runtime_opportunity_score_authority") or {}),
        "source_pm_reason_codes": list(row.get("source_pm_reason_codes") or []),
    }
