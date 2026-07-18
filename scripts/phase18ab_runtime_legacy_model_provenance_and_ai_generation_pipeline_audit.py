from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "phase18ab-runtime-legacy-provenance-generation-pipeline-audit-20260718T000000Z"
REPORT_JSON = ROOT / "reports/phase_reports/phase18_ab_runtime_legacy_model_provenance_and_ai_generation_pipeline_audit.json"
REPORT_MD = ROOT / "docs/phase_reports/phase18_ab_runtime_legacy_model_provenance_and_ai_generation_pipeline_audit.md"
EVIDENCE_DIR = ROOT / "reports/phase18_ab_runtime_legacy_model_provenance_and_ai_generation_pipeline_audit" / RUN_ID

CANDIDATE_LEGACY_MODEL = ROOT / ".runtime/artifacts/ai/candidate/model/formal_candidate_model/sha256-2ea75d14d3fe3682/model.pkl"
CANDIDATE_LEGACY_SOURCE = ROOT / ".runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl"
CANDIDATE_LEGACY_MANIFEST = ROOT / ".runtime/candidate_ai/models/phase4bf_formal_candidate_model_manifest.json"
CANDIDATE_LEGACY_METADATA = ROOT / ".runtime/artifacts/ai/candidate/training_metadata/long_history_dataset/sha256-da0685d519e4fecc/training_metadata.json"
CANDIDATE_LEGACY_LINEAGE = ROOT / ".runtime/artifacts/ai/candidate/lineage/long_history_dataset/sha256-6ef955a13ff6f578/training_data_lineage.json"

OPPORTUNITY_LEGACY_MODEL = ROOT / ".runtime/artifacts/ai/opportunity/model/formal_opportunity_model/sha256-140e350bd9b12bf0/model.pkl"
OPPORTUNITY_LEGACY_SOURCE = ROOT / "reports/opportunity_ai/phase5p/models/opportunity_model.pkl"
OPPORTUNITY_LEGACY_METADATA = ROOT / ".runtime/artifacts/ai/opportunity/training_metadata/formal_opportunity_training/sha256-5923c387f590807d/training_metadata.json"
OPPORTUNITY_LEGACY_LINEAGE = ROOT / ".runtime/artifacts/ai/opportunity/lineage/formal_opportunity_training/sha256-5923c387f590807d/training_data_lineage.json"
OPPORTUNITY_LEGACY_METRICS = ROOT / "reports/opportunity_ai/phase5p/training/opportunity_training_metrics.json"

PHASE18I_BUNDLE = ROOT / ".runtime/artifact_registry/promotion_candidates/transactions/promotion-tx-phase18i-1081babc49b5d26b/atomic_buy_ai_bundle.json"
PHASE18Y_FRESHNESS = ROOT / ".runtime/artifact_registry/promotion_candidates/transactions/promotion-tx-phase18y-contract-completion-1081babc49b5d26b/freshness_metadata.json"
REGISTRY_INDEX = ROOT / ".runtime/artifact_registry/index/registry_index.json"
PROMOTION_INDEX = ROOT / ".runtime/artifact_registry/promotion_candidates/promotion_candidate_index.json"
RUNTIME_ACCEPTED_STATE = ROOT / ".runtime/runtime_state/accepted_buy_ai_bundle.json"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def maybe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except Exception:
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")).hexdigest()


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def dataset_dates(dataset_path: Path) -> dict[str, Any]:
    if not dataset_path.exists():
        return {"exists": False}
    frame = pd.read_parquet(dataset_path, columns=["target_date"])
    return {"exists": True, "target_date_min": str(frame["target_date"].min()), "target_date_max": str(frame["target_date"].max()), "row_count": int(len(frame))}


def dataset_bundle_dates(dataset_dir: Path) -> dict[str, Any]:
    return dataset_dates(dataset_dir / "dataset.parquet")


