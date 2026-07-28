from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ai_fund_lab_v2.strategy.corporate_event import (
    CorporateEventConsumerError,
    CorporateEventInputPaths,
    CorporateEventSchemaError,
    deterministic_event_id,
    load_corporate_event_fixture,
    produce_corporate_event_artifact,
    produced_but_not_consumed_evidence,
    sha256_file,
    validate_corporate_event_artifact,
    verify_source_hashes,
)


BUSINESS_DATE = "2026-07-10"


def test_phase22_aa_valid_draft_with_delisting_event_identity_and_fixture_consumer(tmp_path: Path) -> None:
    inputs = _write_sources(tmp_path, delisting=True)
    path = tmp_path / "corporate_event.json"
    result = produce_corporate_event_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=path,
        as_of="2026-07-10T00:00:00+00:00",
        require_full_source_coverage=False,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert result.status == "PASS"
    assert payload["schema_version"] == "corporate_event_authority.v1"
    assert payload["artifact_lifecycle_status"] == "DRAFT"
    assert payload["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    assert payload["events"][0]["event_type"] == "DELISTING_PENDING"
    assert payload["events"][0]["event_id"] == deterministic_event_id(payload["events"][0])
    assert validate_corporate_event_artifact(payload)["status"] == "PASS"
    assert load_corporate_event_fixture(path)["event_count"] == 1
    with pytest.raises(CorporateEventConsumerError):
        load_corporate_event_fixture(path, for_production=True)


def test_phase22_aa_schema_blocks_required_field_invalid_event_type_date_order_status_and_version(tmp_path: Path) -> None:
    inputs = _write_sources(tmp_path, delisting=True)
    result = produce_corporate_event_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=tmp_path / "corporate_event.json",
        as_of="2026-07-10T00:00:00+00:00",
        require_full_source_coverage=False,
    )
    payload = dict(result.payload)
    event = dict(payload["events"][0])

    mutations = [
        lambda item: item.pop("business_date"),
        lambda item: item.update({"schema_version": "corporate_event_authority.v999"}),
        lambda item: item.update({"producer_result_status": "OK"}),
        lambda item: item.update({"runtime_consumer_eligibility": "ELIGIBLE"}),
        lambda item: item.update({"events": [{**event, "event_type": "OTHER"}]}),
        lambda item: item.update({"events": [{**event, "announcement_date": "20260710"}]}),
        lambda item: item.update({"events": [{**event, "announcement_date": "2026-07-11", "effective_date": "2026-07-10"}]}),
    ]
    for mutation in mutations:
        broken = dict(payload)
        mutation(broken)
        with pytest.raises(CorporateEventSchemaError):
            validate_corporate_event_artifact(broken)


def test_phase22_aa_pit_no_leakage_and_determinism(tmp_path: Path) -> None:
    inputs = _write_sources(tmp_path, delisting=True)
    first = produce_corporate_event_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=tmp_path / "first.json",
        as_of="2026-07-10T00:00:00+00:00",
        require_full_source_coverage=False,
    )
    second = produce_corporate_event_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=tmp_path / "second.json",
        as_of="2026-07-10T00:00:00+00:00",
        require_full_source_coverage=False,
    )
    assert first.artifact_hash == second.artifact_hash
    assert first.payload["events"][0]["announcement_date"] <= BUSINESS_DATE
    assert first.payload["events"][0]["availability_date"] <= BUSINESS_DATE

    future_inputs = _write_sources(tmp_path / "future", future_row=True)
    future = produce_corporate_event_artifact(
        business_date=BUSINESS_DATE,
        input_paths=future_inputs,
        output_path=tmp_path / "future.json",
        as_of="2026-07-10T00:00:00+00:00",
        require_full_source_coverage=False,
    )
    assert future.status == "PASS"
    assert future.payload["temporal_safety"]["future_leakage_used"] is False

    only_future = produce_corporate_event_artifact(
        business_date="2026-07-01",
        input_paths=future_inputs,
        output_path=tmp_path / "only_future.json",
        as_of="2026-07-01T00:00:00+00:00",
        require_full_source_coverage=False,
    )
    assert only_future.status == "BLOCK"
    assert "future_listed_issues_row_rejected" in only_future.payload["reason_codes"]
    with pytest.raises(CorporateEventConsumerError):
        load_corporate_event_fixture(tmp_path / "only_future.json")

    future_only_inputs = _write_sources(tmp_path / "future_only", future_row=True)
    future_only = produce_corporate_event_artifact(
        business_date="2026-07-01",
        input_paths=future_only_inputs,
        output_path=tmp_path / "future_only.json",
        as_of="2026-07-01T00:00:00+00:00",
        require_full_source_coverage=False,
    )
    assert future_only.status == "BLOCK"
    assert "future_listed_issues_row_rejected" in future_only.payload["reason_codes"]


def test_phase22_aa_only_future_listed_source_blocks(tmp_path: Path) -> None:
    inputs = _write_sources(tmp_path, future_row=True)
    future = produce_corporate_event_artifact(
        business_date="2026-07-01",
        input_paths=inputs,
        output_path=tmp_path / "future.json",
        as_of="2026-07-01T00:00:00+00:00",
        require_full_source_coverage=False,
    )
    assert future.status == "BLOCK"
    assert "future_listed_issues_row_rejected" in future.payload["reason_codes"]
    with pytest.raises(CorporateEventConsumerError):
        load_corporate_event_fixture(tmp_path / "future.json")


