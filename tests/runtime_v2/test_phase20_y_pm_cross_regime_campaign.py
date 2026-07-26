from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.analyze_pm_cross_regime import analyze_runs, write_json
from scripts.phase20_y_prepare_pm_cross_regime_campaign import build_campaign_manifest


def _quotes(path: Path) -> list[str]:
    dates = pd.bdate_range("2026-01-01", periods=70).strftime("%Y-%m-%d").tolist()
    rows = []
    for symbol in ("11110", "22220"):
        price = 100.0
        for idx, date in enumerate(dates):
            price *= 1.0 + (0.002 if idx % 2 == 0 else -0.001)
            rows.append({"Date": date, "Code": symbol, "Open": price, "High": price + 1, "Low": price - 1, "Close": price, "Volume": 1000})
    pd.DataFrame(rows).to_parquet(path, index=False)
    return dates


def test_phase20_y_campaign_manifest_selects_ready_primary_periods_without_pm_outcomes(tmp_path: Path) -> None:
    quotes_path = tmp_path / "quotes.parquet"
    dates = _quotes(quotes_path)
    candidates_path = tmp_path / "candidates.json"
    write_json(
        candidates_path,
        {
            "candidate_periods": [
                _candidate("Run-A", "BULL", [], dates[0], dates[19], 0.05, 0.01),
                _candidate("Run-B", "BEAR", [], dates[1], dates[20], -0.06, 0.02),
                _candidate("Run-C", "RANGE", [], dates[49], dates[68], 0.0, 0.006),
                _candidate("Run-E", "LOW_VOLATILITY", ["RANGE"], dates[10], dates[29], 0.001, 0.005),
            ]
        },
    )

    manifest = build_campaign_manifest(candidate_periods_path=candidates_path, quotes_path=quotes_path)

    assert manifest["final_status"] == "PHASE20_Y_PM_CROSS_REGIME_VALIDATION_CAMPAIGN_READY"
    assert manifest["primary_campaign_periods"]["BULL"]["candidate_id"] == "Run-A"
    assert manifest["primary_campaign_periods"]["BEAR"]["candidate_id"] == "Run-B"
    assert manifest["primary_campaign_periods"]["RANGE"]["candidate_id"] == "Run-E"
    assert manifest["primary_campaign_periods"]["RANGE"]["campaign_selection_source"] == "SECONDARY_REGIME_DATA_AVAILABILITY_FALLBACK"
    assert manifest["selection_policy"]["pm_outcome_used_for_period_selection"] is False
    assert "--run-id <BULL_RUN_ID>" in manifest["cross_regime_analysis_command"]
    assert "--run-id <BEAR_RUN_ID>" in manifest["cross_regime_analysis_command"]
    assert "--run-id <RANGE_RUN_ID>" in manifest["cross_regime_analysis_command"]
    assert manifest["acceptance"]["RANGE_PRIMARY_READY"] == "PASS"


def test_phase20_y_analysis_outputs_required_horizons_and_metrics(tmp_path: Path) -> None:
    quotes_path = tmp_path / "quotes.parquet"
    dates = _quotes(quotes_path)
    candidate_path = tmp_path / "candidates.json"
    write_json(candidate_path, {"candidate_periods": [{"candidate_id": "Run-A", "start_date": dates[0], "end_date": dates[-1], "primary_regime": "BULL"}]})
    run_dir = tmp_path / "reports" / "runtime_tests" / "runs" / "run-1" / "daily" / dates[25] / "position_management"
    run_dir.mkdir(parents=True)
    write_json(
        run_dir / "pm_decisions.json",
        {
            "business_date": dates[25],
            "decisions": [
                {
                    "pm_decision_id": "pm-1",
                    "symbol": "11110",
                    "decision_type": "EXIT",
                    "dominant_cause": "EXIT_BY_HARD_STOP",
                    "decision_trace": {"technical_features": {"volatility_return_std_20d": 0.09}},
                }
            ],
        },
    )

    report = analyze_runs(
        run_ids=("run-1",),
        evidence_root=tmp_path / "reports" / "runtime_tests",
        quotes_path=quotes_path,
        candidate_periods_path=candidate_path,
    )

    stats = report["aggregates_by_action"]["EXIT"]
    for horizon in ("return_1bd", "return_5bd", "return_10bd", "return_20bd"):
        assert horizon in stats
        assert "negative_rate" in stats[horizon]
        assert "p25" in stats[horizon]
        assert "p75" in stats[horizon]
        assert stats[horizon]["count_with_return"] == 1


def _candidate(
    candidate_id: str,
    primary: str,
    secondary: list[str],
    start: str,
    end: str,
    period_return: float,
    volatility: float,
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "primary_regime": primary,
        "secondary_regime": secondary,
        "start_date": start,
        "end_date": end,
        "business_days": 20,
        "period_return": period_return,
        "realized_volatility": volatility,
        "breadth": 0.5,
        "selection_reason": "market data only",
        "data_completeness": {"status": "PASS", "min_symbol_count": 2, "median_symbol_count": 2},
    }
