import json
from pathlib import Path

from ai_fund_lab_v2.safety_phase11.integrated_backtest_audit import (
    AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER,
    AUDIT_PROFILE_STRESS_INJECTION,
    FORBIDDEN_AUDIT_VALUES,
    IntegratedBacktestAuditConfig,
    run_integrated_backtest_audit,
)
from ai_fund_lab_v2.safety_phase11.models import SafetyState


def _run_fixture(tmp_path):
    return run_integrated_backtest_audit(
        IntegratedBacktestAuditConfig(
            period_id="fixture",
            start_date="2025-06-01",
            end_date="2025-12-31",
            output_subdir="fixture",
            reports_dir=tmp_path / "reports",
            docs_dir=tmp_path / "docs" / "phase_reports",
            max_days=190,
        )
    )


def _run_fixture_without_manual_approval(tmp_path):
    return run_integrated_backtest_audit(
        IntegratedBacktestAuditConfig(
            period_id="fixture_no_manual",
            start_date="2025-06-01",
            end_date="2025-12-31",
            output_subdir="fixture_no_manual",
            reports_dir=tmp_path / "reports",
            docs_dir=tmp_path / "docs" / "phase_reports",
            max_days=190,
            manual_approval_simulation=False,
            audit_profile=AUDIT_PROFILE_STRESS_INJECTION,
        )
    )


def _run_stress_fixture(tmp_path):
    return run_integrated_backtest_audit(
        IntegratedBacktestAuditConfig(
            period_id="fixture_stress",
            start_date="2025-06-01",
            end_date="2025-12-31",
            output_subdir="fixture_stress",
            reports_dir=tmp_path / "reports",
            docs_dir=tmp_path / "docs" / "phase_reports",
            max_days=190,
            audit_profile=AUDIT_PROFILE_STRESS_INJECTION,
        )
    )


def test_integrated_backtest_audit_runner_completes_with_small_fixture(tmp_path):
    result = _run_fixture(tmp_path)
    assert result.status == "PASS"
    assert result.business_day_count == len(result.daily_records)
    assert Path(result.summary_path).exists()
    assert Path(result.daily_path).exists()
    assert Path(result.trades_path).exists()
    assert result.performance["initial_cash"] == 1000000.0
    assert "final_equity" in result.performance
    assert result.flow_counts["fixed_4_code_stub_used"] is False
    assert result.flow_counts["candidate_universe_size"] >= 30
    assert result.flow_counts["candidate_count_total"] > result.business_day_count
    assert result.safety_behavior["audit_profile"] == "normal_market"
    assert result.flow_counts["periodic_mock_emergency_injection_enabled"] is False


def test_integrated_backtest_audit_calls_safety_every_day(tmp_path):
    result = _run_fixture(tmp_path)
    assert result.safety["safety_check_count"] == result.business_day_count
    assert (
        result.safety["ALLOW_count"]
        + result.safety["BLOCK_count"]
        + result.safety["REVIEW_REQUIRED_count"]
        + result.safety["EMERGENCY_STOP_count"]
    ) >= result.business_day_count


def test_integrated_backtest_audit_blocks_new_buy_during_buy_stop_and_emergency(tmp_path):
    result = _run_stress_fixture(tmp_path)
    buy_review_records = [
        row
        for row in result.daily_records
        if row.safety_state_before in {SafetyState.BUY_STOP, SafetyState.MARKET_STRESS, SafetyState.BUY_REVIEW_REQUIRED, SafetyState.BUY_OPPORTUNITY_REVIEW}
    ]
    emergency_records = [row for row in result.daily_records if row.safety_state_before in {SafetyState.SYSTEM_EMERGENCY_STOP, SafetyState.EMERGENCY_STOP}]
    assert buy_review_records
    assert emergency_records
    assert all(not row.order_submitted for row in buy_review_records if row.order_blocked_reason and row.safety_state_before is SafetyState.BUY_STOP)
    assert all(not row.order_submitted for row in emergency_records)
    assert result.safety_behavior["emergency_blocked_order_flow"] is True


