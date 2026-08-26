from __future__ import annotations

from pathlib import Path

import pytest

from ai_fund_lab_v2.strategy.strategy_intelligence import build_strategy_intelligence_payload

from tests.strategy.test_phase30_j_strategy_intelligence import (
    _candidate_summary,
    _opportunity_summary,
    _price_volatility_summary,
    _technical_summary,
    _write_json,
)
from tests.strategy.test_phase30_l_strategy_intelligence_gap_repair import _write_source_artifacts_l


def test_phase30_n_lifecycle_context_uses_canonical_campaign_authority(tmp_path: Path) -> None:
    business_date = "2026-07-15"
    paths = _write_source_artifacts_l(tmp_path, business_date=business_date, action="HOLD", buy_quality_action="BUY_WAIT", market_returns=True)
    campaign_path = _campaigns(tmp_path, business_date=business_date, status="OPEN", current_quantity=100)

    payload = _payload(tmp_path, business_date=business_date, paths=paths, campaign_path=campaign_path, action="HOLD")

    lifecycle = payload["symbol_intelligence"]["11110"]["lifecycle_context"]
    assert lifecycle["current_position_authority_status"] == "COMPLETE"
    assert lifecycle["campaign_identity_authority_status"] == "COMPLETE"
    assert lifecycle["position_campaign_id"] == "pc-11110-0001"
    assert lifecycle["campaign_opened_date"] == "2026-07-10"
    assert lifecycle["campaign_status"] == "OPEN"
    assert lifecycle["current_quantity"] == 100
    assert lifecycle["current_market_value"] == 105000
    assert lifecycle["quantity_basis"] == "ADJUSTED"
    assert lifecycle["valuation_price_basis"] == "ADJUSTED"
    assert lifecycle["campaign_authority_owner"] == "positions/position_campaigns.json"
    assert lifecycle["current_authority_owner"] == "Runtime Current / PM current position adapter"


def test_phase31_g108_runtime_owned_fill_open_campaign_identity_propagates(tmp_path: Path) -> None:
    business_date = "2022-11-28"
    symbol = "93180"
    paths = _write_source_artifacts_l(tmp_path, business_date=business_date, action="HOLD", buy_quality_action="BUY_WAIT", market_returns=True)
    campaign_path = _write_json(
        tmp_path / "position_campaigns.json",
        {
            "schema_version": "position_campaign_observability.v1",
            "business_date": business_date,
            "authority": "CANONICAL_PRE_ACTION_POSITION_CAMPAIGN_LIFECYCLE",
            "position_campaigns": [
                {
                    "position_campaign_id": "pc-93bafcd34c4af64c-93180-0001",
                    "symbol": symbol,
                    "campaign_status": "CLOSED",
                    "opened_business_date": "2022-10-25",
                    "closed_business_date": "2022-10-27",
                    "current_quantity": 0,
                    "events": [
                        {"business_date": "2022-10-25", "side": "BUY", "stage": "BUY", "quantity": 6500},
                        {"business_date": "2022-10-27", "side": "SELL", "stage": "SELL", "quantity": 6500},
                    ],
                },
                {
                    "position_campaign_id": "pc-93bafcd34c4af64c-93180-0002",
                    "symbol": symbol,
                    "campaign_status": "OPEN",
                    "opened_business_date": "2022-11-25",
                    "closed_business_date": "",
                    "current_quantity": 700,
                    "events": [
                        {
                            "business_date": "2022-11-25",
                            "side": "BUY",
                            "stage": "BUY",
                            "quantity": 700,
                            "evidence_type": "execution-time evidence",
                        }
                    ],
                },
            ],
        },
    )

    payload = _payload_for_symbol(
        tmp_path,
        business_date=business_date,
        paths=paths,
        campaign_path=campaign_path,
        action="HOLD",
        symbol=symbol,
        quantity=700,
        average_price=4,
        market_value=2800,
    )

    lifecycle = payload["symbol_intelligence"][symbol]["lifecycle_context"]
    assert lifecycle["current_position_state"] == "HELD"
    assert lifecycle["current_quantity"] == 700
    assert lifecycle["position_campaign_id"] == "pc-93bafcd34c4af64c-93180-0002"
    assert lifecycle["campaign_opened_date"] == "2022-11-25"
    assert lifecycle["campaign_status"] == "OPEN"
    assert lifecycle["campaign_identity_authority_status"] == "COMPLETE"
    assert "position_campaign_id" not in lifecycle["missing_campaign_authority_fields"]


