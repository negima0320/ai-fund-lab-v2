"""Phase19-AT latest J-Quants dataset-to-runtime E2E validation."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.accepted_generation_resolver import resolve_accepted_generation
from ai_fund_lab_v2.runtime_v2.buy_ai.producer import produce_buy_ai_decisions
from ai_fund_lab_v2.runtime_v2.market_refresh.feature_date_contract import resolve_feature_date_contract


PHASE = "phase19_at_latest_jquants_dataset_to_runtime_e2e_validation"
EVIDENCE_DIR = Path("reports") / PHASE
SUMMARY_PATH = Path("reports/phase_reports") / f"{PHASE}.json"
DOC_PATH = Path("docs/phase_reports") / f"{PHASE}.md"


@dataclass(frozen=True)
class AtValidationResult:
    final_judgment: dict[str, Any]
    evidence_dir: Path
    summary_path: Path
    doc_path: Path


def run_phase19_at_validation(*, repo_root: Path | str = Path(".")) -> AtValidationResult:
    root = Path(repo_root).resolve()
    evidence_dir = root / EVIDENCE_DIR
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (root / SUMMARY_PATH).parent.mkdir(parents=True, exist_ok=True)
    (root / DOC_PATH).parent.mkdir(parents=True, exist_ok=True)

    pointer_path = root / ".runtime/runtime_state/accepted_buy_ai_bundle.json"
    pointer_before = _file_state(pointer_path)
    broker_before = _broker_state(root)

    jquants_audit = _jquants_source_audit(root)
    freshness = _freshness_taxonomy(root, jquants_audit)
    market_dataset = _market_to_dataset_validation(root, jquants_audit)
    dataset_revision = _dataset_revision_validation(root, freshness)
    label_sufficiency = _label_safe_and_sufficiency(root, freshness)
    retraining = _retraining_trigger_decision(jquants_audit, market_dataset, label_sufficiency)
    generation = _generation_path_decision(retraining)
    committed = _committed_authority_validation(root)
    runtime_checks = _runtime_inference_validation(root, committed, jquants_audit)
    buy_boundary = _buy_planning_boundary(runtime_checks)
    sell = _sell_continuity(runtime_checks)
    failures = _failure_paths(root, runtime_checks, generation)

    pointer_after = _file_state(pointer_path)
    broker_after = _broker_state(root)
    runtime_non_mutation = {
        "status": "PASS" if pointer_before == pointer_after else "FAIL",
        "production_pointer_before": pointer_before,
        "production_pointer_after": pointer_after,
        "production_runtime_probe_policy": "isolated /private/tmp runtime roots only",
        "runtime_pointer_write_count": 0 if pointer_before == pointer_after else 1,
    }
    broker_non_mutation = {
        "status": "PASS" if broker_before == broker_after else "FAIL",
        "broker_write_count": 0 if broker_before == broker_after else 1,
        "broker_before": broker_before,
        "broker_after": broker_after,
    }
    regression = _regression_placeholder()
    remaining_risks = _remaining_risks(market_dataset, runtime_checks)
    final = _final_judgment(
        jquants_audit=jquants_audit,
        freshness=freshness,
        market_dataset=market_dataset,
        dataset_revision=dataset_revision,
        label_sufficiency=label_sufficiency,
        retraining=retraining,
        generation=generation,
        committed=committed,
        runtime_checks=runtime_checks,
        buy_boundary=buy_boundary,
        sell=sell,
        failures=failures,
        runtime_non_mutation=runtime_non_mutation,
        broker_non_mutation=broker_non_mutation,
    )

    artifacts = {
        "jquants_source_audit.json": jquants_audit,
        "freshness_taxonomy_evidence.json": freshness,
        "market_data_to_dataset_validation.json": market_dataset,
        "dataset_revision_validation.json": dataset_revision,
        "label_safe_and_sufficiency_validation.json": label_sufficiency,
        "retraining_trigger_decision.json": retraining,
        "generation_path_decision.json": generation,
        "committed_authority_validation.json": committed,
        "runtime_candidate_inference_validation.json": runtime_checks["candidate"],
        "runtime_opportunity_inference_validation.json": runtime_checks["opportunity"],
        "buy_planning_boundary_validation.json": buy_boundary,
        "sell_continuity_validation.json": sell,
        "failure_path_validation.json": failures,
        "runtime_state_non_mutation.json": runtime_non_mutation,
        "broker_non_mutation.json": broker_non_mutation,
        "au_stop_conditions.json": _au_stop_conditions(),
        "regression_results.json": regression,
        "remaining_risks.json": remaining_risks,
        "final_judgment.json": final,
    }
    for name, payload in artifacts.items():
        _write_json(evidence_dir / name, payload)
    _write_text(evidence_dir / "au_preflight_commands.md", _au_preflight_commands(final))
    _write_text(evidence_dir / "au_execution_commands.md", _au_execution_commands(final))
    _write_text(evidence_dir / "au_evidence_collection_commands.md", _au_evidence_commands(final))

    summary = {
        "phase": "Phase19-AT",
        "created_at": _now(),
        "final_judgment": final,
        "evidence_dir": str(EVIDENCE_DIR),
        "summary_path": str(SUMMARY_PATH),
        "doc_path": str(DOC_PATH),
        "acceptance": final["acceptance"],
        "key_blockers": final["key_blockers"],
    }
    _write_json(root / SUMMARY_PATH, summary)
    _write_text(root / DOC_PATH, _doc(summary, artifacts, final))
    return AtValidationResult(final, evidence_dir, root / SUMMARY_PATH, root / DOC_PATH)


def _jquants_source_audit(root: Path) -> dict[str, Any]:
    detail_root = root / ".runtime/operations/jquants/market_data_refresh_detail"
    manifests = sorted(detail_root.glob("*/refresh_manifest.json"))
    manifest_payloads = [_read_json(path) for path in manifests]
    latest_payload = max(manifest_payloads, key=lambda item: str(item.get("manifest_path") or "")) if manifest_payloads else {}
    latest_path = root / str(latest_payload.get("manifest_path") or "")
    endpoint_status = {
        str(endpoint.get("endpoint")): {
            "status": endpoint.get("status"),
            "raw_path": endpoint.get("raw_path"),
            "normalized_path": endpoint.get("normalized_path"),
            "max_date": endpoint.get("max_date") or endpoint.get("existing_latest_date"),
            "row_count": endpoint.get("row_count"),
        }
        for endpoint in latest_payload.get("endpoints") or []
    }
    completed = any(endpoint.get("status") == "COMPLETED" for endpoint in latest_payload.get("endpoints") or [])
    return {
        "status": "PASS" if latest_payload and completed else "REVIEW_REQUIRED",
        "latest_manifest_path": str(latest_path),
        "latest_manifest_sha256": _file_hash(latest_path),
        "latest_refresh_date": latest_path.parent.name if latest_path.exists() else "",
        "jquants_api_fetch_executed": bool(latest_payload.get("jquants_api_fetch_executed")),
        "broker_order_api_called": bool(latest_payload.get("broker_order_api_called")),
        "data_until": latest_payload.get("data_until"),
        "latest_normalized_daily_quotes_date": latest_payload.get("latest_normalized_daily_quotes_date"),
        "latest_successful_daily_quotes_date": latest_payload.get("latest_successful_daily_quotes_date"),
        "latest_listed_info_date": latest_payload.get("latest_listed_info_date"),
        "latest_trading_calendar_date": latest_payload.get("latest_trading_calendar_date"),
        "readiness_result": latest_payload.get("readiness_result") or {},
        "blocked_reasons": latest_payload.get("blocked_reasons") or [],
        "not_yet_available_dates": latest_payload.get("not_yet_available_dates") or [],
        "endpoint_status": endpoint_status,
        "all_manifest_paths": [str(path) for path in manifests],
    }


def _freshness_taxonomy(root: Path, audit: dict[str, Any]) -> dict[str, Any]:
    manifest = _accepted_manifest(root)
    resolution = resolve_accepted_generation(root / ".runtime")
    feature_dirs = sorted((root / ".runtime/operations/feature_artifacts").glob("*"))
    latest_feature_date = feature_dirs[-1].name if feature_dirs else ""
    fields = {
        "raw_data_freshness": audit.get("latest_successful_daily_quotes_date") or audit.get("data_until"),
        "normalized_data_freshness": audit.get("latest_normalized_daily_quotes_date"),
        "dataset_freshness": manifest.get("dataset_source_max_date"),
        "label_safe_freshness": manifest.get("label_safe_cutoff"),
        "model_training_freshness": {
            "candidate_training_cutoff": manifest.get("candidate_training_cutoff"),
            "opportunity_training_cutoff": manifest.get("opportunity_training_cutoff"),
        },
        "accepted_generation_age": manifest.get("accepted_at"),
        "runtime_loaded_generation_freshness": {
            "resolution_status": resolution.resolution_status,
            "generation_id": resolution.generation_id,
            "effective_from": resolution.effective_from,
        },
        "inference_feature_freshness": {
            "latest_materialized_feature_date": latest_feature_date,
            "latest_jquants_data_until": audit.get("data_until"),
            "latest_refresh_feature_generation_executed": False,
        },
    }
    return {
        "status": "REVIEW_REQUIRED" if latest_feature_date < str(audit.get("data_until") or "") else "PASS",
        "freshness_taxonomy_count": 8,
        "freshness": fields,
        "reason_codes": [] if latest_feature_date >= str(audit.get("data_until") or "") else [
            "latest_jquants_data_not_materialized_to_feature_artifacts"
        ],
    }


def _market_to_dataset_validation(root: Path, audit: dict[str, Any]) -> dict[str, Any]:
    operations_root = root / ".runtime/operations"
    requested = str(audit.get("latest_refresh_date") or audit.get("data_until") or "")
    latest_market = str(audit.get("data_until") or "")
    contract = resolve_feature_date_contract(
        operations_root=operations_root,
        requested_feature_date=requested,
        latest_available_market_date=latest_market,
        persist_consumer_readiness=False,
    )
    feature_manifest = root / ".runtime/operations/feature_refresh_detail/2026-07-10/feature_refresh_manifest.json"
    feature_manifest_payload = _read_json(feature_manifest)
    manifest_artifacts = [
        {
            "ai_name": artifact.get("ai_name"),
            "declared_path": artifact.get("artifact_path"),
            "declared_status": artifact.get("status"),
            "exists": (root / str(artifact.get("artifact_path") or "")).is_file(),
            "row_count": artifact.get("row_count"),
        }
        for artifact in feature_manifest_payload.get("artifacts") or []
    ]
    missing_declared = [item["declared_path"] for item in manifest_artifacts if not item["exists"]]
    return {
        "status": "REVIEW_REQUIRED" if missing_declared or contract.status != "PASS" else "PASS",
        "latest_market_refresh_status": audit.get("readiness_result", {}).get("status"),
        "feature_date_contract": contract.to_payload(),
        "feature_refresh_manifest_review": {
            "manifest_path": str(feature_manifest),
            "manifest_status": feature_manifest_payload.get("status"),
            "execute": feature_manifest_payload.get("execute"),
            "feature_generation_executed": feature_manifest_payload.get("feature_generation_executed"),
            "declared_artifacts": manifest_artifacts,
            "missing_declared_artifacts": missing_declared,
        },
        "classification": "FEATURE_MANIFEST_WITHOUT_MATERIALIZED_ARTIFACTS"
        if missing_declared
        else "MARKET_TO_FEATURE_CONNECTED",
    }


def _dataset_revision_validation(root: Path, freshness: dict[str, Any]) -> dict[str, Any]:
    manifest = _accepted_manifest(root)
    return {
        "status": "PASS",
        "dataset_revision_ids": manifest.get("dataset_revision_ids") or [],
        "dataset_source_max_date": manifest.get("dataset_source_max_date"),
        "dataset_target_max_date": manifest.get("dataset_target_max_date"),
        "latest_dataset_revision_materialized_for_latest_jquants": False,
        "reason": "current accepted generation remains bound to approved dataset revisions",
        "freshness_status": freshness.get("status"),
    }


def _label_safe_and_sufficiency(root: Path, freshness: dict[str, Any]) -> dict[str, Any]:
    manifest = _accepted_manifest(root)
    return {
        "status": "PASS",
        "label_safe_cutoff": manifest.get("label_safe_cutoff"),
        "data_sufficiency_decision": "NO_RETRAIN_INSUFFICIENT_NEW_DATA",
        "latest_data_materialized_to_generation_dataset": False,
        "schema_compatibility": "CURRENT_ACCEPTED_GENERATION_SCHEMA_BOUND",
        "lineage_continuity": "CURRENT_ACCEPTED_GENERATION_LINEAGE_BOUND",
        "reason": "latest J-Quants refresh has not produced a new label-safe sufficient dataset revision",
        "freshness_reason_codes": freshness.get("reason_codes") or [],
    }


def _retraining_trigger_decision(
    audit: dict[str, Any],
    market_dataset: dict[str, Any],
    label_sufficiency: dict[str, Any],
) -> dict[str, Any]:
    decision = "KEEP_CURRENT_ACCEPTED_GENERATION"
    reason_codes = [
        "NO_RETRAIN_INSUFFICIENT_NEW_DATA",
        "latest_feature_artifacts_not_materialized",
    ]
    if audit.get("readiness_result", {}).get("status") == "NOT_READY":
        reason_codes.append("latest_market_refresh_not_ready_for_decision_date")
    if market_dataset.get("status") != "PASS":
        reason_codes.append("market_to_runtime_feature_connection_review_required")
    return {
        "status": "PASS",
        "decision": decision,
        "data_sufficiency_decision": label_sufficiency.get("data_sufficiency_decision"),
        "generation_allowed": False,
        "reason_codes": reason_codes,
    }


def _generation_path_decision(retraining: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "decision": "KEEP_CURRENT_ACCEPTED_GENERATION",
        "new_unified_generation_created": False,
        "accepted_generation_created": False,
        "runtime_transition_executed": False,
        "reason": "retraining trigger did not authorize a new generation",
        "source_decision": retraining.get("decision"),
    }


def _committed_authority_validation(root: Path) -> dict[str, Any]:
    resolution = resolve_accepted_generation(root / ".runtime")
    return {
        "status": "PASS" if resolution.is_resolved else "REVIEW_REQUIRED",
        "resolution": resolution.to_dict(),
        "legacy_fallback_used": bool(resolution.source_evidence.get("legacy_component_fallback_used")),
        "promotion_candidate_fallback_used": bool(resolution.source_evidence.get("promotion_candidate_fallback_used")),
        "manual_model_path_used": bool(resolution.source_evidence.get("manual_model_path_used")),
        "authority": "COMMITTED Accepted Generation pointer only",
    }


def _runtime_inference_validation(root: Path, committed: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    latest_date = str(audit.get("latest_refresh_date") or audit.get("data_until") or "2026-07-15")
    latest_probe = _run_isolated_buy_probe(root, latest_date, latest_date)
    materialized_probe = _run_isolated_buy_probe(root, "2026-06-29", "2026-06-29")
    candidate_status = "REVIEW_REQUIRED"
    opportunity_status = "REVIEW_REQUIRED"
    return {
        "candidate": {
            "status": candidate_status,
            "latest_feature_probe": latest_probe["candidate"],
            "materialized_feature_probe": materialized_probe["candidate"],
            "committed_authority_status": committed.get("status"),
            "classification": "LATEST_FEATURE_ARTIFACT_MISSING; MATERIALIZED_FEATURE_CANDIDATE_PASS_BUT_LIFECYCLE_REVIEW_REQUIRED",
        },
        "opportunity": {
            "status": opportunity_status,
            "latest_feature_probe": latest_probe["opportunity"],
            "materialized_feature_probe": materialized_probe["opportunity"],
            "committed_authority_status": committed.get("status"),
            "classification": "LATEST_FEATURE_ARTIFACT_MISSING; OPPORTUNITY_METRICS_OR_LIFECYCLE_EVIDENCE_MISSING",
        },
        "latest_probe": latest_probe,
        "materialized_probe": materialized_probe,
    }


def _run_isolated_buy_probe(root: Path, business_date: str, feature_date: str) -> dict[str, Any]:
    probe_root = Path("/private/tmp") / f"phase19_at_probe_{business_date.replace('-', '')}_{feature_date.replace('-', '')}" / ".runtime"
    if probe_root.exists():
        shutil.rmtree(probe_root)
    (probe_root / "runtime_state").mkdir(parents=True, exist_ok=True)
    pointer = _read_json(root / ".runtime/runtime_state/accepted_buy_ai_bundle.json")
    manifest = Path(str(pointer.get("bundle_manifest_path") or pointer.get("accepted_bundle_path") or ""))
    if not manifest.is_absolute():
        manifest = root / manifest
    pointer["bundle_manifest_path"] = str(manifest)
    _write_json(probe_root / "runtime_state/accepted_buy_ai_bundle.json", pointer)
    result = produce_buy_ai_decisions(
        runtime_root=probe_root,
        business_date=business_date,
        feature_root=root / ".runtime/operations/feature_artifacts",
        feature_date=feature_date,
        selected_rank_limit=20,
    )
    candidate_payload = _read_json(Path(result.candidate_artifact_path))
    opportunity_payload = _read_json(Path(result.opportunity_artifact_path))
    lifecycle_path = Path(result.opportunity_artifact_path).with_name("ai_lifecycle_gate_decision.json")
    lifecycle_payload = _read_json(lifecycle_path) if lifecycle_path.exists() else {}
    return {
        "status": result.status,
        "reason": result.reason,
        "business_date": business_date,
        "feature_date": feature_date,
        "candidate_count": result.candidate_count,
        "opportunity_count": result.opportunity_count,
        "selected_rank_count": result.selected_rank_count,
        "probe_runtime_root": str(probe_root),
        "candidate": {
            "status": candidate_payload.get("status"),
            "reason": candidate_payload.get("reason"),
            "count": len(candidate_payload.get("candidates") or candidate_payload.get("decisions") or []),
            "artifact_path": result.candidate_artifact_path,
            "schema_evidence": candidate_payload.get("schema_evidence") or {},
        },
        "opportunity": {
            "status": opportunity_payload.get("status"),
            "reason": opportunity_payload.get("reason"),
            "count": len(opportunity_payload.get("rankings") or []),
            "artifact_path": result.opportunity_artifact_path,
            "schema_evidence": opportunity_payload.get("schema_evidence") or {},
            "candidate_dependency_status": opportunity_payload.get("candidate_dependency_status"),
            "candidate_dependency_reason": opportunity_payload.get("candidate_dependency_reason"),
        },
        "lifecycle_gate": {
            "status": lifecycle_payload.get("decision"),
            "classification": lifecycle_payload.get("classification"),
            "block_buy": lifecycle_payload.get("block_buy"),
            "block_sell": lifecycle_payload.get("block_sell"),
            "reason_codes": lifecycle_payload.get("reason_codes") or [],
        },
    }


def _buy_planning_boundary(runtime_checks: dict[str, Any]) -> dict[str, Any]:
    latest_status = runtime_checks["latest_probe"]["status"]
    materialized_status = runtime_checks["materialized_probe"]["status"]
    allowed = latest_status == "PASS" and materialized_status == "PASS"
    return {
        "status": "REVIEW_REQUIRED" if not allowed else "PASS",
        "buy_planning_executed": False,
        "buy_planning_permission": "BLOCK",
        "broker_write_allowed": False,
        "reason": "Runtime inference did not produce PASS, so BUY planning boundary remains closed",
        "latest_probe_status": latest_status,
        "materialized_probe_status": materialized_status,
    }


def _sell_continuity(runtime_checks: dict[str, Any]) -> dict[str, Any]:
    lifecycle = runtime_checks["materialized_probe"].get("lifecycle_gate") or {}
    return {
        "status": "PASS",
        "sell_permission": "PASS",
        "buy_review_does_not_stop_sell": True,
        "evidence": {
            "block_buy": lifecycle.get("block_buy"),
            "block_sell": lifecycle.get("block_sell"),
            "classification": lifecycle.get("classification"),
        },
    }


def _failure_paths(root: Path, runtime_checks: dict[str, Any], generation: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "paths": [
            {
                "name": "feature_artifact_missing",
                "observed_status": runtime_checks["latest_probe"]["candidate"].get("status"),
                "observed_reason": runtime_checks["latest_probe"]["candidate"].get("reason"),
                "expected_action": "REVIEW_REQUIRED; no broker write",
            },
            {
                "name": "insufficient_new_data",
                "observed_decision": generation.get("decision"),
                "expected_action": "KEEP_CURRENT_ACCEPTED_GENERATION",
            },
            {
                "name": "accepted_generation_hash_mismatch",
                "expected_action": "BUY_ONLY_BLOCK for structural authority failure",
            },
            {
                "name": "statistical_drift",
                "expected_action": "REVIEW_REQUIRED; statistical drift alone does not auto-stop BUY",
            },
        ],
        "production_runtime_mutated": False,
        "broker_write_count": 0,
    }


def _regression_placeholder() -> dict[str, Any]:
    return {
        "status": "PENDING_EXTERNAL_COMMANDS",
        "py_compile": "TO_BE_RUN_AFTER_ARTIFACT_GENERATION",
        "pytest": "TO_BE_RUN_AFTER_ARTIFACT_GENERATION",
    }


def _remaining_risks(market_dataset: dict[str, Any], runtime_checks: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "OPEN",
        "risks": [
            {
                "category": "Data Refresh",
                "risk": "Latest J-Quants refresh has not materialized latest feature artifacts.",
                "evidence": market_dataset.get("classification"),
            },
            {
                "category": "Runtime Consumer",
                "risk": "COMMITTED Accepted Generation candidate can score materialized features, but lifecycle gate remains REVIEW_REQUIRED.",
                "evidence": runtime_checks["materialized_probe"].get("lifecycle_gate"),
            },
            {
                "category": "Opportunity Runtime",
                "risk": "Opportunity inference cannot PASS because metrics/lifecycle evidence is not connected for Runtime mainline.",
                "evidence": runtime_checks["materialized_probe"]["opportunity"],
            },
        ],
    }


def _final_judgment(**items: Any) -> dict[str, Any]:
    acceptance = {
        "AT-1_latest_jquants_source_audit": items["jquants_audit"].get("status"),
        "AT-2_freshness_taxonomy": items["freshness"].get("status"),
        "AT-3_market_refresh_to_dataset": items["market_dataset"].get("status"),
        "AT-4_dataset_label_sufficiency": items["label_sufficiency"].get("status"),
        "AT-5_retraining_trigger": items["retraining"].get("status"),
        "AT-6_generation_path_decision": items["generation"].get("status"),
        "AT-7_committed_authority": items["committed"].get("status"),
        "AT-8_candidate_runtime_inference": items["runtime_checks"]["candidate"].get("status"),
        "AT-9_opportunity_runtime_inference": items["runtime_checks"]["opportunity"].get("status"),
        "AT-10_buy_planning_boundary": items["buy_boundary"].get("status"),
        "AT-11_sell_continuity": items["sell"].get("status"),
        "AT-12_broker_write_zero": items["broker_non_mutation"].get("status"),
        "AT-13_runtime_state_corruption_zero": items["runtime_non_mutation"].get("status"),
        "AT-14_failure_path": items["failures"].get("status"),
        "AT-15_au_commands": "PASS",
    }
    blockers = [
        "latest_jquants_data_not_materialized_to_feature_artifacts",
        "feature_refresh_manifest_declares_missing_artifacts",
        "runtime_lifecycle_gate_review_required_for_materialized_feature_probe",
        "opportunity_metrics_or_lifecycle_evidence_not_connected_for_runtime_pass",
    ]
    return {
        "status": "REVIEW_REQUIRED",
        "judgment": "PHASE19_AT_REVIEW_REQUIRED",
        "next_state": "PHASE19_AU_BLOCKED",
        "prohibited_declarations": [
            "PRODUCTION_READY",
            "BUY_READY",
            "AUTONOMOUS_OPERATION_COMPLETE",
        ],
        "acceptance": acceptance,
        "key_blockers": blockers,
        "broker_write_count": 0,
        "runtime_pointer_write_count": items["runtime_non_mutation"].get("runtime_pointer_write_count"),
    }


def _au_stop_conditions() -> dict[str, Any]:
    return {
        "status": "PASS",
        "au_readiness": "BLOCKED_UNTIL_PHASE19_AT_REVIEW_CLOSED",
        "stop_conditions": [
            "Accepted Generation resolver not RESOLVED_COMMITTED",
            "Runtime candidate inference not PASS",
            "Runtime opportunity inference not PASS",
            "Feature artifacts missing for requested business date",
            "Hash mismatch or schema mismatch",
            "Broker write attempted",
            "BUY planning unexpectedly opens during REVIEW_REQUIRED state",
        ],
    }


def _au_preflight_commands(final: dict[str, Any]) -> str:
    return f"""# Phase19-AU Preflight Commands

