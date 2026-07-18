from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

_TRAINING_SPEC = importlib.util.spec_from_file_location("phase18y_training_pipeline", SRC / "ai_fund_lab_v2" / "ai_lifecycle" / "training_pipeline.py")
assert _TRAINING_SPEC is not None and _TRAINING_SPEC.loader is not None
_TRAINING_MODULE = importlib.util.module_from_spec(_TRAINING_SPEC)
sys.modules[_TRAINING_SPEC.name] = _TRAINING_MODULE
_TRAINING_SPEC.loader.exec_module(_TRAINING_MODULE)
transform_features = _TRAINING_MODULE.transform_features


RUN_ID = "phase18y-contract-completion-20260717T000000Z"
SOURCE_TX_ID = "promotion-tx-phase18i-1081babc49b5d26b"
SUPERSEDING_TX_ID = "promotion-tx-phase18y-contract-completion-1081babc49b5d26b"
SOURCE_TX_DIR = ROOT / ".runtime" / "artifact_registry" / "promotion_candidates" / "transactions" / SOURCE_TX_ID
TX_DIR = ROOT / ".runtime" / "artifact_registry" / "promotion_candidates" / "transactions" / SUPERSEDING_TX_ID
REPORT_MD = ROOT / "docs" / "phase_reports" / "phase18_y_accepted_atomic_buy_ai_bundle_contract_completion.md"
REPORT_JSON = ROOT / "reports" / "phase_reports" / "phase18_y_accepted_atomic_buy_ai_bundle_contract_completion.json"
EVIDENCE_DIR = ROOT / "reports" / "phase18_y_accepted_atomic_buy_ai_bundle_contract_completion" / RUN_ID
ACCEPTED_STATE = ROOT / ".runtime" / "runtime_state" / "accepted_buy_ai_bundle.json"
REGISTRY_EVENTS = ROOT / ".runtime" / "artifact_registry" / "events" / "registry_events.jsonl"
REGISTRY_INDEX = ROOT / ".runtime" / "artifact_registry" / "index" / "registry_index.json"


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def source_snapshot() -> dict[str, Any]:
    return {
        "registry_events_hash": file_hash(REGISTRY_EVENTS),
        "registry_index_hash": file_hash(REGISTRY_INDEX),
        "accepted_state_exists": ACCEPTED_STATE.exists(),
        "accepted_state_hash": file_hash(ACCEPTED_STATE),
    }


def load_source_bundle() -> dict[str, Any]:
    return read_json(SOURCE_TX_DIR / "atomic_buy_ai_bundle.json")


def split_frames(dataset: pd.DataFrame, split: dict[str, Any]) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for name in ("train", "validation", "test", "recent_holdout"):
        dates = set(split[name]["dates"])
        out[name] = dataset[dataset["target_date"].astype(str).isin(dates)].copy()
    return out


def derive_model_training_cutoff(training_dir: Path) -> dict[str, Any]:
    split = read_json(training_dir / "split_definition.json")
    spec = read_json(training_dir / "training_config.json")
    train_end = str(split["train"]["end"])
    window = str(spec.get("window_name") or "")
    if window == "rolling_3y":
        cutoff = train_end
        authority = "split_definition.train.end with selected rolling_3y training window"
    elif window in {"full_history", "recent_weighted"}:
        cutoff = train_end
        authority = "split_definition.train.end with selected training window"
    else:
        cutoff = train_end
        authority = "split_definition.train.end"
    return {
        "model_training_cutoff": cutoff,
        "authority": authority,
        "training_config": spec,
        "split_train_start": split["train"]["start"],
        "split_train_end": train_end,
        "split_train_date_count": split["train"]["date_count"],
    }


