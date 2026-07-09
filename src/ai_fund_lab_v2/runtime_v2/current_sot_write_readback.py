"""Phase14-D22 Current SoT write/read-back helper."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.runtime_v2.asset.models import (
    CurrentAssetPosition,
    CurrentAssetState,
)
from ai_fund_lab_v2.runtime_v2.asset.writer import write_current_asset_state
from ai_fund_lab_v2.runtime_v2.audit.auditor import run_audit
from ai_fund_lab_v2.runtime_v2.broker_readonly.models import (
    BrokerCashSnapshot,
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
)
from ai_fund_lab_v2.runtime_v2.current_state.reader import read_current_state
from ai_fund_lab_v2.runtime_v2.current_state.writer import write_runtime_state
from ai_fund_lab_v2.runtime_v2.ledger.models import (
    LedgerCashRecord,
    LedgerEventRecord,
    LedgerOrderRecord,
    LedgerPositionRecord,
)
from ai_fund_lab_v2.runtime_v2.ledger.writer import write_ledger_records
from ai_fund_lab_v2.runtime_v2.notification.payload import build_notification_payload
from ai_fund_lab_v2.runtime_v2.pending.reader import pending_order_plan_from_payload
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.reconcile.reconciler import run_reconciliation
from ai_fund_lab_v2.runtime_v2.report.builder import build_runtime_report
from ai_fund_lab_v2.runtime_v2.report.models import ReportBuildInput
from ai_fund_lab_v2.runtime_v2.storage.path_resolver import resolve_current_path


@dataclass(frozen=True)
class CurrentSotWriteReadbackResult:
    final_decision: str
    base_dir: str
    fixed_state_path: str
    mode_rooted_write_rejected: bool
    state_readback_classification: str
    orders_readback_classification: str
    executions_readback_classification: str
    positions_readback_classification: str
    cash_readback_classification: str
    events_readback_classification: str
    pending_readback_classification: str
    runtime_state_readback_classification: str
    after_position_7203_quantity: float
    cash: float
    buying_power: float
    reconciliation_findings: int
    report_created: bool
    audit_findings: int
    per_run_artifact_used_as_current: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_current_sot_write_readback_e2e(
    *,
    base_dir: Path,
    evidence_root: Path,
    mode: str = "demo",
    environment: str = "demo",
    business_date: str = "2026-07-07",
) -> CurrentSotWriteReadbackResult:
    asset_state = _asset_state_from_payload(_load_json(evidence_root / "asset_state" / "asset_state.json"))
    pending_plan = pending_order_plan_from_payload(
        _load_json(evidence_root / "pending_order_plan" / "pending_order_plan.json")
    )
    snapshot = _load_json(evidence_root / "broker_readonly_after" / "tachibana_demo_snapshot.json")
    event_payloads = _load_json(evidence_root / "ledger_events" / "phase14d15_sell_events.json").get("events") or []

    broker_orders = _broker_orders(snapshot, pending_plan_id=pending_plan.pending_plan_id)
    broker_positions = _broker_positions(snapshot)
    broker_cash = _broker_cash(snapshot)
    ledger_orders = _ledger_orders(
        broker_orders,
        pending_plan_id=pending_plan.pending_plan_id,
        linked_record_ids=pending_plan.consume.ledger_order_record_ids,
    )
    ledger_positions = _ledger_positions(asset_state)
    ledger_cash = (_ledger_cash(asset_state),)
    ledger_events = tuple(_ledger_event(event) for event in event_payloads)

    _assert_mode_rooted_current_write_is_rejected(base_dir=base_dir, asset_state=asset_state)

    write_current_asset_state(
        base_dir / resolve_current_path(mode, environment, "persistent_ledger_state"),
        asset_state,
    )
    write_ledger_records(
        base_dir / resolve_current_path(mode, environment, "persistent_ledger_orders"),
        ledger_orders,
    )
    write_ledger_records(
        base_dir / resolve_current_path(mode, environment, "persistent_ledger_executions"),
        (),
    )
    write_ledger_records(
        base_dir / resolve_current_path(mode, environment, "persistent_ledger_positions"),
        ledger_positions,
    )
    write_ledger_records(
        base_dir / resolve_current_path(mode, environment, "persistent_ledger_cash"),
        ledger_cash,
    )
    write_ledger_records(
        base_dir / resolve_current_path(mode, environment, "persistent_ledger_events"),
        ledger_events,
    )
    write_pending_order_plan(
        base_dir / resolve_current_path(mode, environment, "pending_order_plan"),
        pending_plan,
    )
    write_runtime_state(
        base_dir / resolve_current_path(mode, environment, "runtime_state"),
        {
            "schema_version": "1",
            "runtime_id": "runtime-v2-demo",
            "run_id": "phase14d22-current-sot-write-readback",
            "state": "CURRENT_STATE_LOADED",
            "environment": environment,
            "updated_at": asset_state.created_at,
        },
    )

    readbacks = {
        object_type: read_current_state(
            mode=mode,
            environment=environment,
            object_type=object_type,
            base_dir=base_dir,
        )
        for object_type in (
            "persistent_ledger_state",
            "persistent_ledger_orders",
            "persistent_ledger_executions",
            "persistent_ledger_positions",
            "persistent_ledger_cash",
            "persistent_ledger_events",
            "pending_order_plan",
            "runtime_state",
        )
    }

    reconciliation = run_reconciliation(
        mode=mode,
        environment=environment,
        business_date=business_date,
        pending_plan=pending_plan,
        ledger_orders=ledger_orders,
        ledger_executions=(),
        broker_orders=broker_orders,
        broker_executions=(),
        broker_positions=broker_positions,
        broker_cash=broker_cash,
        asset_state=asset_state,
    )
    report = build_runtime_report(
        ReportBuildInput(
            mode=mode,
            environment=environment,
            business_date=business_date,
            target_session_date=business_date,
            asset_state=asset_state,
            pending_plan=pending_plan,
            ledger_orders=ledger_orders,
            ledger_executions=(),
            ledger_positions=ledger_positions,
            ledger_cash_records=ledger_cash,
            broker_orders=broker_orders,
            broker_executions=(),
            broker_positions=broker_positions,
            broker_cash=broker_cash,
            reconciliation_result=reconciliation,
            review_events=ledger_events,
        )
    )
    notification_payload = build_notification_payload(
        report=report,
        channel="phase14d22_payload_only",
    )
    audit = run_audit(
        mode=mode,
        environment=environment,
        business_date=business_date,
        report=report,
        notification_payload=notification_payload,
        reconciliation_result=reconciliation,
        asset_state=asset_state,
    )

    position_7203 = next(
        (position.quantity for position in (asset_state.positions or ()) if position.symbol == "7203"),
        0.0,
    )
    final_decision = "PHASE14D22_CURRENT_SOT_WRITE_READBACK_PASS"
    if (
        any(result.classification not in {"VALID", "CONFIRMED_EMPTY"} for result in readbacks.values())
        or reconciliation.findings
        or audit.findings
        or position_7203 != 0.0
    ):
        final_decision = "PHASE14D22_REVIEW_REQUIRED"

    return CurrentSotWriteReadbackResult(
        final_decision=final_decision,
        base_dir=str(base_dir),
        fixed_state_path=str(base_dir / resolve_current_path(mode, environment, "persistent_ledger_state")),
        mode_rooted_write_rejected=True,
        state_readback_classification=readbacks["persistent_ledger_state"].classification,
        orders_readback_classification=readbacks["persistent_ledger_orders"].classification,
        executions_readback_classification=readbacks["persistent_ledger_executions"].classification,
        positions_readback_classification=readbacks["persistent_ledger_positions"].classification,
        cash_readback_classification=readbacks["persistent_ledger_cash"].classification,
        events_readback_classification=readbacks["persistent_ledger_events"].classification,
        pending_readback_classification=readbacks["pending_order_plan"].classification,
        runtime_state_readback_classification=readbacks["runtime_state"].classification,
        after_position_7203_quantity=position_7203,
        cash=float(asset_state.cash or 0),
        buying_power=float(asset_state.buying_power or 0),
        reconciliation_findings=len(reconciliation.findings),
        report_created=report is not None,
        audit_findings=len(audit.findings),
        per_run_artifact_used_as_current=False,
    )


def _asset_state_from_payload(payload: Mapping[str, Any]) -> CurrentAssetState:
    return CurrentAssetState(
        schema_version=str(payload["schema_version"]),
        asset_state_id=str(payload["asset_state_id"]),
        environment=str(payload["environment"]),
        source=str(payload["source"]),
        as_of=str(payload["as_of"]),
        positions=tuple(
            CurrentAssetPosition(
                symbol=str(position["symbol"]),
                quantity=float(position["quantity"]),
                average_price=float(position["average_price"]),
                market_value=float(position["market_value"]),
                source=str(position["source"]),
                as_of=str(position["as_of"]),
            )
            for position in (payload.get("positions") or ())
        ),
        cash=float(payload["cash"]) if payload.get("cash") is not None else None,
        buying_power=float(payload["buying_power"]) if payload.get("buying_power") is not None else None,
        market_value=float(payload["market_value"]) if payload.get("market_value") is not None else None,
        total_equity=float(payload["total_equity"]) if payload.get("total_equity") is not None else None,
        review_required=bool(payload["review_required"]),
        production_equivalent=bool(payload["production_equivalent"]),
        current_state_confirmed_empty=bool(payload["current_state_confirmed_empty"]),
        current_positions_unknown=bool(payload["current_positions_unknown"]),
        cash_unknown=bool(payload["cash_unknown"]),
        buying_power_unknown=bool(payload["buying_power_unknown"]),
        generated_from=tuple(payload.get("generated_from") or ()),
        created_at=str(payload["created_at"]),
    )


def _broker_orders(snapshot: Mapping[str, Any], *, pending_plan_id: str) -> tuple[BrokerOrderSnapshot, ...]:
    return tuple(
        BrokerOrderSnapshot(
            snapshot_id=f"broker-order-{order.get('order_id_hash')}",
            schema_version="1",
            environment="demo",
            source="phase14d15_broker_readonly_after",
            as_of=str(order.get("as_of") or snapshot.get("generated_at") or ""),
            broker_ref_hash=str(order.get("order_id_hash") or ""),
            review_required=False,
            production_equivalent=True,
            order_ref_hash=str(order.get("order_id_hash") or ""),
            pending_plan_id=pending_plan_id,
            pending_item_id="phase14d15-sell-7203-100" if str(order.get("issue_code")) == "7203" and _side(order) == "SELL" else "",
            symbol=str(order.get("issue_code") or ""),
            side=_side(order),
            quantity=_float(order.get("quantity")),
            order_status=_status(order),
            filled_quantity=_float(order.get("executed_quantity")),
            remaining_quantity=_float(order.get("remaining_quantity")),
            accepted_at=str(order.get("order_datetime") or ""),
            updated_at=str(order.get("as_of") or snapshot.get("generated_at") or ""),
        )
        for order in (snapshot.get("orders") or ())
    )


def _broker_positions(snapshot: Mapping[str, Any]) -> tuple[BrokerPositionSnapshot, ...]:
    return tuple(
        BrokerPositionSnapshot(
            snapshot_id=f"broker-position-{position.get('position_id') or position.get('issue_code')}",
            schema_version="1",
            environment="demo",
            source="phase14d15_broker_readonly_after",
            as_of=str(position.get("as_of") or snapshot.get("generated_at") or ""),
            broker_ref_hash=str(position.get("position_id") or position.get("issue_code") or ""),
            review_required=False,
            production_equivalent=True,
            position_ref_hash=str(position.get("position_id") or position.get("issue_code") or ""),
            position_key=str(position.get("issue_code") or position.get("symbol") or ""),
            symbol=str(position.get("issue_code") or position.get("symbol") or ""),
            quantity=_float(position.get("quantity")),
            average_price=_float(position.get("average_price")),
            market_value=_float(position.get("market_value")),
        )
        for position in (snapshot.get("positions") or ())
    )


def _broker_cash(snapshot: Mapping[str, Any]) -> BrokerCashSnapshot:
    cash = snapshot.get("buying_power") or snapshot.get("account_summary") or {}
    return BrokerCashSnapshot(
        snapshot_id="broker-cash-phase14d15-after",
        schema_version="1",
        environment="demo",
        source="phase14d15_broker_readonly_after",
        as_of=str(cash.get("as_of") or snapshot.get("generated_at") or ""),
        broker_ref_hash=str(cash.get("raw_clmid") or "cash"),
        review_required=False,
        production_equivalent=True,
        cash_ref_hash=str(cash.get("raw_clmid") or "cash"),
        cash=_float(cash.get("cash_available")),
        buying_power=_float(cash.get("buying_power")),
        currency=str(cash.get("currency") or "JPY"),
    )


def _ledger_orders(
    broker_orders: tuple[BrokerOrderSnapshot, ...],
    *,
    pending_plan_id: str,
    linked_record_ids: tuple[str, ...],
) -> tuple[LedgerOrderRecord, ...]:
    records = []
    for index, order in enumerate(broker_orders):
        record_id = linked_record_ids[index] if index < len(linked_record_ids) else f"ledger-order-{index + 1}"
        records.append(
            LedgerOrderRecord(
                record_id=record_id,
                record_type="order",
                schema_version="1",
                environment="demo",
                source="phase14d15_orderlist_position_cash_reflection",
                created_at=order.as_of,
                dedup_key=f"phase14d22:{order.order_ref_hash}",
                order_id=order.order_ref_hash,
                pending_plan_id=pending_plan_id if order.side == "SELL" and order.symbol == "7203" else "",
                pending_item_id=order.pending_item_id,
                side=order.side,
                symbol=order.symbol,
                quantity=order.quantity,
                status=order.order_status,
            )
        )
    return tuple(records)


def _ledger_positions(asset_state: CurrentAssetState) -> tuple[LedgerPositionRecord, ...]:
    return tuple(
        LedgerPositionRecord(
            record_id=f"ledger-position-phase14d22-{position.symbol}",
            record_type="position",
            schema_version="1",
            environment=asset_state.environment,
            source=asset_state.source,
            created_at=position.as_of,
            dedup_key=f"phase14d22:position:{position.symbol}",
            position_key=position.symbol,
            symbol=position.symbol,
            quantity=position.quantity,
            average_price=position.average_price,
            market_value=position.market_value,
            as_of=position.as_of,
        )
        for position in (asset_state.positions or ())
    )


def _ledger_cash(asset_state: CurrentAssetState) -> LedgerCashRecord:
    return LedgerCashRecord(
        record_id="ledger-cash-phase14d22",
        record_type="cash",
        schema_version="1",
        environment=asset_state.environment,
        source=asset_state.source,
        created_at=asset_state.created_at,
        dedup_key="phase14d22:cash",
        cash_key="phase14d22:cash",
        cash=float(asset_state.cash or 0),
        buying_power=float(asset_state.buying_power or 0),
        currency="JPY",
        as_of=asset_state.created_at,
    )


def _ledger_event(payload: Mapping[str, Any]) -> LedgerEventRecord:
    return LedgerEventRecord(
        record_id=str(payload["record_id"]),
        record_type=str(payload["record_type"]),
        schema_version=str(payload["schema_version"]),
        environment=str(payload["environment"]),
        source=str(payload["source"]),
        created_at=str(payload["created_at"]),
        dedup_key=str(payload["dedup_key"]),
        review_required=bool(payload["review_required"]),
        production_equivalent=bool(payload["production_equivalent"]),
        event_id=str(payload["event_id"]),
        event_type=str(payload["event_type"]),
        severity=str(payload["severity"]),
        message=str(payload["message"]),
        related_id=str(payload["related_id"]),
    )


def _assert_mode_rooted_current_write_is_rejected(*, base_dir: Path, asset_state: CurrentAssetState) -> None:
    try:
        write_current_asset_state(
            base_dir / ".runtime" / "demo" / "persistent_ledger" / "state.json",
            asset_state,
        )
    except ValueError:
        return
    raise AssertionError("mode-rooted Current write was not rejected")


def _side(order: Mapping[str, Any]) -> str:
    side = str(order.get("side") or "")
    if "売" in side or side.upper() == "SELL":
        return "SELL"
    if "買" in side or side.upper() == "BUY":
        return "BUY"
    return side.upper()


def _status(order: Mapping[str, Any]) -> str:
    status = str(order.get("status") or order.get("order_status") or "")
    if "全部約定" in status or _float(order.get("executed_quantity")) > 0 and _float(order.get("remaining_quantity")) == 0:
        return "filled"
    if "取消" in status:
        return "canceled"
    return status or "unknown"


def _float(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
