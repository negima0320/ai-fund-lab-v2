import json
from pathlib import Path

from ai_fund_lab_v2.safety_phase11.integrated_backtest_audit import (
    AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER,
    IntegratedBacktestAuditConfig,
    run_integrated_backtest_audit,
)
from ai_fund_lab_v2.safety_phase11.models import SafetyReviewClass


def test_mainline_adapter_non_blocking_reviews_reach_virtual_fill(tmp_path):
    result = run_integrated_backtest_audit(
        IntegratedBacktestAuditConfig(
            period_id="fixture_non_blocking_review_policy",
            start_date="2025-06-01",
            end_date="2025-08-31",
            output_subdir="fixture_non_blocking_review_policy",
            reports_dir=tmp_path / "reports",
            docs_dir=tmp_path / "docs" / "phase_reports",
            max_days=45,
            audit_profile=AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER,
        )
    )
    order_decisions = json.loads(Path(result.flow_counts["order_decisions_path"]).read_text(encoding="utf-8"))["order_decisions"]
    non_blocking = [item for item in order_decisions if item["review_class"] == SafetyReviewClass.NON_BLOCKING_REVIEW.value]

    assert non_blocking
    assert all(item["fill_allowed"] is True for item in non_blocking)
    assert any(item["filled"] is True for item in non_blocking)
    assert result.flow_counts["orders_review_required"] == 0
    assert result.flow_counts["non_blocking_review_order_count"] == len(non_blocking)


def test_mainline_adapter_max_exposure_blocks_buy_not_sell(tmp_path):
    result = run_integrated_backtest_audit(
        IntegratedBacktestAuditConfig(
            period_id="fixture_max_exposure_buy_only",
            start_date="2025-06-01",
            end_date="2025-08-31",
            output_subdir="fixture_max_exposure_buy_only",
            reports_dir=tmp_path / "reports",
            docs_dir=tmp_path / "docs" / "phase_reports",
            max_days=45,
            audit_profile=AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER,
        )
    )
    order_decisions = json.loads(Path(result.flow_counts["order_decisions_path"]).read_text(encoding="utf-8"))["order_decisions"]
    max_exposure = [item for item in order_decisions if "MAX_EXPOSURE_EXCEEDED" in item["blocking_reason_codes"]]
    sell_orders = [item for item in order_decisions if item["side"] == "SELL"]

    assert max_exposure
    assert all(item["side"] == "BUY" for item in max_exposure)
    assert sell_orders
    assert all("MAX_EXPOSURE_EXCEEDED" not in item["blocking_reason_codes"] for item in sell_orders)
