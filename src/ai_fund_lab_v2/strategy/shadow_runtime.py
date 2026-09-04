from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.runtime_v2.accepted_generation_resolver import resolve_accepted_generation
from ai_fund_lab_v2.runtime_v2.buy_ai.opportunity_eligibility import evaluate_opportunity_buy_eligibility
from ai_fund_lab_v2.runtime_v2.safety.portfolio_limits import load_portfolio_safety_limits
from ai_fund_lab_v2.strategy import corporate_event
from ai_fund_lab_v2.strategy import buy_quality
from ai_fund_lab_v2.strategy import input_materialization
from ai_fund_lab_v2.strategy import market_context
from ai_fund_lab_v2.strategy import portfolio_construction
from ai_fund_lab_v2.strategy import portfolio_policy
from ai_fund_lab_v2.strategy import position_management
from ai_fund_lab_v2.strategy import position_sizing
from ai_fund_lab_v2.strategy import runtime_planning
from ai_fund_lab_v2.strategy import source_manifest
from ai_fund_lab_v2.strategy import strategy_intelligence
from ai_fund_lab_v2.strategy.observability import produce_strategy_decision_trace
from ai_fund_lab_v2.strategy.target_weight_precision import target_weight_sum_tolerance


STRATEGY_SHADOW_MANIFEST_SCHEMA_VERSION = "strategy_shadow_input_manifest.v1"
STRATEGY_SHADOW_SUMMARY_SCHEMA_VERSION = "runtime_test_strategy_shadow_summary.v1"
STRATEGY_SHADOW_RUN_MANIFEST_SCHEMA_VERSION = "runtime_test_strategy_shadow_run_manifest.v1"
STRATEGY_SHADOW_RUN_SUMMARY_SCHEMA_VERSION = "runtime_test_strategy_shadow_run_summary.v1"

OPPORTUNITY_SCORE_SEMANTIC_METADATA_FIELDS = (
    "canonical_score_field",
    "score_semantic_role",
    "calibration_applied",
    "economic_units_available",
)

ARTIFACT_FILENAMES = {
    "market_context": "market_context.json",
    "corporate_event": "corporate_event.json",
    "portfolio_policy": "portfolio_policy.json",
    "buy_quality": "buy_quality_decisions.json",
    "portfolio_construction_draft": "portfolio_construction_draft.json",
    "position_sizing_preflight": "position_sizing_preflight.json",
    "portfolio_construction": "portfolio_construction.json",
    "position_sizing": "position_sizing.json",
    "position_management": "position_management.json",
    "runtime_planning": "runtime_planning.json",
    "strategy_intelligence": "strategy_intelligence.json",
}

INPUT_SOURCE_FILENAMES = {
    "price_volatility": "price_volatility.json",
    "technical_features": "technical_features.json",
}


def strategy_shadow_job_descriptor(*, run_dir: Path, business_date: str) -> dict[str, Any]:
    strategy_dir = run_dir / "daily" / business_date / "strategy"
    return {
        "job": "strategy_shadow_generation",
        "business_date": business_date,
        "execution_order": "after_daily_runtime_jobs",
        "input_authority": "Runtime read-only snapshots and COMMITTED Accepted Generation resolver",
        "expected_output_path": str(strategy_dir),
        "mutation_policy": "read_only_strategy_shadow_no_runtime_state_mutation",
        "failure_policy": "Runtime Test evidence REVIEW_REQUIRED is recorded separately from active Runtime; BLOCK is isolated to strategy evidence unless mutation is detected",
        "metadata_classification": "read_only_runtime_test_evidence_job",
        "active_runtime_strategy_consumer": "runtime_v2.planning.strategy_authority.activate_strategy_planning_authority",
        "active_runtime_consumer_eligibility": "NO",
        "runtime_switch_performed": False,
    }


def generate_strategy_shadow_for_day(
    *,
    run_dir: Path,
    runtime_root: Path,
    run_id: str,
    profile_id: str,
    business_date: str,
    feature_date: str = "",
    feature_date_authority: Mapping[str, Any] | None = None,
    historical_evaluation_authority_path: str = "",
    artifact_subdir: str = "strategy",
    decision_timing: str = "EOD",
    authority_role: str = "POST_RUNTIME_OBSERVABILITY_SHADOW",
    materialization_role: str = "LATEST_RUNTIME_STATE_MATERIALIZATION",
) -> dict[str, Any]:
    strategy_dir = run_dir / "daily" / business_date / artifact_subdir
    strategy_dir.mkdir(parents=True, exist_ok=True)
    before = _runtime_authority_hashes(runtime_root)
    feature_authority = _normalize_feature_date_authority(
        business_date=business_date,
        planned_feature_date=feature_date,
        feature_date_authority=feature_date_authority,
    )
    operations_root = runtime_root / "operations"
    strategy_sources = _resolve_strategy_source_authority(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date=business_date,
        operations_root=operations_root,
    )
    manifest = _build_input_manifest(
        run_id=run_id,
        profile_id=profile_id,
        runtime_root=runtime_root,
        business_date=business_date,
        feature_date=str(feature_authority.get("selected_feature_date") or business_date),
        feature_date_authority=feature_authority,
        historical_evaluation_authority_path=historical_evaluation_authority_path,
        strategy_source_authority=strategy_sources,
    )
    manifest = {
        **manifest,
        "artifact_subdir": artifact_subdir,
        "authority_role": authority_role,
        "materialization_role": materialization_role,
        "decision_timing": decision_timing,
        "formal_planning_snapshot": artifact_subdir == "strategy"
        and authority_role == "FORMAL_PLANNING_AUTHORITY_INPUT",
    }
    _write_json(strategy_dir / "input_manifest.json", manifest)

    artifact_paths = {name: strategy_dir / filename for name, filename in ARTIFACT_FILENAMES.items()}
    results: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, Any]] = []

    def produce(name: str, func) -> None:
        try:
            result = func()
            results[name] = _producer_result_payload(result)
        except Exception as exc:
            errors.append({"component": name, "error": str(exc)})
            _write_json(
                artifact_paths[name],
                _error_artifact(name=name, business_date=business_date, error=str(exc)),
            )
            results[name] = {
                "status": "BLOCK",
                "reason": str(exc),
                "artifact_path": str(artifact_paths[name]),
                "artifact_hash": _file_hash(artifact_paths[name]),
            }

    as_of = f"{business_date}T00:00:00+00:00"
    candidate = _ai_output_summary(runtime_root / "runtime_state" / "buy_ai" / business_date / "candidate_decisions.json", business_date=business_date)
    opportunity = _ai_output_summary(runtime_root / "runtime_state" / "buy_ai" / business_date / "opportunity_rankings.json", business_date=business_date)
    opportunity_artifact_path = _optional_opportunity_artifact_path(opportunity, business_date=business_date)
    current = _current_summary(runtime_root=runtime_root, business_date=business_date)
    prior_exit_supply = _supply_prior_exit_state(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date=business_date,
        candidate=candidate,
        opportunity=opportunity,
        current=current,
    )
    candidate = prior_exit_supply["candidate"]
    opportunity = prior_exit_supply["opportunity"]
    cash = _cash_summary(runtime_root=runtime_root, business_date=business_date)
    exposure = _exposure_summary(runtime_root=runtime_root, business_date=business_date)
    pending = _pending_summary(runtime_root=runtime_root, business_date=business_date)
    safety = _safety_summary()
    input_source_paths = {name: strategy_dir / filename for name, filename in INPUT_SOURCE_FILENAMES.items()}
    input_symbols = _strategy_input_symbols(candidate, opportunity, current)
    price_source = Path(strategy_sources["paths"]["normalized_ohlcv"])
    price_volatility = input_materialization.produce_price_volatility_artifact(
        business_date=business_date,
        feature_date=str(feature_authority.get("selected_feature_date") or business_date),
        source_path=price_source,
        output_path=input_source_paths["price_volatility"],
        symbols=input_symbols,
        as_of=as_of,
    )
    technical_features = input_materialization.produce_pm_technical_feature_artifact(
        business_date=business_date,
        feature_date=str(feature_authority.get("selected_feature_date") or business_date),
        source_path=price_source,
        output_path=input_source_paths["technical_features"],
        symbols=input_symbols,
        as_of=as_of,
        listed_issues_path=Path(strategy_sources["paths"]["listed_issues"]),
        runtime_run_id=run_id,
    )
    input_source_manifest = {
        "price_volatility": _input_source_ref(price_volatility),
        "technical_features": _input_source_ref(technical_features),
        "strategy_source_authority": strategy_sources,
        "prior_exit_state": prior_exit_supply["evidence"],
    }

    produce(
        "market_context",
        lambda: market_context.produce_market_context_artifact(
            business_date=business_date,
            input_paths=market_context.MarketContextInputPaths(
                daily_quotes_path=Path(strategy_sources["paths"]["normalized_ohlcv"]),
                listed_issues_path=Path(strategy_sources["paths"]["listed_issues"]),
                trading_calendar_path=Path(strategy_sources["paths"]["trading_calendar"]),
            ),
            config=_load_optional(lambda: market_context.load_market_context_config(Path("configs/strategy/market_context.json"))),
            output_path=artifact_paths["market_context"],
            as_of=as_of,
            expected_source_hashes=strategy_sources["expected_hashes"],
        ),
    )
    produce(
        "corporate_event",
        lambda: corporate_event.produce_corporate_event_artifact(
            business_date=business_date,
            input_paths=corporate_event.CorporateEventInputPaths(
                listed_issues_path=Path(strategy_sources["paths"]["listed_issues"]),
                trading_calendar_path=Path(strategy_sources["paths"]["trading_calendar"]),
                earnings_schedule_path=_optional_path(strategy_sources["paths"].get("earnings_schedule")),
                financial_statements_path=_optional_path(strategy_sources["paths"].get("financial_statements")),
                corporate_actions_path=_optional_path(strategy_sources["paths"].get("corporate_actions")),
            ),
            output_path=artifact_paths["corporate_event"],
            as_of=as_of,
            expected_source_hashes=strategy_sources["expected_hashes"],
            require_full_source_coverage=not bool(strategy_sources.get("run_scoped_historical_authority_used")),
        ),
    )
    reentry_source_supply = _supply_reentry_source_evidence(
        business_date=business_date,
        opportunity=opportunity,
        technical_features=_materialized_summary(technical_features),
        corporate_event_path=artifact_paths["corporate_event"],
    )
    opportunity = reentry_source_supply["opportunity"]
    input_source_manifest["reentry_source_evidence"] = reentry_source_supply["evidence"]
    pp_config = _portfolio_policy_config()
    policy_config_summary = _portfolio_policy_config_summary(pp_config, business_date)
    input_source_manifest["portfolio_policy_config"] = _policy_config_source_ref(pp_config, business_date=business_date, as_of=as_of)
    manifest = {**manifest, "strategy_input_sources": input_source_manifest}
    _write_json(strategy_dir / "input_manifest.json", manifest)
    produce(
        "portfolio_policy",
        lambda: portfolio_policy.produce_portfolio_policy_artifact(
            business_date=business_date,
            market_context_artifact_path=artifact_paths["market_context"],
            corporate_event_artifact_path=artifact_paths["corporate_event"],
            candidate_summary=_pp_summary(candidate, business_date),
            opportunity_summary=_pp_summary(opportunity, business_date),
            current_portfolio_summary=current["summary"],
            current_cash_summary=cash["summary"],
            current_exposure_summary=exposure["summary"],
            pending_reservation_summary=pending["summary"],
            safety_limit_summary=safety["summary"],
            policy_config=pp_config,
            output_path=artifact_paths["portfolio_policy"],
            as_of=as_of,
        ),
    )
    campaign_connection = _materialize_pre_action_position_campaigns(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date=business_date,
        current=current,
        as_of=as_of,
    )
    input_source_manifest["pre_action_campaign_lifecycle"] = campaign_connection["evidence"]
    manifest = {**manifest, "strategy_input_sources": input_source_manifest}
    _write_json(strategy_dir / "input_manifest.json", manifest)
    produce(
        "strategy_intelligence",
        lambda: strategy_intelligence.produce_strategy_intelligence_artifact(
            business_date=business_date,
            candidate_summary=candidate,
            opportunity_summary=opportunity,
            current_summary=current,
            technical_feature_summary=_materialized_summary(technical_features),
            price_volatility_summary=_materialized_summary(price_volatility),
            market_context_artifact_path=artifact_paths["market_context"],
            corporate_event_artifact_path=artifact_paths["corporate_event"],
            buy_quality_artifact_path=None,
            portfolio_construction_artifact_path=None,
            position_sizing_artifact_path=None,
            position_management_artifact_path=None,
            runtime_planning_artifact_path=None,
            output_path=artifact_paths["strategy_intelligence"],
            position_campaigns_artifact_path=campaign_connection["artifact_path"],
            as_of=as_of,
            production_consumer_connected=True,
            consumer_stage="PRE_ACTION_PRODUCTION_EVIDENCE",
        ),
    )
    pm_reference = _pm_accepted_generation_reference(manifest)
    produce(
        "position_management",
        lambda: position_management.produce_position_management_artifact(
            business_date=business_date,
            market_context_artifact_path=artifact_paths["market_context"],
            corporate_event_artifact_path=artifact_paths["corporate_event"],
            portfolio_policy_artifact_path=artifact_paths["portfolio_policy"],
            existing_pm_decisions=_existing_pm_decisions(runtime_root=runtime_root, business_date=business_date),
            runtime_current_positions=_runtime_current_position_rows(current),
            position_lifecycle_summary=_pm_summary(current, business_date),
            technical_feature_summary=_pm_summary(_materialized_summary(technical_features), business_date),
            opportunity_summary=_pm_summary(opportunity, business_date),
            accepted_generation_reference=pm_reference,
            output_path=artifact_paths["position_management"],
            as_of=as_of,
            strategy_intelligence_artifact_path=artifact_paths["strategy_intelligence"],
        ),
    )
    add_baseline_evidence = _supply_add_expected_edge_baseline(
        run_dir=run_dir,
        business_date=business_date,
        opportunity=opportunity,
        current=current,
        position_management=results.get("position_management", {}),
    )
    opportunity = add_baseline_evidence["opportunity"]
    _write_json(strategy_dir / "add_baseline_supply_evidence.json", add_baseline_evidence["evidence"])
    produce(
        "buy_quality",
        lambda: buy_quality.produce_buy_quality_artifact(
            business_date=business_date,
            candidate_summary=_bq_summary(candidate, business_date),
            opportunity_summary=_bq_summary(opportunity, business_date),
            market_context_artifact_path=artifact_paths["market_context"],
            portfolio_policy_artifact_path=artifact_paths["portfolio_policy"],
            current_portfolio_summary=_bq_summary(current, business_date),
            pending_summary=_bq_summary(pending, business_date),
            price_volatility_summary=_bq_summary(_materialized_summary(price_volatility), business_date),
            corporate_event_artifact_path=artifact_paths["corporate_event"],
            output_path=artifact_paths["buy_quality"],
            as_of=as_of,
        ),
    )
    produce(
        "portfolio_construction_draft",
        lambda: portfolio_construction.produce_portfolio_construction_artifact(
            business_date=business_date,
            market_context_artifact_path=artifact_paths["market_context"],
            corporate_event_artifact_path=artifact_paths["corporate_event"],
            portfolio_policy_artifact_path=artifact_paths["portfolio_policy"],
            position_management_artifact_path=artifact_paths["position_management"],
            candidate_summary=_pc_summary(candidate, business_date),
            opportunity_summary=_pc_summary(opportunity, business_date),
            current_portfolio_summary=_pc_summary(current, business_date),
            pending_summary=_pc_summary(pending, business_date),
            policy_config_summary=_pc_summary(results.get("portfolio_policy", policy_config_summary), business_date),
            buy_quality_summary=_pc_summary(results.get("buy_quality", {}), business_date),
            strategy_intelligence_artifact_path=artifact_paths["strategy_intelligence"],
            output_path=artifact_paths["portfolio_construction_draft"],
            as_of=as_of,
        ),
    )
    ps_config = _load_optional(lambda: position_sizing.load_position_sizing_config(Path("configs/strategy/position_sizing.json")))
    produce(
        "position_sizing_preflight",
        lambda: position_sizing.produce_position_sizing_artifact(
            business_date=business_date,
            portfolio_construction_summary=_ps_summary(results.get("portfolio_construction_draft", {}), business_date),
            capital_deployment_summary=_ps_summary({"status": "REVIEW_REQUIRED", "summary": {"reason": "capital_deployment_is_downstream_of_position_sizing_in_shadow_chain"}}, business_date),
            dynamic_cash_exposure_summary=_ps_summary(results.get("portfolio_policy", {}), business_date),
            dynamic_position_count_summary=_ps_summary(results.get("portfolio_policy", {}), business_date),
            position_management_summary=_ps_summary(results.get("position_management", {}), business_date),
            opportunity_summary=_ps_summary(opportunity, business_date),
            current_position_summary=_ps_summary(current, business_date),
            price_volatility_summary=_ps_summary(_materialized_summary(price_volatility), business_date),
            safety_limit_summary=_ps_summary(safety, business_date),
            config=ps_config,
            output_path=artifact_paths["position_sizing_preflight"],
            as_of=as_of,
        ),
    )
    produce(
        "portfolio_construction",
        lambda: _produce_lot_aware_final_portfolio_construction(
            business_date=business_date,
            draft_path=artifact_paths["portfolio_construction_draft"],
            preflight_path=artifact_paths["position_sizing_preflight"],
            output_path=artifact_paths["portfolio_construction"],
        ),
    )
    produce(
        "position_sizing",
        lambda: position_sizing.produce_position_sizing_artifact(
            business_date=business_date,
            portfolio_construction_summary=_ps_summary(results.get("portfolio_construction", {}), business_date),
            capital_deployment_summary=_ps_summary({"status": "REVIEW_REQUIRED", "summary": {"reason": "capital_deployment_is_downstream_of_position_sizing_in_shadow_chain"}}, business_date),
            dynamic_cash_exposure_summary=_ps_summary(results.get("portfolio_policy", {}), business_date),
            dynamic_position_count_summary=_ps_summary(results.get("portfolio_policy", {}), business_date),
            position_management_summary=_ps_summary(results.get("position_management", {}), business_date),
            opportunity_summary=_ps_summary(opportunity, business_date),
            current_position_summary=_ps_summary(current, business_date),
            price_volatility_summary=_ps_summary(_materialized_summary(price_volatility), business_date),
            safety_limit_summary=_ps_summary(safety, business_date),
            config=ps_config,
            output_path=artifact_paths["position_sizing"],
            as_of=as_of,
            production_consumer_connected=True,
        ),
    )
    produce(
        "runtime_planning",
        lambda: runtime_planning.produce_runtime_planning_artifact(
            business_date=business_date,
            portfolio_construction_artifact_path=artifact_paths["portfolio_construction"],
            capital_deployment_artifact_path=None,
            portfolio_policy_artifact_path=artifact_paths["portfolio_policy"],
            position_management_artifact_path=artifact_paths["position_management"],
            position_sizing_artifact_path=artifact_paths["position_sizing"],
            current_portfolio_summary=_rp_summary(current, business_date),
            current_cash_summary=_rp_summary(cash, business_date),
            current_position_summary=_rp_summary(current, business_date),
            pending_summary=_rp_summary(pending, business_date),
            planning_config_summary=_rp_summary({"status": "PASS", "source_ref": "configs/runtime_v2/capital_deployment.json", "source_hash": _file_hash(Path("configs/runtime_v2/capital_deployment.json")), "summary": {}}, business_date),
            output_path=artifact_paths["runtime_planning"],
            opportunity_artifact_path=opportunity_artifact_path,
            as_of=as_of,
        ),
    )
    trace_result = produce_strategy_decision_trace(
        business_date=business_date,
        profile=profile_id,
        run_id=run_id,
        artifact_paths={k: artifact_paths[k] for k in ARTIFACT_FILENAMES},
        output_path=strategy_dir / "strategy_decision_trace.json",
        legacy_context={"max_positions": 5, "target_investment_ratio": 0.85, "cash_buffer": 0.15},
        outcome_context={
            "runtime_result_available": False,
            "execution_result_available": False,
            "strategy_input_allowed": False,
            "learning_input_allowed": False,
        },
    )
    results["strategy_decision_trace"] = _producer_result_payload(trace_result)
    comparison = _legacy_shadow_comparison(results)
    _write_json(strategy_dir / "legacy_shadow_comparison.json", comparison)
    after = _runtime_authority_hashes(runtime_root)
    mutation = before != after
    statuses = [str(item.get("status") or "") for item in results.values()]
    feature_authority_status = str(feature_authority.get("authority_status") or "REVIEW_REQUIRED")
    strategy_status = "BLOCK" if mutation or "BLOCK" in statuses else "REVIEW_REQUIRED" if "REVIEW_REQUIRED" in statuses or trace_result.status in {"REVIEW_REQUIRED", "INCOMPLETE_ATTRIBUTION"} else "PASS"
    if feature_authority_status == "BLOCK":
        strategy_status = "BLOCK"
    elif feature_authority_status != "PASS" and strategy_status == "PASS":
        strategy_status = "REVIEW_REQUIRED"
    formal_planning_snapshot = bool(manifest.get("formal_planning_snapshot"))
    summary = {
        "schema_version": STRATEGY_SHADOW_SUMMARY_SCHEMA_VERSION,
        "run_id": run_id,
        "profile_id": profile_id,
        "business_date": business_date,
        "artifact_subdir": artifact_subdir,
        "authority_role": authority_role,
        "materialization_role": materialization_role,
        "decision_timing": decision_timing,
        "formal_planning_snapshot": formal_planning_snapshot,
        "post_runtime_shadow": artifact_subdir != "strategy",
        "strategy_shadow_judgment": strategy_status,
        "runtime_judgment": "UNCHANGED_BY_STRATEGY_SHADOW",
        "overall_test_judgment": "REVIEW_REQUIRED" if strategy_status == "REVIEW_REQUIRED" else strategy_status,
        "artifact_count": len(results),
        "artifacts": results,
        "errors": errors,
        "input_manifest_path": str(strategy_dir / "input_manifest.json"),
        "strategy_decision_trace_path": str(strategy_dir / "strategy_decision_trace.json"),
        "legacy_shadow_comparison_path": str(strategy_dir / "legacy_shadow_comparison.json"),
        "feature_date_authority": feature_authority,
        "feature_date_authority_status": feature_authority_status,
        "runtime_mutation_performed": mutation,
        "runtime_authority_hashes_before": before,
        "runtime_authority_hashes_after": after,
        "broker_connection_performed": False,
        "broker_write_performed": False,
        "external_delivery_performed": False,
        "shadow_consumer_eligibility": "REVIEW_REQUIRED" if strategy_status != "PASS" else "YES",
        "active_runtime_consumer_eligibility": "YES" if formal_planning_snapshot else "NO",
        "runtime_switch_performed": False,
        "strategy_intelligence_production_consumer_connected": formal_planning_snapshot,
        "legacy_authority_active": not formal_planning_snapshot,
        "legacy_authority_active_semantics": "retired_for_formal_planning_strategy_intelligence_production_evidence"
        if formal_planning_snapshot
        else "report_only_shadow_observability_not_formal_planning_authority",
        "legacy_formal_planning_authority_active": False,
        "strategy_planning_authority_consumer_called": False,
    }
    _write_json(strategy_dir / "strategy_shadow_summary.json", summary)
    source_payload = source_manifest.build_strategy_source_manifest(
        run_dir=run_dir,
        runtime_root=runtime_root,
        run_id=run_id,
        profile_id=profile_id,
        business_date=business_date,
        strategy_dir=strategy_dir,
        decision_timing=decision_timing,
        input_manifest=manifest,
    )
    source_manifest_path = strategy_dir / "source_manifest.json"
    _write_json(source_manifest_path, source_payload)
    source_manifest_hash = source_manifest.manifest_hash(source_payload)
    manifest = {
        **manifest,
        "source_manifest_path": str(source_manifest_path),
        "source_manifest_hash": source_manifest_hash,
    }
    _write_json(strategy_dir / "input_manifest.json", manifest)
    pit = source_payload.get("pit_validation") if isinstance(source_payload.get("pit_validation"), dict) else {}
    summary = {
        **summary,
        "source_manifest_path": str(source_manifest_path),
        "source_manifest_hash": source_manifest_hash,
        "pit_validation": pit,
        "direct_blockers": source_payload.get("direct_blockers", {}),
        "propagated_blockers": source_payload.get("propagated_blockers", {}),
        "root_blocker_components": source_payload.get("root_blocker_components", []),
        "root_reason_codes": source_payload.get("root_reason_codes", []),
        "latest_fallback_used": bool(pit.get("latest_fallback_used")),
        "current_state_leakage_detected": bool(pit.get("current_state_leakage_detected")),
        "future_row_rejection_count": int(pit.get("future_row_rejection_count") or 0),
        "sector_pit_status": (source_payload.get("sector") or {}).get("pit_status") if isinstance(source_payload.get("sector"), dict) else "",
        "corporate_event_coverage_status": (source_payload.get("corporate_event") or {}).get("coverage_status") if isinstance(source_payload.get("corporate_event"), dict) else "",
    }
    evidence_index = _build_strategy_evidence_index(strategy_dir=strategy_dir, summary=summary, input_manifest=manifest, source_payload=source_payload)
    _write_json(strategy_dir / "strategy_evidence_index.json", evidence_index)
    summary = {**summary, "strategy_evidence_index_path": str(strategy_dir / "strategy_evidence_index.json")}
    _write_json(strategy_dir / "strategy_shadow_summary.json", summary)
    update_run_strategy_shadow_indexes(run_dir=run_dir)
    return summary


