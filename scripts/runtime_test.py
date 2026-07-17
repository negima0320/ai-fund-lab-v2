#!/usr/bin/env python3
"""Runtime Test command runner.

This script is a thin lifecycle runner around the normal Runtime v2 CLI. It
does not make AI decisions, produce features, generate fills, or mutate Ledger /
Current / Pending except through explicit lifecycle reset / rollback commands.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.historical_support.reset_plan import (
    RESETTABLE_RELATIVE_PATHS,
    RESET_EXCLUDED_RELATIVE_PREFIXES,
)
from ai_fund_lab_v2.runtime_v2.market_refresh.feature_date_contract import (
    load_feature_date_contract,
    resolve_feature_date_contract,
)
from ai_fund_lab_v2.runtime_v2.storage.path_resolver import reject_mode_rooted_runtime_root


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

    status = subparsers.add_parser("status")
    add_common(status)

    plan = subparsers.add_parser("plan")
    add_common(plan)
    add_plan_window(plan)
    plan.add_argument("--write-evidence", action="store_true")

    backup = subparsers.add_parser("backup")
    add_common(backup)
    add_mutation_safety(backup)

    reset = subparsers.add_parser("reset")
    add_common(reset)
    add_mutation_safety(reset)
    reset.add_argument("--backup-id")
    reset.add_argument("--initial-cash", type=float)

    run = subparsers.add_parser("run")
    add_common(run)
    add_plan_window(run)
    add_mutation_safety(run)
    run.add_argument("--run-id")
    run.add_argument("--auto-prepare", action="store_true")

    validate = subparsers.add_parser("validate")
    add_common(validate)
    validate.add_argument("--run-id")
    validate.add_argument("--business-date")

    resume = subparsers.add_parser("resume")
    add_common(resume)
    add_mutation_safety(resume)
    resume.add_argument("--run-id", required=True)

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

    if args.subcommand == "status":
        return status(profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "plan":
        return plan_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "backup":
        return backup_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "reset":
        return reset_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "run":
        return run_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "validate":
        return validate_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "resume":
        return resume_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "rollback":
        return rollback_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    if args.subcommand == "close":
        return close_command(args, profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    raise RuntimeTestError("unsupported subcommand", status="INVALID_ARGUMENT", exit_code=EXIT_INVALID_ARGUMENT)


def status(*, profile: dict[str, Any], runtime_root: Path, evidence_root: Path) -> CommandResult:
    active_run = active_run_for_profile(evidence_root, profile_id=str(profile["profile_id"]))
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
            "current_summary": summarize_json(runtime_root / "persistent_ledger" / "state.json"),
            "ledger_summary": summarize_ledger(runtime_root),
            "pending_summary": summarize_json(runtime_root / "pending_order_plan" / "pending_order_plan.json"),
            "runtime_state_summary": summarize_json(runtime_root / "runtime_state" / "current_state.json"),
            "registry_checkpoint": file_ref(runtime_root / "artifact_registry" / "checkpoints" / "latest.json", root=runtime_root),
            "accepted_artifact_hash": accepted_artifact_hash(runtime_root),
            "latest_backup": latest_backup(evidence_root).get("backup_id", ""),
            "external_effect_policy": profile["external_effect_policy"],
        }
    )
    return CommandResult("PASS", EXIT_PASS, runner_response(payload))


def plan_command(
    args: argparse.Namespace,
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
) -> CommandResult:
    plan_payload = build_plan(
        profile=profile,
        runtime_root=runtime_root,
        evidence_root=evidence_root,
        business_days=args.business_days,
        start_date=args.start_date,
        date_from=args.date_from,
        date_to=args.date_to,
    )
    baseline_compatibility = build_baseline_compatibility(
        runtime_root=runtime_root,
        requested_start_date=plan_payload["business_dates"][0]["business_date"],
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
    plan_status = "PASS" if baseline_compatibility["baseline_compatibility_status"] == "PASS" else "PLAN_REVIEW_REQUIRED"
    payload = base_payload("plan", plan_status)
    payload.update(plan_payload)
    payload["runtime_test_plan_schema_version"] = plan_payload["schema_version"]
    exit_code = EXIT_PASS if plan_status == "PASS" else EXIT_REVIEW_REQUIRED
    payload["exit_code"] = exit_code
    return CommandResult(plan_status, exit_code, runner_response(payload))


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
        "dry_run": bool(args.dry_run),
    }
    if not args.dry_run:
        require_confirm(args)
        try:
            apply_reset(runtime_root=runtime_root, initial_state=initial_state, profile=profile)
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


def run_command(
    args: argparse.Namespace,
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
) -> CommandResult:
    require_historical_mutation_context(args=args, profile=profile)
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
    }
    write_json_atomic(run_dir / "run_state.json", run_state)
    for day in plan_payload["business_dates"]:
        for job in day["jobs"]:
            run_state["next_job"] = f"{day['business_date']}:{job['job']}"
            write_json_atomic(run_dir / "run_state.json", run_state)
            command_resolution = resolve_run_job_command(runtime_root=runtime_root, job_record=job)
            command = command_resolution["command"]
            completed = run_runtime_cli(command, cwd=Path.cwd())
            job_record = {
                "business_date": day["business_date"],
                "job": job["job"],
                "exit_code": completed.returncode,
                "command": command,
                "planned_command": job["command"],
                "feature_date_command_resolution": command_resolution["resolution"],
            }
            collect_runtime_cli_job_evidence(
                completed=completed,
                run_dir=run_dir,
                runtime_root=runtime_root,
                business_date=day["business_date"],
                job=job["job"],
            )
            run_state["completed_jobs"].append(job_record)
            write_json_atomic(run_dir / "run_state.json", run_state)
            if completed.returncode != 0:
                run_state["status"] = "HALT"
                run_state["halted_at"] = job_record
                write_json_atomic(run_dir / "run_state.json", run_state)
                raise RuntimeTestError(
                    f"Runtime CLI stopped at {run_state['next_job']} with exit code {completed.returncode}",
                    status="HALT",
                    exit_code=EXIT_HALT,
                )
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
    checks = {
        "normal_runtime_root": str(runtime_root).endswith(".runtime"),
        "current_exists": (runtime_root / "persistent_ledger" / "state.json").exists(),
        "pending_exists": (runtime_root / "pending_order_plan" / "pending_order_plan.json").exists(),
        "runtime_state_exists": (runtime_root / "runtime_state" / "current_state.json").exists(),
        "external_effect_absence": profile["external_effect_policy"].get("broker_write") is False,
        "run_state_present": bool(run_state) if args.run_id else True,
    }
    status_value = "PASS" if all(checks.values()) else "VALIDATION_FAILURE"
    payload = base_payload("validate", status_value)
    payload.update(
        {
            "run_id": args.run_id or "",
            "business_date": args.business_date or "",
            "checks": checks,
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
    validate_plan_entry_gate(plan_payload)
    completed_success = {
        (record.get("business_date"), record.get("job"))
        for record in run_state.get("completed_jobs", [])
        if int(record.get("exit_code", 1)) == 0
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
            command_resolution = resolve_run_job_command(runtime_root=runtime_root, job_record=job)
            command = command_resolution["command"]
            completed = run_runtime_cli(command, cwd=Path.cwd())
            job_record = {
                "business_date": day["business_date"],
                "job": job["job"],
                "exit_code": completed.returncode,
                "command": command,
                "planned_command": job["command"],
                "feature_date_command_resolution": command_resolution["resolution"],
                "resumed": True,
            }
            collect_runtime_cli_job_evidence(
                completed=completed,
                run_dir=run_dir,
                runtime_root=runtime_root,
                business_date=day["business_date"],
                job=job["job"],
            )
            run_state.setdefault("completed_jobs", []).append(job_record)
            write_json_atomic(run_dir / "run_state.json", run_state)
            if completed.returncode != 0:
                run_state["status"] = "HALT"
                run_state["halted_at"] = job_record
                write_json_atomic(run_dir / "run_state.json", run_state)
                raise RuntimeTestError(
                    f"resume stopped at {run_state['next_job']} with exit code {completed.returncode}",
                    status="HALT",
                    exit_code=EXIT_HALT,
                )
    run_state["status"] = "COMPLETED"
    run_state["next_job"] = ""
    write_json_atomic(run_dir / "run_state.json", run_state)
    payload = base_payload("resume", "PASS")
    payload.update({"run_id": args.run_id, "evidence_path": str(run_dir), "completed_business_days": run_state.get("completed_business_days", [])})
    return CommandResult("PASS", EXIT_PASS, runner_response(payload))


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


def close_command(
    args: argparse.Namespace,
    *,
    profile: dict[str, Any],
    runtime_root: Path,
    evidence_root: Path,
) -> CommandResult:
    run_state = load_run_state(evidence_root, args.run_id)
    validation = validate_command(argparse.Namespace(run_id=args.run_id, business_date="", json=False), profile=profile, runtime_root=runtime_root, evidence_root=evidence_root)
    status_value = "PASS" if validation.exit_code == EXIT_PASS and run_state.get("status") in {"COMPLETED", "HALT"} else "REVIEW_REQUIRED"
    summary = {
        "schema_version": FINAL_SUMMARY_SCHEMA_VERSION,
        "run_id": args.run_id,
        "profile_id": profile["profile_id"],
        "status": status_value,
        "test_validity_judgment": "VALID" if status_value == "PASS" else "REVIEW_REQUIRED",
        "acceptance_gate_judgment": status_value,
        "final_state_hashes": state_hashes(runtime_root),
        "closed_at": utc_now(),
        "post_close_lifecycle_recommendation": "validate evidence, then explicitly rollback or transition by separate command",
    }
    run_dir = runs_root(evidence_root) / args.run_id
    write_json_atomic(run_dir / "final_summary.json", summary)
    payload = base_payload("close", status_value)
    payload.update(summary)
    payload["runtime_test_final_summary_schema_version"] = summary["schema_version"]
    return CommandResult(status_value, EXIT_PASS if status_value == "PASS" else EXIT_REVIEW_REQUIRED, runner_response(payload))


def show(args: argparse.Namespace) -> CommandResult:
    if args.backup_id:
        path = BACKUP_ROOT / args.backup_id / "backup_manifest.json"
    elif args.run_id:
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
    dates = resolve_business_dates(
        profile=profile,
        runtime_root=runtime_root,
        business_days=business_days,
        start_date=start_date,
        date_from=date_from,
        date_to=date_to,
    )
    final_run_id = run_id or f"runtime-test-{profile['profile_id']}-{timestamp_id()}"
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
            }
        )
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "run_id": final_run_id,
        "profile_id": profile["profile_id"],
        "profile_hash": semantic_hash(profile),
        "requested_start_date": dates[0] if dates else "",
        "requested_end_date": dates[-1] if dates else "",
        "requested_business_days": len(dates),
        "environment_id": f"{profile['mode']}:{profile['broker_environment']}",
        "runtime_root": str(runtime_root),
        "business_dates": days,
        "job_sequence": profile["job_sequence"],
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


def validate_plan_entry_gate(plan_payload: dict[str, Any]) -> None:
    validate_schema(
        payload=plan_payload,
        artifact_name="runtime test plan",
        supported=SUPPORTED_PLAN_SCHEMA_VERSIONS,
    )
    failures: list[dict[str, Any]] = []
    for day in plan_payload.get("business_dates", []):
        business_date = str(day.get("business_date") or "")
        feature = dict(day.get("feature_date_evidence") or {})
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


def resolve_run_job_command(*, runtime_root: Path, job_record: dict[str, Any]) -> dict[str, Any]:
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
        return {"command": command, "resolution": resolution}
    selected = contract.selected_feature_date
    command = command_with_option(command, "--feature-date", selected)
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


def apply_reset(*, runtime_root: Path, initial_state: dict[str, Any], profile: dict[str, Any]) -> None:
    created_at = utc_now()
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
            "as_of": created_at,
            "business_date": "",
            "positions": [],
            "cash": float(initial_state["cash"]),
            "buying_power": float(initial_state["buying_power"]),
            "market_value": 0.0,
            "total_equity": float(initial_state["cash"]),
            "review_required": False,
            "production_equivalent": False,
            "current_state_confirmed_empty": True,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
            "cash_confirmed": True,
            "buying_power_confirmed": True,
            "generated_from": [],
            "created_at": created_at,
            "updated_at": created_at,
            "temporal_schema_version": "runtime_v2_current_temporal_v1",
            "temporal_status": "READY",
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
    if not final_summary_path.exists():
        return False
    try:
        payload = read_json(final_summary_path)
        validate_schema(
            payload=payload,
            artifact_name="runtime test final summary",
            supported={FINAL_SUMMARY_SCHEMA_VERSION},
        )
    except Exception:
        return False
    return bool(payload.get("closed_at"))


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


def run_runtime_cli(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = env.get("PYTHONPATH") or "src"
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)


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
            "source_manifest_path": str(manifest_path) if manifest_path else "",
            "runtime_manifest_copied": bool(copied_manifest),
            "runtime_manifest_path": copied_manifest,
            "runtime_log_copied": bool(copied_log),
            "runtime_log_path": copied_log,
        },
    )


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
