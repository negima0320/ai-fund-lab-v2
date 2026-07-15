from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SCRIPT = REPO_ROOT / "scripts/phase17_b1i_b_pm_adapter_authority_resolution.py"
REPORT_ROOT = REPO_ROOT / "reports/phase17_aj_buy_opportunity_pm_contract_integration/pm_adapter_registry_acceptance"
sys.path.insert(0, str(REPO_ROOT / "src"))


def _load_base_module():
    spec = importlib.util.spec_from_file_location("phase17_b1i_b_pm_adapter_authority_resolution", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Phase17-B1I-B PM adapter authority script")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _phase17_aj_tests(module: Any) -> list[dict[str, Any]]:
    commands = [
        [sys.executable, "-m", "pytest", "-q", "tests/runtime_v2/test_phase17_aj_buy_opportunity_pm_contract.py"],
        [sys.executable, "-m", "pytest", "-q", "tests/runtime_v2/test_phase17_b1i_b_pm_adapter_authority.py"],
        [sys.executable, "-m", "pytest", "-q", "tests/runtime_v2/test_phase15ap_position_management_input_contract.py"],
        [sys.executable, "-m", "pytest", "-q", "tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py"],
        [sys.executable, "-m", "pytest", "-q", "tests/runtime_v2/test_phase17_af_day2_morning_temporal_authority.py"],
        [sys.executable, "-m", "pytest", "-q", "tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py"],
        [sys.executable, "-m", "pytest", "-q", "tests/runtime_v2/test_phase17_ah_pm_adapter_registry_identity_guard.py"],
        [sys.executable, "-m", "pytest", "-q", "tests/artifact_registry/test_phase16av_runtime_lookup_adapter.py"],
        [sys.executable, "-m", "pytest", "-q", "tests/runtime_v2/test_phase16av_registry_consumer_cutover.py"],
    ]
    results = []
    env = {**os.environ, "PYTHONPATH": "src", "PYTHONPYCACHEPREFIX": "/private/tmp/phase17aj_registry_pycache"}
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
    module.VERSION = "phase17_aj_buy_opportunity_pm_contract_integration.v1"
    module.EVIDENCE_ID = "control_position_management_accepted_current_path_v6"
    module.REPORT_ROOT = REPORT_ROOT
    module.PHASE_DOC = REPORT_ROOT / "pm_adapter_registry_acceptance.md"
    module.PHASE_JSON = REPORT_ROOT / "pm_adapter_registry_acceptance.json"
    module.PREVIOUS_ACCEPTED_ADAPTER_HASH = "2e6790f07cb3981fe0dbc575b059bbbc1abd6fb27f6c74b989b8bb8285951535"
    module.run_tests = lambda: _phase17_aj_tests(module)
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
