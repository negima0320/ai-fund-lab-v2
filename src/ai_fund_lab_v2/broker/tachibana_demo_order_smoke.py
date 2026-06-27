from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.broker.secrets import TachibanaSecretLoader
from ai_fund_lab_v2.broker.settings import BrokerConfigurationError, BrokerSettings, load_broker_settings
from ai_fund_lab_v2.broker.tachibana_order_request import (
    TachibanaCashStockOrderRequest,
    TachibanaCashStockOrderRequestBuilder,
)
from ai_fund_lab_v2.runtime import (
    DemoOrderExecutor,
    OrderApprovalGate,
    OrderApprovalScope,
    OrderCommand,
    OrderResultStatus,
    OrderSide,
    OrderType,
    PriceType,
    RuntimeMode,
)


@dataclass(frozen=True)
class TachibanaDemoOrderSmokeResult:
    status: str
    executed: bool
    report_path: Path
    message: str = ""


def run_tachibana_demo_order_live_smoke_foundation(
    *,
    reports_dir: Path,
    run_enabled: bool = False,
    dry_run: bool = False,
    report_filename: str = "phase10u_tachibana_demo_order_live_smoke_foundation_result.json",
    source: str = "phase10u_demo_order_live_smoke_foundation",
    env: dict[str, str] | None = None,
    settings: BrokerSettings | None = None,
    approval_id: str = "phase10u_demo_order_dry_run",
    issue_code: str = "7203",
    side: OrderSide = OrderSide.BUY,
    quantity: Decimal = Decimal("100"),
    limit_price: Decimal = Decimal("2000"),
    max_notional: Decimal = Decimal("250000"),
    approval_expires_at: datetime | None = None,
) -> TachibanaDemoOrderSmokeResult:
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / report_filename
    resolved_settings = settings or load_broker_settings(env=env)
    if not run_enabled:
        payload = _base_payload(
            resolved_settings,
            source=source,
            status="SKIPPED",
            executed=False,
            message="Explicit run flag was not provided; no Tachibana demo order live smoke foundation ran.",
        )
        _write_json(report_path, payload)
        return TachibanaDemoOrderSmokeResult(status="SKIPPED", executed=False, report_path=report_path, message=payload["message"])
    if not dry_run:
        payload = _base_payload(
            resolved_settings,
            source=source,
            status="BLOCKED_LIVE_SUBMIT_NOT_IMPLEMENTED",
            executed=False,
            message="Phase10-U supports dry-run readiness only; live order submission is not implemented.",
        )
        _write_json(report_path, payload)
        return TachibanaDemoOrderSmokeResult(status="BLOCKED_LIVE_SUBMIT_NOT_IMPLEMENTED", executed=False, report_path=report_path, message=payload["message"])

    try:
        resolved_settings.require_demo_environment()
    except BrokerConfigurationError as exc:
        payload = _base_payload(
            resolved_settings,
            source=source,
            status="BLOCKED_PRODUCTION_PROHIBITED",
            executed=False,
            message=str(exc),
        )
        _write_json(report_path, payload)
        return TachibanaDemoOrderSmokeResult(status="BLOCKED_PRODUCTION_PROHIBITED", executed=False, report_path=report_path, message=payload["message"])

    command = OrderCommand(
        runtime_id="phase10u_demo_order_dry_run",
        environment=RuntimeMode.DEMO,
        paper_test_id="paper_test2_2026-06-29",
        issue_code=issue_code,
        side=side,
        quantity=quantity,
        order_type=OrderType.CASH_EQUITY,
        price_type=PriceType.LIMIT,
        limit_price=limit_price,
        evaluation_cash_basis=Decimal("1000000"),
        broker_cash_upper_bound=Decimal("20000000"),
        approval_required=True,
        approval_id=approval_id,
        live_order_allowed=True,
    )
    second_password_status = TachibanaSecretLoader(resolved_settings).classify_second_password_file()
    approval_scope = OrderApprovalScope(
        approval_id=approval_id,
        environment=RuntimeMode.DEMO,
        issue_code=issue_code,
        side=side,
        quantity=quantity,
        max_notional=max_notional,
        expires_at=approval_expires_at or (datetime.now(timezone.utc) + timedelta(minutes=10)),
    )
    authorization = OrderApprovalGate().authorize(
        command,
        approval_scope,
        second_password_present=second_password_status.present,
        now=datetime.now(timezone.utc),
    )
    order_request = TachibanaCashStockOrderRequest.from_order_command(
        command,
        second_password_present=second_password_status.present,
    )
    builder = TachibanaCashStockOrderRequestBuilder()
    payload_summary = builder.build_final_payload_summary(order_request, dry_run=True)
    executor_result = DemoOrderExecutor().submit(command, authorization=authorization, dry_run=True)
    status = "DRY_RUN_READY" if executor_result.status is OrderResultStatus.DRY_RUN_READY else executor_result.status.value
    payload = {
        **_base_payload(resolved_settings, source=source, status=status, executed=False, message=executor_result.reason),
        "dry_run": True,
        "environment_guard": "PASS_DEMO_ONLY",
        "approval": {
            "approval_id_present": bool(approval_id),
            "scope_matched": authorization.approved,
            "status": authorization.status.value,
            "reason": authorization.reason,
        },
        "second_password": second_password_status.to_dict(),
        "order_policy": {
            "side": side.value,
            "buy_only_first_smoke": side is OrderSide.BUY,
            "price_type": PriceType.LIMIT.value,
            "limit_only_first_smoke": True,
            "quantity": str(quantity),
            "max_notional": str(max_notional),
            "evaluation_cash_basis": "1000000",
            "demo_buying_power_upper_bound": "20000000",
        },
        "final_payload_summary": payload_summary,
        "executor_result": executor_result.to_dict(),
        "post_submit_reconciliation": _post_submit_reconciliation_skeleton(),
    }
    _write_json(report_path, payload)
    return TachibanaDemoOrderSmokeResult(status=status, executed=False, report_path=report_path, message=executor_result.reason)


def _post_submit_reconciliation_skeleton() -> dict[str, Any]:
    return {
        "mode": "dry_run_skeleton",
        "order_list": "NOT_EXECUTED",
        "order_detail": "NOT_EXECUTED",
        "positions": "NOT_EXECUTED",
        "fill_monitor": "NOT_EXECUTED",
        "broker_snapshot": "NOT_EXECUTED",
        "raw_order_id_saved": False,
        "raw_response_saved": False,
    }


def _base_payload(settings: BrokerSettings, *, source: str, status: str, executed: bool, message: str) -> dict[str, Any]:
    return {
        "status": status,
        "executed": executed,
        "created_at": utc_now_iso(),
        "broker": "tachibana",
        "source": source,
        "environment": settings.environment,
        "message": message,
        "live_api_connected": False,
        "demo_order_submitted": False,
        "production_order_submitted": False,
        "clmkabu_new_order_executed": False,
        "broker_order_api_called": False,
        "cancel_api_called": False,
        "correction_api_called": False,
        "second_password_api_called": False,
        "unlock_gate_called": False,
        "broker_snapshot_updated": False,
        "paper_ledger_updated": False,
        "ai_learning_updated": False,
        "backtest_run": False,
        "raw_payload_saved": False,
        "raw_response_saved": False,
        "secret_saved": False,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