def build_materialized_baseline(bundle: dict[str, Any]) -> dict[str, Any]:
    dataset_dir = ROOT / bundle["opportunity_dataset"]["dataset_dir"]
    training_dir = ROOT / bundle["opportunity_training"]["training_dir"]
    dataset = pd.read_parquet(dataset_dir / "dataset.parquet")
    split = read_json(training_dir / "split_definition.json")
    frames = split_frames(dataset, split)
    baseline_frame = frames["recent_holdout"].sort_values(["target_date", "code"]).copy()
    with (training_dir / "model.pkl").open("rb") as handle:
        model_payload = pickle.load(handle)
    feature_columns = list(model_payload["feature_columns"])
    matrix = transform_features(baseline_frame, feature_columns, model_payload["preprocessing"])
    raw = model_payload["model"].predict(matrix)
    calibration_model = model_payload.get("calibration_model")
    if calibration_model is not None:
        scores = calibration_model.predict(raw)
    else:
        scores = raw
    baseline_frame["score"] = scores
    feature_source = "feature__candidate_score" if "feature__candidate_score" in baseline_frame.columns else feature_columns[0]
    prediction_values = [round(float(value), 10) for value in baseline_frame["score"].astype(float).tolist()]
    feature_values = [round(float(value), 10) for value in pd.to_numeric(baseline_frame[feature_source], errors="coerce").fillna(0.0).astype(float).tolist()]
    payload = {
        "schema_version": "accepted_runtime_materialized_baseline.v1",
        "baseline_identity": f"{bundle['buy_ai_bundle_id']}:recent_holdout_materialized_baseline",
        "baseline_date_range": {
            "authority_split": "recent_holdout",
            "start": str(split["recent_holdout"]["start"]),
            "end": str(split["recent_holdout"]["end"]),
        },
        "row_count": int(len(baseline_frame)),
        "prediction_distribution_values": prediction_values,
        "feature_distribution_values": feature_values,
        "feature_distribution_source": feature_source,
        "candidate_population": int(len(baseline_frame)),
        "positive_coverage": float((baseline_frame["score"] > 0).mean()) if len(baseline_frame) else 0.0,
        "accepted_bundle_ref": "",
        "lineage": {
            "source": "Phase18-H training bundle recent_holdout predictions",
            "dataset_dir": str((ROOT / bundle["opportunity_dataset"]["dataset_dir"]).relative_to(ROOT)),
            "training_dir": str(training_dir.relative_to(ROOT)),
            "model_hash": bundle["opportunity_training"]["model_hash"],
            "training_bundle_hash": bundle["opportunity_training"]["bundle_hash"],
            "dataset_hash": bundle["opportunity_dataset"]["dataset_hash"],
            "split_definition_hash": file_hash(training_dir / "split_definition.json"),
            "model_artifact_hash": file_hash(training_dir / "model.pkl"),
            "calibration_model_hash": file_hash(training_dir / "calibration_model.pkl"),
            "current_runtime_evidence_used": False,
            "paper_ledger_used": False,
            "backtest_pnl_used": False,
            "future_rows_used": False,
        },
    }
    payload["baseline_hash"] = stable_hash({key: value for key, value in payload.items() if key != "baseline_hash"})
    return payload


def build_freshness_metadata(bundle: dict[str, Any], *, model_cutoff: dict[str, Any]) -> dict[str, Any]:
    dataset_meta = read_json(ROOT / bundle["opportunity_dataset"]["dataset_dir"] / "dataset_metadata.json")
    calendar = dataset_meta["input_artifacts"]["trading_calendar"]
    label_safe = dataset_meta["label_safe_cutoff"]["label_safe_cutoff"]
    training_dataset_max = dataset_meta["input_artifacts"]["opportunity_source"]["max_target_date"]
    payload = {
        "schema_version": "accepted_runtime_freshness_metadata.v1",
        "training_dataset_max_date": training_dataset_max,
        "label_safe_cutoff": label_safe,
        "model_training_cutoff": model_cutoff["model_training_cutoff"],
        "model_training_cutoff_authority": model_cutoff,
        "model_accepted_at_authority": "set_by_registry_accepted_event_at_authority_approval",
        "formal_trading_calendar_ref": calendar["source_ref"],
        "formal_trading_calendar_identity": stable_hash(calendar),
        "formal_trading_calendar_hash": calendar["content_hash"],
        "dataset_metadata_ref": str((ROOT / bundle["opportunity_dataset"]["dataset_dir"] / "dataset_metadata.json").relative_to(ROOT)),
        "source_refs": {
            "opportunity_dataset": bundle["opportunity_dataset"]["dataset_dir"],
            "opportunity_training": bundle["opportunity_training"]["training_dir"],
        },
    }
    payload["freshness_metadata_hash"] = stable_hash({key: value for key, value in payload.items() if key != "freshness_metadata_hash"})
    return payload


