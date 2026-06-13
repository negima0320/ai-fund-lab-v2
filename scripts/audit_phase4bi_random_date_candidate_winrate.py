#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import pickle
import random
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

PHASE = "Phase4-BI"
OUTPUT_DIR = Path("reports/candidate_ai/final_check")
SUMMARY_PATH = OUTPUT_DIR / "phase4bi_random_date_candidate_winrate_summary.json"
BY_DATE_CSV_PATH = OUTPUT_DIR / "phase4bi_random_date_candidate_winrate_by_date.csv"
CANDIDATES_CSV_PATH = OUTPUT_DIR / "phase4bi_random_date_candidate_winrate_candidates.csv"
MANIFEST_PATH = OUTPUT_DIR / "phase4bi_random_date_candidate_winrate_manifest.json"
DOC_PATH = Path("docs/phase_reports/phase4bi_random_date_candidate_winrate_audit.md")
BF_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4bf_formal_lightgbm_training_summary.json")
BE_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4be_long_history_dataset_rebuild_summary.json")

READY = "PHASE4_FINAL_CHECK_COMPLETE"
BLOCKED_SELECTION_LEAKAGE = "BLOCKED_BY_SELECTION_LEAKAGE"
BLOCKED_MODEL = "BLOCKED_BY_MISSING_MODEL"
BLOCKED_FEATURE = "BLOCKED_BY_MISSING_FEATURE_TABLE"
BLOCKED_LABEL = "BLOCKED_BY_MISSING_LABEL_TABLE"
BLOCKED_DATES = "BLOCKED_BY_NO_ELIGIBLE_TARGET_DATES"
BLOCKED_AUDIT = "BLOCKED_BY_AUDIT_FAILURE"

