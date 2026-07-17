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
    excluded_at_stage: str = ""

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
    if not row and payload:
        for item in payload.get("rankings") or ():
            if _symbol(item.get("symbol") or item.get("code")) == normalized_symbol:
                row = dict(item)
                break
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
    expected_edge = _finite_float(row.get("expected_edge_score"))
    if expected_edge is None:
        return _result_from_row(
            row,
            status="BLOCKED",
            eligibility="BUY_INELIGIBLE",
            reason_code="opportunity_expected_edge_invalid",
            reason="Opportunity expected_edge_score is missing or non-finite",
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
    no_buy_reason = str(row.get("no_buy_reason") or "").strip()
    if expected_edge <= 0:
        return _result_from_row(
            row,
            status="BLOCKED",
            eligibility="BUY_INELIGIBLE",
            reason_code="non_positive_expected_edge_score",
            reason="Opportunity expected_edge_score must be positive for BUY",
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
    if no_buy_reason.lower() not in NO_BUY_REASON_EMPTY_VALUES:
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
        )
    return _result_from_row(
        row,
        status="PASS",
        eligibility="BUY_ELIGIBLE",
        reason_code="opportunity_positive_expected_edge",
        reason="Opportunity expected edge is positive and no no_buy_reason is present",
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
) -> OpportunityBuyEligibilityResult:
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
        excluded_at_stage=excluded_at_stage,
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
    no_buy_reason: str = "",
    buy_rank: int | None = None,
    is_top5: bool | None = None,
    opportunity_business_date: str = "",
    opportunity_feature_date: str = "",
    row_present: bool = False,
    schema_status: str = "",
    artifact_status: str = "",
    excluded_at_stage: str = "",
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
        excluded_at_stage=excluded_at_stage,
    )


def _symbol(value: Any) -> str:
    return str(value or "").strip().upper().removesuffix(".T")


def _finite_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


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
