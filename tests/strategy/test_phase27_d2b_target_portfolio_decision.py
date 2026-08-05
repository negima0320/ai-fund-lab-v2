from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.strategy.position_intent import produce_position_intent_artifact
from ai_fund_lab_v2.strategy.target_portfolio_decision import (
    TargetPortfolioDecisionSchemaError,
    build_target_portfolio_decision_payload,
    produce_target_portfolio_decision_artifact,
    validate_target_portfolio_decision_artifact,
)


def test_phase27_d2b_maps_pm_intents_to_shadow_target_resolution(tmp_path: Path) -> None:
    intent_path = _position_intent(tmp_path)
    current_path = _current(tmp_path)

    payload, evidence = build_target_portfolio_decision_payload(
        business_date="2026-07-15",
        run_id="run-d2b",
        accepted_generation="generation-a",
        position_intent_artifact_path=intent_path,
        current_artifact_path=current_path,
    )

    assert payload["schema_version"] == "target_portfolio_decision.v1"
    assert payload["authority_mode"] == "SHADOW"
    assert payload["decision_effect"] == "NONE"
    assert evidence["existing_portfolio_construction_replaced"] is False
    assert evidence["downstream_connection"] == "NONE_IN_D2_B"
    rows = {row["source_position_intent"]: row for row in payload["decisions"]}
    assert _triplet(rows["ADD"]) == ("RETAIN", "INCREASE", "POSITIVE_DELTA_REQUIRED")
    assert _triplet(rows["HOLD"]) == ("RETAIN", "MAINTAIN", "ZERO_DELTA_EXPECTED")
    assert _triplet(rows["REDUCE"]) == ("RETAIN", "DECREASE", "NEGATIVE_DELTA_REQUIRED")
    assert _triplet(rows["EXIT"]) == ("REMOVE", "REMOVE", "FULL_REMOVAL_REQUIRED")
    for row in payload["decisions"]:
        assert row["resolution_status"] == "PASS"
        assert row["decision_effect"] == "NONE"
        assert "target_weight_candidate" not in row
        assert "quantity_delta_candidate" not in row
        assert "pending_item_id" not in row
    assert validate_target_portfolio_decision_artifact(payload)["status"] == "PASS"


def test_phase27_d2b_materializes_shadow_target_portfolio_decision(tmp_path: Path) -> None:
    result = produce_target_portfolio_decision_artifact(
        runtime_root=tmp_path,
        business_date="2026-07-15",
        run_id="run-d2b",
        accepted_generation="generation-a",
        position_intent_artifact_path=_position_intent(tmp_path),
        current_artifact_path=_current(tmp_path),
    )

    path = Path(result.artifact_path)
    assert path.name == "target_portfolio_decision.json"
    written = json.loads(path.read_text())
    assert written["artifact_hash"] == result.artifact_hash
    assert written["summary"]["target_direction_counts"] == {
        "DECREASE": 1,
        "INCREASE": 1,
        "MAINTAIN": 1,
        "REMOVE": 1,
    }


@pytest.mark.parametrize("intent", ["ADD", "HOLD", "REDUCE", "EXIT"])
def test_phase27_d2b_current_holding_required_for_existing_position_intents(tmp_path: Path, intent: str) -> None:
    intent_path = _position_intent(tmp_path, decisions=[_pm("7203", intent, "campaign-1")])
    current_path = _current(tmp_path, positions=[])
    payload, _ = build_target_portfolio_decision_payload(
        business_date="2026-07-15",
        run_id="run-d2b",
        accepted_generation="generation-a",
        position_intent_artifact_path=intent_path,
        current_artifact_path=current_path,
    )

    row = payload["decisions"][0]
    assert row["resolution_status"] == "REVIEW_REQUIRED"
    assert f"{intent}_WITHOUT_CURRENT_HOLDING" in row["resolution_reason_codes"]
    assert "current_position" in row["missing_required_inputs"]
    assert validate_target_portfolio_decision_artifact(payload)["status"] == "PASS"


def test_phase27_d2b_duplicate_intent_blocks_validation(tmp_path: Path) -> None:
    intent_path = _duplicate_position_intent(tmp_path)
    current_path = _current(tmp_path, positions=[_pos("7203", "campaign-1")])
    payload, _ = build_target_portfolio_decision_payload(
        business_date="2026-07-15",
        run_id="run-d2b",
        accepted_generation="generation-a",
        position_intent_artifact_path=intent_path,
        current_artifact_path=current_path,
    )

    assert payload["artifact_status"] == "BLOCK"
    assert "DUPLICATE_DEDUP_KEY" in payload["reason_codes"]
    with pytest.raises(TargetPortfolioDecisionSchemaError):
        validate_target_portfolio_decision_artifact(payload)


def test_phase27_d2b_position_intent_date_mismatch_blocks(tmp_path: Path) -> None:
    intent_path = _position_intent(tmp_path)
    payload = json.loads(intent_path.read_text())
    payload["business_date"] = "2026-07-14"
    intent_path.write_text(json.dumps(payload))
    out, _ = build_target_portfolio_decision_payload(
        business_date="2026-07-15",
        run_id="run-d2b",
        accepted_generation="generation-a",
        position_intent_artifact_path=intent_path,
        current_artifact_path=_current(tmp_path),
    )

    assert out["artifact_status"] == "BLOCK"
    assert "POSITION_INTENT_BUSINESS_DATE_MISMATCH" in out["reason_codes"]