def test_phase30_n_held_position_without_canonical_campaign_is_not_complete(tmp_path: Path) -> None:
    business_date = "2026-07-15"
    paths = _write_source_artifacts_l(tmp_path, business_date=business_date, action="HOLD", buy_quality_action="BUY_WAIT", market_returns=True)

    payload = _payload(tmp_path, business_date=business_date, paths=paths, campaign_path=None, action="HOLD")

    lifecycle = payload["symbol_intelligence"]["11110"]["lifecycle_context"]
    assert lifecycle["current_position_state"] == "HELD"
    assert lifecycle["current_position_authority_status"] == "MISSING"
    assert lifecycle["campaign_identity_authority_status"] == "MISSING"
    assert lifecycle["position_campaign_id"] is None
    assert "position_campaign_id" in lifecycle["missing_campaign_authority_fields"]


def test_phase30_n_add_reduce_exit_preserve_campaign_identity(tmp_path: Path) -> None:
    business_date = "2026-07-15"
    campaign_path = _campaigns(tmp_path, business_date=business_date, status="OPEN", current_quantity=100)
    for action, expected in (
        ("ADD", "ADD_WORTHINESS_EVIDENCE_SHADOW"),
        ("REDUCE", "PM_REDUCE_EVIDENCE_OBSERVED_SHADOW"),
        ("EXIT", "PM_EXIT_EVIDENCE_OBSERVED_SHADOW"),
    ):
        action_dir = tmp_path / action
        paths = _write_source_artifacts_l(action_dir, business_date=business_date, action=action, buy_quality_action="BUY_WAIT", market_returns=True)
        payload = _payload(action_dir, business_date=business_date, paths=paths, campaign_path=campaign_path, action=action)
        row = payload["symbol_intelligence"]["11110"]
        assert row["strategy_intelligence_interpretation"]["state"] == expected
        assert row["lifecycle_context"]["position_campaign_id"] == "pc-11110-0001"
        assert row["lifecycle_context"]["campaign_opened_date"] == "2026-07-10"


def test_phase30_n_reentry_uses_new_open_campaign_identity(tmp_path: Path) -> None:
    business_date = "2026-07-15"
    paths = _write_source_artifacts_l(tmp_path, business_date=business_date, action="REENTRY", buy_quality_action="FULL_ALLOCATION_ELIGIBLE", market_returns=True)
    campaign_path = _write_json(
        tmp_path / "position_campaigns.json",
        {
            "schema_version": "position_campaign_observability.v1",
            "business_date": business_date,
            "position_campaigns": [
                {
                    "position_campaign_id": "pc-11110-old",
                    "symbol": "11110",
                    "campaign_status": "CLOSED",
                    "opened_business_date": "2026-07-01",
                    "closed_business_date": "2026-07-08",
                    "current_quantity": 0,
                    "events": [{"business_date": "2026-07-01", "side": "BUY"}, {"business_date": "2026-07-08", "side": "SELL"}],
                },
                {
                    "position_campaign_id": "pc-11110-new",
                    "symbol": "11110",
                    "campaign_status": "OPEN",
                    "opened_business_date": "2026-07-15",
                    "current_quantity": 100,
                    "events": [{"business_date": "2026-07-15", "side": "BUY", "stage": "BUY"}],
                },
            ],
        },
    )

    payload = _payload(tmp_path, business_date=business_date, paths=paths, campaign_path=campaign_path, action="REENTRY")

    lifecycle = payload["symbol_intelligence"]["11110"]["lifecycle_context"]
    assert lifecycle["position_campaign_id"] == "pc-11110-new"
    assert lifecycle["campaign_opened_date"] == "2026-07-15"
    assert lifecycle["campaign_status"] == "OPEN"


def test_phase30_n_conflicting_active_campaigns_block(tmp_path: Path) -> None:
    business_date = "2026-07-15"
    paths = _write_source_artifacts_l(tmp_path, business_date=business_date, action="HOLD", buy_quality_action="BUY_WAIT", market_returns=True)
    campaign_path = _write_json(
        tmp_path / "position_campaigns.json",
        {
            "schema_version": "position_campaign_observability.v1",
            "business_date": business_date,
            "position_campaigns": [
                {"position_campaign_id": "pc-a", "symbol": "11110", "campaign_status": "OPEN", "opened_business_date": "2026-07-10", "current_quantity": 100},
                {"position_campaign_id": "pc-b", "symbol": "11110", "campaign_status": "OPEN", "opened_business_date": "2026-07-11", "current_quantity": 100},
            ],
        },
    )

    with pytest.raises(ValueError, match="CAMPAIGN_AUTHORITY_CONFLICT:11110"):
        _payload(tmp_path, business_date=business_date, paths=paths, campaign_path=campaign_path, action="HOLD")


