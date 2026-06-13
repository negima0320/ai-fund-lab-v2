#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
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

from ai_fund_lab_v2.data_store import create_storage_backend  # noqa: E402
from ai_fund_lab_v2.runtime import RuntimePaths  # noqa: E402
from scripts.build_phase4al_labels import (  # noqa: E402
    DOWNSIDE_BAD_THRESHOLD_20D,
    FORBIDDEN_NON_LABEL_TERMS,
    LABEL_COLUMNS,
    LABEL_VERSION,
)

PHASE = "Phase4-BD"
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4bd_long_history_label_regeneration_summary.json")
PHASE4BC_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4bc_long_history_feature_regeneration_summary.json")

READY_INPUT = "READY_FOR_LONG_HISTORY_LABEL_REGENERATION"
READY = "READY_FOR_LONG_HISTORY_DATASET_REBUILD"
BLOCKED_GENERATION = "BLOCKED_BY_LABEL_GENERATION"
BLOCKED_COVERAGE = "BLOCKED_BY_LABEL_COVERAGE"
BLOCKED_FEATURE_MODIFIED = "BLOCKED_BY_FEATURE_TABLE_MODIFIED"
BLOCKED_PATH = "BLOCKED_BY_OUTPUT_PATH_SAFETY"

TRAIN_START = "2021-09-09"
TRAIN_END = "2024-12-31"
VALIDATION_START = "2025-01-01"
VALIDATION_END = "2025-12-31"
TEST_START = "2026-01-01"
TEST_END = "2026-05-15"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Phase4-BD long-history Candidate label table.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--report-dir", default="reports/candidate_ai/full_range")
    parser.add_argument("--input-format", choices=("parquet", "jsonl"), default="parquet")
    parser.add_argument("--output-format", choices=("parquet", "jsonl"), default="parquet")
    parser.add_argument("--phase4bc-summary", default=str(PHASE4BC_SUMMARY_PATH))
    args = parser.parse_args(argv)
    summary = build_phase4bd_long_history_labels(
        runtime_dir=args.runtime_dir,
        report_dir=args.report_dir,
        input_format=args.input_format,
        output_format=args.output_format,
        phase4bc_summary_path=Path(args.phase4bc_summary),
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def build_phase4bd_long_history_labels(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    input_format: str = "parquet",
    output_format: str = "parquet",
    phase4bc_summary_path: Path = PHASE4BC_SUMMARY_PATH,
) -> dict[str, Any]:
    paths = RuntimePaths(runtime_dir=Path(runtime_dir))
    report_dir = Path(report_dir)
    summary_path = report_dir / SUMMARY_PATH.name
    bc_summary = _read_json_optional(phase4bc_summary_path)
    normalized_path = _real_runtime_normalized_path(paths, input_format)
    labels_root = paths.runtime_dir / "candidate_ai" / "labels"
    manifests_root = paths.runtime_dir / "candidate_ai" / "manifests"
    audit_root = paths.runtime_dir / "candidate_ai" / "audit"

    if bc_summary.get("readiness_status") != READY_INPUT:
        summary = _blocked_summary(
            readiness_status=BLOCKED_GENERATION,
            reason="Phase4-BC summary is missing or not ready for long-history label regeneration.",
            paths=paths,
            normalized_path=normalized_path,
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary
    if not _safe_candidate_output_paths(paths.runtime_dir, labels_root, manifests_root, audit_root):
        summary = _blocked_summary(
            readiness_status=BLOCKED_PATH,
            reason="Candidate AI label output paths are not under .runtime/candidate_ai.",
            paths=paths,
            normalized_path=normalized_path,
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary

    feature_table_path = Path(str(bc_summary.get("feature_output_path") or ""))
    feature_hash_before = _file_hash(feature_table_path)
    if not normalized_path.is_file() or not feature_table_path.is_file():
        summary = _blocked_summary(
            readiness_status=BLOCKED_GENERATION,
            reason="Required normalized input or Phase4-BC feature artifact is missing.",
            paths=paths,
            normalized_path=normalized_path,
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary

    normalized = _read_normalized_frame(normalized_path, input_format)
    if normalized.empty:
        summary = _blocked_summary(
            readiness_status=BLOCKED_GENERATION,
            reason="Long-history normalized input is empty.",
            paths=paths,
            normalized_path=normalized_path,
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary

    labels = build_long_history_label_frame(
        normalized,
        source_snapshot_id=f"phase4bc:{bc_summary.get('manifest_path') or feature_table_path}",
    )
    label_dates = sorted(labels["target_date"].dropna().astype(str).unique().tolist()) if not labels.empty else []
    suffix = f"{label_dates[0] if label_dates else 'none'}_{label_dates[-1] if label_dates else 'none'}"
    label_path = _label_output_path(labels_root, output_format, suffix)
    manifest_path = manifests_root / f"phase4bd_long_history_labels_manifest_{suffix}.json"
    audit_path = audit_root / f"phase4bd_long_history_labels_audit_{suffix}.json"

    labels_root.mkdir(parents=True, exist_ok=True)
    manifests_root.mkdir(parents=True, exist_ok=True)
    audit_root.mkdir(parents=True, exist_ok=True)
    _write_label_frame(label_path, labels, output_format)

    feature_hash_after = _file_hash(feature_table_path)
    feature_table_modified = feature_hash_before != feature_hash_after
    feature_table_joined = _feature_table_contains_label_columns(feature_table_path)
    leakage = audit_label_isolation(labels=labels, feature_table_path=feature_table_path)
    leakage_audit_status = "OK" if leakage["status"] == "OK" and not feature_table_modified and not feature_table_joined else "ERROR"
    split_stats = _split_stats(labels)
    tail_stats = _tail_unavailable_stats(normalized)
    counts = _label_counts(labels)
    positive_rate = _rate(counts["momentum_candidate_label_count"], len(labels))
    coverage_ok = _label_coverage_ok(labels, split_stats)
    readiness_status = _resolve_readiness(
        label_rows=len(labels),
        coverage_ok=coverage_ok,
        feature_table_modified=feature_table_modified,
        feature_table_joined=feature_table_joined,
        leakage_audit_status=leakage_audit_status,
    )

    audit_payload = {
        "phase": PHASE,
        "created_at": _now(),
        "label_isolation": leakage,
        "leakage_audit_status": leakage_audit_status,
        "feature_table_modified": feature_table_modified,
        "feature_table_joined": feature_table_joined,
        "label_counts": counts,
        "split_stats": split_stats,
        "tail_unavailable": tail_stats,
    }
    manifest_payload = {
        "phase": PHASE,
        "created_at": _now(),
        "label_version": LABEL_VERSION,
        "data_source_type": "real_runtime",
        "input_sources": ["daily_quotes_normalized_real_runtime_long_history", "phase4bc_feature_table_reference"],
        "normalized_input_path": str(normalized_path),
        "feature_table_path_reference": str(feature_table_path),
        "feature_table_joined": False,
        "label_output_path": str(label_path),
        "manifest_path": str(manifest_path),
        "audit_path": str(audit_path),
        "target_date_min": label_dates[0] if label_dates else None,
        "target_date_max": label_dates[-1] if label_dates else None,
        "target_date_count": len(label_dates),
        "label_row_count": int(len(labels)),
        "label_column_count": len(LABEL_COLUMNS),
        "source_snapshot_id": f"phase4bc:{bc_summary.get('manifest_path') or feature_table_path}",
        "dataset_rebuild_executed": False,
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
        "label_generation_executed": True,
        "normalized_row_count": int(len(normalized)),
        "label_row_count": int(len(labels)),
        "label_column_count": len(LABEL_COLUMNS),
        "label_target_date_min": label_dates[0] if label_dates else None,
        "label_target_date_max": label_dates[-1] if label_dates else None,
        "label_target_date_count": len(label_dates),
        "code_count": int(labels["code"].nunique()) if not labels.empty else 0,
        "future_return_5d_count": counts["future_return_5d_count"],
        "future_return_10d_count": counts["future_return_10d_count"],
        "future_return_20d_count": counts["future_return_20d_count"],
        "future_max_return_20d_count": counts["future_max_return_20d_count"],
        "future_max_drawdown_20d_count": counts["future_max_drawdown_20d_count"],
        "top_decile_20d_count": counts["top_decile_20d_count"],
        "downside_bad_20d_count": counts["downside_bad_20d_count"],
        "momentum_candidate_label_count": counts["momentum_candidate_label_count"],
        "momentum_candidate_label_positive_rate": positive_rate,
        "train_label_row_count_estimate": split_stats["train"]["row_count"],
        "validation_label_row_count_estimate": split_stats["validation"]["row_count"],
        "test_label_row_count_estimate": split_stats["test"]["row_count"],
        "train_positive_rate": split_stats["train"]["positive_rate"],
        "validation_positive_rate": split_stats["validation"]["positive_rate"],
        "test_positive_rate": split_stats["test"]["positive_rate"],
        "label_unavailable_tail_target_date_count": tail_stats["target_date_count"],
        "label_unavailable_tail_row_count": tail_stats["row_count"],
        "feature_table_modified": feature_table_modified,
        "feature_table_joined": feature_table_joined,
        "leakage_audit_status": leakage_audit_status,
        "dataset_rebuild_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "label_output_path": str(label_path),
        "manifest_path": str(manifest_path),
        "audit_path": str(audit_path),
        "feature_table_path_reference": str(feature_table_path),
        "normalized_input_path": str(normalized_path),
        "recommended_next_action": "Phase4-BE Long History Dataset Rebuild: join feature and label tables for training only; inference datasets must not include labels.",
        "summary_path": str(summary_path),
    }
    _write_json(summary_path, summary)
    return summary


def build_long_history_label_frame(normalized: Any, *, source_snapshot_id: str) -> Any:
    import numpy as np
    import pandas as pd

    frame = normalized.copy()
    frame["target_date"] = frame.get("Date", frame.get("target_date")).astype(str)
    frame["code"] = frame.get("Code", frame.get("code")).astype(str).str.strip()
    frame["Close"] = pd.to_numeric(frame["Close"], errors="coerce")
    frame = frame.dropna(subset=["target_date", "code", "Close"]).sort_values(["code", "target_date"]).reset_index(drop=True)
    grouped = frame.groupby("code", sort=False, group_keys=False)
    close = frame["Close"]
    future_start = grouped["target_date"].shift(-1)
    future_end = grouped["target_date"].shift(-20)
    future_return_5d = grouped["Close"].shift(-5) / close - 1.0
    future_return_10d = grouped["Close"].shift(-10) / close - 1.0
    future_return_20d = grouped["Close"].shift(-20) / close - 1.0
    future_max = grouped["Close"].transform(_future_rolling_max_20)
    future_min = grouped["Close"].transform(_future_rolling_min_20)
    labels = frame[["target_date", "code"]].copy()
    labels["label_version"] = LABEL_VERSION
    labels["label_horizon"] = "20d"
    labels["future_start_date"] = future_start
    labels["future_end_date"] = future_end
    labels["created_at"] = _now()
    labels["source_snapshot_id"] = source_snapshot_id
    labels["future_return_5d"] = future_return_5d
    labels["future_return_10d"] = future_return_10d
    labels["future_return_20d"] = future_return_20d
    labels["future_max_return_20d"] = future_max / close - 1.0
    labels["future_max_drawdown_20d"] = future_min / close - 1.0
    labels = labels.dropna(
        subset=[
            "future_return_5d",
            "future_return_10d",
            "future_return_20d",
            "future_max_return_20d",
            "future_max_drawdown_20d",
            "future_start_date",
            "future_end_date",
        ]
    ).reset_index(drop=True)
    for column in ("future_return_5d", "future_return_10d", "future_return_20d", "future_max_return_20d", "future_max_drawdown_20d"):
        labels[column] = labels[column].replace([np.inf, -np.inf], np.nan).round(6)
    labels = labels.dropna(subset=["future_return_20d", "future_max_return_20d", "future_max_drawdown_20d"])
    rank = labels.groupby("target_date")["future_return_20d"].rank(method="first", ascending=False)
    group_size = labels.groupby("target_date")["future_return_20d"].transform("size")
    top_count = np.ceil(group_size * 0.1)
    labels["top_decile_20d"] = (rank <= top_count).astype(bool)
    labels["downside_bad_20d"] = (labels["future_max_drawdown_20d"] <= DOWNSIDE_BAD_THRESHOLD_20D).astype(bool)
    labels["momentum_candidate_label"] = (labels["top_decile_20d"] & ~labels["downside_bad_20d"]).astype(bool)
    return labels


def audit_label_isolation(*, labels: Any, feature_table_path: Path) -> dict[str, Any]:
    columns = [str(column) for column in labels.columns]
    unexpected_forbidden = sorted(
        column
        for column in columns
        if _contains_forbidden_non_label_term(column) and column not in LABEL_COLUMNS
    )
    feature_has_labels = _feature_table_contains_label_columns(feature_table_path)
    status = "OK" if len(labels) > 0 and not unexpected_forbidden and not feature_has_labels else "ERROR"
    return {
        "status": status,
        "unexpected_forbidden_columns": unexpected_forbidden,
        "feature_table_contains_label_columns": feature_has_labels,
        "label_table_physically_separate": "/candidate_ai/labels/" not in str(feature_table_path).replace("\\", "/"),
        "messages": [] if status == "OK" else ["label isolation audit failed"],
    }


def _future_rolling_max_20(values: Any) -> Any:
    return values.shift(-1).iloc[::-1].rolling(20, min_periods=20).max().iloc[::-1]


def _future_rolling_min_20(values: Any) -> Any:
    return values.shift(-1).iloc[::-1].rolling(20, min_periods=20).min().iloc[::-1]


def _label_counts(labels: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for column in LABEL_COLUMNS:
        if column in {"top_decile_20d", "downside_bad_20d", "momentum_candidate_label"}:
            counts[f"{column}_count"] = int(labels[column].sum()) if column in labels else 0
        else:
            counts[f"{column}_count"] = int(labels[column].notna().sum()) if column in labels else 0
    return counts


def _split_stats(labels: Any) -> dict[str, dict[str, Any]]:
    return {
        "train": _one_split_stats(labels, TRAIN_START, TRAIN_END),
        "validation": _one_split_stats(labels, VALIDATION_START, VALIDATION_END),
        "test": _one_split_stats(labels, TEST_START, TEST_END),
    }


def _one_split_stats(labels: Any, start: str, end: str) -> dict[str, Any]:
    split = labels[(labels["target_date"].astype(str) >= start) & (labels["target_date"].astype(str) <= end)]
    positives = int(split["momentum_candidate_label"].sum()) if not split.empty else 0
    dates = sorted(split["target_date"].astype(str).unique().tolist()) if not split.empty else []
    return {
        "row_count": int(len(split)),
        "target_date_min": dates[0] if dates else None,
        "target_date_max": dates[-1] if dates else None,
        "target_date_count": len(dates),
        "positive_count": positives,
        "positive_rate": _rate(positives, len(split)),
    }


def _tail_unavailable_stats(normalized: Any) -> dict[str, Any]:
    frame = normalized.copy()
    frame["target_date"] = frame.get("Date", frame.get("target_date")).astype(str)
    frame["code"] = frame.get("Code", frame.get("code")).astype(str).str.strip()
    frame = frame.dropna(subset=["target_date", "code"]).sort_values(["code", "target_date"])
    index_from_end = frame.groupby("code", sort=False).cumcount(ascending=False)
    unavailable = frame[index_from_end < 20]
    dates = sorted(unavailable["target_date"].astype(str).unique().tolist())
    return {
        "target_date_count": len(dates),
        "target_date_min": dates[0] if dates else None,
        "target_date_max": dates[-1] if dates else None,
        "row_count": int(len(unavailable)),
    }


def _label_coverage_ok(labels: Any, split_stats: dict[str, dict[str, Any]]) -> bool:
    if labels.empty:
        return False
    return all(stats["row_count"] > 0 and stats["positive_count"] > 0 for stats in split_stats.values())


def _resolve_readiness(
    *,
    label_rows: int,
    coverage_ok: bool,
    feature_table_modified: bool,
    feature_table_joined: bool,
    leakage_audit_status: str,
) -> str:
    if label_rows <= 0:
        return BLOCKED_GENERATION
    if feature_table_modified or feature_table_joined:
        return BLOCKED_FEATURE_MODIFIED
    if leakage_audit_status != "OK":
        return BLOCKED_FEATURE_MODIFIED
    if not coverage_ok:
        return BLOCKED_COVERAGE
    return READY


def _feature_table_contains_label_columns(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        import pandas as pd

        columns = [str(column) for column in pd.read_parquet(path).columns] if path.suffix == ".parquet" else _json_columns(path)
    except Exception:
        columns = _json_columns(path)
    return any(
        column in LABEL_COLUMNS
        or column.startswith(("future_return_", "future_max_return_", "future_max_drawdown_", "top_decile_", "downside_bad_"))
        or "label" in column
        for column in columns
    )


def _json_columns(path: Path) -> list[str]:
    payload = _read_json_optional(path)
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    if not rows:
        return []
    columns: set[str] = set()
    for row in rows[:100]:
        columns.update(str(column) for column in row.keys())
    return sorted(columns)


def _contains_forbidden_non_label_term(column: str) -> bool:
    normalized = column.lower()
    tokens = [token for token in normalized.replace("-", "_").split("_") if token]
    return any(term in normalized or term in tokens for term in FORBIDDEN_NON_LABEL_TERMS)


def _read_normalized_frame(path: Path, input_format: str) -> Any:
    import pandas as pd

    if input_format == "parquet":
        return pd.read_parquet(path)
    return pd.DataFrame(create_storage_backend(input_format).read_records(path))


def _write_label_frame(path: Path, labels: Any, output_format: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "parquet":
        labels.to_parquet(path, index=False, engine="pyarrow")
        return
    create_storage_backend(output_format).write_records(path, labels.astype(object).where(labels.notna(), None).to_dict("records"))


def _label_output_path(labels_root: Path, output_format: str, suffix: str) -> Path:
    return create_storage_backend(output_format).path_for(labels_root / f"phase4bd_long_history_labels_{suffix}")


def _real_runtime_normalized_path(paths: RuntimePaths, input_format: str) -> Path:
    return create_storage_backend(input_format).path_for(
        paths.runtime_dir / "data" / "raw_normalized_real_runtime" / "jquants" / "equities_bars_daily" / "data"
    )


def _safe_candidate_output_paths(runtime_dir: Path, *paths: Path) -> bool:
    root = (runtime_dir.resolve() / "candidate_ai").resolve()
    for path in paths:
        try:
            path.resolve().relative_to(root)
        except ValueError:
            return False
    return True


def _blocked_summary(*, readiness_status: str, reason: str, paths: RuntimePaths, normalized_path: Path, summary_path: Path) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness_status,
        "block_reason": reason,
        "label_generation_executed": False,
        "normalized_row_count": 0,
        "label_row_count": 0,
        "label_column_count": len(LABEL_COLUMNS),
        "label_target_date_min": None,
        "label_target_date_max": None,
        "label_target_date_count": 0,
        "code_count": 0,
        "feature_table_modified": False,
        "feature_table_joined": False,
        "leakage_audit_status": "SKIPPED",
        "dataset_rebuild_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "normalized_input_path": str(normalized_path),
        "runtime_dir": str(paths.runtime_dir),
        "recommended_next_action": "Fix the label regeneration blocker, then rerun Phase4-BD.",
        "summary_path": str(summary_path),
    }


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