def test_phase27_d2b_accepted_generation_mismatch_blocks(tmp_path: Path) -> None:
    payload, _ = build_target_portfolio_decision_payload(
        business_date="2026-07-15",
        run_id="run-d2b",
        accepted_generation="generation-b",
        position_intent_artifact_path=_position_intent(tmp_path),
        current_artifact_path=_current(tmp_path),
    )

    assert payload["artifact_status"] == "BLOCK"
    assert "ACCEPTED_GENERATION_MISMATCH" in payload["reason_codes"]


def test_phase27_d2b_campaign_mismatch_reviews(tmp_path: Path) -> None:
    payload, _ = build_target_portfolio_decision_payload(
        business_date="2026-07-15",
        run_id="run-d2b",
        accepted_generation="generation-a",
        position_intent_artifact_path=_position_intent(tmp_path, decisions=[_pm("7203", "ADD", "campaign-a")]),
        current_artifact_path=_current(tmp_path, positions=[_pos("7203", "campaign-b")]),
    )

    row = payload["decisions"][0]
    assert row["resolution_status"] == "REVIEW_REQUIRED"
    assert "POSITION_CAMPAIGN_MISMATCH" in row["resolution_reason_codes"]


def test_phase27_d2b_missing_current_reviews_without_fallback(tmp_path: Path) -> None:
    payload, _ = build_target_portfolio_decision_payload(
        business_date="2026-07-15",
        run_id="run-d2b",
        accepted_generation="generation-a",
        position_intent_artifact_path=_position_intent(tmp_path),
        current_artifact_path=tmp_path / "missing_current.json",
    )

    assert payload["artifact_status"] == "REVIEW_REQUIRED"
    assert "CURRENT_ARTIFACT_MISSING" in payload["reason_codes"]
    assert all(row["review_status"] == "REVIEW_REQUIRED" for row in payload["decisions"])


def test_phase27_d2b_schema_rejects_downstream_fields(tmp_path: Path) -> None:
    payload, _ = build_target_portfolio_decision_payload(
        business_date="2026-07-15",
        run_id="run-d2b",
        accepted_generation="generation-a",
        position_intent_artifact_path=_position_intent(tmp_path),
        current_artifact_path=_current(tmp_path),
    )
    payload["decisions"][0]["quantity_delta_candidate"] = 100
    with pytest.raises(TargetPortfolioDecisionSchemaError):
        validate_target_portfolio_decision_artifact(payload)


def _triplet(row: dict[str, object]) -> tuple[object, object, object]:
    return (row["target_membership_decision"], row["target_direction"], row["target_weight_effect"])


def _position_intent(tmp_path: Path, decisions: list[dict[str, object]] | None = None) -> Path:
    pm_path = _write_json(
        tmp_path / "pm.json",
        {
            "schema_version": "runtime_v2_position_management_decision_v1",
            "business_date": "2026-07-15",
            "accepted_generation": "generation-a",
            "decisions": decisions
            or [
                _pm("7203", "ADD", "campaign-add"),
                _pm("6758", "HOLD", "campaign-hold"),
                _pm("9984", "REDUCE", "campaign-reduce"),
                _pm("8306", "EXIT", "campaign-exit"),
            ],
        },
    )
    result = produce_position_intent_artifact(
        runtime_root=tmp_path,
        business_date="2026-07-15",
        run_id="run-d2b",
        accepted_generation="generation-a",
        pm_artifact_path=pm_path,
        output_path=tmp_path / "position_intent.json",
    )
    return Path(result.artifact_path)


def _duplicate_position_intent(tmp_path: Path) -> Path:
    intent_path = _position_intent(tmp_path, decisions=[_pm("7203", "ADD", "campaign-1")])
    payload = json.loads(intent_path.read_text())
    duplicate = dict(payload["intents"][0])
    duplicate["pm_intent"] = "HOLD"
    duplicate["source_position_intent"] = "HOLD"
    duplicate["proposed_position_intent"] = "HOLD"
    payload["intents"].append(duplicate)
    intent_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return intent_path


def _current(tmp_path: Path, positions: list[dict[str, object]] | None = None) -> Path:
    return _write_json(
        tmp_path / "current.json",
        {
            "business_date": "2026-07-15",
            "positions": positions
            if positions is not None
            else [
                _pos("7203", "campaign-add"),
                _pos("6758", "campaign-hold"),
                _pos("9984", "campaign-reduce"),
                _pos("8306", "campaign-exit"),
            ],
        },
    )


def _pm(symbol: str, decision: str, campaign: str) -> dict[str, object]:
    return {
        "decision_id": f"pm-2026-07-15-{symbol}-{decision.lower()}",
        "business_date": "2026-07-15",
        "symbol": symbol,
        "decision": decision,
        "position_campaign_id": campaign,
        "runtime_position_quantity": 100,
    }


def _pos(symbol: str, campaign: str) -> dict[str, object]:
    return {"symbol": symbol, "position_campaign_id": campaign, "quantity": 100, "current_weight": 0.1}


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return path
