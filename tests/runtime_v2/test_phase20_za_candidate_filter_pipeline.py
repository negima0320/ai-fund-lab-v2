from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.inspect_phase20_za_candidate_filter_pipeline import build_report


REQUIRED_FEATURES = [
    "liquidity_avg_volume_20d",
    "missing_flags_insufficient_history",
    "missing_flags_price",
    "missing_flags_volume",
    "price_momentum_return_20d",
    "price_momentum_return_5d",
    "price_momentum_return_60d",
    "trend_close_over_ma_20d",
    "trend_ma_20_60_ratio",
    "trend_ma_5_20_ratio",
    "volatility_return_std_20d",
    "volume_momentum_ratio_1d_20d",
    "volume_momentum_ratio_5d",
]


def test_phase20_za_filter_pipeline_identifies_universe_filter_as_first_zero(tmp_path: Path) -> None:
    target_feature = tmp_path / "target.parquet"
    control_feature = tmp_path / "control.parquet"
    target_quotes = tmp_path / "target_quotes.parquet"
    control_quotes = tmp_path / "control_quotes.parquet"
    target_manifest = tmp_path / "target_manifest.json"
    control_manifest = tmp_path / "control_manifest.json"
    _write_manifest(target_manifest, "REVIEW_REQUIRED", "candidate_feature_rows_empty", 0)
    _write_manifest(control_manifest, "PASS", "", 2)
    pd.DataFrame([_row("2026-03-24", "10010", eligible=False), _row("2026-03-24", "10020", eligible=False)]).to_parquet(target_feature, index=False)
    pd.DataFrame([_row("2026-06-16", "10010", eligible=True), _row("2026-06-16", "10020", eligible=False)]).to_parquet(control_feature, index=False)
    _write_quotes(target_quotes, "2026-02-16", 25)
    _write_quotes(control_quotes, "2026-02-16", 81)

    report = build_report(
        target_feature=target_feature,
        control_feature=control_feature,
        target_date="2026-03-24",
        control_date="2026-06-16",
        target_manifest=target_manifest,
        control_manifest=control_manifest,
        target_quotes=target_quotes,
        control_quotes=control_quotes,
    )

    assert report["root_cause_classification"] == "ALL_ROWS_MISSING_HISTORY"
    assert report["candidate_feature_rows_empty_code_path"]["first_zero_stage"] == "universe_eligible true"
    assert report["comparison"]["eligible_row_count_after_producer_filters"]["target"] == 0
    assert report["comparison"]["eligible_row_count_after_producer_filters"]["control"] == 1
    assert report["source_quote_coverage"]["target_median_symbol_history_satisfies_60bd"] is False
    assert report["source_quote_coverage"]["control_median_symbol_history_satisfies_60bd"] is True
    assert report["runtime_bug_or_fail_closed"]["repair_required"] is False


def _row(date: str, code: str, *, eligible: bool) -> dict[str, object]:
    values: dict[str, object] = {
        "as_of_date": date,
        "target_date": date,
        "code": code,
        "data_until": date,
        "data_end_date": date,
        "universe_eligible": eligible,
        "excluded_reason": "" if eligible else "insufficient_lookback",
        "universe_exclusion_reason": "" if eligible else "insufficient_lookback",
        "is_current_listed": True,
        "has_current_name": True,
        "is_fresh_price": True,
        "is_allowed_product": True,
        "missing_flags_insufficient_history": not eligible,
        "missing_flags_price": not eligible,
        "missing_flags_volume": False,
    }
    for feature in REQUIRED_FEATURES:
        values.setdefault(feature, 1.0 if eligible else None)
    values["missing_flags_insufficient_history"] = not eligible
    values["missing_flags_price"] = not eligible
    values["missing_flags_volume"] = False
    return values


def _write_manifest(path: Path, status: str, reason: str, count: int) -> None:
    path.write_text(
        json.dumps(
            {
                "candidate_required_columns": REQUIRED_FEATURES,
                "buy_ai_status": status,
                "buy_ai_reason": reason,
                "candidate_count": count,
            }
        ),
        encoding="utf-8",
    )


def _write_quotes(path: Path, start: str, periods: int) -> None:
    rows = []
    dates = pd.bdate_range(start, periods=periods).strftime("%Y-%m-%d").tolist()
    for code in ("10010", "10020"):
        for idx, date in enumerate(dates):
            rows.append({"Date": date, "Code": code, "Close": 100 + idx, "Volume": 1000})
    pd.DataFrame(rows).to_parquet(path, index=False)
