import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.broker import BrokerBalanceSnapshot, BrokerPositionSnapshot
from ai_fund_lab_v2.safety import (
    PortfolioPositionState,
    SafetyStatus,
    build_broker_state_from_snapshots,
    build_mock_portfolio_state_from_broker_state,
    run_safety_dry_run,
)


def test_safety_dry_run_outputs_report_lock_and_audit_for_ok(tmp_path: Path) -> None:
    broker_state = build_broker_state()
    portfolio_state = build_mock_portfolio_state_from_broker_state(broker_state)

    result = run_safety_dry_run(broker_state, portfolio_state, runtime_dir=tmp_path / ".runtime")

    assert result.report.status == SafetyStatus.OK
    assert result.lock.is_locked is False
    assert result.report_path.parent == tmp_path / ".runtime" / "safety" / "reports"
    assert result.lock_path.parent == tmp_path / ".runtime" / "safety" / "locks"
    assert result.audit_path.parent == tmp_path / ".runtime" / "safety" / "audit"
    assert result.report_path.is_file()
    assert result.lock_path.is_file()
    assert result.audit_path.is_file()
    audit_payload = json.loads(result.audit_path.read_text(encoding="utf-8"))
    assert audit_payload["status"] == "OK"
    assert audit_payload["trading_locked"] is False
    assert audit_payload["broker_snapshot_id"] == "balance-snapshot-1"


def test_safety_dry_run_halts_on_position_mismatch(tmp_path: Path) -> None:
    broker_state = build_broker_state()
    portfolio_state = build_mock_portfolio_state_from_broker_state(broker_state)
    mismatched_position = replace(portfolio_state.positions[0], quantity=Decimal("90"))
    mismatched_portfolio = replace(portfolio_state, positions=(mismatched_position,))

    result = run_safety_dry_run(broker_state, mismatched_portfolio, runtime_dir=tmp_path / ".runtime")

    assert result.report.status == SafetyStatus.HALT
    assert result.lock.is_locked is True
    assert result.report.trading_locked is True
    assert any(issue.code == "position_quantity_mismatch" for issue in result.report.issues)


def test_safety_dry_run_outputs_do_not_contain_secret_or_url(tmp_path: Path) -> None:
    broker_state = build_broker_state()
    portfolio_state = build_mock_portfolio_state_from_broker_state(broker_state)
    mismatched_position = PortfolioPositionState(
        symbol="7203",
        quantity=Decimal("90"),
        side="long",
        account_type="cash",
    )
    mismatched_portfolio = replace(portfolio_state, positions=(mismatched_position,))

    result = run_safety_dry_run(broker_state, mismatched_portfolio, runtime_dir=tmp_path / ".runtime")

    saved_text = (
        result.report_path.read_text(encoding="utf-8")
        + result.lock_path.read_text(encoding="utf-8")
        + result.audit_path.read_text(encoding="utf-8")
    )
    assert "secret" not in saved_text.lower()
    assert "http://" not in saved_text.lower()
    assert "https://" not in saved_text.lower()


def build_broker_state():
    return build_broker_state_from_snapshots(
        balance_snapshot=BrokerBalanceSnapshot(
            snapshot_id="balance-snapshot-1",
            as_of="2999-01-01T00:00:00+00:00",
            cash_available=Decimal("1000000"),
            buying_power=Decimal("800000"),
        ),
        position_snapshots=(BrokerPositionSnapshot(issue_code="7203", quantity=Decimal("100"), account_type="cash"),),
    )
