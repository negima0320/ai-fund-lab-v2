"""Current valuation-only / no-fill producer for Runtime v2."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.current_state.temporal import (
    CURRENT_TEMPORAL_SCHEMA_VERSION,
    build_current_temporal_candidate,
    write_current_temporal_state,
)
from ai_fund_lab_v2.runtime_v2.historical_support.asof import SUPPORTED_ASOF_SCHEMA_VERSIONS
from ai_fund_lab_v2.runtime_v2.temporal import (
    FreshnessStatus,
    evaluate_current_position_freshness,
    evaluate_current_valuation_freshness,
    resolve_temporal_context,
)


CURRENT_VALUATION_REFRESH_SCHEMA_VERSION = "runtime_v2_current_valuation_refresh_v1"
ALLOWED_MARKET_STATUSES = {"READY", "VALID_CARRYOVER"}
ALLOWED_PRICE_TYPES = {"daily_close", "intraday_quote", "broker_valuation_price", "jquants_daily_quote"}


@dataclass(frozen=True)
class CurrentValuationRefreshResult:
    status: str
    reason: str
    artifact_path: str
    source_current_path: str
    market_evidence_path: str
    market_date: str
    valuation_as_of: str
    position_state_as_of: str
    no_fill: bool
    position_count: int
    valued_position_count: int
    missing_symbols: tuple[str, ...]
    valuation_source: str
    previous_total_market_value: float
    new_total_market_value: float
    previous_unrealized_pnl: float
    new_unrealized_pnl: float
    apply_requested: bool
    apply_executed: bool
    backup_path: str
    review_required: bool
    candidate_current: dict[str, Any]
    valuation_refresh_precondition_status: str = ""
    existing_valuation_as_of: str = ""
    previous_trading_date: str = ""
    target_valuation_date: str = ""
    valuation_refresh_action: str = ""
    projection_status: str = ""
    projection_source_market_date: str = ""
    apply_status: str = ""
    post_apply_valuation_as_of: str = ""
    post_apply_source_market_date: str = ""
    postcondition_status: str = ""
    postcondition_reason: str = ""
    temporal_authority: str = ""
    temporal_reason: str = ""

    @property
    def manifest_fields(self) -> dict[str, Any]:
        return {
            "current_valuation_refresh_status": self.status,
            "current_valuation_refresh_reason": self.reason,
            "current_valuation_refresh_artifact_path": self.artifact_path,
            "current_valuation_source_current_path": self.source_current_path,
            "current_valuation_market_evidence_path": self.market_evidence_path,
            "current_valuation_market_date": self.market_date,
            "current_valuation_as_of": self.valuation_as_of,
            "current_valuation_position_state_as_of": self.position_state_as_of,
            "current_valuation_no_fill": self.no_fill,
            "current_valuation_position_count": self.position_count,
            "current_valuation_valued_position_count": self.valued_position_count,
            "current_valuation_missing_symbols": list(self.missing_symbols),
            "current_valuation_source": self.valuation_source,
            "current_valuation_previous_total_market_value": self.previous_total_market_value,
            "current_valuation_new_total_market_value": self.new_total_market_value,
            "current_valuation_previous_unrealized_pnl": self.previous_unrealized_pnl,
            "current_valuation_new_unrealized_pnl": self.new_unrealized_pnl,
            "current_valuation_apply_requested": self.apply_requested,
            "current_valuation_apply_executed": self.apply_executed,
            "current_valuation_backup_path": self.backup_path,
            "current_valuation_review_required": self.review_required,
            "valuation_refresh_precondition_status": self.valuation_refresh_precondition_status,
            "existing_valuation_as_of": self.existing_valuation_as_of,
            "previous_trading_date": self.previous_trading_date,
            "target_valuation_date": self.target_valuation_date,
            "valuation_refresh_action": self.valuation_refresh_action,
            "projection_status": self.projection_status,
            "projection_source_market_date": self.projection_source_market_date,
            "apply_status": self.apply_status,
            "post_apply_valuation_as_of": self.post_apply_valuation_as_of,
            "post_apply_source_market_date": self.post_apply_source_market_date,
            "postcondition_status": self.postcondition_status,
            "postcondition_reason": self.postcondition_reason,
            "temporal_authority": self.temporal_authority,
            "temporal_reason": self.temporal_reason,
            "current_position_status": self.candidate_current.get("current_position_status") or "",
            "current_valuation_status": self.candidate_current.get("current_valuation_status") or "",
        }


def validate_current_valuation_input(*, current: dict[str, Any], market_evidence: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    reasons: list[str] = []
    if current.get("temporal_schema_version") != CURRENT_TEMPORAL_SCHEMA_VERSION:
        reasons.append("current_temporal_schema_required")
    market_status = str(market_evidence.get("market_status") or "")
    freshness = str(market_evidence.get("market_freshness_status") or market_status)
    market_date = str(market_evidence.get("market_date") or "")
    if market_status not in ALLOWED_MARKET_STATUSES or freshness not in ALLOWED_MARKET_STATUSES:
        reasons.append("market_status_not_allowed")
    if not market_date:
        reasons.append("market_date_missing")
    return ("READY" if not reasons else "REVIEW_REQUIRED", tuple(reasons))


def build_current_valuation_candidate(
    *,
    runtime_root: Path | str,
    business_date: str,
    now: datetime | None = None,
    market_evidence_path: Path | str | None = None,
    allow_legacy_temporal_current: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], tuple[str, ...], tuple[str, ...]]:
    root = Path(runtime_root)
    current_path = root / "persistent_ledger" / "state.json"
    current_payload = _read_json(current_path)
    temporal_current, metadata, missing_evidence, warnings = build_current_temporal_candidate(
        runtime_root=root,
        business_date=business_date,
        current_payload=current_payload,
        now=now,
    )
    legacy_allowed = allow_legacy_temporal_current and not missing_evidence
    if (metadata.legacy_as_of_used and not legacy_allowed) or (metadata.review_required and not legacy_allowed):
        return temporal_current, {}, tuple(missing_evidence), tuple((*warnings, "current_temporal_migration_required_before_valuation"))
    positions = [_normalize_position(position) for position in temporal_current.get("positions") or []]
    runtime_positions = [position for position in positions if not _is_broker_only_position(position)]
    market_path, market = _load_market_evidence(
        root,
        market_evidence_path=market_evidence_path,
        business_date=business_date,
        required_symbols={_symbol(position) for position in runtime_positions if _symbol(position)},
    )
    market_date = str(market.get("market_date") or market.get("latest_available_market_date") or "")
    freshness = str(market.get("market_freshness_status") or market.get("market_status") or "")
    if freshness == "DATA_NOT_YET_AVAILABLE":
        return temporal_current, market, ("market_data_not_yet_available",), warnings
    quotes = dict(market.get("quotes") or {})
    validation_status, validation_reasons = validate_current_valuation_input(current=temporal_current, market_evidence=market)
    if validation_status != "READY":
        return temporal_current, market, tuple(validation_reasons), warnings
    if not runtime_positions:
        candidate = dict(temporal_current)
        candidate.update(
            {
                "no_position": True,
                "no_position_reason": "current_has_no_runtime_owned_positions",
                "no_fill": True,
                "previous_valuation_as_of": str(temporal_current.get("valuation_as_of") or ""),
                "previous_trading_date": str(temporal_current.get("valuation_as_of") or ""),
                "valuation_as_of": market_date or candidate.get("valuation_as_of") or "",
                "source_market_date": market_date or candidate.get("source_market_date") or "",
                "valuation_source": str(market_path),
                "valuation_generated_at": _iso(now),
            }
        )
        return _attach_temporal_status(candidate, business_date=business_date, now=now), market, (), warnings
    quote_status = str(market.get("quote_status") or "")
    quote_status_not_allowed = quote_status not in ALLOWED_MARKET_STATUSES
    missing_symbols: list[str] = []
    invalid_symbols: list[str] = []
    valued_positions: list[dict[str, Any]] = []
    for position in runtime_positions:
        symbol = _symbol(position)
        quote = _quote_for_symbol(quotes, symbol)
        if not quote:
            missing_symbols.append(symbol)
            continue
        price, price_authority, price_reason, price_basis = _resolve_basis_compatible_valuation_price(
            position=position,
            quote=quote,
        )
        if price is None or price <= 0:
            invalid_symbols.append(symbol)
            continue
        if price_authority != "PASS":
            invalid_symbols.append(symbol)
            continue
        price_type = str(quote.get("price_type") or "")
        if price_type not in ALLOWED_PRICE_TYPES:
            invalid_symbols.append(symbol)
            continue
        quote_freshness = str(quote.get("freshness_status") or "")
        if quote_freshness not in ALLOWED_MARKET_STATUSES:
            invalid_symbols.append(symbol)
            continue
        quote_market_date = str(quote.get("market_date") or "")
        if quote_market_date and quote_market_date != market_date:
            invalid_symbols.append(symbol)
            continue
        if not str(quote.get("source") or ""):
            invalid_symbols.append(symbol)
            continue
        quantity = float(position.get("quantity") or 0)
        average_price = float(position.get("average_price") or position.get("avg_price") or 0)
        updated = dict(position)
        updated["current_price"] = price
        updated["market_value"] = quantity * price
        updated["unrealized_pnl"] = (price - average_price) * quantity
        updated["valuation_as_of"] = market_date
        updated["source_market_date"] = market_date
        updated["valuation_source"] = str(quote.get("source") or market_path)
        updated["valuation_price_type"] = price_type
        updated["valuation_adjusted"] = bool(quote.get("adjusted"))
        updated["valuation_price_authority"] = price_authority
        updated["valuation_price_authority_reason"] = price_reason
        updated["valuation_price_basis"] = price_basis
        updated["quantity_basis"] = price_basis
        updated["valuation_price_role"] = _valuation_price_role_for_basis(quote=quote, price_basis=price_basis)
        updated["valuation_price_provenance"] = str(
            _valuation_price_provenance_for_basis(quote=quote, price_basis=price_basis)
            or quote.get("price_provenance")
            or quote.get("source")
            or market_path
        )
        valued_positions.append(updated)
    if missing_symbols or invalid_symbols or quote_status_not_allowed:
        reasons = ["current_valuation_quote_missing"] if missing_symbols else []
        if quote_status_not_allowed:
            reasons.append("quote_status_not_allowed")
        reasons.extend("current_valuation_quote_invalid:" + symbol for symbol in invalid_symbols)
        return temporal_current, market, tuple(sorted(reasons + missing_symbols)), warnings
    previous_total = _sum_market_value(runtime_positions)
    previous_unrealized = _sum_unrealized(runtime_positions)
    candidate = dict(temporal_current)
    candidate["previous_valuation_as_of"] = str(temporal_current.get("valuation_as_of") or "")
    candidate["previous_trading_date"] = str(temporal_current.get("valuation_as_of") or "")
    candidate["positions"] = valued_positions
    candidate["market_value"] = _sum_market_value(valued_positions)
    candidate["total_equity"] = float(candidate.get("cash") or 0) + candidate["market_value"]
    candidate["valuation_as_of"] = market_date
    candidate["source_market_date"] = market_date
    candidate["valuation_source"] = str(market_path)
    candidate["valuation_generated_at"] = _iso(now)
    candidate["no_fill"] = True
    candidate["previous_total_market_value"] = previous_total
    candidate["new_total_market_value"] = candidate["market_value"]
    candidate["previous_unrealized_pnl"] = previous_unrealized
    candidate["new_unrealized_pnl"] = _sum_unrealized(valued_positions)
    candidate["cash"] = temporal_current.get("cash")
    candidate["buying_power"] = temporal_current.get("buying_power")
    candidate["realized_pnl"] = temporal_current.get("realized_pnl")
    return _attach_temporal_status(candidate, business_date=business_date, now=now), market, (), warnings


def run_current_valuation_refresh(
    *,
    runtime_root: Path | str,
    business_date: str,
    apply_current_valuation: bool = False,
    now: datetime | None = None,
    market_evidence_path: Path | str | None = None,
    safety_authority: dict[str, Any] | None = None,
    runtime_test_context: dict[str, Any] | None = None,
    environment_context: dict[str, Any] | None = None,
    allow_legacy_temporal_current: bool = False,
) -> CurrentValuationRefreshResult:
    root = Path(runtime_root)
    generated_at = _iso(now)
    artifact_path = root / "runtime_state" / "current_valuation" / business_date / "current_valuation_refresh.json"
    source_path = root / "persistent_ledger" / "state.json"
    try:
        candidate, market, missing, warnings = build_current_valuation_candidate(
            runtime_root=root,
            business_date=business_date,
            now=now,
            market_evidence_path=market_evidence_path,
            allow_legacy_temporal_current=allow_legacy_temporal_current,
        )
    except ValueError as exc:
        payload = _artifact_payload(
            business_date=business_date,
            generated_at=generated_at,
            status="HALT",
            reason=str(exc),
            source_current_path=str(source_path),
            market_evidence_path="",
            market_date="",
            candidate_current={},
            missing_symbols=(),
            missing_evidence=("current",),
            warnings=(str(exc),),
            apply_requested=apply_current_valuation,
            apply_executed=False,
            backup_path="",
            history_path="",
            projection_status="NOT_EXECUTED",
        )
        _write_json(artifact_path, payload)
        return _result_from_payload(payload, artifact_path=artifact_path)
    market_path, _ = (
        _load_market_evidence(
            root,
            market_evidence_path=market_evidence_path,
            business_date=business_date,
            required_symbols={_symbol(position) for position in candidate.get("positions") or [] if _symbol(position)},
        )
        if market
        else ("", {})
    )
    authority_reasons = _authority_review_reasons(
        business_date=business_date,
        candidate_current=candidate,
        market_evidence_path=str(market_path),
        market_date=str(market.get("market_date") or ""),
        safety_authority=safety_authority,
        runtime_test_context=runtime_test_context,
        environment_context=environment_context,
    )
    if authority_reasons:
        missing = tuple((*missing, *authority_reasons))
    missing_symbols = _missing_symbols_from_reasons(missing)
    position_count = len(candidate.get("positions") or [])
    valued_position_count = _valued_position_count(candidate)
    valuation_incomplete = valued_position_count != position_count and not candidate.get("no_position")
    status = "READY" if not missing and not warnings and not valuation_incomplete else "REVIEW_REQUIRED"
    reason = "current_valuation_ready" if status == "READY" else "current_valuation_review_required"
    if candidate.get("no_position"):
        status = "READY"
        reason = "current_has_no_runtime_owned_positions"
    projection_status = "PASS" if status == "READY" else "REVIEW_REQUIRED"
    apply_executed = False
    backup_path = ""
    history_path = _write_valuation_history(root=root, valuation_as_of=str(candidate.get("valuation_as_of") or business_date), candidate=candidate, market=market)
    postcondition_status = "NOT_APPLICABLE"
    postcondition_reason = "apply_not_requested"
    if apply_current_valuation and status == "READY":
        backup_path = str(_atomic_write_current(root=root, source_path=source_path, payload=candidate, now=now))
        apply_executed = True
        postcondition_reasons = _post_apply_validation(source_path=source_path, business_date=business_date)
        if postcondition_reasons:
            status = "REVIEW_REQUIRED"
            reason = "current_valuation_postcondition_failed"
            missing = tuple((*missing, *postcondition_reasons))
            postcondition_status = "REVIEW_REQUIRED"
            postcondition_reason = ",".join(postcondition_reasons)
        else:
            postcondition_status = "PASS"
            postcondition_reason = "current_valuation_postcondition_ready"
    elif apply_current_valuation and status != "READY":
        postcondition_status = "NOT_EXECUTED"
        postcondition_reason = "apply_not_executed_because_projection_not_ready"
    payload = _artifact_payload(
        business_date=business_date,
        generated_at=generated_at,
        status=status,
        reason=reason,
        source_current_path=str(source_path),
        market_evidence_path=str(market_path),
        market_date=str(market.get("market_date") or ""),
        candidate_current=candidate,
        missing_symbols=missing_symbols,
        missing_evidence=missing,
        warnings=warnings,
        apply_requested=apply_current_valuation,
        apply_executed=apply_executed,
        backup_path=backup_path,
        history_path=str(history_path),
        projection_status=projection_status,
        postcondition_status=postcondition_status,
        postcondition_reason=postcondition_reason,
    )
    _write_json(artifact_path, payload)
    return _result_from_payload(payload, artifact_path=artifact_path)


def _attach_temporal_status(candidate: dict[str, Any], *, business_date: str, now: datetime | None) -> dict[str, Any]:
    context = resolve_temporal_context(
        runtime_business_date=business_date,
        latest_available_market_date=str(candidate.get("source_market_date") or "") or None,
        now=now,
    )
    from ai_fund_lab_v2.runtime_v2.temporal import CurrentTemporalState

    state = CurrentTemporalState(
        position_state_as_of=str(candidate.get("position_state_as_of") or ""),
        valuation_as_of=str(candidate.get("valuation_as_of") or ""),
        last_execution_date=str(candidate.get("last_execution_date") or ""),
        last_reconciled_at=str(candidate.get("last_reconciled_at") or ""),
        source_market_date=str(candidate.get("source_market_date") or ""),
    )
    position = evaluate_current_position_freshness(context=context, current=state)
    valuation = evaluate_current_valuation_freshness(context=context, current=state, now=now)
    candidate["current_position_status"] = position.status.value
    candidate["current_valuation_status"] = valuation.status.value
    candidate["current_position_temporal_evidence"] = position.to_payload()
    candidate["current_valuation_temporal_evidence"] = valuation.to_payload()
    candidate["temporal_status"] = "READY" if valuation.status in {FreshnessStatus.READY, FreshnessStatus.VALID_CARRYOVER} else "REVIEW_REQUIRED"
    return candidate


def _artifact_payload(
    *,
    business_date: str,
    generated_at: str,
    status: str,
    reason: str,
    source_current_path: str,
    market_evidence_path: str,
    market_date: str,
    candidate_current: dict[str, Any],
    missing_symbols: tuple[str, ...],
    missing_evidence: tuple[str, ...],
    warnings: tuple[str, ...],
    apply_requested: bool,
    apply_executed: bool,
    backup_path: str,
    history_path: str,
    projection_status: str,
    postcondition_status: str = "NOT_APPLICABLE",
    postcondition_reason: str = "",
) -> dict[str, Any]:
    apply_status = "APPLIED" if apply_executed else "NOT_REQUESTED" if not apply_requested else "NOT_EXECUTED"
    return {
        "schema_version": CURRENT_VALUATION_REFRESH_SCHEMA_VERSION,
        "business_date": business_date,
        "generated_at": generated_at,
        "status": status,
        "reason": reason,
        "review_required": status == "REVIEW_REQUIRED",
        "apply_requested": apply_requested,
        "apply_executed": apply_executed,
        "valuation_refresh_precondition_status": "PASS" if candidate_current else "REVIEW_REQUIRED",
        "existing_valuation_as_of": candidate_current.get("previous_valuation_as_of") or "",
        "previous_trading_date": candidate_current.get("previous_trading_date") or "",
        "target_valuation_date": business_date,
        "valuation_refresh_action": "APPLY" if apply_requested else "PROJECT_ONLY",
        "projection_status": projection_status,
        "projection_source_market_date": market_date,
        "apply_status": apply_status,
        "post_apply_valuation_as_of": candidate_current.get("valuation_as_of") if apply_executed else "",
        "post_apply_source_market_date": candidate_current.get("source_market_date") if apply_executed else "",
        "postcondition_status": postcondition_status,
        "postcondition_reason": postcondition_reason,
        "temporal_authority": "current_valuation_business_date_projection",
        "temporal_reason": "current_valuation_projection_uses_target_market_date",
        "source_current_path": source_current_path,
        "market_evidence_path": market_evidence_path,
        "market_date": market_date,
        "valuation_as_of": candidate_current.get("valuation_as_of") or "",
        "position_state_as_of": candidate_current.get("position_state_as_of") or "",
        "no_fill": bool(candidate_current.get("no_fill")),
        "no_position": bool(candidate_current.get("no_position")),
        "no_position_reason": candidate_current.get("no_position_reason") or "",
        "position_count": len(candidate_current.get("positions") or []),
        "valued_position_count": _valued_position_count(candidate_current),
        "missing_symbols": list(missing_symbols),
        "missing_evidence": list(missing_evidence),
        "warnings": list(warnings),
        "valuation_source": candidate_current.get("valuation_source") or "",
        "previous_total_market_value": float(candidate_current.get("previous_total_market_value") or 0),
        "new_total_market_value": float(candidate_current.get("new_total_market_value") or candidate_current.get("market_value") or 0),
        "previous_unrealized_pnl": float(candidate_current.get("previous_unrealized_pnl") or 0),
        "new_unrealized_pnl": float(candidate_current.get("new_unrealized_pnl") or 0),
        "candidate_current": candidate_current,
        "backup_path": backup_path,
        "history_path": history_path,
        "next_operator_action": "review missing quote/current evidence" if status == "REVIEW_REQUIRED" else "apply explicitly if reviewing temp candidate is accepted",
    }


def _result_from_payload(payload: dict[str, Any], *, artifact_path: Path) -> CurrentValuationRefreshResult:
    return CurrentValuationRefreshResult(
        status=str(payload.get("status") or ""),
        reason=str(payload.get("reason") or ""),
        artifact_path=str(artifact_path),
        source_current_path=str(payload.get("source_current_path") or ""),
        market_evidence_path=str(payload.get("market_evidence_path") or ""),
        market_date=str(payload.get("market_date") or ""),
        valuation_as_of=str(payload.get("valuation_as_of") or ""),
        position_state_as_of=str(payload.get("position_state_as_of") or ""),
        no_fill=bool(payload.get("no_fill")),
        position_count=int(payload.get("position_count") or 0),
        valued_position_count=int(payload.get("valued_position_count") or 0),
        missing_symbols=tuple(payload.get("missing_symbols") or ()),
        valuation_source=str(payload.get("valuation_source") or ""),
        previous_total_market_value=float(payload.get("previous_total_market_value") or 0),
        new_total_market_value=float(payload.get("new_total_market_value") or 0),
        previous_unrealized_pnl=float(payload.get("previous_unrealized_pnl") or 0),
        new_unrealized_pnl=float(payload.get("new_unrealized_pnl") or 0),
        apply_requested=bool(payload.get("apply_requested")),
        apply_executed=bool(payload.get("apply_executed")),
        backup_path=str(payload.get("backup_path") or ""),
        review_required=bool(payload.get("review_required")),
        candidate_current=dict(payload.get("candidate_current") or {}),
        valuation_refresh_precondition_status=str(payload.get("valuation_refresh_precondition_status") or ""),
        existing_valuation_as_of=str(payload.get("existing_valuation_as_of") or ""),
        previous_trading_date=str(payload.get("previous_trading_date") or ""),
        target_valuation_date=str(payload.get("target_valuation_date") or ""),
        valuation_refresh_action=str(payload.get("valuation_refresh_action") or ""),
        projection_status=str(payload.get("projection_status") or ""),
        projection_source_market_date=str(payload.get("projection_source_market_date") or ""),
        apply_status=str(payload.get("apply_status") or ""),
        post_apply_valuation_as_of=str(payload.get("post_apply_valuation_as_of") or ""),
        post_apply_source_market_date=str(payload.get("post_apply_source_market_date") or ""),
        postcondition_status=str(payload.get("postcondition_status") or ""),
        postcondition_reason=str(payload.get("postcondition_reason") or ""),
        temporal_authority=str(payload.get("temporal_authority") or ""),
        temporal_reason=str(payload.get("temporal_reason") or ""),
    )


def _load_market_evidence(
    root: Path,
    *,
    market_evidence_path: Path | str | None = None,
    business_date: str = "",
    required_symbols: set[str] | None = None,
) -> tuple[Path | str, dict[str, Any]]:
    if market_evidence_path:
        path = Path(market_evidence_path)
        payload = _read_json(path)
        if payload.get("schema_version") in SUPPORTED_ASOF_SCHEMA_VERSIONS:
            return path, _market_evidence_from_historical_asof_view(
                path=path,
                payload=payload,
                business_date=business_date or str(payload.get("business_date") or ""),
                required_symbols=required_symbols or set(),
            )
        if path.name == "historical_asof_view.json" or "authorities" in payload:
            raise ValueError(f"unsupported historical_asof_view schema_version: {payload.get('schema_version') or '<missing>'}")
        return path, payload
    latest = root / "runtime_state" / "market" / "latest.json"
    if latest.is_file():
        payload = _read_json(latest)
        artifact = Path(str(payload.get("artifact_path") or ""))
        if artifact.is_file():
            return artifact, _read_json(artifact)
    candidates = sorted((root / "runtime_state" / "market").glob("*/market_evidence.json"))
    if not candidates:
        raise ValueError("market_evidence missing")
    return candidates[-1], _read_json(candidates[-1])


def _market_evidence_from_historical_asof_view(
    *,
    path: Path,
    payload: dict[str, Any],
    business_date: str,
    required_symbols: set[str],
) -> dict[str, Any]:
    if str(payload.get("status") or "") != "PASS":
        return _market_review_payload(path=path, business_date=business_date, reason="historical_asof_view_not_pass")
    if str(payload.get("business_date") or "") != business_date:
        return _market_review_payload(path=path, business_date=business_date, reason="historical_asof_view_business_date_mismatch")
    authority = next(
        (
            dict(entry)
            for entry in payload.get("authorities") or []
            if str(entry.get("authority") or "") == "normalized_ohlcv" and str(entry.get("status") or "") == "PASS"
        ),
        {},
    )
    raw_authority = next(
        (
            dict(entry)
            for entry in payload.get("authorities") or []
            if str(entry.get("authority") or "") == "raw_ohlcv" and str(entry.get("status") or "") == "PASS"
        ),
        {},
    )
    source_path = _historical_logical_normalized_ohlcv_path_from_asof_view(
        asof_view_path=path,
        business_date=business_date,
        fallback_physical_path=Path(str(authority.get("physical_source_path") or "")),
    )
    raw_source_path = _historical_logical_raw_ohlcv_path_from_asof_view(
        asof_view_path=path,
        business_date=business_date,
        fallback_physical_path=Path(str(raw_authority.get("physical_source_path") or "")),
    )
    if not authority or not source_path.is_file():
        return _market_review_payload(path=path, business_date=business_date, reason="historical_normalized_ohlcv_missing")
    quotes, missing = _quotes_from_parquet(
        source_path=source_path,
        market_date=business_date,
        required_symbols=required_symbols,
        economic_source_path=raw_source_path,
    )
    quote_payload = {quote["symbol"]: quote for quote in quotes}
    quote_status = "READY" if not missing and quote_payload else "REVIEW_REQUIRED"
    if not required_symbols and not quote_payload:
        quote_status = "NOT_REQUIRED"
    return {
        "schema_version": "runtime_v2_market_evidence_v1",
        "runtime_business_date": business_date,
        "market_date": business_date,
        "latest_expected_trading_date": business_date,
        "latest_available_market_date": str(payload.get("latest_available_market_date") or business_date),
        "market_status": "READY",
        "market_freshness_status": "READY",
        "quote_status": quote_status,
        "quotes": quote_payload,
        "historical_asof_view_path": str(path),
        "historical_market_authority": "normalized_ohlcv",
        "historical_market_source_path": str(source_path),
        "historical_economic_source_path": str(raw_source_path) if raw_source_path.is_file() else "",
        "historical_market_source_scope": (
            "run_scoped_logical_input"
            if "inputs/historical_asof" in str(source_path)
            else "historical_asof_physical_authority"
        ),
        "missing_symbols": sorted(missing),
    }


def _historical_logical_normalized_ohlcv_path_from_asof_view(
    *,
    asof_view_path: Path,
    business_date: str,
    fallback_physical_path: Path,
) -> Path:
    manifest_path = (
        asof_view_path.parent
        / "inputs"
        / "historical_asof"
        / business_date
        / "logical_input_manifest.json"
    )
    if not manifest_path.exists():
        return fallback_physical_path
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return manifest_path.parent / "__invalid_historical_logical_valuation_source__.parquet"
    if str(manifest.get("business_date") or "") != business_date:
        return manifest_path.parent / "__mismatched_historical_logical_valuation_source__.parquet"
    if str(manifest.get("status") or "") != "PASS":
        return manifest_path.parent / "__blocked_historical_logical_valuation_source__.parquet"
    logical_paths = manifest.get("logical_paths")
    if not isinstance(logical_paths, dict):
        return manifest_path.parent / "__missing_historical_logical_valuation_source__.parquet"
    normalized = str(logical_paths.get("normalized_ohlcv") or "")
    return Path(normalized) if normalized else manifest_path.parent / "__missing_historical_logical_valuation_source__.parquet"


def _historical_logical_raw_ohlcv_path_from_asof_view(
    *,
    asof_view_path: Path,
    business_date: str,
    fallback_physical_path: Path,
) -> Path:
    manifest_path = (
        asof_view_path.parent
        / "inputs"
        / "historical_asof"
        / business_date
        / "logical_input_manifest.json"
    )
    if not manifest_path.exists():
        return fallback_physical_path
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return manifest_path.parent / "__invalid_historical_logical_economic_source__.parquet"
    if str(manifest.get("business_date") or "") != business_date:
        return manifest_path.parent / "__mismatched_historical_logical_economic_source__.parquet"
    if str(manifest.get("status") or "") != "PASS":
        return manifest_path.parent / "__blocked_historical_logical_economic_source__.parquet"
    logical_paths = manifest.get("logical_paths")
    if not isinstance(logical_paths, dict):
        return manifest_path.parent / "__missing_historical_logical_economic_source__.parquet"
    raw = str(logical_paths.get("raw_ohlcv") or "")
    return Path(raw) if raw else manifest_path.parent / "__missing_historical_logical_economic_source__.parquet"


def _market_review_payload(*, path: Path, business_date: str, reason: str) -> dict[str, Any]:
    return {
        "schema_version": "runtime_v2_market_evidence_v1",
        "runtime_business_date": business_date,
        "market_date": business_date,
        "latest_available_market_date": business_date,
        "market_status": "REVIEW_REQUIRED",
        "market_freshness_status": "REVIEW_REQUIRED",
        "quote_status": "REVIEW_REQUIRED",
        "quotes": {},
        "historical_asof_view_path": str(path),
        "reason": reason,
    }


def _quotes_from_parquet(
    *,
    source_path: Path,
    market_date: str,
    required_symbols: set[str],
    economic_source_path: Path | None = None,
) -> tuple[list[dict[str, Any]], set[str]]:
    try:
        import pandas as pd

        frame = pd.read_parquet(source_path)
    except Exception:
        return [], set(required_symbols)
    if frame.empty:
        return [], set(required_symbols)
    date_column = _first_column(frame, ("target_date", "Date", "date", "market_date"))
    code_column = _first_column(frame, ("code", "Code", "LocalCode", "symbol", "issue_code"))
    close_column = _first_column(frame, ("close", "Close", "AdjustmentClose", "adjustment_close", "price"))
    price_source_column = _first_column(frame, ("PriceSource", "price_source"))
    if not date_column or not code_column or not close_column:
        return [], set(required_symbols)
    rows = frame[frame[date_column].astype(str) == market_date].copy()
    if rows.empty:
        return [], set(required_symbols)
    economic_rows = _economic_rows_from_parquet(
        source_path=economic_source_path,
        market_date=market_date,
        required_symbols=required_symbols,
    )
    quotes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows.to_dict(orient="records"):
        symbol = _normalize_symbol(str(row.get(code_column) or ""))
        if not symbol or required_symbols and symbol not in required_symbols:
            continue
        price = row.get(close_column)
        if price is None:
            continue
        price_source = str(row.get(price_source_column) or "").lower() if price_source_column else ""
        adjusted = str(close_column).lower().startswith("adjust") or price_source == "adjusted"
        price_metadata = _normalized_quote_price_metadata(
            adjusted=adjusted,
            price_source=price_source,
            source_column=close_column,
            row=row,
            economic_row=economic_rows.get(symbol),
            economic_source_path=economic_source_path,
        )
        quotes.append(
            {
                "symbol": symbol,
                "price": float(price),
                "price_type": "jquants_daily_quote",
                "market_date": market_date,
                "observed_at": market_date,
                "source": str(source_path),
                "freshness_status": "READY",
                "adjusted": adjusted,
                **price_metadata,
            }
        )
        seen.add(symbol)
    return quotes, set(required_symbols) - seen


def _economic_rows_from_parquet(
    *,
    source_path: Path | None,
    market_date: str,
    required_symbols: set[str],
) -> dict[str, dict[str, Any]]:
    if not source_path or not source_path.is_file():
        return {}
    try:
        import pandas as pd

        frame = pd.read_parquet(source_path)
    except Exception:
        return {}
    if frame.empty:
        return {}
    date_column = _first_column(frame, ("target_date", "Date", "date", "market_date"))
    code_column = _first_column(frame, ("code", "Code", "LocalCode", "symbol", "issue_code"))
    if not date_column or not code_column:
        return {}
    rows = frame[frame[date_column].astype(str) == market_date].copy()
    if rows.empty:
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in rows.to_dict(orient="records"):
        symbol = _normalize_symbol(str(row.get(code_column) or ""))
        if not symbol or required_symbols and symbol not in required_symbols:
            continue
        result[symbol] = row
    return result


def _first_column(frame: Any, candidates: tuple[str, ...]) -> str:
    columns = {str(column): str(column) for column in frame.columns}
    lower = {str(column).lower(): str(column) for column in frame.columns}
    for candidate in candidates:
        if candidate in columns:
            return columns[candidate]
        if candidate.lower() in lower:
            return lower[candidate.lower()]
    return ""


def _write_valuation_history(*, root: Path, valuation_as_of: str, candidate: dict[str, Any], market: dict[str, Any]) -> Path:
    payload = {
        "schema_version": "runtime_v2_current_valuation_history_v1",
        "valuation_as_of": valuation_as_of,
        "no_fill": True,
        "previous_temporal_metadata": {
            "position_state_as_of": candidate.get("position_state_as_of"),
            "last_execution_date": candidate.get("last_execution_date"),
        },
        "new_temporal_metadata": {
            "valuation_as_of": candidate.get("valuation_as_of"),
            "source_market_date": candidate.get("source_market_date"),
        },
        "position_level_valuation": candidate.get("positions") or [],
        "source_quote_evidence": {
            "market_date": market.get("market_date"),
            "market_status": market.get("market_status"),
            "quote_status": market.get("quote_status"),
        },
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    path = root / "persistent_ledger" / "history" / "valuation" / (valuation_as_of or "unknown") / f"{digest}.json"
    if not path.exists():
        _write_json(path, payload)
    return path


def _atomic_write_current(*, root: Path, source_path: Path, payload: dict[str, Any], now: datetime | None) -> Path:
    timestamp = _iso(now).replace(":", "").replace("+", "")
    backup_path = root / "persistent_ledger" / "history" / "current" / f"{timestamp}.json"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path.exists():
        shutil.copy2(source_path, backup_path)
    temp_path = source_path.with_suffix(".json.tmp")
    write_current_temporal_state(temp_path, payload)
    os.replace(temp_path, source_path)
    _read_json(source_path)
    return backup_path


def _normalize_position(position: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(position)
    if "average_price" not in normalized and "avg_price" in normalized:
        normalized["average_price"] = normalized["avg_price"]
    return normalized


def _is_broker_only_position(position: dict[str, Any]) -> bool:
    return bool(position.get("broker_only")) or str(position.get("ownership") or "").lower() == "broker_only"


def _symbol(position: dict[str, Any]) -> str:
    return _normalize_symbol(str(position.get("symbol") or position.get("issue_code") or ""))


def _quote_for_symbol(quotes: dict[str, Any], symbol: str) -> dict[str, Any]:
    return dict(quotes.get(symbol) or quotes.get(symbol + "0") or {})


def _normalize_symbol(value: str) -> str:
    text = value.strip()
    if text.endswith(".T"):
        text = text[:-2]
    return text


def _price(quote: dict[str, Any]) -> float | None:
    try:
        return float(quote.get("price"))
    except (TypeError, ValueError):
        return None


def _resolve_economic_valuation_price(quote: dict[str, Any]) -> tuple[float | None, str, str]:
    price = _price(quote)
    if not bool(quote.get("adjusted")):
        return price, "PASS", "quote_price_is_economic_unadjusted"
    reconciliation_status = str(quote.get("economic_price_reconciliation_status") or "")
    provenance = str(quote.get("economic_price_provenance") or "")
    economic_price = _positive_float(quote.get("economic_valuation_price"))
    if reconciliation_status == "PASS" and provenance and economic_price is not None:
        return economic_price, "PASS", "adjusted_price_reconciled_to_economic_valuation_price"
    return None, "REVIEW_REQUIRED", "adjusted_price_missing_economic_valuation_reconciliation"


def _resolve_basis_compatible_valuation_price(
    *,
    position: dict[str, Any],
    quote: dict[str, Any],
) -> tuple[float | None, str, str, str]:
    if not bool(quote.get("adjusted")):
        price, authority, reason = _resolve_economic_valuation_price(quote)
        return price, authority, reason, "RAW"
    if str(quote.get("price_basis") or "").upper() == "RECONCILED":
        price, authority, reason = _resolve_economic_valuation_price(quote)
        return price, authority, reason, "RECONCILED"
    basis, basis_reason = _resolve_position_quantity_basis(position=position, quote=quote)
    if basis == "ADJUSTED":
        adjusted_price = _positive_float(
            quote.get("adjusted_basis_valuation_price", quote.get("adjusted_analytical_price"))
        )
        provenance = str(quote.get("adjusted_basis_price_provenance") or "")
        status = str(quote.get("adjusted_basis_reconciliation_status") or "")
        if adjusted_price is not None and provenance and status == "PASS":
            return (
                adjusted_price,
                "PASS",
                "valuation_price_basis_matches_adjusted_quantity_basis",
                "ADJUSTED",
            )
        return None, "REVIEW_REQUIRED", "adjusted_quantity_basis_price_reconciliation_missing", "ADJUSTED"
    if basis == "RAW":
        price, authority, reason = _resolve_economic_valuation_price(quote)
        return price, authority, reason, "RAW"
    return None, "REVIEW_REQUIRED", basis_reason or "position_quantity_basis_unresolved", "UNKNOWN"


def _resolve_position_quantity_basis(*, position: dict[str, Any], quote: dict[str, Any]) -> tuple[str, str]:
    explicit = str(position.get("quantity_basis") or position.get("position_quantity_basis") or "").upper()
    if explicit in {"RAW", "ADJUSTED", "RECONCILED"}:
        return ("RAW" if explicit == "RECONCILED" else explicit), "explicit_position_quantity_basis"
    ratio = _positive_float(quote.get("raw_adjusted_close_ratio"))
    if ratio is not None and abs(ratio - 1.0) <= 0.000001:
        return "ADJUSTED", "raw_adjusted_basis_equivalent"
    quantity = _positive_float(position.get("quantity"))
    observed_prices = [
        _positive_float(position.get("average_price") or position.get("avg_price")),
        _positive_float(position.get("current_price")),
    ]
    if quantity is not None and quantity > 0:
        observed_prices.append(_positive_float((_positive_float(position.get("market_value")) or 0.0) / quantity))
    adjusted_candidates = _quote_basis_candidates(
        quote,
        (
            "adjusted_basis_valuation_price",
            "adjusted_analytical_price",
            "adjusted_analytical_open",
            "adjusted_analytical_high",
            "adjusted_analytical_low",
        ),
    )
    raw_candidates = _quote_basis_candidates(
        quote,
        (
            "economic_valuation_price",
            "raw_economic_open",
            "raw_economic_high",
            "raw_economic_low",
        ),
    )
    adjusted_match = _any_price_match(observed_prices, adjusted_candidates)
    raw_match = _any_price_match(observed_prices, raw_candidates)
    if adjusted_match and not raw_match:
        return "ADJUSTED", "position_unit_price_matches_adjusted_quote_basis"
    if raw_match and not adjusted_match:
        return "RAW", "position_unit_price_matches_raw_quote_basis"
    if adjusted_match and raw_match:
        return "UNKNOWN", "position_quantity_basis_ambiguous"
    return "UNKNOWN", "position_quantity_basis_unresolved"


def _quote_basis_candidates(quote: dict[str, Any], keys: tuple[str, ...]) -> list[float]:
    values: list[float] = []
    for key in keys:
        value = _positive_float(quote.get(key))
        if value is not None:
            values.append(value)
    return values


def _any_price_match(observed: list[float | None], candidates: list[float]) -> bool:
    return any(
        value is not None and _price_close(value, candidate)
        for value in observed
        for candidate in candidates
    )


def _price_close(left: float, right: float) -> bool:
    tolerance = max(0.01, abs(right) * 0.0001)
    return abs(left - right) <= tolerance


def _valuation_price_role_for_basis(*, quote: dict[str, Any], price_basis: str) -> str:
    if price_basis == "ADJUSTED":
        return str(quote.get("adjusted_basis_price_role") or "reconciled_adjusted_basis_valuation_price")
    return str(quote.get("price_role") or "economic_valuation_price")


def _valuation_price_provenance_for_basis(*, quote: dict[str, Any], price_basis: str) -> str:
    if price_basis == "ADJUSTED":
        return str(quote.get("adjusted_basis_price_provenance") or "")
    return str(quote.get("economic_price_provenance") or "")


def _positive_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _normalized_quote_price_metadata(
    *,
    adjusted: bool,
    price_source: str,
    source_column: str,
    row: dict[str, Any],
    economic_row: dict[str, Any] | None = None,
    economic_source_path: Path | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "normalized_price_source": price_source or ("adjusted" if adjusted else "unadjusted"),
        "price_source_column": source_column,
    }
    normalized_price = row.get(source_column)
    if not adjusted:
        metadata.update(
            {
                "price_role": "economic_valuation_price",
                "economic_price_reconciliation_status": "PASS",
                "economic_price_provenance": "normalized_ohlcv_unadjusted_close",
                "economic_valuation_price": normalized_price,
                "price_basis": "RAW",
                "adjusted_basis_reconciliation_status": "NOT_REQUIRED",
            }
        )
        return metadata
    explicit_status = str(
        row.get("economic_price_reconciliation_status") or row.get("EconomicPriceReconciliationStatus") or ""
    )
    explicit_price = row.get("economic_valuation_price", row.get("EconomicValuationPrice"))
    explicit_provenance = str(row.get("economic_price_provenance") or row.get("EconomicPriceProvenance") or "")
    if explicit_status == "PASS" and explicit_provenance and _positive_float(explicit_price) is not None:
        metadata.update(
            {
                "price_role": "reconciled_adjusted_economic_valuation_price",
                "economic_price_reconciliation_status": "PASS",
                "economic_price_provenance": explicit_provenance,
                "economic_valuation_price": float(explicit_price),
                "price_basis": "RECONCILED",
            }
        )
        return metadata
    raw_close_column = _first_mapping_key(economic_row or {}, ("C", "Close", "close", "price"))
    raw_close = _positive_float((economic_row or {}).get(raw_close_column)) if raw_close_column else None
    raw_open = _positive_float((economic_row or {}).get("O"))
    raw_high = _positive_float((economic_row or {}).get("H"))
    raw_low = _positive_float((economic_row or {}).get("L"))
    raw_adjusted_close = _positive_float((economic_row or {}).get("AdjC"))
    raw_adjusted_open = _positive_float((economic_row or {}).get("AdjO"))
    raw_adjusted_high = _positive_float((economic_row or {}).get("AdjH"))
    raw_adjusted_low = _positive_float((economic_row or {}).get("AdjL"))
    if raw_close is not None and economic_source_path and economic_source_path.is_file():
        adjusted_basis_price = _positive_float(normalized_price) or raw_adjusted_close
        adjusted_provenance = (
            f"normalized_adjusted_ohlcv_close:{source_column}|raw_ohlcv_adjusted_close:{economic_source_path}:AdjC"
            if adjusted_basis_price is not None
            else ""
        )
        metadata.update(
            {
                "price_role": "reconciled_raw_economic_valuation_price",
                "economic_price_reconciliation_status": "PASS",
                "economic_price_provenance": f"raw_ohlcv_close:{economic_source_path}:{raw_close_column}",
                "economic_valuation_price": raw_close,
                "price_basis": "RAW",
                "raw_economic_open": raw_open,
                "raw_economic_high": raw_high,
                "raw_economic_low": raw_low,
                "raw_adjusted_open": raw_adjusted_open,
                "raw_adjusted_high": raw_adjusted_high,
                "raw_adjusted_low": raw_adjusted_low,
                "raw_adjusted_close": raw_adjusted_close,
                "raw_adjusted_close_ratio": raw_close / adjusted_basis_price if adjusted_basis_price else None,
                "adjusted_analytical_open": row.get("Open", raw_adjusted_open),
                "adjusted_analytical_high": row.get("High", raw_adjusted_high),
                "adjusted_analytical_low": row.get("Low", raw_adjusted_low),
                "adjusted_analytical_price": normalized_price,
                "adjusted_basis_valuation_price": adjusted_basis_price,
                "adjusted_basis_reconciliation_status": "PASS" if adjusted_basis_price is not None and adjusted_provenance else "REVIEW_REQUIRED",
                "adjusted_basis_price_role": "reconciled_adjusted_basis_valuation_price",
                "adjusted_basis_price_provenance": adjusted_provenance,
            }
        )
        return metadata
    metadata.update(
        {
            "price_role": "adjusted_analytical_price",
            "economic_price_reconciliation_status": "REVIEW_REQUIRED",
            "economic_price_provenance": "",
        }
    )
    return metadata


def _first_mapping_key(row: dict[str, Any], candidates: tuple[str, ...]) -> str:
    exact = {str(key): str(key) for key in row}
    lower = {str(key).lower(): str(key) for key in row}
    for candidate in candidates:
        if candidate in exact:
            return exact[candidate]
        match = lower.get(candidate.lower())
        if match:
            return match
    return ""


def _sum_market_value(positions: list[dict[str, Any]]) -> float:
    return sum(float(position.get("market_value") or 0) for position in positions)


def _sum_unrealized(positions: list[dict[str, Any]]) -> float:
    return sum(float(position.get("unrealized_pnl") or 0) for position in positions)


def _valued_position_count(candidate_current: dict[str, Any]) -> int:
    count = 0
    for position in candidate_current.get("positions") or []:
        if (
            str(position.get("valuation_as_of") or "")
            and str(position.get("source_market_date") or "")
            and str(position.get("valuation_source") or "")
            and position.get("market_value") is not None
        ):
            count += 1
    return count


def _authority_review_reasons(
    *,
    business_date: str,
    candidate_current: dict[str, Any],
    market_evidence_path: str,
    market_date: str,
    safety_authority: dict[str, Any] | None,
    runtime_test_context: dict[str, Any] | None,
    environment_context: dict[str, Any] | None,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if candidate_current.get("positions") and not market_evidence_path:
        reasons.append("current_valuation_market_evidence_path_missing")
    if candidate_current.get("positions") and not market_date:
        reasons.append("current_valuation_market_date_missing")
    if market_date and market_date != business_date and str(candidate_current.get("current_valuation_status") or "") == "READY":
        reasons.append("current_valuation_market_date_mismatch")
    if runtime_test_context:
        reasons.extend(
            _historical_runtime_context_reasons(
                business_date=business_date,
                runtime_test_context=runtime_test_context,
                environment_context=environment_context or {},
                safety_authority=safety_authority or {},
            )
        )
    return tuple(sorted(set(reasons)))


def _historical_runtime_context_reasons(
    *,
    business_date: str,
    runtime_test_context: dict[str, Any],
    environment_context: dict[str, Any],
    safety_authority: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if str(runtime_test_context.get("business_date") or "") != business_date:
        reasons.append("runtime_test_business_date_mismatch")
    run_id = str(runtime_test_context.get("run_id") or "")
    evidence_root = str(runtime_test_context.get("evidence_root") or "")
    if not run_id or not evidence_root or run_id not in evidence_root:
        reasons.append("runtime_test_evidence_identity_missing")
    if not bool(environment_context.get("historical_replay")):
        reasons.append("historical_replay_capability_missing")
    if bool(environment_context.get("broker_write")):
        reasons.append("historical_broker_write_not_blocked")
    if bool(environment_context.get("external_delivery")):
        reasons.append("historical_external_delivery_not_blocked")
    if str(safety_authority.get("safety_status") or "") != "PASS":
        reasons.append("historical_safety_authority_missing")
    if str(safety_authority.get("safety_policy_version") or "") != "historical_replay_neutral_safety_v1":
        reasons.append("historical_safety_policy_version_missing")
    if str(safety_authority.get("safety_source") or "") != "data_readiness_historical_temporal_authority":
        reasons.append("historical_safety_source_missing")
    permissions = dict(safety_authority.get("safety_action_permissions") or {})
    if str(permissions.get("broker_write") or "") != "BLOCKED":
        reasons.append("historical_safety_broker_write_not_blocked")
    return reasons


def _missing_symbols_from_reasons(reasons: tuple[str, ...]) -> tuple[str, ...]:
    symbols = [
        reason
        for reason in reasons
        if reason
        and not reason.startswith("current_valuation_")
        and not reason.startswith("historical_")
        and not reason.startswith("runtime_test_")
        and reason
        not in {
            "market_status_not_allowed",
            "quote_status_not_allowed",
            "current_temporal_schema_required",
            "current_valuation_market_date_mismatch",
        }
        and ":" not in reason
    ]
    return tuple(sorted(set(symbols)))


def _post_apply_validation(*, source_path: Path, business_date: str) -> tuple[str, ...]:
    try:
        current = _read_json(source_path)
    except ValueError:
        return ("post_apply_current_missing",)
    reasons: list[str] = []
    if str(current.get("business_date") or "") != business_date:
        reasons.append("post_apply_business_date_mismatch")
    if str(current.get("valuation_as_of") or "") != business_date:
        reasons.append("post_apply_valuation_as_of_mismatch")
    if str(current.get("source_market_date") or "") != business_date:
        reasons.append("post_apply_source_market_date_mismatch")
    positions = list(current.get("positions") or [])
    for position in positions:
        symbol = str(position.get("symbol") or position.get("code") or "")
        if str(position.get("valuation_as_of") or "") != business_date:
            reasons.append(f"post_apply_position_valuation_as_of_mismatch:{symbol}")
        if str(position.get("source_market_date") or "") != business_date:
            reasons.append(f"post_apply_position_source_market_date_mismatch:{symbol}")
        if position.get("current_price") in (None, "") or float(position.get("current_price") or 0) <= 0:
            reasons.append(f"post_apply_position_price_missing:{symbol}")
        quantity = float(position.get("quantity") or 0)
        price = float(position.get("current_price") or 0)
        market_value = float(position.get("market_value") or 0)
        if abs(market_value - quantity * price) > 0.0001:
            reasons.append(f"post_apply_position_market_value_mismatch:{symbol}")
    market_value_total = sum(float(position.get("market_value") or 0) for position in positions)
    if abs(float(current.get("market_value") or 0) - market_value_total) > 0.0001:
        reasons.append("post_apply_total_market_value_mismatch")
    total_equity = float(current.get("total_equity") or 0)
    expected_total_equity = float(current.get("cash") or 0) + float(current.get("market_value") or 0)
    if abs(total_equity - expected_total_equity) > 0.0001:
        reasons.append("post_apply_total_equity_mismatch")
    return tuple(sorted(set(reasons)))


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"{path} missing") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} invalid json: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must be a JSON object")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _iso(value: datetime | None) -> str:
    return (value or datetime.now(timezone.utc)).isoformat()
