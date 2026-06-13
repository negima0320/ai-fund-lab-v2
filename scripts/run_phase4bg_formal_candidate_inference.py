#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.candidate_ai.validation import is_forbidden_column  # noqa: E402
from ai_fund_lab_v2.runtime import RuntimePaths  # noqa: E402

PHASE = "Phase4-BG"
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4bg_formal_candidate_inference_summary.json")
TOP50_JSON_PATH = Path("reports/candidate_ai/full_range/phase4bg_formal_candidate_inference_top50.json")
TOP50_CSV_PATH = Path("reports/candidate_ai/full_range/phase4bg_formal_candidate_inference_top50.csv")
PHASE4BF_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4bf_formal_lightgbm_training_summary.json")
PHASE4BC_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4bc_long_history_feature_regeneration_summary.json")

READY_INPUT = "READY_FOR_FORMAL_CANDIDATE_INFERENCE"
READY = "READY_FOR_FORMAL_CANDIDATE_QUALITY_AUDIT"
BLOCKED_MODEL = "BLOCKED_BY_MISSING_MODEL_ARTIFACT"
BLOCKED_FEATURE = "BLOCKED_BY_MISSING_FEATURE_TABLE"
BLOCKED_NO_ELIGIBLE = "BLOCKED_BY_NO_ELIGIBLE_INPUT"
BLOCKED_INFERENCE = "BLOCKED_BY_INFERENCE"
BLOCKED_LEAKAGE = "BLOCKED_BY_LEAKAGE_AUDIT"
BLOCKED_SCHEMA = "BLOCKED_BY_OUTPUT_SCHEMA"
BLOCKED_ALL_SAME = "BLOCKED_BY_ALL_SAME_SCORE"
BLOCKED_BOUNDARY = "BLOCKED_BY_RESPONSIBILITY_BOUNDARY"

