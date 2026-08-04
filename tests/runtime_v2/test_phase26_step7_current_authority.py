from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.asset.runtime_owned_fill_projection import (
    project_runtime_owned_fills_to_current,
)
from ai_fund_lab_v2.runtime_v2.historical_support.environment import (
    EnvironmentCompositionError,
    HistoricalExecutionSnapshotProvider,
)
from ai_fund_lab_v2.runtime_v2.planning_submit_feasibility import (
    evaluate_planning_submit_feasibility,
    load_runtime_current_exposure,
)
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import load_capital_deployment_policy

from tests.runtime_v2.test_phase24_ht_planning_submit_feasibility import (
    _item,
    _position,
    _write_policy,
)


BUSINESS_DATE = "2026-07-09"


def test_phase26_step7_valid_current_materializes_selected_sources(tmp_path: Path) -> None:
    current_path = _runtime_root(tmp_path) / "persistent_ledger" / "state.json"
    _write_current(current_path, cash=500_000, positions=[_position("1111", 100, 1000)])

    current = load_runtime_current_exposure(current_path, business_date=BUSINESS_DATE)
    payload = current.to_payload()

    assert current.current_authority_status == "PASS"
    assert payload["selected_current_source"] == str(current_path)
    assert payload["selected_cash_source"].endswith(":cash")
    assert payload["selected_positions_source"].endswith(":positions")
    assert payload["selected_valuation_source"].endswith(":positions.market_value")
    assert payload["current_authority_winner"] == "persistent_ledger_state"
    assert payload["legacy_current_used"] is False
    assert payload["current_fallback_used"] is False
    assert payload["runtime_evaluation_capital_used_as_current"] is False