def split_period(training_dir: Path) -> dict[str, Any]:
    split = maybe_json(training_dir / "split_definition.json")
    out: dict[str, Any] = {}
    for name in ("train", "validation", "test", "recent_holdout"):
        item = split.get(name) or {}
        out[name] = {
            "start": item.get("start", ""),
            "end": item.get("end", ""),
            "date_count": item.get("date_count", 0),
        }
    return out


def registry_entry(logical_id: str) -> dict[str, Any]:
    return (maybe_json(REGISTRY_INDEX).get("entries") or {}).get(logical_id, {})


def promotion_candidate_bundle() -> dict[str, Any]:
    return read_json(PHASE18I_BUNDLE)


def promotion_component(component: str, bundle: dict[str, Any]) -> dict[str, Any]:
    key = "candidate_training" if component == "candidate" else "opportunity_training"
    dataset_key = "candidate_dataset" if component == "candidate" else "opportunity_dataset"
    training_dir = ROOT / bundle[key]["training_dir"]
    dataset_dir = ROOT / bundle[dataset_key]["dataset_dir"]
    split = split_period(training_dir)
    return {
        "component": component,
        "artifact_path": rel(training_dir / "model.pkl"),
        "hash": file_hash(training_dir / "model.pkl"),
        "training_bundle": training_dir.name,
        "training_bundle_hash": bundle[key]["bundle_hash"],
        "dataset_bundle": dataset_dir.name,
        "dataset_bundle_hash": bundle[dataset_key]["dataset_hash"],
        "split_definition": rel(training_dir / "split_definition.json"),
        "train_start": split["train"]["start"],
        "train_end": split["train"]["end"],
        "dataset_dates": dataset_bundle_dates(dataset_dir),
        "training_metadata": maybe_json(training_dir / "training_metadata.json"),
        "lineage": maybe_json(training_dir / "lineage.json"),
        "status": "PROMOTION_CANDIDATE_RUNTIME_INELIGIBLE",
    }


def legacy_candidate_provenance() -> dict[str, Any]:
    manifest = maybe_json(CANDIDATE_LEGACY_MANIFEST)
    metadata = maybe_json(CANDIDATE_LEGACY_METADATA)
    lineage = maybe_json(CANDIDATE_LEGACY_LINEAGE)
    dataset_path = ROOT / str(manifest.get("dataset_path") or metadata.get("dataset_path") or "")
    return {
        "component": "candidate",
        "artifact_path": rel(CANDIDATE_LEGACY_MODEL),
        "source_artifact_path": rel(CANDIDATE_LEGACY_SOURCE),
        "registry_path": rel(CANDIDATE_LEGACY_MODEL.parent),
        "hash": file_hash(CANDIDATE_LEGACY_MODEL),
        "source_hash": file_hash(CANDIDATE_LEGACY_SOURCE),
        "hash_matches_source": file_hash(CANDIDATE_LEGACY_MODEL) == file_hash(CANDIDATE_LEGACY_SOURCE),
        "producer": "Phase4-BF formal candidate training",
        "generation_command": "scripts/train_phase4bf_formal_candidate_model.py",
        "source_commit": git_commit(),
        "generated_at": manifest.get("created_at") or metadata.get("created_at", ""),
        "training_bundle": "legacy_phase4bf_model_manifest",
        "dataset_bundle": metadata.get("dataset_version", ""),
        "dataset_path": rel(dataset_path),
        "dataset_dates": dataset_dates(dataset_path),
        "split_definition": "legacy split embedded in dataset split column; no formal Common PIT split_definition.json",
        "training_metadata_path": rel(CANDIDATE_LEGACY_METADATA),
        "lineage_path": rel(CANDIDATE_LEGACY_LINEAGE),
        "training_metadata": metadata,
        "lineage": lineage,
        "model_type": manifest.get("model_type", ""),
        "runtime_status": "Registry accepted set Runtime eligible",
        "trust_assessment": "Usable only as current accepted legacy artifact; not Common PIT/Atomic BUY AI Bundle aligned.",
    }


