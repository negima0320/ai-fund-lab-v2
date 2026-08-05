from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "position_intent.v1"
ARTIFACT_TYPE = "position_intent"
PRODUCER_VERSION = "phase27_d2a_position_intent_shadow_producer.v1"
AUTHORITY_MODE = "SHADOW"
DECISION_EFFECT = "NONE"
ALLOWED_INTENTS = {"BUY_NEW", "ADD", "HOLD", "REDUCE", "EXIT", "NO_ACTION", "UNRESOLVED"}
PM_INTENT_MAP = {
    "ADD": "ADD",
    "HOLD": "HOLD",
    "REDUCE": "REDUCE",
    "EXIT": "EXIT",
}
REQUIRED_ROW_FIELDS = (
    "schema_version",
    "artifact_type",
    "authority_mode",
    "decision_effect",
    "run_id",
    "business_date",
    "accepted_generation",
    "symbol",
    "position_campaign_id",
    "current_position_state",
    "current_quantity",
    "current_notional",
    "current_weight",
    "candidate_id",
    "opportunity_id",
    "opportunity_rank",
    "opportunity_score",
    "quality_decision_id",
    "quality_score",
    "quality_action",
    "pm_decision_id",
    "pm_intent",
    "momentum_continuation_state",
    "momentum_authority_mode",
    "incremental_investment_eligibility",
    "incremental_eligibility_authority_mode",
    "proposed_position_intent",
    "intent_reason_codes",
    "intent_summary",
    "input_artifact_refs",
    "lineage",
    "evidence_status",
    "missing_required_inputs",
    "review_status",
)


class PositionIntentError(RuntimeError):
    pass


class PositionIntentSchemaError(PositionIntentError):
    pass


@dataclass(frozen=True)
class PositionIntentProducerResult:
    status: str
    reason: str
    artifact_path: str
    artifact_hash: str
    payload: dict[str, Any]
    evidence: dict[str, Any]


def default_runtime_artifact_path(runtime_root: Path | str, business_date: str) -> Path:
    return Path(runtime_root) / "strategy_artifacts" / "position_intent" / business_date / "position_intent.json"


def produce_position_intent_artifact(
    *,
    runtime_root: Path | str,
    business_date: str,
    run_id: str,
    accepted_generation: str | None,
    output_path: Path | str | None = None,
    pm_artifact_path: Path | str | None = None,
    candidate_artifact_path: Path | str | None = None,
    opportunity_artifact_path: Path | str | None = None,
    quality_artifact_path: Path | str | None = None,
    current_artifact_path: Path | str | None = None,
    market_context_artifact_path: Path | str | None = None,
    portfolio_policy_artifact_path: Path | str | None = None,
    pending_artifact_path: Path | str | None = None,
    safety_artifact_path: Path | str | None = None,
    corporate_event_artifact_path: Path | str | None = None,
    as_of: str | None = None,
) -> PositionIntentProducerResult:
    root = Path(runtime_root)
    resolved_output = Path(output_path) if output_path is not None else default_runtime_artifact_path(root, business_date)
    payload, evidence = build_position_intent_payload(
        business_date=business_date,
        run_id=run_id,
        accepted_generation=accepted_generation,
        pm_artifact_path=pm_artifact_path,
        candidate_artifact_path=candidate_artifact_path,
        opportunity_artifact_path=opportunity_artifact_path,
        quality_artifact_path=quality_artifact_path,
        current_artifact_path=current_artifact_path,
        market_context_artifact_path=market_context_artifact_path,
        portfolio_policy_artifact_path=portfolio_policy_artifact_path,
        pending_artifact_path=pending_artifact_path,
        safety_artifact_path=safety_artifact_path,
        corporate_event_artifact_path=corporate_event_artifact_path,
        as_of=as_of,
    )
    validate_position_intent_artifact(payload)
    artifact_hash = position_intent_hash(payload)
    final_payload = {**payload, "artifact_hash": artifact_hash}
    _write_json(resolved_output, final_payload)
    return PositionIntentProducerResult(
        status=str(final_payload["artifact_status"]),
        reason=",".join(final_payload.get("reason_codes") or []),
        artifact_path=str(resolved_output),
        artifact_hash=artifact_hash,
        payload=final_payload,
        evidence=evidence,
    )


