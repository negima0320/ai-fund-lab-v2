from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.runtime_v2.accepted_generation_resolver import resolve_accepted_generation
from ai_fund_lab_v2.runtime_v2.safety.portfolio_limits import load_portfolio_safety_limits
from ai_fund_lab_v2.strategy import capital_deployment
from ai_fund_lab_v2.strategy import corporate_event
from ai_fund_lab_v2.strategy import dynamic_cash_exposure
from ai_fund_lab_v2.strategy import dynamic_position_count
from ai_fund_lab_v2.strategy import input_materialization
from ai_fund_lab_v2.strategy import market_context
from ai_fund_lab_v2.strategy import portfolio_construction
from ai_fund_lab_v2.strategy import portfolio_policy
from ai_fund_lab_v2.strategy import position_management
from ai_fund_lab_v2.strategy import position_sizing
from ai_fund_lab_v2.strategy import runtime_planning
from ai_fund_lab_v2.strategy import source_manifest
from ai_fund_lab_v2.strategy.observability import produce_strategy_decision_trace


STRATEGY_SHADOW_MANIFEST_SCHEMA_VERSION = "strategy_shadow_input_manifest.v1"
STRATEGY_SHADOW_SUMMARY_SCHEMA_VERSION = "runtime_test_strategy_shadow_summary.v1"
STRATEGY_SHADOW_RUN_MANIFEST_SCHEMA_VERSION = "runtime_test_strategy_shadow_run_manifest.v1"
STRATEGY_SHADOW_RUN_SUMMARY_SCHEMA_VERSION = "runtime_test_strategy_shadow_run_summary.v1"