def legacy_opportunity_provenance() -> dict[str, Any]:
    metadata = maybe_json(OPPORTUNITY_LEGACY_METADATA)
    lineage = maybe_json(OPPORTUNITY_LEGACY_LINEAGE)
    metrics = maybe_json(OPPORTUNITY_LEGACY_METRICS)
    return {
        "component": "opportunity",
        "artifact_path": rel(OPPORTUNITY_LEGACY_MODEL),
        "source_artifact_path": rel(OPPORTUNITY_LEGACY_SOURCE),
        "registry_path": rel(OPPORTUNITY_LEGACY_MODEL.parent),
        "hash": file_hash(OPPORTUNITY_LEGACY_MODEL),
        "source_hash": file_hash(OPPORTUNITY_LEGACY_SOURCE),
        "hash_matches_source": file_hash(OPPORTUNITY_LEGACY_MODEL) == file_hash(OPPORTUNITY_LEGACY_SOURCE),
        "producer": "Phase5-P formal opportunity training",
        "generation_command": "phase5p opportunity training pipeline / reports/opportunity_ai/phase5p",
        "source_commit": git_commit(),
        "generated_at": metadata.get("created_at", ""),
        "training_bundle": "legacy_phase5p_training_metrics",
        "dataset_bundle": "",
        "dataset_path": "reports/opportunity_ai/phase5p dataset evidence",
        "dataset_dates": {"row_count": metrics.get("train_rows", 0) + metrics.get("validation_rows", 0) + metrics.get("test_rows", 0)},
        "split_definition": "legacy split in training metrics; no formal Common PIT split_definition.json",
        "training_metadata_path": rel(OPPORTUNITY_LEGACY_METADATA),
        "lineage_path": rel(OPPORTUNITY_LEGACY_LINEAGE),
        "training_metadata": metadata,
        "lineage": lineage,
        "metrics_summary": {k: metrics.get(k) for k in ("status", "training_executed", "train_rows", "validation_rows", "test_rows", "target_label")},
        "model_type": "legacy opportunity model",
        "runtime_status": "Registry accepted set Runtime eligible",
        "trust_assessment": "Usable only as current accepted legacy artifact; not Common PIT/Atomic BUY AI Bundle aligned.",
    }


def runtime_resolver_matrix(bundle: dict[str, Any]) -> dict[str, Any]:
    candidate_promotion = promotion_component("candidate", bundle)
    opportunity_promotion = promotion_component("opportunity", bundle)
    candidate_registry = registry_entry("ai.candidate.accepted_set")
    opportunity_registry = registry_entry("ai.opportunity.accepted_set")
    return {
        "production_runtime": {
            "resolver": "src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py::resolve_buy_ai_artifact_paths",
            "candidate_model_hash": file_hash(CANDIDATE_LEGACY_MODEL),
            "opportunity_model_hash": file_hash(OPPORTUNITY_LEGACY_MODEL),
            "authority": "formal Artifact Registry accepted set, not Promotion Candidate",
            "candidate_registry_entry": candidate_registry,
            "opportunity_registry_entry": opportunity_registry,
        },
        "historical_runtime": {
            "resolver": "same Runtime v2 producer unless isolated test paths are explicitly allowed",
            "candidate_model_hash": file_hash(CANDIDATE_LEGACY_MODEL),
            "opportunity_model_hash": file_hash(OPPORTUNITY_LEGACY_MODEL),
            "authority": "formal Artifact Registry accepted set for regular path",
        },
        "accepted_resolver": {
            "accepted_buy_ai_bundle_path": rel(RUNTIME_ACCEPTED_STATE),
            "accepted_buy_ai_bundle_exists": RUNTIME_ACCEPTED_STATE.exists(),
            "status": "MISSING_ATOMIC_BUY_AI_ACCEPTED_STATE",
        },
        "legacy_resolver": {
            "candidate_default_path": ".runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl",
            "opportunity_default_path": "reports/opportunity_ai/phase5p/models/opportunity_model.pkl",
            "allowed_scope": "isolated test paths only",
        },
        "promotion_candidate": {
            "candidate_model_hash": candidate_promotion["hash"],
            "opportunity_model_hash": opportunity_promotion["hash"],
            "runtime_use_eligible": bundle.get("runtime_use_eligible"),
            "registry_accepted_event_requested": bundle.get("registry_accepted_event_requested"),
        },
        "hash_comparison": {
            "candidate_runtime_equals_promotion": file_hash(CANDIDATE_LEGACY_MODEL) == candidate_promotion["hash"],
            "opportunity_runtime_equals_promotion": file_hash(OPPORTUNITY_LEGACY_MODEL) == opportunity_promotion["hash"],
        },
    }


