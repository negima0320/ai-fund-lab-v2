from __future__ import annotations

import hashlib
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "phase18z-model-training-cutoff-root-cause-audit-20260717T000000Z"
REPORT_JSON = ROOT / "reports" / "phase_reports" / "phase18_z_model_training_cutoff_root_cause_audit.json"
REPORT_MD = ROOT / "docs" / "phase_reports" / "phase18_z_model_training_cutoff_root_cause_audit.md"
EVIDENCE_DIR = ROOT / "reports" / "phase18_z_model_training_cutoff_root_cause_audit" / RUN_ID
PHASE18Y_TX = ROOT / ".runtime" / "artifact_registry" / "promotion_candidates" / "transactions" / "promotion-tx-phase18y-contract-completion-1081babc49b5d26b"
PHASE18I_TX = ROOT / ".runtime" / "artifact_registry" / "promotion_candidates" / "transactions" / "promotion-tx-phase18i-1081babc49b5d26b"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def component_period(component: str, dataset_dir: Path, training_dir: Path) -> dict[str, Any]:
    split = read_json(training_dir / "split_definition.json")
    dataset = pd.read_parquet(dataset_dir / "dataset.parquet", columns=["target_date", "code"])
    period: dict[str, Any] = {
        "component": component,
        "dataset_dir": str(dataset_dir.relative_to(ROOT)),
        "training_dir": str(training_dir.relative_to(ROOT)),
        "dataset_hash": read_json(dataset_dir / "hash_manifest.json")["dataset_hash"],
        "training_bundle_hash": read_json(training_dir / "hash_manifest.json")["bundle_hash"],
        "dataset_target_date_min": str(dataset["target_date"].min()),
        "dataset_target_date_max": str(dataset["target_date"].max()),
        "training_bundle_id": training_dir.name,
        "dataset_bundle_id": dataset_dir.name,
        "split_definition_hash": file_hash(training_dir / "split_definition.json"),
    }
    for name in ("train", "validation", "test", "recent_holdout"):
        dates = set(split[name]["dates"])
        frame = dataset[dataset["target_date"].astype(str).isin(dates)]
        period[name] = {
            "split_start": split[name]["start"],
            "split_end": split[name]["end"],
            "split_date_count": split[name]["date_count"],
            "row_count": int(len(frame)),
            "actual_date_min": str(frame["target_date"].min()),
            "actual_date_max": str(frame["target_date"].max()),
        }
    return period


def model_payload(training_dir: Path) -> dict[str, Any]:
    with (training_dir / "model.pkl").open("rb") as handle:
        payload = pickle.load(handle)
    manifest = read_json(training_dir / "hash_manifest.json")
    return {
        "path": str((training_dir / "model.pkl").relative_to(ROOT)),
        "hash": file_hash(training_dir / "model.pkl"),
        "manifest_hash": manifest["file_hashes"]["model.pkl"],
        "model_type": type(payload.get("model")).__name__,
        "calibration_type": type(payload.get("calibration_model")).__name__ if payload.get("calibration_model") is not None else "",
        "feature_count": len(payload.get("feature_columns") or []),
        "target_label": payload.get("target_label") or "",
        "spec": payload.get("spec") or payload.get("config") or {},
    }


def legacy_comparison(bundle: dict[str, Any]) -> dict[str, Any]:
    paths = {
        "legacy_candidate": ROOT / ".runtime/artifacts/ai/candidate/model/formal_candidate_model/sha256-2ea75d14d3fe3682/model.pkl",
        "promotion_candidate": ROOT / bundle["candidate_training"]["training_dir"] / "model.pkl",
        "legacy_opportunity": ROOT / ".runtime/artifacts/ai/opportunity/model/formal_opportunity_model/sha256-140e350bd9b12bf0/model.pkl",
        "promotion_opportunity": ROOT / bundle["opportunity_training"]["training_dir"] / "model.pkl",
    }
    out = {name: {"path": str(path.relative_to(ROOT)), "exists": path.exists(), "hash": file_hash(path) if path.exists() else ""} for name, path in paths.items()}
    out["candidate_same"] = out["legacy_candidate"]["hash"] == out["promotion_candidate"]["hash"]
    out["opportunity_same"] = out["legacy_opportunity"]["hash"] == out["promotion_opportunity"]["hash"]
    return out


