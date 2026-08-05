from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.strategy.position_intent import (
    PositionIntentSchemaError,
    build_position_intent_payload,
    default_runtime_artifact_path,
    produce_position_intent_artifact,
    validate_position_intent_artifact,
)


def test_phase27_d2a_pm_decisions_map_to_shadow_position_intents(tmp_path: Path) -> None:
    pm_path = _write_pm(tmp_path)

    payload, evidence = build_position_intent_payload(
        business_date="2026-07-15",
        run_id="run-d2a",
        accepted_generation="generation-a",
        pm_artifact_path=pm_path,
        current_artifact_path=_write_json(tmp_path / "current.json", {"business_date": "2026-07-15"}),
    )

    assert payload["schema_version"] == "position_intent.v1"
    assert payload["authority_mode"] == "SHADOW"
    assert payload["decision_effect"] == "NONE"
    assert payload["summary"]["decision_effect_zero"] is True
    assert evidence["consumer_connection"] == "NONE_IN_D2_A"
    assert [row["proposed_position_intent"] for row in payload["intents"]] == ["ADD", "HOLD", "REDUCE", "EXIT"]
    assert [row["pm_intent"] for row in payload["intents"]] == ["ADD", "HOLD", "REDUCE", "EXIT"]
    for row in payload["intents"]:
        assert row["authority_mode"] == "SHADOW"
        assert row["decision_effect"] == "NONE"
        assert row["accepted_generation"] == "generation-a"
        assert row["business_date"] == "2026-07-15"
        assert row["lineage"]["source_pm_artifact"] == str(pm_path)
        assert row["lineage"]["source_pm_decision_id"].startswith("pm-")
        assert "target_weight_candidate" not in row
        assert "quantity_delta_candidate" not in row
        assert "planning_intent" not in row
        assert "pending_item_id" not in row
    assert validate_position_intent_artifact(payload)["status"] == "PASS"


def test_phase27_d2a_produce_materializes_run_scoped_shadow_artifact(tmp_path: Path) -> None:
    pm_path = _write_pm(tmp_path)
    result = produce_position_intent_artifact(
        runtime_root=tmp_path,
        business_date="2026-07-15",
        run_id="run-d2a",
        accepted_generation="generation-a",
        pm_artifact_path=pm_path,
    )

    expected = default_runtime_artifact_path(tmp_path, "2026-07-15")
    assert Path(result.artifact_path) == expected
    assert expected.is_file()
    written = json.loads(expected.read_text())
    assert written["artifact_hash"] == result.artifact_hash
    assert written["decision_effect"] == "NONE"
    assert written["summary"]["intent_counts"] == {"ADD": 1, "EXIT": 1, "HOLD": 1, "REDUCE": 1}


def test_phase27_d2a_missing_pm_artifact_is_review_required_without_fallback(tmp_path: Path) -> None:
    payload, _ = build_position_intent_payload(
        business_date="2026-07-15",
        run_id="run-d2a",
        accepted_generation="generation-a",
        pm_artifact_path=tmp_path / "missing_pm.json",
    )

    assert payload["artifact_status"] == "REVIEW_REQUIRED"
    assert payload["intents"] == []
    assert "PM_ARTIFACT_MISSING" in payload["reason_codes"]
    assert validate_position_intent_artifact(payload)["status"] == "PASS"


def test_phase27_d2a_pm_business_date_mismatch_is_review_required(tmp_path: Path) -> None:
    pm_path = _write_pm(tmp_path, business_date="2026-07-14")
    payload, _ = build_position_intent_payload(
        business_date="2026-07-15",
        run_id="run-d2a",
        accepted_generation="generation-a",
        pm_artifact_path=pm_path,
    )

    assert payload["artifact_status"] == "REVIEW_REQUIRED"
    assert payload["intents"] == []
    assert "PM_ARTIFACT_BUSINESS_DATE_MISMATCH" in payload["reason_codes"]