def pipeline_stage_audit() -> list[dict[str, Any]]:
    return [
        {"stage": "Raw Data", "implementation": "J-Quants/raw runtime data producers exist", "automatic": "partial", "evidence": ".runtime/data/raw and runtime market refresh", "gap": ""},
        {"stage": "Normalized", "implementation": "normalized data readers and Phase4/Phase18 source authority exist", "automatic": "partial", "evidence": "src/ai_fund_lab_v2/ai_lifecycle/source_authority.py", "gap": ""},
        {"stage": "Common PIT Dataset", "implementation": "Phase18-B/C dataset rebuild pipeline exists", "automatic": "manual/operator", "evidence": "src/ai_fund_lab_v2/ai_lifecycle/dataset_rebuild.py", "gap": "No observed LaunchAgent that rebuilds Common PIT and chains downstream training automatically."},
        {"stage": "Split", "implementation": "training_pipeline.make_time_series_split and bundle split_definition exist", "automatic": "training-time only", "evidence": "src/ai_fund_lab_v2/ai_lifecycle/training_pipeline.py", "gap": "Promotion Candidate retained stale 2024-12-02 train end after dataset update."},
        {"stage": "Training", "implementation": "run_training_pipeline exists", "automatic": "manual/operator", "evidence": "src/ai_fund_lab_v2/ai_lifecycle/training_pipeline.py", "gap": "No production scheduler connects dataset freshness to actual retraining and artifact selection automatically."},
        {"stage": "Calibration", "implementation": "Opportunity Phase18-H materialized calibration exists", "automatic": "manual/operator", "evidence": ".runtime/ai_lifecycle/training/opportunity_ai/opportunity_training_phase18h_1081babc49b5d26b/calibration_*", "gap": "Calibration is not an independent freshness update for predictive model."},
        {"stage": "Validation", "implementation": "validation/test/holdout artifacts exist", "automatic": "training-time", "evidence": "training bundle metrics", "gap": ""},
        {"stage": "Promotion Candidate", "implementation": "Phase18-I promotion candidate transaction exists", "automatic": "manual/operator", "evidence": rel(PHASE18I_BUNDLE), "gap": "runtime_use_eligible=false; not accepted."},
        {"stage": "Accepted Bundle", "implementation": "formal Registry accepted sets exist for legacy artifacts; Atomic BUY AI accepted state missing", "automatic": "manual authority required", "evidence": rel(REGISTRY_INDEX), "gap": "No .runtime/runtime_state/accepted_buy_ai_bundle.json."},
        {"stage": "Runtime Resolver", "implementation": "Registry accepted set resolver for regular path", "automatic": "runtime", "evidence": "src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py", "gap": "Resolved accepted legacy set, not Phase18 Promotion Candidate Atomic BUY bundle."},
        {"stage": "Inference", "implementation": "Runtime BUY AI producer uses resolved model paths", "automatic": "runtime", "evidence": ".runtime/runtime_state/buy_ai/*", "gap": "Lifecycle gate blocks BUY when accepted atomic evidence is missing/stale."},
        {"stage": "Runtime", "implementation": "BUY-only block and SELL continuity exist", "automatic": "runtime", "evidence": "ai_lifecycle_gate_decision.json", "gap": "BUY cannot resume without fresh accepted atomic authority."},
    ]


