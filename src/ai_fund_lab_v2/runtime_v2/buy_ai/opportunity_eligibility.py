"""Opportunity BUY eligibility resolver for Runtime v2."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

OPPORTUNITY_BUY_ELIGIBILITY_POLICY_VERSION = "runtime_v2_opportunity_buy_eligibility_v1"
OPPORTUNITY_BUY_ELIGIBILITY_SCHEMA_VERSION = "runtime_v2_opportunity_buy_eligibility_result_v1"

NO_BUY_REASON_EMPTY_VALUES = {"", "none", "null", "n/a", "na", "not_applicable", "no_buy_reason_none"}


@dataclass(frozen=True)
class OpportunityBuyEligibilityResult:
    status: str
    buy_eligibility: str
    eligible: bool
    reason_code: str
    reason: str
    symbol: str
    business_date: str
    feature_date: str
    expected_edge_score: float | None = None
    expected_return: float | None = None
    no_buy_reason: str = ""
    buy_rank: int | None = None
    is_top5: bool | None = None
    opportunity_artifact_path: str = ""
    opportunity_artifact_hash: str = ""
    opportunity_business_date: str = ""
    opportunity_feature_date: str = ""
    opportunity_row_present: bool = False
    opportunity_schema_status: str = ""
    opportunity_artifact_status: str = ""
    opportunity_row_id: str = ""
    opportunity_authority: str = ""
    excluded_at_stage: str = ""
    runtime_opportunity_score: float | None = None
    canonical_score_field: str = ""
    score_semantic_role: str = ""
    calibration_applied: bool = False
    economic_units_available: bool = False
    absolute_economic_gate_applicable: bool = False
    expected_edge_score_semantic_role: str = ""
    expected_return_semantic_role: str = ""
    relative_competition_eligible: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {"schema_version": OPPORTUNITY_BUY_ELIGIBILITY_SCHEMA_VERSION, **asdict(self)}


def evaluate_opportunity_buy_eligibility(
    *,
    symbol: str,
    business_date: str,
    feature_date: str,
    opportunity_artifact_path: Path | str | None = None,
    opportunity_payload: Mapping[str, Any] | None = None,
    opportunity_row: Mapping[str, Any] | None = None,
    expected_artifact_hash: str = "",
    require_row_identity: bool = False,
    excluded_at_stage: str = "",
) -> OpportunityBuyEligibilityResult:
    normalized_symbol = _symbol(symbol)
    artifact_path = Path(opportunity_artifact_path) if opportunity_artifact_path else None
    artifact_hash = _file_hash(artifact_path) if artifact_path is not None else ""
    payload = dict(opportunity_payload or {})
    if not payload and artifact_path is not None:
        try:
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        except Exception:
            return _result(
                status="BLOCKED",
                eligibility="BUY_INELIGIBLE",
                reason_code="opportunity_artifact_unreadable",
                reason="Opportunity artifact is missing or unreadable",
                symbol=normalized_symbol,
                business_date=business_date,
                feature_date=feature_date,
                artifact_path=str(artifact_path),
                artifact_hash=artifact_hash,
                excluded_at_stage=excluded_at_stage,
            )
    if expected_artifact_hash and artifact_hash and _normalize_hash(expected_artifact_hash) != _normalize_hash(artifact_hash):
        return _result(
            status="BLOCKED",
            eligibility="BUY_INELIGIBLE",
            reason_code="opportunity_artifact_hash_mismatch",
            reason="Opportunity artifact hash changed after Morning eligibility decision",
            symbol=normalized_symbol,
            business_date=business_date,
            feature_date=feature_date,
            artifact_path=str(artifact_path or ""),
            artifact_hash=artifact_hash,
            excluded_at_stage=excluded_at_stage,
        )
    if not payload and opportunity_row is None:
        return _result(
            status="BLOCKED",
            eligibility="BUY_INELIGIBLE",
            reason_code="opportunity_evidence_missing",
            reason="Opportunity BUY evidence is required",
            symbol=normalized_symbol,
            business_date=business_date,
            feature_date=feature_date,
            artifact_path=str(artifact_path or ""),
            artifact_hash=artifact_hash,
            excluded_at_stage=excluded_at_stage,
        )
    artifact_status = str(payload.get("status") or ("PASS" if opportunity_row is not None else "")).upper()
    schema_status = "PASS" if payload.get("schema_version") or opportunity_row is not None else "MISSING"
    if payload and artifact_status != "PASS":
        return _result(
            status="BLOCKED",
            eligibility="BUY_INELIGIBLE",
            reason_code="opportunity_artifact_status_not_pass",
            reason="Opportunity artifact status is not PASS",
            symbol=normalized_symbol,
            business_date=business_date,
            feature_date=feature_date,
            artifact_path=str(artifact_path or ""),
            artifact_hash=artifact_hash,
            opportunity_business_date=str(payload.get("business_date") or ""),
            opportunity_feature_date=str(payload.get("feature_date") or ""),
            schema_status=schema_status,
            artifact_status=artifact_status,
            excluded_at_stage=excluded_at_stage,
        )
    if payload:
        payload_business_date = str(payload.get("business_date") or "")
        payload_feature_date = str(payload.get("feature_date") or payload.get("target_date") or "")
        if payload_business_date and payload_business_date != business_date:
            return _date_mismatch(
                "opportunity_business_date_mismatch",
                normalized_symbol,
                business_date,
                feature_date,
                payload,
                artifact_path,
                artifact_hash,
                excluded_at_stage,
            )
        if payload_feature_date and payload_feature_date != feature_date:
            return _date_mismatch(
                "opportunity_feature_date_mismatch",
                normalized_symbol,
                business_date,
                feature_date,
                payload,
                artifact_path,
                artifact_hash,
                excluded_at_stage,
            )
    row = dict(opportunity_row or {})
    expected_row_id = str(
        row.get("opportunity_row_id")
        or row.get("row_id")
        or row.get("opportunity_id")
        or ""
    )
    if require_row_identity and not expected_row_id:
        return _result(
            status="BLOCKED",
            eligibility="BUY_INELIGIBLE",
            reason_code="opportunity_row_identity_missing",
            reason="Opportunity row identity is required for Submit Guard",
            symbol=normalized_symbol,
            business_date=business_date,
            feature_date=feature_date,
            artifact_path=str(artifact_path or ""),
            artifact_hash=artifact_hash,
            opportunity_business_date=str(payload.get("business_date") or ""),
            opportunity_feature_date=str(payload.get("feature_date") or ""),
            schema_status=schema_status,
            artifact_status=artifact_status,
            excluded_at_stage=excluded_at_stage,
        )
    if not row and payload:
        for item in payload.get("rankings") or ():
            if _symbol(item.get("symbol") or item.get("code")) == normalized_symbol:
                row = dict(item)
                break
    elif row and payload and expected_row_id:
        matching_row = _find_payload_row_by_identity(
            payload=payload,
            symbol=normalized_symbol,
            expected_row_id=expected_row_id,
            business_date=business_date,
        )
        if matching_row is None:
            return _result_from_row(
                row,
                status="BLOCKED",
                eligibility="BUY_INELIGIBLE",
                reason_code="opportunity_row_identity_mismatch",
                reason="Opportunity row identity does not match ranking artifact",
                symbol=normalized_symbol,
                business_date=business_date,
                feature_date=feature_date,
                payload=payload,
                artifact_path=artifact_path,
                artifact_hash=artifact_hash,
                schema_status=schema_status,
                artifact_status=artifact_status,
                excluded_at_stage=excluded_at_stage,
            )
    if not row:
        return _result(
            status="BLOCKED",
            eligibility="BUY_INELIGIBLE",
            reason_code="opportunity_row_missing",
            reason="Opportunity ranking row is missing for symbol",
            symbol=normalized_symbol,
            business_date=business_date,
            feature_date=feature_date,
            artifact_path=str(artifact_path or ""),
            artifact_hash=artifact_hash,
            opportunity_business_date=str(payload.get("business_date") or ""),
            opportunity_feature_date=str(payload.get("feature_date") or ""),
            schema_status=schema_status,
            artifact_status=artifact_status,
            excluded_at_stage=excluded_at_stage,
        )
    row_symbol = _symbol(row.get("symbol") or row.get("code"))
    if row_symbol != normalized_symbol:
        return _result_from_row(
            row,
            status="BLOCKED",
            eligibility="BUY_INELIGIBLE",
            reason_code="opportunity_symbol_mismatch",
            reason="Opportunity row symbol does not match Pending symbol",
            symbol=normalized_symbol,
            business_date=business_date,
            feature_date=feature_date,
            payload=payload,
            artifact_path=artifact_path,
            artifact_hash=artifact_hash,
            schema_status=schema_status,
            artifact_status=artifact_status,
            excluded_at_stage=excluded_at_stage,
        )
    row_business_date = str(row.get("business_date") or "")
    row_feature_date = str(row.get("feature_date") or row.get("target_date") or "")
    if row_business_date and row_business_date != business_date:
        return _result_from_row(
            row,
            status="BLOCKED",
            eligibility="BUY_INELIGIBLE",
            reason_code="opportunity_row_business_date_mismatch",
            reason="Opportunity row business_date mismatch",
            symbol=normalized_symbol,
            business_date=business_date,
            feature_date=feature_date,
            payload=payload,
            artifact_path=artifact_path,
            artifact_hash=artifact_hash,
            schema_status=schema_status,
            artifact_status=artifact_status,
            excluded_at_stage=excluded_at_stage,
        )
    if row_feature_date and row_feature_date != feature_date:
        return _result_from_row(
            row,
            status="BLOCKED",
            eligibility="BUY_INELIGIBLE",
            reason_code="opportunity_row_feature_date_mismatch",
            reason="Opportunity row feature_date mismatch",
            symbol=normalized_symbol,
            business_date=business_date,
            feature_date=feature_date,
            payload=payload,
            artifact_path=artifact_path,
            artifact_hash=artifact_hash,
            schema_status=schema_status,
            artifact_status=artifact_status,
            excluded_at_stage=excluded_at_stage,
        )
    score_contract = _score_contract(row=row, payload=payload)
    if score_contract["status"] != "PASS":
        return _result_from_row(
            row,
            status="BLOCKED",
            eligibility="BUY_INELIGIBLE",
            reason_code=str(score_contract["reason_code"]),
            reason=str(score_contract["reason"]),
            symbol=normalized_symbol,
            business_date=business_date,
            feature_date=feature_date,
            payload=payload,
            artifact_path=artifact_path,
            artifact_hash=artifact_hash,
            schema_status=schema_status,
            artifact_status=artifact_status,
            excluded_at_stage=excluded_at_stage,
            score_contract=score_contract,
        )
    resolved_score = _finite_float(score_contract["score"])
    if resolved_score is None:
        return _result_from_row(
            row,
            status="BLOCKED",
            eligibility="BUY_INELIGIBLE",
            reason_code="opportunity_expected_edge_invalid",
            reason="Opportunity runtime_opportunity_score is missing or non-finite",
            symbol=normalized_symbol,
            business_date=business_date,
            feature_date=feature_date,
            payload=payload,
            artifact_path=artifact_path,
            artifact_hash=artifact_hash,
            schema_status=schema_status,
            artifact_status=artifact_status,
            excluded_at_stage=excluded_at_stage,
            score_contract=score_contract,
        )
    no_buy_reason = str(row.get("no_buy_reason") or "").strip()
    if score_contract["economic_units_available"] and resolved_score <= 0:
        return _result_from_row(
            row,
            status="BLOCKED",
            eligibility="BUY_INELIGIBLE",
            reason_code="non_positive_expected_edge_score",
            reason="Calibrated economic expected return must be positive for BUY",
            symbol=normalized_symbol,
            business_date=business_date,
            feature_date=feature_date,
            payload=payload,
            artifact_path=artifact_path,
            artifact_hash=artifact_hash,
            schema_status=schema_status,
            artifact_status=artifact_status,
            excluded_at_stage=excluded_at_stage,
            score_contract=score_contract,
        )
    if opportunity_no_buy_reason_blocks_buy(
        no_buy_reason,
        economic_units_available=bool(score_contract["economic_units_available"]),
    ):
        return _result_from_row(
            row,
            status="BLOCKED",
            eligibility="BUY_INELIGIBLE",
            reason_code="opportunity_no_buy_reason_present",
            reason="Opportunity no_buy_reason blocks new BUY",
            symbol=normalized_symbol,
            business_date=business_date,
            feature_date=feature_date,
            payload=payload,
            artifact_path=artifact_path,
            artifact_hash=artifact_hash,
            schema_status=schema_status,
            artifact_status=artifact_status,
            excluded_at_stage=excluded_at_stage,
            score_contract=score_contract,
        )
    reason_code = (
        "uncalibrated_relative_score_competition_eligible"
        if not score_contract["economic_units_available"]
        else "opportunity_positive_expected_edge"
    )
    reason = (
        "Uncalibrated runtime opportunity score is eligible for relative competition"
        if not score_contract["economic_units_available"]
        else "Opportunity economic expected edge is positive and no blocking no_buy_reason is present"
    )
    return _result_from_row(
        row,
        status="PASS",
        eligibility="BUY_ELIGIBLE",
        reason_code=reason_code,
        reason=reason,
        symbol=normalized_symbol,
        business_date=business_date,
        feature_date=feature_date,
        payload=payload,
        artifact_path=artifact_path,
        artifact_hash=artifact_hash,
        schema_status=schema_status,
        artifact_status=artifact_status,
        excluded_at_stage=excluded_at_stage,
        score_contract=score_contract,
    )


def opportunity_no_buy_reason_blocks_buy(no_buy_reason: Any, *, economic_units_available: bool = True) -> bool:
    reasons = {part.strip().lower() for part in str(no_buy_reason or "").split("|") if part.strip()}
    reasons = {reason for reason in reasons if reason not in NO_BUY_REASON_EMPTY_VALUES}
    if not reasons:
        return False
    relative_metadata_reasons = {"non_positive_expected_edge_score", "below_opportunity_top20"}
    hard_reasons = {
        "high_downside_risk_score",
        "corporate_event_block",
        "corporate_action_block",
        "liquidity_block",
        "not_currently_listed",
        "unsupported_broker_product_category",
        "broker_product_category_unsupported",
    }
    if reasons & hard_reasons:
        return True
    if economic_units_available and "non_positive_expected_edge_score" in reasons:
        return True
    return bool(reasons - relative_metadata_reasons)


def _score_contract(*, row: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        field: _finite_float(row.get(field))
        for field in ("runtime_opportunity_score", "expected_edge_score", "opportunity_score")
        if field in row
    }
    fields = {field: value for field, value in fields.items() if value is not None}
    canonical_field = str(payload.get("canonical_score_field") or row.get("canonical_score_field") or "runtime_opportunity_score")
    score = fields.get(canonical_field)
    source_field = canonical_field if score is not None else ""
    if score is None:
        for field in ("runtime_opportunity_score", "expected_edge_score", "opportunity_score"):
            if field in fields:
                score = fields[field]
                source_field = field
                break
    if score is None:
        return {
            "status": "BLOCKED",
            "reason_code": "opportunity_score_invalid",
            "reason": "Opportunity score is missing or non-finite",
            "score": None,
        }
    if len({round(value, 12) for value in fields.values()}) > 1:
        return {
            "status": "BLOCKED",
            "reason_code": "opportunity_score_field_conflict",
            "reason": "Opportunity score aliases disagree",
            "score": score,
        }
    calibration_applied = _truthy_bool(row.get("calibration_applied", payload.get("calibration_applied", False)))
    economic_units_available = _truthy_bool(
        row.get("economic_units_available", payload.get("economic_units_available", False))
    )
    semantic_role = str(
        row.get("score_semantic_role")
        or payload.get("score_semantic_role")
        or ("calibrated_economic_expected_return" if calibration_applied and economic_units_available else "uncalibrated_relative_model_score")
    )
    prediction_semantics = str(row.get("prediction_semantics") or payload.get("prediction_semantics") or "runtime_opportunity_score")
    economic_roles = {
        "calibrated_economic_expected_return",
        "calibrated_expected_return",
        "calibrated_expected_edge",
        "economic_expected_return",
        "economic_expected_edge",
    }
    uncalibrated_roles = {
        "uncalibrated_relative_model_score",
        "relative_opportunity_score",
        "runtime_opportunity_score",
        "raw_model_score",
        "model_score",
    }
    if economic_units_available and (not calibration_applied or semantic_role not in economic_roles):
        return {
            "status": "BLOCKED",
            "reason_code": "opportunity_score_semantic_metadata_malformed",
            "reason": "Economic opportunity score metadata is malformed",
            "score": score,
        }
    if not economic_units_available and semantic_role not in uncalibrated_roles:
        return {
            "status": "BLOCKED",
            "reason_code": "opportunity_score_semantic_metadata_malformed",
            "reason": "Uncalibrated opportunity score metadata is malformed",
            "score": score,
        }
    return {
        "status": "PASS",
        "reason_code": "",
        "reason": "",
        "score": score,
        "source_field": source_field,
        "canonical_score_field": canonical_field,
        "prediction_semantics": prediction_semantics,
        "score_semantic_role": semantic_role,
        "calibration_applied": calibration_applied,
        "economic_units_available": economic_units_available,
        "absolute_economic_gate_applicable": bool(calibration_applied and economic_units_available),
        "expected_edge_score_semantic_role": str(
            row.get("expected_edge_score_semantic_role")
            or payload.get("expected_edge_score_semantic_role")
            or "deprecated_alias_uncalibrated_runtime_opportunity_score"
        ),
        "expected_return_semantic_role": str(
            row.get("expected_return_semantic_role")
            or payload.get("expected_return_semantic_role")
            or "deprecated_alias_uncalibrated_runtime_opportunity_score_not_economic_return"
        ),
    }


def _find_payload_row_by_identity(
    *,
    payload: Mapping[str, Any],
    symbol: str,
    expected_row_id: str,
    business_date: str,
) -> Mapping[str, Any] | None:
    for index, item in enumerate(payload.get("rankings") or (), start=1):
        if not isinstance(item, Mapping):
            continue
        if _symbol(item.get("symbol") or item.get("code")) != symbol:
            continue
        if _opportunity_row_id(row=item, business_date=business_date, symbol=symbol, index=index) == expected_row_id:
            return item
    return None


def _opportunity_row_id(*, row: Mapping[str, Any], business_date: str, symbol: str, index: int) -> str:
    explicit = str(row.get("opportunity_id") or row.get("row_id") or "")
    if explicit:
        return explicit
    rank = str(row.get("buy_rank") or row.get("rank") or index)
    digest = hashlib.sha256(
        json.dumps(
            {
                "business_date": str(row.get("business_date") or business_date),
                "feature_date": str(row.get("feature_date") or row.get("target_date") or business_date),
                "symbol": symbol,
                "rank": rank,
                "expected_edge_score": row.get("expected_edge_score"),
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:16]
    return f"opportunity-{business_date}-{symbol}-{rank}-{digest}"


def _date_mismatch(
    reason_code: str,
    symbol: str,
    business_date: str,
    feature_date: str,
    payload: Mapping[str, Any],
    artifact_path: Path | None,
    artifact_hash: str,
    excluded_at_stage: str,
) -> OpportunityBuyEligibilityResult:
    return _result(
        status="BLOCKED",
        eligibility="BUY_INELIGIBLE",
        reason_code=reason_code,
        reason="Opportunity artifact temporal authority mismatch",
        symbol=symbol,
        business_date=business_date,
        feature_date=feature_date,
        artifact_path=str(artifact_path or ""),
        artifact_hash=artifact_hash,
        opportunity_business_date=str(payload.get("business_date") or ""),
        opportunity_feature_date=str(payload.get("feature_date") or ""),
        schema_status="PASS" if payload.get("schema_version") else "MISSING",
        artifact_status=str(payload.get("status") or ""),
        excluded_at_stage=excluded_at_stage,
    )


def _result_from_row(
    row: Mapping[str, Any],
    *,
    status: str,
    eligibility: str,
    reason_code: str,
    reason: str,
    symbol: str,
    business_date: str,
    feature_date: str,
    payload: Mapping[str, Any],
    artifact_path: Path | None,
    artifact_hash: str,
    schema_status: str,
    artifact_status: str,
    excluded_at_stage: str,
    score_contract: Mapping[str, Any] | None = None,
) -> OpportunityBuyEligibilityResult:
    contract = dict(score_contract or {})
    return _result(
        status=status,
        eligibility=eligibility,
        reason_code=reason_code,
        reason=reason,
        symbol=symbol,
        business_date=business_date,
        feature_date=feature_date,
        expected_edge_score=_finite_float(row.get("expected_edge_score")),
        expected_return=_finite_float(row.get("expected_return")),
        runtime_opportunity_score=_finite_float(row.get("runtime_opportunity_score", contract.get("score"))),
        no_buy_reason=str(row.get("no_buy_reason") or ""),
        buy_rank=_int_or_none(row.get("buy_rank") if row.get("buy_rank") not in (None, "") else row.get("rank")),
        is_top5=_bool_or_none(row.get("is_top5")),
        artifact_path=str(artifact_path or ""),
        artifact_hash=artifact_hash,
        opportunity_business_date=str(row.get("business_date") or payload.get("business_date") or ""),
        opportunity_feature_date=str(row.get("feature_date") or row.get("target_date") or payload.get("feature_date") or ""),
        row_present=True,
        schema_status=schema_status,
        artifact_status=artifact_status,
        row_id=str(row.get("opportunity_row_id") or row.get("row_id") or row.get("opportunity_id") or ""),
        opportunity_authority=str(row.get("opportunity_authority") or ""),
        excluded_at_stage=excluded_at_stage,
        canonical_score_field=str(contract.get("canonical_score_field") or ""),
        score_semantic_role=str(contract.get("score_semantic_role") or ""),
        calibration_applied=bool(contract.get("calibration_applied", False)),
        economic_units_available=bool(contract.get("economic_units_available", False)),
        absolute_economic_gate_applicable=bool(contract.get("absolute_economic_gate_applicable", False)),
        expected_edge_score_semantic_role=str(contract.get("expected_edge_score_semantic_role") or ""),
        expected_return_semantic_role=str(contract.get("expected_return_semantic_role") or ""),
        relative_competition_eligible=(
            contract.get("status") == "PASS"
            and not bool(contract.get("economic_units_available", False))
        ),
    )


def _result(
    *,
    status: str,
    eligibility: str,
    reason_code: str,
    reason: str,
    symbol: str,
    business_date: str,
    feature_date: str,
    artifact_path: str = "",
    artifact_hash: str = "",
    expected_edge_score: float | None = None,
    expected_return: float | None = None,
    runtime_opportunity_score: float | None = None,
    no_buy_reason: str = "",
    buy_rank: int | None = None,
    is_top5: bool | None = None,
    opportunity_business_date: str = "",
    opportunity_feature_date: str = "",
    row_present: bool = False,
    schema_status: str = "",
    artifact_status: str = "",
    row_id: str = "",
    opportunity_authority: str = "",
    excluded_at_stage: str = "",
    canonical_score_field: str = "",
    score_semantic_role: str = "",
    calibration_applied: bool = False,
    economic_units_available: bool = False,
    absolute_economic_gate_applicable: bool = False,
    expected_edge_score_semantic_role: str = "",
    expected_return_semantic_role: str = "",
    relative_competition_eligible: bool = False,
) -> OpportunityBuyEligibilityResult:
    return OpportunityBuyEligibilityResult(
        status=status,
        buy_eligibility=eligibility,
        eligible=status == "PASS" and eligibility == "BUY_ELIGIBLE",
        reason_code=reason_code,
        reason=reason,
        symbol=symbol,
        business_date=business_date,
        feature_date=feature_date,
        expected_edge_score=expected_edge_score,
        expected_return=expected_return,
        runtime_opportunity_score=runtime_opportunity_score,
        no_buy_reason=no_buy_reason,
        buy_rank=buy_rank,
        is_top5=is_top5,
        opportunity_artifact_path=artifact_path,
        opportunity_artifact_hash=artifact_hash,
        opportunity_business_date=opportunity_business_date,
        opportunity_feature_date=opportunity_feature_date,
        opportunity_row_present=row_present,
        opportunity_schema_status=schema_status,
        opportunity_artifact_status=artifact_status,
        opportunity_row_id=row_id,
        opportunity_authority=opportunity_authority,
        excluded_at_stage=excluded_at_stage,
        canonical_score_field=canonical_score_field,
        score_semantic_role=score_semantic_role,
        calibration_applied=calibration_applied,
        economic_units_available=economic_units_available,
        absolute_economic_gate_applicable=absolute_economic_gate_applicable,
        expected_edge_score_semantic_role=expected_edge_score_semantic_role,
        expected_return_semantic_role=expected_return_semantic_role,
        relative_competition_eligible=relative_competition_eligible,
    )


def _symbol(value: Any) -> str:
    return str(value or "").strip().upper().removesuffix(".T")


def _finite_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _truthy_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool_or_none(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _file_hash(path: Path | None) -> str:
    if path is None or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_hash(value: str) -> str:
    return str(value or "").removeprefix("sha256:")
