from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from scripts.audit_phase4bg_formal_candidate_inference import run_audit
from scripts.run_phase4bg_formal_candidate_inference import (
    READY,
    audit_inference_features,
    run_phase4bg_formal_candidate_inference,
    validate_candidate_output,
)


def test_phase4bg_runs_formal_candidate_inference(tmp_path: Path) -> None:
    runtime_dir, bf_summary, bc_summary = _prepare_fixture(tmp_path, row_count=60)

    summary = run_phase4bg_formal_candidate_inference(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        phase4bf_summary_path=bf_summary,
        phase4bc_summary_path=bc_summary,
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["inference_executed"] is True
    assert summary["formal_inference"] is True
    assert summary["target_date"] == "2026-06-12"
    assert summary["input_feature_row_count"] == 60
    assert summary["eligible_input_count"] == 55
    assert summary["excluded_input_count"] == 5
    assert summary["scored_count"] == 55
    assert summary["candidate_count"] == 50
    assert summary["unique_candidate_score_count"] > 1
    assert summary["all_same_score"] is False
    assert summary["ranking_effective"] is True
    assert summary["future_column_used_as_feature"] is False
    assert summary["label_column_used_as_feature"] is False
    assert summary["leakage_audit_status"] == "OK"
    assert summary["responsibility_boundary_status"] == "OK"
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False
    assert summary["broker_api_called"] is False
    assert summary["order_executed"] is False
    assert Path(summary["top50_json_path"]).is_file()
    assert Path(summary["top50_csv_path"]).is_file()


def test_phase4bg_top50_schema_and_sort(tmp_path: Path) -> None:
    runtime_dir, bf_summary, bc_summary = _prepare_fixture(tmp_path, row_count=60)
    summary = run_phase4bg_formal_candidate_inference(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        phase4bf_summary_path=bf_summary,
        phase4bc_summary_path=bc_summary,
    )
    payload = json.loads(Path(summary["top50_json_path"]).read_text(encoding="utf-8"))
    rows = payload["rows"]
    scores = [row["candidate_score"] for row in rows]

    assert validate_candidate_output(rows)
    assert [row["candidate_rank"] for row in rows] == list(range(1, 51))
    assert scores == sorted(scores, reverse=True)
    assert all("not_buy_decision" in row["audit_flags"] for row in rows)
    assert all("not_purchase_rank" in row["audit_flags"] for row in rows)


def test_phase4bg_feature_audit_rejects_label_and_future_features() -> None:
    result = audit_inference_features(
        [
            "feature__price_momentum_return_5d",
            "feature__future_return_20d",
            "label__momentum_candidate_label",
        ]
    )

    assert result["status"] == "ERROR"
    assert result["future_column_used_as_feature"] is True
    assert result["label_column_used_as_feature"] is True


def test_phase4bg_audit_completes(tmp_path: Path) -> None:
    runtime_dir, bf_summary, bc_summary = _prepare_fixture(tmp_path, row_count=60)
    summary_path = tmp_path / "reports" / "phase4bg_formal_candidate_inference_summary.json"
    run_phase4bg_formal_candidate_inference(
        runtime_dir=runtime_dir,
        report_dir=tmp_path / "reports",
        phase4bf_summary_path=bf_summary,
        phase4bc_summary_path=bc_summary,
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
    assert result["checks"]["candidate_schema_ok"] is True
    assert result["checks"]["backtest_trading_broker_order_not_executed"] is True


def test_phase4bg_report_documents_formal_inference_scope() -> None:
    report = Path("docs/phase_reports/phase4bg_formal_candidate_inference.md").read_text(encoding="utf-8")

    assert "Formal Candidate Inference" in report
    assert "READY_FOR_FORMAL_CANDIDATE_QUALITY_AUDIT" in report
    assert "not a buy signal" in report
    assert "backtest_executed: `False`" in report


def _prepare_fixture(tmp_path: Path, *, row_count: int) -> tuple[Path, Path, Path]:
    runtime_dir = tmp_path / "runtime"
    model_dir = runtime_dir / "candidate_ai" / "models"
    feature_dir = runtime_dir / "candidate_ai" / "features"
    model_dir.mkdir(parents=True)
    feature_dir.mkdir(parents=True)
    feature_columns = [
        "feature__price_momentum_return_5d",
        "feature__volume_momentum_ratio_5d",
        "feature__liquidity_avg_volume_20d",
    ]
    model = LogisticRegression(random_state=42).fit(
        np.asarray([[0.1, 1.5, 1.0], [-0.1, 0.5, 0.1], [0.2, 1.8, 2.0], [-0.2, 0.7, 0.2]], dtype=float),
        np.asarray([1, 0, 1, 0], dtype=int),
    )
    model_path = model_dir / "phase4bf_formal_candidate_model.pkl"
    manifest_path = model_dir / "phase4bf_formal_candidate_model_manifest.json"
    with model_path.open("wb") as handle:
        pickle.dump(
            {
                "phase": "Phase4-BF",
                "model_type": "sklearn.LogisticRegression",
                "target_label": "label__momentum_candidate_label",
                "feature_columns": feature_columns,
                "model": model,
                "formal_training": True,
            },
            handle,
        )
    manifest_path.write_text(json.dumps({"production_model_promoted": False}), encoding="utf-8")
    feature_path = feature_dir / "features.parquet"
    pd.DataFrame([_feature_row(index) for index in range(row_count)]).to_parquet(feature_path, index=False)
    bf_summary = tmp_path / "phase4bf.json"
    bc_summary = tmp_path / "phase4bc.json"
    bf_summary.write_text(
        json.dumps(
            {
                "readiness_status": "READY_FOR_FORMAL_CANDIDATE_INFERENCE",
                "model_artifact_path": str(model_path),
                "model_manifest_path": str(manifest_path),
                "model_type": "sklearn.LogisticRegression",
            }
        ),
        encoding="utf-8",
    )
    bc_summary.write_text(json.dumps({"feature_output_path": str(feature_path)}), encoding="utf-8")
    return runtime_dir, bf_summary, bc_summary


def _feature_row(index: int) -> dict[str, object]:
    excluded = index % 12 == 0
    return {
        "target_date": "2026-06-12",
        "code": f"{1000 + index}",
        "universe_eligible": not excluded,
        "excluded_reason": "insufficient_history" if excluded else "",
        "source_snapshot_id": "fixture_snapshot",
        "feature_version": "fixture_feature_v1",
        "price_momentum_return_5d": 0.2 - index * 0.001,
        "volume_momentum_ratio_5d": 1.8 - index * 0.01,
        "liquidity_avg_volume_20d": 2.0 - index * 0.01,
    }
