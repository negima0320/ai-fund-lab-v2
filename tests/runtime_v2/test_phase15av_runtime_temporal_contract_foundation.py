from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ai_fund_lab_v2.runtime_v2.temporal import (
    CurrentTemporalState,
    FreshnessStatus,
    PublicationWindow,
    evaluate_current_valuation_freshness,
    evaluate_market_freshness,
    evaluate_safety_temporal_status,
    resolve_temporal_context,
    worst_freshness_status,
)


JST = ZoneInfo("Asia/Tokyo")


def test_phase15av_trading_day_market_ready(tmp_path):
    context = resolve_temporal_context(
        runtime_business_date="2026-07-10",
        latest_available_market_date="2026-07-10",
        now=datetime(2026, 7, 10, 9, 0, tzinfo=JST),
        root=tmp_path,
    )

    evidence = evaluate_market_freshness(context=context, actual_date="2026-07-10")

    assert evidence.status == FreshnessStatus.READY
    assert evidence.expected_date == "2026-07-10"
    assert evidence.actual_date == "2026-07-10"
    assert evidence.comparison_contract == "market_latest_expected_trading_date"


def test_phase15av_non_trading_day_valid_carryover(tmp_path):
    context = resolve_temporal_context(
        runtime_business_date="2026-07-11",
        latest_available_market_date="2026-07-10",
        now=datetime(2026, 7, 11, 9, 0, tzinfo=JST),
        root=tmp_path,
    )

    evidence = evaluate_market_freshness(context=context, actual_date="2026-07-10")

    assert evidence.status == FreshnessStatus.VALID_CARRYOVER
    assert context.latest_expected_trading_date == "2026-07-10"
    assert context.is_non_trading_carryover_day is True


def test_phase15av_before_publication_window_is_data_not_yet_available(tmp_path):
    publication_window = PublicationWindow(
        expected_available_at=datetime(2026, 7, 10, 15, 30, tzinfo=JST),
        grace_period=timedelta(minutes=30),
    )
    context = resolve_temporal_context(
        runtime_business_date="2026-07-10",
        latest_available_market_date="2026-07-09",
        publication_window=publication_window,
        now=datetime(2026, 7, 10, 10, 0, tzinfo=JST),
        root=tmp_path,
    )

    evidence = evaluate_market_freshness(
        context=context,
        actual_date="2026-07-09",
        now=datetime(2026, 7, 10, 10, 0, tzinfo=JST),
    )

    assert evidence.status == FreshnessStatus.DATA_NOT_YET_AVAILABLE
    assert evidence.reason == "market_data_not_yet_available"


def test_phase15av_after_publication_grace_is_stale(tmp_path):
    publication_window = PublicationWindow(
        expected_available_at=datetime(2026, 7, 10, 15, 30, tzinfo=JST),
        grace_period=timedelta(minutes=30),
    )
    context = resolve_temporal_context(
        runtime_business_date="2026-07-10",
        latest_available_market_date="2026-07-09",
        publication_window=publication_window,
        now=datetime(2026, 7, 10, 18, 0, tzinfo=JST),
        root=tmp_path,
    )

    evidence = evaluate_market_freshness(
        context=context,
        actual_date="2026-07-09",
        now=datetime(2026, 7, 10, 18, 0, tzinfo=JST),
    )

    assert evidence.status == FreshnessStatus.STALE
    assert evidence.reason == "market_evidence_stale_after_publication_window"


def test_phase15av_safety_expired_status(tmp_path):
    context = resolve_temporal_context(
        runtime_business_date="2026-07-10",
        now=datetime(2026, 7, 10, 9, 0, tzinfo=JST),
        root=tmp_path,
    )

    evidence = evaluate_safety_temporal_status(
        context=context,
        generated_at="2026-07-10T08:00:00+09:00",
        expires_at="2026-07-10T08:30:00+09:00",
        now=datetime(2026, 7, 10, 9, 0, tzinfo=JST),
    )

    assert evidence.status == FreshnessStatus.EXPIRED
    assert evidence.reason == "safety_decision_expired"


def test_phase15av_status_precedence_halt_review_ready():
    assert (
        worst_freshness_status(
            (
                FreshnessStatus.READY,
                FreshnessStatus.REVIEW_REQUIRED,
                FreshnessStatus.HALT,
            )
        )
        == FreshnessStatus.HALT
    )
    assert (
        worst_freshness_status(
            (
                FreshnessStatus.READY,
                FreshnessStatus.REVIEW_REQUIRED,
            )
        )
        == FreshnessStatus.REVIEW_REQUIRED
    )


def test_phase15av_current_temporal_model_fields_retained(tmp_path):
    context = resolve_temporal_context(
        runtime_business_date="2026-07-10",
        latest_available_market_date="2026-07-10",
        now=datetime(2026, 7, 10, 9, 0, tzinfo=JST),
        root=tmp_path,
    )
    current = CurrentTemporalState(
        position_state_as_of="2026-07-09",
        valuation_as_of="2026-07-10",
        last_execution_date="2026-07-09",
        last_reconciled_at="2026-07-10T08:00:00+09:00",
        source_market_date="2026-07-10",
    )

    evidence = evaluate_current_valuation_freshness(context=context, current=current)

    assert current.to_payload() == {
        "position_state_as_of": "2026-07-09",
        "valuation_as_of": "2026-07-10",
        "last_execution_date": "2026-07-09",
        "last_reconciled_at": "2026-07-10T08:00:00+09:00",
        "source_market_date": "2026-07-10",
    }
    assert evidence.status == FreshnessStatus.READY


def test_phase15av_temporal_resolver_is_deterministic(tmp_path):
    kwargs = {
        "runtime_business_date": "2026-07-10",
        "runtime_mode": "demo",
        "broker_environment": "demo",
        "latest_available_market_date": "2026-07-10",
        "now": datetime(2026, 7, 10, 9, 0, tzinfo=JST),
        "root": tmp_path,
    }

    first = resolve_temporal_context(**kwargs)
    second = resolve_temporal_context(**kwargs)

    assert first.to_payload() == second.to_payload()