def update_run_strategy_shadow_indexes(*, run_dir: Path) -> dict[str, Any]:
    daily_root = run_dir / "daily"
    summaries: list[dict[str, Any]] = []
    for path in sorted(daily_root.glob("*/strategy/strategy_shadow_summary.json")):
        summaries.append(_read_json(path))
    expected = _planned_business_dates(run_dir)
    generated = [str(item.get("business_date") or path.parent.parent.name) for item, path in zip(summaries, sorted(daily_root.glob("*/strategy/strategy_shadow_summary.json")))]
    review = sorted(str(item.get("business_date") or "") for item in summaries if item.get("strategy_shadow_judgment") == "REVIEW_REQUIRED")
    blocked = sorted(str(item.get("business_date") or "") for item in summaries if item.get("strategy_shadow_judgment") == "BLOCK")
    complete = sorted(str(item.get("business_date") or "") for item in summaries if item.get("strategy_shadow_judgment") == "PASS")
    pit_valid = sorted(str(item.get("business_date") or "") for item in summaries if (item.get("pit_validation") or {}).get("status") == "PASS")
    pit_blocked = sorted(str(item.get("business_date") or "") for item in summaries if (item.get("pit_validation") or {}).get("status") == "BLOCK")
    source_unavailable = sorted(str(item.get("business_date") or "") for item in summaries if (item.get("pit_validation") or {}).get("source_unavailable"))
    bootstrap_required = sorted(str(item.get("business_date") or "") for item in summaries if (item.get("pit_validation") or {}).get("bootstrap_required"))
    root_counts: dict[str, int] = {}
    for item in summaries:
        for component in item.get("root_blocker_components", []) or []:
            root_counts[str(component)] = root_counts.get(str(component), 0) + 1
    consumer_called = any(bool(item.get("strategy_planning_authority_consumer_called")) for item in summaries)
    active_consumer = any(str(item.get("active_runtime_consumer_eligibility") or "") == "YES" for item in summaries)
    strategy_authority_active = any(bool(item.get("strategy_planning_authority_active")) for item in summaries)
    manifest = {
        "schema_version": STRATEGY_SHADOW_RUN_MANIFEST_SCHEMA_VERSION,
        "run_id": run_dir.name,
        "business_dates_expected": expected,
        "business_dates_generated": sorted(generated),
        "complete_dates": complete,
        "review_required_dates": review,
        "blocked_dates": blocked,
        "missing_dates": sorted(set(expected) - set(generated)),
        "pit_valid_dates": pit_valid,
        "pit_blocked_dates": pit_blocked,
        "source_unavailable_dates": source_unavailable,
        "bootstrap_required_dates": bootstrap_required,
        "root_blocker_counts": dict(sorted(root_counts.items())),
        "future_row_rejection_count": sum(int((item.get("pit_validation") or {}).get("future_row_rejection_count") or item.get("future_row_rejection_count") or 0) for item in summaries),
        "latest_fallback_used": any(bool(item.get("latest_fallback_used") or (item.get("pit_validation") or {}).get("latest_fallback_used")) for item in summaries),
        "current_state_leakage_detected": any(bool(item.get("current_state_leakage_detected") or (item.get("pit_validation") or {}).get("current_state_leakage_detected")) for item in summaries),
        "sector_pit_status": sorted(set(str(item.get("sector_pit_status") or "") for item in summaries if item.get("sector_pit_status"))),
        "corporate_event_coverage_status": sorted(set(str(item.get("corporate_event_coverage_status") or "") for item in summaries if item.get("corporate_event_coverage_status"))),
        "runtime_mutation_performed": any(bool(item.get("runtime_mutation_performed")) for item in summaries),
        "broker_connection_performed": False,
        "broker_write_performed": False,
        "external_delivery_performed": False,
        "shadow_consumer_eligibility": "REVIEW_REQUIRED" if review or blocked else "YES" if summaries else "NO",
        "active_runtime_consumer_eligibility": "YES" if active_consumer else "NO",
        "runtime_switch_performed": False,
        "legacy_authority_active": False if active_consumer else True,
        "legacy_authority_active_semantics": "retired_for_formal_planning_strategy_intelligence_production_evidence"
        if active_consumer
        else "report_only_shadow_observability_not_formal_planning_authority",
        "legacy_formal_planning_authority_active": not strategy_authority_active,
        "strategy_planning_authority_active": strategy_authority_active,
        "strategy_planning_authority_consumer_called": consumer_called,
    }
    manifest["artifact_count"] = sum(int(item.get("artifact_count") or 0) for item in summaries)
    manifest["hash_validation"] = "PASS" if summaries else "REVIEW_REQUIRED"
    manifest["date_validation"] = "PASS" if not manifest["missing_dates"] else "REVIEW_REQUIRED"
    manifest["lineage_validation"] = "REVIEW_REQUIRED" if review or blocked or not summaries else "PASS"
    summary = {
        "schema_version": STRATEGY_SHADOW_RUN_SUMMARY_SCHEMA_VERSION,
        **manifest,
        "strategy_shadow_judgment": "BLOCK" if blocked or manifest["runtime_mutation_performed"] else "REVIEW_REQUIRED" if review or manifest["missing_dates"] else "PASS",
        "daily_summaries": summaries,
    }
    _write_json(run_dir / "strategy_shadow_manifest.json", manifest)
    _write_json(run_dir / "strategy_shadow_summary.json", summary)
    return summary


def load_run_strategy_shadow_summary(*, run_dir: Path) -> dict[str, Any]:
    path = run_dir / "strategy_shadow_summary.json"
    if not path.is_file():
        return update_run_strategy_shadow_indexes(run_dir=run_dir) if run_dir.exists() else {}
    return _read_json(path)


def validate_run_strategy_shadow(*, run_dir: Path, business_date: str | None = None) -> dict[str, Any]:
    summary = update_run_strategy_shadow_indexes(run_dir=run_dir)
    dates = [business_date] if business_date else summary.get("business_dates_expected") or summary.get("business_dates_generated") or []
    required = ["input_manifest.json", "source_manifest.json", *ARTIFACT_FILENAMES.values(), "strategy_decision_trace.json", "legacy_shadow_comparison.json", "strategy_shadow_summary.json", "strategy_evidence_index.json"]
    per_day = []
    for day in dates:
        strategy_dir = run_dir / "daily" / str(day) / "strategy"
        missing = [name for name in required if not (strategy_dir / name).is_file()]
        checks: dict[str, Any] = {}
        if not missing:
            pp = _read_json(strategy_dir / "portfolio_policy.json")
            sizing = _read_json(strategy_dir / "position_sizing.json")
            input_manifest = _read_json(strategy_dir / "input_manifest.json")
            source_payload = _read_json(strategy_dir / "source_manifest.json")
            pit = source_payload.get("pit_validation") if isinstance(source_payload.get("pit_validation"), dict) else {}
            checks = {
                "source_manifest_completeness": "PASS" if _source_manifest_complete(source_payload) else "REVIEW_REQUIRED",
                "source_manifest_hash_reference": "PASS" if input_manifest.get("source_manifest_hash") == source_manifest.manifest_hash(source_payload) else "BLOCK",
                "source_manifest_business_date": "PASS" if source_payload.get("business_date") == str(day) else "BLOCK",
                "pit_validation_status": "PASS" if pit.get("status") == "PASS" else "REVIEW_REQUIRED" if pit.get("status") == "REVIEW_REQUIRED" else "BLOCK" if pit.get("status") == "BLOCK" else "REVIEW_REQUIRED",
                "latest_fallback_absence": "PASS" if pit.get("latest_fallback_used") is False else "BLOCK",
                "current_state_leakage_absence": "PASS" if pit.get("current_state_leakage_detected") is False else "BLOCK",
                "portfolio_policy_target_position_count_authority": "PASS" if "target_position_count" in pp else "BLOCK",
                "portfolio_policy_target_gross_exposure_authority": "PASS" if "target_gross_exposure_ratio" in pp else "BLOCK",
                "portfolio_policy_cash_reserve_authority": "PASS" if "cash_reserve_ratio" in pp else "BLOCK",
                "fixed_cap_non_use": "PASS" if pp.get("dynamic_position_count_artifact_policy") == "REMOVE" and pp.get("dynamic_cash_exposure_artifact_policy") == "REMOVE" else "BLOCK",
                "legacy_authority_isolation": "PASS" if pp.get("legacy_authority_active") is False else "REVIEW_REQUIRED",
                "target_weight_sum": "PASS"
                if _float(sizing.get("total_target_weight"))
                <= _float(sizing.get("target_gross_exposure_ratio"))
                + target_weight_sum_tolerance(
                    sum(
                        1
                        for position in sizing.get("positions") or []
                        if isinstance(position, dict)
                        and str(position.get("sizing_status") or "") in {"SIZED", "CAPPED"}
                    )
                )
                else "BLOCK",
                "feature_date_authority_present": "PASS" if isinstance(input_manifest.get("feature_date_authority"), dict) else "REVIEW_REQUIRED",
            }
        day_status = "PASS" if not missing and all(value == "PASS" for value in checks.values()) else "REVIEW_REQUIRED"
        if any(value == "BLOCK" for value in checks.values()):
            day_status = "BLOCK"
        per_day.append({"business_date": day, "strategy_dir": str(strategy_dir), "missing": missing, "checks": checks, "status": day_status})
    statuses = {row["status"] for row in per_day}
    return {
        "schema_version": "runtime_test_strategy_shadow_validation.v1",
        "status": "BLOCK" if "BLOCK" in statuses else "PASS" if per_day and statuses == {"PASS"} else "REVIEW_REQUIRED",
        "per_day": per_day,
        "run_summary": summary,
        "structural_validity": "PASS" if per_day and all(not row["missing"] for row in per_day) else "REVIEW_REQUIRED",
        "policy_acceptance": "NOT_REQUESTED",
    }