def business_day_diff(calendar_path: Path, start: str, end: str) -> int:
    frame = pd.read_parquet(calendar_path)
    col = "Date" if "Date" in frame.columns else ("date" if "date" in frame.columns else frame.columns[0])
    dates = sorted(pd.to_datetime(frame[col]).dt.strftime("%Y-%m-%d").dropna().unique().tolist())
    if end < start:
        return -business_day_diff(calendar_path, end, start)
    return sum(1 for item in dates if start < item <= end)


def validate_pre_acceptance(bundle: dict[str, Any], baseline: dict[str, Any], freshness: dict[str, Any]) -> dict[str, Any]:
    calendar_ref = str(freshness["formal_trading_calendar_ref"]).replace("artifact:", "")
    calendar_path = ROOT / calendar_ref
    lag = business_day_diff(calendar_path, freshness["model_training_cutoff"], freshness["label_safe_cutoff"])
    checks = {
        "bundle_hash": "PASS" if bundle.get("joint_bundle_hash") else "FAIL",
        "baseline_hash": "PASS" if baseline["baseline_hash"] == stable_hash({k: v for k, v in baseline.items() if k != "baseline_hash"}) else "FAIL",
        "baseline_not_current_runtime": "PASS" if baseline["lineage"]["current_runtime_evidence_used"] is False else "FAIL",
        "baseline_row_count": "PASS" if baseline["row_count"] > 0 and len(baseline["prediction_distribution_values"]) == baseline["row_count"] else "FAIL",
        "calendar_authority": "PASS" if calendar_path.exists() and str(freshness["formal_trading_calendar_ref"]) != "weekday_fallback" else "FAIL",
        "model_training_cutoff_materialized": "PASS" if freshness.get("model_training_cutoff") else "FAIL",
        "model_training_lag_business_days": lag,
        "model_training_lag_status": "PASS" if 0 <= lag <= 20 else "BLOCK",
        "rollback_ref": "PASS" if bundle.get("rollback_reference") else "FAIL",
    }
    overall = "PASS" if all(value == "PASS" for key, value in checks.items() if key != "model_training_lag_business_days") else "BLOCK"
    return {"status": overall, "checks": checks}


