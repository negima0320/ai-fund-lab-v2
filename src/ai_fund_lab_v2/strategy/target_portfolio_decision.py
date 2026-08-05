from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "target_portfolio_decision.v1"
ARTIFACT_TYPE = "target_portfolio_decision"
PRODUCER_VERSION = "phase27_d2b_target_portfolio_decision_shadow_resolver.v1"
AUTHORITY_MODE = "SHADOW"
DECISION_EFFECT = "NONE"

INTENT_MAPPING = {
    "ADD": ("RETAIN", "INCREASE", "POSITIVE_DELTA_REQUIRED"),
    "HOLD": ("RETAIN", "MAINTAIN", "ZERO_DELTA_EXPECTED"),
    "REDUCE": ("RETAIN", "DECREASE", "NEGATIVE_DELTA_REQUIRED"),
    "EXIT": ("REMOVE", "REMOVE", "FULL_REMOVAL_REQUIRED"),
}
ALLOWED_MEMBERSHIP = {"ADD_CANDIDATE", "RETAIN", "REMOVE", "NO_MEMBERSHIP_CHANGE", "UNRESOLVED"}
ALLOWED_DIRECTION = {"INCREASE", "MAINTAIN", "DECREASE", "REMOVE", "NONE", "UNRESOLVED"}
ALLOWED_EFFECT = {
    "POSITIVE_DELTA_REQUIRED",
    "ZERO_DELTA_EXPECTED",
    "NEGATIVE_DELTA_REQUIRED",
    "FULL_REMOVAL_REQUIRED",
    "NOT_RESOLVED",
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
    "current_weight",
    "source_position_intent_id",
    "source_position_intent",
    "source_pm_decision_id",
    "source_pm_intent",
    "target_membership_decision",
    "target_direction",
    "target_weight_effect",
    "resolution_status",
    "resolution_reason_codes",
    "resolution_summary",
    "input_artifact_refs",
    "lineage",
    "evidence_status",
    "missing_required_inputs",
    "review_status",
)


class TargetPortfolioDecisionError(RuntimeError):
    pass


class TargetPortfolioDecisionSchemaError(TargetPortfolioDecisionError):
    pass


@dataclass(frozen=True)
class TargetPortfolioDecisionProducerResult:
    status: str
    reason: str
    artifact_path: str
    artifact_hash: str
    payload: dict[str, Any]
    evidence: dict[str, Any]


def default_runtime_artifact_path(runtime_root: Path | str, business_date: str) -> Path:
    return Path(runtime_root) / "strategy_artifacts" / "target_portfolio_decision" / business_date / "target_portfolio_decision.json"


def produce_target_portfolio_decision_artifact(
    *,
    runtime_root: Path | str,
    business_date: str,
    run_id: str,
    accepted_generation: str | None,
    position_intent_artifact_path: Path | str,
    current_artifact_path: Path | str | None,
    output_path: Path | str | None = None,
    portfolio_policy_artifact_path: Path | str | None = None,
    market_context_artifact_path: Path | str | None = None,
    as_of: str | None = None,
) -> TargetPortfolioDecisionProducerResult:
    resolved_output = Path(output_path) if output_path is not None else default_runtime_artifact_path(runtime_root, business_date)
    payload, evidence = build_target_portfolio_decision_payload(
        business_date=business_date,
        run_id=run_id,
        accepted_generation=accepted_generation,
        position_intent_artifact_path=position_intent_artifact_path,
        current_artifact_path=current_artifact_path,
        portfolio_policy_artifact_path=portfolio_policy_artifact_path,
        market_context_artifact_path=market_context_artifact_path,
        as_of=as_of,
    )
    validate_target_portfolio_decision_artifact(payload)
    artifact_hash = target_portfolio_decision_hash(payload)
    final_payload = {**payload, "artifact_hash": artifact_hash}
    _write_json(resolved_output, final_payload)
    return TargetPortfolioDecisionProducerResult(
        status=str(final_payload["artifact_status"]),
        reason=",".join(final_payload.get("reason_codes") or []),
        artifact_path=str(resolved_output),
        artifact_hash=artifact_hash,
        payload=final_payload,
        evidence=evidence,
    )


