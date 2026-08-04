import json
from pathlib import Path

from ai_fund_lab_v2.broker.settings import BrokerSettings
from ai_fund_lab_v2.runtime_v2.broker_adapter.fake_demo_submit import FakeRuntimeV2DemoSubmitAdapter
from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import run_execution_readonly_pipeline
from ai_fund_lab_v2.runtime_v2.planning.models import (
    AIPlanningSignal,
    CapitalAllocationSignal,
    PlanningInput,
    RuntimeSafetyContext,
)
from ai_fund_lab_v2.runtime_v2.planning.planner import build_order_plan
from ai_fund_lab_v2.runtime_v2.planning.sell_pipeline import (
    SellExitDecision,
    run_sell_planning_pending_pipeline,
)
from ai_fund_lab_v2.runtime_v2.report.markdown_writer import (
    build_markdown_reports,
    load_runtime_v2_report_context,
)
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline


def test_phase14e32_sell_planning_uses_current_position_as_only_sell_source(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, positions=[_current_position("6522", quantity=100, price=102)])

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(SellExitDecision(symbol="6522", quantity=100, reason="exit signal"),),
    )
    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")

    assert result.status == "PASS"
    assert result.current_position_count == 1
    assert result.selected_symbols == ("6522",)
    assert pending["state"] == "APPROVED"
    assert pending["items"][0]["side"] == "SELL"
    assert pending["items"][0]["symbol"] == "6522"
    assert pending["items"][0]["quantity"] == 100
    assert pending["approval"]["approval_status"] == "APPROVED"


