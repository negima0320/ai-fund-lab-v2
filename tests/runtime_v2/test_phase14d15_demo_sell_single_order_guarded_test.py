import json
from pathlib import Path

from ai_fund_lab_v2.broker import phase14d15_demo_sell_test
from ai_fund_lab_v2.broker.phase14d15_demo_sell_test import run_phase14d15_demo_sell_single_order_guarded_test
from ai_fund_lab_v2.broker.settings import BrokerSettings
from ai_fund_lab_v2.runtime_v2.submit.models import RuntimeV2SubmitCommand, RuntimeV2SubmitResult


class AcceptingSellAdapter:
    def preflight(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        assert command.symbol == "7203"
        assert command.side == "SELL"
        assert command.quantity == 100
        assert command.source_current_path == "pending_order_plan/pending_order_plan.json"
        return RuntimeV2SubmitResult(
            status="DRY_RUN_READY",
            submitted=False,
            accepted=False,
            blocked=False,
            review_required=False,
            broker_api_called=False,
            reason="dry-run ready",
        )

    def submit(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        assert command.side == "SELL"
        return RuntimeV2SubmitResult(
            status="ACCEPTED",
            submitted=True,
            accepted=True,
            blocked=False,
            review_required=False,
            broker_api_called=True,
            broker_order_id_hash="sha256:d15-sell-order",
            reason="accepted",
        )


class FailingSubmitAdapter(AcceptingSellAdapter):
    def submit(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        return RuntimeV2SubmitResult(
            status="BLOCKED",
            submitted=False,
            accepted=False,
            blocked=True,
            review_required=False,
            broker_api_called=False,
            reason="blocked by fake adapter",
        )


def test_phase14d15_sell_test_passes_with_orderlist_position_cash_evidence(tmp_path, monkeypatch):
    def fake_snapshot(*, settings, report_path: Path, snapshot_path: Path, symbol: str, source: str) -> str:
        if "before" in source:
            _write_snapshot(
                snapshot_path,
                positions=[_position("7203", quantity="100", available_quantity="100")],
                orders=[],
                cash="1000000",
                buying_power="1000000",
            )
        else:
            _write_snapshot(
                snapshot_path,
                positions=[],
                orders=[_sell_order("7203", status="全部約定", executed_quantity="100", remaining_quantity="0")],
                cash="1294100",
                buying_power="1294100",
            )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("{}\n", encoding="utf-8")
        return "PASS"

    monkeypatch.setattr(phase14d15_demo_sell_test, "_readonly_snapshot", fake_snapshot)

    result = run_phase14d15_demo_sell_single_order_guarded_test(
        root=tmp_path / "runtime",
        docs_report_path=tmp_path / "docs" / "d15.md",
        json_report_path=tmp_path / "reports" / "d15.json",
        adapter=AcceptingSellAdapter(),
        settings=BrokerSettings(environment="demo", base_url="https://demo-kabuka.e-shiten.jp/e_api_v4r9"),
    )

    assert result.final_decision == "PHASE14D15_DEMO_SELL_SINGLE_ORDER_PASS"
    assert result.sell_submit_executed is True
    assert result.buy_submit_executed is False
    assert result.before_position_quantity == 100
    assert result.before_available_quantity == 100
    assert result.after_position_quantity == 0
    assert result.position_decreased_or_disappeared is True
    assert result.cash_or_buying_power_updated is True
    assert result.orderlist_position_cash_evidence_used is True
    assert result.asset_built_from_broker_order_only is False
    assert result.reconcile_pass is True
    assert result.notification_sent is False


def test_phase14d15_blocks_when_available_quantity_is_below_sell_quantity(tmp_path, monkeypatch):
    def fake_snapshot(*, settings, report_path: Path, snapshot_path: Path, symbol: str, source: str) -> str:
        _write_snapshot(
            snapshot_path,
            positions=[_position("7203", quantity="100", available_quantity="99")],
            orders=[],
            cash="1000000",
            buying_power="1000000",
        )
        return "PASS"

    monkeypatch.setattr(phase14d15_demo_sell_test, "_readonly_snapshot", fake_snapshot)

    result = run_phase14d15_demo_sell_single_order_guarded_test(
        root=tmp_path / "runtime",
        docs_report_path=tmp_path / "docs" / "d15.md",
        json_report_path=tmp_path / "reports" / "d15.json",
        adapter=FailingSubmitAdapter(),
        settings=BrokerSettings(environment="demo", base_url="https://demo-kabuka.e-shiten.jp/e_api_v4r9"),
    )

    assert result.final_decision == "PHASE14D15_REVIEW_REQUIRED"
    assert result.sell_submit_executed is False
    assert "7203 available_quantity is below planned SELL quantity" in result.blocked_reasons


def _write_snapshot(
    path: Path,
    *,
    positions: list[dict],
    orders: list[dict],
    cash: str,
    buying_power: str,
) -> None:
    payload = {
        "generated_at": "2026-07-07T04:00:00+00:00",
        "health": {
            "orders": {"status": "PASS"},
            "positions": {"status": "PASS"},
            "account": {"status": "PASS"},
        },
        "buying_power": {
            "cash_ref": "cash-1",
            "cash": cash,
            "buying_power": buying_power,
            "currency": "JPY",
        },
        "orders": orders,
        "positions": positions,
        "executions": [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _position(issue_code: str, *, quantity: str, available_quantity: str) -> dict:
    return {
        "position_id": f"position-{issue_code}",
        "issue_code": issue_code,
        "account_type": "cash",
        "quantity": quantity,
        "available_quantity": available_quantity,
        "average_price": "102",
        "market_value": "294100",
    }


def _sell_order(issue_code: str, *, status: str, executed_quantity: str, remaining_quantity: str) -> dict:
    return {
        "order_id_hash": f"order-{issue_code}-sell",
        "issue_code": issue_code,
        "side": "sell",
        "quantity": "100",
        "executed_quantity": executed_quantity,
        "remaining_quantity": remaining_quantity,
        "status": status,
        "as_of": "2026-07-07T04:00:00+00:00",
    }