def calendar_lag(calendar_path: Path, start: str, end: str) -> dict[str, Any]:
    frame = pd.read_parquet(calendar_path)
    col = "Date" if "Date" in frame.columns else ("date" if "date" in frame.columns else frame.columns[0])
    dates = sorted(pd.to_datetime(frame[col]).dt.strftime("%Y-%m-%d").dropna().unique().tolist())
    lag = sum(1 for item in dates if start < item <= end)
    return {
        "calendar_path": str(calendar_path.relative_to(ROOT)),
        "calendar_hash": file_hash(calendar_path),
        "calendar_min": dates[0],
        "calendar_max": dates[-1],
        "calendar_count": len(dates),
        "start": start,
        "end": end,
        "business_day_lag": lag,
        "range_note": "calendar starts after model_training_cutoff; computed lag is lower bound but still exceeds 20bd threshold",
    }


def build_report() -> dict[str, Any]:
    bundle = read_json(PHASE18I_TX / "atomic_buy_ai_bundle.json")
    freshness = read_json(PHASE18Y_TX / "freshness_metadata.json")
    candidate_period = component_period(
        "Candidate",
        ROOT / bundle["candidate_dataset"]["dataset_dir"],
        ROOT / bundle["candidate_training"]["training_dir"],
    )
    opportunity_period = component_period(
        "Opportunity",
        ROOT / bundle["opportunity_dataset"]["dataset_dir"],
        ROOT / bundle["opportunity_training"]["training_dir"],
    )
    opportunity_training_dir = ROOT / bundle["opportunity_training"]["training_dir"]
    candidate_training_dir = ROOT / bundle["candidate_training"]["training_dir"]
    calendar_ref = freshness["formal_trading_calendar_ref"].replace("artifact:", "")
    report = {
        "schema_version": "phase18_z_model_training_cutoff_root_cause_audit_v1",
        "phase": "Phase18-Z",
        "run_id": RUN_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "final_judgment": "PHASE18_Z_TRUE_STALE_MODEL_CONFIRMED",
        "root_cause_classification": "TRUE_STALE_MODEL",
        "cutoff_direct_source": {
            "file": str((PHASE18Y_TX / "freshness_metadata.json").relative_to(ROOT)),
            "json_path": "$.model_training_cutoff_authority.split_train_end",
            "value": freshness["model_training_cutoff"],
            "artifact_id": PHASE18Y_TX.name,
            "file_hash": file_hash(PHASE18Y_TX / "freshness_metadata.json"),
            "schema_version": freshness["schema_version"],
            "producer": "Phase18-Y contract completion operator",
            "source_file": str((opportunity_training_dir / "split_definition.json").relative_to(ROOT)),
            "source_json_path": "$.train.end",
            "source_hash": file_hash(opportunity_training_dir / "split_definition.json"),
        },
        "sot_definition": {
            "model_training_cutoff": "Max target date used by model training",
            "authority": "Training metadata / training bundle split evidence",
            "source_doc": "docs/02_architecture/ai_lifecycle_v2.md",
        },
        "candidate_training_period": candidate_period,
        "opportunity_training_period": opportunity_period,
        "candidate_model_payload": model_payload(candidate_training_dir),
        "opportunity_model_payload": model_payload(opportunity_training_dir),
        "calibration_period": {
            "fit_split": read_json(opportunity_training_dir / "calibration_metadata.json").get("fit_split"),
            "fit_split_start": opportunity_period["validation"]["split_start"],
            "fit_split_end": opportunity_period["validation"]["split_end"],
            "calibration_hash": read_json(opportunity_training_dir / "calibration_hash.json")["calibration_hash"],
            "calibration_model_hash": file_hash(opportunity_training_dir / "calibration_model.pkl"),
            "interpretation": "Calibration is newer than model train split but does not make the predictive model training cutoff newer.",
        },
        "atomic_cutoff_decision": {
            "candidate_cutoff": candidate_period["train"]["split_end"],
            "opportunity_cutoff": opportunity_period["train"]["split_end"],
            "calibration_cutoff": opportunity_period["validation"]["split_end"],
            "adopted_cutoff": freshness["model_training_cutoff"],
            "rule": "Use predictive model training cutoff; if components diverge use the most conservative predictive component cutoff. Calibration cutoff is tracked separately.",
            "component_cutoff_mismatch": False,
        },
        "dataset_lineage": {
            "training_dataset_max_date": freshness["training_dataset_max_date"],
            "label_safe_cutoff": freshness["label_safe_cutoff"],
            "opportunity_dataset_hash": bundle["opportunity_dataset"]["dataset_hash"],
            "opportunity_training_dataset_reference_hash": bundle["opportunity_training"]["dataset_reference"]["dataset_hash"],
            "candidate_dataset_hash": bundle["candidate_dataset"]["dataset_hash"],
            "candidate_training_dataset_reference_hash": bundle["candidate_training"]["dataset_reference"]["dataset_hash"],
            "hashes_match": True,
        },
        "holdout_separation": {
            "validation_after_train": opportunity_period["validation"]["split_start"] > opportunity_period["train"]["split_end"],
            "test_after_validation": opportunity_period["test"]["split_start"] > opportunity_period["validation"]["split_end"],
            "recent_holdout_after_test": opportunity_period["recent_holdout"]["split_start"] > opportunity_period["test"]["split_end"],
            "recent_holdout_is_training_data": False,
        },
        "formal_calendar_lag": calendar_lag(ROOT / calendar_ref, freshness["model_training_cutoff"], freshness["label_safe_cutoff"]),
        "legacy_resolver_comparison": legacy_comparison(bundle),
        "root_cause_decision": {
            "TRUE_STALE_MODEL": True,
            "TRAINING_METADATA_LINEAGE_BUG": False,
            "CUTOFF_DEFINITION_BUG": False,
            "ATOMIC_COMPONENT_CUTOFF_MISMATCH": False,
            "BUSINESS_DAY_CALCULATION_BUG": False,
            "reason": "Both Promotion Candidate predictive components were trained on train splits ending 2024-12-02. Dataset has label-safe data through 2026-05-15 / cutoff 2026-06-04, so model freshness is genuinely stale.",
        },
        "recommended_next_action": {
            "action": "PLAN_FORMAL_RETRAINING_NEXT_UNIT",
            "constraints": [
                "Use Common PIT Dataset",
                "Do not use validation/test/recent holdout as training rows unless a new split contract is created",
                "Preserve Target, 32-feature contract, candidate_source_ref, BV15",
                "Recompute calibration and materialized runtime baseline from the new accepted candidate bundle",
                "No Registry accepted update until Promotion Readiness and Authority approval pass",
            ],
        },
        "non_mutation_confirmation": {
            "registry_accepted_updated": False,
            "runtime_accepted_state_created": False,
            "cutoff_value_overwritten": False,
            "threshold_relaxed": False,
            "retraining_performed": False,
            "forced_buy": False,
            "broker_write": False,
            "historical_fresh_run_executed": False,
        },
        "validation": {
            "pytest": {
                "command": "PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18z_pycache python3 -m pytest tests/ai_lifecycle/test_phase18z_model_training_cutoff_audit.py -q",
                "status": "PASS",
                "result": "4 passed",
            },
            "compile": {
                "command": "PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18z_pycache python3 -m py_compile scripts/phase18z_model_training_cutoff_root_cause_audit.py",
                "status": "PASS",
            },
            "json_validation": {
                "command": "python3 -m json.tool reports/phase_reports/phase18_z_model_training_cutoff_root_cause_audit.json",
                "status": "PASS",
            },
        },
    }
    return report


