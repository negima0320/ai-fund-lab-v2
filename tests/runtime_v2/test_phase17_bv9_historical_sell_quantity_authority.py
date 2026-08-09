from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.historical_support.environment import HistoricalSubmitAdapter
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline
from tests.runtime_v2.test_phase17_g_historical_submit_guard_and_fill import (
    BUSINESS_DATE,
    EVALUATION_TIME,
    _historical_context,
    _pending,
    _write_policy,
    _write_safety,
)

SYMBOL = "70630"

def test_phase17_bv9_historical_full_sell_quantity_authority_passes(tmp_path: Path) -> None:
    runtime_root, policy_path, adapter = _runtime_sell_fixture(tmp_path, owned_quantity=2500, sell_quantity=2500)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        submit_enabled=True,
        job="submit",
        adapter=adapter,
        capital_deployment_policy_path=policy_path,
        environment_context=_historical_context(),
    )

    evidence = result.item_results[0].guard_evidence
    assert result.status == "PASS"
    assert result.submitted_count == 1
    assert evidence["broker_available_quantity_checked"] is True
    assert evidence["broker_available_quantity_source"] == "historical_simulated_broker_authority"
    assert evidence["broker_available_quantity"] == 2500
    assert evidence["broker_restricted_quantity"] == 0
    assert evidence["sell_quantity_guard_status"] == "PASS"
    assert evidence["manual_review_required"] is False


def test_phase17_bv9_historical_partial_sell_quantity_authority_passes(tmp_path: Path) -> None:
    runtime_root, policy_path, adapter = _runtime_sell_fixture(tmp_path, owned_quantity=2500, sell_quantity=1000)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        submit_enabled=True,
        job="submit",
        adapter=adapter,
        capital_deployment_policy_path=policy_path,
        environment_context=_historical_context(),
    )

    evidence = result.item_results[0].guard_evidence
    assert result.status == "PASS"
    assert result.submitted_count == 1
    assert evidence["broker_total_quantity"] == 2500
    assert evidence["broker_available_quantity"] == 2500


def test_phase17_bv9_historical_sell_quantity_insufficient_blocks(tmp_path: Path) -> None:
    runtime_root, policy_path, adapter = _runtime_sell_fixture(tmp_path, owned_quantity=2000, sell_quantity=2500)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        submit_enabled=True,
        job="submit",
        adapter=adapter,
        capital_deployment_policy_path=policy_path,
        environment_context=_historical_context(),
    )

    evidence = result.item_results[0].guard_evidence
    assert result.status in {"BLOCKED", "REVIEW_REQUIRED"}
    assert result.submitted_count == 0
    assert evidence["sell_quantity_guard_status"] == "CURRENT_INSUFFICIENT"


def test_phase17_bv9_historical_restricted_sell_quantity_blocks(tmp_path: Path) -> None:
    runtime_root, policy_path, adapter = _runtime_sell_fixture(tmp_path, owned_quantity=2500, sell_quantity=2000)
    _append_order(runtime_root, symbol=SYMBOL, side="SELL", quantity=1000)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        submit_enabled=True,
        job="submit",
        adapter=adapter,
        capital_deployment_policy_path=policy_path,
        environment_context=_historical_context(),
    )

    evidence = result.item_results[0].guard_evidence
    assert result.status in {"BLOCKED", "REVIEW_REQUIRED"}
    assert result.submitted_count == 0
    assert evidence["broker_available_quantity"] == 1500
    assert evidence["broker_restricted_quantity"] == 1000
    assert evidence["sell_quantity_guard_status"] == "BROKER_AVAILABLE_INSUFFICIENT"


def test_phase17_bv9_demo_sell_still_requires_broker_readonly(tmp_path: Path) -> None:
    runtime_root, policy_path, _ = _runtime_sell_fixture(tmp_path, owned_quantity=2500, sell_quantity=1000, environment="demo")

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        capital_deployment_policy_path=policy_path,
    )

    evidence = result.item_results[0].guard_evidence
    assert result.status in {"BLOCKED", "REVIEW_REQUIRED"}
    assert result.submitted_count == 0
    assert evidence["broker_available_quantity_checked"] is False
    assert evidence["broker_available_quantity_source"] == "missing"
    assert evidence["sell_quantity_guard_status"] == "BROKER_AVAILABLE_MISSING"


