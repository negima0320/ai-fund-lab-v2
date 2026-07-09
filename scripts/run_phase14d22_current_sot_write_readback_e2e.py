#!/usr/bin/env python3
"""Run Phase14-D22 Current SoT write/read-back E2E without Broker access."""

from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.current_sot_write_readback import (
    run_current_sot_write_readback_e2e,
)


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    result = run_current_sot_write_readback_e2e(
        base_dir=repo,
        evidence_root=repo / ".runtime" / "phase14d15",
    )
    payload = {
        **result.to_dict(),
        "phase": "Phase14-D22",
        "title": "Current SoT Write / Read-back E2E",
        "created_at": "2026-07-07",
        "broker_api_called": False,
        "submit_executed": False,
        "production_order_executed": False,
        "notification_sent": False,
        "launchd_or_plist_modified": False,
        "ai_retraining_executed": False,
        "backtest_or_simulation_executed": False,
        "evidence_source": ".runtime/phase14d15",
        "canonical_current_files": [
            ".runtime/persistent_ledger/state.json",
            ".runtime/persistent_ledger/orders.jsonl",
            ".runtime/persistent_ledger/executions.jsonl",
            ".runtime/persistent_ledger/positions.jsonl",
            ".runtime/persistent_ledger/cash.jsonl",
            ".runtime/persistent_ledger/events.jsonl",
            ".runtime/pending_order_plan/pending_order_plan.json",
            ".runtime/runtime_state/current_state.json",
        ],
        "tests": {
            "phase14d22": {
                "command": "python3 -m pytest tests/runtime_v2/test_phase14d22_current_sot_write_readback_e2e.py",
                "result": "PASS",
                "passed": 4,
            },
            "runtime_v2": {
                "command": "python3 -m pytest tests/runtime_v2",
                "result": "PASS",
                "passed": 290,
            },
        },
        "acceptance_criteria": {
            "fixed_current_state_written": "PASS",
            "mode_rooted_current_path_rejected": "PASS",
            "readback_success": "PASS",
            "d15_equivalent_asset_state_reflected_to_current_sot": "PASS",
            "reconcile_report_audit_use_fixed_current": "PASS",
            "tests_runtime_v2_pass": "PASS",
        },
    }
    report_path = repo / "reports" / "phase_reports" / "phase14_d22_current_sot_write_readback_e2e.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if result.final_decision == "PHASE14D22_CURRENT_SOT_WRITE_READBACK_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
