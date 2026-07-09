import json
from pathlib import Path

from ai_fund_lab_v2.broker.settings import BrokerSettings
from ai_fund_lab_v2.runtime_v2.broker_adapter.fake_demo_submit import FakeRuntimeV2DemoSubmitAdapter
from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import run_execution_readonly_pipeline
from ai_fund_lab_v2.runtime_v2.planning.models import (
    AIPlanningSignal,
    CapitalAllocationSignal,
    PlanningInput,
    SafetySignal,
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
            safety_signals=(
                SafetySignal(
                    safety_id="sell-over-safety",
                    symbol="6522",
                    side="SELL",
                    allowed=True,
                    review_required=False,
                    blocked=False,
                    reason="allow",
                ),
            ),
        )
    )

    item = result.order_plan.items[0]
    assert item.blocked is True
    assert "sell quantity exceeds current position" in item.reason


def test_phase14e32_sell_submit_execution_current_report_notification_flow(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, positions=[_current_position("6522", quantity=100, price=102)])
    run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(SellExitDecision(symbol="6522", quantity=100, reason="exit signal"),),
    )

    submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
    )

    assert submit.status == "PASS"
    assert submit.submitted_count == 1
    assert submit.item_results[0].side == "SELL"

    execution = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        snapshot_provider=_sell_filled_snapshot,
    )

    executions = _read_jsonl(runtime_root / "persistent_ledger" / "executions.jsonl")
    assert execution.status == "PASS"
    assert execution.execution_equivalent_count == 1
    assert execution.asset_current_written is True
    assert execution.runtime_owned_projection_status == "PASS"
    assert execution.projected_position_count == 0
    assert executions[0]["side"] == "SELL"
    assert executions[0]["filled_quantity"] == 100

    state = _load_json(runtime_root / "persistent_ledger" / "state.json")

    assert state["positions"] == []
    assert state["cash"] == 1_000_000 + 10_200
    assert state["buying_power"] == state["cash"]
    assert state["market_value"] == 0
    assert state["total_equity"] == state["cash"]

    reports = build_markdown_reports(load_runtime_v2_report_context(runtime_root, business_date="2026-07-08"))
    summary = reports.summary
    assert summary["today_operation"]["sell_order_count"] == 1
    assert summary["today_operation"]["sell_filled_count"] == 1
    assert summary["current_portfolio"]["position_count"] == 0
    assert summary["notification"]["sell_filled_count"] == 1
    assert reports.public_scan["passed"] is True


def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    (root / "pending_order_plan").mkdir(parents=True)
    (root / "runtime_state").mkdir(parents=True)
    ledger = root / "persistent_ledger"
    ledger.mkdir(parents=True)
    for name in ("orders", "executions", "positions", "cash", "events"):
        (ledger / f"{name}.jsonl").write_text("", encoding="utf-8")
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


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
