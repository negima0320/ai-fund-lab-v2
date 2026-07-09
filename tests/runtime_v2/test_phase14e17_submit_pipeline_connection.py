import json
from pathlib import Path

from ai_fund_lab_v2.broker.settings import BrokerSettings
from ai_fund_lab_v2.runtime_v2.cli import run_daily_operation
from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalArtifact, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.broker_adapter.capability import get_broker_capability, is_symbol_allowed_by_capability
from ai_fund_lab_v2.runtime_v2.broker_adapter.fake_demo_submit import FakeRuntimeV2DemoSubmitAdapter
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.submit.pipeline import SubmitItemResult, SubmitPipelineResult, run_submit_pipeline


def test_phase14e17_submit_pipeline_submits_all_approved_pending_items(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    pending = _approved_pending(("65220", "78780", "68970", "63270", "45910"))
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
    )

    updated = json.loads((runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))
    orders = _read_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl")

    assert result.status == "PASS"
    assert result.demo_submit_executed is True
    assert result.submitted_count == 5
    assert result.accepted_count == 5
    assert result.rejected_count == 0
    assert result.unknown_count == 0
    assert result.blocked_count == 0
    assert result.submitted_symbols == ("65220", "78780", "68970", "63270", "45910")
    assert len(result.submitted_order_ids) == 5
    assert len(result.ledger_order_record_ids) == 5
    assert updated["state"] == "CONSUMED"
    assert updated["consume"]["consumed"] is True
    assert len(updated["consume"]["submitted_order_ids"]) == 5
    assert len(orders) == 5
    assert {order["source"] for order in orders} == {"runtime_v2_submit_pipeline"}
    assert all(order["raw_request_saved"] is False for order in (updated,))


def test_phase14e17_submit_pipeline_blocks_demo_9000_series_before_submit(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    pending = _approved_pending(("9432",))
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
    )

    orders = _read_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl")

    assert result.status == "BLOCKED"
    assert result.demo_submit_executed is False
    assert result.submitted_count == 0
    assert result.blocked_count == 1
    assert result.item_results[0].reason == "symbol not supported by broker capability"
    assert orders == []


def test_phase14e17_production_capability_does_not_block_9000_series():
    production = get_broker_capability("production")
    demo = get_broker_capability("demo")

    assert is_symbol_allowed_by_capability("9432", production) is True
    assert is_symbol_allowed_by_capability("9432", demo) is False


