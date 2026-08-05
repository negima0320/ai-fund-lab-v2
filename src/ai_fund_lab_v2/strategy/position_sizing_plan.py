from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "position_sizing_plan.v1"
ARTIFACT_TYPE = "position_sizing_plan"
PRODUCER_VERSION = "phase27_d2d_position_sizing_plan_shadow_producer.v1"
AUTHORITY_MODE = "SHADOW"
DECISION_EFFECT = "NONE"
DEFAULT_LOT_SIZE = 100

ALLOWED_DELTA_CLASS = {
    "POSITIVE_DELTA",
    "ZERO_DELTA",
    "NEGATIVE_PARTIAL_DELTA",
    "FULL_NEGATIVE_DELTA",
    "NOT_SIZED",
}
ALLOWED_SIZING_STATUS = {
    "POSITIVE_DELTA_SIZED",
    "ZERO_DELTA_SIZED",
    "NEGATIVE_DELTA_SIZED",
    "FULL_EXIT_DELTA_SIZED",
    "ADD_NOT_SIZED",
    "HOLD_NOT_SIZED",
    "REDUCE_NOT_SIZED",
    "EXIT_NOT_SIZED",
    "UNRESOLVED_NOT_SIZED",
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
    "source_target_portfolio_decision_id",
    "source_position_intent",
    "source_pm_intent",
    "target_membership_decision",
    "target_direction",
    "target_weight_effect",
    "current_quantity",
    "target_quantity_candidate",
    "quantity_delta_candidate",
    "orderable_quantity_delta",
    "lot_rounding_result",
    "delta_classification",
    "sizing_status",
    "reason_codes",
    "lineage",
    "review_status",
)


class PositionSizingPlanError(RuntimeError):
    pass


class PositionSizingPlanSchemaError(PositionSizingPlanError):
    pass


@dataclass(frozen=True)
class PositionSizingPlanProducerResult:
    status: str
    reason: str
    artifact_path: str
    artifact_hash: str
    payload: dict[str, Any]
    evidence: dict[str, Any]


def default_runtime_artifact_path(runtime_root: Path | str, business_date: str) -> Path:
    return Path(runtime_root) / "strategy_artifacts" / "position_sizing_plan" / business_date / "position_sizing_plan.json"


def produce_position_sizing_plan_artifact(
    *,
    runtime_root: Path | str,
    business_date: str,
    run_id: str,
    accepted_generation: str | None,
    target_portfolio_decision_artifact_path: Path | str,
    output_path: Path | str | None = None,
    lot_size: int = DEFAULT_LOT_SIZE,
    as_of: str | None = None,
) -> PositionSizingPlanProducerResult:
    resolved_output = Path(output_path) if output_path is not None else default_runtime_artifact_path(runtime_root, business_date)
    payload, evidence = build_position_sizing_plan_payload(
        business_date=business_date,
        run_id=run_id,
        accepted_generation=accepted_generation,
        target_portfolio_decision_artifact_path=target_portfolio_decision_artifact_path,
        lot_size=lot_size,
        as_of=as_of,
    )
    validate_position_sizing_plan_artifact(payload)
    artifact_hash = position_sizing_plan_hash(payload)
    final_payload = {**payload, "artifact_hash": artifact_hash}
    _write_json(resolved_output, final_payload)
    return PositionSizingPlanProducerResult(
        status=str(final_payload["artifact_status"]),
        reason=",".join(final_payload.get("reason_codes") or []),
        artifact_path=str(resolved_output),
        artifact_hash=artifact_hash,
        payload=final_payload,
        evidence=evidence,
    )


