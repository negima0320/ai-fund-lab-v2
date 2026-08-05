from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.strategy.position_intent import produce_position_intent_artifact
from ai_fund_lab_v2.strategy.position_sizing_plan import (
    PositionSizingPlanSchemaError,
    build_position_sizing_plan_payload,
    produce_position_sizing_plan_artifact,
    validate_position_sizing_plan_artifact,
)
from ai_fund_lab_v2.strategy.target_portfolio_decision import produce_target_portfolio_decision_artifact


def test_phase27_d2d_maps_existing_position_intents_to_shadow_quantity_deltas(tmp_path: Path) -> None:
    target_path = _target_portfolio_decision(tmp_path)

    payload, evidence = build_position_sizing_plan_payload(
        business_date="2026-07-15",
        run_id="run-d2d",
        accepted_generation="generation-a",
        target_portfolio_decision_artifact_path=target_path,
    )

    assert payload["schema_version"] == "position_sizing_plan.v1"
    assert payload["authority_mode"] == "SHADOW"
    assert payload["decision_effect"] == "NONE"
    assert evidence["formal_position_sizing_replaced"] is False
    assert evidence["runtime_planning_connection"] == "NONE_IN_D2_D"
    assert evidence["pending_connection"] == "NONE_IN_D2_D"
    rows = {row["source_pm_intent"]: row for row in payload["positions"]}
    assert _quantities(rows["ADD"]) == (100, 200, 100, "POSITIVE_DELTA", "POSITIVE_DELTA_SIZED")
    assert _quantities(rows["HOLD"]) == (100, 100, 0, "ZERO_DELTA", "ZERO_DELTA_SIZED")
    assert _quantities(rows["REDUCE"]) == (200, 100, -100, "NEGATIVE_PARTIAL_DELTA", "NEGATIVE_DELTA_SIZED")
    assert _quantities(rows["EXIT"]) == (100, 0, -100, "FULL_NEGATIVE_DELTA", "FULL_EXIT_DELTA_SIZED")
    for row in payload["positions"]:
        assert row["decision_effect"] == "NONE"
        assert "planning_intent" not in row
        assert "pending_item_id" not in row
        assert "submit_command" not in row
    assert validate_position_sizing_plan_artifact(payload)["status"] == "PASS"


def test_phase27_d2d_materializes_position_sizing_plan_shadow_artifact(tmp_path: Path) -> None:
    result = produce_position_sizing_plan_artifact(
        runtime_root=tmp_path,
        business_date="2026-07-15",
        run_id="run-d2d",
        accepted_generation="generation-a",
        target_portfolio_decision_artifact_path=_target_portfolio_decision(tmp_path),
    )

    written = json.loads(Path(result.artifact_path).read_text())
    assert Path(result.artifact_path).name == "position_sizing_plan.json"
    assert written["artifact_hash"] == result.artifact_hash
    assert written["summary"]["delta_classification_counts"] == {
        "FULL_NEGATIVE_DELTA": 1,
        "NEGATIVE_PARTIAL_DELTA": 1,
        "POSITIVE_DELTA": 1,
        "ZERO_DELTA": 1,
    }
    assert written["summary"]["runtime_connected"] is False
    assert written["summary"]["pending_decided"] is False
    assert written["summary"]["submit_decided"] is False


def test_phase27_d2d_sizing_cannot_change_pm_add_to_hold(tmp_path: Path) -> None:
    target_path = _target_portfolio_decision(tmp_path, decisions=[_pm("7203", "ADD", "campaign-add", quantity=100)])
    payload, _ = build_position_sizing_plan_payload(
        business_date="2026-07-15",
        run_id="run-d2d",
        accepted_generation="generation-a",
        target_portfolio_decision_artifact_path=target_path,
    )

    row = payload["positions"][0]
    assert row["source_pm_intent"] == "ADD"
    assert row["quantity_delta_candidate"] > 0
    row["quantity_delta_candidate"] = 0
    row["target_quantity_candidate"] = row["current_quantity"]
    row["delta_classification"] = "ZERO_DELTA"
    row["sizing_status"] = "ZERO_DELTA_SIZED"
    with pytest.raises(PositionSizingPlanSchemaError):
        validate_position_sizing_plan_artifact(payload)


