"""Runtime v2 daily operation rehearsal CLI.

The CLI is the single entrypoint intended for manual and launchd rehearsal
operation. It keeps external writes disabled for the initial launchd rehearsal.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.orchestrator.models import RuntimeRunRequest
from ai_fund_lab_v2.runtime_v2.orchestrator.orchestrator import RuntimeOrchestrator
from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import (
    run_execution_readonly_pipeline,
)
from ai_fund_lab_v2.runtime_v2.market_refresh.pipeline import (
    run_runtime_v2_market_refresh_pipeline,
)
from ai_fund_lab_v2.runtime_v2.planning.morning_pipeline import (
    run_morning_ai_planning_pending_pipeline,
)
from ai_fund_lab_v2.runtime_v2.planning.sell_pipeline import (
    SellExitDecision,
    run_sell_planning_pending_pipeline,
)
from ai_fund_lab_v2.runtime_v2.report.public_report_writer import (
    generate_public_report_from_current,
)
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline

EXIT_SUCCESS = 0
EXIT_BLOCKED = 10
EXIT_REVIEW_REQUIRED = 20
EXIT_HALT = 30
EXIT_CONFIG_ERROR = 40
EXIT_UNEXPECTED_ERROR = 70
ALLOWED_JOBS = (
    "daily_rehearsal",
    "morning",
    "sell_planning",
    "submit",
    "execution",
    "market_refresh",
)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    started_at = _utc_now()
    business_date = args.business_date or date.today().isoformat()
    run_id = f"runtime-v2-{args.job}-{business_date}-{started_at.replace(':', '').replace('-', '')}"
    stages: list[dict[str, Any]] = []
    generated: dict[str, Any] = {}
    errors: list[str] = []
    warnings: list[str] = []
    final_state = "UNKNOWN"
    exit_code = EXIT_SUCCESS

    log_path = Path(args.log_root) / business_date / f"{run_id}.log"

    try:
        _append_log(log_path, f"run_id={run_id} stage=cli_start mode={args.mode} job={args.job}")
        _validate_rehearsal_args(args)
        stages.append(_stage("cli_start", "PASS", "Runtime v2 daily operation CLI started."))
        stages.append(
            _stage(
                "operation_contract",
                "PASS",
                "launchd is a starter only; Runtime v2 CLI owns decisions.",
            )
        )
        stages.extend(_job_checkpoints(args.job))

        request = RuntimeRunRequest(
            mode=args.mode,
            environment=args.mode,
            business_date=business_date,
            dry_run=True,
        )
        base_dir = _base_dir_for_runtime_root(Path(args.runtime_root))
        result = RuntimeOrchestrator(base_dir=base_dir).run_preflight(request)
        final_state = result.end_state.value
        warnings.extend(result.warnings)
        errors.extend(result.errors)
        stages.append(
            _stage(
                "current_sot_preflight",
                "REVIEW_REQUIRED" if result.review_required else "PASS",
                f"Runtime preflight ended at {result.end_state.value}.",
                {
                    "transitions": [
                        {
                            "from_state": transition.from_state.value,
                            "to_state": transition.to_state.value,
                            "allowed": transition.allowed,
                            "reason": transition.reason,
                        }
                        for transition in result.transitions
                    ]
                },
            )
        )

        if result.blocked and args.stop_on_blocked:
            exit_code = EXIT_BLOCKED
        elif result.review_required and args.stop_on_review_required:
            exit_code = EXIT_REVIEW_REQUIRED

        if args.job == "morning" and exit_code == EXIT_SUCCESS:
            morning_result = run_morning_ai_planning_pending_pipeline(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                mode=args.mode,
                feature_root=Path(args.feature_root),
                feature_date=args.feature_date,
                max_orders=args.max_orders,
            )
            stages.append(
                _stage(
                    "morning_ai_planning_pending_pipeline",
                    morning_result.status,
                    "Morning AI/Planning/Approval/Pending pipeline executed.",
                    morning_result.to_stage_details(),
                )
            )
            if morning_result.status == "NO_SIGNAL":
                warnings.append(f"morning pipeline no signal: {morning_result.reason}")
            elif morning_result.status == "REVIEW_REQUIRED":
                exit_code = EXIT_REVIEW_REQUIRED
                final_state = "REVIEW_REQUIRED"
                warnings.append(f"morning pipeline review required: {morning_result.reason}")
            elif morning_result.status == "BLOCKED":
                exit_code = EXIT_BLOCKED
                final_state = "BLOCKED"
                errors.append(f"morning pipeline blocked: {morning_result.reason}")

        if args.job == "sell_planning" and exit_code == EXIT_SUCCESS:
            sell_result = run_sell_planning_pending_pipeline(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                mode=args.mode,
                exit_decisions=_sell_exit_decisions_from_current(
                    runtime_root=Path(args.runtime_root),
                    max_orders=args.max_orders,
                ),
                max_orders=args.max_orders,
            )
            stages.append(
                _stage(
                    "sell_planning_pending_pipeline",
                    sell_result.status,
                    "SELL Planning/Approval/Pending pipeline executed from Current SoT positions.",
                    sell_result.to_stage_details(),
                )
            )
            if sell_result.status == "NO_SIGNAL":
                warnings.append(f"sell planning pipeline no signal: {sell_result.reason}")
            elif sell_result.status == "REVIEW_REQUIRED":
                exit_code = EXIT_REVIEW_REQUIRED
                final_state = "REVIEW_REQUIRED"
                warnings.append(f"sell planning pipeline review required: {sell_result.reason}")
            elif sell_result.status == "BLOCKED":
                exit_code = EXIT_BLOCKED
                final_state = "BLOCKED"
                errors.append(f"sell planning pipeline blocked: {sell_result.reason}")

        submit_result = None
        if args.job == "submit" and _as_bool(args.submit_enabled) and exit_code == EXIT_SUCCESS:
            submit_result = run_submit_pipeline(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                mode=args.mode,
                submit_enabled=_as_bool(args.submit_enabled),
                job=args.job,
            )
            stages.append(
                _stage(
                    "runtime_v2_submit_pipeline",
                    submit_result.status,
                    "Runtime v2 Submit pipeline executed.",
                    submit_result.to_stage_details(),
                )
            )
            if submit_result.status == "BLOCKED":
                exit_code = EXIT_BLOCKED
                final_state = "BLOCKED"
                errors.append(submit_result.reason)
            elif submit_result.status == "REVIEW_REQUIRED":
                exit_code = EXIT_REVIEW_REQUIRED
                final_state = "REVIEW_REQUIRED"
                warnings.append(submit_result.reason)
        elif args.job == "submit" and not _as_bool(args.submit_enabled) and exit_code == EXIT_SUCCESS:
            stages.append(
                _stage(
                    "runtime_v2_submit_pipeline",
                    "DISABLED",
                    "Submit pipeline disabled because --submit-enabled=false.",
                )
            )

        if args.job == "execution" and exit_code == EXIT_SUCCESS:
            execution_result = run_execution_readonly_pipeline(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                mode=args.mode,
            )
            stages.append(
                _stage(
                    "runtime_v2_execution_readonly_pipeline",
                    execution_result.status,
                    "Runtime v2 Execution ReadOnly pipeline executed.",
                    execution_result.to_stage_details(),
                )
            )
            if execution_result.status == "BLOCKED":
                exit_code = EXIT_BLOCKED
                final_state = "BLOCKED"
                errors.append(execution_result.reason)
            elif execution_result.status == "REVIEW_REQUIRED":
                exit_code = EXIT_REVIEW_REQUIRED
                final_state = "REVIEW_REQUIRED"
                warnings.append(execution_result.reason)

        if args.job == "market_refresh" and exit_code == EXIT_SUCCESS:
            market_refresh_result = run_runtime_v2_market_refresh_pipeline(
                business_date=business_date,
                operations_root=Path(args.feature_root).parent,
                allow_api_fetch=_as_bool(args.market_refresh_allow_api_fetch),
            )
            stages.append(
                _stage(
                    "runtime_v2_market_refresh_pipeline",
                    market_refresh_result.status,
                    "Runtime v2 market refresh pipeline executed.",
                    market_refresh_result.to_stage_details(),
                )
            )
            generated["feature_artifacts"] = market_refresh_result.generated_feature_artifacts
            generated["feature_artifact_dir"] = market_refresh_result.feature_artifact_dir
            if market_refresh_result.status == "BLOCKED":
                exit_code = EXIT_BLOCKED
                final_state = "BLOCKED"
                errors.append(market_refresh_result.reason)
            elif market_refresh_result.status == "REVIEW_REQUIRED":
                exit_code = EXIT_REVIEW_REQUIRED
                final_state = "REVIEW_REQUIRED"
                warnings.append(market_refresh_result.reason)

        report_generated = generate_public_report_from_current(
            runtime_root=Path(args.runtime_root),
            runtime_output_dir=Path(args.reports_root) / business_date,
            public_output_dir=Path(args.public_reports_root) / business_date,
            business_date=business_date,
            write_latest=True,
        )
        generated.update(report_generated)
        stages.append(_stage("ledger_asset_reconcile_report", "PASS", "Runtime v2 report artifacts generated."))
        stages.append(_stage("markdown_public_report", "PASS", "Markdown/Public report generated."))
        stages.append(_stage("notification_payload", "PASS", "Payload-only artifact generated; no delivery."))
        stages.append(_stage("audit", "PASS", "Audit artifact generated."))

        if not generated["redaction_scan"]["passed"] and exit_code == EXIT_SUCCESS:
            exit_code = EXIT_REVIEW_REQUIRED
            final_state = "REVIEW_REQUIRED"
            errors.append("public report redaction scan failed")

    except ValueError as exc:
        exit_code = EXIT_CONFIG_ERROR
        final_state = "BLOCKED"
        errors.append(str(exc))
        stages.append(_stage("config_guard", "BLOCKED", str(exc)))
    except Exception as exc:  # pragma: no cover - defensive last line of the CLI
        exit_code = EXIT_UNEXPECTED_ERROR
        final_state = "HALT"
        errors.append(f"unexpected error: {exc}")
        stages.append(_stage("unexpected_error", "HALT", "Unexpected runtime v2 CLI error."))

    manifest = {
        "schema_version": "1",
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": _utc_now(),
        "business_date": business_date,
        "mode": args.mode,
        "job": args.job,
        "submit_enabled": _as_bool(args.submit_enabled),
        "notification_mode": args.notification_mode,
        "stop_on_review_required": args.stop_on_review_required,
        "stop_on_blocked": args.stop_on_blocked,
        "runtime_root": args.runtime_root,
        "final_state": final_state,
        "exit_code": exit_code,
        "stages": stages,
        "warnings": warnings,
        "errors": errors,
        "generated_artifacts": _trim_generated(generated),
        "prohibited_actions": {
            "demo_submit_executed": bool(
                args.job == "submit"
                and "submit_result" in locals()
                and submit_result is not None
                and submit_result.demo_submit_executed
            ),
            "production_order_executed": False,
            "notification_sent": False,
            "phase9_runtime_called": False,
            "phase9_writer_called": False,
            "phase_artifact_used_as_current": False,
            "mode_rooted_current_used": False,
        },
    }
    manifest_path = _write_manifest(Path(args.manifest_root), business_date, run_id, manifest)
    _append_log(log_path, f"run_id={run_id} exit_code={exit_code} manifest={manifest_path}")
    print(json.dumps({"exit_code": exit_code, "manifest": str(manifest_path)}, ensure_ascii=False))
    return exit_code


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("demo", "simulation", "production"), required=True)
    parser.add_argument("--job", choices=ALLOWED_JOBS, default="daily_rehearsal")
    parser.add_argument("--business-date")
    parser.add_argument("--submit-enabled", choices=("true", "false"), default="false")
    parser.add_argument(
        "--notification-mode",
        choices=("payload-only", "send-disabled", "send-enabled"),
        default="payload-only",
    )
    parser.add_argument("--stop-on-review-required", action="store_true")
    parser.add_argument("--stop-on-blocked", action="store_true")
    parser.add_argument("--runtime-root", default=".runtime")
    parser.add_argument("--reports-root", default="reports/runtime_v2")
    parser.add_argument("--public-reports-root", default="reports/public/runtime_v2")
    parser.add_argument("--manifest-root", default=".runtime/runtime_state/run_manifest")
    parser.add_argument("--log-root", default=".runtime/runtime_state/logs")
    parser.add_argument("--feature-root", default=".runtime/operations/feature_artifacts")
    parser.add_argument("--feature-date")
    parser.add_argument("--max-orders", type=int, default=5)
    parser.add_argument("--market-refresh-allow-api-fetch", choices=("true", "false"), default="false")
    return parser.parse_args(argv)


def _validate_rehearsal_args(args: argparse.Namespace) -> None:
    if args.mode != "demo":
        raise ValueError("Runtime v2 daily scheduler rehearsal allows --mode demo only")
    if _as_bool(args.submit_enabled) and args.job != "submit":
        raise ValueError("Runtime v2 daily scheduler rehearsal allows --submit-enabled true only for submit job")
    if args.notification_mode != "payload-only":
        raise ValueError("Runtime v2 daily scheduler rehearsal requires --notification-mode payload-only")
    runtime_root = Path(args.runtime_root)
    runtime_root_text = str(runtime_root)
    if runtime_root_text.endswith("/demo") or "/demo/" in runtime_root_text:
        raise ValueError("mode-rooted Current path is not allowed")
    if args.max_orders < 0:
        raise ValueError("--max-orders must be non-negative")


def _job_checkpoints(job: str) -> list[dict[str, Any]]:
    job_steps = {
        "daily_rehearsal": (
            ("jquants_market_refresh", "External refresh hook recorded."),
            ("feature_refresh", "Feature refresh hook recorded."),
            ("ai_inference", "AI inference hook recorded."),
            ("planning", "Planning hook recorded."),
            ("approval", "Approval linkage hook recorded."),
            ("safety", "Safety checkpoint recorded."),
            ("broker_readonly", "Broker ReadOnly checkpoint recorded; broker write is disabled."),
        ),
        "morning": (
            ("broker_readonly", "Morning Broker ReadOnly checkpoint recorded; broker write is disabled."),
            ("current_sot", "Morning Current SoT checkpoint recorded."),
            ("business_day", "Business day checkpoint recorded."),
            ("carryover", "Carryover checkpoint recorded."),
            ("safety", "Morning Safety checkpoint recorded."),
            ("reconcile", "Morning Reconcile checkpoint recorded."),
            ("ai_inference", "Morning AI inference checkpoint recorded."),
            ("planning", "Morning Planning checkpoint recorded."),
            ("approval", "Morning Approval checkpoint recorded."),
            ("pending_generation", "Morning Pending generation checkpoint recorded."),
            ("submit_stop", "Morning job stops before Submit."),
        ),
        "sell_planning": (
            ("current_sot", "SELL Current SoT checkpoint recorded."),
            ("sell_source", "SELL source checkpoint recorded; Current positions only."),
            ("sell_planning", "SELL Planning checkpoint recorded."),
            ("approval", "SELL Approval checkpoint recorded."),
            ("pending_generation", "SELL Pending generation checkpoint recorded."),
            ("submit_stop", "SELL planning job stops before Submit."),
        ),
        "submit": (
            ("pending", "Open Pending checkpoint recorded."),
            ("approval_recheck", "Open Approval recheck checkpoint recorded."),
            ("safety", "Open Safety checkpoint recorded."),
            ("demo_submit_guarded_checkpoint", "Open Demo Submit guard checkpoint recorded; submit pipeline owns broker write decision."),
        ),
        "execution": (
            ("broker_readonly", "Execution Broker ReadOnly checkpoint recorded; broker write is disabled."),
            ("execution_reflection", "Execution Reflection checkpoint recorded."),
            ("ledger", "Ledger checkpoint recorded."),
            ("asset", "Asset checkpoint recorded."),
            ("reconcile", "Execution Reconcile checkpoint recorded."),
            ("runtime_report", "Runtime Report checkpoint recorded."),
            ("markdown_public_report_checkpoint", "Markdown/Public Report checkpoint recorded."),
            ("audit_checkpoint", "Audit checkpoint recorded."),
        ),
        "market_refresh": (
            ("jquants_market_refresh", "After-close J-Quants checkpoint recorded."),
            ("canonical_update", "Canonical update checkpoint recorded."),
            ("feature_refresh", "Feature Refresh checkpoint recorded."),
            ("candidate_input", "Candidate Input checkpoint recorded."),
            ("opportunity_input", "Opportunity Input checkpoint recorded."),
            ("position_input", "Position Input checkpoint recorded."),
            ("capital_input", "Capital Input checkpoint recorded."),
            ("ai_inference_blocked", "AI inference is blocked in market_refresh job."),
        ),
    }
    return [_stage(name, "CHECKPOINT", message) for name, message in job_steps[job]]


def _as_bool(value: str) -> bool:
    return value.lower() == "true"


def _stage(name: str, status: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "name": name,
        "status": status,
        "message": message,
        "created_at": _utc_now(),
    }
    if details:
        payload["details"] = details
    return payload


def _base_dir_for_runtime_root(runtime_root: Path) -> Path | None:
    if runtime_root.name == ".runtime":
        return runtime_root.parent
    return None


def _sell_exit_decisions_from_current(*, runtime_root: Path, max_orders: int) -> tuple[SellExitDecision, ...]:
    state_path = runtime_root / "persistent_ledger" / "state.json"
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    positions = payload.get("positions") or []
    decisions: list[SellExitDecision] = []
    for position in positions:
        symbol = str(position.get("symbol") or position.get("issue_code") or "").strip()
        quantity = float(position.get("quantity") or 0)
        if not symbol or quantity <= 0:
            continue
        decisions.append(
            SellExitDecision(
                symbol=symbol,
                quantity=quantity,
                reason="runtime_v2_sell_planning_current_position_exit",
            )
        )
        if len(decisions) >= max_orders:
            break
    return tuple(decisions)


def _write_manifest(root: Path, business_date: str, run_id: str, manifest: dict[str, Any]) -> Path:
    path = root / business_date / f"{run_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _append_log(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{_utc_now()} {line}\n")


def _trim_generated(generated: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in generated.items()
        if key
        in {
            "runtime_report_md",
            "runtime_report_json",
            "notification_payload_json",
            "audit_result_json",
            "public_report_md",
            "public_report_json",
            "latest_md",
            "latest_json",
            "redaction_scan",
            "feature_artifacts",
            "feature_artifact_dir",
        }
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
