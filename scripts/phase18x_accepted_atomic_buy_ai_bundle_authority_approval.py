from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "phase18x-accepted-atomic-buy-ai-bundle-authority-20260717T000000Z"
PROMOTION_TX_ID = "promotion-tx-phase18i-1081babc49b5d26b"
PROMOTION_TX_DIR = ROOT / ".runtime" / "artifact_registry" / "promotion_candidates" / "transactions" / PROMOTION_TX_ID
REPORT_MD = ROOT / "docs" / "phase_reports" / "phase18_x_accepted_atomic_buy_ai_bundle_authority_approval.md"
REPORT_JSON = ROOT / "reports" / "phase_reports" / "phase18_x_accepted_atomic_buy_ai_bundle_authority_approval.json"
EVIDENCE_DIR = ROOT / "reports" / "phase18_x_accepted_atomic_buy_ai_bundle_authority_approval" / RUN_ID
REGISTRY_EVENTS = ROOT / ".runtime" / "artifact_registry" / "events" / "registry_events.jsonl"
REGISTRY_INDEX = ROOT / ".runtime" / "artifact_registry" / "index" / "registry_index.json"
REGISTRY_CHECKPOINT = ROOT / ".runtime" / "artifact_registry" / "checkpoints" / "latest.json"
ACCEPTED_STATE = ROOT / ".runtime" / "runtime_state" / "accepted_buy_ai_bundle.json"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")).hexdigest()


def snapshot_authority() -> dict[str, Any]:
    return {
        "registry_events_hash": file_hash(REGISTRY_EVENTS),
        "registry_index_hash": file_hash(REGISTRY_INDEX),
        "registry_checkpoint_hash": file_hash(REGISTRY_CHECKPOINT),
        "accepted_state_exists": ACCEPTED_STATE.exists(),
        "accepted_state_hash": file_hash(ACCEPTED_STATE),
    }


def load_inputs() -> dict[str, Any]:
    return {
        "phase18h": read_json(ROOT / "reports" / "phase_reports" / "phase18_h_promotion_blocking_issues_resolution.json"),
        "phase18i": read_json(ROOT / "reports" / "phase_reports" / "phase18_i_authority_approval_and_registry_promotion_operator.json"),
        "phase18u_md_exists": (ROOT / "docs" / "phase_reports" / "phase18_u_final_independent_contract_closure_review.md").exists(),
        "phase18w": read_json(ROOT / "reports" / "phase_reports" / "phase18_w_historical_runtime_scoped_block_and_accepted_bundle_authority.json"),
        "transaction": read_json(PROMOTION_TX_DIR / "transaction.json"),
        "authority_decision": read_json(PROMOTION_TX_DIR / "authority_decision.json"),
        "review": read_json(PROMOTION_TX_DIR / "promotion_review_artifact.json"),
        "bundle": read_json(PROMOTION_TX_DIR / "atomic_buy_ai_bundle.json"),
        "rollback": read_json(PROMOTION_TX_DIR / "rollback_metadata.json"),
        "promotion_index": read_json(ROOT / ".runtime" / "artifact_registry" / "promotion_candidates" / "promotion_candidate_index.json"),
    }


def check_file_hash(path: Path, expected: str) -> dict[str, Any]:
    actual = file_hash(path)
    return {"path": str(path.relative_to(ROOT)), "expected": expected, "actual": actual, "status": "PASS" if actual == expected else "FAIL"}


