import json
from pathlib import Path

from ai_fund_lab_v2.broker import phase14d8_pure_buy_retest
from ai_fund_lab_v2.broker.phase14d8_pure_buy_retest import run_phase14d8_pure_runtime_v2_demo_buy_retest
from ai_fund_lab_v2.broker.settings import BrokerSettings
from ai_fund_lab_v2.runtime_v2.submit.models import RuntimeV2SubmitCommand, RuntimeV2SubmitResult


class AcceptingAdapter:
    def preflight(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        assert command.symbol == "7203"
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
        assert command.side == "BUY"
        return RuntimeV2SubmitResult(
            status="ACCEPTED",
            submitted=True,
            accepted=True,
            blocked=False,
            review_required=False,
            broker_api_called=True,
            broker_order_id_hash="sha256:d8-order",
            reason="accepted",
        )


def test_phase14d8_retest_passes_after_d7_cancel_sync_with_runtime_v2_command(tmp_path, monkeypatch):
    d7 = tmp_path / "d7.json"
    _write_d7(d7, final_decision="PHASE14D7_BROKER_STATE_SYNC_PASS", target_order_cancelled=True)

    def fake_snapshot(*, settings, report_path: Path, snapshot_path: Path, symbol: str, source: str) -> str:
        orders = [
            _order("9432", "取消完了", remaining_quantity="0"),
        ]
        if "after" in source:
            orders.append(_order("7203", "未約定", remaining_quantity="100"))
        _write_snapshot(snapshot_path, orders=orders)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("{}\n", encoding="utf-8")
        return "FAILED_BROKER_READONLY_FETCH"

    monkeypatch.setattr(phase14d8_pure_buy_retest, "_readonly_snapshot", fake_snapshot)

    result = run_phase14d8_pure_runtime_v2_demo_buy_retest(
        root=tmp_path / "runtime",
        docs_report_path=tmp_path / "docs" / "d8.md",
        json_report_path=tmp_path / "reports" / "d8.json",
        adapter=AcceptingAdapter(),
        settings=BrokerSettings(environment="demo", base_url="https://demo-kabuka.e-shiten.jp/e_api_v4r9"),
        d7_report_path=d7,
        symbol="7203",
    )

    assert result.final_decision == "PHASE14D8_PURE_RUNTIME_V2_DEMO_BUY_PASS"
    assert result.d7_sync_pass is True
    assert result.existing_9432_cancelled is True
    assert result.runtime_v2_pure_submit_path is True
    assert result.legacy_order_command_submit_authority_used is False
    assert result.demo_submit_executed is True
    assert result.order_status_readonly_confirmed is True
    assert result.sell_submit_executed is False


def test_phase14d8_retest_blocks_9000_series_before_submit(tmp_path, monkeypatch):
    d7 = tmp_path / "d7.json"
    _write_d7(d7, final_decision="PHASE14D7_BROKER_STATE_SYNC_PASS", target_order_cancelled=True)

    def fake_snapshot(*, settings, report_path: Path, snapshot_path: Path, symbol: str, source: str) -> str:
        _write_snapshot(snapshot_path, orders=[_order("9432", "取消完了", remaining_quantity="0")])
        return "PASS"

    monkeypatch.setattr(phase14d8_pure_buy_retest, "_readonly_snapshot", fake_snapshot)

    result = run_phase14d8_pure_runtime_v2_demo_buy_retest(
        root=tmp_path / "runtime",
        docs_report_path=tmp_path / "docs" / "d8.md",
        json_report_path=tmp_path / "reports" / "d8.json",
        adapter=AcceptingAdapter(),
        settings=BrokerSettings(environment="demo", base_url="https://demo-kabuka.e-shiten.jp/e_api_v4r9"),
        d7_report_path=d7,
        symbol="9432",
    )

    assert result.final_decision == "PHASE14D8_REVIEW_REQUIRED"
    assert result.demo_submit_executed is False
    assert "9000-series symbols excluded" in result.blocked_reasons


def _write_d7(path: Path, *, final_decision: str, target_order_cancelled: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "final_decision": final_decision,
                "target_order_cancelled": target_order_cancelled,
                "pending_consumed": True,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_snapshot(path: Path, *, orders: list[dict]) -> None:
    payload = {
        "generated_at": "2026-07-07T04:00:00+00:00",
        "health": {"orders": {"status": "PASS"}},
        "buying_power": {"cash_ref": "cash-1", "cash": "20000000", "buying_power": "20000000", "currency": "JPY"},
        "orders": orders,
        "positions": [],
        "executions": [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _order(issue_code: str, status: str, *, remaining_quantity: str) -> dict:
    return {
        "order_id_hash": f"order-{issue_code}-{status}",
        "issue_code": issue_code,
        "side": "buy",
        "quantity": "100",
        "executed_quantity": "0",
        "remaining_quantity": remaining_quantity,
        "status": status,
        "as_of": "2026-07-07T04:00:00+00:00",
    }