def build_position_intent_payload(
    *,
    business_date: str,
    run_id: str,
    accepted_generation: str | None,
    pm_artifact_path: Path | str | None = None,
    candidate_artifact_path: Path | str | None = None,
    opportunity_artifact_path: Path | str | None = None,
    quality_artifact_path: Path | str | None = None,
    current_artifact_path: Path | str | None = None,
    market_context_artifact_path: Path | str | None = None,
    portfolio_policy_artifact_path: Path | str | None = None,
    pending_artifact_path: Path | str | None = None,
    safety_artifact_path: Path | str | None = None,
    corporate_event_artifact_path: Path | str | None = None,
    as_of: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_iso_date(business_date, field="business_date")
    if not str(run_id or "").strip():
        raise PositionIntentSchemaError("run_id is required")
    generated_at = as_of or f"{business_date}T00:00:00+00:00"
    refs = _input_refs(
        pm_artifact_path=pm_artifact_path,
        candidate_artifact_path=candidate_artifact_path,
        opportunity_artifact_path=opportunity_artifact_path,
        quality_artifact_path=quality_artifact_path,
        current_artifact_path=current_artifact_path,
        market_context_artifact_path=market_context_artifact_path,
        portfolio_policy_artifact_path=portfolio_policy_artifact_path,
        pending_artifact_path=pending_artifact_path,
        safety_artifact_path=safety_artifact_path,
        corporate_event_artifact_path=corporate_event_artifact_path,
    )
    reason_codes: list[str] = []
    status = "PASS"
    intents: list[dict[str, Any]] = []
    pm_payload = _read_json_if_present(pm_artifact_path)
    if pm_artifact_path is None:
        reason_codes.append("PM_ARTIFACT_NOT_YET_CONNECTED")
        status = "REVIEW_REQUIRED"
    elif pm_payload is None:
        reason_codes.append("PM_ARTIFACT_MISSING")
        status = "REVIEW_REQUIRED"
    elif str(pm_payload.get("business_date") or "") != business_date:
        reason_codes.append("PM_ARTIFACT_BUSINESS_DATE_MISMATCH")
        status = "REVIEW_REQUIRED"
    elif pm_payload.get("accepted_generation") not in (None, "", accepted_generation):
        reason_codes.append("ACCEPTED_GENERATION_MISMATCH")
        status = "REVIEW_REQUIRED"
    else:
        for decision in _pm_decisions(pm_payload):
            intents.append(
                _row_from_pm_decision(
                    decision=decision,
                    business_date=business_date,
                    run_id=run_id,
                    accepted_generation=accepted_generation,
                    refs=refs,
                    pm_artifact_path=pm_artifact_path,
                )
            )
    if opportunity_artifact_path is not None or candidate_artifact_path is not None or quality_artifact_path is not None:
        buy_rows = _shadow_buy_candidate_rows(
            business_date=business_date,
            run_id=run_id,
            accepted_generation=accepted_generation,
            refs=refs,
            candidate_artifact_path=candidate_artifact_path,
            opportunity_artifact_path=opportunity_artifact_path,
            quality_artifact_path=quality_artifact_path,
        )
        intents.extend(buy_rows)
        if buy_rows:
            status = "REVIEW_REQUIRED" if status == "PASS" else status
            reason_codes.append("BUY_NEW_SHADOW_UNRESOLVED_INCREMENTAL_ELIGIBILITY_NOT_CONNECTED")
    source_status = _scope_source_status(refs)
    missing_sources = [name for name, ref in refs.items() if ref["status"] in {"MISSING", "NOT_YET_CONNECTED"}]
    if missing_sources and status == "PASS":
        status = "REVIEW_REQUIRED"
    reason_codes.extend(f"SCOPE_SOURCE_{name.upper()}_{refs[name]['status']}" for name in missing_sources)
    duplicate_keys = _duplicate_dedup_keys(intents)
    if duplicate_keys:
        status = "BLOCK"
        reason_codes.append("DUPLICATE_DEDUP_KEY")
        for row in intents:
            if _dedup_key(row) in duplicate_keys:
                row["evidence_status"] = "BLOCK"
                row["review_status"] = "BLOCK"
                row["missing_required_inputs"].append("duplicate_dedup_key")
                row["intent_reason_codes"].append("DUPLICATE_DEDUP_KEY")
    reason_codes = sorted(set(reason_codes))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "authority_mode": AUTHORITY_MODE,
        "decision_effect": DECISION_EFFECT,
        "producer_version": PRODUCER_VERSION,
        "run_id": run_id,
        "business_date": business_date,
        "accepted_generation": accepted_generation,
        "generated_at": generated_at,
        "artifact_status": status,
        "review_status": status,
        "reason_codes": reason_codes,
        "scope_contract": {
            "scope_sources": [
                "Current Holdings",
                "BUY-eligible candidates reaching required Strategy stage",
                "Pending / Open-order symbols",
                "Mandatory Safety Review symbols",
                "Corporate-event affected symbols",
            ],
            "connected_scope_sources": [name for name, ref in refs.items() if ref["status"] == "PRESENT"],
            "missing_or_not_yet_connected_scope_sources": missing_sources,
            "dedup_key": ["run_id", "business_date", "symbol", "accepted_generation", "position_campaign_id"],
            "full_candidate_universe_role": "OBSERVABILITY_ONLY",
        },
        "input_artifact_refs": refs,
        "summary": {
            "intent_count": len(intents),
            "intent_counts": _counts(row.get("proposed_position_intent") for row in intents),
            "pm_intent_counts": _counts(row.get("pm_intent") for row in intents if row.get("pm_intent")),
            "duplicate_dedup_key_count": len(duplicate_keys),
            "source_status": source_status,
            "decision_effect_zero": True,
        },
        "intents": intents,
    }
    evidence = {
        "schema_path": "docs/02_architecture/schemas/position_intent.v1.schema.json",
        "producer": "ai_fund_lab_v2.strategy.position_intent",
        "authority_mode": AUTHORITY_MODE,
        "decision_effect": DECISION_EFFECT,
        "consumer_connection": "NONE_IN_D2_A",
        "decision_effect_zero_fields": [
            "target_weight_not_written",
            "target_notional_not_written",
            "target_quantity_not_written",
            "quantity_delta_not_written",
            "planning_intent_not_written",
            "pending_not_written",
            "approval_not_written",
            "submit_not_written",
        ],
    }
    return payload, evidence