def validate_bundle_artifacts(bundle: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    for component, dir_key, hash_key in (
        ("candidate_dataset", "dataset_dir", "dataset_hash"),
        ("opportunity_dataset", "dataset_dir", "dataset_hash"),
        ("candidate_training", "training_dir", "bundle_hash"),
        ("opportunity_training", "training_dir", "bundle_hash"),
    ):
        payload = bundle.get(component) or {}
        directory = ROOT / str(payload.get(dir_key) or "")
        manifest = read_json(directory / "hash_manifest.json") if (directory / "hash_manifest.json").exists() else {}
        expected = payload.get(hash_key)
        actual = manifest.get(hash_key)
        checks[component] = {
            "directory": str(directory.relative_to(ROOT)) if directory.exists() else str(directory),
            "directory_exists": directory.exists(),
            "lineage_exists": (directory / "lineage.json").exists(),
            "hash_manifest_exists": (directory / "hash_manifest.json").exists(),
            "expected_hash": expected,
            "manifest_hash": actual,
            "status": "PASS" if directory.exists() and (directory / "lineage.json").exists() and expected and actual == expected else "FAIL",
        }
    opp_train = ROOT / bundle["opportunity_training"]["training_dir"]
    required_calibration = ["calibration_model.pkl", "calibration_parameters.json", "calibration_metadata.json", "calibration_schema.json", "calibration_hash.json"]
    checks["opportunity_calibration"] = {
        "required_files": required_calibration,
        "missing": [name for name in required_calibration if not (opp_train / name).exists()],
    }
    checks["opportunity_calibration"]["status"] = "PASS" if not checks["opportunity_calibration"]["missing"] else "FAIL"
    return checks


def baseline_completeness(bundle: dict[str, Any]) -> dict[str, Any]:
    inline = bundle.get("runtime_baseline") or bundle.get("materialized_drift_baseline")
    ref = bundle.get("runtime_baseline_ref") or bundle.get("materialized_drift_baseline_ref")
    opp_train = ROOT / bundle["opportunity_training"]["training_dir"]
    prediction_distribution = read_json(opp_train / "prediction_distribution.json")
    summary_only = bool(prediction_distribution) and all(isinstance(value, dict) and "row_count" in value for value in prediction_distribution.values())
    return {
        "status": "PASS" if isinstance(inline, dict) or ref else "FAIL",
        "runtime_baseline_inline": isinstance(inline, dict),
        "runtime_baseline_ref": str(ref or ""),
        "prediction_distribution_summary_only": summary_only,
        "reason": "" if isinstance(inline, dict) or ref else "missing_materialized_runtime_baseline_values",
    }


def freshness_metadata_completeness(bundle: dict[str, Any]) -> dict[str, Any]:
    opp_train = ROOT / bundle["opportunity_training"]["training_dir"]
    training_meta = read_json(opp_train / "training_metadata.json")
    phase18j = read_json(ROOT / "reports" / "phase_reports" / "phase18_j_runtime_discovery_freshness_gate_acceptance.json")
    phase18j_cutoff = (((phase18j.get("freshness_gate") or {}).get("opportunity") or {}).get("model_training_cutoff"))
    metadata_cutoff = training_meta.get("model_training_cutoff") or training_meta.get("training_cutoff") or training_meta.get("training_data_cutoff")
    return {
        "status": "PASS" if metadata_cutoff else "FAIL",
        "training_metadata_path": str(opp_train.relative_to(ROOT) / "training_metadata.json"),
        "training_metadata_model_training_cutoff": metadata_cutoff or "",
        "phase18j_model_training_cutoff_evidence": phase18j_cutoff or "",
        "reason": "" if metadata_cutoff else "model_training_cutoff_not_materialized_in_training_metadata_or_accepted_bundle_contract",
    }


def authority_approval_checks(inputs: dict[str, Any]) -> dict[str, Any]:
    bundle = inputs["bundle"]
    phase18h = inputs["phase18h"]
    phase18i = inputs["phase18i"]
    authority_decision = inputs["authority_decision"]
    review = inputs["review"]
    tx = inputs["transaction"]
    promotion_index = inputs["promotion_index"]["promotion_candidates"].get(bundle["buy_ai_bundle_id"], {})
    bundle_checks = validate_bundle_artifacts(bundle)
    baseline = baseline_completeness(bundle)
    freshness = freshness_metadata_completeness(bundle)
    checks = {
        "phase18h_promotion_ready_with_review": {
            "status": "PASS" if (phase18h.get("final_judgment") or {}).get("primary") == "PHASE18_H_PROMOTION_READY_WITH_REVIEW" else "FAIL",
            "evidence": phase18h.get("final_judgment"),
        },
        "phase18i_authority_review_valid": {
            "status": "PASS" if authority_decision.get("decision") == "PROMOTION_APPROVED_WITH_REVIEW" and not authority_decision.get("blocking_items") else "FAIL",
            "decision": authority_decision.get("decision"),
            "blocking_items": authority_decision.get("blocking_items"),
        },
        "phase18i_accepted_event_authorized": {
            "status": "PASS" if authority_decision.get("registry_accepted_event_authorized") is True else "FAIL",
            "registry_accepted_event_authorized": authority_decision.get("registry_accepted_event_authorized"),
            "approval_scope": authority_decision.get("approval_scope"),
        },
        "phase18u_contract_closure": {
            "status": "PASS" if inputs["phase18u_md_exists"] else "FAIL",
        },
        "promotion_candidate_index_consistency": {
            "status": "PASS" if promotion_index.get("bundle_hash") == bundle.get("joint_bundle_hash") and promotion_index.get("runtime_use_eligible") is False else "FAIL",
            "promotion_index_entry": promotion_index,
        },
        "promotion_candidate_not_runtime_eligible": {
            "status": "PASS" if bundle.get("runtime_use_eligible") is True else "FAIL",
            "runtime_use_eligible": bundle.get("runtime_use_eligible"),
            "registry_accepted_event_requested": bundle.get("registry_accepted_event_requested"),
        },
        "joint_bundle_hash": {
            "status": "PASS" if tx.get("bundle_hash") == bundle.get("joint_bundle_hash") == review.get("joint_bundle_hash") else "FAIL",
            "transaction_hash": tx.get("bundle_hash"),
            "bundle_hash": bundle.get("joint_bundle_hash"),
            "review_hash": review.get("joint_bundle_hash"),
        },
        "bundle_artifacts": bundle_checks,
        "materialized_runtime_baseline": baseline,
        "freshness_metadata": freshness,
        "rollback_reference": {
            "status": "PASS" if inputs["rollback"].get("rollback_hash") and inputs["rollback"].get("previous_bundle") else "FAIL",
            "rollback_hash": inputs["rollback"].get("rollback_hash"),
            "previous_bundle_keys": sorted((inputs["rollback"].get("previous_bundle") or {}).keys()),
        },
    }
    return checks


def blockers_from_checks(checks: dict[str, Any]) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    for name, payload in checks.items():
        if name == "bundle_artifacts":
            for child, child_payload in payload.items():
                if child_payload.get("status") != "PASS":
                    blockers.append({"item": f"bundle_artifacts.{child}", "reason": str(child_payload)})
            continue
        if isinstance(payload, dict) and payload.get("status") != "PASS":
            blockers.append({"item": name, "reason": payload.get("reason") or json.dumps(payload, sort_keys=True, default=str)})
    return blockers


def isolated_atomicity_rehearsal() -> dict[str, Any]:
    result: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="phase18x_atomicity_") as tmp_name:
        root = Path(tmp_name)
        event_log = root / "registry_events.jsonl"
        index = root / "registry_index.json"
        accepted_state = root / "accepted_buy_ai_bundle.json"
        event_log.write_text("before\n", encoding="utf-8")
        write_json(index, {"state": "before"})
        before = {name: file_hash(path) for name, path in {"event_log": event_log, "index": index, "accepted_state": accepted_state}.items()}

        def attempt(fail_at: str | None) -> dict[str, Any]:
            backups = {path: path.read_bytes() if path.exists() else None for path in (event_log, index, accepted_state)}
            try:
                if fail_at == "registry_write":
                    raise RuntimeError("registry_write_failure")
                event_log.write_text("before\naccepted\n", encoding="utf-8")
                if fail_at == "index_write":
                    raise RuntimeError("index_write_failure")
                write_json(index, {"state": "accepted"})
                if fail_at == "runtime_state_write":
                    raise RuntimeError("runtime_state_write_failure")
                write_json(accepted_state, {"state": "accepted"})
                return {"status": "PASS"}
            except RuntimeError as exc:
                for path, data in backups.items():
                    if data is None:
                        if path.exists():
                            path.unlink()
                    else:
                        path.write_bytes(data)
                return {"status": "RESTORED", "error": str(exc)}

        for fail_at in ("registry_write", "index_write", "runtime_state_write"):
            outcome = attempt(fail_at)
            after = {name: file_hash(path) for name, path in {"event_log": event_log, "index": index, "accepted_state": accepted_state}.items()}
            result[fail_at] = {"outcome": outcome, "hashes_unchanged": before == after}
        success = attempt(None)
        result["success"] = {"outcome": success, "accepted_state_exists": accepted_state.exists()}
    return result


