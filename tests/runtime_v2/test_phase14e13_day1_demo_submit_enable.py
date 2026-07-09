import plistlib
from dataclasses import replace
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.broker_adapter.capability import get_broker_capability
from ai_fund_lab_v2.runtime_v2.submit.guards import run_submit_preflight
from tests.runtime_v2.pending_fixtures import make_approved_pending_plan


PLIST_PATHS = {
    "morning": Path("tools/launchd/com.aifundlab.runtime_v2.morning.plist"),
    "submit": Path("tools/launchd/com.aifundlab.runtime_v2.submit.plist"),
    "execution": Path("tools/launchd/com.aifundlab.runtime_v2.execution.plist"),
    "market_refresh": Path("tools/launchd/com.aifundlab.runtime_v2.market_refresh.plist"),
}


def test_phase14e13_only_submit_job_has_submit_enabled_true():
    for job, path in PLIST_PATHS.items():
        plist = plistlib.loads(path.read_bytes())
        args = plist["ProgramArguments"]

        assert args[:3] == [
            "/usr/bin/python3",
            "-m",
            "ai_fund_lab_v2.runtime_v2.cli.run_daily_operation",
        ]
        assert args[args.index("--mode") + 1] == "demo"
        assert args[args.index("--job") + 1] == job
        assert args[args.index("--notification-mode") + 1] == "payload-only"

        expected_submit_enabled = "true" if job == "submit" else "false"
        assert args[args.index("--submit-enabled") + 1] == expected_submit_enabled

        joined = " ".join(args)
        assert "phase9" not in joined.lower()
        assert "run_phase14d" not in joined
        assert ".runtime/demo" not in joined


def test_phase14e13_demo_capability_and_9000_series_submit_guard_remain_enabled():
    capability = get_broker_capability("demo")
    assert capability.default_evaluation_capital == 1_000_000
    assert capability.cash_as_truth is False
    assert capability.positions_as_truth is False
    assert capability.supports_9000_series_orders is False

    plan = make_approved_pending_plan()
    item = replace(plan.items[0], symbol="9432")
    plan = replace(plan, items=(item,))
    result = run_submit_preflight(
        pending_plan=plan,
        approval_artifact=_approval_for(plan),
        approved_item_id=item.pending_item_id,
        existing_order_dedup_keys=set(),
        environment="demo",
        base_url_is_demo=True,
        base_url_is_production=False,
        live_order_allowed=True,
    )

    assert result.blocked is True
    assert result.reason == "symbol not supported by broker capability"


def _approval_for(plan):
    from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalArtifact, ApprovalStatus

    item = plan.items[0]
    return ApprovalArtifact(
        approval_id="approval-e13",
        approval_request_id="approval-request-e13",
        pending_plan_id=plan.pending_plan_id,
        order_plan_id=plan.source_order_plan.order_plan_id,
        status=ApprovalStatus.APPROVED,
        approved_item_ids=(item.pending_item_id,),
        rejected_item_ids=(),
        approval_hash=plan.approval.approval_hash,
        approved_at="2026-07-07T00:00:00Z",
        expires_at="2026-07-08T00:00:00Z",
        review_required=False,
        reason="phase14e13 test",
    )
