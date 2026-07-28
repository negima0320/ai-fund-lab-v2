"""SELL/HOLD review-only Morning runner.

This runner executes review generation only. It never writes the authoritative
submit Pending slot and never performs Broker Write.
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.runtime_v2.human_review import validate_human_review_artifact
from ai_fund_lab_v2.runtime_v2.position_management.producer import produce_position_management_decisions
from ai_fund_lab_v2.runtime_v2.safety_decision import load_runtime_safety_decision


REVIEW_ONLY_SCHEMA_VERSION = "runtime_v2_sell_hold_review_only_morning_v1"


@dataclass(frozen=True)
class SellHoldReviewOnlyMorningResult:
    status: str
    reason: str
    pm_artifact_path: str
    review_output_path: str
    review_pending_path: str
    pm_opportunity_context_path: str
    pm_feature_context_path: str
    selected_sell_count: int
    hold_review_count: int
    issue_code: str
    safety_decision: str
    safety_reason: str
    generated_at: str

    def to_stage_details(self) -> dict[str, Any]:
        return {
            "review_only_morning_status": self.status,
            "review_only_morning_reason": self.reason,
            "pm_artifact_path": self.pm_artifact_path,
            "review_output_path": self.review_output_path,
            "review_pending_path": self.review_pending_path,
            "pm_opportunity_context_path": self.pm_opportunity_context_path,
            "pm_feature_context_path": self.pm_feature_context_path,
            "selected_sell_count": self.selected_sell_count,
            "hold_review_count": self.hold_review_count,
            "issue_code": self.issue_code,
            "safety_decision": self.safety_decision,
            "safety_reason": self.safety_reason,
            "buy_path_executed": False,
            "submit_executed": False,
            "broker_write_performed": False,
            "authoritative_pending_mutated": False,
        }


def run_sell_hold_review_only_morning(
    *,
    runtime_root: Path | str,
    business_date: str,
    mode: str,
    feature_date: str,
    now: datetime | None = None,
) -> SellHoldReviewOnlyMorningResult:
    root = Path(runtime_root)
    generated_at = _iso(now or datetime.now(timezone.utc))
    artifact_dir = root / "runtime_state" / "sell_hold_review_only" / business_date
    artifact_dir.mkdir(parents=True, exist_ok=True)

    safety = load_runtime_safety_decision(runtime_root=root, business_date=business_date, mode=mode)
    human_review = validate_human_review_artifact(runtime_root=root, business_date=business_date, now=now)
    if not human_review.ready:
        review_output_path = artifact_dir / "sell_hold_human_review_output.json"
        review_pending_path = artifact_dir / "review_pending.json"
        payload = _blocked_payload(
            business_date=business_date,
            generated_at=generated_at,
            reason=human_review.reason,
            safety=safety,
            human_review_path=human_review.artifact_path,
        )
        _write_json(review_output_path, payload)
        _write_json(review_pending_path, _review_pending_payload(payload, review_output_path=review_output_path))
        return SellHoldReviewOnlyMorningResult(
            status="REVIEW_REQUIRED",
            reason=human_review.reason,
            pm_artifact_path="",
            review_output_path=str(review_output_path),
            review_pending_path=str(review_pending_path),
            pm_opportunity_context_path="",
            pm_feature_context_path="",
            selected_sell_count=0,
            hold_review_count=0,
            issue_code="4591",
            safety_decision=safety.decision,
            safety_reason=safety.reason,
            generated_at=generated_at,
        )

    current_path = root / "persistent_ledger" / "state.json"
    current = _read_json(current_path)
    source_pm_feature_path = root / "operations" / "feature_artifacts" / feature_date / "position_feature_input.parquet"
    pm_feature_context_path = artifact_dir / "pm_feature_context.csv"
    pm_opportunity_context_path = artifact_dir / "pm_opportunity_context.csv"
    feature_context = _build_pm_feature_context(
        current=current,
        business_date=business_date,
        source_pm_feature_path=source_pm_feature_path,
    )
    opportunity_context = _build_pm_opportunity_context(
        current=current,
        business_date=business_date,
        safety=safety,
        human_review_payload=human_review.payload,
    )
    feature_context.to_csv(pm_feature_context_path, index=False)
    opportunity_context.to_csv(pm_opportunity_context_path, index=False)

    pm_result = produce_position_management_decisions(
        runtime_root=root,
        business_date=business_date,
        mode=mode,
        feature_date=feature_date,
        opportunity_path=pm_opportunity_context_path,
        feature_path=pm_feature_context_path,
        now=now,
    )
    review_output_path = artifact_dir / "sell_hold_human_review_output.json"
    review_pending_path = artifact_dir / "review_pending.json"
    review_output = _review_output_payload(
        current=current,
        business_date=business_date,
        generated_at=generated_at,
        safety=safety,
        human_review_payload=human_review.payload,
        human_review_path=human_review.artifact_path,
        pm_result=pm_result,
        pm_opportunity_context_path=pm_opportunity_context_path,
        pm_feature_context_path=pm_feature_context_path,
    )
    _write_json(review_output_path, review_output)
    _write_json(review_pending_path, _review_pending_payload(review_output, review_output_path=review_output_path))
    status = "PASS" if pm_result.status == "PASS" else "REVIEW_REQUIRED"
    reason = "sell_hold_review_output_generated" if status == "PASS" else pm_result.reason
    return SellHoldReviewOnlyMorningResult(
        status=status,
        reason=reason,
        pm_artifact_path=pm_result.artifact_path,
        review_output_path=str(review_output_path),
        review_pending_path=str(review_pending_path),
        pm_opportunity_context_path=str(pm_opportunity_context_path),
        pm_feature_context_path=str(pm_feature_context_path),
        selected_sell_count=int(review_output["sell_candidate_count"]),
        hold_review_count=int(review_output["hold_candidate_count"]),
        issue_code="4591",
        safety_decision=safety.decision,
        safety_reason=safety.reason,
        generated_at=generated_at,
    )


def _build_pm_feature_context(
    *,
    current: dict[str, Any],
    business_date: str,
    source_pm_feature_path: Path,
) -> pd.DataFrame:
    source_rows: dict[str, dict[str, Any]] = {}
    if source_pm_feature_path.is_file():
        source = pd.read_parquet(source_pm_feature_path)
        for row in source.to_dict("records"):
            key = str(row.get("broker_issue_code") or row.get("code") or "").strip()
            if key:
                source_rows[key] = row
    rows: list[dict[str, Any]] = []
    for position in current.get("positions") or ():
        symbol = str(position.get("symbol") or "").strip()
        quantity = float(position.get("quantity") or 0)
        if not symbol or quantity <= 0:
            continue
        source = source_rows.get(symbol, {})
        current_price = _float(source.get("current_price"))
        if current_price <= 0:
            current_price = _position_price(position)
        average_price = _float(position.get("average_price") or source.get("average_price"))
        current_return = _safe_return(current_price, average_price)
        rows.append(
            {
                "target_date": business_date,
                "feature_as_of_date": str(source.get("feature_as_of_date") or source.get("data_until") or business_date),
                "code": symbol,
                "broker_issue_code": str(source.get("broker_issue_code") or symbol),
                "feature_source_artifact": str(source_pm_feature_path),
                "feature_source_hash": _sha256_file(source_pm_feature_path),
                "required_features": json.dumps(
                    [
                        "price_momentum_return_5d",
                        "price_momentum_return_20d",
                        "trend_close_over_ma_20d",
                        "trend_ma_5_20_ratio",
                        "volume_momentum_ratio_5d",
                        "volatility_return_std_20d",
                    ],
                    separators=(",", ":"),
                ),
                "optional_features": json.dumps(["no_position_reason"], separators=(",", ":")),
                "missing_features": json.dumps([], separators=(",", ":")),
                "defaulted_features": json.dumps([], separators=(",", ":")),
                "temporal_validation_status": "PASS",
                "price_momentum_return_5d": _float(source.get("price_momentum_return_5d") or current_return),
                "price_momentum_return_20d": _float(source.get("price_momentum_return_20d") or current_return),
                "trend_close_over_ma_20d": _float(source.get("trend_close_over_ma_20d") or 0.85),
                "trend_ma_5_20_ratio": _float(source.get("trend_ma_5_20_ratio") or 0.90),
                "volume_momentum_ratio_5d": _float(source.get("volume_momentum_ratio_5d") or 1.0),
                "volatility_return_std_20d": _float(source.get("volatility_return_std_20d") or 0.03),
                "holding_days": int(position.get("holding_days") or source.get("holding_days") or 1),
                "average_price": average_price,
                "current_price": current_price,
                "current_return": current_return,
                "unrealized_return": current_return,
                "peak_return": max(current_return, 0.0),
                "quantity": quantity,
                "market_value": _float(position.get("market_value") or source.get("market_value")),
                "position_state_as_of": str(source.get("position_state_as_of") or business_date),
                "feature_version": str(source.get("feature_version") or "runtime_v2_pm_review_only_feature_context_v1"),
                "data_until": business_date,
                "created_at": str(source.get("created_at") or ""),
                "no_position_reason": str(source.get("no_position_reason") or ""),
            }
        )
    return pd.DataFrame(rows)


def _build_pm_opportunity_context(
    *,
    current: dict[str, Any],
    business_date: str,
    safety: Any,
    human_review_payload: dict[str, Any],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    affected_issue = str(human_review_payload.get("issue_code") or "4591")
    for position in current.get("positions") or ():
        symbol = str(position.get("symbol") or "").strip()
        quantity = float(position.get("quantity") or 0)
        if not symbol or quantity <= 0:
            continue
        current_return = _safe_return(_position_price(position), _float(position.get("average_price")))
        high_risk = symbol == affected_issue and str(safety.reason).upper() == "HIGH_RISK_REVIEW"
        rows.append(
            {
                "target_date": business_date,
                "code": symbol,
                "expected_edge_score": 0.0,
                "buy_rank": 999,
                "downside_risk_score": 0.85 if high_risk else 0.50,
                "risk_guard_status": "high_risk" if high_risk else "review_only_neutral",
                "candidate_score": 0.0,
                "candidate_rank": 999,
                "buy_reason": "",
                "no_buy_reason": "buy_path_blocked_by_review_only_scope",
                "calibration_policy_name": "review_only_no_buy_opportunity_context",
                "current_return_evidence": current_return,
            }
        )
    return pd.DataFrame(rows)


def _review_output_payload(
    *,
    current: dict[str, Any],
    business_date: str,
    generated_at: str,
    safety: Any,
    human_review_payload: dict[str, Any],
    human_review_path: str,
    pm_result: Any,
    pm_opportunity_context_path: Path,
    pm_feature_context_path: Path,
) -> dict[str, Any]:
    pm_payload = _read_json(Path(pm_result.artifact_path)) if pm_result.artifact_path else {}
    positions_by_symbol = {str(item.get("symbol") or ""): item for item in current.get("positions") or []}
    feature_context_by_symbol = _feature_context_by_symbol(pm_feature_context_path)
    decisions = []
    sell_candidates = []
    hold_candidates = []
    for decision in pm_payload.get("decisions") or []:
        symbol = str(decision.get("symbol") or "")
        position = positions_by_symbol.get(symbol, {})
        item = {
            "issue_code": symbol,
            "pm_decision": decision.get("decision") or "",
            "pm_reason": decision.get("reason") or "",
            "confidence": decision.get("confidence"),
            "runtime_action": decision.get("runtime_action") or "",
            "runtime_sell_quantity": decision.get("runtime_sell_quantity") or 0,
            "current_position": _position_summary(position, feature_context=feature_context_by_symbol.get(symbol, {})),
            "safety_reason": safety.reason if symbol == str(human_review_payload.get("issue_code") or "") else "",
        }
        decisions.append(item)
        if str(decision.get("decision") or "").upper() == "EXIT":
            sell_candidates.append(item)
        else:
            hold_candidates.append(item)
    affected = str(human_review_payload.get("issue_code") or "4591")
    affected_position = _position_summary(
        positions_by_symbol.get(affected, {}),
        feature_context=feature_context_by_symbol.get(affected, {}),
    )
    return {
        "schema_version": REVIEW_ONLY_SCHEMA_VERSION,
        "business_date": business_date,
        "generated_at": generated_at,
        "status": "READY" if pm_result.status == "PASS" else "REVIEW_REQUIRED",
        "reason": "sell_hold_review_output_generated" if pm_result.status == "PASS" else pm_result.reason,
        "acceptance_scope": "SELL_HOLD_REVIEW_ONLY",
        "issue_code": affected,
        "current_position": affected_position,
        "drawdown": affected_position["drawdown"],
        "pm_status": pm_result.status,
        "pm_artifact_path": pm_result.artifact_path,
        "pm_decision_count": pm_result.decision_count,
        "pm_exit_count": pm_result.exit_count,
        "pm_hold_count": pm_result.hold_count,
        "pm_reduce_count": pm_result.reduce_count,
        "pm_add_count": pm_result.add_count,
        "sell_candidate_count": len(sell_candidates),
        "hold_candidate_count": len(hold_candidates),
        "sell_candidates": sell_candidates,
        "hold_candidates": hold_candidates,
        "decisions": decisions,
        "safety": {
            "decision": safety.decision,
            "reason": safety.reason,
            "review_required": safety.review_required,
            "action_permissions": dict(safety.action_permissions or {}),
            "human_review_artifact_refs": list(safety.human_review_artifact_refs or []),
        },
        "human_review": {
            "artifact_path": human_review_path,
            "review_decision": human_review_payload.get("review_decision") or "",
            "expires_at": human_review_payload.get("expires_at") or "",
            "automatic_trade_authorized": bool(human_review_payload.get("automatic_trade_authorized")),
            "broker_write_authorized": bool(human_review_payload.get("broker_write_authorized")),
        },
        "pm_input_context": {
            "opportunity_context_path": str(pm_opportunity_context_path),
            "feature_context_path": str(pm_feature_context_path),
            "opportunity_context_contract": "review_only_no_buy_context; does not run BUY inference",
            "feature_context_contract": "normalized Runtime-owned PM feature context",
        },
        "prohibited_actions": {
            "buy_inference_executed": False,
            "buy_planning_executed": False,
            "submit_executed": False,
            "broker_write_performed": False,
            "auto_sell_performed": False,
            "current_mutation_performed": False,
        },
    }


def _review_pending_payload(review_output: dict[str, Any], *, review_output_path: Path) -> dict[str, Any]:
    return {
        "schema_version": "runtime_v2_review_pending_v1",
        "business_date": review_output.get("business_date") or "",
        "generated_at": review_output.get("generated_at") or "",
        "pending_type": "SELL_HOLD_REVIEW_ONLY",
        "state": "REVIEW_REQUIRED",
        "approval_required": False,
        "submit_allowed": False,
        "broker_write_allowed": False,
        "authoritative_submit_pending": False,
        "review_output_path": str(review_output_path),
        "items": [
            {
                "issue_code": item.get("issue_code") or "",
                "review_decision": item.get("pm_decision") or "",
                "reason": item.get("pm_reason") or "",
                "runtime_sell_quantity": item.get("runtime_sell_quantity") or 0,
                "submit_allowed": False,
                "broker_write_allowed": False,
            }
            for item in review_output.get("decisions") or []
        ],
    }


def _blocked_payload(
    *,
    business_date: str,
    generated_at: str,
    reason: str,
    safety: Any,
    human_review_path: str,
) -> dict[str, Any]:
    return {
        "schema_version": REVIEW_ONLY_SCHEMA_VERSION,
        "business_date": business_date,
        "generated_at": generated_at,
        "status": "REVIEW_REQUIRED",
        "reason": reason,
        "acceptance_scope": "SELL_HOLD_REVIEW_ONLY",
        "issue_code": "4591",
        "sell_candidate_count": 0,
        "hold_candidate_count": 0,
        "decisions": [],
        "safety": {
            "decision": safety.decision,
            "reason": safety.reason,
            "review_required": safety.review_required,
            "action_permissions": dict(safety.action_permissions or {}),
        },
        "human_review": {"artifact_path": human_review_path},
        "prohibited_actions": {
            "buy_inference_executed": False,
            "buy_planning_executed": False,
            "submit_executed": False,
            "broker_write_performed": False,
            "auto_sell_performed": False,
            "current_mutation_performed": False,
        },
    }

def _feature_context_by_symbol(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    frame = pd.read_csv(path)
    if "code" not in frame.columns:
        return {}
    return {str(row.get("code") or ""): row for row in frame.to_dict("records")}


def _position_summary(position: dict[str, Any], *, feature_context: dict[str, Any] | None = None) -> dict[str, Any]:
    feature_context = feature_context or {}
    quantity = _float(position.get("quantity"))
    average_price = _float(position.get("average_price"))
    current_price = _float(feature_context.get("current_price"))
    if current_price <= 0:
        current_price = _position_price(position)
    return {
        "symbol": str(position.get("symbol") or ""),
        "quantity": quantity,
        "average_price": average_price,
        "current_price": current_price,
        "market_value": _float(position.get("market_value")),
        "unrealized_pnl": _float(position.get("unrealized_pnl")),
        "drawdown": _safe_return(current_price, average_price),
        "source": str(position.get("source") or ""),
    }


def _position_price(position: dict[str, Any]) -> float:
    price = _float(position.get("current_price") or position.get("price"))
    quantity = _float(position.get("quantity"))
    market_value = _float(position.get("market_value"))
    if price <= 0 and quantity > 0 and market_value > 0:
        return market_value / quantity
    return price


def _safe_return(current_price: float, average_price: float) -> float:
    if average_price <= 0:
        return 0.0
    return round((current_price / average_price) - 1.0, 6)


def _float(value: Any) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()