def test_phase22_aa_source_hash_missing_and_no_event_semantics(tmp_path: Path) -> None:
    missing = produce_corporate_event_artifact(
        business_date=BUSINESS_DATE,
        input_paths=CorporateEventInputPaths(listed_issues_path=tmp_path / "missing.parquet"),
        output_path=tmp_path / "missing.json",
        as_of="2026-07-10T00:00:00+00:00",
    )
    assert missing.status == "REVIEW_REQUIRED"
    assert missing.payload["coverage_status"] == "MISSING"
    assert missing.payload["no_event_semantics"]["unknown_event_state_when_source_missing"] is True

    no_event_inputs = _write_sources(tmp_path / "no_event", delisting=False)
    no_event = produce_corporate_event_artifact(
        business_date=BUSINESS_DATE,
        input_paths=no_event_inputs,
        output_path=tmp_path / "no_event.json",
        as_of="2026-07-10T00:00:00+00:00",
        require_full_source_coverage=False,
    )
    assert no_event.status == "PASS"
    assert no_event.payload["events"] == []
    assert no_event.payload["coverage_status"] == "AVAILABLE"

    review = produce_corporate_event_artifact(
        business_date=BUSINESS_DATE,
        input_paths=no_event_inputs,
        output_path=tmp_path / "coverage_gap.json",
        as_of="2026-07-10T00:00:00+00:00",
        require_full_source_coverage=True,
    )
    assert review.status == "REVIEW_REQUIRED"
    assert review.payload["coverage_status"] == "PARTIAL"
    assert "corporate_event_source_coverage_incomplete" in review.payload["reason_codes"]

    mismatch = produce_corporate_event_artifact(
        business_date=BUSINESS_DATE,
        input_paths=no_event_inputs,
        output_path=tmp_path / "mismatch.json",
        as_of="2026-07-10T00:00:00+00:00",
        expected_source_hashes={"jquants_listed_issues": "0" * 64},
        require_full_source_coverage=False,
    )
    assert mismatch.status == "BLOCK"
    assert mismatch.payload["source_authority_status"] == "HASH_MISMATCH"

    valid = produce_corporate_event_artifact(
        business_date=BUSINESS_DATE,
        input_paths=no_event_inputs,
        output_path=tmp_path / "valid_hash.json",
        as_of="2026-07-10T00:00:00+00:00",
        expected_source_hashes={"jquants_listed_issues": sha256_file(no_event_inputs.listed_issues_path)},
        require_full_source_coverage=False,
    )
    assert verify_source_hashes(valid.payload)["status"] == "PASS"


def test_phase22_aa_produced_but_not_consumed_detection(tmp_path: Path) -> None:
    inputs = _write_sources(tmp_path)
    result = produce_corporate_event_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=tmp_path / "corporate_event.json",
        as_of="2026-07-10T00:00:00+00:00",
        require_full_source_coverage=False,
    )
    assert produced_but_not_consumed_evidence(result.payload) == {
        "schema_version": "phase22_aa_produced_but_not_consumed_validation.v1",
        "artifact_produced": True,
        "production_consumer_connected": False,
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "legacy_authority_active": True,
        "runtime_switch_performed": False,
        "candidate_behavior_changed": False,
        "opportunity_behavior_changed": False,
        "pm_behavior_changed": False,
        "pending_changed": False,
        "submit_changed": False,
        "status": "PASS",
    }


def _write_sources(root: Path, *, delisting: bool = False, future_row: bool = False) -> CorporateEventInputPaths:
    root.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "Date": "2026-07-10",
            "Code": "10010",
            "CoName": "A",
            "MktNm": "Prime",
            "ListedStatus": "LISTED",
        }
    ]
    if delisting:
        rows.append(
            {
                "Date": "2026-07-10",
                "Code": "20020",
                "CoName": "B",
                "MktNm": "Prime",
                "ListedStatus": "DELISTING_PENDING",
                "DelistingStatus": "ANNOUNCED",
                "FinalTradingDate": "2026-07-31",
            }
        )
    if future_row:
        rows.append(
            {
                "Date": "2026-07-13",
                "Code": "30030",
                "CoName": "C",
                "ListedStatus": "DELISTING_PENDING",
                "DelistingStatus": "ANNOUNCED",
                "FinalTradingDate": "2026-07-31",
            }
        )
    listed_path = root / "listed_issues.parquet"
    pd.DataFrame(rows).to_parquet(listed_path)
    calendar_path = root / "trading_calendar.parquet"
    pd.DataFrame([{"Date": "2026-07-10", "HolDiv": "1"}]).to_parquet(calendar_path)
    return CorporateEventInputPaths(
        listed_issues_path=listed_path,
        trading_calendar_path=calendar_path,
        earnings_schedule_path=root / "earnings_missing.parquet",
        financial_statements_path=root / "statements_missing.parquet",
        corporate_actions_path=root / "corporate_actions_missing.parquet",
    )
