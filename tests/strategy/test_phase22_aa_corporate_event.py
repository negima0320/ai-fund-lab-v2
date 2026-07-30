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
    resolve_default_input_paths,
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
    assert payload["source_coverage_semantics"] == "PARTIAL"
    assert payload["coverage_contract"]["blocking_scope"] == "NONE"
    assert payload["coverage_contract"]["missing_source_treated_as_no_event"] is False
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


def test_phase23_f_partial_coverage_keeps_review_scope_without_no_event_fallback(tmp_path: Path) -> None:
    inputs = _write_sources(tmp_path)
    result = produce_corporate_event_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=tmp_path / "corporate_event.json",
        as_of="2026-07-10T00:00:00+00:00",
        require_full_source_coverage=True,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.payload["coverage_status"] == "PARTIAL"
    assert result.payload["source_coverage_semantics"] == "PARTIAL"
    assert result.payload["coverage_contract"]["blocking_scope"] == "EVENT_SENSITIVE_RULES_ONLY"
    assert result.payload["coverage_contract"]["event_absence_authorized"] is False
    assert result.payload["coverage_contract"]["partial_coverage_may_pass"] is False
    assert result.payload["no_event_semantics"]["event_absence_authorized"] is False


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


def test_phase23_s_default_financial_statement_source_uses_jquants_fins_summary() -> None:
    paths = resolve_default_input_paths(Path(".runtime/operations"))

    assert str(paths.financial_statements_path).endswith("jquants/raw/jquants/fins_summary/data.parquet")


def test_phase23_s_financial_statement_source_materializes_pit_event_and_symbol_coverage(tmp_path: Path) -> None:
    inputs = _write_sources(tmp_path / "sources", financial_statement=True, extra_listed_symbol=True)
    result = produce_corporate_event_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=tmp_path / "corporate_event.json",
        as_of="2026-07-10T00:00:00+00:00",
        require_full_source_coverage=True,
    )

    payload = result.payload
    assert result.status == "REVIEW_REQUIRED"
    assert payload["overall_coverage_status"] == "PARTIAL"
    assert "jquants_financial_statements_not_implemented_or_missing" not in payload["reason_codes"]
    assert "jquants_earnings_schedule_not_implemented_or_missing" in payload["reason_codes"]
    assert any(event["event_type"] == "EARNINGS_ANNOUNCEMENT" for event in payload["events"])
    assert "10010" in payload["known_event_symbols"]
    fact = next(item for item in payload["symbol_event_facts"] if item["security_code"] == "30030")
    assert fact["event_status"] == "UNKNOWN_DUE_TO_MISSING_COVERAGE"
    assert payload["no_event_semantics"]["event_absence_authorized"] is False
    assert payload["pit_validation"]["latest_fallback_used"] is False


def test_phase23_w_financial_statement_source_reference_preserves_disc_no(tmp_path: Path) -> None:
    inputs = _write_sources(tmp_path / "sources", extra_listed_symbol=True)
    statements_path = tmp_path / "sources" / "fins_summary_multi_disc_no.parquet"
    pd.DataFrame(
        [
            {
                "DiscDate": "2026-07-10",
                "Code": "10010",
                "DiscNo": "20260710590001",
                "DocType": "ForecastRevision",
            },
            {
                "DiscDate": "2026-07-10",
                "Code": "10010",
                "DiscNo": "20260710590002",
                "DocType": "ForecastRevision",
            },
        ]
    ).to_parquet(statements_path)
    inputs = CorporateEventInputPaths(
        listed_issues_path=inputs.listed_issues_path,
        trading_calendar_path=inputs.trading_calendar_path,
        corporate_actions_path=inputs.corporate_actions_path,
        earnings_schedule_path=inputs.earnings_schedule_path,
        financial_statements_path=statements_path,
    )

    result = produce_corporate_event_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=tmp_path / "corporate_event.json",
        as_of="2026-07-10T00:00:00+00:00",
        require_full_source_coverage=True,
    )

    financial_events = [event for event in result.payload["events"] if event["reason_codes"] == ["financial_statement_disclosure_fact"]]
    assert len(financial_events) == 2
    assert {event["revision_id"] for event in financial_events} == {"20260710590001", "20260710590002"}
    assert all(event["revision_id"] in event["source_reference"] for event in financial_events)


