from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.paper_trading.daily_run_result import DailyCandidate, DailyRunResult


READY = "READY"
SKIPPED = "SKIPPED"
BLOCKED = "BLOCKED"
INVALID = "INVALID"


@dataclass(frozen=True)
class ArtifactReadStatus:
    name: str
    status: str
    path: str = ""
    row_count: int = 0
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AIArtifactIntegrationResult:
    status: str
    daily_result: DailyRunResult
    artifact_statuses: tuple[ArtifactReadStatus, ...]
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "daily_result": self.daily_result.to_dict(),
            "artifact_statuses": [status.to_dict() for status in self.artifact_statuses],
            "warnings": list(self.warnings),
            "blocked_reasons": list(self.blocked_reasons),
        }


@dataclass(frozen=True)
class AIArtifactPaths:
    candidate_artifact: Path | None = None
    opportunity_artifact: Path | None = None
    position_artifact: Path | None = None
    allocation_artifact: Path | None = None
    order_plan_artifact: Path | None = None


def adapt_ai_artifacts(
    *,
    decision_for: str,
    data_until: str,
    paths: AIArtifactPaths,
) -> AIArtifactIntegrationResult:
    statuses: list[ArtifactReadStatus] = []
    warnings: list[str] = []
    blocked: list[str] = []
    buy: list[DailyCandidate] = []
    sell: list[DailyCandidate] = []
    hold: list[DailyCandidate] = []
    artifact_state: dict[str, Any] = {}

    candidate_rows, status = _read_rows("candidate", paths.candidate_artifact)
    statuses.append(status)
    if candidate_rows:
        candidate_status = _validate_dates("candidate", candidate_rows, decision_for=decision_for, data_until=data_until)
        if candidate_status:
            statuses.append(candidate_status)
            blocked.extend(candidate_status.blocked_reasons)
        artifact_state["candidate_count"] = len(candidate_rows)

    opportunity_rows, status = _read_rows("opportunity", paths.opportunity_artifact)
    statuses.append(status)
    if opportunity_rows:
        opportunity_status = _validate_dates("opportunity", opportunity_rows, decision_for=decision_for, data_until=data_until)
        if opportunity_status:
            statuses.append(opportunity_status)
            blocked.extend(opportunity_status.blocked_reasons)
        for row in sorted(opportunity_rows, key=lambda item: _int_value(item, "rank", "buy_rank", default=999))[:10]:
            buy.append(_candidate_from_row(row, side="BUY", score_keys=("public_confidence_score", "opportunity_score", "expected_edge_score")))

    position_rows, status = _read_rows("position", paths.position_artifact)
    statuses.append(status)
    if position_rows:
        position_status = _validate_dates("position", position_rows, decision_for=decision_for, data_until=data_until)
        if position_status:
            statuses.append(position_status)
            blocked.extend(position_status.blocked_reasons)
        for row in position_rows:
            action = str(row.get("action") or row.get("position_signal") or "").upper()
            candidate = _candidate_from_row(row, side="SELL" if action in {"EXIT", "REDUCE"} else "HOLD", score_keys=("public_confidence_score", "position_score"))
            if action in {"EXIT", "REDUCE"}:
                sell.append(candidate)
            elif action == "HOLD":
                hold.append(candidate)

    allocation_rows, status = _read_rows("allocation", paths.allocation_artifact)
    statuses.append(status)
    if allocation_rows:
        artifact_state["allocation_decision_count"] = len(allocation_rows)
        for row in allocation_rows:
            _apply_allocation_to_candidates(row, buy=buy, sell=sell, hold=hold)

    order_plan_rows, status = _read_order_plan(paths.order_plan_artifact)
    statuses.append(status)
    if status.status == INVALID:
        blocked.extend(status.blocked_reasons)
    elif order_plan_rows:
        artifact_state["order_plan_item_count"] = len(order_plan_rows)
        for row in order_plan_rows:
            side = str(row.get("side") or "").upper()
            candidate = _candidate_from_row(row, side=side, score_keys=("public_confidence_score",))
            if side == "BUY":
                buy.append(candidate)
            elif side == "SELL":
                sell.append(candidate)
            elif side == "HOLD":
                hold.append(candidate)

    missing = [status.name for status in statuses if status.status == SKIPPED and status.name in {"candidate", "opportunity", "position", "allocation", "order_plan"}]
    if missing:
        warnings.append(f"artifact_missing={','.join(sorted(missing))}")
    blocked.extend(reason for status in statuses for reason in status.blocked_reasons)
    overall = INVALID if any(status.status == INVALID for status in statuses) else (BLOCKED if blocked else READY)
    if missing and overall != INVALID and not buy and not sell and not hold:
        overall = BLOCKED
        hold.append(
            DailyCandidate(
                issue_code="",
                side="HOLD",
                public_confidence_score=25,
                short_reason="本日は判断材料不足です。",
                caution_note="artifact missingのため仮想注文は作成していません。",
                reason="artifact_missing",
            )
        )
    result = DailyRunResult(
        buy_candidates=tuple(buy),
        sell_candidates=tuple(sell),
        hold_candidates=tuple(hold),
        artifact_state={
            **artifact_state,
            "artifact_statuses": [status.to_dict() for status in statuses],
            "integration_status": overall,
        },
        safety_state={"status": "OK" if overall == READY else overall, "blocked_reasons": blocked},
        review_state={"status": "pending" if overall == READY else "review_only"},
    )
    return AIArtifactIntegrationResult(
        status=overall,
        daily_result=result,
        artifact_statuses=tuple(statuses),
        warnings=tuple(warnings),
        blocked_reasons=tuple(dict.fromkeys(blocked)),
    )


