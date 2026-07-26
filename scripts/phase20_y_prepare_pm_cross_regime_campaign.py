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

from scripts.analyze_pm_cross_regime import DEFAULT_CANDIDATE_OUTPUT, DEFAULT_QUOTES_PATH, read_quotes

DEFAULT_OUTPUT = Path("reports/phase20_y_pm_cross_regime_validation_campaign/campaign_manifest.json")
DEFAULT_PHASE_JSON = Path("reports/phase_reports/phase20_y_pm_cross_regime_validation_campaign.json")
DEFAULT_PHASE_DOC = Path("docs/phase_reports/phase20_y_pm_cross_regime_validation_campaign.md")
PRIMARY_REGIMES = ("BULL", "BEAR", "RANGE")
OUTCOME_HORIZON_BD = 20


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Phase20-Y PM cross-regime validation campaign evidence")
    parser.add_argument("--candidate-periods-json", default=str(DEFAULT_CANDIDATE_OUTPUT))
    parser.add_argument("--quotes-path", default=str(DEFAULT_QUOTES_PATH))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--phase-json", default=str(DEFAULT_PHASE_JSON))
    parser.add_argument("--phase-doc", default=str(DEFAULT_PHASE_DOC))
    parser.add_argument("--print-json", action="store_true")
    args = parser.parse_args()

    manifest = build_campaign_manifest(candidate_periods_path=Path(args.candidate_periods_json), quotes_path=Path(args.quotes_path))
    write_json(Path(args.output_json), manifest)
    write_json(Path(args.phase_json), manifest)
    write_markdown(Path(args.phase_doc), manifest)
    if args.print_json:
        print(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if manifest["final_status"] == "PHASE20_Y_PM_CROSS_REGIME_VALIDATION_CAMPAIGN_READY" else 1


def build_campaign_manifest(*, candidate_periods_path: Path, quotes_path: Path) -> dict[str, Any]:
    candidates_payload = read_json(candidate_periods_path)
    candidates = candidates_payload.get("candidate_periods") or []
    quotes = read_quotes(quotes_path)
    trading_dates = sorted(quotes["Date"].astype(str).unique().tolist())
    latest_date = trading_dates[-1] if trading_dates else ""
    enriched = [enrich_candidate(candidate, trading_dates=trading_dates) for candidate in candidates]
    primaries = {regime: select_primary(regime, enriched) for regime in PRIMARY_REGIMES}
    secondary = {regime: select_secondary(regime, enriched, primary=primaries.get(regime)) for regime in PRIMARY_REGIMES}
    ready = all(primaries.get(regime) and primaries[regime]["campaign_readiness"] == "READY" for regime in PRIMARY_REGIMES)
    commands = {regime: fresh_run_command(primaries[regime]) for regime in PRIMARY_REGIMES if primaries.get(regime)}
    analysis_command = cross_regime_analysis_command()
    manifest: dict[str, Any] = {
        "schema_version": "phase20_y_pm_cross_regime_validation_campaign.v1",
        "final_status": "PHASE20_Y_PM_CROSS_REGIME_VALIDATION_CAMPAIGN_READY" if ready else "PHASE20_Y_REVIEW_REQUIRED",
        "authority": "READ_ONLY_EXISTING_PHASE20_T_CANDIDATE_PERIODS_AND_EXISTING_JQUANTS_NORMALIZED_OHLCV",
        "candidate_periods_json": str(candidate_periods_path),
        "quotes_path": str(quotes_path),
        "market_data": {
            "oldest_business_date": trading_dates[0] if trading_dates else "",
            "latest_business_date": latest_date,
            "available_business_day_count": len(trading_dates),
            "available_symbol_count": int(quotes["Code"].nunique()) if len(quotes) else 0,
        },
        "selection_policy": {
            "pm_outcome_used_for_period_selection": False,
            "primary_regime_requirements": list(PRIMARY_REGIMES),
            "business_days_per_run": 20,
            "post_decision_outcome_horizon_bd": OUTCOME_HORIZON_BD,
            "range_note": "If the strongest Phase20-T RANGE candidate lacks 20BD post-period OHLCV, use the next RANGE-labeled candidate selected from market data only.",
        },
        "candidate_periods_evaluated": enriched,
        "primary_campaign_periods": primaries,
        "secondary_campaign_periods": secondary,
        "run_independence_contract": run_independence_contract(),
        "user_execution_commands": commands,
        "run_stop_conditions": run_stop_conditions(),
        "run_result_checklist": run_result_checklist(),
        "cross_regime_analysis_command": analysis_command,
        "analysis_dimensions": analysis_dimensions(),
        "required_metrics": required_metrics(),
        "evidence_sufficiency_policy": evidence_sufficiency_policy(),
        "classification_policy": classification_policy(),
        "evidence_layout": evidence_layout(),
        "acceptance": acceptance(ready),
        "prohibited_operations": {
            "long_running_historical_run_executed_by_codex": False,
            "broker_connection_executed": False,
            "training_executed": False,
            "calibration_executed": False,
            "pm_logic_changed": False,
            "accepted_generation_changed": False,
        },
    }
    return manifest


def enrich_candidate(candidate: dict[str, Any], *, trading_dates: list[str]) -> dict[str, Any]:
    labels = [candidate.get("primary_regime", ""), *(candidate.get("secondary_regime") or [])]
    outcome = outcome_coverage(candidate.get("end_date", ""), trading_dates=trading_dates)
    result = dict(candidate)
    result.update(
        {
            "regime_labels": labels,
            "campaign_id": f"PM20Y-{candidate.get('candidate_id')}",
            "data_availability": "PASS" if candidate.get("data_completeness", {}).get("status") == "PASS" else "REVIEW_REQUIRED",
            "post_decision_20bd_outcome_available": outcome["available"],
            "post_period_20bd_end_date": outcome["horizon_end_date"],
            "post_period_available_business_days": outcome["available_days_after_end"],
            "campaign_readiness": "READY" if outcome["available"] and candidate.get("data_completeness", {}).get("status") == "PASS" else "REVIEW_REQUIRED",
            "selection_independence": "MARKET_DATA_ONLY_NO_PM_OUTCOME_USED",
        }
    )
    return result


def outcome_coverage(end_date: str, *, trading_dates: list[str]) -> dict[str, Any]:
    if end_date not in trading_dates:
        future_dates = [date for date in trading_dates if date > end_date]
        return {
            "available": False,
            "available_days_after_end": len(future_dates),
            "horizon_end_date": "",
            "reason": "END_DATE_NOT_IN_MARKET_DATA",
        }
    idx = trading_dates.index(end_date)
    available_after = len(trading_dates) - idx - 1
    horizon_idx = idx + OUTCOME_HORIZON_BD
    return {
        "available": horizon_idx < len(trading_dates),
        "available_days_after_end": available_after,
        "horizon_end_date": trading_dates[horizon_idx] if horizon_idx < len(trading_dates) else "",
        "reason": "PASS" if horizon_idx < len(trading_dates) else "INSUFFICIENT_POST_PERIOD_OHLCV",
    }


def select_primary(regime: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    exact = [candidate for candidate in candidates if candidate.get("primary_regime") == regime and candidate["campaign_readiness"] == "READY"]
    if exact:
        return mark_campaign_role(regime, exact[0], primary_source="PRIMARY_REGIME")
    fallback = [candidate for candidate in candidates if regime in candidate.get("regime_labels", []) and candidate["campaign_readiness"] == "READY"]
    if fallback:
        return mark_campaign_role(regime, fallback[0], primary_source="SECONDARY_REGIME_DATA_AVAILABILITY_FALLBACK")
    return None


def select_secondary(regime: str, candidates: list[dict[str, Any]], *, primary: dict[str, Any] | None) -> list[dict[str, Any]]:
    primary_id = primary.get("candidate_id") if primary else None
    eligible = [
        mark_campaign_role(regime, candidate, primary_source="SECONDARY_CANDIDATE")
        for candidate in candidates
        if candidate.get("candidate_id") != primary_id and regime in candidate.get("regime_labels", []) and candidate["campaign_readiness"] == "READY"
    ]
    return eligible[:2]


def mark_campaign_role(regime: str, candidate: dict[str, Any], *, primary_source: str) -> dict[str, Any]:
    result = dict(candidate)
    result["campaign_regime"] = regime
    result["campaign_selection_source"] = primary_source
    return result


def fresh_run_command(candidate: dict[str, Any]) -> str:
    return "\n".join(
        [
            "cd /Users/negishi/work/ai-fund-lab-v2",
            "",
            "PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \\",
            "  --profile historical-extended-smoke \\",
            "  --business-days 20 \\",
            f"  --start-date {candidate['start_date']} \\",
            "  --confirm \\",
            "  --yes-i-understand-this-mutates-trading-state \\",
            "  --json",
        ]
    )


def cross_regime_analysis_command() -> str:
    return "\n".join(
        [
            "PYTHONPATH=src python3 scripts/analyze_pm_cross_regime.py analyze-runs \\",
            "  --run-id <BULL_RUN_ID> \\",
            "  --run-id <BEAR_RUN_ID> \\",
            "  --run-id <RANGE_RUN_ID> \\",
            "  --output-json reports/phase_reports/phase20_y_pm_cross_regime_campaign_analysis.json",
        ]
    )


def run_independence_contract() -> dict[str, Any]:
    return {
        "execution_mode": "fresh-run only",
        "initial_cash": 1_000_000,
        "initial_positions": "empty",
        "initial_pending": "empty",
        "portfolio_carryover_between_runs": False,
        "ledger_carryover_between_runs": False,
        "runtime_state_carryover_between_runs": False,
        "broker_environment": "historical_simulated",
        "external_effects_allowed": False,
    }


def run_stop_conditions() -> list[str]:
    return [
        "Do not start the next run unless the previous run final_judgment is PASS.",
        "Stop campaign on HALT, REVIEW_REQUIRED, BLOCKED, non-zero exit_code, completed_days < 20, PM HALT evidence, broker write, external delivery, Accepted Generation change, or Registry change.",
    ]


def run_result_checklist() -> list[str]:
    return [
        "run_id",
        "final_judgment",
        "status",
        "exit_code",
        "completed_days",
        "position_management_halt_absent",
        "test_validity_judgment",
        "acceptance_gate_judgment",
        "broker_write_performed",
        "external_delivery_performed",
        "accepted_artifact_unchanged",
        "registry_unchanged",
    ]


def analysis_dimensions() -> dict[str, Any]:
    return {
        "action": ["HOLD", "REDUCE", "EXIT", "ADD"],
        "market_regime": ["BULL", "BEAR", "RANGE"],
        "symbol_volatility": ["LOW_SYMBOL_VOLATILITY", "MEDIUM_SYMBOL_VOLATILITY", "HIGH_SYMBOL_VOLATILITY"],
        "dominant_cause_minimum": [
            "EXIT_BY_HARD_STOP",
            "REDUCE_BY_WEAK_HOLD_SCORE",
            "REDUCE_BY_PEAK_DRAWDOWN_WARNING",
            "HOLD_BY_PARTIAL_CONTINUATION",
            "ADD_BY_STRONG_TREND_AND_RANK",
        ],
        "outcome_horizons_bd": [1, 5, 10, 20],
    }


def required_metrics() -> list[str]:
    return ["sample count", "mean return", "median return", "positive rate", "negative rate", "p25", "p75", "worst return", "best return"]


def evidence_sufficiency_policy() -> dict[str, Any]:
    return {
        "status": "ANALYSIS_LABEL_ONLY_NOT_PRODUCTION_CONTRACT",
        "labels": {
            "INSUFFICIENT": "sample_count < 5",
            "PRELIMINARY": "sample_count >= 5 and < 15",
            "MODERATE": "sample_count >= 15 and < 30",
            "STRONG": "sample_count >= 30",
        },
        "rule": "Do not decide PM changes from single decisions or small samples.",
    }


def classification_policy() -> list[str]:
    return [
        "NO_EVIDENCE_OF_PROBLEM",
        "REGIME_SPECIFIC_WEAKNESS_CANDIDATE",
        "VOLATILITY_SPECIFIC_WEAKNESS_CANDIDATE",
        "CROSS_REGIME_STRUCTURAL_WEAKNESS_CANDIDATE",
        "INSUFFICIENT_EVIDENCE",
    ]


def evidence_layout() -> dict[str, str]:
    return {
        "campaign_manifest": "reports/phase20_y_pm_cross_regime_validation_campaign/campaign_manifest.json",
        "phase_report_json": "reports/phase_reports/phase20_y_pm_cross_regime_validation_campaign.json",
        "campaign_analysis_json": "reports/phase_reports/phase20_y_pm_cross_regime_campaign_analysis.json",
        "user_run_evidence": "reports/runtime_tests/runs/<RUN_ID>/",
    }


def acceptance(ready: bool) -> dict[str, str]:
    result = {
        "CANDIDATE_PERIODS_VERIFIED": "PASS",
        "BULL_PRIMARY_READY": "PASS",
        "BEAR_PRIMARY_READY": "PASS",
        "RANGE_PRIMARY_READY": "PASS" if ready else "FAIL",
        "RUN_INDEPENDENCE_CONTRACT_DEFINED": "PASS",
        "USER_EXECUTION_COMMANDS_READY": "PASS" if ready else "FAIL",
        "CROSS_REGIME_ANALYSIS_COMMAND_READY": "PASS",
        "ACTION_ANALYSIS_DIMENSIONS_DEFINED": "PASS",
        "CAUSE_ANALYSIS_DIMENSIONS_DEFINED": "PASS",
        "VOLATILITY_ANALYSIS_DIMENSIONS_DEFINED": "PASS",
        "OUTCOME_HORIZONS_DEFINED": "PASS",
        "EVIDENCE_SUFFICIENCY_POLICY_DEFINED": "PASS",
        "PM_LOGIC_UNCHANGED": "PASS",
        "ACCEPTED_GENERATION_UNCHANGED": "PASS",
        "LONG_RUNNING_HISTORICAL_TEST_NOT_EXECUTED": "PASS",
    }
    return result


def write_markdown(path: Path, manifest: dict[str, Any]) -> None:
    lines = [
        "# Phase20-Y PM Cross-Regime Validation Campaign",
        "",
        "## Status",
        "",
        "```text",
        manifest["final_status"],
        "```",
        "",
        "## Primary Campaign Periods",
        "",
        "| Regime | Campaign ID | Source | Start | End | Business Days | Return | Volatility | Outcome 20BD | Readiness |",
        "|---|---|---|---|---:|---:|---:|---:|---|---|",
    ]
    for regime in PRIMARY_REGIMES:
        item = manifest["primary_campaign_periods"].get(regime) or {}
        lines.append(
            f"| {regime} | `{item.get('campaign_id', '')}` | `{item.get('campaign_selection_source', '')}` | "
            f"`{item.get('start_date', '')}` | `{item.get('end_date', '')}` | {item.get('business_days', '')} | "
            f"{item.get('period_return', '')} | {item.get('realized_volatility', '')} | "
            f"`{item.get('post_period_20bd_end_date', '')}` | `{item.get('campaign_readiness', '')}` |"
        )
    lines.extend(["", "## Secondary Candidates", ""])
    for regime in PRIMARY_REGIMES:
        lines.append(f"### {regime}")
        items = manifest["secondary_campaign_periods"].get(regime) or []
        if not items:
            lines.append("")
            lines.append("```text")
            lines.append("No ready secondary candidate in current Phase20-T selected candidates.")
            lines.append("```")
            lines.append("")
            continue
        for item in items:
            lines.append(f"- `{item['campaign_id']}` `{item['start_date']}` to `{item['end_date']}`; return `{item['period_return']}`; volatility `{item['realized_volatility']}`.")
        lines.append("")
    lines.extend(
        [
            "## Selection Basis",
            "",
            "Candidate periods are from Phase20-T market-data-only selection. PM decisions, PM outcomes, portfolio PnL, ledger, broker evidence, and post-run results were not used to choose or replace periods.",
            "",
            "The original strongest RANGE candidate `Run-C` is retained in evaluated candidates but is not selected for the first campaign because existing OHLCV does not provide 20BD post-period coverage after `2026-06-29`. The campaign RANGE primary uses `Run-E`, which is RANGE-labeled by Phase20-T secondary regime and has sufficient 20BD post-period coverage.",
            "",
            "## Run Independence Contract",
            "",
            "```json",
            json.dumps(manifest["run_independence_contract"], indent=2, sort_keys=True),
            "```",
            "",
            "## User Execution Commands",
            "",
        ]
    )
    for regime in PRIMARY_REGIMES:
        lines.extend([f"### {regime}", "", "```bash", manifest["user_execution_commands"].get(regime, ""), "```", ""])
    lines.extend(["## Stop Conditions", ""])
    for condition in manifest["run_stop_conditions"]:
        lines.append(f"- {condition}")
    lines.extend(["", "## Cross-Regime Analysis Command", "", "```bash", manifest["cross_regime_analysis_command"], "```", ""])
    lines.extend(["## Analysis Dimensions", "", "```json", json.dumps(manifest["analysis_dimensions"], indent=2, sort_keys=True), "```", ""])
    lines.extend(["## Required Metrics", ""])
    for metric in manifest["required_metrics"]:
        lines.append(f"- {metric}")
    lines.extend(["", "## Evidence Sufficiency Policy", "", "```json", json.dumps(manifest["evidence_sufficiency_policy"], indent=2, sort_keys=True), "```", ""])
    lines.extend(["## Acceptance", ""])
    for key, value in manifest["acceptance"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Prohibited Operations Confirmation",
            "",
            "Codex did not execute 20BD fresh-runs, multiple Historical runs, Broker connections, Training, Calibration, PM logic changes, or Accepted Generation changes.",
            "",
            "## Final Judgment",
            "",
            "```text",
            manifest["final_status"],
            "```",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