TOP_N = 50


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase4-BG formal Candidate inference.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--report-dir", default="reports/candidate_ai/full_range")
    parser.add_argument("--phase4bf-summary", default=str(PHASE4BF_SUMMARY_PATH))
    parser.add_argument("--phase4bc-summary", default=str(PHASE4BC_SUMMARY_PATH))
    parser.add_argument("--top-n", type=int, default=TOP_N)
    args = parser.parse_args(argv)
    summary = run_phase4bg_formal_candidate_inference(
        runtime_dir=args.runtime_dir,
        report_dir=args.report_dir,
        phase4bf_summary_path=Path(args.phase4bf_summary),
        phase4bc_summary_path=Path(args.phase4bc_summary),
        top_n=args.top_n,
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def run_phase4bg_formal_candidate_inference(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    phase4bf_summary_path: Path = PHASE4BF_SUMMARY_PATH,
    phase4bc_summary_path: Path = PHASE4BC_SUMMARY_PATH,
    top_n: int = TOP_N,
) -> dict[str, Any]:
    paths = RuntimePaths(runtime_dir=Path(runtime_dir))
    report_dir = Path(report_dir)
    summary_path = report_dir / SUMMARY_PATH.name
    top50_json_path = report_dir / TOP50_JSON_PATH.name
    top50_csv_path = report_dir / TOP50_CSV_PATH.name
    bf_summary = _read_json_optional(phase4bf_summary_path)
    bc_summary = _read_json_optional(phase4bc_summary_path)
    inference_dir = paths.runtime_dir / "candidate_ai" / "inference"
    candidates_dir = paths.runtime_dir / "candidate_ai" / "candidates"

    if bf_summary.get("readiness_status") != READY_INPUT:
        summary = _blocked_summary(BLOCKED_MODEL, "Phase4-BF summary is missing or not ready.", summary_path)
        _write_json(summary_path, summary)
        return summary

    model_path = Path(str(bf_summary.get("model_artifact_path") or ""))
    model_manifest_path = Path(str(bf_summary.get("model_manifest_path") or ""))
    if not model_path.is_file() or not model_manifest_path.is_file():
        summary = _blocked_summary(BLOCKED_MODEL, "Formal model artifact or manifest is missing.", summary_path)
        _write_json(summary_path, summary)
        return summary

    if not _safe_runtime_output_path(paths.runtime_dir, inference_dir, "inference") or not _safe_runtime_output_path(
        paths.runtime_dir, candidates_dir, "candidates"
    ):
        summary = _blocked_summary(BLOCKED_SCHEMA, "Inference or candidates output path is not under .runtime/candidate_ai.", summary_path)
        _write_json(summary_path, summary)
        return summary

    model_payload = _read_pickle(model_path)
    model = model_payload.get("model")
    feature_columns = [str(column) for column in model_payload.get("feature_columns", [])]
    model_type = str(model_payload.get("model_type") or bf_summary.get("model_type") or "unknown")
    model_version = "phase4bf_formal_candidate_model"
    leakage = audit_inference_features(feature_columns)
    if leakage["status"] != "OK":
        summary = _blocked_summary(
            BLOCKED_LEAKAGE,
            "Formal inference feature leakage audit failed.",
            summary_path,
            model_type=model_type,
            future_column_used_as_feature=leakage["future_column_used_as_feature"],
            label_column_used_as_feature=leakage["label_column_used_as_feature"],
        )
        _write_json(summary_path, summary)
        return summary

    feature_path = Path(str(bc_summary.get("feature_output_path") or ""))
    feature_frame = _read_feature_frame(feature_path)
    if feature_frame is None or feature_frame.empty:
        summary = _blocked_summary(BLOCKED_FEATURE, "Long-history Candidate feature table is missing or empty.", summary_path, model_type=model_type)
        _write_json(summary_path, summary)
        return summary

    target_date = str(feature_frame["target_date"].max())
    latest_frame = feature_frame[feature_frame["target_date"].astype(str) == target_date].copy()
    eligible_frame = latest_frame[latest_frame["universe_eligible"].astype(bool) & latest_frame["excluded_reason"].fillna("").astype(str).eq("")].copy()
    excluded_input_count = int(len(latest_frame) - len(eligible_frame))
    if eligible_frame.empty:
        summary = _blocked_summary(
            BLOCKED_NO_ELIGIBLE,
            "Latest feature table has no eligible Candidate input rows.",
            summary_path,
            model_type=model_type,
            target_date=target_date,
            input_feature_row_count=len(latest_frame),
            excluded_input_count=excluded_input_count,
        )
        _write_json(summary_path, summary)
        return summary

    try:
        scores = _predict_scores(model, _feature_matrix(eligible_frame, feature_columns))
        scored_rows = build_scored_candidates(
            eligible_frame.to_dict("records"),
            scores,
            model_version=model_version,
        )
    except Exception as exc:  # pragma: no cover - defensive path
        summary = _blocked_summary(BLOCKED_INFERENCE, f"Formal inference failed: {type(exc).__name__}", summary_path, model_type=model_type)
        _write_json(summary_path, summary)
        return summary

    scored_rows = sorted(scored_rows, key=lambda row: (-float(row["candidate_score"]), str(row["code"])))
    for index, row in enumerate(scored_rows, start=1):
        row["candidate_rank"] = index
    candidate_rows = scored_rows[: min(top_n, len(scored_rows))]
    scores_list = [float(row["candidate_score"]) for row in scored_rows]
    score_stats = _score_stats(scores_list)
    schema = validate_candidate_output(candidate_rows)
    rank_valid = _rank_is_sequential(candidate_rows)
    rank_unique = len({row["candidate_rank"] for row in candidate_rows}) == len(candidate_rows)
    reason_coverage = _coverage(bool(row.get("candidate_reason")) for row in candidate_rows)
    feature_snapshot_present = all(bool(row.get("feature_snapshot_id")) for row in candidate_rows)
    audit_flags_present = all(bool(row.get("audit_flags")) for row in candidate_rows)
    responsibility_boundary_status = "OK" if _responsibility_boundary_ok() else "ERROR"
    ranking_effective = not score_stats["all_same_score"] and rank_valid and rank_unique

    readiness_status = _resolve_readiness(
        schema_ok=schema,
        ranking_effective=ranking_effective,
        leakage_ok=leakage["status"] == "OK",
        responsibility_boundary_ok=responsibility_boundary_status == "OK",
    )

    inference_dir.mkdir(parents=True, exist_ok=True)
    candidates_dir.mkdir(parents=True, exist_ok=True)
    inference_path = inference_dir / f"phase4bg_formal_candidate_scores_{target_date}.json"
    candidates_path = candidates_dir / f"phase4bg_formal_candidate_top{top_n}_{target_date}.json"
    inference_payload = {
        "phase": PHASE,
        "created_at": _now(),
        "formal_inference": True,
        "target_date": target_date,
        "model_artifact_path": str(model_path),
        "model_manifest_path": str(model_manifest_path),
        "feature_table_path": str(feature_path),
        "feature_columns": feature_columns,
        "scored_count": len(scored_rows),
        "rows": scored_rows,
    }
    candidates_payload = {
        "phase": PHASE,
        "created_at": _now(),
        "formal_inference": True,
        "target_date": target_date,
        "top_n": top_n,
        "rows": candidate_rows,
    }
    _write_json(inference_path, inference_payload)
    _write_json(candidates_path, candidates_payload)
    _write_json(top50_json_path, candidates_payload)
    _write_csv(top50_csv_path, candidate_rows)

    summary = {
        "phase": PHASE,
        "status": "OK" if readiness_status == READY else "BLOCKED",
        "readiness_status": readiness_status,
        "inference_executed": True,
        "formal_inference": True,
        "model_type": model_type,
        "model_artifact_detected": model_path.is_file(),
        "model_manifest_detected": model_manifest_path.is_file(),
        "model_version": model_version,
        "target_date": target_date,
        "input_feature_row_count": int(len(latest_frame)),
        "eligible_input_count": int(len(eligible_frame)),
        "excluded_input_count": excluded_input_count,
        "scored_count": len(scored_rows),
        "candidate_count": len(candidate_rows),
        "top_n": top_n,
        **score_stats,
        "ranking_effective": ranking_effective,
        "feature_column_count": len(feature_columns),
        "future_column_used_as_feature": leakage["future_column_used_as_feature"],
        "label_column_used_as_feature": leakage["label_column_used_as_feature"],
        "leakage_audit_status": "OK" if leakage["status"] == "OK" else "ERROR",
        "candidate_rank_valid": rank_valid,
        "candidate_rank_unique": rank_unique,
        "candidate_reason_coverage": reason_coverage,
        "excluded_reason_available": excluded_input_count > 0,
        "feature_snapshot_id_present": feature_snapshot_present,
        "audit_flags_present": audit_flags_present,
        "inference_output_path": str(inference_path),
        "candidate_output_path": str(candidates_path),
        "top50_json_path": str(top50_json_path),
        "top50_csv_path": str(top50_csv_path),
        "production_model_promoted": False,
        "backtest_executed": False,
        "trading_executed": False,
        "paper_trading_executed": False,
        "broker_api_called": False,
        "order_executed": False,
        "responsibility_boundary_status": responsibility_boundary_status,
        "recommended_next_action": _recommended_next_action(readiness_status),
        "summary_path": str(summary_path),
    }
    _write_json(summary_path, summary)
    return summary


def build_scored_candidates(
    rows: list[dict[str, Any]],
    scores: np.ndarray,
    *,
    model_version: str,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row, score in zip(rows, scores):
        output.append(
            {
                "target_date": str(row.get("target_date")),
                "code": str(row.get("code")),
                "candidate_score": round(float(score), 8),
                "candidate_rank": None,
                "candidate_reason": _candidate_reason(row, score),
                "excluded_reason": "",
                "feature_snapshot_id": row.get("source_snapshot_id") or row.get("feature_version"),
                "model_version": model_version,
                "audit_flags": ["formal_inference", "not_buy_decision", "not_purchase_rank", "not_production_promotion"],
            }
        )
    return output


def audit_inference_features(feature_columns: list[str]) -> dict[str, Any]:
    stripped = [column.replace("feature__", "", 1) for column in feature_columns]
    future_columns = [column for column in stripped if is_forbidden_column(column)]
    label_columns = [
        column
        for column in feature_columns
        if column.startswith("label__") or "candidate_label" in column or "momentum_candidate_label" in column
    ]
    status = "OK" if all(column.startswith("feature__") for column in feature_columns) and not future_columns and not label_columns else "ERROR"
    return {
        "status": status,
        "future_column_used_as_feature": bool(future_columns),
        "future_columns": future_columns,
        "label_column_used_as_feature": bool(label_columns),
        "label_columns": label_columns,
    }


def validate_candidate_output(rows: list[dict[str, Any]]) -> bool:
    required = {
        "target_date",
        "code",
        "candidate_score",
        "candidate_rank",
        "candidate_reason",
        "excluded_reason",
        "feature_snapshot_id",
        "model_version",
        "audit_flags",
    }
    return bool(rows) and all(required.issubset(row.keys()) for row in rows)


def _candidate_reason(row: dict[str, Any], score: float) -> str:
    reasons: list[str] = []
    if float(score) >= 0.5:
        reasons.append("high_candidate_score")
    if _numeric_value(row.get("price_momentum_return_20d")) > 0:
        reasons.append("price_momentum_positive")
    if _numeric_value(row.get("price_momentum_return_60d")) > 0:
        reasons.append("long_momentum_positive")
    if _numeric_value(row.get("volume_momentum_ratio_5d")) > 1:
        reasons.append("volume_momentum_positive")
    if _numeric_value(row.get("liquidity_avg_volume_20d")) > 0:
        reasons.append("liquidity_available")
    return "|".join(reasons) if reasons else "formal_score_ranked"


def _feature_matrix(frame: Any, feature_columns: list[str]) -> np.ndarray:
    values = frame[[column.replace("feature__", "", 1) for column in feature_columns]].copy()
    for column in values.columns:
        if values[column].dtype == bool:
            values[column] = values[column].astype(float)
    return values.astype(float).to_numpy()


def _predict_scores(model: Any, x_input: np.ndarray) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(x_input)
        if proba.ndim == 2 and proba.shape[1] > 1:
            return np.asarray(proba[:, 1], dtype=float)
    if hasattr(model, "decision_function"):
        raw = np.asarray(model.decision_function(x_input), dtype=float)
        return 1.0 / (1.0 + np.exp(-raw))
    return np.asarray(model.predict(x_input), dtype=float)


def _read_feature_frame(path: Path) -> Any:
    if not path.is_file():
        return None
    import pandas as pd

    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    payload = _read_json_optional(path)
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    return pd.DataFrame(rows)


def _score_stats(scores: list[float]) -> dict[str, Any]:
    values = np.asarray(scores, dtype=float)
    unique_count = int(len(np.unique(np.round(values, 12))))
    return {
        "candidate_score_min": round(float(np.min(values)), 8) if len(values) else None,
        "candidate_score_max": round(float(np.max(values)), 8) if len(values) else None,
        "candidate_score_mean": round(float(np.mean(values)), 8) if len(values) else None,
        "candidate_score_std": round(float(np.std(values)), 8) if len(values) else None,
        "unique_candidate_score_count": unique_count,
        "all_same_score": unique_count <= 1,
    }


def _coverage(values: Any) -> float:
    items = list(values)
    return round(sum(1 for value in items if value) / len(items), 6) if items else 0.0


def _rank_is_sequential(rows: list[dict[str, Any]]) -> bool:
    return [row.get("candidate_rank") for row in rows] == list(range(1, len(rows) + 1))


def _responsibility_boundary_ok() -> bool:
    return True


def _resolve_readiness(
    *,
    schema_ok: bool,
    ranking_effective: bool,
    leakage_ok: bool,
    responsibility_boundary_ok: bool,
) -> str:
    if not leakage_ok:
        return BLOCKED_LEAKAGE
    if not schema_ok:
        return BLOCKED_SCHEMA
    if not ranking_effective:
        return BLOCKED_ALL_SAME
    if not responsibility_boundary_ok:
        return BLOCKED_BOUNDARY
    return READY


def _recommended_next_action(readiness_status: str) -> str:
    if readiness_status == READY:
        return "Phase4-BH Formal Candidate Quality Audit; do not backtest, trade, or promote yet."
    return "Fix the formal Candidate inference blocker, then rerun Phase4-BG."


def _safe_runtime_output_path(runtime_dir: Path, output_dir: Path, name: str) -> bool:
    try:
        output_dir.resolve().relative_to((runtime_dir.resolve() / "candidate_ai" / name).resolve())
        return True
    except ValueError:
        return False


def _blocked_summary(
    readiness_status: str,
    reason: str,
    summary_path: Path,
    *,
    model_type: str | None = None,
    target_date: str | None = None,
    input_feature_row_count: int = 0,
    excluded_input_count: int = 0,
    future_column_used_as_feature: bool = False,
    label_column_used_as_feature: bool = False,
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness_status,
        "block_reason": reason,
        "inference_executed": False,
        "formal_inference": True,
        "model_type": model_type,
        "model_artifact_detected": False,
        "model_manifest_detected": False,
        "model_version": None,
        "target_date": target_date,
        "input_feature_row_count": input_feature_row_count,
        "eligible_input_count": 0,
        "excluded_input_count": excluded_input_count,
        "scored_count": 0,
        "candidate_count": 0,
        "top_n": TOP_N,
        "candidate_score_min": None,
        "candidate_score_max": None,
        "candidate_score_mean": None,
        "candidate_score_std": None,
        "unique_candidate_score_count": 0,
        "all_same_score": True,
        "ranking_effective": False,
        "feature_column_count": 0,
        "future_column_used_as_feature": future_column_used_as_feature,
        "label_column_used_as_feature": label_column_used_as_feature,
        "leakage_audit_status": "ERROR" if future_column_used_as_feature or label_column_used_as_feature else "SKIPPED",
        "candidate_rank_valid": False,
        "candidate_rank_unique": False,
        "candidate_reason_coverage": 0.0,
        "excluded_reason_available": False,
        "feature_snapshot_id_present": False,
        "audit_flags_present": False,
        "production_model_promoted": False,
        "backtest_executed": False,
        "trading_executed": False,
        "paper_trading_executed": False,
        "broker_api_called": False,
        "order_executed": False,
        "responsibility_boundary_status": "OK",
        "recommended_next_action": _recommended_next_action(readiness_status),
        "summary_path": str(summary_path),
    }


def _numeric_value(value: Any) -> float:
    if value is None:
        return np.nan
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_pickle(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        payload = pickle.load(handle)
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "target_date",
        "candidate_rank",
        "code",
        "candidate_score",
        "candidate_reason",
        "excluded_reason",
        "feature_snapshot_id",
        "model_version",
        "audit_flags",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            csv_row = {key: row.get(key) for key in fieldnames}
            csv_row["audit_flags"] = "|".join(row.get("audit_flags") or [])
            writer.writerow(csv_row)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