DEFAULT_YEARS = (2025, 2024, 2023, 2022, 2021)
FIRST_TRAINABLE_TARGET_DATE = "2021-09-09"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase4-BI random-date Candidate win-rate final check.")
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--dates-per-year", type=int, default=1)
    parser.add_argument("--years", nargs="+", type=int, default=list(DEFAULT_YEARS))
    parser.add_argument("--top-n", type=int, default=50)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)
    summary = run_phase4bi_random_date_candidate_winrate(
        random_seed=args.random_seed,
        dates_per_year=args.dates_per_year,
        years=args.years,
        top_n=args.top_n,
        run_id=args.run_id,
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def run_phase4bi_random_date_candidate_winrate(
    *,
    random_seed: int = 42,
    dates_per_year: int = 1,
    years: list[int] | tuple[int, ...] = DEFAULT_YEARS,
    top_n: int = 50,
    run_id: str | None = None,
    bf_summary_path: Path = BF_SUMMARY_PATH,
    be_summary_path: Path = BE_SUMMARY_PATH,
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, Any]:
    try:
        bf_summary = _read_json(bf_summary_path)
        be_summary = _read_json(be_summary_path)
        model_path = Path(str(bf_summary.get("model_artifact_path") or ""))
        feature_table_path = Path(str(be_summary.get("feature_table_path") or ""))
        dataset_path = Path(str(be_summary.get("dataset_output_path") or ""))
        if not model_path.is_file():
            return _write_blocked(output_dir, BLOCKED_MODEL, "Phase4-BF model artifact is missing.")
        if not feature_table_path.is_file():
            return _write_blocked(output_dir, BLOCKED_FEATURE, "Long-history feature table is missing.")
        if not dataset_path.is_file():
            return _write_blocked(output_dir, BLOCKED_LABEL, "Long-history dataset with labels is missing.")

        model_payload = _read_pickle(model_path)
        model = model_payload.get("model")
        feature_columns = [str(column) for column in model_payload.get("feature_columns", [])]
        if model is None or not feature_columns:
            return _write_blocked(output_dir, BLOCKED_MODEL, "Model payload is missing model or feature columns.")

        feature_frame = _read_feature_table(feature_table_path, feature_columns)
        label_frame = _read_label_table(dataset_path)
        selection_leakage = selection_frame_has_leakage(feature_frame)
        if selection_leakage:
            return _write_blocked(output_dir, BLOCKED_SELECTION_LEAKAGE, "Selection frame contains label or future columns.")

        sampled_dates = sample_target_dates(
            feature_frame=feature_frame,
            label_frame=label_frame,
            years=years,
            dates_per_year=dates_per_year,
            random_seed=random_seed,
            top_n=top_n,
        )
        if len(sampled_dates) != len(years) * dates_per_year:
            return _write_blocked(output_dir, BLOCKED_DATES, "Could not sample all requested years and dates.")

        by_date_rows: list[dict[str, Any]] = []
        candidate_rows: list[dict[str, Any]] = []
        rng = random.Random(random_seed)
        for sampled in sampled_dates:
            target_date = sampled["target_date"]
            features_for_date = feature_frame[feature_frame["target_date"] == target_date].copy()
            labels_for_date = label_frame[label_frame["target_date"] == target_date].copy()
            selected = select_candidates_for_date(
                feature_frame_only=features_for_date,
                model=model,
                feature_columns=feature_columns,
                top_n=top_n,
            )
            evaluated = selected.merge(labels_for_date, on=["target_date", "code"], how="left", validate="one_to_one")
            market = features_for_date[
                features_for_date["universe_eligible"].astype(bool)
                & features_for_date["excluded_reason"].fillna("").astype(str).eq("")
            ][["target_date", "code"]].merge(labels_for_date, on=["target_date", "code"], how="inner")
            random_codes = rng.sample(list(market["code"].astype(str)), k=min(top_n, len(market)))
            random_baseline = market[market["code"].astype(str).isin(random_codes)]
            by_date_rows.append(
                {
                    "sampled_year": sampled["sampled_year"],
                    "target_date": target_date,
                    "top_n": top_n,
                    "candidate_count": int(len(evaluated)),
                    **_prefixed("candidate", winrate_metrics(evaluated)),
                    **_prefixed("market", winrate_metrics(market)),
                    **_prefixed("random", winrate_metrics(random_baseline)),
                }
            )
            for _, row in evaluated.iterrows():
                candidate_rows.append(
                    {
                        "sampled_year": sampled["sampled_year"],
                        "target_date": target_date,
                        "candidate_rank": int(row["candidate_rank"]),
                        "code": str(row["code"]),
                        "candidate_score": round(float(row["candidate_score"]), 8),
                        "future_return_5d": _round(row.get("label__future_return_5d")),
                        "future_return_10d": _round(row.get("label__future_return_10d")),
                        "future_return_20d": _round(row.get("label__future_return_20d")),
                        "future_max_return_20d": _round(row.get("label__future_max_return_20d")),
                        "downside_bad_20d": False if _is_nan(row.get("label__downside_bad_20d")) else bool(row.get("label__downside_bad_20d")),
                    }
                )

        totals = total_metrics(candidate_rows, by_date_rows)
        summary = {
            "phase": PHASE,
            "status": "OK",
            "readiness_status": READY,
            "final_check_executed": True,
            "random_seed": random_seed,
            "dates_per_year": dates_per_year,
            "years": list(years),
            "top_n": top_n,
            "run_id": run_id,
            "sampled_dates": sampled_dates,
            **totals,
            "future_data_used_for_selection": False,
            "label_data_used_for_selection": False,
            "leakage_audit_status": "OK",
            "backtest_executed": False,
            "trading_executed": False,
            "paper_trading_executed": False,
            "broker_api_called": False,
            "order_executed": False,
            "summary_path": str(output_dir / _name_with_run_id(SUMMARY_PATH.name, run_id)),
            "by_date_csv_path": str(output_dir / _name_with_run_id(BY_DATE_CSV_PATH.name, run_id)),
            "candidates_csv_path": str(output_dir / _name_with_run_id(CANDIDATES_CSV_PATH.name, run_id)),
            "manifest_path": str(output_dir / _name_with_run_id(MANIFEST_PATH.name, run_id)),
            "recommended_next_action": "Phase4 final check complete; proceed to Phase5 Opportunity AI preparation.",
        }
        paths = _output_paths(output_dir, run_id)
        _write_json(paths["summary"], summary)
        _write_csv(paths["by_date"], by_date_rows)
        _write_csv(paths["candidates"], candidate_rows)
        _write_json(
            paths["manifest"],
            {
                "phase": PHASE,
                "created_at": _now(),
                "random_seed": random_seed,
                "dates_per_year": dates_per_year,
                "years": list(years),
                "top_n": top_n,
                "run_id": run_id,
                "sampled_dates": sampled_dates,
                "future_data_used_for_selection": False,
                "label_data_used_for_selection": False,
                "feature_table_path": str(feature_table_path),
                "dataset_path": str(dataset_path),
                "model_path": str(model_path),
            },
        )
        _write_markdown(DOC_PATH, summary, by_date_rows)
        return summary
    except Exception as exc:  # pragma: no cover - defensive report path
        return _write_blocked(output_dir, BLOCKED_AUDIT, f"Final check audit failed: {type(exc).__name__}")


def sample_target_dates(
    *,
    feature_frame: Any,
    label_frame: Any,
    years: list[int] | tuple[int, ...],
    dates_per_year: int,
    random_seed: int,
    top_n: int,
) -> list[dict[str, Any]]:
    rng = random.Random(random_seed)
    eligible_counts = (
        feature_frame[
            feature_frame["universe_eligible"].astype(bool)
            & feature_frame["excluded_reason"].fillna("").astype(str).eq("")
        ]
        .groupby("target_date", sort=False)
        .size()
        .to_dict()
    )
    label_counts = label_frame.groupby("target_date", sort=False).size().to_dict()
    feature_dates = set(str(date) for date in eligible_counts)
    label_dates = set(str(date) for date in label_counts)
    sampled: list[dict[str, Any]] = []
    for year in years:
        candidates = sorted(date for date in feature_dates & label_dates if date.startswith(f"{year}-"))
        if year == 2021:
            candidates = [date for date in candidates if date >= FIRST_TRAINABLE_TARGET_DATE]
        candidates = [
            date
            for date in candidates
            if int(eligible_counts.get(date, 0)) >= top_n and int(label_counts.get(date, 0)) >= top_n
        ]
        if len(candidates) < dates_per_year:
            continue
        picked = rng.sample(candidates, dates_per_year)
        sampled.extend({"sampled_year": year, "target_date": date} for date in sorted(picked))
    return sampled


def select_candidates_for_date(*, feature_frame_only: Any, model: Any, feature_columns: list[str], top_n: int) -> Any:
    if selection_frame_has_leakage(feature_frame_only):
        raise ValueError("selection frame contains label/future columns")
    stripped_feature_columns = [column.replace("feature__", "", 1) for column in feature_columns]
    eligible = feature_frame_only[
        feature_frame_only["universe_eligible"].astype(bool)
        & feature_frame_only["excluded_reason"].fillna("").astype(str).eq("")
    ].copy()
    matrix = eligible[stripped_feature_columns].astype(float).to_numpy()
    scores = _predict_scores(model, matrix)
    eligible["candidate_score"] = scores
    selected = eligible.sort_values(["candidate_score", "code"], ascending=[False, True]).head(top_n).copy()
    selected["candidate_rank"] = range(1, len(selected) + 1)
    return selected[["target_date", "code", "candidate_score", "candidate_rank"]]


def selection_frame_has_leakage(frame: Any) -> bool:
    columns = [str(column).lower() for column in getattr(frame, "columns", [])]
    forbidden_prefixes = ("label__", "future_return_", "future_max_return_", "future_max_drawdown_", "top_decile_", "downside_bad_")
    forbidden_terms = ("momentum_candidate_label", "backtest", "trade", "portfolio", "cash", "order", "execution", "pnl")
    return any(column.startswith(forbidden_prefixes) or any(term in column for term in forbidden_terms) for column in columns)


def winrate_metrics(frame: Any) -> dict[str, Any]:
    return {
        "win_rate_5d": _mean_bool(frame["label__future_return_5d"] > 0),
        "win_rate_10d": _mean_bool(frame["label__future_return_10d"] > 0),
        "win_rate_20d": _mean_bool(frame["label__future_return_20d"] > 0),
        "avg_return_5d": _mean_float(frame["label__future_return_5d"]),
        "avg_return_10d": _mean_float(frame["label__future_return_10d"]),
        "avg_return_20d": _mean_float(frame["label__future_return_20d"]),
        "avg_future_max_return_20d": _mean_float(frame["label__future_max_return_20d"]),
        "downside_bad_rate_20d": _mean_bool(frame["label__downside_bad_20d"].astype(bool)),
    }


def total_metrics(candidate_rows: list[dict[str, Any]], by_date_rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_candidate_count = len(candidate_rows)
    metrics = {
        "total_sampled_date_count": len(by_date_rows),
        "total_candidate_count": total_candidate_count,
        "total_win_rate_5d": _row_rate(candidate_rows, "future_return_5d"),
        "total_win_rate_10d": _row_rate(candidate_rows, "future_return_10d"),
        "total_win_rate_20d": _row_rate(candidate_rows, "future_return_20d"),
        "total_avg_return_5d": _row_mean(candidate_rows, "future_return_5d"),
        "total_avg_return_10d": _row_mean(candidate_rows, "future_return_10d"),
        "total_avg_return_20d": _row_mean(candidate_rows, "future_return_20d"),
        "total_avg_future_max_return_20d": _row_mean(candidate_rows, "future_max_return_20d"),
        "total_downside_bad_rate_20d": _mean_bool([row["downside_bad_20d"] for row in candidate_rows]),
    }
    for prefix in ("market", "random"):
        for horizon in ("5d", "10d", "20d"):
            metrics[f"total_{prefix}_win_rate_{horizon}"] = _mean_float(
                [row[f"{prefix}_win_rate_{horizon}"] for row in by_date_rows]
            )
    for horizon in ("5d", "10d", "20d"):
        metrics[f"candidate_vs_market_win_rate_diff_{horizon}"] = _diff(
            metrics[f"total_win_rate_{horizon}"], metrics[f"total_market_win_rate_{horizon}"]
        )
        metrics[f"candidate_vs_random_win_rate_diff_{horizon}"] = _diff(
            metrics[f"total_win_rate_{horizon}"], metrics[f"total_random_win_rate_{horizon}"]
        )
    return metrics


def _read_feature_table(path: Path, feature_columns: list[str]) -> Any:
    import pandas as pd

    columns = [
        "target_date",
        "code",
        "universe_eligible",
        "excluded_reason",
        *[column.replace("feature__", "", 1) for column in feature_columns],
    ]
    return pd.read_parquet(path, columns=columns).assign(target_date=lambda df: df["target_date"].astype(str), code=lambda df: df["code"].astype(str))


def _read_label_table(path: Path) -> Any:
    import pandas as pd

    columns = [
        "target_date",
        "code",
        "label__future_return_5d",
        "label__future_return_10d",
        "label__future_return_20d",
        "label__future_max_return_20d",
        "label__downside_bad_20d",
    ]
    return pd.read_parquet(path, columns=columns).assign(target_date=lambda df: df["target_date"].astype(str), code=lambda df: df["code"].astype(str))


def _predict_scores(model: Any, matrix: np.ndarray) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(matrix)
        if proba.ndim == 2 and proba.shape[1] > 1:
            return np.asarray(proba[:, 1], dtype=float)
    if hasattr(model, "decision_function"):
        raw = np.asarray(model.decision_function(matrix), dtype=float)
        return 1.0 / (1.0 + np.exp(-raw))
    return np.asarray(model.predict(matrix), dtype=float)


def _prefixed(prefix: str, metrics: dict[str, Any]) -> dict[str, Any]:
    return {f"{prefix}_{key}": value for key, value in metrics.items()}


def _mean_bool(values: Any) -> float:
    items = [value for value in list(values) if not _is_nan(value)]
    return round(sum(bool(value) for value in items) / len(items), 6) if items else 0.0


def _mean_float(values: Any) -> float:
    items = [float(value) for value in list(values) if not _is_nan(value)]
    return round(float(np.mean(items)), 6) if items else 0.0


def _row_rate(rows: list[dict[str, Any]], key: str) -> float:
    return _mean_bool(row[key] > 0 for row in rows)


def _row_mean(rows: list[dict[str, Any]], key: str) -> float:
    return _mean_float(row[key] for row in rows)


def _round(value: Any) -> float:
    return round(float(value), 6)


def _diff(left: float, right: float) -> float:
    return round(float(left - right), 6)


def _is_nan(value: Any) -> bool:
    try:
        return bool(np.isnan(value))
    except TypeError:
        return False


def _read_json(path: Path) -> dict[str, Any]:
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
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(path: Path, summary: dict[str, Any], by_date_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Phase4-BI Random Date Candidate Win-rate Audit",
        "",
        f"- status: `{summary['status']}`",
        f"- readiness_status: `{summary['readiness_status']}`",
        f"- random_seed: `{summary['random_seed']}`",
        f"- sampled_dates: `{summary['sampled_dates']}`",
        "",
        "## Total",
        "",
        f"- total_win_rate_5d: `{summary['total_win_rate_5d']}`",
        f"- total_win_rate_10d: `{summary['total_win_rate_10d']}`",
        f"- total_win_rate_20d: `{summary['total_win_rate_20d']}`",
        f"- candidate_vs_market_win_rate_diff_20d: `{summary['candidate_vs_market_win_rate_diff_20d']}`",
        f"- candidate_vs_random_win_rate_diff_20d: `{summary['candidate_vs_random_win_rate_diff_20d']}`",
        "",
        "## By Date",
        "",
    ]
    for row in by_date_rows:
        lines.append(
            f"- {row['target_date']}: win5/10/20 = `{row['candidate_win_rate_5d']}` / `{row['candidate_win_rate_10d']}` / `{row['candidate_win_rate_20d']}`"
        )
    lines.extend(
        [
            "",
            "## Leakage Guard",
            "",
            "- Candidate selection used feature table columns only.",
            "- Label/future columns were used only after candidate selection for evaluation.",
            "- This is not backtest, trading, Paper Trading, broker API, order execution, or portfolio simulation.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_blocked(output_dir: Path, readiness: str, reason: str) -> dict[str, Any]:
    summary = {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness,
        "final_check_executed": False,
        "block_reason": reason,
        "future_data_used_for_selection": False,
        "label_data_used_for_selection": False,
        "leakage_audit_status": "SKIPPED",
        "backtest_executed": False,
        "trading_executed": False,
        "paper_trading_executed": False,
        "broker_api_called": False,
        "order_executed": False,
        "recommended_next_action": "Fix the Phase4-BI final check blocker and rerun.",
    }
    _write_json(output_dir / SUMMARY_PATH.name, summary)
    return summary


def _output_paths(output_dir: Path, run_id: str | None) -> dict[str, Path]:
    return {
        "summary": output_dir / _name_with_run_id(SUMMARY_PATH.name, run_id),
        "by_date": output_dir / _name_with_run_id(BY_DATE_CSV_PATH.name, run_id),
        "candidates": output_dir / _name_with_run_id(CANDIDATES_CSV_PATH.name, run_id),
        "manifest": output_dir / _name_with_run_id(MANIFEST_PATH.name, run_id),
    }


def _name_with_run_id(name: str, run_id: str | None) -> str:
    if not run_id:
        return name
    stem, suffix = name.rsplit(".", 1)
    return f"{stem}_{run_id}.{suffix}"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
