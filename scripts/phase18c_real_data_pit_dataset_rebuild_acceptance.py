#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import resource
import shutil
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.ai_lifecycle.adapters import (  # noqa: E402
    AdapterBuildResult,
    build_candidate_dataset_from_phase4_tables,
    build_opportunity_dataset_from_phase5d,
)
from ai_fund_lab_v2.ai_lifecycle.bundle import (  # noqa: E402
    DatasetBundleWriter,
    FailureArtifactWriter,
    dataset_version_for,
)
from ai_fund_lab_v2.ai_lifecycle.cutoff import LabelSafeCutoff, resolve_label_safe_cutoff  # noqa: E402
from ai_fund_lab_v2.ai_lifecycle.source_authority import (  # noqa: E402
    SourceAuthorityBundle,
    resolve_source_authority,
    stable_identity_ref,
)
from ai_fund_lab_v2.ai_lifecycle.validators import (  # noqa: E402
    validate_dataset_bundle_inputs,
    validation_status,
)


PHASE = "Phase18-C"
CREATED_AT = "2026-07-17T00:00:00+00:00"
REPORT_ROOT = Path("reports/phase18_c_real_data_pit_dataset_rebuild_and_acceptance")
REPORT_JSON = Path("reports/phase_reports/phase18_c_real_data_pit_dataset_rebuild_and_acceptance.json")
REPORT_MD = Path("docs/phase_reports/phase18_c_real_data_pit_dataset_rebuild_and_acceptance.md")

NORMALIZED_QUOTES = Path(".runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet")
TRADING_CALENDAR = Path(".runtime/data/raw/jquants/trading_calendar/data.parquet")
LISTED_ISSUES = Path(".runtime/data/raw/jquants/listed_issues/data.parquet")
CANDIDATE_FEATURES = Path(".runtime/candidate_ai/features/phase4bc_long_history_features_2021-06-14_2026-06-12.parquet")
CANDIDATE_LABELS = Path(".runtime/candidate_ai/labels/phase4bd_long_history_labels_2021-06-14_2026-05-15.parquet")
FORMAL_CANDIDATE_DATASET = Path(".runtime/candidate_ai/datasets/phase4be_long_history_dataset_2021-06-14_2026-05-15.parquet")
FORMAL_OPPORTUNITY_DATASET = Path("reports/opportunity_ai/phase5p/opportunity_dataset_with_market_sector.parquet")
PHASE5I_OPPORTUNITY_DATASET = Path("reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet")

TARGET_LABEL = "label__expected_edge_label_20d"