def build_position_sizing_plan_payload(
    *,
    business_date: str,
    run_id: str,
    accepted_generation: str | None,
    target_portfolio_decision_artifact_path: Path | str,
    lot_size: int = DEFAULT_LOT_SIZE,
    as_of: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_iso_date(business_date, field="business_date")
    if not str(run_id or "").strip():
        raise PositionSizingPlanSchemaError("run_id is required")
    if lot_size <= 0:
        raise PositionSizingPlanSchemaError("lot_size must be positive")
    refs = _input_refs(target_portfolio_decision_artifact_path=target_portfolio_decision_artifact_path)
    reason_codes: list[str] = []
    artifact_status = "PASS"
    target_payload = _read_json_if_present(target_portfolio_decision_artifact_path)
    if target_payload is None:
        artifact_status = "BLOCK"
        reason_codes.append("TARGET_PORTFOLIO_DECISION_ARTIFACT_MISSING")
        decision_rows: list[Mapping[str, Any]] = []
    elif target_payload.get("schema_version") != "target_portfolio_decision.v1":
        artifact_status = "BLOCK"
        reason_codes.append("TARGET_PORTFOLIO_DECISION_SCHEMA_MISMATCH")
        decision_rows = []
    elif target_payload.get("business_date") != business_date:
        artifact_status = "BLOCK"
        reason_codes.append("TARGET_PORTFOLIO_DECISION_BUSINESS_DATE_MISMATCH")
        decision_rows = []
    elif target_payload.get("accepted_generation") not in (None, "", accepted_generation):
        artifact_status = "BLOCK"
        reason_codes.append("ACCEPTED_GENERATION_MISMATCH")
        decision_rows = []
    elif target_payload.get("authority_mode") != "SHADOW" or target_payload.get("decision_effect") != "NONE":
        artifact_status = "BLOCK"
        reason_codes.append("TARGET_PORTFOLIO_DECISION_AUTHORITY_MISMATCH")
        decision_rows = []
    else:
        rows = target_payload.get("decisions") or []
        decision_rows = [row for row in rows if isinstance(row, Mapping)]
        if target_payload.get("artifact_status") in {"REVIEW_REQUIRED", "BLOCK"}:
            artifact_status = str(target_payload.get("artifact_status"))
            reason_codes.append(f"TARGET_PORTFOLIO_DECISION_{artifact_status}")

    positions = [
        _sizing_row_from_target_decision(
            decision=row,
            business_date=business_date,
            run_id=run_id,
            accepted_generation=accepted_generation,
            refs=refs,
            lot_size=lot_size,
        )
        for row in decision_rows
    ]
    duplicate_keys = _duplicate_dedup_keys(positions)
    if duplicate_keys:
        artifact_status = "BLOCK"
        reason_codes.append("DUPLICATE_DEDUP_KEY")
        for row in positions:
            if _dedup_key(row) in duplicate_keys:
                row["review_status"] = "BLOCK"
                row["reason_codes"].append("DUPLICATE_DEDUP_KEY")
    if any(row["review_status"] in {"REVIEW_REQUIRED", "BLOCK"} for row in positions) and artifact_status == "PASS":
        artifact_status = "REVIEW_REQUIRED"
    reason_codes.extend(
        f"ROW_{row['review_status']}"
        for row in positions
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
        "artifact_status": artifact_status,
        "review_status": artifact_status,
        "reason_codes": reason_codes,
        "lot_size": lot_size,
        "input_artifact_refs": refs,
        "summary": {
            "position_count": len(positions),
            "sizing_status_counts": _counts(row.get("sizing_status") for row in positions),
            "delta_classification_counts": _counts(row.get("delta_classification") for row in positions),
            "duplicate_dedup_key_count": len(duplicate_keys),
            "decision_effect_zero": True,
            "runtime_connected": False,
            "pending_decided": False,
            "submit_decided": False,
        },
        "positions": positions,
    }
    evidence = {
        "schema_path": "docs/02_architecture/schemas/position_sizing_plan.v1.schema.json",
        "producer": "ai_fund_lab_v2.strategy.position_sizing_plan",
        "authority_mode": AUTHORITY_MODE,
        "decision_effect": DECISION_EFFECT,
        "formal_position_sizing_replaced": False,
        "runtime_planning_connection": "NONE_IN_D2_D",
        "pending_connection": "NONE_IN_D2_D",
        "submit_connection": "NONE_IN_D2_D",
    }
    return payload, evidence


def validate_position_sizing_plan_artifact(payload: Mapping[str, Any]) -> dict[str, Any]:
    _require(payload, "schema_version", SCHEMA_VERSION)
    _require(payload, "artifact_type", ARTIFACT_TYPE)
    _require(payload, "authority_mode", AUTHORITY_MODE)
    _require(payload, "decision_effect", DECISION_EFFECT)
    _validate_iso_date(str(payload.get("business_date") or ""), field="business_date")
    if payload.get("artifact_status") not in {"PASS", "REVIEW_REQUIRED", "BLOCK"}:
        raise PositionSizingPlanSchemaError("artifact_status must be PASS/REVIEW_REQUIRED/BLOCK")
    rows = payload.get("positions")
    if not isinstance(rows, list):
        raise PositionSizingPlanSchemaError("positions must be a list")
    keys: set[tuple[Any, ...]] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise PositionSizingPlanSchemaError("position row must be object")
        for field in REQUIRED_ROW_FIELDS:
            if field not in row:
                raise PositionSizingPlanSchemaError(f"position row missing required field: {field}")
        _require(row, "schema_version", SCHEMA_VERSION)
        _require(row, "artifact_type", "position_sizing_plan_row")
        _require(row, "authority_mode", AUTHORITY_MODE)
        _require(row, "decision_effect", DECISION_EFFECT)
        _validate_iso_date(str(row.get("business_date") or ""), field="row.business_date")
        if row.get("business_date") != payload.get("business_date"):
            raise PositionSizingPlanSchemaError("row business_date mismatch")
        if row.get("delta_classification") not in ALLOWED_DELTA_CLASS:
            raise PositionSizingPlanSchemaError("invalid delta_classification")
        if row.get("sizing_status") not in ALLOWED_SIZING_STATUS:
            raise PositionSizingPlanSchemaError("invalid sizing_status")
        _validate_pm_intent_not_overwritten(row)
        key = _dedup_key(row)
        if key in keys:
            raise PositionSizingPlanSchemaError("duplicate dedup key")
        keys.add(key)
        forbidden = {
            "planning_intent",
            "BUY_ADD",
            "BUY_NEW",
            "pending_item_id",
            "order_plan_item_id",
            "approval_id",
            "submit_command",
            "execution_id",
        }
        present_forbidden = forbidden & set(row)
        if present_forbidden:
            raise PositionSizingPlanSchemaError(f"position_sizing_plan row contains downstream fields: {sorted(present_forbidden)}")
    return {"status": "PASS", "row_count": len(rows)}


def position_sizing_plan_hash(payload: Mapping[str, Any]) -> str:
    canonical = dict(payload)
    canonical.pop("artifact_hash", None)
    return hashlib.sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _sizing_row_from_target_decision(
    *,
    decision: Mapping[str, Any],
    business_date: str,
    run_id: str,
    accepted_generation: str | None,
    refs: Mapping[str, Any],
    lot_size: int,
) -> dict[str, Any]:
    source_intent = str(decision.get("source_position_intent") or "UNRESOLVED").upper()
    pm_intent = str(decision.get("source_pm_intent") or source_intent or "UNRESOLVED").upper()
    current_quantity = _number(decision.get("current_quantity"))
    target_quantity, status, delta_class, reasons = _quantity_contract(
        pm_intent=pm_intent,
        current_quantity=current_quantity,
        lot_size=lot_size,
    )
    delta = None if target_quantity is None or current_quantity is None else int(target_quantity - current_quantity)
    orderable_delta = _orderable_delta(delta=delta, current_quantity=current_quantity)
    lot_rounding_result = {
        "lot_size": lot_size,
        "rounding_mode": "DIRECTIONAL_SHADOW_MIN_LOT",
        "rounded_delta": orderable_delta,
        "status": "PASS" if delta is not None else "NOT_SIZED",
    }
    review_status = "PASS" if status.endswith("_SIZED") else "REVIEW_REQUIRED"
    if str(decision.get("review_status") or "") in {"REVIEW_REQUIRED", "BLOCK"}:
        review_status = str(decision.get("review_status"))
        reasons.append(f"TARGET_PORTFOLIO_DECISION_ROW_{review_status}")
    row = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "position_sizing_plan_row",
        "authority_mode": AUTHORITY_MODE,
        "decision_effect": DECISION_EFFECT,
        "run_id": run_id,
        "business_date": business_date,
        "accepted_generation": accepted_generation,
        "symbol": str(decision.get("symbol") or "").strip(),
        "position_campaign_id": decision.get("position_campaign_id"),
        "source_target_portfolio_decision_id": _target_decision_id(decision),
        "source_position_intent": source_intent,
        "source_pm_intent": pm_intent,
        "target_membership_decision": decision.get("target_membership_decision"),
        "target_direction": decision.get("target_direction"),
        "target_weight_effect": decision.get("target_weight_effect"),
        "current_quantity": current_quantity,
        "target_quantity_candidate": target_quantity,
        "quantity_delta_candidate": delta,
        "orderable_quantity_delta": orderable_delta,
        "lot_rounding_result": lot_rounding_result,
        "delta_classification": delta_class,
        "sizing_status": status,
        "reason_codes": sorted(set(reasons + ["DECISION_EFFECT_NONE", "SHADOW_ONLY_RUNTIME_NOT_CONNECTED"])),
        "lineage": {
            "source_target_portfolio_decision_artifact": refs["target_portfolio_decision"].get("path") or "MISSING",
            "source_target_portfolio_decision_id": _target_decision_id(decision),
            "source_position_intent_id": decision.get("source_position_intent_id") or "MISSING",
            "source_pm_decision_id": decision.get("source_pm_decision_id") or "MISSING",
            "position_campaign_id": decision.get("position_campaign_id"),
            "accepted_generation": accepted_generation,
            "business_date": business_date,
        },
        "review_status": review_status,
    }
    row["dedup_key"] = _dedup_key(row)
    return row


