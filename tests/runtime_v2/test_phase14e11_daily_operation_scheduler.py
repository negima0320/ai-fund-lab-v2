import json
import plistlib
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main


PLISTS = {
    "morning": {
        "path": Path("tools/launchd/com.aifundlab.runtime_v2.morning.plist"),
        "label": "com.aifundlab.runtime_v2.morning",
        "hour": 8,
        "minute": 45,
        "submit_enabled": "false",
        "required_stages": {"ai_inference", "planning", "approval", "pending_generation", "submit_stop"},
        "forbidden_stages": {"demo_submit_guarded_checkpoint"},
    },
    "submit": {
        "path": Path("tools/launchd/com.aifundlab.runtime_v2.submit.plist"),
        "label": "com.aifundlab.runtime_v2.submit",
        "hour": 8,
        "minute": 58,
        "submit_enabled": "true",
        "required_stages": {"pending", "approval_recheck", "safety", "demo_submit_guarded_checkpoint"},
        "forbidden_stages": {"ai_inference", "jquants_market_refresh"},
    },
    "execution": {
        "path": Path("tools/launchd/com.aifundlab.runtime_v2.execution.plist"),
        "label": "com.aifundlab.runtime_v2.execution",
        "hour": 9,
        "minute": 5,
        "submit_enabled": "false",
        "required_stages": {"execution_reflection", "ledger", "asset", "reconcile", "markdown_public_report_checkpoint"},
        "forbidden_stages": {"ai_inference", "demo_submit_guarded_checkpoint"},
    },
    "market_refresh": {
        "path": Path("tools/launchd/com.aifundlab.runtime_v2.market_refresh.plist"),
        "label": "com.aifundlab.runtime_v2.market_refresh",
        "hour": 15,
        "minute": 30,
        "submit_enabled": "false",
        "required_stages": {"jquants_market_refresh", "canonical_update", "feature_refresh", "ai_inference_blocked"},
        "forbidden_stages": {"ai_inference", "demo_submit_guarded_checkpoint"},
    },
}


def test_phase14e11_launchd_plists_call_runtime_v2_cli_only():
    for job, expected in PLISTS.items():
        plist = plistlib.loads(expected["path"].read_bytes())
        args = plist["ProgramArguments"]
        joined = " ".join(args)

        assert plist["Label"] == expected["label"]
        assert args[:3] == [
            "/usr/bin/python3",
            "-m",
            "ai_fund_lab_v2.runtime_v2.cli.run_daily_operation",
        ]
        assert args[args.index("--mode") + 1] == "demo"
        assert args[args.index("--job") + 1] == job
        assert args[args.index("--submit-enabled") + 1] == expected["submit_enabled"]
        assert args[args.index("--notification-mode") + 1] == "payload-only"
        assert "--stop-on-review-required" in args
        assert "--stop-on-blocked" in args
        assert ".runtime/demo" not in joined
        assert "phase9" not in joined.lower()
        assert "run_phase14d" not in joined

        schedule = plist["StartCalendarInterval"]
        assert isinstance(schedule, list)
        assert {entry["Weekday"] for entry in schedule} == {2, 3, 4, 5, 6}
        assert {entry["Hour"] for entry in schedule} == {expected["hour"]}
        assert {entry["Minute"] for entry in schedule} == {expected["minute"]}
        assert plist["StandardOutPath"].endswith(".out.log")
        assert plist["StandardErrorPath"].endswith(".err.log")