def test_phase26_step7_current_cash_missing_does_not_use_runtime_evaluation_capital(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(
        root / "persistent_ledger" / "state.json",
        cash=None,
        positions=[_position("1111", 100, 1000)],
        runtime_evaluation_capital=1_000_000,
    )
    current = load_runtime_current_exposure(root / "persistent_ledger" / "state.json", business_date=BUSINESS_DATE)

    result = evaluate_planning_submit_feasibility(
        items=(_item("buy-1", amount=100_000),),
        policy=policy,
        current=current,
        authority_source="phase26_step7_current_negative",
        business_date=BUSINESS_DATE,
        runtime_mode="demo",
    )

    item = result.evidence["items"][0]
    assert result.status == "REVIEW_REQUIRED"
    assert item["violated_policy"] == "cash_missing"
    assert item["runtime_evaluation_capital_used_as_current"] is False
    assert item["current_fallback_used"] is False


def test_phase26_step7_future_dated_current_rejected_without_latest_fallback(tmp_path: Path) -> None:
    current_path = _runtime_root(tmp_path) / "persistent_ledger" / "state.json"
    _write_current(current_path, cash=500_000, positions=[], as_of="2026-07-10")

    current = load_runtime_current_exposure(current_path, business_date=BUSINESS_DATE)

    assert current.current_authority_status == "REVIEW_REQUIRED"
    assert current.current_authority_reason == "future_dated_current_rejected"
    assert current.cash is None
    assert current.current_total_equity is None
    assert current.current_fallback_used is False


def test_phase26_step7_source_conflict_fails_closed_without_silent_merge(tmp_path: Path) -> None:
    current_path = _runtime_root(tmp_path) / "persistent_ledger" / "state.json"
    _write_current(
        current_path,
        cash=500_000,
        positions=[],
        source_conflict_detected=True,
        source_selection_reason="broker_ledger_conflict_requires_review",
    )

    current = load_runtime_current_exposure(current_path, business_date=BUSINESS_DATE)

    assert current.current_authority_status == "REVIEW_REQUIRED"
    assert current.current_authority_reason == "current_source_conflict_detected"
    assert current.source_conflict_detected is True
    assert current.source_selection_reason == "broker_ledger_conflict_requires_review"
    assert current.current_fallback_used is False


def test_phase26_step7_projection_requires_current_cash_not_initial_capital(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_current(
        root / "persistent_ledger" / "state.json",
        cash=None,
        positions=[],
        runtime_evaluation_capital=1_000_000,
    )
    _write_jsonl(root / "persistent_ledger" / "orders.jsonl", [_order("BUY", "7203", 100, 1000)])
    _write_jsonl(root / "persistent_ledger" / "executions.jsonl", [_execution("BUY", "7203", 100, 1000)])
    _write_jsonl(root / "persistent_ledger" / "positions.jsonl", [_ledger_position("7203", 100, 1000)])

    result = project_runtime_owned_fills_to_current(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="demo",
        write=False,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "no runtime_evaluation_capital" in result.reason
    assert result.current_sot_after["runtime_owned_projection"]["runtime_evaluation_capital_used_as_current"] is False
    assert result.current_sot_after["runtime_owned_projection"]["current_fallback_used"] is False


def test_phase26_step7_historical_snapshot_rejects_runtime_evaluation_capital_cash_fallback(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_current(
        root / "persistent_ledger" / "state.json",
        cash=None,
        positions=[],
        runtime_evaluation_capital=1_000_000,
    )
    provider = HistoricalExecutionSnapshotProvider(runtime_root=root, business_date=BUSINESS_DATE)

    try:
        provider(mode="historical", snapshot_path=root / "snapshot.json", report_path=root / "report.json")
    except EnvironmentCompositionError as exc:
        assert "no runtime_evaluation_capital fallback" in str(exc)
    else:
        raise AssertionError("historical snapshot provider must fail closed when current cash is missing")


def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    (root / "persistent_ledger").mkdir(parents=True, exist_ok=True)
    for name in ("orders", "executions", "positions", "cash", "events"):
        (root / "persistent_ledger" / f"{name}.jsonl").write_text("", encoding="utf-8")
    return root


def _write_current(
    path: Path,
    *,
    cash,
    positions: list[dict],
    as_of: str = BUSINESS_DATE,
    runtime_evaluation_capital: float | None = None,
    source_conflict_detected: bool = False,
    source_selection_reason: str = "explicit_persistent_ledger_state_current_authority",
) -> None:
    market_value = sum(float(position.get("market_value") or 0.0) for position in positions)
    payload = {
        "schema_version": "1",
        "asset_state_id": "asset-phase26-step7",
        "environment": "demo",
        "source": "runtime_v2_runtime_owned_fill_projection",
        "as_of": as_of,
        "positions": positions,
        "cash": cash,
        "buying_power": cash,
        "market_value": market_value,
        "total_equity": None if cash is None else cash + market_value,
        "source_conflict_detected": source_conflict_detected,
        "source_selection_reason": source_selection_reason,
    }
    if runtime_evaluation_capital is not None:
        payload["runtime_evaluation_capital"] = runtime_evaluation_capital
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _order(side: str, symbol: str, quantity: float, price: float) -> dict:
    return {
        "record_id": f"order-{side}-{symbol}",
        "source": "runtime_v2_submit_pipeline",
        "status": "ACCEPTED",
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "estimated_price": price,
        "issue_code_normalization": {"broker_issue_code": symbol},
    }


def _execution(side: str, symbol: str, quantity: float, price: float) -> dict:
    return {
        "record_id": f"execution-{side}-{symbol}",
        "source": "runtime_v2_execution_readonly",
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "price": price,
        "execution_price": price,
        "cash_effect": -quantity * price if side == "BUY" else quantity * price,
    }


def _ledger_position(symbol: str, quantity: float, price: float) -> dict:
    return {
        "record_id": f"position-{symbol}",
        "source": "runtime_v2_execution_readonly",
        "symbol": symbol,
        "quantity": quantity,
        "average_price": price,
        "market_value": quantity * price,
        "recorded_at": BUSINESS_DATE,
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