def test_phase31_g108_closed_only_campaign_does_not_complete_held_position(tmp_path: Path) -> None:
    business_date = "2026-07-15"
    paths = _write_source_artifacts_l(tmp_path, business_date=business_date, action="HOLD", buy_quality_action="BUY_WAIT", market_returns=True)
    campaign_path = _write_json(
        tmp_path / "position_campaigns.json",
        {
            "schema_version": "position_campaign_observability.v1",
            "business_date": business_date,
            "position_campaigns": [
                {
                    "position_campaign_id": "pc-11110-closed",
                    "symbol": "11110",
                    "campaign_status": "CLOSED",
                    "opened_business_date": "2026-07-10",
                    "closed_business_date": "2026-07-14",
                    "current_quantity": 0,
                    "events": [{"business_date": "2026-07-10", "side": "BUY"}, {"business_date": "2026-07-14", "side": "SELL"}],
                }
            ],
        },
    )

    payload = _payload(tmp_path, business_date=business_date, paths=paths, campaign_path=campaign_path, action="HOLD")

    lifecycle = payload["symbol_intelligence"]["11110"]["lifecycle_context"]
    assert lifecycle["current_position_state"] == "HELD"
    assert lifecycle["campaign_identity_authority_status"] == "MISSING"
    assert lifecycle["position_campaign_id"] is None
    assert "position_campaign_id" in lifecycle["missing_campaign_authority_fields"]


def test_phase31_g108_campaign_symbol_mismatch_does_not_complete_held_position(tmp_path: Path) -> None:
    business_date = "2026-07-15"
    paths = _write_source_artifacts_l(tmp_path, business_date=business_date, action="HOLD", buy_quality_action="BUY_WAIT", market_returns=True)
    campaign_path = _write_json(
        tmp_path / "position_campaigns.json",
        {
            "schema_version": "position_campaign_observability.v1",
            "business_date": business_date,
            "position_campaigns": [
                {
                    "position_campaign_id": "pc-22220-0001",
                    "symbol": "22220",
                    "campaign_status": "OPEN",
                    "opened_business_date": "2026-07-10",
                    "current_quantity": 100,
                }
            ],
        },
    )

    payload = _payload(tmp_path, business_date=business_date, paths=paths, campaign_path=campaign_path, action="HOLD")

    lifecycle = payload["symbol_intelligence"]["11110"]["lifecycle_context"]
    assert lifecycle["current_position_state"] == "HELD"
    assert lifecycle["campaign_identity_authority_status"] == "MISSING"
    assert lifecycle["position_campaign_id"] is None


def test_phase31_g108_campaign_quantity_mismatch_does_not_complete_held_position(tmp_path: Path) -> None:
    business_date = "2026-07-15"
    paths = _write_source_artifacts_l(tmp_path, business_date=business_date, action="HOLD", buy_quality_action="BUY_WAIT", market_returns=True)
    campaign_path = _write_json(
        tmp_path / "position_campaigns.json",
        {
            "schema_version": "position_campaign_observability.v1",
            "business_date": business_date,
            "position_campaigns": [
                {
                    "position_campaign_id": "pc-11110-0001",
                    "symbol": "11110",
                    "campaign_status": "OPEN",
                    "opened_business_date": "2026-07-10",
                    "current_quantity": 50,
                }
            ],
        },
    )

    payload = _payload(tmp_path, business_date=business_date, paths=paths, campaign_path=campaign_path, action="HOLD")

    lifecycle = payload["symbol_intelligence"]["11110"]["lifecycle_context"]
    assert lifecycle["current_position_state"] == "HELD"
    assert lifecycle["campaign_identity_authority_status"] == "MISSING"
    assert "campaign_current_quantity_mismatch" in lifecycle["missing_campaign_authority_fields"]


def _payload(tmp_path: Path, *, business_date: str, paths: dict[str, Path], campaign_path: Path | None, action: str) -> dict:
    payload, _ = build_strategy_intelligence_payload(
        business_date=business_date,
        candidate_summary=_candidate_summary(business_date),
        opportunity_summary=_opportunity_summary(business_date),
        current_summary=_current_summary_n(business_date, action=action),
        technical_feature_summary=_technical_summary(business_date),
        price_volatility_summary=_price_volatility_summary(business_date),
        position_campaigns_artifact_path=campaign_path,
        as_of=f"{business_date}T00:00:00+00:00",
        **paths,
    )
    return payload