def build_target_portfolio_decision_payload(
    *,
    business_date: str,
    run_id: str,
    accepted_generation: str | None,
    position_intent_artifact_path: Path | str,
    current_artifact_path: Path | str | None,
    portfolio_policy_artifact_path: Path | str | None = None,
    market_context_artifact_path: Path | str | None = None,
    as_of: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_iso_date(business_date, field="business_date")
    if not str(run_id or "").strip():
        raise TargetPortfolioDecisionSchemaError("run_id is required")
    refs = _input_refs(
        position_intent_artifact_path=position_intent_artifact_path,
        current_artifact_path=current_artifact_path,
        portfolio_policy_artifact_path=portfolio_policy_artifact_path,
        market_context_artifact_path=market_context_artifact_path,
    )
    reason_codes: list[str] = []
    status = "PASS"
    intent_payload = _read_json_if_present(position_intent_artifact_path)
    if intent_payload is None:
        status = "BLOCK"
        reason_codes.append("POSITION_INTENT_ARTIFACT_MISSING")
        intent_rows: list[Mapping[str, Any]] = []
    elif intent_payload.get("business_date") != business_date:
        status = "BLOCK"
        reason_codes.append("POSITION_INTENT_BUSINESS_DATE_MISMATCH")
        intent_rows = []
    elif intent_payload.get("accepted_generation") not in (None, "", accepted_generation):
        status = "BLOCK"
        reason_codes.append("ACCEPTED_GENERATION_MISMATCH")
        intent_rows = []
    else:
        rows = intent_payload.get("intents") or []
        intent_rows = [row for row in rows if isinstance(row, Mapping)]
    current_payload = _read_json_if_present(current_artifact_path)
    if current_artifact_path is None:
        status = "REVIEW_REQUIRED" if status == "PASS" else status
        reason_codes.append("CURRENT_ARTIFACT_NOT_YET_CONNECTED")
    elif current_payload is None:
        status = "REVIEW_REQUIRED" if status == "PASS" else status
        reason_codes.append("CURRENT_ARTIFACT_MISSING")
    elif _payload_business_date(current_payload) not in ("", business_date):
        status = "BLOCK"
        reason_codes.append("CURRENT_BUSINESS_DATE_MISMATCH")
    current_by_symbol = _current_positions_by_symbol(current_payload or {})

    decisions = [
        _decision_from_intent(
            intent=row,
            business_date=business_date,
            run_id=run_id,
            accepted_generation=accepted_generation,
            refs=refs,
            current_by_symbol=current_by_symbol,
            current_artifact_present=current_payload is not None,
        )
        for row in intent_rows
    ]
    duplicate_keys = _duplicate_dedup_keys(decisions)
    if duplicate_keys:
        status = "BLOCK"
        reason_codes.append("DUPLICATE_DEDUP_KEY")
        for row in decisions:
            if _dedup_key(row) in duplicate_keys:
                row["resolution_status"] = "BLOCK"
                row["evidence_status"] = "BLOCK"
                row["review_status"] = "BLOCK"
                row["resolution_reason_codes"].append("DUPLICATE_DEDUP_KEY")
                row["missing_required_inputs"].append("duplicate_dedup_key")
    if any(row["review_status"] in {"REVIEW_REQUIRED", "BLOCK"} for row in decisions) and status == "PASS":
        status = "REVIEW_REQUIRED"
    reason_codes.extend(
        f"ROW_{row['review_status']}"
        for row in decisions
        if row["review_status"] in {"REVIEW_REQUIRED", "BLOCK"}
    )
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
        "generated_at": as_of or f"{business_date}T00:00:00+00:00",
        "artifact_status": status,
        "review_status": status,
        "reason_codes": reason_codes,
        "input_artifact_refs": refs,
        "summary": {
            "decision_count": len(decisions),
            "target_membership_counts": _counts(row.get("target_membership_decision") for row in decisions),
            "target_direction_counts": _counts(row.get("target_direction") for row in decisions),
            "resolution_status_counts": _counts(row.get("resolution_status") for row in decisions),
            "duplicate_dedup_key_count": len(duplicate_keys),
            "decision_effect_zero": True,
        },
        "decisions": decisions,
    }
    evidence = {
        "schema_path": "docs/02_architecture/schemas/target_portfolio_decision.v1.schema.json",
        "producer": "ai_fund_lab_v2.strategy.target_portfolio_decision",
        "authority_mode": AUTHORITY_MODE,
        "decision_effect": DECISION_EFFECT,
        "existing_portfolio_construction_replaced": False,
        "downstream_connection": "NONE_IN_D2_B",
    }
    return payload, evidence