def test_phase14e11_cli_runs_all_scheduler_jobs_without_external_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "ai_fund_lab_v2.runtime_v2.cli.run_daily_operation.run_execution_readonly_pipeline",
        _fake_execution_readonly_pipeline,
    )
    monkeypatch.setattr(
        "ai_fund_lab_v2.runtime_v2.cli.run_daily_operation.evaluate_runtime_data_readiness",
        _fake_data_readiness_ready,
    )
    monkeypatch.setattr(
        "ai_fund_lab_v2.runtime_v2.cli.run_daily_operation.run_runtime_v2_market_refresh_pipeline",
        _fake_market_refresh_pipeline,
    )
    monkeypatch.setattr(
        "ai_fund_lab_v2.runtime_v2.cli.run_daily_operation.run_morning_ai_planning_pending_pipeline",
        _fake_morning_pipeline,
    )
    monkeypatch.setattr(
        "ai_fund_lab_v2.runtime_v2.cli.run_daily_operation.produce_buy_ai_decisions",
        _fake_buy_ai_decisions,
    )
    for job, expected in PLISTS.items():
        job_root = tmp_path / job
        runtime_root = _write_fixed_current(job_root / ".runtime")
        policy_path = _write_policy(job_root / "capital_deployment_policy.json")

        exit_code = main(
            [
                "--mode",
                "demo",
                "--job",
                job,
                "--business-date",
                "2026-07-07",
                "--submit-enabled",
                "false",
                "--notification-mode",
                "payload-only",
                "--stop-on-review-required",
                "--stop-on-blocked",
                "--runtime-root",
                str(runtime_root),
                "--reports-root",
                str(job_root / "reports" / "runtime_v2"),
                "--public-reports-root",
                str(job_root / "reports" / "public" / "runtime_v2"),
                "--manifest-root",
                str(job_root / ".runtime" / "runtime_state" / "run_manifest"),
                "--log-root",
                str(job_root / ".runtime" / "runtime_state" / "logs"),
                "--capital-deployment-policy",
                str(policy_path),
            ]
        )

        assert exit_code == 0
        manifests = sorted((job_root / ".runtime" / "runtime_state" / "run_manifest" / "2026-07-07").glob("*.json"))
        assert len(manifests) == 1
        manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
        stage_names = {stage["name"] for stage in manifest["stages"]}

        assert manifest["job"] == job
        assert manifest["mode"] == "demo"
        assert manifest["submit_enabled"] is False
        assert manifest["notification_mode"] == "payload-only"
        assert expected["required_stages"] <= stage_names
        assert not expected["forbidden_stages"] & stage_names
        assert manifest["prohibited_actions"]["demo_submit_executed"] is False
        assert manifest["prohibited_actions"]["production_order_executed"] is False
        assert manifest["prohibited_actions"]["notification_sent"] is False
        assert manifest["prohibited_actions"]["phase9_runtime_called"] is False
        assert manifest["prohibited_actions"]["phase9_writer_called"] is False
        assert manifest["prohibited_actions"]["mode_rooted_current_used"] is False
        assert (job_root / "reports" / "public" / "runtime_v2" / "latest.md").exists()


def test_phase14e11_cli_blocks_non_payload_notification_mode(tmp_path):
    runtime_root = _write_fixed_current(tmp_path / ".runtime")

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "morning",
            "--business-date",
            "2026-07-07",
            "--submit-enabled",
            "false",
            "--notification-mode",
            "send-enabled",
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

    assert exit_code == 40


def test_phase14e11_cli_allows_submit_enabled_true_for_submit_job_only(tmp_path, monkeypatch):
    # Data Readiness is covered by dedicated gate tests; this scheduler test
    # isolates the submit-enabled guard path.
    monkeypatch.setattr(
        "ai_fund_lab_v2.runtime_v2.cli.run_daily_operation.evaluate_runtime_data_readiness",
        _fake_data_readiness_ready,
    )
    submit_root = tmp_path / "submit"
    runtime_root = _write_fixed_current(submit_root / ".runtime")
    submit_policy_path = _write_policy(submit_root / "capital_deployment_policy.json")

    submit_exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "submit",
            "--business-date",
            "2026-07-07",
            "--submit-enabled",
            "true",
            "--notification-mode",
            "payload-only",
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(submit_root / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(submit_root / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(submit_root / ".runtime" / "runtime_state" / "run_manifest"),
            "--log-root",
            str(submit_root / ".runtime" / "runtime_state" / "logs"),
            "--capital-deployment-policy",
            str(submit_policy_path),
        ]
    )

    morning_root = tmp_path / "morning"
    morning_runtime_root = _write_fixed_current(morning_root / ".runtime")
    morning_exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "morning",
            "--business-date",
            "2026-07-07",
            "--submit-enabled",
            "true",
            "--notification-mode",
            "payload-only",
            "--runtime-root",
            str(morning_runtime_root),
            "--reports-root",
            str(morning_root / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(morning_root / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(morning_root / ".runtime" / "runtime_state" / "run_manifest"),
            "--log-root",
            str(morning_root / ".runtime" / "runtime_state" / "logs"),
        ]
    )

    assert submit_exit_code == 10
    assert morning_exit_code == 40


def _write_fixed_current(root: Path) -> Path:
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-e11",
            "environment": "demo",
            "updated_at": "2026-07-07T00:00:00Z",
            "positions": [],
            "cash": 1000000.0,
            "buying_power": 1000000.0,
            "market_value": 0.0,
            "total_equity": 1000000.0,
            "source": "phase14e8_demo_operation_initial_state",
            "review_required": False,
            "current_state_confirmed_empty": True,
            "cash_confirmed": True,
            "buying_power_confirmed": True,
        },
    )
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "1",
            "pending_plan_id": "pending-e11",
            "state": "CONSUMED",
            "environment": "demo",
            "created_at": "2026-07-07T00:00:00Z",
            "updated_at": "2026-07-07T00:00:00Z",
            "items": [],
        },
    )
    _write_json(
        root / "runtime_state" / "current_state.json",
        {
            "schema_version": "1",
            "runtime_id": "runtime-v2-demo",
            "run_id": "phase14e11-test",
            "state": "CURRENT_STATE_LOADED",
            "environment": "demo",
            "updated_at": "2026-07-07T00:00:00Z",
        },
    )
    _write_jsonl(root / "persistent_ledger" / "orders.jsonl", [])
    _write_jsonl(root / "persistent_ledger" / "executions.jsonl", [])
    _write_jsonl(root / "persistent_ledger" / "positions.jsonl", [])
    _write_jsonl(root / "persistent_ledger" / "cash.jsonl", [])
    _write_jsonl(root / "persistent_ledger" / "events.jsonl", [])
    return root


