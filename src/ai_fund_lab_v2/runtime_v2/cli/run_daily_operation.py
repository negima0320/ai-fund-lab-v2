"""Runtime v2 daily operation rehearsal CLI.

The CLI is the single entrypoint intended for manual and launchd rehearsal
operation. It keeps external writes disabled for the initial launchd rehearsal.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.operations.market_calendar import resolve_operation_date
from ai_fund_lab_v2.runtime_v2.orchestrator.models import RuntimeRunRequest
from ai_fund_lab_v2.runtime_v2.orchestrator.orchestrator import RuntimeOrchestrator
from ai_fund_lab_v2.runtime_v2.buy_ai.producer import produce_buy_ai_decisions
from ai_fund_lab_v2.runtime_v2.data_readiness import evaluate_runtime_data_readiness
from ai_fund_lab_v2.runtime_v2.current_state.temporal import run_current_temporal_migration
from ai_fund_lab_v2.runtime_v2.current_state.valuation import run_current_valuation_refresh
from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import (
    run_execution_readonly_pipeline,
)
from ai_fund_lab_v2.runtime_v2.market_refresh.pipeline import (
    run_runtime_v2_market_refresh_pipeline,
)
from ai_fund_lab_v2.runtime_v2.market_refresh.feature_date_contract import (
    load_feature_date_contract,
    resolve_feature_date_contract,
)
from ai_fund_lab_v2.runtime_v2.planning.morning_pipeline import (
    run_morning_ai_planning_pending_pipeline,
)
from ai_fund_lab_v2.runtime_v2.planning.sell_pipeline import (
    run_sell_planning_pending_pipeline,
)
from ai_fund_lab_v2.runtime_v2.pending.lifecycle_runner import run_pending_lifecycle_review
from ai_fund_lab_v2.runtime_v2.position_management.producer import produce_position_management_decisions
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import (
    CapitalDeploymentPolicyError,
    invalid_policy_manifest_fields,
    load_capital_deployment_policy,
    missing_policy_manifest_fields,
)
from ai_fund_lab_v2.runtime_v2.report.public_report_writer import (
    generate_public_report_from_current,
)
from ai_fund_lab_v2.runtime_v2.safety_decision import (
    load_runtime_safety_decision,
    safety_manifest_fields,
)
from ai_fund_lab_v2.runtime_v2.safety.evaluation import run_runtime_safety_evaluation
from ai_fund_lab_v2.runtime_v2.safety.producer import produce_runtime_safety_decision
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
    "safety_evaluation",
    "safety_refresh",
    "data_readiness",
    "pending_lifecycle",
    "current_temporal_migration",
    "current_valuation_refresh",
)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    started_at = _utc_now()
    business_date = args.business_date or date.today().isoformat()
    evaluation_time = None
    run_id = f"runtime-v2-{args.job}-{business_date}-{started_at.replace(':', '').replace('-', '')}"
    stages: list[dict[str, Any]] = []
    generated: dict[str, Any] = {}
    errors: list[str] = []
    warnings: list[str] = []
    final_state = "UNKNOWN"
    exit_code = EXIT_SUCCESS
    capital_policy_manifest = missing_policy_manifest_fields(
        None,
        reason="POLICY_NOT_EVALUATED",
    )
    capital_deployment_policy = None
    runtime_safety_decision = None
    submit_guard_policy: dict[str, Any] = {}
    submit_policy_consistency: dict[str, Any] = {}
    submit_guard_item_evidence: list[dict[str, Any]] = []
    safety_evaluation_manifest: dict[str, Any] = {}
    safety_producer_manifest: dict[str, Any] = {}
    position_management_manifest: dict[str, Any] = {}
    buy_ai_manifest: dict[str, Any] = {}
    data_readiness_manifest: dict[str, Any] = {}
    pending_lifecycle_manifest: dict[str, Any] = {}
    market_evidence_manifest: dict[str, Any] = {}
    current_temporal_migration_manifest: dict[str, Any] = {}
    current_valuation_manifest: dict[str, Any] = {}
    non_trading_day_evidence = _non_trading_day_demo_override_evidence(args, business_date)

    log_path = Path(args.log_root) / business_date / f"{run_id}.log"

    try:
        _append_log(log_path, f"run_id={run_id} stage=cli_start mode={args.mode} job={args.job}")
        _validate_rehearsal_args(args)
        evaluation_time = _parse_evaluation_time(args.evaluation_time)
        stages.append(_stage("cli_start", "PASS", "Runtime v2 daily operation CLI started."))
        stages.append(
            _stage(
                "operation_contract",
                "PASS",
                "launchd is a starter only; Runtime v2 CLI owns decisions.",
            )
        )
        stages.extend(_job_checkpoints(args.job))
        override_status, override_reason = _non_trading_day_override_gate(args, non_trading_day_evidence)
        stages.append(
            _stage(
                "non_trading_day_demo_acceptance_override",
                override_status,
                "Non-trading-day Demo Acceptance override evaluated.",
                non_trading_day_evidence,
            )
        )
        if override_status == "BLOCKED":
            exit_code = EXIT_BLOCKED
            final_state = "BLOCKED"
            errors.append(override_reason)
        elif override_status == "REVIEW_REQUIRED":
            exit_code = EXIT_REVIEW_REQUIRED
            final_state = "REVIEW_REQUIRED"
            warnings.append(override_reason)
        capital_policy_manifest = _load_capital_policy_manifest(args.capital_deployment_policy)
        if capital_policy_manifest["capital_deployment_policy_loaded"]:
            capital_deployment_policy = load_capital_deployment_policy(Path(args.capital_deployment_policy))
        stages.append(
            _stage(
                "capital_deployment_policy",
                "PASS" if capital_policy_manifest["capital_deployment_policy_loaded"] else "REVIEW_REQUIRED",
                "Explicit Capital Deployment Policy evaluated.",
                capital_policy_manifest,
            )
        )
        if _policy_required_for_job(args.job) and not capital_policy_manifest["capital_deployment_policy_loaded"]:
            warnings.append(
                "capital deployment policy review required: "
                + str(capital_policy_manifest["policy_validation_status"])
            )
        if args.job == "safety_evaluation" and exit_code == EXIT_SUCCESS:
            safety_evaluation_result = run_runtime_safety_evaluation(
                runtime_root=Path(args.runtime_root),
                reports_root=Path(args.safety_reports_root),
                business_date=business_date,
                mode=args.mode,
                now=evaluation_time,
            )
            safety_evaluation_manifest = dict(safety_evaluation_result.manifest_fields)
            stages.append(
                _stage(
                    "runtime_safety_evaluation",
                    safety_evaluation_result.status,
                    "Runtime Safety evaluation built Phase11 Safety evidence from Runtime regular-path artifacts.",
                    safety_evaluation_manifest,
                )
            )
            if safety_evaluation_result.status == "HALT":
                exit_code = EXIT_HALT
                final_state = "HALT"
                errors.append(safety_evaluation_result.reason)
            elif safety_evaluation_result.status == "BLOCKED":
                exit_code = EXIT_BLOCKED
                final_state = "BLOCKED"
                errors.append(safety_evaluation_result.reason)
            elif safety_evaluation_result.status == "REVIEW_REQUIRED":
                exit_code = EXIT_REVIEW_REQUIRED
                final_state = "REVIEW_REQUIRED"
                warnings.append(safety_evaluation_result.reason)
        if args.job == "safety_refresh" and exit_code == EXIT_SUCCESS:
            safety_producer_result = produce_runtime_safety_decision(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                mode=args.mode,
                source_artifact_path=args.safety_report_path,
                now=evaluation_time,
            )
            safety_producer_manifest = dict(safety_producer_result.manifest_fields)
            stages.append(
                _stage(
                    "runtime_safety_decision_producer",
                    safety_producer_result.status,
                    "Runtime Safety Decision producer normalized authoritative Safety evidence.",
                    safety_producer_manifest,
                )
            )
            if safety_producer_result.status == "HALT":
                exit_code = EXIT_HALT
                final_state = "HALT"
                errors.append(safety_producer_result.reason)
            elif safety_producer_result.status == "BLOCKED":
                exit_code = EXIT_BLOCKED
                final_state = "BLOCKED"
                errors.append(safety_producer_result.reason)
            elif safety_producer_result.status == "REVIEW_REQUIRED":
                exit_code = EXIT_REVIEW_REQUIRED
                final_state = "REVIEW_REQUIRED"
                warnings.append(safety_producer_result.reason)
        runtime_safety_decision = load_runtime_safety_decision(
            runtime_root=Path(args.runtime_root),
            business_date=business_date,
            mode=args.mode,
        )
        stages.append(
            _stage(
                "safety_operation_guard",
                _safety_stage_status(runtime_safety_decision),
                "Runtime v2 Safety / Operation Guard evaluated.",
                safety_manifest_fields(runtime_safety_decision),
            )
        )

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
        if override_status == "BLOCKED":
            final_state = "BLOCKED"
        elif override_status == "REVIEW_REQUIRED":
            final_state = "REVIEW_REQUIRED"
        elif safety_evaluation_manifest.get("safety_evaluation_status") in {"HALT", "BLOCKED", "REVIEW_REQUIRED"}:
            final_state = str(safety_evaluation_manifest["safety_evaluation_status"])
        elif safety_producer_manifest.get("safety_producer_status") in {"HALT", "BLOCKED", "REVIEW_REQUIRED"}:
            final_state = str(safety_producer_manifest["safety_producer_status"])

        if result.blocked and args.stop_on_blocked:
            exit_code = EXIT_BLOCKED
        elif result.review_required and args.stop_on_review_required:
            exit_code = EXIT_REVIEW_REQUIRED
        if _policy_required_for_job(args.job) and not capital_policy_manifest["capital_deployment_policy_loaded"]:
            exit_code = EXIT_REVIEW_REQUIRED
            final_state = "REVIEW_REQUIRED"

        if args.job == "pending_lifecycle" and exit_code == EXIT_SUCCESS:
            pending_lifecycle_result = run_pending_lifecycle_review(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                mode=args.mode,
                action=args.pending_action,
            )
            pending_lifecycle_manifest = dict(pending_lifecycle_result.manifest_fields)
            stages.append(
                _stage(
                    "pending_lifecycle",
                    pending_lifecycle_result.status,
                    "Pending lifecycle reviewed active Pending and applied allowed regular-path transition.",
                    pending_lifecycle_manifest,
                )
            )
            if pending_lifecycle_result.status == "REVIEW_REQUIRED":
                exit_code = EXIT_REVIEW_REQUIRED
                final_state = "REVIEW_REQUIRED"
                warnings.append(pending_lifecycle_result.reason)
            elif pending_lifecycle_result.status in {"EXPIRED", "CANCELLED", "SUPERSEDED", "NOOP"}:
                final_state = "COMPLETED"

        if args.job == "current_temporal_migration" and exit_code == EXIT_SUCCESS:
            current_temporal_migration_result = run_current_temporal_migration(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                apply_current_migration=args.apply_current_migration,
                now=evaluation_time,
            )
            current_temporal_migration_manifest = dict(current_temporal_migration_result.manifest_fields)
            stages.append(
                _stage(
                    "current_temporal_migration",
                    current_temporal_migration_result.status,
                    "Current Temporal Schema migration candidate generated; apply requires explicit option.",
                    current_temporal_migration_manifest,
                )
            )
            generated["current_temporal_migration_artifact"] = current_temporal_migration_result.artifact_path
            if current_temporal_migration_result.status == "HALT":
                exit_code = EXIT_HALT
                final_state = "HALT"
                errors.append(current_temporal_migration_result.reason)
            elif current_temporal_migration_result.status == "REVIEW_REQUIRED":
                exit_code = EXIT_REVIEW_REQUIRED
                final_state = "REVIEW_REQUIRED"
                warnings.append(current_temporal_migration_result.reason)

        if args.job == "current_valuation_refresh" and exit_code == EXIT_SUCCESS:
            current_valuation_result = run_current_valuation_refresh(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                apply_current_valuation=args.apply_current_valuation,
                now=evaluation_time,
            )
            current_valuation_manifest = dict(current_valuation_result.manifest_fields)
            stages.append(
                _stage(
                    "current_valuation_refresh",
                    current_valuation_result.status,
                    "Current valuation-only / no-fill producer generated a valuation candidate.",
                    current_valuation_manifest,
                )
            )
            generated["current_valuation_refresh_artifact"] = current_valuation_result.artifact_path
            if current_valuation_result.status == "HALT":
                exit_code = EXIT_HALT
                final_state = "HALT"
                errors.append(current_valuation_result.reason)
            elif current_valuation_result.status == "REVIEW_REQUIRED":
                exit_code = EXIT_REVIEW_REQUIRED
                final_state = "REVIEW_REQUIRED"
                warnings.append(current_valuation_result.reason)

        data_readiness_result = None
        if _data_readiness_required_for_job(args.job) and exit_code == EXIT_SUCCESS:
            data_readiness_result = evaluate_runtime_data_readiness(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                mode=args.mode,
                readiness_scope=_readiness_scope_for_args(args),
                feature_root=Path(args.feature_root),
                feature_date=_resolve_buy_ai_feature_date(args, business_date)
                if _readiness_scope_for_args(args) == "morning"
                else args.feature_date,
                candidate_model_path=args.candidate_model_path,
                opportunity_model_path=args.opportunity_model_path,
                pm_opportunity_path=args.pm_opportunity_path,
                pm_feature_path=args.pm_feature_path,
                allow_non_trading_day_demo=args.allow_non_trading_day_demo,
            )
            data_readiness_manifest = data_readiness_result.to_manifest_fields()
            stages.append(
                _stage(
                    "runtime_data_readiness_gate",
                    data_readiness_result.status,
                    "Runtime Data Readiness Gate evaluated input evidence before Runtime execution.",
                    data_readiness_result.payload,
                )
            )
            generated["data_readiness_artifact"] = data_readiness_result.artifact_path
            if data_readiness_result.status == "HALT":
                exit_code = EXIT_HALT
                final_state = "HALT"
                errors.extend(data_readiness_result.payload.get("halt_reasons") or [data_readiness_result.reason])
            elif data_readiness_result.status == "REVIEW_REQUIRED":
                exit_code = EXIT_REVIEW_REQUIRED
                final_state = "REVIEW_REQUIRED"
                warnings.extend(data_readiness_result.payload.get("review_reasons") or [data_readiness_result.reason])

        if args.job == "morning" and exit_code == EXIT_SUCCESS:
            buy_ai_result = produce_buy_ai_decisions(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                feature_root=Path(args.feature_root),
                feature_date=_resolve_buy_ai_feature_date(args, business_date),
                candidate_model_path=args.candidate_model_path,
                opportunity_model_path=args.opportunity_model_path,
                opportunity_training_metrics_path=args.opportunity_training_metrics_path,
                selected_rank_limit=args.max_orders,
            )
            buy_ai_manifest = buy_ai_result.to_manifest_fields()
            stages.append(
                _stage(
                    "candidate_opportunity_ai_runtime_producer",
                    buy_ai_result.status,
                    "Candidate AI and Opportunity AI generated authoritative BUY decision artifacts.",
                    buy_ai_manifest,
                )
            )
            if buy_ai_result.status == "REVIEW_REQUIRED":
                exit_code = EXIT_REVIEW_REQUIRED
                final_state = "REVIEW_REQUIRED"
                warnings.append(f"buy ai review required: {buy_ai_result.reason}")
        if args.job == "morning" and exit_code == EXIT_SUCCESS:
            morning_result = run_morning_ai_planning_pending_pipeline(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                mode=args.mode,
                feature_root=Path(args.feature_root),
                feature_date=args.feature_date,
                max_orders=args.max_orders,
                capital_deployment_policy=capital_deployment_policy,
                safety_decision=runtime_safety_decision,
                ai_signals=buy_ai_result.ai_signals,
                buy_ai_context=buy_ai_manifest,
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
            elif morning_result.status == "HALT":
                exit_code = EXIT_HALT
                final_state = "HALT"
                errors.append(f"morning pipeline halted: {morning_result.reason}")

        if args.job == "sell_planning" and exit_code == EXIT_SUCCESS:
            pm_result = produce_position_management_decisions(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                mode=args.mode,
                feature_date=args.feature_date,
                opportunity_path=args.pm_opportunity_path,
                feature_path=args.pm_feature_path,
            )
            position_management_manifest = pm_result.to_manifest_fields()
            stages.append(
                _stage(
                    "position_management_ai_runtime_producer",
                    pm_result.status,
                    "Position Management AI generated the authoritative SELL decision artifact.",
                    position_management_manifest,
                )
            )
            if pm_result.status == "REVIEW_REQUIRED":
                exit_code = EXIT_REVIEW_REQUIRED
                final_state = "REVIEW_REQUIRED"
                warnings.append(f"position management review required: {pm_result.reason}")
            if exit_code == EXIT_SUCCESS:
                sell_result = run_sell_planning_pending_pipeline(
                    runtime_root=Path(args.runtime_root),
                    business_date=business_date,
                    mode=args.mode,
                    exit_decisions=pm_result.sell_exit_decisions,
                    max_orders=args.max_orders,
                    capital_deployment_policy=capital_deployment_policy,
                    safety_decision=runtime_safety_decision,
                )
                stages.append(
                    _stage(
                        "sell_planning_pending_pipeline",
                        sell_result.status,
                        "SELL Planning/Approval/Pending pipeline executed from Position Management AI decisions and Current SoT quantities.",
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
                elif sell_result.status == "HALT":
                    exit_code = EXIT_HALT
                    final_state = "HALT"
                    errors.append(f"sell planning pipeline halted: {sell_result.reason}")

        submit_result = None
        if args.job == "submit" and _as_bool(args.submit_enabled) and exit_code == EXIT_SUCCESS:
            submit_result = run_submit_pipeline(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                mode=args.mode,
                submit_enabled=_as_bool(args.submit_enabled),
                job=args.job,
                capital_deployment_policy_path=args.capital_deployment_policy,
                safety_decision=runtime_safety_decision,
            )
            submit_guard_policy = dict(submit_result.submit_guard_policy)
            submit_policy_consistency = dict(submit_result.submit_policy_consistency)
            submit_guard_item_evidence = list(submit_result.submit_guard_item_evidence)
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
            elif submit_result.status == "HALT":
                exit_code = EXIT_HALT
                final_state = "HALT"
                errors.append(submit_result.reason)
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
                mode=args.mode,
            )
            market_evidence_manifest = {
                "market_evidence_status": market_refresh_result.market_evidence_status,
                "market_evidence_reason": market_refresh_result.market_evidence_reason,
                "market_evidence_path": market_refresh_result.market_evidence_path,
                "market_evidence_latest_pointer_path": market_refresh_result.market_evidence_latest_pointer_path,
                "market_evidence_history_artifact_path": market_refresh_result.market_evidence_history_artifact_path,
                "market_date": market_refresh_result.market_date,
                "latest_expected_trading_date": market_refresh_result.latest_expected_trading_date,
                "latest_available_market_date": market_refresh_result.latest_available_market_date,
                "market_freshness_status": market_refresh_result.market_freshness_status,
                "quote_status": market_refresh_result.quote_status,
                "quote_count": market_refresh_result.quote_count,
                "missing_quote_count": market_refresh_result.missing_quote_count,
                "market_summary_status": market_refresh_result.market_summary_status,
                "publication_status": market_refresh_result.publication_status,
                "provider_status": market_refresh_result.provider_status,
            }
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

        _write_manifest(
            Path(args.manifest_root),
            business_date,
            run_id,
            _build_manifest(
                args=args,
                run_id=run_id,
                started_at=started_at,
                business_date=business_date,
                final_state=final_state,
                exit_code=exit_code,
                capital_policy_manifest=capital_policy_manifest,
                runtime_safety_decision=runtime_safety_decision,
                submit_guard_policy=submit_guard_policy,
                submit_policy_consistency=submit_policy_consistency,
                submit_guard_item_evidence=submit_guard_item_evidence,
                stages=stages,
                warnings=warnings,
                errors=errors,
                generated=generated,
                non_trading_day_evidence=non_trading_day_evidence,
                safety_evaluation_manifest=safety_evaluation_manifest,
                safety_producer_manifest=safety_producer_manifest,
                position_management_manifest=position_management_manifest,
                buy_ai_manifest=buy_ai_manifest,
                data_readiness_manifest=data_readiness_manifest,
                pending_lifecycle_manifest=pending_lifecycle_manifest,
                market_evidence_manifest=market_evidence_manifest,
                current_temporal_migration_manifest=current_temporal_migration_manifest,
                current_valuation_manifest=current_valuation_manifest,
                submit_result=submit_result if "submit_result" in locals() else None,
            ),
        )
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

    manifest = _build_manifest(
        args=args,
        run_id=run_id,
        started_at=started_at,
        business_date=business_date,
        final_state=final_state,
        exit_code=exit_code,
        capital_policy_manifest=capital_policy_manifest,
        runtime_safety_decision=runtime_safety_decision,
        submit_guard_policy=submit_guard_policy,
        submit_policy_consistency=submit_policy_consistency,
        submit_guard_item_evidence=submit_guard_item_evidence,
        stages=stages,
        warnings=warnings,
        errors=errors,
        generated=generated,
        non_trading_day_evidence=non_trading_day_evidence,
        safety_evaluation_manifest=safety_evaluation_manifest,
        safety_producer_manifest=safety_producer_manifest,
        position_management_manifest=position_management_manifest,
        buy_ai_manifest=buy_ai_manifest,
        data_readiness_manifest=data_readiness_manifest,
        pending_lifecycle_manifest=pending_lifecycle_manifest,
        market_evidence_manifest=market_evidence_manifest,
        current_temporal_migration_manifest=current_temporal_migration_manifest,
        current_valuation_manifest=current_valuation_manifest,
        submit_result=submit_result if "submit_result" in locals() else None,
    )
    manifest_path = _write_manifest(Path(args.manifest_root), business_date, run_id, manifest)
    _append_log(log_path, f"run_id={run_id} exit_code={exit_code} manifest={manifest_path}")
    print(json.dumps({"exit_code": exit_code, "manifest": str(manifest_path)}, ensure_ascii=False))
    return exit_code


def _build_manifest(
    *,
    args: argparse.Namespace,
    run_id: str,
    started_at: str,
    business_date: str,
    final_state: str,
    exit_code: int,
    capital_policy_manifest: dict[str, Any],
    runtime_safety_decision: Any,
    submit_guard_policy: dict[str, Any],
    submit_policy_consistency: dict[str, Any],
    submit_guard_item_evidence: list[dict[str, Any]],
    stages: list[dict[str, Any]],
    warnings: list[str],
    errors: list[str],
    generated: dict[str, Any],
    non_trading_day_evidence: dict[str, Any],
    safety_evaluation_manifest: dict[str, Any],
    safety_producer_manifest: dict[str, Any],
    position_management_manifest: dict[str, Any],
    buy_ai_manifest: dict[str, Any],
    data_readiness_manifest: dict[str, Any],
    pending_lifecycle_manifest: dict[str, Any],
    market_evidence_manifest: dict[str, Any],
    current_temporal_migration_manifest: dict[str, Any],
    current_valuation_manifest: dict[str, Any],
    submit_result: Any,
) -> dict[str, Any]:
    return {
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
        "reason": _final_reason(errors=errors, warnings=warnings),
        **non_trading_day_evidence,
        **safety_evaluation_manifest,
        **safety_producer_manifest,
        **position_management_manifest,
        **buy_ai_manifest,
        **data_readiness_manifest,
        **pending_lifecycle_manifest,
        **market_evidence_manifest,
        **current_temporal_migration_manifest,
        **current_valuation_manifest,
        **capital_policy_manifest,
        **safety_manifest_fields(runtime_safety_decision),
        "submit_guard_policy": submit_guard_policy,
        "submit_policy_consistency": submit_policy_consistency,
        "submit_guard_item_evidence": submit_guard_item_evidence,
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


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("demo", "simulation", "production"), required=True)
    parser.add_argument("--job", choices=ALLOWED_JOBS, default="daily_rehearsal")
    parser.add_argument("--readiness-scope", choices=("morning", "sell_planning", "submit", "execution"))
    parser.add_argument("--pending-action", choices=("review", "expire", "cancel"), default="review")
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
    parser.add_argument("--safety-reports-root", default="reports")
    parser.add_argument("--public-reports-root", default="reports/public/runtime_v2")
    parser.add_argument("--manifest-root", default=".runtime/runtime_state/run_manifest")
    parser.add_argument("--log-root", default=".runtime/runtime_state/logs")
    parser.add_argument("--feature-root", default=".runtime/operations/feature_artifacts")
    parser.add_argument("--feature-date")
    parser.add_argument("--pm-opportunity-path")
    parser.add_argument("--pm-feature-path")
    parser.add_argument("--candidate-model-path")
    parser.add_argument("--opportunity-model-path")
    parser.add_argument("--opportunity-training-metrics-path")
    parser.add_argument("--max-orders", type=int)
    parser.add_argument("--capital-deployment-policy")
    parser.add_argument("--safety-report-path")
    parser.add_argument("--market-refresh-allow-api-fetch", choices=("true", "false"), default="false")
    parser.add_argument("--allow-non-trading-day-demo", action="store_true")
    parser.add_argument("--evaluation-time")
    parser.add_argument("--apply-current-migration", action="store_true")
    parser.add_argument("--apply-current-valuation", action="store_true")
    return parser.parse_args(argv)


def _validate_rehearsal_args(args: argparse.Namespace) -> None:
    if args.mode == "production" and args.allow_non_trading_day_demo:
        return
    if args.job in {"safety_evaluation", "safety_refresh"} and args.mode in {"demo", "production"}:
        return
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
    if args.max_orders is not None and args.max_orders < 0:
        raise ValueError("--max-orders must be non-negative")


def _non_trading_day_demo_override_evidence(args: argparse.Namespace, business_date: str) -> dict[str, Any]:
    calendar = resolve_operation_date(business_date, root=_base_dir_for_runtime_root(Path(args.runtime_root)))
    business_day = bool(calendar.get("is_business_day"))
    market_open = not bool(calendar.get("market_closed"))
    override_requested = bool(args.allow_non_trading_day_demo)
    override_active = bool(args.mode == "demo" and override_requested and not business_day and not market_open)
    return {
        "trading_day": business_day,
        "business_day": business_day,
        "market_open": market_open,
        "market_closed_reason": calendar.get("market_closed_reason") or "",
        "calendar_source": calendar.get("calendar_source") or "",
        "latest_available_market_date": calendar.get("latest_available_market_date") or "",
        "non_trading_day_demo_override_requested": override_requested,
        "non_trading_day_demo_override": override_active,
        "override_source": "operator_cli" if override_active else "not_applicable",
        "override_reason": "demo_acceptance_non_trading_day" if override_active else "not_applicable",
        "production_equivalent": not override_active,
        "acceptance_scope": "demo_acceptance_only" if override_active else "regular_runtime",
    }


def _non_trading_day_override_gate(args: argparse.Namespace, evidence: dict[str, Any]) -> tuple[str, str]:
    if args.mode == "production" and args.allow_non_trading_day_demo:
        evidence.update(
            {
                "non_trading_day_demo_override": False,
                "override_source": "operator_cli",
                "override_reason": "non_trading_day_demo_override_forbidden_in_production",
                "production_equivalent": False,
                "acceptance_scope": "forbidden_in_production",
            }
        )
        return "BLOCKED", "non_trading_day_demo_override_forbidden_in_production"
    if evidence["business_day"] and evidence["market_open"]:
        if args.allow_non_trading_day_demo:
            evidence.update(
                {
                    "non_trading_day_demo_override": False,
                    "override_source": "not_applicable",
                    "override_reason": "trading_day_override_not_applicable",
                    "production_equivalent": True,
                    "acceptance_scope": "regular_runtime",
                }
            )
        return "PASS", ""
    if args.mode == "demo" and args.allow_non_trading_day_demo:
        return "PASS", ""
    evidence.update(
        {
            "non_trading_day_demo_override": False,
            "override_source": "not_applicable",
            "override_reason": "non_trading_day",
            "production_equivalent": False,
            "acceptance_scope": "regular_runtime_stop",
        }
    )
    return "REVIEW_REQUIRED", "non_trading_day"


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
            ("position_management_ai", "Position Management AI decision producer checkpoint recorded."),
            ("sell_source", "SELL source checkpoint recorded; AI decision artifact drives SELL intent."),
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
        "safety_evaluation": (
            ("runtime_current", "Runtime Current SoT checkpoint recorded."),
            ("broker_readonly", "Broker ReadOnly evidence checkpoint recorded."),
            ("market_evidence", "Market/quote evidence checkpoint recorded."),
            ("orders_executions", "Order and execution evidence checkpoint recorded."),
            ("phase11_safety_report", "Phase11 Safety Report generation checkpoint recorded."),
            ("no_broker_write", "Safety evaluation performs no broker write."),
        ),
        "safety_refresh": (
            ("authoritative_safety_source", "Authoritative Safety evidence checkpoint recorded."),
            ("runtime_safety_decision_contract", "Runtime Safety Decision contract checkpoint recorded."),
            ("atomic_publish", "Runtime Safety Decision atomic publish checkpoint recorded."),
            ("no_broker_write", "Safety refresh performs no broker write."),
        ),
        "data_readiness": (
            ("runtime_data_readiness", "Runtime Data Readiness Gate checkpoint recorded."),
            ("read_only_evidence", "Read-only readiness artifact generation checkpoint recorded."),
            ("no_broker_write", "Data readiness performs no broker write."),
        ),
        "pending_lifecycle": (
            ("pending_lifecycle_review", "Pending lifecycle review checkpoint recorded."),
            ("history", "Pending lifecycle history checkpoint recorded."),
            ("no_broker_write", "Pending lifecycle performs no broker write."),
        ),
        "current_temporal_migration": (
            ("current_read", "Current SoT read checkpoint recorded."),
            ("ledger_market_evidence_read", "Ledger and Market Evidence read-only checkpoint recorded."),
            ("migration_candidate", "Current Temporal migration candidate checkpoint recorded."),
            ("apply_guard", "Apply requires explicit --apply-current-migration."),
            ("no_broker_write", "Current temporal migration performs no broker write."),
        ),
        "current_valuation_refresh": (
            ("current_temporal_read", "Current Temporal State read checkpoint recorded."),
            ("market_quote_evidence", "Market / Quote Evidence read checkpoint recorded."),
            ("valuation_projection", "Valuation-only projection checkpoint recorded."),
            ("apply_guard", "Apply requires explicit --apply-current-valuation."),
            ("no_broker_write", "Current valuation refresh performs no broker write."),
        ),
    }
    return [_stage(name, "CHECKPOINT", message) for name, message in job_steps[job]]


def _as_bool(value: str) -> bool:
    return value.lower() == "true"


def _parse_evaluation_time(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("--evaluation-time must include timezone")
    return parsed.astimezone(timezone.utc)


def _policy_required_for_job(job: str) -> bool:
    return job in {"morning", "sell_planning", "submit", "data_readiness"}


def _data_readiness_required_for_job(job: str) -> bool:
    return job in {"data_readiness", "morning", "sell_planning"}


def _readiness_scope_for_args(args: argparse.Namespace) -> str:
    if args.readiness_scope:
        return args.readiness_scope
    if args.job in {"morning", "sell_planning", "submit", "execution"}:
        return args.job
    return "morning"


def _load_capital_policy_manifest(policy_path: str | None) -> dict[str, Any]:
    if not policy_path:
        return missing_policy_manifest_fields(
            policy_path,
            reason="POLICY_MISSING:--capital-deployment-policy is required",
        )
    try:
        return load_capital_deployment_policy(Path(policy_path)).to_manifest_fields()
    except CapitalDeploymentPolicyError as exc:
        if "missing" in str(exc).lower():
            return missing_policy_manifest_fields(policy_path, reason="POLICY_MISSING:" + str(exc))
        return invalid_policy_manifest_fields(policy_path, reason="POLICY_INVALID:" + str(exc))


def _safety_stage_status(decision: Any) -> str:
    if decision is None:
        return "REVIEW_REQUIRED"
    if decision.safety_status != "PASS":
        return "REVIEW_REQUIRED"
    if decision.halt_runtime or decision.emergency_stop or decision.decision == "HALT":
        return "HALT"
    if decision.decision == "BLOCKED":
        return "BLOCKED"
    if decision.review_required or decision.decision == "REVIEW_REQUIRED":
        return "REVIEW_REQUIRED"
    return "PASS"


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
            "data_readiness_artifact",
            "current_temporal_migration_artifact",
            "current_valuation_refresh_artifact",
        }
    }


def _final_reason(*, errors: list[str], warnings: list[str]) -> str:
    if errors:
        return errors[0]
    if warnings:
        return warnings[0]
    return ""


def _previous_calendar_day(value: str) -> str:
    return (date.fromisoformat(value) - timedelta(days=1)).isoformat()


def _resolve_buy_ai_feature_date(args: argparse.Namespace, business_date: str) -> str:
    requested = args.feature_date or _previous_calendar_day(business_date)
    if args.feature_date:
        return requested
    operations_root = Path(args.feature_root).parent
    contract = load_feature_date_contract(
        operations_root=operations_root,
        requested_feature_date=requested,
    ) or resolve_feature_date_contract(
        operations_root=operations_root,
        requested_feature_date=requested,
    )
    return contract.selected_feature_date or requested


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