def validate_target_portfolio_decision_artifact(payload: Mapping[str, Any]) -> dict[str, Any]:
    _require(payload, "schema_version", SCHEMA_VERSION)
    _require(payload, "artifact_type", ARTIFACT_TYPE)
    _require(payload, "authority_mode", AUTHORITY_MODE)
    _require(payload, "decision_effect", DECISION_EFFECT)
    _validate_iso_date(str(payload.get("business_date") or ""), field="business_date")
    if payload.get("artifact_status") not in {"PASS", "REVIEW_REQUIRED", "BLOCK"}:
        raise TargetPortfolioDecisionSchemaError("artifact_status must be PASS/REVIEW_REQUIRED/BLOCK")
    rows = payload.get("decisions")
    if not isinstance(rows, list):
        raise TargetPortfolioDecisionSchemaError("decisions must be a list")
    keys: set[tuple[Any, ...]] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise TargetPortfolioDecisionSchemaError("decision row must be object")
        for field in REQUIRED_ROW_FIELDS:
            if field not in row:
                raise TargetPortfolioDecisionSchemaError(f"decision row missing required field: {field}")
        _require(row, "schema_version", SCHEMA_VERSION)
        _require(row, "artifact_type", "target_portfolio_decision_row")
        _require(row, "authority_mode", AUTHORITY_MODE)
        _require(row, "decision_effect", DECISION_EFFECT)
        _validate_iso_date(str(row.get("business_date") or ""), field="row.business_date")
        if row.get("business_date") != payload.get("business_date"):
            raise TargetPortfolioDecisionSchemaError("row business_date mismatch")
        if row.get("target_membership_decision") not in ALLOWED_MEMBERSHIP:
            raise TargetPortfolioDecisionSchemaError("invalid target_membership_decision")
        if row.get("target_direction") not in ALLOWED_DIRECTION:
            raise TargetPortfolioDecisionSchemaError("invalid target_direction")
        if row.get("target_weight_effect") not in ALLOWED_EFFECT:
            raise TargetPortfolioDecisionSchemaError("invalid target_weight_effect")
        key = _dedup_key(row)
        if key in keys:
            raise TargetPortfolioDecisionSchemaError("duplicate dedup key")
        keys.add(key)
        forbidden = {
            "target_weight",
            "target_weight_candidate",
            "target_notional",
            "target_notional_candidate",
            "target_quantity",
            "target_quantity_candidate",
            "quantity_delta",
            "quantity_delta_candidate",
            "order_quantity",
            "planning_intent",
            "pending_item_id",
            "order_plan_item_id",
        }
        present_forbidden = forbidden & set(row)
        if present_forbidden:
            raise TargetPortfolioDecisionSchemaError(f"target_portfolio_decision row contains downstream fields: {sorted(present_forbidden)}")
    return {"status": "PASS", "row_count": len(rows)}


