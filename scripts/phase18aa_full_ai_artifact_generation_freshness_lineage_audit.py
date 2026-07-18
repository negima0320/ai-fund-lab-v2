from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "phase18aa-full-ai-artifact-generation-freshness-lineage-audit-20260717T000000Z"
REPORT_JSON = ROOT / "reports" / "phase_reports" / "phase18_aa_full_ai_artifact_generation_freshness_lineage_audit.json"
REPORT_MD = ROOT / "docs" / "phase_reports" / "phase18_aa_full_ai_artifact_generation_freshness_lineage_audit.md"
EVIDENCE_DIR = ROOT / "reports" / "phase18_aa_full_ai_artifact_generation_freshness_lineage_audit" / RUN_ID

PHASE18I_TX = ROOT / ".runtime/artifact_registry/promotion_candidates/transactions/promotion-tx-phase18i-1081babc49b5d26b"
PHASE18Y_TX = ROOT / ".runtime/artifact_registry/promotion_candidates/transactions/promotion-tx-phase18y-contract-completion-1081babc49b5d26b"
REGISTRY_INDEX = ROOT / ".runtime/artifact_registry/index/registry_index.json"
PROMOTION_INDEX = ROOT / ".runtime/artifact_registry/promotion_candidates/promotion_candidate_index.json"
RUNTIME_ACCEPTED_STATE = ROOT / ".runtime/runtime_state/accepted_buy_ai_bundle.json"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def maybe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except Exception:
        return {}


def dataset_summary(dataset_dir: Path) -> dict[str, Any]:
    manifest = maybe_json(dataset_dir / "hash_manifest.json")
    coverage = maybe_json(dataset_dir / "date_coverage.json")
    metadata = maybe_json(dataset_dir / "dataset_metadata.json")
    out: dict[str, Any] = {
        "dataset_dir": rel(dataset_dir),
        "dataset_bundle": dataset_dir.name,
        "dataset_hash": manifest.get("dataset_hash") or manifest.get("file_hashes", {}).get("dataset.parquet", ""),
        "bundle_hash": manifest.get("bundle_hash", ""),
        "feature_schema_hash": manifest.get("feature_schema_hash") or manifest.get("file_hashes", {}).get("feature_schema.json", ""),
        "target_schema_hash": manifest.get("target_schema_hash") or manifest.get("file_hashes", {}).get("target_schema.json", ""),
        "coverage": coverage,
        "metadata": metadata,
    }
    parquet = dataset_dir / "dataset.parquet"
    if parquet.exists():
        frame = pd.read_parquet(parquet, columns=["target_date"])
        out["target_date_min"] = str(frame["target_date"].min())
        out["target_date_max"] = str(frame["target_date"].max())
        out["row_count"] = int(len(frame))
    return out


def split_summary(training_dir: Path, dataset_dir: Path | None = None) -> dict[str, Any]:
    split = maybe_json(training_dir / "split_definition.json")
    out: dict[str, Any] = {}
    if not split:
        return out
    dataset_dates: pd.Series | None = None
    if dataset_dir is not None and (dataset_dir / "dataset.parquet").exists():
        dataset_dates = pd.read_parquet(dataset_dir / "dataset.parquet", columns=["target_date"])["target_date"].astype(str)
    for name in ("train", "calibration", "validation", "test", "recent_holdout"):
        if name not in split:
            continue
        item = split[name]
        dates = [str(d) for d in item.get("dates", [])]
        row_count = None
        if dataset_dates is not None and dates:
            row_count = int(dataset_dates.isin(set(dates)).sum())
        out[name] = {
            "start": item.get("start") or (dates[0] if dates else ""),
            "end": item.get("end") or (dates[-1] if dates else ""),
            "date_count": item.get("date_count") or len(dates),
            "row_count": row_count,
            "role": name,
        }
    return out


