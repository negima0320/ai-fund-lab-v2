#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.policy_manifest import build_policy_manifest, write_policy_manifest  # noqa: E402


DEFAULT_FEATURE_MANIFEST = Path(".runtime/phase9/feature_refresh/2026-06-15/feature_refresh_manifest.json")
DEFAULT_OUTPUT_DIR = Path(".runtime/phase9/policy_manifests")

POLICIES = {
    "position": {
        "policy_name": "Position Management Winner Holding Policy",
        "policy_version": "position_management_policy_phase6i_winner_holding_v1",
        "implementation_ref": "src/ai_fund_lab_v2/position_management_ai/winner_holding_calibration.py",
    },
    "capital": {
        "policy_name": "Capital Allocation CAP5",
        "policy_version": "phase7d_realistic_execution_constraints_v1/CAP5",
        "implementation_ref": "src/ai_fund_lab_v2/capital_allocation_ai/phase7d_execution_constraints_validation.py",
    },
}


def generate_policy_manifests(
    *,
    decision_for: str,
    data_until: str,
    feature_manifest_path: Path | str = DEFAULT_FEATURE_MANIFEST,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    feature_manifest = _load_json(Path(feature_manifest_path))
    artifacts = {item.get("ai_name"): item for item in feature_manifest.get("artifacts", []) if isinstance(item, dict)}
    outputs: dict[str, Any] = {}
    for ai_name, spec in POLICIES.items():
        artifact = artifacts.get(ai_name, {})
        manifest = build_policy_manifest(
            ai_name=ai_name,
            policy_name=spec["policy_name"],
            policy_version=spec["policy_version"],
            implementation_ref=spec["implementation_ref"],
            data_until=data_until,
            decision_for=decision_for,
            feature_schema_hash=str(artifact.get("feature_schema_hash") or ""),
            source_data_refs=artifact.get("source_data_refs") or {},
            train_until_required=False,
            label_horizon_required=False,
        )
        path = write_policy_manifest(manifest, output_dir)
        outputs[ai_name] = {"path": str(path), "manifest": manifest.to_dict()}
    return {
        "status": "POLICY_MANIFESTS_GENERATED",
        "decision_for": decision_for,
        "data_until": data_until,
        "outputs": outputs,
        "model_retraining_executed": False,
        "inference_executed": False,
        "order_plan_generation_executed": False,
        "broker_order_api_called": False,
        "virtual_fill_executed": False,
    }


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Phase9 policy manifests.")
    parser.add_argument("--decision-for", required=True)
    parser.add_argument("--data-until", required=True)
    parser.add_argument("--feature-manifest-path", default=str(DEFAULT_FEATURE_MANIFEST))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    result = generate_policy_manifests(
        decision_for=args.decision_for,
        data_until=args.data_until,
        feature_manifest_path=args.feature_manifest_path,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