def test_integrated_backtest_audit_recovery_never_auto_returns_normal(tmp_path):
    result = _run_fixture_without_manual_approval(tmp_path)
    recovery_records = [row for row in result.daily_records if row.safety_state_after is SafetyState.RECOVERY_CANDIDATE]
    assert recovery_records
    for before, after in zip(result.daily_records, result.daily_records[1:]):
        if before.safety_state_after is SafetyState.RECOVERY_CANDIDATE:
            assert after.safety_state_after is not SafetyState.NORMAL
    assert result.safety_behavior["recovery_candidate_did_not_auto_normal"] is True
    assert result.safety_behavior["manual_approval_required_for_normal"] is True
    assert result.safety_behavior["manual_approval_simulated"] is False


def test_integrated_backtest_audit_manual_approval_simulation_can_return_through_manual_approved(tmp_path):
    result = _run_stress_fixture(tmp_path)
    assert result.safety_behavior["manual_approval_simulated"] is True
    assert result.state_residency_days["MANUAL_APPROVED"] > 0
    for before, after in zip(result.daily_records, result.daily_records[1:]):
        assert not (
            before.safety_state_after is SafetyState.RECOVERY_CANDIDATE
            and after.safety_state_after is SafetyState.NORMAL
        )


def test_integrated_backtest_audit_integrity_flags_are_expected(tmp_path):
    result = _run_fixture(tmp_path)
    assert result.integrity["live_order_executed"] is False
    assert result.integrity["demo_order_executed"] is False
    assert result.integrity["production_order_executed"] is False
    assert result.integrity["auto_sell_executed"] is False
    assert result.integrity["auto_recovery_executed"] is False
    assert result.integrity["broker_api_connected"] is False
    assert result.integrity["broker_snapshot_updated"] is False
    assert result.integrity["paper_ledger_mutated_unexpectedly"] is False
    assert result.integrity["ai_training_data_mutated"] is False
    assert result.integrity["secret_or_raw_response_persisted"] is False


def test_integrated_backtest_audit_flow_metrics_are_separated(tmp_path):
    result = _run_fixture(tmp_path)
    assert result.flow_counts["orders_generated"] > 0
    assert result.flow_counts["orders_before_safety"] > 0
    assert result.flow_counts["buy_fill_count"] > 0
    assert result.flow_counts["sell_fill_count"] > 0
    assert result.flow_counts["position_open_count"] > 0
    assert result.flow_counts["position_close_count"] > 0
    assert result.performance["trade_count"] == result.flow_counts["buy_fill_count"] + result.flow_counts["sell_fill_count"]
    assert result.performance["round_trip_count"] == result.flow_counts["position_close_count"]
    assert result.performance["trade_count_definition"] == "buy_fill_count + sell_fill_count"
    assert result.performance["closed_trades_count"] == result.flow_counts["sell_fill_count"]
    assert result.performance["performance_metrics_placeholder"] is False
    assert result.performance["win_rate"] is not None
    assert result.performance["profit_factor"] is not None


def test_integrated_backtest_audit_normal_market_disables_periodic_emergency_injection(tmp_path):
    result = _run_fixture(tmp_path)
    assert result.safety_behavior["periodic_mock_emergency_injection_enabled"] is False
    assert result.state_residency_days["EMERGENCY_STOP"] == 0
    assert result.safety["market_crash_guard_count"] == 0
    assert result.safety_behavior["normal_market_mock_boolean_crash_triggered"] is False
    assert result.pass_conditions["emergency_stop_days_ratio_within_threshold"] is True
    assert result.pass_conditions["periodic_mock_emergency_injection_disabled"] is True