def test_phase27_d2d_reduce_requires_negative_partial_or_reduce_not_sized(tmp_path: Path) -> None:
    target_path = _target_portfolio_decision(tmp_path, decisions=[_pm("9984", "REDUCE", "campaign-reduce", quantity=100)])
    payload, _ = build_position_sizing_plan_payload(
        business_date="2026-07-15",
        run_id="run-d2d",
        accepted_generation="generation-a",
        target_portfolio_decision_artifact_path=target_path,
    )

    row = payload["positions"][0]
    assert row["source_pm_intent"] == "REDUCE"
    assert row["sizing_status"] == "REDUCE_NOT_SIZED"
    assert row["quantity_delta_candidate"] is None
    assert row["delta_classification"] == "NOT_SIZED"
    assert "PARTIAL_REDUCE_REQUIRES_REMAINING_QUANTITY" in row["reason_codes"]
    assert validate_position_sizing_plan_artifact(payload)["status"] == "PASS"


def test_phase27_d2d_schema_rejects_runtime_and_pending_fields(tmp_path: Path) -> None:
    payload, _ = build_position_sizing_plan_payload(
        business_date="2026-07-15",
        run_id="run-d2d",
        accepted_generation="generation-a",
        target_portfolio_decision_artifact_path=_target_portfolio_decision(tmp_path),
    )
    payload["positions"][0]["planning_intent"] = "BUY_ADD"
    payload["positions"][0]["pending_item_id"] = "opi-forbidden"
    with pytest.raises(PositionSizingPlanSchemaError):
        validate_position_sizing_plan_artifact(payload)


def test_phase27_d2d_target_portfolio_generation_mismatch_blocks(tmp_path: Path) -> None:
    payload, _ = build_position_sizing_plan_payload(
        business_date="2026-07-15",
        run_id="run-d2d",
        accepted_generation="generation-b",
        target_portfolio_decision_artifact_path=_target_portfolio_decision(tmp_path),
    )

    assert payload["artifact_status"] == "BLOCK"
    assert "ACCEPTED_GENERATION_MISMATCH" in payload["reason_codes"]
    assert validate_position_sizing_plan_artifact(payload)["status"] == "PASS"


def _quantities(row: dict[str, object]) -> tuple[object, object, object, object, object]:
    return (
        row["current_quantity"],
        row["target_quantity_candidate"],
        row["quantity_delta_candidate"],
        row["delta_classification"],
        row["sizing_status"],
    )


def _target_portfolio_decision(tmp_path: Path, decisions: list[dict[str, object]] | None = None) -> Path:
    pm_path = _write_json(
        tmp_path / "pm.json",
        {
            "schema_version": "runtime_v2_position_management_decision_v1",
            "business_date": "2026-07-15",
            "accepted_generation": "generation-a",
            "decisions": decisions
            or [
                _pm("7203", "ADD", "campaign-add", quantity=100),
                _pm("6758", "HOLD", "campaign-hold", quantity=100),
                _pm("9984", "REDUCE", "campaign-reduce", quantity=200),
                _pm("8306", "EXIT", "campaign-exit", quantity=100),
            ],
        },
    )
    intent = produce_position_intent_artifact(
        runtime_root=tmp_path,
        business_date="2026-07-15",
        run_id="run-d2d",
        accepted_generation="generation-a",
        pm_artifact_path=pm_path,
        output_path=tmp_path / "position_intent.json",
    )
    target = produce_target_portfolio_decision_artifact(
        runtime_root=tmp_path,
        business_date="2026-07-15",
        run_id="run-d2d",
        accepted_generation="generation-a",
        position_intent_artifact_path=intent.artifact_path,
        current_artifact_path=_current(tmp_path, decisions or json.loads(pm_path.read_text())["decisions"]),
        output_path=tmp_path / "target_portfolio_decision.json",
    )
    return Path(target.artifact_path)


def _pm(symbol: str, decision: str, campaign: str, *, quantity: int) -> dict[str, object]:
    return {
        "decision_id": f"pm-2026-07-15-{symbol}-{decision.lower()}",
        "business_date": "2026-07-15",
        "symbol": symbol,
        "decision": decision,
        "position_campaign_id": campaign,
        "runtime_position_quantity": quantity,
    }


def _current(tmp_path: Path, decisions: list[dict[str, object]]) -> Path:
    return _write_json(
        tmp_path / "current.json",
        {
            "business_date": "2026-07-15",
            "positions": [
                {
                    "symbol": item["symbol"],
                    "position_campaign_id": item["position_campaign_id"],
                    "quantity": item["runtime_position_quantity"],
                    "current_weight": 0.1,
                }
                for item in decisions
            ],
        },
    )


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return path