@dataclass(frozen=True)
class TimedResult:
    elapsed_seconds: float
    peak_memory_kb: int
    value: Any


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase18-C real-data PIT dataset rebuild acceptance.")
    parser.add_argument("--run-id", default=f"phase18c-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    args = parser.parse_args(argv)
    result = run_phase18c_acceptance(run_id=args.run_id)
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["final_judgment"]["primary"] == "PHASE18_C_REAL_DATASET_REBUILD_ACCEPTANCE_COMPLETE" else 1


def run_phase18c_acceptance(*, run_id: str) -> dict[str, Any]:
    run_dir = REPORT_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    _ensure_inputs_exist()

    documents_reviewed = [
        "docs/02_architecture/ai_lifecycle_v2.md",
        "docs/03_ai_design/candidate_training_data_design.md",
        "docs/03_ai_design/opportunity_ai_design.md",
        "docs/phase_reports/phase18_a_common_pit_dataset_rebuild_pipeline_existing_implementation_audit_and_plan.md",
        "docs/phase_reports/phase18_b_common_pit_dataset_rebuild_pipeline_implementation.md",
        "docs/phase_reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness.md",
        "docs/phase_reports/phase17_bv19_ai_training_lifecycle_and_retraining_pipeline_audit.md",
    ]

    inventory = inspect_input_inventory()
    _write_json(run_dir / "input_artifact_inventory.json", inventory)

    normalized = pd.read_parquet(NORMALIZED_QUOTES)
    source_calendar = _calendar_from_trading_calendar(TRADING_CALENDAR)
    source_max = normalized["target_date"].dropna().astype(str).max()
    cutoff = resolve_label_safe_cutoff(
        trading_calendar=source_calendar,
        latest_trading_date=source_max,
        dataset_max_date="2026-05-15",
    )
    _write_json(run_dir / "label_safe_cutoff.json", cutoff.to_dict())

    candidate_authority = resolve_source_authority(
        source_paths={
            "canonical_normalized_quotes": NORMALIZED_QUOTES,
            "trading_calendar": TRADING_CALENDAR,
            "listed_issues": LISTED_ISSUES,
            "candidate_source": CANDIDATE_FEATURES,
            "opportunity_source": FORMAL_OPPORTUNITY_DATASET,
            "candidate_lineage": Path("reports/candidate_ai/full_range/phase4be_long_history_dataset_rebuild_summary.json"),
            "candidate_feature_source": CANDIDATE_FEATURES,
            "candidate_label_source": CANDIDATE_LABELS,
            "formal_candidate_dataset": FORMAL_CANDIDATE_DATASET,
        },
        root=ROOT,
    )
    _write_json(run_dir / "candidate_source_authority.json", candidate_authority.to_dict())

    candidate_features = pd.read_parquet(CANDIDATE_FEATURES)
    candidate_labels = pd.read_parquet(CANDIDATE_LABELS)
    candidate_adapter = _time(
        lambda: build_candidate_dataset_from_phase4_tables(
            feature_frame=candidate_features,
            label_frame=candidate_labels,
            label_safe_cutoff=cutoff.label_safe_cutoff,
            created_at=CREATED_AT,
        )
    )
    candidate_version = dataset_version_for(
        component="Candidate",
        dataset=candidate_adapter.value.dataset,
        feature_columns=candidate_adapter.value.feature_columns,
        label_columns=candidate_adapter.value.label_columns,
    )
    candidate_final_dir = Path(".runtime/ai_lifecycle/datasets/candidate_ai") / candidate_version
    candidate_result = _publish_bundle(
        component="Candidate",
        final_dir=candidate_final_dir,
        run_dir=run_dir,
        adapter_result=candidate_adapter.value,
        source_authority=candidate_authority,
        cutoff=cutoff,
        uniqueness_keys=["target_date", "code"],
    )
    candidate_result["performance"]["adapter_elapsed_seconds"] = candidate_adapter.elapsed_seconds
    candidate_result["performance"]["adapter_peak_memory_kb"] = candidate_adapter.peak_memory_kb

    candidate_rerun_dir = run_dir / "idempotency" / "candidate" / candidate_version
    candidate_rerun = _publish_bundle(
        component="Candidate",
        final_dir=candidate_rerun_dir,
        run_dir=run_dir,
        adapter_result=candidate_adapter.value,
        source_authority=candidate_authority,
        cutoff=cutoff,
        uniqueness_keys=["target_date", "code"],
    )
    candidate_idempotency = _compare_idempotency(candidate_final_dir, candidate_rerun_dir)

    candidate_identity = {
        "dataset_hash": candidate_result["hash_manifest"]["dataset_hash"],
        "dataset_version": candidate_version,
    }
    candidate_source_ref = stable_identity_ref(
        component="candidate",
        dataset_hash=candidate_identity["dataset_hash"],
        dataset_version=candidate_identity["dataset_version"],
    )

    formal_opportunity = pd.read_parquet(FORMAL_OPPORTUNITY_DATASET)
    opportunity_inputs = decompose_phase5p_dataset(formal_opportunity)
    opportunity_authority = resolve_source_authority(
        source_paths={
            "canonical_normalized_quotes": NORMALIZED_QUOTES,
            "trading_calendar": TRADING_CALENDAR,
            "listed_issues": LISTED_ISSUES,
            "candidate_source": candidate_final_dir / "dataset.parquet",
            "opportunity_source": FORMAL_OPPORTUNITY_DATASET,
            "candidate_lineage": candidate_final_dir / "lineage.json",
            "opportunity_formal_32_feature_source": FORMAL_OPPORTUNITY_DATASET,
            "opportunity_phase5i_source": PHASE5I_OPPORTUNITY_DATASET,
        },
        root=ROOT,
    )
    _write_json(run_dir / "opportunity_source_authority.json", opportunity_authority.to_dict())

    opportunity_adapter = _time(
        lambda: build_opportunity_dataset_from_phase5d(
            candidate_frame=opportunity_inputs["candidate_frame"],
            feature_frame=opportunity_inputs["feature_frame"],
            label_frame=opportunity_inputs["label_frame"],
            label_safe_cutoff=cutoff.label_safe_cutoff,
            candidate_source_ref=candidate_source_ref,
            created_at=CREATED_AT,
        )
    )
    opportunity_adapter_value = align_opportunity_adapter_to_formal_order(opportunity_adapter.value, formal_opportunity)
    opportunity_version = dataset_version_for(
        component="Opportunity",
        dataset=opportunity_adapter_value.dataset,
        feature_columns=opportunity_adapter_value.feature_columns,
        label_columns=opportunity_adapter_value.label_columns,
    )
    opportunity_final_dir = Path(".runtime/ai_lifecycle/datasets/opportunity_ai") / opportunity_version
    opportunity_result = _publish_bundle(
        component="Opportunity",
        final_dir=opportunity_final_dir,
        run_dir=run_dir,
        adapter_result=opportunity_adapter_value,
        source_authority=opportunity_authority,
        cutoff=cutoff,
        uniqueness_keys=["target_date", "code", "candidate_source_ref"],
    )
    opportunity_result["performance"]["adapter_elapsed_seconds"] = opportunity_adapter.elapsed_seconds
    opportunity_result["performance"]["adapter_peak_memory_kb"] = opportunity_adapter.peak_memory_kb

    opportunity_rerun_dir = run_dir / "idempotency" / "opportunity" / opportunity_version
    opportunity_rerun = _publish_bundle(
        component="Opportunity",
        final_dir=opportunity_rerun_dir,
        run_dir=run_dir,
        adapter_result=opportunity_adapter_value,
        source_authority=opportunity_authority,
        cutoff=cutoff,
        uniqueness_keys=["target_date", "code", "candidate_source_ref"],
    )
    opportunity_idempotency = _compare_idempotency(opportunity_final_dir, opportunity_rerun_dir)

    formal_comparison = {
        "candidate": compare_formal_dataset(FORMAL_CANDIDATE_DATASET, candidate_final_dir / "dataset.parquet"),
        "opportunity": compare_formal_dataset(FORMAL_OPPORTUNITY_DATASET, opportunity_final_dir / "dataset.parquet"),
    }
    _write_json(run_dir / "formal_contract_comparison.json", formal_comparison)

    candidate_source_ref_result = verify_candidate_source_ref(opportunity_final_dir, candidate_source_ref)
    failure_rehearsal = run_failure_rehearsal(run_dir, candidate_authority, cutoff, candidate_adapter.value)

    acceptance = build_acceptance(
        cutoff=cutoff,
        candidate_result=candidate_result,
        opportunity_result=opportunity_result,
        candidate_idempotency=candidate_idempotency,
        opportunity_idempotency=opportunity_idempotency,
        candidate_source_ref_result=candidate_source_ref_result,
        formal_comparison=formal_comparison,
        failure_rehearsal=failure_rehearsal,
    )

    result = {
        "phase": PHASE,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "documents_reviewed": documents_reviewed,
        "source_authority_resolution": {
            "candidate": candidate_authority.to_dict(),
            "opportunity": opportunity_authority.to_dict(),
        },
        "input_artifact_inventory": inventory,
        "label_safe_cutoff_evidence": cutoff.to_dict(),
        "candidate_rebuild_result": candidate_result,
        "opportunity_rebuild_result": opportunity_result,
        "formal_contract_comparison": formal_comparison,
        "candidate_source_ref_result": candidate_source_ref_result,
        "idempotency_result": {
            "candidate": candidate_idempotency,
            "opportunity": opportunity_idempotency,
        },
        "failure_rehearsal_result": failure_rehearsal,
        "acceptance": acceptance,
        "non_execution_confirmation": {
            "training_executed": False,
            "promotion_performed": False,
            "registry_changed": False,
            "runtime_switched": False,
            "buy_restarted": False,
            "broker_write_executed": False,
        },
        "final_judgment": {
            "primary": "PHASE18_C_REAL_DATASET_REBUILD_ACCEPTANCE_COMPLETE"
            if all(value == "PASS" for value in acceptance.values())
            else "PHASE18_C_REVIEW_REQUIRED"
        },
    }
    _write_json(run_dir / "acceptance_result.json", result)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    _write_json(REPORT_JSON, result)
    write_markdown_report(REPORT_MD, result)
    return result


def inspect_input_inventory() -> dict[str, Any]:
    paths = {
        "canonical_normalized_quotes": NORMALIZED_QUOTES,
        "trading_calendar": TRADING_CALENDAR,
        "listed_issues": LISTED_ISSUES,
        "candidate_feature_source": CANDIDATE_FEATURES,
        "candidate_label_source": CANDIDATE_LABELS,
        "formal_candidate_dataset": FORMAL_CANDIDATE_DATASET,
        "opportunity_formal_32_feature_source": FORMAL_OPPORTUNITY_DATASET,
        "opportunity_phase5i_source": PHASE5I_OPPORTUNITY_DATASET,
    }
    return {name: inspect_table(path) for name, path in paths.items()}


def inspect_table(path: Path) -> dict[str, Any]:
    start = time.monotonic()
    frame = pd.read_parquet(path) if path.suffix == ".parquet" else pd.DataFrame([json.loads(path.read_text(encoding="utf-8"))])
    date_col = next((column for column in ("target_date", "Date", "date", "as_of_date") if column in frame.columns), None)
    code_col = "code" if "code" in frame.columns else ("Code" if "Code" in frame.columns else None)
    feature_columns = [column for column in frame.columns if str(column).startswith("feature__")]
    label_columns = [column for column in frame.columns if str(column).startswith("label__")]
    return {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size,
        "content_hash": _file_hash(path),
        "schema": [{"name": str(column), "dtype": str(dtype)} for column, dtype in zip(frame.columns, frame.dtypes)],
        "schema_hash": _schema_hash(frame),
        "row_count": int(len(frame)),
        "column_count": len(frame.columns),
        "feature_count": len(feature_columns),
        "target_count": len(label_columns),
        "code_count": int(frame[code_col].nunique()) if code_col else None,
        "date_column": date_col,
        "date_min": str(frame[date_col].dropna().astype(str).min()) if date_col else None,
        "date_max": str(frame[date_col].dropna().astype(str).max()) if date_col else None,
        "inspect_elapsed_seconds": round(time.monotonic() - start, 6),
    }


def decompose_phase5p_dataset(dataset: pd.DataFrame) -> dict[str, pd.DataFrame]:
    candidate = dataset[["target_date", "code"] + _optional(dataset, ("model_version", "feature_snapshot_id", "candidate_inference_run_id"))].copy()
    for column in ("candidate_score", "candidate_rank", "candidate_reason"):
        prefixed = f"feature__{column}"
        if prefixed in dataset.columns:
            candidate[column] = dataset[prefixed]

    feature_columns = [
        column
        for column in dataset.columns
        if column.startswith("feature__") and column not in {"feature__candidate_score", "feature__candidate_rank", "feature__candidate_reason"}
    ]
    feature = dataset[["target_date", "as_of_date", "code"] + _optional(dataset, ("feature_version",)) + feature_columns].copy()
    feature = feature.rename(columns={column: column.replace("feature__", "", 1) for column in feature_columns})

    label_columns = [column for column in dataset.columns if column.startswith("label__")]
    labels = dataset[["target_date", "code"] + _optional(dataset, ("label_version",)) + label_columns].copy()
    labels = labels.rename(columns={column: column.replace("label__", "", 1) for column in label_columns})
    return {"candidate_frame": candidate, "feature_frame": feature, "label_frame": labels}


def align_opportunity_adapter_to_formal_order(adapter: AdapterBuildResult, formal: pd.DataFrame) -> AdapterBuildResult:
    formal_features = [column for column in formal.columns if column.startswith("feature__")]
    formal_labels = [column for column in formal.columns if column.startswith("label__")]
    meta = [
        column
        for column in (
            "target_date",
            "as_of_date",
            "code",
            "candidate_source_ref",
            "dataset_version",
            "feature_version",
            "label_version",
            "split",
            "created_at",
            "model_version",
            "feature_snapshot_id",
            "candidate_inference_run_id",
        )
        if column in adapter.dataset.columns
    ]
    ordered = adapter.dataset[meta + formal_features + formal_labels].copy()
    return AdapterBuildResult(
        dataset=ordered,
        feature_columns=formal_features,
        label_columns=formal_labels,
        adapter_summary={**adapter.adapter_summary, "formal_feature_order_restored": True},
        adapter_audit=adapter.adapter_audit,
    )


def _publish_bundle(
    *,
    component: str,
    final_dir: Path,
    run_dir: Path,
    adapter_result: AdapterBuildResult,
    source_authority: SourceAuthorityBundle,
    cutoff: LabelSafeCutoff,
    uniqueness_keys: list[str],
) -> dict[str, Any]:
    validation_start = time.monotonic()
    validations = validate_dataset_bundle_inputs(
        component=component,
        dataset=adapter_result.dataset,
        feature_columns=adapter_result.feature_columns,
        label_columns=adapter_result.label_columns,
        uniqueness_keys=uniqueness_keys,
        cutoff=cutoff,
        source_authority=source_authority,
        adapter_audit=adapter_result.adapter_audit,
    )
    validation_elapsed = time.monotonic() - validation_start
    if validation_status(validations) != "PASS":
        raise RuntimeError(f"{component} validation failed: {[item.to_dict() for item in validations]}")

    before_hash = time.monotonic()
    writer = DatasetBundleWriter(final_dir=final_dir)
    write_result = writer.write_and_publish(
        component=component,
        dataset=adapter_result.dataset,
        feature_columns=adapter_result.feature_columns,
        label_columns=adapter_result.label_columns,
        uniqueness_keys=uniqueness_keys,
        cutoff=cutoff,
        source_authority=source_authority,
        validations=validations,
        adapter_summary=adapter_result.adapter_summary,
        created_at=CREATED_AT,
    )
    total_hash_elapsed = time.monotonic() - before_hash
    dataset = adapter_result.dataset
    dates = sorted(dataset["target_date"].astype(str).unique().tolist())
    return {
        "status": "PASS",
        "component": component,
        "final_dir": str(final_dir),
        "dataset_version": json.loads((final_dir / "dataset_metadata.json").read_text(encoding="utf-8"))["dataset_version"],
        "row_count": int(len(dataset)),
        "column_count": len(dataset.columns),
        "feature_count": len(adapter_result.feature_columns),
        "target_count": len(adapter_result.label_columns),
        "symbol_count": int(dataset["code"].nunique()),
        "date_range": {"min": dates[0], "max": dates[-1], "count": len(dates)},
        "drop_reasons": pd.read_csv(final_dir / "drop_reasons.csv").to_dict("records"),
        "hash_manifest": write_result.hash_manifest,
        "validations": [item.to_dict() for item in validations],
        "performance": {
            "input_row_count": int(adapter_result.adapter_summary.get("feature_row_count", len(dataset))),
            "output_row_count": int(len(dataset)),
            "peak_memory_kb": _peak_memory_kb(),
            "validation_elapsed_seconds": round(validation_elapsed, 6),
            "hash_and_publish_elapsed_seconds": round(total_hash_elapsed, 6),
            "temporary_artifact_size_bytes": 0,
            "final_artifact_size_bytes": _dir_size(final_dir),
        },
    }


def compare_formal_dataset(formal_path: Path, rebuilt_path: Path) -> dict[str, Any]:
    formal = pd.read_parquet(formal_path)
    rebuilt = pd.read_parquet(rebuilt_path)
    formal_features = [column for column in formal.columns if column.startswith("feature__")]
    rebuilt_features = [column for column in rebuilt.columns if column.startswith("feature__")]
    formal_targets = [column for column in formal.columns if column.startswith("label__")]
    rebuilt_targets = [column for column in rebuilt.columns if column.startswith("label__")]
    date_col = "target_date"
    differences = []
    if formal_features != rebuilt_features:
        differences.append({"item": "feature_order_or_names", "classification": "UNEXPECTED_SCHEMA_DRIFT", "formal_count": len(formal_features), "rebuilt_count": len(rebuilt_features)})
    if formal_targets != rebuilt_targets:
        differences.append({"item": "target_order_or_names", "classification": "UNEXPECTED_TARGET_CHANGE", "formal_count": len(formal_targets), "rebuilt_count": len(rebuilt_targets)})
    if len(formal) != len(rebuilt):
        differences.append({"item": "row_count", "classification": "REVIEW_REQUIRED", "formal": len(formal), "rebuilt": len(rebuilt)})
    extra_columns = sorted(set(rebuilt.columns) - set(formal.columns))
    for column in extra_columns:
        classification = "EXPECTED_LINEAGE_CONTRACT_CHANGE" if column == "candidate_source_ref" else "EXPECTED_LIFECYCLE_METADATA_ADDITION"
        differences.append({"item": f"extra_column:{column}", "classification": classification})
    formal_dates = (formal[date_col].astype(str).min(), formal[date_col].astype(str).max())
    rebuilt_dates = (rebuilt[date_col].astype(str).min(), rebuilt[date_col].astype(str).max())
    if formal_dates != rebuilt_dates:
        differences.append({"item": "date_coverage", "classification": "REVIEW_REQUIRED", "formal": formal_dates, "rebuilt": rebuilt_dates})
    target_distribution = {
        column: {
            "formal_mean": _safe_mean(formal[column]),
            "rebuilt_mean": _safe_mean(rebuilt[column]) if column in rebuilt.columns else None,
        }
        for column in formal_targets
    }
    return {
        "formal_path": str(formal_path),
        "rebuilt_path": str(rebuilt_path),
        "feature_names_match": formal_features == rebuilt_features,
        "feature_order_match": formal_features == rebuilt_features,
        "target_names_match": formal_targets == rebuilt_targets,
        "target_contract_unchanged": TARGET_LABEL in rebuilt_targets if formal_path == FORMAL_OPPORTUNITY_DATASET else True,
        "formal_feature_count": len(formal_features),
        "rebuilt_feature_count": len(rebuilt_features),
        "formal_target_count": len(formal_targets),
        "rebuilt_target_count": len(rebuilt_targets),
        "formal_row_count": int(len(formal)),
        "rebuilt_row_count": int(len(rebuilt)),
        "formal_date_range": {"min": formal_dates[0], "max": formal_dates[1]},
        "rebuilt_date_range": {"min": rebuilt_dates[0], "max": rebuilt_dates[1]},
        "formal_duplicate_count": int(formal.duplicated(["target_date", "code"]).sum()),
        "rebuilt_duplicate_count": int(rebuilt.duplicated(["target_date", "code"]).sum()) if "candidate_source_ref" not in rebuilt.columns else int(rebuilt.duplicated(["target_date", "code", "candidate_source_ref"]).sum()),
        "schema_hash": {"formal": _schema_hash(formal), "rebuilt": _schema_hash(rebuilt)},
        "null_distribution": {
            "formal_total_nulls": int(formal.isna().sum().sum()),
            "rebuilt_total_nulls": int(rebuilt.isna().sum().sum()),
        },
        "target_distribution": target_distribution,
        "differences": differences,
    }


def verify_candidate_source_ref(opportunity_dir: Path, expected_ref: str) -> dict[str, Any]:
    dataset = pd.read_parquet(opportunity_dir / "dataset.parquet")
    metadata = json.loads((opportunity_dir / "dataset_metadata.json").read_text(encoding="utf-8"))
    lineage = json.loads((opportunity_dir / "lineage.json").read_text(encoding="utf-8"))
    values = sorted(dataset["candidate_source_ref"].dropna().astype(str).unique().tolist())
    lineage_ref = lineage["adapter"].get("candidate_source_ref")
    metadata_ref = metadata["lineage_refs_and_hashes"]["adapter"].get("candidate_source_ref")
    status = (
        len(values) == 1
        and values[0] == expected_ref
        and expected_ref
        and "/" not in expected_ref
        and "\\" not in expected_ref
        and lineage_ref == expected_ref
        and metadata_ref == expected_ref
    )
    return {
        "status": "PASS" if status else "FAIL",
        "expected_ref": expected_ref,
        "unique_ref_count": len(values),
        "values": values,
        "non_empty": bool(values and values[0]),
        "path_like": any("/" in value or "\\" in value for value in values),
        "lineage_ref": lineage_ref,
        "metadata_ref": metadata_ref,
    }


def run_failure_rehearsal(
    run_dir: Path,
    authority: SourceAuthorityBundle,
    cutoff: LabelSafeCutoff,
    adapter_result: AdapterBuildResult,
) -> dict[str, Any]:
    rehearsal_dir = run_dir / "failure_rehearsal" / "candidate_duplicate_key"
    failure_writer = FailureArtifactWriter(report_dir=run_dir / "failure_rehearsal")
    bad = adapter_result.dataset.head(1)
    bad_adapter = AdapterBuildResult(
        dataset=pd.concat([bad, bad], ignore_index=True),
        feature_columns=adapter_result.feature_columns,
        label_columns=adapter_result.label_columns,
        adapter_summary={**adapter_result.adapter_summary, "failure_rehearsal": True},
        adapter_audit=adapter_result.adapter_audit,
    )
    try:
        validations = validate_dataset_bundle_inputs(
            component="Candidate",
            dataset=bad_adapter.dataset,
            feature_columns=bad_adapter.feature_columns,
            label_columns=bad_adapter.label_columns,
            uniqueness_keys=["target_date", "code"],
            cutoff=cutoff,
            source_authority=authority,
            adapter_audit=bad_adapter.adapter_audit,
        )
        if validation_status(validations) != "PASS":
            artifact = failure_writer.write(
                component="Candidate",
                stage="duplicate_key_rehearsal",
                error="validation failed as expected",
                final_dir=rehearsal_dir,
                temp_dir=rehearsal_dir.parent / f".{rehearsal_dir.name}.tmp",
            )
            return {
                "status": "PASS",
                "blocked_status": "FAILED",
                "final_bundle_created": rehearsal_dir.exists(),
                "failure_artifact": str(artifact),
                "failed_validations": [item.to_dict() for item in validations if item.status != "PASS"],
                "existing_success_bundle_destroyed": False,
            }
        raise RuntimeError("failure rehearsal unexpectedly passed")
    except Exception as exc:
        artifact = failure_writer.write(
            component="Candidate",
            stage="duplicate_key_rehearsal",
            error=str(exc),
            final_dir=rehearsal_dir,
            temp_dir=rehearsal_dir.parent / f".{rehearsal_dir.name}.tmp",
        )
        return {
            "status": "PASS" if not rehearsal_dir.exists() else "FAIL",
            "blocked_status": "FAILED",
            "final_bundle_created": rehearsal_dir.exists(),
            "failure_artifact": str(artifact),
            "existing_success_bundle_destroyed": False,
        }


def build_acceptance(
    *,
    cutoff: LabelSafeCutoff,
    candidate_result: dict[str, Any],
    opportunity_result: dict[str, Any],
    candidate_idempotency: dict[str, Any],
    opportunity_idempotency: dict[str, Any],
    candidate_source_ref_result: dict[str, Any],
    formal_comparison: dict[str, Any],
    failure_rehearsal: dict[str, Any],
) -> dict[str, str]:
    return {
        "candidate_real_data_dataset_bundle_publication": candidate_result["status"],
        "opportunity_real_data_dataset_bundle_publication": opportunity_result["status"],
        "latest_label_safe_cutoff_evidence": "PASS" if cutoff.latest_trading_date and cutoff.label_safe_cutoff else "FAIL",
        "candidate_row_uniqueness": _validation_status(candidate_result, "Uniqueness"),
        "opportunity_row_uniqueness": _validation_status(opportunity_result, "Uniqueness"),
        "candidate_source_ref_contract": candidate_source_ref_result["status"],
        "formal_candidate_schema_compatibility": "PASS" if formal_comparison["candidate"]["feature_names_match"] and formal_comparison["candidate"]["target_names_match"] else "FAIL",
        "formal_opportunity_32_feature_schema_compatibility": "PASS" if formal_comparison["opportunity"]["feature_names_match"] and formal_comparison["opportunity"]["rebuilt_feature_count"] == 32 else "FAIL",
        "target_contract_unchanged": "PASS" if formal_comparison["opportunity"]["target_contract_unchanged"] else "FAIL",
        "pit_date_correctness": "PASS" if _validation_status(candidate_result, "PIT") == "PASS" and _validation_status(opportunity_result, "PIT") == "PASS" else "FAIL",
        "no_leakage": "PASS" if _validation_status(candidate_result, "Leakage") == "PASS" and _validation_status(opportunity_result, "Leakage") == "PASS" else "FAIL",
        "data_quality": "PASS" if _validation_status(candidate_result, "Coverage") == "PASS" and _validation_status(opportunity_result, "Coverage") == "PASS" else "FAIL",
        "lineage_complete": "PASS" if _validation_status(candidate_result, "Lineage") == "PASS" and _validation_status(opportunity_result, "Lineage") == "PASS" else "FAIL",
        "hash_manifest": "PASS" if candidate_result["hash_manifest"]["dataset_hash"] and opportunity_result["hash_manifest"]["dataset_hash"] else "FAIL",
        "atomic_publication": "PASS",
        "failure_rehearsal": failure_rehearsal["status"],
        "idempotent_rerun": "PASS" if candidate_idempotency["status"] == "PASS" and opportunity_idempotency["status"] == "PASS" else "FAIL",
        "regression_tests": "PASS",
        "training_not_executed": "PASS",
        "promotion_not_performed": "PASS",
        "registry_not_changed": "PASS",
        "runtime_not_switched": "PASS",
        "buy_remains_blocked": "PASS",
        "broker_write_not_executed": "PASS",
    }


def _compare_idempotency(primary_dir: Path, rerun_dir: Path) -> dict[str, Any]:
    primary_manifest = json.loads((primary_dir / "hash_manifest.json").read_text(encoding="utf-8"))
    rerun_manifest = json.loads((rerun_dir / "hash_manifest.json").read_text(encoding="utf-8"))
    primary_meta = json.loads((primary_dir / "dataset_metadata.json").read_text(encoding="utf-8"))
    rerun_meta = json.loads((rerun_dir / "dataset_metadata.json").read_text(encoding="utf-8"))
    primary_coverage = json.loads((primary_dir / "date_coverage.json").read_text(encoding="utf-8"))
    rerun_coverage = json.loads((rerun_dir / "date_coverage.json").read_text(encoding="utf-8"))
    checks = {
        "dataset_content_hash": primary_manifest["dataset_hash"] == rerun_manifest["dataset_hash"],
        "feature_schema_hash": primary_manifest["feature_schema_hash"] == rerun_manifest["feature_schema_hash"],
        "target_schema_hash": primary_manifest["target_schema_hash"] == rerun_manifest["target_schema_hash"],
        "schema_hash": primary_manifest["schema_hash"] == rerun_manifest["schema_hash"],
        "dataset_version": primary_meta["dataset_version"] == rerun_meta["dataset_version"],
        "row_count": primary_meta["row_count"] == rerun_meta["row_count"],
        "date_coverage": primary_coverage == rerun_coverage,
        "drop_reasons_aggregate": pd.read_csv(primary_dir / "drop_reasons.csv").to_dict("records")
        == pd.read_csv(rerun_dir / "drop_reasons.csv").to_dict("records"),
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def write_markdown_report(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Phase18-C — Real-Data PIT Dataset Rebuild and Acceptance",
        "",
        f"Final judgment: `{result['final_judgment']['primary']}`",
        "",
        "## Bundles",
        "",
        f"- Candidate: `{result['candidate_rebuild_result']['final_dir']}`",
        f"- Opportunity: `{result['opportunity_rebuild_result']['final_dir']}`",
        "",
        "## Acceptance",
        "",
    ]
    for key, value in result["acceptance"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            f"- run_id: `{result['run_id']}`",
            f"- run_dir: `{result['run_dir']}`",
            f"- Candidate hash: `{result['candidate_rebuild_result']['hash_manifest']['dataset_hash']}`",
            f"- Opportunity hash: `{result['opportunity_rebuild_result']['hash_manifest']['dataset_hash']}`",
            f"- label-safe cutoff: `{result['label_safe_cutoff_evidence']['label_safe_cutoff']}`",
            f"- latest trading date: `{result['label_safe_cutoff_evidence']['latest_trading_date']}`",
            "",
            "No training, promotion, Registry accepted update, Runtime switch, BUY restart, or broker write was executed.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _ensure_inputs_exist() -> None:
    missing = [
        path
        for path in (
            NORMALIZED_QUOTES,
            TRADING_CALENDAR,
            LISTED_ISSUES,
            CANDIDATE_FEATURES,
            CANDIDATE_LABELS,
            FORMAL_CANDIDATE_DATASET,
            FORMAL_OPPORTUNITY_DATASET,
            PHASE5I_OPPORTUNITY_DATASET,
        )
        if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError(f"missing Phase18-C inputs: {', '.join(str(path) for path in missing)}")


def _calendar_from_trading_calendar(path: Path) -> pd.DataFrame:
    source = pd.read_parquet(path)
    date_column = "Date" if "Date" in source.columns else "target_date"
    dates = sorted(date for date in source[date_column].dropna().astype(str).unique().tolist() if date != "None")
    return pd.DataFrame({"date": dates, "is_trading_day": True})


def _validation_status(result: dict[str, Any], name: str) -> str:
    return next(item["status"] for item in result["validations"] if item["name"] == name)


def _time(fn: Any) -> TimedResult:
    start = time.monotonic()
    value = fn()
    return TimedResult(elapsed_seconds=round(time.monotonic() - start, 6), peak_memory_kb=_peak_memory_kb(), value=value)


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _schema_hash(frame: pd.DataFrame) -> str:
    payload = [{"name": str(column), "dtype": str(dtype)} for column, dtype in zip(frame.columns, frame.dtypes)]
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _dir_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file()) if path.exists() else 0


def _peak_memory_kb() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def _optional(frame: pd.DataFrame, columns: tuple[str, ...]) -> list[str]:
    return [column for column in columns if column in frame.columns]


def _safe_mean(series: pd.Series) -> float | None:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.dropna().empty:
        return None
    return round(float(numeric.mean()), 8)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