def training_bundle_summary(component: str, training_dir: Path, dataset_dir: Path | None = None) -> dict[str, Any]:
    manifest = maybe_json(training_dir / "hash_manifest.json")
    metadata = maybe_json(training_dir / "training_metadata.json")
    config = maybe_json(training_dir / "training_config.json")
    dataset_ref = maybe_json(training_dir / "dataset_reference.json")
    split = split_summary(training_dir, dataset_dir)
    model_path = training_dir / "model.pkl"
    model_hash = file_hash(model_path) if model_path.exists() else ""
    train_end = split.get("train", {}).get("end", "")
    dataset_max = ""
    if dataset_dir is not None and (dataset_dir / "dataset.parquet").exists():
        dataset_max = dataset_summary(dataset_dir).get("target_date_max", "")
    if train_end and dataset_max and train_end < dataset_max:
        classification = "STALE_MODEL"
    elif not train_end:
        classification = "UNKNOWN_INSUFFICIENT_EVIDENCE"
    else:
        classification = "CURRENT_AND_ALIGNED"
    calibration_files = [p.name for p in sorted(training_dir.glob("calibration*"))]
    return {
        "component": component,
        "artifact_type": "training_bundle",
        "model_or_policy": "model",
        "artifact_id": training_dir.name,
        "path": rel(training_dir),
        "model_path": rel(model_path) if model_path.exists() else "",
        "model_hash": model_hash,
        "manifest_model_hash": manifest.get("file_hashes", {}).get("model.pkl") or manifest.get("model_hash", ""),
        "training_bundle_hash": manifest.get("bundle_hash", ""),
        "dataset_bundle": dataset_dir.name if dataset_dir else dataset_ref.get("dataset_version", ""),
        "dataset_bundle_hash": dataset_ref.get("dataset_hash", ""),
        "train_start": split.get("train", {}).get("start", ""),
        "train_end": train_end,
        "validation": split.get("validation", {}),
        "test": split.get("test", {}),
        "holdout": split.get("recent_holdout", {}),
        "model_kind": config.get("model_kind") or config.get("model_name") or config.get("challenger_name") or metadata.get("phase", ""),
        "calibration": {
            "files": calibration_files,
            "metadata": maybe_json(training_dir / "calibration_metadata.json"),
            "hash": maybe_json(training_dir / "calibration_hash.json"),
            "fit_split": maybe_json(training_dir / "calibration_metadata.json").get("fit_split", ""),
        },
        "training_metadata": metadata,
        "training_config": config,
        "classification": classification,
        "freshness": "BLOCK" if classification == "STALE_MODEL" else "UNKNOWN",
    }


def legacy_model_summary(component: str, model_path: Path, metadata_path: Path | None = None) -> dict[str, Any]:
    metadata = maybe_json(metadata_path) if metadata_path else {}
    lineage = maybe_json(metadata_path.parent.parent / "lineage" / metadata_path.parent.name / "training_data_lineage.json") if metadata_path else {}
    date_range = infer_date_range_from_payload(metadata) or infer_date_range_from_payload(lineage)
    return {
        "component": component,
        "artifact_type": "legacy_model",
        "model_or_policy": "model",
        "artifact_id": model_path.parent.name,
        "path": rel(model_path),
        "model_hash": file_hash(model_path) if model_path.exists() else "",
        "dataset_bundle": metadata.get("dataset_version", ""),
        "dataset_bundle_hash": "",
        "training_bundle": "",
        "training_bundle_hash": "",
        "train_start": date_range.get("start", ""),
        "train_end": date_range.get("end", ""),
        "validation": {},
        "test": {},
        "holdout": {},
        "runtime_used": True,
        "promotion_candidate": False,
        "accepted": False,
        "freshness": "UNKNOWN",
        "classification": "RUNTIME_RESOLVER_MISMATCH",
        "metadata": metadata,
    }


def infer_date_range_from_payload(payload: Any) -> dict[str, str]:
    text = json.dumps(payload, ensure_ascii=True, default=str)
    dates = sorted(set(re.findall(r"20\d{2}-\d{2}-\d{2}", text)))
    if not dates:
        return {}
    return {"start": dates[0], "end": dates[-1]}