def _quantity_contract(
    *,
    pm_intent: str,
    current_quantity: int | None,
    lot_size: int,
) -> tuple[int | None, str, str, list[str]]:
    if current_quantity is None or current_quantity < 0:
        return None, f"{pm_intent if pm_intent in {'ADD', 'HOLD', 'REDUCE', 'EXIT'} else 'UNRESOLVED'}_NOT_SIZED", "NOT_SIZED", ["CURRENT_QUANTITY_MISSING"]
    if pm_intent == "ADD":
        return current_quantity + lot_size, "POSITIVE_DELTA_SIZED", "POSITIVE_DELTA", ["PM_ADD_PRESERVED", "MIN_LOT_POSITIVE_DELTA_SHADOW"]
    if pm_intent == "HOLD":
        return current_quantity, "ZERO_DELTA_SIZED", "ZERO_DELTA", ["PM_HOLD_PRESERVED", "ZERO_DELTA_SHADOW"]
    if pm_intent == "REDUCE":
        if current_quantity <= lot_size:
            return None, "REDUCE_NOT_SIZED", "NOT_SIZED", ["PM_REDUCE_PRESERVED", "PARTIAL_REDUCE_REQUIRES_REMAINING_QUANTITY"]
        return current_quantity - lot_size, "NEGATIVE_DELTA_SIZED", "NEGATIVE_PARTIAL_DELTA", ["PM_REDUCE_PRESERVED", "MIN_LOT_NEGATIVE_DELTA_SHADOW"]
    if pm_intent == "EXIT":
        return 0, "FULL_EXIT_DELTA_SIZED", "FULL_NEGATIVE_DELTA", ["PM_EXIT_PRESERVED", "FULL_EXIT_DELTA_SHADOW"]
    return None, "UNRESOLVED_NOT_SIZED", "NOT_SIZED", ["PM_INTENT_UNRESOLVED"]