def validate_position_intent_artifact(payload: Mapping[str, Any]) -> dict[str, Any]:
    _require(payload, "schema_version", SCHEMA_VERSION)
    _require(payload, "artifact_type", ARTIFACT_TYPE)
    _require(payload, "authority_mode", AUTHORITY_MODE)
    _require(payload, "decision_effect", DECISION_EFFECT)
    _require_nonempty(payload, "run_id")
    _validate_iso_date(str(payload.get("business_date") or ""), field="business_date")
    if payload.get("artifact_status") not in {"PASS", "REVIEW_REQUIRED", "BLOCK"}:
        raise PositionIntentSchemaError("artifact_status must be PASS/REVIEW_REQUIRED/BLOCK")
    rows = payload.get("intents")
    if not isinstance(rows, list):
        raise PositionIntentSchemaError("intents must be a list")
    keys: set[tuple[Any, ...]] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise PositionIntentSchemaError("intent row must be object")
        for field in REQUIRED_ROW_FIELDS:
            if field not in row:
                raise PositionIntentSchemaError(f"intent row missing required field: {field}")
        _require(row, "schema_version", SCHEMA_VERSION)
        _require(row, "artifact_type", "position_intent_row")
        _require(row, "authority_mode", AUTHORITY_MODE)
        _require(row, "decision_effect", DECISION_EFFECT)
        _validate_iso_date(str(row.get("business_date") or ""), field="row.business_date")
        if row.get("business_date") != payload.get("business_date"):
            raise PositionIntentSchemaError("row business_date mismatch")
        intent = str(row.get("proposed_position_intent") or "")
        if intent not in ALLOWED_INTENTS:
            raise PositionIntentSchemaError(f"invalid proposed_position_intent: {intent}")
        key = _dedup_key(row)
        if key in keys:
            raise PositionIntentSchemaError("duplicate dedup key")
        keys.add(key)
        forbidden = {"target_weight", "target_weight_candidate", "target_notional", "target_notional_candidate", "target_quantity", "target_quantity_candidate", "quantity_delta", "quantity_delta_candidate", "planning_intent", "pending_item_id", "approval_id", "submit_command"}
        present_forbidden = forbidden & set(row)
        if present_forbidden:
            raise PositionIntentSchemaError(f"position_intent row contains downstream authority fields: {sorted(present_forbidden)}")
    return {"status": "PASS", "row_count": len(rows)}


