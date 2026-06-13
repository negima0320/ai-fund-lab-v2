from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.audit_phase4bk_winner_loser_case_study import (
    READY,
    candidate_selection_frame_has_leakage,
    run_phase4bk_winner_loser_case_study,
)


def test_phase4bk_runs_case_study(tmp_path: Path) -> None:
    candidate_path, be_summary_path, bf_summary_path, output_dir = prepare_fixture(tmp_path)

    summary = run_phase4bk_winner_loser_case_study(
        candidate_path=candidate_path,
        be_summary_path=be_summary_path,
        bf_summary_path=bf_summary_path,
        output_dir=output_dir,
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["best_case_count"] == 50
    assert summary["worst_case_count"] == 50
    assert summary["future_data_used_for_selection"] is False
    assert summary["label_data_used_for_selection"] is False
    assert summary["future_data_used_for_case_analysis"] is True
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False
    assert (output_dir / "phase4bk_winner_loser_cases_summary.json").is_file()
    assert (output_dir / "phase4bk_winner_loser_best.csv").is_file()
    assert (output_dir / "phase4bk_winner_loser_worst.csv").is_file()
    assert (output_dir / "phase4bk_winner_loser_feature_compare.csv").is_file()


def test_phase4bk_best_and_worst_are_yearly(tmp_path: Path) -> None:
    candidate_path, be_summary_path, bf_summary_path, output_dir = prepare_fixture(tmp_path)

    run_phase4bk_winner_loser_case_study(
        candidate_path=candidate_path,
        be_summary_path=be_summary_path,
        bf_summary_path=bf_summary_path,
        output_dir=output_dir,
    )

    best = pd.read_csv(output_dir / "phase4bk_winner_loser_best.csv")
    worst = pd.read_csv(output_dir / "phase4bk_winner_loser_worst.csv")
    assert best.groupby("sampled_year").size().to_dict() == {2021: 10, 2022: 10, 2023: 10, 2024: 10, 2025: 10}
    assert worst.groupby("sampled_year").size().to_dict() == {2021: 10, 2022: 10, 2023: 10, 2024: 10, 2025: 10}
    assert best["future_max_return_20d"].mean() > worst["future_max_return_20d"].mean()
    assert best["future_return_20d"].mean() > worst["future_return_20d"].mean()


def test_phase4bk_feature_compare_has_required_features(tmp_path: Path) -> None:
    candidate_path, be_summary_path, bf_summary_path, output_dir = prepare_fixture(tmp_path)

    run_phase4bk_winner_loser_case_study(
        candidate_path=candidate_path,
        be_summary_path=be_summary_path,
        bf_summary_path=bf_summary_path,
        output_dir=output_dir,
    )

    compare = pd.read_csv(output_dir / "phase4bk_winner_loser_feature_compare.csv")
    assert "price_momentum_return_20d" in set(compare["feature_name"])
    assert "liquidity_avg_volume_20d" in set(compare["feature_name"])
    assert "candidate_score" in set(compare["feature_name"])


def test_phase4bk_selection_leakage_checks_only_selection_columns() -> None:
    frame = pd.DataFrame(
        {
            "sampled_year": [2025],
            "target_date": ["2025-01-01"],
            "top_n": [50],
            "candidate_rank": [1],
            "code": ["1234"],
            "candidate_score": [0.7],
            "future_return_20d": [0.2],
        }
    )

    assert candidate_selection_frame_has_leakage(frame) is False


def prepare_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    output_dir = tmp_path / "reports"
    feature_path = tmp_path / "features.parquet"
    candidate_path = tmp_path / "candidates.csv"
    rows = []
    feature_rows = []
    for year in (2021, 2022, 2023, 2024, 2025):
        target_date = f"{year}-09-15"
        for rank in range(1, 61):
            code = f"{year}{rank:04d}"
            score = 1.0 - rank / 100
            return20 = (61 - rank) / 100 if rank <= 30 else -(rank - 30) / 100
            drawdown = -0.02 if rank <= 30 else -0.2 - rank / 1000
            rows.append(
                {
                    "sampled_year": year,
                    "target_date": target_date,
                    "top_n": 50,
                    "candidate_rank": rank,
                    "code": code,
                    "candidate_score": score,
                    "future_return_5d": return20 / 4,
                    "future_return_10d": return20 / 2,
                    "future_return_20d": return20,
                    "future_max_return_20d": return20 + 0.1,
                    "future_max_drawdown_20d": drawdown,
                    "top_decile_20d": rank <= 6,
                    "downside_bad_20d": rank > 40,
                }
            )
            feature_rows.append(
                {
                    "target_date": target_date,
                    "code": code,
                    "liquidity_avg_volume_20d": 1000 + rank,
                    "price_momentum_return_5d": 0.1 - rank / 1000,
                    "price_momentum_return_20d": 0.2 - rank / 1000,
                    "price_momentum_return_60d": 0.3 - rank / 1000,
                    "volatility_return_std_20d": rank / 1000,
                    "trend_close_over_ma_20d": 1.1 - rank / 1000,
                    "trend_ma_5_20_ratio": 1.05 - rank / 1000,
                    "trend_ma_20_60_ratio": 1.04 - rank / 1000,
                    "volume_momentum_ratio_5d": 2.0 - rank / 1000,
                    "volume_momentum_ratio_1d_20d": 1.5 - rank / 1000,
                }
            )
    pd.DataFrame(rows).to_csv(candidate_path, index=False)
    pd.DataFrame(feature_rows).to_parquet(feature_path, index=False)
    be_summary_path = tmp_path / "be_summary.json"
    bf_summary_path = tmp_path / "bf_summary.json"
    be_summary_path.write_text(json.dumps({"feature_table_path": str(feature_path)}), encoding="utf-8")
    bf_summary_path.write_text(json.dumps({"model_manifest_path": str(tmp_path / "model_manifest.json")}), encoding="utf-8")
    return candidate_path, be_summary_path, bf_summary_path, output_dir
