import json
from pathlib import Path

from ai_fund_lab_v2.safety_phase11.integration_dry_run import (
    FORBIDDEN_MOCK_VALUES,
    PHASE11G_SCENARIOS,
    IntegrationDryRunConfig,
    run_phase11g_integration_dry_run,
)
from ai_fund_lab_v2.safety_phase11.models import SafetyDecision, SafetyState


def _run(tmp_path):
    return run_phase11g_integration_dry_run(
        IntegrationDryRunConfig(
            business_date="2026-06-29",
            environment="test_dry_run",
            runtime_id="phase11g_test",
            reports_dir=tmp_path / "reports",
            runtime_dir=tmp_path / ".runtime",
        )
    )


def _by_name(summary):
    return {item.scenario_name: item for item in summary.scenario_results}


def test_phase11g_runs_all_10_scenarios(tmp_path):
    summary = _run(tmp_path)
    assert summary.status == "PHASE11G_SAFETY_INTEGRATION_DRY_RUN_COMPLETE"
    assert tuple(item.scenario_name for item in summary.scenario_results) == PHASE11G_SCENARIOS
    assert Path(summary.summary_report_path).exists()
    assert Path(summary.phase_report_path).exists()
    assert Path(summary.phase_report_json_path).exists()


def test_phase11g_scenario_expected_states(tmp_path):
    scenarios = _by_name(_run(tmp_path))

    normal = scenarios["normal"]
    assert normal.overall_decision is SafetyDecision.ALLOW
    assert normal.next_state is SafetyState.NORMAL

    warning = scenarios["individual_warning"]
    assert warning.overall_decision is SafetyDecision.REVIEW_REQUIRED
    assert warning.next_state is SafetyState.WARNING
    assert warning.monitor_result.review_items

    stop_loss = scenarios["stop_loss_candidate"]
    assert stop_loss.overall_decision is SafetyDecision.REVIEW_REQUIRED
    assert stop_loss.next_state is SafetyState.WARNING
    assert "new_buy_without_human_review" in _scenario_json(stop_loss)["blocked_actions"]
    assert stop_loss.monitor_result.review_items

    emergency = scenarios["emergency_candidate"]
    assert emergency.overall_decision is SafetyDecision.REVIEW_REQUIRED
    assert emergency.next_state is SafetyState.WARNING
    blocked = _scenario_json(emergency)["blocked_actions"]
    assert "new_buy_without_human_review" in blocked
    assert emergency.monitor_result.review_items

    market = scenarios["market_crash"]
    assert market.next_state is SafetyState.MARKET_STRESS
    assert "new_buy_without_human_review" in _scenario_json(market)["blocked_actions"]

    duplicate = scenarios["duplicate_active_order"]
    assert duplicate.overall_decision in {SafetyDecision.BLOCK, SafetyDecision.EMERGENCY_STOP}
    assert "DUPLICATE_ACTIVE_BUY_ORDER" in duplicate.monitor_result.monitor_summary["triggered_reason_codes"]

    stale = scenarios["stale_quote_snapshot"]
    assert stale.overall_decision in {SafetyDecision.BLOCK, SafetyDecision.REVIEW_REQUIRED, SafetyDecision.EMERGENCY_STOP}
    assert stale.next_state in {SafetyState.BUY_REVIEW_REQUIRED, SafetyState.SYSTEM_EMERGENCY_STOP, SafetyState.EMERGENCY_STOP}

    manual = scenarios["manual_emergency"]
    assert manual.next_state is SafetyState.SYSTEM_EMERGENCY_STOP
    manual_blocked = _scenario_json(manual)["blocked_actions"]
    assert {"new_buy", "new_sell_auto_execution", "retry", "automatic_recovery"}.issubset(set(manual_blocked))

    recovery = scenarios["recovery_candidate"]
    assert recovery.recovery_decision.recovery_candidate is True
    assert recovery.next_state is SafetyState.RECOVERY_CANDIDATE
    assert recovery.next_state is not SafetyState.NORMAL
    assert recovery.recovery_decision.auto_recovery_executed is False

    unlock = scenarios["manual_unlock"]
    assert unlock.recovery_decision.recovery_candidate is True
    assert unlock.manual_unlock_validation is not None
    assert unlock.manual_unlock_validation.valid is True
    assert unlock.manual_unlock_validation.next_state is SafetyState.MANUAL_APPROVED
    assert unlock.normal_return_validation is not None
    assert unlock.normal_return_validation.valid is True
    assert unlock.normal_return_validation.next_state is SafetyState.NORMAL


def test_phase11g_never_executes_auto_trade_sell_or_recovery(tmp_path):
    summary = _run(tmp_path)
    for item in summary.scenario_results:
        payload = _scenario_json(item)
        assert payload["auto_trade_executed"] is False
        assert payload["auto_sell_executed"] is False
        assert payload["auto_recovery_executed"] is False
        assert item.auto_trade_executed is False
        assert item.auto_sell_executed is False
        assert item.auto_recovery_executed is False


def test_phase11g_report_review_queue_and_event_outputs_redact_forbidden_values(tmp_path):
    summary = _run(tmp_path)
    paths = [Path(summary.summary_report_path), Path(summary.phase_report_path), Path(summary.phase_report_json_path)]
    for item in summary.scenario_results:
        paths.extend(
            [
                Path(item.scenario_report_path),
                Path(item.safety_report_path),
                Path(item.markdown_report_path),
                Path(item.review_queue_path),
                Path(item.runtime_review_queue_path),
            ]
        )
        paths.extend(Path(path) for path in item.event_paths)

    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths if path.exists())
    for value in FORBIDDEN_MOCK_VALUES:
        assert value not in combined
    assert "raw_response_saved" in combined
    assert "broker_api_connected" in combined


def test_phase11g_summary_confirms_no_external_or_runtime_side_effects(tmp_path):
    summary = _run(tmp_path)
    payload = json.loads(Path(summary.phase_report_json_path).read_text(encoding="utf-8"))
    assert payload["broker_api_connected"] is False
    assert payload["websocket_connected"] is False
    assert payload["demo_order_submitted"] is False
    assert payload["production_order_submitted"] is False
    assert payload["auto_sell_executed"] is False
    assert payload["auto_recovery_executed"] is False
    assert payload["runtime_behavior_changed"] is False
    assert payload["ai_learning_updated"] is False
    assert payload["persistence_protection"]["forbidden_value_leak_detected"] is False


def _scenario_json(result):
    return json.loads(Path(result.scenario_report_path).read_text(encoding="utf-8"))
