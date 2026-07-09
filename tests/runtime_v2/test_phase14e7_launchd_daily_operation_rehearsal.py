import json
import plistlib
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main


PLIST_PATH = Path("tools/launchd/com.aifundlab.runtime_v2.daily_operation_rehearsal.plist")


def test_launchd_rehearsal_plist_starts_runtime_v2_cli_only():
    plist = plistlib.loads(PLIST_PATH.read_bytes())
    args = plist["ProgramArguments"]
    joined = " ".join(args)

    assert plist["Label"] == "com.aifundlab.runtime_v2.daily_operation_rehearsal"
    assert args[:3] == [
        "/usr/bin/python3",
        "-m",
        "ai_fund_lab_v2.runtime_v2.cli.run_daily_operation",
    ]
    assert "--mode" in args
    assert args[args.index("--mode") + 1] == "demo"
    assert "--submit-enabled" in args
    assert args[args.index("--submit-enabled") + 1] == "false"
    assert "--notification-mode" in args
    assert args[args.index("--notification-mode") + 1] == "payload-only"
    assert "--stop-on-review-required" in args
    assert "--stop-on-blocked" in args
    assert "run_phase14d" not in joined
    assert "run_phase9" not in joined
    assert "run_daily_report.py" not in joined
    assert ".runtime/demo" not in joined
    assert plist["StandardOutPath"].endswith(".out.log")
    assert plist["StandardErrorPath"].endswith(".err.log")


def test_daily_operation_cli_writes_manifest_reports_and_latest_public_report(tmp_path):
    runtime_root = _write_fixed_current(tmp_path / ".runtime")

    exit_code = main(
        [
            "--mode",
            "demo",
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
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(tmp_path / ".runtime" / "runtime_state" / "run_manifest"),
            "--log-root",
            str(tmp_path / ".runtime" / "runtime_state" / "logs"),
        ]
    )

    assert exit_code == 0
    manifests = sorted((tmp_path / ".runtime" / "runtime_state" / "run_manifest" / "2026-07-07").glob("*.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    stage_names = {stage["name"] for stage in manifest["stages"]}

    assert manifest["exit_code"] == 0
    assert manifest["submit_enabled"] is False
    assert manifest["notification_mode"] == "payload-only"
    assert manifest["prohibited_actions"]["demo_submit_executed"] is False
    assert manifest["prohibited_actions"]["production_order_executed"] is False
    assert manifest["prohibited_actions"]["notification_sent"] is False
    assert manifest["prohibited_actions"]["phase_artifact_used_as_current"] is False
    assert manifest["prohibited_actions"]["mode_rooted_current_used"] is False
    assert "current_sot_preflight" in stage_names
    assert "markdown_public_report" in stage_names
    assert "audit" in stage_names
    assert (tmp_path / "reports" / "public" / "runtime_v2" / "latest.md").exists()
    assert (tmp_path / "reports" / "runtime_v2" / "2026-07-07" / "runtime_report.md").exists()


def test_daily_operation_cli_blocks_submit_enabled(tmp_path):
    runtime_root = _write_fixed_current(tmp_path / ".runtime")

    exit_code = main(
        [
            "--mode",
            "demo",
            "--business-date",
            "2026-07-07",
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

    assert exit_code == 40


def _write_fixed_current(root: Path) -> Path:
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-e7",
            "environment": "demo",
            "updated_at": "2026-07-07T00:00:00Z",
            "positions": [{"symbol": "7203", "quantity": 0}],
            "cash": 19999648.0,
            "buying_power": 19999648.0,
            "source": "broker_positions",
            "review_required": False,
        },
    )
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "1",
            "pending_plan_id": "pending-e7",
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
            "run_id": "phase14e7-test",
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


def _write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