def test_phase28_d48_historical_sell_unsupported_broker_category_fails_closed(tmp_path: Path) -> None:
    runtime_root, policy_path, adapter = _runtime_sell_fixture(
        tmp_path,
        owned_quantity=700,
        sell_quantity=100,
        listed_info={
            "code": "93990",
            "market": "スタンダード",
            "product_category": "021",
            "security_type": "021",
            "current_listed": True,
        },
        symbol="93990",
    )

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        submit_enabled=True,
        job="submit",
        adapter=adapter,
        capital_deployment_policy_path=policy_path,
        environment_context=_historical_context(),
    )

    evidence = result.item_results[0].guard_evidence
    assert result.status in {"BLOCKED", "REVIEW_REQUIRED"}
    assert result.submitted_count == 0
    assert evidence["current_quantity"] == 700
    assert evidence["quantity"] == 100
    assert evidence["broker_available_quantity"] is None
    assert evidence["broker_available_quantity_source"] == "historical_simulated_broker_authority"
    assert evidence["broker_available_quantity_reason"] == "BROKER_PRODUCT_CATEGORY_UNSUPPORTED"
    assert evidence["sell_quantity_guard_status"] == "BROKER_AVAILABLE_MISSING"


def _runtime_sell_fixture(
    tmp_path: Path,
    *,
    owned_quantity: float,
    sell_quantity: float,
    environment: str = "historical",
    listed_info: dict | None = None,
    symbol: str = SYMBOL,
) -> tuple[Path, Path, HistoricalSubmitAdapter]:
    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_market_data(tmp_path, symbol=symbol)
    policy_path = runtime_root / "runtime_state" / "policy" / "capital_deployment.json"
    _write_policy(policy_path)
    _write_safety(runtime_root, decision="ALLOW")
    _write_current(runtime_root, owned_quantity=owned_quantity, symbol=symbol)
    pending = _pending(environment, side="SELL", policy_path=policy_path)
    item = replace(
        pending.items[0],
        symbol=symbol,
        quantity=float(sell_quantity),
        estimated_amount=float(sell_quantity) * 3000.0,
        capital_allocation_amount=float(sell_quantity) * 3000.0,
        listed_info=listed_info
        or {"code": symbol, "market": "東証", "product_category": "011", "security_type": "011", "current_listed": True},
    )
    approval = replace(
        pending.approval,
        approved_order_conditions={
            "item-1": {
                "order_type": "MARKET",
                "target_session": BUSINESS_DATE,
                "quantity": float(sell_quantity),
                "side": "SELL",
                "issue_code": symbol,
                "limit_price": None,
                "time_in_force": "DAY",
                "price_condition": "MARKET",
            }
        },
    )
    pending = replace(pending, environment=environment, items=(item,), approval=approval)
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)
    adapter = HistoricalSubmitAdapter(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        evaluation_time=EVALUATION_TIME,
        pit_manifest_path=tmp_path / "pit_manifest.json",
        ohlcv_path=tmp_path / "ohlcv.parquet",
        listed_issues_path=tmp_path / "listed.parquet",
        raw_ohlcv_path=tmp_path / "raw_ohlcv.parquet",
    )
    return runtime_root, policy_path, adapter


def _write_current(runtime_root: Path, *, owned_quantity: float, symbol: str = SYMBOL) -> None:
    payload = {
        "cash": 1_000_000.0,
        "buying_power": 1_000_000.0,
        "positions": [
            {
                "symbol": symbol,
                "quantity": float(owned_quantity),
                "average_price": 2500.0,
                "market_value": float(owned_quantity) * 3000.0,
                "source": "runtime_v2_runtime_owned_fill_projection",
                "position_state_source": "runtime_owned_execution_ledger",
            }
        ],
        "market_value": float(owned_quantity) * 3000.0,
        "total_equity": 1_000_000.0 + float(owned_quantity) * 3000.0,
        "source": "runtime_v2_runtime_owned_fill_projection",
    }
    path = runtime_root / "persistent_ledger" / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    for name in ("orders", "executions", "cash", "events", "positions"):
        ledger = runtime_root / "persistent_ledger" / f"{name}.jsonl"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text("", encoding="utf-8")


def _append_order(runtime_root: Path, *, symbol: str, side: str, quantity: float) -> None:
    path = runtime_root / "persistent_ledger" / "orders.jsonl"
    record = {
        "record_type": "order",
        "environment": "historical",
        "symbol": symbol,
        "side": side,
        "quantity": float(quantity),
        "status": "ACCEPTED",
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def _write_market_data(root: Path, symbol: str = SYMBOL) -> None:
    import pandas as pd

    ohlcv = pd.DataFrame([{"Date": BUSINESS_DATE, "Code": symbol, "Open": 3000.0}])
    raw = pd.DataFrame([{"Date": BUSINESS_DATE, "Code": symbol, "AdjFactor": 1.0}])
    listed = pd.DataFrame([{"Date": BUSINESS_DATE, "Code": symbol}])
    ohlcv.to_parquet(root / "ohlcv.parquet", index=False)
    raw.to_parquet(root / "raw_ohlcv.parquet", index=False)
    listed.to_parquet(root / "listed.parquet", index=False)
    manifest = {
        "entries": [
            {
                "business_date": BUSINESS_DATE,
                "source_hashes": {"ohlcv_normalized": _sha(root / "ohlcv.parquet")},
            }
        ]
    }
    (root / "pit_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _sha(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
