from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "compare_pm_runtime_adapter_equivalence.py"


def load_equivalence_script():
    spec = importlib.util.spec_from_file_location("compare_pm_runtime_adapter_equivalence", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_phase20_v_pm_runtime_adapter_behavioral_equivalence(tmp_path: Path) -> None:
    script = load_equivalence_script()

    report = script.build_report(tmp_path / "phase20_v_equivalence")

    assert report["old_hash_verified"] is True
    assert report["old_accepted_hash"] == script.OLD_ACCEPTED_HASH
    assert report["scenario_count"] == 8
    assert report["canonical_match_count"] == 8
    assert report["decision_count_old"] == report["decision_count_new"] == 6
    assert report["forbidden_difference_count"] == 0
    assert report["trace_failure_count"] == 0
    assert report["equivalence_judgment"] == "PM_RUNTIME_ADAPTER_BEHAVIORALLY_EQUIVALENT"
    assert report["acceptance_refresh_readiness"] == "FORMAL_ACCEPTANCE_REFRESH_READY"
    assert report["accepted_generation_modified"] is False
    assert report["long_running_historical_test_executed"] is False
    observed = {scenario["scenario_id"]: scenario["observed_action"] for scenario in report["scenarios"]}
    assert observed["V-A-HOLD"] == "HOLD"
    assert observed["V-B-REDUCE"] == "REDUCE"
    assert observed["V-C-EXIT"] == "EXIT"
    assert observed["V-D-ADD"] == "ADD"
    assert observed["V-E-READY-EMPTY"] == "NO_POSITION"
    assert observed["V-G-INVALID-REQUIRED"] == "REVIEW_REQUIRED"


def test_phase20_v_equivalence_harness_rejects_wrong_old_hash(tmp_path: Path, monkeypatch) -> None:
    script = load_equivalence_script()
    monkeypatch.setattr(script, "OLD_ACCEPTED_HASH", "not-the-real-hash")

    try:
        script.build_report(tmp_path / "phase20_v_bad_hash")
    except RuntimeError as exc:
        assert "old accepted source hash mismatch" in str(exc)
    else:
        raise AssertionError("expected old accepted hash mismatch")
