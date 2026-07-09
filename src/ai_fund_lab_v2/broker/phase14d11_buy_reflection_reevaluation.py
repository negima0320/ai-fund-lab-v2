"""Phase14-D11 reevaluate D8 BUY reflection with D10 evidence policy."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.settings import DEMO_BASE_URL, PROD_BASE_URL, BrokerSettings, load_broker_settings
from ai_fund_lab_v2.broker.tachibana_broker_snapshot import run_tachibana_broker_snapshot
from ai_fund_lab_v2.runtime_v2.asset.builder import build_current_asset_state
from ai_fund_lab_v2.runtime_v2.audit.auditor import run_audit
from ai_fund_lab_v2.runtime_v2.broker_readonly.normalizer import normalize_broker_readonly_payload
from ai_fund_lab_v2.runtime_v2.execution.fill_classifier import classify_orderlist_position_cash_fill
from ai_fund_lab_v2.runtime_v2.execution.ledger_projection import (
    project_cash_to_ledger_record,
    project_order_to_ledger_record,
    project_position_to_ledger_record,
)
from ai_fund_lab_v2.runtime_v2.ledger.models import LedgerEventRecord
from ai_fund_lab_v2.runtime_v2.notification.payload import build_notification_payload
from ai_fund_lab_v2.runtime_v2.reconcile.reconciler import run_reconciliation
from ai_fund_lab_v2.runtime_v2.report.builder import build_runtime_report
from ai_fund_lab_v2.runtime_v2.report.models import ReportBuildInput


@dataclass(frozen=True)
class Phase14D11Result:
    final_decision: str
    environment: str
    base_url_is_demo: bool
    base_url_is_production: bool
    readonly_status: str
    readonly_orders_health_pass: bool
    readonly_positions_health_pass: bool
    readonly_account_health_pass: bool
    readonly_executions_detail_status: str
    target_issue_code: str
    target_side: str
    target_quantity: float
    target_order_found: bool
    target_order_status: str
    target_executed_quantity: float
    target_remaining_quantity: float
    target_position_found: bool
    target_position_quantity: float
    cash_evidence_present: bool
    cash_value: float | None
    buying_power_value: float | None
    fill_classification: str
    execution_equivalent: bool
    detail_optional_missing: bool
    ledger_order_count: int
    ledger_execution_count: int
    ledger_event_count: int
    ledger_position_count: int
    ledger_cash_count: int
    asset_state_created: bool
    asset_contains_target_position: bool
    reconcile_pass: bool
    reconciliation_findings: int
    report_sections: int
    report_detail_optional_missing_noted: bool
    notification_payload_created: bool
    notification_sent: bool
    audit_pass: bool
    audit_findings: int
    additional_demo_submit_executed: bool
    buy_resubmit_executed: bool
    sell_submit_executed: bool
    cancel_api_called: bool
    production_order_executed: bool
    production_broker_api_write_executed: bool
    real_money_operation_executed: bool
    launchd_or_plist_modified: bool
    snapshot_path: str
    blocked_reasons: tuple[str, ...] = ()
    review_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_phase14d11_d8_buy_reflection_reevaluation(
    *,
    root: Path,
    docs_report_path: Path,
    json_report_path: Path,
    settings: BrokerSettings | None = None,
    target_issue_code: str = "7203",
    target_quantity: float = 100.0,
    run_readonly: bool = True,
    snapshot_path: Path | None = None,
) -> Phase14D11Result:
    settings = settings or load_broker_settings()
    root.mkdir(parents=True, exist_ok=True)
    docs_report_path.parent.mkdir(parents=True, exist_ok=True)
    json_report_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_path or root / "broker_readonly_resync" / "tachibana_demo_snapshot.json"
    snapshot_report_path = root / "broker_readonly_resync" / "snapshot_report.json"
    blocked_reasons: list[str] = []
    review_reasons: list[str] = []
    base_url = settings.base_url.rstrip("/")
    base_url_is_demo = base_url == DEMO_BASE_URL
    base_url_is_production = base_url == PROD_BASE_URL

    if settings.environment != "demo":
        blocked_reasons.append("environment is not demo")
    if not base_url_is_demo or base_url_is_production:
        blocked_reasons.append("base URL is not demo-only")

    if run_readonly:
        readonly_status = _run_readonly_snapshot(
            settings=settings,
            report_path=snapshot_report_path,
            snapshot_path=snapshot_path,
            symbol=target_issue_code,
        )
    else:
        readonly_status = _existing_snapshot_status(snapshot_report_path)
    if not snapshot_path.exists():
        blocked_reasons.append("readonly snapshot missing")

    payload = _load_json(snapshot_path) if snapshot_path.exists() else {}
    health = payload.get("health") or {}
    readonly_orders_health_pass = _health_status(health, "orders") == "PASS"
    readonly_positions_health_pass = _health_status(health, "positions") == "PASS"
    readonly_account_health_pass = _health_status(health, "account") == "PASS"
    readonly_executions_detail_status = _health_status(health, "executions")
    if not readonly_orders_health_pass:
        blocked_reasons.append("CLMOrderList ReadOnly health is not PASS")
    if not readonly_positions_health_pass:
        review_reasons.append("CLMGenbutuKabuList ReadOnly health is not PASS")
    if not readonly_account_health_pass:
        review_reasons.append("CLMZanKaiSummary / CLMZanKaiKanougaku health is not PASS")

    bundle = _bundle_from_snapshot(payload)
    target_order = _find_target_order(bundle.orders, target_issue_code=target_issue_code, target_quantity=target_quantity)
    target_position = _find_target_position(bundle.positions, target_issue_code=target_issue_code)
    cash = bundle.cash
    if target_order is None:
        blocked_reasons.append("7203 BUY 100 order not found in CLMOrderList")
    policy_result = (
        classify_orderlist_position_cash_fill(
            order=target_order,
            positions=bundle.positions,
            cash=cash,
            executions=bundle.executions,
        )
        if target_order is not None
        else None
    )
    if policy_result is not None and not policy_result.execution_equivalent:
        review_reasons.append(policy_result.reason)

    ledger_orders = tuple(project_order_to_ledger_record(order) for order in bundle.orders)
    ledger_positions = tuple(project_position_to_ledger_record(position) for position in bundle.positions)
    ledger_cash = (project_cash_to_ledger_record(cash),) if cash else ()
    ledger_events = (
        (
            _detail_optional_missing_event(policy_result, target_issue_code=target_issue_code)
            if policy_result and policy_result.detail_optional_missing
            else None
        ),
    )
    ledger_events = tuple(event for event in ledger_events if event is not None)
    asset_state = build_current_asset_state(
        environment="demo",
        positions=ledger_positions,
        cash_records=ledger_cash,
        source="phase14d11_orderlist_position_cash_reflection",
        as_of=_business_date(),
    )
    reconciliation = run_reconciliation(
        mode="demo",
        environment="demo",
        business_date=_business_date(),
        ledger_orders=ledger_orders,
        ledger_executions=(),
        broker_orders=bundle.orders,
        broker_executions=(),
        broker_positions=bundle.positions,
        broker_cash=cash,
        asset_state=asset_state,
    )
    report = build_runtime_report(
        ReportBuildInput(
            mode="demo",
            environment="demo",
            business_date=_business_date(),
            target_session_date=_business_date(),
            asset_state=asset_state,
            ledger_orders=ledger_orders,
            ledger_executions=(),
            ledger_positions=ledger_positions,
            ledger_cash_records=ledger_cash,
            broker_orders=bundle.orders,
            broker_executions=(),
            broker_positions=bundle.positions,
            broker_cash=cash,
            reconciliation_result=reconciliation,
            review_events=ledger_events,
        )
    )
    notification_payload = build_notification_payload(report=report, channel="phase14d11_payload_only")
    audit = run_audit(
        mode="demo",
        environment="demo",
        business_date=_business_date(),
        report=report,
        notification_payload=notification_payload,
        reconciliation_result=reconciliation,
        asset_state=asset_state,
    )
    if reconciliation.findings:
        review_reasons.append(f"reconciliation findings={len(reconciliation.findings)}")
    if audit.findings:
        review_reasons.append(f"audit findings={len(audit.findings)}")

    report_detail_optional_missing_noted = any(
        "detail_optional_missing" in section.content for section in report.sections
    )
    asset_contains_target_position = any(
        position.symbol == target_issue_code and position.quantity >= target_quantity
        for position in (asset_state.positions or ())
    )
    final_decision = "PHASE14D11_D8_BUY_REFLECTION_PASS"
    if (
        blocked_reasons
        or review_reasons
        or policy_result is None
        or not policy_result.execution_equivalent
        or not asset_contains_target_position
        or reconciliation.findings
        or audit.findings
    ):
        final_decision = "PHASE14D11_REVIEW_REQUIRED"

    _write_json(root / "ledger_events" / "phase14d11_execution_equivalent_events.json", {"events": _jsonable(ledger_events)})
    _write_json(root / "asset_state" / "asset_state.json", _jsonable(asset_state))
    _write_json(root / "report" / "runtime_report.json", _jsonable(report))
    _write_json(root / "audit" / "audit_result.json", _jsonable(audit))

    result = Phase14D11Result(
        final_decision=final_decision,
        environment=settings.environment,
        base_url_is_demo=base_url_is_demo,
        base_url_is_production=base_url_is_production,
        readonly_status=readonly_status,
        readonly_orders_health_pass=readonly_orders_health_pass,
        readonly_positions_health_pass=readonly_positions_health_pass,
        readonly_account_health_pass=readonly_account_health_pass,
        readonly_executions_detail_status=readonly_executions_detail_status,
        target_issue_code=target_issue_code,
        target_side="BUY",
        target_quantity=target_quantity,
        target_order_found=target_order is not None,
        target_order_status=target_order.order_status if target_order else "",
        target_executed_quantity=target_order.filled_quantity if target_order else 0.0,
        target_remaining_quantity=target_order.remaining_quantity if target_order else 0.0,
        target_position_found=target_position is not None,
        target_position_quantity=target_position.quantity if target_position else 0.0,
        cash_evidence_present=cash is not None,
        cash_value=cash.cash if cash else None,
        buying_power_value=cash.buying_power if cash else None,
        fill_classification=policy_result.classification.classification.value if policy_result else "NOT_CLASSIFIED",
        execution_equivalent=bool(policy_result and policy_result.execution_equivalent),
        detail_optional_missing=bool(policy_result and policy_result.detail_optional_missing),
        ledger_order_count=len(ledger_orders),
        ledger_execution_count=0,
        ledger_event_count=len(ledger_events),
        ledger_position_count=len(ledger_positions),
        ledger_cash_count=len(ledger_cash),
        asset_state_created=asset_state is not None,
        asset_contains_target_position=asset_contains_target_position,
        reconcile_pass=not reconciliation.findings,
        reconciliation_findings=len(reconciliation.findings),
        report_sections=len(report.sections),
        report_detail_optional_missing_noted=report_detail_optional_missing_noted,
        notification_payload_created=notification_payload is not None,
        notification_sent=False,
        audit_pass=not audit.findings,
        audit_findings=len(audit.findings),
        additional_demo_submit_executed=False,
        buy_resubmit_executed=False,
        sell_submit_executed=False,
        cancel_api_called=False,
        production_order_executed=False,
        production_broker_api_write_executed=False,
        real_money_operation_executed=False,
        launchd_or_plist_modified=False,
        snapshot_path=str(snapshot_path),
        blocked_reasons=tuple(blocked_reasons),
        review_reasons=tuple(dict.fromkeys(review_reasons)),
    )
    _write_json(json_report_path, result.to_dict())
    docs_report_path.write_text(_markdown_report(result), encoding="utf-8")
    return result


def _run_readonly_snapshot(*, settings: BrokerSettings, report_path: Path, snapshot_path: Path, symbol: str) -> str:
    result = run_tachibana_broker_snapshot(
        reports_dir=report_path.parent,
        run_enabled=True,
        report_filename=report_path.name,
        snapshot_path=snapshot_path,
        source="phase14d11_d8_buy_reflection_reevaluation",
        settings=settings,
        symbols=(symbol,),
        include_quotes=False,
    )
    return result.status


def _bundle_from_snapshot(payload: dict[str, Any]):
    as_of = str(payload.get("generated_at") or _now())
    return normalize_broker_readonly_payload(
        environment="demo",
        source="phase14d11_orderlist_position_cash_reflection",
        as_of=as_of,
        orders=tuple(_runtime_order_payload(order) for order in payload.get("orders") or ()),
        executions=tuple(_runtime_execution_payload(execution) for execution in payload.get("executions") or ()),
        positions=tuple(_runtime_position_payload(position) for position in payload.get("positions") or ()),
        cash=_runtime_cash_payload(payload.get("buying_power") or payload.get("account_summary") or {}),
    )


def _runtime_order_payload(order: dict[str, Any]) -> dict[str, Any]:
    return {
        "order_id": order.get("order_id_hash") or order.get("order_id") or order.get("order_ref") or _hash_text(json.dumps(order, sort_keys=True)),
        "symbol": order.get("issue_code") or order.get("symbol") or "",
        "side": _normalize_side(str(order.get("side") or "")),
        "quantity": _float(order.get("quantity")),
        "order_status": _normalize_order_status(str(order.get("status") or order.get("order_status") or "")),
        "filled_quantity": _float(order.get("executed_quantity") or order.get("filled_quantity")),
        "remaining_quantity": _float(order.get("remaining_quantity")),
        "accepted_at": str(order.get("order_datetime") or order.get("accepted_at") or ""),
        "updated_at": str(order.get("as_of") or order.get("updated_at") or ""),
    }


def _runtime_execution_payload(execution: dict[str, Any]) -> dict[str, Any]:
    return {
        "execution_id": execution.get("execution_id") or execution.get("execution_ref") or _hash_text(json.dumps(execution, sort_keys=True)),
        "order_id": execution.get("order_id_hash") or execution.get("order_id") or execution.get("order_ref") or "",
        "execution_key": execution.get("execution_key") or "",
        "symbol": execution.get("issue_code") or execution.get("symbol") or "",
        "side": _normalize_side(str(execution.get("side") or "")),
        "quantity": _float(execution.get("quantity")),
        "price": _float(execution.get("price")),
        "executed_at": str(execution.get("executed_at") or execution.get("as_of") or ""),
    }


def _runtime_position_payload(position: dict[str, Any]) -> dict[str, Any]:
    return {
        "position_id": position.get("position_id") or position.get("position_ref") or _hash_text(json.dumps(position, sort_keys=True)),
        "position_key": position.get("issue_code") or position.get("symbol") or position.get("account_type") or "",
        "symbol": position.get("issue_code") or position.get("symbol") or "",
        "quantity": _float(position.get("quantity")),
        "average_price": _float(position.get("average_price")),
        "market_value": _float(position.get("market_value")),
    }


def _runtime_cash_payload(cash: dict[str, Any]) -> dict[str, Any]:
    return {
        "cash_ref": cash.get("cash_ref") or cash.get("raw_clmid") or "cash",
        "cash": cash.get("cash") or cash.get("cash_available") or 0,
        "buying_power": cash.get("buying_power") or 0,
        "currency": cash.get("currency") or "JPY",
    }


def _find_target_order(orders, *, target_issue_code: str, target_quantity: float):
    candidates = [
        order
        for order in orders
        if order.symbol == target_issue_code
        and order.side.upper() == "BUY"
        and abs(order.quantity - target_quantity) < 0.000001
    ]
    return candidates[0] if candidates else None


def _find_target_position(positions, *, target_issue_code: str):
    candidates = [position for position in positions if position.symbol == target_issue_code]
    return candidates[0] if candidates else None


def _detail_optional_missing_event(policy_result, *, target_issue_code: str) -> LedgerEventRecord:
    message = "CLMOrderListDetail optional missing"
    if policy_result.execution_equivalent:
        message += "; OrderList/Position/Cash evidence used"
    else:
        message += "; OrderList-derived fill is not execution-equivalent without Position/Cash corroboration"
    return LedgerEventRecord(
        record_id=f"ledger-event-phase14d11-{target_issue_code}",
        record_type="event",
        schema_version="1",
        environment="demo",
        source="phase14d11_orderlist_position_cash_reflection",
        created_at=policy_result.classification.as_of,
        dedup_key=f"phase14d11:{target_issue_code}:detail_optional_missing",
        review_required=False,
        production_equivalent=True,
        event_id=f"phase14d11:{target_issue_code}:order_list_derived_full_fill",
        event_type="detail_optional_missing",
        severity="INFO",
        message=message,
        related_id=policy_result.classification.order_ref_hash,
    )


def _health_status(health: dict[str, Any], key: str) -> str:
    return str(((health.get(key) or {}).get("status") or "UNKNOWN"))


def _existing_snapshot_status(snapshot_report_path: Path) -> str:
    if not snapshot_report_path.exists():
        return "USING_EXISTING_SNAPSHOT"
    return str((_load_json(snapshot_report_path).get("status") or "USING_EXISTING_SNAPSHOT"))


def _normalize_order_status(status: str) -> str:
    if "取消" in status:
        return "canceled"
    if "失効" in status:
        return "expired"
    if "未約定" in status:
        return "open"
    if "約定" in status:
        return "filled"
    return status.strip().lower() or status


def _normalize_side(side: str) -> str:
    normalized = side.strip().lower()
    if normalized in {"buy", "3", "買", "買付"}:
        return "BUY"
    if normalized in {"sell", "1", "売", "売付"}:
        return "SELL"
    return side.upper()


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if hasattr(value, "value"):
        return value.value
    return value


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _hash_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _business_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _markdown_report(result: Phase14D11Result) -> str:
    return f"""# Phase14-D11 D8 BUY Reflection Reevaluation

