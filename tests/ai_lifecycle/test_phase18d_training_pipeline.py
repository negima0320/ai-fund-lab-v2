from __future__ import annotations

from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.ai_lifecycle.bundle import DatasetBundleWriter
from ai_fund_lab_v2.ai_lifecycle.cutoff import LabelSafeCutoff
from ai_fund_lab_v2.ai_lifecycle.source_authority import resolve_source_authority
from ai_fund_lab_v2.ai_lifecycle.training_pipeline import (
    DatasetAuthority,
    TrainingConfig,
    audit_forbidden_features,
    compare_training_bundles,
    make_time_series_split,
    run_training_pipeline,
    verify_dataset_authority,
)
from ai_fund_lab_v2.ai_lifecycle.validators import validate_dataset_bundle_inputs


def test_phase18d_dataset_authority_split_training_and_failure(tmp_path: Path) -> None:
    dataset = _candidate_dataset()
    feature_columns = ["feature__x1", "feature__x2"]
    label_columns = ["label__momentum_candidate_label", "label__future_return_20d"]
    authority = resolve_source_authority(source_frames=_source_frames(dataset))
    cutoff = LabelSafeCutoff(latest_trading_date="2026-06-26", label_safe_cutoff="2026-06-04", target_horizon_business_days=20)
    validations = validate_dataset_bundle_inputs(
        component="Candidate",
        dataset=dataset,
        feature_columns=feature_columns,
        label_columns=label_columns,
        uniqueness_keys=["target_date", "code"],
        cutoff=cutoff,
        source_authority=authority,
        adapter_audit={"status": "OK"},
    )
    bundle_dir = tmp_path / "candidate_dataset"
    DatasetBundleWriter(final_dir=bundle_dir).write_and_publish(
        component="Candidate",
        dataset=dataset,
        feature_columns=feature_columns,
        label_columns=label_columns,
        uniqueness_keys=["target_date", "code"],
        cutoff=cutoff,
        source_authority=authority,
        validations=validations,
        adapter_summary={"adapter": "fixture"},
        created_at="2026-07-17T00:00:00+00:00",
    )
    manifest = _read_json(bundle_dir / "hash_manifest.json")
    metadata = _read_json(bundle_dir / "dataset_metadata.json")
    dataset_authority = DatasetAuthority(
        component="Candidate",
        dataset_dir=bundle_dir,
        dataset_hash=manifest["dataset_hash"],
        feature_schema_hash=manifest["feature_schema_hash"],
        target_schema_hash=manifest["target_schema_hash"],
        dataset_version=metadata["dataset_version"],
    )

    assert verify_dataset_authority(dataset_authority)["status"] == "PASS"
    assert verify_dataset_authority(DatasetAuthority(**{**dataset_authority.__dict__, "dataset_hash": "bad"}))["status"] == "FAIL"
    split = make_time_series_split(dataset)
    assert split["embargo_business_days"] == 20
    assert audit_forbidden_features(feature_columns)["status"] == "PASS"

    config = TrainingConfig(
        component="Candidate",
        challenger_name="fixture_candidate",
        model_kind="sklearn_sgd_classifier",
        target_label="label__momentum_candidate_label",
        max_iter=5,
    )
    first = run_training_pipeline(
        authority=dataset_authority,
        output_dir=tmp_path / "training_a",
        config=config,
        champion_identity={"name": "fixture_champion"},
        report_dir=tmp_path / "failures",
    )
    second = run_training_pipeline(
        authority=dataset_authority,
        output_dir=tmp_path / "training_b",
        config=config,
        champion_identity={"name": "fixture_champion"},
        report_dir=tmp_path / "failures",
    )
    assert first["status"] == "PASS"
    assert second["status"] == "PASS"
    assert compare_training_bundles(first, second)["status"] == "PASS"

    bad = run_training_pipeline(
        authority=DatasetAuthority(**{**dataset_authority.__dict__, "dataset_hash": "bad"}),
        output_dir=tmp_path / "bad_training",
        config=config,
        champion_identity={"name": "fixture_champion"},
        report_dir=tmp_path / "failures",
    )
    assert bad["status"] == "FAIL"
    assert Path(bad["failure_artifact"]).is_file()


def _candidate_dataset() -> pd.DataFrame:
    dates = pd.bdate_range("2024-10-01", "2026-05-15").strftime("%Y-%m-%d").tolist()
    rows = []
    for date_index, date in enumerate(dates):
        for code_index, code in enumerate(("1001", "1002", "1003")):
            x1 = date_index / 100.0 + code_index * 0.1
            x2 = (date_index % 7) - code_index
            rows.append(
                {
                    "target_date": date,
                    "as_of_date": date,
                    "code": code,
                    "dataset_version": "fixture",
                    "feature__x1": x1,
                    "feature__x2": x2,
                    "label__momentum_candidate_label": bool((x1 + x2) % 2 > 1),
                    "label__future_return_20d": x1 / 10.0,
                }
            )
    return pd.DataFrame(rows)


def _source_frames(dataset: pd.DataFrame) -> dict[str, pd.DataFrame]:
    calendar = pd.DataFrame({"date": sorted(dataset["target_date"].unique()), "is_trading_day": True})
    return {
        "canonical_normalized_quotes": dataset[["target_date", "code"]].copy(),
        "trading_calendar": calendar,
        "listed_issues": dataset[["target_date", "code"]].head(5).copy(),
        "candidate_source": dataset.head(5).copy(),
        "opportunity_source": dataset.tail(5).copy(),
        "candidate_lineage": pd.DataFrame({"target_date": ["2026-01-01"], "lineage": ["fixture"]}),
    }


def _read_json(path: Path) -> dict:
    import json

    return json.loads(path.read_text(encoding="utf-8"))
