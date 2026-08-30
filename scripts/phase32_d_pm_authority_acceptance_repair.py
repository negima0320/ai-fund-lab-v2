from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SCRIPT = REPO_ROOT / "scripts/phase17_b1i_b_pm_adapter_authority_resolution.py"
REPORT_ROOT = REPO_ROOT / "reports/phase32_d_post_phase32c_morning_halt_authority_repair"
PHASE_DOC = REPO_ROOT / "docs/phase_reports/phase32_d_pm_runtime_adapter_authority_acceptance.md"
PHASE_JSON = REPO_ROOT / "reports/phase_reports/phase32_d_pm_runtime_adapter_authority_acceptance.json"
EVIDENCE_ID = "control_position_management_accepted_current_path_phase32_d"
VERSION = "phase32_d_post_phase32c_pm_runtime_adapter_authority_acceptance.v1"


def _load_base_module():
    spec = importlib.util.spec_from_file_location("phase17_b1i_b_pm_adapter_authority_resolution", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load canonical PM authority module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = _load_base_module()
    module.REPORT_ROOT = REPORT_ROOT
    module.PHASE_DOC = PHASE_DOC
    module.PHASE_JSON = PHASE_JSON
    module.EVIDENCE_ID = EVIDENCE_ID
    module.VERSION = VERSION

    def run_focused_tests():
        commands = [
            [sys.executable, "-m", "pytest", "-q", "tests/runtime_v2/test_phase17_b1i_b_pm_adapter_authority.py"],
            [sys.executable, "-m", "pytest", "-q", "tests/runtime_v2/test_phase31_g30_authority_lineage.py"],
            [sys.executable, "-m", "pytest", "-q", "tests/runtime_v2/test_phase32_c_provenance_campaign_identity.py"],
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_submit_uses_order_increment_not_position_scope_delta",
                "tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_true_order_increment_mismatch_still_reviews",
            ],
        ]
        results = []
        env = {**os.environ, "PYTHONPATH": "src", "PYTHONPYCACHEPREFIX": "/private/tmp/phase32d_pycache"}
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
                module.write_json(REPORT_ROOT / "focused_test_failure.json", result)
                raise RuntimeError(f"focused test failed: {' '.join(command)}")
        return results

    module.run_tests = run_focused_tests
    return int(module.main())


if __name__ == "__main__":
    raise SystemExit(main())