def test_phase27_d2a_accepted_generation_mismatch_is_review_required(tmp_path: Path) -> None:
    pm_path = _write_pm(tmp_path)
    payload, _ = build_position_intent_payload(
        business_date="2026-07-15",
        run_id="run-d2a",
        accepted_generation="generation-b",
        pm_artifact_path=pm_path,
    )

    assert payload["artifact_status"] == "REVIEW_REQUIRED"
    assert payload["intents"] == []
    assert "ACCEPTED_GENERATION_MISMATCH" in payload["reason_codes"]


def test_phase27_d2a_duplicate_dedup_key_blocks_validation(tmp_path: Path) -> None:
    pm_path = _write_pm(
        tmp_path,
        decisions=[
            _pm_decision("7203", "ADD", campaign_id="campaign-1"),
            _pm_decision("7203", "HOLD", campaign_id="campaign-1"),
        ],
    )
    payload, _ = build_position_intent_payload(
        business_date="2026-07-15",
        run_id="run-d2a",
        accepted_generation="generation-a",
        pm_artifact_path=pm_path,
    )

    assert payload["artifact_status"] == "BLOCK"
    assert "DUPLICATE_DEDUP_KEY" in payload["reason_codes"]
    with pytest.raises(PositionIntentSchemaError):
        validate_position_intent_artifact(payload)


def test_phase27_d2a_buy_candidates_remain_unresolved_shadow_when_incremental_missing(tmp_path: Path) -> None:
    opportunity_path = _write_json(
        tmp_path / "opportunity.json",
        {
            "business_date": "2026-07-15",
            "opportunities": [
                {
                    "symbol": "9984",
                    "opportunity_id": "opp-9984",
                    "buy_rank": 1,
                    "expected_edge_score": 0.42,
                }
            ],
        },
    )
    payload, _ = build_position_intent_payload(
        business_date="2026-07-15",
        run_id="run-d2a",
        accepted_generation="generation-a",
        pm_artifact_path=None,
        opportunity_artifact_path=opportunity_path,
    )

    row = payload["intents"][0]
    assert row["symbol"] == "9984"
    assert row["proposed_position_intent"] == "UNRESOLVED"
    assert row["current_position_state"] == "NO_POSITION"
    assert "INCREMENTAL_ELIGIBILITY_NOT_AVAILABLE" in row["intent_reason_codes"]
    assert row["review_status"] == "REVIEW_REQUIRED"
    assert validate_position_intent_artifact(payload)["status"] == "PASS"


def test_phase27_d2a_schema_rejects_downstream_authority_fields(tmp_path: Path) -> None:
    payload, _ = build_position_intent_payload(
        business_date="2026-07-15",
        run_id="run-d2a",
        accepted_generation="generation-a",
        pm_artifact_path=_write_pm(tmp_path),
    )
    payload["intents"][0]["quantity_delta_candidate"] = 100
    with pytest.raises(PositionIntentSchemaError):
        validate_position_intent_artifact(payload)


def _write_pm(
    tmp_path: Path,
    *,
    business_date: str = "2026-07-15",
    decisions: list[dict[str, object]] | None = None,
) -> Path:
    return _write_json(
        tmp_path / "position_management_decisions.json",
        {
            "schema_version": "runtime_v2_position_management_decision_v1",
            "business_date": business_date,
            "accepted_generation": "generation-a",
            "decisions": decisions
            or [
                _pm_decision("7203", "ADD", campaign_id="campaign-add"),
                _pm_decision("6758", "HOLD", campaign_id="campaign-hold"),
                _pm_decision("9984", "REDUCE", campaign_id="campaign-reduce"),
                _pm_decision("8306", "EXIT", campaign_id="campaign-exit"),
            ],
        },
    )


def _pm_decision(symbol: str, decision: str, *, campaign_id: str) -> dict[str, object]:
    return {
        "decision_id": f"pm-2026-07-15-{symbol}-{decision.lower()}",
        "business_date": "2026-07-15",
        "symbol": symbol,
        "decision": decision,
        "position_campaign_id": campaign_id,
        "runtime_position_quantity": 100,
        "runtime_action": "NO_SELL_ORDER_ADD_OUT_OF_SELL_SCOPE" if decision == "ADD" else "NO_SELL_ORDER",
        "reason": f"{decision} fixture",
    }


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return path
