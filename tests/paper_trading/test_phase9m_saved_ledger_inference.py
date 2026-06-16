from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.paper_trading.daily_inference_runner import INFERENCE_READY, run_daily_inference
from ai_fund_lab_v2.paper_trading.initial_ledger import create_initial_ledger
from tests.paper_trading.test_phase9l2_daily_inference_runner import _write_l2_inputs


def test_saved_initial_ledger_can_drive_l2_inference_without_memory_warning(tmp_path: Path) -> None:
    feature_root, quotes_path = _write_l2_inputs(tmp_path)
    created = create_initial_ledger(
        initial_cash=Decimal("1000000"),
        currency="JPY",
        ledger_root=tmp_path / ".runtime" / "phase9" / "ledger",
        start_date="2026-06-16",
    )

    result = run_daily_inference(
        decision_for="2026-06-15",
        data_until="2026-06-15",
        runtime_dir=tmp_path / ".runtime",
        reports_root=tmp_path / "reports",
        feature_root=feature_root,
        canonical_quotes_path=quotes_path,
        ledger_path=Path(created.latest_path),
    )

    assert result.status == INFERENCE_READY
    assert "initial_ledger_in_memory_only" not in result.warnings
    assert not any(result.prohibited_flags.values())
    assert Path(result.artifact_paths["order_plan"]).is_file()

