from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "phase18x_accepted_atomic_buy_ai_bundle_authority_approval.py"


def load_module():
    spec = importlib.util.spec_from_file_location("phase18x_authority", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_phase18x_authority_approval_blocks_without_mutating_registry_or_runtime_state() -> None:
    module = load_module()
    before = module.snapshot_authority()
    report = module.build_report()
    after = module.snapshot_authority()

    assert report["final_judgment"] == "PHASE18_X_AUTHORITY_APPROVAL_BLOCKED"
    assert report["authority_approval_status"] == "AUTHORITY_APPROVAL_BLOCKED"
    assert before == after
    assert report["registry_unchanged"] is True
    assert report["runtime_accepted_state_unchanged"] is True
    assert report["accepted_state_materialized"] is False
    assert {item["item"] for item in report["blocking_items"]} >= {
        "phase18i_accepted_event_authorized",
        "promotion_candidate_not_runtime_eligible",
        "materialized_runtime_baseline",
        "freshness_metadata",
    }


def test_phase18x_atomicity_rehearsal_restores_failure_paths() -> None:
    module = load_module()
    rehearsal = module.isolated_atomicity_rehearsal()

    for name in ("registry_write", "index_write", "runtime_state_write"):
        assert rehearsal[name]["outcome"]["status"] == "RESTORED"
        assert rehearsal[name]["hashes_unchanged"] is True
    assert rehearsal["success"]["outcome"]["status"] == "PASS"
    assert rehearsal["success"]["accepted_state_exists"] is True