def build_completed_transaction() -> dict[str, Any]:
    before = source_snapshot()
    source_bundle = load_source_bundle()
    TX_DIR.mkdir(parents=True, exist_ok=True)
    baseline = build_materialized_baseline(source_bundle)
    baseline_path = TX_DIR / "runtime_baseline.json"
    write_json(baseline_path, baseline)
    model_cutoff = derive_model_training_cutoff(ROOT / source_bundle["opportunity_training"]["training_dir"])
    freshness = build_freshness_metadata(source_bundle, model_cutoff=model_cutoff)
    freshness_path = TX_DIR / "freshness_metadata.json"
    write_json(freshness_path, freshness)
    completed_bundle = dict(source_bundle)
    completed_bundle.update(
        {
            "schema_version": "buy_ai_promotion_candidate_bundle.v2.contract_completed",
            "supersedes_transaction_id": SOURCE_TX_ID,
            "contract_completion_transaction_id": SUPERSEDING_TX_ID,
            "runtime_baseline_ref": "runtime_baseline.json",
            "freshness_metadata_ref": "freshness_metadata.json",
            "runtime_use_eligible": False,
            "registry_accepted_event_requested": False,
            "contract_completion_hash": "",
        }
    )
    validation = validate_pre_acceptance(completed_bundle, baseline, freshness)
    eligibility = {
        "schema_version": "promotion_candidate_runtime_eligibility_decision.v1",
        "decision": "RUNTIME_USE_ELIGIBILITY_BLOCKED" if validation["status"] != "PASS" else "RUNTIME_USE_ELIGIBLE",
        "runtime_use_eligible": validation["status"] == "PASS",
        "registry_accepted_event_requested": validation["status"] == "PASS",
        "reason": "pre_acceptance_validation_blocked" if validation["status"] != "PASS" else "all_pre_acceptance_contracts_pass",
        "validation": validation,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if eligibility["runtime_use_eligible"]:
        completed_bundle["runtime_use_eligible"] = True
        completed_bundle["registry_accepted_event_requested"] = True
    completed_bundle["contract_completion_hash"] = stable_hash({k: v for k, v in completed_bundle.items() if k != "contract_completion_hash"})
    write_json(TX_DIR / "completed_atomic_buy_ai_bundle.json", completed_bundle)
    write_json(TX_DIR / "runtime_eligibility_decision.json", eligibility)
    authority_review = {
        "schema_version": "accepted_event_authority_review.v1",
        "approval_scope": "ACCEPTED_EVENT_PRECHECK_ONLY" if validation["status"] != "PASS" else "REGISTRY_ACCEPTED_EVENT",
        "registry_accepted_event_authorized": validation["status"] == "PASS",
        "authorized_bundle_id": completed_bundle["buy_ai_bundle_id"],
        "authorized_bundle_hash": completed_bundle["joint_bundle_hash"],
        "contract_completion_hash": completed_bundle["contract_completion_hash"],
        "reviewer": "AI Lifecycle Authority Simulator Phase18-Y",
        "authority_identity": "Phase18-Y Accepted Atomic BUY AI Bundle Contract Completion Authority",
        "evidence_refs": [
            str(baseline_path.relative_to(ROOT)),
            str(freshness_path.relative_to(ROOT)),
            str((TX_DIR / "runtime_eligibility_decision.json").relative_to(ROOT)),
        ],
        "approval_timestamp": datetime.now(timezone.utc).isoformat(),
        "rollback_previous_accepted_ref": completed_bundle.get("rollback_reference"),
        "blocking_items": [] if validation["status"] == "PASS" else ["model_training_lag_status"],
    }
    write_json(TX_DIR / "accepted_event_authority_review.json", authority_review)
    after = source_snapshot()
    final = "PHASE18_Y_CONTRACT_COMPLETION_COMPLETE" if validation["status"] == "PASS" else "PHASE18_Y_CONTRACT_COMPLETION_BLOCKED"
    report = {
        "schema_version": "phase18_y_contract_completion_report_v1",
        "phase": "Phase18-Y",
        "run_id": RUN_ID,
        "source_transaction_id": SOURCE_TX_ID,
        "superseding_transaction_id": SUPERSEDING_TX_ID,
        "final_judgment": final,
        "contract_completion_status": validation["status"],
        "materialized_runtime_baseline": {
            "path": str(baseline_path.relative_to(ROOT)),
            "baseline_hash": baseline["baseline_hash"],
            "baseline_identity": baseline["baseline_identity"],
            "row_count": baseline["row_count"],
            "date_range": baseline["baseline_date_range"],
            "current_runtime_evidence_used": False,
        },
        "freshness_metadata": {
            "path": str(freshness_path.relative_to(ROOT)),
            "model_training_cutoff": freshness["model_training_cutoff"],
            "label_safe_cutoff": freshness["label_safe_cutoff"],
            "training_dataset_max_date": freshness["training_dataset_max_date"],
            "formal_trading_calendar_ref": freshness["formal_trading_calendar_ref"],
            "model_training_lag_business_days": validation["checks"]["model_training_lag_business_days"],
            "model_training_lag_status": validation["checks"]["model_training_lag_status"],
        },
        "eligibility_decision": eligibility,
        "authority_review": authority_review,
        "pre_acceptance_validation": validation,
        "accepted_state_materialized": False,
        "registry_accepted_event_written": False,
        "registry_index_updated": False,
        "runtime_accepted_state_created": False,
        "authority_snapshot_before": before,
        "authority_snapshot_after": after,
        "registry_unchanged": before["registry_events_hash"] == after["registry_events_hash"] and before["registry_index_hash"] == after["registry_index_hash"],
        "runtime_accepted_state_unchanged": before["accepted_state_exists"] == after["accepted_state_exists"] and before["accepted_state_hash"] == after["accepted_state_hash"],
        "prohibited_actions": {
            "phase18j_report_value_copied": False,
            "synthetic_baseline": False,
            "current_runtime_evidence_used_as_baseline": False,
            "promotion_candidate_direct_runtime_adoption": False,
            "latest_or_manual_fallback": False,
            "registry_accepted_state_updated": False,
            "runtime_accepted_state_created": False,
            "bv15_relaxed": False,
            "forced_buy": False,
            "broker_write": False,
            "production_runtime_executed": False,
            "historical_fresh_run_executed": False,
        },
    }
    write_json(EVIDENCE_DIR / "contract_completion_report.json", report)
    write_json(REPORT_JSON, report)
    write_markdown(report)
    return report


def write_markdown(report: dict[str, Any]) -> None:
    lines = [
        "# Phase18-Y Accepted Atomic BUY AI Bundle Contract Completion",
        "",
        f"- Run ID: `{report['run_id']}`",
        f"- Final judgment: `{report['final_judgment']}`",
        f"- Contract completion status: `{report['contract_completion_status']}`",
        f"- Superseding transaction: `{report['superseding_transaction_id']}`",
        f"- Registry unchanged: `{report['registry_unchanged']}`",
        f"- Runtime accepted state unchanged: `{report['runtime_accepted_state_unchanged']}`",
        "",
        "## Materialized Runtime Baseline",
        "",
        f"- Path: `{report['materialized_runtime_baseline']['path']}`",
        f"- Baseline identity: `{report['materialized_runtime_baseline']['baseline_identity']}`",
        f"- Baseline hash: `{report['materialized_runtime_baseline']['baseline_hash']}`",
        f"- Row count: `{report['materialized_runtime_baseline']['row_count']}`",
        f"- Date range: `{report['materialized_runtime_baseline']['date_range']}`",
        f"- Current Runtime evidence used: `{report['materialized_runtime_baseline']['current_runtime_evidence_used']}`",
        "",
        "## Freshness Metadata",
        "",
        f"- model_training_cutoff: `{report['freshness_metadata']['model_training_cutoff']}`",
        f"- label_safe_cutoff: `{report['freshness_metadata']['label_safe_cutoff']}`",
        f"- training_dataset_max_date: `{report['freshness_metadata']['training_dataset_max_date']}`",
        f"- formal_trading_calendar_ref: `{report['freshness_metadata']['formal_trading_calendar_ref']}`",
        f"- model_training_lag_business_days: `{report['freshness_metadata']['model_training_lag_business_days']}`",
        f"- model_training_lag_status: `{report['freshness_metadata']['model_training_lag_status']}`",
        "",
        "## Eligibility",
        "",
        f"- Decision: `{report['eligibility_decision']['decision']}`",
        f"- runtime_use_eligible: `{report['eligibility_decision']['runtime_use_eligible']}`",
        f"- registry_accepted_event_requested: `{report['eligibility_decision']['registry_accepted_event_requested']}`",
        "",
        "## Authority Review",
        "",
        f"- approval_scope: `{report['authority_review']['approval_scope']}`",
        f"- registry_accepted_event_authorized: `{report['authority_review']['registry_accepted_event_authorized']}`",
        f"- reviewer: `{report['authority_review']['reviewer']}`",
        f"- blocking_items: `{report['authority_review']['blocking_items']}`",
        "",
        "## Non-Execution Confirmation",
        "",
    ]
    for key, value in report["prohibited_actions"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Final", "", f"`{report['final_judgment']}`", ""])
    write_text(REPORT_MD, "\n".join(lines))


def main() -> int:
    report = build_completed_transaction()
    print(json.dumps({"final_judgment": report["final_judgment"], "contract_completion_status": report["contract_completion_status"]}, sort_keys=True))
    return 0 if report["final_judgment"] in {"PHASE18_Y_CONTRACT_COMPLETION_COMPLETE", "PHASE18_Y_AUTHORITY_APPROVAL_COMPLETE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