def test_integrated_backtest_audit_stress_profile_enables_intentional_injection(tmp_path):
    result = _run_stress_fixture(tmp_path)
    assert result.safety_behavior["audit_profile"] == AUDIT_PROFILE_STRESS_INJECTION
    assert result.safety_behavior["periodic_mock_emergency_injection_enabled"] is True
    assert result.state_residency_days["SYSTEM_EMERGENCY_STOP"] > 0
    assert result.pass_conditions["stress_profile_enabled"] is True
    assert result.pass_conditions["stress_injection_triggered_safety"] is True


def test_integrated_backtest_audit_market_crash_source_is_reported(tmp_path):
    result = _run_fixture(tmp_path)
    payload = json.loads(Path(result.summary_path).read_text(encoding="utf-8"))
    assert payload["market_crash_input"]["market_crash_source"] == "synthetic_none"
    assert payload["market_crash_input"]["is_synthetic"] is True
    assert payload["market_crash_input"]["market_crash"] is False
    assert payload["market_crash_input"]["severe_crash"] is False


def test_integrated_backtest_audit_output_redacts_secret_and_raw_values(tmp_path):
    result = _run_fixture(tmp_path)
    paths = [Path(result.summary_path), Path(result.daily_path), Path(result.trades_path), Path(result.phase_report_json_path), Path(result.phase_report_path)]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths if path.exists())
    for value in FORBIDDEN_AUDIT_VALUES:
        assert value not in combined
    payload = json.loads(Path(result.summary_path).read_text(encoding="utf-8"))
    assert payload["integrity"]["secret_or_raw_response_persisted"] is False


def test_integrated_backtest_audit_tmp_output_does_not_write_fixed_docs_path(tmp_path):
    result = _run_fixture(tmp_path)
    assert str(result.phase_report_path).startswith(str(tmp_path))
    assert Path(result.phase_report_path).exists()


def test_integrated_backtest_audit_mainline_paper_adapter_reuses_phase9_components(tmp_path):
    result = run_integrated_backtest_audit(
        IntegratedBacktestAuditConfig(
            period_id="fixture_mainline_adapter",
            start_date="2025-06-01",
            end_date="2025-08-31",
            output_subdir="fixture_mainline_adapter",
            reports_dir=tmp_path / "reports",
            docs_dir=tmp_path / "docs" / "phase_reports",
            max_days=12,
            audit_profile=AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER,
        )
    )
    reuse_map = result.safety_behavior["mainline_reuse_map"]
    assert result.safety_behavior["audit_profile"] == AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER
    assert reuse_map["candidate_source"].startswith("mainline_artifact")
    assert reuse_map["allocation_source"].startswith("CAP5")
    assert reuse_map["fill_source"] == "mainline_virtual_fill"
    assert reuse_map["ledger_source"] == "PaperTradingLedger"
    assert result.flow_counts["orders_generated"] > 0
    assert result.flow_counts["buy_fill_count"] > 0
    assert result.integrity["live_order_executed"] is False
    assert result.integrity["broker_api_connected"] is False
    assert Path(result.summary_path).exists()


def test_integrated_backtest_audit_mainline_adapter_safety_off_comparison_runs(tmp_path):
    result = run_integrated_backtest_audit(
        IntegratedBacktestAuditConfig(
            period_id="fixture_mainline_adapter_safety_off",
            start_date="2025-06-01",
            end_date="2025-08-31",
            output_subdir="fixture_mainline_adapter_safety_off",
            reports_dir=tmp_path / "reports",
            docs_dir=tmp_path / "docs" / "phase_reports",
            max_days=35,
            audit_profile=AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER,
            safety_enabled=False,
            max_holding_days=10,
        )
    )
    assert result.safety_behavior["safety_enabled"] is False
    assert result.flow_counts["orders_generated"] > 0
    assert result.flow_counts["sell_fill_count"] > 0
    assert result.integrity["auto_sell_executed"] is False
    assert result.integrity["auto_recovery_executed"] is False