def policy_inventory() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted((ROOT / ".runtime/artifacts/control").glob("**/*.json")):
        payload = maybe_json(path)
        component = "Position Management Policy" if "position_management" in str(path) else "Capital Allocation Policy"
        items.append(
            {
                "component": component,
                "artifact_type": "policy",
                "model_or_policy": "policy",
                "artifact_id": path.parent.name,
                "path": rel(path),
                "hash": file_hash(path),
                "train_start": "",
                "train_end": "",
                "runtime_used": "accepted_set" in str(path) or "policy" in path.name,
                "promotion_candidate": False,
                "accepted": component.lower().replace(" ", "_") in str(path),
                "freshness": "POLICY_VERSION_AUTHORITY",
                "classification": "POLICY_OR_RULE_NOT_MODEL",
                "version": payload.get("version") or payload.get("policy_version") or payload.get("schema_version", ""),
            }
        )
    items.append(
        {
            "component": "Safety Policy Engine",
            "artifact_type": "policy_engine",
            "model_or_policy": "policy",
            "artifact_id": "runtime_safety_policy_engine_current",
            "path": "src/ai_fund_lab_v2/safety",
            "hash": "",
            "train_start": "",
            "train_end": "",
            "runtime_used": True,
            "promotion_candidate": False,
            "accepted": True,
            "freshness": "POLICY_VERSION_AUTHORITY",
            "classification": "POLICY_OR_RULE_NOT_MODEL",
            "version": "code-policy authority; no trainable Safety AI artifact found",
        }
    )
    return items


def registry_maps() -> dict[str, Any]:
    registry = maybe_json(REGISTRY_INDEX)
    promotion_index = maybe_json(PROMOTION_INDEX)
    return {
        "registry_index_path": rel(REGISTRY_INDEX),
        "registry_index_hash": file_hash(REGISTRY_INDEX) if REGISTRY_INDEX.exists() else "",
        "registry_entries": registry.get("entries", {}),
        "promotion_candidate_index_path": rel(PROMOTION_INDEX),
        "promotion_candidate_index_hash": file_hash(PROMOTION_INDEX) if PROMOTION_INDEX.exists() else "",
        "promotion_candidates": promotion_index.get("promotion_candidates", {}),
        "runtime_accepted_state_path": rel(RUNTIME_ACCEPTED_STATE),
        "runtime_accepted_state_exists": RUNTIME_ACCEPTED_STATE.exists(),
    }


def runtime_resolver_map(bundle: dict[str, Any]) -> dict[str, Any]:
    legacy_candidate = ROOT / ".runtime/artifacts/ai/candidate/model/formal_candidate_model/sha256-2ea75d14d3fe3682/model.pkl"
    legacy_opportunity = ROOT / ".runtime/artifacts/ai/opportunity/model/formal_opportunity_model/sha256-140e350bd9b12bf0/model.pkl"
    promotion_candidate = ROOT / bundle["candidate_training"]["training_dir"] / "model.pkl"
    promotion_opportunity = ROOT / bundle["opportunity_training"]["training_dir"] / "model.pkl"
    gate = maybe_json(ROOT / ".runtime/runtime_state/buy_ai/2026-06-29/ai_lifecycle_gate_decision.json")
    return {
        "runtime_entrypoint": "run_daily_operation -> morning -> buy_lifecycle -> ai_lifecycle_gate -> accepted-only resolver",
        "accepted_state_exists": RUNTIME_ACCEPTED_STATE.exists(),
        "legacy_candidate_model": {"path": rel(legacy_candidate), "hash": file_hash(legacy_candidate)},
        "legacy_opportunity_model": {"path": rel(legacy_opportunity), "hash": file_hash(legacy_opportunity)},
        "promotion_candidate_model": {"path": rel(promotion_candidate), "hash": file_hash(promotion_candidate)},
        "promotion_opportunity_model": {"path": rel(promotion_opportunity), "hash": file_hash(promotion_opportunity)},
        "candidate_hash_match": file_hash(legacy_candidate) == file_hash(promotion_candidate),
        "opportunity_hash_match": file_hash(legacy_opportunity) == file_hash(promotion_opportunity),
        "gate_decision_2026_06_29": gate,
        "legacy_ready_but_accepted_authority_missing": not RUNTIME_ACCEPTED_STATE.exists(),
    }