作成日: 2026-07-07

## Status

```text
{result.final_decision}
```

## Summary

- environment: `{result.environment}`
- base_url_is_demo: `{result.base_url_is_demo}`
- base_url_is_production: `{result.base_url_is_production}`
- readonly_status: `{result.readonly_status}`
- readonly_orders_health_pass: `{result.readonly_orders_health_pass}`
- readonly_positions_health_pass: `{result.readonly_positions_health_pass}`
- readonly_account_health_pass: `{result.readonly_account_health_pass}`
- readonly_executions_detail_status: `{result.readonly_executions_detail_status}`
- target_issue_code: `{result.target_issue_code}`
- target_side: `{result.target_side}`
- target_quantity: `{result.target_quantity}`

## Evidence

- target_order_found: `{result.target_order_found}`
- target_order_status: `{result.target_order_status}`
- target_executed_quantity: `{result.target_executed_quantity}`
- target_remaining_quantity: `{result.target_remaining_quantity}`
- target_position_found: `{result.target_position_found}`
- target_position_quantity: `{result.target_position_quantity}`
- cash_evidence_present: `{result.cash_evidence_present}`
- cash_value: `{result.cash_value}`
- buying_power_value: `{result.buying_power_value}`
- fill_classification: `{result.fill_classification}`
- execution_equivalent: `{result.execution_equivalent}`
- detail_optional_missing: `{result.detail_optional_missing}`
- snapshot_path: `{result.snapshot_path}`