def test_phase23_t_earnings_calendar_source_materializes_scheduled_event_with_pit_availability(tmp_path: Path) -> None:
    inputs = _write_sources(tmp_path / "sources", earnings_calendar=True, extra_listed_symbol=True)
    result = produce_corporate_event_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=tmp_path / "corporate_event.json",
        as_of="2026-07-10T00:00:00+00:00",
        require_full_source_coverage=True,
    )

    payload = result.payload
    assert result.status == "REVIEW_REQUIRED"
    assert "jquants_earnings_schedule_not_implemented_or_missing" not in payload["reason_codes"]
    assert payload["source_scoped_coverage"]["earnings_calendar_coverage"]["coverage_status"] == "AVAILABLE"
    event = next(event for event in payload["events"] if event["reason_codes"] == ["earnings_calendar_scheduled_date_current_snapshot_exception"])
    assert event["security_code"] == "10010"
    assert event["announcement_date"] is None
    assert event["availability_date"] == BUSINESS_DATE
    assert event["effective_date"] == "2026-07-13"
    assert event["event_status"] == "SCHEDULED"
    assert payload["earnings_calendar_authority_type"] == "CURRENT_SNAPSHOT_CALENDAR_ONLY"
    assert payload["earnings_calendar_exception_scope"] == "earnings_scheduled_date_only"
    assert payload["earnings_calendar_historical_pit_compliant"] is False
    assert payload["approved_non_pit_calendar_exception_used"] is True
    assert payload["pit_validation"]["future_leakage_used"] is False


def test_phase23_z_earnings_calendar_future_snapshot_uses_scheduled_date_only(tmp_path: Path) -> None:
    inputs = _write_sources(tmp_path / "sources", earnings_calendar_future=True)
    result = produce_corporate_event_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=tmp_path / "corporate_event.json",
        as_of="2026-07-10T00:00:00+00:00",
        require_full_source_coverage=False,
    )

    assert result.status == "PASS"
    assert "future_earnings_calendar_row_rejected" not in result.payload["reason_codes"]
    assert any("earnings_calendar_scheduled_date_current_snapshot_exception" in event["reason_codes"] for event in result.payload["events"])
    authority = result.payload["earnings_calendar_authority"]
    assert authority["authority_type"] == "CURRENT_SNAPSHOT_CALENDAR_ONLY"
    assert authority["historical_pit_compliant"] is False
    assert "PublicationDate" in authority["ignored_non_scope_columns_present"]
    assert result.payload["temporal_safety"]["future_leakage_used"] is False


def test_phase23_z_earnings_calendar_without_availability_date_is_allowed_for_schedule_only(tmp_path: Path) -> None:
    inputs = _write_sources(tmp_path / "sources", earnings_calendar_missing_availability=True)
    result = produce_corporate_event_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=tmp_path / "corporate_event.json",
        as_of="2026-07-10T00:00:00+00:00",
        require_full_source_coverage=False,
    )

    assert result.status == "PASS"
    assert "earnings_calendar_availability_date_missing" not in result.payload["reason_codes"]
    assert result.payload["earnings_calendar_authority"]["scheduled_date_column"] == "Date"
    assert result.payload["pit_validation"]["latest_fallback_used"] is False


def test_phase23_s_scoped_coverage_allows_known_no_event_without_full_source_claim(tmp_path: Path) -> None:
    inputs = _write_sources(tmp_path / "sources")
    result = produce_corporate_event_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=tmp_path / "corporate_event.json",
        as_of="2026-07-10T00:00:00+00:00",
        require_full_source_coverage=False,
    )

    payload = result.payload
    assert result.status == "PASS"
    assert payload["coverage_status"] == "AVAILABLE"
    assert payload["known_no_event_symbols"] == ["10010"]
    assert payload["unknown_symbols"] == []
    assert payload["symbol_event_facts"][0]["event_status"] == "KNOWN_NO_EVENT"
    assert payload["no_event_semantics"]["event_absence_authorized"] is True


def test_phase23_y_available_source_scoped_coverage_has_no_missing_reason(tmp_path: Path) -> None:
    inputs = _write_sources(tmp_path / "sources", earnings_calendar=True, financial_statement=True)
    result = produce_corporate_event_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=tmp_path / "corporate_event.json",
        as_of="2026-07-10T00:00:00+00:00",
        require_full_source_coverage=True,
    )

    payload = result.payload
    assert result.status == "PASS"
    assert "jquants_corporate_actions_not_implemented_or_missing" not in payload["reason_codes"]
    for name in ("listing_status_coverage", "earnings_calendar_coverage", "financial_statement_coverage"):
        coverage = payload["source_scoped_coverage"][name]
        assert coverage["coverage_status"] == "AVAILABLE"
        assert not any(reason.endswith("_not_implemented_or_missing") for reason in coverage["reason_codes"])