def _fake_market_refresh_pipeline(**kwargs):
    feature_root = Path(kwargs["operations_root"]) / "feature_artifacts" / kwargs["business_date"]
    artifacts = {
        name: str(feature_root / name)
        for name in (
            "candidate_features.parquet",
            "opportunity_feature_input.parquet",
            "position_feature_input.parquet",
            "capital_policy_input.parquet",
        )
    }
    return type(
        "MarketRefreshResult",
        (),
        {
            "status": "PASS",
            "reason": "fake market refresh",
            "market_evidence_status": "READY",
            "market_evidence_reason": "fake_market_evidence_ready",
            "market_evidence_path": str(feature_root.parent / "market" / "market_evidence.json"),
            "market_evidence_latest_pointer_path": str(feature_root.parent / "market" / "latest.json"),
            "market_evidence_history_artifact_path": str(feature_root.parent / "market" / "history.json"),
            "market_date": kwargs["business_date"],
            "latest_expected_trading_date": kwargs["business_date"],
            "latest_available_market_date": kwargs["business_date"],
            "market_freshness_status": "READY",
            "quote_status": "READY",
            "quote_count": 1,
            "missing_quote_count": 0,
            "market_summary_status": "READY",
            "publication_status": "READY",
            "provider_status": "NOT_CALLED",
            "generated_feature_artifacts": artifacts,
            "feature_artifact_dir": str(feature_root),
            "to_stage_details": lambda self: {
                "status": "PASS",
                "generated_feature_artifacts": artifacts,
                "feature_artifact_dir": str(feature_root),
            },
        },
    )()


def _write_policy(path: Path) -> Path:
    _write_json(
        path,
        {
            "policy_version": "capital_deployment_v1",
            "policy_source": str(path),
            "evaluation_capital": 1_000_000,
            "target_investment_ratio": 0.85,
            "cash_buffer": 0.05,
            "max_exposure": 850_000,
            "max_position_weight": 0.2,
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


def _write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


class _FakeExecutionReadOnlyResult:
    status = "PASS"
    reason = "test execution readonly connected"

    def to_stage_details(self):
        return {
            "orderlist_readonly_connected": True,
            "execution_reflection_connected": True,
            "ledger_connected": True,
            "asset_connected": True,
            "reconcile_status": "PASS",
        }


def _fake_execution_readonly_pipeline(**kwargs):
    return _FakeExecutionReadOnlyResult()


class _FakeMorningResult:
    status = "PASS"
    reason = ""
    selected_symbols = ("7203",)

    def to_stage_details(self):
        return {
            "status": "PASS",
            "reason": "",
            "evaluation_capital": 1_000_000,
            "selected_symbols": list(self.selected_symbols),
        }


def _fake_morning_pipeline(**kwargs):
    return _FakeMorningResult()


class _FakeBuyAIResult:
    status = "PASS"
    reason = ""
    ai_signals = ()

    def to_manifest_fields(self):
        return {
            "buy_ai_status": self.status,
            "buy_ai_reason": self.reason,
            "candidate_count": 0,
            "opportunity_count": 0,
            "selected_rank_count": 0,
        }


def _fake_buy_ai_decisions(**kwargs):
    return _FakeBuyAIResult()


class _FakeDataReadinessReady:
    status = "READY"
    reason = "test data readiness ready"
    artifact_path = "test-data-readiness.json"
    payload = {
        "overall_status": "READY",
        "readiness_scope": "test_scheduler",
        "review_reasons": [],
        "halt_reasons": [],
        "next_operator_action": "continue",
    }

    def to_manifest_fields(self):
        return {
            "data_readiness_status": self.status,
            "data_readiness_scope": self.payload["readiness_scope"],
            "data_readiness_artifact_path": self.artifact_path,
            "data_readiness_review_reasons": [],
            "data_readiness_halt_reasons": [],
            "data_readiness_next_operator_action": "continue",
        }


def _fake_data_readiness_ready(**kwargs):
    return _FakeDataReadinessReady()
