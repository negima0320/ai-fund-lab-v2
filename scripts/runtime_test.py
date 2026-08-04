#!/usr/bin/env python3
"""Runtime Test command runner.

This script is a thin lifecycle runner around the normal Runtime v2 CLI. It
does not make AI decisions, produce features, generate fills, or mutate Ledger /
Current / Pending except through explicit lifecycle reset / rollback commands.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.historical_support.reset_plan import (
    RESETTABLE_RELATIVE_PATHS,
    RESET_EXCLUDED_RELATIVE_PREFIXES,
)
from ai_fund_lab_v2.runtime_v2.historical_support.isolated_root import (
    day1_pre_run_absent_artifacts,
    materialize_isolated_historical_runtime_root,
    protected_shared_runtime_hashes,
)
from ai_fund_lab_v2.runtime_v2.ai_status import (
    build_ai_status_report,
    write_ai_status_evidence,
)
from ai_fund_lab_v2.runtime_v2.accepted_generation_resolver import (
    resolve_accepted_generation,
    resolve_accepted_generation_for_evaluation,
)
from ai_fund_lab_v2.runtime_v2.system_status import (
    build_system_status_report,
    build_system_status_scoped_view,
    SYSTEM_STATUS_SCOPES,
    write_system_status_evidence,
)
from ai_fund_lab_v2.runtime_v2.market_refresh.feature_date_contract import (
    load_feature_date_contract,
    resolve_feature_date_contract,
)
from ai_fund_lab_v2.runtime_v2.market_data_bootstrap import (
    build_market_data_bootstrap_plan,
    execute_market_data_bootstrap,
)
from ai_fund_lab_v2.runtime_v2.market_data_acquisition import (
    FETCH_CONFIRM_FLAG,
    acquisition_status,
    build_acquisition_plan,
    resume_acquisition,
    run_acquisition,
)
from ai_fund_lab_v2.runtime_v2.performance_evaluation import (
    materialize_capital_efficiency_trace,
    materialize_daily_evaluation_evidence,
)
from ai_fund_lab_v2.runtime_v2.storage.path_resolver import reject_mode_rooted_runtime_root
from ai_fund_lab_v2.strategy.observability import (
    build_strategy_decision_trace,
    summarize_strategy_trace,
)
from ai_fund_lab_v2.strategy.historical_source_foundation import build_historical_strategy_preflight
from ai_fund_lab_v2.strategy.shadow_runtime import (
    generate_strategy_shadow_for_day,
    load_run_strategy_shadow_summary,
    strategy_shadow_job_descriptor,
    update_run_strategy_shadow_indexes,
    validate_run_strategy_shadow,
)


EXIT_PASS = 0
EXIT_REVIEW_REQUIRED = 10
EXIT_BLOCKED = 20
EXIT_HALT = 30
EXIT_VALIDATION_FAILURE = 40
EXIT_ROLLBACK_FAILURE = 50
EXIT_INVALID_ARGUMENT = 60
EXIT_PRECONDITION_FAILURE = 70
EXIT_TEST_INVALID = 80
EXIT_INTERNAL_ERROR = 90

EXIT_CODES = {
    EXIT_PASS: "PASS",
    EXIT_REVIEW_REQUIRED: "REVIEW_REQUIRED",
    EXIT_BLOCKED: "BLOCKED",
    EXIT_HALT: "HALT",
    EXIT_VALIDATION_FAILURE: "VALIDATION_FAILURE",
    EXIT_ROLLBACK_FAILURE: "ROLLBACK_FAILURE",
    EXIT_INVALID_ARGUMENT: "INVALID_ARGUMENT",
    EXIT_PRECONDITION_FAILURE: "PRECONDITION_FAILURE",
    EXIT_TEST_INVALID: "TEST_INVALID",
    EXIT_INTERNAL_ERROR: "INTERNAL_ERROR",
}

RUNTIME_TEST_JOB_TERMINATE_GRACE_ENV = "RUNTIME_TEST_JOB_TERMINATE_GRACE_SECONDS"
RUNTIME_TEST_JOB_DEFAULT_TERMINATE_GRACE_SECONDS = 10.0
RUNTIME_TEST_SUBPROCESS_TRACE_SCHEMA_VERSION = "runtime_test_subprocess_trace_v1"

SCOPED_BUY_ONLY_JOB_STATUSES = {"REVIEW_REQUIRED_BUY_ONLY", "BLOCKED_BUY_ONLY"}
PM_RUNTIME_TEST_FATAL_STATUSES = {"HALT"}

PROFILE_PATHS = {
    "historical-smoke": Path("config/runtime_tests/historical_smoke_5bd.json"),
    "historical-extended-smoke": Path("config/runtime_tests/historical_extended_smoke_10bd.json"),
}

RUNNER_SCHEMA_VERSION = "runtime_test_runner_v1"
RUN_STATE_SCHEMA_VERSION = "runtime_test_run_state_v1"
PLAN_SCHEMA_VERSION = "runtime_test_plan_v1"
BACKUP_MANIFEST_SCHEMA_VERSION = "runtime_test_backup_manifest_v1"
RESET_MANIFEST_SCHEMA_VERSION = "runtime_test_reset_manifest_v1"
FINAL_SUMMARY_SCHEMA_VERSION = "runtime_test_final_summary_v1"
FRESH_RUN_SUMMARY_SCHEMA_VERSION = "runtime_test_fresh_run_summary_v1"
HISTORICAL_EVALUATION_AUTHORITY_SCHEMA_VERSION = "historical_evaluation_authority.v1"
SUMMARY_SCHEMA_VERSION = "runtime_test_summary_v2"
SUMMARY_SCOPE_CONTRACT_VERSION = "runtime_test_summarize_scope_contract.v1"
PERFORMANCE_METRIC_CONTRACT_VERSION = "phase20_b_performance_metric_contract.v1"
PERFORMANCE_OBSERVABILITY_CONTRACT_VERSION = "phase20_j_performance_observability_contract.v1"
PERFORMANCE_OBSERVABILITY_SCHEMA_VERSION = "runtime_test_performance_observability_v1"
POSITION_QUANTITY_EPSILON = 1e-6
REDUCE_NON_EXECUTABLE_FEASIBILITY_STATUS = "NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY"
REDUCE_NON_EXECUTABLE_REASON = "REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY"
REDUCE_NON_EXECUTABLE_LIFECYCLE_EVENT = "REDUCE_NOT_EXECUTED_MINIMUM_TRADABLE_QUANTITY"
SUMMARY_SCOPES = ("overview", "performance", "positions", "lifecycle", "strategy", "strategy-trace", "strategy-attribution", "strategy-readiness", "strategy-shadow", "full")
LEGACY_RUN_STATE_SCHEMA_VERSIONS = {"phase17_k_run_state_v1"}
LEGACY_PLAN_SCHEMA_VERSIONS = {"phase17_k_runtime_test_plan_v1"}
LEGACY_BACKUP_MANIFEST_SCHEMA_VERSIONS = {"phase17_k_backup_manifest_v1"}
SUPPORTED_RUN_STATE_SCHEMA_VERSIONS = {RUN_STATE_SCHEMA_VERSION, *LEGACY_RUN_STATE_SCHEMA_VERSIONS}
SUPPORTED_PLAN_SCHEMA_VERSIONS = {PLAN_SCHEMA_VERSION, *LEGACY_PLAN_SCHEMA_VERSIONS}
SUPPORTED_BACKUP_MANIFEST_SCHEMA_VERSIONS = {
    BACKUP_MANIFEST_SCHEMA_VERSION,
    *LEGACY_BACKUP_MANIFEST_SCHEMA_VERSIONS,
}
MUTATION_CONFIRM_FLAG = "--yes-i-understand-this-mutates-trading-state"
MARKET_DATA_MUTATION_CONFIRM_FLAG = "--yes-i-understand-this-mutates-market-data"
EVIDENCE_ROOT = Path("reports/runtime_tests")
BACKUP_ROOT = EVIDENCE_ROOT / "backups"
RUNS_ROOT = EVIDENCE_ROOT / "runs"
RUNTIME_CLI_MODULE = "ai_fund_lab_v2.runtime_v2.cli.run_daily_operation"
JOB_SEQUENCE = (
    "market_refresh",
    "data_readiness",
    "morning",
    "sell_planning",
    "submit",
    "execution",
    "current_valuation_refresh",
    "runtime_state_refresh",
)
FEATURE_DATE_JOBS = {"data_readiness", "morning", "sell_planning", "submit"}
SUBMIT_ENABLED_JOBS = {"submit"}


@dataclass(frozen=True)
class CommandResult:
    status: str
    exit_code: int
    payload: dict[str, Any]


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = dispatch(args)
    except RuntimeTestError as exc:
        payload = {
            "schema_version": RUNNER_SCHEMA_VERSION,
            "status": exc.status,
            "exit_code": exc.exit_code,
            "error": str(exc),
        }
        emit(payload, json_output=getattr(args, "json", False))
        return exc.exit_code
    except Exception as exc:  # pragma: no cover - defensive top-level guard
        payload = {
            "schema_version": RUNNER_SCHEMA_VERSION,
            "status": "INTERNAL_ERROR",
            "exit_code": EXIT_INTERNAL_ERROR,
            "error": str(exc),
        }
        emit(payload, json_output=getattr(args, "json", False))
        return EXIT_INTERNAL_ERROR
    emit(result.payload, json_output=getattr(args, "json", False))
    return result.exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI Fund Lab v2 Runtime Test command runner")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    def add_common(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--profile", default="historical-smoke")
        sub.add_argument("--runtime-root")
        sub.add_argument("--evidence-root", default=str(EVIDENCE_ROOT))
        sub.add_argument("--json", action="store_true")

    def add_plan_window(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--business-days", type=int)
        sub.add_argument("--start-date")
        sub.add_argument("--date-from")
        sub.add_argument("--date-to", dest="date_to")
        sub.add_argument("--end-date", dest="date_to")

    def add_mutation_safety(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--dry-run", action="store_true")
        sub.add_argument("--confirm", action="store_true")
        sub.add_argument(MUTATION_CONFIRM_FLAG, dest="explicit_mutation_confirm", action="store_true")

    run_status = subparsers.add_parser("run-status")
    add_common(run_status)

    status = subparsers.add_parser("status", help="Compatibility alias for run-status")
    add_common(status)

    summarize = subparsers.add_parser("summarize")
    add_common(summarize)
    summarize.add_argument("--run-id", required=True)
    summarize.add_argument("--scope", choices=SUMMARY_SCOPES)
    summarize.add_argument("--write-evidence", action="store_true")

    daily_evidence = subparsers.add_parser("daily-evidence")
    add_common(daily_evidence)
    daily_evidence.add_argument("--run-id", required=True)
    daily_evidence.add_argument("--business-date")
    daily_evidence.add_argument("--performance-evidence-root", default="reports/performance_evaluations")

    capital_trace = subparsers.add_parser("capital-trace")
    add_common(capital_trace)
    capital_trace.add_argument("--run-id", required=True)
    capital_trace.add_argument("--business-date", required=True)
    capital_trace.add_argument("--performance-evidence-root", default="reports/performance_evaluations")

    ai_status = subparsers.add_parser("ai-status")
    add_common(ai_status)
    ai_status.add_argument("--detailed", action="store_true")
    ai_status.add_argument("--write-evidence", action="store_true")
    ai_status.add_argument("--check-runtime-readiness", action="store_true")

    system_status = subparsers.add_parser("system-status")
    add_common(system_status)
    system_status.add_argument("--write-evidence", action="store_true")
    system_status.add_argument("--scope", default="overview", choices=sorted(set(SYSTEM_STATUS_SCOPES) | {"strategy"}))
    system_status.add_argument("--full", action="store_true", help="Alias for --scope full")
    system_status.add_argument("--target-start-date")
    system_status.add_argument("--target-end-date")

    market_data_bootstrap = subparsers.add_parser("market-data-bootstrap")
    add_common(market_data_bootstrap)
    market_data_bootstrap_sub = market_data_bootstrap.add_subparsers(dest="market_data_bootstrap_action")
    market_data_bootstrap_plan = market_data_bootstrap_sub.add_parser("plan")
    add_common(market_data_bootstrap_plan)
    market_data_bootstrap_plan.add_argument("--years", type=int, default=5)
    market_data_bootstrap_plan.add_argument("--source-path", default=".runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet")
    market_data_bootstrap_plan.add_argument("--target-start-date")
    market_data_bootstrap_plan.add_argument("--target-end-date")
    market_data_bootstrap_plan.add_argument("--write-evidence", action="store_true")
    market_data_bootstrap_run = market_data_bootstrap_sub.add_parser("run")
    add_common(market_data_bootstrap_run)
    market_data_bootstrap_run.add_argument("--years", type=int, default=5)
    market_data_bootstrap_run.add_argument("--source-path", default=".runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet")
    market_data_bootstrap_run.add_argument("--target-start-date")
    market_data_bootstrap_run.add_argument("--target-end-date")
    market_data_bootstrap_run.add_argument("--write-evidence", action="store_true")
    market_data_bootstrap_run.add_argument("--confirm", action="store_true")
    market_data_bootstrap_run.add_argument(MARKET_DATA_MUTATION_CONFIRM_FLAG, dest="explicit_market_data_mutation_confirm", action="store_true")

    market_data_acquisition = subparsers.add_parser("market-data-acquisition")
    add_common(market_data_acquisition)
    market_data_acquisition_sub = market_data_acquisition.add_subparsers(dest="market_data_acquisition_action")
    market_data_acquisition_plan = market_data_acquisition_sub.add_parser("plan")
    add_common(market_data_acquisition_plan)
    market_data_acquisition_plan.add_argument("--start-date", required=True)
    market_data_acquisition_plan.add_argument("--end-date", required=True)
    market_data_acquisition_plan.add_argument("--run-id")
    market_data_acquisition_plan.add_argument("--chunk", choices=("day", "week", "month"), default="month")
    market_data_acquisition_plan.add_argument("--write-evidence", action="store_true")
    market_data_acquisition_run = market_data_acquisition_sub.add_parser("run")
    add_common(market_data_acquisition_run)
    market_data_acquisition_run.add_argument("--start-date", required=True)
    market_data_acquisition_run.add_argument("--end-date", required=True)
    market_data_acquisition_run.add_argument("--run-id")
    market_data_acquisition_run.add_argument("--chunk", choices=("day", "week", "month"), default="month")
    market_data_acquisition_run.add_argument("--max-pages-per-chunk", type=int, default=100)
    market_data_acquisition_run.add_argument("--confirm", action="store_true")
    market_data_acquisition_run.add_argument(FETCH_CONFIRM_FLAG, dest="explicit_fetch_confirm", action="store_true")
    market_data_acquisition_run.add_argument("--write-evidence", action="store_true")
    market_data_acquisition_resume = market_data_acquisition_sub.add_parser("resume")
    add_common(market_data_acquisition_resume)
    market_data_acquisition_resume.add_argument("--run-id", required=True)
    market_data_acquisition_resume.add_argument("--max-pages-per-chunk", type=int, default=100)
    market_data_acquisition_resume.add_argument("--confirm", action="store_true")
    market_data_acquisition_resume.add_argument(FETCH_CONFIRM_FLAG, dest="explicit_fetch_confirm", action="store_true")
    market_data_acquisition_resume.add_argument("--write-evidence", action="store_true")
    market_data_acquisition_status = market_data_acquisition_sub.add_parser("status")
    add_common(market_data_acquisition_status)
    market_data_acquisition_status.add_argument("--run-id", required=True)

    prepare_isolated = subparsers.add_parser("prepare-isolated")
    add_common(prepare_isolated)
    prepare_isolated.add_argument("--run-id")
    prepare_isolated.add_argument("--target-business-date")
    prepare_isolated.add_argument("--write-evidence", action="store_true")

    plan = subparsers.add_parser("plan")
    add_common(plan)
    add_plan_window(plan)
    plan.add_argument("--write-evidence", action="store_true")
    plan.add_argument("--run-id")

    backup = subparsers.add_parser("backup")
    add_common(backup)
    add_mutation_safety(backup)

    reset = subparsers.add_parser("reset")
    add_common(reset)
    add_mutation_safety(reset)
    reset.add_argument("--backup-id")
    reset.add_argument("--initial-cash", type=float)
    reset.add_argument("--initial-position-state-date")

    run = subparsers.add_parser("run")
    add_common(run)
    add_plan_window(run)
    add_mutation_safety(run)
    run.add_argument("--run-id")
    run.add_argument("--auto-prepare", action="store_true")

    fresh = subparsers.add_parser("fresh-run")
    add_common(fresh)
    add_plan_window(fresh)
    add_mutation_safety(fresh)
    fresh.add_argument("--initial-cash", type=float)
    fresh.add_argument(
        "--auto-abandon-on-error",
        action="store_true",
        help="Automatically abandon a HALT run created by fresh-run so a later fresh-run is not blocked.",
    )
    fresh.add_argument("--auto-abandon-reason", default="fresh_run_auto_abandon_on_error")

    validate = subparsers.add_parser("validate")
    add_common(validate)
    validate.add_argument("--run-id")
    validate.add_argument("--business-date")

    resume = subparsers.add_parser("resume")
    add_common(resume)
    add_mutation_safety(resume)
    resume.add_argument("--run-id", required=True)

    abandon = subparsers.add_parser("abandon")
    add_common(abandon)
    add_mutation_safety(abandon)
    abandon.add_argument("--run-id", required=True)
    abandon.add_argument("--reason", default="operator_abandoned_halt_run")
    abandon.add_argument(
        "--allow-stale-running",
        action="store_true",
        help="Allow abandonment after converting an externally interrupted RUNNING run to HALT evidence.",
    )

    rollback = subparsers.add_parser("rollback")
    add_common(rollback)
    add_mutation_safety(rollback)
    rollback.add_argument("--backup-id", required=True)

    close = subparsers.add_parser("close")
    add_common(close)
    close.add_argument("--run-id", required=True)

    show = subparsers.add_parser("show")
    add_common(show)
    show.add_argument("--run-id")
    show.add_argument("--backup-id")
    show.add_argument("--business-date")
    show.add_argument("--artifact")

    subparsers.add_parser("list-runs").add_argument("--json", action="store_true")
    subparsers.add_parser("list-backups").add_argument("--json", action="store_true")
    return parser


def dispatch(args: argparse.Namespace) -> CommandResult:
    if args.subcommand == "list-runs":
        return list_runs()
    if args.subcommand == "list-backups":
        return list_backups()
    if args.subcommand == "show":
        return show(args)

    profile = load_profile(args.profile)
    runtime_root = Path(args.runtime_root or profile["runtime_root"])
    evidence_root = Path(getattr(args, "evidence_root", str(EVIDENCE_ROOT)))
    validate_environment(profile=profile, runtime_root=runtime_root)

    if args.subcommand in {"run-status", "status"}:
        return status(profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "summarize":
        return summarize_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "daily-evidence":
        return daily_evidence_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "capital-trace":
        return capital_trace_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "ai-status":
        return ai_status_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "system-status":
        return system_status_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "market-data-bootstrap":
        return market_data_bootstrap_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "market-data-acquisition":
        return market_data_acquisition_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "prepare-isolated":
        return prepare_isolated_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "plan":
        return plan_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "backup":
        return backup_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "reset":
        return reset_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "run":
        return run_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "fresh-run":
        return fresh_run_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "validate":
        return validate_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "resume":
        return resume_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "abandon":
        return abandon_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "rollback":
        return rollback_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "close":
        return close_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    raise RuntimeTestError("unsupported subcommand", status="INVALID_ARGUMENT", exit_code=EXIT_INVALID_ARGUMENT)


def status(*, profile: dict[str, Any], runtime_root: Path, evidence_root: Path) -> CommandResult:
    active_run = active_run_for_profile(evidence_root, profile_id=str(profile["profile_id"]))
    active_run_id = str(active_run.get("run_id") or "") if active_run else ""
    strategy_shadow = read_json_optional(runs_root(evidence_root) / active_run_id / "strategy_shadow_summary.json") if active_run_id else {}
    halt_summary = _runtime_halt_summary(runs_root(evidence_root) / active_run_id) if active_run_id else {}
    payload = base_payload("status", "PASS")
    payload.update(
        {
            "runtime_root": str(runtime_root),
            "current_environment": read_environment(runtime_root),
            "active_test_run": active_run.get("run_id") if active_run else "",
            "run_status": active_run.get("status") if active_run else "IDLE",
            "current_business_date": read_runtime_business_date(runtime_root),
            "completed_business_days": active_run.get("completed_business_days", []) if active_run else [],
            "next_job": active_run.get("next_job", "") if active_run else "",
            "halt_summary": halt_summary,
            "current_summary": summarize_json(runtime_root / "persistent_ledger" / "state.json"),
            "ledger_summary": summarize_ledger(runtime_root),
            "pending_summary": summarize_json(runtime_root / "pending_order_plan" / "pending_order_plan.json"),
            "runtime_state_summary": summarize_json(runtime_root / "runtime_state" / "current_state.json"),
            "registry_checkpoint": file_ref(runtime_root / "artifact_registry" / "checkpoints" / "latest.json", root=runtime_root),
            "accepted_artifact_hash": accepted_artifact_hash(runtime_root),
            "latest_backup": latest_backup(evidence_root).get("backup_id", ""),
            "external_effect_policy": profile["external_effect_policy"],
            "strategy_shadow": {
                "enabled": True,
                "current_date": (strategy_shadow.get("business_dates_expected") or [""])[-1] if strategy_shadow else "",
                "last_completed_date": (strategy_shadow.get("business_dates_generated") or [""])[-1] if strategy_shadow else "",
                "generated_dates": strategy_shadow.get("business_dates_generated", []) if strategy_shadow else [],
                "review_required_dates": strategy_shadow.get("review_required_dates", []) if strategy_shadow else [],
                "blocked_dates": strategy_shadow.get("blocked_dates", []) if strategy_shadow else [],
                "latest_strategy_trace": _latest_strategy_trace_path(run_dir=runs_root(evidence_root) / active_run_id) if active_run_id else "",
                "active_runtime_consumer_eligibility": "NO",
            },
        }
    )
    return CommandResult("PASS", EXIT_PASS, runner_response(payload))


def _runtime_halt_summary(run_dir: Path) -> dict[str, Any]:
    if not run_dir or not run_dir.exists():
        return {}
    run_state = read_json_optional(run_dir / "run_state.json")
    halted_at = run_state.get("halted_at") if isinstance(run_state.get("halted_at"), dict) else {}
    business_date = str(halted_at.get("business_date") or "")
    job = str(halted_at.get("job") or "")
    summary: dict[str, Any] = {
        "schema_version": "runtime_test_halt_summary_v1",
        "status": "HALT" if halted_at else "NOT_HALTED",
        "halted_business_date": business_date,
        "halted_job": job,
        "halt_classification": "",
        "root_reason": "",
        "root_reason_code": "",
        "blocked_item_count": 0,
        "expected_hash": "",
        "actual_hash": "",
        "expected_content_hash": "",
        "actual_content_hash": "",
        "source_paths": {},
        "recommended_action": "",
        "manifest_path": "",
    }
    if not halted_at:
        return summary
    manifest_path = run_dir / "daily" / business_date / job / "runtime_manifest.json"
    if not manifest_path.is_file():
        summary["root_reason"] = str(halted_at.get("runtime_test_job_status") or halted_at.get("exit_code") or "")
        summary["root_reason_code"] = str(halted_at.get("runtime_test_job_status") or "")
        summary["halt_classification"] = str(halted_at.get("runtime_test_job_status") or "RUNTIME_CLI_NONZERO_EXIT")
        summary["recommended_action"] = "Inspect the halted job evidence and Runtime CLI output."
        return summary
    manifest = read_json_optional(manifest_path)
    summary["manifest_path"] = str(manifest_path)
    item_results = _collect_submit_item_results(manifest)
    halted_items = [
        item
        for item in item_results
        if ((item.get("response_classification") or {}).get("status") == "HALT") or bool(item.get("blocked"))
    ]
    summary["blocked_item_count"] = len(halted_items) or int(manifest.get("blocked_count") or 0)
    first = halted_items[0] if halted_items else {}
    classification = first.get("response_classification") if isinstance(first.get("response_classification"), dict) else {}
    diagnostic = first.get("configuration_diagnostic") if isinstance(first.get("configuration_diagnostic"), dict) else {}
    manifest_reason = _first_text(
        manifest.get("reason"),
        *_as_text_list(manifest.get("data_readiness_halt_reasons")),
        *_as_text_list(manifest.get("data_readiness_review_reasons")),
        *_as_text_list(manifest.get("errors")),
        *_as_text_list(manifest.get("warnings")),
        halted_at.get("runtime_test_job_status"),
        halted_at.get("exit_code"),
    )
    manifest_reason_code = _first_text(
        manifest.get("reason_code"),
        manifest.get("root_reason_code"),
        *_as_text_list(manifest.get("data_readiness_halt_reasons")),
        *_as_text_list(manifest.get("data_readiness_review_reasons")),
        halted_at.get("runtime_test_job_status"),
    )
    manifest_classification = _first_text(
        manifest.get("halt_classification"),
        manifest.get("classification"),
        manifest.get("final_state"),
        manifest.get("status"),
        halted_at.get("runtime_test_job_status"),
        "RUNTIME_CLI_NONZERO_EXIT",
    )
    manifest_action = _first_text(
        manifest.get("recommended_action"),
        manifest.get("next_operator_action"),
        manifest.get("data_readiness_next_operator_action"),
        "Inspect the halted job evidence and repair the root Runtime authority before resume.",
    )
    summary.update(
        {
            "halt_classification": str(
                classification.get("mismatch_class")
                or classification.get("root_reason_code")
                or classification.get("status")
                or manifest_classification
            ),
            "root_reason": str(classification.get("reason") or first.get("reason") or manifest_reason),
            "root_reason_code": str(classification.get("root_reason_code") or classification.get("mismatch_class") or manifest_reason_code),
            "expected_hash": str(classification.get("expected_hash") or classification.get("expected_content_hash") or ""),
            "actual_hash": str(classification.get("source_hash") or classification.get("actual_content_hash") or ""),
            "expected_content_hash": str(classification.get("expected_content_hash") or classification.get("expected_hash") or ""),
            "actual_content_hash": str(classification.get("actual_content_hash") or classification.get("source_hash") or ""),
            "source_paths": {
                "expected_source_path": str(classification.get("expected_source_path") or ""),
                "actual_source_path": str(classification.get("actual_source_path") or ""),
                "ohlcv_path": str(diagnostic.get("ohlcv_path") or ""),
                "raw_ohlcv_path": str(diagnostic.get("raw_ohlcv_path") or ""),
                "listed_issues_path": str(diagnostic.get("listed_issues_path") or ""),
                "historical_asof_view_path": str(diagnostic.get("historical_asof_view_path") or ""),
            },
            "recommended_action": str(classification.get("recommended_action") or manifest_action),
        }
    )
    return summary


def _first_text(*values: Any) -> str:
    for value in values:
        if value in (None, ""):
            continue
        text = str(value)
        if text:
            return text
    return ""


def _as_text_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    if value in (None, ""):
        return []
    return [str(value)]


def _mark_run_halted(run_dir: Path, run_state: dict[str, Any], job_record: dict[str, Any]) -> None:
    run_state["status"] = "HALT"
    run_state["halted_at"] = job_record
    write_json_atomic(run_dir / "run_state.json", run_state)
    run_state["halt_summary"] = _runtime_halt_summary(run_dir)
    write_json_atomic(run_dir / "run_state.json", run_state)


def _mark_running_run_interrupted_halt(
    *,
    run_dir: Path,
    run_state: dict[str, Any],
    reason: str,
    exit_code: int = 130,
) -> dict[str, Any]:
    next_job = str(run_state.get("next_job") or "")
    business_date, _, job = next_job.partition(":")
    interrupted = {
        "business_date": business_date,
        "job": job,
        "exit_code": exit_code,
        "command": [],
        "planned_command": {},
        "runtime_test_job_status": "SUBPROCESS_INTERRUPTED",
        "reason": reason,
        "interrupted_at": utc_now(),
        "completed_runtime_cli_evidence": False,
        "orphan_process_status": "EXTERNALLY_VERIFIED_REQUIRED",
    }
    run_state.setdefault("completed_jobs", []).append(interrupted)
    _mark_run_halted(run_dir, run_state, interrupted)
    return interrupted


def _collect_submit_item_results(value: Any) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if isinstance(value.get("item_results"), list):
            results.extend(item for item in value["item_results"] if isinstance(item, dict))
        for child in value.values():
            results.extend(_collect_submit_item_results(child))
    elif isinstance(value, list):
        for child in value:
            results.extend(_collect_submit_item_results(child))
    return results


def summarize_command(
    args: argparse.Namespace,
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
) -> CommandResult:
    run_id = str(args.run_id)
    run_dir = runs_root(evidence_root) / run_id
    if not run_dir.exists():
        raise RuntimeTestError(
            f"unknown run_id: {run_id}",
            status="PRECONDITION_FAILURE",
            exit_code=EXIT_PRECONDITION_FAILURE,
        )

    summary_id = f"runtime-test-summary-{run_id}-{timestamp_id()}"
    findings: list[dict[str, Any]] = []
    plan = read_json_optional(run_dir / "plan.json")
    run_state = read_json_optional(run_dir / "run_state.json")
    final_summary = read_json_optional(run_dir / "final_summary.json")
    fresh_summary = read_json_optional(run_dir / "fresh_run_summary.json")
    missing = [
        name
        for name, payload in (
            ("plan.json", plan),
            ("run_state.json", run_state),
            ("final_summary.json", final_summary),
            ("fresh_run_summary.json", fresh_summary),
        )
        if not payload
    ]
    if missing:
        findings.append(_summary_finding("REVIEW_REQUIRED", "RUN_EVIDENCE_INCOMPLETE", {"missing": missing}))

    planned_root = Path(str(plan.get("runtime_root") or fresh_summary.get("runtime_root") or runtime_root))
    if planned_root != runtime_root and str(planned_root) not in {"", str(runtime_root)}:
        findings.append(
            _summary_finding(
                "REVIEW_REQUIRED",
                "RUN_RUNTIME_ROOT_UNRESOLVED",
                {"plan_runtime_root": str(planned_root), "inspected_runtime_root": str(runtime_root)},
            )
        )
    final_hashes = final_summary.get("final_state_hashes") if isinstance(final_summary.get("final_state_hashes"), dict) else {}
    current_hashes = state_hashes(runtime_root) if runtime_root.exists() else {}
    final_snapshot_state, final_snapshot_authority = _load_verified_final_state_snapshot(run_dir=run_dir, final_summary=final_summary)
    runtime_authority = "CURRENT_RUNTIME_ROOT_FINAL_HASH_MATCH"
    runtime_state_available = bool(final_hashes) and current_hashes == final_hashes
    final_state_available = runtime_state_available or bool(final_snapshot_state)
    final_state_authority = "CURRENT_RUNTIME_ROOT_FINAL_HASH_MATCH" if runtime_state_available else final_snapshot_authority.get("status", "NOT_AVAILABLE")
    if not final_hashes:
        runtime_authority = "FINAL_STATE_HASH_NOT_AVAILABLE"
        findings.append(_summary_finding("REVIEW_REQUIRED", "RUN_EVIDENCE_INCOMPLETE", {"missing": ["final_state_hashes"]}))
    elif current_hashes != final_hashes:
        runtime_authority = "CURRENT_RUNTIME_ROOT_FINAL_HASH_MISMATCH"
        findings.append(
            _summary_finding(
                "INFO",
                "RUN_FINAL_STATE_HASH_MISMATCH",
                {
                    "final_state_hashes": final_hashes,
                    "current_state_hashes": current_hashes,
                    "past_run_summary_impact": "NONE_WHEN_RUN_SCOPED_EVIDENCE_EXISTS",
                },
            )
        )

    completed_business_days = _completed_business_days(run_state=run_state, fresh_summary=fresh_summary)
    observability = _load_performance_observability(
        run_dir=run_dir,
        run_id=run_id,
        completed_business_days=completed_business_days,
    )
    pm = _summarize_pm_decisions(
        runtime_root=runtime_root,
        run_dir=run_dir,
        run_id=run_id,
        available=runtime_state_available,
        completed_business_days=completed_business_days,
    )
    plans = _collect_order_plan_items(
        runtime_root=runtime_root,
        run_dir=run_dir,
        run_id=run_id,
        available=runtime_state_available,
        completed_business_days=completed_business_days,
    )
    orders = (
        _filter_rows_by_business_days(
            _read_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl"),
            completed_business_days,
            include_without_business_date=True,
        )
        if runtime_state_available
        else _run_scoped_orders_from_fills(observability)
    )
    executions = (
        _filter_rows_by_business_days(_read_jsonl(runtime_root / "persistent_ledger" / "executions.jsonl"), completed_business_days)
        if runtime_state_available
        else _run_scoped_executions_from_fills(observability)
    )
    current_state = read_json_optional(runtime_root / "persistent_ledger" / "state.json") if runtime_state_available else final_snapshot_state
    pending_state = read_json_optional(runtime_root / "pending_order_plan" / "pending_order_plan.json") if runtime_state_available else {}

    if runtime_state_available and not (runtime_root / "persistent_ledger" / "state.json").exists():
        findings.append(_summary_finding("REVIEW_REQUIRED", "LEDGER_NOT_AVAILABLE", {"path": str(runtime_root / "persistent_ledger" / "state.json")}))
    elif not final_state_available:
        severity = "INFO" if observability.get("status") == "AVAILABLE" else "REVIEW_REQUIRED"
        findings.append(
            _summary_finding(
                severity,
                "CURRENT_RUNTIME_ROOT_LEDGER_NOT_USED_FOR_PAST_RUN",
                {"reason": runtime_authority, "run_scoped_observability_status": observability.get("status")},
            )
        )

    trading = _summarize_trading(plans=plans, orders=orders, executions=executions, pending_state=pending_state)
    reduce_exit = _summarize_reduce_exit(plans=plans)
    if reduce_exit["sell_plan_items_with_unknown_source_decision"]:
        findings.append(
            _summary_finding(
                "REVIEW_REQUIRED",
                "SELL_PLAN_SOURCE_DECISION_NOT_TRACEABLE",
                {"count": reduce_exit["sell_plan_items_with_unknown_source_decision"]},
            )
        )
    trade_attribution, attribution_findings, realized_pnl_from_trades = _build_trade_attribution(
        sell_plan_items=plans["sell"],
        executions=executions,
        pm_decisions=pm.get("decision_records", []),
    )
    findings.extend(attribution_findings)
    performance = _summarize_performance(
        fresh_summary=fresh_summary,
        current_state=current_state,
        realized_pnl_from_trades=realized_pnl_from_trades,
        runtime_state_available=final_state_available,
        current_state_authority=final_state_authority,
        current_state_authority_status="CANONICAL_FINAL_STATE_SNAPSHOT" if final_snapshot_state and not runtime_state_available else "CANONICAL_CURRENT_STATE",
        observability=observability,
    )
    current_positions = _summarize_current_positions(current_state)
    lifecycle = _summarize_lifecycle(
        pm=pm,
        trading=trading,
        reduce_exit=reduce_exit,
        current_state=current_state,
        pending_state=pending_state,
        run_scoped_position_authority=observability.get("status") == "AVAILABLE",
    )
    if lifecycle["status"] != "PASS":
        findings.append(_summary_finding("REVIEW_REQUIRED", "LIFECYCLE_CONSISTENCY_REVIEW_REQUIRED", lifecycle))

    external_effects = _summarize_external_effects(run_dir=run_dir, fresh_summary=fresh_summary)
    observability_judgment = _observability_completeness_judgment(observability)
    performance_analysis_readiness = _performance_analysis_readiness_judgment(observability)
    summary_authority_matrix = _build_summary_authority_matrix(
        pm=pm,
        plans=plans,
        observability=observability,
        final_state_authority=final_state_authority,
        runtime_state_available=runtime_state_available,
        current_hashes=current_hashes,
        final_hashes=final_hashes,
    )
    requested_business_days = int(plan.get("requested_business_days") or fresh_summary.get("requested_business_days") or fresh_summary.get("business_days") or 0)
    resolved_business_day_count = int(plan.get("resolved_business_day_count") or fresh_summary.get("resolved_business_day_count") or len(plan.get("business_dates") or completed_business_days))
    completed_business_day_count = len(completed_business_days)
    independent_acceptance = _summary_independent_acceptance_judgment(
        runtime_execution_status=str(run_state.get("status") or final_summary.get("status") or ""),
        requested_business_days=requested_business_days,
        resolved_business_day_count=resolved_business_day_count,
        completed_business_day_count=completed_business_day_count,
        window_resolution_status=str(plan.get("window_resolution_status") or fresh_summary.get("window_resolution_status") or ""),
        lifecycle_status=str(lifecycle.get("status") or ""),
        summary_authority_matrix=summary_authority_matrix,
        legacy_request_preserved=bool(plan.get("requested_window") or plan.get("resolved_business_day_count")),
    )
    run_summary = {
        "profile_id": plan.get("profile_id") or fresh_summary.get("profile_id") or profile.get("profile_id", ""),
        "status": run_state.get("status") or final_summary.get("status") or "UNKNOWN",
        "final_judgment": final_summary.get("final_judgment") or final_summary.get("status") or "UNKNOWN",
        "operational_status": final_summary.get("operational_status") or final_summary.get("status") or "UNKNOWN",
        "strategy_review_status": final_summary.get("strategy_review_status") or "NOT_EVALUATED",
        "close_authority_judgment": final_summary.get("close_authority_judgment") or final_summary.get("status") or "UNKNOWN",
        "final_runtime_judgment": final_summary.get("final_runtime_judgment") or final_summary.get("final_judgment") or final_summary.get("status") or "UNKNOWN",
        "strategy_shadow_review_required": bool(final_summary.get("strategy_shadow_review_required")),
        "completed_business_days": sorted(completed_business_days),
        "business_day_count": completed_business_day_count,
        "requested_business_days": requested_business_days,
        "resolved_business_day_count": resolved_business_day_count,
        "completed_business_day_count": completed_business_day_count,
        "window_resolution_status": plan.get("window_resolution_status") or fresh_summary.get("window_resolution_status") or "REQUEST_NOT_PRESERVED_IN_LEGACY_PLAN",
        "request_conformance_status": independent_acceptance["requested_window_conformance_judgment"],
        "date_from": fresh_summary.get("date_from") or "",
        "date_to": fresh_summary.get("date_to") or "",
        "run_dir": str(run_dir),
        "runtime_root": str(runtime_root),
        "runtime_state_authority": runtime_authority,
        "final_state_authority": final_state_authority,
        "final_state_snapshot_authority": final_snapshot_authority,
        "event_collection_authority": "RUN_SCOPED_EVIDENCE_WITH_COMPLETED_BUSINESS_DAY_FILTER",
        "final_state_hashes": final_hashes,
        "current_state_hashes": current_hashes,
        "summary_authority_matrix": summary_authority_matrix,
        "independent_acceptance": independent_acceptance,
    }
    performance_judgment = "NEGATIVE_RETURN_OBSERVED" if float(performance.get("total_return_amount") or 0.0) < 0 else "NOT_EVALUATED"
    runtime_judgment = "BLOCKED" if any(f["severity"] == "BLOCKED" for f in findings) else "PASS"
    if runtime_judgment == "PASS" and any(f["severity"] == "REVIEW_REQUIRED" for f in findings):
        runtime_judgment = "REVIEW_REQUIRED"
    status_value = runtime_judgment
    exit_code = EXIT_PASS if status_value == "PASS" else EXIT_BLOCKED if status_value == "BLOCKED" else EXIT_REVIEW_REQUIRED
    scope = str(getattr(args, "scope", "") or "full")
    scope_sections = _build_summarize_scope_sections(
        run_id=run_id,
        run_summary=run_summary,
        external_effects=external_effects,
        performance=performance,
        pm=pm,
        trading=trading,
        reduce_exit=reduce_exit,
        trade_attribution=trade_attribution,
        current_positions=current_positions,
        lifecycle=lifecycle,
        findings=findings,
        plans=plans,
        executions=executions,
        observability=observability,
    )
    strategy_trace = _build_strategy_summary_scope(
        run_id=run_id,
        profile_id=str(plan.get("profile_id") or fresh_summary.get("profile_id") or profile.get("profile_id", "")),
        runtime_root=runtime_root,
        run_dir=run_dir,
        run_summary=run_summary,
    )
    strategy_shadow_summary = load_run_strategy_shadow_summary(run_dir=run_dir)
    if strategy_shadow_summary:
        strategy_trace["trace_status"] = strategy_trace.get("status")
        strategy_trace["status"] = strategy_shadow_summary.get("strategy_shadow_judgment", strategy_trace.get("status"))
        strategy_trace["shadow_run_summary"] = strategy_shadow_summary
    payload = {
        "schema_version": "runtime_test_summary_v1",
        "summary_scope_schema_version": SUMMARY_SCHEMA_VERSION,
        "subcommand": "summarize",
        "summary_id": summary_id,
        "run_id": run_id,
        "generated_at": utc_now(),
        "scope": scope,
        "scope_default": "legacy-compatible full" if not getattr(args, "scope", None) else "explicit",
        "available_scopes": list(SUMMARY_SCOPES),
        "contract_versions": {
            "summarize_scope_contract": SUMMARY_SCOPE_CONTRACT_VERSION,
            "performance_metric_contract": PERFORMANCE_METRIC_CONTRACT_VERSION,
            "performance_observability_contract": PERFORMANCE_OBSERVABILITY_CONTRACT_VERSION,
        },
        "authority": {
            "run_event_aggregation": "RUN_SCOPED_EVIDENCE_WITH_COMPLETED_BUSINESS_DAY_FILTER",
            "runtime_root_detail": runtime_authority,
            "shared_runtime_event_authority": "PROHIBITED",
            "summary_authority_matrix": summary_authority_matrix,
        },
        "source_evidence": {
            "run_dir": str(run_dir),
            "plan": str(run_dir / "plan.json"),
            "run_state": str(run_dir / "run_state.json"),
            "final_summary": str(run_dir / "final_summary.json"),
            "fresh_run_summary": str(run_dir / "fresh_run_summary.json"),
        },
        "missing_evidence": [],
        "warnings": [],
        "overview": scope_sections["overview"] if scope in {"overview", "full"} else None,
        "performance_scope": scope_sections["performance"] if scope in {"performance", "full"} else None,
        "positions_scope": scope_sections["positions"] if scope in {"positions", "full"} else None,
        "lifecycle_scope": scope_sections["lifecycle"] if scope in {"lifecycle", "full"} else None,
        "strategy_scope": strategy_trace if scope in {"strategy", "strategy-trace", "strategy-attribution", "strategy-readiness", "strategy-shadow"} else None,
        "strategy_shadow_summary": strategy_shadow_summary,
        "run": run_summary,
        "external_effects": external_effects,
        "performance": performance,
        "pm_decisions": {key: value for key, value in pm.items() if key != "decision_records"},
        "trading": trading,
        "reduce_exit": reduce_exit,
        "trade_attribution": trade_attribution,
        "performance_observability": observability,
        "observability_completeness_judgment": observability_judgment,
        "performance_analysis_readiness_judgment": performance_analysis_readiness,
        "current_positions": current_positions,
        "lifecycle_consistency": lifecycle,
        "summary_authority_matrix": summary_authority_matrix,
        "independent_acceptance": independent_acceptance,
        "findings": findings,
        "runtime_judgment": runtime_judgment,
        "performance_judgment": performance_judgment,
        "strategy_judgment": strategy_trace.get("status", "NOT_EVALUATED") if scope in {"strategy", "strategy-trace", "strategy-attribution", "strategy-readiness", "strategy-shadow"} else "NOT_EVALUATED",
        "status": status_value,
        "final_judgment": status_value,
        "exit_code": exit_code,
        "evidence_path": "",
    }
    if bool(args.write_evidence):
        evidence_path = evidence_root / "summaries" / summary_id
        payload["evidence_path"] = str(evidence_path)
        payload["human_summary"] = _format_runtime_test_summary(payload)
        write_json_atomic(evidence_path / "summary.json", payload)
        _write_text_atomic(evidence_path / "summary.txt", payload["human_summary"])
    else:
        payload["human_summary"] = _format_runtime_test_summary(payload)
    return CommandResult(status_value, exit_code, payload)


def daily_evidence_command(
    args: argparse.Namespace,
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
) -> CommandResult:
    del profile, runtime_root
    result = materialize_daily_evaluation_evidence(
        run_id=str(args.run_id),
        runtime_test_evidence_root=evidence_root,
        performance_evidence_root=Path(str(args.performance_evidence_root)),
        business_date=str(args.business_date) if getattr(args, "business_date", None) else None,
    )
    status = str(result.get("status") or "REVIEW_REQUIRED")
    exit_code = EXIT_PASS if status == "PASS" else EXIT_PRECONDITION_FAILURE if status == "PRECONDITION_FAILURE" else EXIT_REVIEW_REQUIRED
    payload = {
        "schema_version": "runtime_test_daily_evidence_command.v1",
        "subcommand": "daily-evidence",
        "status": status,
        "exit_code": exit_code,
        "read_only_runtime": True,
        "strategy_mutation": False,
        "runtime_mutation": False,
        "result": result,
    }
    return CommandResult(status, exit_code, payload)


def capital_trace_command(
    args: argparse.Namespace,
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
) -> CommandResult:
    del profile, runtime_root
    result = materialize_capital_efficiency_trace(
        run_id=str(args.run_id),
        runtime_test_evidence_root=evidence_root,
        performance_evidence_root=Path(str(args.performance_evidence_root)),
        business_date=str(args.business_date),
    )
    status = str(result.get("status") or "REVIEW_REQUIRED")
    exit_code = EXIT_PASS if status == "PASS" else EXIT_PRECONDITION_FAILURE if status == "PRECONDITION_FAILURE" else EXIT_REVIEW_REQUIRED
    payload = {
        "schema_version": "runtime_test_capital_trace_command.v1",
        "subcommand": "capital-trace",
        "status": status,
        "exit_code": exit_code,
        "read_only_runtime": True,
        "strategy_mutation": False,
        "runtime_mutation": False,
        "result": result,
    }
    return CommandResult(status, exit_code, payload)


def _summary_finding(severity: str, reason: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"severity": severity, "reason": reason, "evidence": evidence or {}}


def _build_summary_authority_matrix(
    *,
    pm: dict[str, Any],
    plans: dict[str, Any],
    observability: dict[str, Any],
    final_state_authority: str,
    runtime_state_available: bool,
    current_hashes: dict[str, str],
    final_hashes: dict[str, str],
) -> dict[str, Any]:
    plan_matrix = dict(plans.get("summary_authority_matrix") or {})
    pm_source = str(pm.get("source") or "")
    pm_authority = "RUN_SCOPED_EVIDENCE" if pm_source == "run_scoped_position_management_evidence" else (
        "CURRENT_RUNTIME_FALLBACK_FINAL_HASH_MATCH" if pm_source == "runtime_root_position_management_decisions_completed_business_day_filter" else "UNAVAILABLE"
    )
    fallback_used = pm_authority.startswith("CURRENT_RUNTIME")
    matrix = {
        "pm_decisions": {
            "authority": pm_authority,
            "fallback_used": fallback_used,
            "source": pm_source,
            "run_scoped_empty_is_authoritative": pm_source == "run_scoped_position_management_evidence" and int(pm.get("decision_count") or 0) == 0,
        },
        "buy_planning": plan_matrix.get("buy_planning", {"authority": "UNAVAILABLE", "fallback_used": False, "source_paths": []}),
        "sell_planning": plan_matrix.get("sell_planning", {"authority": "UNAVAILABLE", "fallback_used": False, "source_paths": []}),
        "non_executable_sell_decisions": plan_matrix.get("non_executable_sell_decisions", {"authority": "UNAVAILABLE", "fallback_used": False, "source_paths": []}),
        "fills": {
            "authority": "RUN_SCOPED_EVIDENCE" if observability.get("status") == "AVAILABLE" else "UNAVAILABLE",
            "fallback_used": False,
            "count": len(observability.get("fills") or []),
        },
        "position_campaigns": {
            "authority": "RUN_SCOPED_EVIDENCE" if observability.get("status") == "AVAILABLE" else "UNAVAILABLE",
            "fallback_used": False,
            "count": len(observability.get("position_campaigns") or []),
        },
        "current_positions": {
            "authority": final_state_authority,
            "fallback_used": bool(runtime_state_available),
            "final_hash_match": bool(final_hashes) and current_hashes == final_hashes,
        },
    }
    for artifact_class, entry in matrix.items():
        if isinstance(entry, dict) and entry.get("fallback_used"):
            entry.setdefault("fallback_reason", "final_hash_match_and_run_scoped_class_absence")
            entry.setdefault("final_hash_match", bool(final_hashes) and current_hashes == final_hashes)
    return matrix


def _summary_independent_acceptance_judgment(
    *,
    runtime_execution_status: str,
    requested_business_days: int,
    resolved_business_day_count: int,
    completed_business_day_count: int,
    window_resolution_status: str,
    lifecycle_status: str,
    summary_authority_matrix: dict[str, Any],
    legacy_request_preserved: bool,
) -> dict[str, Any]:
    runtime_execution = "PASS" if runtime_execution_status in {"COMPLETED", "PASS"} else (runtime_execution_status or "UNKNOWN")
    requested_window_resolution = "PASS" if window_resolution_status == "PASS" else "NOT_PASS"
    if not legacy_request_preserved:
        requested_window_resolution = "NOT_PASS"
    requested_window_conformance = (
        "PASS"
        if legacy_request_preserved
        and requested_business_days == resolved_business_day_count == completed_business_day_count
        and window_resolution_status == "PASS"
        else "NOT_PASS"
    )
    fallback_violations = [
        key
        for key, entry in summary_authority_matrix.items()
        if isinstance(entry, dict)
        and entry.get("fallback_used")
        and key in {"pm_decisions", "sell_planning", "non_executable_sell_decisions", "fills", "position_campaigns"}
        and entry.get("authority") != "RUN_SCOPED_EVIDENCE"
    ]
    summary_isolation = "PASS" if not fallback_violations else "NOT_PASS"
    lifecycle_judgment = "PASS" if lifecycle_status == "PASS" else "NOT_PASS"
    overall = (
        "PASS"
        if runtime_execution == "PASS"
        and requested_window_conformance == "PASS"
        and summary_isolation == "PASS"
        and lifecycle_judgment == "PASS"
        else "REVIEW_REQUIRED"
    )
    return {
        "runtime_execution_judgment": runtime_execution,
        "requested_window_resolution_judgment": requested_window_resolution,
        "requested_window_conformance_judgment": requested_window_conformance,
        "summary_evidence_isolation_judgment": summary_isolation,
        "lifecycle_consistency_judgment": lifecycle_judgment,
        "strategy_to_active_runtime_judgment": "NOT_ESTABLISHED",
        "overall_independent_judgment": overall,
        "fallback_violations": fallback_violations,
        "legacy_request_preserved": legacy_request_preserved,
        "requested_business_days": requested_business_days,
        "resolved_business_day_count": resolved_business_day_count,
        "completed_business_day_count": completed_business_day_count,
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    value = payload.get("items")
    return value if isinstance(value, list) else []


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _completed_business_days(*, run_state: dict[str, Any], fresh_summary: dict[str, Any]) -> set[str]:
    days = run_state.get("completed_business_days") or fresh_summary.get("completed_days") or []
    return {str(day) for day in days if str(day)}


def _business_date(row: dict[str, Any], *, fallback: str = "") -> str:
    return str(row.get("business_date") or row.get("_plan_date") or fallback or "")


def _in_completed_business_days(row: dict[str, Any], completed_business_days: set[str], *, fallback: str = "") -> bool:
    if not completed_business_days:
        return True
    return _business_date(row, fallback=fallback) in completed_business_days


def _filter_rows_by_business_days(
    rows: list[dict[str, Any]],
    completed_business_days: set[str],
    *,
    include_without_business_date: bool = False,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if include_without_business_date and not _business_date(row):
            filtered.append(row)
            continue
        if _in_completed_business_days(row, completed_business_days):
            filtered.append(row)
    return filtered


def _manifest_payload(payload: dict[str, Any]) -> dict[str, Any]:
    manifest = payload.get("manifest")
    return manifest if isinstance(manifest, dict) else payload


def _matches_requested_run(payload: dict[str, Any], *, run_id: str, run_dir: Path) -> bool:
    manifest = _manifest_payload(payload)
    evidence_root = str(manifest.get("runtime_test_evidence_root") or manifest.get("data_readiness_safety_runtime_test_evidence_root") or "")
    evidence_matches = not evidence_root or evidence_root == str(run_dir)
    if evidence_root and not evidence_matches:
        try:
            evidence_matches = Path(evidence_root).resolve() == run_dir.resolve()
        except OSError:
            evidence_matches = False
    payload_run_id = str(manifest.get("runtime_test_run_id") or manifest.get("data_readiness_safety_runtime_test_run_id") or "")
    return (not payload_run_id or payload_run_id == run_id) and evidence_matches


def _pm_artifact_status(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    input_contract = payload.get("input_contract") if isinstance(payload.get("input_contract"), dict) else {}
    status = str(payload.get("status") or payload.get("pm_status") or input_contract.get("status") or "")
    authority_status = str(
        payload.get("pm_runtime_adapter_authority_status")
        or payload.get("position_management_authority_status")
        or input_contract.get("pm_runtime_adapter_authority_status")
        or ""
    )
    input_status = str(payload.get("pm_input_schema_status") or input_contract.get("pm_input_schema_status") or "")
    reason = str(
        payload.get("reason")
        or payload.get("pm_reason")
        or payload.get("pm_review_reason")
        or input_contract.get("pm_runtime_adapter_authority_reason")
        or input_contract.get("pm_review_reason")
        or ""
    )
    decision_count = int(payload.get("pm_decision_count") or len(payload.get("decisions") or []))
    trace_status = "NOT_REQUIRED_EMPTY" if decision_count == 0 else ("AVAILABLE" if payload.get("decision_trace_path") else "EMBEDDED_OR_NOT_RETAINED")
    return {
        "position_management_status": status or "UNKNOWN",
        "position_management_authority_status": authority_status or "UNKNOWN",
        "position_management_input_status": input_status or "UNKNOWN",
        "position_management_reason": reason,
        "position_management_decision_count": decision_count,
        "position_management_trace_status": trace_status,
    }


def _is_pm_artifact_fatal(payload: dict[str, Any] | None) -> bool:
    status = _pm_artifact_status(payload)
    return any(
        str(status.get(field) or "").upper() in PM_RUNTIME_TEST_FATAL_STATUSES
        for field in (
            "position_management_status",
            "position_management_authority_status",
            "position_management_input_status",
        )
    )


def _pm_fatal_evidence_for_run(run_dir: Path, *, completed_business_days: set[str] | None = None) -> list[dict[str, Any]]:
    completed = completed_business_days or set()
    findings: list[dict[str, Any]] = []
    patterns = (
        ("sell_planning_position_management_evidence", "daily/*/sell_planning/position_management_evidence.json"),
        ("run_scoped_pm_decision_snapshot", "daily/*/position_management/pm_decisions.json"),
    )
    for source, pattern in patterns:
        for path in sorted(run_dir.glob(pattern)):
            business_date = path.parts[-3]
            if completed and business_date not in completed:
                continue
            payload = read_json_optional(path)
            if not payload or not _is_pm_artifact_fatal(payload):
                continue
            status = _pm_artifact_status(payload)
            findings.append(
                {
                    "business_date": business_date,
                    "source": source,
                    "path": str(path),
                    **status,
                }
            )
    return findings


def _summarize_pm_decisions(
    *,
    runtime_root: Path,
    run_dir: Path,
    run_id: str,
    available: bool,
    completed_business_days: set[str],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    run_evidence_seen = False
    run_evidence_counts: Counter[str] = Counter()
    fatal_statuses: list[dict[str, Any]] = []
    for path in sorted(run_dir.glob("daily/*/sell_planning/position_management_evidence.json")):
        business_date = path.parts[-3]
        if completed_business_days and business_date not in completed_business_days:
            continue
        payload = read_json_optional(path)
        if payload and _matches_requested_run(payload, run_id=run_id, run_dir=run_dir):
            run_evidence_seen = True
            pm_status = _pm_artifact_status(payload)
            if _is_pm_artifact_fatal(payload):
                fatal_statuses.append(
                    {
                        "business_date": business_date,
                        "path": str(path),
                        "status": pm_status["position_management_status"],
                        "authority_status": pm_status["position_management_authority_status"],
                        "reason": pm_status["position_management_reason"],
                    }
                )
            run_evidence_counts["HOLD"] += int(payload.get("pm_hold_count") or 0)
            run_evidence_counts["ADD"] += int(payload.get("pm_add_count") or 0)
            run_evidence_counts["REDUCE"] += int(payload.get("pm_reduce_count") or 0)
            run_evidence_counts["EXIT"] += int(payload.get("pm_exit_count") or 0)
    if available:
        for path in sorted((runtime_root / "runtime_state" / "position_management").glob("*/position_management_decisions.json")):
            if completed_business_days and path.parent.name not in completed_business_days:
                continue
            payload = read_json_optional(path)
            for decision in payload.get("decisions") or []:
                if isinstance(decision, dict) and _in_completed_business_days(decision, completed_business_days, fallback=path.parent.name):
                    record = _normalize_pm_decision_record(decision, fallback_business_date=path.parent.name)
                    record["_artifact_path"] = str(path)
                    record["_run_authority"] = "runtime_root_final_hash_match_completed_business_day_filter"
                    records.append(record)
    for path in sorted(run_dir.glob("daily/*/position_management/pm_decisions.json")):
        business_date = path.parts[-3]
        if completed_business_days and business_date not in completed_business_days:
            continue
        payload = read_json_optional(path)
        if payload and not _matches_requested_run(payload, run_id=run_id, run_dir=run_dir):
            continue
        for decision in payload.get("decisions") or []:
            if isinstance(decision, dict) and _in_completed_business_days(decision, completed_business_days, fallback=business_date):
                record = _normalize_pm_decision_record(decision, fallback_business_date=business_date)
                record["_artifact_path"] = str(path)
                record["_run_authority"] = "run_scoped_pm_decision_observability"
                records.append(record)
    records = _dedupe_pm_decision_records(records)
    decision_counts = Counter(str(row.get("decision") or "UNKNOWN") for row in records)
    for decision, count in run_evidence_counts.items():
        if count and not decision_counts.get(decision):
            decision_counts[decision] = count
    action_counts = Counter(str(row.get("runtime_action") or "UNKNOWN") for row in records)
    reason_counts = Counter(str(row.get("reason") or "") for row in records)
    by_date: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in records:
        by_date[str(row.get("business_date") or "")][str(row.get("decision") or "UNKNOWN")] += 1
    decision_count = len(records)
    if run_evidence_seen and decision_count == 0:
        decision_count = sum(run_evidence_counts.values())
    return {
        "source": (
            "run_scoped_position_management_evidence"
            if run_evidence_seen
            else "runtime_root_position_management_decisions_completed_business_day_filter"
            if available
            else "UNAVAILABLE_RUNTIME_STATE_AUTHORITY_NOT_CONFIRMED"
        ),
        "decision_count": decision_count,
        "decision_distribution": dict(sorted(decision_counts.items())),
        "runtime_action_distribution": dict(sorted(action_counts.items())),
        "reason_distribution": dict(reason_counts.most_common()),
        "decision_by_date": {date_key: dict(sorted(counts.items())) for date_key, counts in sorted(by_date.items())},
        "reduce_count": decision_counts.get("REDUCE", 0),
        "exit_count": decision_counts.get("EXIT", 0),
        "hold_count": decision_counts.get("HOLD", 0),
        "add_count": decision_counts.get("ADD", 0),
        "decision_records": records,
        "completed_business_day_filter": sorted(completed_business_days),
        "fatal_status_count": len(fatal_statuses),
        "fatal_statuses": fatal_statuses,
    }


def _normalize_pm_decision_record(decision: dict[str, Any], *, fallback_business_date: str) -> dict[str, Any]:
    record = dict(decision)
    decision_type = str(record.get("decision") or record.get("decision_type") or "UNKNOWN")
    decision_id = str(record.get("decision_id") or record.get("pm_decision_id") or "")
    reason = record.get("reason") if record.get("reason") not in (None, "") else record.get("decision_reason")
    runtime_action = record.get("runtime_action") if record.get("runtime_action") not in (None, "") else record.get("decision_status")
    record["decision"] = decision_type
    record["decision_type"] = decision_type
    record["decision_id"] = decision_id
    record["pm_decision_id"] = decision_id
    record["reason"] = reason or ""
    record["runtime_action"] = runtime_action or ""
    record["business_date"] = str(record.get("business_date") or fallback_business_date)
    return record


def _dedupe_pm_decision_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in records:
        key = (
            str(row.get("business_date") or ""),
            str(row.get("symbol") or ""),
            str(row.get("decision") or ""),
            str(row.get("decision_id") or ""),
        )
        existing = by_key.get(key)
        if not existing or existing.get("_run_authority") != "run_scoped_pm_decision_observability":
            by_key[key] = row
    return sorted(by_key.values(), key=lambda row: (str(row.get("business_date") or ""), str(row.get("symbol") or ""), str(row.get("decision_id") or "")))


def _collect_order_plan_items(
    *,
    runtime_root: Path,
    run_dir: Path,
    run_id: str,
    available: bool,
    completed_business_days: set[str],
) -> dict[str, list[dict[str, Any]]]:
    result = {"buy": [], "sell": [], "non_executable_sell_decisions": [], "summary_authority_matrix": {}}
    matrix: dict[str, Any] = {
        "buy_planning": {"authority": "UNAVAILABLE", "fallback_used": False, "source_paths": []},
        "sell_planning": {"authority": "UNAVAILABLE", "fallback_used": False, "source_paths": []},
        "non_executable_sell_decisions": {"authority": "UNAVAILABLE", "fallback_used": False, "source_paths": []},
    }
    if available:
        for path in sorted((runtime_root / "runtime_state" / "morning_pipeline").glob("*/order_plan.json")):
            if completed_business_days and path.parent.name not in completed_business_days:
                continue
            for item in _items(read_json_optional(path)):
                if isinstance(item, dict) and _in_completed_business_days(item, completed_business_days, fallback=path.parent.name):
                    result["buy"].append(
                        {
                            **item,
                            "_artifact_path": str(path),
                            "_plan_date": path.parent.name,
                            "_run_authority": "runtime_root_final_hash_match_completed_business_day_filter",
                        }
                    )
                    matrix["buy_planning"]["authority"] = "CURRENT_RUNTIME_FALLBACK_FINAL_HASH_MATCH"
                    matrix["buy_planning"]["fallback_used"] = True
                    matrix["buy_planning"]["source_paths"].append(str(path))
        for path in sorted((runtime_root / "runtime_state" / "sell_pipeline").glob("*/order_plan.json")):
            if completed_business_days and path.parent.name not in completed_business_days:
                continue
            payload = read_json_optional(path)
            for item in _items(payload):
                if isinstance(item, dict) and _in_completed_business_days(item, completed_business_days, fallback=path.parent.name):
                    result["sell"].append(
                        {
                            **item,
                            "_artifact_path": str(path),
                            "_plan_date": path.parent.name,
                            "_run_authority": "runtime_root_final_hash_match_completed_business_day_filter",
                        }
                    )
                    matrix["sell_planning"]["authority"] = "CURRENT_RUNTIME_FALLBACK_FINAL_HASH_MATCH"
                    matrix["sell_planning"]["fallback_used"] = True
                    matrix["sell_planning"]["source_paths"].append(str(path))
            for item in payload.get("non_executable_sell_decisions") or []:
                if isinstance(item, dict):
                    result["non_executable_sell_decisions"].append(
                        {
                            **item,
                            "_artifact_path": str(path),
                            "_plan_date": path.parent.name,
                            "_run_authority": "runtime_root_final_hash_match_completed_business_day_filter",
                        }
                    )
                    matrix["non_executable_sell_decisions"]["authority"] = "CURRENT_RUNTIME_FALLBACK_FINAL_HASH_MATCH"
                    matrix["non_executable_sell_decisions"]["fallback_used"] = True
                    matrix["non_executable_sell_decisions"]["source_paths"].append(str(path))
    for path in sorted(run_dir.glob("daily/*/sell_planning/sell_planning_manifest.json")):
        business_date = path.parts[-3]
        if completed_business_days and business_date not in completed_business_days:
            continue
        payload = read_json_optional(path)
        if payload and not _matches_requested_run(payload, run_id=run_id, run_dir=run_dir):
            continue
        manifest = _manifest_payload(payload)
        if matrix["sell_planning"]["authority"] != "RUN_SCOPED_EVIDENCE":
            matrix["sell_planning"]["source_paths"] = []
        matrix["sell_planning"]["authority"] = "RUN_SCOPED_EVIDENCE"
        matrix["sell_planning"]["fallback_used"] = False
        matrix["sell_planning"]["source_paths"].append(str(path))
        if matrix["non_executable_sell_decisions"]["authority"] != "RUN_SCOPED_EVIDENCE":
            matrix["non_executable_sell_decisions"]["source_paths"] = []
        matrix["non_executable_sell_decisions"]["authority"] = "RUN_SCOPED_EVIDENCE"
        matrix["non_executable_sell_decisions"]["fallback_used"] = False
        matrix["non_executable_sell_decisions"]["source_paths"].append(str(path))
        if int(manifest.get("pm_decision_count") or 0) == 0 and int(manifest.get("pm_exit_count") or 0) == 0 and int(manifest.get("pm_reduce_count") or 0) == 0:
            result["sell"] = [item for item in result["sell"] if str(item.get("_plan_date") or item.get("business_date") or "") != business_date]
            result["non_executable_sell_decisions"] = [
                item
                for item in result["non_executable_sell_decisions"]
                if str(item.get("_plan_date") or item.get("business_date") or "") != business_date
            ]
    for path in sorted(run_dir.glob("daily/*/submit/runtime_manifest.json")):
        business_date = path.parts[-3]
        if completed_business_days and business_date not in completed_business_days:
            continue
        payload = read_json_optional(path)
        if payload and not _matches_requested_run(payload, run_id=run_id, run_dir=run_dir):
            continue
        manifest = _manifest_payload(payload)
        for item in manifest.get("submit_guard_item_evidence") or []:
            if not isinstance(item, dict):
                continue
            side = str(item.get("side") or "").upper()
            if side not in {"BUY", "SELL"}:
                continue
            contract = item.get("quantity_contract") if isinstance(item.get("quantity_contract"), dict) else {}
            quality = contract.get("buy_quality_authority") if isinstance(contract.get("buy_quality_authority"), dict) else {}
            plan_item = {
                **item,
                "business_date": item.get("business_date") or business_date,
                "side": side,
                "quantity": _float(item.get("quantity") or item.get("selected_quantity") or contract.get("selected_quantity") or contract.get("planned_quantity")),
                "order_plan_item_id": item.get("order_plan_item_id") or contract.get("source_planning_id") or contract.get("planning_intent_source") or "",
                "pending_item_id": item.get("pending_item_id") or "",
                "source_decision_id": item.get("source_decision_id") or contract.get("source_planning_id") or contract.get("planning_intent_source") or "",
                "quality_decision_id": item.get("quality_decision_id") or contract.get("quality_decision_id") or quality.get("quality_decision_id") or "",
                "quantity_contract": contract,
                "_artifact_path": str(path),
                "_plan_date": business_date,
                "_run_authority": "run_scoped_submit_guard_item_evidence",
            }
            result["buy" if side == "BUY" else "sell"].append(plan_item)
            key = "buy_planning" if side == "BUY" else "sell_planning"
            if matrix[key]["authority"] != "RUN_SCOPED_EVIDENCE":
                matrix[key]["source_paths"] = []
            matrix[key]["authority"] = "RUN_SCOPED_EVIDENCE"
            matrix[key]["fallback_used"] = False
            matrix[key]["source_paths"].append(str(path))
    if not result["buy"] or not result["sell"]:
        fill_plans = _run_scoped_plan_proxies_from_fills(run_dir=run_dir, run_id=run_id, completed_business_days=completed_business_days)
        if not result["buy"]:
            result["buy"] = fill_plans["buy"]
        if not result["sell"]:
            result["sell"] = fill_plans["sell"]
    for side_key in ("buy", "sell"):
        deduped: dict[tuple[str, str, str, float, str], dict[str, Any]] = {}
        for item in result[side_key]:
            key = (
                str(item.get("_plan_date") or item.get("business_date") or ""),
                str(item.get("side") or side_key).upper(),
                str(item.get("symbol") or ""),
                _float(item.get("quantity")),
                str(item.get("pending_item_id") or ""),
            )
            existing = deduped.get(key)
            if not existing or str(item.get("_run_authority") or "") == "run_scoped_submit_guard_item_evidence":
                deduped[key] = item
        result[side_key] = sorted(deduped.values(), key=lambda row: (str(row.get("_plan_date") or row.get("business_date") or ""), str(row.get("symbol") or ""), str(row.get("pending_item_id") or "")))
    matrix["buy_planning"]["source_paths"] = sorted(set(matrix["buy_planning"]["source_paths"]))
    matrix["sell_planning"]["source_paths"] = sorted(set(matrix["sell_planning"]["source_paths"]))
    matrix["non_executable_sell_decisions"]["source_paths"] = sorted(set(matrix["non_executable_sell_decisions"]["source_paths"]))
    result["summary_authority_matrix"] = matrix
    return result


def _run_scoped_plan_proxies_from_fills(*, run_dir: Path, run_id: str, completed_business_days: set[str]) -> dict[str, list[dict[str, Any]]]:
    result = {"buy": [], "sell": []}
    for path in sorted(run_dir.glob("daily/*/execution/fills.json")):
        business_date = path.parts[-3]
        if completed_business_days and business_date not in completed_business_days:
            continue
        payload = read_json_optional(path)
        if payload and not _matches_requested_run(payload, run_id=run_id, run_dir=run_dir):
            continue
        for fill in payload.get("fills") or []:
            if not isinstance(fill, dict):
                continue
            side = str(fill.get("side") or "").upper()
            if side not in {"BUY", "SELL"}:
                continue
            source_decision = str(fill.get("source_decision_type") or ("BUY" if side == "BUY" else "UNKNOWN")).upper()
            plan = {
                "business_date": fill.get("business_date") or business_date,
                "symbol": fill.get("symbol") or "",
                "side": side,
                "quantity": _float(fill.get("quantity")),
                "price": fill.get("execution_price"),
                "order_plan_item_id": fill.get("order_plan_item_id") or "",
                "pending_item_id": fill.get("pending_item_id") or "",
                "quantity_contract": {
                    "source_decision": source_decision,
                    "source_decision_id": fill.get("source_decision_id") or "",
                    "final_sell_quantity": _float(fill.get("quantity")) if side == "SELL" else 0.0,
                    "status": "DERIVED_FROM_RUN_SCOPED_FILL_OBSERVABILITY",
                },
                "_artifact_path": str(path),
                "_plan_date": business_date,
                "_run_authority": "run_scoped_fill_observability_execution_equivalent_plan_proxy",
            }
            result["buy" if side == "BUY" else "sell"].append(plan)
    return result


def _run_scoped_orders_from_fills(observability: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for fill in observability.get("fills") if isinstance(observability.get("fills"), list) else []:
        if not isinstance(fill, dict):
            continue
        rows.append(
            {
                "record_type": "order",
                "dedup_key": f"runtime_v2_submit:run-scoped-fill:{fill.get('execution_id') or fill.get('order_id') or ''}",
                "business_date": fill.get("business_date") or "",
                "pending_item_id": fill.get("pending_item_id") or fill.get("execution_id") or "",
                "side": str(fill.get("side") or "UNKNOWN").upper(),
                "symbol": fill.get("symbol") or "",
                "quantity": _float(fill.get("quantity")),
                "order_id": fill.get("order_id") or "",
                "_run_authority": "run_scoped_fill_observability_execution_equivalent_order",
            }
        )
    return rows


def _run_scoped_executions_from_fills(observability: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for fill in observability.get("fills") if isinstance(observability.get("fills"), list) else []:
        if not isinstance(fill, dict):
            continue
        rows.append(
            {
                "record_type": "execution",
                "business_date": fill.get("business_date") or "",
                "side": str(fill.get("side") or "UNKNOWN").upper(),
                "symbol": fill.get("symbol") or "",
                "filled_quantity": _float(fill.get("quantity")),
                "quantity": _float(fill.get("quantity")),
                "price": fill.get("execution_price"),
                "execution_id": fill.get("execution_id") or "",
                "pending_item_id": fill.get("pending_item_id") or "",
                "_run_authority": "run_scoped_fill_observability",
            }
        )
    return rows


def _is_submitted_order_record(row: dict[str, Any]) -> bool:
    return (
        row.get("record_type") == "order"
        and str(row.get("dedup_key") or "").startswith("runtime_v2_submit:")
        and bool(row.get("business_date"))
        and bool(row.get("pending_item_id"))
    )


def _summarize_trading(
    *,
    plans: dict[str, list[dict[str, Any]]],
    orders: list[dict[str, Any]],
    executions: list[dict[str, Any]],
    pending_state: dict[str, Any],
) -> dict[str, Any]:
    submitted = [row for row in orders if _is_submitted_order_record(row)]
    submitted_counter = Counter(str(row.get("side") or "UNKNOWN") for row in submitted)
    execution_counter = Counter(str(row.get("side") or "UNKNOWN") for row in executions if row.get("record_type") == "execution")
    execution_quantity = Counter()
    for row in executions:
        if row.get("record_type") == "execution":
            execution_quantity[str(row.get("side") or "UNKNOWN")] += _float(row.get("filled_quantity") or row.get("quantity"))
    pending_items = [item for item in _items(pending_state) if isinstance(item, dict)]
    pending_counter = Counter(str(item.get("side") or "UNKNOWN") for item in pending_items)
    return {
        "buy_plan_count": len(plans["buy"]),
        "sell_plan_count": len(plans["sell"]),
        "submitted_order_count": len(submitted),
        "submitted_order_distribution": dict(sorted(submitted_counter.items())),
        "submitted_order_double_count_prevention": {
            "submitted_order_filter": "record_type=order,dedup_key_prefix=runtime_v2_submit,business_date_present,pending_item_id_present",
            "ignored_execution_equivalent_order_records": len([row for row in orders if row.get("record_type") == "order"]) - len(submitted),
        },
        "execution_count": len([row for row in executions if row.get("record_type") == "execution"]),
        "execution_distribution": dict(sorted(execution_counter.items())),
        "execution_quantity_by_side": dict(sorted(execution_quantity.items())),
        "sell_execution_count": execution_counter.get("SELL", 0),
        "buy_execution_count": execution_counter.get("BUY", 0),
        "pending_state": pending_state.get("state") or pending_state.get("status") or "",
        "pending_item_distribution": dict(sorted(pending_counter.items())),
    }


def _summarize_reduce_exit(*, plans: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    source_counter = Counter()
    terminal_counter = Counter()
    rows: list[dict[str, Any]] = []
    non_executable_rows: list[dict[str, Any]] = []
    unknown = 0
    for item in plans["sell"]:
        contract = item.get("quantity_contract") if isinstance(item.get("quantity_contract"), dict) else {}
        source_decision = str(contract.get("source_decision") or "")
        if not source_decision:
            source_decision = "UNKNOWN"
            unknown += 1
        source_counter[source_decision] += 1
        rows.append(
            {
                "business_date": item.get("_plan_date") or item.get("business_date") or "",
                "symbol": item.get("symbol") or "",
                "source_decision": source_decision,
                "quantity": _float(item.get("quantity") or contract.get("final_sell_quantity")),
                "reduce_intensity": contract.get("reduce_intensity") or "",
                "position_quantity_before": _float(contract.get("position_quantity_before")),
                "sellable_quantity": _float(contract.get("sellable_quantity")),
                "target_reduce_ratio": _float(contract.get("target_reduce_ratio")),
                "expected_remaining_quantity": _float(contract.get("expected_remaining_quantity")),
                "quantity_contract_version": contract.get("quantity_contract_version") or "",
                "status": contract.get("status") or item.get("status") or "",
                "artifact_path": item.get("_artifact_path") or "",
            }
        )
    for item in plans.get("non_executable_sell_decisions", []):
        contract = item.get("quantity_contract") if isinstance(item.get("quantity_contract"), dict) else {}
        feasibility_status = str(item.get("execution_feasibility_status") or contract.get("execution_feasibility_status") or "")
        reason = str(contract.get("reason") or item.get("reason") or "")
        terminal_counter[feasibility_status or "UNKNOWN"] += 1
        non_executable_rows.append(
            {
                "business_date": item.get("_plan_date") or item.get("business_date") or "",
                "symbol": item.get("symbol") or "",
                "source_decision": contract.get("source_decision") or item.get("original_decision") or "",
                "source_decision_id": item.get("source_decision_id") or contract.get("source_decision_id") or "",
                "execution_feasibility_status": feasibility_status,
                "reason": reason,
                "status": contract.get("status") or item.get("status") or "",
                "effective_action": item.get("effective_action") or contract.get("effective_action") or "",
                "pending_order_generated": item.get("pending_order_generated", contract.get("pending_order_generated")),
                "runtime_continuation_status": item.get("runtime_continuation_status") or contract.get("runtime_continuation_status") or "",
                "position_lifecycle_event": contract.get("position_lifecycle_event") or item.get("position_lifecycle_event") or "",
                "position_quantity_before": _float(contract.get("position_quantity_before")),
                "position_quantity_after": _float(item.get("position_quantity_after", contract.get("position_quantity_after"))),
                "expected_remaining_quantity": _float(contract.get("expected_remaining_quantity")),
                "final_sell_quantity": _float(contract.get("final_sell_quantity")),
                "rounded_executable_quantity": _float(contract.get("rounded_executable_quantity", contract.get("rounded_reduce_quantity"))),
                "quantity_contract_version": contract.get("quantity_contract_version") or "",
                "artifact_path": item.get("_artifact_path") or "",
            }
        )
    return {
        "sell_plan_source_decision_distribution": dict(sorted(source_counter.items())),
        "reduce_sell_plan_count": source_counter.get("REDUCE", 0),
        "exit_sell_plan_count": source_counter.get("EXIT", 0),
        "sell_plan_items_with_unknown_source_decision": unknown,
        "non_executable_sell_decision_count": len(non_executable_rows),
        "non_executable_reduce_terminal_count": len([row for row in non_executable_rows if row.get("source_decision") == "REDUCE"]),
        "non_executable_reduce_reason_distribution": dict(sorted(Counter(str(row.get("reason") or "UNKNOWN") for row in non_executable_rows if row.get("source_decision") == "REDUCE").items())),
        "non_executable_reduce_feasibility_distribution": dict(sorted(terminal_counter.items())),
        "non_executable_items": non_executable_rows,
        "items": rows,
    }


def _build_trade_attribution(
    *,
    sell_plan_items: list[dict[str, Any]],
    executions: list[dict[str, Any]],
    pm_decisions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], float | None]:
    findings: list[dict[str, Any]] = []
    sell_plans = defaultdict(list)
    for item in sell_plan_items:
        sell_plans[(str(item.get("_plan_date") or item.get("business_date") or ""), str(item.get("symbol") or ""))].append(item)
    pm_index = {(str(row.get("business_date") or ""), str(row.get("symbol") or "")): row for row in pm_decisions}
    positions: dict[str, dict[str, float]] = defaultdict(lambda: {"quantity": 0.0, "average_price": 0.0})
    attributions: list[dict[str, Any]] = []
    realized_total = 0.0
    traceable = True
    for row in sorted(
        [e for e in executions if e.get("record_type") == "execution"],
        key=lambda x: (
            str(x.get("business_date") or ""),
            0 if str(x.get("side") or "").upper() == "BUY" else 1,
            str(x.get("record_id") or x.get("execution_id") or ""),
        ),
    ):
        symbol = str(row.get("symbol") or row.get("broker_issue_code") or "")
        side = str(row.get("side") or "").upper()
        qty = _float(row.get("filled_quantity") or row.get("quantity"))
        price = _float(row.get("price") or row.get("average_price") or row.get("market_price"), default=-1.0)
        pos = positions[symbol]
        if side == "BUY":
            old_qty = pos["quantity"]
            new_qty = old_qty + qty
            if new_qty > 0:
                pos["average_price"] = ((old_qty * pos["average_price"]) + (qty * price)) / new_qty
            pos["quantity"] = new_qty
            continue
        if side != "SELL":
            continue
        business_date = str(row.get("business_date") or "")
        matched_plan = _match_sell_plan(sell_plans.get((business_date, symbol), []), qty)
        contract = matched_plan.get("quantity_contract") if isinstance(matched_plan.get("quantity_contract"), dict) else {}
        source_decision = str(contract.get("source_decision") or "UNKNOWN")
        pm = pm_index.get((business_date, symbol), {})
        if price < 0 or pos["quantity"] <= 0 or qty <= 0 or not matched_plan:
            traceable = False
            findings.append(
                _summary_finding(
                    "REVIEW_REQUIRED",
                    "REVIEW_REQUIRED_TRADE_LEVEL_REALIZED_PNL_NOT_TRACEABLE",
                    {"business_date": business_date, "symbol": symbol, "quantity": qty, "matched_sell_plan": bool(matched_plan)},
                )
            )
            realized_pnl = None
        else:
            realized_pnl = (price - pos["average_price"]) * qty
            realized_total += realized_pnl
        remaining = max(pos["quantity"] - qty, 0.0)
        attributions.append(
            {
                "business_date": business_date,
                "symbol": symbol,
                "side": "SELL",
                "quantity": qty,
                "price": price if price >= 0 else None,
                "source_decision": source_decision,
                "reduce_intensity": contract.get("reduce_intensity") or "",
                "pm_decision_id": pm.get("decision_id") or "",
                "pm_reason": pm.get("reason") or "",
                "pm_runtime_action": pm.get("runtime_action") or "",
                "entry_average_price": pos["average_price"] if pos["quantity"] > 0 else None,
                "realized_pnl": realized_pnl,
                "pnl_traceability": "CALCULATED_FROM_LEDGER_AVERAGE_COST" if realized_pnl is not None else "REVIEW_REQUIRED_TRADE_LEVEL_REALIZED_PNL_NOT_TRACEABLE",
                "remaining_quantity_after_trade": remaining,
                "sell_plan_artifact_path": matched_plan.get("_artifact_path") or "",
                "execution_id": row.get("execution_id") or row.get("record_id") or "",
            }
        )
        pos["quantity"] = remaining
    return attributions, findings, realized_total if traceable else None


def _match_sell_plan(candidates: list[dict[str, Any]], quantity: float) -> dict[str, Any]:
    if not candidates:
        return {}
    for item in candidates:
        if abs(_float(item.get("quantity")) - quantity) < 0.0001:
            return item
    return candidates[0]


def _summarize_performance(
    *,
    fresh_summary: dict[str, Any],
    current_state: dict[str, Any],
    realized_pnl_from_trades: float | None,
    runtime_state_available: bool,
    current_state_authority: str = "CURRENT_RUNTIME_ROOT_FINAL_HASH_MATCH",
    current_state_authority_status: str = "CANONICAL_CURRENT_STATE",
    observability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    initial = _float(fresh_summary.get("initial_cash") or current_state.get("runtime_evaluation_capital"))
    final_equity = _float(current_state.get("total_equity") or (_float(current_state.get("cash")) + _float(current_state.get("market_value"))))
    derived = _derive_performance_from_run_scoped_campaigns(initial=initial, observability=observability or {})
    if not runtime_state_available and derived:
        return {
            "initial_equity": initial if initial else None,
            "final_cash": "MISSING",
            "final_market_value": derived["final_market_value"],
            "final_equity": derived["final_equity"],
            "total_return_amount": derived["total_return_amount"],
            "total_return_percent": derived["total_return_percent"],
            "realized_pnl": derived["realized_pnl"],
            "realized_pnl_method": derived["realized_pnl_method"],
            "unrealized_pnl": derived["unrealized_pnl"],
            "position_count": derived["position_count"],
            "performance_authority": derived["authority"],
            "performance_authority_status": derived["status"],
            "canonical_final_equity_status": "MISSING",
            "negative_return_runtime_effect": "DOES_NOT_FAIL_RUNTIME_JUDGMENT",
        }
    total_return = final_equity - initial if runtime_state_available and initial else None
    realized = current_state.get("realized_pnl")
    realized_method = "current_state.realized_pnl"
    if realized in (None, ""):
        realized = realized_pnl_from_trades
        realized_method = "trade_attribution_average_cost" if realized is not None else "NOT_TRACEABLE"
    unrealized = current_state.get("new_unrealized_pnl")
    if unrealized in (None, "") and not (current_state.get("positions") or []):
        unrealized = 0.0
    return {
        "initial_equity": initial if initial else None,
        "final_cash": current_state.get("cash"),
        "final_market_value": current_state.get("market_value"),
        "final_equity": final_equity if runtime_state_available else None,
        "total_return_amount": total_return,
        "total_return_percent": (total_return / initial * 100.0) if total_return is not None and initial else None,
        "realized_pnl": realized,
        "realized_pnl_method": realized_method,
        "unrealized_pnl": unrealized,
        "position_count": len(current_state.get("positions") or []),
        "performance_authority": current_state_authority if runtime_state_available else "NOT_AVAILABLE",
        "performance_authority_status": current_state_authority_status if runtime_state_available else "NOT_AVAILABLE",
        "canonical_final_equity_status": "AVAILABLE" if runtime_state_available else "MISSING",
        "negative_return_runtime_effect": "DOES_NOT_FAIL_RUNTIME_JUDGMENT",
    }


def _derive_performance_from_run_scoped_campaigns(*, initial: float, observability: dict[str, Any]) -> dict[str, Any]:
    campaigns = observability.get("position_campaigns") if isinstance(observability.get("position_campaigns"), list) else []
    fills = observability.get("fills") if isinstance(observability.get("fills"), list) else []
    if campaigns:
        realized = _sum_available_values(campaign.get("realized_pnl") for campaign in campaigns if isinstance(campaign, dict))
        unrealized = _sum_available_values(campaign.get("unrealized_pnl") for campaign in campaigns if isinstance(campaign, dict))
        total_return = realized + unrealized
        open_count = len(
            [
                campaign
                for campaign in campaigns
                if isinstance(campaign, dict)
                and str(campaign.get("campaign_status") or "").upper() == "OPEN"
                and _float(campaign.get("current_quantity")) > POSITION_QUANTITY_EPSILON
            ]
        )
        return {
            "status": "DERIVABLE_EXACT_FROM_RUN_SCOPED_POSITION_CAMPAIGNS",
            "authority": "RUN_SCOPED_POSITION_CAMPAIGN_OBSERVABILITY",
            "final_market_value": "MISSING",
            "final_equity": initial + total_return if initial else None,
            "total_return_amount": total_return,
            "total_return_percent": (total_return / initial * 100.0) if initial else None,
            "realized_pnl": realized,
            "unrealized_pnl": unrealized,
            "realized_pnl_method": "run_scoped_position_campaigns_gross",
            "position_count": open_count,
        }
    if initial and observability.get("status") == "AVAILABLE" and not fills:
        return {
            "status": "DERIVABLE_EXACT_FROM_RUN_SCOPED_NO_TRADE_EVIDENCE",
            "authority": "RUN_SCOPED_NO_TRADE_OBSERVABILITY",
            "final_market_value": 0.0,
            "final_equity": initial,
            "total_return_amount": 0.0,
            "total_return_percent": 0.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "realized_pnl_method": "run_scoped_no_trade_observability",
            "position_count": 0,
        }
    return {}


def _summarize_current_positions(current_state: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for pos in current_state.get("positions") or []:
        if not isinstance(pos, dict):
            continue
        rows.append(
            {
                "symbol": pos.get("symbol") or "",
                "quantity": _float(pos.get("quantity")),
                "average_price": pos.get("average_price"),
                "current_price": pos.get("current_price"),
                "market_value": pos.get("market_value"),
                "unrealized_pnl": pos.get("unrealized_pnl"),
                "valuation_as_of": pos.get("valuation_as_of") or current_state.get("valuation_as_of") or "",
            }
        )
    return rows


def _summarize_lifecycle(
    *,
    pm: dict[str, Any],
    trading: dict[str, Any],
    reduce_exit: dict[str, Any],
    current_state: dict[str, Any],
    pending_state: dict[str, Any],
    run_scoped_position_authority: bool = False,
) -> dict[str, Any]:
    pending_consistent = _pending_empty_or_explained(trading=trading, pending_state=pending_state)
    reduce_resolution = _classify_pm_reduce_lifecycle_outcomes(pm=pm, reduce_exit=reduce_exit)
    checks = {
        "PM_EXIT_TO_SELL_PLAN": pm.get("exit_count", 0) == reduce_exit.get("exit_sell_plan_count", 0),
        "PM_REDUCE_TO_PARTIAL_SELL_PLAN": reduce_resolution["status"] == "PASS",
        "SELL_PLAN_TO_SUBMIT": trading.get("sell_plan_count", 0) == trading.get("submitted_order_distribution", {}).get("SELL", 0),
        "SELL_SUBMIT_TO_EXECUTION": trading.get("submitted_order_distribution", {}).get("SELL", 0) == trading.get("execution_distribution", {}).get("SELL", 0),
        "LEDGER_TO_CURRENT": bool(current_state) or run_scoped_position_authority,
        "PENDING_EMPTY_OR_EXPLAINED": pending_consistent,
    }
    return {
        "status": "PASS" if all(checks.values()) else "REVIEW_REQUIRED",
        "checks": checks,
        "check_semantics": {
            "PM_EXIT_TO_SELL_PLAN": "PASS_WHEN_COUNTS_MATCH_OR_BOTH_ZERO",
            "PM_REDUCE_TO_PARTIAL_SELL_PLAN": "PASS_WHEN_EACH_PM_REDUCE_RESOLVES_TO_EXACTLY_ONE_EXECUTABLE_SELL_PLAN_OR_APPROVED_NON_EXECUTABLE_TERMINAL_OUTCOME",
            "SELL_PLAN_TO_SUBMIT": "PASS_WHEN_COUNTS_MATCH_OR_BOTH_ZERO",
            "SELL_SUBMIT_TO_EXECUTION": "PASS_WHEN_COUNTS_MATCH_OR_BOTH_ZERO",
            "LEDGER_TO_CURRENT": "PASS_WHEN_FINAL_CURRENT_STATE_AVAILABLE_OR_RUN_SCOPED_POSITION_CAMPAIGN_AUTHORITY_AVAILABLE_FOR_PAST_RUN",
            "PENDING_EMPTY_OR_EXPLAINED": "PASS_WHEN_EMPTY_CONSUMED_TERMINALIZED_OR_EXECUTION_EXPLAINS_FINAL_PENDING_STATE",
        },
        "pm_reduce_count": pm.get("reduce_count", 0),
        "executable_reduce_sell_plan_count": reduce_resolution["executable_reduce_sell_plan_count"],
        "non_executable_reduce_terminal_count": reduce_resolution["non_executable_reduce_terminal_count"],
        "unresolved_reduce_count": reduce_resolution["unresolved_reduce_count"],
        "conflicting_reduce_count": reduce_resolution["conflicting_reduce_count"],
        "non_executable_reduce_reason_distribution": reduce_resolution["non_executable_reduce_reason_distribution"],
        "reduce_lifecycle_outcome_distribution": reduce_resolution["outcome_distribution"],
        "reduce_lifecycle_items": reduce_resolution["items"],
        "non_executable_reduce_items": reduce_resolution["non_executable_items"],
        "unresolved_reduce_items": reduce_resolution["unresolved_items"],
        "conflicting_reduce_items": reduce_resolution["conflicting_items"],
        "pm_exit_count": pm.get("exit_count", 0),
        "sell_plan_count": trading.get("sell_plan_count", 0),
        "submitted_sell_order_count": trading.get("submitted_order_distribution", {}).get("SELL", 0),
        "sell_execution_count": trading.get("execution_distribution", {}).get("SELL", 0),
    }


def _classify_pm_reduce_lifecycle_outcomes(*, pm: dict[str, Any], reduce_exit: dict[str, Any]) -> dict[str, Any]:
    pm_reduce_records = [row for row in pm.get("decision_records", []) if str(row.get("decision") or row.get("decision_type") or "") == "REDUCE"]
    reduce_plans = [row for row in reduce_exit.get("items", []) if str(row.get("source_decision") or "") == "REDUCE"]
    terminal_rows = [row for row in reduce_exit.get("non_executable_items", []) if str(row.get("source_decision") or "") == "REDUCE"]
    items: list[dict[str, Any]] = []
    if not pm_reduce_records:
        fallback_pm_reduce_count = int(pm.get("reduce_count") or 0)
        executable_count = int(reduce_exit.get("reduce_sell_plan_count") or 0)
        terminal_count = int(reduce_exit.get("non_executable_reduce_terminal_count") or 0)
        unresolved = max(fallback_pm_reduce_count - executable_count - terminal_count, 0)
        return {
            "status": "PASS" if fallback_pm_reduce_count == executable_count + terminal_count and unresolved == 0 else "REVIEW_REQUIRED",
            "executable_reduce_sell_plan_count": executable_count,
            "non_executable_reduce_terminal_count": terminal_count,
            "unresolved_reduce_count": unresolved,
            "conflicting_reduce_count": 0,
            "non_executable_reduce_reason_distribution": reduce_exit.get("non_executable_reduce_reason_distribution", {}),
            "outcome_distribution": {
                "EXECUTABLE_WITH_SELL_PLAN": executable_count,
                "NON_EXECUTABLE_TERMINAL": terminal_count,
                "UNRESOLVED": unresolved,
                "CONFLICTING": 0,
            },
            "items": [],
            "non_executable_items": terminal_rows,
            "unresolved_items": [],
            "conflicting_items": [],
        }

    outcome_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    non_executable_items: list[dict[str, Any]] = []
    unresolved_items: list[dict[str, Any]] = []
    conflicting_items: list[dict[str, Any]] = []
    for decision in pm_reduce_records:
        plans = _matching_reduce_plans(decision=decision, plans=reduce_plans)
        terminals = _matching_reduce_terminals(decision=decision, terminals=terminal_rows)
        valid_terminals = [row for row in terminals if _is_approved_non_executable_reduce_terminal(row)]
        invalid_terminals = [row for row in terminals if not _is_approved_non_executable_reduce_terminal(row)]
        if len(plans) == 1 and not terminals:
            outcome = "EXECUTABLE_WITH_SELL_PLAN"
        elif not plans and len(valid_terminals) == 1 and not invalid_terminals:
            outcome = "NON_EXECUTABLE_TERMINAL"
        elif plans and terminals:
            outcome = "CONFLICTING"
        elif len(plans) > 1 or len(valid_terminals) > 1:
            outcome = "CONFLICTING"
        else:
            outcome = "UNRESOLVED"
        row = {
            "business_date": decision.get("business_date") or "",
            "symbol": decision.get("symbol") or "",
            "pm_decision_id": decision.get("decision_id") or decision.get("pm_decision_id") or "",
            "position_campaign_id": decision.get("position_campaign_id") or "",
            "outcome": outcome,
            "compatible_sell_plan_count": len(plans),
            "compatible_non_executable_terminal_count": len(terminals),
            "valid_non_executable_terminal_count": len(valid_terminals),
            "invalid_non_executable_terminal_count": len(invalid_terminals),
            "sell_plan_artifact_paths": sorted({str(plan.get("artifact_path") or "") for plan in plans if plan.get("artifact_path")}),
            "terminal_artifact_paths": sorted({str(item.get("artifact_path") or "") for item in terminals if item.get("artifact_path")}),
        }
        outcome_counts[outcome] += 1
        if outcome == "NON_EXECUTABLE_TERMINAL":
            reason = str(valid_terminals[0].get("reason") or "UNKNOWN")
            reason_counts[reason] += 1
            non_executable_items.append({**row, "reason": reason, "execution_feasibility_status": valid_terminals[0].get("execution_feasibility_status") or ""})
        elif outcome == "UNRESOLVED":
            unresolved_items.append(row)
        elif outcome == "CONFLICTING":
            conflicting_items.append(row)
        items.append(row)
    return {
        "status": "PASS" if not unresolved_items and not conflicting_items else "REVIEW_REQUIRED",
        "executable_reduce_sell_plan_count": outcome_counts["EXECUTABLE_WITH_SELL_PLAN"],
        "non_executable_reduce_terminal_count": outcome_counts["NON_EXECUTABLE_TERMINAL"],
        "unresolved_reduce_count": outcome_counts["UNRESOLVED"],
        "conflicting_reduce_count": outcome_counts["CONFLICTING"],
        "non_executable_reduce_reason_distribution": dict(sorted(reason_counts.items())),
        "outcome_distribution": dict(sorted(outcome_counts.items())),
        "items": items,
        "non_executable_items": non_executable_items,
        "unresolved_items": unresolved_items,
        "conflicting_items": conflicting_items,
    }


def _matching_reduce_plans(*, decision: dict[str, Any], plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [plan for plan in plans if _same_reduce_decision_key(decision=decision, row=plan)]


def _matching_reduce_terminals(*, decision: dict[str, Any], terminals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [terminal for terminal in terminals if _same_reduce_decision_key(decision=decision, row=terminal)]


def _same_reduce_decision_key(*, decision: dict[str, Any], row: dict[str, Any]) -> bool:
    if str(decision.get("business_date") or "") != str(row.get("business_date") or ""):
        return False
    if str(decision.get("symbol") or "") != str(row.get("symbol") or ""):
        return False
    decision_id = str(decision.get("decision_id") or decision.get("pm_decision_id") or "")
    row_decision_id = str(row.get("source_decision_id") or "")
    if decision_id and row_decision_id:
        return decision_id == row_decision_id
    return True


def _is_approved_non_executable_reduce_terminal(row: dict[str, Any]) -> bool:
    before = _float(row.get("position_quantity_before"))
    after = _float(row.get("position_quantity_after"))
    expected_remaining = _float(row.get("expected_remaining_quantity"))
    return (
        str(row.get("source_decision") or "") == "REDUCE"
        and str(row.get("execution_feasibility_status") or "") == REDUCE_NON_EXECUTABLE_FEASIBILITY_STATUS
        and str(row.get("reason") or "") == REDUCE_NON_EXECUTABLE_REASON
        and str(row.get("status") or "") == "NOT_EXECUTABLE"
        and str(row.get("effective_action") or "") == "NO_SELL_ORDER"
        and row.get("pending_order_generated") is False
        and str(row.get("runtime_continuation_status") or "") == "PASS"
        and str(row.get("position_lifecycle_event") or "") == REDUCE_NON_EXECUTABLE_LIFECYCLE_EVENT
        and abs(_float(row.get("final_sell_quantity"))) <= POSITION_QUANTITY_EPSILON
        and abs(_float(row.get("rounded_executable_quantity"))) <= POSITION_QUANTITY_EPSILON
        and abs(after - before) <= POSITION_QUANTITY_EPSILON
        and abs(expected_remaining - before) <= POSITION_QUANTITY_EPSILON
    )


def _pending_empty_or_explained(*, trading: dict[str, Any], pending_state: dict[str, Any]) -> bool:
    state = str(pending_state.get("state") or pending_state.get("status") or "").upper()
    pending_items = sum(int(count or 0) for count in (trading.get("pending_item_distribution") or {}).values())
    if state in {"", "EMPTY", "CONSUMED", "TERMINALIZED", "NOT_REQUIRED"} and pending_items == 0:
        return True
    if (
        trading.get("submitted_order_count", 0) == trading.get("execution_count", 0)
        and trading.get("submitted_order_count", 0) > 0
        and trading.get("sell_plan_count", 0) == trading.get("submitted_order_distribution", {}).get("SELL", 0)
    ):
        return True
    return False


def _summarize_external_effects(*, run_dir: Path, fresh_summary: dict[str, Any]) -> dict[str, Any]:
    policy = fresh_summary.get("external_effect_policy") if isinstance(fresh_summary.get("external_effect_policy"), dict) else {}
    audits = [read_json_optional(path) for path in sorted(run_dir.glob("daily/*/*/external_effect_audit.json"))]
    truthy_policy = {key: value for key, value in policy.items() if value is True}
    audit_review = [audit for audit in audits if audit.get("status") not in {"", "PASS"}]
    return {
        "policy": policy,
        "historical_external_effects_disabled": not truthy_policy,
        "audit_count": len(audits),
        "audit_review_required_count": len(audit_review),
        "broker_write": bool(policy.get("broker_write")),
        "external_delivery": bool(policy.get("external_delivery")),
        "jquants_fetch": bool(policy.get("jquants_fetch")),
        "tachibana_api": bool(policy.get("tachibana_api")),
    }


def _metric(
    value: Any,
    *,
    status: str,
    authority: str,
    confidence: str = "DERIVABLE_PARTIAL",
    limitations: list[str] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "value": value,
        "status": status,
        "authority": authority,
        "confidence_class": confidence,
        "limitations": limitations or [],
        "warnings": warnings or [],
        "contract_version": PERFORMANCE_METRIC_CONTRACT_VERSION,
    }


def _load_run_matched_json(path: Path, *, run_id: str) -> dict[str, Any]:
    payload = read_json_optional(path)
    if str(payload.get("run_id") or "") != run_id:
        return {}
    return payload


def _phase20_baseline_metrics(*, run_id: str) -> dict[str, Any]:
    root = Path("reports") / "performance_baselines" / run_id
    payload = _load_run_matched_json(root / "performance_metrics.json", run_id=run_id)
    if not payload:
        return {}
    metrics = payload.get("metrics")
    if not isinstance(metrics, list):
        return {}
    return {str(row.get("metric_name") or row.get("metric_id") or ""): row for row in metrics if isinstance(row, dict)}


def _phase20_attribution_payload(path_name: str, *, run_id: str) -> Any:
    path = Path("reports") / "performance_attribution" / run_id / path_name
    if not path.exists():
        return None
    payload = read_json_optional(path)
    if isinstance(payload, dict) and str(payload.get("run_id") or "") not in {"", run_id}:
        return None
    return payload


def _missing_value() -> dict[str, str]:
    return {"value": "MISSING", "status": "NOT_AVAILABLE"}


def _status_value(value: Any, status: str = "AVAILABLE") -> dict[str, Any]:
    if value in (None, ""):
        return _missing_value()
    return {"value": value, "status": status}


def _sum_available_values(values: Any) -> float:
    total = 0.0
    for value in values:
        if isinstance(value, dict):
            if value.get("status") == "NOT_AVAILABLE":
                continue
            value = value.get("value")
        if value in (None, "", "MISSING", "NOT_AVAILABLE"):
            continue
        total += _float(value)
    return total


def _sum_observability_pnl_by_symbol(rows: list[dict[str, Any]]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for row in rows:
        symbol = str(row.get("symbol") or "")
        if not symbol:
            continue
        pnl = row.get("gross_realized_pnl")
        if isinstance(pnl, dict):
            pnl = pnl.get("value") if pnl.get("status") != "NOT_AVAILABLE" else None
        if pnl not in (None, "", "MISSING", "NOT_AVAILABLE"):
            totals[symbol] += _float(pnl)
    return dict(sorted(totals.items()))


def _field_status_from_observability(rows: list[dict[str, Any]], field: str) -> str:
    if not rows:
        return "NOT_RETAINED"
    statuses = {
        str((row.get(field) or {}).get("status") or "AVAILABLE") if isinstance(row.get(field), dict) else "AVAILABLE"
        for row in rows
    }
    if statuses == {"NOT_AVAILABLE"}:
        return "NOT_AVAILABLE"
    if "NOT_AVAILABLE" in statuses:
        return "PARTIAL"
    return "AVAILABLE"


def _load_performance_observability(*, run_dir: Path, run_id: str, completed_business_days: set[str]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": PERFORMANCE_OBSERVABILITY_SCHEMA_VERSION,
        "contract_version": PERFORMANCE_OBSERVABILITY_CONTRACT_VERSION,
        "status": "NOT_RETAINED",
        "position_campaigns": [],
        "fills": [],
        "realized_slices": [],
        "pm_decisions": [],
        "benchmark_snapshots": [],
        "read_issues": [],
    }
    loaders = (
        ("position_campaigns", "daily/*/positions/position_campaigns.json", "position_campaigns", "position_campaign_observability.v1"),
        ("fills", "daily/*/execution/fills.json", "fills", "runtime_fill_observability.v1"),
        ("realized_slices", "daily/*/execution/realized_slices.json", "realized_slices", "realized_slice_observability.v1"),
        ("pm_decisions", "daily/*/position_management/pm_decisions.json", "decisions", "pm_decision_snapshot.v1"),
        ("benchmark_snapshots", "daily/*/benchmark/benchmark_snapshot.json", None, "benchmark_snapshot_observability.v1"),
    )
    seen = False
    for target_key, pattern, body_key, expected_schema in loaders:
        for path in sorted(run_dir.glob(pattern)):
            business_date = path.parts[-3]
            if completed_business_days and business_date not in completed_business_days:
                continue
            try:
                payload = read_json(path)
            except Exception as exc:
                result["read_issues"].append(
                    {
                        "severity": "REVIEW_REQUIRED",
                        "reason": "OBSERVABILITY_EVIDENCE_JSON_READ_FAILED",
                        "path": str(path),
                        "error": str(exc),
                    }
                )
                continue
            if str(payload.get("run_id") or "") != run_id:
                result["read_issues"].append(
                    {
                        "severity": "REVIEW_REQUIRED",
                        "reason": "OBSERVABILITY_EVIDENCE_RUN_ID_MISMATCH",
                        "path": str(path),
                        "expected_run_id": run_id,
                        "actual_run_id": str(payload.get("run_id") or ""),
                    }
                )
                continue
            payload_business_date = str(payload.get("business_date") or "")
            if payload_business_date and payload_business_date != business_date:
                result["read_issues"].append(
                    {
                        "severity": "REVIEW_REQUIRED",
                        "reason": "OBSERVABILITY_EVIDENCE_BUSINESS_DATE_MISMATCH",
                        "path": str(path),
                        "path_business_date": business_date,
                        "payload_business_date": payload_business_date,
                    }
                )
                continue
            if str(payload.get("schema_version") or "") not in {"", expected_schema}:
                result["read_issues"].append(
                    {
                        "severity": "REVIEW_REQUIRED",
                        "reason": "OBSERVABILITY_EVIDENCE_SCHEMA_VERSION_UNKNOWN",
                        "path": str(path),
                        "expected_schema_version": expected_schema,
                        "actual_schema_version": str(payload.get("schema_version") or ""),
                    }
                )
                continue
            seen = True
            if body_key is None:
                result[target_key].append(payload)
            else:
                rows = payload.get(body_key)
                if isinstance(rows, list):
                    for row in rows:
                        if not isinstance(row, dict):
                            continue
                        copied = dict(row)
                        copied.setdefault("_snapshot_business_date", business_date)
                        result[target_key].append(copied)
    if seen:
        result["status"] = "AVAILABLE"
    result["position_campaign_snapshot_count"] = len(result["position_campaigns"])
    result["position_campaigns"] = _dedupe_position_campaign_snapshots(result["position_campaigns"])
    result["position_campaign_count"] = len(result["position_campaigns"])
    if result["read_issues"]:
        result["status"] = "REVIEW_REQUIRED"
    return result


def _dedupe_position_campaign_snapshots(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for row in rows:
        campaign_id = str(row.get("position_campaign_id") or "")
        if not campaign_id:
            continue
        current = selected.get(campaign_id)
        if current is None or _campaign_snapshot_rank(row) > _campaign_snapshot_rank(current):
            selected[campaign_id] = row
    return sorted(selected.values(), key=lambda row: (str(row.get("symbol") or ""), str(row.get("position_campaign_id") or "")))


def _observability_completeness_judgment(observability: dict[str, Any]) -> dict[str, Any]:
    read_issues = observability.get("read_issues") if isinstance(observability.get("read_issues"), list) else []
    status = str(observability.get("status") or "NOT_RETAINED")
    if read_issues:
        judgment = "REVIEW_REQUIRED"
    elif status == "AVAILABLE":
        judgment = "PASS"
    else:
        judgment = "NOT_RETAINED"
    return {
        "judgment": judgment,
        "status": status,
        "read_issue_count": len(read_issues),
        "position_campaign_count": observability.get("position_campaign_count", 0),
        "position_campaign_snapshot_count": observability.get("position_campaign_snapshot_count", 0),
        "runtime_judgment_impact": "NONE",
    }


def _performance_analysis_readiness_judgment(observability: dict[str, Any]) -> dict[str, Any]:
    read_issues = observability.get("read_issues") if isinstance(observability.get("read_issues"), list) else []
    campaigns = observability.get("position_campaigns") if isinstance(observability.get("position_campaigns"), list) else []
    fills = observability.get("fills") if isinstance(observability.get("fills"), list) else []
    realized_slices = observability.get("realized_slices") if isinstance(observability.get("realized_slices"), list) else []
    gaps = []
    if read_issues:
        gaps.append("observability_read_issues")
    if not campaigns:
        gaps.append("position_campaigns_missing")
    if not fills:
        gaps.append("fills_missing")
    if not realized_slices:
        gaps.append("realized_slices_missing_or_no_sell_executions")
    judgment = "REVIEW_REQUIRED" if read_issues else "READY_WITH_NON_BLOCKING_GAPS" if gaps else "READY"
    return {
        "judgment": judgment,
        "gaps": gaps,
        "benchmark_status": "MISSING_SOURCE_NOT_CONFIRMED",
        "net_realized_pnl_status": "NOT_AVAILABLE_FEES_TAX_MISSING",
        "runtime_judgment_impact": "NONE",
    }


def _campaign_snapshot_rank(row: dict[str, Any]) -> tuple[str, int, int]:
    status_rank = 1 if str(row.get("campaign_status") or "").upper() == "CLOSED" else 0
    return (
        str(row.get("_snapshot_business_date") or row.get("business_date") or row.get("opened_business_date") or ""),
        len(row.get("events") or []),
        status_rank,
    )


def _metric_has_available_value(row: dict[str, Any]) -> bool:
    value = row.get("value")
    return value not in (None, "", "MISSING", "NOT_AVAILABLE")


def _realized_pnl_reconciliation(current_realized: Any, slice_total: float, has_slices: bool) -> dict[str, Any]:
    if current_realized not in (None, "", "MISSING", "NOT_AVAILABLE") and has_slices:
        difference = _float(current_realized) - slice_total
        if abs(difference) < 0.0001:
            return {
                "status": "PASS",
                "metric_status": "DERIVABLE_EXACT",
                "authority": "FINAL_CURRENT_STATE_REALIZED_PNL_RECONCILED_TO_RUN_SCOPED_REALIZED_SLICES_GROSS",
                "confidence_class": "DERIVABLE_EXACT",
                "current_state_realized_pnl": _float(current_realized),
                "realized_slice_gross_pnl": slice_total,
                "difference": difference,
                "warnings": [],
                "limitations": ["Net realized PnL remains NOT_AVAILABLE when fees/tax are missing."],
            }
        return {
            "status": "REVIEW_REQUIRED",
            "metric_status": "REVIEW_REQUIRED",
            "authority": "REALIZED_PNL_RECONCILIATION_MISMATCH",
            "confidence_class": "UNKNOWN",
            "current_state_realized_pnl": _float(current_realized),
            "realized_slice_gross_pnl": slice_total,
            "difference": difference,
            "warnings": ["REALIZED_PNL_RECONCILIATION_MISMATCH"],
            "limitations": ["Do not choose one value silently when current state and realized slices disagree."],
        }
    if current_realized not in (None, "", "MISSING", "NOT_AVAILABLE"):
        return {
            "status": "CURRENT_STATE_ONLY",
            "metric_status": "DERIVABLE_PARTIAL",
            "authority": "FINAL_CURRENT_STATE_REALIZED_PNL",
            "confidence_class": "DERIVABLE_PARTIAL",
            "current_state_realized_pnl": _float(current_realized),
            "realized_slice_gross_pnl": "NOT_RETAINED",
            "difference": "NOT_AVAILABLE",
            "warnings": [],
            "limitations": ["Run-scoped realized slice evidence was not retained."],
        }
    if has_slices:
        return {
            "status": "REALIZED_SLICE_ONLY",
            "metric_status": "DERIVABLE_EXACT",
            "authority": "RUN_SCOPED_REALIZED_SLICES_GROSS",
            "confidence_class": "DERIVABLE_EXACT",
            "current_state_realized_pnl": "NOT_AVAILABLE",
            "realized_slice_gross_pnl": slice_total,
            "difference": "NOT_AVAILABLE",
            "warnings": [],
            "limitations": ["Final current state realized_pnl was not available for reconciliation."],
        }
    return {
        "status": "NOT_AVAILABLE",
        "metric_status": "NOT_AVAILABLE",
        "authority": "REALIZED_PNL_EVIDENCE_NOT_RETAINED",
        "confidence_class": "UNKNOWN",
        "current_state_realized_pnl": "NOT_AVAILABLE",
        "realized_slice_gross_pnl": "NOT_RETAINED",
        "difference": "NOT_AVAILABLE",
        "warnings": [],
        "limitations": ["Neither current state realized_pnl nor run-scoped realized slices were available."],
    }


def _summary_metric_from_baseline(metrics: dict[str, Any], name: str) -> dict[str, Any] | None:
    row = metrics.get(name)
    if not isinstance(row, dict):
        return None
    return _metric(
        row.get("value"),
        status=str(row.get("status") or "AVAILABLE"),
        authority=str(row.get("authority") or "phase20_baseline_metric"),
        confidence=str(row.get("confidence_class") or "DERIVABLE_EXACT"),
        limitations=[str(item) for item in row.get("limitations") or []],
        warnings=[str(item) for item in row.get("warnings") or []],
    )


def _build_performance_scope(
    *,
    run_id: str,
    performance: dict[str, Any],
    trading: dict[str, Any],
    current_positions: list[dict[str, Any]],
    observability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    observability = observability or {}
    baseline = _phase20_baseline_metrics(run_id=run_id)
    authority = (
        "PHASE20_BASELINE_ARTIFACT_RUN_MATCHED"
        if baseline
        else str(performance.get("performance_authority") or "RUNTIME_TEST_SUMMARY_DERIVED")
    )
    realized_slices = observability.get("realized_slices") if isinstance(observability.get("realized_slices"), list) else []
    realized_slice_total = _sum_available_values(row.get("gross_realized_pnl") for row in realized_slices if isinstance(row, dict))
    symbol_realized_pnl = _sum_observability_pnl_by_symbol(realized_slices)
    fills = observability.get("fills") if isinstance(observability.get("fills"), list) else []
    buy_execution_notional = _sum_available_values(
        row.get("gross_notional") for row in fills if isinstance(row, dict) and str(row.get("side") or "").upper() == "BUY"
    )
    sell_execution_notional = _sum_available_values(
        row.get("gross_notional") for row in fills if isinstance(row, dict) and str(row.get("side") or "").upper() == "SELL"
    )
    total_execution_notional = buy_execution_notional + sell_execution_notional
    realized_reconciliation = _realized_pnl_reconciliation(performance.get("realized_pnl"), realized_slice_total, bool(realized_slices))
    benchmark_snapshots = observability.get("benchmark_snapshots") if isinstance(observability.get("benchmark_snapshots"), list) else []
    benchmark_statuses = sorted({str(row.get("status") or "MISSING") for row in benchmark_snapshots if isinstance(row, dict)})
    metrics: dict[str, Any] = {
        "Initial Equity": _metric(performance.get("initial_equity"), status="DERIVABLE_EXACT" if performance.get("initial_equity") is not None else "NOT_AVAILABLE", authority=authority),
        "Final Equity": _metric(performance.get("final_equity"), status="DERIVABLE_EXACT" if performance.get("final_equity") is not None else "NOT_AVAILABLE", authority=authority),
        "Total Return": _metric(performance.get("total_return_amount"), status="DERIVABLE_EXACT" if performance.get("total_return_amount") is not None else "NOT_AVAILABLE", authority=authority),
        "Return Rate": _metric(performance.get("total_return_percent"), status="DERIVABLE_EXACT" if performance.get("total_return_percent") is not None else "NOT_AVAILABLE", authority=authority),
        "Realized PnL": _metric(
            performance.get("realized_pnl") if performance.get("realized_pnl") is not None else realized_slice_total if realized_slices else "NOT_AVAILABLE",
            status=realized_reconciliation["metric_status"],
            authority=realized_reconciliation["authority"],
            confidence=realized_reconciliation["confidence_class"],
            warnings=realized_reconciliation["warnings"],
            limitations=realized_reconciliation["limitations"],
        ),
        "Realized Slice Gross PnL": _metric(
            realized_slice_total if realized_slices else "MISSING",
            status="DERIVABLE_EXACT" if realized_slices else "MISSING",
            authority="RUN_SCOPED_REALIZED_SLICE_OBSERVABILITY" if realized_slices else "RUN_SCOPED_REALIZED_SLICE_OBSERVABILITY_NOT_RETAINED",
            confidence="DERIVABLE_EXACT" if realized_slices else "UNKNOWN",
            limitations=[] if realized_slices else ["Only Phase20-J and later runs retain realized slice evidence."],
        ),
        "Unrealized PnL": _metric(performance.get("unrealized_pnl"), status="DERIVABLE_EXACT" if performance.get("unrealized_pnl") is not None else "NOT_AVAILABLE", authority=authority),
        "BUY Count": _metric(trading.get("execution_distribution", {}).get("BUY", 0), status="DERIVABLE_EXACT", authority="RUN_SCOPED_EXECUTION_EVIDENCE"),
        "SELL Count": _metric(trading.get("execution_distribution", {}).get("SELL", 0), status="DERIVABLE_EXACT", authority="RUN_SCOPED_EXECUTION_EVIDENCE"),
        "Position Count": _metric(
            performance.get("position_count", len(current_positions)),
            status="DERIVABLE_EXACT" if performance.get("position_count", len(current_positions)) is not None else "NOT_AVAILABLE",
            authority=authority,
        ),
    }
    for name in (
        "Daily Equity Curve",
        "Maximum Drawdown",
        "Gross Exposure",
        "Cash Ratio",
        "Cash Utilization",
        "Turnover",
        "Single-name Concentration",
    ):
        baseline_metric = _summary_metric_from_baseline(baseline, name)
        metrics[name] = baseline_metric or _metric(
            "NOT_AVAILABLE",
            status="NOT_AVAILABLE",
            authority="RUN_EVIDENCE_NOT_SUFFICIENT_FOR_SCOPE_METRIC",
            confidence="UNKNOWN",
            limitations=["Metric requires retained daily valuation or Phase20 baseline artifact for this run."],
        )
    metrics["Execution Notional"] = _summary_metric_from_baseline(baseline, "Execution Notional") or _metric(
        {
            "buy_execution_notional": buy_execution_notional,
            "sell_execution_notional": sell_execution_notional,
            "total_execution_notional": total_execution_notional,
        }
        if fills
        else "NOT_AVAILABLE",
        status="DERIVABLE_EXACT" if fills else "NOT_AVAILABLE",
        authority="RUN_SCOPED_FILL_OBSERVABILITY" if fills else "RUN_SCOPED_FILL_OBSERVABILITY_NOT_RETAINED",
        confidence="DERIVABLE_EXACT" if fills else "UNKNOWN",
        limitations=[] if fills else ["Only Phase20-J and later runs retain fill observability."],
    )
    for name in ("Benchmark", "Sector", "lot-level realized PnL"):
        metrics[name] = _metric(
            "MISSING",
            status="MISSING",
            authority="NOT_PRESENT_IN_RUNTIME_TEST_RUN_EVIDENCE",
            confidence="UNKNOWN",
            limitations=["No inference or external lookup is allowed."],
        )
    drawdown = metrics["Maximum Drawdown"]["value"] if isinstance(metrics.get("Maximum Drawdown"), dict) else "NOT_AVAILABLE"
    daily_curve = metrics["Daily Equity Curve"]["value"] if isinstance(metrics.get("Daily Equity Curve"), dict) else []
    peak_date = bottom_date = recovery = "NOT_AVAILABLE"
    if isinstance(daily_curve, list) and daily_curve:
        peak_date = str((daily_curve[0] or {}).get("peak_date") or "")
        bottom_row = min(daily_curve, key=lambda row: _float((row or {}).get("drawdown_amount")), default={})
        bottom_date = str((bottom_row or {}).get("business_date") or "")
        recovery = "UNRECOVERED" if _float((daily_curve[-1] or {}).get("drawdown_amount")) < 0 else "RECOVERED"
    return {
        "operator_question": "How did this run perform?",
        "status": "AVAILABLE_WITH_GAPS" if baseline else "DERIVABLE_PARTIAL",
        "authority": authority,
        "metrics": metrics,
        "daily_equity_curve_summary": {
            "points": len(daily_curve) if isinstance(daily_curve, list) else 0,
            "first": daily_curve[0] if isinstance(daily_curve, list) and daily_curve else None,
            "last": daily_curve[-1] if isinstance(daily_curve, list) and daily_curve else None,
        },
        "drawdown": {
            "maximum_drawdown": drawdown,
            "peak_date": peak_date,
            "bottom_date": bottom_date,
            "recovery": recovery,
        },
        "realized_slice_observability": {
            "status": "AVAILABLE" if realized_slices else "NOT_RETAINED",
            "slice_count": len(realized_slices),
            "gross_realized_pnl": realized_slice_total if realized_slices else "MISSING",
            "symbol_level_realized_pnl": symbol_realized_pnl,
            "reconciliation": realized_reconciliation,
            "fees_status": _field_status_from_observability(realized_slices, "fees"),
            "tax_status": _field_status_from_observability(realized_slices, "tax"),
        },
        "execution_notional": {
            "status": "DERIVABLE_EXACT" if fills else "NOT_RETAINED",
            "buy_execution_notional": buy_execution_notional if fills else "MISSING",
            "sell_execution_notional": sell_execution_notional if fills else "MISSING",
            "total_execution_notional": total_execution_notional if fills else "MISSING",
        },
        "benchmark_observability": {
            "status": benchmark_statuses[-1] if benchmark_statuses else "MISSING",
            "snapshot_count": len(benchmark_snapshots),
            "source": "NOT_CONFIRMED",
            "excess_return_status": "MISSING",
        },
    }


def _build_positions_scope(
    *,
    run_id: str,
    plans: dict[str, list[dict[str, Any]]],
    current_positions: list[dict[str, Any]],
    trade_attribution: list[dict[str, Any]],
    observability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    observability = observability or {}
    observed_campaigns = observability.get("position_campaigns") if isinstance(observability.get("position_campaigns"), list) else []
    if observed_campaigns:
        rows = [_position_scope_row_from_campaign(campaign) for campaign in observed_campaigns if isinstance(campaign, dict)]
        return {
            "operator_question": "What happened to each position campaign?",
            "status": "AVAILABLE_WITH_PHASE20_J_OBSERVABILITY",
            "lot_level_claim": "PROHIBITED_STABLE_LOT_ID_NOT_AVAILABLE",
            "position_campaign_identity": "POSITION_CAMPAIGN_ID_AVAILABLE",
            "campaign_count": len(rows),
            "daily_snapshot_count": observability.get("position_campaign_snapshot_count", len(rows)),
            "positions": sorted(rows, key=lambda row: (str(row.get("symbol") or ""), str(row.get("position_campaign_id") or ""))),
        }
    buy_rows = _phase20_attribution_payload("buy_attribution.json", run_id=run_id)
    diagnosis = _load_run_matched_json(Path("reports") / "performance_diagnosis" / run_id / "performance_diagnosis.json", run_id=run_id)
    diagnosis_rows = ((diagnosis.get("buy_performance_diagnosis") or {}).get("rows") or []) if diagnosis else []
    by_symbol: dict[str, dict[str, Any]] = {}
    for item in plans.get("buy", []):
        symbol = str(item.get("symbol") or "")
        by_symbol.setdefault(symbol, {}).update(
            {
                "symbol": symbol,
                "buy_date": item.get("_plan_date") or item.get("business_date") or "",
                "buy_price": item.get("price") or item.get("limit_price") or "MISSING",
                "buy_quantity": item.get("quantity") or "MISSING",
                "initial_capital_allocated": (_float(item.get("quantity")) * _float(item.get("price") or item.get("limit_price"))) if item.get("price") or item.get("limit_price") else "MISSING",
                "evidence_status": "DERIVABLE_PARTIAL",
                "limitations": ["Stable lot ID is not available; row is a symbol-level position campaign."],
            }
        )
    if isinstance(buy_rows, list):
        for row in buy_rows:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol") or "")
            by_symbol.setdefault(symbol, {"symbol": symbol}).update(
                {
                    "buy_date": row.get("business_date") or row.get("buy_date") or by_symbol.get(symbol, {}).get("buy_date", ""),
                    "buy_price": row.get("buy_price", by_symbol.get(symbol, {}).get("buy_price", "MISSING")),
                    "buy_quantity": row.get("buy_quantity", row.get("quantity", by_symbol.get(symbol, {}).get("buy_quantity", "MISSING"))),
                    "initial_capital_allocated": row.get("capital_allocated", by_symbol.get(symbol, {}).get("initial_capital_allocated", "MISSING")),
                    "opportunity_rank": row.get("opportunity_rank", "MISSING"),
                    "candidate_score": row.get("candidate_score", "MISSING"),
                    "opportunity_score": row.get("opportunity_score", "MISSING"),
                    "confidence": row.get("confidence", "MISSING"),
                    "evidence_status": row.get("evidence_status", "DERIVABLE_PARTIAL"),
                }
            )
    for row in diagnosis_rows:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol") or "")
        by_symbol.setdefault(symbol, {"symbol": symbol}).update(
            {
                "opportunity_rank": row.get("opportunity_rank", "MISSING"),
                "candidate_score": row.get("candidate_score", "MISSING"),
                "opportunity_score": row.get("opportunity_score", "MISSING"),
                "confidence": row.get("confidence", "MISSING"),
                "open_closed": row.get("status_open_closed", "MISSING"),
                "final_last_observed_return": row.get("final_return", "MISSING"),
                "mfe": row.get("maximum_favorable_excursion", "NOT_AVAILABLE"),
                "mae": row.get("maximum_adverse_excursion", "NOT_AVAILABLE"),
                "post_hoc_classification": "POST_HOC_ATTRIBUTION_ONLY",
                "evidence_status": row.get("evidence_status", "DERIVABLE_PARTIAL"),
                "limitations": row.get("limitations", []),
            }
        )
    for pos in current_positions:
        symbol = str(pos.get("symbol") or "")
        by_symbol.setdefault(symbol, {"symbol": symbol}).update(
            {
                "open_closed": "OPEN",
                "final_quantity": pos.get("quantity"),
                "average_price": pos.get("average_price"),
                "final_last_observed_price": pos.get("current_price"),
                "open_unrealized_pnl": pos.get("unrealized_pnl"),
            }
        )
    for row in trade_attribution:
        symbol = str(row.get("symbol") or "")
        if symbol:
            by_symbol.setdefault(symbol, {"symbol": symbol}).setdefault("available_realized_pnl", 0.0)
            if row.get("realized_pnl") is not None:
                by_symbol[symbol]["available_realized_pnl"] = _float(by_symbol[symbol]["available_realized_pnl"]) + _float(row.get("realized_pnl"))
    for campaign in observed_campaigns:
        if not isinstance(campaign, dict):
            continue
        symbol = str(campaign.get("symbol") or "")
        if not symbol:
            continue
        by_symbol.setdefault(symbol, {"symbol": symbol}).update(
            {
                "position_campaign_id": campaign.get("position_campaign_id", "MISSING"),
                "open_closed": campaign.get("campaign_status", "MISSING"),
                "final_quantity": campaign.get("current_quantity", "MISSING"),
                "available_realized_pnl": campaign.get("realized_pnl", "MISSING"),
                "open_unrealized_pnl": campaign.get("unrealized_pnl", "MISSING"),
                "buy_notional": campaign.get("buy_notional", "MISSING"),
                "sell_notional": campaign.get("sell_notional", "MISSING"),
                "total_campaign_pnl": campaign.get("total_campaign_pnl", "MISSING"),
                "evidence_status": "AVAILABLE",
                "limitations": campaign.get("limitations", []),
            }
        )
    rows = []
    for row in by_symbol.values():
        rows.append(
            {
                "symbol": row.get("symbol", ""),
                "position_campaign_id": row.get("position_campaign_id", "MISSING"),
                "buy_date": row.get("buy_date", "MISSING"),
                "buy_price": row.get("buy_price", "MISSING"),
                "buy_quantity": row.get("buy_quantity", "MISSING"),
                "initial_capital_allocated": row.get("initial_capital_allocated", "MISSING"),
                "opportunity_rank": row.get("opportunity_rank", "MISSING"),
                "candidate_score": row.get("candidate_score", "MISSING"),
                "opportunity_score": row.get("opportunity_score", "MISSING"),
                "confidence": row.get("confidence", "MISSING"),
                "open_closed": row.get("open_closed", "MISSING"),
                "final_quantity": row.get("final_quantity", "MISSING"),
                "average_price": row.get("average_price", "MISSING"),
                "final_last_observed_price": row.get("final_last_observed_price", "MISSING"),
                "open_unrealized_pnl": row.get("open_unrealized_pnl", "MISSING"),
                "available_realized_pnl": row.get("available_realized_pnl", "MISSING"),
                "buy_notional": row.get("buy_notional", "MISSING"),
                "sell_notional": row.get("sell_notional", "MISSING"),
                "total_campaign_pnl": row.get("total_campaign_pnl", "MISSING"),
                "final_last_observed_return": row.get("final_last_observed_return", "MISSING"),
                "mfe": row.get("mfe", "NOT_AVAILABLE"),
                "mae": row.get("mae", "NOT_AVAILABLE"),
                "post_hoc_classification": row.get("post_hoc_classification", "POST_HOC_ATTRIBUTION_ONLY"),
                "evidence_status": row.get("evidence_status", "DERIVABLE_PARTIAL"),
                "limitations": row.get("limitations", ["Stable lot ID is not available; symbol-level campaign only."]),
            }
        )
    return {
        "operator_question": "What happened to each symbol-level position campaign?",
        "status": "DERIVABLE_PARTIAL" if rows else "MISSING",
        "lot_level_claim": "PROHIBITED_STABLE_LOT_ID_NOT_AVAILABLE",
        "position_campaign_identity": "POSITION_CAMPAIGN_ID_AVAILABLE" if observed_campaigns else "NOT_RETAINED_FOR_OLD_RUN",
        "positions": sorted(rows, key=lambda row: str(row.get("symbol") or "")),
    }


def _position_scope_row_from_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": campaign.get("symbol", ""),
        "position_campaign_id": campaign.get("position_campaign_id", "MISSING"),
        "buy_date": campaign.get("opened_business_date", "MISSING"),
        "closed_business_date": campaign.get("closed_business_date", ""),
        "buy_price": "MISSING",
        "buy_quantity": "MISSING",
        "initial_capital_allocated": campaign.get("buy_notional", "MISSING"),
        "opportunity_rank": "MISSING",
        "candidate_score": "MISSING",
        "opportunity_score": "MISSING",
        "confidence": "MISSING",
        "open_closed": campaign.get("campaign_status", "MISSING"),
        "campaign_status": campaign.get("campaign_status", "MISSING"),
        "final_quantity": campaign.get("current_quantity", "MISSING"),
        "current_quantity": campaign.get("current_quantity", "MISSING"),
        "average_price": campaign.get("average_cost", "MISSING"),
        "final_last_observed_price": "MISSING",
        "open_unrealized_pnl": campaign.get("unrealized_pnl", "MISSING"),
        "unrealized_pnl": campaign.get("unrealized_pnl", "MISSING"),
        "available_realized_pnl": campaign.get("realized_pnl", "MISSING"),
        "realized_pnl": campaign.get("realized_pnl", "MISSING"),
        "buy_notional": campaign.get("buy_notional", "MISSING"),
        "sell_notional": campaign.get("sell_notional", "MISSING"),
        "total_campaign_pnl": campaign.get("total_campaign_pnl", "MISSING"),
        "final_last_observed_return": "MISSING",
        "mfe": "NOT_AVAILABLE",
        "mae": "NOT_AVAILABLE",
        "post_hoc_classification": "POST_HOC_ATTRIBUTION_ONLY",
        "evidence_status": "AVAILABLE",
        "event_count": len(campaign.get("events") or []),
        "limitations": campaign.get("limitations", ["Stable lot ID is not available; realized_slice is the formal realized PnL unit."]),
    }


def _build_lifecycle_scope(
    *,
    run_id: str,
    plans: dict[str, list[dict[str, Any]]],
    pm: dict[str, Any],
    trade_attribution: list[dict[str, Any]],
    current_positions: list[dict[str, Any]],
    observability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    observability = observability or {}
    observed_campaigns = observability.get("position_campaigns") if isinstance(observability.get("position_campaigns"), list) else []
    if observed_campaigns:
        return {
            "operator_question": "How did BUY to HOLD/ADD/REDUCE/EXIT evolve?",
            "status": "AVAILABLE_WITH_PHASE20_J_OBSERVABILITY",
            "authority": "RUN_SCOPED_POSITION_CAMPAIGN_OBSERVABILITY",
            "post_hoc_policy": "POST_HOC_ATTRIBUTION_ONLY",
            "campaign_count": len(observed_campaigns),
            "daily_snapshot_count": observability.get("position_campaign_snapshot_count", len(observed_campaigns)),
            "position_lifecycles": observed_campaigns,
            "pm_decision_snapshots": observability.get("pm_decisions", []),
            "fills": observability.get("fills", []),
            "realized_slices": observability.get("realized_slices", []),
        }
    phase20_lifecycle = _phase20_attribution_payload("trade_lifecycle.json", run_id=run_id)
    if isinstance(phase20_lifecycle, list):
        return {
            "operator_question": "How did BUY to HOLD/ADD/REDUCE/EXIT evolve?",
            "status": "AVAILABLE_WITH_DERIVABLE_GAPS",
            "authority": "PHASE20_ATTRIBUTION_ARTIFACT_RUN_MATCHED",
            "post_hoc_policy": "POST_HOC_ATTRIBUTION_ONLY",
            "position_lifecycles": phase20_lifecycle,
        }
    symbols = sorted(
        {
            *(str(item.get("symbol") or "") for item in plans.get("buy", [])),
            *(str(row.get("symbol") or "") for row in trade_attribution),
            *(str(row.get("symbol") or "") for row in current_positions),
        }
        - {""}
    )
    records = []
    for symbol in symbols:
        events: list[dict[str, Any]] = []
        for item in plans.get("buy", []):
            if str(item.get("symbol") or "") == symbol:
                events.append(
                    {
                        "stage": "BUY decision / execution",
                        "business_date": item.get("_plan_date") or item.get("business_date") or "",
                        "decision_type": "BUY",
                        "decision_reason": item.get("reason") or "MISSING",
                        "quantity_before": "MISSING",
                        "quantity_after": item.get("quantity", "MISSING"),
                        "price": item.get("price") or item.get("limit_price") or "MISSING",
                        "pnl": "NOT_AVAILABLE",
                        "evidence_status": "DERIVABLE_PARTIAL",
                        "evidence_type": "decision-time evidence",
                    }
                )
        for row in trade_attribution:
            if str(row.get("symbol") or "") == symbol:
                events.append(
                    {
                        "stage": row.get("source_decision") or "REDUCE/EXIT",
                        "business_date": row.get("business_date") or "",
                        "decision_type": row.get("source_decision") or "SELL",
                        "decision_reason": row.get("pm_reason") or "MISSING",
                        "quantity_before": "MISSING",
                        "quantity_after": row.get("remaining_quantity_after_trade", "MISSING"),
                        "price": row.get("price", "MISSING"),
                        "pnl": row.get("realized_pnl", "MISSING"),
                        "post_hoc_return": "NOT_AVAILABLE",
                        "mfe": "NOT_AVAILABLE",
                        "mae": "NOT_AVAILABLE",
                        "post_hoc_classification": "POST_HOC_ATTRIBUTION_ONLY",
                        "evidence_status": row.get("pnl_traceability", "DERIVABLE_PARTIAL"),
                        "evidence_type": "execution evidence",
                    }
                )
        final_pos = next((row for row in current_positions if str(row.get("symbol") or "") == symbol), {})
        events.append(
            {
                "stage": "Final Position",
                "business_date": final_pos.get("valuation_as_of") or "",
                "decision_type": "FINAL_POSITION",
                "decision_reason": "end-of-day valuation",
                "quantity_before": "MISSING",
                "quantity_after": final_pos.get("quantity", 0),
                "price": final_pos.get("current_price", "MISSING"),
                "pnl": final_pos.get("unrealized_pnl", "MISSING"),
                "evidence_status": "DERIVABLE_PARTIAL" if final_pos else "MISSING",
                "evidence_type": "end-of-day valuation",
            }
        )
        records.append({"symbol": symbol, "status": "DERIVABLE_PARTIAL", "events": events})
    if not records and pm.get("decision_count", 0):
        records.append({"symbol": "MISSING", "status": "MISSING", "events": [], "limitations": ["PM decision body was not retained in summary payload."]})
    return {
        "operator_question": "How did BUY to HOLD/ADD/REDUCE/EXIT evolve?",
        "status": "DERIVABLE_PARTIAL" if records else "MISSING",
        "authority": "RUN_SCOPED_EVIDENCE_WITH_COMPLETED_BUSINESS_DAY_FILTER",
        "post_hoc_policy": "POST_HOC_ATTRIBUTION_ONLY",
        "position_lifecycles": records,
    }


def _build_summarize_scope_sections(
    *,
    run_id: str,
    run_summary: dict[str, Any],
    external_effects: dict[str, Any],
    performance: dict[str, Any],
    pm: dict[str, Any],
    trading: dict[str, Any],
    reduce_exit: dict[str, Any],
    trade_attribution: list[dict[str, Any]],
    current_positions: list[dict[str, Any]],
    lifecycle: dict[str, Any],
    findings: list[dict[str, Any]],
    plans: dict[str, list[dict[str, Any]]],
    executions: list[dict[str, Any]],
    observability: dict[str, Any],
) -> dict[str, Any]:
    overview = {
        "operator_question": "What happened in this run overall?",
        "run_identity": {
            "run_id": run_id,
            "profile_id": run_summary.get("profile_id"),
            "business_dates": run_summary.get("completed_business_days", []),
            "runtime_state_authority": run_summary.get("runtime_state_authority"),
        },
        "runtime_judgment": run_summary.get("final_judgment"),
        "external_effect_judgment": "PASS" if external_effects.get("historical_external_effects_disabled") else "REVIEW_REQUIRED",
        "initial_equity": performance.get("initial_equity"),
        "final_equity": performance.get("final_equity"),
        "total_return": performance.get("total_return_amount"),
        "return_rate": performance.get("total_return_percent"),
        "buy_count": trading.get("execution_distribution", {}).get("BUY", 0),
        "sell_count": trading.get("execution_distribution", {}).get("SELL", 0),
        "pm_counts": {
            "HOLD": pm.get("hold_count", 0),
            "ADD": pm.get("add_count", 0),
            "REDUCE": pm.get("reduce_count", 0),
            "EXIT": pm.get("exit_count", 0),
        },
        "lifecycle_consistency": lifecycle,
        "review_block_summary": findings,
        "current_positions_summary": {"count": len(current_positions), "symbols": [row.get("symbol") for row in current_positions]},
        "operator_judgment": "REVIEW_REQUIRED" if findings else "PASS",
    }
    return {
        "overview": overview,
        "performance": _build_performance_scope(run_id=run_id, performance=performance, trading=trading, current_positions=current_positions, observability=observability),
        "positions": _build_positions_scope(run_id=run_id, plans=plans, current_positions=current_positions, trade_attribution=trade_attribution, observability=observability),
        "lifecycle": _build_lifecycle_scope(run_id=run_id, plans=plans, pm=pm, trade_attribution=trade_attribution, current_positions=current_positions, observability=observability),
    }


def _build_strategy_summary_scope(
    *,
    run_id: str,
    profile_id: str,
    runtime_root: Path,
    run_dir: Path,
    run_summary: dict[str, Any],
) -> dict[str, Any]:
    business_dates = [str(day) for day in (run_summary.get("completed_business_days") or []) if str(day)]
    business_date = business_dates[-1] if business_dates else str(run_summary.get("date_to") or "")
    if not business_date:
        return {
            "schema_version": "strategy_decision_trace.v1",
            "status": "INCOMPLETE_ATTRIBUTION",
            "reason": "business_date_unavailable_from_run_evidence",
            "runtime_behavior_changed": False,
            "runtime_switch_performed": False,
        }
    trace = build_strategy_decision_trace(
        business_date=business_date,
        profile=profile_id,
        run_id=run_id,
        artifact_paths=_strategy_artifact_paths(runtime_root=runtime_root, run_dir=run_dir, business_date=business_date),
        legacy_context={
            "max_positions": 5,
            "target_investment_ratio": 0.85,
            "cash_buffer": 0.15,
        },
        outcome_context={
            "runtime_result_available": False,
            "execution_result_available": False,
            "outcome_attribution_available": False,
            "strategy_input_allowed": False,
            "learning_input_allowed": False,
        },
    )
    return {
        "schema_version": trace["schema_version"],
        "status": trace["overall_status"],
        "business_date": trace["business_date"],
        "trace": trace,
        "overview": summarize_strategy_trace(trace, scope="overview"),
        "positions": summarize_strategy_trace(trace, scope="positions"),
        "lineage": summarize_strategy_trace(trace, scope="lineage"),
        "shadow": summarize_strategy_trace(trace, scope="shadow"),
        "readiness": summarize_strategy_trace(trace, scope="readiness"),
        "runtime_behavior_changed": False,
        "runtime_switch_performed": False,
    }


def _strategy_artifact_paths(*, runtime_root: Path, run_dir: Path | None = None, business_date: str) -> dict[str, Path]:
    root = run_dir / "daily" / business_date / "strategy" if run_dir is not None else runtime_root / "strategy_artifacts"
    names = {
        "market_context": "market_context.json",
        "corporate_event": "corporate_event.json",
        "portfolio_policy": "portfolio_policy.json",
        "dynamic_position_count": "dynamic_position_count.json",
        "dynamic_cash_exposure": "dynamic_cash_exposure.json",
        "portfolio_construction": "portfolio_construction.json",
        "position_sizing": "position_sizing.json",
        "position_management": "position_management.json",
        "runtime_planning": "runtime_planning.json",
    }
    if run_dir is not None:
        return {kind: root / filename for kind, filename in names.items()}
    return {kind: root / kind / business_date / filename for kind, filename in names.items()}


def _latest_strategy_trace_path(*, run_dir: Path) -> str:
    paths = sorted(run_dir.glob("daily/*/strategy/strategy_decision_trace.json"))
    return str(paths[-1]) if paths else ""


def _format_runtime_test_summary(payload: dict[str, Any]) -> str:
    scope = str(payload.get("scope") or "full")
    if scope in {"strategy", "strategy-trace", "strategy-attribution", "strategy-readiness", "strategy-shadow"}:
        strategy_scope = payload.get("strategy_scope") or {}
        trace = strategy_scope.get("trace") or {}
        portfolio = trace.get("portfolio_attribution") or {}
        positions = trace.get("per_symbol_attribution") or []
        lines = [
            "Strategy Observability Summary",
            f"- run_id: {payload['run_id']}",
            f"- status: {strategy_scope.get('status')}",
            f"- business_date: {strategy_scope.get('business_date')}",
            f"- market: {portfolio.get('market_regime')} trend={portfolio.get('market_trend')} breadth={portfolio.get('breadth')} volatility={portfolio.get('volatility')}",
            f"- position_count: {portfolio.get('target_position_count')} / members={portfolio.get('target_member_count')}",
            f"- cash_exposure: cash={portfolio.get('target_cash_ratio')} exposure={portfolio.get('target_gross_exposure')}",
            f"- pm_actions: HOLD={portfolio.get('hold_count')} ADD={portfolio.get('add_count')} REDUCE={portfolio.get('reduce_count')} EXIT={portfolio.get('exit_count')} UNRESOLVED={portfolio.get('unresolved_count')}",
            f"- positions: {len(positions)}",
            f"- blocking_reasons: {trace.get('blocking_reasons') or []}",
            f"- review_reasons: {trace.get('review_reasons') or []}",
            f"- runtime_behavior_changed: {strategy_scope.get('runtime_behavior_changed')}",
            f"- runtime_switch_performed: {strategy_scope.get('runtime_switch_performed')}",
        ]
        return "\n".join(lines)
    if scope == "overview":
        overview = payload.get("overview") or {}
        return "\n".join(
            [
                "Run Overview",
                f"- run_id: {payload['run_id']}",
                f"- runtime_judgment: {payload.get('runtime_judgment')}",
                f"- business_dates: {overview.get('run_identity', {}).get('business_dates', [])}",
                f"- equity: {overview.get('initial_equity')} -> {overview.get('final_equity')} / return: {overview.get('total_return')} ({overview.get('return_rate')}%)",
                f"- executions: BUY={overview.get('buy_count')} SELL={overview.get('sell_count')}",
                f"- pm_counts: {overview.get('pm_counts')}",
                f"- lifecycle_consistency: {(overview.get('lifecycle_consistency') or {}).get('status')}",
                f"- current_positions: {overview.get('current_positions_summary')}",
                f"- findings: {len(overview.get('review_block_summary') or [])}",
            ]
        )
    if scope == "performance":
        performance_scope = payload.get("performance_scope") or {}
        metrics = performance_scope.get("metrics") or {}
        return "\n".join(
            [
                "Performance Summary",
                f"- run_id: {payload['run_id']}",
                f"- status: {performance_scope.get('status')} / authority: {performance_scope.get('authority')}",
                f"- initial_equity: {(metrics.get('Initial Equity') or {}).get('value')}",
                f"- final_equity: {(metrics.get('Final Equity') or {}).get('value')}",
                f"- total_return: {(metrics.get('Total Return') or {}).get('value')}",
                f"- return_rate: {(metrics.get('Return Rate') or {}).get('value')}",
                f"- maximum_drawdown: {(metrics.get('Maximum Drawdown') or {}).get('value')}",
                f"- turnover: {(metrics.get('Turnover') or {}).get('value')}",
                f"- cash_utilization: {(metrics.get('Cash Utilization') or {}).get('value')}",
                f"- execution_notional: {(metrics.get('Execution Notional') or {}).get('value')}",
                f"- realized_slice_gross_pnl: {(metrics.get('Realized Slice Gross PnL') or {}).get('value')}",
                f"- metric_warnings: {_metric_warning_names(metrics)}",
            ]
        )
    if scope == "positions":
        positions_scope = payload.get("positions_scope") or {}
        rows = positions_scope.get("positions") or []
        lines = [
            "Position Campaign Summary",
            f"- run_id: {payload['run_id']}",
            f"- status: {positions_scope.get('status')}",
            f"- lot_level_claim: {positions_scope.get('lot_level_claim')}",
            f"- position_campaigns: {positions_scope.get('campaign_count', len(rows))}",
        ]
        for row in rows[:20]:
            lines.append(
                f"- {row.get('symbol')} / {row.get('position_campaign_id')}: status={row.get('campaign_status', row.get('open_closed'))} qty={row.get('current_quantity', row.get('final_quantity'))} realized={row.get('realized_pnl', row.get('available_realized_pnl'))} unrealized={row.get('unrealized_pnl', row.get('open_unrealized_pnl'))} total={row.get('total_campaign_pnl')}"
            )
        return "\n".join(lines)
    if scope == "lifecycle":
        lifecycle_scope = payload.get("lifecycle_scope") or {}
        rows = lifecycle_scope.get("position_lifecycles") or []
        lines = [
            "Position Lifecycle Summary",
            f"- run_id: {payload['run_id']}",
            f"- status: {lifecycle_scope.get('status')}",
            f"- post_hoc_policy: {lifecycle_scope.get('post_hoc_policy')}",
            f"- position_campaigns: {lifecycle_scope.get('campaign_count', len(rows))}",
        ]
        for row in rows[:10]:
            lines.append(
                f"- {row.get('symbol')} / {row.get('position_campaign_id')}: status={row.get('campaign_status', row.get('status'))} events={len(row.get('events') or [])} opened={row.get('opened_business_date', 'MISSING')} closed={row.get('closed_business_date', '')} realized={row.get('realized_pnl', 'MISSING')} unrealized={row.get('unrealized_pnl', 'MISSING')} total={row.get('total_campaign_pnl', 'MISSING')}"
            )
        return "\n".join(lines)
    run = payload["run"]
    performance = payload["performance"]
    pm = payload["pm_decisions"]
    trading = payload["trading"]
    reduce_exit = payload["reduce_exit"]
    lifecycle = payload["lifecycle_consistency"]
    findings = payload["findings"]
    lines = [
        "Run Summary",
        f"- run_id: {payload['run_id']}",
        f"- status: {run.get('status')} / final_judgment: {run.get('final_judgment')}",
        f"- business_days: {run.get('business_day_count')} ({run.get('date_from')} to {run.get('date_to')})",
        f"- runtime_state_authority: {run.get('runtime_state_authority')}",
        "",
        "External Effect Summary",
        f"- historical_external_effects_disabled: {payload['external_effects'].get('historical_external_effects_disabled')}",
        "",
        "Performance Summary",
        f"- final_equity: {performance.get('final_equity')} / return: {performance.get('total_return_amount')} ({performance.get('total_return_percent')}%)",
        f"- realized_pnl: {performance.get('realized_pnl')} / unrealized_pnl: {performance.get('unrealized_pnl')}",
        "",
        "PM Decision Summary",
        f"- decisions: {pm.get('decision_count')} {pm.get('decision_distribution')}",
        "",
        "BUY / SELL Summary",
        f"- buy_plan_count: {trading.get('buy_plan_count')} / sell_plan_count: {trading.get('sell_plan_count')}",
        f"- submitted: {trading.get('submitted_order_distribution')} / executions: {trading.get('execution_distribution')}",
        "",
        "REDUCE / EXIT Summary",
        f"- source_decisions: {reduce_exit.get('sell_plan_source_decision_distribution')}",
        "",
        "Trade Attribution",
        f"- sell_trades: {len(payload['trade_attribution'])}",
        "",
        "Current Positions",
        f"- positions: {len(payload['current_positions'])}",
        "",
        "Lifecycle Consistency",
        f"- status: {lifecycle.get('status')} checks={lifecycle.get('checks')}",
        f"- PM REDUCE Lifecycle: decisions={lifecycle.get('pm_reduce_count')} executable={lifecycle.get('executable_reduce_sell_plan_count')} non_executable={lifecycle.get('non_executable_reduce_terminal_count')} unresolved={lifecycle.get('unresolved_reduce_count')} conflicting={lifecycle.get('conflicting_reduce_count')}",
        "",
        "Review / Block Summary",
        f"- findings: {len(findings)} {[finding.get('reason') for finding in findings]}",
        "",
        "Operator Judgment",
        f"- runtime_judgment: {payload['runtime_judgment']}",
        f"- performance_judgment: {payload['performance_judgment']}",
        f"- strategy_judgment: {payload['strategy_judgment']}",
    ]
    if payload.get("evidence_path"):
        lines.append(f"- evidence_path: {payload['evidence_path']}")
    return "\n".join(lines)


def _metric_warning_names(metrics: dict[str, Any]) -> list[str]:
    warnings = []
    for name, row in metrics.items():
        if not isinstance(row, dict):
            continue
        status = str(row.get("status") or "")
        if status in {"MISSING", "NOT_AVAILABLE", "NOT_RETAINED", "REVIEW_REQUIRED"}:
            warnings.append(name)
    return warnings


def ai_status_command(
    args: argparse.Namespace,
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
) -> CommandResult:
    try:
        report = build_ai_status_report(
            runtime_root=runtime_root,
            check_runtime_readiness=bool(args.check_runtime_readiness),
        )
        evidence_path = ""
        if args.write_evidence:
            evidence_path = str(write_ai_status_evidence(report, evidence_root=evidence_root))
        payload = runner_response(
            {
                "schema_version": report["schema_version"],
                "subcommand": "ai-status",
                "status": report["status"],
                "current_step": "ai-status",
                "completed_days": [],
                "next_step": "manual review" if report["status"] == "REVIEW_REQUIRED" else "",
                "backup_id": "",
                "evidence_path": evidence_path,
                "final_judgment": report["final_judgment"]["final_judgment"],
                "exit_code": report["exit_code"],
                "runtime_root": str(runtime_root),
                "profile_id": profile.get("profile_id", ""),
                "read_only": True,
                "broker_access": "NOT_PERFORMED",
                "ai_status_report": report,
                "phase22_strategy_ai_input_binding": _latest_strategy_ai_binding(evidence_root=evidence_root, profile=profile),
                "human_summary": report["detailed_human_summary"] if args.detailed else report["human_summary"],
            }
        )
        return CommandResult(str(report["status"]), int(report["exit_code"]), payload)
    except Exception as exc:
        payload = base_payload("ai-status", "HALT")
        payload.update(
            {
                "status": "COMMAND_ERROR",
                "exit_code": EXIT_HALT,
                "error": str(exc),
                "read_only": True,
                "broker_access": "NOT_PERFORMED",
            }
        )
        return CommandResult("COMMAND_ERROR", EXIT_HALT, runner_response(payload))


def system_status_command(
    args: argparse.Namespace,
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
) -> CommandResult:
    try:
        requested_scope = str(getattr(args, "scope", "overview") or "overview")
        scope = "full" if getattr(args, "full", False) else ("readiness" if requested_scope == "strategy" else requested_scope)
        expected_business_date = str((profile.get("window") or {}).get("date_from") or "")
        post_run_context = latest_closed_runtime_test_system_status_context(
            evidence_root=evidence_root,
            profile=profile,
            runtime_root=runtime_root,
        )
        if post_run_context:
            expected_business_date = str(post_run_context.get("final_business_date") or expected_business_date)
        target_business_dates = post_run_context.get("completed_business_days") if post_run_context else system_status_target_business_dates(profile)
        explicit_target_start = str(getattr(args, "target_start_date", "") or "")
        explicit_target_end = str(getattr(args, "target_end_date", "") or "")
        if explicit_target_start:
            post_run_context = {}
            expected_business_date = explicit_target_start
            if explicit_target_end:
                target_business_dates = [explicit_target_start, explicit_target_end]
            else:
                target_business_dates = [explicit_target_start]
        report = build_system_status_report(
            runtime_root=runtime_root,
            expected_business_date=expected_business_date or None,
            runtime_mode=str(profile.get("mode") or ""),
            profile_id=str(profile.get("profile_id") or ""),
            broker_environment=str(profile.get("broker_environment") or ""),
            target_business_dates=target_business_dates,
            post_run_context=post_run_context,
        )
        evidence_path = ""
        if args.write_evidence:
            evidence_path = str(write_system_status_evidence(report, evidence_root=evidence_root))
        scoped_view = build_system_status_scoped_view(report, scope=scope)
        strategy_readiness = _system_strategy_readiness(evidence_root=evidence_root, profile=profile, runtime_root=runtime_root)
        scoped_view.setdefault("sections", {})["strategy_shadow_readiness"] = strategy_readiness
        if requested_scope == "strategy":
            scoped_view["scope"] = "strategy"
            scoped_view["human_summary"] = _render_strategy_system_status(strategy_readiness)
        payload = runner_response(
            {
                "schema_version": scoped_view["schema_version"],
                "subcommand": "system-status",
                "status": report["status"],
                "current_step": "system-status",
                "completed_days": [],
                "next_step": "manual review" if report["status"] == "REVIEW_REQUIRED" else "",
                "backup_id": "",
                "evidence_path": evidence_path,
                "final_judgment": report["final_judgment"]["final_judgment"],
                "exit_code": report["exit_code"],
                "runtime_root": str(runtime_root),
                "profile_id": profile.get("profile_id", ""),
                "read_only": True,
                "broker_access": "NOT_PERFORMED",
                "scope": "strategy" if requested_scope == "strategy" else scope,
                "system_status_schema_version": scoped_view["schema_version"],
                "inspection_context": scoped_view["inspection_context"],
                "status_summary": scoped_view["status_summary"],
                "findings": scoped_view["findings"],
                "sections": scoped_view["sections"],
                "strategy_shadow_readiness": strategy_readiness,
                "legacy_json_compatibility": scoped_view["legacy_json_compatibility"],
                "system_status_report": report,
                "human_summary": scoped_view["human_summary"],
            }
        )
        return CommandResult(str(report["status"]), int(report["exit_code"]), payload)
    except Exception as exc:
        payload = base_payload("system-status", "HALT")
        payload.update(
            {
                "status": "COMMAND_ERROR",
                "exit_code": EXIT_HALT,
                "error": str(exc),
                "read_only": True,
                "broker_access": "NOT_PERFORMED",
            }
        )
        return CommandResult("COMMAND_ERROR", EXIT_HALT, runner_response(payload))


def market_data_bootstrap_command(
    args: argparse.Namespace,
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
) -> CommandResult:
    del profile
    action = str(getattr(args, "market_data_bootstrap_action", "") or "")
    if action not in {"plan", "run"}:
        payload = base_payload("market-data-bootstrap", "INVALID_ARGUMENT")
        payload.update(
            {
                "status": "INVALID_ARGUMENT",
                "exit_code": EXIT_INVALID_ARGUMENT,
                "error": "market-data-bootstrap requires one of: plan, run",
                "read_only": True,
                "broker_access": "NOT_PERFORMED",
            }
        )
        return CommandResult("INVALID_ARGUMENT", EXIT_INVALID_ARGUMENT, runner_response(payload))
    phase_evidence_root = Path(evidence_root).parent / "phase20_bb_runtime_market_data_bootstrap"
    kwargs = {
        "runtime_root": runtime_root,
        "source_path": Path(str(getattr(args, "source_path", "") or ".runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet")),
        "evidence_root": phase_evidence_root,
        "years": int(getattr(args, "years", 5) or 5),
        "target_start_date": getattr(args, "target_start_date", None),
        "target_end_date": getattr(args, "target_end_date", None),
        "write_evidence": bool(getattr(args, "write_evidence", False)),
    }
    if action == "plan":
        result = build_market_data_bootstrap_plan(**kwargs)
    else:
        result = execute_market_data_bootstrap(
            **kwargs,
            confirm=bool(getattr(args, "confirm", False)),
            explicit_mutation_confirm=bool(getattr(args, "explicit_market_data_mutation_confirm", False)),
        )
    status = "PASS" if result.get("status") == "PASS" else "BLOCKED"
    exit_code = EXIT_PASS if status == "PASS" else EXIT_BLOCKED
    payload = runner_response(
        {
            "schema_version": result.get("schema_version", RUNNER_SCHEMA_VERSION),
            "subcommand": "market-data-bootstrap",
            "action": action,
            "status": status,
            "current_step": "market-data-bootstrap",
            "completed_days": [],
            "next_step": "operator review" if status != "PASS" else "",
            "backup_id": "",
            "evidence_path": str(phase_evidence_root) if bool(getattr(args, "write_evidence", False)) else "",
            "final_judgment": result.get("final_judgment", status),
            "exit_code": exit_code,
            "runtime_root": str(runtime_root),
            "read_only": action == "plan",
            "broker_access": "NOT_PERFORMED",
            "jquants_api_fetch_executed": False,
            "runtime_market_data_mutated": bool(result.get("runtime_market_data_mutated", False)),
            "bootstrap_result": result,
        }
    )
    return CommandResult(status, exit_code, payload)


def market_data_acquisition_command(
    args: argparse.Namespace,
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
) -> CommandResult:
    del profile
    action = str(getattr(args, "market_data_acquisition_action", "") or "")
    phase_evidence_root = Path(evidence_root).parent / "phase20_bh_historical_trading_calendar_business_day_authority"
    try:
        if action == "plan":
            result = build_acquisition_plan(
                runtime_root=runtime_root,
                start_date=str(getattr(args, "start_date")),
                end_date=str(getattr(args, "end_date")),
                run_id=getattr(args, "run_id", None),
                evidence_root=phase_evidence_root,
                chunk=str(getattr(args, "chunk", "month") or "month"),
                write_evidence=bool(getattr(args, "write_evidence", False)),
            )
        elif action == "run":
            result = run_acquisition(
                runtime_root=runtime_root,
                start_date=str(getattr(args, "start_date")),
                end_date=str(getattr(args, "end_date")),
                run_id=getattr(args, "run_id", None),
                evidence_root=phase_evidence_root,
                chunk=str(getattr(args, "chunk", "month") or "month"),
                confirm=bool(getattr(args, "confirm", False)),
                explicit_fetch_confirm=bool(getattr(args, "explicit_fetch_confirm", False)),
                write_evidence=bool(getattr(args, "write_evidence", False)),
                max_pages_per_chunk=int(getattr(args, "max_pages_per_chunk", 100) or 100),
            )
        elif action == "resume":
            result = resume_acquisition(
                runtime_root=runtime_root,
                run_id=str(getattr(args, "run_id")),
                evidence_root=phase_evidence_root,
                confirm=bool(getattr(args, "confirm", False)),
                explicit_fetch_confirm=bool(getattr(args, "explicit_fetch_confirm", False)),
                write_evidence=bool(getattr(args, "write_evidence", False)),
                max_pages_per_chunk=int(getattr(args, "max_pages_per_chunk", 100) or 100),
            )
        elif action == "status":
            result = acquisition_status(
                runtime_root=runtime_root,
                run_id=str(getattr(args, "run_id")),
                evidence_root=phase_evidence_root,
            )
        else:
            result = {
                "schema_version": RUNNER_SCHEMA_VERSION,
                "operation": action,
                "status": "BLOCK",
                "final_judgment": "ACQUISITION_INVALID_ACTION",
                "blocked_reasons": ["market-data-acquisition requires one of: plan, run, resume, status"],
                "runtime_market_data_mutated": False,
                "jquants_api_fetch_executed": False,
            }
    except Exception as exc:  # noqa: BLE001
        result = {
            "schema_version": RUNNER_SCHEMA_VERSION,
            "operation": action,
            "status": "BLOCK",
            "final_judgment": "ACQUISITION_COMMAND_ERROR",
            "blocked_reasons": [str(exc)],
            "runtime_market_data_mutated": False,
            "jquants_api_fetch_executed": False,
        }
    status = "PASS" if result.get("status") == "PASS" else "REVIEW_REQUIRED" if result.get("status") == "IN_PROGRESS" else "BLOCKED"
    exit_code = EXIT_PASS if status == "PASS" else EXIT_REVIEW_REQUIRED if status == "REVIEW_REQUIRED" else EXIT_BLOCKED
    payload = runner_response(
        {
            "schema_version": result.get("schema_version", RUNNER_SCHEMA_VERSION),
            "subcommand": "market-data-acquisition",
            "action": action,
            "status": status,
            "current_step": "market-data-acquisition",
            "completed_days": [],
            "next_step": "resume" if status == "REVIEW_REQUIRED" else "operator review" if status == "BLOCKED" else "",
            "backup_id": "",
            "evidence_path": str(phase_evidence_root) if bool(getattr(args, "write_evidence", False)) else "",
            "final_judgment": result.get("final_judgment", status),
            "exit_code": exit_code,
            "runtime_root": str(runtime_root),
            "read_only": action in {"plan", "status"},
            "broker_access": "NOT_PERFORMED",
            "jquants_api_fetch_executed": bool(result.get("jquants_api_fetch_executed", False)),
            "runtime_market_data_mutated": bool(result.get("runtime_market_data_mutated", False)),
            "acquisition_result": result,
        }
    )
    return CommandResult(status, exit_code, payload)


def system_status_target_business_dates(profile: dict[str, Any]) -> list[str]:
    accepted = profile.get("accepted_feature_dates")
    if isinstance(accepted, dict) and accepted:
        return sorted(str(day) for day in accepted)
    window = profile.get("window") if isinstance(profile.get("window"), dict) else {}
    start = str(window.get("date_from") or "")
    end = str(window.get("date_to") or "")
    if not start or not end:
        return []
    try:
        current = date.fromisoformat(start)
        final = date.fromisoformat(end)
    except ValueError:
        return []
    days: list[str] = []
    while current <= final:
        if current.weekday() < 5:
            days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def latest_closed_runtime_test_system_status_context(
    *,
    evidence_root: Path,
    profile: dict[str, Any],
    runtime_root: Path,
) -> dict[str, Any]:
    """Resolve a closed Historical Runtime Test context for read-only post-run inspection."""

    profile_id = str(profile.get("profile_id") or "")
    if str(profile.get("mode") or "") != "historical" or not profile_id:
        return {}
    if active_run_for_profile(evidence_root, profile_id=profile_id):
        return {}
    root = runs_root(evidence_root)
    if not root.exists():
        return {}
    summaries = sorted(root.glob("*/fresh_run_summary.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for summary_path in summaries:
        summary = read_json_optional(summary_path)
        if str(summary.get("profile_id") or "") != profile_id:
            continue
        if str(summary.get("status") or "") != "PASS" or str(summary.get("close_result") or "") != "PASS":
            continue
        completed_days = [str(day) for day in summary.get("completed_days") or [] if str(day)]
        if not completed_days:
            continue
        run_id = str(summary.get("run_id") or summary_path.parent.name)
        final_summary = read_json_optional(runs_root(evidence_root) / run_id / "final_summary.json")
        if str(final_summary.get("status") or "") != "PASS" or not final_summary.get("closed_at"):
            continue
        if not _runtime_roots_match(str(summary.get("runtime_root") or ""), runtime_root):
            continue
        final_state_hashes = final_summary.get("final_state_hashes") if isinstance(final_summary.get("final_state_hashes"), dict) else {}
        current_state_hashes = state_hashes(runtime_root) if runtime_root.exists() else {}
        final_state_hash_match = bool(final_state_hashes) and current_state_hashes == final_state_hashes
        current_state = read_json_optional(runtime_root / "persistent_ledger" / "state.json") if final_state_hash_match else {}
        final_positions = current_state.get("positions") if isinstance(current_state.get("positions"), list) else []
        final_day = completed_days[-1]
        context = {
            "schema_version": "system_status_historical_post_run_context.v1",
            "context_type": "HISTORICAL_POST_RUN",
            "status": "PASS",
            "authority": "latest_closed_runtime_test",
            "run_id": run_id,
            "profile_id": profile_id,
            "run_evidence_root": str(summary_path.parent),
            "runtime_root": str(runtime_root),
            "completed_business_days": completed_days,
            "final_business_date": final_day,
            "closed_at": str(final_summary.get("closed_at") or ""),
            "fresh_run_summary_path": str(summary_path),
            "final_summary_path": str(runs_root(evidence_root) / run_id / "final_summary.json"),
            "final_state_hashes": final_state_hashes,
            "current_state_hashes": current_state_hashes,
            "final_state_hash_match": final_state_hash_match,
            "final_position_count": len(final_positions) if final_state_hash_match else "NOT_AVAILABLE",
            "final_position_count_authority": (
                "CURRENT_RUNTIME_ROOT_FINAL_HASH_MATCH"
                if final_state_hash_match
                else "NOT_AVAILABLE_FINAL_STATE_HASH_MISMATCH"
            ),
            "runtime_stage": "EXECUTION_DONE",
            "completed_runtime_components": _completed_runtime_components(runtime_root, final_day),
        }
        context.update(_historical_post_run_safety_context(runtime_root, final_day))
        return context
    return {}


def _latest_strategy_run_summary(*, evidence_root: Path, profile: dict[str, Any], runtime_root: Path) -> dict[str, Any]:
    active = active_run_for_profile(evidence_root, profile_id=str(profile.get("profile_id") or ""))
    run_id = str(active.get("run_id") or "") if active else ""
    if not run_id:
        context = latest_closed_runtime_test_system_status_context(evidence_root=evidence_root, profile=profile, runtime_root=runtime_root)
        run_id = str(context.get("run_id") or "")
    if not run_id:
        return {}
    return load_run_strategy_shadow_summary(run_dir=runs_root(evidence_root) / run_id)


def _system_strategy_readiness(*, evidence_root: Path, profile: dict[str, Any], runtime_root: Path) -> dict[str, Any]:
    summary = _latest_strategy_run_summary(evidence_root=evidence_root, profile=profile, runtime_root=runtime_root)
    return {
        "schema_version": "phase22_strategy_shadow_system_status.v1",
        "status": summary.get("strategy_shadow_judgment", "NOT_AVAILABLE") if summary else "NOT_AVAILABLE",
        "strategy_producer_availability": "PASS",
        "strategy_artifact_freshness": "PASS" if summary.get("business_dates_generated") else "REVIEW_REQUIRED",
        "strategy_artifact_status": summary.get("strategy_shadow_judgment", "NOT_AVAILABLE") if summary else "NOT_AVAILABLE",
        "shadow_consumer_eligibility": summary.get("shadow_consumer_eligibility", "NO") if summary else "NO",
        "active_consumer_eligibility": "NO",
        "corporate_event_coverage": "REVIEW_REQUIRED",
        "historical_sector_pit_status": "REVIEW_REQUIRED",
        "runtime_switch_performed": False,
        "production_readiness_impact": "NONE_SHADOW_ONLY",
        "run_id": summary.get("run_id", "") if summary else "",
        "generated_dates": summary.get("business_dates_generated", []) if summary else [],
        "review_required_dates": summary.get("review_required_dates", []) if summary else [],
        "blocked_dates": summary.get("blocked_dates", []) if summary else [],
    }


def _render_strategy_system_status(strategy: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Phase22 Strategy Shadow Status",
            "==============================",
            f"Status              : {strategy.get('status')}",
            f"Run ID              : {strategy.get('run_id')}",
            f"Generated Dates     : {len(strategy.get('generated_dates') or [])}",
            f"Review Dates        : {len(strategy.get('review_required_dates') or [])}",
            f"Blocked Dates       : {len(strategy.get('blocked_dates') or [])}",
            f"Shadow Eligibility  : {strategy.get('shadow_consumer_eligibility')}",
            f"Active Eligibility  : {strategy.get('active_consumer_eligibility')}",
            f"Runtime Switch      : {strategy.get('runtime_switch_performed')}",
        ]
    )


def _latest_strategy_ai_binding(*, evidence_root: Path, profile: dict[str, Any]) -> dict[str, Any]:
    active = active_run_for_profile(evidence_root, profile_id=str(profile.get("profile_id") or ""))
    run_id = str(active.get("run_id") or "") if active else ""
    if not run_id:
        return {"status": "NOT_AVAILABLE", "reason": "no_active_runtime_test_run"}
    run_dir = runs_root(evidence_root) / run_id
    paths = sorted(run_dir.glob("daily/*/strategy/input_manifest.json"))
    if not paths:
        return {"status": "NOT_AVAILABLE", "run_id": run_id, "reason": "strategy_shadow_input_manifest_missing"}
    manifest = read_json_optional(paths[-1])
    return {
        "status": "PASS" if manifest.get("accepted_generation_id") else "REVIEW_REQUIRED",
        "run_id": run_id,
        "business_date": manifest.get("business_date", ""),
        "accepted_generation_id": manifest.get("accepted_generation_id", ""),
        "candidate_artifact_reference": manifest.get("candidate_artifact", ""),
        "candidate_artifact_hash": manifest.get("candidate_artifact_hash", ""),
        "opportunity_artifact_reference": manifest.get("opportunity_artifact", ""),
        "opportunity_artifact_hash": manifest.get("opportunity_artifact_hash", ""),
        "feature_schema_hash": manifest.get("feature_schema_hash", {}),
        "read_only": True,
    }


def _runtime_roots_match(recorded_root: str, runtime_root: Path) -> bool:
    if not recorded_root:
        return False
    recorded = Path(recorded_root)
    if not recorded.is_absolute():
        recorded = Path.cwd() / recorded
    try:
        return recorded.resolve() == runtime_root.resolve()
    except FileNotFoundError:
        return recorded.absolute() == runtime_root.absolute()


def _completed_runtime_components(runtime_root: Path, business_date: str) -> list[str]:
    manifest_dir = runtime_root / "runtime_state" / "run_manifest" / business_date
    jobs = {
        "sell_planning": "sell_planning",
        "approval": "morning",
        "submit": "submit",
        "execution": "execution",
        "reporting": "execution",
        "notification": "execution",
    }
    completed: set[str] = set()
    if manifest_dir.is_dir():
        for path in manifest_dir.glob("*.json"):
            payload = read_json_optional(path)
            job = str(payload.get("job") or "")
            if str(payload.get("exit_code") or "0") not in {"0", ""}:
                continue
            for component, expected_job in jobs.items():
                if job == expected_job:
                    completed.add(component)
    return sorted(completed)


def _historical_post_run_safety_context(runtime_root: Path, business_date: str) -> dict[str, Any]:
    manifest_dir = runtime_root / "runtime_state" / "run_manifest" / business_date
    if not manifest_dir.is_dir():
        return {"safety_status": "MISSING", "safety_business_date": business_date}
    candidates = sorted(manifest_dir.glob("*data_readiness*.json")) + sorted(manifest_dir.glob("*submit*.json"))
    for path in candidates:
        payload = read_json_optional(path)
        safety_status = str(payload.get("data_readiness_safety_status") or payload.get("safety_status") or "")
        safety_date = str(payload.get("data_readiness_safety_authority_business_date") or payload.get("safety_authority_business_date") or "")
        safety_source = str(payload.get("data_readiness_safety_authority_source") or payload.get("safety_authority_source") or "")
        if safety_status in {"READY", "PASS"} and safety_date == business_date and safety_source == "data_readiness_historical_temporal_authority":
            return {
                "safety_status": safety_status,
                "safety_business_date": safety_date,
                "safety_authority_source": safety_source,
                "safety_authority": str(payload.get("data_readiness_safety_authority") or payload.get("safety_authority") or ""),
                "safety_policy_version": str(payload.get("data_readiness_safety_authority_policy_version") or payload.get("safety_policy_version") or ""),
                "safety_decision": str(payload.get("safety_decision") or "ALLOW"),
                "safety_decision_id": str(payload.get("safety_decision_id") or ""),
                "safety_authority_path": str(path),
                "safety_authority_sha256": sha256_file(path),
            }
    return {"safety_status": "MISSING", "safety_business_date": business_date}


def prepare_isolated_command(
    args: argparse.Namespace,
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
) -> CommandResult:
    if profile.get("mode") != "historical":
        raise RuntimeTestError("prepare-isolated is only valid for historical profiles", status="INVALID_ARGUMENT", exit_code=EXIT_INVALID_ARGUMENT)
    run_id = args.run_id or f"runtime-test-{profile['profile_id']}-{timestamp_id()}"
    target_business_date = args.target_business_date or str((profile.get("window") or {}).get("date_from") or "")
    if not target_business_date:
        raise RuntimeTestError("target business date is required", status="INVALID_ARGUMENT", exit_code=EXIT_INVALID_ARGUMENT)
    result = materialize_isolated_historical_runtime_root(
        repo_root=Path.cwd(),
        shared_runtime_root=runtime_root,
        run_id=run_id,
        profile=profile,
        target_business_date=target_business_date,
    )
    isolated_runtime_root = Path(result["isolated_runtime_root"])
    report = build_system_status_report(
        runtime_root=isolated_runtime_root,
        expected_business_date=target_business_date,
        runtime_mode=str(profile.get("mode") or ""),
        profile_id=str(profile.get("profile_id") or ""),
        broker_environment=str(profile.get("broker_environment") or ""),
        target_business_dates=system_status_target_business_dates(profile),
    )
    temporal = report["temporal_authority_audit"]
    result["temporal_preflight"] = {
        "status": "PASS" if temporal.get("future_state_reference_count") == 0 and temporal.get("temporal_isolation_status") == "PASS" else "BLOCK",
        "target_business_date": target_business_date,
        "future_state_reference_count": temporal.get("future_state_reference_count"),
        "temporal_isolation_status": temporal.get("temporal_isolation_status"),
    }
    result["system_status"] = {
        "status": report["status"],
        "exit_code": report["exit_code"],
        "runtime_root": str(isolated_runtime_root),
        "final_judgment": report["final_judgment"]["final_judgment"],
    }
    result["run_id_root_binding"] = {
        "status": "PASS",
        "run_id": run_id,
        "isolated_runtime_root": str(isolated_runtime_root),
        "day1_to_day5_same_root_required": True,
        "resume_must_resolve_same_root": True,
        "different_run_state_sharing": False,
    }
    result["day1_pre_run_artifact_inventory"] = day1_pre_run_absent_artifacts(isolated_runtime_root, target_business_date)
    final_status = "PASS" if (
        result.get("status") == "PASS"
        and result["temporal_preflight"]["status"] == "PASS"
        and result["day1_pre_run_artifact_inventory"]["status"] == "PASS"
    ) else "BLOCK"
    result["status"] = final_status
    result["exit_code"] = EXIT_PASS if final_status == "PASS" else EXIT_BLOCKED
    evidence_path = ""
    if args.write_evidence:
        evidence_path = str(write_prepare_isolated_evidence(result, evidence_root=evidence_root))
        result["evidence_path"] = evidence_path
    payload = base_payload("prepare-isolated", final_status)
    payload.update(result)
    payload["current_step"] = "prepare-isolated"
    payload["next_step"] = "AY Day1 manual run" if final_status == "PASS" else "manual review"
    payload["final_judgment"] = (
        ["PHASE19_BB_ISOLATED_HISTORICAL_RUNTIME_READY", "PHASE19_AY_DAY1_MANUAL_RUN_READY"]
        if final_status == "PASS"
        else ["PHASE19_BB_FAIL", "PHASE19_AY_DAY1_BLOCKED"]
    )
    payload["read_only_shared_runtime"] = result.get("shared_runtime_non_mutation") is True
    return CommandResult(final_status, int(payload["exit_code"]), runner_response(payload))


def write_prepare_isolated_evidence(result: dict[str, Any], *, evidence_root: Path) -> Path:
    run_id = str(result.get("run_id") or timestamp_id())
    root = Path(evidence_root) / "prepare_isolated" / run_id
    root.mkdir(parents=True, exist_ok=True)
    mapping = {
        "prepare_isolated_result.json": result,
        "shared_runtime_pre_hashes.json": result.get("shared_runtime_pre_hashes", {}),
        "shared_runtime_post_hashes.json": result.get("shared_runtime_post_hashes", {}),
        "isolated_runtime_root_manifest.json": result.get("metadata", {}),
        "historical_initial_state_materialization.json": result.get("historical_initial_state", {}),
        "accepted_generation_resolution.json": result.get("accepted_generation_resolution", {}),
        "temporal_preflight_result.json": result.get("temporal_preflight", {}),
        "run_id_root_binding.json": result.get("run_id_root_binding", {}),
        "day1_pre_run_artifact_inventory.json": result.get("day1_pre_run_artifact_inventory", {}),
    }
    for name, payload in mapping.items():
        write_json_atomic(root / name, payload)
    return root


def plan_command(
    args: argparse.Namespace,
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
) -> CommandResult:
    validate_plan_namespace(args)
    plan_payload = build_plan(
        profile=profile,
        runtime_root=runtime_root,
        evidence_root=evidence_root,
        business_days=args.business_days,
        start_date=args.start_date,
        date_from=args.date_from,
        date_to=args.date_to,
        run_id=args.run_id,
    )
    baseline_compatibility = build_baseline_compatibility(
        runtime_root=runtime_root,
        requested_start_date=str(
            ((plan_payload.get("business_dates") or [{}])[0]).get("business_date")
            or plan_payload.get("requested_start_date")
            or ""
        ),
        run_id=plan_payload["run_id"],
        profile_id=profile["profile_id"],
        mode=profile["mode"],
    )
    plan_payload["baseline_compatibility"] = baseline_compatibility
    validate_plan_entry_gate(plan_payload)
    try:
        persistence = persist_runtime_test_plan(
            evidence_root=evidence_root,
            plan_payload=plan_payload,
            profile_id=str(profile["profile_id"]),
        )
    except Exception as exc:
        raise RuntimeTestError(
            f"runtime test plan persistence failed: {exc}",
            status="PRECONDITION_FAILURE",
            exit_code=EXIT_PRECONDITION_FAILURE,
        ) from exc
    plan_payload["plan_persistence"] = persistence
    plan_judgment = (
        "PASS"
        if baseline_compatibility["baseline_compatibility_status"] == "PASS"
        and plan_payload.get("window_resolution_status") == "PASS"
        else "PLAN_REVIEW_REQUIRED"
    )
    plan_status = "PASS" if plan_judgment == "PASS" else "REVIEW_REQUIRED"
    payload = base_payload("plan", plan_status)
    payload.update(plan_payload)
    payload["plan_judgment"] = plan_judgment
    payload["window_resolution_judgment"] = plan_payload.get("window_resolution_status", "")
    payload["request_conformance_judgment"] = plan_payload.get("request_conformance_status", "")
    payload["runtime_test_plan_schema_version"] = plan_payload["schema_version"]
    exit_code = EXIT_PASS if plan_status == "PASS" else EXIT_REVIEW_REQUIRED
    payload["exit_code"] = exit_code
    return CommandResult(plan_status, exit_code, runner_response(payload))


def plan_namespace_from_fresh_run(args: argparse.Namespace, *, run_id: str | None = None) -> argparse.Namespace:
    """Build the exact internal Namespace required by plan_command."""

    return argparse.Namespace(
        business_days=args.business_days,
        start_date=args.start_date,
        date_from=args.date_from,
        date_to=args.date_to,
        run_id=run_id,
        write_evidence=False,
        json=False,
    )


def validate_plan_namespace(args: argparse.Namespace) -> dict[str, Any]:
    required = ("business_days", "start_date", "date_from", "date_to", "run_id")
    missing = [name for name in required if not hasattr(args, name)]
    if missing:
        raise RuntimeTestError(
            "plan namespace missing required attributes: " + ", ".join(missing),
            status="INVALID_ARGUMENT",
            exit_code=EXIT_INVALID_ARGUMENT,
        )
    return {
        "status": "PASS",
        "required_attributes": list(required),
        "run_id_present": bool(getattr(args, "run_id")),
        "run_id_required_before_plan": False,
    }


def backup_command(
    args: argparse.Namespace,
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
) -> CommandResult:
    require_historical_mutation_context(args=args, profile=profile)
    backup_id = f"backup-{profile['profile_id']}-{timestamp_id()}"
    backup_dir = backups_root(evidence_root) / backup_id
    inventory = build_backup_inventory(runtime_root)
    manifest = {
        "schema_version": BACKUP_MANIFEST_SCHEMA_VERSION,
        "backup_id": backup_id,
        "backup_path": str(backup_dir),
        "manifest_path": str(backup_dir / "backup_manifest.json"),
        "profile_id": profile["profile_id"],
        "runtime_root": str(runtime_root),
        "created_at": utc_now(),
        "source_commit": git_commit(),
        "source_dirty": source_dirty(),
        "scope": "resettable_trading_state_only",
        "targets": inventory,
        "excluded_prefixes": list(RESET_EXCLUDED_RELATIVE_PREFIXES),
        "restore_validation_plan": "validate file inventory and hashes before rollback",
        "dry_run": bool(args.dry_run),
    }
    manifest["file_count"] = sum(1 for item in inventory if item.get("kind") == "file")
    manifest["bundle_hash"] = semantic_hash(inventory)
    if not args.dry_run:
        require_confirm(args)
        if backup_dir.exists():
            raise RuntimeTestError("backup_id collision", status="HALT", exit_code=EXIT_HALT)
        tmp_dir = backup_dir.with_name(backup_dir.name + ".partial")
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        copy_resettable_state(runtime_root=runtime_root, destination=tmp_dir / "state")
        write_json_atomic(tmp_dir / "backup_manifest.json", manifest)
        tmp_dir.rename(backup_dir)
    payload = base_payload("backup", "PASS")
    payload.update(manifest)
    payload["runtime_test_backup_manifest_schema_version"] = manifest["schema_version"]
    return CommandResult("PASS", EXIT_PASS, runner_response(payload))


def reset_command(
    args: argparse.Namespace,
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
) -> CommandResult:
    require_historical_mutation_context(args=args, profile=profile)
    backup = load_backup_manifest(evidence_root, args.backup_id)
    initial_state = dict(profile["initial_state"])
    if args.initial_cash is not None:
        initial_state["cash"] = args.initial_cash
        initial_state["buying_power"] = args.initial_cash
    initial_position_state_date = str(getattr(args, "initial_position_state_date", "") or "")
    if initial_position_state_date:
        validate_initial_position_state_date(initial_position_state_date)
    manifest = {
        "schema_version": RESET_MANIFEST_SCHEMA_VERSION,
        "status": "DRY_RUN" if args.dry_run else "PASS",
        "profile_id": profile["profile_id"],
        "runtime_root": str(runtime_root),
        "backup_id": backup["backup_id"],
        "initial_state": initial_state,
        "reset_scope": list(RESETTABLE_RELATIVE_PATHS),
        "excluded_prefixes": list(RESET_EXCLUDED_RELATIVE_PREFIXES),
        "all_or_nothing": True,
        "partial_reset_prohibited": True,
        "created_at": utc_now(),
        "initial_date_policy": "historical_fresh_run_first_business_date" if initial_position_state_date else "legacy_reset_without_logical_date",
        "resolved_initial_position_state_date": initial_position_state_date,
        "logical_time_fields": ["business_date", "as_of", "position_state_as_of"],
        "wall_clock_fields": ["created_at", "updated_at", "reset_executed_at"],
        "dry_run": bool(args.dry_run),
    }
    if not args.dry_run:
        require_confirm(args)
        try:
            apply_reset(
                runtime_root=runtime_root,
                initial_state=initial_state,
                profile=profile,
                initial_position_state_date=initial_position_state_date,
            )
        except Exception as exc:
            restore_from_backup(runtime_root=runtime_root, backup_manifest=backup)
            raise RuntimeTestError(
                f"reset failed; rollback attempted: {exc}",
                status="ROLLBACK_REQUIRED",
                exit_code=EXIT_ROLLBACK_FAILURE,
            ) from exc
    manifest["post_reset_hash"] = directory_hash(runtime_root) if runtime_root.exists() else ""
    manifest["clean_state_invariant"] = reset_clean_state_invariant(
        runtime_root=runtime_root,
        initial_state=initial_state,
        executed=not args.dry_run,
    )
    payload = base_payload("reset", "PASS" if not args.dry_run else "DRY_RUN")
    payload.update(manifest)
    payload["runtime_test_reset_manifest_schema_version"] = manifest["schema_version"]
    return CommandResult(payload["status"], EXIT_PASS, runner_response(payload))


def materialize_historical_evaluation_authority(
    *,
    run_dir: Path,
    runtime_root: Path,
    profile: dict[str, Any],
    plan_payload: dict[str, Any],
) -> dict[str, Any]:
    if str(profile.get("mode") or "") != "historical":
        return {"status": "NOT_REQUESTED", "reason": "non_historical_runtime_test_profile"}
    business_dates = [
        str(day.get("business_date") or "")
        for day in plan_payload.get("business_dates", [])
        if isinstance(day, dict) and day.get("business_date")
    ]
    market_as_of_business_date = business_dates[0] if business_dates else ""
    evaluation_authority_time = utc_now()
    resolution = resolve_accepted_generation_for_evaluation(
        runtime_root,
        evaluation_authority_time=evaluation_authority_time,
    )
    if not resolution.is_resolved:
        raise RuntimeTestError(
            "historical evaluation authority cannot be fixed: " + resolution.block_reason,
            status="PRECONDITION_FAILURE",
            exit_code=EXIT_PRECONDITION_FAILURE,
        )
    manifest_path = Path(resolution.bundle_manifest_path)
    manifest = read_json(manifest_path)
    authority_path = run_dir / "historical_evaluation_authority.json"
    freshness = manifest.get("freshness_metadata") if isinstance(manifest.get("freshness_metadata"), dict) else {}
    field_sources = freshness.get("field_sources") if isinstance(freshness.get("field_sources"), dict) else {}
    candidate_member = manifest.get("candidate_member") if isinstance(manifest.get("candidate_member"), dict) else {}
    opportunity_member = manifest.get("opportunity_member") if isinstance(manifest.get("opportunity_member"), dict) else {}
    authority = {
        "schema_version": HISTORICAL_EVALUATION_AUTHORITY_SCHEMA_VERSION,
        "status": "PASS",
        "authority_contract": "run-start fixed Human Accepted Generation for Historical Runtime evaluation",
        "evaluation_mode": "CURRENT_ACCEPTED_RUNTIME_ON_HISTORICAL_DATA",
        "strict_oos_ai_performance": False,
        "strict_oos_reason": "Historical Runtime performance evaluates current accepted Runtime behavior; training overlap is reported separately.",
        "production_authority_unchanged": True,
        "historical_business_date_acceptance_comparison": "NOT_APPLIED_TO_ACCEPTED_GENERATION",
        "daily_pit_scope": ["market_data", "financial_data", "corporate_event", "feature", "calendar"],
        "latest_fallback_used": False,
        "current_pointer_updates_during_run": "IGNORED_BY_RUN_AUTHORITY",
        "run_id": str(plan_payload.get("run_id") or ""),
        "profile_id": str(profile.get("profile_id") or ""),
        "runtime_root": str(runtime_root),
        "authority_path": str(authority_path),
        "fixed_at": evaluation_authority_time,
        "evaluation_authority_time": evaluation_authority_time,
        "market_as_of_business_date": market_as_of_business_date,
        "authority_context": {
            "schema_version": "runtime_authority_context.v1",
            "evaluation_authority": {
                "generation_id": resolution.generation_id,
                "fixed_at": evaluation_authority_time,
                "authority_time": evaluation_authority_time,
            },
            "market_as_of_authority": {"business_date": market_as_of_business_date},
            "feature_as_of_authority": {"feature_date": ""},
            "execution_environment": {"broker_environment": str(profile.get("broker_environment") or "")},
        },
        "evaluation_period": {
            "date_from": business_dates[0] if business_dates else "",
            "date_to": business_dates[-1] if business_dates else "",
            "business_dates": business_dates,
        },
        "generation_id": resolution.generation_id,
        "accepted_generation_id": resolution.generation_id,
        "bundle_manifest_path": resolution.bundle_manifest_path,
        "accepted_at": resolution.accepted_at,
        "effective_from": resolution.effective_from,
        "accepted_decision": resolution.authority_decision,
        "aggregate_hash": resolution.aggregate_hash,
        "manifest_content_hash": str((resolution.source_evidence or {}).get("manifest_content_hash") or ""),
        "candidate_model": {
            "artifact_path": str(candidate_member.get("model_file") or (resolution.candidate_member.artifact_path if resolution.candidate_member else "")),
            "model_hash": str(candidate_member.get("model_hash") or (resolution.candidate_member.model_hash if resolution.candidate_member else "")),
            "scaler": str(candidate_member.get("scaler_file") or ""),
            "scaler_hash": str(candidate_member.get("scaler_hash") or ""),
            "feature_schema_hash": str(candidate_member.get("feature_schema_hash") or ""),
        },
        "opportunity_model": {
            "artifact_path": str(opportunity_member.get("model_file") or (resolution.opportunity_member.artifact_path if resolution.opportunity_member else "")),
            "model_hash": str(opportunity_member.get("model_hash") or (resolution.opportunity_member.model_hash if resolution.opportunity_member else "")),
            "scaler": str(opportunity_member.get("scaler_file") or ""),
            "scaler_hash": str(opportunity_member.get("scaler_hash") or ""),
            "feature_schema_hash": str(opportunity_member.get("feature_schema_hash") or ""),
        },
        "training_cutoff": {
            "candidate": _freshness_field_value(field_sources, "candidate_training_cutoff"),
            "opportunity": _freshness_field_value(field_sources, "opportunity_training_cutoff"),
            "calibration_candidate": _freshness_field_value(field_sources, "candidate_calibration_cutoff"),
            "calibration_opportunity": _freshness_field_value(field_sources, "opportunity_calibration_cutoff"),
            "validation": _freshness_field_value(field_sources, "validation_cutoff"),
        },
        "dataset_revision": {
            "dataset_revision_id": str(manifest.get("dataset_revision_id") or ""),
            "dataset_source_max_date": str(freshness.get("dataset_source_max_date") or ""),
            "dataset_target_max_date": str(freshness.get("dataset_target_max_date") or ""),
            "raw_data_max_date_at_generation": str(freshness.get("raw_data_max_date_at_generation") or ""),
            "normalized_data_max_date_at_generation": str(freshness.get("normalized_data_max_date_at_generation") or ""),
        },
        "hashes": {
            "run_authority_hash": "",
            "aggregate_hash": resolution.aggregate_hash,
            "manifest_content_hash": str((resolution.source_evidence or {}).get("manifest_content_hash") or ""),
            "candidate_model_hash": str(candidate_member.get("model_hash") or ""),
            "candidate_scaler_hash": str(candidate_member.get("scaler_hash") or ""),
            "opportunity_model_hash": str(opportunity_member.get("model_hash") or ""),
            "opportunity_scaler_hash": str(opportunity_member.get("scaler_hash") or ""),
        },
        "runtime_version": {"source_commit": git_commit(), "source_dirty": source_dirty()},
        "strategy_version": {"config_hashes": _strategy_config_hashes()},
    }
    authority["training_overlap"] = _training_overlap(
        training_cutoff=authority["training_cutoff"],
        evaluation_period=authority["evaluation_period"],
    )
    authority["hashes"]["run_authority_hash"] = "sha256:" + semantic_hash(authority | {"hashes": {**authority["hashes"], "run_authority_hash": ""}})
    authority["run_authority_hash"] = authority["hashes"]["run_authority_hash"]
    write_json_atomic(authority_path, authority)
    return authority


def validate_historical_evaluation_authority(
    *,
    run_dir: Path,
    runtime_root: Path,
    expected: dict[str, Any] | None = None,
) -> dict[str, Any]:
    authority_path = Path(str((expected or {}).get("authority_path") or run_dir / "historical_evaluation_authority.json"))
    if not authority_path.is_file():
        return {"status": "BLOCK", "reason": "historical_evaluation_authority_missing", "authority_path": str(authority_path)}
    authority = read_json_optional(authority_path)
    evaluation_period = authority.get("evaluation_period") if isinstance(authority.get("evaluation_period"), dict) else {}
    business_dates = evaluation_period.get("business_dates") if isinstance(evaluation_period.get("business_dates"), list) else []
    fixed_business_date = str(
        evaluation_period.get("date_from")
        or (business_dates[0] if business_dates else "")
        or ""
    )
    resolution = resolve_accepted_generation(
        runtime_root,
        business_date=fixed_business_date,
        fixed_authority_path=authority_path,
    )
    checks = {
        "authority_file_present": bool(authority),
        "schema_version": authority.get("schema_version") == HISTORICAL_EVALUATION_AUTHORITY_SCHEMA_VERSION,
        "resolution_status": resolution.is_resolved,
        "generation_id_fixed": bool(authority.get("generation_id")) and authority.get("generation_id") == resolution.generation_id,
        "aggregate_hash_fixed": bool(authority.get("aggregate_hash")) and authority.get("aggregate_hash") == resolution.aggregate_hash,
        "business_date_acceptance_comparison_not_applied": authority.get("historical_business_date_acceptance_comparison") == "NOT_APPLIED_TO_ACCEPTED_GENERATION",
        "latest_fallback_absent": authority.get("latest_fallback_used") is False,
        "production_authority_unchanged": authority.get("production_authority_unchanged") is True,
    }
    if expected:
        checks["run_authority_hash_unchanged"] = authority.get("run_authority_hash") == expected.get("run_authority_hash")
    status = "PASS" if all(checks.values()) else "BLOCK"
    return {
        "schema_version": "historical_evaluation_authority_validation.v1",
        "status": status,
        "authority_path": str(authority_path),
        "generation_id": str(authority.get("generation_id") or ""),
        "run_authority_hash": str(authority.get("run_authority_hash") or ""),
        "checks": checks,
        "reason_codes": [] if status == "PASS" else [name for name, passed in checks.items() if not passed],
        "current_pointer_change_ignored": True,
        "resolver_resolution": resolution.to_dict(),
    }


def _freshness_field_value(field_sources: dict[str, Any], name: str) -> str:
    payload = field_sources.get(name) if isinstance(field_sources.get(name), dict) else {}
    return str(payload.get("value") or "")


def _training_overlap(*, training_cutoff: dict[str, str], evaluation_period: dict[str, Any]) -> dict[str, Any]:
    start = str(evaluation_period.get("date_from") or "")
    cutoff_values = [value for value in training_cutoff.values() if value]
    latest_cutoff = max(cutoff_values) if cutoff_values else ""
    overlap = bool(start and latest_cutoff and latest_cutoff >= start)
    return {
        "status": "OVERLAP" if overlap else "NO_OVERLAP" if latest_cutoff and start else "UNKNOWN",
        "latest_training_cutoff": latest_cutoff,
        "evaluation_start": start,
        "strict_oos_label_allowed": not overlap and bool(latest_cutoff and start),
    }


def _strategy_config_hashes() -> dict[str, str]:
    root = Path("configs/strategy")
    if not root.exists():
        return {}
    return {
        str(path): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def run_command(
    args: argparse.Namespace,
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
) -> CommandResult:
    require_historical_mutation_context(args=args, profile=profile)
    if getattr(args, "auto_prepare", False):
        raise RuntimeTestError(
            "--auto-prepare is deprecated and incomplete; use `fresh-run` for formal Status->Backup->Reset->Plan->Run->Validate->Close orchestration",
            status="INVALID_ARGUMENT",
            exit_code=EXIT_INVALID_ARGUMENT,
        )
    if args.run_id:
        plan_payload = load_plan_for_run(evidence_root=evidence_root, run_id=args.run_id)
    else:
        plan_payload = build_plan(
            profile=profile,
            runtime_root=runtime_root,
            evidence_root=evidence_root,
            business_days=args.business_days,
            start_date=args.start_date,
            date_from=args.date_from,
            date_to=args.date_to,
        )
    validate_plan_entry_gate(plan_payload)
    if args.dry_run:
        payload = base_payload("run", "DRY_RUN")
        payload.update(plan_payload)
        payload["dry_run_no_mutation"] = True
        payload["runtime_test_plan_schema_version"] = plan_payload["schema_version"]
        return CommandResult("DRY_RUN", EXIT_PASS, runner_response(payload))
    require_confirm(args)
    validate_run_preconditions(runtime_root=runtime_root, evidence_root=evidence_root, plan_payload=plan_payload, profile=profile)
    run_id = plan_payload["run_id"]
    run_dir = runs_root(evidence_root) / run_id
    write_json_atomic(run_dir / "plan.json", plan_payload)
    historical_authority = materialize_historical_evaluation_authority(
        run_dir=run_dir,
        runtime_root=runtime_root,
        profile=profile,
        plan_payload=plan_payload,
    )
    historical_authority_validation = validate_historical_evaluation_authority(
        run_dir=run_dir,
        runtime_root=runtime_root,
        expected=historical_authority,
    )
    if historical_authority_validation["status"] != "PASS":
        raise RuntimeTestError(
            "historical evaluation authority gate failed: "
            + json.dumps(historical_authority_validation, ensure_ascii=False, sort_keys=True),
            status="PRECONDITION_FAILURE",
            exit_code=EXIT_PRECONDITION_FAILURE,
        )
    run_state = {
        "schema_version": RUN_STATE_SCHEMA_VERSION,
        "run_id": run_id,
        "profile_id": profile["profile_id"],
        "status": "RUNNING",
        "created_at": utc_now(),
        "completed_business_days": [],
        "completed_jobs": [],
        "next_job": "",
        "source_baseline": source_baseline(runtime_root),
        "historical_evaluation_authority": historical_authority,
        "historical_evaluation_authority_validation": historical_authority_validation,
    }
    write_json_atomic(run_dir / "run_state.json", run_state)
    for day in plan_payload["business_dates"]:
        for job in day["jobs"]:
            run_state["next_job"] = f"{day['business_date']}:{job['job']}"
            write_json_atomic(run_dir / "run_state.json", run_state)
            command_resolution = resolve_run_job_command(
                runtime_root=runtime_root,
                job_record=job,
                historical_evaluation_authority=historical_authority,
            )
            command = command_resolution["command"]
            subprocess_trace_path = run_dir / "daily" / day["business_date"] / job["job"] / "subprocess_trace.json"
            completed = _invoke_runtime_cli_job(
                command,
                cwd=Path.cwd(),
                trace_path=subprocess_trace_path,
                context={
                    "run_id": run_id,
                    "profile_id": str(profile["profile_id"]),
                    "business_date": day["business_date"],
                    "job": job["job"],
                    "runtime_root": str(runtime_root),
                    "evidence_root": str(evidence_root),
                    "source_commit": git_commit(),
                    "source_dirty": source_dirty(),
                },
            )
            job_record = {
                "business_date": day["business_date"],
                "job": job["job"],
                "exit_code": completed.returncode,
                "command": command,
                "planned_command": job["command"],
                "feature_date_command_resolution": command_resolution["resolution"],
                "subprocess_trace_path": str(subprocess_trace_path),
                "subprocess_trace": getattr(completed, "runtime_test_subprocess_trace", {}),
            }
            collect_runtime_cli_job_evidence(
                completed=completed,
                run_dir=run_dir,
                runtime_root=runtime_root,
                business_date=day["business_date"],
                job=job["job"],
            )
            write_performance_observability_evidence(
                run_dir=run_dir,
                runtime_root=runtime_root,
                run_id=run_id,
                business_date=day["business_date"],
                job=job["job"],
            )
            scoped_block = classify_scoped_buy_only_result(
                run_dir=run_dir,
                business_date=day["business_date"],
                job=job["job"],
                exit_code=completed.returncode,
            )
            if scoped_block:
                job_record["runtime_test_job_status"] = scoped_block["status"]
                job_record["scoped_block_continuation"] = scoped_block
            pm_fatal = _pm_fatal_evidence_for_run(run_dir, completed_business_days={day["business_date"]})
            if pm_fatal:
                job_record["runtime_test_job_status"] = "HALT_PM_POSITION_MANAGEMENT"
                job_record["position_management_halt"] = pm_fatal
            run_state["completed_jobs"].append(job_record)
            write_json_atomic(run_dir / "run_state.json", run_state)
            if pm_fatal:
                _mark_run_halted(run_dir, run_state, job_record)
                raise RuntimeTestError(
                    f"Runtime Test stopped at {run_state['next_job']} because Position Management artifact status is HALT",
                    status="HALT",
                    exit_code=EXIT_HALT,
                )
            if completed.returncode != 0 and not scoped_block:
                _mark_run_halted(run_dir, run_state, job_record)
                raise RuntimeTestError(
                    f"Runtime CLI stopped at {run_state['next_job']} with exit code {completed.returncode}",
                    status="HALT",
                    exit_code=EXIT_HALT,
                )
        run_state["next_job"] = f"{day['business_date']}:strategy_shadow_generation"
        write_json_atomic(run_dir / "run_state.json", run_state)
        shadow_feature_authority = resolve_strategy_shadow_feature_date_authority(
            runtime_root=runtime_root,
            run_state=run_state,
            day=day,
        )
        shadow_summary = generate_strategy_shadow_for_day(
            run_dir=run_dir,
            runtime_root=runtime_root,
            run_id=run_id,
            profile_id=str(profile["profile_id"]),
            business_date=str(day["business_date"]),
            feature_date=str(shadow_feature_authority.get("selected_feature_date") or ""),
            feature_date_authority=shadow_feature_authority,
            historical_evaluation_authority_path=str(historical_authority.get("authority_path") or ""),
            artifact_subdir="strategy_eod_shadow",
            decision_timing="EOD_POST_RUNTIME_OBSERVABILITY_SHADOW",
            authority_role="POST_RUNTIME_OBSERVABILITY_SHADOW",
            materialization_role="LATEST_RUNTIME_STATE_MATERIALIZATION",
        )
        shadow_record = {
            "business_date": day["business_date"],
            "job": "strategy_shadow_generation",
            "exit_code": 0 if not shadow_summary.get("runtime_mutation_performed") else EXIT_HALT,
            "command": ["runtime_test.py", "internal:strategy_shadow_generation"],
            "planned_command": day.get("strategy_shadow_job", {}),
            "runtime_test_job_status": shadow_summary.get("strategy_shadow_judgment", "REVIEW_REQUIRED"),
            "strategy_shadow_summary_path": str(run_dir / "daily" / str(day["business_date"]) / "strategy_eod_shadow" / "strategy_shadow_summary.json"),
            "active_runtime_decision_changed": False,
            "runtime_switch_performed": False,
        }
        run_state["completed_jobs"].append(shadow_record)
        write_json_atomic(run_dir / "run_state.json", run_state)
        if shadow_summary.get("runtime_mutation_performed"):
            _mark_run_halted(run_dir, run_state, shadow_record)
            raise RuntimeTestError("Strategy shadow generation mutated Runtime authority state", status="HALT", exit_code=EXIT_HALT)
        run_state["completed_business_days"].append(day["business_date"])
    run_state["status"] = "COMPLETED"
    run_state["next_job"] = ""
    write_json_atomic(run_dir / "run_state.json", run_state)
    payload = base_payload("run", "PASS")
    payload.update({"run_id": run_id, "evidence_path": str(run_dir), "completed_business_days": run_state["completed_business_days"]})
    return CommandResult("PASS", EXIT_PASS, runner_response(payload))


def validate_command(
    args: argparse.Namespace,
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
) -> CommandResult:
    run_state = load_run_state(evidence_root, args.run_id) if args.run_id else {}
    run_dir = runs_root(evidence_root) / args.run_id if args.run_id else Path()
    completed_days = set(str(day) for day in (run_state.get("completed_business_days") or []))
    pm_fatal = _pm_fatal_evidence_for_run(run_dir, completed_business_days=completed_days) if args.run_id else []
    strategy_validation = validate_run_strategy_shadow(run_dir=run_dir, business_date=args.business_date or None) if args.run_id else {}
    historical_authority_validation = (
        validate_historical_evaluation_authority(
            run_dir=run_dir,
            runtime_root=runtime_root,
            expected=run_state.get("historical_evaluation_authority") if isinstance(run_state.get("historical_evaluation_authority"), dict) else None,
        )
        if args.run_id
        else {"status": "NOT_REQUESTED"}
    )
    checks = {
        "normal_runtime_root": str(runtime_root).endswith(".runtime"),
        "current_exists": (runtime_root / "persistent_ledger" / "state.json").exists(),
        "pending_exists": (runtime_root / "pending_order_plan" / "pending_order_plan.json").exists(),
        "runtime_state_exists": (runtime_root / "runtime_state" / "current_state.json").exists(),
        "external_effect_absence": profile["external_effect_policy"].get("broker_write") is False,
        "run_state_present": bool(run_state) if args.run_id else True,
        "position_management_halt_absent": not pm_fatal,
        "strategy_shadow_structural_validity": strategy_validation.get("structural_validity") == "PASS" if args.run_id else True,
        "historical_evaluation_authority_gate": historical_authority_validation.get("status") == "PASS" if args.run_id else True,
    }
    status_value = "PASS" if all(checks.values()) else "VALIDATION_FAILURE"
    payload = base_payload("validate", status_value)
    payload.update(
        {
            "run_id": args.run_id or "",
            "business_date": args.business_date or "",
            "checks": checks,
            "position_management_halt_evidence": pm_fatal,
            "strategy_shadow_validation": strategy_validation,
            "strategy_shadow_policy_acceptance": strategy_validation.get("policy_acceptance", "NOT_REQUESTED") if strategy_validation else "NOT_REQUESTED",
            "historical_evaluation_authority_validation": historical_authority_validation,
            "state_hashes": state_hashes(runtime_root),
            "repair_performed": False,
        }
    )
    return CommandResult(status_value, EXIT_PASS if status_value == "PASS" else EXIT_VALIDATION_FAILURE, runner_response(payload))


def resume_command(
    args: argparse.Namespace,
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
) -> CommandResult:
    require_historical_mutation_context(args=args, profile=profile)
    run_state = load_run_state(evidence_root, args.run_id)
    if is_run_closed(evidence_root=evidence_root, run_id=str(args.run_id)):
        raise RuntimeTestError(
            f"resume rejected; run is closed: {args.run_id}",
            status="PRECONDITION_FAILURE",
            exit_code=EXIT_PRECONDITION_FAILURE,
        )
    baseline = run_state.get("source_baseline") or {}
    current = source_baseline(runtime_root)
    mismatches = [key for key in ("source_commit", "source_dirty", "registry_hash") if baseline.get(key) != current.get(key)]
    if mismatches:
        raise RuntimeTestError(
            f"resume rejected; baseline changed: {', '.join(mismatches)}",
            status="PRECONDITION_FAILURE",
            exit_code=EXIT_PRECONDITION_FAILURE,
        )
    if args.dry_run:
        payload = base_payload("resume", "DRY_RUN")
        payload.update({"run_id": args.run_id, "resume_allowed": True, "dry_run_no_mutation": True})
        return CommandResult("DRY_RUN", EXIT_PASS, runner_response(payload))
    require_confirm(args)
    run_dir = runs_root(evidence_root) / args.run_id
    plan_path = run_dir / "plan.json"
    if not plan_path.exists():
        raise RuntimeTestError("resume requires the original plan.json", status="PRECONDITION_FAILURE", exit_code=EXIT_PRECONDITION_FAILURE)
    plan_payload = load_plan(plan_path)
    validate_plan_run_id(plan_payload=plan_payload, requested_run_id=args.run_id, plan_path=plan_path)
    validate_plan_entry_gate(
        plan_payload,
        run_dir=run_dir,
        run_state=run_state,
        resume=True,
    )
    historical_authority = run_state.get("historical_evaluation_authority") if isinstance(run_state.get("historical_evaluation_authority"), dict) else {}
    historical_authority_validation = validate_historical_evaluation_authority(
        run_dir=run_dir,
        runtime_root=runtime_root,
        expected=historical_authority,
    )
    if historical_authority_validation["status"] != "PASS":
        raise RuntimeTestError(
            "resume rejected; historical evaluation authority gate failed: "
            + json.dumps(historical_authority_validation, ensure_ascii=False, sort_keys=True),
            status="PRECONDITION_FAILURE",
            exit_code=EXIT_PRECONDITION_FAILURE,
        )
    run_state["historical_evaluation_authority_validation"] = historical_authority_validation
    completed_success = {
        (record.get("business_date"), record.get("job"))
        for record in run_state.get("completed_jobs", [])
        if int(record.get("exit_code", 1)) == 0 or str(record.get("runtime_test_job_status") or "") in SCOPED_BUY_ONLY_JOB_STATUSES
    }
    run_state["status"] = "RUNNING"
    write_json_atomic(run_dir / "run_state.json", run_state)
    for day in plan_payload.get("business_dates", []):
        for job in day.get("jobs", []):
            identity = (day["business_date"], job["job"])
            if identity in completed_success:
                continue
            run_state["next_job"] = f"{day['business_date']}:{job['job']}"
            write_json_atomic(run_dir / "run_state.json", run_state)
            command_resolution = resolve_run_job_command(
                runtime_root=runtime_root,
                job_record=job,
                historical_evaluation_authority=historical_authority,
            )
            command = command_resolution["command"]
            subprocess_trace_path = run_dir / "daily" / day["business_date"] / job["job"] / "subprocess_trace.json"
            completed = _invoke_runtime_cli_job(
                command,
                cwd=Path.cwd(),
                trace_path=subprocess_trace_path,
                context={
                    "run_id": str(args.run_id),
                    "profile_id": str(profile["profile_id"]),
                    "business_date": day["business_date"],
                    "job": job["job"],
                    "runtime_root": str(runtime_root),
                    "evidence_root": str(evidence_root),
                    "source_commit": git_commit(),
                    "source_dirty": source_dirty(),
                    "resumed": True,
                },
            )
            job_record = {
                "business_date": day["business_date"],
                "job": job["job"],
                "exit_code": completed.returncode,
                "command": command,
                "planned_command": job["command"],
                "feature_date_command_resolution": command_resolution["resolution"],
                "resumed": True,
                "subprocess_trace_path": str(subprocess_trace_path),
                "subprocess_trace": getattr(completed, "runtime_test_subprocess_trace", {}),
            }
            collect_runtime_cli_job_evidence(
                completed=completed,
                run_dir=run_dir,
                runtime_root=runtime_root,
                business_date=day["business_date"],
                job=job["job"],
            )
            write_performance_observability_evidence(
                run_dir=run_dir,
                runtime_root=runtime_root,
                run_id=str(args.run_id),
                business_date=day["business_date"],
                job=job["job"],
            )
            scoped_block = classify_scoped_buy_only_result(
                run_dir=run_dir,
                business_date=day["business_date"],
                job=job["job"],
                exit_code=completed.returncode,
            )
            if scoped_block:
                job_record["runtime_test_job_status"] = scoped_block["status"]
                job_record["scoped_block_continuation"] = scoped_block
            pm_fatal = _pm_fatal_evidence_for_run(run_dir, completed_business_days={day["business_date"]})
            if pm_fatal:
                job_record["runtime_test_job_status"] = "HALT_PM_POSITION_MANAGEMENT"
                job_record["position_management_halt"] = pm_fatal
            run_state.setdefault("completed_jobs", []).append(job_record)
            write_json_atomic(run_dir / "run_state.json", run_state)
            if pm_fatal:
                _mark_run_halted(run_dir, run_state, job_record)
                raise RuntimeTestError(
                    f"resume stopped at {run_state['next_job']} because Position Management artifact status is HALT",
                    status="HALT",
                    exit_code=EXIT_HALT,
                )
            if completed.returncode != 0 and not scoped_block:
                _mark_run_halted(run_dir, run_state, job_record)
                raise RuntimeTestError(
                    f"resume stopped at {run_state['next_job']} with exit code {completed.returncode}",
                    status="HALT",
                    exit_code=EXIT_HALT,
                )
        shadow_identity = (day["business_date"], "strategy_shadow_generation")
        if shadow_identity not in completed_success:
            run_state["next_job"] = f"{day['business_date']}:strategy_shadow_generation"
            write_json_atomic(run_dir / "run_state.json", run_state)
            shadow_feature_authority = resolve_strategy_shadow_feature_date_authority(
                runtime_root=runtime_root,
                run_state=run_state,
                day=day,
            )
            shadow_summary = generate_strategy_shadow_for_day(
                run_dir=run_dir,
                runtime_root=runtime_root,
                run_id=str(args.run_id),
                profile_id=str(profile["profile_id"]),
                business_date=str(day["business_date"]),
                feature_date=str(shadow_feature_authority.get("selected_feature_date") or ""),
                feature_date_authority=shadow_feature_authority,
                historical_evaluation_authority_path=str(historical_authority.get("authority_path") or ""),
                artifact_subdir="strategy_eod_shadow",
                decision_timing="EOD_POST_RUNTIME_OBSERVABILITY_SHADOW",
                authority_role="POST_RUNTIME_OBSERVABILITY_SHADOW",
                materialization_role="LATEST_RUNTIME_STATE_MATERIALIZATION",
            )
            shadow_record = {
                "business_date": day["business_date"],
                "job": "strategy_shadow_generation",
                "exit_code": 0 if not shadow_summary.get("runtime_mutation_performed") else EXIT_HALT,
                "command": ["runtime_test.py", "internal:strategy_shadow_generation"],
                "planned_command": day.get("strategy_shadow_job", {}),
                "runtime_test_job_status": shadow_summary.get("strategy_shadow_judgment", "REVIEW_REQUIRED"),
                "strategy_shadow_summary_path": str(run_dir / "daily" / str(day["business_date"]) / "strategy_eod_shadow" / "strategy_shadow_summary.json"),
                "active_runtime_decision_changed": False,
                "runtime_switch_performed": False,
                "resumed": True,
            }
            run_state.setdefault("completed_jobs", []).append(shadow_record)
            write_json_atomic(run_dir / "run_state.json", run_state)
            if shadow_summary.get("runtime_mutation_performed"):
                _mark_run_halted(run_dir, run_state, shadow_record)
                raise RuntimeTestError("Strategy shadow generation mutated Runtime authority state", status="HALT", exit_code=EXIT_HALT)
        if day["business_date"] not in run_state.get("completed_business_days", []):
            run_state.setdefault("completed_business_days", []).append(day["business_date"])
    run_state["status"] = "COMPLETED"
    run_state["next_job"] = ""
    write_json_atomic(run_dir / "run_state.json", run_state)
    payload = base_payload("resume", "PASS")
    payload.update({"run_id": args.run_id, "evidence_path": str(run_dir), "completed_business_days": run_state.get("completed_business_days", [])})
    return CommandResult("PASS", EXIT_PASS, runner_response(payload))


def abandon_command(
    args: argparse.Namespace,
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
) -> CommandResult:
    run_id = str(args.run_id)
    run_state = load_run_state(evidence_root, run_id)
    run_dir = runs_root(evidence_root) / run_id
    current_status = str(run_state.get("status") or "")
    already_abandoned = is_run_abandoned(evidence_root=evidence_root, run_id=run_id)
    active = active_run_for_profile(evidence_root, profile_id=str(profile["profile_id"]))
    active_run = str(active.get("run_id") or "") == run_id
    files_to_create = [
        str(run_dir / "abandonment.json"),
        str(run_dir / "final_summary.json"),
    ]
    payload = base_payload("abandon", "DRY_RUN" if args.dry_run else "ABANDONED")
    payload.update(
        {
            "run_id": run_id,
            "profile_id": profile["profile_id"],
            "current_status": current_status,
            "previous_status": current_status,
            "active_run": active_run,
            "abandonment_possible": current_status == "HALT" or already_abandoned,
            "already_abandoned": already_abandoned,
            "resume_disabled": already_abandoned,
            "files_to_create": files_to_create,
            "files_to_modify": [],
            "evidence_to_preserve": [
                str(run_dir / "run_state.json"),
                str(run_dir / "plan.json"),
                str(run_dir / "daily"),
                str(run_dir / "fresh_run_summary.json"),
            ],
            "trading_state_mutation": False,
            "trading_state_mutated": False,
            "broker_access": False,
            "broker_write": False,
            "external_delivery": False,
            "evidence_preserved": True,
            "run_state_preserved": True,
            "run_state_original_status": current_status,
            "accepted_generation_changed": False,
            "registry_changed": False,
            "state_hashes_before": state_hashes(runtime_root),
        }
    )
    if already_abandoned:
        abandonment = load_abandonment(evidence_root=evidence_root, run_id=run_id)
        payload.update(
            {
                "status": "ABANDONED",
                "final_judgment": "ABANDONED",
                "exit_code": EXIT_PASS,
                "abandoned_at": abandonment.get("abandoned_at") or "",
                "resume_disabled": True,
                "abandonment_path": str(run_dir / "abandonment.json"),
                "final_summary_path": str(run_dir / "final_summary.json"),
                "evidence_path": str(run_dir),
                "state_hashes_after": state_hashes(runtime_root),
            }
        )
        return CommandResult("ABANDONED", EXIT_PASS, runner_response(payload))
    if current_status == "RUNNING":
        if not bool(getattr(args, "allow_stale_running", False)):
            raise RuntimeTestError(
                "abandon rejected; RUNNING run must be halted or stopped before abandon",
                status="PRECONDITION_FAILURE",
                exit_code=EXIT_PRECONDITION_FAILURE,
            )
        interrupted = _mark_running_run_interrupted_halt(
            run_dir=run_dir,
            run_state=run_state,
            reason=str(getattr(args, "reason", "") or "stale_running_abandon"),
        )
        run_state = load_run_state(evidence_root, run_id)
        current_status = str(run_state.get("status") or "")
        payload["current_status"] = current_status
        payload["stale_running_converted_to_halt"] = True
        payload["stale_running_halt_record"] = interrupted
    if current_status != "HALT":
        raise RuntimeTestError(
            f"abandon rejected; run status is not HALT: {current_status}",
            status="PRECONDITION_FAILURE",
            exit_code=EXIT_PRECONDITION_FAILURE,
        )
    if args.dry_run:
        payload.update(
            {
                "dry_run_no_mutation": True,
                "resume_disabled": False,
                "state_hashes_after": payload["state_hashes_before"],
            }
        )
        return CommandResult("DRY_RUN", EXIT_PASS, runner_response(payload))
    require_confirm(args)
    abandon_reason = str(getattr(args, "reason", "") or "operator_abandoned_halt_run")
    abandonment = _write_abandonment_artifacts(
        evidence_root=evidence_root,
        runtime_root=runtime_root,
        profile=profile,
        run_id=run_id,
        run_state=run_state,
        abandon_reason=abandon_reason,
        abandoned_by="operator",
    )
    payload.update(
        {
            "status": "ABANDONED",
            "final_judgment": "ABANDONED",
            "exit_code": EXIT_PASS,
            "abandoned_at": abandonment["abandoned_at"],
            "abandon_reason": abandon_reason,
            "resume_disabled": True,
            "abandonment_path": str(run_dir / "abandonment.json"),
            "final_summary_path": str(run_dir / "final_summary.json"),
            "evidence_path": str(run_dir),
            "state_hashes_after": state_hashes(runtime_root),
        }
    )
    return CommandResult("ABANDONED", EXIT_PASS, runner_response(payload))


def _write_abandonment_artifacts(
    *,
    evidence_root: Path,
    runtime_root: Path,
    profile: dict[str, Any],
    run_id: str,
    run_state: dict[str, Any],
    abandon_reason: str,
    abandoned_by: str,
) -> dict[str, Any]:
    run_dir = runs_root(evidence_root) / run_id
    current_status = str(run_state.get("status") or "")
    abandoned_at = utc_now()
    final_state_snapshot = write_final_state_snapshot(run_dir=run_dir, runtime_root=runtime_root)
    abandonment = {
        "schema_version": "runtime_test_abandonment_v1",
        "run_id": run_id,
        "profile_id": profile["profile_id"],
        "previous_status": current_status,
        "abandoned_at": abandoned_at,
        "abandon_reason": abandon_reason,
        "abandoned_by": abandoned_by,
        "resume_disabled": True,
        "evidence_preserved": True,
        "trading_state_mutated": False,
        "broker_access": False,
        "broker_write": False,
        "external_delivery": False,
        "run_state_path": str(run_dir / "run_state.json"),
        "run_state_preserved": True,
        "run_state_original_status": current_status,
        "halted_at": run_state.get("halted_at") or {},
        "next_job_before_abandon": run_state.get("next_job") or "",
        "completed_business_days_before_abandon": run_state.get("completed_business_days") or [],
        "rollback_evidence_preserved": True,
    }
    final_summary = {
        "schema_version": FINAL_SUMMARY_SCHEMA_VERSION,
        "run_id": run_id,
        "profile_id": profile["profile_id"],
        "status": "ABANDONED",
        "final_judgment": "ABANDONED",
        "test_validity_judgment": "ABANDONED",
        "acceptance_gate_judgment": "ABANDONED",
        "previous_status": current_status,
        "abandoned_at": abandoned_at,
        "abandon_reason": abandon_reason,
        "abandoned_by": abandoned_by,
        "resume_disabled": True,
        "evidence_preserved": True,
        "trading_state_mutated": False,
        "broker_access": False,
        "broker_write": False,
        "external_delivery": False,
        "final_state_hashes": state_hashes(runtime_root),
        "final_state_snapshot": {
            "status": final_state_snapshot.get("status"),
            "manifest_path": str(run_dir / "final_state_snapshot" / "manifest.json"),
        },
        "post_close_lifecycle_recommendation": "start a new fresh-run; this run is not resumable",
    }
    write_json_atomic(run_dir / "abandonment.json", abandonment)
    write_json_atomic(run_dir / "final_summary.json", final_summary)
    return abandonment


def rollback_command(
    args: argparse.Namespace,
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
) -> CommandResult:
    require_historical_mutation_context(args=args, profile=profile)
    backup = load_backup_manifest(evidence_root, args.backup_id)
    payload = base_payload("rollback", "DRY_RUN" if args.dry_run else "PASS")
    payload.update(
        {
            "backup_id": backup["backup_id"],
            "runtime_root": str(runtime_root),
            "all_or_nothing": True,
            "restore_operational_foundation": False,
            "dry_run": bool(args.dry_run),
        }
    )
    if not args.dry_run:
        require_confirm(args)
        restore_from_backup(runtime_root=runtime_root, backup_manifest=backup)
        payload["post_restore_hash"] = directory_hash(runtime_root) if runtime_root.exists() else ""
    return CommandResult(payload["status"], EXIT_PASS, runner_response(payload))


def _strategy_planning_authority_run_summary(run_dir: Path) -> dict[str, Any]:
    daily_root = run_dir / "daily"
    planned_dates = _runtime_test_planned_business_dates(run_dir)
    rows: list[dict[str, Any]] = []
    called_dates: list[str] = []
    missing_dates: list[str] = []
    statuses: list[str] = []
    for business_date in planned_dates:
        evidence_path = daily_root / business_date / "morning" / "strategy_planning_authority_evidence.json"
        payload = read_json_optional(evidence_path)
        details = payload.get("details") if isinstance(payload.get("details"), dict) else payload
        status = str(details.get("status") or payload.get("status") or "NOT_EXECUTED")
        planning_eligibility = str(details.get("planning_consumer_eligibility") or "NOT_EVALUATED")
        called = status != "NOT_EXECUTED" and planning_eligibility != "NOT_EVALUATED"
        if called:
            called_dates.append(business_date)
        else:
            missing_dates.append(business_date)
        statuses.append(status)
        rows.append(
            {
                "business_date": business_date,
                "called": called,
                "status": status,
                "planning_consumer_eligibility": planning_eligibility,
                "strategy_artifact_eligibility": str(details.get("strategy_artifact_eligibility") or ""),
                "pending_item_count": int(details.get("pending_item_count") or 0),
                "pending_path": str(details.get("pending_path") or ""),
                "broker_write_performed": bool(details.get("broker_write_performed")),
                "runtime_switch_performed": bool(details.get("runtime_switch_performed")),
                "legacy_formal_planning_authority_active": bool(details.get("legacy_formal_planning_authority_active", not called)),
                "evidence_path": str(evidence_path),
                "reason": str(details.get("reason") or payload.get("reason") or ""),
                "reason_codes": list(details.get("reason_codes") or []),
            }
        )
    if not planned_dates:
        status = "NOT_EVALUATED"
    elif any(row["status"] in {"BLOCK", "BLOCKED", "HALT"} for row in rows):
        status = "BLOCK"
    elif missing_dates or any(row["status"] in {"REVIEW_REQUIRED", "NOT_EXECUTED"} for row in rows):
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"
    return {
        "schema_version": "runtime_test_strategy_planning_authority_run_summary_v1",
        "status": status,
        "planned_dates": planned_dates,
        "called_dates": called_dates,
        "missing_dates": missing_dates,
        "per_day": rows,
        "planning_consumer_eligibility": "ELIGIBLE" if called_dates and not missing_dates and status == "PASS" else "REVIEW_REQUIRED" if rows else "NOT_EVALUATED",
        "active_runtime_consumer_eligibility": "YES" if called_dates and not missing_dates and status == "PASS" else "NO",
        "legacy_formal_planning_authority_active": bool(missing_dates),
        "broker_write_performed": any(row["broker_write_performed"] for row in rows),
        "runtime_switch_performed": any(row["runtime_switch_performed"] for row in rows),
    }


def _strategy_shadow_blocks_operational_close(strategy_shadow: dict[str, Any]) -> bool:
    shadow_status = str(strategy_shadow.get("strategy_shadow_judgment") or "")
    if shadow_status == "BLOCK":
        return True
    if (
        strategy_shadow.get("broker_write_performed")
        or strategy_shadow.get("runtime_switch_performed")
        or strategy_shadow.get("runtime_mutation_performed")
    ):
        return True
    return False


def _strategy_review_status(strategy_shadow: dict[str, Any]) -> str:
    shadow_status = str(strategy_shadow.get("strategy_shadow_judgment") or "NOT_EVALUATED")
    if shadow_status == "BLOCK":
        return "BLOCK"
    if shadow_status == "REVIEW_REQUIRED" or strategy_shadow.get("review_required_dates"):
        return "REVIEW_REQUIRED"
    if shadow_status == "PASS":
        return "PASS"
    return "NOT_EVALUATED"


def _strategy_shadow_close_review_classification(strategy_shadow: dict[str, Any]) -> str:
    review_status = _strategy_review_status(strategy_shadow)
    if review_status == "BLOCK":
        return "BLOCKING_STRATEGY_SHADOW_INVALIDITY"
    if _strategy_shadow_blocks_operational_close(strategy_shadow):
        return "BLOCKING_STRATEGY_SHADOW_PRODUCTION_CONSUMER_CONFLICT"
    if review_status == "REVIEW_REQUIRED":
        return "NON_MUTATING_STRATEGY_SHADOW_REVIEW_NON_BLOCKING"
    if review_status == "PASS":
        return "PASS"
    return "NOT_EVALUATED"


def _production_planning_authority_gate_status(strategy_authority: dict[str, Any]) -> str:
    if strategy_authority.get("broker_write_performed") or strategy_authority.get("runtime_switch_performed"):
        return "BLOCK"
    authority_status = str(strategy_authority.get("status") or "NOT_EVALUATED")
    if authority_status == "BLOCK":
        return "BLOCK"
    if authority_status in {"REVIEW_REQUIRED", "NOT_EVALUATED"}:
        return "REVIEW_REQUIRED"
    return "PASS"


def _strategy_acceptance_gate_status(*, strategy_shadow: dict[str, Any], strategy_authority: dict[str, Any]) -> str:
    shadow_status = str(strategy_shadow.get("strategy_shadow_judgment") or "")
    if shadow_status == "BLOCK" or _strategy_shadow_blocks_operational_close(strategy_shadow):
        return "BLOCK"
    planning_status = _production_planning_authority_gate_status(strategy_authority)
    if planning_status == "PASS" and _strategy_review_status(strategy_shadow) == "REVIEW_REQUIRED":
        return "REVIEW_REQUIRED"
    return planning_status


def _runtime_summary_contract_payload() -> dict[str, Any]:
    return {
        "schema_version": "runtime_summary_contract.v1",
        "runtime_summary": {
            "authority": "runtime execution completion and state validation",
            "responsibility": "Reports command completion, trading state, accounting state, runtime halt, and runtime execution judgment.",
            "excluded_inputs": ["performance_metrics", "strategy_shadow_diagnostic_review"],
        },
        "performance_summary": {
            "authority": "run-scoped post-hoc performance evidence",
            "responsibility": "Reports return, PnL, drawdown, trade, cash, exposure, and attribution metrics for human review.",
            "strategy_input_allowed": False,
        },
        "lifecycle_summary": {
            "authority": "run-scoped position campaign and realized slice evidence",
            "responsibility": "Reports campaign continuity, fill lineage, realized slice continuity, and open/closed lifecycle status.",
        },
        "review_summary": {
            "authority": "non-blocking evidence review and diagnostic findings",
            "responsibility": "Reports REVIEW_REQUIRED conditions that do not change runtime execution results.",
        },
        "operator_summary": {
            "authority": "close command operator guidance",
            "responsibility": "Reports next operator action and separates rerun/readiness guidance from runtime decisions.",
        },
        "evaluation_summary": {
            "authority": "close/evaluation authority",
            "responsibility": "Separates runtime execution judgment, acceptance gate judgment, and close authority judgment.",
        },
        "performance_toolkit_boundary": {
            "toolkit_reads_run_evidence_only": True,
            "toolkit_changes_runtime_decisions": False,
            "historical_results_used_as_strategy_input": False,
        },
    }


def _close_block_evidence(
    *,
    blocking_reasons: list[str],
    review_reasons: list[str],
    strategy_shadow_classification: str,
    historical_status: str,
    production_planning_judgment: str,
) -> dict[str, Any]:
    if blocking_reasons:
        return {
            "block_rule": "CLOSE_AUTHORITY_BLOCKING_REASON_PRESENT",
            "block_reason": ",".join(blocking_reasons),
            "block_artifact": "final_summary.close_authority_classification",
            "block_evidence": {
                "blocking_reasons": blocking_reasons,
                "strategy_shadow_close_classification": strategy_shadow_classification,
                "historical_evaluation_authority_status": historical_status,
                "production_planning_judgment": production_planning_judgment,
            },
        }
    return {
        "block_rule": "NO_BLOCKING_CLOSE_RULE_TRIGGERED",
        "block_reason": "",
        "block_artifact": "",
        "block_evidence": {
            "blocking_reasons": [],
            "review_reasons": review_reasons,
            "strategy_shadow_close_classification": strategy_shadow_classification,
            "historical_evaluation_authority_status": historical_status,
            "production_planning_judgment": production_planning_judgment,
        },
    }


def _date_integrity_summary(*, run_state: dict[str, Any], historical_authority: dict[str, Any]) -> dict[str, Any]:
    completed_days = [str(day) for day in (run_state.get("completed_business_days") or []) if str(day)]
    evaluation_period = historical_authority.get("evaluation_period") if isinstance(historical_authority.get("evaluation_period"), dict) else {}
    evaluation_days = [str(day) for day in (evaluation_period.get("business_dates") or []) if str(day)]
    selected_days = completed_days or evaluation_days
    return {
        "schema_version": "runtime_summary_date_integrity.v1",
        "status": "PASS" if completed_days == evaluation_days and bool(selected_days) else "REVIEW_REQUIRED",
        "completed_days": len(completed_days),
        "completed_start": completed_days[0] if completed_days else "",
        "completed_end": completed_days[-1] if completed_days else "",
        "summary_business_days": len(selected_days),
        "summary_start": selected_days[0] if selected_days else "",
        "summary_end": selected_days[-1] if selected_days else "",
        "evaluation_business_days": len(evaluation_days),
        "evaluation_start": evaluation_days[0] if evaluation_days else str(evaluation_period.get("date_from") or ""),
        "evaluation_end": evaluation_days[-1] if evaluation_days else str(evaluation_period.get("date_to") or ""),
        "completed_matches_evaluation_period": completed_days == evaluation_days,
        "source": "run_state.completed_business_days + historical_evaluation_authority.evaluation_period.business_dates",
    }


def _candidate_current_from_manifest(path: Path) -> dict[str, Any]:
    payload = read_json_optional(path)
    artifact = payload.get("artifact") if isinstance(payload.get("artifact"), dict) else {}
    current = artifact.get("candidate_current") if isinstance(artifact.get("candidate_current"), dict) else {}
    return current


def _run_scoped_pnl_reconciliation(*, run_dir: Path) -> dict[str, Any]:
    valuation_paths = sorted(run_dir.glob("daily/*/current_valuation_refresh/current_valuation_manifest.json"))
    valuations: list[dict[str, Any]] = []
    for path in valuation_paths:
        current = _candidate_current_from_manifest(path)
        if current:
            valuations.append(
                {
                    "business_date": path.parts[-3],
                    "total_equity": _float(current.get("total_equity")),
                    "realized_pnl_field": _float(current.get("realized_pnl")),
                    "unrealized_pnl": _float(current.get("new_unrealized_pnl") or current.get("unrealized_pnl")),
                    "path": str(path),
                }
            )
    realized_paths = sorted(run_dir.glob("daily/*/execution/realized_slices.json"))
    realized_slices: list[dict[str, Any]] = []
    for path in realized_paths:
        payload = read_json_optional(path)
        for row in payload.get("realized_slices") or []:
            if isinstance(row, dict):
                realized_slices.append({**row, "_artifact_path": str(path)})
    if not valuations:
        return {"schema_version": "runtime_pnl_reconciliation.v1", "status": "REVIEW_REQUIRED", "reason": "valuation_evidence_missing"}
    first = valuations[0]
    last = valuations[-1]
    initial_equity = _float(first["total_equity"]) - _float(first["realized_pnl_field"]) - _float(first["unrealized_pnl"])
    final_equity = _float(last["total_equity"])
    realized = sum(_float(row.get("gross_realized_pnl")) for row in realized_slices)
    unrealized = _float(last["unrealized_pnl"])
    equity_delta = final_equity - initial_equity
    residual = equity_delta - realized - unrealized
    tolerance = 0.01
    return {
        "schema_version": "runtime_pnl_reconciliation.v1",
        "status": "PASS" if abs(residual) <= tolerance else "REVIEW_REQUIRED",
        "canonical_authority": "run_scoped_realized_slices_plus_current_valuation_unrealized_pnl",
        "equation": "equity_delta = realized + unrealized + cash_adjustment + other_adjustment",
        "initial_equity": initial_equity,
        "final_equity": final_equity,
        "equity_delta": equity_delta,
        "realized": realized,
        "unrealized": unrealized,
        "cash_adjustment": 0.0,
        "other_adjustment": residual,
        "legacy_current_realized_pnl_field": _float(last["realized_pnl_field"]),
        "legacy_current_realized_pnl_field_status": "NOT_CANONICAL_NET_REALIZED_PNL_FOR_EVALUATION",
        "realized_slice_count": len(realized_slices),
        "valuation_day_count": len(valuations),
        "first_valuation": first,
        "last_valuation": last,
        "realized_slice_paths": [str(path) for path in realized_paths],
        "tolerance": tolerance,
    }


def _buy_fill_lineage_validation(*, run_dir: Path, run_id: str) -> dict[str, Any]:
    fills: list[dict[str, Any]] = []
    for path in sorted(run_dir.glob("daily/*/execution/fills.json")):
        payload = read_json_optional(path)
        for row in payload.get("fills") or []:
            if isinstance(row, dict) and str(row.get("side") or "").upper() == "BUY":
                fills.append({**row, "_artifact_path": str(path)})
    missing = [
        {
            "business_date": row.get("business_date") or "",
            "symbol": row.get("symbol") or "",
            "execution_id": row.get("execution_id") or "",
            "missing_fields": [
                field
                for field in ("pending_item_id", "order_plan_item_id", "quality_decision_id", "position_campaign_id")
                if str(row.get(field) or "") in {"", "MISSING"}
            ],
            "artifact_path": row.get("_artifact_path") or "",
        }
        for row in fills
        if any(str(row.get(field) or "") in {"", "MISSING"} for field in ("pending_item_id", "order_plan_item_id", "quality_decision_id", "position_campaign_id"))
    ]
    run_state = read_json_optional(run_dir / "run_state.json")
    completed = set(str(day) for day in (run_state.get("completed_business_days") or []) if str(day))
    observability = _load_performance_observability(run_dir=run_dir, run_id=run_id, completed_business_days=completed)
    plans = _collect_order_plan_items(runtime_root=Path(".runtime"), run_dir=run_dir, run_id=run_id, available=False, completed_business_days=completed)
    executions = _run_scoped_executions_from_fills(observability)
    campaign_by_execution = {str(row.get("execution_id") or ""): str(row.get("position_campaign_id") or "") for row in observability.get("fills") or [] if isinstance(row, dict)}
    replayed: list[dict[str, Any]] = []
    for business_date in sorted(completed):
        replayed.extend(
            _build_fill_rows(
                run_id=run_id,
                business_date=business_date,
                executions=executions,
                execution_campaign_ids=campaign_by_execution,
                plans=plans,
            )
        )
    replayed_buys = [row for row in replayed if str(row.get("side") or "").upper() == "BUY"]
    replay_missing = [
        row
        for row in replayed_buys
        if any(str(row.get(field) or "") in {"", "MISSING"} for field in ("pending_item_id", "order_plan_item_id", "quality_decision_id", "position_campaign_id"))
    ]
    return {
        "schema_version": "buy_fill_lineage_validation.v1",
        "status": "PASS" if not replay_missing else "REVIEW_REQUIRED",
        "existing_artifact_status": "PASS" if not missing else "REVIEW_REQUIRED_PRE_REPAIR_ARTIFACT",
        "buy_fill_count": len(fills),
        "missing_lineage_count": len(replay_missing),
        "existing_artifact_missing_lineage_count": len(missing),
        "replayed_buy_fill_count": len(replayed_buys),
        "missing_lineage": missing[:50],
        "replayed_missing_lineage": replay_missing[:50],
        "lineage_fields": ["pending_item_id", "order_plan_item_id", "quality_decision_id", "position_campaign_id"],
        "source": "run_scoped_execution_fills + run_scoped_submit_guard_item_evidence",
        "repair_evidence": "direct_replay_without_runtime_job_execution",
    }


def _close_authority_classification(
    *,
    validation_exit_code: int,
    run_state_status: str,
    pm_fatal: dict[str, Any],
    strategy_shadow: dict[str, Any],
    strategy_authority: dict[str, Any],
    historical_authority_validation: dict[str, Any],
) -> dict[str, Any]:
    validation_passed = validation_exit_code == EXIT_PASS
    trading_state_judgment = "PASS" if validation_passed and not pm_fatal else "REVIEW_REQUIRED"
    accounting_state_judgment = "PASS" if validation_passed and not pm_fatal else "REVIEW_REQUIRED"
    runtime_execution_judgment = "PASS" if run_state_status in {"COMPLETED", "HALT"} else "REVIEW_REQUIRED"
    production_planning_judgment = _production_planning_authority_gate_status(strategy_authority)
    strategy_shadow_review_status = _strategy_review_status(strategy_shadow)
    strategy_shadow_classification = _strategy_shadow_close_review_classification(strategy_shadow)
    historical_status = str(historical_authority_validation.get("status") or "NOT_REQUESTED")

    blocking_reasons: list[str] = []
    review_reasons: list[str] = []
    if trading_state_judgment != "PASS":
        review_reasons.append("trading_state_validation_not_pass")
    if accounting_state_judgment != "PASS":
        review_reasons.append("accounting_state_validation_not_pass")
    if runtime_execution_judgment != "PASS":
        review_reasons.append("runtime_execution_not_completed")
    if historical_status == "BLOCK":
        blocking_reasons.append("historical_evaluation_authority_block")
    if production_planning_judgment == "BLOCK":
        blocking_reasons.append("production_planning_authority_block")
    elif production_planning_judgment != "PASS":
        review_reasons.append("production_planning_authority_not_pass")
    if strategy_shadow_classification.startswith("BLOCKING_"):
        blocking_reasons.append("strategy_shadow_blocking_close_invalidity")
    elif strategy_shadow_classification == "NON_MUTATING_STRATEGY_SHADOW_REVIEW_NON_BLOCKING":
        review_reasons.append("strategy_shadow_review_required_non_blocking")

    if blocking_reasons:
        close_authority_judgment = "BLOCK"
    elif review_reasons:
        close_authority_judgment = "REVIEW_REQUIRED"
    else:
        close_authority_judgment = "PASS"
    final_runtime_judgment = (
        "BLOCK"
        if blocking_reasons
        else "REVIEW_REQUIRED"
        if runtime_execution_judgment != "PASS" or trading_state_judgment != "PASS" or accounting_state_judgment != "PASS"
        else "PASS"
    )
    strategy_shadow_review_required = strategy_shadow_review_status == "REVIEW_REQUIRED"
    operational_status = final_runtime_judgment
    acceptance_gate_judgment = "BLOCK" if blocking_reasons else "REVIEW_REQUIRED" if review_reasons else "PASS"
    block_evidence = _close_block_evidence(
        blocking_reasons=blocking_reasons,
        review_reasons=review_reasons,
        strategy_shadow_classification=strategy_shadow_classification,
        historical_status=historical_status,
        production_planning_judgment=production_planning_judgment,
    )
    return {
        "schema_version": "runtime_test_close_authority_classification_v1",
        "trading_state_judgment": trading_state_judgment,
        "accounting_state_judgment": accounting_state_judgment,
        "runtime_execution_judgment": runtime_execution_judgment,
        "production_planning_judgment": production_planning_judgment,
        "strategy_shadow_judgment": strategy_shadow_review_status,
        "strategy_shadow_review_required": strategy_shadow_review_required,
        "strategy_shadow_close_classification": strategy_shadow_classification,
        "close_authority_judgment": close_authority_judgment,
        "final_runtime_judgment": final_runtime_judgment,
        "acceptance_gate_judgment": acceptance_gate_judgment,
        "operational_status": operational_status,
        "strategy_review_status": strategy_shadow_review_status,
        "blocking_reasons": blocking_reasons,
        "review_reasons": review_reasons,
        **block_evidence,
    }


def _runtime_test_planned_business_dates(run_dir: Path) -> list[str]:
    plan = read_json_optional(run_dir / "plan.json")
    return [str(day.get("business_date") or "") for day in plan.get("business_dates", []) if isinstance(day, dict)]


def close_command(
    args: argparse.Namespace,
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
) -> CommandResult:
    run_state = load_run_state(evidence_root, args.run_id)
    validation = validate_command(argparse.Namespace(run_id=args.run_id, business_date="", json=False), profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    run_dir = runs_root(evidence_root) / args.run_id
    completed_days = set(str(day) for day in (run_state.get("completed_business_days") or []))
    pm_fatal = _pm_fatal_evidence_for_run(run_dir, completed_business_days=completed_days)
    status_value = "PASS" if validation.exit_code == EXIT_PASS and not pm_fatal and run_state.get("status") in {"COMPLETED", "HALT"} else "REVIEW_REQUIRED"
    final_state_snapshot = write_final_state_snapshot(run_dir=run_dir, runtime_root=runtime_root)
    strategy_shadow = update_run_strategy_shadow_indexes(run_dir=run_dir)
    strategy_authority = _strategy_planning_authority_run_summary(run_dir)
    halt_summary = _runtime_halt_summary(run_dir)
    historical_authority = read_json_optional(run_dir / "historical_evaluation_authority.json")
    historical_authority_validation = validate_historical_evaluation_authority(
        run_dir=run_dir,
        runtime_root=runtime_root,
        expected=historical_authority,
    ) if historical_authority else {"status": "NOT_REQUESTED"}
    close_authority = _close_authority_classification(
        validation_exit_code=validation.exit_code,
        run_state_status=str(run_state.get("status") or ""),
        pm_fatal=pm_fatal,
        strategy_shadow=strategy_shadow,
        strategy_authority=strategy_authority,
        historical_authority_validation=historical_authority_validation,
    )
    date_integrity = _date_integrity_summary(run_state=run_state, historical_authority=historical_authority)
    pnl_reconciliation = _run_scoped_pnl_reconciliation(run_dir=run_dir)
    buy_fill_lineage = _buy_fill_lineage_validation(run_dir=run_dir, run_id=args.run_id)
    runtime_summary_contract = _runtime_summary_contract_payload()
    status_value = str(close_authority["close_authority_judgment"])
    final_runtime_judgment = str(close_authority["final_runtime_judgment"])
    acceptance_gate_judgment = str(close_authority["acceptance_gate_judgment"])
    summary = {
        "schema_version": FINAL_SUMMARY_SCHEMA_VERSION,
        "run_id": args.run_id,
        "profile_id": profile["profile_id"],
        "status": status_value,
        "runtime_status": run_state.get("status") or "",
        "operational_status": close_authority["operational_status"],
        "strategy_review_status": close_authority["strategy_review_status"],
        "final_runtime_judgment": final_runtime_judgment,
        "final_judgment": status_value,
        "runtime_judgment": final_runtime_judgment,
        "block_rule": close_authority["block_rule"],
        "block_reason": close_authority["block_reason"],
        "block_artifact": close_authority["block_artifact"],
        "block_evidence": close_authority["block_evidence"],
        "halt_summary": halt_summary,
        "test_validity_judgment": "VALID" if acceptance_gate_judgment == "PASS" else acceptance_gate_judgment,
        "acceptance_gate_judgment": acceptance_gate_judgment,
        "close_authority_judgment": close_authority["close_authority_judgment"],
        "close_authority_classification": close_authority,
        "runtime_summary_contract": runtime_summary_contract,
        "runtime_summary": {
            "schema_version": "runtime_summary.v1",
            "runtime_status": run_state.get("status") or "",
            "runtime_execution_judgment": close_authority["runtime_execution_judgment"],
            "trading_state_judgment": close_authority["trading_state_judgment"],
            "accounting_state_judgment": close_authority["accounting_state_judgment"],
            "halt_status": halt_summary.get("status"),
            "performance_metrics_used": False,
        },
        "performance_summary": {
            "schema_version": "runtime_performance_summary_reference.v1",
            "authority": "performance_report_when_generated_or_run_scoped_evaluation_integrity",
            "pnl_reconciliation_status": pnl_reconciliation.get("status"),
            "strategy_input_added": False,
            "historical_result_used_as_strategy_input": False,
        },
        "lifecycle_summary": {
            "schema_version": "runtime_lifecycle_summary.v1",
            "buy_fill_lineage_status": buy_fill_lineage.get("status"),
            "buy_fill_count": buy_fill_lineage.get("buy_fill_count", 0),
            "buy_fill_missing_lineage_count": buy_fill_lineage.get("missing_lineage_count", 0),
        },
        "review_summary": {
            "schema_version": "runtime_review_summary.v1",
            "review_reasons": close_authority["review_reasons"],
            "strategy_review_required_dates": strategy_shadow.get("review_required_dates", []),
            "non_blocking_review": not bool(close_authority["blocking_reasons"]) and bool(close_authority["review_reasons"]),
        },
        "operator_summary": {
            "schema_version": "runtime_operator_summary.v1",
            "close_action": "review_non_blocking_evidence" if status_value == "REVIEW_REQUIRED" else "runtime_close_blocked" if status_value == "BLOCK" else "run_closed",
            "post_close_lifecycle_recommendation": "validate evidence, then explicitly rollback or transition by separate command",
        },
        "evaluation_summary": {
            "schema_version": "runtime_evaluation_summary.v1",
            "runtime_execution_judgment": close_authority["runtime_execution_judgment"],
            "final_runtime_judgment": final_runtime_judgment,
            "acceptance_gate_judgment": acceptance_gate_judgment,
            "close_authority_judgment": status_value,
            "block_rule": close_authority["block_rule"],
            "block_reason": close_authority["block_reason"],
            "performance_gate_judgment": "NOT_APPLIED",
        },
        "date_integrity": date_integrity,
        "business_days": date_integrity["summary_business_days"],
        "start": date_integrity["summary_start"],
        "end": date_integrity["summary_end"],
        "completed_days": date_integrity["completed_days"],
        "pnl_reconciliation": pnl_reconciliation,
        "buy_fill_lineage_validation": buy_fill_lineage,
        "position_management_halt_evidence": pm_fatal,
        "final_state_hashes": state_hashes(runtime_root),
        "final_state_snapshot": {
            "status": final_state_snapshot.get("status"),
            "manifest_path": str(run_dir / "final_state_snapshot" / "manifest.json"),
        },
        "strategy_shadow_judgment": strategy_shadow.get("strategy_shadow_judgment", "REVIEW_REQUIRED"),
        "strategy_shadow_review_required": close_authority["strategy_shadow_review_required"],
        "strategy_shadow_close_classification": close_authority["strategy_shadow_close_classification"],
        "strategy_dates_generated": strategy_shadow.get("business_dates_generated", []),
        "strategy_review_required_dates": strategy_shadow.get("review_required_dates", []),
        "strategy_blocked_dates": strategy_shadow.get("blocked_dates", []),
        "strategy_artifact_completeness": "PASS" if not strategy_shadow.get("missing_dates") else "REVIEW_REQUIRED",
        "strategy_lineage_completeness": strategy_shadow.get("lineage_validation", "REVIEW_REQUIRED"),
        "strategy_consumer_eligibility": strategy_shadow.get("shadow_consumer_eligibility", "REVIEW_REQUIRED"),
        "strategy_planning_authority": strategy_authority,
        "strategy_planning_authority_status": strategy_authority.get("status", "NOT_EVALUATED"),
        "strategy_planning_authority_dates_called": strategy_authority.get("called_dates", []),
        "strategy_planning_authority_dates_missing": strategy_authority.get("missing_dates", []),
        "strategy_planning_authority_acceptance": close_authority["production_planning_judgment"],
        "production_planning_judgment": close_authority["production_planning_judgment"],
        "trading_state_judgment": close_authority["trading_state_judgment"],
        "accounting_state_judgment": close_authority["accounting_state_judgment"],
        "runtime_execution_judgment": close_authority["runtime_execution_judgment"],
        "historical_evaluation_authority": historical_authority,
        "historical_evaluation_authority_validation": historical_authority_validation,
        "evaluation_mode": str(historical_authority.get("evaluation_mode") or ""),
        "training_cutoff": historical_authority.get("training_cutoff") if isinstance(historical_authority.get("training_cutoff"), dict) else {},
        "evaluation_period": historical_authority.get("evaluation_period") if isinstance(historical_authority.get("evaluation_period"), dict) else {},
        "training_overlap": historical_authority.get("training_overlap") if isinstance(historical_authority.get("training_overlap"), dict) else {},
        "planning_consumer_eligibility": strategy_authority.get("planning_consumer_eligibility", "NOT_EVALUATED"),
        "active_runtime_consumer_eligibility": strategy_authority.get("active_runtime_consumer_eligibility", "NO"),
        "legacy_formal_planning_authority_active": bool(strategy_authority.get("legacy_formal_planning_authority_active")),
        "legacy_authority_active": bool(strategy_shadow.get("legacy_authority_active")),
        "legacy_authority_active_semantics": "legacy_shadow_preservation_marker_not_formal_planning_authority",
        "closed_at": utc_now(),
        "post_close_lifecycle_recommendation": "validate evidence, then explicitly rollback or transition by separate command",
    }
    run_dir = runs_root(evidence_root) / args.run_id
    write_json_atomic(run_dir / "final_summary.json", summary)
    payload = base_payload("close", status_value)
    payload.update(summary)
    payload["runtime_test_final_summary_schema_version"] = summary["schema_version"]
    return CommandResult(status_value, EXIT_PASS if status_value == "PASS" else EXIT_REVIEW_REQUIRED, runner_response(payload))


def fresh_run_command(
    args: argparse.Namespace,
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
) -> CommandResult:
    require_historical_mutation_context(args=args, profile=profile)
    fresh_run_id = f"fresh-run-{profile['profile_id']}-{timestamp_id()}"
    started_at = utc_now()
    before = _fresh_run_authority_snapshot(runtime_root)
    plan_namespace = plan_namespace_from_fresh_run(args)
    plan_namespace_contract = validate_plan_namespace(plan_namespace)
    plan_preview = build_plan(
        profile=profile,
        runtime_root=runtime_root,
        evidence_root=evidence_root,
        business_days=plan_namespace.business_days,
        start_date=plan_namespace.start_date,
        date_from=plan_namespace.date_from,
        date_to=plan_namespace.date_to,
        run_id=plan_namespace.run_id,
    )
    dry_run_plan_request_contract = {
        **plan_namespace_contract,
        "plan_request_construction": "PASS",
        "runtime_test_run_id_generated_by": "plan",
        "fresh_run_id_is_runtime_test_run_id": False,
        "backup_id_is_runtime_test_run_id": False,
        "generated_runtime_test_run_id": plan_preview["run_id"],
        "fresh_run_id": fresh_run_id,
    }
    active = active_run_for_profile(evidence_root, profile_id=str(profile["profile_id"]))
    if args.dry_run:
        payload = _fresh_run_summary(
            fresh_run_id=fresh_run_id,
            profile=profile,
            runtime_root=runtime_root,
            evidence_root=evidence_root,
            started_at=started_at,
            status="DRY_RUN",
            exit_code=EXIT_PASS,
            steps=_fresh_run_dry_run_steps(profile=profile, runtime_root=runtime_root, evidence_root=evidence_root, plan_payload=plan_preview),
            backup_id="",
            run_id=plan_preview["run_id"],
            plan_payload=plan_preview,
            initial_cash=args.initial_cash,
            before=before,
            after=before,
            failed_step="",
            error="",
            active_run=active,
            dry_run=True,
        )
        payload["plan_request_contract"] = dry_run_plan_request_contract
        payload["steps"]["plan"]["summary"]["plan_request_construction"] = "PASS"
        payload["steps"]["plan"]["summary"]["namespace_contract"] = plan_namespace_contract
        return CommandResult("DRY_RUN", EXIT_PASS, runner_response(payload))
    require_confirm(args)
    if active:
        payload = _fresh_run_summary(
            fresh_run_id=fresh_run_id,
            profile=profile,
            runtime_root=runtime_root,
            evidence_root=evidence_root,
            started_at=started_at,
            status="PRECONDITION_FAILURE",
            exit_code=EXIT_PRECONDITION_FAILURE,
            steps=_initial_fresh_run_steps(),
            backup_id="",
            run_id="",
            plan_payload=plan_preview,
            initial_cash=args.initial_cash,
            before=before,
            after=_fresh_run_authority_snapshot(runtime_root),
            failed_step="status",
            error=f"active run exists for profile {profile['profile_id']}: {active.get('run_id')}",
            active_run=active,
            dry_run=False,
        )
        _persist_fresh_run_summary(evidence_root=evidence_root, run_id="", fresh_run_id=fresh_run_id, payload=payload)
        return CommandResult(payload["status"], payload["exit_code"], runner_response(payload))
    steps = _initial_fresh_run_steps()
    backup_id = ""
    run_id = ""
    plan_payload: dict[str, Any] = plan_preview
    failed_step = ""
    error = ""

    def execute(name: str, func) -> CommandResult:
        nonlocal failed_step, error
        try:
            result = func()
        except RuntimeTestError as exc:
            steps[name] = _fresh_step(name, exc.status, {"error": str(exc), "exit_code": exc.exit_code})
            failed_step = name
            error = str(exc)
            raise
        except Exception as exc:
            steps[name] = _fresh_step(name, "INTERNAL_ERROR", {"error": str(exc), "exit_code": EXIT_INTERNAL_ERROR})
            failed_step = name
            error = str(exc)
            raise RuntimeTestError(str(exc), status="INTERNAL_ERROR", exit_code=EXIT_INTERNAL_ERROR) from exc
        steps[name] = _fresh_step(name, result.status, result.payload)
        if result.exit_code != EXIT_PASS:
            failed_step = name
            error = str(result.payload.get("error") or result.payload.get("reason") or f"{name} returned {result.status}")
            raise RuntimeTestError(error, status=result.status, exit_code=result.exit_code)
        return result

    exit_code = EXIT_PASS
    final_status = "PASS"
    try:
        execute("status", lambda: status(profile=profile, runtime_root=runtime_root, evidence_root=evidence_root))
        backup_result = execute(
            "backup",
            lambda: backup_command(
                argparse.Namespace(dry_run=False, confirm=True, explicit_mutation_confirm=True),
                profile=profile,
                runtime_root=runtime_root,
                evidence_root=evidence_root,
            ),
        )
        backup_id = str(backup_result.payload.get("backup_id") or "")
        reset_result = execute(
            "reset",
            lambda: reset_command(
                argparse.Namespace(
                    dry_run=False,
                    confirm=True,
                    explicit_mutation_confirm=True,
                    backup_id=backup_id,
                    initial_cash=args.initial_cash,
                    initial_position_state_date=str(plan_preview.get("requested_start_date") or ""),
                ),
                profile=profile,
                runtime_root=runtime_root,
                evidence_root=evidence_root,
            ),
        )
        if not (reset_result.payload.get("clean_state_invariant") or {}).get("passes"):
            failed_step = "reset"
            error = "reset clean-state invariant failed"
            raise RuntimeTestError("reset clean-state invariant failed", status="VALIDATION_FAILURE", exit_code=EXIT_VALIDATION_FAILURE)
        plan_result = execute(
            "plan",
            lambda: plan_command(plan_namespace, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root),
        )
        plan_payload = dict(plan_result.payload)
        run_id = str(plan_payload.get("run_id") or "")
        if not run_id:
            failed_step = "plan"
            error = "plan did not generate runtime test run_id"
            raise RuntimeTestError(error, status="PRECONDITION_FAILURE", exit_code=EXIT_PRECONDITION_FAILURE)
        execute(
            "run",
            lambda: run_command(
                argparse.Namespace(
                    dry_run=False,
                    confirm=True,
                    explicit_mutation_confirm=True,
                    run_id=run_id,
                    business_days=None,
                    start_date=None,
                    date_from=None,
                    date_to=None,
                    auto_prepare=False,
                ),
                profile=profile,
                runtime_root=runtime_root,
                evidence_root=evidence_root,
            ),
        )
        execute(
            "validate",
            lambda: validate_command(
                argparse.Namespace(run_id=run_id, business_date="", json=False),
                profile=profile,
                runtime_root=runtime_root,
                evidence_root=evidence_root,
            ),
        )
        execute(
            "close",
            lambda: close_command(
                argparse.Namespace(run_id=run_id, json=False),
                profile=profile,
                runtime_root=runtime_root,
                evidence_root=evidence_root,
            ),
        )
    except RuntimeTestError as exc:
        exit_code = exc.exit_code
        final_status = exc.status
        if not failed_step:
            failed_step = "fresh-run"
            error = str(exc)
    except KeyboardInterrupt as exc:
        exit_code = 130
        final_status = "HALT"
        if not failed_step:
            failed_step = "run" if run_id else "fresh-run"
        error = "fresh-run interrupted by operator"
        if run_id:
            run_dir = runs_root(evidence_root) / run_id
            run_state = read_json_optional(run_dir / "run_state.json")
            if str(run_state.get("status") or "") == "RUNNING":
                _mark_running_run_interrupted_halt(
                    run_dir=run_dir,
                    run_state=run_state,
                    reason="operator_interrupt",
                    exit_code=exit_code,
                )
        steps.setdefault(failed_step, _fresh_step(failed_step, "HALT", {"error": error, "exit_code": exit_code}))
    after = _fresh_run_authority_snapshot(runtime_root)
    payload = _fresh_run_summary(
        fresh_run_id=fresh_run_id,
        profile=profile,
        runtime_root=runtime_root,
        evidence_root=evidence_root,
        started_at=started_at,
        status=final_status,
        exit_code=exit_code,
        steps=steps,
        backup_id=backup_id,
        run_id=run_id,
        plan_payload=plan_payload,
        initial_cash=args.initial_cash,
        before=before,
        after=after,
        failed_step=failed_step,
        error=error,
        active_run=active,
        dry_run=False,
    )
    if run_id:
        payload["halt_summary"] = _runtime_halt_summary(runs_root(evidence_root) / run_id)
    payload["auto_abandon"] = _maybe_auto_abandon_fresh_run(
        args=args,
        profile=profile,
        runtime_root=runtime_root,
        evidence_root=evidence_root,
        run_id=run_id,
        final_status=final_status,
        exit_code=exit_code,
    )
    if payload["auto_abandon"].get("performed"):
        payload["resume_possible"] = False
        payload["resume_recommendation"] = "Run was automatically abandoned after fresh-run error; start a new fresh-run after reviewing evidence."
        payload["recommended_command"] = "PYTHONPATH=src python3 scripts/runtime_test.py status"
    payload["plan_request_contract"] = {
        **plan_namespace_contract,
        "plan_request_construction": "PASS",
        "runtime_test_run_id_generated_by": "plan",
        "fresh_run_id_is_runtime_test_run_id": False,
        "backup_id_is_runtime_test_run_id": False,
        "generated_runtime_test_run_id": run_id or plan_preview["run_id"],
        "fresh_run_id": fresh_run_id,
        "backup_id": backup_id,
    }
    summary_path = _persist_fresh_run_summary(evidence_root=evidence_root, run_id=run_id, fresh_run_id=fresh_run_id, payload=payload)
    payload["evidence_path"] = str(summary_path.parent)
    payload["fresh_run_summary_path"] = str(summary_path)
    return CommandResult(final_status, exit_code, runner_response(payload))


def _maybe_auto_abandon_fresh_run(
    *,
    args: argparse.Namespace,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
    run_id: str,
    final_status: str,
    exit_code: int,
) -> dict[str, Any]:
    requested = bool(getattr(args, "auto_abandon_on_error", False))
    result = {
        "requested": requested,
        "performed": False,
        "reason": "",
        "run_id": run_id,
        "fresh_run_status": final_status,
        "fresh_run_exit_code": exit_code,
        "abandonment_path": "",
        "final_summary_path": "",
    }
    if not requested:
        result["reason"] = "not_requested"
        return result
    if final_status in {"PASS", "DRY_RUN"} or exit_code == EXIT_PASS:
        result["reason"] = "fresh_run_completed_without_error"
        return result
    if not run_id:
        result["reason"] = "no_run_id_created"
        return result
    try:
        run_state = load_run_state(evidence_root, run_id)
    except Exception as exc:
        result["reason"] = f"run_state_unavailable:{type(exc).__name__}"
        result["error"] = str(exc)
        return result
    run_status = str(run_state.get("status") or "")
    result["run_state_status"] = run_status
    if is_run_abandoned(evidence_root=evidence_root, run_id=run_id):
        result.update(
            {
                "performed": False,
                "reason": "already_abandoned",
                "abandonment_path": str(runs_root(evidence_root) / run_id / "abandonment.json"),
                "final_summary_path": str(runs_root(evidence_root) / run_id / "final_summary.json"),
            }
        )
        return result
    if run_status != "HALT":
        result["reason"] = f"run_state_not_halt:{run_status or '<missing>'}"
        return result
    abandon_reason = str(getattr(args, "auto_abandon_reason", "") or "fresh_run_auto_abandon_on_error")
    try:
        abandonment = _write_abandonment_artifacts(
            evidence_root=evidence_root,
            runtime_root=runtime_root,
            profile=profile,
            run_id=run_id,
            run_state=run_state,
            abandon_reason=abandon_reason,
            abandoned_by="fresh-run",
        )
    except Exception as exc:
        result["reason"] = f"auto_abandon_failed:{type(exc).__name__}"
        result["error"] = str(exc)
        return result
    result.update(
        {
            "performed": True,
            "reason": "halt_run_abandoned_after_fresh_run_error",
            "abandon_reason": abandon_reason,
            "abandoned_at": abandonment.get("abandoned_at") or "",
            "resume_disabled": True,
            "abandonment_path": str(runs_root(evidence_root) / run_id / "abandonment.json"),
            "final_summary_path": str(runs_root(evidence_root) / run_id / "final_summary.json"),
        }
    )
    return result


def show(args: argparse.Namespace) -> CommandResult:
    if args.backup_id:
        path = BACKUP_ROOT / args.backup_id / "backup_manifest.json"
    elif args.run_id:
        if str(getattr(args, "artifact", "") or "") == "strategy":
            run_dir = RUNS_ROOT / args.run_id
            if getattr(args, "business_date", ""):
                path = run_dir / "daily" / str(args.business_date) / "strategy" / "strategy_shadow_summary.json"
                payload = read_json(path)
                manifest_path = run_dir / "daily" / str(args.business_date) / "strategy" / "source_manifest.json"
                if manifest_path.is_file():
                    payload = {**payload, "source_manifest": read_json(manifest_path), "source_manifest_path": str(manifest_path)}
                return CommandResult("PASS", EXIT_PASS, runner_response(payload))
            else:
                path = run_dir / "strategy_shadow_summary.json"
                if not path.is_file():
                    update_run_strategy_shadow_indexes(run_dir=run_dir)
            payload = read_json(path)
            return CommandResult("PASS", EXIT_PASS, runner_response(payload))
        if str(getattr(args, "artifact", "") or "") == "run":
            run_dir = RUNS_ROOT / args.run_id
            payload = read_json(run_dir / "run_state.json")
            payload["halt_summary"] = _runtime_halt_summary(run_dir)
            return CommandResult("PASS", EXIT_PASS, runner_response(payload))
        path = RUNS_ROOT / args.run_id / "run_state.json"
    else:
        raise RuntimeTestError("show requires --run-id or --backup-id", status="INVALID_ARGUMENT", exit_code=EXIT_INVALID_ARGUMENT)
    payload = read_json(path)
    return CommandResult("PASS", EXIT_PASS, runner_response(payload))


def list_runs() -> CommandResult:
    runs = []
    if RUNS_ROOT.exists():
        for path in sorted(RUNS_ROOT.iterdir()):
            if path.is_dir():
                state_path = path / "run_state.json"
                state = read_json(state_path) if state_path.exists() else {"run_id": path.name, "status": "UNKNOWN"}
                runs.append({"run_id": state.get("run_id", path.name), "status": state.get("status", "UNKNOWN")})
    payload = base_payload("list-runs", "PASS")
    payload["runs"] = runs
    return CommandResult("PASS", EXIT_PASS, runner_response(payload))


def list_backups() -> CommandResult:
    backups = []
    if BACKUP_ROOT.exists():
        for path in sorted(BACKUP_ROOT.iterdir()):
            manifest_path = path / "backup_manifest.json"
            if manifest_path.exists():
                manifest = read_json(manifest_path)
                backups.append(
                    {
                        "backup_id": manifest.get("backup_id", path.name),
                        "created_at": manifest.get("created_at", ""),
                        "bundle_hash": manifest.get("bundle_hash", ""),
                    }
                )
    payload = base_payload("list-backups", "PASS")
    payload["backups"] = backups
    return CommandResult("PASS", EXIT_PASS, runner_response(payload))


def build_plan(
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
    business_days: int | None,
    start_date: str | None,
    date_from: str | None,
    date_to: str | None,
    run_id: str | None = None,
) -> dict[str, Any]:
    window = resolve_business_window(
        profile=profile,
        runtime_root=runtime_root,
        business_days=business_days,
        start_date=start_date,
        date_from=date_from,
        date_to=date_to,
    )
    dates = list(window["resolved_business_dates"])
    final_run_id = run_id or f"runtime-test-{profile['profile_id']}-{timestamp_id()}"
    preflight_start_date = dates[0] if dates else str(window.get("requested_start_date") or "")
    strategy_source_preflight = build_historical_strategy_preflight(
        runtime_root=runtime_root,
        requested_start_date=preflight_start_date,
        requested_business_days=int(window["requested_business_days"]),
        requested_dates=dates,
    ) if preflight_start_date else {}
    source_blocked_dates = list(strategy_source_preflight.get("blocked_dates") or [])
    if not source_blocked_dates and not dates:
        source_blocked_dates = list(window.get("unresolved_requested_dates") or [])
    first_eligible_start = str(strategy_source_preflight.get("first_eligible_start_date") or "") if strategy_source_preflight else ""
    source_readiness = {
        "schema_version": "runtime_test_plan_source_readiness_v1",
        "requested_start_date": window["requested_start_date"],
        "requested_end_date": window["requested_end_date"],
        "requested_business_days": int(window["requested_business_days"]),
        "resolved_business_dates": dates,
        "required_warmup_start": str(strategy_source_preflight.get("required_warmup_start") or window["requested_start_date"]) if strategy_source_preflight else window["requested_start_date"],
        "eligible_dates": list(strategy_source_preflight.get("eligible_dates") or []) if strategy_source_preflight else [],
        "blocked_dates": source_blocked_dates,
        "first_eligible_start_date": first_eligible_start or None,
        "operator_ready": bool(strategy_source_preflight.get("operator_ready")) if strategy_source_preflight else False,
        "root_blockers": list(strategy_source_preflight.get("root_blockers") or []) if strategy_source_preflight else ["calendar_readiness"],
        "calendar_readiness": {
            "status": window["window_resolution_status"],
            "reason": window["window_resolution_reason"],
            "calendar_max_date": window["calendar_max_date"],
            "unresolved_requested_dates": list(window["unresolved_requested_dates"]),
        },
        "market_readiness": dict(strategy_source_preflight.get("market_coverage") or {}) if strategy_source_preflight else {},
        "listed_readiness": dict(strategy_source_preflight.get("listed_coverage") or {}) if strategy_source_preflight else {},
        "sector_readiness": dict(strategy_source_preflight.get("sector_coverage") or {}) if strategy_source_preflight else {},
        "corporate_event_readiness": dict(strategy_source_preflight.get("corporate_event_coverage") or {}) if strategy_source_preflight else {},
        "candidate_readiness": dict(strategy_source_preflight.get("candidate_generation_readiness") or {}) if strategy_source_preflight else {},
        "opportunity_readiness": dict(strategy_source_preflight.get("opportunity_generation_readiness") or {}) if strategy_source_preflight else {},
    }
    days = []
    for business_date in dates:
        feature = resolve_feature_date(profile=profile, runtime_root=runtime_root, business_date=business_date)
        jobs = []
        for job in profile["job_sequence"]:
            jobs.append(
                {
                    "job": job,
                    "business_date": business_date,
                    "feature_date": feature["selected_feature_date"] if job in FEATURE_DATE_JOBS else "",
                    "evaluation_time": f"{business_date}T{profile['evaluation_times'][job]}",
                    "submit_enabled": job in SUBMIT_ENABLED_JOBS,
                    "command": runtime_cli_command(
                        profile=profile,
                        runtime_root=runtime_root,
                        business_date=business_date,
                        feature_date=feature["selected_feature_date"] if job in FEATURE_DATE_JOBS else "",
                        evaluation_time=f"{business_date}T{profile['evaluation_times'][job]}",
                        job=job,
                        run_id=final_run_id,
                        evidence_root=evidence_root,
                    ),
                }
            )
        days.append(
            {
                "business_date": business_date,
                "feature_date": feature["selected_feature_date"],
                "carryover": feature["selected_feature_date"] != business_date,
                "feature_date_evidence": feature,
                "jobs": jobs,
                "strategy_shadow_job": strategy_shadow_job_descriptor(
                    run_dir=runs_root(evidence_root) / final_run_id,
                    business_date=business_date,
                ),
            }
        )
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "run_id": final_run_id,
        "profile_id": profile["profile_id"],
        "profile_hash": semantic_hash(profile),
        "requested_start_date": window["requested_start_date"],
        "requested_end_date": window["requested_end_date"],
        "profile_start_date": window["profile_start_date"],
        "selected_start_date": window["selected_start_date"],
        "selection_authority": window["selection_authority"],
        "override_applied": window["override_applied"],
        "override_reason": window["override_reason"],
        "requested_business_days": int(window["requested_business_days"]),
        "requested_window": dict(window["requested_window"]),
        "resolved_business_dates": dates,
        "resolved_business_day_count": len(dates),
        "resolved_date_from": dates[0] if dates else "",
        "resolved_date_to": dates[-1] if dates else "",
        "window_resolution_status": window["window_resolution_status"],
        "window_resolution_reason": window["window_resolution_reason"],
        "calendar_authority": dict(window["calendar_authority"]),
        "calendar_max_date": window["calendar_max_date"],
        "unresolved_requested_dates": list(window["unresolved_requested_dates"]),
        "required_warmup_start": source_readiness["required_warmup_start"],
        "eligible_dates": source_readiness["eligible_dates"],
        "blocked_dates": source_readiness["blocked_dates"],
        "first_eligible_start_date": source_readiness["first_eligible_start_date"],
        "operator_ready": source_readiness["operator_ready"],
        "root_blockers": source_readiness["root_blockers"],
        "source_readiness": source_readiness,
        "calendar_readiness": source_readiness["calendar_readiness"],
        "market_readiness": source_readiness["market_readiness"],
        "listed_readiness": source_readiness["listed_readiness"],
        "sector_readiness": source_readiness["sector_readiness"],
        "corporate_event_readiness": source_readiness["corporate_event_readiness"],
        "candidate_readiness": source_readiness["candidate_readiness"],
        "opportunity_readiness": source_readiness["opportunity_readiness"],
        "request_conformance_status": "PASS" if window["window_resolution_status"] == "PASS" else "NOT_PASS",
        "environment_id": f"{profile['mode']}:{profile['broker_environment']}",
        "runtime_root": str(runtime_root),
        "business_dates": days,
        "job_sequence": profile["job_sequence"],
        "strategy_shadow": {
            "enabled": True,
            "execution_order": "runtime_test_evidence_after_daily_runtime_jobs",
            "metadata_classification": "read_only_runtime_test_evidence_job",
            "source_preflight": strategy_source_preflight,
            "operator_ready": bool(strategy_source_preflight.get("operator_ready")) if strategy_source_preflight else False,
            "first_eligible_start_date": first_eligible_start or None,
            "components": [
                "market_context",
                "corporate_event",
                "portfolio_policy",
                "dynamic_position_count",
                "dynamic_cash_exposure",
                "portfolio_construction",
                "position_sizing",
                "position_management",
                "capital_deployment",
                "runtime_planning",
                "strategy_decision_trace",
            ],
            "mutation_policy": "read_only_no_pending_ledger_current_registry_or_accepted_generation_mutation",
            "active_runtime_consumer_eligibility": "NO",
            "runtime_switch_performed": False,
            "active_runtime_strategy_consumer": "runtime_v2.planning.strategy_authority.activate_strategy_planning_authority",
            "active_runtime_strategy_consumer_job": "morning",
            "active_runtime_strategy_consumer_contract": "production_demo_historical_common_morning_strategy_planning_authority",
            "legacy_lifecycle_active": False,
        },
        "initial_state": profile["initial_state"],
        "reset_scope": list(RESETTABLE_RELATIVE_PATHS),
        "excluded_scope": list(RESET_EXCLUDED_RELATIVE_PREFIXES),
        "expected_evidence_paths": {
            "run_root": str(runs_root(evidence_root) / final_run_id),
            "plan": str(runs_root(evidence_root) / final_run_id / "plan.json"),
            "daily": str(runs_root(evidence_root) / final_run_id / "daily"),
            "validation": str(runs_root(evidence_root) / final_run_id / "validation"),
        },
        "external_effects": profile["external_effect_policy"],
        "fill_model": profile["fill_model"],
        "rollback_policy": profile["rollback_policy"],
        "source_commit": git_commit(),
        "created_at": utc_now(),
    }


def validate_plan_entry_gate(
    plan_payload: dict[str, Any],
    *,
    run_dir: Path | None = None,
    run_state: dict[str, Any] | None = None,
    resume: bool = False,
) -> None:
    validate_schema(
        payload=plan_payload,
        artifact_name="runtime test plan",
        supported=SUPPORTED_PLAN_SCHEMA_VERSIONS,
    )
    failures: list[dict[str, Any]] = []
    resume_classification = _resume_day_classification(run_state or {}) if resume else {}
    for day in plan_payload.get("business_dates", []):
        business_date = str(day.get("business_date") or "")
        feature = dict(day.get("feature_date_evidence") or {})
        lifecycle_state = resume_classification.get(business_date, "FUTURE")
        if resume and lifecycle_state in {"COMPLETED", "FAILED"}:
            run_scoped = _run_scoped_feature_date_contract_evidence(
                run_dir=run_dir,
                business_date=business_date,
            )
            checks = _resume_feature_date_checks(
                day=day,
                feature=feature,
                run_scoped=run_scoped,
                lifecycle_state=lifecycle_state,
            )
            failed = [name for name, passed in checks.items() if not passed]
            if failed:
                failures.append(
                    {
                        "business_date": business_date,
                        "resume_lifecycle_state": lifecycle_state,
                        "failed_checks": failed,
                        "feature_date_evidence": feature,
                        "run_scoped_feature_date_evidence": run_scoped,
                    }
                )
            continue
        expected = str(feature.get("profile_expected_selected_feature_date") or "")
        selected = str(feature.get("selected_feature_date") or "")
        source = str(feature.get("source") or "")
        contract_materialized = bool(feature.get("contract_materialized"))
        contract_path = Path(str(feature.get("contract_path") or ""))
        materialized_contract_exists = bool(contract_path.is_file())
        plan_expectation_only = source == "runtime_test_plan_schedule_expectation"
        normal_contract = source == "normal_feature_date_contract"
        checks = {
            "source_is_plan_expectation_or_normal_contract": plan_expectation_only or normal_contract,
            "status_pass": feature.get("status") == "PASS",
            "materialized_contract_state_consistent": (
                materialized_contract_exists if normal_contract else not materialized_contract_exists
            )
            and contract_materialized is normal_contract,
            "contract_hash_present": bool(feature.get("contract_hash")),
            "profile_not_authority": feature.get("profile_value_used_as_authority") is False,
            "selected_feature_date_present": bool(selected),
            "selected_matches_profile_expected": not expected or selected == expected,
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            failures.append(
                {
                    "business_date": business_date,
                    "failed_checks": failed,
                    "feature_date_evidence": feature,
                }
            )
    if failures:
        raise RuntimeTestError(
            "plan entry gate failed: " + json.dumps(failures, ensure_ascii=False, sort_keys=True),
            status="PRECONDITION_FAILURE",
            exit_code=EXIT_PRECONDITION_FAILURE,
        )


def _resume_day_classification(run_state: dict[str, Any]) -> dict[str, str]:
    classification = {
        str(day): "COMPLETED"
        for day in run_state.get("completed_business_days", [])
        if str(day)
    }
    failed_day = str((run_state.get("halted_at") or {}).get("business_date") or "")
    if not failed_day:
        next_job = str(run_state.get("next_job") or "")
        failed_day = next_job.split(":", 1)[0] if ":" in next_job else ""
    if failed_day:
        classification[failed_day] = "FAILED"
    return classification


def _resume_feature_date_checks(
    *,
    day: dict[str, Any],
    feature: dict[str, Any],
    run_scoped: dict[str, Any],
    lifecycle_state: str,
) -> dict[str, bool]:
    expected = str(feature.get("profile_expected_selected_feature_date") or "")
    plan_selected = str(feature.get("selected_feature_date") or day.get("feature_date") or "")
    run_selected = str(run_scoped.get("selected_feature_date") or "")
    return {
        "resume_lifecycle_state_materialized": lifecycle_state in {"COMPLETED", "FAILED"},
        "run_scoped_contract_authority_present": bool(run_scoped),
        "run_scoped_contract_source_normal": str(run_scoped.get("feature_date_authority_source") or "") == "normal_feature_date_contract",
        "run_scoped_status_pass": str(run_scoped.get("status") or "") == "PASS",
        "run_scoped_selected_feature_date_present": bool(run_selected),
        "run_scoped_selected_matches_plan": bool(run_selected) and (not plan_selected or run_selected == plan_selected),
        "run_scoped_selected_matches_profile_expected": bool(run_selected) and (not expected or run_selected == expected),
        "plan_expectation_not_used_as_materialized_authority": str(feature.get("authority_status") or "") == "NOT_YET_MATERIALIZED"
        or str(feature.get("source") or "") == "runtime_test_plan_schedule_expectation",
    }


def _run_scoped_feature_date_contract_evidence(*, run_dir: Path | None, business_date: str) -> dict[str, Any]:
    if run_dir is None or not business_date:
        return {}
    daily_dir = Path(run_dir) / "daily" / business_date
    if not daily_dir.exists():
        return {}
    preferred = [
        daily_dir / "data_readiness" / "data_readiness.json",
        daily_dir / "market_refresh" / "runtime_manifest.json",
        daily_dir / "morning" / "runtime_manifest.json",
        daily_dir / "morning" / "morning_manifest.json",
        daily_dir / "strategy" / "input_manifest.json",
        daily_dir / "market_refresh" / "inputs" / "historical_asof" / business_date / "logical_input_manifest.json",
    ]
    candidates = [path for path in preferred if path.exists()]
    candidates.extend(path for path in sorted(daily_dir.rglob("*.json")) if path not in set(candidates))
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        evidence = _find_feature_date_contract_evidence(payload)
        if evidence:
            evidence = dict(evidence)
            evidence["run_scoped_evidence_path"] = str(path)
            evidence.setdefault("contract_hash", semantic_hash(evidence))
            evidence.setdefault("status", "PASS")
            return evidence
    return {}


def _find_feature_date_contract_evidence(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        source = str(value.get("feature_date_authority_source") or value.get("contract_source") or "")
        selected = str(value.get("selected_feature_date") or "")
        if source in {"normal_feature_date_contract", "materialized_feature_date_contract"} and selected:
            evidence = dict(value)
            evidence["feature_date_authority_source"] = "normal_feature_date_contract"
            evidence["selected_feature_date"] = selected
            evidence["status"] = str(evidence.get("status") or "PASS")
            return evidence
        for child in value.values():
            found = _find_feature_date_contract_evidence(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_feature_date_contract_evidence(child)
            if found:
                return found
    return {}


def persist_runtime_test_plan(
    *,
    evidence_root: Path,
    plan_payload: dict[str, Any],
    profile_id: str,
) -> dict[str, Any]:
    run_id = str(plan_payload.get("run_id") or "")
    if not run_id:
        raise ValueError("plan run_id missing")
    plan_path = runs_root(evidence_root) / run_id / "plan.json"
    persistence = {
        "status": "PENDING",
        "path": str(plan_path),
        "exists": False,
        "read_back_valid": False,
        "run_id_matches": False,
        "profile_id_matches": False,
        "schema_version_matches": False,
        "source_commit_matches": False,
        "business_dates_match": False,
        "job_sequence_matches": False,
        "artifact_hash": "",
    }
    plan_payload["plan_persistence"] = dict(persistence)
    plan_payload["plan_persistence"]["status"] = "PASS"
    plan_payload["plan_persistence"]["artifact_hash"] = plan_artifact_hash(plan_payload)
    write_json_atomic(plan_path, plan_payload)
    read_back = load_plan(plan_path)
    validation = validate_persisted_plan(
        expected=plan_payload,
        actual=read_back,
        expected_run_id=run_id,
        expected_profile_id=profile_id,
        plan_path=plan_path,
    )
    if validation["status"] != "PASS":
        raise ValueError("plan persistence validation failed: " + json.dumps(validation, sort_keys=True))
    plan_payload["plan_persistence"] = dict(validation)
    plan_payload["plan_persistence"]["artifact_hash"] = plan_artifact_hash(plan_payload)
    write_json_atomic(plan_path, plan_payload)
    final_read_back = load_plan(plan_path)
    final_validation = validate_persisted_plan(
        expected=plan_payload,
        actual=final_read_back,
        expected_run_id=run_id,
        expected_profile_id=profile_id,
        plan_path=plan_path,
    )
    if final_validation["status"] != "PASS":
        raise ValueError("final plan persistence validation failed: " + json.dumps(final_validation, sort_keys=True))
    return final_validation


def validate_persisted_plan(
    *,
    expected: dict[str, Any],
    actual: dict[str, Any],
    expected_run_id: str,
    expected_profile_id: str,
    plan_path: Path,
) -> dict[str, Any]:
    actual_persistence = dict(actual.get("plan_persistence") or {})
    expected_hash = plan_artifact_hash(expected)
    actual_hash = plan_artifact_hash(actual)
    checks = {
        "exists": plan_path.is_file(),
        "read_back_valid": isinstance(actual, dict),
        "run_id_matches": str(actual.get("run_id") or "") == expected_run_id,
        "profile_id_matches": str(actual.get("profile_id") or "") == expected_profile_id,
        "schema_version_matches": str(actual.get("schema_version") or "") == str(expected.get("schema_version") or ""),
        "source_commit_matches": str(actual.get("source_commit") or "") == str(expected.get("source_commit") or ""),
        "business_dates_match": actual.get("business_dates") == expected.get("business_dates"),
        "job_sequence_matches": actual.get("job_sequence") == expected.get("job_sequence"),
        "artifact_hash_matches": actual_hash == expected_hash == str(actual_persistence.get("artifact_hash") or ""),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    return {
        "status": status,
        "path": str(plan_path),
        "exists": checks["exists"],
        "read_back_valid": checks["read_back_valid"],
        "run_id_matches": checks["run_id_matches"],
        "profile_id_matches": checks["profile_id_matches"],
        "schema_version_matches": checks["schema_version_matches"],
        "source_commit_matches": checks["source_commit_matches"],
        "business_dates_match": checks["business_dates_match"],
        "job_sequence_matches": checks["job_sequence_matches"],
        "artifact_hash": actual_hash,
    }


def plan_artifact_hash(payload: dict[str, Any]) -> str:
    canonical = json.loads(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    persistence = dict(canonical.get("plan_persistence") or {})
    if persistence:
        persistence["artifact_hash"] = ""
        canonical["plan_persistence"] = persistence
    return "sha256:" + semantic_hash(canonical)


def runtime_cli_command(
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    business_date: str,
    feature_date: str,
    evaluation_time: str,
    job: str,
    run_id: str,
    evidence_root: Path,
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        RUNTIME_CLI_MODULE,
        "--mode",
        profile["mode"],
        "--broker-environment",
        profile["broker_environment"],
        "--runtime-root",
        str(runtime_root),
        "--notification-mode",
        profile["external_effect_policy"]["notification_mode"],
        "--market-refresh-allow-api-fetch",
        "true" if profile["external_effect_policy"].get("jquants_fetch") else "false",
        "--stop-on-review-required",
        "--stop-on-blocked",
        "--business-date",
        business_date,
        "--evaluation-time",
        evaluation_time,
        "--job",
        job,
        "--submit-enabled",
        "true" if job in SUBMIT_ENABLED_JOBS else "false",
        "--runtime-test-run-id",
        run_id,
        "--runtime-test-profile-id",
        profile["profile_id"],
        "--runtime-test-evidence-root",
        str(runs_root(evidence_root) / run_id),
        "--runtime-test-source-commit",
        git_commit(),
    ]
    if feature_date:
        command.extend(["--feature-date", feature_date])
    if job == "current_valuation_refresh":
        command.append("--apply-current-valuation")
    return command


def resolve_run_job_command(
    *,
    runtime_root: Path,
    job_record: dict[str, Any],
    historical_evaluation_authority: dict[str, Any] | None = None,
) -> dict[str, Any]:
    command = list(job_record.get("command") or [])
    job = str(job_record.get("job") or "")
    business_date = str(job_record.get("business_date") or "")
    planned_feature_date = str(job_record.get("feature_date") or "")
    resolution = {
        "schema_version": "runtime_test_run_feature_date_command_resolution_v1",
        "job": job,
        "business_date": business_date,
        "planned_feature_date": planned_feature_date,
        "materialized_contract_required": job in FEATURE_DATE_JOBS,
        "materialized_contract_present": False,
        "selected_feature_date": "",
        "feature_date_argument_action": "not_required",
        "feature_date_authority_source": "",
        "reason": "",
    }
    if job not in FEATURE_DATE_JOBS:
        command = command_with_historical_evaluation_authority(command, historical_evaluation_authority)
        return {"command": command, "resolution": resolution}
    contract = load_feature_date_contract(
        operations_root=runtime_root / "operations",
        requested_feature_date=business_date,
    )
    if contract is None:
        command = command_without_option(command, "--feature-date")
        resolution.update(
            {
                "feature_date_argument_action": "removed_no_materialized_contract",
                "feature_date_authority_source": "missing_normal_feature_date_contract",
                "reason": "materialized_feature_date_contract_missing_at_run_boundary",
            }
        )
        command = command_with_historical_evaluation_authority(command, historical_evaluation_authority)
        return {"command": command, "resolution": resolution}
    selected = contract.selected_feature_date
    command = command_with_option(command, "--feature-date", selected)
    command = command_with_historical_evaluation_authority(command, historical_evaluation_authority)
    resolution.update(
        {
            "materialized_contract_present": True,
            "selected_feature_date": selected,
            "feature_date_argument_action": "set_from_materialized_contract",
            "feature_date_authority_source": "normal_feature_date_contract",
            "reason": "runtime_job_command_feature_date_resolved_from_materialized_contract",
            "contract_status": contract.status,
            "contract_reason": contract.reason,
            "contract_artifact_path": contract.contract_artifact_path,
            "planned_matches_materialized": (not planned_feature_date) or planned_feature_date == selected,
        }
    )
    return {"command": command, "resolution": resolution}


def command_with_historical_evaluation_authority(command: list[str], authority: dict[str, Any] | None) -> list[str]:
    if not authority:
        return command
    authority_path = str(authority.get("authority_path") or "")
    if not authority_path:
        return command
    if "--mode" in command:
        mode_index = command.index("--mode")
        if mode_index + 1 < len(command) and command[mode_index + 1] != "historical":
            return command
    return command_with_option(command, "--historical-evaluation-authority", authority_path)


def resolve_strategy_shadow_feature_date_authority(
    *,
    runtime_root: Path,
    run_state: dict[str, Any],
    day: dict[str, Any],
) -> dict[str, Any]:
    business_date = str(day.get("business_date") or "")
    planned = str(day.get("feature_date") or "")
    completed_resolutions = [
        record.get("feature_date_command_resolution")
        for record in run_state.get("completed_jobs", [])
        if str(record.get("business_date") or "") == business_date
        and str(record.get("job") or "") in FEATURE_DATE_JOBS
        and isinstance(record.get("feature_date_command_resolution"), dict)
    ]
    selected_values = sorted(
        {
            str(resolution.get("selected_feature_date") or "")
            for resolution in completed_resolutions
            if str(resolution.get("selected_feature_date") or "")
        }
    )
    if len(selected_values) == 1:
        selected = selected_values[0]
        source_resolution = next(
            resolution
            for resolution in completed_resolutions
            if str(resolution.get("selected_feature_date") or "") == selected
        )
        return {
            "schema_version": "runtime_test_strategy_shadow_feature_date_authority_v1",
            "business_date": business_date,
            "planned_feature_date": planned,
            "materialized_feature_date": selected,
            "selected_feature_date": selected,
            "feature_date_authority_source": "completed_runtime_job_feature_date_command_resolution",
            "planned_matches_materialized": (not planned) or planned == selected,
            "feature_date_contract_path": str(source_resolution.get("contract_artifact_path") or ""),
            "authority_status": "PASS",
            "reason": "strategy_shadow_feature_date_resolved_from_completed_runtime_jobs",
            "completed_runtime_job_resolutions": completed_resolutions,
        }
    if len(selected_values) > 1:
        return {
            "schema_version": "runtime_test_strategy_shadow_feature_date_authority_v1",
            "business_date": business_date,
            "planned_feature_date": planned,
            "materialized_feature_date": "",
            "selected_feature_date": planned,
            "feature_date_authority_source": "conflicting_completed_runtime_job_feature_date_command_resolution",
            "planned_matches_materialized": False,
            "feature_date_contract_path": "",
            "authority_status": "BLOCK",
            "reason": "strategy_shadow_feature_date_conflicting_completed_runtime_job_resolutions",
            "completed_runtime_job_resolutions": completed_resolutions,
        }
    contract = load_feature_date_contract(
        operations_root=runtime_root / "operations",
        requested_feature_date=business_date,
    )
    if contract is not None:
        selected = contract.selected_feature_date
        return {
            "schema_version": "runtime_test_strategy_shadow_feature_date_authority_v1",
            "business_date": business_date,
            "planned_feature_date": planned,
            "materialized_feature_date": selected,
            "selected_feature_date": selected,
            "feature_date_authority_source": "materialized_feature_date_contract",
            "planned_matches_materialized": (not planned) or planned == selected,
            "feature_date_contract_path": contract.contract_artifact_path,
            "authority_status": "PASS" if str(contract.status) == "PASS" else "REVIEW_REQUIRED",
            "reason": "strategy_shadow_feature_date_resolved_from_materialized_contract",
            "completed_runtime_job_resolutions": completed_resolutions,
        }
    if completed_resolutions:
        return {
            "schema_version": "runtime_test_strategy_shadow_feature_date_authority_v1",
            "business_date": business_date,
            "planned_feature_date": planned,
            "materialized_feature_date": "",
            "selected_feature_date": planned,
            "feature_date_authority_source": "missing_selected_feature_date_in_completed_runtime_job_resolution",
            "planned_matches_materialized": False,
            "feature_date_contract_path": "",
            "authority_status": "BLOCK",
            "reason": "strategy_shadow_feature_date_required_runtime_job_resolution_missing_selected_date",
            "completed_runtime_job_resolutions": completed_resolutions,
        }
    return {
        "schema_version": "runtime_test_strategy_shadow_feature_date_authority_v1",
        "business_date": business_date,
        "planned_feature_date": planned,
        "materialized_feature_date": "",
        "selected_feature_date": planned,
        "feature_date_authority_source": "plan_feature_date_no_materialized_runtime_job_authority",
        "planned_matches_materialized": False,
        "feature_date_contract_path": str(runtime_root / "operations" / "feature_date_contract" / f"{business_date}.json"),
        "authority_status": "REVIEW_REQUIRED",
        "reason": "strategy_shadow_feature_date_materialized_authority_missing",
        "completed_runtime_job_resolutions": [],
    }


def command_with_option(command: list[str], option: str, value: str) -> list[str]:
    updated = command_without_option(command, option)
    if value:
        updated.extend([option, value])
    return updated


def command_without_option(command: list[str], option: str) -> list[str]:
    updated: list[str] = []
    skip_next = False
    for item in command:
        if skip_next:
            skip_next = False
            continue
        if item == option:
            skip_next = True
            continue
        updated.append(item)
    return updated


def resolve_business_dates(
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    business_days: int | None,
    start_date: str | None,
    date_from: str | None,
    date_to: str | None,
) -> list[str]:
    return list(
        resolve_business_window(
            profile=profile,
            runtime_root=runtime_root,
            business_days=business_days,
            start_date=start_date,
            date_from=date_from,
            date_to=date_to,
        )["resolved_business_dates"]
    )


def resolve_business_window(
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    business_days: int | None,
    start_date: str | None,
    date_from: str | None,
    date_to: str | None,
) -> dict[str, Any]:
    calendar = load_trading_calendar_authority(runtime_root=runtime_root)
    calendar_days = list(calendar["business_days"])
    requested_count = int(business_days or profile["business_days"])
    profile_start_date = str((profile.get("window") or {}).get("date_from") or "")
    cli_date_from = str(date_from or "")
    cli_start_date = str(start_date or "")
    if date_from and date_to:
        requested_start = date_from
        requested_end = date_to
        requested_intent_dates = weekday_business_days(date_from=date_from, date_to=date_to)
        if business_days:
            requested_intent_dates = requested_intent_dates[:requested_count]
        selection_authority = "cli_date_from"
        override_reason = "cli_date_from_and_date_to_define_explicit_window"
    else:
        if date_from:
            requested_start = date_from
            selection_authority = "cli_date_from"
            override_reason = "cli_date_from_defines_business_days_window_start"
        elif start_date:
            requested_start = start_date
            selection_authority = "cli_start_date"
            override_reason = "cli_start_date_defines_business_days_window_start"
        else:
            requested_start = profile_start_date
            selection_authority = "profile_window_date_from"
            override_reason = "profile_default_used_when_cli_start_absent"
        requested_intent_dates = weekday_business_days_from_start(start_date=requested_start, business_days=requested_count)
        requested_end = requested_intent_dates[-1] if requested_intent_dates else ""
    if not business_days and date_from and date_to:
        requested_count = len(requested_intent_dates)
    if calendar_days:
        if date_from and date_to:
            resolved = [day for day in calendar_days if day in set(requested_intent_dates) and date_from <= day <= date_to]
            if business_days:
                resolved = resolved[:requested_count]
        else:
            resolved = [day for day in calendar_days if day >= requested_start][:requested_count]
    elif date_from and date_to:
        resolved = list(requested_intent_dates)
    else:
        resolved = list(requested_intent_dates)
    unresolved = [day for day in requested_intent_dates[:requested_count] if day not in set(resolved)]
    status = "PASS" if requested_count == len(resolved) else "REVIEW_REQUIRED"
    reason = "requested_window_fully_resolved" if status == "PASS" else "requested_window_partially_resolved_calendar_authority_insufficient"
    override_applied = selection_authority != "profile_window_date_from"
    return {
        "requested_start_date": requested_start,
        "requested_end_date": requested_end,
        "profile_start_date": profile_start_date,
        "selected_start_date": requested_start,
        "selection_authority": selection_authority,
        "override_applied": override_applied,
        "override_reason": override_reason,
        "requested_business_days": requested_count,
        "requested_window": {
            "requested_start_date": requested_start,
            "requested_end_date": requested_end,
            "profile_start_date": profile_start_date,
            "selected_start_date": requested_start,
            "selection_authority": selection_authority,
            "override_applied": override_applied,
            "override_reason": override_reason,
            "requested_business_days": requested_count,
            "requested_intent_dates": requested_intent_dates[:requested_count],
            "request_source": "cli_or_profile_window",
        },
        "resolved_business_dates": resolved,
        "resolved_business_day_count": len(resolved),
        "resolved_date_from": resolved[0] if resolved else "",
        "resolved_date_to": resolved[-1] if resolved else "",
        "window_resolution_status": status,
        "window_resolution_reason": reason,
        "calendar_authority": calendar,
        "calendar_max_date": calendar.get("max_date", ""),
        "unresolved_requested_dates": unresolved,
    }


def weekday_business_days_from_start(*, start_date: str, business_days: int) -> list[str]:
    start = date.fromisoformat(start_date)
    days: list[str] = []
    current = start
    while len(days) < business_days:
        if current.weekday() < 5:
            days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def load_trading_calendar_authority(*, runtime_root: Path) -> dict[str, Any]:
    base_path = runtime_root / "operations" / "jquants" / "historical_snapshots" / "trading_calendar" / "data.parquet"
    base_days = _read_calendar_business_days(base_path)
    overlays = _validated_calendar_overlay_authorities(runtime_root=runtime_root)
    composed_days = sorted({*base_days, *(day for overlay in overlays for day in overlay["business_days"])})
    source_paths = [str(base_path)] + [overlay["path"] for overlay in overlays]
    return {
        "schema_version": "runtime_test_calendar_authority_v1",
        "authority": "validated_canonical_calendar_base_plus_validated_incremental_staging_overlay" if overlays else "canonical_calendar_base",
        "status": "PASS" if composed_days else "MISSING",
        "path": str(base_path),
        "source_paths": source_paths,
        "source_hashes": {path: file_ref(Path(path)).get("sha256", "") for path in source_paths},
        "base_path": str(base_path),
        "base_max_date": max(base_days) if base_days else "",
        "overlay_count": len(overlays),
        "overlays": overlays,
        "business_days": composed_days,
        "max_date": max(composed_days) if composed_days else "",
        "duplicate_policy": "Date key dedupe; validated overlay may extend base but does not mutate canonical",
        "canonical_mutated": False,
    }


def _read_calendar_business_days(path: Path) -> list[str]:
    if not path.is_file():
        return []
    try:
        import pandas as pd

        frame = pd.read_parquet(path)
    except Exception:
        return []
    if "Date" not in frame.columns:
        return []
    calendar_state_columns = [column for column in ("HolDiv", "HolidayDivision", "holiday_division") if column in frame.columns]
    if calendar_state_columns:
        mask = None
        for column in calendar_state_columns:
            column_mask = frame[column].notna() & frame[column].map(_is_calendar_open_value)
            mask = column_mask if mask is None else mask | column_mask
        frame = frame[mask].copy()
    return sorted(str(value) for value in frame["Date"].dropna().unique())


def _validated_calendar_overlay_authorities(*, runtime_root: Path) -> list[dict[str, Any]]:
    runs_root = runtime_root / "market_data_acquisition" / "runs"
    if not runs_root.is_dir():
        return []
    overlays: list[dict[str, Any]] = []
    for calendar_path in sorted(runs_root.glob("*/raw/jquants/trading_calendar/data.parquet")):
        run_root = calendar_path.parents[3]
        eligibility = _validated_acquisition_staging_for_calendar(run_root=run_root, calendar_path=calendar_path)
        if eligibility["status"] != "PASS":
            continue
        days = _read_calendar_business_days(calendar_path)
        overlays.append(
            {
                **eligibility,
                "path": str(calendar_path),
                "business_days": days,
                "min_date": min(days) if days else "",
                "max_date": max(days) if days else "",
                "content_hash": file_ref(calendar_path).get("sha256", ""),
            }
        )
    return overlays


def _validated_acquisition_staging_for_calendar(*, run_root: Path, calendar_path: Path) -> dict[str, Any]:
    state_path = run_root / "state.json"
    plan_path = run_root / "plan.json"
    if not state_path.is_file() or not plan_path.is_file() or not calendar_path.is_file():
        return {"status": "BLOCK", "reason": "STAGING_VALIDATION_ARTIFACT_MISSING", "run_root": str(run_root)}
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "BLOCK", "reason": f"STAGING_VALIDATION_ARTIFACT_UNREADABLE:{type(exc).__name__}", "run_root": str(run_root)}
    final = dict(state.get("final_validation") or {})
    inventory = dict(final.get("normalized_inventory") or {})
    schema = dict(final.get("schema_comparison") or {})
    lineage = dict(final.get("jquants_lineage") or {})
    blocked = []
    if state.get("status") != "PASS" or plan.get("status") != "PASS" or final.get("status") != "PASS":
        blocked.append("STAGING_FINAL_VALIDATION_NOT_PASS")
    if state.get("acquisition_run_id") != run_root.name or plan.get("acquisition_run_id") != run_root.name:
        blocked.append("STAGING_RUN_ID_MISMATCH")
    if inventory.get("duplicate_key_count"):
        blocked.append("STAGING_DUPLICATE_KEYS")
    if int(final.get("future_date_count") or 0):
        blocked.append("STAGING_FUTURE_DATE_ROWS")
    if lineage.get("status") != "PASS":
        blocked.append("STAGING_LINEAGE_NOT_PASS")
    if schema.get("status") != "PASS" or schema.get("runtime_merge_compatible") is not True:
        blocked.append("STAGING_SCHEMA_NOT_RUNTIME_COMPATIBLE")
    return {
        "status": "PASS" if not blocked else "BLOCK",
        "reason": "validated_incremental_staging_ready" if not blocked else blocked[0],
        "run_root": str(run_root),
        "acquisition_run_id": str(state.get("acquisition_run_id") or ""),
        "state_path": str(state_path),
        "plan_path": str(plan_path),
        "blocked_reasons": blocked,
    }


def _is_calendar_open_value(value: Any) -> bool:
    return str(value).strip() in {"1", "1.0"}


def _legacy_resolve_business_dates(
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    business_days: int | None,
    start_date: str | None,
    date_from: str | None,
    date_to: str | None,
) -> list[str]:
    calendar_days = load_trading_calendar_business_days(runtime_root=runtime_root)
    if date_from and date_to:
        if calendar_days:
            return [day for day in calendar_days if date_from <= day <= date_to]
        return weekday_business_days(date_from=date_from, date_to=date_to)
    count = business_days or int(profile["business_days"])
    start_text = start_date or profile["window"]["date_from"]
    if calendar_days:
        selected = [day for day in calendar_days if day >= start_text]
        return selected[:count]
    start = date.fromisoformat(start_text)
    days = []
    current = start
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def load_trading_calendar_business_days(*, runtime_root: Path) -> list[str]:
    source = runtime_root / "operations" / "jquants" / "historical_snapshots" / "trading_calendar" / "data.parquet"
    if not source.is_file():
        return []
    try:
        import pandas as pd

        frame = pd.read_parquet(source)
    except Exception:
        return []
    if "Date" not in frame.columns:
        return []
    if "HolDiv" in frame.columns:
        mask = frame["HolDiv"].astype(str) == "1"
    elif "HolidayDivision" in frame.columns:
        mask = frame["HolidayDivision"].astype(str) == "1"
    else:
        return []
    return sorted(str(value) for value in frame.loc[mask, "Date"].dropna().unique())


def weekday_business_days(*, date_from: str, date_to: str) -> list[str]:
    start = date.fromisoformat(date_from)
    end = date.fromisoformat(date_to)
    days: list[str] = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def resolve_feature_date(*, profile: dict[str, Any], runtime_root: Path, business_date: str) -> dict[str, Any]:
    contract_path = runtime_root / "operations" / "feature_date_contract" / f"{business_date}.json"
    expected = str((profile.get("accepted_feature_dates") or {}).get(business_date) or "")
    contract = load_feature_date_contract(
        operations_root=runtime_root / "operations",
        requested_feature_date=business_date,
    )
    if contract is None:
        selected = expected or business_date
        payload = {
            "status": "PASS",
            "reason": "feature_date_contract_not_yet_materialized_plan_expectation_only",
            "requested_feature_date": business_date,
            "selected_feature_date": selected,
            "latest_available_market_date": selected,
            "contract_artifact_path": str(contract_path),
            "plan_feature_date_expectation_source": "runtime_test_profile_schedule",
        }
        source = "runtime_test_plan_schedule_expectation"
        feature_date_authority_source = "not_yet_materialized_plan_expectation"
        authority_status = "NOT_YET_MATERIALIZED"
        reason = payload["reason"]
    else:
        payload = contract.to_payload()
        payload["contract_artifact_path"] = contract.contract_artifact_path
        selected = contract.selected_feature_date
        source = "normal_feature_date_contract"
        feature_date_authority_source = "normal_feature_date_contract"
        authority_status = "PASS"
        reason = str(payload.get("reason") or "")
        if expected and selected != expected:
            authority_status = "REVIEW_REQUIRED"
            reason = "feature_date_authority_mismatch"
        payload["status"] = authority_status if authority_status != "PASS" else str(payload.get("status") or "UNKNOWN")
    payload["reason"] = reason
    return {
        "source": source,
        "contract_path": str(contract_path),
        "contract_hash": semantic_hash(payload),
        "contract_materialized": contract is not None,
        "materialized_contract_exists": contract_path.is_file(),
        "stale_existing_contract_ignored": False,
        "profile_expected_selected_feature_date": expected,
        "profile_value_used_as_authority": False,
        "profile_value_used_as_plan_expectation": bool(expected),
        "requested_feature_date": business_date,
        "selected_feature_date": selected,
        "carryover": selected != business_date,
        "status": payload.get("status", "UNKNOWN"),
        "reason": payload.get("reason", ""),
        "authority_status": authority_status,
        "feature_date_authority_source": feature_date_authority_source,
        "run_authority_required_stage": "runtime_market_refresh_and_data_readiness",
    }


def validate_initial_position_state_date(value: str) -> None:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise RuntimeTestError(
            "initial position state date must be YYYY-MM-DD",
            status="PRECONDITION_FAILURE",
            exit_code=EXIT_PRECONDITION_FAILURE,
        ) from exc


def apply_reset(
    *,
    runtime_root: Path,
    initial_state: dict[str, Any],
    profile: dict[str, Any],
    initial_position_state_date: str = "",
) -> None:
    created_at = utc_now()
    logical_position_date = initial_position_state_date
    for rel in RESETTABLE_RELATIVE_PATHS:
        target = runtime_root / rel
        if not target.exists():
            continue
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    ensure_parent(runtime_root / "persistent_ledger" / "state.json")
    write_json_atomic(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "runtime_v2_current_temporal_v1",
            "asset_state_id": f"runtime-test-initial-{timestamp_id()}",
            "environment": profile["mode"],
            "source": "runtime_test_reset",
            "as_of": logical_position_date or created_at,
            "business_date": logical_position_date,
            "position_state_as_of": logical_position_date,
            "position_state_source": "runtime_test_reset",
            "positions": [],
            "cash": float(initial_state["cash"]),
            "buying_power": float(initial_state["buying_power"]),
            "market_value": 0.0,
            "total_equity": float(initial_state["cash"]),
            "review_required": False,
            "production_equivalent": False,
            "current_state_confirmed_empty": True,
            "current_positions_unknown": False,
            "current_position_status": "READY" if logical_position_date else "",
            "no_position": True,
            "no_position_reason": "runtime_test_initial_empty_portfolio",
            "cash_unknown": False,
            "buying_power_unknown": False,
            "cash_confirmed": True,
            "buying_power_confirmed": True,
            "generated_from": [],
            "created_at": created_at,
            "updated_at": created_at,
            "reset_executed_at": created_at,
            "logical_time_fields": {
                "business_date": logical_position_date,
                "as_of": logical_position_date or "LEGACY_WALL_CLOCK_FALLBACK",
                "position_state_as_of": logical_position_date,
            },
            "wall_clock_fields": {
                "created_at": created_at,
                "updated_at": created_at,
                "reset_executed_at": created_at,
            },
            "temporal_schema_version": "runtime_v2_current_temporal_v1",
            "temporal_status": "READY",
            "current_valuation_status": "NOT_REQUIRED_EMPTY" if logical_position_date else "",
            "valuation_as_of": "",
            "source_market_date": "",
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
        },
    )
    for rel in (
        "persistent_ledger/orders.jsonl",
        "persistent_ledger/executions.jsonl",
        "persistent_ledger/positions.jsonl",
        "persistent_ledger/cash.jsonl",
        "persistent_ledger/events.jsonl",
    ):
        path = runtime_root / rel
        ensure_parent(path)
        path.write_text("", encoding="utf-8")
    write_json_atomic(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "runtime_v2_pending_slot_v1",
            "status": "EMPTY",
            "state": "EMPTY",
            "active_pending": False,
            "last_pending_plan_id": "",
            "last_terminal_state": "",
            "last_transition_at": created_at,
            "history_path": "",
        },
    )
    write_json_atomic(
        runtime_root / "runtime_state" / "current_state.json",
        {
            "schema_version": "runtime_v2_operation_state_v1",
            "runtime_mode": profile["mode"],
            "environment": profile["mode"],
            "state": "READY",
            "reason": "runtime_test_reset_initial_state",
            "business_date": "",
            "generated_at": created_at,
            "updated_at": created_at,
            "asset_state_source": "persistent_ledger/state.json",
            "pending_state_source": "pending_order_plan/pending_order_plan.json",
            "production_equivalent": False,
            "asset_state_is_authoritative_here": False,
        },
    )


def reset_clean_state_invariant(*, runtime_root: Path, initial_state: dict[str, Any], executed: bool) -> dict[str, Any]:
    current = read_json(runtime_root / "persistent_ledger" / "state.json") if (runtime_root / "persistent_ledger" / "state.json").exists() else {}
    pending = read_json(runtime_root / "pending_order_plan" / "pending_order_plan.json") if (runtime_root / "pending_order_plan" / "pending_order_plan.json").exists() else {}
    stale_dirs = {
        "stale_feature_date_contracts_remaining": sorted(str(path) for path in (runtime_root / "operations" / "feature_date_contract").glob("*.json"))
        if (runtime_root / "operations" / "feature_date_contract").exists()
        else [],
        "stale_feature_consumer_readiness_remaining": sorted(str(path) for path in (runtime_root / "operations" / "feature_consumer_readiness").glob("*.json"))
        if (runtime_root / "operations" / "feature_consumer_readiness").exists()
        else [],
        "stale_feature_artifacts_remaining": sorted(str(path) for path in (runtime_root / "operations" / "feature_artifacts").glob("*"))
        if (runtime_root / "operations" / "feature_artifacts").exists()
        else [],
        "stale_run_manifests_remaining": sorted(str(path) for path in (runtime_root / "runtime_state" / "run_manifest").glob("*"))
        if (runtime_root / "runtime_state" / "run_manifest").exists()
        else [],
    }
    return {
        "schema_version": "runtime_test_reset_clean_state_invariant_v1",
        "operational_state_reset": bool(executed),
        **stale_dirs,
        "ledger_initial_cash": current.get("cash"),
        "ledger_positions": current.get("positions") if isinstance(current.get("positions"), list) else [],
        "pending_state": pending.get("state") or pending.get("status") or "",
        "historical_broker_state_reset": not (runtime_root / "runtime_state" / "historical_broker").exists(),
        "expected_initial_cash": float(initial_state["cash"]),
        "passes": bool(
            executed
            and not stale_dirs["stale_feature_date_contracts_remaining"]
            and not stale_dirs["stale_feature_consumer_readiness_remaining"]
            and not stale_dirs["stale_feature_artifacts_remaining"]
            and not stale_dirs["stale_run_manifests_remaining"]
            and float(current.get("cash") or -1) == float(initial_state["cash"])
            and current.get("positions") == []
            and (pending.get("state") or pending.get("status")) == "EMPTY"
            and not (runtime_root / "runtime_state" / "historical_broker").exists()
        ),
    }


def copy_resettable_state(*, runtime_root: Path, destination: Path) -> None:
    for rel in RESETTABLE_RELATIVE_PATHS:
        source = runtime_root / rel
        target = destination / rel
        if not source.exists():
            continue
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def restore_from_backup(*, runtime_root: Path, backup_manifest: dict[str, Any]) -> None:
    backup_path = Path(backup_manifest["backup_path"]) / "state"
    if not backup_path.exists():
        raise RuntimeTestError("backup state directory missing", status="ROLLBACK_FAILURE", exit_code=EXIT_ROLLBACK_FAILURE)
    for rel in RESETTABLE_RELATIVE_PATHS:
        target = runtime_root / rel
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
    for source in sorted(backup_path.rglob("*")):
        if not source.is_file():
            continue
        rel = source.relative_to(backup_path)
        target = runtime_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def build_backup_inventory(runtime_root: Path) -> list[dict[str, Any]]:
    return [file_ref(runtime_root / rel, root=runtime_root) | {"resettable": True} for rel in RESETTABLE_RELATIVE_PATHS]


def validate_run_preconditions(
    *,
    runtime_root: Path,
    evidence_root: Path,
    plan_payload: dict[str, Any] | None = None,
    profile: dict[str, Any] | None = None,
) -> None:
    if not latest_backup(evidence_root):
        raise RuntimeTestError("run requires valid backup", status="PRECONDITION_FAILURE", exit_code=EXIT_PRECONDITION_FAILURE)
    required = [
        runtime_root / "persistent_ledger" / "state.json",
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        runtime_root / "runtime_state" / "current_state.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeTestError("run requires valid initial state: " + ", ".join(missing), status="PRECONDITION_FAILURE", exit_code=EXIT_PRECONDITION_FAILURE)
    if plan_payload:
        planned_runtime_root = str(plan_payload.get("runtime_root") or "")
        if planned_runtime_root and Path(planned_runtime_root) != Path(runtime_root):
            raise RuntimeTestError(
                f"runtime_root_binding_mismatch: planned={planned_runtime_root}, actual={runtime_root}",
                status="PRECONDITION_FAILURE",
                exit_code=EXIT_PRECONDITION_FAILURE,
            )
        requested_start_date = str((plan_payload.get("business_dates") or [{}])[0].get("business_date") or "")
        compatibility = build_baseline_compatibility(
            runtime_root=runtime_root,
            requested_start_date=requested_start_date,
            run_id=str(plan_payload.get("run_id") or ""),
            profile_id=str(plan_payload.get("profile_id") or (profile or {}).get("profile_id") or ""),
            mode=str((profile or {}).get("mode") or ""),
        )
        if compatibility["baseline_compatibility_status"] != "PASS":
            raise RuntimeTestError(
                "runtime_test_clean_baseline_mismatch: "
                + ",".join(compatibility.get("mismatch_reasons") or ["unknown"])
                + "; next_operator_action=reset_or_rollback_to_compatible_backup",
                status="HALT",
                exit_code=EXIT_HALT,
            )


def build_baseline_compatibility(
    *,
    runtime_root: Path,
    requested_start_date: str,
    run_id: str,
    profile_id: str = "",
    mode: str = "",
) -> dict[str, Any]:
    state = inspect_runtime_test_state(runtime_root)
    mismatches = baseline_mismatch_reasons(state=state, requested_start_date=requested_start_date, run_id=run_id)
    return {
        "schema_version": "runtime_test_baseline_compatibility_v1",
        "baseline_compatibility_status": "PASS" if not mismatches else "REVIEW_REQUIRED",
        "requested_start_date": requested_start_date,
        "run_id": run_id,
        "profile_id": profile_id,
        "mode": mode,
        "current_state_date": state["runtime_state_business_date"],
        "ledger_date": state["ledger_business_date"],
        "pending_target_date": state["pending_target_date"],
        "pending_active": state["pending_active"],
        "pending_origin_run_id": state["pending_origin_run_id"],
        "safety_authority_date": state["safety_authority_date"],
        "compatible_backup_required": bool(mismatches),
        "recommended_backup_id": "",
        "mismatch_reasons": mismatches,
        "next_operator_action": "proceed" if not mismatches else "reset_or_rollback_to_compatible_backup",
        "state_matrix": state,
    }


def classify_backup_for_clean_baseline(
    *,
    backup_manifest: dict[str, Any],
    requested_start_date: str,
    run_id: str = "",
) -> dict[str, Any]:
    backup_id = str(backup_manifest.get("backup_id") or "")
    backup_path = Path(str(backup_manifest.get("backup_path") or ""))
    state_root = backup_path / "state"
    state = inspect_runtime_test_state(state_root)
    mismatches = baseline_mismatch_reasons(state=state, requested_start_date=requested_start_date, run_id=run_id)
    return {
        "backup_id": backup_id,
        "created_at": backup_manifest.get("created_at") or "",
        "backup_path": str(backup_path),
        "current_business_date": state["runtime_state_business_date"],
        "current_as_of": state["current_state_as_of"],
        "ledger_business_date": state["ledger_business_date"],
        "ledger_as_of": state["ledger_as_of"],
        "pending_state": state["pending_state"],
        "pending_active": state["pending_active"],
        "pending_target_session_date": state["pending_target_date"],
        "pending_runtime_test_run_id": state["pending_origin_run_id"],
        "pending_safety_business_date": state["pending_safety_business_date"],
        "runtime_state_business_date": state["runtime_state_business_date"],
        "safety_artifact_business_date": state["safety_artifact_business_date"],
        "clean_baseline": not mismatches,
        "restorable_for_requested_start_date": not mismatches,
        "rejected_reasons": mismatches,
    }


def inspect_runtime_test_state(root: Path) -> dict[str, Any]:
    ledger = read_json_optional(root / "persistent_ledger" / "state.json")
    pending = read_json_optional(root / "pending_order_plan" / "pending_order_plan.json")
    runtime_state = read_json_optional(root / "runtime_state" / "current_state.json")
    safety = read_json_optional(root / "runtime_state" / "safety" / "latest_safety_decision.json")
    safety_context = pending.get("safety_context") if isinstance(pending.get("safety_context"), dict) else {}
    return {
        "root": str(root),
        "ledger_exists": bool(ledger),
        "ledger_business_date": _business_state_date(ledger),
        "ledger_as_of": str(ledger.get("as_of") or ""),
        "ledger_position_state_as_of": str(ledger.get("position_state_as_of") or ""),
        "ledger_valuation_as_of": str(ledger.get("valuation_as_of") or ""),
        "runtime_state_exists": bool(runtime_state),
        "runtime_state_business_date": str(runtime_state.get("business_date") or ""),
        "runtime_state_as_of": str(runtime_state.get("as_of") or ""),
        "runtime_state_state": str(runtime_state.get("state") or runtime_state.get("status") or ""),
        "current_state_as_of": str(runtime_state.get("as_of") or runtime_state.get("business_date") or ""),
        "pending_exists": bool(pending),
        "pending_state": str(pending.get("state") or pending.get("status") or ""),
        "pending_status": str(pending.get("status") or ""),
        "pending_active": bool(pending.get("active_pending")),
        "pending_target_date": str(pending.get("target_session_date") or pending.get("business_date") or ""),
        "pending_origin_run_id": str(pending.get("runtime_test_run_id") or safety_context.get("runtime_test_run_id") or ""),
        "pending_safety_business_date": str(safety_context.get("safety_business_date") or ""),
        "pending_safety_evidence_root": str(safety_context.get("runtime_test_evidence_root") or ""),
        "safety_artifact_exists": bool(safety),
        "safety_artifact_business_date": str(safety.get("business_date") or ""),
        "safety_artifact_run_id": str(safety.get("runtime_test_run_id") or ""),
        "safety_authority_date": str(safety_context.get("safety_business_date") or safety.get("business_date") or ""),
    }


def baseline_mismatch_reasons(*, state: dict[str, Any], requested_start_date: str, run_id: str) -> list[str]:
    reasons: list[str] = []
    if not requested_start_date:
        reasons.append("requested_start_date_missing")
        return reasons
    for label, value in (
        ("current_state_date", state.get("runtime_state_business_date")),
        ("ledger_date", state.get("ledger_business_date")),
        ("pending_target_date", state.get("pending_target_date")),
        ("pending_safety_business_date", state.get("pending_safety_business_date")),
        ("safety_artifact_business_date", state.get("safety_artifact_business_date")),
    ):
        if _date_gt(str(value or ""), requested_start_date):
            reasons.append(f"{label}_future")
    if state.get("pending_active"):
        reasons.append("pending_active")
    pending_run_id = str(state.get("pending_origin_run_id") or "")
    if pending_run_id and run_id and pending_run_id != run_id:
        reasons.append("pending_foreign_runtime_test_run_id")
    safety_run_id = str(state.get("safety_artifact_run_id") or "")
    if safety_run_id and run_id and safety_run_id != run_id:
        reasons.append("safety_foreign_runtime_test_run_id")
    return sorted(set(reasons))


def _business_state_date(payload: dict[str, Any]) -> str:
    for key in ("business_date", "position_state_as_of", "valuation_as_of"):
        value = str(payload.get(key) or "")
        if _date_only(value):
            return _date_only(value)
    if payload.get("current_state_confirmed_empty") is True and not payload.get("business_date"):
        return ""
    return ""


def _date_only(value: str) -> str:
    text = str(value or "")
    if len(text) >= 10 and text[4:5] == "-" and text[7:8] == "-":
        return text[:10]
    return ""


def _date_gt(left: str, right: str) -> bool:
    left_date = _date_only(left)
    right_date = _date_only(right)
    return bool(left_date and right_date and left_date > right_date)


def read_json_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except Exception:
        return {}


def require_historical_mutation_context(*, args: argparse.Namespace, profile: dict[str, Any]) -> None:
    if profile.get("mode") == "production":
        raise RuntimeTestError("production use is blocked by Runtime Test runner", status="HALT", exit_code=EXIT_HALT)
    if profile.get("mode") != "historical":
        raise RuntimeTestError("Phase17-K runner mutating commands are limited to historical profiles", status="PRECONDITION_FAILURE", exit_code=EXIT_PRECONDITION_FAILURE)


def require_confirm(args: argparse.Namespace) -> None:
    if not (getattr(args, "confirm", False) and getattr(args, "explicit_mutation_confirm", False)):
        raise RuntimeTestError(
            f"mutating command requires --confirm {MUTATION_CONFIRM_FLAG}",
            status="PRECONDITION_FAILURE",
            exit_code=EXIT_PRECONDITION_FAILURE,
        )


def validate_environment(*, profile: dict[str, Any], runtime_root: Path) -> None:
    try:
        reject_mode_rooted_runtime_root(runtime_root)
    except ValueError as exc:
        raise RuntimeTestError(str(exc), status="INVALID_ARGUMENT", exit_code=EXIT_INVALID_ARGUMENT) from exc
    if str(runtime_root) != profile["runtime_root"] and runtime_root.name != ".runtime":
        raise RuntimeTestError("runtime_root must be fixed .runtime", status="INVALID_ARGUMENT", exit_code=EXIT_INVALID_ARGUMENT)
    if profile.get("mode") == "production":
        raise RuntimeTestError("production profile is not allowed in this runner", status="HALT", exit_code=EXIT_HALT)
    if profile.get("mode") == "historical":
        policy = profile.get("external_effect_policy") or {}
        if any(bool(policy.get(key)) for key in ("external_delivery", "jquants_fetch", "broker_write", "tachibana_api")):
            raise RuntimeTestError("historical profile must disable external effects", status="HALT", exit_code=EXIT_HALT)


def load_profile(profile: str) -> dict[str, Any]:
    path = PROFILE_PATHS.get(profile, Path(profile))
    if not path.exists():
        raise RuntimeTestError(f"profile not found: {profile}", status="INVALID_ARGUMENT", exit_code=EXIT_INVALID_ARGUMENT)
    payload = read_json(path)
    payload["_profile_path"] = str(path)
    payload["_profile_hash"] = sha256_file(path)
    return payload


def load_backup_manifest(evidence_root: Path, backup_id: str | None) -> dict[str, Any]:
    selected = backup_id or latest_backup(evidence_root).get("backup_id", "")
    if not selected:
        raise RuntimeTestError("valid backup is required", status="PRECONDITION_FAILURE", exit_code=EXIT_PRECONDITION_FAILURE)
    path = backups_root(evidence_root) / selected / "backup_manifest.json"
    if not path.exists():
        raise RuntimeTestError(f"backup manifest not found: {selected}", status="PRECONDITION_FAILURE", exit_code=EXIT_PRECONDITION_FAILURE)
    payload = read_json(path)
    validate_schema(
        payload=payload,
        artifact_name="runtime test backup manifest",
        supported=SUPPORTED_BACKUP_MANIFEST_SCHEMA_VERSIONS,
    )
    return payload


def load_run_state(evidence_root: Path, run_id: str | None) -> dict[str, Any]:
    if not run_id:
        raise RuntimeTestError("run_id is required", status="INVALID_ARGUMENT", exit_code=EXIT_INVALID_ARGUMENT)
    path = runs_root(evidence_root) / run_id / "run_state.json"
    if not path.exists():
        raise RuntimeTestError(f"run state not found: {run_id}", status="PRECONDITION_FAILURE", exit_code=EXIT_PRECONDITION_FAILURE)
    payload = read_json(path)
    validate_schema(
        payload=payload,
        artifact_name="runtime test run state",
        supported=SUPPORTED_RUN_STATE_SCHEMA_VERSIONS,
    )
    actual = str(payload.get("run_id") or "")
    if actual != run_id:
        raise RuntimeTestError(
            f"run state run_id mismatch: requested={run_id} actual={actual or '<missing>'}",
            status="TEST_INVALID",
            exit_code=EXIT_TEST_INVALID,
        )
    return payload


def load_plan(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    validate_schema(
        payload=payload,
        artifact_name="runtime test plan",
        supported=SUPPORTED_PLAN_SCHEMA_VERSIONS,
    )
    return payload


def load_plan_for_run(*, evidence_root: Path, run_id: str) -> dict[str, Any]:
    plan_path = runs_root(evidence_root) / run_id / "plan.json"
    if not plan_path.exists():
        candidates = similar_run_id_candidates(evidence_root=evidence_root, run_id=run_id)
        suffix = f"; similar_run_id_candidates={candidates}" if candidates else ""
        raise RuntimeTestError(
            f"runtime test plan not found for exact run_id: {run_id}{suffix}",
            status="PRECONDITION_FAILURE",
            exit_code=EXIT_PRECONDITION_FAILURE,
        )
    payload = load_plan(plan_path)
    validate_plan_run_id(plan_payload=payload, requested_run_id=run_id, plan_path=plan_path)
    return payload


def validate_plan_run_id(*, plan_payload: dict[str, Any], requested_run_id: str, plan_path: Path) -> None:
    actual = str(plan_payload.get("run_id") or "")
    if actual != requested_run_id:
        raise RuntimeTestError(
            f"plan run_id mismatch: requested={requested_run_id} actual={actual or '<missing>'} plan={plan_path}",
            status="TEST_INVALID",
            exit_code=EXIT_TEST_INVALID,
        )


def similar_run_id_candidates(*, evidence_root: Path, run_id: str) -> list[str]:
    root = runs_root(evidence_root)
    if not root.exists():
        return []
    normalized = run_id.rstrip("Z")
    candidates: list[str] = []
    for path in sorted(root.iterdir()):
        if not path.is_dir():
            continue
        name = path.name
        if name == run_id:
            continue
        if name.rstrip("Z") == normalized:
            candidates.append(name)
    return candidates[:5]


def validate_schema(*, payload: dict[str, Any], artifact_name: str, supported: set[str]) -> None:
    schema = str(payload.get("schema_version") or "")
    if schema not in supported:
        raise RuntimeTestError(
            f"unsupported {artifact_name} schema_version: {schema or '<missing>'}",
            status="TEST_INVALID",
            exit_code=EXIT_TEST_INVALID,
        )


def latest_backup(evidence_root: Path) -> dict[str, Any]:
    root = backups_root(evidence_root)
    if not root.exists():
        return {}
    manifests = sorted(root.glob("*/backup_manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not manifests:
        return {}
    payload = read_json(manifests[0])
    validate_schema(
        payload=payload,
        artifact_name="runtime test backup manifest",
        supported=SUPPORTED_BACKUP_MANIFEST_SCHEMA_VERSIONS,
    )
    return payload


def latest_run(evidence_root: Path) -> dict[str, Any]:
    root = runs_root(evidence_root)
    if not root.exists():
        return {}
    states = sorted(root.glob("*/run_state.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not states:
        return {}
    payload = read_json(states[0])
    validate_schema(
        payload=payload,
        artifact_name="runtime test run state",
        supported=SUPPORTED_RUN_STATE_SCHEMA_VERSIONS,
    )
    return payload


def active_run_for_profile(evidence_root: Path, *, profile_id: str) -> dict[str, Any]:
    root = runs_root(evidence_root)
    if not root.exists():
        return {}
    states = sorted(root.glob("*/run_state.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for state_path in states:
        payload = read_json(state_path)
        validate_schema(
            payload=payload,
            artifact_name="runtime test run state",
            supported=SUPPORTED_RUN_STATE_SCHEMA_VERSIONS,
        )
        run_profile_id = str(payload.get("profile_id") or "")
        if run_profile_id and run_profile_id != profile_id:
            continue
        run_id = str(payload.get("run_id") or state_path.parent.name)
        if is_run_closed(evidence_root=evidence_root, run_id=run_id):
            continue
        if str(payload.get("status") or "") in {"RUNNING", "HALT"}:
            return payload
    return {}


def is_run_closed(*, evidence_root: Path, run_id: str) -> bool:
    final_summary_path = runs_root(evidence_root) / run_id / "final_summary.json"
    if final_summary_path.exists():
        try:
            payload = read_json(final_summary_path)
            validate_schema(
                payload=payload,
                artifact_name="runtime test final summary",
                supported={FINAL_SUMMARY_SCHEMA_VERSION},
            )
        except Exception:
            payload = {}
        if bool(payload.get("closed_at")):
            return True
        if bool(payload.get("abandoned_at")):
            return True
        if str(payload.get("status") or "") == "ABANDONED":
            return True
    return is_run_abandoned(evidence_root=evidence_root, run_id=run_id)


def is_run_abandoned(*, evidence_root: Path, run_id: str) -> bool:
    abandonment = load_abandonment(evidence_root=evidence_root, run_id=run_id)
    return bool(abandonment.get("abandoned_at")) and bool(abandonment.get("resume_disabled", True))


def load_abandonment(*, evidence_root: Path, run_id: str) -> dict[str, Any]:
    path = runs_root(evidence_root) / run_id / "abandonment.json"
    if not path.exists():
        return {}
    try:
        payload = read_json(path)
    except Exception:
        return {}
    if str(payload.get("run_id") or "") != run_id:
        return {}
    return payload


def backups_root(evidence_root: Path) -> Path:
    return evidence_root / "backups"


def runs_root(evidence_root: Path) -> Path:
    return evidence_root / "runs"


def source_baseline(runtime_root: Path) -> dict[str, Any]:
    return {
        "source_commit": git_commit(),
        "source_dirty": source_dirty(),
        "registry_hash": directory_hash(runtime_root / "artifact_registry") if (runtime_root / "artifact_registry").exists() else "",
        "accepted_artifact_hash": accepted_artifact_hash(runtime_root),
        "captured_at": utc_now(),
    }


def state_hashes(runtime_root: Path) -> dict[str, str]:
    paths = {
        "current": runtime_root / "persistent_ledger" / "state.json",
        "pending": runtime_root / "pending_order_plan" / "pending_order_plan.json",
        "runtime_state": runtime_root / "runtime_state" / "current_state.json",
        "ledger": runtime_root / "persistent_ledger",
    }
    return {name: file_ref(path, root=runtime_root).get("sha256", "") for name, path in paths.items()}


def write_final_state_snapshot(*, run_dir: Path, runtime_root: Path) -> dict[str, Any]:
    snapshot_root = run_dir / "final_state_snapshot"
    files = {
        "current_state": runtime_root / "persistent_ledger" / "state.json",
        "pending_order_plan": runtime_root / "pending_order_plan" / "pending_order_plan.json",
        "runtime_current_state": runtime_root / "runtime_state" / "current_state.json",
    }
    entries: dict[str, Any] = {}
    for name, source in files.items():
        if not source.exists():
            entries[name] = {"source_path": str(source), "snapshot_path": "", "exists": False, "sha256": ""}
            continue
        target = snapshot_root / source.relative_to(runtime_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        entries[name] = {
            "source_path": str(source),
            "snapshot_path": str(target),
            "exists": True,
            "sha256": sha256_file(target),
        }
    manifest = {
        "schema_version": "runtime_test_final_state_snapshot_v1",
        "status": "AVAILABLE" if entries.get("current_state", {}).get("exists") else "CURRENT_STATE_MISSING",
        "generated_at": utc_now(),
        "state_hashes": state_hashes(runtime_root),
        "files": entries,
    }
    write_json_atomic(snapshot_root / "manifest.json", manifest)
    return manifest


def _load_verified_final_state_snapshot(*, run_dir: Path, final_summary: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    snapshot = final_summary.get("final_state_snapshot") if isinstance(final_summary.get("final_state_snapshot"), dict) else {}
    manifest_path = Path(str(snapshot.get("manifest_path") or run_dir / "final_state_snapshot" / "manifest.json"))
    manifest = read_json_optional(manifest_path)
    if not manifest:
        return {}, {"status": "NOT_RETAINED", "manifest_path": str(manifest_path)}
    current_entry = ((manifest.get("files") or {}).get("current_state") or {}) if isinstance(manifest.get("files"), dict) else {}
    snapshot_path = Path(str(current_entry.get("snapshot_path") or ""))
    if not snapshot_path.exists():
        return {}, {"status": "SNAPSHOT_CURRENT_STATE_MISSING", "manifest_path": str(manifest_path), "snapshot_path": str(snapshot_path)}
    expected = str(current_entry.get("sha256") or "")
    actual = sha256_file(snapshot_path)
    if expected and actual != expected:
        return {}, {
            "status": "SNAPSHOT_CURRENT_STATE_HASH_MISMATCH",
            "manifest_path": str(manifest_path),
            "snapshot_path": str(snapshot_path),
            "expected_sha256": expected,
            "actual_sha256": actual,
        }
    payload = read_json_optional(snapshot_path)
    if not payload:
        return {}, {"status": "SNAPSHOT_CURRENT_STATE_JSON_INVALID", "manifest_path": str(manifest_path), "snapshot_path": str(snapshot_path)}
    return payload, {
        "status": "RUN_SCOPED_FINAL_STATE_SNAPSHOT_VERIFIED",
        "manifest_path": str(manifest_path),
        "snapshot_path": str(snapshot_path),
        "sha256": actual,
    }


def accepted_artifact_hash(runtime_root: Path) -> str:
    candidates = [
        runtime_root / "artifact_registry" / "index" / "registry_index.json",
        runtime_root / "artifact_registry" / "checkpoints" / "latest.json",
    ]
    refs = [file_ref(path, root=runtime_root) for path in candidates]
    return semantic_hash(refs)


def summarize_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    try:
        payload = read_json(path)
    except Exception as exc:
        return {"path": str(path), "exists": True, "valid": False, "error": str(exc)}
    return {
        "path": str(path),
        "exists": True,
        "schema_version": payload.get("schema_version", ""),
        "state": payload.get("state") or payload.get("status") or "",
        "environment": payload.get("environment") or payload.get("runtime_mode") or "",
        "cash": payload.get("cash"),
        "buying_power": payload.get("buying_power"),
        "positions_count": len(payload.get("positions") or []) if isinstance(payload.get("positions"), list) else 0,
    }


def summarize_ledger(runtime_root: Path) -> dict[str, Any]:
    root = runtime_root / "persistent_ledger"
    files = ["orders.jsonl", "executions.jsonl", "positions.jsonl", "cash.jsonl", "events.jsonl"]
    return {
        name: {
            "exists": (root / name).exists(),
            "records": count_jsonl(root / name),
            "sha256": sha256_file(root / name) if (root / name).exists() else "",
        }
        for name in files
    }


def read_environment(runtime_root: Path) -> str:
    for path in (runtime_root / "runtime_state" / "current_state.json", runtime_root / "persistent_ledger" / "state.json"):
        if path.exists():
            payload = read_json(path)
            env = payload.get("environment") or payload.get("runtime_mode")
            if env:
                return str(env)
    return "UNKNOWN"


def read_runtime_business_date(runtime_root: Path) -> str:
    for path in (runtime_root / "runtime_state" / "current_state.json", runtime_root / "persistent_ledger" / "state.json"):
        if path.exists():
            payload = read_json(path)
            value = payload.get("business_date") or payload.get("as_of")
            if value:
                return str(value)
    return ""


def write_performance_observability_evidence(
    *,
    run_dir: Path,
    runtime_root: Path,
    run_id: str,
    business_date: str,
    job: str,
) -> None:
    if not run_id or not business_date:
        return
    if job in {"morning", "sell_planning", "execution", "current_valuation_refresh"}:
        bundle = _build_performance_observability_bundle(
            run_dir=run_dir,
            runtime_root=runtime_root,
            run_id=run_id,
            business_date=business_date,
        )
        if job in {"execution", "current_valuation_refresh"}:
            write_json_atomic(run_dir / "daily" / business_date / "execution" / "fills.json", bundle["fills"])
            write_json_atomic(run_dir / "daily" / business_date / "execution" / "realized_slices.json", bundle["realized_slices"])
            write_json_atomic(run_dir / "daily" / business_date / "positions" / "position_campaigns.json", bundle["position_campaigns"])
        if job == "sell_planning":
            write_json_atomic(run_dir / "daily" / business_date / "position_management" / "pm_decisions.json", bundle["pm_decisions"])
        if job == "morning":
            write_json_atomic(run_dir / "daily" / business_date / "positions" / "position_campaigns.json", bundle["position_campaigns"])
    if job in {"market_refresh", "current_valuation_refresh", "execution"}:
        write_json_atomic(
            run_dir / "daily" / business_date / "benchmark" / "benchmark_snapshot.json",
            _build_missing_benchmark_snapshot(run_dir=run_dir, runtime_root=runtime_root, run_id=run_id, business_date=business_date),
        )


def _build_performance_observability_bundle(*, run_dir: Path, runtime_root: Path, run_id: str, business_date: str) -> dict[str, Any]:
    executions = _dedupe_execution_rows([row for row in _read_jsonl(runtime_root / "persistent_ledger" / "executions.jsonl") if row.get("record_type") == "execution"])
    plans = _collect_observability_plan_items(runtime_root=runtime_root, business_date=business_date)
    pm_payload = read_json_optional(runtime_root / "runtime_state" / "position_management" / business_date / "position_management_decisions.json")
    pm_status = _pm_artifact_status(pm_payload)
    state = read_json_optional(runtime_root / "persistent_ledger" / "state.json")
    campaign_state = _derive_position_campaign_state(
        run_id=run_id,
        business_date=business_date,
        executions=executions,
        plans=plans,
        current_state=state,
    )
    common = _observability_common(run_dir=run_dir, runtime_root=runtime_root, run_id=run_id, business_date=business_date)
    return {
        "fills": {
            **common,
            "schema_version": "runtime_fill_observability.v1",
            "fills": _build_fill_rows(
                run_id=run_id,
                business_date=business_date,
                executions=executions,
                execution_campaign_ids=campaign_state["execution_campaign_ids"],
                plans=plans,
            ),
        },
        "realized_slices": {
            **common,
            "schema_version": "realized_slice_observability.v1",
            "cost_basis_method": "AVERAGE_COST_RUNTIME_OWNED_FILL_PROJECTION",
            "lot_level_status": "MISSING_STABLE_LOT_ID_NOT_AVAILABLE",
            "realized_slices": campaign_state["realized_slices"],
        },
        "position_campaigns": {
            **common,
            "schema_version": "position_campaign_observability.v1",
            "identity_policy": "RUN_SCOPED_DETERMINISTIC_EXECUTION_REPLAY_SYMBOL_SEQUENCE",
            "symbol_only_identity": "PROHIBITED",
            "position_campaigns": campaign_state["campaigns"],
        },
        "pm_decisions": {
            **common,
            "schema_version": "pm_decision_snapshot.v1",
            "snapshot_policy": "DECISION_TIME_ONLY_NO_POST_HOC_OUTCOMES",
            "source_status": "AVAILABLE" if pm_payload else "NOT_RETAINED",
            **pm_status,
            "pm_status": pm_status["position_management_status"],
            "pm_authority_status": pm_status["position_management_authority_status"],
            "pm_input_schema_status": pm_status["position_management_input_status"],
            "pm_reason": pm_status["position_management_reason"],
            "pm_decision_count": pm_status["position_management_decision_count"],
            "pm_trace_status": pm_status["position_management_trace_status"],
            "decisions": _build_pm_decision_snapshots(
                run_id=run_id,
                business_date=business_date,
                pm_payload=pm_payload,
                campaign_by_symbol=campaign_state["active_campaign_by_symbol"],
                source_path=runtime_root / "runtime_state" / "position_management" / business_date / "position_management_decisions.json",
            ),
        },
    }


def _dedupe_execution_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        key = _execution_key(row)
        if not key:
            key = f"row-index:{index}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _observability_common(*, run_dir: Path, runtime_root: Path, run_id: str, business_date: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "business_date": business_date,
        "authority": "RUNTIME_TEST_RUN_SCOPED_OBSERVABILITY_EVIDENCE",
        "contract_version": PERFORMANCE_OBSERVABILITY_CONTRACT_VERSION,
        "generated_at": utc_now(),
        "source_artifacts": {
            "run_dir": str(run_dir),
            "runtime_root": str(runtime_root),
        },
        "temporal_safety": {
            "decision_time_evidence": "SEPARATED",
            "execution_time_evidence": "SEPARATED",
            "eod_valuation": "SEPARATED",
            "post_hoc_attribution": "NOT_WRITTEN_TO_DECISION_SNAPSHOT",
        },
    }


def _collect_observability_plan_items(*, runtime_root: Path, business_date: str) -> dict[str, list[dict[str, Any]]]:
    result = {"buy": [], "sell": []}
    for side, rel in (("buy", "morning_pipeline"), ("sell", "sell_pipeline")):
        path = runtime_root / "runtime_state" / rel / business_date / "order_plan.json"
        payload = read_json_optional(path)
        for item in _items(payload):
            if isinstance(item, dict):
                result[side].append({**item, "_artifact_path": str(path), "_plan_date": business_date})
    return result


def _derive_position_campaign_state(
    *,
    run_id: str,
    business_date: str,
    executions: list[dict[str, Any]],
    plans: dict[str, list[dict[str, Any]]],
    current_state: dict[str, Any],
) -> dict[str, Any]:
    positions: dict[str, dict[str, Any]] = defaultdict(lambda: {"quantity": 0.0, "cost": 0.0, "campaign_index": 0, "campaign_id": ""})
    campaigns: dict[str, dict[str, Any]] = {}
    execution_campaign_ids: dict[str, str] = {}
    realized_slices: list[dict[str, Any]] = []
    current_positions = {str(row.get("symbol") or ""): row for row in current_state.get("positions") or [] if isinstance(row, dict)}
    sequenced = [
        (index, row)
        for index, row in enumerate(executions)
        if str(row.get("business_date") or "") <= business_date
    ]
    ordered = [
        row
        for _, row in sorted(
            sequenced,
            key=lambda item: (
                str(item[1].get("business_date") or ""),
                str(item[1].get("executed_at") or ""),
                item[0],
            ),
        )
    ]
    for row in ordered:
        symbol = str(row.get("symbol") or row.get("broker_issue_code") or "")
        if not symbol:
            continue
        side = str(row.get("side") or "").upper()
        qty = _float(row.get("filled_quantity") or row.get("quantity"))
        price = _float(row.get("price") or row.get("average_price") or row.get("market_price"), default=-1.0)
        if qty <= 0 or price < 0:
            continue
        state = positions[symbol]
        if side == "BUY":
            if state["quantity"] <= POSITION_QUANTITY_EPSILON:
                state["campaign_index"] += 1
                state["campaign_id"] = _position_campaign_id(run_id=run_id, symbol=symbol, sequence=int(state["campaign_index"]))
                campaigns[state["campaign_id"]] = _new_campaign(row=row, run_id=run_id, business_date=business_date, symbol=symbol, campaign_id=state["campaign_id"], plans=plans)
            campaign = campaigns[state["campaign_id"]]
            old_quantity = _float(state["quantity"])
            state["quantity"] = old_quantity + qty
            state["cost"] = _float(state["cost"]) + qty * price
            campaign["current_quantity"] = state["quantity"]
            campaign["average_cost"] = state["cost"] / state["quantity"] if state["quantity"] > 0 else _missing_value()
            campaign["buy_notional"] = _float(campaign.get("buy_notional")) + qty * price
            campaign["events"].append(_campaign_event(row=row, stage="BUY" if old_quantity <= 0 else "ADD", campaign_id=state["campaign_id"], realized_slice_id=""))
            execution_campaign_ids[_execution_key(row)] = state["campaign_id"]
            continue
        if side != "SELL":
            continue
        campaign_id = str(state.get("campaign_id") or "")
        execution_campaign_ids[_execution_key(row)] = campaign_id
        if not campaign_id or campaign_id not in campaigns:
            continue
        average_cost = state["cost"] / state["quantity"] if state["quantity"] > 0 else 0.0
        sell_quantity = min(qty, _float(state["quantity"]))
        allocated_cost = average_cost * sell_quantity
        gross_pnl = (price - average_cost) * sell_quantity
        state["quantity"] = max(_float(state["quantity"]) - sell_quantity, 0.0)
        if state["quantity"] <= POSITION_QUANTITY_EPSILON:
            state["quantity"] = 0.0
        state["cost"] = max(_float(state["cost"]) - allocated_cost, 0.0)
        if state["quantity"] <= POSITION_QUANTITY_EPSILON:
            state["cost"] = 0.0
        campaign = campaigns[campaign_id]
        slice_id = f"realized-slice-{_short_hash('|'.join((campaign_id, _execution_key(row), str(len(realized_slices) + 1))))}"
        source = _execution_source_decision(row=row, plans=plans)
        slice_row = {
            "realized_slice_id": slice_id,
            "position_campaign_id": campaign_id,
            "symbol": symbol,
            "business_date": str(row.get("business_date") or ""),
            "sell_execution_id": row.get("execution_id") or row.get("record_id") or row.get("execution_ref") or "",
            "sell_quantity": sell_quantity,
            "sell_price": price,
            "cost_basis_method": "AVERAGE_COST_RUNTIME_OWNED_FILL_PROJECTION",
            "allocated_cost_basis": allocated_cost,
            "gross_realized_pnl": gross_pnl,
            "fees": _missing_value(),
            "tax": _missing_value(),
            "net_realized_pnl": _missing_value(),
            "remaining_quantity": state["quantity"],
            "remaining_average_cost": (state["cost"] / state["quantity"]) if state["quantity"] > 0 else 0.0,
            "source_decision_type": source["source_decision_type"],
            "source_decision_id": source["source_decision_id"],
        }
        if str(row.get("business_date") or "") == business_date:
            realized_slices.append(slice_row)
        campaign["realized_pnl"] = _float(campaign.get("realized_pnl")) + gross_pnl
        campaign["sell_notional"] = _float(campaign.get("sell_notional")) + sell_quantity * price
        campaign["current_quantity"] = state["quantity"]
        campaign["average_cost"] = (state["cost"] / state["quantity"]) if state["quantity"] > 0 else 0.0
        campaign["campaign_status"] = "CLOSED" if state["quantity"] <= POSITION_QUANTITY_EPSILON else "OPEN"
        campaign["events"].append(_campaign_event(row=row, stage=source["source_decision_type"] if source["source_decision_type"] in {"REDUCE", "EXIT"} else "SELL", campaign_id=campaign_id, realized_slice_id=slice_id))
    for campaign in campaigns.values():
        symbol = str(campaign.get("symbol") or "")
        pos = current_positions.get(symbol, {}) if campaign.get("campaign_status") == "OPEN" else {}
        campaign["unrealized_pnl"] = pos.get("unrealized_pnl", 0.0 if campaign.get("campaign_status") == "CLOSED" else "MISSING")
        campaign["total_campaign_pnl"] = (
            _float(campaign.get("realized_pnl")) + _float(campaign.get("unrealized_pnl"))
            if campaign.get("unrealized_pnl") not in ("MISSING", None, "")
            else "MISSING"
        )
        campaign["limitations"] = ["Stable lot_id is not available; realized_slice is the formal realized PnL unit."]
    active_by_symbol = {
        str(campaign.get("symbol") or ""): str(campaign.get("position_campaign_id") or "")
        for campaign in campaigns.values()
        if campaign.get("campaign_status") == "OPEN"
    }
    return {
        "campaigns": sorted(campaigns.values(), key=lambda row: (str(row.get("symbol") or ""), str(row.get("position_campaign_id") or ""))),
        "realized_slices": realized_slices,
        "execution_campaign_ids": execution_campaign_ids,
        "active_campaign_by_symbol": active_by_symbol,
    }


def _position_campaign_id(*, run_id: str, symbol: str, sequence: int) -> str:
    return f"pc-{_short_hash(run_id)}-{symbol}-{sequence:04d}"


def _short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _new_campaign(*, row: dict[str, Any], run_id: str, business_date: str, symbol: str, campaign_id: str, plans: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    source = _execution_source_decision(row=row, plans=plans)
    return {
        "position_campaign_id": campaign_id,
        "run_id": run_id,
        "symbol": symbol,
        "campaign_status": "OPEN",
        "opened_business_date": str(row.get("business_date") or business_date),
        "closed_business_date": "",
        "current_quantity": 0.0,
        "average_cost": _missing_value(),
        "buy_notional": 0.0,
        "sell_notional": 0.0,
        "realized_pnl": 0.0,
        "unrealized_pnl": "MISSING",
        "total_campaign_pnl": "MISSING",
        "buy_observability": source,
        "events": [],
    }


def _campaign_event(*, row: dict[str, Any], stage: str, campaign_id: str, realized_slice_id: str) -> dict[str, Any]:
    source = _execution_source_decision(row=row, plans={})
    return {
        "business_date": str(row.get("business_date") or ""),
        "stage": stage,
        "position_campaign_id": campaign_id,
        "symbol": str(row.get("symbol") or row.get("broker_issue_code") or ""),
        "side": str(row.get("side") or "").upper(),
        "quantity": _float(row.get("filled_quantity") or row.get("quantity")),
        "price": _float(row.get("price") or row.get("average_price") or row.get("market_price")),
        "execution_id": row.get("execution_id") or row.get("record_id") or row.get("execution_ref") or "",
        "realized_slice_id": realized_slice_id,
        "pending_item_id": row.get("pending_item_id") or source["pending_item_id"],
        "order_plan_item_id": row.get("order_plan_item_id") or source["order_plan_item_id"],
        "quality_decision_id": row.get("quality_decision_id") or source["quality_decision_id"],
        "evidence_type": "execution-time evidence",
    }


def _execution_key(row: dict[str, Any]) -> str:
    return str(row.get("execution_id") or row.get("record_id") or row.get("execution_ref") or row.get("execution_key") or _short_hash(json.dumps(row, sort_keys=True, default=str)))


def _execution_source_decision(*, row: dict[str, Any], plans: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    side = str(row.get("side") or "").upper()
    symbol = str(row.get("symbol") or row.get("broker_issue_code") or "")
    business_date = str(row.get("business_date") or "")
    pending_item_id = str(row.get("pending_item_id") or "")
    if pending_item_id == "MISSING":
        pending_item_id = ""
    candidates = plans.get("sell" if side == "SELL" else "buy", [])
    matched = {}
    symbol_candidates = [item for item in candidates if not symbol or str(item.get("symbol") or "") == symbol]
    if pending_item_id:
        matched = next((item for item in symbol_candidates if str(item.get("pending_item_id") or "") == pending_item_id), {})
    if not matched and business_date:
        matched = next((item for item in symbol_candidates if str(item.get("_plan_date") or item.get("business_date") or "") == business_date), {})
    contract = matched.get("quantity_contract") if isinstance(matched.get("quantity_contract"), dict) else {}
    quality_authority = contract.get("buy_quality_authority") if isinstance(contract.get("buy_quality_authority"), dict) else {}
    source_decision = str(contract.get("source_decision") or ("BUY" if side == "BUY" else "MISSING"))
    return {
        "source_decision_type": source_decision,
        "source_decision_id": matched.get("source_decision_id") or contract.get("source_decision_id") or contract.get("source_planning_id") or matched.get("decision_id") or "MISSING",
        "order_plan_item_id": matched.get("order_plan_item_id") or matched.get("plan_item_id") or contract.get("source_planning_id") or "MISSING",
        "pending_item_id": pending_item_id or matched.get("pending_item_id") or "MISSING",
        "order_id": row.get("order_id") or row.get("order_ref") or "MISSING",
        "quality_decision_id": matched.get("quality_decision_id") or contract.get("quality_decision_id") or quality_authority.get("quality_decision_id") or "MISSING",
    }


def _build_fill_rows(
    *,
    run_id: str,
    business_date: str,
    executions: list[dict[str, Any]],
    execution_campaign_ids: dict[str, str],
    plans: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in executions:
        if str(row.get("business_date") or "") != business_date:
            continue
        qty = _float(row.get("filled_quantity") or row.get("quantity"))
        price = _float(row.get("price") or row.get("average_price") or row.get("market_price"), default=-1.0)
        side = str(row.get("side") or "").upper()
        notional = qty * price if qty > 0 and price >= 0 else None
        source = _execution_source_decision(row=row, plans=plans)
        rows.append(
            {
                "run_id": run_id,
                "business_date": business_date,
                "position_campaign_id": execution_campaign_ids.get(_execution_key(row)) or "MISSING",
                "symbol": row.get("symbol") or row.get("broker_issue_code") or "",
                "side": side,
                "execution_id": row.get("execution_id") or row.get("record_id") or row.get("execution_ref") or "",
                "order_id": source["order_id"],
                "order_plan_item_id": source["order_plan_item_id"],
                "pending_item_id": source["pending_item_id"],
                "quantity": qty,
                "execution_price": price if price >= 0 else _missing_value(),
                "gross_notional": _status_value(notional, "DERIVABLE_EXACT"),
                "fees": _missing_value(),
                "tax": _missing_value(),
                "slippage": _missing_value(),
                "cash_effect": _status_value((-notional if side == "BUY" else notional) if notional is not None else None, "DERIVABLE_EXACT"),
                "source_decision_type": source["source_decision_type"],
                "source_decision_id": source["source_decision_id"],
                "quality_decision_id": source["quality_decision_id"],
            }
        )
    return rows


def _build_pm_decision_snapshots(
    *,
    run_id: str,
    business_date: str,
    pm_payload: dict[str, Any],
    campaign_by_symbol: dict[str, str],
    source_path: Path,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for decision in pm_payload.get("decisions") or []:
        if not isinstance(decision, dict):
            continue
        symbol = str(decision.get("symbol") or "")
        decision_type = decision.get("decision") or "MISSING"
        trace = decision.get("decision_trace") if isinstance(decision.get("decision_trace"), dict) else {}
        position_state = trace.get("position_state") if isinstance(trace.get("position_state"), dict) else {}
        rows.append(
            {
                "run_id": run_id,
                "business_date": business_date,
                "position_campaign_id": campaign_by_symbol.get(symbol) or "MISSING",
                "symbol": symbol,
                "pm_decision_id": decision.get("decision_id") or "MISSING",
                "decision_type": decision_type,
                "decision_reason": decision.get("reason") or "MISSING",
                "reason_codes": decision.get("decision_reason_codes")
                or [part for part in str(decision.get("reason") or "").replace(";", "|").split("|") if part],
                "dominant_cause": decision.get("dominant_cause", _missing_value()),
                "secondary_causes": decision.get("secondary_causes", _missing_value()),
                "decision_status": decision.get("status") or decision.get("runtime_action") or "MISSING",
                "quantity_before": decision.get("runtime_position_quantity", _missing_value()),
                "quantity_requested": _pm_quantity_requested_snapshot(decision=decision, decision_type=str(decision_type)),
                "quantity_after_expected": _missing_value(),
                "average_cost": position_state.get("average_price", decision.get("average_price", decision.get("entry_price", _missing_value()))),
                "current_price": position_state.get("current_price", decision.get("current_price", _missing_value())),
                "market_value": position_state.get("market_value", decision.get("market_value", _missing_value())),
                "unrealized_pnl": position_state.get("unrealized_pnl", decision.get("unrealized_pnl", _missing_value())),
                "realized_pnl_to_date": _missing_value(),
                "confidence": decision.get("confidence", _missing_value()),
                "confidence_semantics": decision.get("confidence_semantics", _missing_value()),
                "action_score": decision.get("action_score", _missing_value()),
                "thresholds": decision.get("thresholds", _missing_value()),
                "feature_snapshot_ref": decision.get("feature_snapshot_ref", trace.get("input_authority", {}).get("feature_snapshot_ref", _missing_value())),
                "feature_business_date": decision.get("feature_business_date", trace.get("feature_business_date", decision.get("feature_date", _missing_value()))),
                "current_position_ref": str(source_path),
                "generation_id": decision.get("generation_id", _missing_value()),
                "generated_at": decision.get("generated_at", _missing_value()),
                "temporal_classification": "DECISION_TIME_EVIDENCE_ONLY",
            }
        )
    return rows


def _pm_quantity_requested_snapshot(*, decision: dict[str, Any], decision_type: str) -> Any:
    if str(decision_type or "").upper() != "REDUCE":
        return decision.get("runtime_sell_quantity", _missing_value())
    authority = str(decision.get("runtime_quantity_authority") or "")
    action = str(decision.get("runtime_action") or "")
    sell_quantity = decision.get("runtime_sell_quantity", _missing_value())
    if authority == "SELL_PLANNING_REDUCE_QUANTITY_CONTRACT" or action == "SELL_PARTIAL_POSITION_REDUCE_QUANTITY_BY_SELL_PLANNING":
        return {
            "value": "DELEGATED_TO_SELL_PLANNING",
            "status": "NOT_SPECIFIED_BY_PM",
            "raw_runtime_sell_quantity": sell_quantity,
            "quantity_authority": authority or "SELL_PLANNING_REDUCE_QUANTITY_CONTRACT",
            "reason": "PM_REDUCE_INTENT_SELL_PLANNING_OWNS_EXECUTABLE_QUANTITY",
        }
    return sell_quantity


def _build_missing_benchmark_snapshot(*, run_dir: Path, runtime_root: Path, run_id: str, business_date: str) -> dict[str, Any]:
    payload = _observability_common(run_dir=run_dir, runtime_root=runtime_root, run_id=run_id, business_date=business_date)
    payload.update(
        {
            "schema_version": "benchmark_snapshot_observability.v1",
            "status": "MISSING",
            "benchmark_id": "TOPIX_TOTAL_OR_PRICE_RETURN_JQUANTS_COMPATIBLE",
            "benchmark_name": "TOPIX",
            "benchmark_source": "NOT_CONFIRMED",
            "benchmark_implementation": "NOT_PERFORMED",
            "required_decision": "USER_OR_ARCHITECTURE_APPROVAL",
            "close": _missing_value(),
            "daily_return": _missing_value(),
            "normalized_value": _missing_value(),
            "consumer_cutoff": _missing_value(),
            "future_rows_consumed": False,
            "source_hash": _missing_value(),
        }
    )
    return payload


def _runtime_test_job_terminate_grace_seconds() -> float:
    return _float_env(RUNTIME_TEST_JOB_TERMINATE_GRACE_ENV, RUNTIME_TEST_JOB_DEFAULT_TERMINATE_GRACE_SECONDS)


def _float_env(name: str, default: float) -> float:
    raw = str(os.environ.get(name, "") or "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return max(value, 0.0)


def run_runtime_cli(
    command: list[str],
    *,
    cwd: Path,
    trace_path: Path | None = None,
    context: dict[str, Any] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = env.get("PYTHONPATH") or "src"
    grace_seconds = _runtime_test_job_terminate_grace_seconds()
    started_at = utc_now()
    started_monotonic = time.monotonic()
    trace = {
        "schema_version": RUNTIME_TEST_SUBPROCESS_TRACE_SCHEMA_VERSION,
        "status": "RUNNING",
        "started_at": started_at,
        "ended_at": "",
        "elapsed_seconds": 0.0,
        "command": command,
        "cwd": str(cwd),
        "pid": None,
        "returncode": None,
        "formal_stall_timeout_contract": "NOT_CONFIGURED",
        "stall_timeout_seconds": None,
        "stall_timeout_reason": "No Architecture/Runbook last-progress heartbeat threshold is defined.",
        "terminate_grace_seconds": grace_seconds,
        "timed_out": False,
        "termination_signal": "",
        "killed_after_grace": False,
        "env_overrides": {"PYTHONPATH": env.get("PYTHONPATH", "")},
        **dict(context or {}),
    }
    if trace_path is not None:
        trace_path.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(command, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    trace["pid"] = process.pid
    if trace_path is not None:
        write_json_atomic(trace_path, trace)
    try:
        stdout, stderr = process.communicate()
        returncode = int(process.returncode or 0)
        trace.update(
            {
                "status": "COMPLETED",
                "ended_at": utc_now(),
                "elapsed_seconds": round(time.monotonic() - started_monotonic, 6),
                "returncode": returncode,
            }
        )
        completed = subprocess.CompletedProcess(command, returncode, stdout or "", stderr or "")
    except KeyboardInterrupt:
        trace.update(
            {
                "status": "INTERRUPTED",
                "interrupted_at": utc_now(),
                "elapsed_seconds": round(time.monotonic() - started_monotonic, 6),
                "termination_signal": "SIGTERM",
            }
        )
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=grace_seconds if grace_seconds > 0 else 0.0)
        except subprocess.TimeoutExpired:
            trace["killed_after_grace"] = True
            trace["termination_signal"] = "SIGKILL_AFTER_SIGTERM"
            process.kill()
            stdout, stderr = process.communicate()
        trace.update(
            {
                "ended_at": utc_now(),
                "elapsed_seconds": round(time.monotonic() - started_monotonic, 6),
                "returncode": int(process.returncode or 130),
            }
        )
        if trace_path is not None:
            write_json_atomic(trace_path, trace)
        raise
    if trace_path is not None:
        write_json_atomic(trace_path, trace)
    setattr(completed, "runtime_test_subprocess_trace", trace)
    return completed


def _invoke_runtime_cli_job(
    command: list[str],
    *,
    cwd: Path,
    trace_path: Path,
    context: dict[str, Any],
) -> subprocess.CompletedProcess[str]:
    try:
        return run_runtime_cli(command, cwd=cwd, trace_path=trace_path, context=context)
    except TypeError as exc:
        if "unexpected keyword argument" not in str(exc):
            raise
        return run_runtime_cli(command, cwd=cwd)


def collect_runtime_cli_job_evidence(
    *,
    completed: subprocess.CompletedProcess[str],
    run_dir: Path,
    runtime_root: Path,
    business_date: str,
    job: str,
) -> None:
    job_dir = run_dir / "daily" / business_date / job
    job_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = runtime_cli_manifest_path(completed.stdout)
    copied_manifest = ""
    copied_log = ""
    run_id = ""
    if manifest_path and manifest_path.is_file():
        copied_manifest_path = job_dir / "runtime_manifest.json"
        shutil.copy2(manifest_path, copied_manifest_path)
        copied_manifest = str(copied_manifest_path)
        try:
            manifest = read_json(manifest_path)
            run_id = str(manifest.get("run_id") or "")
        except (OSError, json.JSONDecodeError):
            run_id = ""
    if run_id:
        log_path = runtime_root / "runtime_state" / "logs" / business_date / f"{run_id}.log"
        if log_path.is_file():
            copied_log_path = job_dir / "runtime_log.log"
            shutil.copy2(log_path, copied_log_path)
            copied_log = str(copied_log_path)
    write_json_atomic(
        job_dir / "cli_result.json",
        {
            "schema_version": "runtime_test_cli_job_evidence_v1",
            "business_date": business_date,
            "job": job,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "subprocess_trace": getattr(completed, "runtime_test_subprocess_trace", {}),
            "source_manifest_path": str(manifest_path) if manifest_path else "",
            "runtime_manifest_copied": bool(copied_manifest),
            "runtime_manifest_path": copied_manifest,
            "runtime_log_copied": bool(copied_log),
            "runtime_log_path": copied_log,
        },
    )


def classify_scoped_buy_only_result(
    *,
    run_dir: Path,
    business_date: str,
    job: str,
    exit_code: int,
) -> dict[str, Any] | None:
    if exit_code == 0 or job != "morning":
        return None
    job_dir = run_dir / "daily" / business_date / job
    manifest_path = job_dir / "runtime_manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        manifest = read_json(manifest_path)
    except (OSError, json.JSONDecodeError):
        return None
    gate = manifest.get("ai_lifecycle_gate") if isinstance(manifest.get("ai_lifecycle_gate"), dict) else {}
    if not gate:
        gate = _stage_details(manifest, "candidate_opportunity_ai_runtime_producer").get("ai_lifecycle_gate", {})
        if not isinstance(gate, dict):
            gate = {}
    decision = str(gate.get("decision") or manifest.get("ai_lifecycle_gate_decision") or "").upper()
    classification = str(gate.get("classification") or manifest.get("ai_lifecycle_gate_classification") or "").upper()
    status = "REVIEW_REQUIRED_BUY_ONLY" if decision == "REVIEW_REQUIRED" else ("BLOCKED_BUY_ONLY" if decision == "BLOCK" else "")
    continuity = _stage_details(manifest, "buy_lifecycle_sell_continuity")
    authorization = _stage_details(manifest, "buy_lifecycle_sell_authorization_continuity")
    checks = {
        "runtime_cli_nonzero": exit_code != 0,
        "morning_job": job == "morning",
        "known_lifecycle_decision": decision in {"REVIEW_REQUIRED", "BLOCK"},
        "not_critical_authority_violation": classification != "CRITICAL_AUTHORITY_VIOLATION",
        "block_buy_planning": _bool_field(gate, manifest, "block_buy_planning", "ai_lifecycle_gate_block_buy_planning"),
        "block_buy_submit": _bool_field(gate, manifest, "block_buy_submit", "ai_lifecycle_gate_block_buy_submit"),
        "does_not_block_sell_planning": not _bool_field(gate, manifest, "block_sell_planning", "ai_lifecycle_gate_block_sell_planning"),
        "does_not_block_sell_submit": not _bool_field(gate, manifest, "block_sell_submit", "ai_lifecycle_gate_block_sell_submit"),
        "sell_planning_permission_pass": _str_field(gate, manifest, "sell_planning_permission") == "PASS",
        "sell_submit_authorization_permission_pass": _str_field(gate, manifest, "sell_submit_authorization_permission") == "PASS",
        "sell_continuity_pass": continuity.get("status") == "PASS",
        "sell_authorization_continuity_pass": authorization.get("status") == "PASS",
        "call_graph_reached": bool(authorization.get("call_graph_reached")),
        "no_broker_write": not bool(continuity.get("broker_write_performed")) and not bool(authorization.get("broker_write_performed")),
    }
    if not status or not all(checks.values()):
        return None
    result = {
        "schema_version": "runtime_test_scoped_buy_only_continuation_v1",
        "status": status,
        "scope": "BUY_ONLY",
        "business_date": business_date,
        "job": job,
        "runtime_cli_exit_code": exit_code,
        "runtime_manifest_path": str(manifest_path),
        "decision": decision,
        "classification": classification,
        "checks": checks,
        "reason": "runtime_lifecycle_gate_block_is_scoped_to_buy_planning_and_submit",
    }
    write_json_atomic(job_dir / "scoped_block_continuation.json", result)
    return result


def _stage_details(manifest: dict[str, Any], name: str) -> dict[str, Any]:
    for stage in manifest.get("stages") or []:
        if not isinstance(stage, dict) or stage.get("name") != name:
            continue
        details = stage.get("details")
        if isinstance(details, dict):
            payload = dict(details)
            payload.setdefault("status", stage.get("status"))
            return payload
        return {"status": stage.get("status")}
    return {}


def _bool_field(gate: dict[str, Any], manifest: dict[str, Any], gate_key: str, manifest_key: str) -> bool:
    if gate_key in gate:
        return bool(gate.get(gate_key))
    return bool(manifest.get(manifest_key))


def _str_field(gate: dict[str, Any], manifest: dict[str, Any], key: str) -> str:
    value = gate.get(key)
    if value is None:
        value = manifest.get(f"ai_lifecycle_gate_{key}")
    if value is None:
        value = manifest.get(key)
    return str(value or "").upper()


def runtime_cli_manifest_path(stdout: str) -> Path | None:
    for line in reversed(stdout.splitlines()):
        text = line.strip()
        if not text.startswith("{"):
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        manifest = payload.get("manifest")
        if isinstance(manifest, str) and manifest:
            return Path(manifest)
    return None


def _initial_fresh_run_steps() -> dict[str, dict[str, Any]]:
    return {name: _fresh_step(name, "NOT_EXECUTED", {}) for name in ("status", "backup", "reset", "plan", "run", "validate", "close")}


def _fresh_step(name: str, status: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "step": name,
        "status": status,
        "exit_code": int(payload.get("exit_code", next((code for code, value in EXIT_CODES.items() if value == status), EXIT_PASS))),
        "run_id": payload.get("run_id") or "",
        "backup_id": payload.get("backup_id") or "",
        "evidence_path": payload.get("evidence_path") or payload.get("backup_path") or "",
        "summary": _fresh_step_summary(payload),
    }


def _fresh_step_summary(payload: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "runtime_root",
        "current_environment",
        "active_test_run",
        "run_status",
        "accepted_artifact_hash",
        "latest_backup",
        "bundle_hash",
        "clean_state_invariant",
        "requested_business_days",
        "requested_start_date",
        "requested_end_date",
        "profile_start_date",
        "selected_start_date",
        "selection_authority",
        "override_applied",
        "override_reason",
        "resolved_business_day_count",
        "resolved_date_from",
        "resolved_date_to",
        "window_resolution_status",
        "window_resolution_reason",
        "request_conformance_status",
        "unresolved_requested_dates",
        "job_sequence",
        "completed_business_days",
        "checks",
        "test_validity_judgment",
        "acceptance_gate_judgment",
        "error",
    )
    return {key: payload[key] for key in keys if key in payload}


def _fresh_run_dry_run_steps(*, profile: dict[str, Any], runtime_root: Path, evidence_root: Path, plan_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    steps = _initial_fresh_run_steps()
    steps["status"] = _fresh_step("status", "PLANNED_READ_ONLY", {"runtime_root": str(runtime_root), "external_effect_policy": profile["external_effect_policy"]})
    steps["backup"] = _fresh_step("backup", "PLANNED_NO_WRITE", {"target_root": str(backups_root(evidence_root)), "scope": list(RESETTABLE_RELATIVE_PATHS), "excluded_prefixes": list(RESET_EXCLUDED_RELATIVE_PREFIXES)})
    steps["reset"] = _fresh_step("reset", "PLANNED_NO_MUTATION", {"initial_state": profile["initial_state"], "partial_reset_prohibited": True})
    steps["plan"] = _fresh_step("plan", "PLANNED_NO_WRITE", {"run_id": plan_payload["run_id"], "requested_business_days": plan_payload["requested_business_days"], "requested_start_date": plan_payload["requested_start_date"], "requested_end_date": plan_payload["requested_end_date"], "profile_start_date": plan_payload.get("profile_start_date", ""), "selected_start_date": plan_payload.get("selected_start_date", ""), "selection_authority": plan_payload.get("selection_authority", ""), "override_applied": plan_payload.get("override_applied", False), "override_reason": plan_payload.get("override_reason", ""), "resolved_business_day_count": plan_payload.get("resolved_business_day_count", 0), "resolved_date_from": plan_payload.get("resolved_date_from", ""), "resolved_date_to": plan_payload.get("resolved_date_to", ""), "window_resolution_status": plan_payload.get("window_resolution_status", ""), "window_resolution_reason": plan_payload.get("window_resolution_reason", ""), "request_conformance_status": plan_payload.get("request_conformance_status", ""), "unresolved_requested_dates": plan_payload.get("unresolved_requested_dates", []), "job_sequence": plan_payload["job_sequence"], "strategy_shadow": plan_payload.get("strategy_shadow", {})})
    steps["run"] = _fresh_step("run", "PLANNED_NO_EXECUTION", {"job_sequence": plan_payload["job_sequence"], "strategy_shadow_execution_order": (plan_payload.get("strategy_shadow") or {}).get("execution_order", ""), "runtime_cli_module": RUNTIME_CLI_MODULE})
    steps["validate"] = _fresh_step("validate", "PLANNED_NO_EXECUTION", {"checks": ["Runtime root", "Current", "Pending", "Runtime State", "external effect policy", "run state", "state hashes", "strategy shadow structural evidence"]})
    steps["close"] = _fresh_step("close", "PLANNED_NO_MUTATION", {"final_summary": "planned"})
    return steps


def _fresh_run_authority_snapshot(runtime_root: Path) -> dict[str, Any]:
    registry = runtime_root / "artifact_registry"
    return {
        "runtime_root": str(runtime_root),
        "registry_hash": directory_hash(registry) if registry.exists() else "",
        "registry_checkpoint_hash": file_ref(registry / "checkpoints" / "latest.json", root=runtime_root).get("sha256", ""),
        "accepted_artifact_hash": accepted_artifact_hash(runtime_root),
        "current_hash": file_ref(runtime_root / "persistent_ledger" / "state.json", root=runtime_root).get("sha256", ""),
        "pending_hash": file_ref(runtime_root / "pending_order_plan" / "pending_order_plan.json", root=runtime_root).get("sha256", ""),
        "runtime_state_hash": file_ref(runtime_root / "runtime_state" / "current_state.json", root=runtime_root).get("sha256", ""),
    }


def _fresh_run_summary(
    *,
    fresh_run_id: str,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
    started_at: str,
    status: str,
    exit_code: int,
    steps: dict[str, dict[str, Any]],
    backup_id: str,
    run_id: str,
    plan_payload: dict[str, Any],
    initial_cash: float | None,
    before: dict[str, Any],
    after: dict[str, Any],
    failed_step: str,
    error: str,
    active_run: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any]:
    completed_jobs = _completed_jobs_for_run(evidence_root=evidence_root, run_id=run_id)
    completed_days = _completed_days_for_run(evidence_root=evidence_root, run_id=run_id)
    summary = {
        "schema_version": FRESH_RUN_SUMMARY_SCHEMA_VERSION,
        "subcommand": "fresh-run",
        "fresh_run_id": fresh_run_id,
        "run_id": run_id,
        "profile_id": profile["profile_id"],
        "status": status,
        "final_judgment": status,
        "exit_code": exit_code,
        "started_at": started_at,
        "finished_at": utc_now(),
        "runtime_root": str(runtime_root),
        "evidence_root": str(evidence_root),
        "backup_id": backup_id,
        "date_from": plan_payload.get("requested_start_date") or "",
        "date_to": plan_payload.get("requested_end_date") or "",
        "business_days": int(plan_payload.get("requested_business_days") or 0),
        "requested_business_days": int(plan_payload.get("requested_business_days") or 0),
        "resolved_business_day_count": int(plan_payload.get("resolved_business_day_count") or len(plan_payload.get("business_dates") or [])),
        "resolved_date_from": plan_payload.get("resolved_date_from") or "",
        "resolved_date_to": plan_payload.get("resolved_date_to") or "",
        "completed_business_day_count": len(completed_days),
        "window_resolution_status": plan_payload.get("window_resolution_status") or "",
        "window_resolution_reason": plan_payload.get("window_resolution_reason") or "",
        "request_conformance_status": "PASS" if int(plan_payload.get("requested_business_days") or 0) == len(completed_days) and plan_payload.get("window_resolution_status") == "PASS" else "NOT_PASS",
        "unresolved_requested_dates": list(plan_payload.get("unresolved_requested_dates") or []),
        "independent_acceptance": _independent_acceptance_judgment(
            runtime_execution_status=status,
            requested_business_days=int(plan_payload.get("requested_business_days") or 0),
            resolved_business_day_count=int(plan_payload.get("resolved_business_day_count") or len(plan_payload.get("business_dates") or [])),
            completed_business_day_count=len(completed_days),
            window_resolution_status=str(plan_payload.get("window_resolution_status") or ""),
        ),
        "initial_cash": float(initial_cash if initial_cash is not None else profile["initial_state"]["cash"]),
        "steps": steps,
        "status_result": steps["status"]["status"],
        "backup_result": steps["backup"]["status"],
        "reset_result": steps["reset"]["status"],
        "plan_result": steps["plan"]["status"],
        "run_result": steps["run"]["status"],
        "validate_result": steps["validate"]["status"],
        "close_result": steps["close"]["status"],
        "completed_days": completed_days,
        "completed_jobs": completed_jobs,
        "failed_step": failed_step,
        "halted_step": failed_step,
        "error": error,
        "active_run_conflict": bool(active_run),
        "active_run": active_run,
        "resume_possible": bool(run_id and status in {"HALT", "REVIEW_REQUIRED", "BLOCKED"}),
        "rollback_possible": bool(backup_id and status not in {"PASS", "DRY_RUN"}),
        "recommended_command": _fresh_run_recommended_command(status=status, run_id=run_id, backup_id=backup_id),
        "resume_recommendation": _fresh_run_resume_recommendation(status=status, run_id=run_id),
        "rollback_recommendation": _fresh_run_rollback_recommendation(status=status, backup_id=backup_id),
        "evidence_paths": _fresh_run_evidence_paths(evidence_root=evidence_root, run_id=run_id, fresh_run_id=fresh_run_id),
        "registry_hash_before": before.get("registry_hash", ""),
        "registry_hash_after": after.get("registry_hash", ""),
        "accepted_artifact_hash_before": before.get("accepted_artifact_hash", ""),
        "accepted_artifact_hash_after": after.get("accepted_artifact_hash", ""),
        "registry_unchanged": before.get("registry_hash", "") == after.get("registry_hash", ""),
        "accepted_artifact_unchanged": before.get("accepted_artifact_hash", "") == after.get("accepted_artifact_hash", ""),
        "broker_write_performed": False,
        "external_delivery_performed": False,
        "external_effect_policy": profile["external_effect_policy"],
        "dry_run": dry_run,
        "dry_run_no_mutation": dry_run,
        "existing_run_evidence_preserved": True,
        "automatic_evidence_purge_performed": False,
        "production_profile_rejected": profile.get("mode") != "production",
    }
    return summary


def _completed_jobs_for_run(*, evidence_root: Path, run_id: str) -> list[dict[str, Any]]:
    if not run_id:
        return []
    try:
        return list(load_run_state(evidence_root, run_id).get("completed_jobs") or [])
    except Exception:
        return []


def _completed_days_for_run(*, evidence_root: Path, run_id: str) -> list[str]:
    if not run_id:
        return []
    try:
        return list(load_run_state(evidence_root, run_id).get("completed_business_days") or [])
    except Exception:
        return []


def _fresh_run_recommended_command(*, status: str, run_id: str, backup_id: str) -> str:
    if status == "PASS":
        return f"PYTHONPATH=src python3 scripts/runtime_test.py show --run-id {run_id}" if run_id else ""
    if run_id and status in {"HALT", "REVIEW_REQUIRED", "BLOCKED"}:
        return f"PYTHONPATH=src python3 scripts/runtime_test.py resume --run-id {run_id} --dry-run"
    if backup_id:
        return f"PYTHONPATH=src python3 scripts/runtime_test.py rollback --backup-id {backup_id} --dry-run"
    return "PYTHONPATH=src python3 scripts/runtime_test.py status"


def _fresh_run_resume_recommendation(*, status: str, run_id: str) -> str:
    if run_id and status in {"HALT", "REVIEW_REQUIRED", "BLOCKED"}:
        return f"Review halted job evidence, then run resume dry-run for {run_id}."
    if status == "PASS":
        return "Run is closed; resume is not required."
    return "Resume is not available before a run_id exists."


def _fresh_run_rollback_recommendation(*, status: str, backup_id: str) -> str:
    if backup_id and status != "PASS":
        return f"Rollback is available with backup_id={backup_id}; run rollback dry-run before actual restore."
    if status == "PASS":
        return "Rollback is optional and must be a separate explicit operator action."
    return "Rollback is not available before backup succeeds."


def _fresh_run_evidence_paths(*, evidence_root: Path, run_id: str, fresh_run_id: str) -> dict[str, str]:
    return {
        "run_root": str(runs_root(evidence_root) / run_id) if run_id else "",
        "plan": str(runs_root(evidence_root) / run_id / "plan.json") if run_id else "",
        "run_state": str(runs_root(evidence_root) / run_id / "run_state.json") if run_id else "",
        "final_summary": str(runs_root(evidence_root) / run_id / "final_summary.json") if run_id else "",
        "fresh_run_summary": str((runs_root(evidence_root) / run_id / "fresh_run_summary.json") if run_id else (evidence_root / "fresh_runs" / fresh_run_id / "fresh_run_summary.json")),
        "backup_root": str(backups_root(evidence_root)),
    }


def _persist_fresh_run_summary(*, evidence_root: Path, run_id: str, fresh_run_id: str, payload: dict[str, Any]) -> Path:
    if run_id:
        path = runs_root(evidence_root) / run_id / "fresh_run_summary.json"
    else:
        path = evidence_root / "fresh_runs" / fresh_run_id / "fresh_run_summary.json"
    write_json_atomic(path, payload)
    return path


def base_payload(subcommand: str, status: str) -> dict[str, Any]:
    exit_code = next((code for code, name in EXIT_CODES.items() if name == status), EXIT_PASS)
    return {
        "schema_version": RUNNER_SCHEMA_VERSION,
        "subcommand": subcommand,
        "status": status,
        "current_step": subcommand,
        "completed_days": [],
        "next_step": "",
        "backup_id": "",
        "evidence_path": "",
        "final_judgment": status,
        "exit_code": exit_code,
    }


def runner_response(payload: dict[str, Any]) -> dict[str, Any]:
    response = dict(payload)
    response["schema_version"] = RUNNER_SCHEMA_VERSION
    return response


def emit(payload: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    if payload.get("subcommand") == "summarize" and payload.get("human_summary"):
        print(payload["human_summary"])
        if payload.get("evidence_path"):
            print(f"Evidence Path: {payload['evidence_path']}")
        print(f"Exit Code: {payload.get('exit_code', '')}")
        return
    if payload.get("subcommand") in {"ai-status", "system-status"} and payload.get("human_summary"):
        print(payload["human_summary"])
        if payload.get("evidence_path"):
            print(f"Evidence Path: {payload['evidence_path']}")
        print(f"Exit Code: {payload.get('exit_code', '')}")
        return
    keys = ["run_id", "status", "current_step", "completed_days", "next_step", "backup_id", "evidence_path", "final_judgment", "exit_code"]
    for key in keys:
        if key in payload:
            print(f"{key}: {payload[key]}")
    if "error" in payload:
        print(f"error: {payload['error']}")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return payload


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    data = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(path)


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(path)


def file_ref(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    rel = str(path.relative_to(root)) if root is not None and path.exists() and path.is_relative_to(root) else str(path)
    if not path.exists():
        return {"path": rel, "exists": False, "sha256": "", "size": 0}
    if path.is_dir():
        return {"path": rel, "exists": True, "kind": "directory", "file_count": sum(1 for child in path.rglob("*") if child.is_file()), "sha256": directory_hash(path)}
    return {"path": rel, "exists": True, "kind": "file", "size": path.stat().st_size, "sha256": sha256_file(path)}


def directory_hash(path: Path) -> str:
    if not path.exists():
        return ""
    entries = []
    for child in sorted(path.rglob("*")):
        if child.is_file():
            entries.append({"path": str(child.relative_to(path)), "size": child.stat().st_size, "sha256": sha256_file(child)})
    return semantic_hash(entries)


def _independent_acceptance_judgment(
    *,
    runtime_execution_status: str,
    requested_business_days: int,
    resolved_business_day_count: int,
    completed_business_day_count: int,
    window_resolution_status: str,
) -> dict[str, Any]:
    runtime_execution = "PASS" if runtime_execution_status == "PASS" else runtime_execution_status or "UNKNOWN"
    requested_window_resolution = "PASS" if window_resolution_status == "PASS" else "NOT_PASS"
    requested_window_conformance = (
        "PASS"
        if requested_business_days == resolved_business_day_count == completed_business_day_count
        and window_resolution_status == "PASS"
        else "NOT_PASS"
    )
    overall = "PASS" if runtime_execution == "PASS" and requested_window_conformance == "PASS" else "REVIEW_REQUIRED"
    return {
        "runtime_execution_judgment": runtime_execution,
        "requested_window_resolution_judgment": requested_window_resolution,
        "requested_window_conformance_judgment": requested_window_conformance,
        "summary_evidence_isolation_judgment": "NOT_EVALUATED_IN_FRESH_RUN_SUMMARY",
        "lifecycle_consistency_judgment": "NOT_EVALUATED_IN_FRESH_RUN_SUMMARY",
        "strategy_to_active_runtime_judgment": "NOT_ESTABLISHED",
        "overall_independent_judgment": overall,
        "requested_business_days": requested_business_days,
        "resolved_business_day_count": resolved_business_day_count,
        "completed_business_day_count": completed_business_day_count,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def semantic_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def timestamp_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "UNKNOWN"


def source_dirty() -> bool:
    try:
        return bool(subprocess.check_output(["git", "status", "--short"], text=True).strip())
    except Exception:
        return True


class RuntimeTestError(Exception):
    def __init__(self, message: str, *, status: str, exit_code: int) -> None:
        super().__init__(message)
        self.status = status
        self.exit_code = exit_code


if __name__ == "__main__":
    raise SystemExit(main())
