from pathlib import Path

from ai_fund_lab_v2.broker.settings import BrokerSettings
from ai_fund_lab_v2.broker import phase14d5_pure_retest
from ai_fund_lab_v2.broker.phase14d5_pure_retest import run_phase14d5_pure_runtime_v2_demo_buy_retest
from ai_fund_lab_v2.runtime_v2.submit.models import RuntimeV2SubmitCommand, RuntimeV2SubmitResult


class AcceptingAdapter:
    def preflight(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        assert command.source_current_path == "pending_order_plan/pending_order_plan.json"
        assert command.symbol == "7203"
        return RuntimeV2SubmitResult(
            status="DRY_RUN_READY",
            submitted=False,
            accepted=False,
            blocked=False,
            review_required=False,
            broker_api_called=False,
            reason="test dry-run ready",
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
            broker_order_id_hash="sha256:test-order",
            reason="accepted",
        )


def test_phase14d5_harness_uses_runtime_v2_command_and_generates_report_without_broker_api(tmp_path, monkeypatch):
    def fake_snapshot(*, settings, report_path: Path, snapshot_path: Path, symbol: str, source: str) -> str:
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(
            """
{
  "generated_at": "2026-07-07T00:00:00+00:00",
  "buying_power": {"cash_ref": "cash-1", "cash": 1000000, "buying_power": 1000000, "currency": "JPY"},
  "positions": [],
  "orders": [{"order_ref": "order-1", "order_id": "order-1", "symbol": "7203", "side": "BUY", "quantity": 100, "status": "ACCEPTED"}],
  "executions": []
}
""".strip()
            + "\n",
            encoding="utf-8",
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("{}\n", encoding="utf-8")
        return "PASS"

    monkeypatch.setattr(phase14d5_pure_retest, "_readonly_snapshot", fake_snapshot)

    result = run_phase14d5_pure_runtime_v2_demo_buy_retest(
        root=tmp_path / "runtime",
        docs_report_path=tmp_path / "docs" / "phase14_d5.md",
        json_report_path=tmp_path / "reports" / "phase14_d5.json",
        adapter=AcceptingAdapter(),
        settings=BrokerSettings(environment="demo", base_url="https://demo-kabuka.e-shiten.jp/e_api_v4r9"),
        symbol="7203",
        quantity=100.0,
        estimated_price=3000.0,
    )

    assert result.final_decision == "PHASE14D5_PURE_RUNTIME_V2_DEMO_BUY_PASS"
    assert result.runtime_v2_pure_submit_path is True
    assert result.legacy_order_command_submit_authority_used is False
    assert result.legacy_runtime_mode_submit_authority_used is False
    assert result.demo_submit_executed is True
    assert result.order_status_readonly_confirmed is True
    assert result.notification_sent is False


def test_phase14d5_harness_blocks_9000_series_without_submit(tmp_path, monkeypatch):
    def fake_snapshot(*, settings, report_path: Path, snapshot_path: Path, symbol: str, source: str) -> str:
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(
            '{"generated_at":"2026-07-07T00:00:00+00:00","buying_power":{"cash_ref":"cash-1","cash":1000000,"buying_power":1000000,"currency":"JPY"}}\n',
            encoding="utf-8",
        )
        return "PASS"

    monkeypatch.setattr(phase14d5_pure_retest, "_readonly_snapshot", fake_snapshot)

    result = run_phase14d5_pure_runtime_v2_demo_buy_retest(
        root=tmp_path / "runtime",
        docs_report_path=tmp_path / "docs" / "phase14_d5.md",
        json_report_path=tmp_path / "reports" / "phase14_d5.json",
        adapter=AcceptingAdapter(),
        settings=BrokerSettings(environment="demo", base_url="https://demo-kabuka.e-shiten.jp/e_api_v4r9"),
        symbol="9432",
        quantity=100.0,
        estimated_price=200.0,
    )

    assert result.final_decision == "PHASE14D5_REVIEW_REQUIRED"
    assert result.demo_submit_executed is False
    assert "9000-series symbols excluded" in result.blocked_reasons
