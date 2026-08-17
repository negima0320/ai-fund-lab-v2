"""Runtime v2 daily operation rehearsal CLI.

The CLI is the single entrypoint intended for manual and launchd rehearsal
operation. It keeps external writes disabled for the initial launchd rehearsal.
"""

from __future__ import annotations

import argparse
import json
import traceback
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.operations.market_calendar import resolve_operation_date
from ai_fund_lab_v2.runtime_v2.orchestrator.models import RuntimeRunRequest
from ai_fund_lab_v2.runtime_v2.orchestrator.orchestrator import RuntimeOrchestrator
from ai_fund_lab_v2.runtime_v2.broker_readonly.refresh import run_broker_readonly_refresh
from ai_fund_lab_v2.runtime_v2.artifact_lookup import (
    RuntimeArtifactLookupHalt,
    resolve_runtime_capital_policy_path,
)
from ai_fund_lab_v2.runtime_v2.accepted_generation_resolver import resolve_accepted_generation
from ai_fund_lab_v2.runtime_v2.buy_ai.producer import produce_buy_ai_decisions
from ai_fund_lab_v2.runtime_v2.data_readiness import evaluate_runtime_data_readiness
from ai_fund_lab_v2.runtime_v2.lifecycle_sell_continuity import evaluate_sell_continuity_from_buy_lifecycle_gate
from ai_fund_lab_v2.runtime_v2.current_state.temporal import run_current_temporal_migration
from ai_fund_lab_v2.runtime_v2.current_state.valuation import run_current_valuation_refresh
from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import (
    run_execution_readonly_pipeline,
)
from ai_fund_lab_v2.runtime_v2.historical_support.environment import (
    EnvironmentCompositionError,
    resolve_environment_composition,
)
from ai_fund_lab_v2.runtime_v2.market_refresh.pipeline import (
    run_runtime_v2_market_refresh_pipeline,
)
from ai_fund_lab_v2.runtime_v2.market_refresh.feature_date_contract import (
    load_feature_date_contract,
    resolve_feature_date_contract,
)
from ai_fund_lab_v2.runtime_v2.planning.morning_pipeline import (
    evaluate_morning_capability,
    run_morning_ai_planning_pending_pipeline,
)
from ai_fund_lab_v2.runtime_v2.planning.strategy_authority import (
    activate_strategy_planning_authority,
)
from ai_fund_lab_v2.runtime_v2.planning.sell_pipeline import (
    evaluate_sell_planning_capability,
    run_sell_planning_pending_pipeline,
)
from ai_fund_lab_v2.runtime_v2.pending.lifecycle_runner import run_pending_lifecycle_review
from ai_fund_lab_v2.runtime_v2.pending_apply import run_authoritative_pending_apply_review
from ai_fund_lab_v2.runtime_v2.pending_promotion import run_submit_pending_promotion_review
from ai_fund_lab_v2.runtime_v2.position_management.producer import produce_position_management_decisions
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import (
    CapitalDeploymentPolicyError,
    capital_deployment_policy_hash,
    invalid_policy_manifest_fields,
    load_capital_deployment_policy,
    missing_policy_manifest_fields,
)
from ai_fund_lab_v2.runtime_v2.report.public_report_writer import (
    generate_public_report_from_current,
)
from ai_fund_lab_v2.runtime_v2.review_only.sell_hold_morning import (
    run_sell_hold_review_only_morning,
)
from ai_fund_lab_v2.runtime_v2.runtime_state import produce_runtime_operation_state
from ai_fund_lab_v2.runtime_v2.safety_decision import (
    RuntimeSafetyDecision,
    load_runtime_safety_decision,
    safety_manifest_fields,
)
from ai_fund_lab_v2.runtime_v2.safety.evaluation import run_runtime_safety_evaluation
from ai_fund_lab_v2.runtime_v2.safety.producer import produce_runtime_safety_decision
from ai_fund_lab_v2.runtime_v2.storage.json_safe import JsonSerializationContractError
from ai_fund_lab_v2.runtime_v2.storage.path_resolver import reject_mode_rooted_runtime_root
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline
from ai_fund_lab_v2.runtime_v2.submit.models import SubmitEnvironmentGuardContext
from ai_fund_lab_v2.strategy.shadow_runtime import (
    generate_strategy_shadow_for_day,
    update_run_strategy_shadow_indexes,
)

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
    "sell_hold_review_only_morning",
    "submit_pending_promotion_review",
    "authoritative_pending_apply_review",
    "submit",
    "execution",
    "market_refresh",
    "safety_evaluation",
    "safety_refresh",
    "data_readiness",
    "pending_lifecycle",
    "runtime_state_refresh",
    "current_temporal_migration",
    "current_valuation_refresh",
    "broker_readonly_refresh",
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
    capital_deployment_policy_path: Path | None = None
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
    sell_hold_review_only_manifest: dict[str, Any] = {}
    buy_ai_manifest: dict[str, Any] = {}
    data_readiness_manifest: dict[str, Any] = {}
    pending_lifecycle_manifest: dict[str, Any] = {}
    pending_promotion_manifest: dict[str, Any] = {}
    pending_apply_manifest: dict[str, Any] = {}
    market_evidence_manifest: dict[str, Any] = {}
    current_temporal_migration_manifest: dict[str, Any] = {}
    current_valuation_manifest: dict[str, Any] = {}
    broker_readonly_manifest: dict[str, Any] = {}
    runtime_state_manifest: dict[str, Any] = {}
    strategy_planning_authority_manifest: dict[str, Any] = {}
    environment_composition = None
    environment_manifest: dict[str, Any] = {}
    non_trading_day_evidence = _non_trading_day_demo_override_evidence(args, business_date)

    log_path = Path(args.log_root) / business_date / f"{run_id}.log"

    try:
        _append_log(log_path, f"run_id={run_id} stage=cli_start mode={args.mode} job={args.job}")
        _validate_rehearsal_args(args)
        evaluation_time = _parse_evaluation_time(args.evaluation_time)
        try:
            environment_composition = resolve_environment_composition(
                mode=args.mode,
                runtime_root=Path(args.runtime_root),
                broker_environment=args.broker_environment,
                external_delivery=args.notification_mode != "payload-only",
                broker_write=False
                if args.mode == "historical"
                else args.job == "submit" and _as_bool(args.submit_enabled),
                business_date=args.business_date,
                evaluation_time=args.evaluation_time,
                historical_asof_view_path=_historical_asof_view_path(args=args, business_date=business_date),
            )
        except EnvironmentCompositionError as exc:
            raise ValueError(str(exc)) from exc
        composition_fields = environment_composition.manifest_fields(
            runtime_root=Path(args.runtime_root),
            environment_id=f"{environment_composition.runtime_mode}:{environment_composition.broker_environment}",
            run_id=run_id,
            business_date=business_date,
            evaluation_time=args.evaluation_time or (evaluation_time.isoformat() if evaluation_time else ""),
        )
        environment_manifest = composition_fields if args.mode == "historical" else {}
        stages.append(_stage("cli_start", "PASS", "Runtime v2 daily operation CLI started."))
        stages.append(
            _stage(
                "environment_composition",
                "PASS",
                "Runtime environment composition resolved.",
                composition_fields,
            )
        )
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
        capital_policy_manifest = _load_capital_policy_manifest(
            args.capital_deployment_policy,
            runtime_root=Path(args.runtime_root),
        )
        if capital_policy_manifest["capital_deployment_policy_loaded"]:
            capital_deployment_policy_path = Path(capital_policy_manifest["capital_deployment_policy_path"])
            capital_deployment_policy = load_capital_deployment_policy(capital_deployment_policy_path)
        stages.append(
            _stage(
                "capital_deployment_policy",
                "PASS" if capital_policy_manifest["capital_deployment_policy_loaded"] else "REVIEW_REQUIRED",
                "Registry-resolved Capital Deployment Policy evaluated.",
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

        if exit_code != EXIT_HALT:
            runtime_state_result = produce_runtime_operation_state(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                mode=args.mode,
                state=final_state if final_state != "UNKNOWN" else "CURRENT_STATE_LOADED",
                safety_state=_runtime_safety_state_for_operation_state(runtime_safety_decision),
                now=evaluation_time,
            )
            runtime_state_manifest = dict(runtime_state_result.manifest_fields)
            stages.append(
                _stage(
                    "runtime_state_refresh",
                    runtime_state_result.status,
                    "Authoritative Runtime Operation State artifact refreshed.",
                    runtime_state_manifest,
                )
            )
            generated["runtime_state_artifact"] = runtime_state_result.artifact_path
            if runtime_state_result.status == "HALT":
                exit_code = EXIT_HALT
                final_state = "HALT"
                errors.append(runtime_state_result.reason)
            elif runtime_state_result.status == "REVIEW_REQUIRED" and exit_code == EXIT_SUCCESS:
                exit_code = EXIT_REVIEW_REQUIRED
                final_state = "REVIEW_REQUIRED"
                warnings.append(runtime_state_result.reason)

        if args.job == "pending_lifecycle" and exit_code == EXIT_SUCCESS:
            pending_lifecycle_result = run_pending_lifecycle_review(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                mode=args.mode,
                action=args.pending_action,
                now=evaluation_time,
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

        if args.job == "broker_readonly_refresh" and exit_code == EXIT_SUCCESS:
            broker_readonly_result = run_broker_readonly_refresh(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                mode=args.mode,
                evaluation_time=evaluation_time,
            )
            broker_readonly_manifest = dict(broker_readonly_result.manifest_fields)
            stages.append(
                _stage(
                    "broker_readonly_refresh",
                    broker_readonly_result.status,
                    "Broker ReadOnly snapshot-only producer executed without ledger or Current mutation.",
                    broker_readonly_result.to_stage_details(),
                )
            )
            generated["broker_readonly_snapshot_artifact"] = broker_readonly_result.snapshot_path
            if broker_readonly_result.status == "BLOCKED":
                exit_code = EXIT_BLOCKED
                final_state = "BLOCKED"
                errors.append(broker_readonly_result.reason)
            elif broker_readonly_result.status == "REVIEW_REQUIRED":
                exit_code = EXIT_REVIEW_REQUIRED
                final_state = "REVIEW_REQUIRED"
                warnings.append(broker_readonly_result.reason)

        data_readiness_result = None
        if _data_readiness_required_for_job(args.job, mode=args.mode) and exit_code == EXIT_SUCCESS:
            pre_readiness_lifecycle = _pre_data_readiness_pending_lifecycle_requirement(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
            )
            if pre_readiness_lifecycle["required"]:
                pending_lifecycle_result = run_pending_lifecycle_review(
                    runtime_root=Path(args.runtime_root),
                    business_date=business_date,
                    mode=args.mode,
                    action="review",
                    now=evaluation_time,
                )
                pending_lifecycle_manifest = {
                    "pre_data_readiness_pending_lifecycle_invoked": True,
                    "pre_data_readiness_pending_lifecycle_requirement": pre_readiness_lifecycle,
                    **dict(pending_lifecycle_result.manifest_fields),
                }
                stages.append(
                    _stage(
                        "pre_data_readiness_pending_lifecycle",
                        pending_lifecycle_result.status,
                        "Pending lifecycle authority resolved active stale Pending before Data Readiness.",
                        pending_lifecycle_manifest,
                    )
                )
                if pending_lifecycle_result.status == "REVIEW_REQUIRED":
                    exit_code = EXIT_REVIEW_REQUIRED
                    final_state = "REVIEW_REQUIRED"
                    warnings.append(pending_lifecycle_result.reason)
                elif pending_lifecycle_result.status in {"EXPIRED", "CANCELLED", "SUPERSEDED", "CONSUMED", "NOOP"}:
                    final_state = "CURRENT_STATE_LOADED"
            else:
                pending_lifecycle_manifest.update(
                    {
                        "pre_data_readiness_pending_lifecycle_invoked": False,
                        "pre_data_readiness_pending_lifecycle_requirement": pre_readiness_lifecycle,
                    }
                )
        if _data_readiness_required_for_job(args.job, mode=args.mode) and exit_code == EXIT_SUCCESS:
            data_readiness_result = evaluate_runtime_data_readiness(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                mode=args.mode,
                readiness_scope=_readiness_scope_for_args(args),
                feature_root=Path(args.feature_root),
                feature_date=args.feature_date
                if args.job == "data_readiness" or _readiness_scope_for_args(args) not in {"morning", "morning_full", "morning_sell_hold_review_only"}
                else _resolve_buy_ai_feature_date(args, business_date),
                candidate_model_path=args.candidate_model_path,
                opportunity_model_path=args.opportunity_model_path,
                pm_opportunity_path=args.pm_opportunity_path,
                pm_feature_path=args.pm_feature_path,
                allow_non_trading_day_demo=args.allow_non_trading_day_demo,
                broker_environment=args.broker_environment,
                runtime_test_evidence_root=args.runtime_test_evidence_root,
                runtime_test_run_id=args.runtime_test_run_id,
                runtime_test_profile_id=args.runtime_test_profile_id,
                broker_write=False,
                external_delivery=args.notification_mode != "payload-only",
                now=evaluation_time,
            )
            data_readiness_manifest = data_readiness_result.to_manifest_fields()
            data_readiness_manifest.update(_data_readiness_safety_summary_fields(data_readiness_result.payload))
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
        effective_safety_decision = _effective_runtime_safety_decision(
            args=args,
            business_date=business_date,
            runtime_safety_decision=runtime_safety_decision,
            data_readiness_manifest=data_readiness_manifest,
        )
        if effective_safety_decision is not runtime_safety_decision:
            stages.append(
                _stage(
                    "historical_safety_authority",
                    "PASS",
                    "Historical safety authority from Data Readiness propagated to downstream Planning.",
                    safety_manifest_fields(effective_safety_decision)
                    | {
                        "ignored_latest_safety_decision": data_readiness_manifest.get("data_readiness_ignored_latest_safety_decision") or "",
                        "source_safety_decision": "data_readiness_historical_temporal_authority",
                    },
                )
            )

        if args.job == "current_valuation_refresh" and exit_code == EXIT_SUCCESS:
            current_valuation_result = run_current_valuation_refresh(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                apply_current_valuation=args.apply_current_valuation,
                now=evaluation_time,
                market_evidence_path=_historical_asof_view_path(args=args, business_date=business_date) or None,
                safety_authority=safety_manifest_fields(effective_safety_decision),
                runtime_test_context=_runtime_test_context(args=args, business_date=business_date),
                environment_context=environment_manifest,
                allow_legacy_temporal_current=args.mode == "historical",
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

        if args.job == "morning" and exit_code == EXIT_SUCCESS:
            buy_ai_result = produce_buy_ai_decisions(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                feature_root=Path(args.feature_root),
                feature_date=_resolve_buy_ai_feature_date(args, business_date),
                candidate_model_path=args.candidate_model_path,
                opportunity_model_path=args.opportunity_model_path,
                opportunity_training_metrics_path=args.opportunity_training_metrics_path,
                historical_evaluation_authority_path=args.historical_evaluation_authority or None,
                selected_rank_limit=args.max_orders,
                now=evaluation_time,
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
            if buy_ai_result.status == "HALT":
                exit_code = EXIT_HALT
                final_state = "HALT"
                errors.append(f"buy ai halt: {buy_ai_result.reason}")
            elif buy_ai_result.status == "BLOCKED":
                sell_continuity = evaluate_sell_continuity_from_buy_lifecycle_gate(buy_ai_result.lifecycle_gate_evidence or {})
                stages.extend(_buy_lifecycle_continuity_stages(sell_continuity.to_dict()))
                exit_code = EXIT_BLOCKED
                final_state = "BLOCKED"
                errors.append(f"buy ai blocked: {buy_ai_result.reason}")
            elif buy_ai_result.status == "REVIEW_REQUIRED":
                sell_continuity = evaluate_sell_continuity_from_buy_lifecycle_gate(buy_ai_result.lifecycle_gate_evidence or {})
                stages.extend(_buy_lifecycle_continuity_stages(sell_continuity.to_dict()))
                exit_code = EXIT_REVIEW_REQUIRED
                final_state = "REVIEW_REQUIRED"
                warnings.append(f"buy ai review required: {buy_ai_result.reason}")
        if args.job == "morning" and exit_code == EXIT_SUCCESS:
            morning_capability_context = _morning_capability_context(
                args=args,
                environment_manifest=environment_manifest,
            )
            morning_capability_decision = evaluate_morning_capability(
                mode=args.mode,
                context=morning_capability_context,
            )
            stages.append(
                _stage(
                    "environment_capability_decision",
                    morning_capability_decision.status,
                    "Morning environment/capability policy evaluated before Planning.",
                    morning_capability_decision.to_payload(),
                )
            )
            if morning_capability_decision.status != "PASS":
                exit_code = EXIT_BLOCKED
                final_state = "BLOCKED"
                errors.append(morning_capability_decision.reason)
        if args.job == "morning" and exit_code == EXIT_SUCCESS:
            pm_result = produce_position_management_decisions(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                mode=args.mode,
                feature_date=args.feature_date,
                opportunity_path=args.pm_opportunity_path,
                feature_path=args.pm_feature_path,
                now=evaluation_time,
            )
            position_management_manifest = {
                **pm_result.to_manifest_fields(),
                "strategy_planning_pm_authority": True,
                "strategy_planning_pm_authority_reason": "same_day_pm_materialized_before_formal_strategy_generation",
                "strategy_planning_pm_consumer": "phase22_strategy_artifact_generation",
            }
            stages.append(
                _stage(
                    "position_management_ai_runtime_producer",
                    pm_result.status,
                    "Position Management AI generated same-day PM authority before formal Strategy artifact generation.",
                    position_management_manifest,
                )
            )
            if pm_result.status == "REVIEW_REQUIRED":
                exit_code = EXIT_REVIEW_REQUIRED
                final_state = "REVIEW_REQUIRED"
                warnings.append(f"position management review required before strategy planning: {pm_result.reason}")
            elif pm_result.status in {"BLOCK", "BLOCKED", "HALT"}:
                exit_code = EXIT_BLOCKED if pm_result.status in {"BLOCK", "BLOCKED"} else EXIT_HALT
                final_state = "BLOCKED" if pm_result.status in {"BLOCK", "BLOCKED"} else "HALT"
                errors.append(f"position management unavailable before strategy planning: {pm_result.reason}")
        if args.job == "morning" and exit_code == EXIT_SUCCESS:
            strategy_run_dir = _strategy_planning_run_dir(args=args, run_id=run_id)
            strategy_summary = generate_strategy_shadow_for_day(
                run_dir=strategy_run_dir,
                runtime_root=Path(args.runtime_root),
                run_id=args.runtime_test_run_id or run_id,
                profile_id=args.runtime_test_profile_id or args.mode,
                business_date=business_date,
                feature_date=args.feature_date or business_date,
                feature_date_authority={
                    "authority_status": "PASS",
                    "planned_feature_date": args.feature_date or business_date,
                    "materialized_feature_date": args.feature_date or business_date,
                    "selected_feature_date": args.feature_date or business_date,
                    "feature_date_authority_source": "daily_operation_morning_strategy_planning_authority",
                    "planned_matches_materialized": True,
                },
                historical_evaluation_authority_path=args.historical_evaluation_authority or "",
                artifact_subdir="strategy",
                decision_timing="MORNING_FORMAL_PLANNING_AUTHORITY",
                authority_role="FORMAL_PLANNING_AUTHORITY_INPUT",
                materialization_role="IMMUTABLE_MORNING_PLANNING_SNAPSHOT",
            )
            stages.append(
                _stage(
                    "phase22_strategy_artifact_generation",
                    strategy_summary.get("strategy_shadow_judgment", "REVIEW_REQUIRED"),
                    "Phase22 Strategy artifacts generated for formal Planning Authority consumption.",
                    strategy_summary,
                )
            )
            strategy_dir = strategy_run_dir / "daily" / business_date / "strategy"
            morning_result = activate_strategy_planning_authority(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                mode=args.mode,
                strategy_dir=strategy_dir,
                target_session_date=business_date,
                environment_capability_context=morning_capability_context,
                safety_authority_payload=_strategy_planning_safety_authority_payload(
                    args=args,
                    business_date=business_date,
                    safety_decision=effective_safety_decision,
                    data_readiness_manifest=data_readiness_manifest,
                ),
                submit_policy_authority_payload=_strategy_planning_submit_policy_authority_payload(
                    capital_deployment_policy=capital_deployment_policy,
                ),
            )
            strategy_planning_authority_manifest = morning_result.to_stage_details()
            _mark_strategy_planning_authority_consumer_called(
                strategy_run_dir=strategy_run_dir,
                strategy_dir=strategy_dir,
                result=strategy_planning_authority_manifest,
            )
            stages.append(
                _stage(
                    "phase23_i_strategy_planning_authority_pipeline",
                    morning_result.status,
                    "Phase22 Strategy Planning Authority consumed artifacts and wrote Pending without Broker Write.",
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
            sell_capability_context = _morning_capability_context(
                args=args,
                environment_manifest=environment_manifest,
            )
            sell_capability_decision = evaluate_sell_planning_capability(
                mode=args.mode,
                context=sell_capability_context,
            )
            stages.append(
                _stage(
                    "environment_capability_decision",
                    sell_capability_decision.status,
                    "SELL Planning environment/capability policy evaluated before PM and Planning.",
                    sell_capability_decision.to_payload(),
                )
            )
            if sell_capability_decision.status != "PASS":
                exit_code = EXIT_BLOCKED
                final_state = "BLOCKED"
                errors.append(sell_capability_decision.reason)
        if args.job == "sell_planning" and exit_code == EXIT_SUCCESS:
            pm_result = produce_position_management_decisions(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                mode=args.mode,
                feature_date=args.feature_date,
                opportunity_path=args.pm_opportunity_path,
                feature_path=args.pm_feature_path,
                now=evaluation_time,
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
            if pm_result.status == "NO_POSITION":
                warnings.append("sell planning no position: existing pending continuity preserved")
            if exit_code == EXIT_SUCCESS and pm_result.status != "NO_POSITION":
                sell_result = run_sell_planning_pending_pipeline(
                    runtime_root=Path(args.runtime_root),
                    business_date=business_date,
                    mode=args.mode,
                    exit_decisions=pm_result.sell_exit_decisions,
                    max_orders=args.max_orders,
                    capital_deployment_policy=capital_deployment_policy,
                    submit_policy_context=_strategy_planning_submit_policy_authority_payload(
                        capital_deployment_policy=capital_deployment_policy,
                    ),
                    accepted_generation_binding=_accepted_generation_binding_for_runtime_job(
                        args=args,
                        business_date=business_date,
                        consumer="sell_planning_pending_pipeline",
                    ),
                    safety_decision=effective_safety_decision,
                    environment_capability_context=sell_capability_context,
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

        if args.job == "sell_hold_review_only_morning" and exit_code == EXIT_SUCCESS:
            review_only_result = run_sell_hold_review_only_morning(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                mode=args.mode,
                feature_date=args.feature_date or business_date,
                now=evaluation_time,
            )
            sell_hold_review_only_manifest = dict(review_only_result.to_stage_details())
            stages.append(
                _stage(
                    "sell_hold_review_only_morning",
                    review_only_result.status,
                    "SELL/HOLD Review-only Morning generated PM AI and human review evidence without Submit or Broker Write.",
                    sell_hold_review_only_manifest,
                )
            )
            generated["sell_hold_review_output"] = review_only_result.review_output_path
            generated["sell_hold_review_pending"] = review_only_result.review_pending_path
            if review_only_result.status == "REVIEW_REQUIRED":
                exit_code = EXIT_REVIEW_REQUIRED
                final_state = "REVIEW_REQUIRED"
                warnings.append(f"sell hold review-only morning review required: {review_only_result.reason}")
            elif review_only_result.status == "BLOCKED":
                exit_code = EXIT_BLOCKED
                final_state = "BLOCKED"
                errors.append(f"sell hold review-only morning blocked: {review_only_result.reason}")
            elif review_only_result.status == "HALT":
                exit_code = EXIT_HALT
                final_state = "HALT"
                errors.append(f"sell hold review-only morning halted: {review_only_result.reason}")

        if args.job == "submit_pending_promotion_review" and exit_code == EXIT_SUCCESS:
            promotion_result = run_submit_pending_promotion_review(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                mode=args.mode,
                capital_deployment_policy_path=capital_deployment_policy_path,
                now=evaluation_time,
            )
            pending_promotion_manifest = dict(promotion_result.to_stage_details())
            stages.append(
                _stage(
                    "submit_pending_promotion_review",
                    promotion_result.status,
                    "Review Pending plus Human Approval produced a no-apply Submit Pending Promotion Candidate.",
                    pending_promotion_manifest,
                )
            )
            generated["human_approval_artifact"] = promotion_result.human_approval_path
            generated["review_pending_linkage_artifact"] = promotion_result.review_pending_linkage_path
            generated["pending_promotion_candidate"] = promotion_result.promotion_candidate_path
            if promotion_result.status == "REVIEW_REQUIRED":
                exit_code = EXIT_REVIEW_REQUIRED
                final_state = "REVIEW_REQUIRED"
                warnings.append(promotion_result.reason)
            elif promotion_result.status == "BLOCKED":
                exit_code = EXIT_BLOCKED
                final_state = "BLOCKED"
                errors.append(promotion_result.reason)
            elif promotion_result.status == "HALT":
                exit_code = EXIT_HALT
                final_state = "HALT"
                errors.append(promotion_result.reason)

        if args.job == "authoritative_pending_apply_review" and exit_code == EXIT_SUCCESS:
            pending_apply_result = run_authoritative_pending_apply_review(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                mode=args.mode,
                capital_deployment_policy_path=capital_deployment_policy_path,
                promotion_candidate_path=Path(args.promotion_candidate_path) if args.promotion_candidate_path else None,
                now=evaluation_time,
            )
            pending_apply_manifest = dict(pending_apply_result.to_stage_details())
            stages.append(
                _stage(
                    "authoritative_pending_apply_review",
                    pending_apply_result.status,
                    "Promotion Candidate plus Human Approval produced a no-apply Authoritative Pending Apply Candidate.",
                    pending_apply_manifest,
                )
            )
            generated["authoritative_pending_apply_candidate"] = pending_apply_result.apply_candidate_path
            if pending_apply_result.status == "REVIEW_REQUIRED":
                exit_code = EXIT_REVIEW_REQUIRED
                final_state = "REVIEW_REQUIRED"
                warnings.append(pending_apply_result.reason)
            elif pending_apply_result.status == "BLOCKED":
                exit_code = EXIT_BLOCKED
                final_state = "BLOCKED"
                errors.append(pending_apply_result.reason)
            elif pending_apply_result.status == "HALT":
                exit_code = EXIT_HALT
                final_state = "HALT"
                errors.append(pending_apply_result.reason)

        submit_result = None
        if args.job == "submit" and _as_bool(args.submit_enabled) and exit_code == EXIT_SUCCESS:
            submit_result = run_submit_pipeline(
                runtime_root=Path(args.runtime_root),
                business_date=business_date,
                mode=args.mode,
                submit_enabled=_as_bool(args.submit_enabled),
                job=args.job,
                capital_deployment_policy_path=capital_deployment_policy_path,
                safety_decision=effective_safety_decision,
                now=evaluation_time,
                adapter=environment_composition.submit_adapter if environment_composition is not None else None,
                environment_context=_submit_environment_context(
                    args=args,
                    composition=environment_composition,
                    business_date=business_date,
                    evaluation_time=args.evaluation_time or (evaluation_time.isoformat() if evaluation_time else ""),
                )
                if environment_composition is not None
                else None,
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
                snapshot_provider=environment_composition.execution_snapshot_provider
                if environment_composition is not None
                else None,
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
                now=evaluation_time,
                runtime_test_context=_runtime_test_context(args=args, business_date=business_date),
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
                sell_hold_review_only_manifest=sell_hold_review_only_manifest,
                buy_ai_manifest=buy_ai_manifest,
                data_readiness_manifest=data_readiness_manifest,
                pending_lifecycle_manifest=pending_lifecycle_manifest,
                pending_promotion_manifest=pending_promotion_manifest,
                pending_apply_manifest=pending_apply_manifest,
                market_evidence_manifest=market_evidence_manifest,
                current_temporal_migration_manifest=current_temporal_migration_manifest,
                current_valuation_manifest=current_valuation_manifest,
                broker_readonly_manifest=broker_readonly_manifest,
                runtime_state_manifest=runtime_state_manifest,
                strategy_planning_authority_manifest=strategy_planning_authority_manifest,
                environment_manifest=environment_manifest,
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
    except JsonSerializationContractError as exc:
        exit_code = EXIT_UNEXPECTED_ERROR
        final_state = "HALT"
        errors.append(f"runtime evidence serialization error: {exc.field_path} {exc.python_type}")
        details = _serialization_error_details(args=args, business_date=business_date, exc=exc)
        stages.append(_stage("serialization_error", "HALT", "Runtime evidence serialization contract failed.", details))
        _write_morning_failure_evidence(
            args=args,
            business_date=business_date,
            run_id=run_id,
            error_payload=details,
            data_readiness_manifest=data_readiness_manifest,
            environment_manifest=environment_manifest,
            stack_trace=traceback.format_exc(),
        )
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
        sell_hold_review_only_manifest=sell_hold_review_only_manifest,
        buy_ai_manifest=buy_ai_manifest,
        data_readiness_manifest=data_readiness_manifest,
        pending_lifecycle_manifest=pending_lifecycle_manifest,
        pending_promotion_manifest=pending_promotion_manifest,
        pending_apply_manifest=pending_apply_manifest,
        market_evidence_manifest=market_evidence_manifest,
        current_temporal_migration_manifest=current_temporal_migration_manifest,
        current_valuation_manifest=current_valuation_manifest,
        broker_readonly_manifest=broker_readonly_manifest,
        runtime_state_manifest=runtime_state_manifest,
        strategy_planning_authority_manifest=strategy_planning_authority_manifest,
        environment_manifest=environment_manifest,
        submit_result=submit_result if "submit_result" in locals() else None,
    )
    manifest_path = _write_manifest(Path(args.manifest_root), business_date, run_id, manifest)
    if args.runtime_test_evidence_root and args.job == "morning":
        _write_morning_manifest_evidence(
            evidence_root=Path(args.runtime_test_evidence_root),
            business_date=business_date,
            manifest_path=manifest_path,
            manifest=manifest,
        )
    if args.runtime_test_evidence_root and args.job == "sell_planning":
        _write_sell_planning_manifest_evidence(
            evidence_root=Path(args.runtime_test_evidence_root),
            business_date=business_date,
            manifest_path=manifest_path,
            manifest=manifest,
        )
    if args.runtime_test_evidence_root and args.job == "execution":
        _write_execution_manifest_evidence(
            evidence_root=Path(args.runtime_test_evidence_root),
            business_date=business_date,
            manifest_path=manifest_path,
            manifest=manifest,
        )
    if args.runtime_test_evidence_root and args.job == "current_valuation_refresh":
        _write_current_valuation_manifest_evidence(
            evidence_root=Path(args.runtime_test_evidence_root),
            business_date=business_date,
            manifest_path=manifest_path,
            manifest=manifest,
        )
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
    sell_hold_review_only_manifest: dict[str, Any],
    buy_ai_manifest: dict[str, Any],
    data_readiness_manifest: dict[str, Any],
    pending_lifecycle_manifest: dict[str, Any],
    pending_promotion_manifest: dict[str, Any],
    pending_apply_manifest: dict[str, Any],
    market_evidence_manifest: dict[str, Any],
    current_temporal_migration_manifest: dict[str, Any],
    current_valuation_manifest: dict[str, Any],
    broker_readonly_manifest: dict[str, Any],
    runtime_state_manifest: dict[str, Any],
    strategy_planning_authority_manifest: dict[str, Any],
    environment_manifest: dict[str, Any],
    submit_result: Any,
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "run_id": run_id,
        "runtime_test_run_id": args.runtime_test_run_id or "",
        "runtime_test_profile_id": args.runtime_test_profile_id or "",
        "runtime_test_evidence_root": args.runtime_test_evidence_root or "",
        "historical_evaluation_authority_path": args.historical_evaluation_authority or "",
        "historical_evaluation_authority_mode": "BUSINESS_DATE_BOUND_RUN_START_FIXED" if args.historical_evaluation_authority else "",
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
        **sell_hold_review_only_manifest,
        **buy_ai_manifest,
        **data_readiness_manifest,
        **pending_lifecycle_manifest,
        **pending_promotion_manifest,
        **pending_apply_manifest,
        **market_evidence_manifest,
        **current_temporal_migration_manifest,
        **current_valuation_manifest,
        **broker_readonly_manifest,
        **runtime_state_manifest,
        **_strategy_planning_authority_manifest_fields(strategy_planning_authority_manifest),
        **environment_manifest,
        **capital_policy_manifest,
        **safety_manifest_fields(runtime_safety_decision),
        **_historical_safety_manifest_override(args=args, data_readiness_manifest=data_readiness_manifest),
        **_submit_manifest_fields(submit_result),
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


def _submit_manifest_fields(submit_result: Any) -> dict[str, Any]:
    if submit_result is None:
        return {}
    return {
        "pending_read_valid": bool(getattr(submit_result, "pending_read_valid", False)),
        "pending_classification": str(getattr(submit_result, "pending_classification", "") or ""),
        "pending_active": getattr(submit_result, "pending_active", None),
        "pending_plan_present": bool(getattr(submit_result, "pending_plan_present", False)),
        "pending_item_count": int(getattr(submit_result, "pending_item_count", 0) or 0),
        "no_action_reason": str(getattr(submit_result, "no_action_reason", "") or ""),
        "no_order_authority_status": str(getattr(submit_result, "no_order_authority_status", "") or ""),
        "no_order_authority_reason": str(getattr(submit_result, "no_order_authority_reason", "") or ""),
        "no_order_authority_evidence": dict(getattr(submit_result, "no_order_authority_evidence", {}) or {}),
        "submit_action": str(getattr(submit_result, "submit_action", "UNKNOWN") or "UNKNOWN"),
        "submitted_count": int(getattr(submit_result, "submitted_count", 0) or 0),
        "blocked_count": int(getattr(submit_result, "blocked_count", 0) or 0),
        "review_required": bool(getattr(submit_result, "review_required", False)),
        "halt_required": bool(getattr(submit_result, "halt_required", False)),
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("demo", "historical", "simulation", "production"), required=True)
    parser.add_argument("--job", choices=ALLOWED_JOBS, default="daily_rehearsal")
    parser.add_argument(
        "--readiness-scope",
        choices=(
            "morning",
            "morning_full",
            "morning_sell_hold_review_only",
            "sell_planning",
            "submit",
            "execution",
        ),
    )
    parser.add_argument("--pending-action", choices=("review", "expire", "cancel"), default="review")
    parser.add_argument("--business-date")
    parser.add_argument("--broker-environment")
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
    parser.add_argument("--promotion-candidate-path")
    parser.add_argument("--safety-report-path")
    parser.add_argument("--market-refresh-allow-api-fetch", choices=("true", "false"), default="false")
    parser.add_argument("--allow-non-trading-day-demo", action="store_true")
    parser.add_argument("--evaluation-time")
    parser.add_argument("--apply-current-migration", action="store_true")
    parser.add_argument("--apply-current-valuation", action="store_true")
    parser.add_argument("--runtime-test-run-id")
    parser.add_argument("--runtime-test-profile-id")
    parser.add_argument("--runtime-test-evidence-root")
    parser.add_argument("--runtime-test-source-commit")
    parser.add_argument("--historical-evaluation-authority")
    return parser.parse_args(argv)


def _validate_rehearsal_args(args: argparse.Namespace) -> None:
    if args.mode == "simulation":
        raise ValueError("simulation is not a formal Runtime environment; use --mode historical")
    reject_mode_rooted_runtime_root(Path(args.runtime_root))
    if args.max_orders is not None and args.max_orders < 0:
        raise ValueError("--max-orders must be non-negative")
    if args.mode == "historical":
        if not args.business_date:
            raise ValueError("historical mode requires --business-date")
        if not args.evaluation_time:
            raise ValueError("historical mode requires --evaluation-time")
        if args.broker_environment not in {None, "historical_simulated"}:
            raise ValueError("historical mode requires --broker-environment historical_simulated")
        if args.historical_evaluation_authority and not Path(args.historical_evaluation_authority).is_file():
            raise ValueError("historical evaluation authority file is missing")
        if args.notification_mode != "payload-only":
            raise ValueError("historical mode requires --notification-mode payload-only")
        if _as_bool(args.market_refresh_allow_api_fetch):
            raise ValueError("historical mode requires --market-refresh-allow-api-fetch false")
        if _as_bool(args.submit_enabled) and args.job != "submit":
            raise ValueError("Runtime v2 daily scheduler allows --submit-enabled true only for submit job")
        return
    if args.historical_evaluation_authority:
        raise ValueError("--historical-evaluation-authority is allowed only with --mode historical")
    if args.notification_mode != "payload-only":
        raise ValueError("Runtime v2 daily scheduler requires --notification-mode payload-only")
    if _as_bool(args.submit_enabled) and args.job != "submit":
        raise ValueError("Runtime v2 daily scheduler allows --submit-enabled true only for submit job")
    if args.mode == "production":
        if _as_bool(args.submit_enabled):
            raise ValueError("production submit requires explicit production acceptance outside scheduler rehearsal")
        return
    if args.mode == "demo":
        runtime_root = Path(args.runtime_root)
        runtime_root_text = str(runtime_root)
        if runtime_root_text.endswith("/demo") or "/demo/" in runtime_root_text:
            raise ValueError("mode-rooted Current path is not allowed")
        return
    raise ValueError(f"unsupported Runtime v2 daily scheduler mode: {args.mode}")


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
    if args.mode == "historical":
        evidence.update(
            {
                "non_trading_day_demo_override": False,
                "override_source": "not_applicable",
                "override_reason": "historical_replay_calendar_context",
                "production_equivalent": False,
                "acceptance_scope": "historical_replay",
            }
        )
        return "PASS", ""
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
        "sell_hold_review_only_morning": (
            ("runtime_state", "Runtime State checkpoint recorded."),
            ("data_readiness", "Review-only Data Readiness checkpoint recorded."),
            ("position_management_ai", "Position Management AI review checkpoint recorded."),
            ("sell_hold_review", "SELL/HOLD review output checkpoint recorded."),
            ("review_pending", "Review Pending artifact checkpoint recorded."),
            ("no_buy_path", "BUY inference and BUY Planning remain blocked."),
            ("no_submit", "Review-only Morning performs no Submit."),
            ("no_broker_write", "Review-only Morning performs no Broker write."),
        ),
        "submit_pending_promotion_review": (
            ("review_pending", "Review Pending evidence checkpoint recorded."),
            ("human_approval", "Human Approval artifact checkpoint recorded."),
            ("promotion_validation", "Submit Pending promotion validation checkpoint recorded."),
            ("promotion_candidate", "No-apply Promotion Candidate artifact checkpoint recorded."),
            ("no_pending_apply", "Authoritative Pending slot remains unchanged."),
            ("no_submit", "Promotion review performs no Submit."),
            ("no_broker_write", "Promotion review performs no Broker write."),
        ),
        "authoritative_pending_apply_review": (
            ("promotion_candidate", "Promotion Candidate evidence checkpoint recorded."),
            ("human_approval", "Human Approval evidence checkpoint recorded."),
            ("apply_preconditions", "Authoritative Pending Apply preconditions checkpoint recorded."),
            ("toctou_revalidation", "TOCTOU revalidation checkpoint recorded."),
            ("apply_candidate", "No-apply Authoritative Pending Apply Candidate artifact checkpoint recorded."),
            ("no_authoritative_pending_mutation", "Authoritative Pending slot remains unchanged."),
            ("no_submit", "Apply review performs no Submit."),
            ("no_broker_write", "Apply review performs no Broker write."),
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
        "runtime_state_refresh": (
            ("runtime_state_contract", "Runtime Operation State contract checkpoint recorded."),
            ("atomic_publish", "Runtime Operation State fixed-path artifact checkpoint recorded."),
            ("no_broker_write", "Runtime state refresh performs no broker write."),
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
        "broker_readonly_refresh": (
            ("broker_readonly_snapshot", "Broker ReadOnly snapshot-only evidence checkpoint recorded."),
            ("read_only_guarantee", "Broker ReadOnly refresh does not submit or cancel orders."),
            ("no_ledger_append", "Broker ReadOnly refresh does not append persistent ledger records."),
            ("no_current_apply", "Broker ReadOnly refresh does not mutate Current Position."),
            ("no_pending_mutation", "Broker ReadOnly refresh does not mutate Pending."),
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
    return job in {
        "morning",
        "sell_planning",
        "sell_hold_review_only_morning",
        "submit_pending_promotion_review",
        "authoritative_pending_apply_review",
        "submit",
        "data_readiness",
    }


def _data_readiness_required_for_job(job: str, *, mode: str = "") -> bool:
    if job == "current_valuation_refresh":
        return mode == "historical"
    return job in {
        "data_readiness",
        "morning",
        "sell_planning",
        "sell_hold_review_only_morning",
        "submit",
    }


def _pre_data_readiness_pending_lifecycle_requirement(*, runtime_root: Path, business_date: str) -> dict[str, Any]:
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    payload = _read_json_file(pending_path)
    state = str(payload.get("state") or payload.get("status") or "").upper()
    target_session_date = str(payload.get("target_session_date") or "")
    active_pending = _pending_slot_active(payload)
    required = bool(active_pending and target_session_date and target_session_date < business_date)
    return {
        "schema_version": "runtime_v2_pre_data_readiness_pending_lifecycle_requirement_v1",
        "status": "PENDING_LIFECYCLE_REQUIRED" if required else "NOT_REQUIRED",
        "required": required,
        "reason": "active_pending_target_session_date_elapsed" if required else "no_pre_data_readiness_lifecycle_required",
        "pending_path": str(pending_path) if pending_path.is_file() else "",
        "pending_present": pending_path.is_file(),
        "active_pending": active_pending,
        "pending_state": state,
        "target_session_date": target_session_date,
        "business_date": business_date,
        "orchestration_layer_reimplemented_lifecycle_rules": False,
        "lifecycle_authority": "runtime_v2.pending.lifecycle_runner.run_pending_lifecycle_review",
    }


def _pending_slot_active(payload: dict[str, Any]) -> bool:
    if not payload:
        return False
    state = str(payload.get("state") or payload.get("status") or "").upper()
    if state == "EMPTY":
        return False
    if "active_pending" in payload:
        return bool(payload.get("active_pending"))
    return bool(payload.get("items"))


def _readiness_scope_for_args(args: argparse.Namespace) -> str:
    if args.readiness_scope:
        return args.readiness_scope
    if args.job == "sell_hold_review_only_morning":
        return "morning_sell_hold_review_only"
    if args.job == "current_valuation_refresh":
        return "current_valuation"
    if args.job in {"morning", "sell_planning", "submit", "execution"}:
        return args.job
    return "morning"


def _load_capital_policy_manifest(policy_path: str | None, *, runtime_root: Path) -> dict[str, Any]:
    if _isolated_runtime_root(runtime_root) and policy_path:
        try:
            return load_capital_deployment_policy(Path(policy_path)).to_manifest_fields() | {
                "capital_deployment_policy_authority": "ISOLATED_TEST_DIAGNOSTIC",
            }
        except CapitalDeploymentPolicyError as exc:
            if "missing" in str(exc).lower():
                return missing_policy_manifest_fields(policy_path, reason="POLICY_MISSING:" + str(exc))
            return invalid_policy_manifest_fields(policy_path, reason="POLICY_INVALID:" + str(exc))
    try:
        resolved_policy_path = resolve_runtime_capital_policy_path(policy_path)
    except RuntimeArtifactLookupHalt as exc:
        return missing_policy_manifest_fields(
            policy_path,
            reason="REGISTRY_POLICY_LOOKUP_HALT:" + str(exc),
        )
    try:
        return load_capital_deployment_policy(resolved_policy_path).to_manifest_fields() | {
            "capital_deployment_policy_authority": "ARTIFACT_REGISTRY",
        }
    except CapitalDeploymentPolicyError as exc:
        if "missing" in str(exc).lower():
            return missing_policy_manifest_fields(resolved_policy_path, reason="POLICY_MISSING:" + str(exc))
        return invalid_policy_manifest_fields(resolved_policy_path, reason="POLICY_INVALID:" + str(exc))


def _isolated_runtime_root(runtime_root: Path) -> bool:
    try:
        return runtime_root.resolve() != Path(".runtime").resolve()
    except FileNotFoundError:
        return runtime_root != Path(".runtime")


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


def _runtime_safety_state_for_operation_state(decision: Any) -> str:
    if decision is None:
        return "NORMAL"
    if getattr(decision, "halt_runtime", False) or getattr(decision, "emergency_stop", False):
        return "SYSTEM_EMERGENCY_STOP"
    if getattr(decision, "decision", "") in {"HALT", "EMERGENCY_STOP"}:
        return "SYSTEM_EMERGENCY_STOP"
    if getattr(decision, "decision", "") in {"BLOCKED", "REVIEW_REQUIRED"} or getattr(decision, "review_required", False):
        return "BUY_REVIEW_REQUIRED"
    return "NORMAL"


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


def _strategy_planning_run_dir(*, args: argparse.Namespace, run_id: str) -> Path:
    if args.runtime_test_evidence_root:
        return Path(args.runtime_test_evidence_root)
    return Path(args.runtime_root) / "runtime_state" / "strategy_planning" / run_id


def _strategy_planning_authority_manifest_fields(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload:
        return {
            "strategy_planning_authority": "NOT_EVALUATED",
            "strategy_planning_authority_active": False,
            "strategy_consumer_broker_write_allowed": False,
            "strategy_consumer_broker_write_performed": False,
            "strategy_consumer_runtime_switch_performed": False,
            "legacy_planning_authority_used": False,
        }
    return {
        "strategy_planning_authority": payload.get("planning_consumer_eligibility") or "",
        "strategy_planning_authority_active": payload.get("planning_consumer_eligibility") == "ELIGIBLE",
        "strategy_artifact_eligibility": payload.get("strategy_artifact_eligibility") or "",
        "strategy_consumer_broker_write_allowed": bool(payload.get("broker_write_allowed")),
        "strategy_consumer_broker_write_performed": bool(payload.get("broker_write_performed")),
        "strategy_consumer_runtime_switch_performed": bool(payload.get("runtime_switch_performed")),
        "legacy_planning_authority_used": bool(payload.get("legacy_planning_authority_used")),
        "strategy_planning_order_plan_path": payload.get("order_plan_artifact_path") or "",
        "strategy_planning_pending_path": payload.get("pending_path") or "",
        "strategy_planning_selected_symbols": payload.get("selected_symbols") or [],
    }


def _mark_strategy_planning_authority_consumer_called(
    *,
    strategy_run_dir: Path,
    strategy_dir: Path,
    result: dict[str, Any],
) -> None:
    summary_path = strategy_dir / "strategy_shadow_summary.json"
    if not summary_path.is_file():
        return
    summary = _read_json_file(summary_path)
    planning_eligible = result.get("planning_consumer_eligibility") == "ELIGIBLE"
    summary.update(
        {
            "strategy_planning_authority_consumer_called": True,
            "strategy_planning_authority_consumer_status": result.get("status") or "",
            "strategy_planning_authority_consumer_reason": result.get("reason") or "",
            "strategy_planning_authority_active": planning_eligible,
            "active_runtime_consumer_eligibility": "YES" if planning_eligible else "NO",
            "strategy_planning_authority_evidence": {
                "schema_version": "phase23_r_strategy_consumer_observability.v1",
                "planning_consumer_eligibility": result.get("planning_consumer_eligibility") or "",
                "strategy_artifact_eligibility": result.get("strategy_artifact_eligibility") or "",
                "plan_count": result.get("plan_count") or 0,
                "pending_item_count": result.get("pending_item_count") or 0,
                "selected_symbols": result.get("selected_symbols") or [],
                "reason_codes": result.get("reason_codes") or [],
                "order_plan_artifact_path": result.get("order_plan_artifact_path") or "",
                "pending_path": result.get("pending_path") or "",
                "approval_artifact_path": result.get("approval_artifact_path") or "",
                "broker_write_allowed": bool(result.get("broker_write_allowed")),
                "broker_write_performed": bool(result.get("broker_write_performed")),
                "runtime_switch_performed": bool(result.get("runtime_switch_performed")),
                "legacy_formal_planning_authority_active": bool(result.get("legacy_formal_planning_authority_active")),
            },
        }
    )
    _write_json_file(summary_path, summary)
    update_run_strategy_shadow_indexes(run_dir=strategy_run_dir)


def _buy_lifecycle_continuity_stages(sell_continuity: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _stage(
            "buy_lifecycle_sell_continuity",
            str(sell_continuity.get("status") or "REVIEW_REQUIRED"),
            "BUY lifecycle gate result evaluated for SELL continuity without Broker write.",
            sell_continuity,
        ),
        _stage(
            "buy_lifecycle_sell_authorization_continuity",
            "PASS" if sell_continuity.get("allow_sell_planning") and sell_continuity.get("allow_sell_submit_authorization") else "BLOCKED",
            "BUY lifecycle block scoped to BUY planning/submit; SELL planning and submit authorization remain reachable without Broker write.",
            {
                "call_graph_reached": True,
                "current_refresh_reached": bool(sell_continuity.get("allow_current_refresh")),
                "valuation_refresh_reached": bool(sell_continuity.get("allow_valuation_refresh")),
                "position_management_reached": bool(sell_continuity.get("allow_position_management")),
                "safety_evaluation_reached": bool(sell_continuity.get("allow_safety_evaluation")),
                "sell_planning_stage_reached": bool(sell_continuity.get("allow_sell_planning")),
                "sell_submit_authorization_stage_reached": bool(sell_continuity.get("allow_sell_submit_authorization")),
                "broker_write_performed": False,
                "buy_planning_permission": sell_continuity.get("buy_planning_permission") or "",
                "buy_submit_permission": sell_continuity.get("buy_submit_permission") or "",
                "sell_planning_permission": sell_continuity.get("sell_planning_permission") or "",
                "sell_submit_authorization_permission": sell_continuity.get("sell_submit_authorization_permission") or "",
            },
        ),
    ]


def _data_readiness_safety_summary_fields(payload: dict[str, Any]) -> dict[str, Any]:
    safety = dict((payload.get("components") or {}).get("safety") or {})
    authority = str(safety.get("historical_safety_temporal_authority") or "")
    if not authority:
        return {}
    return {
        "data_readiness_safety_authority": authority,
        "data_readiness_safety_reason": safety.get("reason") or "",
        "data_readiness_safety_status": safety.get("status") or "",
        "data_readiness_ignored_latest_safety_decision": safety.get("ignored_latest_safety_decision") or "",
        "data_readiness_safety_authority_type": safety.get("safety_authority_type") or "",
        "data_readiness_safety_authority_business_date": safety.get("safety_authority_business_date") or "",
        "data_readiness_safety_authority_source": safety.get("safety_authority_source") or "",
        "data_readiness_safety_authority_policy_version": safety.get("safety_authority_policy_version") or "",
        "data_readiness_previous_empty_pending_present": bool(safety.get("previous_empty_pending_present")),
        "data_readiness_previous_empty_pending_ignored_as_safety_authority": bool(
            safety.get("previous_empty_pending_ignored_as_safety_authority")
        ),
        "data_readiness_historical_neutral_authority_generated_or_resolved": bool(
            safety.get("historical_neutral_authority_generated_or_resolved")
        ),
        "data_readiness_safety_broker_write": bool(safety.get("broker_write")),
        "data_readiness_safety_external_delivery": bool(safety.get("external_delivery")),
        "data_readiness_safety_runtime_test_run_id": safety.get("runtime_test_run_id") or "",
        "data_readiness_safety_runtime_test_profile_id": safety.get("runtime_test_profile_id") or "",
        "data_readiness_safety_runtime_test_evidence_root": safety.get("runtime_test_evidence_root") or "",
    }


def _historical_safety_manifest_override(*, args: argparse.Namespace, data_readiness_manifest: dict[str, Any]) -> dict[str, Any]:
    authority = str(data_readiness_manifest.get("data_readiness_safety_authority") or "")
    if args.mode != "historical" or not authority:
        return {}
    reason = str(data_readiness_manifest.get("data_readiness_safety_reason") or "historical_neutral_no_event_safety_ready")
    return {
        "safety_authority": authority,
        "safety_decision_id": "",
        "safety_policy_version": "historical_replay_neutral_safety_v1",
        "safety_source": "data_readiness_historical_temporal_authority",
        "safety_artifact_path": "",
        "safety_decision": "NEUTRAL",
        "safety_reason": reason,
        "safety_status": "PASS",
        "safety_review_required": False,
        "safety_block_buy": False,
        "safety_block_sell": False,
        "safety_block_submit": False,
        "safety_halt_runtime": False,
        "safety_emergency_stop": False,
        "safety_generated_at": "",
        "safety_expires_at": "",
        "safety_action_permissions": {
            "buy_inference": "ALLOWED_FOR_REPLAY",
            "buy_planning": "ALLOWED_FOR_REPLAY",
            "buy_submit": "ALLOWED_FOR_REPLAY",
            "sell_hold_inference": "ALLOWED_FOR_REPLAY",
            "sell_planning": "ALLOWED_FOR_REPLAY",
            "sell_submit": "ALLOWED_FOR_REPLAY",
            "auto_sell": "BLOCKED",
            "human_review": "NOT_REQUIRED",
            "broker_write": "BLOCKED",
        },
        "safety_human_review_artifact_refs": [],
        "ignored_latest_safety_decision": data_readiness_manifest.get("data_readiness_ignored_latest_safety_decision") or "",
    }


def _strategy_planning_safety_authority_payload(
    *,
    args: argparse.Namespace,
    business_date: str,
    safety_decision: RuntimeSafetyDecision | None,
    data_readiness_manifest: dict[str, Any],
) -> dict[str, Any]:
    payload = dict(safety_manifest_fields(safety_decision))
    if args.mode == "historical" and data_readiness_manifest.get("data_readiness_safety_authority"):
        payload.update(
            {
                "safety_authority": data_readiness_manifest.get("data_readiness_safety_authority") or "",
                "safety_authority_type": data_readiness_manifest.get("data_readiness_safety_authority_type") or "",
                "safety_business_date": data_readiness_manifest.get("data_readiness_safety_authority_business_date") or business_date,
                "temporal_authority_business_date": data_readiness_manifest.get("data_readiness_safety_authority_business_date") or business_date,
                "safety_policy_version": data_readiness_manifest.get("data_readiness_safety_authority_policy_version") or payload.get("safety_policy_version") or "",
                "safety_source": data_readiness_manifest.get("data_readiness_safety_authority_source") or payload.get("safety_source") or "",
                "safety_decision": payload.get("safety_decision") or "NEUTRAL",
                "safety_reason": data_readiness_manifest.get("data_readiness_safety_reason") or payload.get("safety_reason") or "",
            }
        )
    if args.runtime_test_run_id:
        payload["runtime_test_run_id"] = args.runtime_test_run_id
    if args.runtime_test_profile_id:
        payload["runtime_test_profile_id"] = args.runtime_test_profile_id
    if args.runtime_test_evidence_root:
        payload["runtime_test_evidence_root"] = args.runtime_test_evidence_root
    return payload


def _strategy_planning_submit_policy_authority_payload(*, capital_deployment_policy: Any | None) -> dict[str, Any]:
    if capital_deployment_policy is None:
        return {}
    return {
        "submit_policy_authority": "capital_deployment_policy",
        "submit_policy_schema_version": "phase23_bb_submit_policy_authority.v1",
        "submit_policy_version": capital_deployment_policy.policy_version,
        "submit_policy_source": capital_deployment_policy.policy_source,
        "submit_policy_hash": capital_deployment_policy_hash(capital_deployment_policy),
    }


def _effective_runtime_safety_decision(
    *,
    args: argparse.Namespace,
    business_date: str,
    runtime_safety_decision: RuntimeSafetyDecision | None,
    data_readiness_manifest: dict[str, Any],
) -> RuntimeSafetyDecision | None:
    authority = str(data_readiness_manifest.get("data_readiness_safety_authority") or "")
    if args.mode != "historical" or not authority:
        return runtime_safety_decision
    reason = str(data_readiness_manifest.get("data_readiness_safety_reason") or "historical_neutral_no_event_safety_ready")
    return RuntimeSafetyDecision(
        safety_decision_id="",
        safety_policy_version="historical_replay_neutral_safety_v1",
        safety_source="data_readiness_historical_temporal_authority",
        business_date=business_date,
        runtime_mode="historical",
        decision="NEUTRAL",
        reason=reason,
        review_required=False,
        block_buy=False,
        block_sell=False,
        block_submit=False,
        halt_runtime=False,
        emergency_stop=False,
        generated_at="",
        expires_at="",
        safety_status="PASS",
        action_permissions={
            "buy_inference": "ALLOWED_FOR_REPLAY",
            "buy_planning": "ALLOWED_FOR_REPLAY",
            "buy_submit": "ALLOWED_FOR_REPLAY",
            "sell_hold_inference": "ALLOWED_FOR_REPLAY",
            "sell_planning": "ALLOWED_FOR_REPLAY",
            "sell_submit": "ALLOWED_FOR_REPLAY",
            "auto_sell": "BLOCKED",
            "human_review": "NOT_REQUIRED",
            "broker_write": "BLOCKED",
        },
        human_review_artifact_refs=[],
        artifact_path="",
    )


def _morning_capability_context(*, args: argparse.Namespace, environment_manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "runtime_mode": environment_manifest.get("runtime_mode") or args.mode,
        "broker_environment": environment_manifest.get("broker_environment") or args.broker_environment or args.mode,
        "historical_replay": bool(environment_manifest.get("historical_replay")),
        "simulation": bool(environment_manifest.get("simulation")),
        "broker_write": bool(environment_manifest.get("broker_write")),
        "external_delivery": bool(environment_manifest.get("external_delivery") or args.notification_mode != "payload-only"),
        "tachibana_demo_write": bool(environment_manifest.get("tachibana_demo_write")),
        "tachibana_production_write": bool(environment_manifest.get("tachibana_production_write")),
        "submit_enabled": _as_bool(args.submit_enabled),
        "runtime_test_run_id": args.runtime_test_run_id or "",
        "runtime_test_profile_id": args.runtime_test_profile_id or "",
        "runtime_test_evidence_root": args.runtime_test_evidence_root or "",
    }


def _serialization_error_details(
    *,
    args: argparse.Namespace,
    business_date: str,
    exc: JsonSerializationContractError,
) -> dict[str, Any]:
    payload = exc.to_payload()
    payload.update(
        {
            "error_type": "TypeError",
            "message": str(exc),
            "job": args.job,
            "stage": "morning",
            "business_date": business_date,
            "artifact_type": _artifact_type_for_field_path(exc.field_path),
        }
    )
    return payload


def _artifact_type_for_field_path(field_path: str) -> str:
    if "metrics_validation" in field_path:
        return "opportunity_rankings"
    if "candidate" in field_path:
        return "candidate_decisions"
    return "runtime_evidence"


def _write_morning_failure_evidence(
    *,
    args: argparse.Namespace,
    business_date: str,
    run_id: str,
    error_payload: dict[str, Any],
    data_readiness_manifest: dict[str, Any],
    environment_manifest: dict[str, Any],
    stack_trace: str,
) -> None:
    if not args.runtime_test_evidence_root or args.job != "morning":
        return
    evidence_dir = Path(args.runtime_test_evidence_root) / "daily" / business_date / "morning"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    _write_json_file(
        evidence_dir / "exception_summary.json",
        {
            **error_payload,
            "run_id": run_id,
            "runtime_test_run_id": args.runtime_test_run_id or "",
            "internal_stack_trace": stack_trace,
        },
    )
    _write_json_file(evidence_dir / "data_readiness_reference.json", data_readiness_manifest)
    _write_json_file(evidence_dir / "environment_composition.json", environment_manifest)
    feature_contract = data_readiness_manifest.get("feature_date_contract") if isinstance(data_readiness_manifest.get("feature_date_contract"), dict) else {}
    _write_json_file(
        evidence_dir / "selected_feature_contract.json",
        {
            "selected_feature_date": data_readiness_manifest.get("selected_feature_date") or "",
            "feature_date_contract_path": feature_contract.get("contract_artifact_path") or "",
        },
    )


def _write_morning_manifest_evidence(
    *,
    evidence_root: Path,
    business_date: str,
    manifest_path: Path,
    manifest: dict[str, Any],
) -> None:
    evidence_dir = evidence_root / "daily" / business_date / "morning"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    _write_json_file(
        evidence_dir / "morning_manifest.json",
        {
            "source_manifest_path": str(manifest_path),
            "manifest": manifest,
        },
    )
    stages = list(manifest.get("stages") or [])
    capability = _stage_details(stages, "environment_capability_decision")
    _write_json_file(
        evidence_dir / "environment_capability_decision.json",
        capability
        or {
            "status": "NOT_EVALUATED",
            "reason": "environment_capability_decision_stage_not_reached",
        },
    )
    strategy_planning = _stage_details(stages, "phase23_i_strategy_planning_authority_pipeline")
    planning = strategy_planning or _stage_details(stages, "morning_ai_planning_pending_pipeline")
    sell_continuity = _stage_details(stages, "buy_lifecycle_sell_continuity")
    sell_authorization = _stage_details(stages, "buy_lifecycle_sell_authorization_continuity")
    _write_json_file(
        evidence_dir / "buy_lifecycle_sell_continuity.json",
        sell_continuity
        or {
            "status": "NOT_EVALUATED",
            "reason": "buy_lifecycle_sell_continuity_stage_not_reached",
        },
    )
    _write_json_file(
        evidence_dir / "sell_authorization_continuity.json",
        sell_authorization
        or {
            "status": "NOT_EVALUATED",
            "reason": "buy_lifecycle_sell_authorization_continuity_stage_not_reached",
            "call_graph_reached": False,
        },
    )
    _write_json_file(
        evidence_dir / "planning_evidence.json",
        planning
        or {
            "status": "NOT_EXECUTED",
            "reason": _final_reason(
                errors=list(manifest.get("errors") or []),
                warnings=list(manifest.get("warnings") or []),
            )
            or "planning_stage_not_reached",
        },
    )
    _write_json_file(
        evidence_dir / "strategy_planning_authority_evidence.json",
        strategy_planning
        or {
            "status": "NOT_EXECUTED",
            "reason": "phase23_i_strategy_planning_authority_stage_not_reached",
            "planning_consumer_eligibility": "NOT_EVALUATED",
            "legacy_formal_planning_authority_active": True,
            "legacy_comparison_artifact_present": False,
            "broker_write_performed": False,
            "runtime_switch_performed": False,
        },
    )
    pending_path = str((planning or {}).get("pending_path") or "")
    planning_lineage_items = list(((planning or {}).get("lineage") or {}).get("items") or [])
    _write_json_file(
        evidence_dir / "pending_generation_evidence.json",
        {
            "status": (planning or {}).get("status") or "NOT_EXECUTED",
            "reason": (planning or {}).get("reason") or ("pending_generation_stage_not_reached" if not planning else ""),
            "pending_path": pending_path,
            "pending_path_written": bool(pending_path and Path(pending_path).is_file()),
            "pending_plan_id": (planning or {}).get("pending_plan_id") or "",
            "rank_authority_lineage": [
                _pending_rank_authority_lineage_item(item)
                for item in planning_lineage_items
                if isinstance(item, dict) and item.get("pending_item_generated") is True
            ],
        },
    )
    prohibited = dict(manifest.get("prohibited_actions") or {})
    _write_json_file(
        evidence_dir / "external_effect_audit.json",
        {
            "status": "PASS"
            if not any(
                bool(prohibited.get(key))
                for key in (
                    "demo_submit_executed",
                    "production_order_executed",
                    "notification_sent",
                    "phase9_runtime_called",
                    "phase9_writer_called",
                    "mode_rooted_current_used",
                )
            )
            else "REVIEW_REQUIRED",
            "broker_order_api_calls": 0,
            "notification_delivery_calls": 0,
            "jquants_fetch_calls": 0,
            "production_access": bool(manifest.get("mode") == "production"),
            "demo_submit": bool(prohibited.get("demo_submit_executed")),
            "prohibited_actions": prohibited,
        },
    )


def _pending_rank_authority_lineage_item(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "planning_id": str(item.get("planning_id") or ""),
        "security_code": str(item.get("security_code") or ""),
        "planning_intent": str(item.get("planning_intent") or ""),
        "order_side_intent": str(item.get("order_side_intent") or ""),
        "opportunity_buy_rank": _int_or_none(item.get("opportunity_buy_rank")),
        "portfolio_input_opportunity_rank": _int_or_none(item.get("portfolio_input_opportunity_rank")),
        "position_sizing_opportunity_buy_rank": _int_or_none(item.get("position_sizing_opportunity_buy_rank")),
        "rank_authority_status": str(item.get("rank_authority_status") or ""),
        "rank_authority": str(item.get("rank_authority") or ""),
        "rank_authority_field": str(item.get("rank_authority_field") or ""),
        "rank_authority_reason": str(item.get("rank_authority_reason") or ""),
        "opportunity_row_id": str(item.get("opportunity_row_id") or ""),
        "opportunity_row_authority_hash": str(item.get("opportunity_row_authority_hash") or ""),
        "opportunity_artifact_path": str(item.get("opportunity_artifact_path") or ""),
        "opportunity_artifact_hash": str(item.get("opportunity_artifact_hash") or ""),
    }


def _write_sell_planning_manifest_evidence(
    *,
    evidence_root: Path,
    business_date: str,
    manifest_path: Path,
    manifest: dict[str, Any],
) -> None:
    evidence_dir = evidence_root / "daily" / business_date / "sell_planning"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    stages = list(manifest.get("stages") or [])
    capability = _stage_details(stages, "environment_capability_decision")
    pm = _stage_details(stages, "position_management_ai_runtime_producer")
    sell = _stage_details(stages, "sell_planning_pending_pipeline")
    readiness = _stage_details(stages, "runtime_data_readiness_gate")
    reason = _final_reason(
        errors=list(manifest.get("errors") or []),
        warnings=list(manifest.get("warnings") or []),
    )
    _write_json_file(
        evidence_dir / "sell_planning_manifest.json",
        {
            "source_manifest_path": str(manifest_path),
            "manifest": manifest,
        },
    )
    _write_json_file(
        evidence_dir / "environment_capability_decision.json",
        capability
        or {
            "status": "NOT_EVALUATED",
            "reason": "environment_capability_decision_stage_not_reached",
        },
    )
    _write_json_file(
        evidence_dir / "data_readiness_authority.json",
        {
            "status": readiness.get("status") or manifest.get("data_readiness_status") or "NOT_EVALUATED",
            "reason": readiness.get("reason") or manifest.get("data_readiness_reason") or reason,
            "data_readiness_artifact_path": manifest.get("data_readiness_artifact_path") or "",
            "safety_authority": manifest.get("data_readiness_safety_authority") or "",
            "ignored_latest_safety_decision": manifest.get("data_readiness_ignored_latest_safety_decision") or "",
            "review_reasons": manifest.get("data_readiness_review_reasons") or [],
            "halt_reasons": manifest.get("data_readiness_halt_reasons") or [],
        },
    )
    _write_json_file(
        evidence_dir / "position_management_evidence.json",
        pm
        or {
            "status": "NOT_EXECUTED",
            "reason": reason or "position_management_stage_not_reached",
        },
    )
    pending_path = str((sell or {}).get("pending_path") or "")
    _write_json_file(
        evidence_dir / "pending_continuity_evidence.json",
        {
            "status": (sell or pm or {}).get("status") or "NOT_EXECUTED",
            "reason": (sell or pm or {}).get("reason") or reason or "sell_planning_stage_not_reached",
            "pending_path": pending_path,
            "pending_path_written_by_sell_planning": bool(sell and pending_path and Path(pending_path).is_file()),
            "no_position_preserved_existing_pending": bool(pm.get("status") == "NO_POSITION" and not sell),
            "pending_plan_id": (sell or {}).get("pending_plan_id") or "",
        },
    )
    prohibited = dict(manifest.get("prohibited_actions") or {})
    _write_json_file(
        evidence_dir / "external_effect_audit.json",
        {
            "status": "PASS"
            if not any(
                bool(prohibited.get(key))
                for key in (
                    "demo_submit_executed",
                    "production_order_executed",
                    "notification_sent",
                    "phase9_runtime_called",
                    "phase9_writer_called",
                    "mode_rooted_current_used",
                )
            )
            else "REVIEW_REQUIRED",
            "broker_order_api_calls": 0,
            "notification_delivery_calls": 0,
            "production_access": bool(manifest.get("mode") == "production"),
            "prohibited_actions": prohibited,
        },
    )


def _write_execution_manifest_evidence(
    *,
    evidence_root: Path,
    business_date: str,
    manifest_path: Path,
    manifest: dict[str, Any],
) -> None:
    evidence_dir = evidence_root / "daily" / business_date / "execution"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    stages = list(manifest.get("stages") or [])
    execution = _stage_details(stages, "runtime_v2_execution_readonly_pipeline")
    environment = _stage_details(stages, "environment_composition")
    reason = _final_reason(
        errors=list(manifest.get("errors") or []),
        warnings=list(manifest.get("warnings") or []),
    )
    _write_json_file(
        evidence_dir / "execution_manifest.json",
        {
            "source_manifest_path": str(manifest_path),
            "manifest": manifest,
        },
    )
    _write_json_file(
        evidence_dir / "environment_capability_decision.json",
        environment
        or {
            "status": "NOT_EVALUATED",
            "reason": "environment_composition_stage_not_reached",
        },
    )
    prohibited = dict(manifest.get("prohibited_actions") or {})
    _write_json_file(
        evidence_dir / "external_effect_audit.json",
        {
            "status": "PASS"
            if not any(
                bool(prohibited.get(key))
                for key in (
                    "demo_submit_executed",
                    "production_order_executed",
                    "notification_sent",
                    "phase9_runtime_called",
                    "phase9_writer_called",
                    "mode_rooted_current_used",
                )
            )
            else "REVIEW_REQUIRED",
            "broker_order_api_calls": 0,
            "notification_delivery_calls": 0,
            "jquants_fetch_calls": 0,
            "production_access": bool(manifest.get("mode") == "production"),
            "broker_write": bool(environment.get("broker_write")),
            "external_delivery": bool(environment.get("external_delivery")),
            "historical_replay": bool(environment.get("historical_replay")),
            "simulation": bool(environment.get("simulation")),
            "prohibited_actions": prohibited,
        },
    )
    _write_json_file(
        evidence_dir / "submitted_order_authority.json",
        {
            "status": execution.get("execution_acceptance_status") or execution.get("status") or "NOT_EXECUTED",
            "reason": execution.get("execution_acceptance_reason") or reason or "execution_stage_not_reached",
            "orders_count": execution.get("orders_count", 0),
            "submitted_order_count": execution.get("submitted_order_count", execution.get("orders_count", 0)),
            "orderlist_required": bool(execution.get("orderlist_required", True)),
            "orderlist_status": execution.get("orderlist_status") or "",
            "execution_action": execution.get("execution_action") or "",
            "submit_action": execution.get("submit_action") or "",
            "submit_authority_status": execution.get("submit_authority_status") or "",
            "submit_authority_path": execution.get("submit_authority_path") or "",
            "submit_authority_reason": execution.get("submit_authority_reason") or "",
            "orderlist_readonly_connected": bool(execution.get("orderlist_readonly_connected")),
            "execution_references": execution.get("execution_references") or [],
            "runtime_test_run_id": manifest.get("runtime_test_run_id") or "",
            "runtime_test_profile_id": manifest.get("runtime_test_profile_id") or "",
            "business_date": manifest.get("business_date") or business_date,
        },
    )
    _write_json_file(
        evidence_dir / "historical_fill_authority.json",
        {
            "status": execution.get("execution_acceptance_status") or execution.get("status") or "NOT_EXECUTED",
            "reason": execution.get("execution_acceptance_reason") or reason or "execution_stage_not_reached",
            "snapshot_status": execution.get("snapshot_status") or "",
            "snapshot_path": execution.get("snapshot_path") or "",
            "report_path": execution.get("report_path") or "",
            "orderlist_required": bool(execution.get("orderlist_required", True)),
            "orderlist_status": execution.get("orderlist_status") or "",
            "execution_action": execution.get("execution_action") or "",
            "execution_equivalent_count": execution.get("execution_equivalent_count", 0),
            "fill_count": execution.get("fill_count", execution.get("execution_equivalent_count", 0)),
            "order_detail_required": bool(execution.get("order_detail_required")),
            "order_detail_status": execution.get("order_detail_status") or "",
            "warnings": execution.get("execution_acceptance_warnings") or [],
        },
    )
    _write_json_file(
        evidence_dir / "execution_normalization_evidence.json",
        {
            "status": execution.get("execution_acceptance_status") or execution.get("status") or "NOT_EXECUTED",
            "reason": execution.get("execution_acceptance_reason") or reason or "execution_stage_not_reached",
            "orders_count": execution.get("orders_count", 0),
            "submitted_order_count": execution.get("submitted_order_count", execution.get("orders_count", 0)),
            "executions_count": execution.get("executions_count", 0),
            "positions_count": execution.get("positions_count", 0),
            "cash_present": bool(execution.get("cash_present")),
            "orderlist_required": bool(execution.get("orderlist_required", True)),
            "orderlist_status": execution.get("orderlist_status") or "",
            "execution_action": execution.get("execution_action") or "",
        },
    )
    _write_json_file(
        evidence_dir / "ledger_append_evidence.json",
        {
            "status": "PASS" if execution.get("ledger_connected") else "NOT_EXECUTED",
            "ledger_orders_appended": execution.get("ledger_orders_appended", 0),
            "ledger_executions_appended": execution.get("ledger_executions_appended", 0),
            "ledger_positions_appended": execution.get("ledger_positions_appended", 0),
            "ledger_cash_appended": execution.get("ledger_cash_appended", 0),
            "ledger_events_appended": execution.get("ledger_events_appended", 0),
        },
    )
    _write_json_file(
        evidence_dir / "current_apply_evidence.json",
        {
            "status": execution.get("current_apply_status") or "NOT_EXECUTED",
            "reason": execution.get("current_apply_reason") or "",
            "runtime_owned_projection_status": execution.get("runtime_owned_projection_status") or "NOT_EXECUTED",
            "runtime_owned_projection_reason": execution.get("runtime_owned_projection_reason") or "",
            "asset_current_written": bool(execution.get("asset_current_written")),
            "current_hash": execution.get("current_hash") or "",
            "current_version": execution.get("current_version") or "",
            "runtime_state_path": execution.get("runtime_state_path") or "",
            "runtime_state_version": execution.get("runtime_state_version") or "",
        },
    )
    _write_json_file(
        evidence_dir / "pending_terminalization_evidence.json",
        {
            "status": execution.get("pending_terminalization_status")
            or ("PASS" if execution.get("current_apply_status") in {"APPLIED", "NOOP_ALREADY_APPLIED"} else "NOT_CONFIRMED"),
            "pending_consumed": bool(
                execution.get("pending_consumed")
                if "pending_consumed" in execution
                else execution.get("current_apply_status") in {"APPLIED", "NOOP_ALREADY_APPLIED"}
            ),
            "pending_mutated": bool(execution.get("pending_mutated", False)),
            "pending_read_valid": bool(execution.get("pending_read_valid", False)),
            "pending_classification": execution.get("pending_classification") or "",
            "pending_active": execution.get("pending_active"),
            "pending_plan_present": bool(execution.get("pending_plan_present", False)),
            "pending_item_count": execution.get("pending_item_count", 0),
            "no_action_reason": execution.get("no_action_reason") or "",
            "execution_references": execution.get("execution_references") or [],
            "item_lifecycle_authority": execution.get("item_lifecycle_authority") or {"status": "NOT_APPLICABLE"},
        },
    )


def _write_current_valuation_manifest_evidence(
    *,
    evidence_root: Path,
    business_date: str,
    manifest_path: Path,
    manifest: dict[str, Any],
) -> None:
    evidence_dir = evidence_root / "daily" / business_date / "current_valuation_refresh"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    stages = list(manifest.get("stages") or [])
    valuation = _stage_details(stages, "current_valuation_refresh")
    producer_reached = bool(valuation)
    blocking_stage = "" if producer_reached else _current_valuation_blocking_stage(manifest)
    blocking_reason = "" if producer_reached else _final_reason(
        errors=list(manifest.get("errors") or []),
        warnings=list(manifest.get("warnings") or []),
    )
    environment = _stage_details(stages, "environment_composition")
    safety = _stage_details(stages, "historical_safety_authority") or {
        key: manifest.get(key)
        for key in (
            "safety_status",
            "safety_decision",
            "safety_policy_version",
            "safety_source",
            "safety_reason",
            "safety_action_permissions",
        )
    }
    prohibited = dict(manifest.get("prohibited_actions") or {})
    artifact_path = str(valuation.get("current_valuation_refresh_artifact_path") or "")
    artifact = _read_json_file(Path(artifact_path)) if artifact_path and Path(artifact_path).is_file() else {}
    candidate = dict(artifact.get("candidate_current") or {})
    _write_json_file(
        evidence_dir / "current_valuation_manifest.json",
        {
            "source_manifest_path": str(manifest_path),
            "execution_reached": producer_reached,
            "blocked_before_producer": not producer_reached,
            "blocking_stage": blocking_stage,
            "blocking_reason": blocking_reason,
            "manifest": manifest,
            "artifact": artifact,
        },
    )
    _write_json_file(
        evidence_dir / "environment_capability_decision.json",
        environment
        or {
            "status": "NOT_EVALUATED",
            "reason": "environment_composition_stage_not_reached",
        },
    )
    _write_json_file(
        evidence_dir / "safety_authority_decision.json",
        {
            "status": safety.get("safety_status") or safety.get("status") or "NOT_EVALUATED",
            "safety_decision": safety.get("safety_decision") or "",
            "safety_policy_version": safety.get("safety_policy_version") or "",
            "safety_source": safety.get("safety_source") or safety.get("source_safety_decision") or "",
            "safety_reason": safety.get("safety_reason") or "",
            "safety_action_permissions": safety.get("safety_action_permissions") or {},
            "ignored_latest_safety_decision": safety.get("ignored_latest_safety_decision") or "",
        },
    )
    _write_json_file(
        evidence_dir / "market_evidence_authority.json",
        {
            "status": "PASS" if artifact.get("market_evidence_path") and artifact.get("market_date") else "NOT_EVALUATED" if not producer_reached else "REVIEW_REQUIRED",
            "execution_reached": producer_reached,
            "blocked_before_producer": not producer_reached,
            "blocking_stage": blocking_stage,
            "blocking_reason": blocking_reason,
            "market_evidence_path": artifact.get("market_evidence_path") or "",
            "market_date": artifact.get("market_date") or "",
            "valuation_source": artifact.get("valuation_source") or "",
            "missing_symbols": artifact.get("missing_symbols") or [],
        },
    )
    _write_json_file(
        evidence_dir / "valuation_input.json",
        {
            "source_current_path": artifact.get("source_current_path") or "",
            "execution_reached": producer_reached,
            "blocked_before_producer": not producer_reached,
            "blocking_stage": blocking_stage,
            "blocking_reason": blocking_reason,
            "position_count": artifact.get("position_count", 0),
            "market_evidence_path": artifact.get("market_evidence_path") or "",
            "market_date": artifact.get("market_date") or "",
        },
    )
    _write_json_file(
        evidence_dir / "valuation_projection.json",
        {
            "status": artifact.get("status") or valuation.get("status") or "NOT_EXECUTED",
            "execution_reached": producer_reached,
            "blocked_before_producer": not producer_reached,
            "blocking_stage": blocking_stage,
            "blocking_reason": blocking_reason,
            "reason": artifact.get("reason") or valuation.get("reason") or "",
            "position_count": artifact.get("position_count", 0),
            "valued_position_count": artifact.get("valued_position_count", 0),
            "previous_total_market_value": artifact.get("previous_total_market_value", 0),
            "new_total_market_value": artifact.get("new_total_market_value", 0),
            "cash": candidate.get("cash"),
            "buying_power": candidate.get("buying_power"),
            "realized_pnl": candidate.get("realized_pnl"),
            "valuation_refresh_precondition_status": artifact.get("valuation_refresh_precondition_status") or "",
            "existing_valuation_as_of": artifact.get("existing_valuation_as_of") or "",
            "previous_trading_date": artifact.get("previous_trading_date") or "",
            "target_valuation_date": artifact.get("target_valuation_date") or "",
            "valuation_refresh_action": artifact.get("valuation_refresh_action") or "",
            "projection_status": artifact.get("projection_status") or "",
            "projection_source_market_date": artifact.get("projection_source_market_date") or "",
            "temporal_authority": artifact.get("temporal_authority") or "",
            "temporal_reason": artifact.get("temporal_reason") or "",
        },
    )
    _write_json_file(
        evidence_dir / "valuation_apply_evidence.json",
        {
            "status": "NOT_EXECUTED" if not producer_reached else "PASS" if artifact.get("apply_executed") else ("DRY_RUN" if not artifact.get("apply_requested") else "NOT_APPLIED"),
            "execution_reached": producer_reached,
            "blocked_before_producer": not producer_reached,
            "blocking_stage": blocking_stage,
            "blocking_reason": blocking_reason,
            "apply_requested": bool(artifact.get("apply_requested")),
            "apply_executed": bool(artifact.get("apply_executed")),
            "backup_path": artifact.get("backup_path") or "",
            "history_path": artifact.get("history_path") or "",
            "apply_status": artifact.get("apply_status") or "",
            "post_apply_valuation_as_of": artifact.get("post_apply_valuation_as_of") or "",
            "post_apply_source_market_date": artifact.get("post_apply_source_market_date") or "",
            "postcondition_status": artifact.get("postcondition_status") or "",
            "postcondition_reason": artifact.get("postcondition_reason") or "",
        },
    )
    _write_json_file(
        evidence_dir / "external_effect_audit.json",
        {
            "status": "PASS"
            if not any(
                bool(prohibited.get(key))
                for key in (
                    "demo_submit_executed",
                    "production_order_executed",
                    "notification_sent",
                    "phase9_runtime_called",
                    "phase9_writer_called",
                    "mode_rooted_current_used",
                )
            )
            else "REVIEW_REQUIRED",
            "broker_order_api_calls": 0,
            "notification_delivery_calls": 0,
            "jquants_fetch_calls": 0,
            "production_access": bool(manifest.get("mode") == "production"),
            "broker_write": bool(environment.get("broker_write")),
            "external_delivery": bool(environment.get("external_delivery")),
            "historical_replay": bool(environment.get("historical_replay")),
            "simulation": bool(environment.get("simulation")),
            "prohibited_actions": prohibited,
        },
    )


def _current_valuation_blocking_stage(manifest: dict[str, Any]) -> str:
    if manifest.get("data_readiness_status") == "REVIEW_REQUIRED":
        return "runtime_data_readiness_gate"
    if manifest.get("safety_status") not in {"", None, "PASS"}:
        return "safety_operation_guard"
    return "pre_producer_gate"


def _stage_details(stages: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for stage in stages:
        if stage.get("name") == name:
            details = stage.get("details")
            if isinstance(details, dict):
                return {
                    "status": stage.get("status") or "",
                    "message": stage.get("message") or "",
                    **details,
                }
            return {
                "status": stage.get("status") or "",
                "message": stage.get("message") or "",
            }
    return {}


def _write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _accepted_generation_binding_for_runtime_job(
    *,
    args: argparse.Namespace,
    business_date: str,
    consumer: str,
) -> dict[str, Any]:
    resolution = resolve_accepted_generation(
        runtime_root=Path(args.runtime_root),
        business_date=business_date,
        fixed_authority_path=args.historical_evaluation_authority or None,
    )
    return resolution.binding_evidence(
        runtime_mode=args.mode,
        business_date=business_date,
        consumer=consumer,
    )


def _submit_environment_context(
    *,
    args: argparse.Namespace,
    composition: Any,
    business_date: str,
    evaluation_time: str,
) -> SubmitEnvironmentGuardContext:
    adapter = composition.submit_adapter
    adapter_type = "DemoSubmitAdapter"
    if args.mode == "historical" and adapter is not None:
        adapter_type = type(adapter).__name__
    elif args.mode == "production":
        adapter_type = "ProductionSubmitAdapter"
    return SubmitEnvironmentGuardContext(
        runtime_environment=composition.runtime_mode,
        pending_environment=args.mode,
        run_type=composition.run_type,
        broker_environment=composition.broker_environment,
        adapter_type=adapter_type,
        broker_write=composition.broker_write,
        external_delivery=composition.external_delivery,
        business_date=business_date,
        evaluation_time=evaluation_time,
        production_acceptance=False,
    )


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


def _runtime_test_context(*, args: argparse.Namespace, business_date: str) -> dict[str, Any] | None:
    if not args.runtime_test_run_id:
        return None
    return {
        "run_id": args.runtime_test_run_id,
        "profile_id": args.runtime_test_profile_id or "",
        "evidence_root": args.runtime_test_evidence_root or "",
        "source_commit": args.runtime_test_source_commit or "",
        "business_date": business_date,
        "job": args.job,
        "environment_id": f"{args.mode}:{args.broker_environment or args.mode}",
    }


def _historical_asof_view_path(*, args: argparse.Namespace, business_date: str) -> str:
    if args.mode != "historical" or not args.runtime_test_evidence_root:
        return ""
    return str(Path(args.runtime_test_evidence_root) / "daily" / business_date / "market_refresh" / "historical_asof_view.json")


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
            "broker_readonly_snapshot_artifact",
            "runtime_state_artifact",
            "sell_hold_review_output",
            "sell_hold_review_pending",
            "human_approval_artifact",
            "review_pending_linkage_artifact",
            "pending_promotion_candidate",
            "authoritative_pending_apply_candidate",
        }
    }


def _final_reason(*, errors: list[str], warnings: list[str]) -> str:
    if errors:
        return errors[0]
    if warnings:
        return warnings[0]
    return ""


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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