def position_intent_hash(payload: Mapping[str, Any]) -> str:
    canonical = dict(payload)
    canonical.pop("artifact_hash", None)
    return hashlib.sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _row_from_pm_decision(
    *,
    decision: Mapping[str, Any],
    business_date: str,
    run_id: str,
    accepted_generation: str | None,
    refs: Mapping[str, Any],
    pm_artifact_path: Path | str | None,
) -> dict[str, Any]:
    pm_intent = str(decision.get("decision") or decision.get("action") or "UNRESOLVED").upper()
    proposed = PM_INTENT_MAP.get(pm_intent, "UNRESOLVED")
    missing: list[str] = []
    symbol = str(decision.get("symbol") or decision.get("security_code") or "").strip()
    if not symbol:
        missing.append("symbol")
    if proposed == "UNRESOLVED":
        missing.append("pm_intent_resolved")
    review_status = "PASS" if not missing else "REVIEW_REQUIRED"
    quantity = _number(decision.get("runtime_position_quantity") or decision.get("current_quantity") or decision.get("quantity"))
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "position_intent_row",
        "authority_mode": AUTHORITY_MODE,
        "decision_effect": DECISION_EFFECT,
        "run_id": run_id,
        "business_date": business_date,
        "accepted_generation": accepted_generation,
        "symbol": symbol,
        "position_campaign_id": _nullable_text(decision.get("position_campaign_id") or decision.get("position_lifecycle_id") or decision.get("campaign_id")),
        "current_position_state": "OPEN_POSITION",
        "current_quantity": quantity,
        "current_notional": _number(decision.get("current_notional") or decision.get("market_value")),
        "current_weight": _number(decision.get("current_weight")),
        "candidate_id": None,
        "opportunity_id": _nullable_text(decision.get("opportunity_id")),
        "opportunity_rank": _number(decision.get("opportunity_rank") or decision.get("buy_rank")),
        "opportunity_score": _number(decision.get("opportunity_score") or decision.get("expected_edge_score")),
        "quality_decision_id": None,
        "quality_score": None,
        "quality_action": None,
        "pm_decision_id": _nullable_text(decision.get("decision_id")),
        "pm_intent": pm_intent,
        "momentum_continuation_state": "INSUFFICIENT_EVIDENCE",
        "momentum_authority_mode": "SHADOW",
        "incremental_investment_eligibility": "INSUFFICIENT_EVIDENCE",
        "incremental_eligibility_authority_mode": "SHADOW",
        "proposed_position_intent": proposed,
        "intent_reason_codes": ["PM_INTENT_SHADOW_MAPPED", "DECISION_EFFECT_NONE"],
        "intent_summary": f"Shadow mapped PM {pm_intent} to proposed intent {proposed}; no downstream decision effect.",
        "input_artifact_refs": dict(refs),
        "lineage": {
            "source_pm_artifact": str(pm_artifact_path or ""),
            "source_pm_decision_id": _nullable_text(decision.get("decision_id")) or "MISSING",
            "source_candidate_artifact": refs["candidate"].get("path") or "NOT_YET_CONNECTED",
            "source_candidate_id": "NOT_APPLICABLE",
            "source_opportunity_artifact": refs["opportunity"].get("path") or "NOT_YET_CONNECTED",
            "source_opportunity_id": _nullable_text(decision.get("opportunity_id")) or "MISSING",
            "source_quality_artifact": refs["quality"].get("path") or "NOT_YET_CONNECTED",
            "source_quality_decision_id": "NOT_YET_CONNECTED",
            "source_current_artifact": refs["current"].get("path") or "NOT_YET_CONNECTED",
            "source_market_context_artifact": refs["market_context"].get("path") or "NOT_YET_CONNECTED",
            "source_portfolio_policy_artifact": refs["portfolio_policy"].get("path") or "NOT_YET_CONNECTED",
            "accepted_generation": accepted_generation,
            "business_date": business_date,
        },
        "evidence_status": review_status,
        "missing_required_inputs": missing,
        "review_status": review_status,
    }


