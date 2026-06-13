from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_phase4ao_dataset_retry import run_audit
from scripts.build_phase4ao_dataset_retry import (
    READY,
    build_phase4ao_dataset_retry,
)


def test_phase4ao_builds_retry_dataset_from_historical_features(tmp_path: Path) -> None:
    runtime_dir, an_summary, al_summary = _prepare_fixture(tmp_path)

    summary = build_phase4ao_dataset_retry(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        phase4an_summary_path=an_summary,
        phase4al_summary_path=al_summary,
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["feature_row_count"] == 4
    assert summary["label_row_count"] == 3
    assert summary["joined_row_count"] == 3
    assert summary["join_success_rate"] == 1.0
    assert summary["test_row_count"] == 3
    assert summary["feature_label_columns_separated"] is True
    assert summary["future_column_detected_in_features"] is False
    assert summary["label_column_detected_in_features"] is False
    assert summary["leakage_audit_status"] == "OK"
    assert summary["training_executed"] is False
    assert summary["inference_executed"] is False
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False
    assert Path(summary["dataset_output_path"]).is_file()


def test_phase4ao_dataset_rows_keep_feature_and_label_prefixes(tmp_path: Path) -> None:
    runtime_dir, an_summary, al_summary = _prepare_fixture(tmp_path)
    summary = build_phase4ao_dataset_retry(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        phase4an_summary_path=an_summary,
        phase4al_summary_path=al_summary,
    )
    dataset = json.loads(Path(summary["dataset_output_path"]).read_text(encoding="utf-8"))
    row = dataset["rows"][0]

    assert "feature__price_momentum_return_5d" in row
    assert "label__future_return_20d" in row
    assert "future_return_20d" not in row
    assert "feature__future_return_20d" not in row


def test_phase4ao_audit_completes(tmp_path: Path) -> None:
    runtime_dir, an_summary, al_summary = _prepare_fixture(tmp_path)
    summary_path = tmp_path / "reports" / "phase4ao_dataset_retry_summary.json"
    build_phase4ao_dataset_retry(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        phase4an_summary_path=an_summary,
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
    assert result["readiness_status"] == READY
    assert result["checks"]["joined_rows_positive"] is True
    assert result["checks"]["training_inference_backtest_trading_not_executed"] is True


def test_phase4ao_report_documents_retry_scope() -> None:
    report = Path("docs/phase_reports/phase4ao_dataset_retry.md").read_text(encoding="utf-8")

    assert "Phase4-AO" in report
    assert "target_date + code" in report
    assert "READY_FOR_FIRST_LIGHTGBM_TRAINING" in report
    assert "LightGBM" in report


def _prepare_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    runtime_dir = tmp_path / "runtime"
    feature_path = runtime_dir / "candidate_ai" / "features" / "phase4an_features.json"
    label_path = runtime_dir / "candidate_ai" / "labels" / "phase4al_labels.json"
    feature_path.parent.mkdir(parents=True)
    label_path.parent.mkdir(parents=True)
    feature_path.write_text(
        json.dumps(
            {
                "rows": [
                    _feature_row("2026-03-02", "7203"),
                    _feature_row("2026-03-02", "6758"),
                    _feature_row("2026-03-03", "7203"),
                    _feature_row("2026-03-03", "6758"),
                ]
            }
        ),
        encoding="utf-8",
    )
    label_path.write_text(
        json.dumps(
            {
                "rows": [
                    _label_row("2026-03-02", "7203"),
                    _label_row("2026-03-02", "6758"),
                    _label_row("2026-03-03", "7203"),
                ]
            }
        ),
        encoding="utf-8",
    )
    an_summary = tmp_path / "phase4an.json"
    al_summary = tmp_path / "phase4al.json"
    an_summary.write_text(
        json.dumps(
            {
                "readiness_status": "READY_FOR_DATASET_BUILDER_RETRY",
                "historical_feature_output_path": str(feature_path),
            }
        ),
        encoding="utf-8",
    )
    al_summary.write_text(
        json.dumps({"readiness_status": "READY_FOR_DATASET_BUILDER", "label_output_path": str(label_path)}),
        encoding="utf-8",
    )
    return runtime_dir, an_summary, al_summary


def _feature_row(target_date: str, code: str) -> dict[str, object]:
    return {
        "target_date": target_date,
        "as_of_date": target_date,
        "code": code,
        "feature_version": "fv",
        "source_snapshot_id": "fixture",
        "feature_set_name": "fixture",
        "created_at": "2026-01-01T00:00:00+00:00",
        "data_start_date": "2026-02-01",
        "data_end_date": target_date,
        "universe_eligible": True,
        "excluded_reason": "",
        "price_momentum_return_5d": 0.1,
        "price_momentum_return_20d": 0.2,
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