def _read_rows(name: str, path: Path | None) -> tuple[list[dict[str, Any]], ArtifactReadStatus]:
    if path is None:
        return [], ArtifactReadStatus(name=name, status=SKIPPED, blocked_reasons=(f"{name}_artifact_missing",))
    if not path.is_file():
        return [], ArtifactReadStatus(name=name, status=SKIPPED, path=str(path), blocked_reasons=(f"{name}_artifact_missing",))
    try:
        rows = _load_table(path)
    except (OSError, json.JSONDecodeError, csv.Error) as exc:
        return [], ArtifactReadStatus(name=name, status=INVALID, path=str(path), blocked_reasons=(f"{name}_artifact_unreadable:{type(exc).__name__}",))
    return rows, ArtifactReadStatus(name=name, status=READY, path=str(path), row_count=len(rows))


def _read_order_plan(path: Path | None) -> tuple[list[dict[str, Any]], ArtifactReadStatus]:
    rows, status = _read_rows("order_plan", path)
    if status.status != READY:
        return rows, status
    payload = _load_json(path) if path and path.suffix.lower() == ".json" else {"items": rows}
    if isinstance(payload, list):
        payload = {"items": payload}
    if not isinstance(payload, dict):
        return [], ArtifactReadStatus(name="order_plan", status=INVALID, path=str(path), blocked_reasons=("order_plan_schema_invalid",))
    blocked: list[str] = []
    if bool(payload.get("executable")):
        blocked.append("order_plan_executable_true")
    if bool(payload.get("live_order_allowed")):
        blocked.append("order_plan_live_order_allowed_true")
    if not bool(payload.get("requires_human_review", True)):
        blocked.append("order_plan_requires_human_review_false")
    items = payload.get("items") or payload.get("order_items") or rows
    if not isinstance(items, list):
        blocked.append("order_plan_items_invalid")
        items = []
    if blocked:
        return [], ArtifactReadStatus(name="order_plan", status=INVALID, path=str(path), row_count=0, blocked_reasons=tuple(blocked))
    return [dict(item) for item in items if isinstance(item, dict)], ArtifactReadStatus(name="order_plan", status=READY, path=str(path), row_count=len(items))