def _shadow_buy_candidate_rows(
    *,
    business_date: str,
    run_id: str,
    accepted_generation: str | None,
    refs: Mapping[str, Any],
    candidate_artifact_path: Path | str | None,
    opportunity_artifact_path: Path | str | None,
    quality_artifact_path: Path | str | None,
) -> list[dict[str, Any]]:
    payload = _read_json_if_present(opportunity_artifact_path) or _read_json_if_present(candidate_artifact_path) or {}
    rows = _extract_rows(payload)
    result: list[dict[str, Any]] = []
    for row in rows:
        symbol = str(row.get("symbol") or row.get("code") or row.get("security_code") or "").strip()
        if not symbol:
            continue
        result.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "position_intent_row",
                "authority_mode": AUTHORITY_MODE,
                "decision_effect": DECISION_EFFECT,
                "run_id": run_id,
                "business_date": business_date,
                "accepted_generation": accepted_generation,
                "symbol": symbol,
                "position_campaign_id": None,
                "current_position_state": "NO_POSITION",
                "current_quantity": None,
                "current_notional": None,
                "current_weight": None,
                "candidate_id": _nullable_text(row.get("candidate_id") or row.get("row_id")),
                "opportunity_id": _nullable_text(row.get("opportunity_id") or row.get("row_id")),
                "opportunity_rank": _number(row.get("opportunity_rank") or row.get("buy_rank") or row.get("rank")),
                "opportunity_score": _number(row.get("opportunity_score") or row.get("expected_edge_score") or row.get("runtime_opportunity_score")),
                "quality_decision_id": None,
                "quality_score": None,
                "quality_action": None,
                "pm_decision_id": None,
                "pm_intent": None,
                "momentum_continuation_state": "INSUFFICIENT_EVIDENCE",
                "momentum_authority_mode": "SHADOW",
                "incremental_investment_eligibility": "INSUFFICIENT_EVIDENCE",
                "incremental_eligibility_authority_mode": "SHADOW",
                "proposed_position_intent": "UNRESOLVED",
                "intent_reason_codes": ["INCREMENTAL_ELIGIBILITY_NOT_AVAILABLE", "BUY_NEW_SHADOW_CANDIDATE", "DECISION_EFFECT_NONE"],
                "intent_summary": "BUY_NEW candidate observed, but active BUY_NEW intent is unresolved because incremental eligibility is not connected in D2-A.",
                "input_artifact_refs": dict(refs),
                "lineage": {
                    "source_pm_artifact": refs["pm"].get("path") or "NOT_APPLICABLE",
                    "source_pm_decision_id": "NOT_APPLICABLE",
                    "source_candidate_artifact": str(candidate_artifact_path or "NOT_YET_CONNECTED"),
                    "source_candidate_id": _nullable_text(row.get("candidate_id") or row.get("row_id")) or "MISSING",
                    "source_opportunity_artifact": str(opportunity_artifact_path or "NOT_YET_CONNECTED"),
                    "source_opportunity_id": _nullable_text(row.get("opportunity_id") or row.get("row_id")) or "MISSING",
                    "source_quality_artifact": str(quality_artifact_path or "NOT_YET_CONNECTED"),
                    "source_quality_decision_id": "NOT_YET_CONNECTED",
                    "source_current_artifact": refs["current"].get("path") or "NOT_YET_CONNECTED",
                    "source_market_context_artifact": refs["market_context"].get("path") or "NOT_YET_CONNECTED",
                    "source_portfolio_policy_artifact": refs["portfolio_policy"].get("path") or "NOT_YET_CONNECTED",
                    "accepted_generation": accepted_generation,
                    "business_date": business_date,
                },
                "evidence_status": "REVIEW_REQUIRED",
                "missing_required_inputs": ["incremental_investment_eligibility"],
                "review_status": "REVIEW_REQUIRED",
            }
        )
    return result


