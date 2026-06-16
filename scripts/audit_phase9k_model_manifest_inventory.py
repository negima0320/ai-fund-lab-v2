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


DEFAULT_OUTPUT = Path("reports/phase_reports/phase9k_model_manifest_inventory.json")

ACTIVE_CANDIDATES = {
    "candidate": {
        "manifest_path": ".runtime/candidate_ai/models/phase4bf_formal_candidate_model_manifest.json",
        "artifact_path": ".runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl",
    },
    "opportunity": {
        "manifest_path": "reports/opportunity_ai/phase5p/training/opportunity_training_audit.json",
        "artifact_path": "reports/opportunity_ai/phase5p/models/opportunity_model.pkl",
    },
    "position": {
        "manifest_path": ".runtime/phase9/policy_manifests/position_policy_manifest.json",
        "artifact_path": "",
    },
    "capital": {
        "manifest_path": ".runtime/phase9/policy_manifests/capital_policy_manifest.json",
        "artifact_path": "",
    },
}


def build_model_manifest_inventory() -> dict[str, Any]:
    items: dict[str, Any] = {}
    for ai_name, refs in ACTIVE_CANDIDATES.items():
        manifest_path = Path(refs["manifest_path"]) if refs["manifest_path"] else None
        artifact_path = Path(refs["artifact_path"]) if refs["artifact_path"] else None
        manifest = _load_json(manifest_path)
        items[ai_name] = {
            "ai_name": ai_name,
            "manifest_path": str(manifest_path) if manifest_path else "",
            "manifest_exists": bool(manifest_path and manifest_path.exists()),
            "manifest_readable": bool(manifest),
            "artifact_path": str(artifact_path) if artifact_path else _artifact_from_manifest(manifest),
            "artifact_exists": _artifact_exists(artifact_path, manifest),
            "model_version": _first_text(manifest, "model_version", "active_model_version") or (
                "opportunity_model_phase5e_v1" if ai_name == "opportunity" and _artifact_exists(artifact_path, manifest) else ""
            ),
            "policy_version": _first_text(manifest, "policy_version", "policy_id", "model_version"),
            "train_until": _first_text(manifest, "train_until"),
            "data_until": _first_text(manifest, "data_until"),
            "label_horizon": manifest.get("label_horizon") or manifest.get("label_horizon_business_days"),
            "feature_schema_hash": _first_text(manifest, "feature_schema_hash"),
            "leakage_audit_status": _first_text(manifest, "leakage_audit_status"),
            "forbidden_source_audit_status": _first_text(manifest, "forbidden_source_audit_status", "forbidden_training_source_audit_status"),
            "created_at": _first_text(manifest, "created_at"),
            "source_data_refs": manifest.get("source_data_refs") or manifest.get("training_sources") or manifest.get("dataset_path") or {},
        }
    return {
        "status": "MODEL_MANIFEST_INVENTORY_COMPLETE",
        "items": items,
        "model_retraining_executed": False,
        "inference_executed": False,
        "order_plan_generation_executed": False,
        "broker_order_api_called": False,
        "virtual_fill_executed": False,
    }


def _load_json(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists() or path.suffix.lower() != ".json":
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _artifact_from_manifest(manifest: dict[str, Any]) -> str:
    return _first_text(manifest, "artifact_path", "model_artifact_path", "policy_artifact_path")


def _artifact_exists(path: Path | None, manifest: dict[str, Any]) -> bool:
    if path and str(path):
        return path.exists()
    artifact = _artifact_from_manifest(manifest)
    return bool(artifact and Path(artifact).exists())


def _first_text(manifest: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = manifest.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory Phase9 model and policy manifests.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    payload = build_model_manifest_inventory()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