def _load_table(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    payload = _load_json(path)
    if isinstance(payload, list):
        return [dict(item) for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("rows", "candidates", "decisions", "items", "order_items"):
            if isinstance(payload.get(key), list):
                return [dict(item) for item in payload[key] if isinstance(item, dict)]
        return [payload]
    return []


def _load_json(path: Path | None) -> Any:
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_dates(name: str, rows: list[Mapping[str, Any]], *, decision_for: str, data_until: str) -> ArtifactReadStatus | None:
    blocked: list[str] = []
    for row in rows:
        row_decision = str(row.get("decision_for") or row.get("target_date") or row.get("run_date") or "")
        row_data_until = str(row.get("data_until") or row.get("as_of_date") or "")
        if row_decision and row_decision != decision_for:
            blocked.append(f"{name}_decision_for_mismatch")
        if row_data_until and row_data_until > decision_for:
            blocked.append(f"{name}_future_data_until")
        elif row_data_until and row_data_until != data_until:
            # A stale artifact is blocked for Phase9-D; later phases may allow explicit catch-up runs.
            blocked.append(f"{name}_data_until_mismatch")
    if not blocked:
        return None
    return ArtifactReadStatus(name=f"{name}_date_validation", status=INVALID, row_count=len(rows), blocked_reasons=tuple(dict.fromkeys(blocked)))


def _candidate_from_row(row: Mapping[str, Any], *, side: str, score_keys: tuple[str, ...]) -> DailyCandidate:
    score = _score(row, score_keys)
    return DailyCandidate(
        issue_code=str(row.get("issue_code") or row.get("symbol") or row.get("code") or ""),
        issue_name=str(row.get("issue_name") or row.get("name") or ""),
        side=side,
        rank=_optional_int(row.get("rank") or row.get("buy_rank") or row.get("candidate_rank")),
        planned_quantity=_decimal(row.get("quantity") or row.get("planned_quantity")),
        planned_amount=_decimal(row.get("planned_amount") or row.get("estimated_value") or row.get("buy_amount") or row.get("sell_amount")),
        public_confidence_score=score,
        short_reason=str(row.get("short_reason") or row.get("reason") or row.get("buy_reason") or row.get("action_reason") or row.get("reason_code") or ""),
        caution_note=str(row.get("caution_note") or "仮想運用での検証中です。"),
        reason=str(row.get("reason") or row.get("validation_notes") or row.get("reason_code") or ""),
    )


def _apply_allocation_to_candidates(row: Mapping[str, Any], *, buy: list[DailyCandidate], sell: list[DailyCandidate], hold: list[DailyCandidate]) -> None:
    side = str(row.get("side") or row.get("action") or "").upper()
    if side in {"BUY", "REPLACE_BUY"}:
        buy.append(_candidate_from_row(row, side="BUY", score_keys=("public_confidence_score", "expected_edge_score")))
    elif side in {"SELL", "REPLACE_SELL", "EMERGENCY_EXIT"}:
        sell.append(_candidate_from_row(row, side="SELL", score_keys=("public_confidence_score", "expected_edge_score")))
    elif side == "HOLD":
        hold.append(_candidate_from_row(row, side="HOLD", score_keys=("public_confidence_score", "expected_edge_score")))


def _score(row: Mapping[str, Any], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        if row.get(key) in (None, ""):
            continue
        try:
            value = float(row[key])
        except (TypeError, ValueError):
            continue
        if 0 <= value <= 1:
            return max(0, min(100, int(round(value * 100))))
        return max(0, min(100, int(round(value))))
    return None


def _int_value(row: Mapping[str, Any], *keys: str, default: int) -> int:
    for key in keys:
        value = _optional_int(row.get(key))
        if value is not None:
            return value
    return default


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value).replace(",", ""))