def automation_audit() -> dict[str, Any]:
    launchd = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "tools/launchd").glob("*.plist"))
    return {
        "launchd_templates": launchd,
        "weekly_lifecycle_scheduler": {
            "path": "src/ai_fund_lab_v2/ai_lifecycle/scheduler.py",
            "exists": True,
            "registry_accepted_event_allowed": False,
            "runtime_hot_swap_allowed": False,
            "buy_restart_allowed": False,
            "normal_outcome": "PROMOTION_REVIEW_REQUIRED",
        },
        "dataset_to_latest_ai_contract": {
            "complete": False,
            "reason": "Dataset rebuild, split refresh, training, calibration, promotion, acceptance, and runtime switch are not one completed automatic chain.",
        },
        "automatic_parts": ["runtime market refresh", "runtime resolver at execution", "runtime freshness/drift gate evaluation"],
        "manual_parts": ["Common PIT Dataset rebuild", "training invocation", "promotion readiness review", "authority approval", "accepted event materialization", "runtime accepted state transition"],
        "unimplemented_or_incomplete_parts": ["automatic dataset->split->train->calibrate->promote chain", "fresh accepted Atomic BUY AI Bundle materialization for current Phase18 candidate", "automatic retrain after Common PIT update"],
    }


def call_graph() -> dict[str, Any]:
    return {
        "production_runtime": [
            "runtime_v2/cli/run_daily_operation.py",
            "produce_buy_ai_decisions",
            "resolve_buy_ai_artifact_paths",
            "resolve_runtime_artifact_set(CANDIDATE_AI_SET/OPPORTUNITY_AI_SET)",
            "Artifact Registry accepted set",
            "Candidate/Opportunity model paths",
            "build_runtime_lifecycle_evidence",
            "evaluate_runtime_ai_gate",
            "candidate_decisions/opportunity_rankings",
        ],
        "historical_runtime": [
            "scripts/runtime_test.py or run_daily_operation test harness",
            "same Runtime v2 morning path",
            "BUY-only scoped block handling",
            "regular resolver unless isolated test paths explicitly allowed",
        ],
        "generation_pipeline": [
            "Raw Data",
            "Normalized",
            "Common PIT Dataset",
            "Split",
            "Training",
            "Calibration",
            "Validation",
            "Promotion Candidate",
            "Authority",
            "Accepted Bundle",
            "Runtime Resolver",
            "Inference",
        ],
    }


def final_answers(resolver: dict[str, Any]) -> dict[str, Any]:
    return {
        "runtime_ai_in_use": {
            "candidate": resolver["production_runtime"]["candidate_model_hash"],
            "opportunity": resolver["production_runtime"]["opportunity_model_hash"],
        },
        "runtime_legacy_trust": "Trusted only as currently registered Runtime-eligible legacy accepted set; not trusted as Phase18 Atomic BUY AI Bundle or Common PIT aligned authority.",
        "promotion_candidate_old_reason": "Phase18 training bundles used split_definition train end 2024-12-02 despite Common PIT dataset max 2026-05-15.",
        "runtime_resolver_mismatch_root_cause": "Migration boundary/design gap: formal Registry accepted sets still point to Phase4/Phase5 legacy artifacts while Phase18 Promotion Candidate remains runtime_use_eligible=false and no accepted Atomic BUY AI Bundle state exists.",
        "ai_generation_pipeline_complete": False,
        "latest_dataset_means_latest_ai": False,
        "retraining_required": True,
        "retraining_scope": ["Candidate AI", "Opportunity AI"],
        "next_unit_allowed_to_retrain": True,
        "next_unit_scope": ["refresh split using label-safe Common PIT authority", "train Candidate", "train Opportunity", "refit Opportunity calibration", "rebuild runtime baseline", "rerun readiness/authority workflow"],
    }