def test_phase23_y_future_earnings_calendar_snapshot_is_pit_partial_not_known_no_event(tmp_path: Path) -> None:
    inputs = _write_sources(tmp_path / "sources", earnings_calendar_future=True, financial_statement=True, extra_listed_symbol=True)
    result = produce_corporate_event_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=tmp_path / "corporate_event.json",
        as_of="2026-07-10T00:00:00+00:00",
        require_full_source_coverage=True,
    )

    payload = result.payload
    assert result.status == "PASS"
    assert payload["coverage_status"] == "AVAILABLE"
    assert "future_earnings_calendar_row_rejected" not in payload["reason_codes"]
    assert "jquants_corporate_actions_not_implemented_or_missing" not in payload["reason_codes"]
    earnings_coverage = payload["source_scoped_coverage"]["earnings_calendar_coverage"]
    assert earnings_coverage["coverage_status"] == "AVAILABLE"
    assert earnings_coverage["reason_codes"] == []
    fact = next(item for item in payload["symbol_event_facts"] if item["security_code"] == "30030")
    assert fact["event_status"] == "KNOWN_NO_EVENT"
    assert fact["reason_codes"] == []
    assert "30030" in payload["known_no_event_symbols"]
    assert any("earnings_calendar_scheduled_date_current_snapshot_exception" in event["reason_codes"] for event in payload["events"])


def test_phase23_z_earnings_calendar_forbidden_future_content_fails_closed(tmp_path: Path) -> None:
    inputs = _write_sources(tmp_path / "sources", earnings_calendar_forbidden_content=True)
    result = produce_corporate_event_artifact(
        business_date=BUSINESS_DATE,
        input_paths=inputs,
        output_path=tmp_path / "corporate_event.json",
        as_of="2026-07-10T00:00:00+00:00",
        require_full_source_coverage=False,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "earnings_calendar_forbidden_future_columns_present" in result.payload["reason_codes"]
    assert not any(
        "earnings_calendar_scheduled_date_current_snapshot_exception" in event["reason_codes"]
        for event in result.payload["events"]
    )


def _write_sources(
    root: Path,
    *,
    delisting: bool = False,
    future_row: bool = False,
    earnings_calendar: bool = False,
    earnings_calendar_future: bool = False,
    earnings_calendar_missing_availability: bool = False,
    earnings_calendar_forbidden_content: bool = False,
    financial_statement: bool = False,
    full_optional_coverage: bool = False,
    extra_listed_symbol: bool = False,
) -> CorporateEventInputPaths:
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
    if extra_listed_symbol:
        rows.append(
            {
                "Date": "2026-07-10",
                "Code": "30030",
                "CoName": "C",
                "MktNm": "Prime",
                "ListedStatus": "LISTED",
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
    earnings_path = root / "earnings_missing.parquet"
    statements_path = root / "statements_missing.parquet"
    corporate_actions_path = root / "corporate_actions_missing.parquet"
    if financial_statement or full_optional_coverage:
        statements_path = root / "fins_summary.parquet"
        pd.DataFrame(
            [
                {
                    "DiscDate": "2026-07-10",
                    "Code": "10010",
                    "TypeOfDocument": "FYFinancialStatements",
                    "CurrentPeriodEndDate": "2026-06-30",
                }
            ]
            if financial_statement
            else []
        ).to_parquet(statements_path)
    if full_optional_coverage:
        earnings_path = root / "earnings.parquet"
        corporate_actions_path = root / "corporate_actions.parquet"
        pd.DataFrame([]).to_parquet(earnings_path)
        pd.DataFrame([]).to_parquet(corporate_actions_path)
    if earnings_calendar or earnings_calendar_future or earnings_calendar_missing_availability or earnings_calendar_forbidden_content:
        earnings_path = root / "earnings.parquet"
        earnings_rows = [
            {
                "PublicationDate": "2026-07-11" if earnings_calendar_future else "2026-07-09",
                "Date": "2026-07-13",
                "Code": "10010",
                "CoName": "A",
                "FY": "2026",
                "FQ": "1Q",
                "PublicationType": "1",
            }
        ]
        if earnings_calendar_missing_availability:
            earnings_rows[0].pop("PublicationDate")
        if earnings_calendar_forbidden_content:
            earnings_rows[0]["NetSales"] = 100
        pd.DataFrame(earnings_rows).to_parquet(earnings_path)
    return CorporateEventInputPaths(
        listed_issues_path=listed_path,
        trading_calendar_path=calendar_path,
        earnings_schedule_path=earnings_path,
        financial_statements_path=statements_path,
        corporate_actions_path=corporate_actions_path,
    )
