#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.model_manifest_review import load_manifest, review_model_manifest  # noqa: E402
from ai_fund_lab_v2.paper_trading.safe_train_until import resolve_safe_train_until  # noqa: E402

INV_PATH = ROOT / "scripts/audit_phase9k_model_manifest_inventory.py"
GEN_PATH = ROOT / "scripts/run_phase9k_generate_policy_manifests.py"

DEFAULT_FEATURE_MANIFEST = Path(".runtime/phase9/feature_refresh/2026-06-15/feature_refresh_manifest.json")
DEFAULT_CALENDAR = Path(".runtime/data/raw/jquants/trading_calendar/data.parquet")
DEFAULT_MD_REPORT = Path("docs/phase_reports/phase9k_model_manifest_retrain_eligibility.md")
DEFAULT_JSON_REPORT = Path("reports/phase_reports/phase9k_model_manifest_retrain_eligibility.json")


def run_phase9k_review(
    *,
    decision_for: str = "2026-06-15",
    data_until: str = "2026-06-15",
    feature_manifest_path: Path | str = DEFAULT_FEATURE_MANIFEST,
    trading_calendar_path: Path | str = DEFAULT_CALENDAR,
    markdown_report_path: Path | str = DEFAULT_MD_REPORT,
    json_report_path: Path | str = DEFAULT_JSON_REPORT,
    policy_output_dir: Path | str = ".runtime/phase9/policy_manifests",
) -> dict[str, Any]:
    generator = _load_module("phase9k_policy_generator", GEN_PATH)
    inventory_mod = _load_module("phase9k_inventory", INV_PATH)
    policy_generation = generator.generate_policy_manifests(
        decision_for=decision_for,
        data_until=data_until,
        feature_manifest_path=feature_manifest_path,
        output_dir=policy_output_dir,
    )
    inventory = inventory_mod.build_model_manifest_inventory()
    feature_hashes = _feature_hashes(Path(feature_manifest_path))
    label_horizons = {
        "candidate": 20,
        "opportunity": 20,
        "position": None,
        "capital": None,
    }
    safe_train_until = {
        ai_name: resolve_safe_train_until(
            data_until=data_until,
            label_horizon_business_days=horizon,
            trading_calendar_path=trading_calendar_path,
            train_until_required=horizon is not None,
        ).to_dict()
        for ai_name, horizon in label_horizons.items()
    }
    reviews = {}
    for ai_name, item in inventory["items"].items():
        manifest_path = item.get("manifest_path")
        manifest = load_manifest(manifest_path)
        if manifest:
            manifest = {
                **manifest,
                "artifact_path": manifest.get("artifact_path") or manifest.get("model_artifact_path") or item.get("artifact_path"),
                "model_version": manifest.get("model_version") or item.get("model_version"),
                "policy_version": manifest.get("policy_version") or item.get("policy_version"),
            }
        if manifest and ai_name in {"candidate", "opportunity"}:
            manifest = {**manifest, "label_horizon": manifest.get("label_horizon") or 20}
        reviews[ai_name] = review_model_manifest(
            ai_name=ai_name,
            manifest=manifest,
            manifest_path=manifest_path,
            expected_feature_schema_hash=feature_hashes.get(ai_name, ""),
            data_until=data_until,
            trading_calendar_path=trading_calendar_path,
        ).to_dict()
    overall = _overall_status(reviews)
    payload = {
        "phase": "Phase9-K",
        "status": overall,
        "decision_for": decision_for,
        "data_until": data_until,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inventory": inventory,
        "policy_generation": policy_generation,
        "feature_schema_hashes": feature_hashes,
        "safe_train_until": safe_train_until,
        "eligibility": reviews,
        "forbidden_source_audit_result": _forbidden_summary(reviews),
        "retrain_required": any(item["retrain_required"] for item in reviews.values()),
        "next_action": _next_action(overall),
        "model_retraining_executed": False,
        "inference_executed": False,
        "order_plan_generation_executed": False,
        "broker_order_api_called": False,
        "open_d_started": False,
        "unlock_trade_called": False,
        "paper_ledger_fill_executed": False,
        "virtual_fill_executed": False,
    }
    _write_outputs(payload, Path(markdown_report_path), Path(json_report_path))
    return payload


def _feature_hashes(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        item.get("ai_name"): str(item.get("feature_schema_hash") or "")
        for item in payload.get("artifacts", [])
        if isinstance(item, dict)
    }


