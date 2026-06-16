from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.paper_trading.daily_inference_runner import run_daily_inference
from tests.paper_trading.test_phase9l2_daily_inference_runner import _write_l2_inputs


def test_phase9l2_order_plan_is_review_only_and_non_executable(tmp_path: Path) -> None:
    feature_root, quotes_path = _write_l2_inputs(tmp_path)

    result = run_daily_inference(
        decision_for="2026-06-15",
        data_until="2026-06-15",
        runtime_dir=tmp_path / ".runtime",
        reports_root=tmp_path / "reports",
        feature_root=feature_root,
        canonical_quotes_path=quotes_path,
        allow_initial_ledger=True,
    )

    order_plan = json.loads(Path(result.artifact_paths["order_plan"]).read_text(encoding="utf-8"))
    assert order_plan["executable"] is False
    assert order_plan["live_order_allowed"] is False
    assert order_plan["requires_human_review"] is True
    assert order_plan["sell_first_buy_after_fill"] is True
    assert all(item["executable"] is False for item in order_plan["items"])
    assert all(item["live_order_allowed"] is False for item in order_plan["items"])
    assert all(item["requires_human_review"] is True for item in order_plan["items"])
    assert result.prohibited_flags["broker_order_api_called"] is False
    assert result.prohibited_flags["open_d_started"] is False
    assert result.prohibited_flags["unlock_trade_called"] is False

