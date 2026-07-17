from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.current_state.valuation import run_current_valuation_refresh
from ai_fund_lab_v2.runtime_v2.data_readiness import evaluate_runtime_data_readiness

from tests.runtime_v2.test_phase15az_current_valuation_no_fill_producer import (
    BUSINESS_DATE as VALUATION_BUSINESS_DATE,
)
from tests.runtime_v2.test_phase15az_current_valuation_no_fill_producer import (
    _load_json as _load_valuation_json,
)
from tests.runtime_v2.test_phase15az_current_valuation_no_fill_producer import (
    _now as _valuation_now,
)
from tests.runtime_v2.test_phase15az_current_valuation_no_fill_producer import (
    _runtime_root as _valuation_runtime_root,
)
from tests.runtime_v2.test_phase15az_current_valuation_no_fill_producer import (
    _write_current as _write_valuation_current,
)
from tests.runtime_v2.test_phase15az_current_valuation_no_fill_producer import (
    _write_market as _write_valuation_market,
)
from tests.runtime_v2.test_phase17_af_day2_morning_temporal_authority import (
    BUSINESS_DATE as DAY2_BUSINESS_DATE,
)
from tests.runtime_v2.test_phase17_af_day2_morning_temporal_authority import (
    PREVIOUS_TRADING_DATE as DAY2_PREVIOUS_TRADING_DATE,
)
from tests.runtime_v2.test_phase17_af_day2_morning_temporal_authority import (
    PROFILE_ID,
    RUN_ID,
)
from tests.runtime_v2.test_phase17_af_day2_morning_temporal_authority import (
    _runtime_root as _readiness_runtime_root,
)
from tests.runtime_v2.test_phase17_af_day2_morning_temporal_authority import (
    _write_feature_inputs,
)
from tests.runtime_v2.test_phase17_af_day2_morning_temporal_authority import (
    _write_model,
)


def test_phase17_bh_day2_precondition_accepts_previous_close_before_projection(tmp_path: Path) -> None:
    root = _readiness_runtime_root(
        tmp_path,
        valuation_as_of=DAY2_PREVIOUS_TRADING_DATE,
        historical=True,
        safety_missing=True,
    )
    feature_root = _write_feature_inputs(root / "operations" / "feature_artifacts")

    result = evaluate_runtime_data_readiness(
        runtime_root=root,
        business_date=DAY2_BUSINESS_DATE,
        mode="historical",
        readiness_scope="current_valuation",
        feature_root=feature_root,
        feature_date=DAY2_BUSINESS_DATE,
        candidate_model_path=_write_model(tmp_path / "candidate.pkl"),
        opportunity_model_path=_write_model(tmp_path / "opportunity.pkl"),
        now=datetime.fromisoformat("2026-07-07T15:35:00+09:00"),
        runtime_test_evidence_root=tmp_path / "reports" / "runtime_tests" / "runs" / RUN_ID,
        runtime_test_run_id=RUN_ID,
        runtime_test_profile_id=PROFILE_ID,
        broker_environment="historical_simulated",
        broker_write=False,
        external_delivery=False,
    )

    assert result.status == "READY"
    assert result.payload["current_valuation_status"] == "READY"
    assert result.payload["current_valuation_expected_date"] == DAY2_BUSINESS_DATE
    assert result.payload["current_valuation_expected_date_policy"] == "current_valuation_refresh_precondition"
    assert result.payload["current_valuation_temporal_authority"] == "current_valuation_previous_close_ready_for_refresh"
    assert result.payload["current_valuation_temporal_reason"] == "previous_trading_day_close_ready_for_current_valuation_refresh"
    assert result.payload["current_valuation_close_confirmed"] is False
    assert result.payload["valuation_refresh_precondition_status"] == "PASS"
    assert "current_valuation_not_ready" not in result.payload["review_reasons"]


def test_phase17_bh_day2_apply_updates_ledger_to_business_date(tmp_path: Path) -> None:
    root = _valuation_runtime_root(tmp_path)
    _write_valuation_current(root, valuation_as_of="2026-07-09", source_market_date="2026-07-09")
    _write_valuation_market(root, market_date=VALUATION_BUSINESS_DATE, price=1100)

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=VALUATION_BUSINESS_DATE,
        apply_current_valuation=True,
        now=_valuation_now(),
    )
    current = _load_valuation_json(root / "persistent_ledger" / "state.json")

    assert result.status == "READY"
    assert result.apply_executed is True
    assert result.projection_status == "PASS"
    assert result.apply_status == "APPLIED"
    assert result.postcondition_status == "PASS"
    assert result.post_apply_valuation_as_of == VALUATION_BUSINESS_DATE
    assert result.post_apply_source_market_date == VALUATION_BUSINESS_DATE
    assert current["valuation_as_of"] == VALUATION_BUSINESS_DATE
    assert current["source_market_date"] == VALUATION_BUSINESS_DATE
    assert current["positions"][0]["valuation_as_of"] == VALUATION_BUSINESS_DATE
    assert current["positions"][0]["source_market_date"] == VALUATION_BUSINESS_DATE


def test_phase17_bh_no_action_day_still_refreshes_current_valuation(tmp_path: Path) -> None:
    root = _valuation_runtime_root(tmp_path)
    _write_valuation_current(root, valuation_as_of="2026-07-09", source_market_date="2026-07-09")
    _write_valuation_market(root, market_date=VALUATION_BUSINESS_DATE, price=1120)

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=VALUATION_BUSINESS_DATE,
        apply_current_valuation=True,
        now=_valuation_now(),
    )

    assert result.status == "READY"
    assert result.no_fill is True
    assert result.position_count == 1
    assert result.valued_position_count == 1
    assert result.new_total_market_value == 112000