def _payload_for_symbol(
    tmp_path: Path,
    *,
    business_date: str,
    paths: dict[str, Path],
    campaign_path: Path | None,
    action: str,
    symbol: str,
    quantity: int,
    average_price: int,
    market_value: int,
) -> dict:
    payload, _ = build_strategy_intelligence_payload(
        business_date=business_date,
        candidate_summary=_candidate_summary_for_symbol(business_date, symbol=symbol),
        opportunity_summary=_opportunity_summary_for_symbol(business_date, symbol=symbol),
        current_summary={
            "status": "PASS",
            "business_date": business_date,
            "feature_date": business_date,
            "source_ref": "Current",
            "source_hash": "current-hash",
            "rows": [
                {
                    "security_code": symbol,
                    "business_date": business_date,
                    "quantity": quantity,
                    "average_price": average_price,
                    "market_value": market_value,
                    "quantity_basis": "ADJUSTED",
                    "valuation_price_basis": "ADJUSTED",
                }
            ],
        },
        technical_feature_summary=_technical_summary_for_symbol(business_date, symbol=symbol),
        price_volatility_summary=_price_volatility_summary_for_symbol(business_date, symbol=symbol),
        position_campaigns_artifact_path=campaign_path,
        as_of=f"{business_date}T00:00:00+00:00",
        **paths,
    )
    return payload


def _current_summary_n(business_date: str, *, action: str) -> dict:
    held = action in {"HOLD", "ADD", "REDUCE", "EXIT", "REENTRY"}
    return {
        "status": "PASS",
        "business_date": business_date,
        "feature_date": business_date,
        "source_ref": "Current",
        "source_hash": "current-hash",
        "rows": [
            {
                "security_code": "11110",
                "business_date": business_date,
                "quantity": 100 if held else 0,
                "average_price": 1000,
                "market_value": 105000 if held else 0,
                "quantity_basis": "ADJUSTED",
                "valuation_price_basis": "ADJUSTED",
                "observed_campaign_mfe": 0.12 if held else None,
                "observed_giveback": 0.015 if held else None,
            }
        ],
    }


def _campaigns(tmp_path: Path, *, business_date: str, status: str, current_quantity: int) -> Path:
    return _write_json(
        tmp_path / "position_campaigns.json",
        {
            "schema_version": "position_campaign_observability.v1",
            "business_date": business_date,
            "artifact_hash": "campaign-hash",
            "position_campaigns": [
                {
                    "position_campaign_id": "pc-11110-0001",
                    "symbol": "11110",
                    "campaign_status": status,
                    "opened_business_date": "2026-07-10",
                    "closed_business_date": "",
                    "current_quantity": current_quantity,
                    "events": [
                        {"business_date": "2026-07-10", "side": "BUY", "stage": "BUY", "quantity": 100},
                        {"business_date": "2026-07-12", "side": "BUY", "stage": "ADD", "quantity": 100},
                        {"business_date": "2026-07-14", "side": "SELL", "stage": "REDUCE", "quantity": 100},
                    ],
                }
            ],
        },
    )


def _candidate_summary_for_symbol(business_date: str, *, symbol: str) -> dict:
    payload = _candidate_summary(business_date)
    rows = []
    for row in payload.get("rows") or ():
        item = dict(row)
        item["security_code"] = symbol
        rows.append(item)
    return {**payload, "rows": rows}


def _opportunity_summary_for_symbol(business_date: str, *, symbol: str) -> dict:
    payload = _opportunity_summary(business_date)
    rows = []
    for row in payload.get("rows") or ():
        item = dict(row)
        item["security_code"] = symbol
        rows.append(item)
    return {**payload, "rows": rows}


def _technical_summary_for_symbol(business_date: str, *, symbol: str) -> dict:
    payload = _technical_summary(business_date)
    rows = []
    for row in payload.get("rows") or ():
        item = dict(row)
        item["security_code"] = symbol
        rows.append(item)
    return {**payload, "rows": rows}


def _price_volatility_summary_for_symbol(business_date: str, *, symbol: str) -> dict:
    payload = _price_volatility_summary(business_date)
    rows = []
    for row in payload.get("rows") or ():
        item = dict(row)
        item["security_code"] = symbol
        rows.append(item)
    return {**payload, "rows": rows}
