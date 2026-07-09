from pathlib import Path

from ai_fund_lab_v2.runtime_v2.demo_buy import run_demo_buy_single_order_guarded_test


def test_phase14d_guard_blocks_production_before_broker_api(tmp_path):
    result = run_demo_buy_single_order_guarded_test(
        root=tmp_path / "runtime",
        reports_dir=tmp_path / "reports",
        docs_report_path=tmp_path / "phase14d.md",
        json_report_path=tmp_path / "phase14d.json",
        environment="production",
        base_url_is_demo=False,
        base_url_is_production=True,
        second_password_file_configured=False,
    )

    assert result.final_decision == "PHASE14D_REVIEW_REQUIRED"
    assert result.production_order_executed is False
    assert result.production_broker_api_write_executed is False
    assert result.broker_api_called is False
    assert result.demo_submit_executed is False
    assert "environment guard failure" in result.blocked_reasons
    assert Path(result.pending_plan_path).exists()
    assert Path(result.approval_artifact_path).exists()
