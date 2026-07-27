from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SCRIPT = REPO_ROOT / "scripts/phase17_b1i_b_pm_adapter_authority_resolution.py"
REPORT_ROOT = REPO_ROOT / "reports/phase21_c_position_management_artifact_authority_refresh"
sys.path.insert(0, str(REPO_ROOT / "src"))


def _load_base_module():
    spec = importlib.util.spec_from_file_location("phase17_b1i_b_pm_adapter_authority_resolution", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load formal PM adapter acceptance writer")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _phase21_c_registry_tests(module: Any) -> list[dict[str, Any]]:
    commands = [
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py",
        ],
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py",
            "tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py",
        ],
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/runtime_v2/test_phase20_v_pm_runtime_adapter_equivalence.py",
            "tests/runtime_v2/test_phase17_ah_pm_adapter_registry_identity_guard.py",
            "tests/runtime_v2/test_phase15ap_position_management_input_contract.py",
            "tests/runtime_v2/test_phase16av_registry_consumer_cutover.py",
        ],
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/artifact_registry/test_phase16ac_full_event_log_validator.py",
            "tests/artifact_registry/test_phase16ad_materialized_index_builder.py",
            "tests/artifact_registry/test_phase16ag_checkpoint_writer.py",
            "tests/artifact_registry/test_phase16au_registry_resolver.py",
        ],
    ]
    results = []
    env = {**os.environ, "PYTHONPATH": "src", "PYTHONPYCACHEPREFIX": "/private/tmp/phase21_c_registry_pycache"}
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
    module.VERSION = "phase21_c_position_management_artifact_authority_refresh.v1"
    module.EVIDENCE_ID = "control_position_management_accepted_current_path_v11"
    module.REPORT_ROOT = REPORT_ROOT
    module.PHASE_DOC = REPO_ROOT / "docs/phase_reports/phase21_c_position_management_artifact_authority_refresh.writer.md"
    module.PHASE_JSON = REPORT_ROOT / "formal_writer_summary.json"
    module.PREVIOUS_ACCEPTED_ADAPTER_HASH = "ac2e7f6a3e9e184889551a8884a0e779ffb37292e8b26daf1e25e1610bba739c"
    module.run_tests = lambda: _phase21_c_registry_tests(module)
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