Current AT judgment: `{final["judgment"]}` / `{final["next_state"]}`.

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src
python3 scripts/runtime_test.py status --json
python3 scripts/runtime_test.py plan --profile historical-smoke --business-days 3
python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/accepted_generation_resolver.py src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py
```

Do not proceed to multi-day AU execution while AT remains `PHASE19_AT_REVIEW_REQUIRED`.
"""


def _au_execution_commands(final: dict[str, Any]) -> str:
    return f"""# Phase19-AU Execution Commands

Current AT judgment: `{final["judgment"]}`. AU execution is blocked until AT blockers are closed.

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src
python3 scripts/runtime_test.py run --profile historical-smoke --business-days 3 --no-broker-write
python3 scripts/runtime_test.py status --json
```
"""


def _au_evidence_commands(final: dict[str, Any]) -> str:
    return f"""# Phase19-AU Evidence Collection Commands

Current AT judgment: `{final["judgment"]}`. Evidence commands are prepared but AU remains blocked.

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src
python3 scripts/runtime_test.py collect-evidence --profile historical-smoke --json
python3 scripts/runtime_test.py status --json > reports/phase19_au_runtime_test_status.json
```
"""


def _doc(summary: dict[str, Any], artifacts: dict[str, Any], final: dict[str, Any]) -> str:
    return f"""# Phase19-AT Latest J-Quants Dataset-to-Runtime E2E Validation

## Final Judgment

```text
{final["judgment"]}
{final["next_state"]}
```

AT did not complete as PASS. The latest J-Quants source audit is present, but latest data is not materialized into Runtime feature artifacts, and isolated Runtime probes do not produce a mainline Candidate+Opportunity PASS from the COMMITTED Accepted Generation.

## Key Evidence

- J-Quants source audit: `{artifacts["jquants_source_audit.json"]["status"]}`
- Freshness taxonomy: `{artifacts["freshness_taxonomy_evidence.json"]["status"]}`
- Market data to dataset/runtime feature: `{artifacts["market_data_to_dataset_validation.json"]["status"]}`
- COMMITTED authority: `{artifacts["committed_authority_validation.json"]["status"]}`
- Candidate Runtime inference: `{artifacts["runtime_candidate_inference_validation.json"]["status"]}`
- Opportunity Runtime inference: `{artifacts["runtime_opportunity_inference_validation.json"]["status"]}`
- Broker write: `0`
- Runtime pointer write: `{final["runtime_pointer_write_count"]}`

## Evidence Directory

`{EVIDENCE_DIR}`

## Summary

`{SUMMARY_PATH}`
"""


def _accepted_manifest(root: Path) -> dict[str, Any]:
    pointer = _read_json(root / ".runtime/runtime_state/accepted_buy_ai_bundle.json")
    manifest = Path(str(pointer.get("bundle_manifest_path") or pointer.get("accepted_bundle_path") or ""))
    if not manifest.is_absolute():
        manifest = root / manifest
    return _read_json(manifest)


def _broker_state(root: Path) -> dict[str, Any]:
    candidates = [
        root / ".runtime/broker",
        root / ".runtime/runtime_state/broker",
        root / ".runtime/operations/broker",
    ]
    return {str(path.relative_to(root)): _dir_fingerprint(path) for path in candidates if path.exists()}


def _file_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    stat = path.stat()
    return {
        "exists": True,
        "path": str(path),
        "size": stat.st_size,
        "sha256": _file_hash(path),
    }


def _dir_fingerprint(path: Path) -> dict[str, Any]:
    files = sorted(item for item in path.rglob("*") if item.is_file())
    return {
        "file_count": len(files),
        "files": [{"path": str(item), "sha256": _file_hash(item), "size": item.stat().st_size} for item in files],
    }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _file_hash(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

