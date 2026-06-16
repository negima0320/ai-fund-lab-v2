from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from pathlib import Path

from ai_fund_lab_v2.order_manager.allocation_decision_loader import AllocationDecision, AllocationDecisionSet


class Phase7ArtifactLoadError(RuntimeError):
    pass


@dataclass(frozen=True)
class Phase7ArtifactConnection:
    final_summary_path: str
    decision_artifact_path: str
    primary_policy: str
    shadow_policies: tuple[str, ...]
    completion_status: str
    allocation: AllocationDecisionSet
    warnings: tuple[str, ...] = ()


def discover_phase7_artifact_paths(root_dir: Path | str = ".") -> dict[str, Path]:
    root = Path(root_dir)
    return {
        "final_summary": root / "reports" / "capital_allocation_ai" / "phase7_final" / "phase7_final_summary.json",
        "decision_artifact": root / "reports" / "capital_allocation_ai" / "phase7a" / "capital_allocation_decisions.csv",
    }


def load_phase7_artifact_connection(root_dir: Path | str = ".") -> Phase7ArtifactConnection:
    paths = discover_phase7_artifact_paths(root_dir)
    final_summary = paths["final_summary"]
    decision_artifact = paths["decision_artifact"]
    if not final_summary.exists():
        raise Phase7ArtifactLoadError(f"Phase7 final summary missing: {final_summary}")
    if not decision_artifact.exists():
        raise Phase7ArtifactLoadError(f"Phase7 decision artifact missing: {decision_artifact}")
    summary_payload = _read_summary(final_summary)
    primary_policy = str(summary_payload.get("primary_policy") or "")
    conservative = str(summary_payload.get("conservative_policy") or "")
    weak = str(summary_payload.get("weak_regime_comparison_policy") or "")
    if primary_policy != "CAP5" or conservative != "CAP4" or weak != "POLICY_Y_CAP4_EDGE08_CONF5":
        raise Phase7ArtifactLoadError("Phase7 policy handoff does not match CAP5/CAP4/POLICY_Y expectations.")
    allocation, warnings = _load_phase7a_csv(decision_artifact)
    return Phase7ArtifactConnection(
        final_summary_path=str(final_summary),
        decision_artifact_path=str(decision_artifact),
        primary_policy=primary_policy,
        shadow_policies=(conservative, weak),
        completion_status=str(summary_payload.get("phase7_completion_status") or ""),
        allocation=allocation,
        warnings=warnings,
    )


def _read_summary(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Phase7ArtifactLoadError(f"Phase7 final summary invalid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise Phase7ArtifactLoadError("Phase7 final summary must be an object.")
    return payload


def _load_phase7a_csv(path: Path) -> tuple[AllocationDecisionSet, tuple[str, ...]]:
    decisions: list[AllocationDecision] = []
    warnings: list[str] = []
    required = {"target_date", "code", "action", "current_position_value", "target_position_value", "buy_amount", "sell_amount"}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise Phase7ArtifactLoadError("Phase7 decision artifact schema is unexpected.")
        for index, row in enumerate(reader, start=1):
            side = _normalize_action(str(row.get("action") or ""))
            if side is None:
                warnings.append(f"skipped review-only action at row {index}: {row.get('action')}")
                continue
            value = _decision_value(row, side)
            quantity = _lot_quantity(value)
            if quantity <= 0:
                warnings.append(f"skipped zero-value decision at row {index}: {row.get('code')}")
                continue
            estimated_price = (value / quantity).quantize(Decimal("0.0001")) if value > 0 else Decimal("0")
            decisions.append(
                AllocationDecision(
                    decision_id=f"phase7a_{index}",
                    issue_code=str(row.get("code") or ""),
                    side=side,
                    action=f"PHASE7_{side}",
                    quantity=quantity,
                    estimated_price=estimated_price,
                    reason_code=str(row.get("replacement_reason") or row.get("defensive_reason") or row.get("emergency_reason") or ""),
                )
            )
    if not decisions:
        raise Phase7ArtifactLoadError("Phase7 decision artifact produced no Phase8-compatible decisions.")
    return (
        AllocationDecisionSet(
            policy_id="CAP5",
            decisions=tuple(decisions),
            source_path=str(path),
            cash_buffer_ratio=Decimal("0.05"),
            max_position_weight=Decimal("0.20"),
            lot_size=100,
            settlement="conservative_T2_cash_unavailable",
            shadow_policies=("CAP4", "POLICY_Y_CAP4_EDGE08_CONF5"),
        ),
        tuple(warnings),
    )


def _normalize_action(action: str) -> str | None:
    normalized = action.upper()
    if normalized in {"BUY", "REPLACE_BUY"}:
        return "BUY"
    if normalized in {"SELL", "REPLACE_SELL", "EMERGENCY_EXIT"}:
        return "SELL"
    if normalized == "HOLD":
        return "HOLD"
    if normalized in {"DEFENSIVE_REVIEW", "SKIP", "NO_ACTION"}:
        return None
    raise Phase7ArtifactLoadError(f"Unexpected Phase7 action: {action}")


def _decision_value(row: dict[str, str], side: str) -> Decimal:
    if side == "BUY":
        return _decimal(row.get("buy_amount")) or _decimal(row.get("target_position_value"))
    if side == "SELL":
        return _decimal(row.get("sell_amount")) or _decimal(row.get("current_position_value"))
    return _decimal(row.get("target_position_value")) or _decimal(row.get("current_position_value"))


def _lot_quantity(value: Decimal) -> Decimal:
    if value <= 0:
        return Decimal("0")
    lots = (value / Decimal("100000")).to_integral_value(rounding=ROUND_DOWN)
    if lots <= 0:
        lots = Decimal("1")
    return lots * Decimal("100")


def _decimal(value: object) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value).replace(",", ""))
