"""Runtime regular-path adapter for Position Management AI.

The adapter does not alter Position Management AI scoring or thresholds.  It
prepares Runtime-owned Current positions as AI input, calls the existing
Position Management inference entrypoint, and normalizes the output into the
Runtime decision artifact consumed by SELL Planning.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.position_management_ai.inference import (
    FEATURE_VERSION,
    MODEL_VERSION,
    run_position_management_inference,
)
from ai_fund_lab_v2.runtime_v2.artifact_lookup import (
    RuntimeArtifactLookupHalt,
    resolve_position_management_policy_artifacts,
)
from ai_fund_lab_v2.runtime_v2.planning.sell_pipeline import SellExitDecision


ARTIFACT_SCHEMA_VERSION = "runtime_v2_position_management_decision_v1"
INFERENCE_VERSION = "position_management_ai_phase6a_regular_path_v1"
PM_INPUT_SCHEMA_VERSION = "runtime_v2_pm_input_v1"
CURRENT_REQUIRED_FIELDS = ("symbol", "quantity", "as_of", "source", "average_price")
PM_FEATURE_REQUIRED_COLUMNS = ("target_date", "code")
OPPORTUNITY_REQUIRED_COLUMNS = (
    "target_date",
    "code",
    "expected_edge_score",
    "buy_rank",
    "downside_risk_score",
)


@dataclass(frozen=True)
class PositionManagementRuntimeResult:
    status: str
    reason: str
    business_date: str
    runtime_id: str
    model_version: str
    inference_version: str
    feature_date: str
    holding_input_path: str
    inference_output_path: str
    action_csv_path: str
    summary_path: str
    audit_path: str
    artifact_path: str
    decision_count: int
    exit_count: int
    hold_count: int
    reduce_count: int
    add_count: int
    generated_at: str
    sell_exit_decisions: tuple[SellExitDecision, ...]
    input_contract: dict[str, Any]

    def to_manifest_fields(self) -> dict[str, Any]:
        return {
            "pm_status": self.status,
            "pm_reason": self.reason,
            "pm_model_version": self.model_version,
            "pm_inference_version": self.inference_version,
            "pm_feature_date": self.feature_date,
            "pm_artifact_path": self.artifact_path,
            "pm_decision_count": self.decision_count,
            "pm_exit_count": self.exit_count,
            "pm_hold_count": self.hold_count,
            "pm_reduce_count": self.reduce_count,
            "pm_add_count": self.add_count,
            "pm_generated_at": self.generated_at,
            "pm_input_schema_status": self.input_contract.get("pm_input_schema_status") or "",
            "pm_current_source": self.input_contract.get("pm_current_source") or "",
            "pm_current_as_of": self.input_contract.get("pm_current_as_of") or "",
            "pm_current_freshness": self.input_contract.get("pm_current_freshness") or "",
            "pm_feature_source": self.input_contract.get("pm_feature_source") or "",
            "pm_feature_row_count": self.input_contract.get("pm_feature_row_count"),
            "pm_opportunity_source": self.input_contract.get("pm_opportunity_source") or "",
            "pm_opportunity_status": self.input_contract.get("pm_opportunity_status") or "",
            "pm_missing_fields": self.input_contract.get("pm_missing_fields") or [],
            "pm_missing_symbols": self.input_contract.get("pm_missing_symbols") or [],
            "pm_derived_fields": self.input_contract.get("pm_derived_fields") or [],
            "pm_defaulted_fields": self.input_contract.get("pm_defaulted_fields") or [],
            "pm_review_required": bool(self.input_contract.get("pm_review_required")),
            "pm_review_reason": self.input_contract.get("pm_review_reason") or "",
        }


def produce_position_management_decisions(
    *,
    runtime_root: Path | str,
    business_date: str,
    mode: str,
    feature_date: str | None = None,
    opportunity_path: Path | str | None = None,
    feature_path: Path | str | None = None,
    now: datetime | None = None,
) -> PositionManagementRuntimeResult:
    root = Path(runtime_root)
    if mode not in {"demo", "production"}:
        raise ValueError("Position Management Runtime producer supports demo/production only")
    _reject_mode_rooted_runtime_root(root)
    generated_at = _iso(now or datetime.now(timezone.utc))
    runtime_id = f"runtime-v2-position-management-{business_date}-{generated_at.replace(':', '').replace('-', '')}"
    resolved_feature_date = feature_date or business_date
    artifact_dir = root / "runtime_state" / "position_management" / business_date
    artifact_dir.mkdir(parents=True, exist_ok=True)
    holding_path = artifact_dir / "current_holdings_snapshot.csv"
    artifact_path = artifact_dir / "position_management_decisions.json"
    try:
        pm_artifacts = resolve_position_management_policy_artifacts()
        pm_artifacts.require_member("RUNTIME_ADAPTER")
    except RuntimeArtifactLookupHalt as exc:
        payload = _artifact_payload(
            business_date=business_date,
            runtime_id=runtime_id,
            mode=mode,
            feature_date=resolved_feature_date,
            generated_at=generated_at,
            holding_path=holding_path,
            opportunity_path=Path(opportunity_path) if opportunity_path else Path(""),
            feature_path=Path(feature_path) if feature_path else Path(""),
            inference_output_path=artifact_dir / "position_management_inference.parquet",
            action_csv_path=artifact_dir / "position_management_actions.csv",
            summary_path=artifact_dir / "position_management_inference_summary.json",
            audit_path=artifact_dir / "position_management_inference_audit.json",
            status="HALT",
            reason=str(exc),
            decisions=(),
            input_contract={"pm_input_schema_status": "HALT", "pm_review_reason": str(exc)},
        )
        _write_json(artifact_path, payload)
        return _result_from_payload(payload, artifact_path=artifact_path, sell_exit_decisions=())
    current_path = root / "persistent_ledger" / "state.json"
    current = _read_json(current_path)
    contract = _validate_pm_input_contract(
        current=current,
        current_path=current_path,
        business_date=business_date,
        feature_date=resolved_feature_date,
        opportunity_path=Path(opportunity_path) if opportunity_path else Path(""),
        feature_path=Path(feature_path) if feature_path else Path(""),
    )
    if contract["pm_input_schema_status"] == "REVIEW_REQUIRED":
        payload = _artifact_payload(
            business_date=business_date,
            runtime_id=runtime_id,
            mode=mode,
            feature_date=resolved_feature_date,
            generated_at=generated_at,
            holding_path=holding_path,
            opportunity_path=Path(opportunity_path) if opportunity_path else Path(""),
            feature_path=Path(feature_path) if feature_path else Path(""),
            inference_output_path=artifact_dir / "position_management_inference.parquet",
            action_csv_path=artifact_dir / "position_management_actions.csv",
            summary_path=artifact_dir / "position_management_inference_summary.json",
            audit_path=artifact_dir / "position_management_inference_audit.json",
            status="REVIEW_REQUIRED",
            reason=str(contract.get("pm_review_reason") or "pm_input_contract_review_required"),
            decisions=(),
            input_contract=contract,
        )
        pd.DataFrame(columns=HOLDING_COLUMNS_FOR_OUTPUT).to_csv(holding_path, index=False)
        _write_json(artifact_path, payload)
        return _result_from_payload(payload, artifact_path=artifact_path, sell_exit_decisions=())
    holding = _holding_frame_from_current(current=current, business_date=business_date, contract=contract)
    holding.to_csv(holding_path, index=False)

    if holding.empty:
        payload = _artifact_payload(
            business_date=business_date,
            runtime_id=runtime_id,
            mode=mode,
            feature_date=resolved_feature_date,
            generated_at=generated_at,
            holding_path=holding_path,
            opportunity_path=Path(opportunity_path) if opportunity_path else Path(""),
            feature_path=Path(feature_path) if feature_path else Path(""),
            inference_output_path=artifact_dir / "position_management_inference.parquet",
            action_csv_path=artifact_dir / "position_management_actions.csv",
            summary_path=artifact_dir / "position_management_inference_summary.json",
            audit_path=artifact_dir / "position_management_inference_audit.json",
            status="NO_POSITION",
            reason="current_position_missing",
            decisions=(),
            input_contract=contract,
        )
        _write_json(artifact_path, payload)
        return _result_from_payload(payload, artifact_path=artifact_path, sell_exit_decisions=())

    if opportunity_path is None or feature_path is None:
        payload = _artifact_payload(
            business_date=business_date,
            runtime_id=runtime_id,
            mode=mode,
            feature_date=resolved_feature_date,
            generated_at=generated_at,
            holding_path=holding_path,
            opportunity_path=Path(opportunity_path) if opportunity_path else Path(""),
            feature_path=Path(feature_path) if feature_path else Path(""),
            inference_output_path=artifact_dir / "position_management_inference.parquet",
            action_csv_path=artifact_dir / "position_management_actions.csv",
            summary_path=artifact_dir / "position_management_inference_summary.json",
            audit_path=artifact_dir / "position_management_inference_audit.json",
            status="REVIEW_REQUIRED",
            reason="position management opportunity/feature artifacts are required",
            decisions=(),
            input_contract=contract,
        )
        _write_json(artifact_path, payload)
        return _result_from_payload(payload, artifact_path=artifact_path, sell_exit_decisions=())

    inference = run_position_management_inference(
        holding_path=holding_path,
        opportunity_path=Path(opportunity_path),
        feature_path=Path(feature_path),
        output_dir=artifact_dir,
        created_at=generated_at,
        inference_run_id=runtime_id,
    )
    output = inference.output
    decisions = tuple(_decision_payload(row, current=current, generated_at=generated_at) for row in output.to_dict("records"))
    status = "PASS" if str(inference.summary.get("status") or "") == "OK" else "REVIEW_REQUIRED"
    reason = "" if status == "PASS" else str(inference.summary.get("readiness_status") or "position_management_inference_not_ready")
    payload = _artifact_payload(
        business_date=business_date,
        runtime_id=runtime_id,
        mode=mode,
        feature_date=resolved_feature_date,
        generated_at=generated_at,
        holding_path=holding_path,
        opportunity_path=Path(opportunity_path),
        feature_path=Path(feature_path),
        inference_output_path=artifact_dir / "position_management_inference.parquet",
        action_csv_path=artifact_dir / "position_management_actions.csv",
        summary_path=artifact_dir / "position_management_inference_summary.json",
        audit_path=artifact_dir / "position_management_inference_audit.json",
        status=status,
        reason=reason,
        decisions=decisions,
        input_contract=contract,
    )
    _write_json(artifact_path, payload)
    return _result_from_payload(
        payload,
        artifact_path=artifact_path,
        sell_exit_decisions=_sell_exit_decisions_from_artifact(payload),
    )


def load_sell_exit_decisions_from_pm_artifact(path: Path | str) -> tuple[SellExitDecision, ...]:
    payload = _read_json(Path(path))
    if payload.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
        raise ValueError("Position Management artifact schema mismatch")
    return _sell_exit_decisions_from_artifact(payload)


def validate_position_management_input_contract(
    *,
    current: dict[str, Any],
    current_path: Path | str,
    business_date: str,
    feature_date: str,
    opportunity_path: Path | str | None,
    feature_path: Path | str | None,
) -> dict[str, Any]:
    """Read-only PM input contract validation for Runtime Data Readiness.

    This is the same contract used by the PM producer before inference.  It
    intentionally does not derive AI decisions or write PM artifacts.
    """

    return _validate_pm_input_contract(
        current=current,
        current_path=Path(current_path),
        business_date=business_date,
        feature_date=feature_date,
        opportunity_path=Path(opportunity_path) if opportunity_path else Path(""),
        feature_path=Path(feature_path) if feature_path else Path(""),
    )


def _sell_exit_decisions_from_artifact(payload: dict[str, Any]) -> tuple[SellExitDecision, ...]:
    decisions: list[SellExitDecision] = []
    for item in payload.get("decisions") or ():
        if str(item.get("decision") or "").upper() != "EXIT":
            continue
        quantity = float(item.get("runtime_sell_quantity") or 0)
        if quantity <= 0:
            continue
        decisions.append(
            SellExitDecision(
                symbol=str(item.get("symbol") or ""),
                quantity=quantity,
                reason=str(item.get("reason") or "position_management_exit"),
                score=float(item.get("confidence") or 0.0),
            )
        )
    return tuple(decisions)


HOLDING_COLUMNS_FOR_OUTPUT = (
    "target_date",
    "code",
    "entry_price",
    "current_price",
    "holding_days",
    "position_size",
    "current_return",
    "peak_return",
)


def _holding_frame_from_current(
    *,
    current: dict[str, Any],
    business_date: str,
    contract: dict[str, Any],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    derived_fields = list(contract.get("pm_derived_fields") or [])
    position_context = dict(contract.get("pm_position_context") or {})
    for position in current.get("positions") or ():
        symbol = str(position.get("symbol") or position.get("issue_code") or "").strip()
        context = dict(position_context.get(symbol) or {})
        quantity = float(position.get("quantity") or 0)
        if not symbol or quantity <= 0:
            continue
        average_price = float(position.get("average_price") or 0)
        market_value = float(position.get("market_value") or 0)
        current_price = float(position.get("current_price") or position.get("price") or 0)
        if current_price <= 0 and market_value > 0:
            current_price = market_value / quantity
            derived_fields.append(f"{symbol}.current_price:market_value/quantity")
        holding_days = int(position.get("holding_days") if position.get("holding_days") not in (None, "") else context.get("holding_days"))
        peak_return = float(position.get("peak_return") if position.get("peak_return") not in (None, "") else context.get("peak_return"))
        current_return = _safe_return(current_price, average_price)
        if "unrealized_pnl" not in position:
            derived_fields.append(f"{symbol}.unrealized_pnl:(current_price-entry_price)*quantity")
        rows.append(
            {
                "target_date": business_date,
                "code": symbol,
                "entry_price": average_price,
                "current_price": current_price,
                "holding_days": holding_days,
                "position_size": quantity,
                "current_return": current_return,
                "peak_return": peak_return,
            }
        )
    contract["pm_derived_fields"] = sorted(set(derived_fields))
    return pd.DataFrame(rows)


def _decision_payload(row: dict[str, Any], *, current: dict[str, Any], generated_at: str) -> dict[str, Any]:
    symbol = str(row.get("code") or "")
    decision = str(row.get("action") or "HOLD").upper()
    position_quantity = _current_quantity(current, symbol)
    confidence = _confidence(row, decision)
    reason = str(row.get("exit_reason") or row.get("action_reason") or decision)
    runtime_sell_quantity = position_quantity if decision == "EXIT" else 0.0
    runtime_action = "SELL_FULL_POSITION" if decision == "EXIT" else "NO_SELL_ORDER"
    if decision == "REDUCE":
        runtime_action = "REVIEW_REQUIRED_REDUCE_QUANTITY_CONTRACT_MISSING"
        reason = reason + "; reduce quantity contract is not defined in Runtime v2"
    if decision == "ADD":
        runtime_action = "NO_SELL_ORDER_ADD_OUT_OF_SELL_SCOPE"
        reason = reason + "; ADD is outside SELL Planning scope"
    return {
        "business_date": str(row.get("target_date") or ""),
        "symbol": symbol,
        "decision": decision,
        "reason": reason,
        "confidence": confidence,
        "hold_score": _float(row.get("hold_score")),
        "exit_score": _float(row.get("exit_score")),
        "add_score": _float(row.get("add_score")),
        "reduce_score": _float(row.get("reduce_score")),
        "continue_holding": bool(row.get("continue_holding")),
        "exit_candidate": bool(row.get("exit_candidate")),
        "reduce_candidate": bool(row.get("reduce_candidate")),
        "add_candidate": bool(row.get("add_candidate")),
        "model_version": str(row.get("model_version") or MODEL_VERSION),
        "feature_version": str(row.get("feature_version") or FEATURE_VERSION),
        "generated_at": generated_at,
        "runtime_position_quantity": position_quantity,
        "runtime_sell_quantity": runtime_sell_quantity,
        "runtime_action": runtime_action,
    }


def _artifact_payload(
    *,
    business_date: str,
    runtime_id: str,
    mode: str,
    feature_date: str,
    generated_at: str,
    holding_path: Path,
    opportunity_path: Path,
    feature_path: Path,
    inference_output_path: Path,
    action_csv_path: Path,
    summary_path: Path,
    audit_path: Path,
    status: str,
    reason: str,
    decisions: tuple[dict[str, Any], ...],
    input_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    counts = _counts(decisions)
    contract = dict(input_contract or {})
    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "business_date": business_date,
        "runtime_id": runtime_id,
        "environment": mode,
        "model_version": MODEL_VERSION,
        "inference_version": INFERENCE_VERSION,
        "feature_date": feature_date,
        "generated_at": generated_at,
        "status": status,
        "reason": reason,
        "review_required": status == "REVIEW_REQUIRED",
        "review_reason": reason if status == "REVIEW_REQUIRED" else "",
        "holding_input_path": str(holding_path),
        "current_source": str(contract.get("pm_current_source") or ""),
        "current_as_of": str(contract.get("pm_current_as_of") or ""),
        "pm_feature_source": str(feature_path),
        "pm_feature_row_count": contract.get("pm_feature_row_count"),
        "opportunity_source": str(opportunity_path),
        "missing_fields": list(contract.get("pm_missing_fields") or []),
        "missing_symbols": list(contract.get("pm_missing_symbols") or []),
        "stale_artifacts": list(contract.get("pm_stale_artifacts") or []),
        "derived_fields": list(contract.get("pm_derived_fields") or []),
        "defaulted_fields": list(contract.get("pm_defaulted_fields") or []),
        "input_contract": contract,
        "opportunity_path": str(opportunity_path),
        "feature_path": str(feature_path),
        "inference_output_path": str(inference_output_path),
        "action_csv_path": str(action_csv_path),
        "summary_path": str(summary_path),
        "audit_path": str(audit_path),
        "decision_count": len(decisions),
        "exit_count": counts["EXIT"],
        "hold_count": counts["HOLD"],
        "reduce_count": counts["REDUCE"],
        "add_count": counts["ADD"],
        "add_auto_sell_used": False,
        "add_scope_reason": "ADD is a Position Management AI decision but is outside SELL Planning auto-order scope.",
        "current_liquidation_contract": "Runtime cleanup/emergency liquidation is separate from Position Management AI decisions.",
        "decisions": list(decisions),
    }


def _result_from_payload(
    payload: dict[str, Any],
    *,
    artifact_path: Path,
    sell_exit_decisions: tuple[SellExitDecision, ...],
) -> PositionManagementRuntimeResult:
    return PositionManagementRuntimeResult(
        status=str(payload["status"]),
        reason=str(payload.get("reason") or ""),
        business_date=str(payload["business_date"]),
        runtime_id=str(payload["runtime_id"]),
        model_version=str(payload["model_version"]),
        inference_version=str(payload["inference_version"]),
        feature_date=str(payload["feature_date"]),
        holding_input_path=str(payload["holding_input_path"]),
        inference_output_path=str(payload["inference_output_path"]),
        action_csv_path=str(payload["action_csv_path"]),
        summary_path=str(payload["summary_path"]),
        audit_path=str(payload["audit_path"]),
        artifact_path=str(artifact_path),
        decision_count=int(payload["decision_count"]),
        exit_count=int(payload["exit_count"]),
        hold_count=int(payload["hold_count"]),
        reduce_count=int(payload["reduce_count"]),
        add_count=int(payload["add_count"]),
        generated_at=str(payload["generated_at"]),
        sell_exit_decisions=sell_exit_decisions,
        input_contract=dict(payload.get("input_contract") or {}),
    )


def _validate_pm_input_contract(
    *,
    current: dict[str, Any],
    current_path: Path,
    business_date: str,
    feature_date: str,
    opportunity_path: Path,
    feature_path: Path,
) -> dict[str, Any]:
    positions = [item for item in current.get("positions") or () if float(item.get("quantity") or 0) > 0]
    held_symbols = tuple(str(item.get("symbol") or item.get("issue_code") or "").strip() for item in positions)
    position_context = _pm_feature_position_context(feature_path=feature_path, feature_date=feature_date)
    missing_fields: list[str] = []
    missing_symbols: list[str] = []
    stale_artifacts: list[str] = []
    derived_fields: list[str] = []
    defaulted_fields: list[str] = []
    current_as_of = str(current.get("as_of") or "")
    current_updated_at = str(current.get("updated_at") or "")
    current_position_status = str(current.get("current_position_status") or "")
    current_valuation_status = str(current.get("current_valuation_status") or "")
    temporal_schema = bool(current.get("temporal_schema_version"))
    temporal_current_ready = (
        temporal_schema
        and current_position_status in {"READY", "VALID_CARRYOVER"}
        and current_valuation_status in {"READY", "VALID_CARRYOVER"}
    )
    if not temporal_current_ready and (current_as_of != business_date or not current_updated_at):
        stale_artifacts.append("current")
    for position in positions:
        symbol = str(position.get("symbol") or position.get("issue_code") or "").strip()
        for field in CURRENT_REQUIRED_FIELDS:
            if field not in position or position.get(field) in (None, ""):
                missing_fields.append(f"current.positions[{symbol}].{field}")
        if "current_price" not in position and "price" not in position:
            if position.get("market_value") and position.get("quantity"):
                derived_fields.append(f"{symbol}.current_price:market_value/quantity")
            else:
                missing_fields.append(f"current.positions[{symbol}].current_price")
        if "holding_days" not in position or position.get("holding_days") in (None, ""):
            if symbol in position_context and position_context[symbol].get("holding_days") not in (None, ""):
                derived_fields.append(f"{symbol}.holding_days:pm_feature")
            else:
                missing_fields.append(f"current.positions[{symbol}].holding_days")
        if "peak_return" not in position or position.get("peak_return") in (None, ""):
            if symbol in position_context and position_context[symbol].get("peak_return") not in (None, ""):
                derived_fields.append(f"{symbol}.peak_return:pm_feature")
            else:
                missing_fields.append(f"current.positions[{symbol}].peak_return")
    feature_status = _pm_feature_status(
        feature_path=feature_path,
        feature_date=feature_date,
        held_symbols=held_symbols,
        current_has_positions=bool(positions),
    )
    opportunity_status = _pm_opportunity_status(
        opportunity_path=opportunity_path,
        feature_date=feature_date,
        held_symbols=held_symbols,
        current_has_positions=bool(positions),
    )
    missing_fields.extend(feature_status["missing_fields"])
    missing_symbols.extend(feature_status["missing_symbols"])
    missing_fields.extend(opportunity_status["missing_fields"])
    missing_symbols.extend(opportunity_status["missing_symbols"])
    if feature_status["stale"]:
        stale_artifacts.append("pm_feature")
    if opportunity_status["stale"]:
        stale_artifacts.append("opportunity")
    review_required = bool(missing_fields or missing_symbols or stale_artifacts or feature_status["review_required"] or opportunity_status["review_required"])
    reason = _pm_review_reason(
        current_has_positions=bool(positions),
        missing_fields=missing_fields,
        missing_symbols=missing_symbols,
        stale_artifacts=stale_artifacts,
        feature_reason=feature_status["reason"],
        opportunity_reason=opportunity_status["reason"],
    )
    return {
        "schema_name": "runtime_v2_pm_input",
        "schema_version": PM_INPUT_SCHEMA_VERSION,
        "pm_input_schema_status": "REVIEW_REQUIRED" if review_required else "READY",
        "pm_current_source": str(current_path),
        "pm_current_as_of": current_as_of,
        "pm_position_state_as_of": str(current.get("position_state_as_of") or ""),
        "pm_valuation_as_of": str(current.get("valuation_as_of") or ""),
        "pm_current_position_status": current_position_status,
        "pm_current_valuation_status": current_valuation_status,
        "pm_current_freshness": "STALE" if "current" in stale_artifacts else "FRESH",
        "pm_feature_source": str(feature_path),
        "pm_feature_row_count": feature_status["row_count"],
        "pm_feature_date": feature_date,
        "pm_opportunity_source": str(opportunity_path),
        "pm_opportunity_status": opportunity_status["status"],
        "pm_missing_fields": sorted(set(missing_fields)),
        "pm_missing_symbols": sorted(set(symbol for symbol in missing_symbols if symbol)),
        "pm_stale_artifacts": sorted(set(stale_artifacts)),
        "pm_derived_fields": sorted(set(derived_fields)),
        "pm_defaulted_fields": defaulted_fields,
        "pm_position_context": position_context,
        "pm_review_required": review_required,
        "pm_review_reason": reason if review_required else "",
    }


def _pm_feature_status(
    *,
    feature_path: Path,
    feature_date: str,
    held_symbols: tuple[str, ...],
    current_has_positions: bool,
) -> dict[str, Any]:
    if not feature_path or not feature_path.is_file():
        return {
            "review_required": current_has_positions,
            "reason": "pm_feature_artifact_missing" if current_has_positions else "",
            "row_count": 0,
            "missing_fields": [] if not current_has_positions else ["pm_feature_source"],
            "missing_symbols": [],
            "stale": False,
        }
    frame = _read_table(feature_path)
    columns = set(str(column) for column in frame.columns)
    missing_fields = [f"pm_feature.{column}" for column in PM_FEATURE_REQUIRED_COLUMNS if column not in columns]
    if missing_fields:
        return {
            "review_required": True,
            "reason": "pm_feature_required_columns_missing",
            "row_count": len(frame),
            "missing_fields": missing_fields,
            "missing_symbols": [],
            "stale": False,
        }
    frame = frame.copy()
    frame["target_date"] = frame["target_date"].astype(str)
    frame["code"] = frame["code"].astype(str)
    date_rows = frame[frame["target_date"] == feature_date].copy()
    stale = bool(len(frame) and date_rows.empty)
    if not current_has_positions:
        has_no_position_reason = "no_position_reason" in columns
        return {
            "review_required": len(frame) == 0 and not has_no_position_reason,
            "reason": "pm_no_position_reason_missing" if len(frame) == 0 and not has_no_position_reason else "",
            "row_count": len(date_rows),
            "missing_fields": [] if has_no_position_reason else ["pm_feature.no_position_reason"],
            "missing_symbols": [],
            "stale": stale,
        }
    if date_rows.empty:
        return {
            "review_required": True,
            "reason": "pm_feature_rows_missing_for_current_positions",
            "row_count": 0,
            "missing_fields": [],
            "missing_symbols": list(held_symbols),
            "stale": stale,
        }
    covered = set(date_rows["code"].astype(str))
    missing_symbols = [symbol for symbol in held_symbols if symbol not in covered]
    return {
        "review_required": bool(missing_symbols),
        "reason": "pm_feature_rows_missing_for_current_positions" if missing_symbols else "",
        "row_count": len(date_rows),
        "missing_fields": [],
        "missing_symbols": missing_symbols,
        "stale": stale,
    }


def _pm_feature_position_context(*, feature_path: Path, feature_date: str) -> dict[str, dict[str, Any]]:
    if not feature_path or not feature_path.is_file():
        return {}
    try:
        frame = _read_table(feature_path)
    except Exception:
        return {}
    if "target_date" not in frame.columns or "code" not in frame.columns:
        return {}
    frame = frame.copy()
    frame["target_date"] = frame["target_date"].astype(str)
    frame["code"] = frame["code"].astype(str)
    rows = frame[frame["target_date"] == feature_date]
    context: dict[str, dict[str, Any]] = {}
    for row in rows.to_dict("records"):
        symbol = str(row.get("broker_issue_code") or row.get("code") or "").strip()
        if not symbol:
            continue
        peak_return = row.get("peak_return")
        if peak_return in (None, "") and row.get("unrealized_return") not in (None, ""):
            peak_return = max(_float(row.get("unrealized_return")), 0.0)
        context[symbol] = {
            "holding_days": row.get("holding_days"),
            "peak_return": peak_return,
        }
    return context


def _pm_opportunity_status(
    *,
    opportunity_path: Path,
    feature_date: str,
    held_symbols: tuple[str, ...],
    current_has_positions: bool,
) -> dict[str, Any]:
    if not current_has_positions:
        return {"review_required": False, "reason": "", "status": "NOT_REQUIRED", "missing_fields": [], "missing_symbols": [], "stale": False}
    if not opportunity_path or not opportunity_path.is_file():
        return {
            "review_required": True,
            "reason": "pm_opportunity_artifact_missing",
            "status": "MISSING",
            "missing_fields": ["pm_opportunity_source"],
            "missing_symbols": [],
            "stale": False,
        }
    if opportunity_path.suffix == ".json":
        payload = _read_json(opportunity_path)
        status = str(payload.get("status") or "")
        review_required = bool(payload.get("review_required")) or status in {"REVIEW_REQUIRED", "BLOCKED", "HALT"}
        rows = payload.get("rankings") or payload.get("rows") or []
        model_version_missing = not bool(payload.get("model_version"))
        generated_missing = not bool(payload.get("generated_at"))
        feature_date_value = str(payload.get("feature_date") or feature_date)
        missing_fields = []
        if model_version_missing:
            missing_fields.append("opportunity.model_version")
        if generated_missing:
            missing_fields.append("opportunity.generated_at")
        frame = pd.DataFrame(rows)
        reason = "pm_opportunity_review_required" if review_required else ""
    else:
        frame = _read_table(opportunity_path)
        status = "READY"
        review_required = False
        missing_fields = []
        feature_date_value = feature_date
        reason = ""
    columns = set(str(column) for column in frame.columns)
    missing_fields.extend(f"opportunity.{column}" for column in OPPORTUNITY_REQUIRED_COLUMNS if column not in columns)
    stale = feature_date_value != feature_date
    missing_symbols: list[str] = []
    if not frame.empty and {"target_date", "code"}.issubset(columns):
        filtered = frame[frame["target_date"].astype(str) == feature_date]
        covered = set(filtered["code"].astype(str))
        missing_symbols = [symbol for symbol in held_symbols if symbol not in covered]
    elif held_symbols:
        missing_symbols = list(held_symbols)
    return {
        "review_required": bool(review_required or missing_fields or missing_symbols or stale),
        "reason": reason or ("pm_opportunity_contract_mismatch" if missing_fields or missing_symbols or stale else ""),
        "status": "REVIEW_REQUIRED" if review_required else status or "READY",
        "missing_fields": missing_fields,
        "missing_symbols": missing_symbols,
        "stale": stale,
    }


def _pm_review_reason(
    *,
    current_has_positions: bool,
    missing_fields: list[str],
    missing_symbols: list[str],
    stale_artifacts: list[str],
    feature_reason: str,
    opportunity_reason: str,
) -> str:
    if stale_artifacts:
        return "pm_input_stale_artifacts"
    if feature_reason:
        return feature_reason
    if opportunity_reason:
        return opportunity_reason
    if missing_symbols:
        return "pm_input_missing_symbol_coverage"
    if missing_fields:
        return "pm_input_required_fields_missing"
    if not current_has_positions:
        return ""
    return "pm_input_contract_review_required"


def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _counts(decisions: tuple[dict[str, Any], ...]) -> dict[str, int]:
    counts = {"HOLD": 0, "REDUCE": 0, "EXIT": 0, "ADD": 0}
    for decision in decisions:
        key = str(decision.get("decision") or "").upper()
        if key in counts:
            counts[key] += 1
    return counts


def _current_quantity(current: dict[str, Any], symbol: str) -> float:
    return sum(
        float(item.get("quantity") or 0)
        for item in current.get("positions") or ()
        if str(item.get("symbol") or item.get("issue_code") or "") == symbol
    )


def _confidence(row: dict[str, Any], decision: str) -> float:
    key = {
        "HOLD": "hold_score",
        "EXIT": "exit_score",
        "REDUCE": "reduce_score",
        "ADD": "add_score",
    }.get(decision, "hold_score")
    return _float(row.get(key))


def _safe_return(current_price: float, entry_price: float) -> float:
    if entry_price <= 0:
        return 0.0
    return round((current_price / entry_price) - 1.0, 6)


def _float(value: Any) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _reject_mode_rooted_runtime_root(root: Path) -> None:
    text = str(root)
    if text.endswith("/demo") or "/demo/" in text:
        raise ValueError("mode-rooted Current path is not allowed")
