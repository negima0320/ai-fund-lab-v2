from __future__ import annotations

import json
import pickle
from pathlib import Path

import pandas as pd
from sklearn.linear_model import LogisticRegression

from scripts.audit_phase4bl_momentum_capture import (
    READY,
    load_bj_sampled_dates,
    run_phase4bl_momentum_capture,
)


def test_phase4bl_runs_momentum_capture(tmp_path: Path) -> None:
    bf_summary, be_summary, bj_summary, output_dir = prepare_fixture(tmp_path)

    summary = run_phase4bl_momentum_capture(
        random_seed=42,
        dates_per_year=2,
        years=[2021, 2022],
        candidate_topn_list=[10, 20, 50],
        future_topk_list=[10, 20, 50],
        bf_summary_path=bf_summary,
        be_summary_path=be_summary,
        bj_summary_path=bj_summary,
        output_dir=output_dir,
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["momentum_capture_audit_executed"] is True
    assert summary["total_sampled_date_count"] == 4
    assert summary["total_candidate_top50_future_return_top50_capture_count"] > 0
    assert summary["future_data_used_for_selection"] is False
    assert summary["label_data_used_for_selection"] is False
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False
    assert (output_dir / "phase4bl_momentum_capture_summary.json").is_file()


def test_phase4bl_reuses_bj_sampled_dates(tmp_path: Path) -> None:
    _, _, bj_summary, _ = prepare_fixture(tmp_path)

    sampled = load_bj_sampled_dates(bj_summary)

    assert sampled == [
        {"sampled_year": 2021, "target_date": "2021-09-10"},
        {"sampled_year": 2021, "target_date": "2021-09-11"},
        {"sampled_year": 2022, "target_date": "2022-06-01"},
        {"sampled_year": 2022, "target_date": "2022-06-02"},
    ]


def test_phase4bl_outputs_intersections_and_group_summaries(tmp_path: Path) -> None:
    bf_summary, be_summary, bj_summary, output_dir = prepare_fixture(tmp_path)

    run_phase4bl_momentum_capture(
        random_seed=7,
        dates_per_year=2,
        years=[2021, 2022],
        candidate_topn_list=[10, 50],
        future_topk_list=[10, 50],
        bf_summary_path=bf_summary,
        be_summary_path=be_summary,
        bj_summary_path=bj_summary,
        output_dir=output_dir,
    )

    for filename in (
        "phase4bl_momentum_capture_by_date.csv",
        "phase4bl_momentum_capture_by_year.csv",
        "phase4bl_momentum_capture_by_topn_topk.csv",
        "phase4bl_momentum_capture_intersections.csv",
        "phase4bl_momentum_capture_manifest.json",
    ):
        assert (output_dir / filename).is_file()
    intersections = pd.read_csv(output_dir / "phase4bl_momentum_capture_intersections.csv")
    assert {"candidate_rank", "future_rank", "future_topk_basis"}.issubset(intersections.columns)


def test_phase4bl_topn_topk_capture_math(tmp_path: Path) -> None:
    bf_summary, be_summary, bj_summary, output_dir = prepare_fixture(tmp_path)

    run_phase4bl_momentum_capture(
        random_seed=3,
        dates_per_year=2,
        years=[2021, 2022],
        candidate_topn_list=[10],
        future_topk_list=[10],
        bf_summary_path=bf_summary,
        be_summary_path=be_summary,
        bj_summary_path=bj_summary,
        output_dir=output_dir,
    )

    by_date = pd.read_csv(output_dir / "phase4bl_momentum_capture_by_date.csv")
    row = by_date[(by_date["future_topk_basis"] == "future_return_20d") & (by_date["candidate_top_n"] == 10)].iloc[0]
    assert row["capture_count"] == 10
    assert row["capture_rate"] == 1.0
    assert row["precision_to_future_topk"] == 1.0


def prepare_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    runtime = tmp_path / "runtime"
    model_dir = runtime / "candidate_ai" / "models"
    feature_dir = runtime / "candidate_ai" / "features"
    dataset_dir = runtime / "candidate_ai" / "datasets"
    model_dir.mkdir(parents=True)
    feature_dir.mkdir(parents=True)
    dataset_dir.mkdir(parents=True)
    feature_columns = ["feature__signal", "feature__noise"]
    dates = [
        (2021, "2021-09-10"),
        (2021, "2021-09-11"),
        (2022, "2022-06-01"),
        (2022, "2022-06-02"),
    ]
    feature_rows = []
    dataset_rows = []
    for year, target_date in dates:
        for idx in range(80):
            code = f"{year}{target_date[-2:]}{idx:03d}"
            signal = idx / 79
            feature_rows.append(
                {
                    "target_date": target_date,
                    "code": code,
                    "universe_eligible": True,
                    "excluded_reason": "",
                    "signal": signal,
                    "noise": (idx % 3) / 3,
                }
            )
            dataset_rows.append(
                {
                    "target_date": target_date,
                    "code": code,
                    "feature__signal": signal,
                    "feature__noise": (idx % 3) / 3,
                    "label__future_return_5d": signal,
                    "label__future_return_10d": signal,
                    "label__future_return_20d": signal,
                    "label__future_max_return_20d": signal,
                    "label__future_max_drawdown_20d": -0.01,
                    "label__top_decile_20d": idx >= 72,
                    "label__downside_bad_20d": False,
                }
            )
    feature_frame = pd.DataFrame(feature_rows)
    dataset_frame = pd.DataFrame(dataset_rows)
    feature_path = feature_dir / "features.parquet"
    dataset_path = dataset_dir / "dataset.parquet"
    feature_frame.to_parquet(feature_path, index=False)
    dataset_frame.to_parquet(dataset_path, index=False)
    model = LogisticRegression(random_state=42).fit(
        dataset_frame[["feature__signal", "feature__noise"]].to_numpy(),
        (dataset_frame["label__future_return_20d"] > 0.5).astype(int).to_numpy(),
    )
    model_path = model_dir / "model.pkl"
    with model_path.open("wb") as handle:
        pickle.dump({"model": model, "feature_columns": feature_columns}, handle)
    bf_summary = tmp_path / "bf_summary.json"
    be_summary = tmp_path / "be_summary.json"
    bj_summary = tmp_path / "bj_summary.json"
    bf_summary.write_text(json.dumps({"model_artifact_path": str(model_path)}), encoding="utf-8")
    be_summary.write_text(
        json.dumps({"feature_table_path": str(feature_path), "dataset_output_path": str(dataset_path)}),
        encoding="utf-8",
    )
    bj_summary.write_text(
        json.dumps(
            {
                "sampled_dates": [
                    {"sampled_year": 2021, "target_date": "2021-09-10"},
                    {"sampled_year": 2021, "target_date": "2021-09-11"},
                    {"sampled_year": 2022, "target_date": "2022-06-01"},
                    {"sampled_year": 2022, "target_date": "2022-06-02"},
                ]
            }
        ),
        encoding="utf-8",
    )
    return bf_summary, be_summary, bj_summary, tmp_path / "reports"