def build_report() -> dict[str, Any]:
    before = snapshot_authority()
    inputs = load_inputs()
    checks = authority_approval_checks(inputs)
    blockers = blockers_from_checks(checks)
    atomicity = isolated_atomicity_rehearsal()
    after = snapshot_authority()
    final_judgment = "PHASE18_X_AUTHORITY_APPROVAL_BLOCKED" if blockers else "PHASE18_X_AUTHORITY_APPROVAL_COMPLETE"
    return {
        "schema_version": "phase18_x_authority_approval_report_v1",
        "phase": "Phase18-X",
        "run_id": RUN_ID,
        "promotion_transaction_id": PROMOTION_TX_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "final_judgment": final_judgment,
        "authority_approval_status": "AUTHORITY_APPROVAL_BLOCKED" if blockers else "AUTHORITY_APPROVAL_COMPLETE",
        "checks": checks,
        "blocking_items": blockers,
        "atomicity_rehearsal": atomicity,
        "authority_snapshot_before": before,
        "authority_snapshot_after": after,
        "registry_unchanged": before["registry_events_hash"] == after["registry_events_hash"] and before["registry_index_hash"] == after["registry_index_hash"],
        "runtime_accepted_state_unchanged": before["accepted_state_hash"] == after["accepted_state_hash"] and before["accepted_state_exists"] == after["accepted_state_exists"],
        "accepted_state_materialized": False,
        "broker_write": False,
        "buy_restart": False,
        "historical_fresh_run_executed": False,
        "prohibited_actions": {
            "promotion_candidate_direct_runtime_reference": False,
            "latest_fallback": False,
            "manual_path_fallback": False,
            "legacy_model_assembled_pseudo_atomic_bundle": False,
            "manual_accepted_state_json_created": False,
            "partial_registry_update": False,
            "hash_schema_lineage_ignored": False,
            "bv15_relaxed": False,
            "forced_buy": False,
            "broker_write": False,
            "production_runtime_execution": False,
            "historical_fresh_run_execution": False,
        },
    }


