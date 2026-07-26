from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SCRIPT = REPO_ROOT / "scripts/phase17_b1i_b_pm_adapter_authority_resolution.py"
REPORT_ROOT = REPO_ROOT / "reports/phase20_w_formal_pm_runtime_adapter_acceptance_refresh"
sys.path.insert(0, str(REPO_ROOT / "src"))


def _load_base_module():
    spec = importlib.util.spec_from_file_location("phase17_b1i_b_pm_adapter_authority_resolution", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load formal PM adapter acceptance writer")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _phase20_w_registry_tests(module: Any) -> list[dict[str, Any]]:
    commands = [
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/runtime_v2/test_phase20_v_pm_runtime_adapter_equivalence.py",
        ],
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/runtime_v2/test_phase17_k_runtime_test_runner.py::test_phase20_u_run_halts_when_pm_artifact_halts_despite_cli_exit_zero",
            "tests/runtime_v2/test_phase20_j_performance_observability.py::test_phase20_u_pm_halt_metadata_is_preserved_and_blocks_validation_close",
            "tests/runtime_v2/test_phase20_j_performance_observability.py::test_phase20_j_writes_campaign_fills_realized_slices_and_pm_snapshot",
        ],
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/runtime_v2/test_phase17_ah_pm_adapter_registry_identity_guard.py",
            "tests/runtime_v2/test_phase15ap_position_management_input_contract.py",
            "tests/runtime_v2/test_phase16av_registry_consumer_cutover.py",
        ],
    ]
    results = []
    env = {**os.environ, "PYTHONPATH": "src", "PYTHONPYCACHEPREFIX": "/private/tmp/phase20_w_registry_pycache"}
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
    module.VERSION = "phase20_w_formal_pm_runtime_adapter_acceptance_refresh.v1"
    module.EVIDENCE_ID = "control_position_management_accepted_current_path_v10"
    module.REPORT_ROOT = REPORT_ROOT
    module.PHASE_DOC = REPO_ROOT / "docs/phase_reports/phase20_w_formal_pm_runtime_adapter_acceptance_refresh.writer.md"
    module.PHASE_JSON = REPORT_ROOT / "formal_writer_summary.json"
    module.PREVIOUS_ACCEPTED_ADAPTER_HASH = "93581111ae9b61facf669f8033d87e927f103d05483b4f212da4a592dbb15185"
    module.run_tests = lambda: _phase20_w_registry_tests(module)
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