def test_phase17_bh_quote_missing_fails_closed(tmp_path: Path) -> None:
    root = _valuation_runtime_root(tmp_path)
    _write_valuation_current(root, valuation_as_of="2026-07-09", source_market_date="2026-07-09")
    _write_valuation_market(root, market_date=VALUATION_BUSINESS_DATE, quotes={})

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=VALUATION_BUSINESS_DATE,
        apply_current_valuation=True,
        now=_valuation_now(),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False
    assert result.projection_status == "REVIEW_REQUIRED"
    assert result.postcondition_status == "NOT_EXECUTED"
    assert result.missing_symbols == ("7203",)


def test_phase17_bh_stale_precondition_fails_closed(tmp_path: Path) -> None:
    root = _readiness_runtime_root(tmp_path, valuation_as_of="2026-07-03")
    feature_root = _write_feature_inputs(root / "operations" / "feature_artifacts")

    result = evaluate_runtime_data_readiness(
        runtime_root=root,
        business_date=DAY2_BUSINESS_DATE,
        mode="demo",
        readiness_scope="current_valuation",
        feature_root=feature_root,
        feature_date=DAY2_BUSINESS_DATE,
        candidate_model_path=_write_model(tmp_path / "candidate.pkl"),
        opportunity_model_path=_write_model(tmp_path / "opportunity.pkl"),
        now=datetime.fromisoformat("2026-07-07T15:35:00+09:00"),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.payload["current_valuation_temporal_reason"] == "current_valuation_older_than_previous_trading_day"
    assert "current_valuation_not_ready" in result.payload["review_reasons"]


def test_phase17_bh_future_valuation_fails_closed(tmp_path: Path) -> None:
    root = _readiness_runtime_root(tmp_path, valuation_as_of="2026-07-08")
    feature_root = _write_feature_inputs(root / "operations" / "feature_artifacts")

    result = evaluate_runtime_data_readiness(
        runtime_root=root,
        business_date=DAY2_BUSINESS_DATE,
        mode="demo",
        readiness_scope="current_valuation",
        feature_root=feature_root,
        feature_date=DAY2_BUSINESS_DATE,
        candidate_model_path=_write_model(tmp_path / "candidate.pkl"),
        opportunity_model_path=_write_model(tmp_path / "opportunity.pkl"),
        now=datetime.fromisoformat("2026-07-07T15:35:00+09:00"),
    )

    assert result.status == "HALT"
    assert result.payload["current_valuation_temporal_reason"] == "current_valuation_future_date"


def test_phase17_bh_apply_postcondition_fails_closed_when_ledger_not_updated(tmp_path: Path, monkeypatch) -> None:
    root = _valuation_runtime_root(tmp_path)
    _write_valuation_current(root, valuation_as_of="2026-07-09", source_market_date="2026-07-09")
    _write_valuation_market(root, market_date=VALUATION_BUSINESS_DATE, price=1100)

    def _skip_write_current(*, root: Path, source_path: Path, payload: dict, now: datetime | None) -> Path:
        backup_path = root / "persistent_ledger" / "history" / "current" / "skipped-write.json"
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_text(json.dumps({"skipped": True}, sort_keys=True) + "\n", encoding="utf-8")
        return backup_path

    monkeypatch.setattr("ai_fund_lab_v2.runtime_v2.current_state.valuation._atomic_write_current", _skip_write_current)

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=VALUATION_BUSINESS_DATE,
        apply_current_valuation=True,
        now=_valuation_now(),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "current_valuation_postcondition_failed"
    assert result.projection_status == "PASS"
    assert result.apply_status == "APPLIED"
    assert result.postcondition_status == "REVIEW_REQUIRED"
    assert "post_apply_valuation_as_of_mismatch" in result.postcondition_reason


def test_phase17_bh_historical_asof_market_authority_used_for_same_business_date(tmp_path: Path) -> None:
    try:
        import pandas as pd
    except ImportError:
        return

    root = _valuation_runtime_root(tmp_path)
    _write_valuation_current(root, valuation_as_of="2026-07-09", source_market_date="2026-07-09")
    normalized = tmp_path / "normalized_ohlcv.parquet"
    pd.DataFrame([{"target_date": VALUATION_BUSINESS_DATE, "code": "7203", "close": 1110.0}]).to_parquet(normalized, index=False)
    asof_view = tmp_path / "historical_asof_view.json"
    asof_view.write_text(
        json.dumps(
            {
                "schema_version": "phase17_l_historical_asof_view_v1",
                "status": "PASS",
                "business_date": VALUATION_BUSINESS_DATE,
                "latest_available_market_date": VALUATION_BUSINESS_DATE,
                "authorities": [
                    {
                        "authority": "normalized_ohlcv",
                        "status": "PASS",
                        "physical_source_path": str(normalized),
                    }
                ],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=VALUATION_BUSINESS_DATE,
        apply_current_valuation=True,
        market_evidence_path=asof_view,
        now=datetime(2026, 7, 10, 6, 35, tzinfo=timezone.utc),
    )

    assert result.status == "READY"
    assert result.market_date == VALUATION_BUSINESS_DATE
    assert result.projection_source_market_date == VALUATION_BUSINESS_DATE
    assert result.candidate_current["positions"][0]["current_price"] == 1110.0
