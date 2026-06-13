from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_phase4at_candidate_feature_quality import (
    READY,
    analyze_feature_quality,
    audit_phase4at_candidate_feature_quality,
    extract_builder_design_features,
    extract_catalog_features,
    summarize_values,
)


def test_phase4at_audits_feature_quality(tmp_path: Path) -> None:
    ao_summary, an_summary = _prepare_fixture(tmp_path)

    summary = audit_phase4at_candidate_feature_quality(
        phase4ao_summary_path=ao_summary,
        phase4an_summary_path=an_summary,
        summary_path=tmp_path / "summary.json",
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["feature_count"] == 4
    assert summary["constant_feature_count"] >= 2
    assert summary["high_null_feature_count"] >= 1
    assert summary["all_null_feature_count"] >= 1
    assert summary["implemented_feature_count"] == 4
    assert summary["missing_feature_count"] > 0
    assert summary["feature_builder_design_gap"]["implemented_but_all_null"]
    assert summary["likely_root_cause"]
    assert summary["recommended_fix_plan"]
    assert summary["training_executed"] is False
    assert summary["inference_executed"] is False
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False


def test_phase4at_feature_stats_include_quantiles_and_variance() -> None:
    stats = summarize_values([1.0, 2.0, 3.0, None])

    assert stats["null_rate"] == 0.25
    assert stats["unique_count"] == 3
    assert stats["variance"] is not None
    assert stats["p25"] == 1.5
    assert stats["median"] == 2.0
    assert stats["p75"] == 2.5


def test_phase4at_detects_constant_near_constant_and_high_null() -> None:
    rows = [
        {"feature__a": 1.0, "feature__b": None, "feature__c": 0.0},
        {"feature__a": 1.0, "feature__b": None, "feature__c": 0.0},
        {"feature__a": 1.0, "feature__b": 2.0, "feature__c": 1.0},
    ]

    report = analyze_feature_quality(rows, ["feature__a", "feature__b", "feature__c"])

    assert "feature__a" in report["constant_features"]
    assert "feature__b" in report["high_null_features"]
    assert report["near_constant_feature_count"] >= 1


def test_phase4at_extracts_design_and_catalog_features() -> None:
    design_features = extract_builder_design_features(Path("docs/03_ai_design/candidate_feature_builder_design.md"))
    catalog_features = extract_catalog_features(Path("docs/03_ai_design/candidate_feature_catalog.md"))

    assert "price_momentum_return_5d" in design_features
    assert "liquidity_avg_turnover_20d" in design_features
    assert "return_5d" in catalog_features
    assert "sales_growth_rate" in catalog_features


def test_phase4at_report_documents_feature_quality_scope(tmp_path: Path) -> None:
    ao_summary, an_summary = _prepare_fixture(tmp_path)
    audit_phase4at_candidate_feature_quality(
        phase4ao_summary_path=ao_summary,
        phase4an_summary_path=an_summary,
        summary_path=tmp_path / "summary.json",
    )

    report = Path("docs/phase_reports/phase4at_candidate_feature_quality.md").read_text(encoding="utf-8")
    assert "Phase4-AT" in report
    assert "feature quality" in report.lower()
    assert "does not add features" in report


def _prepare_fixture(tmp_path: Path) -> tuple[Path, Path]:
    dataset_path = tmp_path / "dataset.json"
    feature_path = tmp_path / "features.json"
    dataset_rows = [
        {
            "target_date": "2026-03-02",
            "feature__price_momentum_return_5d": None,
            "feature__volume_momentum_ratio_5d": None,
            "feature__missing_flags_insufficient_history": True,
            "feature__missing_flags_price": False,
        },
        {
            "target_date": "2026-03-03",
            "feature__price_momentum_return_5d": None,
            "feature__volume_momentum_ratio_5d": None,
            "feature__missing_flags_insufficient_history": True,
            "feature__missing_flags_price": False,
        },
    ]
    feature_rows = [
        {
            "target_date": "2026-05-29",
            "price_momentum_return_5d": 0.1,
            "volume_momentum_ratio_5d": 1.2,
            "missing_flags_insufficient_history": False,
            "missing_flags_price": False,
        },
        {
            "target_date": "2026-05-29",
            "price_momentum_return_5d": 0.2,
            "volume_momentum_ratio_5d": 1.4,
            "missing_flags_insufficient_history": False,
            "missing_flags_price": False,
        },
    ]
    dataset_path.write_text(json.dumps({"rows": dataset_rows}), encoding="utf-8")
    feature_path.write_text(json.dumps({"rows": feature_rows}), encoding="utf-8")
    ao_summary = tmp_path / "ao.json"
    an_summary = tmp_path / "an.json"
    ao_summary.write_text(json.dumps({"dataset_output_path": str(dataset_path)}), encoding="utf-8")
    an_summary.write_text(json.dumps({"historical_feature_output_path": str(feature_path)}), encoding="utf-8")
    return ao_summary, an_summary
