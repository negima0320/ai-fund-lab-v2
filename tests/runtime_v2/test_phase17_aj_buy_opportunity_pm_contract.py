from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.runtime_v2.position_management.producer import (
    validate_position_management_input_contract,
    _pm_opportunity_contract,
    _write_pm_opportunity_context,
)


BUSINESS_DATE = "2026-07-07"
def test_buy_opportunity_context_writer_maps_runtime_artifact_to_pm_columns(tmp_path: Path) -> None:
    opportunity_path = _opportunity(tmp_path, [_ranked("10010", 3)])
    context_path = tmp_path / "pm_opportunity_context.csv"

    _write_pm_opportunity_context(
        source_path=opportunity_path,
        output_path=context_path,
        feature_date=BUSINESS_DATE,
    )

    frame = pd.read_csv(context_path, dtype={"code": str})
    assert list(frame.columns)[:5] == ["target_date", "code", "expected_edge_score", "buy_rank", "downside_risk_score"]
    assert frame.loc[0, "code"] == "10010"
    assert int(frame.loc[0, "buy_rank"]) == 3


def test_no_signal_opportunity_artifact_is_confirmed_empty_ready(tmp_path: Path) -> None:
    payload = _opportunity_payload([])
    opportunity_path = tmp_path / "opportunity_rankings.json"
    opportunity_path.write_text(json.dumps(payload), encoding="utf-8")

    result = _pm_opportunity_contract(opportunity_path=opportunity_path, feature_date=BUSINESS_DATE)

    assert result["status"] == "PASS"
    assert result["frame"].empty
    assert result["empty_semantics"] == "no_buy_signal_confirmed_empty"


def test_unknown_opportunity_schema_is_rejected(tmp_path: Path) -> None:
    path = _opportunity(tmp_path, [_ranked("10010", 1)], schema_version="runtime_v2_unknown")
    contract = _pm_contract_for_opportunity(tmp_path, path)

    assert contract["pm_input_schema_status"] == "REVIEW_REQUIRED"
    assert contract["pm_review_reason"] == "pm_feature_required_columns_missing"
    assert any("unsupported opportunity schema_version" in item for item in contract["pm_missing_fields"])


def test_duplicate_symbol_is_rejected(tmp_path: Path) -> None:
    path = _opportunity(tmp_path, [_ranked("10010", 1), _ranked("10010", 2)])
    contract = _pm_contract_for_opportunity(tmp_path, path)

    assert contract["pm_input_schema_status"] == "REVIEW_REQUIRED"
    assert any("duplicate symbol" in item for item in contract["pm_missing_fields"])


def test_invalid_score_and_rank_are_rejected(tmp_path: Path) -> None:
    bad_score = _ranked("10010", 1)
    bad_score["expected_edge_score"] = "nan"
    score_path = _opportunity(tmp_path / "score", [bad_score])
    score_contract = _pm_contract_for_opportunity(tmp_path / "score", score_path)

    bad_rank = _ranked("10010", 0)
    rank_path = _opportunity(tmp_path / "rank", [bad_rank])
    rank_contract = _pm_contract_for_opportunity(tmp_path / "rank", rank_path)

    assert any("non-finite score" in item for item in score_contract["pm_missing_fields"])
    assert any("invalid rank" in item for item in rank_contract["pm_missing_fields"])


def test_wrong_target_date_and_wrong_role_are_rejected(tmp_path: Path) -> None:
    wrong_date = _ranked("10010", 1)
    wrong_date["target_date"] = "2026-07-08"
    date_path = _opportunity(tmp_path / "date", [wrong_date])
    date_contract = _pm_contract_for_opportunity(tmp_path / "date", date_path)

    role_path = _opportunity(tmp_path / "role", [_ranked("10010", 1)], artifact_role="DISPLAY_ONLY")
    role_contract = _pm_contract_for_opportunity(tmp_path / "role", role_path)

    assert any("target date mismatch" in item for item in date_contract["pm_missing_fields"])
    assert any("wrong opportunity artifact_role" in item for item in role_contract["pm_missing_fields"])


def _pm_contract_for_opportunity(tmp_path: Path, opportunity_path: Path) -> dict[str, Any]:
    return validate_position_management_input_contract(
        current=_current(["10010"]),
        current_path=tmp_path / "current.json",
        runtime_state={"state": "CURRENT_STATE_LOADED"},
        runtime_state_path=tmp_path / "current_state.json",
        business_date=BUSINESS_DATE,
        feature_date=BUSINESS_DATE,
        opportunity_path=opportunity_path,
        feature_path=_feature(tmp_path, ["10010"]),
    )


def _current(symbols: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "temporal_schema_version": "runtime_v2_current_temporal_v1",
        "as_of": BUSINESS_DATE,
        "position_state_as_of": BUSINESS_DATE,
        "valuation_as_of": BUSINESS_DATE,
        "current_position_status": "READY",
        "current_valuation_status": "READY",
        "updated_at": BUSINESS_DATE + "T00:00:00Z",
        "positions": [
            {
                "symbol": symbol,
                "quantity": 100,
                "average_price": 1000,
                "current_price": 980,
                "market_value": 98000,
                "source": "test_current",
                "as_of": BUSINESS_DATE,
            }
            for symbol in symbols
        ],
    }


def _feature(tmp_path: Path, symbols: list[str]) -> Path:
    path = tmp_path / "position_feature_input.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "target_date": BUSINESS_DATE,
                "code": symbol,
                "holding_days": 10,
                "peak_return": 0.03,
                "feature_version": "position_management_feature_v1",
            }
            for symbol in symbols
        ]
    ).to_csv(path, index=False)
    return path


def _opportunity(
    tmp_path: Path,
    rows: list[dict[str, Any]],
    *,
    schema_version: str = "runtime_v2_opportunity_ranking_v1",
    artifact_role: str = "BUY_OPPORTUNITY_RANKING",
) -> Path:
    path = tmp_path / "opportunity_rankings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _opportunity_payload(rows, schema_version=schema_version, artifact_role=artifact_role)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _opportunity_payload(
    rows: list[dict[str, Any]],
    *,
    schema_version: str = "runtime_v2_opportunity_ranking_v1",
    artifact_role: str = "BUY_OPPORTUNITY_RANKING",
) -> dict[str, Any]:
    return {
        "schema_name": "runtime_v2_buy_opportunity_ranking",
        "schema_version": schema_version,
        "artifact_role": artifact_role,
        "producer": "Runtime v2 BUY AI Producer",
        "producer_version": "candidate_opportunity_ai_regular_path_v1",
        "business_date": BUSINESS_DATE,
        "feature_date": BUSINESS_DATE,
        "runtime_id": "runtime-v2-buy-ai-test",
        "model_version": "opportunity_model_test",
        "generated_at": BUSINESS_DATE + "T00:00:00Z",
        "status": "PASS",
        "ranking_count": len(rows),
        "rankings": rows,
    }


def _ranked(symbol: str, rank: int) -> dict[str, Any]:
    return {
        "target_date": BUSINESS_DATE,
        "code": symbol,
        "symbol": symbol,
        "expected_edge_score": 0.07,
        "opportunity_score": 0.07,
        "buy_rank": rank,
        "rank": rank,
        "downside_risk_score": 0.35,
        "candidate_score": 0.8,
        "candidate_rank": rank + 10,
        "reason": "fixture",
    }
