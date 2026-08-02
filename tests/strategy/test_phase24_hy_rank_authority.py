from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.strategy import portfolio_construction, shadow_runtime


def _adapt(rows: list[dict[str, object]], *, kind: str = "opportunity") -> list[dict[str, object]]:
    return shadow_runtime._candidate_downstream_rows(
        rows,
        payload={"business_date": "2022-07-25", "feature_date": "2022-07-25"},
        path=Path(".runtime/runtime_state/buy_ai/2022-07-25/opportunity_rankings.json"),
        source_hash="sha256:phase24hy",
        business_date="2022-07-25",
        kind=kind,
    )


def test_opportunity_row_uses_buy_rank_not_candidate_rank() -> None:
    rows = _adapt(
        [
            {
                "security_code": "66590",
                "business_date": "2022-07-25",
                "feature_date": "2022-07-25",
                "candidate_rank": 1,
                "buy_rank": 4,
                "expected_edge_score": 0.91,
            }
        ]
    )

    row = rows[0]
    assert row["rank"] == 4
    assert row["opportunity_buy_rank"] == 4
    assert row["canonical_opportunity_buy_rank"] == 4
    assert row["rank_authority_status"] == "PASS"
    assert row["rank_authority_field"] == "buy_rank"
    assert row["eligibility_status"] == "ELIGIBLE"


def test_opportunity_row_missing_buy_rank_rejects_without_candidate_fallback() -> None:
    rows = _adapt(
        [
            {
                "security_code": "66590",
                "business_date": "2022-07-25",
                "feature_date": "2022-07-25",
                "candidate_rank": 1,
                "expected_edge_score": 0.91,
            }
        ]
    )

    row = rows[0]
    assert row["rank"] is None
    assert row["opportunity_buy_rank"] is None
    assert row["rank_authority_status"] == "REVIEW_REQUIRED"
    assert row["eligibility_status"] == "REJECTED"
    assert row["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    assert row["rejection_reason"] == "opportunity_rank_authority_missing_or_invalid"


def test_opportunity_row_rank_alias_conflict_rejects() -> None:
    rows = _adapt(
        [
            {
                "security_code": "66590",
                "business_date": "2022-07-25",
                "feature_date": "2022-07-25",
                "buy_rank": 4,
                "rank": 7,
                "expected_edge_score": 0.91,
            }
        ]
    )

    row = rows[0]
    assert row["rank"] is None
    assert row["rank_authority_status"] == "REVIEW_REQUIRED"
    assert row["eligibility_status"] == "REJECTED"
    assert str(row["rejection_reason"]).startswith("opportunity_rank_authority_conflict")


def test_candidate_row_uses_candidate_rank_authority() -> None:
    rows = _adapt(
        [
            {
                "security_code": "72030",
                "business_date": "2022-07-25",
                "feature_date": "2022-07-25",
                "candidate_rank": 2,
                "buy_rank": 9,
                "candidate_score": 0.7,
            }
        ],
        kind="candidate",
    )

    row = rows[0]
    assert row["rank"] == 2
    assert row["candidate_rank_authority"] == "candidate_rank"
    assert row["rank_authority"] == "CANDIDATE_RANK_AUTHORITY"
    assert row["opportunity_buy_rank"] is None


def test_portfolio_member_materializes_opportunity_rank_lineage() -> None:
    opportunity = _adapt(
        [
            {
                "security_code": "66590",
                "business_date": "2022-07-25",
                "feature_date": "2022-07-25",
                "buy_rank": 4,
                "expected_edge_score": 0.91,
            }
        ]
    )[0]

    member = portfolio_construction._member(
        business_date="2022-07-25",
        security_code="66590",
        current_position=False,
        membership_intent="ADD_CANDIDATE",
        weight_intent="INCREASE",
        construction_priority=1,
        candidate=None,
        opportunity=opportunity,
        pm=None,
        reason_codes=["opportunity_selected"],
    )

    assert member["input_opportunity_rank"] == 4
    assert member["opportunity_buy_rank"] == 4
    assert member["input_opportunity_rank_authority"] == "OPPORTUNITY_BUY_RANK_AUTHORITY"
    assert member["input_opportunity_rank_source_path"].endswith("opportunity_rankings.json")
    assert member["input_opportunity_rank_source_hash"] == "sha256:phase24hy"
    assert member["input_opportunity_row_id"]
    assert member["input_opportunity_row_authority_hash"]