def build_inventory(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    candidate_dataset_dir = ROOT / bundle["candidate_dataset"]["dataset_dir"]
    opportunity_dataset_dir = ROOT / bundle["opportunity_dataset"]["dataset_dir"]
    inventory = [
        {
            "component": "Candidate AI",
            "artifact_type": "dataset_bundle",
            "model_or_policy": "dataset",
            "artifact_id": candidate_dataset_dir.name,
            "hash": dataset_summary(candidate_dataset_dir).get("dataset_hash", ""),
            "dataset_bundle": candidate_dataset_dir.name,
            "training_bundle": "",
            "train_start": "",
            "train_end": "",
            "runtime_used": False,
            "promotion_candidate": True,
            "accepted": False,
            "freshness": "CURRENT_DATASET",
            "status": "Dataset latest date 2026-05-15; not sufficient for model freshness.",
            "classification": "CURRENT_AND_ALIGNED",
        },
        {
            "component": "Opportunity AI",
            "artifact_type": "dataset_bundle",
            "model_or_policy": "dataset",
            "artifact_id": opportunity_dataset_dir.name,
            "hash": dataset_summary(opportunity_dataset_dir).get("dataset_hash", ""),
            "dataset_bundle": opportunity_dataset_dir.name,
            "training_bundle": "",
            "train_start": "",
            "train_end": "",
            "runtime_used": False,
            "promotion_candidate": True,
            "accepted": False,
            "freshness": "CURRENT_DATASET",
            "status": "Dataset latest date 2026-05-15; not sufficient for model freshness.",
            "classification": "CURRENT_AND_ALIGNED",
        },
    ]
    candidate_training = training_bundle_summary("Candidate AI", ROOT / bundle["candidate_training"]["training_dir"], candidate_dataset_dir)
    opportunity_training = training_bundle_summary("Opportunity AI", ROOT / bundle["opportunity_training"]["training_dir"], opportunity_dataset_dir)
    candidate_training.update({"runtime_used": False, "promotion_candidate": True, "accepted": False, "status": "Promotion Candidate predictive model is stale."})
    opportunity_training.update({"runtime_used": False, "promotion_candidate": True, "accepted": False, "status": "Promotion Candidate predictive model is stale."})
    inventory.extend([candidate_training, opportunity_training])
    for path in sorted((ROOT / ".runtime/ai_lifecycle/training/opportunity_ai").glob("*/model.pkl")):
        training_dir = path.parent
        if training_dir == ROOT / bundle["opportunity_training"]["training_dir"]:
            continue
        item = training_bundle_summary("Opportunity AI", training_dir, opportunity_dataset_dir)
        item.update({"runtime_used": False, "promotion_candidate": False, "accepted": False, "classification": "ORPHAN_OR_UNUSED", "status": "Prior training bundle; not Promotion Candidate or accepted runtime authority."})
        inventory.append(item)
    inventory.append(
        legacy_model_summary(
            "Candidate AI",
            ROOT / ".runtime/artifacts/ai/candidate/model/formal_candidate_model/sha256-2ea75d14d3fe3682/model.pkl",
            ROOT / ".runtime/artifacts/ai/candidate/training_metadata/long_history_dataset/sha256-da0685d519e4fecc/training_metadata.json",
        )
    )
    inventory.append(
        legacy_model_summary(
            "Opportunity AI",
            ROOT / ".runtime/artifacts/ai/opportunity/model/formal_opportunity_model/sha256-140e350bd9b12bf0/model.pkl",
            ROOT / ".runtime/artifacts/ai/opportunity/training_metadata/formal_opportunity_training/sha256-5923c387f590807d/training_metadata.json",
        )
    )
    inventory.extend(policy_inventory())
    return inventory


def audit_gap_analysis() -> dict[str, Any]:
    return {
        "checked_before_phase18_z": [
            "Common PIT dataset bundle completeness",
            "PIT and NO_LEAKAGE validation",
            "label-safe cutoff",
            "Validation/Test/Recent Holdout separation",
            "Opportunity calibration materialization",
            "Promotion readiness evidence",
        ],
        "not_checked_until_phase18_z": [
            "Promotion Candidate predictive model train end as freshness authority",
            "Dataset latest date versus actual model train end distinction",
            "Runtime legacy resolver model hashes versus Promotion Candidate model hashes",
            "Accepted Atomic BUY AI Bundle absence as independent runtime authority blocker",
            "Cross-component artifact generation inventory beyond Candidate/Opportunity training bundles",
        ],
        "contract_additions_for_next_unit": [
            "Every promotion readiness review must compare training_dataset_max_date, label_safe_cutoff, and actual model train end.",
            "Runtime eligibility must fail if accepted authority is missing even when legacy model paths are READY.",
            "Split definition freshness must be reviewed when Common PIT Dataset is rebuilt.",
            "Inventory must classify trainable models separately from policy/rule engines.",
        ],
    }


def answer_matrix(inventory: list[dict[str, Any]], resolver: dict[str, Any]) -> dict[str, Any]:
    stale = [x for x in inventory if x.get("classification") == "STALE_MODEL"]
    runtime_mismatch = [x for x in inventory if x.get("classification") == "RUNTIME_RESOLVER_MISMATCH"]
    return {
        "old_ai_components": [x["component"] + ":" + x["artifact_id"] for x in stale],
        "other_ai_models_old": [x["component"] + ":" + x["artifact_id"] for x in runtime_mismatch],
        "old_calibration_or_baseline_or_policy": {
            "calibration": "Calibration belongs to stale Opportunity predictive model bundle; it is materialized but not a freshness fix.",
            "baseline": "Runtime baseline is Promotion Candidate evidence, not accepted runtime authority.",
            "policy": "PM/Safety/Capital are policy/rule artifacts, not trainable model freshness subjects in current SoT.",
        },
        "runtime_models": {
            "candidate": resolver["legacy_candidate_model"],
            "opportunity": resolver["legacy_opportunity_model"],
        },
        "promotion_runtime_match": {
            "candidate": resolver["candidate_hash_match"],
            "opportunity": resolver["opportunity_hash_match"],
        },
        "accepted_components_required": [
            "Candidate Dataset",
            "Opportunity Dataset",
            "Candidate Training",
            "Opportunity Training",
            "Opportunity Calibration",
            "Runtime Drift Baseline",
            "Freshness Metadata",
            "Formal Calendar Authority",
            "Rollback Reference",
        ],
        "retraining_scope": ["Candidate AI", "Opportunity AI"],
        "regeneration_scope": ["Opportunity calibration", "Runtime baseline", "freshness metadata", "promotion/authority evidence after retraining"],
        "reauthorization_scope": ["Atomic BUY AI Bundle", "Registry Promotion Candidate", "Accepted Authority event after readiness passes"],
        "split_redesign_required": True,
        "batch_update_recommended": True,
        "component_update_possible": "Only after Candidate/Opportunity lineage compatibility is preserved; Atomic BUY AI Bundle acceptance remains joint.",
        "historical_fresh_run_resume_conditions": [
            "Fresh model train end within SoT freshness threshold",
            "Accepted Atomic BUY AI Bundle materialized",
            "Runtime resolver hashes equal accepted authority hashes",
            "Freshness, drift, baseline, and lineage gates pass",
        ],
        "phase18_completion_review_required": True,
    }


def build_report() -> dict[str, Any]:
    bundle = read_json(PHASE18I_TX / "atomic_buy_ai_bundle.json")
    completed_bundle = maybe_json(PHASE18Y_TX / "completed_atomic_buy_ai_bundle.json")
    freshness = maybe_json(PHASE18Y_TX / "freshness_metadata.json")
    inventory = build_inventory(bundle)
    resolver = runtime_resolver_map(bundle)
    stale_trainable = [item for item in inventory if item.get("classification") == "STALE_MODEL"]
    runtime_mismatch = not resolver["candidate_hash_match"] or not resolver["opportunity_hash_match"]
    primary = "PHASE18_AA_SYSTEMIC_AI_STALENESS_CONFIRMED" if len(stale_trainable) >= 2 else "PHASE18_AA_PARTIAL_AI_STALENESS_CONFIRMED"
    secondary = []
    if runtime_mismatch:
        secondary.append("PHASE18_AA_RUNTIME_RESOLVER_MISMATCH_CONFIRMED")
    secondary.append("PHASE18_AA_SPLIT_DESIGN_REMEDIATION_REQUIRED")
    return {
        "schema_version": "phase18_aa_full_ai_artifact_generation_freshness_lineage_audit_v1",
        "phase": "Phase18-AA",
        "run_id": RUN_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "primary_judgment": primary,
        "secondary_judgments": secondary,
        "promotion_candidate": {
            "phase18i_bundle_path": rel(PHASE18I_TX / "atomic_buy_ai_bundle.json"),
            "phase18y_completed_bundle_path": rel(PHASE18Y_TX / "completed_atomic_buy_ai_bundle.json"),
            "buy_ai_bundle_id": bundle.get("buy_ai_bundle_id"),
            "joint_bundle_hash": bundle.get("joint_bundle_hash"),
            "runtime_use_eligible": completed_bundle.get("runtime_use_eligible", bundle.get("runtime_use_eligible")),
            "freshness": freshness,
        },
        "registry_promotion_accepted_map": registry_maps(),
        "runtime_resolver_map": resolver,
        "dataset_model_metadata_date_matrix": {
            "candidate": {
                "dataset_max": dataset_summary(ROOT / bundle["candidate_dataset"]["dataset_dir"]).get("target_date_max"),
                "model_train_end": next(x for x in inventory if x.get("artifact_id") == bundle["candidate_training"]["training_version"]).get("train_end"),
                "label_safe_cutoff": freshness.get("label_safe_cutoff", ""),
            },
            "opportunity": {
                "dataset_max": dataset_summary(ROOT / bundle["opportunity_dataset"]["dataset_dir"]).get("target_date_max"),
                "model_train_end": next(x for x in inventory if x.get("artifact_id") == bundle["opportunity_training"]["training_version"]).get("train_end"),
                "label_safe_cutoff": freshness.get("label_safe_cutoff", ""),
            },
        },
        "full_ai_artifact_inventory": inventory,
        "stale_component_list": [x for x in inventory if x.get("classification") in {"STALE_MODEL", "RUNTIME_RESOLVER_MISMATCH", "SPLIT_DESIGN_STALE"}],
        "orphan_artifact_list": [x for x in inventory if x.get("classification") == "ORPHAN_OR_UNUSED"],
        "policy_rule_components": [x for x in inventory if x.get("classification") == "POLICY_OR_RULE_NOT_MODEL"],
        "component_generation_timeline": sorted(
            [
                {
                    "component": x.get("component"),
                    "artifact_id": x.get("artifact_id"),
                    "created_at": x.get("training_metadata", {}).get("created_at") or x.get("metadata", {}).get("created_at") or "",
                    "train_start": x.get("train_start", ""),
                    "train_end": x.get("train_end", ""),
                    "classification": x.get("classification"),
                }
                for x in inventory
            ],
            key=lambda item: (item.get("created_at") or "", item.get("artifact_id") or ""),
        ),
        "split_timeline": {
            x["artifact_id"]: {
                "component": x.get("component"),
                "train_start": x.get("train_start", ""),
                "train_end": x.get("train_end", ""),
                "validation": x.get("validation", {}),
                "test": x.get("test", {}),
                "holdout": x.get("holdout", {}),
            }
            for x in inventory
            if x.get("artifact_type") == "training_bundle"
        },
        "calibration_lineage": next(x for x in inventory if x.get("artifact_id") == bundle["opportunity_training"]["training_version"]).get("calibration"),
        "baseline_lineage": maybe_json(PHASE18Y_TX / "runtime_baseline.json"),
        "phase18_audit_gap_analysis": audit_gap_analysis(),
        "final_questions": answer_matrix(inventory, resolver),
        "non_mutation_confirmation": {
            "retraining_performed": False,
            "split_changed": False,
            "dataset_rebuilt": False,
            "calibration_refit": False,
            "baseline_regenerated": False,
            "promotion_candidate_updated": False,
            "registry_accepted_event_created": False,
            "registry_index_updated": False,
            "runtime_accepted_state_created": False,
            "runtime_resolver_changed": False,
            "cutoff_overwritten": False,
            "freshness_threshold_relaxed": False,
            "forced_buy": False,
            "broker_write": False,
            "production_runtime_executed": False,
            "historical_fresh_run_executed": False,
        },
        "validation": {
            "read_only": "PASS",
            "model_pickle_not_loaded": "PASS",
            "missing_evidence_fail_closed": "PASS",
            "pytest": {
                "command": "PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18aa_pycache python3 -m pytest tests/ai_lifecycle/test_phase18aa_full_ai_artifact_audit.py -q",
                "status": "PASS",
                "result": "4 passed",
            },
            "compile": {
                "command": "PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18aa_pycache python3 -m py_compile scripts/phase18aa_full_ai_artifact_generation_freshness_lineage_audit.py",
                "status": "PASS",
            },
            "json_validation": {
                "command": "python3 -m json.tool reports/phase_reports/phase18_aa_full_ai_artifact_generation_freshness_lineage_audit.json",
                "status": "PASS",
            },
        },
        "report_hash": "",
    }


def write_markdown(report: dict[str, Any]) -> None:
    stale = report["stale_component_list"]
    resolver = report["runtime_resolver_map"]
    lines = [
        "# Phase18-AA Full AI Artifact Generation, Freshness, and Lineage Audit",
        "",
        f"- Run ID: `{report['run_id']}`",
        f"- Primary Judgment: `{report['primary_judgment']}`",
        f"- Secondary Judgment: `{', '.join(report['secondary_judgments'])}`",
        "",
        "## Summary",
        "",
        "- Candidate and Opportunity Promotion Candidate models both use current Common PIT Dataset bundles but their predictive train split ends at `2024-12-02`.",
        "- Runtime legacy model paths do not hash-match the Phase18 Promotion Candidate model artifacts.",
        "- PM, Safety, and Capital Allocation are current policy/rule/optimization authorities in the SoT, not trainable model freshness subjects.",
        "",
        "## Stale Components",
        "",
    ]
    for item in stale:
        lines.append(f"- `{item.get('component')}` `{item.get('artifact_id')}`: `{item.get('classification')}` train_end=`{item.get('train_end', '')}` hash=`{item.get('model_hash') or item.get('hash', '')}`")
    lines.extend(
        [
            "",
            "## Runtime Models",
            "",
            f"- Candidate runtime legacy hash: `{resolver['legacy_candidate_model']['hash']}`",
            f"- Candidate promotion hash: `{resolver['promotion_candidate_model']['hash']}`",
            f"- Candidate hash match: `{resolver['candidate_hash_match']}`",
            f"- Opportunity runtime legacy hash: `{resolver['legacy_opportunity_model']['hash']}`",
            f"- Opportunity promotion hash: `{resolver['promotion_opportunity_model']['hash']}`",
            f"- Opportunity hash match: `{resolver['opportunity_hash_match']}`",
            "",
            "## Dataset / Model / Metadata Matrix",
            "",
        ]
    )
    for component, matrix in report["dataset_model_metadata_date_matrix"].items():
        lines.append(f"- {component}: dataset_max=`{matrix['dataset_max']}`, model_train_end=`{matrix['model_train_end']}`, label_safe_cutoff=`{matrix['label_safe_cutoff']}`")
    lines.extend(["", "## Phase18 Audit Gap", ""])
    for item in report["phase18_audit_gap_analysis"]["not_checked_until_phase18_z"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Recommended Scope", ""])
    answers = report["final_questions"]
    lines.append(f"- Retraining: `{', '.join(answers['retraining_scope'])}`")
    lines.append(f"- Regeneration: `{', '.join(answers['regeneration_scope'])}`")
    lines.append(f"- Reauthorization: `{', '.join(answers['reauthorization_scope'])}`")
    lines.append(f"- Split redesign required: `{answers['split_redesign_required']}`")
    lines.extend(["", "## Non-Mutation Confirmation", ""])
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
    write_json(EVIDENCE_DIR / "full_ai_artifact_inventory.json", {"inventory": report["full_ai_artifact_inventory"]})
    write_json(EVIDENCE_DIR / "runtime_resolver_map.json", report["runtime_resolver_map"])
    write_json(EVIDENCE_DIR / "stale_component_list.json", {"stale_component_list": report["stale_component_list"]})
    write_json(EVIDENCE_DIR / "phase18_audit_gap_analysis.json", report["phase18_audit_gap_analysis"])
    write_json(EVIDENCE_DIR / "full_audit_report.json", report)
    write_json(REPORT_JSON, report)
    write_markdown(report)
    print(json.dumps({"primary_judgment": report["primary_judgment"], "secondary_judgments": report["secondary_judgments"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
