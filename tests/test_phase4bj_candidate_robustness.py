from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from scripts.audit_phase4bj_candidate_robustness import (
    READY,
    READY_WEAK,
    run_phase4bj_candidate_robustness,
    sample_target_dates,
    score_candidates_for_date,
    selection_frame_has_leakage,
)


def test_phase4bj_runs_robustness(tmp_path: Path) -> None:
    bf_summary, be_summary, output_dir = _prepare_fixture(tmp_path)

    summary = run_phase4bj_candidate_robustness(
        random_seed=42,
        dates_per_year=2,
        years=[2021, 2022],
        top_n_list=[10, 20, 30, 50],
        bf_summary_path=bf_summary,
        be_summary_path=be_summary,
        output_dir=output_dir,
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] in {READY, READY_WEAK}
    assert summary["robustness_test_executed"] is True
    assert summary["total_sampled_date_count"] == 4
    assert summary["total_candidate_count_top50"] == 200
    assert summary["future_data_used_for_selection"] is False
    assert summary["label_data_used_for_selection"] is False
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False
    assert Path(summary["summary_path"]).is_file()


def test_phase4bj_same_seed_same_dates(tmp_path: Path) -> None:
    _, be_summary, _ = _prepare_fixture(tmp_path)
    be = json.loads(be_summary.read_text(encoding="utf-8"))
    feature_frame = pd.read_parquet(be["feature_table_path"])
    label_frame = pd.read_parquet(be["dataset_output_path"])

    first = sample_target_dates(feature_frame=feature_frame, label_frame=label_frame, years=[2021, 2022], dates_per_year=2, random_seed=7, top_n=50)
    second = sample_target_dates(feature_frame=feature_frame, label_frame=label_frame, years=[2021, 2022], dates_per_year=2, random_seed=7, top_n=50)

    assert first == second


def test_phase4bj_rejects_selection_leakage() -> None:
    frame = pd.DataFrame({"target_date": ["2025-01-01"], "label__future_return_20d": [0.1]})

    assert selection_frame_has_leakage(frame) is True


def test_phase4bj_topn_nested(tmp_path: Path) -> None:
    bf_summary, be_summary, _ = _prepare_fixture(tmp_path)
    bf = json.loads(bf_summary.read_text(encoding="utf-8"))
    be = json.loads(be_summary.read_text(encoding="utf-8"))
    model_payload = pickle.load(open(bf["model_artifact_path"], "rb"))
    feature_frame = pd.read_parquet(be["feature_table_path"])

    scored = score_candidates_for_date(
        feature_frame_only=feature_frame[feature_frame["target_date"] == "2022-06-01"],
        model=model_payload["model"],
        feature_columns=model_payload["feature_columns"],
    )

    top10 = list(scored.head(10)["code"])
    top20 = list(scored.head(20)["code"])
    top50 = list(scored.head(50)["code"])
    assert top10 == top20[:10]
    assert top20 == top50[:20]


def test_phase4bj_outputs_all_csvs(tmp_path: Path) -> None:
    bf_summary, be_summary, output_dir = _prepare_fixture(tmp_path)
    summary = run_phase4bj_candidate_robustness(
        random_seed=11,
        dates_per_year=1,
        years=[2021, 2022],
        top_n_list=[10, 50],
        bf_summary_path=bf_summary,
        be_summary_path=be_summary,
        output_dir=output_dir,
    )

    for filename in (
        "phase4bj_candidate_robustness_by_year.csv",
        "phase4bj_candidate_robustness_by_date.csv",
        "phase4bj_candidate_robustness_by_topn.csv",
        "phase4bj_candidate_robustness_candidates.csv",
        "phase4bj_candidate_robustness_score_decile.csv",
        "phase4bj_candidate_robustness_market_regime.csv",
        "phase4bj_candidate_robustness_sector.csv",
        "phase4bj_candidate_robustness_manifest.json",
    ):
        assert (output_dir / filename).is_file()
    assert summary["market_regime_analysis_status"] == "SKIPPED"
    assert summary["sector_analysis_status"] == "SKIPPED"


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
    for year in (2021, 2022):
        for day in range(1, 13):
            target_date = f"{year}-09-{day + 8:02d}" if year == 2021 else f"{year}-06-{day:02d}"
            for code_index in range(60):
                signal = code_index >= 30
                rows.append(
                    {
                        "target_date": target_date,
                        "code": f"{year}{day:02d}{code_index:02d}",
                        "universe_eligible": True,
                        "excluded_reason": "",
                        "signal": code_index / 60,
                        "noise": (code_index % 5) / 5,
                        "feature__signal": code_index / 60,
                        "feature__noise": (code_index % 5) / 5,
                        "label__future_return_5d": 0.02 if signal else -0.01,
                        "label__future_return_10d": 0.03 if signal else -0.01,
                        "label__future_return_20d": 0.04 if signal else -0.02,
                        "label__future_max_return_20d": 0.1 if signal else 0.01,
                        "label__future_max_drawdown_20d": -0.03 if signal else -0.08,
                        "label__top_decile_20d": code_index >= 54,
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
            "label__future_max_drawdown_20d",
            "label__top_decile_20d",
            "label__downside_bad_20d",
        ]
    ].to_parquet(dataset_path, index=False)
    model = LogisticRegression(random_state=42).fit(
        all_rows[["feature__signal", "feature__noise"]].to_numpy(),
        (all_rows["label__future_return_20d"] > 0).astype(int).to_numpy(),
    )
    model_path = model_dir / "model.pkl"
    with model_path.open("wb") as handle:
        pickle.dump({"model": model, "feature_columns": feature_columns}, handle)
    bf_summary = tmp_path / "bf.json"
    be_summary = tmp_path / "be.json"
    bf_summary.write_text(json.dumps({"model_artifact_path": str(model_path)}), encoding="utf-8")
    be_summary.write_text(json.dumps({"feature_table_path": str(feature_path), "dataset_output_path": str(dataset_path)}), encoding="utf-8")
    return bf_summary, be_summary, tmp_path / "reports"