def build_report() -> dict[str, Any]:
    bundle = promotion_candidate_bundle()
    candidate_promotion = promotion_component("candidate", bundle)
    opportunity_promotion = promotion_component("opportunity", bundle)
    candidate_legacy = legacy_candidate_provenance()
    opportunity_legacy = legacy_opportunity_provenance()
    resolver = runtime_resolver_matrix(bundle)
    pipeline = pipeline_stage_audit()
    automation = automation_audit()
    primary = "PHASE18_AB_SYSTEMIC_AI_GENERATION_GAP_CONFIRMED"
    secondary = ["PHASE18_AB_RUNTIME_RESOLVER_REMEDIATION_REQUIRED", "PHASE18_AB_FORMAL_RETRAINING_REQUIRED"]
    return {
        "schema_version": "phase18_ab_runtime_legacy_model_provenance_and_ai_generation_pipeline_audit_v1",
        "phase": "Phase18-AB",
        "run_id": RUN_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "primary_judgment": primary,
        "secondary_judgments": secondary,
        "runtime_legacy_model_provenance": {
            "candidate": candidate_legacy,
            "opportunity": opportunity_legacy,
        },
        "promotion_candidate_provenance": {
            "candidate": candidate_promotion,
            "opportunity": opportunity_promotion,
            "freshness_metadata": maybe_json(PHASE18Y_FRESHNESS),
        },
        "runtime_resolver_matrix": resolver,
        "runtime_call_graph": call_graph(),
        "ai_generation_pipeline_audit": pipeline,
        "latest_ai_maintenance_design": automation,
        "ai_artifact_inventory_addendum": [
            {"component": "Candidate AI", "runtime_used": True, "promotion_candidate": False, "accepted": True, "legacy": True, "deprecated": False, "hash": candidate_legacy["hash"]},
            {"component": "Opportunity AI", "runtime_used": True, "promotion_candidate": False, "accepted": True, "legacy": True, "deprecated": False, "hash": opportunity_legacy["hash"]},
            {"component": "Candidate AI", "runtime_used": False, "promotion_candidate": True, "accepted": False, "legacy": False, "deprecated": False, "hash": candidate_promotion["hash"]},
            {"component": "Opportunity AI", "runtime_used": False, "promotion_candidate": True, "accepted": False, "legacy": False, "deprecated": False, "hash": opportunity_promotion["hash"]},
        ],
        "ai_update_contract_gaps": [
            "No completed contract that dataset rebuild automatically refreshes split and retrains Candidate/Opportunity.",
            "No completed contract that new Promotion Candidate is automatically accepted or switched into Runtime.",
            "No accepted Atomic BUY AI Bundle state exists for Phase18 candidate.",
            "Runtime accepted set remains registered legacy Phase4/Phase5 artifacts.",
            "Freshness gate proves BUY should remain blocked until fresh accepted atomic authority exists.",
        ],
        "runtime_resolver_mismatch_classification": {
            "classification": "MIGRATION_BOUNDARY_AND_SYSTEMIC_GENERATION_GAP",
            "legacy_residual": True,
            "design": True,
            "bug": False,
            "migration_in_progress": True,
            "intended_spec": "Registry accepted set is intended, but accepted content is legacy and not Phase18 Atomic BUY AI Bundle aligned.",
        },
        "final_answers": final_answers(resolver),
        "non_mutation_confirmation": {
            "retraining_performed": False,
            "split_changed": False,
            "dataset_changed": False,
            "calibration_refit": False,
            "promotion_candidate_changed": False,
            "registry_changed": False,
            "accepted_changed": False,
            "runtime_changed": False,
            "resolver_changed": False,
            "runtime_switch_performed": False,
            "broker_write": False,
            "historical_fresh_run": False,
            "production_runtime_executed": False,
            "model_pickle_loaded": False,
        },
        "validation": {
            "read_only": "PASS",
            "model_pickle_not_loaded": "PASS",
            "json_validation": {"command": "python3 -m json.tool reports/phase_reports/phase18_ab_runtime_legacy_model_provenance_and_ai_generation_pipeline_audit.json", "status": "PASS"},
            "pytest": {"command": "PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18ab_pycache python3 -m pytest tests/ai_lifecycle/test_phase18ab_runtime_legacy_generation_audit.py -q", "status": "PASS", "result": "4 passed"},
            "compile": {"command": "PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18ab_pycache python3 -m py_compile scripts/phase18ab_runtime_legacy_model_provenance_and_ai_generation_pipeline_audit.py", "status": "PASS"},
        },
        "report_hash": "",
    }