def _input_refs(**paths: Path | str | None) -> dict[str, dict[str, Any]]:
    refs: dict[str, dict[str, Any]] = {}
    for key, raw in paths.items():
        name = key.removesuffix("_artifact_path")
        if raw is None:
            refs[name] = {"path": None, "sha256": None, "status": "NOT_YET_CONNECTED"}
            continue
        path = Path(raw)
        if not path.is_file():
            refs[name] = {"path": str(path), "sha256": None, "status": "MISSING"}
            continue
        refs[name] = {"path": str(path), "sha256": _hash_file(path), "status": "PRESENT"}
    return refs


def _scope_source_status(refs: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
    return {name: str(ref.get("status") or "UNKNOWN") for name, ref in refs.items()}


def _pm_decisions(payload: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    decisions = payload.get("decisions")
    if isinstance(decisions, list):
        return tuple(row for row in decisions if isinstance(row, Mapping))
    positions = payload.get("positions")
    if isinstance(positions, list):
        return tuple(row for row in positions if isinstance(row, Mapping))
    return ()


def _extract_rows(payload: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    for key in ("opportunities", "rankings", "candidates", "rows", "items"):
        rows = payload.get(key)
        if isinstance(rows, list):
            return tuple(row for row in rows if isinstance(row, Mapping))
    return ()


def _read_json_if_present(path: Path | str | None) -> dict[str, Any] | None:
    if path is None:
        return None
    resolved = Path(path)
    if not resolved.is_file():
        return None
    with resolved.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise PositionIntentSchemaError(f"artifact must be JSON object: {resolved}")
    return payload


def _duplicate_dedup_keys(rows: Sequence[Mapping[str, Any]]) -> set[tuple[Any, ...]]:
    seen: set[tuple[Any, ...]] = set()
    duplicates: set[tuple[Any, ...]] = set()
    for row in rows:
        key = _dedup_key(row)
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return duplicates


def _dedup_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("run_id"),
        row.get("business_date"),
        row.get("symbol"),
        row.get("accepted_generation"),
        row.get("position_campaign_id"),
    )


def _counts(values: Iterable[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value or "")
        if not key:
            continue
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _require(payload: Mapping[str, Any], field: str, expected: str) -> None:
    if payload.get(field) != expected:
        raise PositionIntentSchemaError(f"{field} must be {expected}")


def _require_nonempty(payload: Mapping[str, Any], field: str) -> None:
    if not str(payload.get(field) or "").strip():
        raise PositionIntentSchemaError(f"{field} is required")


def _validate_iso_date(value: str, *, field: str) -> None:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise PositionIntentSchemaError(f"{field} must be ISO date") from exc


def _nullable_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _number(value: Any) -> float | int | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number.is_integer():
        return int(number)
    return number


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
