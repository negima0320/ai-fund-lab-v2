from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.paper_trading.first_daily_run import (
    FIRST_RUN_PENDING_ORDERS_CREATED,
    FIRST_RUN_READY_FOR_REVIEW,
    run_first_daily_paper_trading_run,
)
from ai_fund_lab_v2.paper_trading.initial_ledger import create_initial_ledger
from ai_fund_lab_v2.paper_trading.ledger import load_ledger
from tests.paper_trading.test_phase9l2_daily_inference_runner import _write_l2_inputs


def test_review_only_first_run_does_not_mutate_ledger_and_generates_review_request(tmp_path: Path) -> None:
    feature_root, quotes_path = _write_l2_inputs(tmp_path)
    ledger_path = _create_ledger(tmp_path)
    before = Path(ledger_path).read_text(encoding="utf-8")

    result = run_first_daily_paper_trading_run(
        decision_for="2026-06-15",
        data_until="2026-06-15",
        ledger_path=ledger_path,
        mode="review-only",
        runtime_dir=tmp_path / ".runtime",
        reports_root=tmp_path / "reports",
        feature_root=feature_root,
        canonical_quotes_path=quotes_path,
        approval_mode="manual_required",
    )

    assert result.status == FIRST_RUN_READY_FOR_REVIEW
    assert result.pending_order_created is False
    assert result.ledger_changed is False
    assert Path(ledger_path).read_text(encoding="utf-8") == before
    assert Path(result.human_review_json_path).is_file()
    assert Path(result.tracker_marker_path).is_file()
    assert result.order_plan_count > 0
    assert not any(result.prohibited_flags.values())


def test_paper_trading_without_approved_review_does_not_create_pending_orders(tmp_path: Path) -> None:
    feature_root, quotes_path = _write_l2_inputs(tmp_path)
    ledger_path = _create_ledger(tmp_path)

    result = run_first_daily_paper_trading_run(
        decision_for="2026-06-15",
        data_until="2026-06-15",
        ledger_path=ledger_path,
        mode="paper-trading",
        runtime_dir=tmp_path / ".runtime",
        reports_root=tmp_path / "reports",
        feature_root=feature_root,
        canonical_quotes_path=quotes_path,
        approval_mode="manual_required",
    )

    assert result.status == FIRST_RUN_READY_FOR_REVIEW
    assert result.review_status == "pending"
    assert result.pending_order_created is False
    assert len(load_ledger(ledger_path).pending_orders) == 0


def test_paper_trading_with_approved_review_creates_pending_orders_without_fill(tmp_path: Path) -> None:
    feature_root, quotes_path = _write_l2_inputs(tmp_path)
    ledger_path = _create_ledger(tmp_path)
    review_only = run_first_daily_paper_trading_run(
        decision_for="2026-06-15",
        data_until="2026-06-15",
        ledger_path=ledger_path,
        mode="review-only",
        runtime_dir=tmp_path / ".runtime",
        reports_root=tmp_path / "reports",
        feature_root=feature_root,
        canonical_quotes_path=quotes_path,
    )
    approved = _approved_review(Path(review_only.human_review_json_path), tmp_path)

    result = run_first_daily_paper_trading_run(
        decision_for="2026-06-15",
        data_until="2026-06-15",
        ledger_path=ledger_path,
        mode="paper-trading",
        runtime_dir=tmp_path / ".runtime",
        reports_root=tmp_path / "reports",
        feature_root=feature_root,
        canonical_quotes_path=quotes_path,
        human_review_path=approved,
        approval_mode="manual_required",
    )
    latest = load_ledger(tmp_path / ".runtime" / "phase9" / "ledger" / "latest.json")

    assert result.status == FIRST_RUN_PENDING_ORDERS_CREATED
    assert result.review_status == "approved"
    assert result.pending_order_created is True
    assert result.pending_order_count > 0
    assert len(latest.positions) == 0
    assert latest.cash == Decimal("1000000")
    assert len(latest.pending_orders) == result.pending_order_count
    assert result.prohibited_flags["virtual_fill_executed"] is False


def _create_ledger(tmp_path: Path) -> Path:
    result = create_initial_ledger(
        initial_cash=Decimal("1000000"),
        currency="JPY",
        ledger_root=tmp_path / ".runtime" / "phase9" / "ledger",
        start_date="2026-06-16",
    )
    return Path(result.latest_path)


def _approved_review(path: Path, tmp_path: Path) -> Path:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["review_status"] = "approved"
    payload["reviewed_at"] = "2026-06-16T00:00:00+00:00"
    payload["reviewer_note"] = "test approval"
    approved = tmp_path / "approved_review.json"
    approved.write_text(json.dumps(payload), encoding="utf-8")
    return approved
