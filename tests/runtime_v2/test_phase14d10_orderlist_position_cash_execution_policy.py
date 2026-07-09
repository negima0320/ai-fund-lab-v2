from ai_fund_lab_v2.runtime_v2.broker_readonly.normalizer import normalize_broker_readonly_payload
from ai_fund_lab_v2.runtime_v2.execution.fill_classifier import classify_orderlist_position_cash_fill
from ai_fund_lab_v2.runtime_v2.execution.models import FillClassificationType
from ai_fund_lab_v2.runtime_v2.ledger.models import LedgerEventRecord
from ai_fund_lab_v2.runtime_v2.report.builder import build_runtime_report
from ai_fund_lab_v2.runtime_v2.report.models import ReportBuildInput


def test_phase14d10_order_list_detail_missing_is_not_review_when_position_and_cash_corroborate():
    bundle = _bundle(include_position=True, include_cash=True)
    result = classify_orderlist_position_cash_fill(
        order=bundle.orders[0],
        positions=bundle.positions,
        cash=bundle.cash,
        executions=(),
    )

    assert result.classification.classification == FillClassificationType.ORDER_LIST_DERIVED_FULL_FILL
    assert result.classification.review_required is False
    assert result.execution_equivalent is True
    assert result.detail_optional_missing is True
    assert result.ledger_execution_allowed is True
    assert result.asset_reflection_allowed is True
    assert "CLMOrderListDetail" not in result.evidence_sources


def test_phase14d10_order_list_only_does_not_become_execution_equivalent():
    bundle = _bundle(include_position=False, include_cash=True)
    result = classify_orderlist_position_cash_fill(
        order=bundle.orders[0],
        positions=bundle.positions,
        cash=bundle.cash,
        executions=(),
    )

    assert result.execution_equivalent is False
    assert result.ledger_execution_allowed is False
    assert result.asset_reflection_allowed is False
    assert result.detail_optional_missing is True


def test_phase14d10_report_can_note_detail_optional_missing():
    event = LedgerEventRecord(
        record_id="ledger-event-detail-optional-missing",
        record_type="event",
        schema_version="1",
        environment="demo",
        source="phase14d10_policy_test",
        created_at="2026-07-07",
        dedup_key="detail_optional_missing:7203",
        event_id="detail_optional_missing:7203",
        event_type="detail_optional_missing",
        severity="INFO",
        message="CLMOrderListDetail missing; OrderList/Position/Cash evidence used",
        related_id="7203",
    )

    report = build_runtime_report(
        ReportBuildInput(
            mode="demo",
            environment="demo",
            business_date="2026-07-07",
            target_session_date="2026-07-07",
            review_events=(event,),
        )
    )

    review_section = next(section for section in report.sections if section.section_id == "review_required_summary")
    assert "detail_optional_missing" in review_section.content


def _bundle(*, include_position: bool, include_cash: bool):
    return normalize_broker_readonly_payload(
        environment="demo",
        source="phase14d10_policy_test",
        as_of="2026-07-07T00:00:00+00:00",
        orders=(
            {
                "order_ref": "order-7203",
                "symbol": "7203",
                "side": "BUY",
                "quantity": 100,
                "order_status": "全部約定",
                "filled_quantity": 100,
                "remaining_quantity": 0,
            },
        ),
        positions=(
            (
                {
                    "position_ref": "position-7203",
                    "position_key": "7203",
                    "symbol": "7203",
                    "quantity": 100,
                    "average_price": 3000,
                    "market_value": 300000,
                },
            )
            if include_position
            else ()
        ),
        cash=(
            {"cash_ref": "cash-1", "cash": 19700000, "buying_power": 19700000, "currency": "JPY"}
            if include_cash
            else None
        ),
    )
