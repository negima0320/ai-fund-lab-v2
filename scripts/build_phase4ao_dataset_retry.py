#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.runtime import RuntimePaths  # noqa: E402
from scripts.build_phase4am_dataset import (  # noqa: E402
    DATASET_META_COLUMNS,
    DATASET_VERSION,
    LABEL_COLUMNS,
    audit_dataset_rows,
    build_dataset_rows,
    _feature_columns,
    _feature_label_columns_separated,
    _safe_divide,
)

PHASE = "Phase4-AO"
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ao_dataset_retry_summary.json")
PHASE4AN_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4an_historical_feature_coverage_summary.json")
PHASE4AL_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4al_label_generation_summary.json")

READY_AN = "READY_FOR_DATASET_BUILDER_RETRY"
READY_AL = "READY_FOR_DATASET_BUILDER"
READY = "READY_FOR_FIRST_LIGHTGBM_TRAINING"
BLOCKED_JOIN_COVERAGE = "BLOCKED_BY_JOIN_COVERAGE"
BLOCKED_DATASET_BUILDER = "BLOCKED_BY_DATASET_BUILDER"
BLOCKED_LEAKAGE = "BLOCKED_BY_LEAKAGE_AUDIT"
BLOCKED_PATH = "BLOCKED_BY_OUTPUT_PATH_SAFETY"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Retry Phase4 dataset build using Phase4-AN historical features.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--report-dir", default="reports/candidate_ai/full_range")
    parser.add_argument("--phase4an-summary", default=str(PHASE4AN_SUMMARY_PATH))
    parser.add_argument("--phase4al-summary", default=str(PHASE4AL_SUMMARY_PATH))
    args = parser.parse_args(argv)
    summary = build_phase4ao_dataset_retry(
        runtime_dir=args.runtime_dir,
        report_dir=args.report_dir,
        phase4an_summary_path=Path(args.phase4an_summary),
        phase4al_summary_path=Path(args.phase4al_summary),
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def build_phase4ao_dataset_retry(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    phase4an_summary_path: Path = PHASE4AN_SUMMARY_PATH,
    phase4al_summary_path: Path = PHASE4AL_SUMMARY_PATH,
) -> dict[str, Any]:
    paths = RuntimePaths(runtime_dir=Path(runtime_dir))
    report_dir = Path(report_dir)
    summary_path = report_dir / SUMMARY_PATH.name
    an_summary = _read_json_optional(phase4an_summary_path)
    al_summary = _read_json_optional(phase4al_summary_path)
    datasets_dir = paths.runtime_dir / "candidate_ai" / "datasets"
    manifests_dir = paths.runtime_dir / "candidate_ai" / "manifests"
    audit_dir = paths.runtime_dir / "candidate_ai" / "audit"

    if an_summary.get("readiness_status") != READY_AN or al_summary.get("readiness_status") != READY_AL:
        summary = _blocked_summary(
            readiness_status=BLOCKED_DATASET_BUILDER,
            reason="Phase4-AN or Phase4-AL summary is missing or not ready.",
            paths=paths,
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary
    if not _safe_runtime_output_path(paths.runtime_dir, datasets_dir):
        summary = _blocked_summary(
            readiness_status=BLOCKED_PATH,
            reason="Dataset retry output path is not under .runtime/candidate_ai/datasets.",
            paths=paths,
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary

    feature_path = Path(str(an_summary.get("historical_feature_output_path") or ""))
    label_path = Path(str(al_summary.get("label_output_path") or ""))
    feature_rows = _read_rows(feature_path)
    label_rows = _read_rows(label_path)
    feature_hash_before = _file_hash(feature_path)
    label_hash_before = _file_hash(label_path)

    joined_rows = build_dataset_rows(feature_rows=feature_rows, label_rows=label_rows)
    feature_hash_after = _file_hash(feature_path)
    label_hash_after = _file_hash(label_path)
    feature_table_modified = feature_hash_before != feature_hash_after
    label_table_modified = label_hash_before != label_hash_after
    leakage = audit_dataset_rows(joined_rows)
    join_success_rate = _safe_divide(len(joined_rows), len(label_rows))
    split_counts = Counter(str(row.get("split") or "unknown") for row in joined_rows)
    feature_columns = _feature_columns(feature_rows)
    label_columns = [column for column in LABEL_COLUMNS if any(f"label__{column}" in row for row in joined_rows)]
    future_column_detected_in_features = bool(leakage.get("forbidden_feature_column_detected"))
    label_column_detected_in_features = bool(leakage.get("unprefixed_label_column_detected"))
    leakage_audit_status = (
        "OK"
        if leakage["status"] == "OK" and not feature_table_modified and not label_table_modified
        else "ERROR"
    )
    readiness_status = _resolve_readiness(
        joined_row_count=len(joined_rows),
        join_success_rate=join_success_rate,
        leakage_audit_status=leakage_audit_status,
        feature_table_modified=feature_table_modified,
        label_table_modified=label_table_modified,
    )

    date_min, date_max = _dataset_date_range(joined_rows)
    datasets_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = datasets_dir / f"phase4ao_dataset_retry_{date_min or 'none'}_{date_max or 'none'}.json"
    manifest_path = manifests_dir / f"phase4ao_dataset_retry_manifest_{date_min or 'none'}_{date_max or 'none'}.json"
    audit_path = audit_dir / f"phase4ao_dataset_retry_audit_{date_min or 'none'}_{date_max or 'none'}.json"
    audit_payload = {
        **leakage,
        "leakage_audit_status": leakage_audit_status,
        "feature_table_modified": feature_table_modified,
        "label_table_modified": label_table_modified,
        "future_column_detected_in_features": future_column_detected_in_features,
        "label_column_detected_in_features": label_column_detected_in_features,
        "feature_label_columns_separated": _feature_label_columns_separated(joined_rows),
        "joined_row_count": len(joined_rows),
        "join_success_rate": join_success_rate,
        "split_counts": dict(split_counts),
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
        "feature_row_count": len(feature_rows),
        "label_row_count": len(label_rows),
        "joined_row_count": len(joined_rows),
        "join_success_rate": join_success_rate,
        "feature_column_count": len(feature_columns),
        "label_column_count": len(label_columns),
        "split_counts": dict(split_counts),
        "leakage_audit_status": leakage_audit_status,
        "dataset_builder_executed": True,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
    }
    _write_json(dataset_path, {"rows": joined_rows})
    _write_json(audit_path, audit_payload)
    _write_json(manifest_path, manifest_payload)

    summary = {
        "phase": PHASE,
        "status": "OK" if readiness_status == READY else "BLOCKED",
        "readiness_status": readiness_status,
        "dataset_builder_executed": True,
        "feature_row_count": len(feature_rows),
        "label_row_count": len(label_rows),
        "joined_row_count": len(joined_rows),
        "join_success_rate": join_success_rate,
        "train_row_count": split_counts.get("train", 0),
        "validation_row_count": split_counts.get("validation", 0),
        "test_row_count": split_counts.get("test", 0),
        "feature_column_count": len(feature_columns),
        "label_column_count": len(label_columns),
        "leakage_audit_status": leakage_audit_status,
        "feature_label_columns_separated": _feature_label_columns_separated(joined_rows),
        "future_column_detected_in_features": future_column_detected_in_features,
        "label_column_detected_in_features": label_column_detected_in_features,
        "feature_table_modified": feature_table_modified,
        "label_table_modified": label_table_modified,
        "dataset_output_path": str(dataset_path),
        "manifest_path": str(manifest_path),
        "audit_path": str(audit_path),
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "recommended_next_action": _recommended_next_action(readiness_status),
        "summary_path": str(summary_path),
    }
    _write_json(summary_path, summary)
    return summary


def _resolve_readiness(
    *,
    joined_row_count: int,
    join_success_rate: float,
    leakage_audit_status: str,
    feature_table_modified: bool,
    label_table_modified: bool,
) -> str:
    if joined_row_count <= 0 or join_success_rate <= 0:
        return BLOCKED_JOIN_COVERAGE
    if leakage_audit_status != "OK" or feature_table_modified or label_table_modified:
        return BLOCKED_LEAKAGE
    return READY


def _recommended_next_action(readiness_status: str) -> str:
    if readiness_status == READY:
        return "Phase4-AP First LightGBM Training."
    if readiness_status == BLOCKED_JOIN_COVERAGE:
        return "Recheck Phase4-AN historical feature coverage and Phase4-AL label target dates before training."
    return "Fix the blocking dataset retry condition, then rerun Phase4-AO."


def _dataset_date_range(rows: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    dates = sorted({str(row.get("target_date") or "") for row in rows if row.get("target_date")})
    return (dates[0] if dates else None, dates[-1] if dates else None)


def _safe_runtime_output_path(runtime_dir: Path, datasets_dir: Path) -> bool:
    try:
        datasets_dir.resolve().relative_to((runtime_dir.resolve() / "candidate_ai" / "datasets").resolve())
        return True
    except ValueError:
        return False


def _blocked_summary(
    *,
    readiness_status: str,
    reason: str,
    paths: RuntimePaths,
    summary_path: Path,
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness_status,
        "block_reason": reason,
        "dataset_builder_executed": False,
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
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "runtime_dir": str(paths.runtime_dir),
        "recommended_next_action": "Fix the blocking condition, then rerun Phase4-AO.",
        "summary_path": str(summary_path),
    }


def _read_rows(path: Path) -> list[dict[str, Any]]:
    payload = _read_json_optional(path)
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    return [dict(row) for row in rows]


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _file_hash(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
