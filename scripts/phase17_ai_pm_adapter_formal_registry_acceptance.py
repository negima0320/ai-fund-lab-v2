from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SCRIPT = REPO_ROOT / "scripts/phase17_b1i_b_pm_adapter_authority_resolution.py"
sys.path.insert(0, str(REPO_ROOT / "src"))


def _load_base_module():
    spec = importlib.util.spec_from_file_location("phase17_b1i_b_pm_adapter_authority_resolution", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Phase17-B1I-B PM adapter authority script")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _phase17_ai_tests(module: Any) -> list[dict[str, Any]]:
    commands = [
        [sys.executable, "-m", "pytest", "-q", "tests/runtime_v2/test_phase17_ah_pm_adapter_registry_identity_guard.py"],
        [sys.executable, "-m", "pytest", "-q", "tests/runtime_v2/test_phase17_b1i_b_pm_adapter_authority.py"],
        [sys.executable, "-m", "pytest", "-q", "tests/runtime_v2/test_phase15ap_position_management_input_contract.py"],
        [sys.executable, "-m", "pytest", "-q", "tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py"],
        [sys.executable, "-m", "pytest", "-q", "tests/runtime_v2/test_phase17_af_day2_morning_temporal_authority.py"],
        [sys.executable, "-m", "pytest", "-q", "tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py"],
        [sys.executable, "-m", "pytest", "-q", "tests/artifact_registry/test_phase16av_runtime_lookup_adapter.py"],
        [sys.executable, "-m", "pytest", "-q", "tests/runtime_v2/test_phase16av_registry_consumer_cutover.py"],
    ]
    results = []
    env = {**os.environ, "PYTHONPATH": "src", "PYTHONPYCACHEPREFIX": "/private/tmp/phase17ai_pycache"}
    for command in commands:
        completed = subprocess.run(command, cwd=REPO_ROOT, env=env, text=True, capture_output=True)
        result = {
            "command": " ".join(command),
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "returncode": completed.returncode,
            "stdout_tail": completed.stdout[-3000:],
            "stderr_tail": completed.stderr[-3000:],
        }
        results.append(result)
        if completed.returncode != 0:
            module.write_json(module.REPORT_ROOT / "test_failure.json", result)
            raise RuntimeError(f"test failed: {' '.join(command)}")
    return results


def main() -> int:
    module = _load_base_module()
    module.VERSION = "phase17_ai_pm_adapter_formal_registry_acceptance.v1"
    module.EVIDENCE_ID = "control_position_management_accepted_current_path_v5"
    module.REPORT_ROOT = REPO_ROOT / "reports/phase17_ai_pm_adapter_formal_registry_acceptance"
    module.PHASE_DOC = REPO_ROOT / "docs/phase_reports/phase17_ai_pm_adapter_formal_registry_acceptance.md"
    module.PHASE_JSON = REPO_ROOT / "reports/phase_reports/phase17_ai_pm_adapter_formal_registry_acceptance.json"
    module.PREVIOUS_ACCEPTED_ADAPTER_HASH = "2924fa7e132e9602653cd1033a9b6b6925f8ef419accfafd673b05bdba4e71df"
    module.run_tests = lambda: _phase17_ai_tests(module)
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
