#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_QUOTES_PATH = Path(".runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet")
DEFAULT_EVIDENCE_ROOT = Path("reports/runtime_tests")
DEFAULT_CANDIDATE_OUTPUT = Path("reports/phase_reports/phase20_pm_cross_regime_candidate_periods.json")
WINDOW_DAYS = 20
SIGNIFICANT_MOVE = 0.05
OUTCOME_HORIZONS = (1, 5, 10, 20)


REGIME_ORDER = (
    "BULL",
    "BEAR",
    "RANGE",
    "HIGH_VOLATILITY",
    "LOW_VOLATILITY",
    "SHARP_DROP_AND_REBOUND",
)


EXPECTED_CAUSES = (
    "EXIT_BY_HARD_STOP",
    "EXIT_BY_TREND_AND_EDGE_BREAK",
    "EXIT_BY_RISK_GUARD",
    "EXIT_BY_EXIT_SCORE_HIGH",
    "REDUCE_BY_WEAK_HOLD_SCORE",
    "REDUCE_BY_REDUCE_SCORE_THRESHOLD",
    "REDUCE_BY_HIGH_DOWNSIDE_RISK",
    "REDUCE_BY_PEAK_DRAWDOWN_WARNING",
    "REDUCE_BY_DRAWDOWN_WARNING",
    "REDUCE_BY_RISK_INCREASED_BUT_TREND_NOT_BROKEN",
    "HOLD_BY_STRONG_CONTINUATION",
    "HOLD_BY_PARTIAL_CONTINUATION",
    "HOLD_BY_FALLBACK",
    "ADD_BY_STRONG_TREND_AND_RANK",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only PM cross-regime candidate and run analysis")
    sub = parser.add_subparsers(dest="command", required=True)

    candidate = sub.add_parser("candidate-periods")
    candidate.add_argument("--quotes-path", default=str(DEFAULT_QUOTES_PATH))
    candidate.add_argument("--business-days", type=int, default=WINDOW_DAYS)
    candidate.add_argument("--output-json", default=str(DEFAULT_CANDIDATE_OUTPUT))
    candidate.add_argument("--print-json", action="store_true")

    analyze = sub.add_parser("analyze-runs")
    analyze.add_argument("--run-id", action="append", required=True)
    analyze.add_argument("--evidence-root", default=str(DEFAULT_EVIDENCE_ROOT))
    analyze.add_argument("--quotes-path", default=str(DEFAULT_QUOTES_PATH))
    analyze.add_argument("--candidate-periods-json", default=str(DEFAULT_CANDIDATE_OUTPUT))
    analyze.add_argument("--output-json", required=True)
    analyze.add_argument("--print-json", action="store_true")

    args = parser.parse_args()
    if args.command == "candidate-periods":
        report = build_candidate_period_report(quotes_path=Path(args.quotes_path), business_days=args.business_days)
        write_json(Path(args.output_json), report)
        if args.print_json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    if args.command == "analyze-runs":
        report = analyze_runs(
            run_ids=tuple(args.run_id),
            evidence_root=Path(args.evidence_root),
            quotes_path=Path(args.quotes_path),
            candidate_periods_path=Path(args.candidate_periods_json),
        )
        write_json(Path(args.output_json), report)
        if args.print_json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    return 2


def build_candidate_period_report(*, quotes_path: Path, business_days: int = WINDOW_DAYS) -> dict[str, Any]:
    quotes = read_quotes(quotes_path)
    completeness = market_data_completeness(quotes)
    proxy = build_market_proxy(quotes)
    windows = rolling_market_windows(proxy, business_days=business_days)
    thresholds = regime_thresholds(windows)
    classified = [classify_window(window, thresholds=thresholds) for window in windows]
    candidates = select_candidate_periods(classified)
    return {
        "schema_version": "phase20_t_pm_cross_regime_candidate_periods.v1",
        "authority": "READ_ONLY_EXISTING_JQUANTS_NORMALIZED_OHLCV",
        "quotes_path": str(quotes_path),
        "business_days": business_days,
        "data_completeness": completeness,
        "market_proxy_method": {
            "index_series_status": "NOT_FOUND_IN_REPOSITORY",
            "market_return_proxy": "equal_weight_mean_symbol_close_to_close_return",
            "breadth": "positive_symbol_ratio",
            "volatility": "realized_std_of_equal_weight_daily_returns",
            "outcome_leakage_policy": "NO_PM_OR_PORTFOLIO_OUTCOMES_USED_FOR_PERIOD_SELECTION",
        },
        "classification_thresholds": thresholds,
        "candidate_periods": candidates,
        "all_window_count": len(classified),
        "acceptance": {
            "PM_CANDIDATE_PERIODS_SELECTED_WITHOUT_OUTCOME_LEAKAGE": True,
            "LONG_RUNNING_HISTORICAL_TEST_EXECUTED": False,
        },
    }


def read_quotes(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(path, columns=["Date", "Code", "Open", "High", "Low", "Close", "Volume"])
    frame = frame.dropna(subset=["Date", "Code", "Close"]).copy()
    frame["Date"] = frame["Date"].astype(str)
    frame["Code"] = frame["Code"].map(normalize_symbol_code)
    return frame.sort_values(["Code", "Date"]).reset_index(drop=True)


def market_data_completeness(quotes: pd.DataFrame) -> dict[str, Any]:
    by_date = quotes.groupby("Date")["Code"].nunique().sort_index()
    dates = list(by_date.index.astype(str))
    missing_weekdays = continuous_weekday_missing_dates(dates)
    return {
        "oldest_business_date": dates[0] if dates else "",
        "latest_business_date": dates[-1] if dates else "",
        "business_day_count": len(dates),
        "row_count": int(len(quotes)),
        "available_symbol_count": int(quotes["Code"].nunique()),
        "symbols_per_day": {
            "min": int(by_date.min()) if len(by_date) else 0,
            "median": safe_float(by_date.median()) if len(by_date) else 0.0,
            "max": int(by_date.max()) if len(by_date) else 0,
        },
        "continuous_weekday_missing_dates": missing_weekdays,
        "continuous_weekday_missing_count": len(missing_weekdays),
        "daily_market_breadth_calculable": True,
        "index_series_available": False,
    }


def continuous_weekday_missing_dates(dates: list[str]) -> list[str]:
    if not dates:
        return []
    observed = set(dates)
    calendar = pd.date_range(dates[0], dates[-1], freq="B").strftime("%Y-%m-%d").tolist()
    return [date for date in calendar if date not in observed]


def build_market_proxy(quotes: pd.DataFrame) -> pd.DataFrame:
    frame = quotes.copy()
    frame["return_1bd"] = frame.groupby("Code")["Close"].pct_change()
    frame["high_low_range"] = (pd.to_numeric(frame["High"], errors="coerce") / pd.to_numeric(frame["Low"], errors="coerce")) - 1.0
    daily = (
        frame.dropna(subset=["return_1bd"])
        .groupby("Date")
        .agg(
            equal_weight_return=("return_1bd", "mean"),
            median_symbol_return=("return_1bd", "median"),
            positive_symbol_ratio=("return_1bd", lambda series: float((series > 0).mean())),
            symbol_count=("Code", "nunique"),
            mean_cross_sectional_volatility=("return_1bd", "std"),
            median_symbol_abs_return=("return_1bd", lambda series: float(series.abs().median())),
            median_intraday_high_low_range=("high_low_range", "median"),
            total_volume=("Volume", "sum"),
        )
        .reset_index()
        .sort_values("Date")
    )
    return daily.reset_index(drop=True)


def rolling_market_windows(proxy: pd.DataFrame, *, business_days: int) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    for start in range(0, len(proxy) - business_days + 1):
        window = proxy.iloc[start : start + business_days].copy()
        returns = window["equal_weight_return"].astype(float)
        cumulative = (1.0 + returns).cumprod()
        sharp = sharp_drop_rebound_stats(window)
        windows.append(
            {
                "start_date": str(window.iloc[0]["Date"]),
                "end_date": str(window.iloc[-1]["Date"]),
                "business_days": business_days,
                "period_return": safe_float(cumulative.iloc[-1] - 1.0),
                "daily_mean_return": safe_float(returns.mean()),
                "daily_median_return": safe_float(window["median_symbol_return"].mean()),
                "realized_volatility": safe_float(returns.std(ddof=1)),
                "mean_cross_sectional_volatility": safe_float(window["mean_cross_sectional_volatility"].mean()),
                "median_symbol_volatility": safe_float(window["median_symbol_abs_return"].mean()),
                "largest_decline": safe_float(returns.min()),
                "largest_rebound": safe_float(returns.max()),
                "breadth": safe_float(window["positive_symbol_ratio"].mean()),
                "high_low_range": safe_float(cumulative.max() / cumulative.min() - 1.0),
                "directional_persistence": safe_float(max((returns > 0).mean(), (returns < 0).mean())),
                "min_symbol_count": int(window["symbol_count"].min()),
                "median_symbol_count": safe_float(window["symbol_count"].median()),
                **sharp,
            }
        )
    return windows


def sharp_drop_rebound_stats(window: pd.DataFrame) -> dict[str, Any]:
    returns = window["equal_weight_return"].astype(float).tolist()
    dates = window["Date"].astype(str).tolist()
    best_drop = 0.0
    best_rebound_after_drop = 0.0
    best_path: dict[str, Any] = {}
    for start in range(len(returns)):
        for bottom in range(start, min(len(returns), start + 5)):
            drop = product_return(returns[start : bottom + 1])
            best_drop = min(best_drop, drop)
            if drop > -0.025:
                continue
            for rebound_end in range(bottom + 1, min(len(returns), bottom + 11)):
                rebound = product_return(returns[bottom + 1 : rebound_end + 1])
                if rebound > best_rebound_after_drop:
                    best_rebound_after_drop = rebound
                    best_path = {
                        "drop_start_date": dates[start],
                        "drop_bottom_date": dates[bottom],
                        "rebound_end_date": dates[rebound_end],
                        "drop_return": safe_float(drop),
                        "rebound_return": safe_float(rebound),
                    }
    return {
        "sharp_drop_return": safe_float(best_drop),
        "sharp_rebound_after_drop": safe_float(best_rebound_after_drop),
        "sharp_drop_rebound_path": best_path,
    }


def regime_thresholds(windows: list[dict[str, Any]]) -> dict[str, Any]:
    vols = pd.Series([item["realized_volatility"] for item in windows])
    return {
        "bull_period_return_min": 0.04,
        "bull_breadth_min": 0.50,
        "bear_period_return_max": -0.045,
        "bear_breadth_max": 0.49,
        "range_abs_period_return_max": 0.018,
        "range_high_low_range_max": 0.055,
        "high_volatility_quantile": 0.75,
        "high_volatility_min": safe_float(vols.quantile(0.75)),
        "low_volatility_quantile": 0.25,
        "low_volatility_max": safe_float(vols.quantile(0.25)),
        "sharp_drop_min_abs": -0.025,
        "sharp_rebound_min": 0.035,
        "classification_data_only": "existing_jquants_normalized_ohlcv_market_proxy",
    }


def classify_window(window: dict[str, Any], *, thresholds: dict[str, Any]) -> dict[str, Any]:
    labels: list[str] = []
    if window["period_return"] >= thresholds["bull_period_return_min"] and window["breadth"] >= thresholds["bull_breadth_min"]:
        labels.append("BULL")
    if window["period_return"] <= thresholds["bear_period_return_max"] and window["breadth"] <= thresholds["bear_breadth_max"]:
        labels.append("BEAR")
    if abs(window["period_return"]) <= thresholds["range_abs_period_return_max"] and window["high_low_range"] <= thresholds["range_high_low_range_max"]:
        labels.append("RANGE")
    if window["realized_volatility"] >= thresholds["high_volatility_min"]:
        labels.append("HIGH_VOLATILITY")
    if window["realized_volatility"] <= thresholds["low_volatility_max"]:
        labels.append("LOW_VOLATILITY")
    if (
        window["sharp_drop_return"] <= thresholds["sharp_drop_min_abs"]
        and window["sharp_rebound_after_drop"] >= thresholds["sharp_rebound_min"]
    ):
        labels.append("SHARP_DROP_AND_REBOUND")
    result = dict(window)
    result["regime_labels"] = labels or ["MIXED"]
    return result


def select_candidate_periods(windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selectors = {
        "Run-A": ("BULL", lambda row: (row["period_return"], row["breadth"])),
        "Run-B": ("BEAR", lambda row: (-row["period_return"], 1.0 - row["breadth"])),
        "Run-C": ("RANGE", lambda row: (-abs(row["period_return"]), -row["realized_volatility"])),
        "Run-D": ("HIGH_VOLATILITY", lambda row: (row["realized_volatility"], abs(row["period_return"]))),
        "Run-E": ("LOW_VOLATILITY", lambda row: (-row["realized_volatility"], -abs(row["period_return"]))),
        "Run-F": ("SHARP_DROP_AND_REBOUND", lambda row: (row["sharp_rebound_after_drop"], -row["sharp_drop_return"])),
    }
    selected: list[dict[str, Any]] = []
    for candidate_id, (regime, key_fn) in selectors.items():
        matches = [row for row in windows if regime in row["regime_labels"]]
        if not matches:
            continue
        chosen = sorted(matches, key=key_fn, reverse=True)[0]
        selected.append(candidate_row(candidate_id, regime, chosen))
    return selected


def candidate_row(candidate_id: str, regime: str, row: dict[str, Any]) -> dict[str, Any]:
    secondary = [label for label in row["regime_labels"] if label != regime]
    return {
        "candidate_id": candidate_id,
        "start_date": row["start_date"],
        "business_days": row["business_days"],
        "end_date": row["end_date"],
        "primary_regime": regime,
        "secondary_regime": secondary,
        "period_return": row["period_return"],
        "daily_mean_return": row["daily_mean_return"],
        "daily_median_return": row["daily_median_return"],
        "realized_volatility": row["realized_volatility"],
        "mean_cross_sectional_volatility": row["mean_cross_sectional_volatility"],
        "median_symbol_volatility": row["median_symbol_volatility"],
        "largest_decline": row["largest_decline"],
        "largest_rebound": row["largest_rebound"],
        "breadth": row["breadth"],
        "high_low_range": row["high_low_range"],
        "directional_persistence": row["directional_persistence"],
        "sharp_drop_return": row["sharp_drop_return"],
        "sharp_rebound_after_drop": row["sharp_rebound_after_drop"],
        "sharp_drop_rebound_path": row["sharp_drop_rebound_path"],
        "data_completeness": {
            "min_symbol_count": row["min_symbol_count"],
            "median_symbol_count": row["median_symbol_count"],
            "status": "PASS" if row["min_symbol_count"] >= 4000 else "REVIEW_REQUIRED",
        },
        "selection_reason": f"Selected from market-data-only 20BD windows as strongest {regime} candidate; no PM, portfolio, ledger, broker, or selected/bought outcome was used.",
    }


def analyze_runs(
    *,
    run_ids: tuple[str, ...],
    evidence_root: Path,
    quotes_path: Path,
    candidate_periods_path: Path,
) -> dict[str, Any]:
    quotes = read_quotes(quotes_path)
    price_index = build_price_index(quotes)
    volatility_index = build_symbol_volatility_index(quotes)
    candidate_payload = read_json(candidate_periods_path) if candidate_periods_path.is_file() else {"candidate_periods": []}
    period_by_date = candidate_period_by_date(candidate_payload.get("candidate_periods") or [])
    decisions: list[dict[str, Any]] = []
    for run_id in run_ids:
        run_dir = evidence_root / "runs" / run_id
        decisions.extend(
            load_run_pm_decisions(
                run_id=run_id,
                run_dir=run_dir,
                price_index=price_index,
                volatility_index=volatility_index,
                period_by_date=period_by_date,
            )
        )
    return {
        "schema_version": "phase20_t_pm_cross_regime_run_analysis.v1",
        "authority": "READ_ONLY_RUN_SCOPED_PM_DECISION_SNAPSHOTS_AND_EXISTING_JQUANTS_OHLCV",
        "run_ids": list(run_ids),
        "decision_count": len(decisions),
        "aggregates_by_action": aggregate(decisions, "action"),
        "aggregates_by_dominant_cause": aggregate(decisions, "dominant_cause", expected_keys=EXPECTED_CAUSES),
        "aggregates_by_market_regime": aggregate(decisions, "market_regime"),
        "aggregates_by_symbol_volatility_bucket": aggregate(decisions, "symbol_volatility_bucket"),
        "decisions": decisions,
        "limitations": [
            "Post-decision returns are analysis-only and are not written to Runtime decision artifacts.",
            "Market regime labels are post-analysis metadata derived from candidate periods.",
            "Missing trace fields are emitted as UNKNOWN rather than silently imputed.",
        ],
    }


def build_price_index(quotes: pd.DataFrame) -> dict[tuple[str, str], dict[str, float]]:
    return {
        (str(row["Date"]), str(row["Code"])): {
            "close": safe_float(row["Close"]),
            "high": safe_float(row["High"]),
            "low": safe_float(row["Low"]),
        }
        for row in quotes.to_dict("records")
    }


def build_symbol_volatility_index(quotes: pd.DataFrame, *, lookback: int = 20, min_observations: int = 20) -> dict[tuple[str, str], dict[str, Any]]:
    frame = quotes[["Date", "Code", "Close"]].copy()
    frame["Close"] = pd.to_numeric(frame["Close"], errors="coerce")
    frame = frame.dropna(subset=["Close"]).sort_values(["Code", "Date"])
    frame["return_1bd"] = frame.groupby("Code")["Close"].pct_change()
    frame["volatility_return_std_20d"] = (
        frame.groupby("Code")["return_1bd"]
        .rolling(window=lookback, min_periods=min_observations)
        .std(ddof=1)
        .reset_index(level=0, drop=True)
    )
    frame["volatility_observation_count"] = (
        frame.groupby("Code")["return_1bd"]
        .rolling(window=lookback, min_periods=1)
        .count()
        .reset_index(level=0, drop=True)
    )
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in frame.to_dict("records"):
        volatility = scalar_or_none(row.get("volatility_return_std_20d"))
        result[(str(row["Date"]), str(row["Code"]))] = {
            "value": volatility,
            "lookback": lookback,
            "observation_count": int(row.get("volatility_observation_count") or 0),
            "min_observations": min_observations,
            "status": "AVAILABLE" if volatility is not None else "INSUFFICIENT_LOOKBACK_DATA",
            "source": "EXISTING_JQUANTS_NORMALIZED_OHLCV_CLOSE_TO_CLOSE_RETURN_STD_20D",
            "future_data_used": False,
        }
    return result


def candidate_period_by_date(candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        for date in pd.date_range(candidate["start_date"], candidate["end_date"], freq="B").strftime("%Y-%m-%d"):
            mapping[date] = candidate
    return mapping


def load_run_pm_decisions(
    *,
    run_id: str,
    run_dir: Path,
    price_index: dict[tuple[str, str], dict[str, float]],
    volatility_index: dict[tuple[str, str], dict[str, Any]],
    period_by_date: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(run_dir.glob("daily/*/position_management/pm_decisions.json")):
        payload = read_json(path)
        business_date = str(payload.get("business_date") or path.parts[-3])
        for item in payload.get("decisions") or []:
            if not isinstance(item, dict):
                continue
            rows.append(
                normalize_decision(
                    run_id=run_id,
                    business_date=business_date,
                    item=item,
                    price_index=price_index,
                    volatility_index=volatility_index,
                    period_by_date=period_by_date,
                )
            )
    return rows


def normalize_decision(
    *,
    run_id: str,
    business_date: str,
    item: dict[str, Any],
    price_index: dict[tuple[str, str], dict[str, float]],
    volatility_index: dict[tuple[str, str], dict[str, Any]],
    period_by_date: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    symbol = normalize_symbol_code(item.get("symbol") or "")
    trace = item.get("decision_trace") if isinstance(item.get("decision_trace"), dict) else {}
    volatility_evidence = extract_symbol_volatility(item=item, trace=trace, symbol=symbol, business_date=business_date, volatility_index=volatility_index)
    volatility = volatility_evidence["value"]
    period = period_by_date.get(business_date, {})
    reason_codes = item.get("reason_codes") or item.get("decision_reason_codes") or []
    action = str(item.get("decision_type") or item.get("decision") or "UNKNOWN")
    dominant_cause = str(item.get("dominant_cause") or trace.get("dominant_cause") or "")
    if not dominant_cause or dominant_cause == "UNKNOWN":
        dominant_cause = dominant_cause_from_reason(action=action, reason_codes=reason_codes)
    return {
        "run_id": run_id,
        "business_date": business_date,
        "symbol": symbol,
        "decision_id": item.get("pm_decision_id") or item.get("decision_id") or "",
        "action": action,
        "dominant_cause": dominant_cause,
        "reason_codes": reason_codes,
        "market_regime": period.get("primary_regime", "UNKNOWN"),
        "market_regime_candidate_id": period.get("candidate_id", ""),
        "symbol_volatility": volatility,
        "symbol_volatility_bucket": volatility_bucket(volatility),
        "symbol_volatility_source": volatility_evidence["source"],
        "symbol_volatility_lookup_status": volatility_evidence["status"],
        "symbol_volatility_lookback": volatility_evidence.get("lookback"),
        "symbol_volatility_observation_count": volatility_evidence.get("observation_count"),
        "symbol_volatility_future_data_used": volatility_evidence.get("future_data_used", False),
        "post_decision_outcome": post_decision_outcome(symbol=symbol, business_date=business_date, price_index=price_index),
    }


def extract_symbol_volatility(
    *,
    item: dict[str, Any],
    trace: dict[str, Any],
    symbol: str,
    business_date: str,
    volatility_index: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    trace_paths = (
        ("decision_trace.technical_features.volatility_return_std_20d", trace.get("technical_features") if isinstance(trace.get("technical_features"), dict) else {}, "volatility_return_std_20d"),
        ("decision_trace.feature_values.volatility_return_std_20d", trace.get("feature_values") if isinstance(trace.get("feature_values"), dict) else {}, "volatility_return_std_20d"),
        ("decision_trace.input_snapshot.volatility_return_std_20d", trace.get("input_snapshot") if isinstance(trace.get("input_snapshot"), dict) else {}, "volatility_return_std_20d"),
    )
    for source, container, key in trace_paths:
        value = scalar_or_none(container.get(key))
        if value is not None:
            return {"value": value, "source": source, "status": "AVAILABLE", "future_data_used": False}
    for key in ("symbol_volatility", "volatility_return_std_20d", "realized_volatility", "volatility", "risk_volatility", "atr_pct"):
        value = scalar_or_none(item.get(key))
        if value is not None:
            return {"value": value, "source": f"pm_decision.{key}", "status": "AVAILABLE", "future_data_used": False}
    market = volatility_index.get((business_date, symbol))
    if market and market.get("value") is not None:
        return dict(market)
    if market:
        return {**market, "value": None}
    return {
        "value": None,
        "source": "EXISTING_JQUANTS_NORMALIZED_OHLCV_CLOSE_TO_CLOSE_RETURN_STD_20D",
        "status": "MARKET_DATA_NOT_FOUND",
        "future_data_used": False,
    }


def dominant_cause_from_reason(*, action: str, reason_codes: list[Any]) -> str:
    codes = {str(code).strip() for code in reason_codes}
    if action == "EXIT":
        if "hard_stop_current_return" in codes:
            return "EXIT_BY_HARD_STOP"
        if "profit_retention_break" in codes:
            return "EXIT_BY_PEAK_DRAWDOWN"
        if "trend_and_opportunity_broken" in codes:
            return "EXIT_BY_TREND_AND_EDGE_BREAK"
        if "risk_guard_status_bad" in codes:
            return "EXIT_BY_RISK_GUARD"
        if "exit_score_high" in codes:
            return "EXIT_BY_EXIT_SCORE_HIGH"
        if "weak_hold_score" in codes:
            return "EXIT_BY_WEAK_HOLD_SCORE"
    if action == "REDUCE":
        if "high_downside_risk_score" in codes:
            return "REDUCE_BY_HIGH_DOWNSIDE_RISK"
        if "peak_drawdown_warning" in codes:
            return "REDUCE_BY_PEAK_DRAWDOWN_WARNING"
        if "risk_increased_but_trend_not_broken" in codes:
            return "REDUCE_BY_RISK_INCREASED_BUT_TREND_NOT_BROKEN"
    if action == "ADD" and {"strong_trend_continuation", "opportunity_rank_still_high", "no_loss_averaging"} & codes:
        return "ADD_BY_STRONG_TREND_AND_RANK"
    if action == "HOLD":
        if {"trend_continuation", "positive_expected_edge", "downside_risk_contained"} <= codes:
            return "HOLD_BY_STRONG_CONTINUATION"
        if codes:
            return "HOLD_BY_PARTIAL_CONTINUATION"
        return "HOLD_BY_FALLBACK"
    return "UNKNOWN"


def post_decision_outcome(*, symbol: str, business_date: str, price_index: dict[tuple[str, str], dict[str, float]]) -> dict[str, Any]:
    symbol = normalize_symbol_code(symbol)
    dates = sorted({date for date, code in price_index if code == symbol})
    if business_date not in dates:
        return {"status": "MISSING_DECISION_PRICE"}
    idx = dates.index(business_date)
    base = price_index[(business_date, symbol)]["close"]
    outcome: dict[str, Any] = {"status": "AVAILABLE", "decision_close": base}
    for horizon in OUTCOME_HORIZONS:
        if idx + horizon >= len(dates):
            outcome[f"return_{horizon}bd"] = None
            outcome[f"mfe_proxy_{horizon}bd"] = None
            outcome[f"mae_proxy_{horizon}bd"] = None
            continue
        future_dates = dates[idx + 1 : idx + horizon + 1]
        close = price_index[(future_dates[-1], symbol)]["close"]
        highs = [price_index[(date, symbol)]["high"] for date in future_dates]
        lows = [price_index[(date, symbol)]["low"] for date in future_dates]
        outcome[f"return_{horizon}bd"] = safe_float(close / base - 1.0)
        outcome[f"mfe_proxy_{horizon}bd"] = safe_float(max(highs) / base - 1.0)
        outcome[f"mae_proxy_{horizon}bd"] = safe_float(min(lows) / base - 1.0)
    return outcome


def aggregate(rows: list[dict[str, Any]], field: str, *, expected_keys: tuple[str, ...] = ()) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(field) or "UNKNOWN")].append(row)
    for key in expected_keys:
        grouped.setdefault(key, [])
    return {key: aggregate_rows(items) for key, items in sorted(grouped.items())}


def aggregate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {"count": len(rows)}
    for horizon in OUTCOME_HORIZONS:
        values = [row.get("post_decision_outcome", {}).get(f"return_{horizon}bd") for row in rows]
        result[f"return_{horizon}bd"] = stats(values)
    return result


def stats(values: list[Any]) -> dict[str, Any]:
    numeric = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if not numeric:
        return {
            "count_with_return": 0,
            "mean": None,
            "median": None,
            "positive_rate": None,
            "negative_rate": None,
            "p25": None,
            "p75": None,
            "max_up": None,
            "max_down": None,
        }
    series = pd.Series(numeric)
    return {
        "count_with_return": len(numeric),
        "mean": safe_float(series.mean()),
        "median": safe_float(series.median()),
        "positive_rate": safe_float((series > 0).mean()),
        "negative_rate": safe_float((series < 0).mean()),
        "p25": safe_float(series.quantile(0.25)),
        "p75": safe_float(series.quantile(0.75)),
        "max_up": safe_float(series.max()),
        "max_down": safe_float(series.min()),
    }


def volatility_bucket(value: float | None) -> str:
    if value is None:
        return "UNKNOWN"
    if value < 0.025:
        return "LOW_SYMBOL_VOLATILITY"
    if value < 0.08:
        return "MEDIUM_SYMBOL_VOLATILITY"
    return "HIGH_SYMBOL_VOLATILITY"


def normalize_symbol_code(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text.endswith(".T"):
        text = text[:-2]
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) == 4:
        return f"{digits}0"
    return digits or text


def product_return(values: list[float]) -> float:
    result = 1.0
    for value in values:
        result *= 1.0 + value
    return result - 1.0


def safe_float(value: Any, ndigits: int = 8) -> float:
    if value is None:
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(number):
        return 0.0
    return round(number, ndigits)


def scalar_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
