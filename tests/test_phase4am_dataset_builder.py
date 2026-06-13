from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_phase4am_dataset import run_audit
from scripts.build_phase4am_dataset import (
    BLOCKED_JOIN_COVERAGE,
    READY,
    assign_time_series_split,
    build_dataset_rows,
    build_phase4am_dataset,
)


def test_phase4am_builds_dataset_when_keys_overlap(tmp_path: Path) -> None:
    runtime_dir, ak_summary, al_summary = _prepare_fixture(tmp_path, overlap=True)

    summary = build_phase4am_dataset(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        phase4ak_summary_path=ak_summary,
        phase4al_summary_path=al_summary,
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["joined_row_count"] == 2
    assert summary["join_success_rate"] == 1.0
    assert summary["test_row_count"] == 2
    assert summary["feature_label_columns_separated"] is True
    assert summary["leakage_audit_status"] == "OK"
    assert summary["training_executed"] is False
    assert summary["inference_executed"] is False
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False
    assert Path(summary["dataset_output_path"]).is_file()


def test_phase4am_blocks_when_keys_do_not_overlap(tmp_path: Path) -> None:
    runtime_dir, ak_summary, al_summary = _prepare_fixture(tmp_path, overlap=False)

    summary = build_phase4am_dataset(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        phase4ak_summary_path=ak_summary,
        phase4al_summary_path=al_summary,
    )

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == BLOCKED_JOIN_COVERAGE
    assert summary["joined_row_count"] == 0
    assert summary["join_success_rate"] == 0.0
    assert summary["recommended_next_action"].startswith("Generate a historical feature table")


def test_phase4am_dataset_rows_prefix_feature_and_label_columns() -> None:
    rows = build_dataset_rows(
        feature_rows=[
            {
                "target_date": "2026-03-02",
                "as_of_date": "2026-03-02",
                "code": "7203",
                "feature_version": "fv",
                "price_momentum_return_5d": 0.1,
            }
        ],
        label_rows=[
            {
                "target_date": "2026-03-02",
                "code": "7203",
                "label_version": "lv",
                "future_return_5d": 0.2,
                "future_return_10d": 0.3,
                "future_return_20d": 0.4,
                "future_max_return_20d": 0.5,
                "future_max_drawdown_20d": -0.1,
                "top_decile_20d": True,
                "downside_bad_20d": False,
                "momentum_candidate_label": True,
            }
        ],
    )

    assert rows[0]["feature__price_momentum_return_5d"] == 0.1
    assert rows[0]["label__future_return_20d"] == 0.4
    assert "future_return_20d" not in rows[0]


def test_phase4am_split_is_time_series() -> None:
    assert assign_time_series_split("2024-12-31") == "train"
    assert assign_time_series_split("2025-01-01") == "validation"
    assert assign_time_series_split("2026-01-01") == "test"


def test_phase4am_audit_completes_for_join_coverage_block(tmp_path: Path) -> None:
    runtime_dir, ak_summary, al_summary = _prepare_fixture(tmp_path, overlap=False)
    summary_path = tmp_path / "reports" / "phase4am_dataset_builder_summary.json"
    build_phase4am_dataset(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        phase4ak_summary_path=ak_summary,
        phase4al_summary_path=al_summary,
    )

    result = run_audit(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        summary_path=summary_path,
        json_report_path=tmp_path / "audit.json",
        markdown_report_path=tmp_path / "audit.md",
    )

    assert result["status"] == "complete"
    assert result["readiness_status"] == BLOCKED_JOIN_COVERAGE


def test_phase4am_report_documents_current_block() -> None:
    report = Path("docs/phase_reports/phase4am_dataset_builder.md").read_text(encoding="utf-8")

    assert "BLOCKED_BY_JOIN_COVERAGE" in report
    assert "target_date + code" in report
    assert "READY_FOR_FIRST_TRAINING" in report


def _prepare_fixture(tmp_path: Path, *, overlap: bool) -> tuple[Path, Path, Path]:
    runtime_dir = tmp_path / "runtime"
    feature_date = "2026-03-02" if overlap else "2026-05-29"
    label_date = "2026-03-02"
    feature_path = runtime_dir / "candidate_ai" / "features" / "features.json"
    label_path = runtime_dir / "candidate_ai" / "labels" / "labels.json"
    feature_path.parent.mkdir(parents=True)
    label_path.parent.mkdir(parents=True)
    feature_path.write_text(
        json.dumps(
            {
                "rows": [
                    _feature_row(feature_date, "7203"),
                    _feature_row(feature_date, "6758"),
                ]
            }
        ),
        encoding="utf-8",
    )
    label_path.write_text(
        json.dumps(
            {
                "rows": [
                    _label_row(label_date, "7203"),
                    _label_row(label_date, "6758"),
                ]
            }
        ),
        encoding="utf-8",
    )
    ak_summary = tmp_path / "phase4ak.json"
    al_summary = tmp_path / "phase4al.json"
    ak_summary.write_text(
        json.dumps({"readiness_status": "READY_FOR_LABEL_GENERATION", "feature_output_path": str(feature_path)}),
        encoding="utf-8",
    )
    al_summary.write_text(
        json.dumps({"readiness_status": "READY_FOR_DATASET_BUILDER", "label_output_path": str(label_path)}),
        encoding="utf-8",
    )
    return runtime_dir, ak_summary, al_summary


def _feature_row(target_date: str, code: str) -> dict[str, object]:
    return {
        "target_date": target_date,
        "as_of_date": target_date,
        "code": code,
        "feature_version": "fv",
        "source_snapshot_id": "fixture",
        "feature_set_name": "fixture",
        "created_at": "2026-01-01T00:00:00+00:00",
        "data_start_date": target_date,
        "data_end_date": target_date,
        "universe_eligible": True,
        "excluded_reason": "",
        "price_momentum_return_5d": 0.1,
        "volume_momentum_ratio_5d": 1.2,
    }


def _label_row(target_date: str, code: str) -> dict[str, object]:
    return {
        "target_date": target_date,
        "code": code,
        "label_version": "lv",
        "future_return_5d": 0.1,
        "future_return_10d": 0.2,
        "future_return_20d": 0.3,
        "future_max_return_20d": 0.4,
        "future_max_drawdown_20d": -0.05,
        "top_decile_20d": True,
        "downside_bad_20d": False,
        "momentum_candidate_label": True,
    }
