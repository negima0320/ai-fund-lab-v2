from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.strategy import position_management as pm
from ai_fund_lab_v2.strategy.position_management import (
    PMSourceSummary,
    PositionManagementConsumerError,
    PositionManagementSchemaError,
    build_regime_event_position_management_payload,
    default_regime_event_runtime_artifact_path,
    load_position_management_fixture,
    load_regime_event_pm_config,
    position_management_hash,
    produce_regime_event_position_management_artifact,
    validate_position_management_artifact,
    verify_source_hashes,
)


def test_phase22_k_produces_read_only_regime_event_pm_actions(tmp_path: Path) -> None:
    payload = _produce(tmp_path, rows=[
        _row("7203", score=0.65, momentum=0.02, target_weight=0.1, current_weight=0.1),
        _row("6758", score=0.9, momentum=0.08, target_weight=0.16, current_weight=0.08),
        _row("9984", score=0.25, momentum=-0.03, current_weight=0.1),
        _row("8306", score=0.1, close_ma=0.9, current_weight=0.1),
        _row("9432", opportunity_status="MISSING"),
    ]).payload

    actions = {item["security_code"]: item["action"] for item in payload["positions"]}
    assert actions["7203"] == "HOLD"
    assert actions["6758"] == "ADD"
    assert actions["9984"] == "REDUCE"
    assert actions["8306"] == "EXIT"
    assert actions["9432"] == "UNRESOLVED"
    assert payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert payload["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    assert payload["quantity_decided"] is False
    assert validate_position_management_artifact(payload)["status"] == "PASS"


def test_phase22_k_regime_relative_rules(tmp_path: Path) -> None:
    bull = _produce(tmp_path / "bull", market={"trend_regime": "BULL", "volatility_regime": "NORMAL", "confidence": 0.9}, rows=[_row("1001", score=0.9, momentum=0.08, target_weight=0.16, current_weight=0.08)]).payload
    range_payload = _produce(tmp_path / "range", market={"trend_regime": "RANGE", "volatility_regime": "NORMAL", "confidence": 0.9}, rows=[_row("1001", score=0.9, momentum=0.08, target_weight=0.16, current_weight=0.08)]).payload
    bear = _produce(tmp_path / "bear", market={"trend_regime": "BEAR", "volatility_regime": "NORMAL", "confidence": 0.9}, rows=[_row("1001", score=0.9, momentum=0.08, target_weight=0.16, current_weight=0.08)]).payload
    high_vol = _produce(tmp_path / "high_vol", market={"trend_regime": "BULL", "volatility_regime": "HIGH", "confidence": 0.9}, rows=[_row("1001", score=0.9, momentum=0.08, target_weight=0.16, current_weight=0.08)]).payload
    uncertain = _produce(tmp_path / "uncertain", market={"trend_regime": "BULL", "volatility_regime": "NORMAL", "confidence": 0.3, "uncertainty": "HIGH"}, rows=[_row("1001", score=0.9, momentum=0.08, target_weight=0.16, current_weight=0.08)]).payload

    assert bull["positions"][0]["action"] == "ADD"
    assert range_payload["positions"][0]["action"] == "ADD"
    assert bear["positions"][0]["action"] in {"HOLD", "REDUCE"}
    assert high_vol["positions"][0]["action"] in {"HOLD", "REDUCE"}
    assert uncertain["positions"][0]["action"] == "UNRESOLVED"


def test_phase22_k_corporate_event_rules_and_leakage(tmp_path: Path) -> None:
    earnings = _produce(tmp_path / "earnings", rows=[_row("2001", score=0.9, momentum=0.08, target_weight=0.16, current_weight=0.08, event_type="EARNINGS", days_to_earnings=1)]).payload
    distant = _produce(tmp_path / "distant", rows=[_row("2002", score=0.9, momentum=0.08, target_weight=0.16, current_weight=0.08, event_type="EARNINGS", days_to_earnings=8)]).payload
    split = _produce(tmp_path / "split", rows=[_row("2003", event_type="SPLIT")]).payload
    tob = _produce(tmp_path / "tob", rows=[_row("2004", event_type="TOB")]).payload
    delisting = _produce(tmp_path / "delisting", rows=[_row("2005", event_type="DELISTING")]).payload
    unavailable = _produce(tmp_path / "unavailable", corporate={"coverage_status": "SOURCE_UNAVAILABLE"}, rows=[_row("2006")]).payload
    future = _produce(tmp_path / "future", rows=[_row("2007", event_type="TOB", event_announced_at="2026-07-16")]).payload

    assert earnings["positions"][0]["action"] != "ADD"
    assert distant["positions"][0]["action"] == "ADD"
    assert split["positions"][0]["action"] == "HOLD"
    assert tob["positions"][0]["action"] == "EXIT"
    assert delisting["positions"][0]["action"] == "EXIT"
    assert unavailable["producer_result_status"] == "REVIEW_REQUIRED"
    assert unavailable["positions"][0]["action"] == "UNRESOLVED"
    assert future["producer_result_status"] == "BLOCK"


def test_phase22_k_technical_opportunity_holding_cooldown_reentry_and_conflicts(tmp_path: Path) -> None:
    healthy = _produce(tmp_path / "healthy", rows=[_row("3001", score=0.9, momentum=0.08, close_ma=1.05, target_weight=0.15, current_weight=0.08)]).payload
    weakening = _produce(tmp_path / "weak", rows=[_row("3002", score=0.8, momentum=-0.03)]).payload
    breakdown = _produce(tmp_path / "break", rows=[_row("3003", score=0.8, close_ma=0.9)]).payload
    vol_expansion = _produce(tmp_path / "vol", rows=[_row("3004", score=0.8, volatility=0.08)]).payload
    cooldown = _produce(tmp_path / "cooldown", rows=[_row("3005", score=0.9, momentum=0.08, target_weight=0.15, current_weight=0.08, days_since_add=1)]).payload
    safety_override = _produce(tmp_path / "hard", rows=[_row("3006", hard_invalidation=True, days_since_add=1)]).payload

    assert healthy["positions"][0]["technical_health_state"] == "HEALTHY"
    assert healthy["positions"][0]["holding_period_state"] == "MATURE"
    assert weakening["positions"][0]["action"] == "REDUCE"
    assert breakdown["positions"][0]["action"] == "EXIT"
    assert vol_expansion["positions"][0]["action"] == "REDUCE"
    assert cooldown["positions"][0]["action"] != "ADD"
    assert safety_override["positions"][0]["action"] == "EXIT"


def test_phase22_k_quantity_boundary_status_hash_fixture_and_runtime_preservation(tmp_path: Path) -> None:
    payload = _produce(tmp_path).payload
    for mutation in (
        lambda item: item["positions"][0].update({"quantity": 100}),
        lambda item: item["positions"][0].update({"sell_percentage": 0.5}),
        lambda item: item["positions"][0].update({"sell_allocation_jpy": 100000}),
        lambda item: item["positions"][0].update({"lot_rounding_result": "100"}),
    ):
        mutated = json.loads(json.dumps(payload))
        mutation(mutated)
        with pytest.raises(PositionManagementSchemaError):
            validate_position_management_artifact(mutated)

    review = _produce(tmp_path / "review", market_status="REVIEW_REQUIRED").payload
    assert review["producer_result_status"] == "REVIEW_REQUIRED"
    assert review["positions"][0]["action"] == "UNRESOLVED"

    future_feature = _produce(tmp_path / "future_feature", technical_feature_date="2026-07-16").payload
    assert future_feature["producer_result_status"] == "BLOCK"

    result = _produce(tmp_path / "ok")
    assert verify_source_hashes(result.payload)["status"] == "PASS"
    assert result.payload["artifact_hash"] == position_management_hash(result.payload)
    assert load_position_management_fixture(result.artifact_path)["schema_version"] == "position_management.v1"
    with pytest.raises(PositionManagementConsumerError):
        load_position_management_fixture(result.artifact_path, for_production=True)
    assert result.payload["shadow_comparison"]["runtime_behavior_changed"] is False


def _produce(
    tmp_path: Path,
    *,
    rows: list[dict[str, object]] | None = None,
    market: dict[str, object] | None = None,
    corporate: dict[str, object] | None = None,
    market_status: str = "PASS",
    technical_feature_date: str = "2026-07-15",
):
    tmp_path.mkdir(parents=True, exist_ok=True)
    return produce_regime_event_position_management_artifact(
        business_date="2026-07-15",
        position_rows=rows or [_row("7203")],
        market_context_summary=_summary(tmp_path, "market", status=market_status, summary=market or {"trend_regime": "BULL", "volatility_regime": "NORMAL", "confidence": 0.9}),
        corporate_event_summary=_summary(tmp_path, "corporate", summary=corporate or {"coverage_status": "AVAILABLE"}),
        portfolio_policy_summary=_summary(tmp_path, "policy", summary={"add_permission": "ALLOWED", "confidence": 0.9}),
        opportunity_summary=_summary(tmp_path, "opportunity"),
        position_sizing_summary=_summary(tmp_path, "sizing", summary={"target_weight": 0.12}),
        position_lifecycle_summary=_summary(tmp_path, "lifecycle"),
        technical_feature_summary=_summary(tmp_path, "technical", feature_date=technical_feature_date),
        current_position_summary=_summary(tmp_path, "current"),
        config=load_regime_event_pm_config("configs/strategy/regime_event_position_management.json"),
        output_path=default_regime_event_runtime_artifact_path(tmp_path / ".runtime", "2026-07-15"),
    )


def _row(
    code: str,
    *,
    score: float | None = 0.8,
    momentum: float = 0.05,
    close_ma: float = 1.03,
    volatility: float = 0.02,
    target_weight: float = 0.12,
    current_weight: float = 0.1,
    event_type: str = "NONE",
    event_announced_at: str = "2026-07-15",
    days_to_earnings: int = 999,
    opportunity_status: str = "PASS",
    days_since_add: int = 99,
    days_since_reduce: int = 99,
    days_since_exit: int = 99,
    hard_invalidation: bool = False,
) -> dict[str, object]:
    row = {
        "position_id": f"pos-{code}",
        "security_code": code,
        "holding_days": 12,
        "price_momentum_return_20d": momentum,
        "trend_close_over_ma_20d": close_ma,
        "volatility_return_std_20d": volatility,
        "target_weight": target_weight,
        "current_weight": current_weight,
        "event_type": event_type,
        "event_announced_at": event_announced_at,
        "days_to_earnings_business": days_to_earnings,
        "opportunity_status": opportunity_status,
        "days_since_add": days_since_add,
        "days_since_reduce": days_since_reduce,
        "days_since_exit": days_since_exit,
        "hard_invalidation": hard_invalidation,
        "legacy_pm_action": "HOLD",
        "confidence": 0.9,
    }
    if score is not None:
        row["opportunity_score"] = score
    return row


def _summary(tmp_path: Path, kind: str, *, status: str = "PASS", business_date: str = "2026-07-15", feature_date: str = "2026-07-15", summary: dict[str, object] | None = None) -> PMSourceSummary:
    path = tmp_path / f"{kind}_summary.json"
    payload = {"kind": kind, "status": status, "business_date": business_date, "feature_date": feature_date, "summary": summary or {}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return PMSourceSummary(status=status, business_date=business_date, feature_date=feature_date, source_ref=str(path), source_hash=pm.sha256_file(path), summary=summary or {})
