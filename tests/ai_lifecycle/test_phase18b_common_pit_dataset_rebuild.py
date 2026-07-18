from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.ai_lifecycle.bundle import REQUIRED_BUNDLE_FILES
from ai_fund_lab_v2.ai_lifecycle.cutoff import resolve_label_safe_cutoff
from ai_fund_lab_v2.ai_lifecycle.dataset_rebuild import DatasetRebuildRequest, rebuild_common_pit_dataset
from ai_fund_lab_v2.ai_lifecycle.source_authority import resolve_source_authority


CREATED_AT = "2026-07-17T00:00:00+00:00"


def test_source_authority_resolves_evidence_hashes(tmp_path: Path) -> None:
    frames = _source_authority_frames()
    paths = _write_source_authority_frames(tmp_path, frames)

    authority = resolve_source_authority(source_paths=paths, root=tmp_path)

    payload = authority.to_dict()
    assert sorted(payload) == sorted(frames)
    assert payload["canonical_normalized_quotes"]["content_hash"]
    assert payload["canonical_normalized_quotes"]["schema_hash"]
    assert payload["trading_calendar"]["source_ref"] == "artifact:trading_calendar.csv"


def test_label_safe_cutoff_uses_20_business_day_horizon() -> None:
    calendar = _calendar("2026-01-01", periods=45)

    cutoff = resolve_label_safe_cutoff(trading_calendar=calendar, latest_trading_date="2026-02-20")

    dates = calendar["date"].astype(str).tolist()
    assert cutoff.latest_trading_date == "2026-02-20"
    assert cutoff.label_safe_cutoff == dates[dates.index("2026-02-20") - 20]
    assert cutoff.target_horizon_business_days == 20


def test_candidate_adapter_writes_complete_bundle(tmp_path: Path) -> None:
    normalized = _normalized_quotes()
    result = _run_candidate(tmp_path, normalized)

    assert result["status"] == "PASS"
    final_dir = tmp_path / "candidate_bundle"
    assert sorted(path.name for path in final_dir.iterdir()) == sorted(REQUIRED_BUNDLE_FILES)
    status = _read_json(final_dir / "status.json")
    assert status["validation_status"] == "PASS"
    assert _validation(status, "PIT")["status"] == "PASS"
    assert _validation(status, "Leakage")["evidence"]["no_leakage_status"] == "NO_LEAKAGE_PASS"
    metadata = _read_json(final_dir / "dataset_metadata.json")
    assert metadata["row_uniqueness_keys"] == ["target_date", "code"]
    assert metadata["training_executed"] is False
    assert metadata["runtime_switch_performed"] is False


def test_opportunity_adapter_candidate_source_ref_and_bundle(tmp_path: Path) -> None:
    request = _opportunity_request(tmp_path, tmp_path / "opportunity_bundle")

    result = rebuild_common_pit_dataset(request)

    assert result["status"] == "PASS"
    dataset = pd.read_parquet(tmp_path / "opportunity_bundle" / "dataset.parquet")
    assert "candidate_source_ref" in dataset.columns
    assert set(dataset["candidate_source_ref"]) == {"candidate:candidate_dataset_v1:abcdef1234567890"}
    assert dataset.duplicated(["target_date", "code", "candidate_source_ref"]).sum() == 0
    metadata = _read_json(tmp_path / "opportunity_bundle" / "dataset_metadata.json")
    assert metadata["row_uniqueness_keys"] == ["target_date", "code", "candidate_source_ref"]
    assert _read_json(tmp_path / "opportunity_bundle" / "feature_schema.json")["columns"]


def test_failure_path_blocks_final_publish_and_writes_artifact(tmp_path: Path) -> None:
    request = _opportunity_request(tmp_path, tmp_path / "bad_bundle")
    request = DatasetRebuildRequest(
        **{
            **request.__dict__,
            "candidate_dataset_identity": {"candidate_source_ref": "/absolute/path/not_allowed"},
        }
    )

    result = rebuild_common_pit_dataset(request)

    assert result["status"] == "FAIL"
    assert not (tmp_path / "bad_bundle").exists()
    failure_path = Path(result["failure_artifact"])
    assert failure_path.is_file()
    assert _read_json(failure_path)["final_bundle_created"] is False


def test_idempotency_same_input_same_hashes_and_version(tmp_path: Path) -> None:
    normalized = _normalized_quotes()

    result_a = _run_candidate(tmp_path / "a", normalized)
    result_b = _run_candidate(tmp_path / "b", normalized)

    manifest_a = result_a["hash_manifest"]
    manifest_b = result_b["hash_manifest"]
    assert manifest_a["dataset_hash"] == manifest_b["dataset_hash"]
    assert manifest_a["schema_hash"] == manifest_b["schema_hash"]
    meta_a = _read_json(tmp_path / "a" / "candidate_bundle" / "dataset_metadata.json")
    meta_b = _read_json(tmp_path / "b" / "candidate_bundle" / "dataset_metadata.json")
    assert meta_a["dataset_version"] == meta_b["dataset_version"]