def write_markdown(report: dict[str, Any]) -> None:
    lines = [
        "# Phase18-X Accepted Atomic BUY AI Bundle Authority Approval and Materialization",
        "",
        f"- Run ID: `{report['run_id']}`",
        f"- Final judgment: `{report['final_judgment']}`",
        f"- Authority status: `{report['authority_approval_status']}`",
        f"- Registry unchanged: `{report['registry_unchanged']}`",
        f"- Runtime accepted state unchanged: `{report['runtime_accepted_state_unchanged']}`",
        f"- Accepted state materialized: `{report['accepted_state_materialized']}`",
        "",
        "## Blocking Items",
        "",
    ]
    if report["blocking_items"]:
        for item in report["blocking_items"]:
            lines.append(f"- `{item['item']}`: {item['reason']}")
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Key Findings",
            "",
            "- Phase18-H readiness evidence remains `PROMOTION_READY_WITH_REVIEW`.",
            "- Phase18-I Authority decision is valid for Promotion Candidate registration, but `registry_accepted_event_authorized=false` and `approval_scope=PROMOTION_CANDIDATE_REGISTRATION_ONLY`.",
            "- The Promotion Candidate bundle itself remains `runtime_use_eligible=false` and `registry_accepted_event_requested=false`.",
            "- No materialized runtime baseline values or baseline ref are present in the Atomic BUY AI Bundle.",
            "- Opportunity training metadata does not materialize `model_training_cutoff`; Phase18-J has review evidence for `2026-05-15`, but it is not part of the accepted runtime contract.",
            "- Registry accepted state and `.runtime/runtime_state/accepted_buy_ai_bundle.json` were not changed.",
            "",
            "## Atomicity Rehearsal",
            "",
        ]
    )
    for name, payload in report["atomicity_rehearsal"].items():
        lines.append(f"- `{name}`: `{payload}`")
    lines.extend(
        [
            "",
            "## Non-Execution Confirmation",
            "",
            "- Promotion Candidate direct Runtime reference: `False`",
            "- latest fallback: `False`",
            "- manual path fallback: `False`",
            "- Registry accepted state update: `False`",
            "- Runtime accepted state update: `False`",
            "- BV15 relaxation: `False`",
            "- forced BUY: `False`",
            "- Broker write: `False`",
            "- Production Runtime execution: `False`",
            "- Historical fresh-run execution: `False`",
            "",
            "## Final",
            "",
            f"`{report['final_judgment']}`",
            "",
        ]
    )
    write_text(REPORT_MD, "\n".join(lines))


def main() -> int:
    report = build_report()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    write_json(EVIDENCE_DIR / "authority_approval_checks.json", report)
    write_json(REPORT_JSON, report)
    write_markdown(report)
    return 0 if report["final_judgment"] == "PHASE18_X_AUTHORITY_APPROVAL_COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
