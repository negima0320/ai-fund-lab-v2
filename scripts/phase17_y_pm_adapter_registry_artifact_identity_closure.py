from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


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


def main() -> int:
    module = _load_base_module()
    module.VERSION = "phase17_y_pm_adapter_registry_artifact_identity_closure.v1"
    module.EVIDENCE_ID = "control_position_management_accepted_current_path_v4"
    module.REPORT_ROOT = REPO_ROOT / "reports/phase17_y_pm_adapter_registry_artifact_identity_closure"
    module.PHASE_DOC = REPO_ROOT / "docs/phase_reports/phase17_y_pm_adapter_registry_artifact_identity_closure.md"
    module.PHASE_JSON = REPO_ROOT / "reports/phase_reports/phase17_y_pm_adapter_registry_artifact_identity_closure.json"
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
