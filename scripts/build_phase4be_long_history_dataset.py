#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.candidate_ai.validation import is_forbidden_column  # noqa: E402
from ai_fund_lab_v2.data_store import create_storage_backend  # noqa: E402
from ai_fund_lab_v2.runtime import RuntimePaths  # noqa: E402
from scripts.build_phase4am_dataset import DATASET_VERSION, LABEL_COLUMNS  # noqa: E402

PHASE = "Phase4-BE"
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4be_long_history_dataset_rebuild_summary.json")
PHASE4BC_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4bc_long_history_feature_regeneration_summary.json")
PHASE4BD_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4bd_long_history_label_regeneration_summary.json")

READY_BC = "READY_FOR_LONG_HISTORY_LABEL_REGENERATION"
READY_BD = "READY_FOR_LONG_HISTORY_DATASET_REBUILD"
READY = "READY_FOR_FORMAL_LIGHTGBM_TRAINING"
BLOCKED_JOIN = "BLOCKED_BY_JOIN_COVERAGE"
BLOCKED_REBUILD = "BLOCKED_BY_DATASET_REBUILD"
BLOCKED_LEAKAGE = "BLOCKED_BY_LEAKAGE_AUDIT"
BLOCKED_QUALITY = "BLOCKED_BY_FEATURE_QUALITY_GATE"
BLOCKED_SPLIT = "BLOCKED_BY_SPLIT_COVERAGE"
BLOCKED_PATH = "BLOCKED_BY_OUTPUT_PATH_SAFETY"

TRAIN_START = "2021-09-09"
TRAIN_END = "2024-12-31"
VALIDATION_START = "2025-01-01"
VALIDATION_END = "2025-12-31"
TEST_START = "2026-01-01"
TEST_END = "2026-05-15"
HIGH_NULL_THRESHOLD = 0.5