ARTIFACT_FILENAMES = {
    "market_context": "market_context.json",
    "corporate_event": "corporate_event.json",
    "portfolio_policy": "portfolio_policy.json",
    "dynamic_position_count": "dynamic_position_count.json",
    "dynamic_cash_exposure": "dynamic_cash_exposure.json",
    "portfolio_construction": "portfolio_construction.json",
    "position_sizing": "position_sizing.json",
    "position_management": "position_management.json",
    "capital_deployment": "capital_deployment.json",
    "runtime_planning": "runtime_planning.json",
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
        "failure_policy": "REVIEW_REQUIRED is recorded without halting active legacy Runtime; BLOCK is isolated to strategy_shadow_judgment unless mutation is detected",
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
) -> dict[str, Any]:
    strategy_dir = run_dir / "daily" / business_date / "strategy"
    strategy_dir.mkdir(parents=True, exist_ok=True)
    before = _runtime_authority_hashes(runtime_root)
    feature_authority = _normalize_feature_date_authority(
        business_date=business_date,
        planned_feature_date=feature_date,
        feature_date_authority=feature_date_authority,
    )
    manifest = _build_input_manifest(
        run_id=run_id,
        profile_id=profile_id,
        runtime_root=runtime_root,
        business_date=business_date,
        feature_date=str(feature_authority.get("selected_feature_date") or business_date),
        feature_date_authority=feature_authority,
    )
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

    operations_root = runtime_root / "operations"
    as_of = f"{business_date}T00:00:00+00:00"
    candidate = _ai_output_summary(runtime_root / "runtime_state" / "buy_ai" / business_date / "candidate_decisions.json", business_date=business_date)
    opportunity = _ai_output_summary(runtime_root / "runtime_state" / "buy_ai" / business_date / "opportunity_rankings.json", business_date=business_date)
    current = _current_summary(runtime_root=runtime_root, business_date=business_date)
    cash = _cash_summary(runtime_root=runtime_root, business_date=business_date)
    exposure = _exposure_summary(runtime_root=runtime_root, business_date=business_date)
    pending = _pending_summary(runtime_root=runtime_root, business_date=business_date)
    safety = _safety_summary()
    input_source_paths = {name: strategy_dir / filename for name, filename in INPUT_SOURCE_FILENAMES.items()}
    input_symbols = _strategy_input_symbols(candidate, opportunity, current)
    price_source = operations_root / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
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
    )
    input_source_manifest = {
        "price_volatility": _input_source_ref(price_volatility),
        "technical_features": _input_source_ref(technical_features),
    }

    produce(
        "market_context",
        lambda: market_context.produce_market_context_artifact(
            business_date=business_date,
            input_paths=market_context.resolve_default_input_paths(operations_root),
            config=_load_optional(lambda: market_context.load_market_context_config(Path("configs/strategy/market_context.json"))),
            output_path=artifact_paths["market_context"],
            as_of=as_of,
        ),
    )
    produce(
        "corporate_event",
        lambda: corporate_event.produce_corporate_event_artifact(
            business_date=business_date,
            input_paths=corporate_event.resolve_default_input_paths(operations_root),
            output_path=artifact_paths["corporate_event"],
            as_of=as_of,
        ),
    )
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
            policy_config=pp_config,
            output_path=artifact_paths["portfolio_policy"],
            as_of=as_of,
        ),
    )
    dpc_config = _load_optional(lambda: dynamic_position_count.load_dynamic_position_count_config(Path("configs/strategy/dynamic_position_count.json")))
    safety_limits = _load_optional(lambda: load_portfolio_safety_limits(Path("configs/safety/portfolio_limits.json"), legacy_active_max_positions=5))
    produce(
        "dynamic_position_count",
        lambda: dynamic_position_count.produce_dynamic_position_count_artifact(
            business_date=business_date,
            market_context_summary=_dpc_summary(results.get("market_context", {}), business_date),
            portfolio_policy_summary=_dpc_summary(results.get("portfolio_policy", {}), business_date),
            candidate_summary=_dpc_summary(candidate, business_date),
            opportunity_summary=_dpc_summary(opportunity, business_date),
            current_portfolio_summary=_dpc_summary(current, business_date),
            safety_hard_maximum=getattr(safety_limits, "safety_hard_maximum", None),
            existing_active_max_positions=5,
            config=dpc_config,
            output_path=artifact_paths["dynamic_position_count"],
            as_of=as_of,
        ),
    )
    dce_config = _load_optional(lambda: dynamic_cash_exposure.load_dynamic_cash_exposure_config(Path("configs/strategy/dynamic_cash_exposure.json")))
    produce(
        "dynamic_cash_exposure",
        lambda: dynamic_cash_exposure.produce_dynamic_cash_exposure_artifact(
            business_date=business_date,
            market_context_summary=_dce_summary(results.get("market_context", {}), business_date),
            portfolio_policy_summary=_dce_summary(results.get("portfolio_policy", {}), business_date),
            dynamic_position_count_summary=_dce_summary(results.get("dynamic_position_count", {}), business_date),
            candidate_summary=_dce_summary(candidate, business_date),
            opportunity_summary=_dce_summary(opportunity, business_date),
            current_cash_summary=_dce_summary(cash, business_date),
            current_exposure_summary=_dce_summary(exposure, business_date),
            pending_reservation_summary=_dce_summary(pending, business_date),
            safety_limit_summary=_dce_summary(safety, business_date),
            config=dce_config,
            output_path=artifact_paths["dynamic_cash_exposure"],
            as_of=as_of,
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
            position_lifecycle_summary=_pm_summary(current, business_date),
            technical_feature_summary=_pm_summary(_materialized_summary(technical_features), business_date),
            opportunity_summary=_pm_summary(opportunity, business_date),
            accepted_generation_reference=pm_reference,
            output_path=artifact_paths["position_management"],
            as_of=as_of,
        ),
    )
    produce(
        "portfolio_construction",
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
            policy_config_summary=_pc_summary(policy_config_summary, business_date),
            output_path=artifact_paths["portfolio_construction"],
            as_of=as_of,
        ),
    )
    ps_config = _load_optional(lambda: position_sizing.load_position_sizing_config(Path("configs/strategy/position_sizing.json")))
    produce(
        "position_sizing",
        lambda: position_sizing.produce_position_sizing_artifact(
            business_date=business_date,
            portfolio_construction_summary=_ps_summary(results.get("portfolio_construction", {}), business_date),
            capital_deployment_summary=_ps_summary({"status": "REVIEW_REQUIRED", "summary": {"reason": "capital_deployment_is_downstream_of_position_sizing_in_shadow_chain"}}, business_date),
            dynamic_cash_exposure_summary=_ps_summary(results.get("dynamic_cash_exposure", {}), business_date),
            dynamic_position_count_summary=_ps_summary(results.get("dynamic_position_count", {}), business_date),
            position_management_summary=_ps_summary(results.get("position_management", {}), business_date),
            opportunity_summary=_ps_summary(opportunity, business_date),
            current_position_summary=_ps_summary(current, business_date),
            price_volatility_summary=_ps_summary(_materialized_summary(price_volatility), business_date),
            safety_limit_summary=_ps_summary(safety, business_date),
            config=ps_config,
            output_path=artifact_paths["position_sizing"],
            as_of=as_of,
        ),
    )
    produce(
        "capital_deployment",
        lambda: capital_deployment.produce_capital_deployment_artifact(
            business_date=business_date,
            portfolio_construction_artifact_path=artifact_paths["portfolio_construction"],
            portfolio_policy_artifact_path=artifact_paths["portfolio_policy"],
            position_management_artifact_path=artifact_paths["position_management"],
            current_cash_summary=_cd_summary(cash, business_date),
            current_exposure_summary=_cd_summary(exposure, business_date),
            current_portfolio_summary=_cd_summary(current, business_date),
            pending_reservation_summary=_cd_summary(pending, business_date),
            policy_config_summary=_cd_summary(policy_config_summary, business_date),
            output_path=artifact_paths["capital_deployment"],
            as_of=as_of,
        ),
    )
    produce(
        "runtime_planning",
        lambda: runtime_planning.produce_runtime_planning_artifact(
            business_date=business_date,
            portfolio_construction_artifact_path=artifact_paths["portfolio_construction"],
            capital_deployment_artifact_path=artifact_paths["capital_deployment"],
            portfolio_policy_artifact_path=artifact_paths["portfolio_policy"],
            position_management_artifact_path=artifact_paths["position_management"],
            current_portfolio_summary=_rp_summary(current, business_date),
            current_cash_summary=_rp_summary(cash, business_date),
            current_position_summary=_rp_summary(current, business_date),
            pending_summary=_rp_summary(pending, business_date),
            planning_config_summary=_rp_summary({"status": "PASS", "source_ref": "configs/runtime_v2/capital_deployment.json", "source_hash": _file_hash(Path("configs/runtime_v2/capital_deployment.json")), "summary": {}}, business_date),
            output_path=artifact_paths["runtime_planning"],
            as_of=as_of,
        ),
    )
    trace_result = produce_strategy_decision_trace(
        business_date=business_date,
        profile=profile_id,
        run_id=run_id,
        artifact_paths={k: artifact_paths[k] for k in ARTIFACT_FILENAMES if k != "capital_deployment"},
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
    summary = {
        "schema_version": STRATEGY_SHADOW_SUMMARY_SCHEMA_VERSION,
        "run_id": run_id,
        "profile_id": profile_id,
        "business_date": business_date,
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
        "active_runtime_consumer_eligibility": "NO",
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
    }
    _write_json(strategy_dir / "strategy_shadow_summary.json", summary)
    source_payload = source_manifest.build_strategy_source_manifest(
        run_dir=run_dir,
        runtime_root=runtime_root,
        run_id=run_id,
        profile_id=profile_id,
        business_date=business_date,
        strategy_dir=strategy_dir,
        decision_timing="EOD",
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
        "active_runtime_consumer_eligibility": "NO",
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
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
            dpc = _read_json(strategy_dir / "dynamic_position_count.json")
            dce = _read_json(strategy_dir / "dynamic_cash_exposure.json")
            sizing = _read_json(strategy_dir / "position_sizing.json")
            input_manifest = _read_json(strategy_dir / "input_manifest.json")
            source_payload = _read_json(strategy_dir / "source_manifest.json")
            pit = source_payload.get("pit_validation") if isinstance(source_payload.get("pit_validation"), dict) else {}
            total_equity = _float(dce.get("portfolio_total_equity"))
            target_ratio = _float(dce.get("target_invested_ratio", dce.get("target_gross_exposure_ratio")))
            target_notional = _float(dce.get("target_invested_notional"))
            checks = {
                "source_manifest_completeness": "PASS" if _source_manifest_complete(source_payload) else "REVIEW_REQUIRED",
                "source_manifest_hash_reference": "PASS" if input_manifest.get("source_manifest_hash") == source_manifest.manifest_hash(source_payload) else "BLOCK",
                "source_manifest_business_date": "PASS" if source_payload.get("business_date") == str(day) else "BLOCK",
                "pit_validation_status": "PASS" if pit.get("status") == "PASS" else "REVIEW_REQUIRED" if pit.get("status") == "REVIEW_REQUIRED" else "BLOCK" if pit.get("status") == "BLOCK" else "REVIEW_REQUIRED",
                "latest_fallback_absence": "PASS" if pit.get("latest_fallback_used") is False else "BLOCK",
                "current_state_leakage_absence": "PASS" if pit.get("current_state_leakage_detected") is False else "BLOCK",
                "total_equity_lineage": "PASS" if total_equity >= 0 and dce.get("source_as_of") else "REVIEW_REQUIRED",
                "ratio_to_notional_consistency": "PASS" if abs(round(total_equity * target_ratio, 2) - target_notional) <= 0.01 else "BLOCK",
                "fixed_cap_non_use": "PASS" if dpc.get("strategy_fixed_position_cap_used") is False and dce.get("strategy_fixed_jpy_exposure_cap_used") is False and dce.get("legacy_max_exposure_authority_used") is False else "BLOCK",
                "legacy_authority_isolation": "PASS" if dpc.get("legacy_authority_active") is True and dce.get("legacy_authority_active") is True else "REVIEW_REQUIRED",
                "pending_single_deduction": "PASS" if dce.get("pending_deduction_count") in (0, 1) else "BLOCK",
                "target_weight_sum": "PASS" if _float(sizing.get("total_target_weight")) <= _float(sizing.get("target_gross_exposure_ratio")) + 0.000001 else "BLOCK",
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


def _build_input_manifest(*, run_id: str, profile_id: str, runtime_root: Path, business_date: str, feature_date: str, feature_date_authority: Mapping[str, Any]) -> dict[str, Any]:
    resolution = resolve_accepted_generation(runtime_root)
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
        "trading_calendar": str(runtime_root / "operations" / "jquants" / "raw" / "jquants" / "trading_calendar" / "data.parquet"),
        "jquants_sources": {"operations_root": str(runtime_root / "operations")},
        "listed_info_source": str(runtime_root / "operations" / "jquants" / "raw" / "jquants" / "listed_issues" / "data.parquet"),
        "market_quote_source": str(runtime_root / "operations" / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"),
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
    rows = payload if isinstance(payload, list) else payload.get("decisions") or payload.get("rankings") or payload.get("items") or []
    if not isinstance(rows, list):
        rows = []
    return {
        "status": "PASS" if path.is_file() else "MISSING",
        "business_date": business_date,
        "feature_date": business_date,
        "source_ref": str(path),
        "source_hash": _file_hash(path),
        "summary": {"row_count": len(rows), "schema_version": payload.get("schema_version", "") if isinstance(payload, dict) else ""},
        "rows": tuple(row for row in rows if isinstance(row, Mapping)),
    }


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
        rows.append({**dict(row), "current_weight": round(value / total_equity, 6) if total_equity > 0 else 0.0})
    return {"status": "PASS" if path.is_file() else "MISSING", "business_date": business_date, "feature_date": business_date, "source_ref": str(path), "source_hash": _file_hash(path), "summary": {"position_count": len(positions), "current_position_count": len(positions), "positions": rows, "cash": cash, "buying_power": _float(payload.get("buying_power", cash)), "current_cash": cash, "current_market_value": market_value, "gross_exposure": market_value, "portfolio_value": total_equity, "portfolio_total_equity": total_equity}, "rows": tuple(rows)}


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


def _pp_summary(item: Mapping[str, Any], business_date: str) -> portfolio_policy.PortfolioPolicyInputSummary:
    return portfolio_policy.PortfolioPolicyInputSummary(status=str(item.get("status") or "MISSING"), business_date=str(item.get("business_date") or business_date), feature_date=str(item.get("feature_date") or business_date), summary=dict(item.get("summary") or {}), source_ref=str(item.get("source_ref") or ""), source_hash=str(item.get("source_hash") or ""))


def _dpc_summary(item: Mapping[str, Any], business_date: str) -> dynamic_position_count.DynamicPositionCountSourceSummary:
    return dynamic_position_count.DynamicPositionCountSourceSummary(**_summary_kwargs(item, business_date))


def _dce_summary(item: Mapping[str, Any], business_date: str) -> dynamic_cash_exposure.CashExposureSourceSummary:
    return dynamic_cash_exposure.CashExposureSourceSummary(**_summary_kwargs(item, business_date))


def _pc_summary(item: Mapping[str, Any], business_date: str) -> portfolio_construction.PortfolioConstructionSourceSummary:
    kw = _summary_kwargs(item, business_date)
    return portfolio_construction.PortfolioConstructionSourceSummary(**kw, rows=tuple(item.get("rows") or ()))


def _ps_summary(item: Mapping[str, Any], business_date: str) -> position_sizing.PositionSizingSourceSummary:
    kw = _summary_kwargs(item, business_date)
    return position_sizing.PositionSizingSourceSummary(**kw, rows=tuple(item.get("rows") or ()))


def _pm_summary(item: Mapping[str, Any], business_date: str) -> position_management.PMSourceSummary:
    return position_management.PMSourceSummary(**_summary_kwargs(item, business_date))


def _cd_summary(item: Mapping[str, Any], business_date: str) -> capital_deployment.CapitalDeploymentSourceSummary:
    return capital_deployment.CapitalDeploymentSourceSummary(**_summary_kwargs(item, business_date))


def _rp_summary(item: Mapping[str, Any], business_date: str) -> runtime_planning.RuntimePlanningSourceSummary:
    kw = _summary_kwargs(item, business_date)
    return runtime_planning.RuntimePlanningSourceSummary(**kw, rows=tuple(item.get("rows") or ()))


def _summary_kwargs(item: Mapping[str, Any], business_date: str) -> dict[str, Any]:
    return {
        "status": str(item.get("status") or "MISSING"),
        "business_date": str(item.get("business_date") or business_date),
        "feature_date": str(item.get("feature_date") or business_date),
        "source_ref": str(item.get("source_ref") or item.get("artifact_path") or ""),
        "source_hash": str(item.get("source_hash") or item.get("artifact_hash") or ""),
        "summary": dict(item.get("summary") or {}),
    }


def _existing_pm_decisions(*, runtime_root: Path, business_date: str) -> list[dict[str, Any]]:
    candidates = [
        runtime_root / "runtime_state" / "sell_pipeline" / business_date / "position_management_decisions.json",
        runtime_root / "runtime_state" / "position_management" / business_date / "position_management_decisions.json",
    ]
    for path in candidates:
        payload = _read_json(path) if path.is_file() else {}
        rows = payload if isinstance(payload, list) else payload.get("decisions") or payload.get("positions") or []
        if isinstance(rows, list):
            return [dict(row) for row in rows if isinstance(row, Mapping)]
    return []


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
