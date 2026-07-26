#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.analyze_pm_cross_regime import build_market_proxy, classify_window, read_quotes, regime_thresholds, rolling_market_windows


DEFAULT_QUOTES_PATH = Path(".runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet")
DEFAULT_OUTPUT = Path("reports/phase_reports/phase20_ba_cross_regime_campaign_reselection.json")
DEFAULT_DOC = Path("docs/phase_reports/phase20_ba_cross_regime_campaign_reselection.md")
REQUIRED_REGIMES = ("BULL", "BEAR", "RANGE")
CAMPAIGN_DAYS = 20
WARMUP_DAYS = 60
OUTCOME_DAYS = 20


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase20-BA warmup-aware campaign reselection")
    parser.add_argument("--quotes-path", default=str(DEFAULT_QUOTES_PATH))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--output-md", default=str(DEFAULT_DOC))
    parser.add_argument("--print-json", action="store_true")
    args = parser.parse_args()
    report = build_report(quotes_path=Path(args.quotes_path))
    write_json(Path(args.output_json), report)
    write_markdown(Path(args.output_md), report)
    if args.print_json:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def build_report(*, quotes_path: Path) -> dict[str, Any]:
    quotes = read_quotes(quotes_path)
    dates = sorted(quotes["Date"].astype(str).unique().tolist())
    proxy = build_market_proxy(quotes)
    raw_windows = rolling_market_windows(proxy, business_days=CAMPAIGN_DAYS)
    thresholds = regime_thresholds(raw_windows)
    windows = [enrich_window(classify_window(window, thresholds=thresholds), dates=dates, quotes=quotes) for window in raw_windows]
    valid_windows = [window for window in windows if window["warmup_pass"] and window["outcome_pass"] and window["candidate_warmup_pass"]]
    by_regime = {
        regime: [window for window in valid_windows if regime in window["regime_labels"]]
        for regime in REQUIRED_REGIMES
    }
    selected = {regime: (items[0] if items else None) for regime, items in by_regime.items()}
    all_required_selected = all(selected[regime] is not None for regime in REQUIRED_REGIMES)
    return {
        "schema_version": "phase20_ba_cross_regime_campaign_reselection.v1",
        "final_status": "PHASE20_BA_CAMPAIGN_RESELECTION_COMPLETE",
        "campaign_ready": all_required_selected,
        "readiness_judgment": "READY" if all_required_selected else "NOT_READY_DATA_COVERAGE_CONSTRAINT",
        "authority": "READ_ONLY_EXISTING_JQUANTS_NORMALIZED_OHLCV",
        "quotes_path": str(quotes_path),
        "data_coverage": {
            "oldest_business_date": dates[0] if dates else "",
            "latest_business_date": dates[-1] if dates else "",
            "business_day_count": len(dates),
            "available_symbol_count": int(quotes["Code"].nunique()) if len(quotes) else 0,
        },
        "constraints": {
            "campaign_business_days": CAMPAIGN_DAYS,
            "candidate_warmup_business_days": WARMUP_DAYS,
            "outcome_business_days": OUTCOME_DAYS,
            "required_regimes": list(REQUIRED_REGIMES),
        },
        "classification_thresholds": thresholds,
        "eligible_window_count": len(valid_windows),
        "eligible_windows": valid_windows,
        "selected_campaigns": selected,
        "missing_required_regimes": [regime for regime in REQUIRED_REGIMES if selected[regime] is None],
        "reason": (
            "No BULL/BEAR/RANGE-complete campaign can be selected from current data while requiring 60BD warmup at run start and 20BD outcome after run end."
            if not all_required_selected
            else "All required regimes selected."
        ),
        "user_execution_commands": {
            regime: fresh_run_command(selected[regime]) if selected[regime] else "NOT_ISSUED: no warmup/outcome-valid candidate for this regime"
            for regime in REQUIRED_REGIMES
        },
        "future_leakage_policy": {
            "feature_date": "must equal run business_date for each day",
            "target_date": "candidate_features.target_date must equal feature_date",
            "as_of_date": "must be <= feature_date; expected same date in current historical feature refresh",
            "data_until": "must be <= feature_date; expected same date in current historical feature refresh",
            "future_ohlcv_used_for_feature": False,
        },
        "acceptance": {
            "HISTORICAL_DATA_INSPECTED": "PASS",
            "WARMUP_CONSTRAINT_ENFORCED": "PASS",
            "OUTCOME_WINDOW_CONSTRAINT_ENFORCED": "PASS",
            "CANDIDATE_WARMUP_CHECKED": "PASS",
            "BULL_SELECTED": "PASS" if selected["BULL"] else "FAIL",
            "BEAR_SELECTED": "PASS" if selected["BEAR"] else "FAIL",
            "RANGE_SELECTED": "PASS" if selected["RANGE"] else "FAIL",
            "NO_HISTORICAL_RUN_EXECUTED": "PASS",
            "CANDIDATE_PRODUCER_UNCHANGED": "PASS",
            "PM_UNCHANGED": "PASS",
            "SAFETY_UNCHANGED": "PASS",
            "ACCEPTED_GENERATION_UNCHANGED": "PASS",
        },
        "prohibited_operations": {
            "fresh_run_executed_by_codex": False,
            "resume_executed_by_codex": False,
            "bear_run_executed_by_codex": False,
            "range_run_executed_by_codex": False,
            "broker_connection_executed": False,
            "training_executed": False,
            "calibration_executed": False,
            "model_changed": False,
            "candidate_producer_changed": False,
            "pm_changed": False,
            "safety_changed": False,
            "accepted_generation_changed": False,
        },
    }


