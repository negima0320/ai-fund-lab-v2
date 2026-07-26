from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.phase20_ba_reselect_cross_regime_campaign import build_report


def test_phase20_ba_real_data_reports_required_regime_gap() -> None:
    report = build_report(quotes_path=Path(".runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet"))

    assert report["final_status"] == "PHASE20_BA_CAMPAIGN_RESELECTION_COMPLETE"
    assert report["campaign_ready"] is False
    assert report["readiness_judgment"] == "NOT_READY_DATA_COVERAGE_CONSTRAINT"
    assert report["eligible_window_count"] == 3
    assert report["missing_required_regimes"] == ["BULL", "BEAR", "RANGE"]
    assert {tuple(item["regime_labels"]) for item in report["eligible_windows"]} == {("HIGH_VOLATILITY",)}
    assert all(command.startswith("NOT_ISSUED") for command in report["user_execution_commands"].values())


def test_phase20_ba_fixture_selects_required_regimes_when_constraints_allow(tmp_path: Path) -> None:
    quotes = tmp_path / "quotes.parquet"
    rows = []
    dates = pd.bdate_range("2026-01-01", periods=150).strftime("%Y-%m-%d").tolist()
    for code_idx in range(60):
        price = 100.0 + code_idx
        for idx, date in enumerate(dates):
            if 65 <= idx < 85:
                drift = 0.01
            elif 90 <= idx < 110:
                drift = -0.01
            elif 112 <= idx < 132:
                drift = 0.0
            else:
                drift = 0.001 if idx % 2 == 0 else -0.001
            price *= 1.0 + drift
            rows.append({"Date": date, "Code": f"{1000 + code_idx}0", "Open": price, "High": price * 1.002, "Low": price * 0.998, "Close": price, "Volume": 1000})
    pd.DataFrame(rows).to_parquet(quotes, index=False)

    report = build_report(quotes_path=quotes)

    assert report["campaign_ready"] is True
    assert report["selected_campaigns"]["BULL"] is not None
    assert report["selected_campaigns"]["BEAR"] is not None
    assert report["selected_campaigns"]["RANGE"] is not None
    assert report["acceptance"]["BULL_SELECTED"] == "PASS"
    assert report["acceptance"]["BEAR_SELECTED"] == "PASS"
    assert report["acceptance"]["RANGE_SELECTED"] == "PASS"