## Runtime v2 Reflection

- ledger_order_count: `{result.ledger_order_count}`
- ledger_execution_count: `{result.ledger_execution_count}`
- ledger_event_count: `{result.ledger_event_count}`
- ledger_position_count: `{result.ledger_position_count}`
- ledger_cash_count: `{result.ledger_cash_count}`
- asset_state_created: `{result.asset_state_created}`
- asset_contains_target_position: `{result.asset_contains_target_position}`
- reconcile_pass: `{result.reconcile_pass}`
- reconciliation_findings: `{result.reconciliation_findings}`
- report_sections: `{result.report_sections}`
- report_detail_optional_missing_noted: `{result.report_detail_optional_missing_noted}`
- notification_payload_created: `{result.notification_payload_created}`
- notification_sent: `{result.notification_sent}`
- audit_pass: `{result.audit_pass}`
- audit_findings: `{result.audit_findings}`

## Prohibited Actions

- additional_demo_submit_executed: `{result.additional_demo_submit_executed}`
- buy_resubmit_executed: `{result.buy_resubmit_executed}`
- sell_submit_executed: `{result.sell_submit_executed}`
- cancel_api_called: `{result.cancel_api_called}`
- production_order_executed: `{result.production_order_executed}`
- production_broker_api_write_executed: `{result.production_broker_api_write_executed}`
- real_money_operation_executed: `{result.real_money_operation_executed}`
- launchd_or_plist_modified: `{result.launchd_or_plist_modified}`

## Blocked Reasons

```text
{chr(10).join(result.blocked_reasons) if result.blocked_reasons else "none"}
```

## Review Reasons

```text
{chr(10).join(result.review_reasons) if result.review_reasons else "none"}
```

## Final Decision

```text
{result.final_decision}
```
"""
