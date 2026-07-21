"""Runtime regular-path adapter for Position Management AI.

The adapter does not alter Position Management AI scoring or thresholds.  It
prepares Runtime-owned Current positions as AI input, calls the existing
Position Management inference entrypoint, and normalizes the output into the
Runtime decision artifact consumed by SELL Planning.
"""

from __future__ import annotations

import json
import hashlib
import math
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
from ai_fund_lab_v2.runtime_v2.market_refresh.feature_date_contract import (
    load_feature_date_contract,
    resolve_feature_date_contract,
)
from ai_fund_lab_v2.runtime_v2.planning.sell_pipeline import SellExitDecision


ARTIFACT_SCHEMA_VERSION = "runtime_v2_position_management_decision_v1"
INFERENCE_VERSION = "position_management_ai_phase6a_regular_path_v1"
PM_INPUT_SCHEMA_VERSION = "runtime_v2_pm_input_v2"
PM_FEATURE_CONTRACT_VERSION = "runtime_v2_pm_feature_input_contract_v2"
PM_REDUCE_INTENSITY_CONTRACT_VERSION = "runtime_v2_pm_reduce_intensity_v1"
CURRENT_REQUIRED_FIELDS = ("symbol", "quantity", "as_of", "source", "average_price")
PM_FEATURE_TECHNICAL_REQUIRED_COLUMNS = (
    "price_momentum_return_5d",
    "price_momentum_return_20d",
    "trend_close_over_ma_20d",
    "trend_ma_5_20_ratio",
    "volume_momentum_ratio_5d",
    "volatility_return_std_20d",
)
PM_FEATURE_REQUIRED_COLUMNS = (
    "target_date",
    "feature_as_of_date",
    "code",
    "feature_source_artifact",
    "feature_source_hash",
    "required_features",
    "optional_features",
    "missing_features",
    "defaulted_features",
    "temporal_validation_status",
    *PM_FEATURE_TECHNICAL_REQUIRED_COLUMNS,
)
PM_FEATURE_OPTIONAL_COLUMNS = ("no_position_reason",)
OPPORTUNITY_REQUIRED_COLUMNS = (
    "target_date",
    "code",
    "expected_edge_score",
    "buy_rank",
    "downside_risk_score",
)
BUY_OPPORTUNITY_SCHEMA_NAME = "runtime_v2_buy_opportunity_ranking"
BUY_OPPORTUNITY_SCHEMA_VERSION = "runtime_v2_opportunity_ranking_v1"
BUY_OPPORTUNITY_LEGACY_SCHEMA_VERSIONS = {"runtime_v2_opportunity_rankings_v1"}
BUY_OPPORTUNITY_ARTIFACT_ROLE = "BUY_OPPORTUNITY_RANKING"
PM_RUNTIME_ADAPTER_AUTHORITY_MISMATCH = "PM_RUNTIME_ADAPTER_AUTHORITY_MISMATCH"


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
            "pm_feature_contract_version": self.input_contract.get("pm_feature_contract_version") or "",
            "pm_feature_source_hash": self.input_contract.get("pm_feature_source_hash") or "",
            "pm_feature_row_count": self.input_contract.get("pm_feature_row_count"),
            "pm_opportunity_source": self.input_contract.get("pm_opportunity_source") or "",
            "pm_opportunity_status": self.input_contract.get("pm_opportunity_status") or "",
            "pm_missing_fields": self.input_contract.get("pm_missing_fields") or [],
            "pm_missing_symbols": self.input_contract.get("pm_missing_symbols") or [],
            "pm_derived_fields": self.input_contract.get("pm_derived_fields") or [],
            "pm_defaulted_fields": self.input_contract.get("pm_defaulted_fields") or [],
            "pm_required_feature_validation": self.input_contract.get("pm_required_feature_validation") or {},
            "pm_optional_feature_status": self.input_contract.get("pm_optional_feature_status") or {},
            "pm_temporal_validation_status": self.input_contract.get("pm_temporal_validation_status") or "",
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
    if mode not in {"historical", "demo", "production"}:
        raise ValueError("Position Management Runtime producer supports historical/demo/production only")
    _reject_mode_rooted_runtime_root(root)
    generated_at = _iso(now or datetime.now(timezone.utc))
    runtime_id = f"runtime-v2-position-management-{business_date}-{generated_at.replace(':', '').replace('-', '')}"
    resolved_feature_date = feature_date or business_date
    resolved_opportunity_path, resolved_pm_feature_path = _resolve_runtime_pm_input_paths(
        root=root,
        business_date=business_date,
        feature_date=resolved_feature_date,
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact_dir = root / "runtime_state" / "position_management" / business_date
    artifact_dir.mkdir(parents=True, exist_ok=True)
    holding_path = artifact_dir / "current_holdings_snapshot.csv"
    artifact_path = artifact_dir / "position_management_decisions.json"
    pm_opportunity_context_path = artifact_dir / "position_management_opportunity_context.csv"
    try:
        pm_runtime_adapter_authority = verify_position_management_runtime_adapter_authority()
    except RuntimeArtifactLookupHalt as exc:
        payload = _artifact_payload(
            business_date=business_date,
            runtime_id=runtime_id,
            mode=mode,
            feature_date=resolved_feature_date,
            generated_at=generated_at,
            holding_path=holding_path,
            opportunity_path=resolved_opportunity_path,
            feature_path=resolved_pm_feature_path,
            inference_output_path=artifact_dir / "position_management_inference.parquet",
            action_csv_path=artifact_dir / "position_management_actions.csv",
            summary_path=artifact_dir / "position_management_inference_summary.json",
            audit_path=artifact_dir / "position_management_inference_audit.json",
            status="HALT",
            reason=str(exc),
            decisions=(),
            input_contract={
                "pm_input_schema_status": "HALT",
                "pm_runtime_adapter_authority_status": "HALT",
                "pm_runtime_adapter_authority_reason": str(exc),
                "pm_review_reason": str(exc),
            },
        )
        _write_json(artifact_path, payload)
        return _result_from_payload(payload, artifact_path=artifact_path, sell_exit_decisions=())
    current_path = root / "persistent_ledger" / "state.json"
    current = _read_json(current_path)
    runtime_state_path = root / "runtime_state" / "current_state.json"
    runtime_state = _read_json(runtime_state_path) if runtime_state_path.is_file() else {}
    contract = _validate_pm_input_contract(
        current=current,
        current_path=current_path,
        runtime_state=runtime_state,
        runtime_state_path=runtime_state_path,
        business_date=business_date,
        feature_date=resolved_feature_date,
        opportunity_path=resolved_opportunity_path,
        feature_path=resolved_pm_feature_path,
    )
    contract["pm_runtime_adapter_authority_status"] = "PASS"
    contract["pm_runtime_adapter_authority"] = pm_runtime_adapter_authority
    if contract["pm_input_schema_status"] == "REVIEW_REQUIRED":
        payload = _artifact_payload(
            business_date=business_date,
            runtime_id=runtime_id,
            mode=mode,
            feature_date=resolved_feature_date,
            generated_at=generated_at,
            holding_path=holding_path,
            opportunity_path=resolved_opportunity_path,
            feature_path=resolved_pm_feature_path,
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
            opportunity_path=resolved_opportunity_path,
            feature_path=resolved_pm_feature_path,
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

    if not resolved_opportunity_path.is_file() or not resolved_pm_feature_path.is_file():
        payload = _artifact_payload(
            business_date=business_date,
            runtime_id=runtime_id,
            mode=mode,
            feature_date=resolved_feature_date,
            generated_at=generated_at,
            holding_path=holding_path,
            opportunity_path=resolved_opportunity_path,
            feature_path=resolved_pm_feature_path,
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
    _write_pm_opportunity_context(
        source_path=resolved_opportunity_path,
        output_path=pm_opportunity_context_path,
        feature_date=resolved_feature_date,
    )

    inference = run_position_management_inference(
        holding_path=holding_path,
        opportunity_path=pm_opportunity_context_path,
        feature_path=resolved_pm_feature_path,
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
        opportunity_path=resolved_opportunity_path,
        feature_path=resolved_pm_feature_path,
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


def _resolve_runtime_pm_input_paths(
    *,
    root: Path,
    business_date: str,
    feature_date: str,
    opportunity_path: Path | str | None,
    feature_path: Path | str | None,
) -> tuple[Path, Path]:
    resolved_opportunity = (
        Path(opportunity_path)
        if opportunity_path
        else root / "runtime_state" / "buy_ai" / business_date / "opportunity_rankings.json"
    )
    if feature_path:
        resolved_feature = Path(feature_path)
    else:
        operations_root = root / "operations"
        contract = load_feature_date_contract(
            operations_root=operations_root,
            requested_feature_date=business_date,
        )
        if contract is None:
            contract = resolve_feature_date_contract(
                operations_root=operations_root,
                requested_feature_date=feature_date,
                persist_consumer_readiness=False,
            )
        generated = dict(contract.generated_feature_artifacts)
        resolved_feature = Path(
            generated.get("position_feature_input.parquet")
            or contract.feature_artifact_dir
        )
        if resolved_feature.is_dir() or resolved_feature.suffix != ".parquet":
            resolved_feature = Path(contract.feature_artifact_dir) / "position_feature_input.parquet"
    return resolved_opportunity, resolved_feature


def verify_position_management_runtime_adapter_authority(
    pm_artifacts: Any | None = None,
    *,
    executing_source_path: Path | str | None = None,
    repo_root: Path | str | None = None,
) -> dict[str, Any]:
    artifacts = pm_artifacts or resolve_position_management_policy_artifacts()
    adapter = artifacts.require_member("RUNTIME_ADAPTER")
    repo = _runtime_source_repo_root(repo_root)
    accepted_path = _canonical_repo_relative_path(Path(adapter.physical_path), repo_root=repo, label="accepted path")
    actual_path = Path(executing_source_path) if executing_source_path is not None else Path(__file__)
    actual_identity = _runtime_adapter_source_identity(actual_path, repo_root=repo)
    if accepted_path != actual_identity["repo_relative_path"]:
        raise RuntimeArtifactLookupHalt(
            f"{PM_RUNTIME_ADAPTER_AUTHORITY_MISMATCH}: accepted path {accepted_path} does not match executing source {actual_identity['repo_relative_path']}"
        )
    actual_hash = actual_identity["content_hash"]
    if actual_hash != adapter.content_hash:
        raise RuntimeArtifactLookupHalt(
            f"{PM_RUNTIME_ADAPTER_AUTHORITY_MISMATCH}: accepted hash {adapter.content_hash} does not match executing source hash {actual_hash}"
        )
    raw_resolver_result = getattr(artifacts, "raw_resolver_result", {})
    _validate_pm_adapter_resolver_result(raw_resolver_result)
    adapter_raw = _raw_member_for_role(raw_resolver_result, "RUNTIME_ADAPTER")
    authority_mode = str(adapter_raw.get("authority_mode") or "ACCEPTED_CURRENT_PATH")
    return {
        "authority_mode": authority_mode,
        "accepted_current_path": adapter_raw.get("accepted_current_path", authority_mode == "ACCEPTED_CURRENT_PATH"),
        "accepted_path": accepted_path,
        "executing_source_path": actual_identity["repo_relative_path"],
        "accepted_hash": adapter.content_hash,
        "executing_source_hash": actual_hash,
        "hash_algorithm": "sha256",
        "hash_materials": ["runtime_adapter_source_bytes"],
        "hash_contract": "sha256 over the canonical runtime adapter source file bytes; source comments are included; absolute paths, cwd, timestamps, cache files, pyc files, and generated artifacts are excluded",
        "canonical_identity": {
            "path_contract": "repo_relative_posix_path",
            "repo_relative_path": actual_identity["repo_relative_path"],
            "checkout_location_independent": True,
        },
        "artifact_set_id": adapter.artifact_set_id,
        "artifact_instance_id": getattr(artifacts, "artifact_instance_id", ""),
        "accepted_event_id": getattr(artifacts, "accepted_event_id", ""),
    }


def load_sell_exit_decisions_from_pm_artifact(path: Path | str) -> tuple[SellExitDecision, ...]:
    artifact_path = Path(path)
    payload = _read_json(artifact_path)
    if payload.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
        raise ValueError("Position Management artifact schema mismatch")
    payload = {**payload, "artifact_path": str(artifact_path)}
    return _sell_exit_decisions_from_artifact(payload)


def validate_position_management_input_contract(
    *,
    current: dict[str, Any],
    current_path: Path | str,
    runtime_state: dict[str, Any] | None = None,
    runtime_state_path: Path | str | None = None,
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
        runtime_state=runtime_state or {},
        runtime_state_path=Path(runtime_state_path) if runtime_state_path else Path(""),
        business_date=business_date,
        feature_date=feature_date,
        opportunity_path=Path(opportunity_path) if opportunity_path else Path(""),
        feature_path=Path(feature_path) if feature_path else Path(""),
    )


def _sell_exit_decisions_from_artifact(payload: dict[str, Any]) -> tuple[SellExitDecision, ...]:
    decisions: list[SellExitDecision] = []
    for item in payload.get("decisions") or ():
        decision = str(item.get("decision") or "").upper()
        if decision not in {"EXIT", "REDUCE"}:
            continue
        quantity = float(item.get("runtime_sell_quantity") or 0)
        if decision == "EXIT" and quantity <= 0:
            continue
        decisions.append(
            SellExitDecision(
                symbol=str(item.get("symbol") or ""),
                quantity=quantity,
                reason=str(item.get("reason") or "position_management_exit"),
                score=float(item.get("confidence") or 0.0),
                source_decision=decision,
                reduce_intensity=str(item.get("reduce_intensity") or ""),
                source_decision_artifact=str(payload.get("artifact_path") or ""),
                source_decision_id=str(item.get("decision_id") or ""),
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
    reduce_intensity = ""
    reduce_intensity_evidence: dict[str, Any] = {}
    if decision == "REDUCE":
        reduce_intensity = _reduce_intensity(row=row, reason=reason)
        reduce_intensity_evidence = {
            "contract_version": PM_REDUCE_INTENSITY_CONTRACT_VERSION,
            "authority": "Position Management emits reduce intensity; Sell Planning owns broker quantity calculation",
            "reduce_score": _float(row.get("reduce_score")),
            "exit_score": _float(row.get("exit_score")),
            "hold_score": _float(row.get("hold_score")),
            "reason": reason,
        }
        runtime_action = "SELL_PARTIAL_POSITION_REDUCE_QUANTITY_BY_SELL_PLANNING"
    if decision == "ADD":
        runtime_action = "NO_SELL_ORDER_ADD_OUT_OF_SELL_SCOPE"
        reason = reason + "; ADD is outside SELL Planning scope"
    return {
        "decision_id": f"pm-{str(row.get('target_date') or '')}-{symbol}-{decision.lower()}",
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
        "reduce_intensity": reduce_intensity,
        "reduce_intensity_evidence": reduce_intensity_evidence,
        "runtime_quantity_authority": (
            "SELL_PLANNING_REDUCE_QUANTITY_CONTRACT"
            if decision == "REDUCE"
            else "PM_EXIT_FULL_POSITION_QUANTITY"
            if decision == "EXIT"
            else ""
        ),
    }


def _reduce_intensity(*, row: dict[str, Any], reason: str) -> str:
    reduce_score = _float(row.get("reduce_score"))
    text = str(reason or "").lower()
    if reduce_score >= 0.60 or "high_downside" in text:
        return "STRONG"
    if reduce_score >= 0.50 or "peak_drawdown_warning" in text:
        return "MEDIUM"
    return "LIGHT"


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
        "feature_contract_version": str(contract.get("pm_feature_contract_version") or PM_FEATURE_CONTRACT_VERSION),
        "feature_source_artifact": str(contract.get("pm_feature_source_artifact") or feature_path),
        "feature_source_hash": str(contract.get("pm_feature_source_hash") or ""),
        "required_features": list(contract.get("pm_required_features") or []),
        "optional_features": list(contract.get("pm_optional_features") or []),
        "required_feature_validation": dict(contract.get("pm_required_feature_validation") or {}),
        "optional_feature_status": dict(contract.get("pm_optional_feature_status") or {}),
        "temporal_validation_status": str(contract.get("pm_temporal_validation_status") or ""),
        "used_feature_snapshot": dict(contract.get("pm_used_feature_snapshot") or {}),
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
    runtime_state: dict[str, Any] | None,
    runtime_state_path: Path,
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
    historical_empty_current_authority = _historical_empty_current_authority_ready(
        current=current,
        runtime_state=runtime_state or {},
        business_date=business_date,
    )
    if historical_empty_current_authority:
        current_as_of = business_date
        current_updated_at = current_updated_at or str((runtime_state or {}).get("generated_at") or f"{business_date}T00:00:00+00:00")
        current_position_status = "READY"
        current_valuation_status = "READY"
    temporal_schema = bool(current.get("temporal_schema_version"))
    temporal_current_ready = (
        temporal_schema
        and current_position_status in {"READY", "VALID_CARRYOVER"}
        and current_valuation_status in {"READY", "VALID_CARRYOVER"}
    ) or historical_empty_current_authority
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
        business_date=business_date,
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
        "pm_runtime_state_source": str(runtime_state_path),
        "pm_current_as_of": current_as_of,
        "pm_position_state_as_of": business_date if historical_empty_current_authority else str(current.get("position_state_as_of") or ""),
        "pm_valuation_as_of": business_date if historical_empty_current_authority else str(current.get("valuation_as_of") or ""),
        "pm_current_position_status": current_position_status,
        "pm_current_valuation_status": current_valuation_status,
        "pm_historical_empty_current_authority": "runtime_state_current_state" if historical_empty_current_authority else "",
        "pm_current_freshness": "STALE" if "current" in stale_artifacts else "FRESH",
        "pm_feature_source": str(feature_path),
        "pm_feature_contract_version": feature_status.get("feature_contract_version") or PM_FEATURE_CONTRACT_VERSION,
        "pm_feature_source_artifact": feature_status.get("source_artifact") or str(feature_path),
        "pm_feature_source_hash": feature_status.get("source_hash") or "",
        "pm_feature_row_count": feature_status["row_count"],
        "pm_feature_date": feature_date,
        "pm_required_features": feature_status.get("required_features") or list(PM_FEATURE_TECHNICAL_REQUIRED_COLUMNS),
        "pm_optional_features": feature_status.get("optional_features") or list(PM_FEATURE_OPTIONAL_COLUMNS),
        "pm_required_feature_validation": feature_status.get("required_feature_validation") or {},
        "pm_optional_feature_status": feature_status.get("optional_feature_status") or {},
        "pm_temporal_validation_status": feature_status.get("temporal_validation_status") or "",
        "pm_used_feature_snapshot": feature_status.get("used_feature_snapshot") or {},
        "pm_opportunity_source": str(opportunity_path),
        "pm_opportunity_status": opportunity_status["status"],
        "pm_opportunity_model_version": opportunity_status.get("model_version") or "",
        "pm_opportunity_model_authority": opportunity_status.get("model_authority") or {},
        "pm_opportunity_contract_schema": opportunity_status.get("schema_name") or "",
        "pm_opportunity_artifact_role": opportunity_status.get("artifact_role") or "",
        "pm_opportunity_row_universe": opportunity_status.get("row_universe") or "",
        "pm_opportunity_ranked_symbol_count": opportunity_status.get("ranked_symbol_count", 0),
        "pm_opportunity_unranked_symbols": opportunity_status.get("unranked_symbols") or [],
        "pm_opportunity_missing_symbol_semantics": opportunity_status.get("missing_symbol_semantics") or "",
        "pm_opportunity_empty_semantics": opportunity_status.get("empty_semantics") or "",
        "pm_missing_fields": sorted(set(missing_fields)),
        "pm_missing_symbols": sorted(set(symbol for symbol in missing_symbols if symbol)),
        "pm_stale_artifacts": sorted(set(stale_artifacts)),
        "pm_derived_fields": sorted(set(derived_fields)),
        "pm_defaulted_fields": sorted(set(defaulted_fields + list(feature_status.get("defaulted_fields") or []))),
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
            "feature_contract_version": PM_FEATURE_CONTRACT_VERSION,
            "source_hash": "",
            "source_artifact": str(feature_path),
            "required_features": list(PM_FEATURE_TECHNICAL_REQUIRED_COLUMNS),
            "optional_features": list(PM_FEATURE_OPTIONAL_COLUMNS),
            "defaulted_fields": [],
            "required_feature_validation": {"status": "NOT_RUN"},
            "optional_feature_status": {},
            "temporal_validation_status": "NOT_RUN",
            "used_feature_snapshot": {},
        }
    frame = _read_table(feature_path)
    columns = set(str(column) for column in frame.columns)
    missing_fields = [f"pm_feature.{column}" for column in PM_FEATURE_REQUIRED_COLUMNS if column not in columns]
    if missing_fields:
        return {
            "review_required": current_has_positions,
            "reason": "pm_feature_required_columns_missing" if current_has_positions else "",
            "row_count": len(frame),
            "missing_fields": missing_fields,
            "missing_symbols": [],
            "stale": False,
            "feature_contract_version": PM_FEATURE_CONTRACT_VERSION,
            "source_hash": _sha256_file(feature_path),
            "source_artifact": str(feature_path),
            "required_features": list(PM_FEATURE_TECHNICAL_REQUIRED_COLUMNS),
            "optional_features": list(PM_FEATURE_OPTIONAL_COLUMNS),
            "defaulted_fields": [],
            "required_feature_validation": {
                "status": "FAIL" if current_has_positions else "NOT_REQUIRED",
                "missing_columns": missing_fields,
            },
            "optional_feature_status": {},
            "temporal_validation_status": "NOT_RUN",
            "used_feature_snapshot": {},
        }
    frame = frame.copy()
    frame["target_date"] = frame["target_date"].astype(str)
    frame["code"] = frame["code"].astype(str)
    date_rows = frame[frame["target_date"] == feature_date].copy()
    stale = bool(len(frame) and date_rows.empty)
    feature_hash = _sha256_file(feature_path)
    defaulted_fields = _pm_feature_json_list_values(date_rows, "defaulted_features")
    missing_feature_values = _pm_feature_json_list_values(date_rows, "missing_features")
    optional_status = {
        "optional_features": list(PM_FEATURE_OPTIONAL_COLUMNS),
        "missing_optional_columns": [column for column in PM_FEATURE_OPTIONAL_COLUMNS if column not in columns],
        "default_policy": "no_position_reason_optional; scoring features do not default in runtime producer",
    }
    if not current_has_positions:
        return {
            "review_required": False,
            "reason": "",
            "row_count": len(date_rows),
            "missing_fields": [],
            "missing_symbols": [],
            "stale": stale,
            "feature_contract_version": PM_FEATURE_CONTRACT_VERSION,
            "source_hash": feature_hash,
            "source_artifact": str(feature_path),
            "required_features": list(PM_FEATURE_TECHNICAL_REQUIRED_COLUMNS),
            "optional_features": list(PM_FEATURE_OPTIONAL_COLUMNS),
            "defaulted_fields": defaulted_fields,
            "required_feature_validation": {"status": "NOT_REQUIRED", "reason": "no_current_positions"},
            "optional_feature_status": optional_status,
            "temporal_validation_status": "PASS" if not stale else "STALE",
            "used_feature_snapshot": {},
        }
    if date_rows.empty:
        return {
            "review_required": True,
            "reason": "pm_feature_rows_missing_for_current_positions",
            "row_count": 0,
            "missing_fields": [],
            "missing_symbols": list(held_symbols),
            "stale": stale,
            "feature_contract_version": PM_FEATURE_CONTRACT_VERSION,
            "source_hash": feature_hash,
            "source_artifact": str(feature_path),
            "required_features": list(PM_FEATURE_TECHNICAL_REQUIRED_COLUMNS),
            "optional_features": list(PM_FEATURE_OPTIONAL_COLUMNS),
            "defaulted_fields": defaulted_fields,
            "required_feature_validation": {"status": "FAIL", "reason": "rows_missing"},
            "optional_feature_status": optional_status,
            "temporal_validation_status": "STALE" if stale else "FAIL",
            "used_feature_snapshot": {},
        }
    covered = set(date_rows["code"].astype(str))
    missing_symbols = [symbol for symbol in held_symbols if symbol not in covered]
    duplicate_count = int(date_rows.duplicated(["target_date", "code"]).sum())
    numeric_failures = _pm_feature_numeric_failures(date_rows, PM_FEATURE_TECHNICAL_REQUIRED_COLUMNS)
    future_count = _pm_feature_future_date_count(date_rows, feature_date=feature_date)
    row_missing_features = sorted(set(missing_feature_values))
    temporal_status_values = sorted(set(date_rows.get("temporal_validation_status", pd.Series([], dtype=str)).dropna().astype(str).tolist()))
    temporal_failure = bool(future_count or any(value not in {"PASS", ""} for value in temporal_status_values))
    missing_required_values = [
        f"pm_feature.{column}"
        for column in PM_FEATURE_TECHNICAL_REQUIRED_COLUMNS
        if column in date_rows.columns and date_rows[column].isna().any()
    ]
    validation_status = "PASS"
    validation_reasons: list[str] = []
    if missing_symbols:
        validation_status = "FAIL"
        validation_reasons.append("missing_held_symbols")
    if duplicate_count:
        validation_status = "FAIL"
        validation_reasons.append("duplicate_target_date_code")
    if numeric_failures:
        validation_status = "FAIL"
        validation_reasons.append("non_finite_numeric_feature")
    if missing_required_values or row_missing_features:
        validation_status = "FAIL"
        validation_reasons.append("required_feature_value_missing")
    if defaulted_fields:
        validation_status = "FAIL"
        validation_reasons.append("implicit_defaulted_feature_not_allowed")
    if temporal_failure or stale:
        validation_status = "FAIL"
        validation_reasons.append("temporal_validation_failed")
    required_validation = {
        "status": validation_status,
        "required_columns": list(PM_FEATURE_REQUIRED_COLUMNS),
        "required_technical_features": list(PM_FEATURE_TECHNICAL_REQUIRED_COLUMNS),
        "missing_columns": [],
        "missing_feature_values": sorted(set(missing_required_values + [f"pm_feature.{item}" for item in row_missing_features])),
        "duplicate_count": duplicate_count,
        "numeric_failures": numeric_failures,
        "reasons": validation_reasons,
    }
    used_feature_snapshot = _pm_used_feature_snapshot(date_rows, held_symbols=held_symbols)
    review_required = bool(missing_symbols or validation_status != "PASS")
    reason = ""
    if review_required:
        reason = "pm_feature_required_feature_missing" if (missing_required_values or row_missing_features) else "pm_feature_contract_validation_failed"
    if missing_symbols:
        reason = "pm_feature_rows_missing_for_current_positions"
    return {
        "review_required": review_required,
        "reason": reason,
        "row_count": len(date_rows),
        "missing_fields": [],
        "missing_symbols": missing_symbols,
        "stale": stale,
        "feature_contract_version": PM_FEATURE_CONTRACT_VERSION,
        "source_hash": feature_hash,
        "source_artifact": str(feature_path),
        "required_features": list(PM_FEATURE_TECHNICAL_REQUIRED_COLUMNS),
        "optional_features": list(PM_FEATURE_OPTIONAL_COLUMNS),
        "defaulted_fields": defaulted_fields,
        "required_feature_validation": required_validation,
        "optional_feature_status": optional_status,
        "temporal_validation_status": "PASS" if not temporal_failure and not stale else "FAIL",
        "used_feature_snapshot": used_feature_snapshot,
    }


def _pm_feature_json_list_values(frame: pd.DataFrame, column: str) -> list[str]:
    if frame.empty or column not in frame.columns:
        return []
    values: list[str] = []
    for raw in frame[column].dropna().tolist():
        if raw in ("", "[]"):
            continue
        parsed: Any
        if isinstance(raw, list):
            parsed = raw
        else:
            try:
                parsed = json.loads(str(raw))
            except json.JSONDecodeError:
                parsed = [str(raw)]
        if isinstance(parsed, list):
            values.extend(str(item) for item in parsed if str(item))
        elif parsed not in (None, ""):
            values.append(str(parsed))
    return sorted(set(values))


def _pm_feature_numeric_failures(frame: pd.DataFrame, columns: tuple[str, ...]) -> list[str]:
    failures: list[str] = []
    for column in columns:
        if column not in frame.columns:
            failures.append(f"pm_feature.{column}:missing_column")
            continue
        values = pd.to_numeric(frame[column], errors="coerce")
        if values.isna().any() or not values.map(lambda value: math.isfinite(float(value))).all():
            failures.append(f"pm_feature.{column}:non_finite")
    return failures


def _pm_feature_future_date_count(frame: pd.DataFrame, *, feature_date: str) -> int:
    count = 0
    target = pd.to_datetime(pd.Series([feature_date]), errors="coerce").iloc[0]
    if pd.isna(target):
        return len(frame)
    for column in ("feature_as_of_date", "data_until", "position_state_as_of"):
        if column not in frame.columns:
            continue
        dates = pd.to_datetime(frame[column], errors="coerce")
        count += int(((dates > target) | dates.isna()).sum())
    return count


def _pm_used_feature_snapshot(frame: pd.DataFrame, *, held_symbols: tuple[str, ...]) -> dict[str, Any]:
    if frame.empty:
        return {"row_count": 0, "symbols": []}
    rows = frame[frame["code"].astype(str).isin(set(held_symbols))] if "code" in frame.columns else frame
    snapshot: dict[str, Any] = {
        "row_count": int(len(rows)),
        "symbols": sorted(rows["code"].astype(str).unique().tolist()) if "code" in rows.columns else [],
        "technical_features": list(PM_FEATURE_TECHNICAL_REQUIRED_COLUMNS),
    }
    for column in PM_FEATURE_TECHNICAL_REQUIRED_COLUMNS:
        if column not in rows.columns:
            continue
        values = pd.to_numeric(rows[column], errors="coerce")
        snapshot[column] = {
            "min": _float(values.min()),
            "max": _float(values.max()),
            "missing_count": int(values.isna().sum()),
        }
    return snapshot


def _sha256_file(path: Path) -> str:
    if not path or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    business_date: str,
    feature_date: str,
    held_symbols: tuple[str, ...],
    current_has_positions: bool,
) -> dict[str, Any]:
    if not current_has_positions:
        return {
            "review_required": False,
            "reason": "",
            "status": "NOT_REQUIRED",
            "missing_fields": [],
            "missing_symbols": [],
            "stale": False,
            "unranked_symbols": [],
            "missing_symbol_semantics": "not_required_without_current_positions",
        }
    if not opportunity_path or not opportunity_path.is_file():
        return {
            "review_required": True,
            "reason": "pm_opportunity_artifact_missing",
            "status": "MISSING",
            "missing_fields": ["pm_opportunity_source"],
            "missing_symbols": [],
            "stale": False,
            "unranked_symbols": [],
            "missing_symbol_semantics": "artifact_missing",
        }
    try:
        contract = _pm_opportunity_contract(
            opportunity_path=opportunity_path,
            business_date=business_date,
            feature_date=feature_date,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {
            "review_required": True,
            "reason": "pm_opportunity_contract_mismatch",
            "status": "HALT",
            "missing_fields": [f"opportunity.contract:{exc}"],
            "missing_symbols": [],
            "stale": False,
            "unranked_symbols": [],
            "missing_symbol_semantics": "contract_halt",
        }
    frame = contract["frame"]
    status = contract["status"]
    review_required = contract["review_required"]
    missing_fields = list(contract["missing_fields"])
    feature_date_value = str(contract["feature_date"])
    reason = str(contract["reason"])
    columns = set(str(column) for column in frame.columns)
    missing_fields.extend(f"opportunity.{column}" for column in OPPORTUNITY_REQUIRED_COLUMNS if column not in columns)
    stale = feature_date_value != feature_date
    missing_symbols: list[str] = []
    unranked_symbols: list[str] = []
    if not frame.empty and {"target_date", "code"}.issubset(columns):
        filtered = frame[frame["target_date"].astype(str) == feature_date]
        covered = set(filtered["code"].astype(str))
        unranked_symbols = [symbol for symbol in held_symbols if symbol not in covered]
    elif held_symbols and not missing_fields and not review_required:
        unranked_symbols = list(held_symbols)
    elif held_symbols:
        missing_symbols = list(held_symbols)
    normalized_status = "REVIEW_REQUIRED" if review_required else "READY" if status in {"", "PASS"} else status
    return {
        "review_required": bool(review_required or missing_fields or missing_symbols or stale),
        "reason": reason or ("pm_opportunity_contract_mismatch" if missing_fields or missing_symbols or stale else ""),
        "status": normalized_status,
        "missing_fields": missing_fields,
        "missing_symbols": missing_symbols,
        "stale": stale,
        "schema_name": contract.get("schema_name") or "",
        "artifact_role": contract.get("artifact_role") or "",
        "row_universe": contract.get("row_universe") or "",
        "ranked_symbol_count": int(contract.get("ranked_symbol_count") or 0),
        "unranked_symbols": unranked_symbols,
        "missing_symbol_semantics": "symbol_not_ranked_is_valid_pm_context_default" if unranked_symbols and not missing_symbols else "",
        "empty_semantics": contract.get("empty_semantics") or "",
        "model_version": contract.get("model_version") or "",
        "model_authority": contract.get("model_authority") or {},
    }


def _pm_opportunity_contract(*, opportunity_path: Path, business_date: str = "", feature_date: str) -> dict[str, Any]:
    if opportunity_path.suffix == ".json":
        payload = _read_json(opportunity_path)
        schema_version = str(payload.get("schema_version") or "")
        status = str(payload.get("status") or "")
        if schema_version == "" and status in {"REVIEW_REQUIRED", "BLOCKED", "HALT"}:
            return {
                "status": "REVIEW_REQUIRED" if status != "HALT" else "HALT",
                "reason": "pm_opportunity_review_required",
                "review_required": True,
                "missing_fields": [],
                "feature_date": str(payload.get("feature_date") or feature_date),
                "frame": pd.DataFrame(columns=OPPORTUNITY_REQUIRED_COLUMNS),
                "schema_name": "",
                "artifact_role": "",
                "row_universe": "review_required_legacy_payload",
                "ranked_symbol_count": 0,
                "empty_semantics": "",
                "model_version": "",
                "model_authority": {},
            }
        schema_name = str(payload.get("schema_name") or BUY_OPPORTUNITY_SCHEMA_NAME)
        artifact_role = str(payload.get("artifact_role") or BUY_OPPORTUNITY_ARTIFACT_ROLE)
        producer = str(payload.get("producer") or "Runtime v2 BUY AI Producer")
        if schema_version != BUY_OPPORTUNITY_SCHEMA_VERSION and schema_version not in BUY_OPPORTUNITY_LEGACY_SCHEMA_VERSIONS:
            raise ValueError("unsupported opportunity schema_version")
        if schema_name != BUY_OPPORTUNITY_SCHEMA_NAME:
            raise ValueError("unsupported opportunity schema_name")
        if artifact_role != BUY_OPPORTUNITY_ARTIFACT_ROLE:
            raise ValueError("wrong opportunity artifact_role")
        if producer != "Runtime v2 BUY AI Producer":
            raise ValueError("producer identity mismatch")
        payload_business_date = str(payload.get("business_date") or "")
        payload_feature_date = str(payload.get("feature_date") or "")
        if business_date and payload_business_date and payload_business_date != business_date:
            raise ValueError("business date mismatch")
        if payload_feature_date != feature_date:
            raise ValueError("target date mismatch")
        review_required = bool(payload.get("review_required")) or status in {"REVIEW_REQUIRED", "BLOCKED", "HALT"}
        missing_fields: list[str] = []
        if not payload.get("model_version"):
            missing_fields.append("opportunity.model_version")
        missing_fields.extend(_opportunity_model_authority_mismatches(payload))
        if not payload.get("generated_at"):
            missing_fields.append("opportunity.generated_at")
        rows_payload = payload.get("rankings")
        if rows_payload is None:
            rows_payload = payload.get("rows")
        if not isinstance(rows_payload, list):
            raise ValueError("opportunity rankings must be a list")
        rows = [_canonical_pm_opportunity_row(row, default_target_date=feature_date) for row in rows_payload]
        frame = pd.DataFrame(rows, columns=OPPORTUNITY_REQUIRED_COLUMNS + ("risk_guard_status", "candidate_score", "candidate_rank", "buy_reason"))
        _validate_pm_opportunity_frame(frame, feature_date=feature_date)
        empty_semantics = "no_buy_signal_confirmed_empty" if status in {"PASS", "READY"} and frame.empty else ""
        return {
            "status": status,
            "reason": "pm_opportunity_review_required" if review_required else "",
            "review_required": review_required,
            "missing_fields": missing_fields,
            "feature_date": payload_feature_date,
            "frame": frame,
            "schema_name": schema_name,
            "artifact_role": artifact_role,
            "row_universe": "ranked_buy_candidates_only",
            "ranked_symbol_count": len(frame),
            "empty_semantics": empty_semantics,
            "model_version": str(payload.get("model_version") or ""),
            "model_authority": dict(payload.get("model_authority") or {}) if isinstance(payload.get("model_authority"), dict) else {},
        }
    frame = _read_table(opportunity_path)
    _validate_pm_opportunity_frame(frame, feature_date=feature_date)
    return {
        "status": "READY",
        "reason": "",
        "review_required": False,
        "missing_fields": [],
        "feature_date": feature_date,
        "frame": frame,
        "schema_name": "runtime_v2_pm_opportunity_context",
        "artifact_role": "PM_OPPORTUNITY_CONTEXT",
        "row_universe": "pm_opportunity_context",
        "ranked_symbol_count": len(frame),
        "empty_semantics": "confirmed_empty" if frame.empty else "",
        "model_version": "",
        "model_authority": {},
    }


def _opportunity_model_authority_mismatches(payload: dict[str, Any]) -> list[str]:
    authority = payload.get("model_authority")
    if authority in (None, {}, ""):
        # Legacy fixture artifacts are allowed to supply only model_version.
        return []
    if not isinstance(authority, dict):
        return ["opportunity.model_authority.invalid"]
    missing: list[str] = []
    for key in ("model_version", "model_hash", "authority_source", "resolution_status"):
        if not authority.get(key):
            missing.append(f"opportunity.model_authority.{key}")
    if payload.get("model_version") and authority.get("model_version") and payload.get("model_version") != authority.get("model_version"):
        missing.append("opportunity.model_authority.model_version_mismatch")
    if authority.get("runtime_model_hash") and authority.get("model_hash") and authority.get("runtime_model_hash") != authority.get("model_hash"):
        missing.append("opportunity.model_authority.model_hash_mismatch")
    if authority.get("hash_match") is False:
        missing.append("opportunity.model_authority.hash_match_false")
    return missing


def _canonical_pm_opportunity_row(row: Any, *, default_target_date: str) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError("opportunity row must be an object")
    code = _normalize_runtime_symbol(row.get("code") or row.get("symbol") or row.get("issue_code"))
    target_date = str(row.get("target_date") or row.get("feature_date") or default_target_date)
    rank = _int_rank(row.get("buy_rank") if row.get("buy_rank") not in (None, "") else row.get("rank"))
    expected_edge = _finite_float(row.get("expected_edge_score") if row.get("expected_edge_score") not in (None, "") else row.get("opportunity_score"))
    downside = _finite_float(row.get("downside_risk_score"))
    candidate_score = row.get("candidate_score")
    candidate_rank = row.get("candidate_rank")
    return {
        "target_date": target_date,
        "code": code,
        "expected_edge_score": expected_edge,
        "buy_rank": rank,
        "downside_risk_score": downside,
        "risk_guard_status": str(row.get("risk_guard_status") or ""),
        "candidate_score": _finite_float(candidate_score) if candidate_score not in (None, "") else 0.0,
        "candidate_rank": _int_rank(candidate_rank) if candidate_rank not in (None, "") else 999999,
        "buy_reason": str(row.get("buy_reason") or row.get("reason") or ""),
    }


def _validate_pm_opportunity_frame(frame: pd.DataFrame, *, feature_date: str) -> None:
    columns = set(str(column) for column in frame.columns)
    missing = [column for column in OPPORTUNITY_REQUIRED_COLUMNS if column not in columns]
    if missing:
        raise ValueError("required opportunity fields missing: " + ",".join(missing))
    if frame.empty:
        return
    normalized = frame.copy()
    normalized["target_date"] = normalized["target_date"].astype(str)
    normalized["code"] = normalized["code"].map(_normalize_runtime_symbol)
    wrong_date = normalized[normalized["target_date"] != feature_date]
    if not wrong_date.empty:
        raise ValueError("target date mismatch")
    if normalized.duplicated(["target_date", "code"]).any():
        raise ValueError("duplicate symbol")
    for column in ("expected_edge_score", "downside_risk_score"):
        values = pd.to_numeric(normalized[column], errors="coerce")
        if values.isna().any() or not all(pd.Series(values).map(lambda value: math.isfinite(float(value)))):
            raise ValueError(f"non-finite score: {column}")
    ranks = pd.to_numeric(normalized["buy_rank"], errors="coerce")
    if ranks.isna().any() or (ranks < 1).any() or (ranks.astype(int) != ranks).any():
        raise ValueError("invalid rank")


def _write_pm_opportunity_context(*, source_path: Path, output_path: Path, feature_date: str) -> Path:
    contract = _pm_opportunity_contract(opportunity_path=source_path, feature_date=feature_date)
    frame = contract["frame"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    return output_path


def _normalize_runtime_symbol(value: Any) -> str:
    text = str(value or "").strip().upper()
    if not text or not text.isalnum() or len(text) not in {4, 5}:
        raise ValueError("invalid symbol identity")
    return text


def _finite_float(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("non-finite score") from exc
    if not math.isfinite(result):
        raise ValueError("non-finite score")
    return result


def _int_rank(value: Any) -> int:
    try:
        rank = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid rank") from exc
    if rank < 1:
        raise ValueError("invalid rank")
    return rank


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


def _historical_empty_current_authority_ready(
    *,
    current: dict[str, Any],
    runtime_state: dict[str, Any],
    business_date: str,
) -> bool:
    positions = [item for item in current.get("positions") or () if float(item.get("quantity") or 0) > 0]
    if positions:
        return False
    if str(current.get("environment") or "") != "historical":
        return False
    if not bool(current.get("current_state_confirmed_empty")):
        return False
    if str(runtime_state.get("business_date") or "") != business_date:
        return False
    if str(runtime_state.get("state") or "") != "CURRENT_STATE_LOADED":
        return False
    if str(runtime_state.get("environment") or runtime_state.get("runtime_mode") or "") != "historical":
        return False
    return True


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


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _runtime_adapter_source_identity(path: Path, *, repo_root: Path) -> dict[str, str]:
    source = path.resolve()
    if not source.is_file():
        raise RuntimeArtifactLookupHalt(f"{PM_RUNTIME_ADAPTER_AUTHORITY_MISMATCH}: executing source file missing: {source}")
    relative = _canonical_repo_relative_path(source, repo_root=repo_root, label="executing source")
    return {
        "repo_relative_path": relative,
        "content_hash": _sha256_file(source),
    }


def _canonical_repo_relative_path(path: Path, *, repo_root: Path, label: str) -> str:
    if path == Path(".") or str(path).strip() in {"", "."}:
        raise RuntimeArtifactLookupHalt(f"{PM_RUNTIME_ADAPTER_AUTHORITY_MISMATCH}: {label} cannot be empty or '.'")
    if path.is_absolute():
        try:
            relative = path.resolve().relative_to(repo_root.resolve())
        except ValueError as exc:
            raise RuntimeArtifactLookupHalt(
                f"{PM_RUNTIME_ADAPTER_AUTHORITY_MISMATCH}: {label} is outside repository root: {path}"
            ) from exc
    else:
        relative = path
    if any(part in {"", ".", ".."} for part in relative.parts):
        raise RuntimeArtifactLookupHalt(f"{PM_RUNTIME_ADAPTER_AUTHORITY_MISMATCH}: {label} must be a repository-relative artifact path")
    return relative.as_posix()


def _runtime_source_repo_root(repo_root: Path | str | None) -> Path:
    if repo_root is not None:
        return Path(repo_root).resolve()
    return Path(__file__).resolve().parents[4]


def _validate_pm_adapter_resolver_result(resolver_result: dict[str, Any]) -> None:
    if not resolver_result:
        return
    schema_version = resolver_result.get("schema_version")
    if schema_version not in {None, "artifact_registry_resolver_result.v1"}:
        raise RuntimeArtifactLookupHalt(f"{PM_RUNTIME_ADAPTER_AUTHORITY_MISMATCH}: unsupported resolver schema_version: {schema_version}")
    members = resolver_result.get("members")
    if members is None:
        return
    adapter_members = [
        member
        for member in members
        if str(member.get("member_role") or member.get("role") or "") == "RUNTIME_ADAPTER"
    ]
    if len(adapter_members) != 1:
        raise RuntimeArtifactLookupHalt(
            f"{PM_RUNTIME_ADAPTER_AUTHORITY_MISMATCH}: expected exactly one RUNTIME_ADAPTER authority, found {len(adapter_members)}"
        )


def _raw_member_for_role(resolver_result: dict[str, Any], role: str) -> dict[str, Any]:
    for member in resolver_result.get("members") or []:
        if str(member.get("member_role") or member.get("role") or "") == role:
            return dict(member)
    return {}


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _reject_mode_rooted_runtime_root(root: Path) -> None:
    text = str(root)
    if text.endswith("/demo") or "/demo/" in text:
        raise ValueError("mode-rooted Current path is not allowed")