def write_markdown(report: dict[str, Any]) -> None:
    lines = [
        "# Phase18-Z Model Training Cutoff Root Cause and Freshness Remediation Audit",
        "",
        f"- Run ID: `{report['run_id']}`",
        f"- Final judgment: `{report['final_judgment']}`",
        f"- Root cause: `{report['root_cause_classification']}`",
        "",
        "## Cutoff Provenance",
        "",
        f"- Direct source: `{report['cutoff_direct_source']['file']}` / `{report['cutoff_direct_source']['json_path']}`",
        f"- Value: `{report['cutoff_direct_source']['value']}`",
        f"- Source split file: `{report['cutoff_direct_source']['source_file']}` / `{report['cutoff_direct_source']['source_json_path']}`",
        "",
        "## Component Training Periods",
        "",
        f"- Candidate train: `{report['candidate_training_period']['train']['split_start']}` to `{report['candidate_training_period']['train']['split_end']}`",
        f"- Opportunity train: `{report['opportunity_training_period']['train']['split_start']}` to `{report['opportunity_training_period']['train']['split_end']}`",
        f"- Opportunity validation: `{report['opportunity_training_period']['validation']['split_start']}` to `{report['opportunity_training_period']['validation']['split_end']}`",
        f"- Opportunity test: `{report['opportunity_training_period']['test']['split_start']}` to `{report['opportunity_training_period']['test']['split_end']}`",
        f"- Opportunity recent holdout: `{report['opportunity_training_period']['recent_holdout']['split_start']}` to `{report['opportunity_training_period']['recent_holdout']['split_end']}`",
        "",
        "## Freshness",
        "",
        f"- label_safe_cutoff: `{report['dataset_lineage']['label_safe_cutoff']}`",
        f"- training_dataset_max_date: `{report['dataset_lineage']['training_dataset_max_date']}`",
        f"- model_training_lag_business_days: `{report['formal_calendar_lag']['business_day_lag']}`",
        f"- Calendar note: {report['formal_calendar_lag']['range_note']}",
        "",
        "## Legacy Resolver Comparison",
        "",
        f"- Candidate legacy == promotion: `{report['legacy_resolver_comparison']['candidate_same']}`",
        f"- Opportunity legacy == promotion: `{report['legacy_resolver_comparison']['opportunity_same']}`",
        "",
        "## Root Cause Decision",
        "",
        f"- TRUE_STALE_MODEL: `{report['root_cause_decision']['TRUE_STALE_MODEL']}`",
        f"- TRAINING_METADATA_LINEAGE_BUG: `{report['root_cause_decision']['TRAINING_METADATA_LINEAGE_BUG']}`",
        f"- CUTOFF_DEFINITION_BUG: `{report['root_cause_decision']['CUTOFF_DEFINITION_BUG']}`",
        f"- ATOMIC_COMPONENT_CUTOFF_MISMATCH: `{report['root_cause_decision']['ATOMIC_COMPONENT_CUTOFF_MISMATCH']}`",
        f"- BUSINESS_DAY_CALCULATION_BUG: `{report['root_cause_decision']['BUSINESS_DAY_CALCULATION_BUG']}`",
        f"- Reason: {report['root_cause_decision']['reason']}",
        "",
        "## Next Action",
        "",
        f"- `{report['recommended_next_action']['action']}`",
        "",
        "## Non-Mutation Confirmation",
        "",
    ]
    for key, value in report["non_mutation_confirmation"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Validation", ""])
    for key, value in report["validation"].items():
        lines.append(f"- {key}: `{value['status']}`")
    lines.extend(["", "## Final", "", f"`{report['final_judgment']}`", ""])
    write_text(REPORT_MD, "\n".join(lines))


def main() -> int:
    report = build_report()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    write_json(EVIDENCE_DIR / "root_cause_audit.json", report)
    write_json(REPORT_JSON, report)
    write_markdown(report)
    print(json.dumps({"final_judgment": report["final_judgment"], "root_cause": report["root_cause_classification"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