def _run_candidate(tmp_path: Path, normalized: pd.DataFrame) -> dict:
    tmp_path.mkdir(parents=True, exist_ok=True)
    frames = _source_authority_frames(quotes=normalized)
    authority = resolve_source_authority(source_frames=frames)
    cutoff = resolve_label_safe_cutoff(
        trading_calendar=frames["trading_calendar"],
        latest_trading_date=frames["trading_calendar"]["date"].max(),
    )
    return rebuild_common_pit_dataset(
        DatasetRebuildRequest(
            component="Candidate",
            final_dir=tmp_path / "candidate_bundle",
            source_authority=authority,
            cutoff=cutoff,
            normalized_quotes=normalized,
            created_at=CREATED_AT,
            failure_report_dir=tmp_path / "failures",
        )
    )


def _opportunity_request(tmp_path: Path, final_dir: Path) -> DatasetRebuildRequest:
    candidate, features, labels = _opportunity_inputs()
    frames = _source_authority_frames(quotes=features)
    authority = resolve_source_authority(source_frames=frames)
    cutoff = resolve_label_safe_cutoff(
        trading_calendar=frames["trading_calendar"],
        latest_trading_date=frames["trading_calendar"]["date"].max(),
    )
    return DatasetRebuildRequest(
        component="Opportunity",
        final_dir=final_dir,
        source_authority=authority,
        cutoff=cutoff,
        candidate_frame=candidate,
        feature_frame=features,
        label_frame=labels,
        candidate_dataset_identity={
            "dataset_hash": "abcdef1234567890ffff",
            "dataset_version": "candidate_dataset_v1",
        },
        created_at=CREATED_AT,
        failure_report_dir=tmp_path / "failures",
    )


def _normalized_quotes() -> pd.DataFrame:
    dates = pd.bdate_range("2026-01-01", periods=95).strftime("%Y-%m-%d").tolist()
    rows = []
    for offset, code in enumerate(("1001", "1002")):
        for index, date in enumerate(dates):
            rows.append(
                {
                    "Date": date,
                    "Code": code,
                    "Close": 100.0 + offset * 10 + index * (1.0 + offset * 0.1),
                    "Volume": 1000 + index * 7 + offset * 20,
                }
            )
    return pd.DataFrame(rows)


def _opportunity_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2026-01-01", periods=25).strftime("%Y-%m-%d").tolist()
    candidate_rows = []
    feature_rows = []
    label_rows = []
    for date_index, date in enumerate(dates[:5]):
        for code_index, code in enumerate(("1001", "1002", "1003")):
            candidate_rows.append(
                {
                    "target_date": date,
                    "code": code,
                    "candidate_score": 0.3 + date_index * 0.01 + code_index * 0.02,
                    "candidate_rank": code_index + 1,
                    "candidate_reason": "phase18b_fixture",
                }
            )
            row = {"target_date": date, "as_of_date": date, "code": code, "feature_version": "fixture"}
            for feature_index in range(29):
                row[f"market_feature_{feature_index:02d}"] = float(date_index + code_index + feature_index / 100.0)
            feature_rows.append(row)
            label_rows.append(
                {
                    "target_date": date,
                    "code": code,
                    "future_return_20d": 0.05 + code_index * 0.01,
                    "future_max_return_20d": 0.10 + code_index * 0.01,
                    "future_max_drawdown_20d": -0.02,
                }
            )
    return pd.DataFrame(candidate_rows), pd.DataFrame(feature_rows), pd.DataFrame(label_rows)


def _source_authority_frames(quotes: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    quotes = quotes if quotes is not None else _normalized_quotes()
    calendar = _calendar("2026-01-01", periods=120)
    listed = pd.DataFrame({"target_date": calendar["date"].head(3), "code": ["1001", "1002", "1003"], "listed": [True, True, True]})
    candidate_lineage = pd.DataFrame({"target_date": ["2026-01-01"], "lineage_ref": ["phase18b_candidate_lineage"]})
    return {
        "canonical_normalized_quotes": quotes,
        "trading_calendar": calendar,
        "listed_issues": listed,
        "candidate_source": quotes.head(3).copy(),
        "opportunity_source": quotes.tail(3).copy(),
        "candidate_lineage": candidate_lineage,
    }


def _write_source_authority_frames(tmp_path: Path, frames: dict[str, pd.DataFrame]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name, frame in frames.items():
        path = tmp_path / f"{name}.csv"
        frame.to_csv(path, index=False)
        paths[name] = path
    return paths


def _calendar(start: str, *, periods: int) -> pd.DataFrame:
    return pd.DataFrame({"date": pd.bdate_range(start, periods=periods).strftime("%Y-%m-%d"), "is_trading_day": True})


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _validation(status: dict, name: str) -> dict:
    return next(item for item in status["validations"] if item["name"] == name)