def _orderable_delta(*, delta: int | None, current_quantity: int | None) -> int | None:
    if delta is None:
        return None
    if current_quantity is None:
        return None
    if delta < 0 and abs(delta) > current_quantity:
        return -current_quantity
    return delta


def _validate_pm_intent_not_overwritten(row: Mapping[str, Any]) -> None:
    pm_intent = str(row.get("source_pm_intent") or "").upper()
    delta = row.get("quantity_delta_candidate")
    status = str(row.get("sizing_status") or "")
    if pm_intent == "ADD" and not ((isinstance(delta, int) and delta > 0) or status == "ADD_NOT_SIZED"):
        raise PositionSizingPlanSchemaError("PM ADD must produce positive delta or ADD_NOT_SIZED")
    if pm_intent == "HOLD" and not ((isinstance(delta, int) and delta == 0) or status == "HOLD_NOT_SIZED"):
        raise PositionSizingPlanSchemaError("PM HOLD must produce zero delta or HOLD_NOT_SIZED")
    if pm_intent == "REDUCE" and not ((isinstance(delta, int) and delta < 0 and row.get("target_quantity_candidate", 0) > 0) or status == "REDUCE_NOT_SIZED"):
        raise PositionSizingPlanSchemaError("PM REDUCE must produce negative partial delta or REDUCE_NOT_SIZED")
    if pm_intent == "EXIT" and not ((isinstance(delta, int) and delta < 0 and row.get("target_quantity_candidate") == 0) or status == "EXIT_NOT_SIZED"):
        raise PositionSizingPlanSchemaError("PM EXIT must produce full negative delta or EXIT_NOT_SIZED")


def _target_decision_id(decision: Mapping[str, Any]) -> str:
    symbol = str(decision.get("symbol") or "").strip()
    source_id = str(decision.get("source_position_intent_id") or "MISSING")
    return f"tpd:{source_id}:{symbol}"


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
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dedup_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("run_id"),
        row.get("business_date"),
        row.get("symbol"),
        row.get("accepted_generation"),
        row.get("position_campaign_id"),
    )


def _duplicate_dedup_keys(rows: Sequence[Mapping[str, Any]]) -> set[tuple[Any, ...]]:
    seen: set[tuple[Any, ...]] = set()
    duplicates: set[tuple[Any, ...]] = set()
    for row in rows:
        key = _dedup_key(row)
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return duplicates


def _number(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _counts(values: Iterable[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _require(payload: Mapping[str, Any], field: str, expected: Any) -> None:
    if payload.get(field) != expected:
        raise PositionSizingPlanSchemaError(f"{field} must be {expected}")


def _validate_iso_date(value: str, *, field: str) -> None:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise PositionSizingPlanSchemaError(f"{field} must be ISO date") from exc
