from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from scripts.audit_phase4bi_random_date_candidate_winrate import (
    READY,
    run_phase4bi_random_date_candidate_winrate,
    sample_target_dates,
    select_candidates_for_date,
    selection_frame_has_leakage,
)


def test_phase4bi_runs_random_date_winrate_audit(tmp_path: Path) -> None:
    bf_summary, be_summary, output_dir = _prepare_fixture(tmp_path)

    summary = run_phase4bi_random_date_candidate_winrate(
        random_seed=42,
        dates_per_year=1,
        years=[2025, 2024, 2023, 2022, 2021],
        top_n=5,
        bf_summary_path=bf_summary,
        be_summary_path=be_summary,
        output_dir=output_dir,
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["total_sampled_date_count"] == 5
    assert summary["total_candidate_count"] == 25
    assert summary["future_data_used_for_selection"] is False
    assert summary["label_data_used_for_selection"] is False
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False
    assert summary["order_executed"] is False
    assert Path(summary["by_date_csv_path"]).is_file()
    assert Path(summary["candidates_csv_path"]).is_file()
    assert Path(summary["manifest_path"]).is_file()


def test_phase4bi_same_seed_samples_same_dates(tmp_path: Path) -> None:
    _, be_summary, _ = _prepare_fixture(tmp_path)
    be = json.loads(be_summary.read_text(encoding="utf-8"))
    feature_frame = pd.read_parquet(be["feature_table_path"])
    label_frame = pd.read_parquet(be["dataset_output_path"])

    first = sample_target_dates(feature_frame=feature_frame, label_frame=label_frame, years=[2025, 2024], dates_per_year=1, random_seed=7, top_n=5)
    second = sample_target_dates(feature_frame=feature_frame, label_frame=label_frame, years=[2025, 2024], dates_per_year=1, random_seed=7, top_n=5)

    assert first == second


def test_phase4bi_selection_rejects_label_or_future_columns(tmp_path: Path) -> None:
    frame = pd.DataFrame({"target_date": ["2025-01-01"], "future_return_20d": [0.1]})

    assert selection_frame_has_leakage(frame) is True


def test_phase4bi_selection_uses_feature_columns_only(tmp_path: Path) -> None:
    bf_summary, be_summary, _ = _prepare_fixture(tmp_path)
    bf = json.loads(bf_summary.read_text(encoding="utf-8"))
    be = json.loads(be_summary.read_text(encoding="utf-8"))
    model_payload = pickle.load(open(bf["model_artifact_path"], "rb"))
    feature_frame = pd.read_parquet(be["feature_table_path"])
    target_date = "2025-06-02"

    selected = select_candidates_for_date(
        feature_frame_only=feature_frame[feature_frame["target_date"] == target_date],
        model=model_payload["model"],
        feature_columns=model_payload["feature_columns"],
        top_n=5,
    )

    assert len(selected) == 5
    assert "label__future_return_20d" not in selected.columns
    assert list(selected["candidate_rank"]) == [1, 2, 3, 4, 5]


def test_phase4bi_output_reproducible(tmp_path: Path) -> None:
    bf_summary, be_summary, output_dir = _prepare_fixture(tmp_path)

    first = run_phase4bi_random_date_candidate_winrate(
        random_seed=99,
        dates_per_year=1,
        years=[2025, 2024],
        top_n=5,
        bf_summary_path=bf_summary,
        be_summary_path=be_summary,
        output_dir=output_dir,
        run_id="first",
    )
    second = run_phase4bi_random_date_candidate_winrate(
        random_seed=99,
        dates_per_year=1,
        years=[2025, 2024],
        top_n=5,
        bf_summary_path=bf_summary,
        be_summary_path=be_summary,
        output_dir=output_dir,
        run_id="second",
    )

    assert first["sampled_dates"] == second["sampled_dates"]


def _prepare_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    runtime = tmp_path / "runtime"
    model_dir = runtime / "candidate_ai" / "models"
    feature_dir = runtime / "candidate_ai" / "features"
    dataset_dir = runtime / "candidate_ai" / "datasets"
    model_dir.mkdir(parents=True)
    feature_dir.mkdir(parents=True)
    dataset_dir.mkdir(parents=True)
    feature_columns = ["feature__signal", "feature__noise"]
    rows = []
    for year in (2021, 2022, 2023, 2024, 2025):
        for day in range(1, 4):
            target_date = f"{year}-09-{day + 8:02d}" if year == 2021 else f"{year}-06-0{day}"
            for code_index in range(12):
                signal = code_index >= 6
                rows.append(
                    {
                        "target_date": target_date,
                        "code": f"{year}{code_index:02d}",
                        "universe_eligible": True,
                        "excluded_reason": "",
                        "signal": code_index / 12,
                        "noise": (code_index % 3) / 3,
                        "feature__signal": code_index / 12,
                        "feature__noise": (code_index % 3) / 3,
                        "label__future_return_5d": 0.02 if signal else -0.01,
                        "label__future_return_10d": 0.03 if signal else -0.01,
                        "label__future_return_20d": 0.04 if signal else -0.02,
                        "label__future_max_return_20d": 0.1 if signal else 0.01,
                        "label__downside_bad_20d": not signal,
                    }
                )
    all_rows = pd.DataFrame(rows)
    feature_path = feature_dir / "features.parquet"
    dataset_path = dataset_dir / "dataset.parquet"
    all_rows[["target_date", "code", "universe_eligible", "excluded_reason", "signal", "noise"]].to_parquet(feature_path, index=False)
    all_rows[
        [
            "target_date",
            "code",
            "feature__signal",
            "feature__noise",
            "label__future_return_5d",
            "label__future_return_10d",
            "label__future_return_20d",
            "label__future_max_return_20d",
            "label__downside_bad_20d",
        ]
    ].to_parquet(dataset_path, index=False)
    model = LogisticRegression(random_state=42).fit(all_rows[["feature__signal", "feature__noise"]].to_numpy(), (all_rows["label__future_return_20d"] > 0).astype(int).to_numpy())
    model_path = model_dir / "model.pkl"
    with model_path.open("wb") as handle:
        pickle.dump({"model": model, "feature_columns": feature_columns}, handle)
    bf_summary = tmp_path / "bf.json"
    be_summary = tmp_path / "be.json"
    bf_summary.write_text(json.dumps({"model_artifact_path": str(model_path)}), encoding="utf-8")
    be_summary.write_text(json.dumps({"feature_table_path": str(feature_path), "dataset_output_path": str(dataset_path)}), encoding="utf-8")
    return bf_summary, be_summary, tmp_path / "reports"