def test_phase14e32_sell_planning_blocks_quantity_above_current_position(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    asset = _write_current_state(runtime_root, positions=[_current_position("6522", quantity=100, price=102)])

    result = build_order_plan(
        PlanningInput(
            mode="demo",
            environment="demo",
            business_date="2026-07-08",
            target_session_date="2026-07-08",
            asset_state=asset,
            ai_signals=(
                AIPlanningSignal(
                    signal_id="sell-over-quantity",
                    symbol="6522",
                    side="SELL",
                    rank=1,
                    score=1.0,
                    reason="exit signal",
                    source_ai="runtime_v2_exit_ai",
                ),
            ),
            capital_allocations=(
                CapitalAllocationSignal(
                    allocation_id="sell-over-allocation",
                    symbol="6522",
                    side="SELL",
                    allocated_amount=200 * 102,
                    max_amount=200 * 102,
                    cash_required=0,
                    reason="oversell fixture",
                    estimated_price=102,
                    price_source="current_sot_position_valuation",
                    price_as_of="2026-07-08",
                    price_confidence="current_sot",
                    price_required=True,
                ),
            ),
            runtime_safety=RuntimeSafetyContext(
                safety_decision_id="sell-over-safety",
                safety_policy_version="safety_test_v1",
                safety_source="test_phase14e32",
                safety_decision="ALLOW",
                safety_reason="allow",
                review_required=False,
                block_buy=False,
                block_sell=False,
                block_submit=False,
                halt_runtime=False,
                emergency_stop=False,
                generated_at="2026-07-08T00:00:00+09:00",
                expires_at="2026-07-09T00:00:00+09:00",
            ),
        )
    )

    item = result.order_plan.items[0]
    assert item.blocked is True
    assert "sell quantity exceeds current position" in item.reason
def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    (root / "pending_order_plan").mkdir(parents=True)
    (root / "runtime_state").mkdir(parents=True)
    ledger = root / "persistent_ledger"
    ledger.mkdir(parents=True)
    for name in ("orders", "executions", "positions", "cash", "events"):
        (ledger / f"{name}.jsonl").write_text("", encoding="utf-8")
    _write_safety_decision(root)
    return root


def _write_current_state(root: Path, *, positions):
    from ai_fund_lab_v2.runtime_v2.asset.models import CurrentAssetPosition, CurrentAssetState

    asset = CurrentAssetState(
        schema_version="1",
        asset_state_id="asset-e32",
        environment="demo",
        source="runtime_v2_runtime_owned_fill_projection",
        as_of="2026-07-08",
        positions=tuple(
            CurrentAssetPosition(
                symbol=str(item["symbol"]),
                quantity=float(item["quantity"]),
                average_price=float(item["average_price"]),
                market_value=float(item["market_value"]),
                source="fixture",
                as_of="2026-07-08",
            )
            for item in positions
        ),
        cash=1_000_000,
        buying_power=1_000_000,
        market_value=sum(float(item["market_value"]) for item in positions),
        total_equity=1_000_000 + sum(float(item["market_value"]) for item in positions),
        review_required=False,
        production_equivalent=False,
        current_state_confirmed_empty=False,
        current_positions_unknown=False,
        cash_unknown=False,
        buying_power_unknown=False,
        generated_from=("fixture",),
        created_at="2026-07-08",
    )
    payload = {
        "schema_version": asset.schema_version,
        "asset_state_id": asset.asset_state_id,
        "environment": asset.environment,
        "source": asset.source,
        "as_of": asset.as_of,
        "positions": positions,
        "cash": asset.cash,
        "buying_power": asset.buying_power,
        "market_value": asset.market_value,
        "total_equity": asset.total_equity,
        "review_required": False,
        "production_equivalent": False,
        "current_state_confirmed_empty": False,
        "current_positions_unknown": False,
        "cash_unknown": False,
        "buying_power_unknown": False,
        "runtime_evaluation_capital": 1_000_000,
        "generated_from": ["fixture"],
        "created_at": "2026-07-08",
        "updated_at": "2026-07-08",
    }
    _write_json(root / "persistent_ledger" / "state.json", payload)
    return asset


def _current_position(symbol: str, *, quantity: float, price: float) -> dict:
    return {
        "symbol": symbol,
        "quantity": quantity,
        "average_price": price,
        "market_value": quantity * price,
        "source": "fixture",
        "as_of": "2026-07-08",
    }


def _sell_filled_snapshot(**kwargs):
    snapshot_path = Path(kwargs["snapshot_path"])
    report_path = Path(kwargs["report_path"])
    _write_json(
        snapshot_path,
        {
            "generated_at": "2026-07-08T09:05:00+09:00",
            "orders": [
                {
                    "order_id_hash": "sell_order_6522",
                    "issue_code": "6522",
                    "side": "sell",
                    "quantity": "100",
                    "executed_quantity": "100",
                    "remaining_quantity": "0",
                    "status": "全部約定",
                    "as_of": "2026-07-08T09:05:00+09:00",
                }
            ],
            "executions": [],
            "positions": [
                {
                    "position_id": "position_6522_zero",
                    "issue_code": "6522",
                    "quantity": "0",
                    "average_price": "102",
                    "market_value": "0",
                }
            ],
            "buying_power": {
                "raw_clmid": "CLMZanKaiKanougaku",
                "cash_available": "19989800",
                "buying_power": "19989800",
                "currency": "JPY",
            },
            "health": {
                "orders": {"status": "PASS", "count": 1},
                "positions": {"status": "PASS", "count": 1},
                "executions": {"status": "PASS", "count": 0, "detail_attempted_count": 0},
            },
        },
    )
    _write_json(report_path, {"status": "PASS"})
    return type("SnapshotResult", (), {"status": "PASS"})()


def _demo_settings() -> BrokerSettings:
    return BrokerSettings(
        environment="demo",
        base_url="https://demo-kabuka.e-shiten.jp/e_api_v4r9",
        second_password_file="/tmp/phase14e32-second-password",
    )


def _write_policy(path: Path) -> Path:
    _write_json(
        path,
        {
            "policy_version": "capital_deployment_v1",
            "policy_source": str(path),
            "evaluation_capital": 1_000_000,
            "max_positions": 5,
            "min_order_amount": 0,
            "max_buy_order_amount": None,
            "max_sell_liquidation_amount": None,
            "buy_notional_policy": "derived_from_capital_allocation_and_constraints",
            "sell_liquidation_policy": "current_owned_available_quantity_policy",
            "manual_review_threshold": {
                "buy_amount": None,
                "sell_liquidation_amount": None,
            },
        },
    )
    return path


def _write_broker_positions_snapshot(root: Path, *, symbol: str, quantity: float, available_quantity: float) -> Path:
    path = root / "broker" / "snapshots" / "positions" / "positions-phase14e32.json"
    _write_json(
        path,
        {
            "kind": "positions",
            "source": "broker_readonly",
            "as_of": "2026-07-08T08:30:00+09:00",
            "review_required": False,
            "production_equivalent": True,
            "records": [
                {
                    "environment": "demo",
                    "source": "broker_readonly",
                    "as_of": "2026-07-08T08:30:00+09:00",
                    "account_type": "cash",
                    "issue_code": symbol,
                    "symbol": symbol,
                    "quantity": quantity,
                    "available_quantity": available_quantity,
                    "review_required": False,
                    "production_equivalent": True,
                }
            ],
        },
    )
    return path


def _load_policy(path: Path):
    from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import load_capital_deployment_policy

    return load_capital_deployment_policy(path)


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_safety_decision(root: Path) -> Path:
    path = root / "runtime_state" / "safety" / "latest_safety_decision.json"
    _write_json(
        path,
        {
            "safety_decision_id": "safety-phase14e32-fixture",
            "safety_policy_version": "safety_policy_v1",
            "safety_source": str(path),
            "business_date": "2026-07-08",
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "phase14e32 fixture safety allow",
            "review_required": False,
            "block_buy": False,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": "2026-07-08T08:00:00+09:00",
            "expires_at": "2026-07-08T15:00:00+09:00",
        },
    )
    return path
