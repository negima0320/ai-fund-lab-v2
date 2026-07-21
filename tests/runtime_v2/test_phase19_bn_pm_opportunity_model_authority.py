from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.accepted_generation_resolver import (
    AcceptedGenerationMember,
    AcceptedGenerationResolution,
)
from ai_fund_lab_v2.runtime_v2.buy_ai.producer import _opportunity_model_authority
from ai_fund_lab_v2.runtime_v2.position_management.producer import validate_position_management_input_contract


BUSINESS_DATE = "2026-07-07"


def test_phase19_bn_opportunity_model_authority_resolves_from_accepted_generation(tmp_path: Path) -> None:
    model_path = tmp_path / "opportunity_model.pkl"
    model_path.write_bytes(b"formal-opportunity-model")
    model_hash = "a" * 64
    resolution = _resolution(model_path, model_hash=model_hash)

    authority = _opportunity_model_authority(
        accepted_generation_resolution=resolution,
        model_path=model_path,
        model_payload={"component": "Opportunity"},
    )

    assert authority["authority_source"] == "Accepted Generation COMMITTED opportunity_member"
    assert authority["accepted_generation_id"] == "accepted-generation-test"
    assert authority["model_version"] == "accepted-generation-test:opportunity:aaaaaaaaaaaaaaaa"
    assert authority["model_hash"] == model_hash
    assert authority["runtime_model_file"] == str(model_path)


def test_phase19_bn_pm_accepts_opportunity_artifact_with_authority_identity(tmp_path: Path) -> None:
    opportunity_path = _opportunity(tmp_path, model_version="accepted-generation-test:opportunity:aaaaaaaaaaaaaaaa")
    contract = _pm_contract(tmp_path, opportunity_path)

    assert contract["pm_input_schema_status"] == "READY"
    assert contract["pm_missing_fields"] == []


def test_phase19_bn_pm_rejects_model_authority_mismatch(tmp_path: Path) -> None:
    opportunity_path = _opportunity(
        tmp_path,
        model_version="accepted-generation-test:opportunity:bbbbbbbbbbbbbbbb",
    )
    contract = _pm_contract(tmp_path, opportunity_path)

    assert contract["pm_input_schema_status"] == "REVIEW_REQUIRED"
    assert "opportunity.model_authority.model_version_mismatch" in contract["pm_missing_fields"]


def test_phase19_bn_pm_rejects_missing_model_identity(tmp_path: Path) -> None:
    opportunity_path = _opportunity(tmp_path, model_version="", include_authority=False)
    contract = _pm_contract(tmp_path, opportunity_path)

    assert contract["pm_input_schema_status"] == "REVIEW_REQUIRED"
    assert "opportunity.model_version" in contract["pm_missing_fields"]


def _resolution(model_path: Path, *, model_hash: str) -> AcceptedGenerationResolution:
    return AcceptedGenerationResolution(
        resolution_status="RESOLVED_COMMITTED",
        generation_id="accepted-generation-test",
        bundle_manifest_path=str(model_path.parent / "accepted_generation_manifest.json"),
        authority_decision="APPROVED",
        transaction_state="COMMITTED",
        effective_from="2026-07-20T00:00:00+09:00",
        accepted_at="2026-07-20T00:00:00+09:00",
        aggregate_hash="b" * 64,
        candidate_member=None,
        opportunity_member=AcceptedGenerationMember(
            role="opportunity",
            artifact_path=str(model_path),
            model_hash=model_hash,
            schema_hash="schema-hash",
            source_generation_id="candidate-generation",
            component_revision="opportunity-revision",
        ),
        calibration_member=None,
        runtime_baseline={},
        freshness_metadata={},
        rollback_reference={},
        source_evidence={},
        block_reason="",
        review_required=False,
        reason_codes=(),
    )


def _pm_contract(tmp_path: Path, opportunity_path: Path) -> dict:
    return validate_position_management_input_contract(
        current={
            "as_of": BUSINESS_DATE,
            "updated_at": BUSINESS_DATE + "T00:00:00Z",
            "temporal_schema_version": "runtime_v2_current_temporal_v1",
            "current_position_status": "READY",
            "current_valuation_status": "READY",
            "positions": [
                {
                    "symbol": "10010",
                    "quantity": 100,
                    "average_price": 1000,
                    "current_price": 1010,
                    "peak_return": 0.02,
                    "as_of": BUSINESS_DATE,
                    "source": "fixture_current",
                }
            ],
            "cash": 1000000,
        },
        current_path=tmp_path / "current.json",
        runtime_state={"state": "CURRENT_STATE_LOADED"},
        runtime_state_path=tmp_path / "current_state.json",
        business_date=BUSINESS_DATE,
        feature_date=BUSINESS_DATE,
        opportunity_path=opportunity_path,
        feature_path=_feature(tmp_path),
    )


def _feature(tmp_path: Path) -> Path:
    path = tmp_path / "position_feature_input.csv"
    path.write_text(
        "target_date,code,market_price,return_1d,return_5d,return_20d,volatility_20d,holding_days,unrealized_return,quantity,avg_price\n"
        f"{BUSINESS_DATE},10010,1010,0.01,0.01,0.01,0.02,1,0.01,100,1000\n",
        encoding="utf-8",
    )
    return path


def _opportunity(tmp_path: Path, *, model_version: str, include_authority: bool = True) -> Path:
    payload = {
        "schema_name": "runtime_v2_buy_opportunity_ranking",
        "schema_version": "runtime_v2_opportunity_ranking_v1",
        "artifact_role": "BUY_OPPORTUNITY_RANKING",
        "producer": "Runtime v2 BUY AI Producer",
        "producer_version": "candidate_opportunity_ai_regular_path_v1",
        "business_date": BUSINESS_DATE,
        "feature_date": BUSINESS_DATE,
        "runtime_id": "runtime-v2-buy-ai-test",
        "model_version": model_version,
        "generated_at": BUSINESS_DATE + "T00:00:00Z",
        "status": "PASS",
        "ranking_count": 1,
        "rankings": [
            {
                "target_date": BUSINESS_DATE,
                "code": "10010",
                "symbol": "10010",
                "expected_edge_score": 0.07,
                "opportunity_score": 0.07,
                "buy_rank": 1,
                "rank": 1,
                "downside_risk_score": 0.35,
                "candidate_score": 0.8,
                "candidate_rank": 10,
                "reason": "fixture",
            }
        ],
    }
    if include_authority:
        payload["model_authority"] = {
            "schema_version": "runtime_v2_opportunity_model_authority_v1",
            "authority_source": "Accepted Generation COMMITTED opportunity_member",
            "resolution_status": "RESOLVED_COMMITTED",
            "accepted_generation_id": "accepted-generation-test",
            "model_version": "accepted-generation-test:opportunity:aaaaaaaaaaaaaaaa",
            "model_identity": "accepted-generation-test:opportunity:aaaaaaaaaaaaaaaa",
            "model_component": "opportunity",
            "model_file": str(tmp_path / "opportunity_model.pkl"),
            "runtime_model_file": str(tmp_path / "opportunity_model.pkl"),
            "model_ref": "reports/opportunity.json",
            "model_hash": "a" * 64,
            "runtime_model_hash": "a" * 64,
            "hash_match": True,
            "authority_hash": "b" * 64,
        }
    path = tmp_path / "opportunity_rankings.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
