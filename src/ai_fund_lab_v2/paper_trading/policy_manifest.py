from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PolicyManifest:
    ai_name: str
    policy_name: str
    policy_version: str
    implementation_ref: str
    data_until: str
    decision_for: str
    feature_schema_hash: str
    train_until_required: bool
    label_horizon_required: bool
    leakage_audit_status: str
    forbidden_source_audit_status: str
    source_data_refs: dict[str, Any]
    broker_api_executed: bool = False
    paper_ledger_training_used: bool = False
    backtest_result_training_used: bool = False
    public_confidence_training_used: bool = False
    model_retraining_executed: bool = False
    inference_executed: bool = False
    order_plan_generation_executed: bool = False
    virtual_fill_executed: bool = False
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_policy_manifest(
    *,
    ai_name: str,
    policy_name: str,
    policy_version: str,
    implementation_ref: str,
    data_until: str,
    decision_for: str,
    feature_schema_hash: str,
    source_data_refs: dict[str, Any],
    train_until_required: bool = False,
    label_horizon_required: bool = False,
    leakage_audit_status: str = "OK",
    forbidden_source_audit_status: str = "OK",
    created_at: str | None = None,
) -> PolicyManifest:
    return PolicyManifest(
        ai_name=ai_name,
        policy_name=policy_name,
        policy_version=policy_version,
        implementation_ref=implementation_ref,
        data_until=data_until,
        decision_for=decision_for,
        feature_schema_hash=feature_schema_hash,
        train_until_required=train_until_required,
        label_horizon_required=label_horizon_required,
        leakage_audit_status=leakage_audit_status,
        forbidden_source_audit_status=forbidden_source_audit_status,
        source_data_refs=source_data_refs,
        created_at=created_at or _now(),
    )


def write_policy_manifest(manifest: PolicyManifest, output_dir: Path | str) -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{manifest.ai_name}_policy_manifest.json"
    path.write_text(json.dumps(manifest.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