def _overall_status(reviews: dict[str, dict[str, Any]]) -> str:
    statuses = {item["status"] for item in reviews.values()}
    if "FORBIDDEN_SOURCE_DETECTED" in statuses:
        return "NOT_READY"
    policy_ready = all(reviews[name]["status"] == "MODEL_ELIGIBLE" for name in ("position", "capital"))
    trainable_ready = all(reviews[name]["status"] == "MODEL_ELIGIBLE" for name in ("candidate", "opportunity"))
    if policy_ready and trainable_ready:
        return "MODELS_READY_FOR_DAILY_INFERENCE"
    if policy_ready and any(reviews[name]["retrain_required"] for name in ("candidate", "opportunity")):
        return "POLICY_MANIFESTS_READY_MODEL_RETRAIN_REQUIRED"
    if any(status == "MANIFEST_METADATA_INCOMPLETE" for status in statuses):
        return "MANIFEST_REPAIR_REQUIRED"
    if any(status in {"RETRAIN_REQUIRED", "FEATURE_SCHEMA_MISMATCH", "LEAKAGE_AUDIT_REQUIRED", "ARTIFACT_MISSING"} for status in statuses):
        return "MODEL_RETRAIN_REQUIRED"
    return "NOT_READY"


def _forbidden_summary(reviews: dict[str, dict[str, Any]]) -> dict[str, Any]:
    blocked = [
        f"{name}:{reason}"
        for name, item in reviews.items()
        for reason in item["blocked_reasons"]
        if "forbidden" in reason
    ]
    if any("forbidden_source_detected" in reason for reason in blocked):
        status = "ERROR"
    elif blocked:
        status = "REVIEW_REQUIRED"
    else:
        status = "OK"
    return {
        "status": status,
        "blocked_reasons": blocked,
    }


def _next_action(status: str) -> str:
    if status == "POLICY_MANIFESTS_READY_MODEL_RETRAIN_REQUIRED":
        return "Run Phase9-L model retrain or manifest repair planning for Candidate/Opportunity using safe_train_until."
    if status == "MANIFEST_REPAIR_REQUIRED":
        return "Repair active model metadata before daily inference."
    if status == "MODELS_READY_FOR_DAILY_INFERENCE":
        return "Proceed to Phase9 daily inference readiness."
    return "Resolve blockers before Phase9 daily inference."


def _write_outputs(payload: dict[str, Any], markdown_path: Path, json_path: Path) -> None:
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(_render_markdown(payload), encoding="utf-8")


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase9-K Model Manifest / Retrain Eligibility Review",
        "",
        f"- status: {payload['status']}",
        f"- decision_for: {payload['decision_for']}",
        f"- data_until: {payload['data_until']}",
        f"- retrain_required: {payload['retrain_required']}",
        "",
        "## Eligibility",
        "",
        "| AI | status | version | train_until | safe_train_until | schema | blockers |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for ai_name, item in payload["eligibility"].items():
        version = item.get("model_version") or item.get("policy_version")
        blockers = ", ".join(item.get("blocked_reasons") or []) or "none"
        lines.append(
            f"| {ai_name} | {item['status']} | {version} | {item.get('train_until') or ''} | "
            f"{item.get('safe_train_until') or ''} | {item.get('feature_schema_hash') or ''} | {blockers} |"
        )
    lines.extend(
        [
            "",
            "## Safe Train Until",
            "",
        ]
    )
    for ai_name, item in payload["safe_train_until"].items():
        lines.append(f"- {ai_name}: {item.get('safe_train_until') or 'not_required'}")
    lines.extend(
        [
            "",
            "## Policy Manifests",
            "",
        ]
    )
    for ai_name, item in payload["policy_generation"]["outputs"].items():
        lines.append(f"- {ai_name}: `{item['path']}`")
    lines.extend(
        [
            "",
            "## Safety",
            "",
            f"- forbidden_source_audit_status: {payload['forbidden_source_audit_result']['status']}",
            f"- model_retraining_executed: {payload['model_retraining_executed']}",
            f"- inference_executed: {payload['inference_executed']}",
            f"- order_plan_generation_executed: {payload['order_plan_generation_executed']}",
            f"- broker_order_api_called: {payload['broker_order_api_called']}",
            f"- virtual_fill_executed: {payload['virtual_fill_executed']}",
            "",
            "## Next Action",
            "",
            f"- {payload['next_action']}",
            "",
        ]
    )
    return "\n".join(lines)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Phase9-K model manifests and retrain eligibility.")
    parser.add_argument("--decision-for", default="2026-06-15")
    parser.add_argument("--data-until", default="2026-06-15")
    parser.add_argument("--feature-manifest-path", default=str(DEFAULT_FEATURE_MANIFEST))
    parser.add_argument("--trading-calendar-path", default=str(DEFAULT_CALENDAR))
    parser.add_argument("--markdown-report-path", default=str(DEFAULT_MD_REPORT))
    parser.add_argument("--json-report-path", default=str(DEFAULT_JSON_REPORT))
    parser.add_argument("--policy-output-dir", default=".runtime/phase9/policy_manifests")
    args = parser.parse_args()
    payload = run_phase9k_review(
        decision_for=args.decision_for,
        data_until=args.data_until,
        feature_manifest_path=args.feature_manifest_path,
        trading_calendar_path=args.trading_calendar_path,
        markdown_report_path=args.markdown_report_path,
        json_report_path=args.json_report_path,
        policy_output_dir=args.policy_output_dir,
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload["status"] != "NOT_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