def test_phase14e17_cli_submit_job_records_submit_pipeline_stage(monkeypatch, tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_asset_state(runtime_root)
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", _approved_pending(("7203",)))

    def fake_submit_pipeline(**kwargs):
        return SubmitPipelineResult(
            status="PASS",
            reason="submitted",
            pending_plan_id="pending-test",
            pending_path=str(runtime_root / "pending_order_plan" / "pending_order_plan.json"),
            orders_ledger_path=str(runtime_root / "persistent_ledger" / "orders.jsonl"),
            demo_submit_executed=True,
            submitted_count=1,
            accepted_count=1,
            rejected_count=0,
            unknown_count=0,
            blocked_count=0,
            pending_consumed=True,
            submitted_order_ids=("sha256:order",),
            ledger_order_record_ids=("ledger-order-1",),
            submitted_symbols=("7203",),
            item_results=(
                SubmitItemResult(
                    pending_item_id="item-1",
                    symbol="7203",
                    side="BUY",
                    quantity=100,
                    preflight_status="PASS",
                    submit_status="ACCEPTED",
                    submitted=True,
                    accepted=True,
                    rejected=False,
                    unknown=False,
                    blocked=False,
                    review_required=False,
                    broker_order_id_hash="sha256:order",
                    ledger_order_record_id="ledger-order-1",
                    reason="fake",
                    issue_code_normalization={"original_symbol": "7203", "broker_issue_code": "7203"},
                    response_classification={"business_classification": "ACCEPTED"},
                    configuration_diagnostic={},
                    next_action="",
                ),
            ),
        )

    monkeypatch.setattr(run_daily_operation, "run_submit_pipeline", fake_submit_pipeline)

    exit_code = run_daily_operation.main(
        [
            "--mode",
            "demo",
            "--job",
            "submit",
            "--business-date",
            "2026-07-08",
            "--submit-enabled",
            "true",
            "--notification-mode",
            "payload-only",
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(tmp_path / ".runtime" / "runtime_state" / "run_manifest"),
            "--log-root",
            str(tmp_path / ".runtime" / "runtime_state" / "logs"),
        ]
    )
    manifest = json.loads(
        next((tmp_path / ".runtime" / "runtime_state" / "run_manifest" / "2026-07-08").glob("*.json")).read_text(
            encoding="utf-8"
        )
    )
    submit_stage = next(stage for stage in manifest["stages"] if stage["name"] == "runtime_v2_submit_pipeline")

    assert exit_code == 0
    assert submit_stage["status"] == "PASS"
    assert submit_stage["details"]["submitted_count"] == 1
    assert manifest["prohibited_actions"]["demo_submit_executed"] is True


def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    (root / "pending_order_plan").mkdir(parents=True)
    ledger = root / "persistent_ledger"
    ledger.mkdir(parents=True)
    for name in ("orders", "executions", "positions", "cash", "events"):
        (ledger / f"{name}.jsonl").write_text("", encoding="utf-8")
    return root


def _write_asset_state(root: Path) -> None:
    payload = {
        "schema_version": "1",
        "asset_state_id": "asset-e17",
        "environment": "demo",
        "source": "phase14e8_demo_operation_initial_state",
        "as_of": "2026-07-08",
        "positions": [],
        "cash": 1_000_000.0,
        "buying_power": 1_000_000.0,
        "market_value": 0,
        "total_equity": 1_000_000.0,
        "review_required": False,
        "production_equivalent": False,
        "current_state_confirmed_empty": True,
        "current_positions_unknown": False,
        "cash_unknown": False,
        "buying_power_unknown": False,
        "generated_from": ["fixture"],
        "created_at": "2026-07-08",
        "updated_at": "2026-07-08",
    }
    (root / "persistent_ledger" / "state.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _approved_pending(symbols: tuple[str, ...]):
    items = tuple(
        PendingOrderItem(
            pending_item_id=f"item-{index}",
            symbol=symbol,
            side="BUY",
            quantity=100.0,
            order_type="MARKET",
            estimated_price=1000.0,
            estimated_amount=100000.0,
            approved=False,
            state="CREATED",
            listed_info={
                "code": symbol,
                "market": "プライム",
                "product_category": "011",
                "security_type": "011",
                "current_listed": True,
            },
        )
        for index, symbol in enumerate(symbols, start=1)
    )
    pending = promote_order_plan_to_pending(
        order_plan_id="order-plan-e17",
        source_order_plan_path=".runtime/runtime_state/morning_pipeline/2026-07-08/order_plan.json",
        source_order_plan_hash="sha256:order-plan-e17",
        environment="demo",
        plan_created_date="2026-07-08",
        intended_submit_date="2026-07-08",
        target_session_date="2026-07-08",
        items=items,
    )
    approval = ApprovalArtifact(
        approval_id="approval-e17",
        approval_request_id="approval-request-e17",
        pending_plan_id=pending.pending_plan_id,
        order_plan_id=pending.source_order_plan.order_plan_id,
        status=ApprovalStatus.APPROVED,
        approved_item_ids=tuple(item.pending_item_id for item in pending.items),
        rejected_item_ids=(),
        approval_hash="sha256:approval-e17",
        approved_at="2026-07-08T08:45:00+09:00",
        expires_at="2026-07-08T15:00:00+09:00",
        review_required=False,
        reason="test approval",
    )
    return link_approval_to_pending(pending_plan=pending, approval_artifact=approval)


def _demo_settings() -> BrokerSettings:
    return BrokerSettings(
        environment="demo",
        base_url="https://demo-kabuka.e-shiten.jp/e_api_v4r9",
        second_password_file="/tmp/phase14e17-second-password",
    )


def _read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
