from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SCRIPT = REPO_ROOT / "scripts/phase17_b1i_b_pm_adapter_authority_resolution.py"
REPORT_ROOT = REPO_ROOT / "reports/phase17_bo_pm_runtime_adapter_registry_formal_acceptance_refresh/registry_acceptance"
sys.path.insert(0, str(REPO_ROOT / "src"))


def _load_base_module():
    spec = importlib.util.spec_from_file_location("phase17_b1i_b_pm_adapter_authority_resolution", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Phase17-B1I-B PM adapter authority script")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _phase17_bo_registry_tests(module: Any) -> list[dict[str, Any]]:
    commands = [
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/runtime_v2/test_phase16av_registry_consumer_cutover.py::test_pm_policy_registry_members_match_legacy_and_current_adapter",
            "tests/runtime_v2/test_phase17_b1i_b_pm_adapter_authority.py::test_registry_resolver_returns_current_pm_source_authority",
        ],
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/runtime_v2/test_phase17_ah_pm_adapter_registry_identity_guard.py",
            "tests/runtime_v2/test_phase17_b1i_b_pm_adapter_authority.py",
            "tests/runtime_v2/test_phase15ap_position_management_input_contract.py",
            "tests/runtime_v2/test_phase16av_registry_consumer_cutover.py",
            "tests/artifact_registry/test_phase16av_runtime_lookup_adapter.py",
        ],
    ]
    results = []
    env = {**os.environ, "PYTHONPATH": "src", "PYTHONPYCACHEPREFIX": "/private/tmp/phase17_bo_registry_pycache"}
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
    module.VERSION = "phase17_bo_pm_runtime_adapter_registry_formal_acceptance_refresh.v1"
    module.EVIDENCE_ID = "control_position_management_accepted_current_path_v7"
    module.REPORT_ROOT = REPORT_ROOT
    module.PHASE_DOC = REPO_ROOT / "docs/phase_reports/phase17_bo_pm_runtime_adapter_registry_acceptance_refresh_internal.md"
    module.PHASE_JSON = REPORT_ROOT / "registry_acceptance_internal.json"
    module.PREVIOUS_ACCEPTED_ADAPTER_HASH = "d08d854266f6822f322a7947fd7deb20a2906d2a56806d030e2618114bdcaa4b"
    module.run_tests = lambda: _phase17_bo_registry_tests(module)
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
