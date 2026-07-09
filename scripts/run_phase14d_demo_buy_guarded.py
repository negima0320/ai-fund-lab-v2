#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from decimal import Decimal

from ai_fund_lab_v2.broker.demo_order import TachibanaDemoOrderAdapter
from ai_fund_lab_v2.broker.settings import DEMO_BASE_URL, PROD_BASE_URL, load_broker_settings
from ai_fund_lab_v2.broker.tachibana_broker_snapshot import run_tachibana_broker_snapshot
from ai_fund_lab_v2.runtime.order_command import OrderCommand, OrderSide, OrderType, PriceType
from ai_fund_lab_v2.runtime.runtime_mode import RuntimeMode
from ai_fund_lab_v2.runtime_v2.demo_buy import run_demo_buy_single_order_guarded_test
from ai_fund_lab_v2.runtime_v2.demo_buy.guarded_test import (
    Phase14DDemoBuyCommand,
    Phase14DReadOnlyResult,
    Phase14DSubmitResult,
)


def _submit_demo_buy(command: Phase14DDemoBuyCommand) -> Phase14DSubmitResult:
    result = TachibanaDemoOrderAdapter().submit_cash_stock_order(
        OrderCommand(
            runtime_id=command.runtime_id,
            environment=RuntimeMode.DEMO,
            paper_test_id="phase14d",
            issue_code=command.issue_code,
            side=OrderSide.BUY,
            quantity=command.quantity,
            order_type=OrderType.CASH_EQUITY,
            price_type=PriceType.MARKET,
            limit_price=Decimal("0"),
            evaluation_cash_basis=command.estimated_amount,
            broker_cash_upper_bound=Decimal("20000000"),
            approval_id=command.approval_id,
            live_order_allowed=command.live_order_allowed,
        )
    )
    return Phase14DSubmitResult(
        status=result.status,
        clm_kabu_new_order_called=result.clm_kabu_new_order_called,
        demo_order_executed=result.demo_order_executed,
        broker_order_api_called=result.broker_order_api_called,
        submit_classification=result.submit_classification,
        post_send_unknown=result.post_send_unknown,
        error_classification=result.error_classification,
    )


def _readonly_snapshot(snapshot_path: Path, *, report_filename: str, source: str) -> Phase14DReadOnlyResult:
    result = run_tachibana_broker_snapshot(
        reports_dir=Path("reports/phase_reports"),
        run_enabled=True,
        report_filename=report_filename,
        snapshot_path=snapshot_path,
        source=source,
        settings=load_broker_settings(),
        include_quotes=False,
    )
    return Phase14DReadOnlyResult(
        status=result.status,
        executed=result.executed,
        snapshot_path=str(snapshot_path),
    )


def main() -> int:
    settings = load_broker_settings()
    result = run_demo_buy_single_order_guarded_test(
        root=Path(".runtime/phase14d"),
        reports_dir=Path("reports/phase_reports"),
        docs_report_path=Path("docs/phase_reports/phase14_d_demo_buy_single_order_guarded_test.md"),
        json_report_path=Path("reports/phase_reports/phase14_d_demo_buy_single_order_guarded_test.json"),
        environment=settings.environment,
        base_url_is_demo=settings.base_url.rstrip("/") == DEMO_BASE_URL,
        base_url_is_production=settings.base_url.rstrip("/") == PROD_BASE_URL,
        readonly_allow_prod=settings.readonly_allow_prod,
        second_password_file_configured=bool(settings.second_password_file),
        submit_func=_submit_demo_buy,
        readonly_before_func=lambda path: _readonly_snapshot(
            path,
            report_filename="phase14d_readonly_before.json",
            source="phase14d_demo_buy_readonly_before",
        ),
        readonly_after_func=lambda path: _readonly_snapshot(
            path,
            report_filename="phase14d_readonly_after.json",
            source="phase14d_demo_buy_readonly_after",
        ),
    )
    print(result.final_decision)
    print(result.json_report_path)
    return 0 if result.final_decision in {"PHASE14D_DEMO_BUY_SINGLE_ORDER_PASS", "PHASE14D_REVIEW_REQUIRED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