def target_portfolio_decision_hash(payload: Mapping[str, Any]) -> str:
    canonical = dict(payload)
    canonical.pop("artifact_hash", None)
    return hashlib.sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _decision_from_intent(
    *,
    intent: Mapping[str, Any],
    business_date: str,
    run_id: str,
    accepted_generation: str | None,
    refs: Mapping[str, Any],
    current_by_symbol: Mapping[str, Mapping[str, Any]],
    current_artifact_present: bool,
) -> dict[str, Any]:
    symbol = str(intent.get("symbol") or "").strip()
    source_intent = str(intent.get("proposed_position_intent") or "UNRESOLVED").upper()
    membership, direction, effect = INTENT_MAPPING.get(source_intent, ("UNRESOLVED", "UNRESOLVED", "NOT_RESOLVED"))
    reason_codes = ["POSITION_INTENT_CONSUMED_SHADOW", "DECISION_EFFECT_NONE"]
    missing: list[str] = []
    resolution_status = "PASS"
    current = current_by_symbol.get(symbol)
    if source_intent in {"BUY_NEW", "UNRESOLVED", "NO_ACTION"}:
        resolution_status = "UNRESOLVED"
        reason_codes.append(f"{source_intent}_NOT_CONNECTED_IN_D2_B")
    elif not current_artifact_present:
        resolution_status = "REVIEW_REQUIRED"
        missing.append("current_artifact")
        reason_codes.append("CURRENT_ARTIFACT_MISSING")
    elif current is None:
        resolution_status = "REVIEW_REQUIRED"
        missing.append("current_position")
        reason_codes.append(f"{source_intent}_WITHOUT_CURRENT_HOLDING")
    elif intent.get("position_campaign_id") and _current_campaign_id(current) and intent.get("position_campaign_id") != _current_campaign_id(current):
        resolution_status = "REVIEW_REQUIRED"
        missing.append("position_campaign_id_match")
        reason_codes.append("POSITION_CAMPAIGN_MISMATCH")
    current_state = "OPEN_POSITION" if current is not None else "NO_POSITION"
    if resolution_status != "PASS":
        if source_intent not in INTENT_MAPPING:
            membership, direction, effect = "UNRESOLVED", "UNRESOLVED", "NOT_RESOLVED"
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "target_portfolio_decision_row",
        "authority_mode": AUTHORITY_MODE,
        "decision_effect": DECISION_EFFECT,
        "run_id": run_id,
        "business_date": business_date,
        "accepted_generation": accepted_generation,
        "symbol": symbol,
        "position_campaign_id": intent.get("position_campaign_id"),
        "current_position_state": current_state,
        "current_quantity": _number((current or {}).get("quantity") or intent.get("current_quantity")),
        "current_weight": _number((current or {}).get("current_weight") or intent.get("current_weight")),
        "source_position_intent_id": intent.get("position_intent_id") or "MISSING",
        "source_position_intent": source_intent,
        "source_pm_decision_id": intent.get("pm_decision_id") or (intent.get("lineage") or {}).get("source_pm_decision_id") or "MISSING",
        "source_pm_intent": intent.get("pm_intent"),
        "target_membership_decision": membership,
        "target_direction": direction,
        "target_weight_effect": effect,
        "resolution_status": resolution_status,
        "resolution_reason_codes": reason_codes,
        "resolution_summary": f"Shadow resolved {source_intent} to {membership}/{direction}/{effect}; no active portfolio output mutation.",
        "input_artifact_refs": dict(refs),
        "lineage": {
            "source_position_intent_artifact": refs["position_intent"].get("path") or "MISSING",
            "source_position_intent_id": intent.get("position_intent_id") or "MISSING",
            "source_pm_artifact": (intent.get("lineage") or {}).get("source_pm_artifact") or "MISSING",
            "source_pm_decision_id": intent.get("pm_decision_id") or (intent.get("lineage") or {}).get("source_pm_decision_id") or "MISSING",
            "source_current_artifact": refs["current"].get("path") or "NOT_YET_CONNECTED",
            "source_portfolio_policy_artifact": refs["portfolio_policy"].get("path") or "NOT_YET_CONNECTED",
            "source_market_context_artifact": refs["market_context"].get("path") or "NOT_YET_CONNECTED",
            "accepted_generation": accepted_generation,
            "business_date": business_date,
        },
        "evidence_status": resolution_status,
        "missing_required_inputs": missing,
        "review_status": resolution_status,
    }


def _current_positions_by_symbol(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = payload.get("positions")
    if not isinstance(rows, list):
        rows = payload.get("current_positions")
    if not isinstance(rows, list):
        return {}
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        symbol = str(row.get("symbol") or row.get("security_code") or row.get("issue_code") or "").strip()
        quantity = _number(row.get("quantity"))
        if symbol and (quantity is None or quantity > 0):
            result[symbol] = row
    return result


def _payload_business_date(payload: Mapping[str, Any]) -> str:
    return str(payload.get("business_date") or payload.get("as_of") or payload.get("date") or "")


def _current_campaign_id(row: Mapping[str, Any]) -> str | None:
    value = row.get("position_campaign_id") or row.get("position_lifecycle_id") or row.get("campaign_id")
    return str(value).strip() if value not in (None, "") else None


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


def _read_json_if_present(path: Path | str | None) -> dict[str, Any] | None:
    if path is None:
        return None
    resolved = Path(path)
    if not resolved.is_file():
        return None
    with resolved.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise TargetPortfolioDecisionSchemaError(f"artifact must be JSON object: {resolved}")
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
        raise TargetPortfolioDecisionSchemaError(f"{field} must be {expected}")


def _validate_iso_date(value: str, *, field: str) -> None:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise TargetPortfolioDecisionSchemaError(f"{field} must be ISO date") from exc


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