def _build_input_manifest(
    *,
    run_id: str,
    profile_id: str,
    runtime_root: Path,
    business_date: str,
    feature_date: str,
    feature_date_authority: Mapping[str, Any],
    historical_evaluation_authority_path: str = "",
    strategy_source_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolution = resolve_accepted_generation(
        runtime_root,
        business_date=business_date,
        fixed_authority_path=historical_evaluation_authority_path or None,
    )
    manifest = _read_json(Path(resolution.bundle_manifest_path)) if resolution.bundle_manifest_path and Path(resolution.bundle_manifest_path).is_file() else {}
    candidate_member = manifest.get("candidate_member") if isinstance(manifest.get("candidate_member"), dict) else {}
    opportunity_member = manifest.get("opportunity_member") if isinstance(manifest.get("opportunity_member"), dict) else {}
    candidate_artifact = runtime_root / "runtime_state" / "buy_ai" / business_date / "candidate_decisions.json"
    opportunity_artifact = runtime_root / "runtime_state" / "buy_ai" / business_date / "opportunity_rankings.json"
    return {
        "schema_version": STRATEGY_SHADOW_MANIFEST_SCHEMA_VERSION,
        "run_id": run_id,
        "business_date": business_date,
        "feature_date": feature_date,
        "planned_feature_date": str(feature_date_authority.get("planned_feature_date") or ""),
        "materialized_feature_date": str(feature_date_authority.get("materialized_feature_date") or ""),
        "selected_feature_date": str(feature_date_authority.get("selected_feature_date") or feature_date),
        "feature_date_authority_source": str(feature_date_authority.get("feature_date_authority_source") or ""),
        "planned_matches_materialized": bool(feature_date_authority.get("planned_matches_materialized")),
        "feature_date_contract_path": str(feature_date_authority.get("feature_date_contract_path") or ""),
        "feature_date_authority": dict(feature_date_authority),
        "profile": profile_id,
        "runtime_root": str(runtime_root),
        "historical_evaluation_authority_path": historical_evaluation_authority_path,
        "historical_evaluation_authority_mode": "BUSINESS_DATE_BOUND_RUN_START_FIXED" if historical_evaluation_authority_path else "",
        "accepted_generation_binding": resolution.binding_evidence(
            runtime_mode=profile_id,
            business_date=business_date,
            consumer="strategy_shadow",
        ),
        "strategy_source_authority": dict(strategy_source_authority or {}),
        "trading_calendar": str((strategy_source_authority or {}).get("paths", {}).get("trading_calendar") or runtime_root / "operations" / "jquants" / "raw" / "jquants" / "trading_calendar" / "data.parquet"),
        "jquants_sources": {"operations_root": str(runtime_root / "operations")},
        "listed_info_source": str((strategy_source_authority or {}).get("paths", {}).get("listed_issues") or runtime_root / "operations" / "jquants" / "raw" / "jquants" / "listed_issues" / "data.parquet"),
        "market_quote_source": str((strategy_source_authority or {}).get("paths", {}).get("normalized_ohlcv") or runtime_root / "operations" / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"),
        "accepted_generation": resolution.to_dict(),
        "accepted_generation_id": resolution.generation_id,
        "candidate_model_reference": str(candidate_member.get("model_file") or (resolution.candidate_member.artifact_path if resolution.candidate_member else "")),
        "candidate_model_hash": str(candidate_member.get("model_hash") or (resolution.candidate_member.model_hash if resolution.candidate_member else "")),
        "opportunity_model_reference": str(opportunity_member.get("model_file") or (resolution.opportunity_member.artifact_path if resolution.opportunity_member else "")),
        "opportunity_model_hash": str(opportunity_member.get("model_hash") or (resolution.opportunity_member.model_hash if resolution.opportunity_member else "")),
        "scaler_reference": {"candidate": str(candidate_member.get("scaler_file") or ""), "opportunity": str(opportunity_member.get("scaler_file") or "")},
        "scaler_hash": {"candidate": str(candidate_member.get("scaler_hash") or ""), "opportunity": str(opportunity_member.get("scaler_hash") or "")},
        "calibration_reference": {"candidate": str(candidate_member.get("calibration_ref") or ""), "opportunity": str(opportunity_member.get("calibration_ref") or "")},
        "calibration_hash": {"candidate": str(candidate_member.get("calibration_hash") or ""), "opportunity": str(opportunity_member.get("calibration_hash") or "")},
        "feature_schema_reference": {"candidate": str(candidate_member.get("feature_schema_ref") or ""), "opportunity": str(opportunity_member.get("feature_schema_ref") or "")},
        "feature_schema_hash": {"candidate": str(candidate_member.get("feature_schema_hash") or ""), "opportunity": str(opportunity_member.get("feature_schema_hash") or "")},
        "candidate_artifact": str(candidate_artifact),
        "candidate_artifact_hash": _file_hash(candidate_artifact),
        "opportunity_artifact": str(opportunity_artifact),
        "opportunity_artifact_hash": _file_hash(opportunity_artifact),
        "current_portfolio_snapshot": str(runtime_root / "persistent_ledger" / "state.json"),
        "pending_snapshot": str(runtime_root / "pending_order_plan" / "pending_order_plan.json"),
        "runtime_state_snapshot": str(runtime_root / "runtime_state" / "current_state.json"),
        "strategy_configs": _config_hashes(Path("configs/strategy")),
        "safety_config": _config_hashes(Path("configs/safety")),
        "source_hashes": _runtime_authority_hashes(runtime_root),
        "config_hashes": {**_config_hashes(Path("configs/strategy")), **_config_hashes(Path("configs/safety"))},
        "future_rows_consumed": False,
        "latest_fallback_used": False,
        "previous_day_strategy_copy_used": False,
        "runtime_mutation_allowed": False,
        "broker_connection_allowed": False,
    }


def _producer_result_payload(result: Any) -> dict[str, Any]:
    return {
        "status": str(getattr(result, "status", "")),
        "reason": str(getattr(result, "reason", "")),
        "artifact_path": str(getattr(result, "artifact_path", "")),
        "artifact_hash": str(getattr(result, "artifact_hash", "")),
    }


def _error_artifact(*, name: str, business_date: str, error: str) -> dict[str, Any]:
    return {
        "schema_version": f"{name}_shadow_error.v1",
        "business_date": business_date,
        "producer_result_status": "BLOCK",
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "artifact_lifecycle_status": "DRAFT",
        "reason_codes": ["strategy_shadow_generation_error"],
        "error": error,
        "runtime_switch_performed": False,
        "production_consumer_connected": False,
    }


def _portfolio_policy_config() -> portfolio_policy.PortfolioPolicyConfig | None:
    path = Path("configs/strategy/portfolio_policy.json")
    return _load_optional(lambda: portfolio_policy.load_portfolio_policy_config(path))


def _portfolio_policy_config_summary(config: portfolio_policy.PortfolioPolicyConfig | None, business_date: str) -> dict[str, Any]:
    path = Path(config.config_source) if config else Path("configs/strategy/portfolio_policy.json")
    if config is None:
        return {
            "status": "REVIEW_REQUIRED",
            "business_date": business_date,
            "feature_date": business_date,
            "source_ref": str(path),
            "source_hash": "",
            "summary": {
                "reason": "missing_portfolio_policy_config_authority",
                "decision_resolution": "UNRESOLVED",
            },
        }
    return {
        "status": "PASS",
        "business_date": business_date,
        "feature_date": business_date,
        "source_ref": config.config_source,
        "source_hash": _file_hash(path),
        "summary": config.to_dict(),
    }


def _policy_config_source_ref(
    config: portfolio_policy.PortfolioPolicyConfig | None,
    *,
    business_date: str,
    as_of: str,
) -> dict[str, Any]:
    path = Path(config.config_source) if config else Path("configs/strategy/portfolio_policy.json")
    return {
        "logical_source_identity": "portfolio_policy_config",
        "physical_path": str(path),
        "content_hash": _file_hash(path),
        "schema_version": "portfolio_policy_config.v1" if config else "",
        "business_date": business_date,
        "feature_date": business_date,
        "generated_at": as_of,
        "upstream_sources": [],
        "pit_status": "PASS" if config else "REVIEW_REQUIRED",
        "coverage_status": "AVAILABLE" if config else "SOURCE_NOT_AVAILABLE",
        "status": "PASS" if config else "REVIEW_REQUIRED",
        "reason_codes": [] if config else ["missing_portfolio_policy_config_authority"],
        "authority_owner": "Strategy Portfolio Policy",
        "environment_scope": ["production", "demo", "historical"],
    }


def _input_source_ref(result: input_materialization.StrategyInputMaterializationResult) -> dict[str, Any]:
    payload = result.payload
    return {
        "logical_source_identity": "price_volatility" if payload.get("schema_version") == input_materialization.PRICE_VOLATILITY_SCHEMA_VERSION else "technical_features",
        "physical_path": result.artifact_path,
        "content_hash": result.artifact_hash,
        "schema_version": str(payload.get("schema_version") or ""),
        "business_date": str(payload.get("business_date") or ""),
        "feature_date": str(payload.get("feature_date") or ""),
        "generated_at": str(payload.get("as_of") or ""),
        "upstream_sources": payload.get("upstream_hashes") or [],
        "pit_status": str((payload.get("pit_validation") or {}).get("status") if isinstance(payload.get("pit_validation"), Mapping) else ""),
        "coverage_status": str(payload.get("coverage_status") or ""),
        "status": result.status,
        "reason_codes": payload.get("reason_codes") or [],
    }


def _materialized_summary(result: input_materialization.StrategyInputMaterializationResult) -> dict[str, Any]:
    payload = result.payload
    return {
        "status": result.status,
        "business_date": str(payload.get("business_date") or ""),
        "feature_date": str(payload.get("feature_date") or ""),
        "source_ref": result.artifact_path,
        "source_hash": result.artifact_hash,
        "summary": {
            "schema_version": payload.get("schema_version"),
            "coverage_status": payload.get("coverage_status"),
            "row_count": payload.get("row_count"),
            "symbol_count": payload.get("symbol_count"),
            "decision_resolution": payload.get("decision_resolution"),
            "pit_validation": payload.get("pit_validation"),
            "reason_codes": payload.get("reason_codes") or [],
        },
        "rows": tuple(row for row in payload.get("rows") or [] if isinstance(row, Mapping)),
    }


def _strategy_input_symbols(*items: Mapping[str, Any]) -> tuple[str, ...]:
    symbols: set[str] = set()
    for item in items:
        rows = item.get("rows") if isinstance(item, Mapping) else []
        if not isinstance(rows, (list, tuple)):
            continue
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            code = str(row.get("security_code") or row.get("symbol") or row.get("code") or row.get("Code") or "")
            if code:
                symbols.add(code)
    return tuple(sorted(symbols))


def _pm_accepted_generation_reference(manifest: Mapping[str, Any]) -> position_management.PMAcceptedGenerationReference:
    accepted = manifest.get("accepted_generation") if isinstance(manifest.get("accepted_generation"), dict) else {}
    candidate = manifest.get("candidate_model_reference") or ""
    scaler = (manifest.get("scaler_reference") or {}).get("candidate") if isinstance(manifest.get("scaler_reference"), dict) else ""
    return position_management.PMAcceptedGenerationReference(
        generation_id=str(manifest.get("accepted_generation_id") or ""),
        generation_status="RESOLVED_COMMITTED" if accepted.get("resolution_status") == "RESOLVED_COMMITTED" else str(accepted.get("resolution_status") or "REVIEW_REQUIRED"),
        model_reference=str(candidate),
        scaler_reference=str(scaler or ""),
        model_generation_id=str(manifest.get("accepted_generation_id") or ""),
        scaler_generation_id=str(manifest.get("accepted_generation_id") or ""),
        model_hash=str(manifest.get("candidate_model_hash") or ""),
        scaler_hash=str((manifest.get("scaler_hash") or {}).get("candidate") if isinstance(manifest.get("scaler_hash"), dict) else ""),
        feature_schema_hash=str((manifest.get("feature_schema_hash") or {}).get("candidate") if isinstance(manifest.get("feature_schema_hash"), dict) else ""),
        accepted_generation_hash=str(accepted.get("aggregate_hash") or ""),
    )


def _ai_output_summary(path: Path, *, business_date: str) -> dict[str, Any]:
    payload = _read_json(path) if path.is_file() else {}
    rows = payload if isinstance(payload, list) else payload.get("rows") or payload.get("decisions") or payload.get("rankings") or payload.get("items") or []
    if not isinstance(rows, list):
        rows = []
    source_hash = _file_hash(path)
    payload_business_date = str(payload.get("business_date") or business_date) if isinstance(payload, Mapping) else business_date
    payload_feature_date = str(payload.get("feature_date") or payload_business_date) if isinstance(payload, Mapping) else business_date
    kind = "candidate" if path.name == "candidate_decisions.json" else "opportunity" if path.name == "opportunity_rankings.json" else "ai_output"
    adapted_rows = _candidate_downstream_rows(
        rows,
        payload=payload if isinstance(payload, Mapping) else {},
        path=path,
        source_hash=source_hash,
        business_date=business_date,
        kind=kind,
    )
    rejection_distribution: dict[str, int] = {}
    for row in adapted_rows:
        reason = str(row.get("rejection_reason") or "ACCEPTED")
        rejection_distribution[reason] = rejection_distribution.get(reason, 0) + 1
    buy_eligible_opportunity_count = (
        sum(
            1
            for row in rows
            if isinstance(row, Mapping)
            and evaluate_opportunity_buy_eligibility(
                symbol=str(row.get("security_code") or row.get("code") or row.get("symbol") or row.get("LocalCode") or ""),
                business_date=business_date,
                feature_date=str(row.get("feature_date") or payload_feature_date),
                opportunity_artifact_path=path,
                opportunity_payload=payload if isinstance(payload, Mapping) else {},
                opportunity_row=row,
            ).eligible
        )
        if kind == "opportunity"
        else None
    )
    return {
        "status": "PASS" if path.is_file() else "MISSING",
        "business_date": payload_business_date,
        "feature_date": payload_feature_date,
        "source_ref": str(path),
        "source_hash": source_hash,
        "summary": {
            "row_count": len(adapted_rows),
            "raw_row_count": len(rows),
            "schema_version": payload.get("schema_version", payload.get("artifact_schema_version", "")) if isinstance(payload, dict) else "",
            "candidate_adapter_contract_version": "runtime_buy_ai_candidate_downstream_adapter.v1" if kind == "candidate" else "",
            "opportunity_adapter_contract_version": "runtime_buy_ai_opportunity_downstream_adapter.v1" if kind == "opportunity" else "",
            "source_available": path.is_file(),
            "consumer_eligible_rows": sum(1 for row in adapted_rows if row.get("eligibility_status") == "ELIGIBLE"),
            **(
                {"candidate_capacity_count": sum(1 for row in adapted_rows if row.get("eligibility_status") == "ELIGIBLE")}
                if kind == "candidate"
                else {
                    "opportunity_capacity_count": sum(1 for row in adapted_rows if row.get("eligibility_status") == "ELIGIBLE"),
                    "buy_eligible_opportunity_count": buy_eligible_opportunity_count,
                    "buy_eligibility_policy_version": "runtime_v2_opportunity_buy_eligibility_v1",
                }
                if kind == "opportunity"
                else {}
            ),
            "rejection_reason_distribution": rejection_distribution,
            "silent_empty_fallback_used": False,
            **(_opportunity_score_semantic_metadata(payload) if kind == "opportunity" else {}),
        },
        "rows": tuple(adapted_rows),
    }


def _optional_opportunity_artifact_path(opportunity_summary: Mapping[str, Any], *, business_date: str) -> Path | None:
    if str(opportunity_summary.get("status") or "") != "PASS":
        return None
    if str(opportunity_summary.get("business_date") or "") != business_date:
        return None
    path = Path(str(opportunity_summary.get("source_ref") or ""))
    if not path.is_file():
        return None
    return path


def _candidate_downstream_rows(
    rows: list[Any],
    *,
    payload: Mapping[str, Any],
    path: Path,
    source_hash: str,
    business_date: str,
    kind: str,
) -> list[dict[str, Any]]:
    generation = payload.get("generation_bound_inference") if isinstance(payload.get("generation_bound_inference"), Mapping) else {}
    accepted_generation_id = str(generation.get("accepted_generation_id") or "")
    accepted_generation_hash = str(generation.get("manifest_hash") or "")
    feature_contract_hash = str(generation.get("feature_order_hash") or "")
    payload_business_date = str(payload.get("business_date") or business_date)
    payload_feature_date = str(payload.get("feature_date") or payload_business_date)
    adapted: list[dict[str, Any]] = []
    for index, item in enumerate(rows, start=1):
        if not isinstance(item, Mapping):
            continue
        row = dict(item)
        code = str(row.get("security_code") or row.get("code") or row.get("symbol") or row.get("LocalCode") or "").strip()
        source_row_date = str(row.get("target_date") or row.get("feature_date") or payload_feature_date)
        row_business_date = str(row.get("business_date") or payload_business_date)
        row_feature_date = str(row.get("feature_date") or source_row_date)
        eligible, rejection_reason = _candidate_downstream_eligibility(row, code=code, business_date=business_date, source_row_date=source_row_date)
        score = row.get("candidate_score", row.get("opportunity_score", row.get("expected_edge_score", row.get("score"))))
        source_row_hash = hashlib.sha256(json.dumps(row, ensure_ascii=True, sort_keys=True, default=str).encode("utf-8")).hexdigest()
        rank_authority = _downstream_rank_authority(
            row,
            kind=kind,
            path=path,
            source_hash=source_hash,
            source_row_hash=source_row_hash,
        )
        rank = rank_authority["rank"]
        if rank_authority["status"] != "PASS":
            eligible = False
            rejection_reason = str(rank_authority["reason"])
        identity = {
            "kind": kind,
            "business_date": business_date,
            "source_row_date": source_row_date,
            "security_code": code,
            "rank": rank,
            "source_hash": source_hash,
        }
        row_id = hashlib.sha256(json.dumps(identity, ensure_ascii=True, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:20]
        adapted.append(
            {
                **row,
                "security_code": code,
                "symbol": str(row.get("symbol") or code),
                "business_date": row_business_date,
                "feature_date": row_feature_date,
                "source_row_date": source_row_date,
                "candidate_id": str(row.get("candidate_id") or (f"candidate-{business_date}-{code}-{row_id}" if kind == "candidate" else "")),
                "opportunity_id": str(row.get("opportunity_id") or (f"opportunity-{business_date}-{code}-{row_id}" if kind == "opportunity" else "")),
                "candidate_order": _int_or_default(row.get("candidate_order", row.get("candidate_rank", rank)), index),
                "rank": rank if kind == "opportunity" else _int_or_default(rank, index),
                "adapter_sort_rank": _int_or_default(rank, index),
                "candidate_rank_authority": "candidate_rank" if kind == "candidate" else "",
                "opportunity_buy_rank": rank if kind == "opportunity" and rank_authority["status"] == "PASS" else None,
                "canonical_opportunity_buy_rank": rank if kind == "opportunity" and rank_authority["status"] == "PASS" else None,
                "rank_authority_status": rank_authority["status"],
                "rank_authority": rank_authority["authority"],
                "rank_authority_field": rank_authority["field"],
                "rank_authority_reason": rank_authority["reason"],
                "rank_authority_source_path": str(path),
                "rank_authority_source_hash": source_hash,
                "rank_authority_row_id": row_id,
                "rank_authority_row_hash": source_row_hash,
                "score": _float(row.get("score", score), default=0.0),
                "candidate_score": _float(row.get("candidate_score", score), default=0.0) if kind == "candidate" else row.get("candidate_score"),
                "expected_edge_score": _float(row.get("expected_edge_score", score), default=0.0) if kind == "opportunity" else row.get("expected_edge_score", score),
                "eligibility_status": "ELIGIBLE" if eligible else "REJECTED",
                "candidate_membership_status": "ELIGIBLE" if eligible else "REJECTED",
                "runtime_consumer_eligibility": "ELIGIBLE" if eligible else "NOT_ELIGIBLE",
                "rejection_reason": rejection_reason,
                "reason_codes": _row_reason_codes(row, rejection_reason=rejection_reason),
                "accepted_generation_id": accepted_generation_id,
                "accepted_generation_hash": accepted_generation_hash,
                "feature_contract_hash": feature_contract_hash,
                "technical_features_join_key": {"code": code, "target_date": source_row_date},
                "source_ref": str(path),
                "source_artifact_path": str(path),
                "source_hash": source_hash,
                "artifact_hash": source_hash,
                "source_artifact_hash": source_hash,
                "source_row_hash": source_row_hash,
                "adapter_contract_version": "runtime_buy_ai_candidate_downstream_adapter.v1" if kind == "candidate" else "runtime_buy_ai_opportunity_downstream_adapter.v1",
                "decision_resolution": "RESOLVED" if eligible else "UNRESOLVED",
                "latest_fallback_used": False,
                "future_row_used": False,
            }
        )
    return adapted


def _downstream_rank_authority(
    row: Mapping[str, Any],
    *,
    kind: str,
    path: Path,
    source_hash: str,
    source_row_hash: str,
) -> dict[str, Any]:
    if kind == "opportunity":
        raw = row.get("opportunity_buy_rank")
        field = "opportunity_buy_rank"
        if raw in (None, ""):
            raw = row.get("buy_rank")
            field = "buy_rank"
        rank = _int_or_none(raw)
        if rank is None:
            return {
                "status": "REVIEW_REQUIRED",
                "rank": None,
                "authority": "OPPORTUNITY_BUY_RANK_AUTHORITY",
                "field": field,
                "reason": "opportunity_rank_authority_missing_or_invalid",
                "source_path": str(path),
                "source_hash": source_hash,
                "row_hash": source_row_hash,
            }
        conflicts: list[str] = []
        for alias in ("buy_rank", "opportunity_buy_rank", "opportunity_rank", "rank"):
            if alias == field or alias not in row or row.get(alias) in (None, ""):
                continue
            alias_rank = _int_or_none(row.get(alias))
            if alias_rank is None or alias_rank != rank:
                conflicts.append(alias)
        if conflicts:
            return {
                "status": "REVIEW_REQUIRED",
                "rank": None,
                "authority": "OPPORTUNITY_BUY_RANK_AUTHORITY",
                "field": field,
                "reason": "opportunity_rank_authority_conflict:" + ",".join(sorted(conflicts)),
                "source_path": str(path),
                "source_hash": source_hash,
                "row_hash": source_row_hash,
            }
        return {
            "status": "PASS",
            "rank": rank,
            "authority": "OPPORTUNITY_BUY_RANK_AUTHORITY",
            "field": field,
            "reason": "",
            "source_path": str(path),
            "source_hash": source_hash,
            "row_hash": source_row_hash,
        }
    raw = row.get("candidate_rank")
    field = "candidate_rank"
    if raw in (None, ""):
        raw = row.get("candidate_order", row.get("rank"))
        field = "candidate_rank_fallback"
    rank = _int_or_none(raw)
    return {
        "status": "PASS" if rank is not None else "REVIEW_REQUIRED",
        "rank": rank,
        "authority": "CANDIDATE_RANK_AUTHORITY",
        "field": field,
        "reason": "" if rank is not None else "candidate_rank_authority_missing_or_invalid",
        "source_path": str(path),
        "source_hash": source_hash,
        "row_hash": source_row_hash,
    }


def _candidate_downstream_eligibility(row: Mapping[str, Any], *, code: str, business_date: str, source_row_date: str) -> tuple[bool, str]:
    if not code:
        return False, "SCHEMA_MISMATCH:security_code_missing"
    if not source_row_date or source_row_date > business_date:
        return False, "PIT_INVALID:future_source_row_date"
    if row.get("universe_eligible") is False or row.get("eligible") is False:
        return False, str(row.get("excluded_reason") or row.get("reason") or "POLICY_REJECTED")
    excluded = str(row.get("excluded_reason") or "").strip()
    if excluded:
        return False, excluded
    return True, ""


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _row_reason_codes(row: Mapping[str, Any], *, rejection_reason: str) -> list[str]:
    raw = row.get("reason_codes")
    reasons = [str(item) for item in raw if str(item)] if isinstance(raw, list) else []
    for field in ("candidate_reason", "reason"):
        text = str(row.get(field) or "")
        if text:
            reasons.extend(part for part in text.split("|") if part)
    if rejection_reason:
        reasons.append(rejection_reason)
    return sorted(set(reasons))


def _int_or_default(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _current_summary(*, runtime_root: Path, business_date: str) -> dict[str, Any]:
    path = runtime_root / "persistent_ledger" / "state.json"
    payload = _read_json(path) if path.is_file() else {}
    positions = payload.get("positions") if isinstance(payload.get("positions"), list) else []
    cash = _float(payload.get("cash", payload.get("buying_power", 0.0)))
    market_value = sum(_float(row.get("market_value", row.get("value", 0.0))) for row in positions if isinstance(row, Mapping))
    total_equity = _float(payload.get("total_equity", cash + market_value))
    rows = []
    for row in positions:
        if not isinstance(row, Mapping):
            continue
        value = _float(row.get("market_value", row.get("value", 0.0)))
        symbol = str(row.get("symbol") or row.get("security_code") or row.get("code") or row.get("issue_code") or "").strip()
        campaign_id = str(row.get("position_campaign_id") or "")
        rows.append({**dict(row), "position_campaign_id": campaign_id, "current_weight": round(value / total_equity, 6) if total_equity > 0 else 0.0})
    return {"status": "PASS" if path.is_file() else "MISSING", "business_date": business_date, "feature_date": business_date, "source_ref": str(path), "source_hash": _file_hash(path), "summary": {"position_count": len(positions), "current_position_count": len(positions), "positions": rows, "cash": cash, "buying_power": _float(payload.get("buying_power", cash)), "current_cash": cash, "current_market_value": market_value, "gross_exposure": market_value, "portfolio_value": total_equity, "portfolio_total_equity": total_equity}, "rows": tuple(rows)}


def _supply_prior_exit_state(
    *,
    run_dir: Path | None = None,
    runtime_root: Path,
    business_date: str,
    candidate: Mapping[str, Any],
    opportunity: Mapping[str, Any],
    current: Mapping[str, Any],
) -> dict[str, Any]:
    current_symbols = {
        str(row.get("symbol") or row.get("security_code") or row.get("code") or "").strip()
        for row in current.get("rows") or ()
        if isinstance(row, Mapping) and _float(row.get("quantity"), default=0.0) > 0
    }
    guard_source = _bounded_recent_exit_guard_state_by_symbol(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date=business_date,
    )
    guard_by_symbol = guard_source["by_symbol"]
    candidate_result = _attach_prior_exit_to_summary(candidate, prior_by_symbol=guard_by_symbol, current_symbols=current_symbols)
    opportunity_result = _attach_prior_exit_to_summary(opportunity, prior_by_symbol=guard_by_symbol, current_symbols=current_symbols)
    supplied_symbols = sorted(set(candidate_result["supplied_symbols"]) | set(opportunity_result["supplied_symbols"]))
    return {
        "candidate": candidate_result["summary"],
        "opportunity": opportunity_result["summary"],
        "evidence": {
            "schema_version": "phase32_ew_bounded_recent_exit_guard_supply_evidence.v1",
            "business_date": business_date,
            "authority": "bounded_recent_exit_guard_index",
            "source_path": guard_source["source_path"],
            "source_hash": guard_source["source_hash"],
            "stale_or_cross_run_guard_rows_rejected": guard_source.get("stale_or_cross_run_rows_rejected", 0),
            "pm_exit_evidence_supplied": False,
            "pm_exit_evidence_campaign_count": 0,
            "temporal_selection_rule": "guard_exit_business_date_strictly_less_than_decision_business_date",
            "materialized_field": "recent_exit_guard_minimal_lineage",
            "prior_closed_campaign_count": len(guard_by_symbol),
            "candidate_supplied_count": candidate_result["supplied_count"],
            "opportunity_supplied_count": opportunity_result["supplied_count"],
            "supplied_symbols": supplied_symbols,
            "current_position_symbols_skipped": sorted(symbol for symbol in current_symbols if symbol in guard_by_symbol),
            "future_or_same_day_exit_used": False,
            "post_hoc_pnl_input_used": False,
            "missing_prior_exit_behavior": "ordinary_current_buy_unchanged",
            "full_executions_jsonl_scanned_for_reentry": False,
            "strict_prior_pm_exit_artifacts_scanned_for_reentry": False,
            "full_prior_campaign_history_scanned_for_reentry": False,
            "daily_full_prior_exit_context_materialized": False,
        },
    }


def _bounded_recent_exit_guard_state_by_symbol(
    *,
    run_dir: Path | None,
    runtime_root: Path,
    business_date: str,
) -> dict[str, Any]:
    paths = [
        runtime_root / "runtime_state" / "recent_exit_guard" / f"{business_date}.json",
        runtime_root / "runtime_state" / "recent_exit_guard.json",
    ]
    if run_dir is not None:
        paths.append(run_dir / "daily" / business_date / "strategy" / "recent_exit_guard.json")
    expected_runtime_test_run_id = run_dir.name if run_dir is not None else ""
    for path in paths:
        payload = _read_json(path)
        rows = payload.get("rows") if isinstance(payload.get("rows"), list) else payload.get("guards")
        if not isinstance(rows, list):
            continue
        by_symbol: dict[str, dict[str, Any]] = {}
        stale_or_cross_run_rows_rejected = 0
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            row_run_id = str(row.get("runtime_test_run_id") or row.get("run_id") or "").strip()
            if expected_runtime_test_run_id and row_run_id and row_run_id != expected_runtime_test_run_id:
                stale_or_cross_run_rows_rejected += 1
                continue
            symbol = str(row.get("symbol") or row.get("security_code") or row.get("code") or "").strip()
            exit_date = str(row.get("most_recent_full_exit_business_date") or row.get("prior_exit_business_date") or "").strip()
            if not symbol or not exit_date or exit_date >= business_date:
                continue
            by_symbol[symbol] = _minimal_recent_exit_guard_row(row, business_date=business_date, source_path=path)
        return {
            "by_symbol": by_symbol,
            "source_path": str(path),
            "source_hash": _file_hash(path),
            "stale_or_cross_run_rows_rejected": stale_or_cross_run_rows_rejected,
        }
    return {"by_symbol": {}, "source_path": "", "source_hash": "", "stale_or_cross_run_rows_rejected": 0}


def _minimal_recent_exit_guard_row(row: Mapping[str, Any], *, business_date: str, source_path: Path) -> dict[str, Any]:
    exit_date = str(row.get("most_recent_full_exit_business_date") or row.get("prior_exit_business_date") or "").strip()
    prior_campaign_id = str(row.get("prior_campaign_id") or row.get("prior_exit_campaign_id") or "").strip()
    source_pm_decision_id = str(row.get("source_pm_decision_id") or "").strip()
    source_decision_id = str(row.get("source_decision_id") or "").strip()
    return {
        "prior_exit_business_date": exit_date,
        "prior_campaign_id": prior_campaign_id,
        "prior_exit_campaign_id": prior_campaign_id,
        "source_pm_decision_id": source_pm_decision_id,
        "source_decision_id": source_decision_id,
        "prior_exit_provenance_status": str(row.get("prior_exit_provenance_status") or "PASS"),
        "prior_exit_reason": str(row.get("guard_relevant_exit_class") or row.get("prior_exit_reason") or ""),
        "ownership_lineage": "PRIOR_EXIT_LINEAGE_PRESENT",
        "recent_exit_guard_state": str(row.get("recent_exit_guard_state") or "ACTIVE_RECENT_EXIT_GUARD"),
        "recent_exit_guard_status": str(row.get("recent_exit_guard_status") or "FAIL_CLOSED"),
        "recent_exit_guard_reason": str(row.get("recent_exit_guard_reason") or "recent_exit_churn_guard_active"),
        "recent_exit_guard_source": {
            "source_path": str(source_path),
            "source_hash": _file_hash(source_path),
            "business_date": business_date,
            "prior_exit_business_date": exit_date,
            "prior_campaign_id": prior_campaign_id,
            "source_pm_decision_id": source_pm_decision_id,
            "source_decision_id": source_decision_id,
        },
    }


def _materialize_pre_action_position_campaigns(
    *,
    run_dir: Path,
    runtime_root: Path | None = None,
    business_date: str,
    current: Mapping[str, Any],
    as_of: str,
) -> dict[str, Any]:
    output_path = run_dir / "daily" / business_date / "positions" / "position_campaigns.json"
    prior_path = _latest_prior_position_campaigns_path(run_dir=run_dir, business_date=business_date)
    prior_payload = _read_json(prior_path) if prior_path is not None else {}
    prior_campaigns = prior_payload.get("position_campaigns") if isinstance(prior_payload.get("position_campaigns"), list) else []
    ledger_path = (runtime_root / "persistent_ledger" / "executions.jsonl") if runtime_root is not None else None
    ledger_campaigns = _strict_prior_ledger_campaigns_by_symbol(
        _read_jsonl(ledger_path) if ledger_path is not None else [],
        business_date=business_date,
    )
    current_by_symbol = {
        str(row.get("symbol") or row.get("security_code") or row.get("code") or row.get("issue_code") or "").strip(): row
        for row in current.get("rows") or ()
        if isinstance(row, Mapping)
        and str(row.get("symbol") or row.get("security_code") or row.get("code") or row.get("issue_code") or "").strip()
        and _float(row.get("quantity"), default=0.0) > 0
    }
    materialized: list[dict[str, Any]] = []
    updated_symbols: set[str] = set()
    closed_symbols: set[str] = set()
    for item in prior_campaigns:
        if not isinstance(item, Mapping):
            continue
        row = dict(item)
        symbol = str(row.get("symbol") or row.get("security_code") or row.get("code") or "").strip()
        current_row = current_by_symbol.get(symbol)
        if current_row and _campaign_is_open(row):
            row = _refresh_campaign_with_current(row, current_row=current_row, business_date=business_date)
            ledger_row = ledger_campaigns.get(symbol)
            if ledger_row and str(ledger_row.get("campaign_status") or "").upper() == "OPEN":
                row = _merge_strict_prior_ledger_history_into_open_campaign(row, ledger_row=ledger_row)
            updated_symbols.add(symbol)
        elif symbol and _campaign_is_open(row) and symbol not in current_by_symbol:
            ledger_row = ledger_campaigns.get(symbol)
            if ledger_row and str(ledger_row.get("campaign_status") or "").upper() == "CLOSED":
                row = _close_campaign_from_ledger(row, ledger_row=ledger_row, business_date=business_date)
                closed_symbols.add(symbol)
        materialized.append(row)
    bootstrap_symbols: list[str] = []
    open_materialized_symbols = {
        str(row.get("symbol") or row.get("security_code") or row.get("code") or "").strip()
        for row in materialized
        if isinstance(row, Mapping) and _campaign_is_open(row)
    }
    for symbol in sorted(set(current_by_symbol) - updated_symbols - open_materialized_symbols):
        ledger_row = ledger_campaigns.get(symbol)
        if not ledger_row or str(ledger_row.get("campaign_status") or "").upper() != "OPEN":
            continue
        materialized.append(_refresh_campaign_with_current(ledger_row, current_row=current_by_symbol[symbol], business_date=business_date))
        updated_symbols.add(symbol)
        bootstrap_symbols.append(symbol)
    prior_pm_decision_evidence = _strict_prior_pm_sell_decision_evidence_by_campaign(
        run_dir=run_dir,
        business_date=business_date,
    )
    pm_decision_evidence_count = 0
    pm_decision_evidence_campaign_count = 0
    for index, row in enumerate(materialized):
        campaign_id = str(row.get("position_campaign_id") or "").strip()
        events = prior_pm_decision_evidence.get(campaign_id, [])
        if not events:
            continue
        patched = dict(row)
        existing_events = [
            item
            for item in patched.get("pm_decision_evidence_events") or []
            if isinstance(item, Mapping)
        ]
        merged = _dedupe_pm_decision_evidence_events([*existing_events, *events])
        patched["pm_decision_evidence_events"] = merged
        patched["pm_decision_evidence_contract"] = {
            "schema_version": "phase31_f1i_pm_decision_evidence_history.v1",
            "authority": "STRICT_PRIOR_PM_DECISION_EVIDENCE",
            "semantic": "decision_intent_representability_evidence_not_execution",
            "source_selection_rule": "daily strategy/position_management artifacts with business_date strictly less than decision business_date",
            "same_day_self_count_protected": True,
            "future_information_used": False,
        }
        materialized[index] = patched
        pm_decision_evidence_count += len(merged)
        pm_decision_evidence_campaign_count += 1
    missing_current_campaign_symbols = sorted(set(current_by_symbol) - updated_symbols)
    payload = {
        "schema_version": "position_campaign_observability.v1",
        "contract_version": "phase30_ad1_pre_action_campaign_lifecycle.v1",
        "business_date": business_date,
        "generated_at": as_of,
        "authority": "CANONICAL_PRE_ACTION_POSITION_CAMPAIGN_LIFECYCLE",
        "identity_policy": str(prior_payload.get("identity_policy") or "RUN_SCOPED_DETERMINISTIC_EXECUTION_REPLAY_SYMBOL_SEQUENCE"),
        "position_campaigns": materialized,
        "source_artifacts": {
            "prior_position_campaigns": {
                "path": str(prior_path or ""),
                "hash": _file_hash(prior_path) if prior_path is not None else "",
                "business_date": str(prior_payload.get("business_date") or ""),
            },
            "current": {
                "path": str(current.get("source_ref") or ""),
                "hash": str(current.get("source_hash") or ""),
                "business_date": str(current.get("business_date") or business_date),
            },
            "ledger_executions": {
                "path": str(ledger_path or ""),
                "hash": _file_hash(ledger_path) if ledger_path is not None else "",
                "temporal_selection_rule": "execution_business_date_strictly_less_than_decision_business_date",
            },
            "strict_prior_pm_decision_evidence": {
                "authority": "strategy.position_management",
                "temporal_selection_rule": "pm_decision_business_date_strictly_less_than_decision_business_date",
                "semantic": "decision_intent_representability_evidence_not_execution",
                "campaigns_with_evidence": pm_decision_evidence_campaign_count,
                "evidence_event_count": pm_decision_evidence_count,
            },
        },
        "temporal_safety": {
            "temporal_stage": "PRE_ACTION_DECISION_SNAPSHOT",
            "source_selection_rule": "latest prior position_campaigns plus strict-prior ledger executions plus strict-prior PM decision evidence plus current state available at decision time",
            "same_day_eod_campaign_reconstruction_used": False,
            "same_day_pm_decision_self_count_used": False,
            "same_day_future_execution_used": False,
            "future_mfe_used": False,
            "future_giveback_used": False,
            "historical_outcome_used_as_runtime_input": False,
            "future_information_used": False,
        },
        "pre_action_connection": {
            "current_open_position_count": len(current_by_symbol),
            "campaigns_materialized_count": len(materialized),
            "updated_open_campaign_count": len(updated_symbols),
            "bootstrap_open_campaign_count": len(bootstrap_symbols),
            "bootstrap_open_campaign_symbols": bootstrap_symbols,
            "closed_campaign_count": len(closed_symbols),
            "closed_campaign_symbols": sorted(closed_symbols),
            "missing_current_campaign_symbols": missing_current_campaign_symbols,
            "missing_current_campaign_behavior": "EXPLICIT_REVIEW_REQUIRED_IN_STRATEGY_INTELLIGENCE_UNLESS_STRICT_PRIOR_LEDGER_OPEN_CAMPAIGN_PROVES_BOOTSTRAP",
            "bootstrap_authority": "persistent_ledger_executions_strict_prior",
            "duplicate_campaign_authority_created": False,
            "pm_decision_evidence_authority": "strategy.position_management strict-prior decision evidence",
            "pm_decision_evidence_event_count": pm_decision_evidence_count,
            "pm_decision_evidence_campaign_count": pm_decision_evidence_campaign_count,
            "fake_execution_event_created": False,
        },
    }
    _write_json(output_path, payload)
    return {
        "artifact_path": output_path,
        "evidence": {
            "schema_version": "phase30_ac_pre_action_campaign_lifecycle_connection.v1",
            "business_date": business_date,
            "artifact_path": str(output_path),
            "artifact_hash": _file_hash(output_path),
            "prior_artifact_path": str(prior_path or ""),
            "prior_artifact_hash": _file_hash(prior_path) if prior_path is not None else "",
            "ledger_executions_path": str(ledger_path or ""),
            "ledger_executions_hash": _file_hash(ledger_path) if ledger_path is not None else "",
            "current_open_position_count": len(current_by_symbol),
            "updated_open_campaign_count": len(updated_symbols),
            "bootstrap_open_campaign_count": len(bootstrap_symbols),
            "bootstrap_open_campaign_symbols": bootstrap_symbols,
            "closed_campaign_count": len(closed_symbols),
            "closed_campaign_symbols": sorted(closed_symbols),
            "missing_current_campaign_symbols": missing_current_campaign_symbols,
            "canonical_authority": "positions/position_campaigns.json",
            "duplicate_campaign_authority_created": False,
            "same_day_eod_campaign_reconstruction_used": False,
            "same_day_pm_decision_self_count_used": False,
            "same_day_future_execution_used": False,
            "pm_decision_evidence_authority": "strategy.position_management strict-prior decision evidence",
            "pm_decision_evidence_event_count": pm_decision_evidence_count,
            "pm_decision_evidence_campaign_count": pm_decision_evidence_campaign_count,
            "fake_execution_event_created": False,
            "future_information_used": False,
        },
    }


def _strict_prior_pm_sell_decision_evidence_by_campaign(
    *,
    run_dir: Path,
    business_date: str,
) -> dict[str, list[dict[str, Any]]]:
    daily_root = run_dir / "daily"
    if not daily_root.is_dir():
        return {}
    by_campaign: dict[str, list[dict[str, Any]]] = {}
    for child in sorted(item for item in daily_root.iterdir() if item.is_dir()):
        decision_date = child.name
        if not decision_date or decision_date >= business_date:
            continue
        pm_path = child / "strategy" / "position_management.json"
        payload = _read_json(pm_path)
        positions = payload.get("positions") if isinstance(payload.get("positions"), list) else []
        for row in positions:
            if not isinstance(row, Mapping):
                continue
            event = _pm_sell_decision_evidence_event(row, business_date=decision_date, source_path=pm_path)
            if not event:
                continue
            campaign_id = str(event.get("campaign_id") or "").strip()
            if not campaign_id:
                continue
            by_campaign.setdefault(campaign_id, []).append(event)
    return {
        campaign_id: _dedupe_pm_decision_evidence_events(events)
        for campaign_id, events in by_campaign.items()
    }


def _strict_prior_pm_exit_decision_evidence_by_campaign(
    *,
    run_dir: Path,
    business_date: str,
) -> dict[str, dict[str, Any]]:
    daily_root = run_dir / "daily"
    if not daily_root.is_dir():
        return {}
    by_campaign: dict[str, dict[str, Any]] = {}
    for child in sorted(item for item in daily_root.iterdir() if item.is_dir()):
        decision_date = child.name
        if not decision_date or decision_date >= business_date:
            continue
        for pm_path in (
            child / "position_management" / "pm_decisions.json",
            child / "strategy" / "position_management.json",
        ):
            payload = _read_json(pm_path)
            rows = payload.get("decisions") if isinstance(payload.get("decisions"), list) else payload.get("positions")
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, Mapping):
                    continue
                event = _pm_exit_decision_context_event(row, business_date=decision_date, source_path=pm_path)
                if not event:
                    continue
                campaign_id = str(event.get("prior_campaign_id") or "").strip()
                if not campaign_id:
                    continue
                current = by_campaign.get(campaign_id)
                if current is None or str(event.get("prior_exit_business_date") or "") >= str(current.get("prior_exit_business_date") or ""):
                    by_campaign[campaign_id] = event
    return by_campaign


def _pm_exit_decision_context_event(
    row: Mapping[str, Any],
    *,
    business_date: str,
    source_path: Path,
) -> dict[str, Any] | None:
    decision_type = str(row.get("decision_type") or row.get("action") or "").upper()
    decision_status = str(row.get("decision_status") or "").upper()
    if decision_type not in {"EXIT", "SELL_EXIT"} and "SELL_FULL_POSITION" not in decision_status:
        return None
    campaign_id = str(
        row.get("position_campaign_id")
        or row.get("campaign_id")
        or row.get("strategy_intelligence_campaign_id")
        or ""
    ).strip()
    symbol = str(row.get("symbol") or row.get("security_code") or row.get("code") or "").strip()
    reason_codes = row.get("reason_codes") if isinstance(row.get("reason_codes"), list) else []
    decision_reason = _semantic_prior_exit_reason(
        row.get("decision_reason"),
        row.get("dominant_cause"),
        reason_codes,
        decision_type,
    )
    return {
        "schema_version": "phase32_h_prior_exit_context.v1",
        "prior_campaign_id": campaign_id,
        "prior_exit_business_date": business_date,
        "prior_exit_decision_type": "EXIT",
        "prior_exit_reason": decision_reason,
        "prior_exit_reason_codes": [str(item) for item in reason_codes if str(item)],
        "source_pm_decision_id": str(row.get("pm_decision_id") or row.get("decision_id") or ""),
        "source_decision_id": str(row.get("source_decision_id") or row.get("pm_decision_id") or row.get("decision_id") or ""),
        "symbol": symbol,
        "provenance_status": "PASS",
        "authority": "STRICT_PRIOR_PM_EXIT_DECISION_CONTEXT",
        "source_artifact_path": str(source_path),
        "source_artifact_hash": _file_hash(source_path),
        "temporal_selection_rule": "pm_exit_decision_business_date_strictly_less_than_reentry_decision_business_date",
        "future_information_used": False,
    }


def _semantic_prior_exit_reason(*candidates: Any) -> str:
    generic = {"", "EXIT", "SELL", "SELL_EXIT", "UNKNOWN"}
    fallback = ""
    for candidate in candidates:
        values = candidate if isinstance(candidate, list) else [candidate]
        for value in values:
            text = str(value or "").strip()
            if not text:
                continue
            fallback = fallback or text
            if text.upper() not in generic:
                return text
    return fallback or "EXIT"


def _pm_sell_decision_evidence_event(
    row: Mapping[str, Any],
    *,
    business_date: str,
    source_path: Path,
) -> dict[str, Any] | None:
    evidence = row.get("canonical_sell_semantic_evidence") if isinstance(row.get("canonical_sell_semantic_evidence"), Mapping) else {}
    original_action = str(evidence.get("original_pm_action") or row.get("action") or "").upper()
    final_action = str(evidence.get("final_pm_action") or row.get("action") or "").upper()
    canonical_state = str(evidence.get("canonical_sell_state") or row.get("canonical_sell_state") or "").upper()
    recovery_state = str(evidence.get("recovery_state") or "").upper()
    recovery = evidence.get("recovery_dimensions") if isinstance(evidence.get("recovery_dimensions"), Mapping) else {}
    parameter_status = str(evidence.get("parameter_resolution_status") or "").upper()
    representability_family = str(evidence.get("representability_family") or "").upper()
    final_reduce_quantity = _float(evidence.get("final_reduce_quantity"), default=0.0)
    minimum_notional = bool(evidence.get("minimum_notional_flag"))
    is_unrepresentable_reduce = bool(
        original_action == "REDUCE"
        and representability_family == "DISCRETE_LOT"
        and abs(final_reduce_quantity) <= 1e-9
        and not minimum_notional
    )
    is_recovery_boundary = bool(
        original_action in {"HOLD", "ADD"}
        and final_action in {"HOLD", "ADD"}
        and canonical_state == "HEALTHY_OR_RECOVERING"
        and recovery_state == "RECOVERY_PRESENT"
    )
    if not is_unrepresentable_reduce and not is_recovery_boundary:
        return None
    campaign_id = str(evidence.get("campaign_id") or row.get("position_campaign_id") or row.get("strategy_intelligence_campaign_id") or "").strip()
    symbol = str(evidence.get("symbol") or row.get("security_code") or row.get("symbol") or "").strip()
    event_kind = "UNREPRESENTABLE_REDUCE_DECISION" if is_unrepresentable_reduce else "RECOVERY_BOUNDARY"
    return {
        "schema_version": "phase31_f1i_pm_decision_evidence_event.v1",
        "business_date": business_date,
        "symbol": symbol,
        "campaign_id": campaign_id,
        "event_kind": event_kind,
        "pm_action": original_action,
        "final_pm_action": final_action,
        "pm_reason_codes": [str(item) for item in row.get("reason_codes") or evidence.get("original_pm_reasons") or []],
        "canonical_sell_state": canonical_state,
        "representability_family": representability_family,
        "current_quantity": evidence.get("current_quantity"),
        "trading_unit": evidence.get("trading_unit"),
        "raw_reduce_quantity": evidence.get("raw_reduce_quantity"),
        "rounded_reduce_quantity": evidence.get("rounded_reduce_quantity"),
        "final_reduce_quantity": evidence.get("final_reduce_quantity"),
        "minimum_notional_flag": minimum_notional,
        "recovery_state": recovery_state,
        "recovery_reset_policy": str(recovery.get("reset_policy") or parameter_status or ""),
        "pit_proof": evidence.get("pit_proof") or {},
        "source_artifact_path": str(source_path),
        "source_artifact_hash": _file_hash(source_path),
        "source_contract_version": str(row.get("canonical_sell_semantic_contract_version") or evidence.get("contract_version") or ""),
        "decision_evidence_not_execution": True,
        "fake_execution_event_created": False,
        "future_information_used": False,
    }


def _dedupe_pm_decision_evidence_events(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for event in events:
        key = (
            str(event.get("business_date") or ""),
            str(event.get("symbol") or ""),
            str(event.get("campaign_id") or ""),
            str(event.get("event_kind") or ""),
        )
        if not all(key):
            continue
        deduped[key] = dict(event)
    return [deduped[key] for key in sorted(deduped)]


def _strict_prior_ledger_campaigns_by_symbol(executions: Iterable[Mapping[str, Any]], *, business_date: str) -> dict[str, dict[str, Any]]:
    states: dict[str, dict[str, Any]] = {}
    ordered = sorted(
        enumerate(executions),
        key=lambda item: (
            str(item[1].get("business_date") or "")[:10],
            str(item[1].get("executed_at") or item[1].get("created_at") or ""),
            item[0],
        ),
    )
    for index, row in ordered:
        execution_date = str(row.get("business_date") or "")[:10]
        if not execution_date or execution_date >= business_date:
            continue
        symbol = str(row.get("symbol") or row.get("broker_issue_code") or row.get("security_code") or row.get("code") or "").strip()
        if not symbol:
            continue
        side = str(row.get("side") or "").upper()
        quantity = _float(row.get("filled_quantity") or row.get("quantity"), default=0.0)
        if side not in {"BUY", "SELL"} or quantity <= 0:
            continue
        state = states.setdefault(symbol, {"quantity": 0.0, "campaign_index": 0, "campaign": {}})
        before_quantity = _float(state.get("quantity"), default=0.0)
        if side == "BUY":
            if before_quantity <= 1e-6:
                state["campaign_index"] = int(state.get("campaign_index") or 0) + 1
                state["campaign"] = _new_campaign_from_execution(
                    row,
                    symbol=symbol,
                    business_date=execution_date,
                    campaign_index=int(state["campaign_index"]),
                    source_index=index,
                )
            state["quantity"] = before_quantity + quantity
            campaign = dict(state.get("campaign") or {})
            campaign["campaign_status"] = "OPEN"
            campaign["current_quantity"] = state["quantity"]
            campaign["buy_history_summary"] = _history_increment(campaign.get("buy_history_summary"), business_date=execution_date)
            if before_quantity > 1e-6:
                campaign["add_history_summary"] = _history_increment(campaign.get("add_history_summary"), business_date=execution_date)
                campaign["latest_add_business_date"] = execution_date
            events = list(campaign.get("events") or [])
            events.append(_campaign_event_from_execution(row, side="BUY", business_date=execution_date))
            campaign["events"] = events
            state["campaign"] = campaign
            continue
        if before_quantity <= 1e-6:
            continue
        after_quantity = max(before_quantity - quantity, 0.0)
        state["quantity"] = 0.0 if after_quantity <= 1e-6 else after_quantity
        campaign = dict(state.get("campaign") or {})
        campaign["current_quantity"] = state["quantity"]
        campaign["reduce_history_summary"] = _history_increment(campaign.get("reduce_history_summary"), business_date=execution_date)
        campaign.setdefault("sell_history_summary", {"count": 0, "latest_business_date": ""})
        campaign["sell_history_summary"] = _history_increment(campaign.get("sell_history_summary"), business_date=execution_date)
        events = list(campaign.get("events") or [])
        events.append(_campaign_event_from_execution(row, side="SELL", business_date=execution_date))
        campaign["events"] = events
        if state["quantity"] <= 1e-6:
            campaign["campaign_status"] = "CLOSED"
            campaign["closed_business_date"] = execution_date
            campaign["current_quantity"] = 0.0
        else:
            campaign["campaign_status"] = "OPEN"
        state["campaign"] = campaign
    return {symbol: dict(state.get("campaign") or {}) for symbol, state in states.items() if state.get("campaign")}


def _new_campaign_from_execution(
    row: Mapping[str, Any],
    *,
    symbol: str,
    business_date: str,
    campaign_index: int,
    source_index: int,
) -> dict[str, Any]:
    execution_ref = str(row.get("execution_id") or row.get("record_id") or row.get("ledger_record_id") or row.get("execution_key") or source_index)
    explicit_campaign_id = str(
        row.get("position_campaign_id")
        or row.get("campaign_id")
        or row.get("canonical_position_campaign_id")
        or row.get("open_position_campaign_id")
        or row.get("source_position_campaign_id")
        or ""
    ).strip()
    campaign_id = explicit_campaign_id or f"pc-{hashlib.sha256(f'{symbol}|{campaign_index}|{execution_ref}'.encode()).hexdigest()[:16]}-{symbol}-{campaign_index:04d}"
    price = _float(row.get("average_price") or row.get("price") or row.get("market_price"), default=0.0)
    return {
        "position_campaign_id": campaign_id,
        "symbol": symbol,
        "campaign_status": "OPEN",
        "opened_business_date": business_date,
        "campaign_age_business_days": 0,
        "entry_thesis_state": "BUY_NEW_LEDGER_BOOTSTRAPPED",
        "current_quantity": 0.0,
        "average_price": price,
        "current_valuation_price": price,
        "current_market_value": _float(row.get("market_value"), default=0.0),
        "current_campaign_relative_return": None,
        "observed_campaign_mfe": None,
        "observed_giveback": 0.0,
        "source_execution_id": str(row.get("execution_id") or ""),
        "source_execution_record_id": str(row.get("record_id") or row.get("ledger_record_id") or ""),
        "source_execution_dedup_key": str(row.get("dedup_key") or row.get("execution_key") or ""),
        "source_execution_business_date": business_date,
        "quantity_basis": row.get("quantity_basis") or row.get("execution_price_basis") or row.get("fill_price_basis") or "",
        "valuation_price_basis": row.get("valuation_price_basis") or row.get("execution_price_basis") or row.get("fill_price_basis") or "",
        "observed_state_authority": "STRICT_PRIOR_LEDGER_EXECUTION_BOOTSTRAP",
        "future_information_used": False,
        "events": [],
    }


def _campaign_event_from_execution(row: Mapping[str, Any], *, side: str, business_date: str) -> dict[str, Any]:
    return {
        "business_date": business_date,
        "side": side,
        "stage": "BUY" if side == "BUY" else "SELL",
        "quantity": _float(row.get("filled_quantity") or row.get("quantity"), default=0.0),
        "price": _float(row.get("average_price") or row.get("price") or row.get("market_price"), default=0.0),
        "position_campaign_id": str(row.get("position_campaign_id") or row.get("campaign_id") or ""),
        "canonical_position_campaign_id": str(row.get("canonical_position_campaign_id") or ""),
        "open_position_campaign_id": str(row.get("open_position_campaign_id") or ""),
        "source_position_campaign_id": str(row.get("source_position_campaign_id") or ""),
        "source_decision_type": str(row.get("source_decision_type") or ""),
        "source_execution_id": str(row.get("execution_id") or ""),
        "source_execution_record_id": str(row.get("record_id") or row.get("ledger_record_id") or ""),
        "source_execution_dedup_key": str(row.get("dedup_key") or row.get("execution_key") or ""),
    }


def _history_increment(summary: Any, *, business_date: str) -> dict[str, Any]:
    payload = dict(summary) if isinstance(summary, Mapping) else {}
    payload["count"] = int(_float(payload.get("count"), default=0.0)) + 1
    payload["latest_business_date"] = business_date
    return payload


def _close_campaign_from_ledger(campaign: Mapping[str, Any], *, ledger_row: Mapping[str, Any], business_date: str) -> dict[str, Any]:
    row = dict(campaign)
    row["campaign_status"] = "CLOSED"
    row["current_quantity"] = 0.0
    row["current_market_value"] = 0.0
    row["closed_business_date"] = str(ledger_row.get("closed_business_date") or ledger_row.get("source_execution_business_date") or business_date)
    row["observed_state_as_of_business_date"] = business_date
    row["observed_state_authority"] = "PRE_ACTION_CURRENT_PLUS_STRICT_PRIOR_LEDGER_EXIT"
    row["future_information_used"] = False
    return row


def _latest_prior_position_campaigns_path(*, run_dir: Path, business_date: str) -> Path | None:
    daily_dir = run_dir / "daily"
    if not daily_dir.is_dir():
        return None
    candidates: list[tuple[str, Path]] = []
    for child in daily_dir.iterdir():
        if not child.is_dir():
            continue
        day = child.name
        if not day or day >= business_date:
            continue
        path = child / "positions" / "position_campaigns.json"
        if path.is_file():
            candidates.append((day, path))
    return sorted(candidates, key=lambda item: item[0])[-1][1] if candidates else None


def _campaign_is_open(row: Mapping[str, Any]) -> bool:
    status = str(row.get("campaign_status") or "").upper()
    quantity = _float(row.get("current_quantity"), default=0.0)
    return status == "OPEN" or quantity > 0


def _refresh_campaign_with_current(campaign: Mapping[str, Any], *, current_row: Mapping[str, Any], business_date: str) -> dict[str, Any]:
    row = dict(campaign)
    quantity = _float(current_row.get("quantity"), default=0.0)
    market_value = _float(current_row.get("market_value", current_row.get("value")), default=0.0)
    avg = _float(current_row.get("average_price"), default=0.0)
    current_price = market_value / quantity if quantity > 0 and market_value > 0 else _float(
        current_row.get("current_price", current_row.get("reference_price", current_row.get("price"))),
        default=0.0,
    )
    campaign_return = current_price / avg - 1.0 if avg > 0 and current_price > 0 else None
    prior_mfe = _float(row.get("observed_campaign_mfe"), default=float("-inf"))
    current_mfe = campaign_return if campaign_return is not None else None
    if current_mfe is not None:
        observed_mfe = max(prior_mfe, current_mfe) if prior_mfe != float("-inf") else current_mfe
    else:
        observed_mfe = None if prior_mfe == float("-inf") else prior_mfe
    prior_giveback = _float(row.get("observed_giveback"), default=0.0)
    observed_giveback = max(prior_giveback, (observed_mfe - campaign_return) if observed_mfe is not None and campaign_return is not None else 0.0)
    row.update(
        {
            "campaign_status": "OPEN",
            "current_quantity": quantity,
            "average_price": avg if avg > 0 else row.get("average_price"),
            "current_market_value": market_value,
            "current_valuation_price": current_price if current_price > 0 else row.get("current_valuation_price"),
            "current_campaign_relative_return": campaign_return,
            "observed_campaign_mfe": observed_mfe,
            "observed_giveback": observed_giveback,
            "observed_state_as_of_business_date": business_date,
            "quantity_basis": current_row.get("quantity_basis", row.get("quantity_basis")),
            "valuation_price_basis": current_row.get("valuation_price_basis", row.get("valuation_price_basis")),
            "observed_state_authority": "PRE_ACTION_CURRENT_PLUS_PRIOR_CANONICAL_CAMPAIGN",
            "future_information_used": False,
        }
    )
    return row


def _merge_strict_prior_ledger_history_into_open_campaign(campaign: Mapping[str, Any], *, ledger_row: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(campaign)
    if not _campaign_is_open(row) or str(ledger_row.get("campaign_status") or "").upper() != "OPEN":
        return row
    campaign_symbol = str(row.get("symbol") or row.get("security_code") or row.get("code") or "").strip()
    ledger_symbol = str(ledger_row.get("symbol") or ledger_row.get("security_code") or ledger_row.get("code") or "").strip()
    if campaign_symbol and ledger_symbol and campaign_symbol != ledger_symbol:
        return row

    existing_events = [dict(item) for item in row.get("events") or [] if isinstance(item, Mapping)]
    ledger_events = [dict(item) for item in ledger_row.get("events") or [] if isinstance(item, Mapping)]
    if not ledger_events:
        return row
    campaign_id = str(row.get("position_campaign_id") or "").strip()
    if not _ledger_events_prove_open_campaign_identity(ledger_events, campaign_id=campaign_id):
        return row

    merged_events = _dedupe_campaign_events_by_execution_identity([*existing_events, *ledger_events])
    row["events"] = merged_events

    buy_dates = [str(event.get("business_date") or "") for event in merged_events if str(event.get("side") or "").upper() == "BUY"]
    sell_dates = [str(event.get("business_date") or "") for event in merged_events if str(event.get("side") or "").upper() == "SELL"]
    if buy_dates:
        row["buy_history_summary"] = {
            "count": len(buy_dates),
            "latest_business_date": max(buy_dates),
        }
        if len(buy_dates) > 1:
            row["add_history_summary"] = {
                "count": len(buy_dates) - 1,
                "latest_business_date": max(buy_dates[1:]),
            }
            row["latest_add_business_date"] = max(buy_dates[1:])
        else:
            row.pop("latest_add_business_date", None)
            if "add_history_summary" in row:
                row["add_history_summary"] = {"count": 0, "latest_business_date": ""}
    if sell_dates and "sell_history_summary" in ledger_row:
        row["sell_history_summary"] = {
            "count": len(sell_dates),
            "latest_business_date": max(sell_dates),
        }
    return row


def _ledger_events_prove_open_campaign_identity(events: Iterable[Mapping[str, Any]], *, campaign_id: str) -> bool:
    if not campaign_id:
        return False
    explicit_ids: set[str] = set()
    bridge_ids: set[str] = set()
    for event in events:
        for key in ("canonical_position_campaign_id", "open_position_campaign_id", "source_position_campaign_id"):
            value = str(event.get(key) or "").strip()
            if value:
                bridge_ids.add(value)
        value = str(event.get("position_campaign_id") or event.get("campaign_id") or "").strip()
        if value:
            explicit_ids.add(value)
    if bridge_ids:
        return campaign_id in bridge_ids
    if explicit_ids:
        return explicit_ids == {campaign_id}
    # Legacy strict-prior ledger events predate campaign identity persistence.
    # They remain valid only when they carry no conflicting campaign identity at all.
    return not explicit_ids and not bridge_ids


def _campaign_event_identity(event: Mapping[str, Any]) -> tuple[str, str, str, str, str, str]:
    return (
        str(event.get("source_execution_dedup_key") or ""),
        str(event.get("source_execution_id") or ""),
        str(event.get("source_execution_record_id") or ""),
        str(event.get("business_date") or ""),
        str(event.get("side") or ""),
        str(event.get("quantity") or ""),
    )


def _campaign_event_natural_identity(event: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(event.get("business_date") or ""),
        str(event.get("side") or ""),
        str(event.get("quantity") or ""),
        str(event.get("price") or ""),
    )


def _campaign_event_has_execution_identity(event: Mapping[str, Any]) -> bool:
    return bool(event.get("source_execution_dedup_key") or event.get("source_execution_id") or event.get("source_execution_record_id"))


def _dedupe_campaign_events_by_execution_identity(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    exact_index: dict[tuple[str, str, str, str, str, str], int] = {}
    natural_index: dict[tuple[str, str, str, str], int] = {}
    for raw_event in events:
        event = dict(raw_event)
        exact = _campaign_event_identity(event)
        natural = _campaign_event_natural_identity(event)
        if any(exact) and exact in exact_index:
            merged[exact_index[exact]] = event
            continue
        if any(natural) and natural in natural_index:
            index = natural_index[natural]
            existing = merged[index]
            if _campaign_event_has_execution_identity(event) and not _campaign_event_has_execution_identity(existing):
                merged[index] = event
                exact_index[_campaign_event_identity(event)] = index
            continue
        index = len(merged)
        merged.append(event)
        if any(exact):
            exact_index[exact] = index
        if any(natural):
            natural_index[natural] = index
    return sorted(merged, key=lambda event: _campaign_event_sort_key(_campaign_event_identity(event)))


def _campaign_event_sort_key(key: tuple[str, str, str, str, str, str]) -> tuple[str, str, str, str, str, str]:
    dedup, execution_id, record_id, business_date, side, quantity = key
    side_order = "0" if side.upper() == "BUY" else "1" if side.upper() == "SELL" else "2"
    return (business_date, side_order, dedup, execution_id, record_id, quantity)


def _resolve_prior_closed_campaigns_from_executions(
    *,
    executions: Iterable[Mapping[str, Any]],
    business_date: str,
    pm_exit_evidence_by_campaign: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    states: dict[str, dict[str, Any]] = {}
    latest_closed: dict[str, dict[str, Any]] = {}
    pm_exit_evidence_by_campaign = pm_exit_evidence_by_campaign or {}
    pm_exit_evidence_by_source_id = _pm_exit_evidence_by_source_id(pm_exit_evidence_by_campaign)
    ordered = sorted(
        enumerate(executions),
        key=lambda item: (
            str(item[1].get("business_date") or ""),
            str(item[1].get("executed_at") or item[1].get("created_at") or ""),
            item[0],
        ),
    )
    for index, row in ordered:
        execution_date = str(row.get("business_date") or "")[:10]
        if not execution_date or execution_date >= business_date:
            continue
        symbol = str(row.get("symbol") or row.get("broker_issue_code") or row.get("security_code") or row.get("code") or "").strip()
        if not symbol:
            continue
        side = str(row.get("side") or "").upper()
        quantity = _float(row.get("filled_quantity") or row.get("quantity"), default=0.0)
        if quantity <= 0:
            continue
        state = states.setdefault(symbol, {"quantity": 0.0, "campaign_index": 0, "campaign_id": ""})
        if side == "BUY":
            if _float(state.get("quantity"), default=0.0) <= 1e-6:
                state["campaign_index"] = int(state.get("campaign_index") or 0) + 1
                explicit_campaign_id = str(row.get("position_campaign_id") or row.get("campaign_id") or "").strip()
                state["campaign_id"] = explicit_campaign_id or f"ledger-derived-{symbol}-{int(state['campaign_index']):04d}"
            state["quantity"] = _float(state.get("quantity"), default=0.0) + quantity
            continue
        if side != "SELL":
            continue
        before_quantity = _float(state.get("quantity"), default=0.0)
        if before_quantity <= 1e-6:
            continue
        sell_quantity = min(quantity, before_quantity)
        after_quantity = max(before_quantity - sell_quantity, 0.0)
        state["quantity"] = 0.0 if after_quantity <= 1e-6 else after_quantity
        if state["quantity"] <= 1e-6:
            closed_count = int(state.get("closed_campaign_count") or 0) + 1
            state["closed_campaign_count"] = closed_count
            reason_codes = row.get("prior_exit_reason_codes") or row.get("previous_exit_reason_codes") or row.get("source_pm_reason_codes") or row.get("reason_codes")
            campaign_id = str(row.get("position_campaign_id") or row.get("campaign_id") or state.get("campaign_id") or f"ledger-derived-{symbol}-{index}").strip()
            pm_context = dict(
                pm_exit_evidence_by_campaign.get(campaign_id)
                or pm_exit_evidence_by_source_id.get(str(row.get("source_pm_decision_id") or "").strip())
                or pm_exit_evidence_by_source_id.get(str(row.get("source_decision_id") or "").strip())
                or {}
            )
            if pm_context:
                campaign_id = str(pm_context.get("prior_campaign_id") or campaign_id).strip()
            prior_exit_reason_codes = (
                list(pm_context.get("prior_exit_reason_codes") or [])
                if pm_context
                else reason_codes
                if isinstance(reason_codes, list)
                else []
            )
            prior_exit_reason = _semantic_prior_exit_reason(
                pm_context.get("prior_exit_reason"),
                row.get("prior_exit_reason"),
                row.get("previous_exit_reason"),
                row.get("source_decision_reason"),
                prior_exit_reason_codes,
                row.get("source_decision_type"),
                row.get("decision_type"),
                row.get("source_decision"),
            )
            source_pm_decision_id = str(pm_context.get("source_pm_decision_id") or row.get("source_pm_decision_id") or "")
            source_decision_id = str(row.get("source_decision_id") or pm_context.get("source_decision_id") or "")
            prior_exit_context = dict(pm_context) if pm_context else {}
            if prior_exit_context:
                prior_exit_context["source_pm_decision_id"] = source_pm_decision_id
                prior_exit_context["source_decision_id"] = source_decision_id
                prior_exit_context["prior_exit_reason"] = prior_exit_reason
                prior_exit_context["prior_exit_reason_codes"] = prior_exit_reason_codes
                prior_exit_context["previous_exit_reason"] = prior_exit_reason
                prior_exit_context["previous_exit_reason_codes"] = prior_exit_reason_codes
            latest_closed[symbol] = {
                "prior_exit_business_date": execution_date,
                "prior_exit_campaign_id": campaign_id,
                "prior_campaign_id": campaign_id,
                "prior_exit_decision_type": str(pm_context.get("prior_exit_decision_type") or "EXIT"),
                "prior_exit_reason": prior_exit_reason,
                "prior_exit_reason_codes": prior_exit_reason_codes,
                "previous_exit_reason": prior_exit_reason,
                "previous_exit_reason_codes": prior_exit_reason_codes,
                "source_pm_decision_id": source_pm_decision_id,
                "source_decision_id": source_decision_id,
                "prior_same_symbol_exit_count": closed_count,
                "prior_exit_state_status": "RESOLVED_FROM_STRICT_PRIOR_PM_EXIT_CONTEXT_AND_PIT_LEDGER"
                if pm_context
                else "RESOLVED_FROM_PIT_LEDGER_EXECUTION_HISTORY",
                "prior_exit_provenance_status": "PASS" if pm_context else "REVIEW_REQUIRED",
                "prior_exit_context": prior_exit_context
                if pm_context
                else {
                    "schema_version": "phase32_h_prior_exit_context.v1",
                    "prior_campaign_id": campaign_id,
                    "prior_exit_business_date": execution_date,
                    "prior_exit_decision_type": "EXIT",
                    "prior_exit_reason": prior_exit_reason,
                    "prior_exit_reason_codes": prior_exit_reason_codes,
                    "previous_exit_reason": prior_exit_reason,
                    "previous_exit_reason_codes": prior_exit_reason_codes,
                    "source_pm_decision_id": "",
                    "source_decision_id": str(row.get("source_decision_id") or ""),
                    "provenance_status": "REVIEW_REQUIRED",
                    "authority": "PIT_LEDGER_EXECUTION_HISTORY_WITHOUT_PM_EXIT_DETAIL",
                    "future_information_used": False,
                },
            }
    return latest_closed


def _pm_exit_evidence_by_source_id(
    pm_exit_evidence_by_campaign: Mapping[str, Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    by_source_id: dict[str, Mapping[str, Any]] = {}
    for event in pm_exit_evidence_by_campaign.values():
        for field in ("source_pm_decision_id", "source_decision_id"):
            source_id = str(event.get(field) or "").strip()
            if source_id:
                by_source_id[source_id] = event
    return by_source_id


def _attach_prior_exit_to_summary(
    summary: Mapping[str, Any],
    *,
    prior_by_symbol: Mapping[str, Mapping[str, Any]],
    current_symbols: set[str],
) -> dict[str, Any]:
    payload = _payload_from_summary_item(summary)
    source_rows = summary.get("rows") or payload.get("rankings") or payload.get("decisions") or payload.get("positions") or ()
    enriched_rows: list[dict[str, Any]] = []
    supplied_symbols: list[str] = []
    for row in source_rows:
        item = dict(row) if isinstance(row, Mapping) else {}
        symbol = str(item.get("code") or item.get("security_code") or item.get("symbol") or "").strip()
        prior = prior_by_symbol.get(symbol)
        if symbol and symbol not in current_symbols and prior and _should_attach_prior_exit_context(item, prior):
            item.update(prior)
            supplied_symbols.append(symbol)
        enriched_rows.append(item)
    enriched_payload = {**payload}
    if "rankings" in enriched_payload:
        enriched_payload["rankings"] = enriched_rows
    elif "decisions" in enriched_payload:
        enriched_payload["decisions"] = enriched_rows
    elif "positions" in enriched_payload:
        enriched_payload["positions"] = enriched_rows
    return {
        "summary": {**dict(summary), "payload": enriched_payload, "rows": tuple(enriched_rows)},
        "supplied_count": len(supplied_symbols),
        "supplied_symbols": supplied_symbols,
    }


def _has_prior_exit_field(row: Mapping[str, Any]) -> bool:
    for field in ("prior_exit_business_date", "last_exit_business_date", "previous_exit_business_date"):
        if str(row.get(field) or "").strip():
            return True
    return False


def _prior_exit_business_date(row: Mapping[str, Any]) -> str:
    return str(
        row.get("prior_exit_business_date")
        or row.get("last_exit_business_date")
        or row.get("previous_exit_business_date")
        or ""
    ).strip()


def _has_complete_prior_exit_context(row: Mapping[str, Any]) -> bool:
    context = row.get("prior_exit_context") if isinstance(row.get("prior_exit_context"), Mapping) else {}
    prior_campaign_id = str(
        (context or {}).get("prior_campaign_id")
        or row.get("prior_campaign_id")
        or row.get("prior_exit_campaign_id")
        or ""
    ).strip()
    source_pm_decision_id = str(
        (context or {}).get("source_pm_decision_id")
        or row.get("source_pm_decision_id")
        or ""
    ).strip()
    source_decision_id = str(
        (context or {}).get("source_decision_id")
        or row.get("source_decision_id")
        or ""
    ).strip()
    provenance_status = str(
        row.get("prior_exit_provenance_status")
        or (context or {}).get("provenance_status")
        or ""
    ).strip().upper()
    return bool(prior_campaign_id and source_pm_decision_id and source_decision_id and provenance_status == "PASS")


def _should_attach_prior_exit_context(row: Mapping[str, Any], prior: Mapping[str, Any]) -> bool:
    if not _has_prior_exit_field(row):
        return True
    if _has_complete_prior_exit_context(row):
        return False
    existing_date = _prior_exit_business_date(row)
    prior_date = _prior_exit_business_date(prior)
    return bool(existing_date and prior_date and existing_date == prior_date)


def _supply_reentry_source_evidence(
    *,
    business_date: str,
    opportunity: Mapping[str, Any],
    technical_features: Mapping[str, Any],
    corporate_event_path: Path,
) -> dict[str, Any]:
    payload = _payload_from_summary_item(opportunity)
    source_rows = opportunity.get("rows") or payload.get("rankings") or ()
    technical_by_symbol = {
        str(row.get("code") or row.get("security_code") or row.get("symbol") or "").strip(): row
        for row in technical_features.get("rows") or ()
        if isinstance(row, Mapping)
        and str(row.get("code") or row.get("security_code") or row.get("symbol") or "").strip()
        and str(row.get("business_date") or row.get("target_date") or row.get("feature_date") or "") <= business_date
    }
    corporate_payload = _read_json(corporate_event_path) if corporate_event_path.is_file() else {}
    corporate_business_date = str(corporate_payload.get("business_date") or "")
    corporate_source_valid = bool(corporate_payload) and corporate_business_date == business_date
    known_no_event = set(str(item) for item in corporate_payload.get("known_no_event_symbols") or ()) if corporate_source_valid else set()
    known_event = set(str(item) for item in corporate_payload.get("known_event_symbols") or ()) if corporate_source_valid else set()
    event_status_by_symbol = _corporate_event_status_by_symbol(corporate_payload) if corporate_source_valid else {}

    enriched_rows: list[dict[str, Any]] = []
    technical_supplied = 0
    ca_no_event_supplied = 0
    ca_event_supplied = 0
    for row in source_rows:
        item = dict(row) if isinstance(row, Mapping) else {}
        symbol = str(item.get("code") or item.get("security_code") or item.get("symbol") or "").strip()
        technical = technical_by_symbol.get(symbol)
        if technical:
            for field in (
                "trend_close_over_ma_20d",
                "price_momentum_return_20d",
                "reference_price",
                "minimum_tick",
                "single_tick_pct",
                "minimum_tick_authority",
                "minimum_tick_authority_status",
                "minimum_tick_authority_hash",
                "minimum_tick_authority_source",
                "minimum_tick_resolution",
                "tick_quantization_status",
                "tick_normalized_trend_state",
                "momentum_confidence_state",
                "close_level_diversity_state",
                "candidate_rank_tick_reliability",
                "trend_robustness_authority",
                "momentum_confidence_authority",
                "tick_quantization_reason_codes",
                "close_level_count_20d",
                "ticks_traversed_20d",
                "net_tick_move_20d",
                "directional_tick_persistence_20d",
                "rolling_median_traded_value_20",
                "rolling_median_traded_value_20_authority",
                "rolling_median_traded_value_20_resolution",
            ):
                if item.get(field) in (None, "") and technical.get(field) not in (None, ""):
                    item[field] = technical.get(field)
            item.setdefault("technical_recovery_source", str(technical_features.get("source_ref") or "technical_features"))
            item.setdefault("technical_recovery_source_status", str(technical.get("coverage_status") or technical_features.get("status") or "UNKNOWN"))
            technical_supplied += 1
        if symbol and not any(str(item.get(field) or "").strip() for field in ("corporate_action_status", "corporate_event_status", "corporate_action_blocking_status", "corporate_event_blocking_status")):
            if symbol in known_no_event:
                item["corporate_action_status"] = "NO_EVENT"
                item["corporate_action_source_status"] = "PASS"
                item["corporate_action_source"] = "corporate_event.known_no_event_symbols"
                ca_no_event_supplied += 1
            elif symbol in known_event:
                item["corporate_action_status"] = event_status_by_symbol.get(symbol, "EVENT_PRESENT")
                item["corporate_action_source_status"] = "PASS"
                item["corporate_action_source"] = "corporate_event.known_event_symbols"
                ca_event_supplied += 1
            elif corporate_source_valid:
                item["corporate_action_source_status"] = "SOURCE_PRESENT_SYMBOL_STATUS_UNKNOWN"
                item["corporate_action_source"] = "corporate_event"
            else:
                item["corporate_action_source_status"] = "SOURCE_MISSING"
                item["corporate_action_source"] = str(corporate_event_path)
        enriched_rows.append(item)

    enriched_payload = {**payload}
    if "rankings" in enriched_payload:
        enriched_payload["rankings"] = enriched_rows
    evidence = {
        "schema_version": "phase29_l21r_reentry_source_evidence_wiring.v1",
        "business_date": business_date,
        "technical_source_path": str(technical_features.get("source_ref") or ""),
        "technical_source_hash": str(technical_features.get("source_hash") or ""),
        "technical_supplied_count": technical_supplied,
        "corporate_event_source_path": str(corporate_event_path),
        "corporate_event_source_hash": _file_hash(corporate_event_path),
        "corporate_event_business_date": corporate_business_date,
        "corporate_event_source_valid": corporate_source_valid,
        "corporate_no_event_supplied_count": ca_no_event_supplied,
        "corporate_event_supplied_count": ca_event_supplied,
        "future_source_used": False,
    }
    return {"opportunity": {**dict(opportunity), "payload": enriched_payload, "rows": tuple(enriched_rows)}, "evidence": evidence}


def _corporate_event_status_by_symbol(payload: Mapping[str, Any]) -> dict[str, str]:
    status_by_symbol: dict[str, str] = {}
    for event in payload.get("events") or ():
        if not isinstance(event, Mapping):
            continue
        symbol = str(event.get("security_code") or event.get("code") or event.get("symbol") or "").strip()
        if not symbol:
            continue
        raw_status = str(event.get("event_status") or event.get("blocking_status") or event.get("status") or "EVENT_PRESENT").upper()
        if raw_status in {"PASS", "RESOLVED", "NO_BLOCKING_EVENT", "NO_EVENT"}:
            status_by_symbol[symbol] = raw_status
        else:
            status_by_symbol[symbol] = "EVENT_PRESENT"
    return status_by_symbol


def _supply_add_expected_edge_baseline(
    *,
    run_dir: Path,
    business_date: str,
    opportunity: Mapping[str, Any],
    current: Mapping[str, Any],
    position_management: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    campaign_artifact_path = run_dir / "daily" / business_date / "positions" / "position_campaigns.json"
    current_campaign_by_symbol = _open_campaign_ids_by_symbol(_read_json(campaign_artifact_path))
    baseline_by_symbol: dict[str, dict[str, Any]] = {}
    daily_root = run_dir / "daily"
    for path in sorted(daily_root.glob("*/strategy/portfolio_construction.json")):
        day = path.parent.parent.name
        if day >= business_date:
            continue
        payload = _read_json(path)
        for member in payload.get("portfolio_members") or ():
            if not isinstance(member, Mapping) or not member.get("current_position"):
                continue
            symbol = str(member.get("security_code") or member.get("symbol") or "").strip()
            active_campaign = current_campaign_by_symbol.get(symbol, "")
            if not symbol or not active_campaign:
                continue
            member_campaign = str(
                member.get("current_position_campaign_id")
                or member.get("position_campaign_id")
                or member.get("campaign_id")
                or member.get("position_management_reference")
                or member.get("current_position_reference")
                or ""
            ).strip()
            if member_campaign and member_campaign != active_campaign:
                continue
            if not member_campaign:
                continue
            score = member.get("runtime_opportunity_score")
            if isinstance(score, bool) or not isinstance(score, (int, float)):
                continue
            baseline_by_symbol[symbol] = {
                "score": float(score),
                "business_date": day,
                "campaign_id": active_campaign,
                "artifact_path": str(path),
                "artifact_hash": _file_hash(path),
            }
    payload = _payload_from_summary_item(opportunity)
    source_rows = opportunity.get("rows") or payload.get("rankings") or payload.get("decisions") or ()
    enriched_rows: list[dict[str, Any]] = []
    supplied = 0
    missing = 0
    for row in source_rows:
        item = dict(row) if isinstance(row, Mapping) else {}
        symbol = str(item.get("code") or item.get("security_code") or item.get("symbol") or "").strip()
        campaign_id = current_campaign_by_symbol.get(symbol, "")
        if campaign_id:
            item.setdefault("position_campaign_id", campaign_id)
        baseline = baseline_by_symbol.get(symbol)
        if baseline:
            item["expected_edge_baseline_score"] = baseline["score"]
            item["expected_edge_baseline_business_date"] = baseline["business_date"]
            item["expected_edge_baseline_campaign_id"] = baseline["campaign_id"]
            item["expected_edge_baseline_type"] = "latest_prior_same_campaign_strategy_evidence"
            item["add_baseline_source_artifact_path"] = baseline["artifact_path"]
            item["add_baseline_source_artifact_hash"] = baseline["artifact_hash"]
            supplied += 1
        elif campaign_id:
            missing += 1
        enriched_rows.append(item)
    enriched_payload = {**payload}
    if "rankings" in enriched_payload:
        enriched_payload["rankings"] = enriched_rows
    elif "decisions" in enriched_payload:
        enriched_payload["decisions"] = enriched_rows
    evidence = {
        "schema_version": "phase28_d55_c_add_baseline_supply_evidence.v1",
        "business_date": business_date,
        "baseline_producer": "latest_prior_same_campaign_strategy_portfolio_construction",
        "baseline_artifact": "daily/<prior_business_date>/strategy/portfolio_construction.json",
        "baseline_field_path": "portfolio_members[].runtime_opportunity_score",
        "campaign_identity_field": "position_campaign_id",
        "campaign_identity_authority": "positions/position_campaigns.json",
        "campaign_identity_authority_path": str(campaign_artifact_path),
        "campaign_identity_authority_hash": _file_hash(campaign_artifact_path),
        "temporal_selection_rule": "latest prior business_date strictly less than current business_date",
        "supplied_count": supplied,
        "missing_count": missing,
        "current_campaign_count": len(current_campaign_by_symbol),
        "future_baseline_used": False,
        "symbol_only_baseline_used": False,
        "missing_baseline_behavior": "UNKNOWN_FAIL_CLOSED",
    }
    return {
        "opportunity": {**dict(opportunity), "payload": enriched_payload, "rows": tuple(enriched_rows)},
        "evidence": evidence,
    }


def _open_campaign_ids_by_symbol(payload: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    campaigns = payload.get("position_campaigns") if isinstance(payload.get("position_campaigns"), list) else []
    for row in campaigns:
        if not isinstance(row, Mapping):
            continue
        symbol = str(row.get("symbol") or row.get("security_code") or row.get("code") or "").strip()
        campaign_id = str(row.get("position_campaign_id") or "").strip()
        status = str(row.get("campaign_status") or "").upper()
        quantity = _float(row.get("current_quantity"), default=0.0)
        if symbol and campaign_id and (status == "OPEN" or quantity > 0):
            result[symbol] = campaign_id
    return result


def _produce_lot_aware_final_portfolio_construction(
    *,
    business_date: str,
    draft_path: Path,
    preflight_path: Path,
    output_path: Path,
) -> Any:
    draft = _read_json(draft_path)
    preflight = _read_json(preflight_path)
    reallocation = portfolio_construction.apply_lot_aware_final_reallocation(
        members=[dict(row) for row in draft.get("portfolio_members") or []],
        lot_feasibility_rows=[dict(row) for row in preflight.get("lot_feasibility_preflight") or []],
        target_gross_exposure=draft.get("target_gross_exposure"),
        single_name_cap=draft.get("single_name_weight_cap"),
        business_date=business_date,
        incremental_budget_evidence=draft.get("incremental_budget_reconciliation"),
        final_capital_competition_risk_pacing_evidence=(
            draft.get("portfolio_policy_allocation_authority", {}).get("risk_pacing_evidence")
            if isinstance(draft.get("portfolio_policy_allocation_authority"), Mapping)
            else {}
        ),
    )
    final_payload = {
        **draft,
        "portfolio_construction_stage": "FINAL_LOT_AWARE_REALLOCATION",
        "portfolio_construction_draft_artifact_path": str(draft_path),
        "position_sizing_preflight_artifact_path": str(preflight_path),
        "portfolio_members": reallocation["members"],
        "total_target_weight": round(sum(float(row.get("target_weight") or 0.0) for row in reallocation["members"]), 6),
        "lot_aware_final_reallocation": reallocation["evidence"],
        "reason_codes": sorted(set([*list(draft.get("reason_codes") or []), *reallocation["reason_codes"]])),
    }
    final_payload = portfolio_construction.promote_final_portfolio_construction_for_production(final_payload)
    portfolio_construction.validate_portfolio_construction_artifact(final_payload)
    artifact_hash = portfolio_construction.portfolio_construction_hash(final_payload)
    final_payload = {**final_payload, "artifact_hash": artifact_hash}
    _write_json(output_path, final_payload)
    return _SimpleProducerResult(
        status=str(final_payload.get("producer_result_status") or "PASS"),
        reason=",".join(final_payload.get("reason_codes") or []),
        artifact_path=str(output_path),
        artifact_hash=artifact_hash,
    )


class _SimpleProducerResult:
    def __init__(self, *, status: str, reason: str, artifact_path: str, artifact_hash: str) -> None:
        self.status = status
        self.reason = reason
        self.artifact_path = artifact_path
        self.artifact_hash = artifact_hash


def _cash_summary(*, runtime_root: Path, business_date: str) -> dict[str, Any]:
    current = _current_summary(runtime_root=runtime_root, business_date=business_date)
    total = _float(current["summary"].get("portfolio_total_equity", 0.0))
    cash = _float(current["summary"].get("cash", 0.0))
    return {**current, "summary": {"cash": cash, "buying_power": current["summary"].get("buying_power", 0.0), "current_cash": cash, "current_cash_ratio": round(cash / total, 6) if total > 0 else 0.0, "portfolio_total_equity": total}}


def _exposure_summary(*, runtime_root: Path, business_date: str) -> dict[str, Any]:
    current = _current_summary(runtime_root=runtime_root, business_date=business_date)
    positions = current["summary"].get("positions") or []
    exposure = sum(float(row.get("market_value") or row.get("value") or 0.0) for row in positions if isinstance(row, Mapping))
    total = _float(current["summary"].get("portfolio_total_equity", 0.0))
    return {**current, "summary": {"gross_exposure": exposure, "current_market_value": exposure, "current_gross_exposure_ratio": round(exposure / total, 6) if total > 0 else 0.0, "position_count": len(positions), "portfolio_total_equity": total}}


def _pending_summary(*, runtime_root: Path, business_date: str) -> dict[str, Any]:
    path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    payload = _read_json(path) if path.is_file() else {}
    items = payload.get("items") or payload.get("orders") or []
    rows = tuple(row for row in items if isinstance(row, Mapping))
    reserved_cash = sum(_float(row.get("cash_required", row.get("target_notional", row.get("notional", 0.0)))) for row in rows)
    return {"status": "PASS" if path.is_file() else "MISSING", "business_date": business_date, "feature_date": business_date, "source_ref": str(path), "source_hash": _file_hash(path), "summary": {"pending_count": len(items) if isinstance(items, list) else 0, "state": payload.get("state", ""), "pending_reserved_cash": reserved_cash, "pending_reserved_exposure": reserved_cash, "reservation_status": "PASS"}, "rows": rows}


def _safety_summary() -> dict[str, Any]:
    path = Path("configs/safety/portfolio_limits.json")
    limits = _load_optional(lambda: load_portfolio_safety_limits(path, legacy_active_max_positions=5))
    return {
        "status": "PASS" if limits else "MISSING",
        "business_date": "",
        "feature_date": "",
        "source_ref": str(path),
        "source_hash": _file_hash(path),
        "summary": limits.to_contract_payload() if limits else {},
    }


def _resolve_strategy_source_authority(
    *,
    run_dir: Path,
    runtime_root: Path,
    business_date: str,
    operations_root: Path,
) -> dict[str, Any]:
    default_paths = {
        "normalized_ohlcv": operations_root / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet",
        "raw_ohlcv": operations_root / "jquants" / "raw" / "jquants" / "equities_bars_daily" / "data.parquet",
        "listed_issues": operations_root / "jquants" / "raw" / "jquants" / "listed_issues" / "data.parquet",
        "trading_calendar": operations_root / "jquants" / "raw" / "jquants" / "trading_calendar" / "data.parquet",
        "earnings_schedule": operations_root / "jquants" / "raw" / "jquants" / "earnings_calendar" / "data.parquet",
        "financial_statements": operations_root / "jquants" / "raw" / "jquants" / "fins_summary" / "data.parquet",
        "corporate_actions": operations_root / "jquants" / "raw" / "jquants" / "corporate_actions" / "data.parquet",
    }
    asof_path = run_dir / "daily" / business_date / "market_refresh" / "historical_asof_view.json"
    manifest_path = asof_path.parent / "inputs" / "historical_asof" / business_date / "logical_input_manifest.json"
    if not asof_path.is_file() and not manifest_path.is_file():
        return _strategy_source_authority_payload(
            business_date=business_date,
            authority="operations_canonical_source_authority",
            resolution_source="operations_default",
            manifest_path=manifest_path,
            paths=default_paths,
            source_identities={},
            run_scoped=False,
            status="PASS",
            reason="operations_default_source_authority",
        )
    if not manifest_path.is_file():
        missing = _missing_strategy_source_paths(manifest_path)
        return _strategy_source_authority_payload(
            business_date=business_date,
            authority="historical_asof_source_authority",
            resolution_source="missing_historical_logical_input_manifest",
            manifest_path=manifest_path,
            paths=missing,
            source_identities={},
            run_scoped=True,
            status="BLOCK",
            reason="historical_logical_input_manifest_missing",
        )
    manifest = _read_json(manifest_path)
    logical_paths = manifest.get("logical_paths") if isinstance(manifest.get("logical_paths"), dict) else {}
    source_identities = manifest.get("source_identities") if isinstance(manifest.get("source_identities"), dict) else {}
    if str(manifest.get("business_date") or "") != business_date or str(manifest.get("status") or "") != "PASS":
        missing = _missing_strategy_source_paths(manifest_path)
        return _strategy_source_authority_payload(
            business_date=business_date,
            authority="historical_asof_source_authority",
            resolution_source="invalid_historical_logical_input_manifest",
            manifest_path=manifest_path,
            paths=missing,
            source_identities=source_identities,
            run_scoped=True,
            status="BLOCK",
            reason="historical_logical_input_manifest_invalid",
        )
    paths = {
        "normalized_ohlcv": Path(str(logical_paths.get("normalized_ohlcv") or "")),
        "raw_ohlcv": Path(str(logical_paths.get("raw_ohlcv") or "")),
        "listed_issues": Path(str(logical_paths.get("listed_issues") or "")),
        "trading_calendar": Path(str(logical_paths.get("trading_calendar") or "")),
        # These roles are not authorized by current historical_asof manifests.
        # Keep them empty so Historical never falls back to operations latest.
        "earnings_schedule": Path(),
        "financial_statements": Path(),
        "corporate_actions": Path(),
    }
    return _strategy_source_authority_payload(
        business_date=business_date,
        authority="historical_asof_source_authority",
        resolution_source="run_scoped_historical_logical_input_manifest",
        manifest_path=manifest_path,
        paths=paths,
        source_identities=source_identities,
        run_scoped=True,
        status="PASS",
        reason="historical_asof_strategy_sources_resolved",
    )


def _strategy_source_authority_payload(
    *,
    business_date: str,
    authority: str,
    resolution_source: str,
    manifest_path: Path,
    paths: Mapping[str, Path],
    source_identities: Mapping[str, Any],
    run_scoped: bool,
    status: str,
    reason: str,
) -> dict[str, Any]:
    expected_hashes: dict[str, str] = {}
    role_map = {
        "normalized_ohlcv": "jquants_daily_quotes",
        "listed_issues": "jquants_listed_issues",
        "trading_calendar": "jquants_trading_calendar",
        "earnings_schedule": "jquants_earnings_schedule",
        "financial_statements": "jquants_financial_statements",
        "corporate_actions": "jquants_corporate_actions",
    }
    for logical_id, producer_role in role_map.items():
        identity = source_identities.get(logical_id) if isinstance(source_identities, Mapping) else None
        if isinstance(identity, Mapping):
            expected = str(identity.get("physical_file_hash") or "")
            if expected:
                expected_hashes[producer_role] = expected
    resolved_paths = {key: str(path) for key, path in paths.items()}
    source_records = {}
    for key, path in paths.items():
        exists = bool(str(path)) and path.is_file()
        source_records[key] = {
            "path": str(path),
            "exists": exists,
            "sha256": _file_hash(path) if exists else "",
            "expected_sha256": expected_hashes.get(role_map.get(key, ""), ""),
            "business_date": business_date,
            "pit_status": "PASS" if exists else "MISSING",
        }
    return {
        "schema_version": "phase23_bm_strategy_source_authority.v1",
        "status": status,
        "reason": reason,
        "authority": authority,
        "business_date": business_date,
        "resolution_source": resolution_source,
        "source_manifest_path": str(manifest_path),
        "source_manifest_hash": _file_hash(manifest_path) if manifest_path.is_file() else "",
        "run_scoped_historical_authority_used": run_scoped and status == "PASS",
        "operations_latest_fallback_used": False if run_scoped else False,
        "paths": resolved_paths,
        "source_records": source_records,
        "expected_hashes": expected_hashes,
    }


def _missing_strategy_source_paths(manifest_path: Path) -> dict[str, Path]:
    root = manifest_path.parent / "__missing_historical_strategy_source_authority__"
    return {
        "normalized_ohlcv": root / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet",
        "raw_ohlcv": root / "raw" / "jquants" / "equities_bars_daily" / "data.parquet",
        "listed_issues": root / "raw" / "jquants" / "listed_issues" / "data.parquet",
        "trading_calendar": root / "raw" / "jquants" / "trading_calendar" / "data.parquet",
        "earnings_schedule": Path(),
        "financial_statements": Path(),
        "corporate_actions": Path(),
    }


def _optional_path(value: Any) -> Path | None:
    text = str(value or "")
    return Path(text) if text else None


def _pp_summary(item: Mapping[str, Any], business_date: str) -> portfolio_policy.PortfolioPolicyInputSummary:
    return portfolio_policy.PortfolioPolicyInputSummary(status=str(item.get("status") or "MISSING"), business_date=str(item.get("business_date") or business_date), feature_date=str(item.get("feature_date") or business_date), summary=dict(item.get("summary") or {}), source_ref=str(item.get("source_ref") or ""), source_hash=str(item.get("source_hash") or ""))


def _pc_summary(item: Mapping[str, Any], business_date: str) -> portfolio_construction.PortfolioConstructionSourceSummary:
    kw = _summary_kwargs(item, business_date)
    payload = _payload_from_summary_item(item)
    rows = item.get("rows") or payload.get("portfolio_members") or payload.get("decisions") or payload.get("rankings") or payload.get("positions") or ()
    return portfolio_construction.PortfolioConstructionSourceSummary(**kw, rows=tuple(rows))


def _bq_summary(item: Mapping[str, Any], business_date: str) -> buy_quality.BuyQualitySourceSummary:
    kw = _summary_kwargs(item, business_date)
    payload = _payload_from_summary_item(item)
    rows = item.get("rows") or payload.get("decisions") or payload.get("rankings") or payload.get("positions") or ()
    return buy_quality.BuyQualitySourceSummary(**kw, rows=tuple(rows))


def _ps_summary(item: Mapping[str, Any], business_date: str) -> position_sizing.PositionSizingSourceSummary:
    kw = _summary_kwargs(item, business_date)
    payload = _payload_from_summary_item(item)
    rows = item.get("rows") or payload.get("portfolio_members") or payload.get("positions") or payload.get("members") or ()
    return position_sizing.PositionSizingSourceSummary(**kw, rows=tuple(rows))


def _pm_summary(item: Mapping[str, Any], business_date: str) -> position_management.PMSourceSummary:
    return position_management.PMSourceSummary(**_summary_kwargs(item, business_date))


def _rp_summary(item: Mapping[str, Any], business_date: str) -> runtime_planning.RuntimePlanningSourceSummary:
    kw = _summary_kwargs(item, business_date)
    return runtime_planning.RuntimePlanningSourceSummary(**kw, rows=tuple(item.get("rows") or ()))


def _summary_kwargs(item: Mapping[str, Any], business_date: str) -> dict[str, Any]:
    payload = _payload_from_summary_item(item)
    summary = dict(item.get("summary") or {})
    if not summary and payload:
        summary = dict(payload)
    if payload:
        summary = _preserve_opportunity_score_semantic_metadata(summary, payload)
    return {
        "status": str(item.get("status") or "MISSING"),
        "business_date": str(item.get("business_date") or payload.get("business_date") or business_date),
        "feature_date": str(item.get("feature_date") or payload.get("feature_date") or business_date),
        "source_ref": str(item.get("source_ref") or item.get("artifact_path") or ""),
        "source_hash": str(item.get("source_hash") or item.get("artifact_hash") or ""),
        "summary": summary,
    }


def _opportunity_score_semantic_metadata(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        field: payload[field]
        for field in OPPORTUNITY_SCORE_SEMANTIC_METADATA_FIELDS
        if field in payload
    }


def _preserve_opportunity_score_semantic_metadata(summary: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(summary)
    for field, value in _opportunity_score_semantic_metadata(payload).items():
        if field not in merged:
            merged[field] = value
    return merged


def _payload_from_summary_item(item: Mapping[str, Any]) -> dict[str, Any]:
    payload = item.get("payload")
    if isinstance(payload, Mapping):
        return dict(payload)
    path = Path(str(item.get("artifact_path") or item.get("source_ref") or ""))
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _existing_pm_decisions(*, runtime_root: Path, business_date: str) -> list[dict[str, Any]]:
    candidates = [
        runtime_root / "runtime_state" / "sell_pipeline" / business_date / "position_management_decisions.json",
        runtime_root / "runtime_state" / "position_management" / business_date / "position_management_decisions.json",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        payload = _read_json(path)
        rows = payload if isinstance(payload, list) else payload.get("decisions") or payload.get("positions") or []
        if isinstance(rows, list):
            source_hash = _file_hash(path)
            result: list[dict[str, Any]] = []
            for row in rows:
                if not isinstance(row, Mapping):
                    continue
                item = dict(row)
                item["_source_artifact_path"] = str(path)
                item["_source_artifact_hash"] = source_hash
                item["_source_business_date"] = str(payload.get("business_date") or business_date) if isinstance(payload, Mapping) else business_date
                result.append(item)
            return result
    return []


def _runtime_current_position_rows(current: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = current.get("rows") if isinstance(current, Mapping) else []
    if not isinstance(rows, (list, tuple)):
        return []
    result: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        symbol = str(row.get("symbol") or row.get("security_code") or row.get("code") or row.get("issue_code") or "").strip()
        if not symbol:
            continue
        quantity = _float(row.get("quantity"), default=0.0)
        if quantity <= 0:
            continue
        result.append(
            {
                "position_id": str(row.get("position_id") or row.get("current_position_reference") or f"runtime-current-{symbol}"),
                "symbol": symbol,
                "quantity": quantity,
                "average_price": _float(row.get("average_price"), default=0.0),
                "acquired_at": str(row.get("acquired_at") or row.get("opened_at") or ""),
                "as_of": str(row.get("as_of") or current.get("business_date") or ""),
                "position_state_as_of": str(row.get("position_state_as_of") or row.get("as_of") or current.get("business_date") or ""),
                "valuation_as_of": str(row.get("valuation_as_of") or row.get("valuation_date") or row.get("as_of") or current.get("business_date") or ""),
                "position_lifecycle_id": str(row.get("position_lifecycle_id") or row.get("source_execution_id") or row.get("position_id") or ""),
                "technical_features_join_key": {"code": symbol, "target_date": str(current.get("business_date") or "")},
                "source": "runtime_current_position_adapter_input",
            }
        )
    return result


def _legacy_shadow_comparison(results: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "strategy_legacy_shadow_comparison.v1",
        "legacy_runtime_authority_active": True,
        "runtime_behavior_changed": False,
        "active_runtime_decision_changed": False,
        "runtime_switch_performed": False,
        "strategy_shadow_components": dict(results),
    }


def _normalize_feature_date_authority(
    *,
    business_date: str,
    planned_feature_date: str,
    feature_date_authority: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if isinstance(feature_date_authority, Mapping) and feature_date_authority:
        selected = str(feature_date_authority.get("selected_feature_date") or planned_feature_date or business_date)
        planned = str(feature_date_authority.get("planned_feature_date") or planned_feature_date or "")
        materialized = str(feature_date_authority.get("materialized_feature_date") or selected)
        return {
            "schema_version": "runtime_test_strategy_shadow_feature_date_authority_v1",
            **dict(feature_date_authority),
            "business_date": str(feature_date_authority.get("business_date") or business_date),
            "planned_feature_date": planned,
            "materialized_feature_date": materialized,
            "selected_feature_date": selected,
            "feature_date_authority_source": str(feature_date_authority.get("feature_date_authority_source") or "provided_strategy_shadow_feature_date_authority"),
            "planned_matches_materialized": bool(feature_date_authority.get("planned_matches_materialized", (not planned) or planned == materialized)),
            "feature_date_contract_path": str(feature_date_authority.get("feature_date_contract_path") or ""),
            "authority_status": str(feature_date_authority.get("authority_status") or "PASS"),
            "reason": str(feature_date_authority.get("reason") or "provided_strategy_shadow_feature_date_authority"),
        }
    selected = planned_feature_date or business_date
    return {
        "schema_version": "runtime_test_strategy_shadow_feature_date_authority_v1",
        "business_date": business_date,
        "planned_feature_date": planned_feature_date,
        "materialized_feature_date": "",
        "selected_feature_date": selected,
        "feature_date_authority_source": "legacy_direct_feature_date_argument",
        "planned_matches_materialized": False,
        "feature_date_contract_path": "",
        "authority_status": "REVIEW_REQUIRED",
        "reason": "strategy_shadow_feature_date_authority_not_supplied_by_runtime_test",
        "completed_runtime_job_resolutions": [],
    }


def _build_strategy_evidence_index(
    *,
    strategy_dir: Path,
    summary: Mapping[str, Any],
    input_manifest: Mapping[str, Any],
    source_payload: Mapping[str, Any],
) -> dict[str, Any]:
    def loc(path_name: str, pointer: str = "") -> dict[str, str]:
        return {"path": str(strategy_dir / path_name), "json_pointer": pointer}

    component_locations = {
        name: loc(filename, "")
        for name, filename in {
            **ARTIFACT_FILENAMES,
            "strategy_decision_trace": "strategy_decision_trace.json",
        }.items()
    }
    return {
        "schema_version": "strategy_shadow_evidence_index.v1",
        "business_date": str(summary.get("business_date") or input_manifest.get("business_date") or ""),
        "top_level_judgment": loc("strategy_shadow_summary.json", "/strategy_shadow_judgment"),
        "judgment_reasons": loc("strategy_shadow_summary.json", "/root_reason_codes"),
        "accepted_generation_resolution": loc("input_manifest.json", "/accepted_generation"),
        "feature_date_authority": loc("input_manifest.json", "/feature_date_authority"),
        "pit_validation": loc("source_manifest.json", "/pit_validation"),
        "schema_validation": loc("strategy_shadow_summary.json", "/artifacts"),
        "component_judgments": component_locations,
        "position_sizing_safety_authority": {
            "strategy_maximum_position_weight": loc("position_sizing.json", "/strategy_maximum_position_weight"),
            "strategy_maximum_position_weight_source": loc("position_sizing.json", "/strategy_maximum_position_weight_source"),
            "safety_maximum_position_weight": loc("position_sizing.json", "/safety_maximum_position_weight"),
            "safety_maximum_position_weight_source": loc("position_sizing.json", "/safety_maximum_position_weight_source"),
            "safety_authority_status": loc("position_sizing.json", "/safety_authority_status"),
            "effective_maximum_position_weight": loc("position_sizing.json", "/effective_maximum_position_weight"),
            "effective_maximum_position_weight_derivation": loc("position_sizing.json", "/effective_maximum_position_weight_derivation"),
            "explicit_zero_cap": loc("position_sizing.json", "/explicit_zero_cap"),
            "emergency_brake_active": loc("position_sizing.json", "/emergency_brake_active"),
            "market_context_risk_state": loc("position_sizing.json", "/market_context_risk_state"),
            "dynamic_position_count": loc("position_sizing.json", "/dynamic_position_count"),
            "dynamic_cash_exposure": loc("position_sizing.json", "/dynamic_cash_exposure"),
            "aggregate_exposure_cap": loc("position_sizing.json", "/aggregate_exposure_cap"),
        },
        "price_volatility_materialization": {
            "artifact_path": loc("input_manifest.json", "/strategy_input_sources/price_volatility/physical_path"),
            "source_path": loc("price_volatility.json", "/source_path"),
            "source_hash": loc("price_volatility.json", "/source_content_hash"),
            "producer_result": loc("price_volatility.json", "/producer_result_status"),
            "validation_status": loc("price_volatility.json", "/validation_status"),
            "coverage_status": loc("price_volatility.json", "/coverage_status"),
            "pit_status": loc("price_volatility.json", "/pit_validation/status"),
            "decision_resolution": loc("price_volatility.json", "/decision_resolution"),
        },
        "technical_features_materialization": {
            "artifact_path": loc("input_manifest.json", "/strategy_input_sources/technical_features/physical_path"),
            "source_path": loc("technical_features.json", "/source_path"),
            "source_hash": loc("technical_features.json", "/source_content_hash"),
            "producer_result": loc("technical_features.json", "/producer_result_status"),
            "validation_status": loc("technical_features.json", "/validation_status"),
            "coverage_status": loc("technical_features.json", "/coverage_status"),
            "pit_status": loc("technical_features.json", "/pit_validation/status"),
            "decision_resolution": loc("technical_features.json", "/decision_resolution"),
        },
        "portfolio_policy_config_authority": {
            "artifact_path": loc("input_manifest.json", "/strategy_input_sources/portfolio_policy_config/physical_path"),
            "source_path": loc("portfolio_policy.json", "/upstream_artifacts/policy_config/config_source"),
            "source_hash": loc("portfolio_policy.json", "/upstream_artifacts/policy_config_hash"),
            "producer_result": loc("portfolio_policy.json", "/producer_result_status"),
            "validation_status": loc("portfolio_policy.json", "/validation_status"),
            "coverage_status": loc("input_manifest.json", "/strategy_input_sources/portfolio_policy_config/coverage_status"),
            "pit_status": loc("input_manifest.json", "/strategy_input_sources/portfolio_policy_config/pit_status"),
            "decision_resolution": loc("portfolio_policy.json", "/decision_resolution"),
        },
        "status_contract_separation": {
            name: {
                "producer_result_status": loc(filename, "/producer_result_status"),
                "producer_calculation_completed": loc(filename, "/producer_calculation_completed"),
                "validation_status": loc(filename, "/validation_status"),
                "artifact_lifecycle_status": loc(filename, "/artifact_lifecycle_status"),
                "runtime_consumer_eligibility": loc(filename, "/runtime_consumer_eligibility"),
                "human_review_status": loc(filename, "/human_review_status"),
                "downstream_calculation_eligibility": loc(filename, "/downstream_calculation_eligibility"),
                "decision_resolution": loc(filename, "/decision_resolution"),
                "direct_reason_codes": loc(filename, "/direct_reason_codes"),
                "propagated_reason_codes": loc(filename, "/propagated_reason_codes"),
                "lifecycle_reason_codes": loc(filename, "/lifecycle_reason_codes"),
                "consumer_eligibility_reason_codes": loc(filename, "/consumer_eligibility_reason_codes"),
            }
            for name, filename in ARTIFACT_FILENAMES.items()
        },
        "runtime_mutation_result": loc("strategy_shadow_summary.json", "/runtime_mutation_performed"),
        "consumer_eligibility": loc("strategy_shadow_summary.json", "/shadow_consumer_eligibility"),
        "active_runtime_consumer_eligibility": loc("strategy_shadow_summary.json", "/active_runtime_consumer_eligibility"),
        "runtime_switch_result": loc("strategy_shadow_summary.json", "/runtime_switch_performed"),
        "source_manifest": loc("source_manifest.json", ""),
        "input_manifest": loc("input_manifest.json", ""),
        "source_manifest_hash": str(input_manifest.get("source_manifest_hash") or ""),
        "pit_validation_status": str((source_payload.get("pit_validation") or {}).get("status") if isinstance(source_payload.get("pit_validation"), Mapping) else ""),
        "runtime_switch_performed": bool(summary.get("runtime_switch_performed")),
        "runtime_mutation_performed": bool(summary.get("runtime_mutation_performed")),
    }


def _runtime_authority_hashes(runtime_root: Path) -> dict[str, str]:
    paths = {
        "pending": runtime_root / "pending_order_plan" / "pending_order_plan.json",
        "ledger_cash": runtime_root / "persistent_ledger" / "cash.jsonl",
        "ledger_orders": runtime_root / "persistent_ledger" / "orders.jsonl",
        "ledger_executions": runtime_root / "persistent_ledger" / "executions.jsonl",
        "ledger_positions": runtime_root / "persistent_ledger" / "positions.jsonl",
        "current": runtime_root / "persistent_ledger" / "state.json",
        "runtime_state": runtime_root / "runtime_state" / "current_state.json",
        "accepted_generation_pointer": runtime_root / "runtime_state" / "accepted_buy_ai_bundle.json",
        "registry_checkpoint": Path("artifact_registry/checkpoints/latest.json"),
    }
    return {name: _file_hash(path) for name, path in paths.items()}


def _config_hashes(root: Path) -> dict[str, str]:
    if not root.is_dir():
        return {}
    return {str(path): _file_hash(path) for path in sorted(root.glob("*.json"))}


def _planned_business_dates(run_dir: Path) -> list[str]:
    plan = _read_json(run_dir / "plan.json") if (run_dir / "plan.json").is_file() else {}
    return [str(day.get("business_date") or "") for day in plan.get("business_dates", []) if isinstance(day, Mapping)]


def _load_optional(func):
    try:
        return func()
    except Exception:
        return None


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if isinstance(value, bool):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{hashlib.sha256(str(path).encode()).hexdigest()[:8]}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _file_hash(path: Path) -> str:
    if not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _source_manifest_complete(payload: Mapping[str, Any]) -> bool:
    required = {
        "portfolio_state",
        "pending_state",
        "market_quotes",
        "benchmark",
        "sector",
        "corporate_event",
        "candidate",
        "opportunity",
        "bootstrap",
        "pit_validation",
        "hashes",
    }
    return payload.get("schema_version") == source_manifest.SOURCE_MANIFEST_SCHEMA_VERSION and required.issubset(set(payload.keys()))