NON_FEATURE_COLUMNS = {
    "target_date",
    "as_of_date",
    "code",
    "feature_version",
    "source_snapshot_id",
    "feature_set_name",
    "created_at",
    "data_start_date",
    "data_end_date",
    "universe_eligible",
    "excluded_reason",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Phase4-BE long-history Candidate training dataset.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--report-dir", default="reports/candidate_ai/full_range")
    parser.add_argument("--output-format", choices=("parquet", "jsonl"), default="parquet")
    parser.add_argument("--phase4bc-summary", default=str(PHASE4BC_SUMMARY_PATH))
    parser.add_argument("--phase4bd-summary", default=str(PHASE4BD_SUMMARY_PATH))
    args = parser.parse_args(argv)
    summary = build_phase4be_long_history_dataset(
        runtime_dir=args.runtime_dir,
        report_dir=args.report_dir,
        output_format=args.output_format,
        phase4bc_summary_path=Path(args.phase4bc_summary),
        phase4bd_summary_path=Path(args.phase4bd_summary),
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def build_phase4be_long_history_dataset(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    output_format: str = "parquet",
    phase4bc_summary_path: Path = PHASE4BC_SUMMARY_PATH,
    phase4bd_summary_path: Path = PHASE4BD_SUMMARY_PATH,
) -> dict[str, Any]:
    paths = RuntimePaths(runtime_dir=Path(runtime_dir))
    report_dir = Path(report_dir)
    summary_path = report_dir / SUMMARY_PATH.name
    bc_summary = _read_json_optional(phase4bc_summary_path)
    bd_summary = _read_json_optional(phase4bd_summary_path)
    datasets_root = paths.runtime_dir / "candidate_ai" / "datasets"
    manifests_root = paths.runtime_dir / "candidate_ai" / "manifests"
    audit_root = paths.runtime_dir / "candidate_ai" / "audit"

    if bc_summary.get("readiness_status") != READY_BC or bd_summary.get("readiness_status") != READY_BD:
        summary = _blocked_summary(
            readiness_status=BLOCKED_REBUILD,
            reason="Phase4-BC or Phase4-BD summary is missing or not ready.",
            paths=paths,
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary
    if not _safe_candidate_output_paths(paths.runtime_dir, datasets_root, manifests_root, audit_root):
        summary = _blocked_summary(
            readiness_status=BLOCKED_PATH,
            reason="Candidate AI dataset output paths are not under .runtime/candidate_ai.",
            paths=paths,
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary

    feature_path = Path(str(bc_summary.get("feature_output_path") or ""))
    label_path = Path(str(bd_summary.get("label_output_path") or ""))
    feature_hash_before = _file_hash(feature_path)
    label_hash_before = _file_hash(label_path)
    if not feature_path.is_file() or not label_path.is_file():
        summary = _blocked_summary(
            readiness_status=BLOCKED_REBUILD,
            reason="Required long-history feature or label artifact is missing.",
            paths=paths,
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary

    feature_frame = _read_frame(feature_path)
    label_frame = _read_frame(label_path)
    dataset, feature_columns, label_columns = build_long_history_dataset_frame(
        feature_frame=feature_frame,
        label_frame=label_frame,
    )
    feature_hash_after = _file_hash(feature_path)
    label_hash_after = _file_hash(label_path)
    feature_table_modified = feature_hash_before != feature_hash_after
    label_table_modified = label_hash_before != label_hash_after
    leakage = audit_dataset_frame(dataset, feature_columns=feature_columns, label_columns=label_columns)
    quality = compute_dataset_feature_quality(dataset, feature_columns=feature_columns)
    splits = split_stats(dataset)
    join_success_rate = _rate(len(dataset), len(label_frame))
    readiness_status = _resolve_readiness(
        joined_row_count=len(dataset),
        join_success_rate=join_success_rate,
        leakage_status=leakage["status"],
        quality_status=quality["status"],
        splits=splits,
        feature_table_modified=feature_table_modified,
        label_table_modified=label_table_modified,
    )

    date_min, date_max = _date_range(dataset)
    datasets_root.mkdir(parents=True, exist_ok=True)
    manifests_root.mkdir(parents=True, exist_ok=True)
    audit_root.mkdir(parents=True, exist_ok=True)
    dataset_path = _dataset_output_path(datasets_root, output_format, f"{date_min or 'none'}_{date_max or 'none'}")
    manifest_path = manifests_root / f"phase4be_long_history_dataset_manifest_{date_min or 'none'}_{date_max or 'none'}.json"
    audit_path = audit_root / f"phase4be_long_history_dataset_audit_{date_min or 'none'}_{date_max or 'none'}.json"
    _write_frame(dataset_path, dataset, output_format)

    audit_payload = {
        "phase": PHASE,
        "created_at": _now(),
        "leakage": leakage,
        "feature_quality_gate": quality,
        "split_stats": splits,
        "feature_table_modified": feature_table_modified,
        "label_table_modified": label_table_modified,
        "join_success_rate": join_success_rate,
    }
    manifest_payload = {
        "phase": PHASE,
        "created_at": _now(),
        "dataset_version": DATASET_VERSION,
        "feature_table_path": str(feature_path),
        "label_table_path": str(label_path),
        "dataset_path": str(dataset_path),
        "manifest_path": str(manifest_path),
        "audit_path": str(audit_path),
        "feature_row_count": int(len(feature_frame)),
        "label_row_count": int(len(label_frame)),
        "joined_row_count": int(len(dataset)),
        "join_success_rate": join_success_rate,
        "feature_column_count": len(feature_columns),
        "label_column_count": len(label_columns),
        "split_counts": {key: value["row_count"] for key, value in splits.items()},
        "leakage_audit_status": leakage["status"],
        "feature_quality_gate_status": quality["status"],
        "dataset_rebuild_executed": True,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
    }
    _write_json(audit_path, audit_payload)
    _write_json(manifest_path, manifest_payload)

    summary = {
        "phase": PHASE,
        "status": "OK" if readiness_status == READY else "BLOCKED",
        "readiness_status": readiness_status,
        "dataset_rebuild_executed": True,
        "feature_row_count": int(len(feature_frame)),
        "label_row_count": int(len(label_frame)),
        "joined_row_count": int(len(dataset)),
        "join_success_rate": join_success_rate,
        "train_row_count": splits["train"]["row_count"],
        "validation_row_count": splits["validation"]["row_count"],
        "test_row_count": splits["test"]["row_count"],
        "train_positive_count": splits["train"]["positive_count"],
        "validation_positive_count": splits["validation"]["positive_count"],
        "test_positive_count": splits["test"]["positive_count"],
        "train_positive_rate": splits["train"]["positive_rate"],
        "validation_positive_rate": splits["validation"]["positive_rate"],
        "test_positive_rate": splits["test"]["positive_rate"],
        "feature_column_count": len(feature_columns),
        "label_column_count": len(label_columns),
        "feature_columns": feature_columns,
        "label_columns": label_columns,
        "future_column_detected_in_features": leakage["future_column_detected_in_features"],
        "label_column_detected_in_features": leakage["label_column_detected_in_features"],
        "feature_column_detected_in_labels": leakage["feature_column_detected_in_labels"],
        "leakage_audit_status": leakage["status"],
        "train_all_null_feature_count": quality["splits"]["train"]["all_null_feature_count"],
        "train_constant_feature_count": quality["splits"]["train"]["constant_feature_count"],
        "train_high_null_feature_count": quality["splits"]["train"]["high_null_feature_count"],
        "train_feature_variance_available": quality["splits"]["train"]["feature_variance_available"],
        "validation_feature_variance_available": quality["splits"]["validation"]["feature_variance_available"],
        "test_feature_variance_available": quality["splits"]["test"]["feature_variance_available"],
        "target_date_min": date_min,
        "target_date_max": date_max,
        "train_target_date_count": splits["train"]["target_date_count"],
        "validation_target_date_count": splits["validation"]["target_date_count"],
        "test_target_date_count": splits["test"]["target_date_count"],
        "feature_table_modified": feature_table_modified,
        "label_table_modified": label_table_modified,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "dataset_output_path": str(dataset_path),
        "manifest_path": str(manifest_path),
        "audit_path": str(audit_path),
        "feature_table_path": str(feature_path),
        "label_table_path": str(label_path),
        "recommended_next_action": "Phase4-BF Formal LightGBM Training using this long-history training dataset.",
        "summary_path": str(summary_path),
    }
    _write_json(summary_path, summary)
    return summary


def build_long_history_dataset_frame(*, feature_frame: Any, label_frame: Any) -> tuple[Any, list[str], list[str]]:
    import pandas as pd

    feature = feature_frame.copy()
    labels = label_frame.copy()
    feature["target_date"] = feature["target_date"].astype(str)
    feature["code"] = feature["code"].astype(str)
    labels["target_date"] = labels["target_date"].astype(str)
    labels["code"] = labels["code"].astype(str)
    feature_columns = [
        column
        for column in feature.columns
        if column not in NON_FEATURE_COLUMNS
    ]
    label_columns = [column for column in LABEL_COLUMNS if column in labels.columns]
    prefixed_feature = feature[["target_date", "as_of_date", "code", "feature_version"] + feature_columns].rename(
        columns={column: f"feature__{column}" for column in feature_columns}
    )
    prefixed_labels = labels[["target_date", "code", "label_version"] + label_columns].rename(
        columns={column: f"label__{column}" for column in label_columns}
    )
    merged = prefixed_feature.merge(prefixed_labels, on=["target_date", "code"], how="inner", validate="one_to_one")
    merged.insert(0, "dataset_version", DATASET_VERSION)
    merged["split"] = merged["target_date"].map(assign_time_series_split)
    merged["created_at"] = _now()
    meta = ["target_date", "as_of_date", "code", "dataset_version", "feature_version", "label_version", "split", "created_at"]
    ordered = meta + [f"feature__{column}" for column in feature_columns] + [f"label__{column}" for column in label_columns]
    return merged[ordered], feature_columns, label_columns


def assign_time_series_split(target_date: str) -> str:
    if target_date <= TRAIN_END:
        return "train"
    if target_date <= VALIDATION_END:
        return "validation"
    return "test"


def audit_dataset_frame(dataset: Any, *, feature_columns: list[str], label_columns: list[str]) -> dict[str, Any]:
    columns = [str(column) for column in dataset.columns]
    prefixed_feature_columns = [f"feature__{column}" for column in feature_columns]
    prefixed_label_columns = [f"label__{column}" for column in label_columns]
    future_column_detected = any(
        column.replace("feature__", "", 1).startswith(("future_return_", "future_max_return_", "future_max_drawdown_", "top_decile_", "downside_bad_"))
        for column in prefixed_feature_columns
    )
    label_column_detected = any("label" in column.replace("feature__", "", 1).lower() for column in prefixed_feature_columns)
    feature_in_labels = any(column.replace("label__", "", 1).startswith("feature_") for column in prefixed_label_columns)
    forbidden_feature_columns = [
        column for column in prefixed_feature_columns if is_forbidden_column(column.replace("feature__", "", 1))
    ]
    unprefixed_label_columns = [column for column in columns if column in LABEL_COLUMNS]
    separated = bool(prefixed_feature_columns) and bool(prefixed_label_columns) and not unprefixed_label_columns
    status = "OK" if not (future_column_detected or label_column_detected or feature_in_labels or forbidden_feature_columns or unprefixed_label_columns) and separated else "ERROR"
    return {
        "status": status,
        "future_column_detected_in_features": future_column_detected,
        "label_column_detected_in_features": label_column_detected,
        "feature_column_detected_in_labels": feature_in_labels,
        "forbidden_feature_columns": forbidden_feature_columns,
        "unprefixed_label_columns": unprefixed_label_columns,
        "feature_label_columns_separated": separated,
        "messages": [] if status == "OK" else ["dataset leakage audit failed"],
    }


def compute_dataset_feature_quality(dataset: Any, *, feature_columns: list[str]) -> dict[str, Any]:
    splits = {
        "train": _split_feature_quality(dataset, feature_columns, TRAIN_START, TRAIN_END),
        "validation": _split_feature_quality(dataset, feature_columns, VALIDATION_START, VALIDATION_END),
        "test": _split_feature_quality(dataset, feature_columns, TEST_START, TEST_END),
    }
    status = "OK" if (
        splits["train"]["all_null_feature_count"] == 0
        and splits["train"]["feature_variance_available"] is True
        and splits["validation"]["feature_variance_available"] is True
        and splits["test"]["feature_variance_available"] is True
    ) else "ERROR"
    return {"status": status, "splits": splits}


def _split_feature_quality(dataset: Any, feature_columns: list[str], start: str, end: str) -> dict[str, Any]:
    split = dataset[(dataset["target_date"].astype(str) >= start) & (dataset["target_date"].astype(str) <= end)]
    prefixed = [f"feature__{column}" for column in feature_columns if not column.startswith("missing_flags_")]
    if split.empty:
        return {
            "row_count": 0,
            "all_null_feature_count": len(prefixed),
            "constant_feature_count": len(prefixed),
            "high_null_feature_count": len(prefixed),
            "feature_variance_available": False,
        }
    non_null = {column: float(split[column].notna().mean()) for column in prefixed}
    unique = {column: int(split[column].nunique(dropna=True)) for column in prefixed}
    variance = {column: _safe_float(split[column].var(skipna=True)) for column in prefixed}
    return {
        "row_count": int(len(split)),
        "all_null_feature_count": sum(1 for column in prefixed if non_null[column] == 0.0),
        "constant_feature_count": sum(1 for column in prefixed if unique[column] <= 1),
        "high_null_feature_count": sum(1 for column in prefixed if non_null[column] < (1.0 - HIGH_NULL_THRESHOLD)),
        "feature_variance_available": any(value is not None and value > 0 for value in variance.values()),
    }


def split_stats(dataset: Any) -> dict[str, dict[str, Any]]:
    return {
        "train": _one_split_stats(dataset, TRAIN_START, TRAIN_END),
        "validation": _one_split_stats(dataset, VALIDATION_START, VALIDATION_END),
        "test": _one_split_stats(dataset, TEST_START, TEST_END),
    }


def _one_split_stats(dataset: Any, start: str, end: str) -> dict[str, Any]:
    split = dataset[(dataset["target_date"].astype(str) >= start) & (dataset["target_date"].astype(str) <= end)]
    positive = int(split["label__momentum_candidate_label"].sum()) if not split.empty else 0
    dates = sorted(split["target_date"].astype(str).unique().tolist()) if not split.empty else []
    return {
        "row_count": int(len(split)),
        "target_date_count": len(dates),
        "target_date_min": dates[0] if dates else None,
        "target_date_max": dates[-1] if dates else None,
        "positive_count": positive,
        "positive_rate": _rate(positive, len(split)),
    }


def _resolve_readiness(
    *,
    joined_row_count: int,
    join_success_rate: float,
    leakage_status: str,
    quality_status: str,
    splits: dict[str, dict[str, Any]],
    feature_table_modified: bool,
    label_table_modified: bool,
) -> str:
    if joined_row_count <= 0 or join_success_rate <= 0:
        return BLOCKED_JOIN
    if any(value["row_count"] <= 0 or value["positive_count"] <= 0 for value in splits.values()):
        return BLOCKED_SPLIT
    if leakage_status != "OK" or feature_table_modified or label_table_modified:
        return BLOCKED_LEAKAGE
    if quality_status != "OK":
        return BLOCKED_QUALITY
    return READY


def _read_frame(path: Path) -> Any:
    import pandas as pd

    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.DataFrame(create_storage_backend("jsonl").read_records(path))


def _write_frame(path: Path, frame: Any, output_format: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "parquet":
        frame.to_parquet(path, index=False, engine="pyarrow")
        return
    create_storage_backend(output_format).write_records(path, frame.astype(object).where(frame.notna(), None).to_dict("records"))


def _dataset_output_path(datasets_root: Path, output_format: str, suffix: str) -> Path:
    return create_storage_backend(output_format).path_for(datasets_root / f"phase4be_long_history_dataset_{suffix}")


def _date_range(dataset: Any) -> tuple[str | None, str | None]:
    dates = sorted(dataset["target_date"].astype(str).unique().tolist()) if not dataset.empty else []
    return (dates[0] if dates else None, dates[-1] if dates else None)


def _safe_candidate_output_paths(runtime_dir: Path, *paths: Path) -> bool:
    root = (runtime_dir.resolve() / "candidate_ai").resolve()
    for path in paths:
        try:
            path.resolve().relative_to(root)
        except ValueError:
            return False
    return True


def _blocked_summary(*, readiness_status: str, reason: str, paths: RuntimePaths, summary_path: Path) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness_status,
        "block_reason": reason,
        "dataset_rebuild_executed": False,
        "feature_row_count": 0,
        "label_row_count": 0,
        "joined_row_count": 0,
        "join_success_rate": 0.0,
        "train_row_count": 0,
        "validation_row_count": 0,
        "test_row_count": 0,
        "feature_column_count": 0,
        "label_column_count": 0,
        "leakage_audit_status": "SKIPPED",
        "future_column_detected_in_features": False,
        "label_column_detected_in_features": False,
        "feature_column_detected_in_labels": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "runtime_dir": str(paths.runtime_dir),
        "recommended_next_action": "Fix the dataset rebuild blocker, then rerun Phase4-BE.",
        "summary_path": str(summary_path),
    }


def _safe_float(value: Any) -> float | None:
    try:
        if value != value:
            return None
        return round(float(value), 10)
    except (TypeError, ValueError):
        return None


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _file_hash(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