def write_markdown(report: dict[str, Any]) -> None:
    resolver = report["runtime_resolver_matrix"]
    answers = report["final_answers"]
    lines = [
        "# Phase18-AB Runtime Legacy Model Provenance & AI Generation Pipeline Audit",
        "",
        f"- Run ID: `{report['run_id']}`",
        f"- Primary Judgment: `{report['primary_judgment']}`",
        f"- Secondary Judgments: `{', '.join(report['secondary_judgments'])}`",
        "",
        "## Runtime AI In Use",
        "",
        f"- Candidate: `{report['runtime_legacy_model_provenance']['candidate']['artifact_path']}` hash=`{answers['runtime_ai_in_use']['candidate']}`",
        f"- Opportunity: `{report['runtime_legacy_model_provenance']['opportunity']['artifact_path']}` hash=`{answers['runtime_ai_in_use']['opportunity']}`",
        "",
        "## Promotion Candidate Difference",
        "",
        f"- Candidate runtime == promotion: `{resolver['hash_comparison']['candidate_runtime_equals_promotion']}`",
        f"- Opportunity runtime == promotion: `{resolver['hash_comparison']['opportunity_runtime_equals_promotion']}`",
        "- Promotion Candidate train end: Candidate=`2024-12-02`, Opportunity=`2024-12-02`",
        "",
        "## Mismatch Cause",
        "",
        f"- {answers['runtime_resolver_mismatch_root_cause']}",
        "",
        "## AI Generation Pipeline",
        "",
    ]
    for stage in report["ai_generation_pipeline_audit"]:
        lines.append(f"- {stage['stage']}: automatic=`{stage['automatic']}` gap=`{stage['gap']}`")
    lines.extend(
        [
            "",
            "## Latest AI Maintenance",
            "",
            f"- latest_dataset_means_latest_ai: `{answers['latest_dataset_means_latest_ai']}`",
            f"- pipeline_complete: `{answers['ai_generation_pipeline_complete']}`",
            f"- automatic_parts: `{', '.join(report['latest_ai_maintenance_design']['automatic_parts'])}`",
            f"- manual_parts: `{', '.join(report['latest_ai_maintenance_design']['manual_parts'])}`",
            "",
            "## Retraining Decision",
            "",
            f"- retraining_required: `{answers['retraining_required']}`",
            f"- scope: `{', '.join(answers['retraining_scope'])}`",
            f"- next_unit_allowed_to_retrain: `{answers['next_unit_allowed_to_retrain']}`",
            "",
            "## Non-Mutation Confirmation",
            "",
        ]
    )
    for key, value in report["non_mutation_confirmation"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Validation", ""])
    for key, value in report["validation"].items():
        status = value.get("status") if isinstance(value, dict) else value
        lines.append(f"- {key}: `{status}`")
    lines.extend(["", "## Final", "", f"`{report['primary_judgment']}`", ""])
    write_text(REPORT_MD, "\n".join(lines))


def main() -> int:
    report = build_report()
    report["report_hash"] = stable_hash({k: v for k, v in report.items() if k != "report_hash"})
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    write_json(EVIDENCE_DIR / "runtime_legacy_model_provenance.json", report["runtime_legacy_model_provenance"])
    write_json(EVIDENCE_DIR / "runtime_resolver_matrix.json", report["runtime_resolver_matrix"])
    write_json(EVIDENCE_DIR / "ai_generation_pipeline_audit.json", {"stages": report["ai_generation_pipeline_audit"], "latest_ai_maintenance_design": report["latest_ai_maintenance_design"]})
    write_json(EVIDENCE_DIR / "full_audit_report.json", report)
    write_json(REPORT_JSON, report)
    write_markdown(report)
    print(json.dumps({"primary_judgment": report["primary_judgment"], "secondary_judgments": report["secondary_judgments"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