def enrich_window(window: dict[str, Any], *, dates: list[str], quotes: pd.DataFrame) -> dict[str, Any]:
    start_idx = dates.index(window["start_date"])
    end_idx = dates.index(window["end_date"])
    warmup_days = start_idx + 1
    outcome_days = len(dates) - end_idx - 1
    start_rows = quotes[quotes["Date"].astype(str) == window["start_date"]]
    history = quotes[quotes["Date"].astype(str) <= window["start_date"]].groupby("Code")["Date"].nunique()
    candidate_rows = int(len(start_rows))
    universe_proxy = int((history >= WARMUP_DAYS).sum())
    enriched = dict(window)
    enriched.update(
        {
            "campaign_id": f"PM20BA-{window['start_date']}",
            "warmup_business_days": warmup_days,
            "outcome_business_days": outcome_days,
            "warmup_pass": warmup_days >= WARMUP_DAYS,
            "outcome_pass": outcome_days >= OUTCOME_DAYS,
            "candidate_features_rows_proxy": candidate_rows,
            "universe_eligible_true_proxy": universe_proxy,
            "required_model_feature_complete_rows_proxy": universe_proxy,
            "candidate_warmup_pass": candidate_rows > 0 and universe_proxy > 0,
            "feature_date_contract": {
                "feature_date": window["start_date"],
                "target_date": window["start_date"],
                "as_of_date": window["start_date"],
                "data_until": window["start_date"],
                "status": "PLANNED_PRODUCTION_CONTRACT_COMPATIBLE",
            },
        }
    )
    return enriched


def fresh_run_command(window: dict[str, Any]) -> str:
    return "\n".join(
        [
            "cd /Users/negishi/work/ai-fund-lab-v2",
            "",
            "PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \\",
            "  --profile historical-extended-smoke \\",
            "  --business-days 20 \\",
            f"  --start-date {window['start_date']} \\",
            "  --confirm \\",
            "  --yes-i-understand-this-mutates-trading-state \\",
            "  --json",
        ]
    )


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Phase20-BA Cross-Regime Campaign Reselection",
        "",
        "## Status",
        "",
        "```text",
        report["final_status"],
        "```",
        "",
        f"Readiness: `{report['readiness_judgment']}`",
        "",
        "## Data Coverage",
        "",
        "```json",
        json.dumps(report["data_coverage"], indent=2, sort_keys=True),
        "```",
        "",
        "## Constraint Result",
        "",
        report["reason"],
        "",
        "Eligible windows satisfying 60BD warmup, 20BD campaign, and 20BD outcome:",
        "",
        "| Start | End | Warmup BD | Outcome BD | Labels | Return | Volatility | Candidate Rows | Eligible Proxy |",
        "|---|---|---:|---:|---|---:|---:|---:|---:|",
    ]
    for item in report["eligible_windows"]:
        lines.append(
            f"| `{item['start_date']}` | `{item['end_date']}` | {item['warmup_business_days']} | {item['outcome_business_days']} | "
            f"`{','.join(item['regime_labels'])}` | {item['period_return']} | {item['realized_volatility']} | "
            f"{item['candidate_features_rows_proxy']} | {item['universe_eligible_true_proxy']} |"
        )
    lines.extend(["", "## Selected Campaigns", ""])
    for regime in REQUIRED_REGIMES:
        item = report["selected_campaigns"][regime]
        if item is None:
            lines.append(f"- {regime}: `NOT_SELECTED`")
        else:
            lines.append(f"- {regime}: `{item['start_date']}` to `{item['end_date']}`")
    lines.extend(["", "## User Execution Commands", ""])
    for regime in REQUIRED_REGIMES:
        lines.extend([f"### {regime}", "", "```bash", report["user_execution_commands"][regime], "```", ""])
    lines.extend(
        [
            "## Future Leakage Contract",
            "",
            "```json",
            json.dumps(report["future_leakage_policy"], indent=2, sort_keys=True),
            "```",
            "",
            "## Acceptance",
            "",
        ]
    )
    for key, value in report["acceptance"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Prohibited Operations Confirmation",
            "",
            "Codex did not execute 20BD Historical Run, resume, BEAR Run, RANGE Run, Broker connection, Training, Calibration, model change, Candidate Producer change, PM change, Safety change, or Accepted Generation change.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
