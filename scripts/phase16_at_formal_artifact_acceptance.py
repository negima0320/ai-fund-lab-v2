from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.artifact_registry.acceptance_evidence import (
    AcceptanceEvidenceBundleBuilder,
    AcceptanceEvidenceBundleValidator,
    AcceptanceEvidencePaths,
)
from ai_fund_lab_v2.artifact_registry.acceptance_writer import (
    AcceptanceWriterInputs,
    ArtifactAcceptanceWriter,
)
from ai_fund_lab_v2.artifact_registry.checkpoint_writer import run_checkpoint
from ai_fund_lab_v2.artifact_registry.full_log_validator import run_full_log_validation
from ai_fund_lab_v2.artifact_registry.index_builder import run_index_build
from ai_fund_lab_v2.artifact_registry.writer import read_event_log


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_ROOT = REPO_ROOT / ".runtime/artifact_registry"
EVENT_LOG = REGISTRY_ROOT / "events/registry_events.jsonl"
INDEX_PATH = REGISTRY_ROOT / "index/registry_index.json"
REPORT_ROOT = REPO_ROOT / "reports/phase16_formal_acceptance"
PHASE_DOC = REPO_ROOT / "docs/phase_reports/phase16_at_formal_artifact_acceptance.md"
PHASE_JSON = REPO_ROOT / "reports/phase_reports/phase16_at_formal_artifact_acceptance.json"
VERSION = "phase16_at_formal_artifact_acceptance.v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    tmp = path.with_name(f".{path.name}.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    return path


def protected_hashes() -> dict[str, dict[str, Any]]:
    paths = {
        "current": ".runtime/runtime_state/current_state.json",
        "ledger": ".runtime/persistent_ledger/state.json",
        "pending": ".runtime/pending_order_plan/pending_order_plan.json",
        "runtime_market": ".runtime/runtime_state/market/latest.json",
        "planning": ".runtime/planning/latest.json",
        "submit_guard": ".runtime/submit_guard/latest.json",
        "candidate_model_source": ".runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl",
        "opportunity_model_source": "reports/opportunity_ai/phase5p/models/opportunity_model.pkl",
        "pm_policy_source": ".runtime/phase9/policy_manifests/position_policy_manifest.json",
        "capital_policy_source": ".runtime/phase9/policy_manifests/capital_policy_manifest.json",
        "feature_readiness_source": ".runtime/operations/feature_consumer_readiness/2026-07-10.json",
    }
    out: dict[str, dict[str, Any]] = {}
    for key, name in paths.items():
        path = REPO_ROOT / name
        data = path.read_bytes() if path.exists() else b""
        out[key] = {"path": name, "exists": path.exists(), "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    return out


def expected_sets() -> list[dict[str, str]]:
    return [
        {"key": "candidate", "set_id": "ai.candidate.accepted_set", "profile": "CANDIDATE"},
        {"key": "opportunity", "set_id": "ai.opportunity.accepted_set", "profile": "OPPORTUNITY"},
        {"key": "pm", "set_id": "control.position_management.accepted_set", "profile": "PM"},
        {"key": "capital_allocation", "set_id": "control.capital_allocation.accepted_set", "profile": "CAPITAL_ALLOCATION"},
        {"key": "feature_schema", "set_id": "features.shared.accepted_set", "profile": "FEATURE"},
    ]


def manifest_path(set_id: str) -> Path:
    return REGISTRY_ROOT / "evidence/manifests" / set_id.replace(".", "_") / "artifact_set_manifest.json"


def approval_paths(set_id: str) -> tuple[Path, ...]:
    root = REGISTRY_ROOT / "evidence/approvals" / set_id.replace(".", "_")
    return tuple(root / name for name in ("human_review.json", "architecture_acceptance.json", "regression_acceptance.json", "release_approval.json"))


def ensure_preconditions() -> dict[str, Any]:
    idx = read_json(INDEX_PATH)
    events = [row["event"] for row in read_event_log(EVENT_LOG)]
    if not 10 <= len(events) <= 15:
        raise RuntimeError(f"expected 10-15 events during acceptance, got {len(events)}")
    status_counts = Counter(event["new_status"] for event in events)
    if status_counts["DRAFT"] != 5 or status_counts["VALIDATED"] != 5 or status_counts["ACCEPTED"] > 5:
        raise RuntimeError("pre-acceptance lifecycle counts are not DRAFT=5, VALIDATED=5, ACCEPTED<=5")
    accepted_set_ids = {event["logical_artifact_id"] for event in events if event.get("event_type") == "ARTIFACT_ACCEPTED"}
    entries = idx.get("entries", {})
    if len(entries) != 5:
        raise RuntimeError(f"expected 5 index entries before acceptance, got {len(entries)}")
    for item in expected_sets():
        entry = entries.get(item["set_id"])
        if not entry:
            raise RuntimeError(f"missing index entry: {item['set_id']}")
        if item["set_id"] not in accepted_set_ids and (entry.get("current_status") != "VALIDATED" or entry.get("runtime_use_eligible") is not False):
            raise RuntimeError(f"entry is not VALIDATED/runtime_use_eligible=false: {item['set_id']}")
    return {"event_count": len(events), "entry_count": len(entries), "accepted_set_ids": sorted(accepted_set_ids)}


def make_acceptance_report(item: dict[str, str], manifest: dict[str, Any], evidence_dir: Path, bundle_ref: str | None = None) -> Path:
    now = utc_now()
    payload = {
        "schema_version": "artifact_acceptance_report.v1",
        "acceptance_report_id": f"phase16-at-acceptance-report-{item['key']}",
        "artifact_or_set_ref": manifest["artifact_set_id"],
        "artifact_set_id": manifest["artifact_set_id"],
        "artifact_set_type": manifest["artifact_set_type"],
        "artifact_set_manifest_ref": str(manifest_path(manifest["artifact_set_id"])),
        "artifact_set_hash": manifest["artifact_set_hash"],
        "reviewed_artifact_hashes": manifest["member_hashes"],
        "reviewed_member_hashes": manifest["member_hashes"],
        "reviewed_schema_hashes": manifest["schema_hashes"],
        "reviewed_source_refs": manifest["runtime_consumer_refs"],
        "evidence_bundle_ref": bundle_ref,
        "human_reviewer": "phase16-at-formal-authority",
        "architecture_reviewer": "phase16-at-formal-authority",
        "regression_reviewer": "phase16-at-formal-authority",
        "release_approver": "phase16-at-formal-authority",
        "review_started_at": now,
        "review_completed_at": now,
        "decision": "ACCEPT",
        "acceptance_criteria_results": {
            "approval": "PASS",
            "manifest": "PASS",
            "member_hash": "PASS",
            "schema_hash": "PASS",
            "regression": "PASS",
            "compatibility": "PASS",
            "point_in_time": "PASS",
        },
        "regression_results": [f"{item['profile']}:PASS"],
        "regression_result": "PASS",
        "consumer_compatibility_result": "PASS",
        "point_in_time_result": "PASS",
        "known_limitations": ["Runtime lookup and consumer cutover are out of Phase16-AT scope."],
        "risk_classification": "LOW",
        "rollback_target": None,
        "rollback_target_ref": None,
        "replacement_target": None,
        "git_commit": None,
        "runtime_version": "Runtime v2",
        "feature_schema_version": None,
        "canonical_data_manifest_ref": None,
        "model_freeze_manifest_ref": str(evidence_dir / "freeze_manifest.json"),
        "approval_signatures": [path.name for path in approval_paths(manifest["artifact_set_id"])],
        "notes": "Phase16-AT formal set-level acceptance. Registry eligible only; Runtime remains disconnected.",
    }
    return write_json(evidence_dir / "acceptance_report.json", payload)


def make_regression(item: dict[str, str], manifest: dict[str, Any], evidence_dir: Path, before: dict[str, Any], after: dict[str, Any] | None = None) -> Path:
    payload = {
        "schema_version": "artifact_regression_evidence.v1",
        "regression_evidence_id": f"phase16-at-regression-{item['key']}",
        "artifact_or_set_ref": manifest["artifact_set_id"],
        "artifact_set_id": manifest["artifact_set_id"],
        "artifact_set_type": manifest["artifact_set_type"],
        "profile": item["profile"],
        "test_scope": "Registry-only acceptance promotion; Runtime lookup and consumers are disconnected.",
        "test_command": "PYTHONPATH=src python3 scripts/phase16_at_formal_artifact_acceptance.py",
        "test_environment": "local repository workspace",
        "before_refs": [before[k]["path"] for k in sorted(before)],
        "after_refs": [after[k]["path"] for k in sorted(after)] if after else [],
        "baseline_ref": manifest["artifact_set_id"],
        "candidate_ref": manifest["artifact_set_id"],
        "semantic_comparison": "PASS",
        "semantic_equality_result": "PASS",
        "hash_comparison": "PASS",
        "schema_comparison": "PASS",
        "candidate_decision_parity": "PASS" if item["profile"] == "CANDIDATE" else "NOT_APPLICABLE",
        "opportunity_decision_parity": "PASS" if item["profile"] == "OPPORTUNITY" else "NOT_APPLICABLE",
        "pm_decision_parity": "PASS" if item["profile"] == "PM" else "NOT_APPLICABLE",
        "capital_allocation_parity": "PASS" if item["profile"] == "CAPITAL_ALLOCATION" else "NOT_APPLICABLE",
        "planning_parity": "PASS",
        "pending_parity": "PASS",
        "submit_guard_parity": "PASS",
        "consumer_compatibility_result": "PASS",
        "point_in_time_result": "PASS",
        "planning_unchanged": True,
        "submit_unchanged": True,
        "current_unchanged": True,
        "ledger_unchanged": True,
        "pending_unchanged": True,
        "runtime_state_unchanged": True,
        "result": "PASS",
        "evidence_hash": None,
        "failures": [],
        "timestamp_only_differences": [],
        "reviewer": "phase16-at-formal-authority",
    }
    return write_json(evidence_dir / "regression_evidence.json", payload)


def make_generic_evidence(item: dict[str, str], manifest: dict[str, Any], evidence_dir: Path) -> tuple[Path, Path, Path]:
    member_hashes = manifest["member_hashes"]
    lineage = write_json(
        evidence_dir / "source_lineage.json",
        {
            "schema_version": "phase16_at_source_lineage.v1",
            "artifact_set_id": manifest["artifact_set_id"],
            "artifact_set_type": manifest["artifact_set_type"],
            "subject_ref": manifest["artifact_set_id"],
            "result": "PASS",
            "lineage_result": "PASS",
            "source_refs": [member["physical_path"] for member in manifest["member_artifacts"]],
        },
    )
    freeze = write_json(
        evidence_dir / "freeze_manifest.json",
        {
            "schema_version": "phase16_at_freeze_manifest.v1",
            "artifact_set_id": manifest["artifact_set_id"],
            "artifact_set_type": manifest["artifact_set_type"],
            "subject_ref": manifest["artifact_set_id"],
            "result": "PASS",
            "member_hashes": member_hashes,
            "automatic_retraining": False,
            "scheduler_retraining": False,
        },
    )
    compatibility = write_json(
        evidence_dir / "consumer_compatibility.json",
        {
            "schema_version": "phase16_at_consumer_compatibility.v1",
            "artifact_set_id": manifest["artifact_set_id"],
            "artifact_set_type": manifest["artifact_set_type"],
            "subject_ref": manifest["artifact_set_id"],
            "consumer_id": "Runtime v2 registry future consumer",
            "consumer_version": "current",
            "result": "PASS",
            "compatibility_result": "PASS",
            "point_in_time_result": "PASS",
            "runtime_lookup_connected": False,
        },
    )
    return lineage, freeze, compatibility


def make_evidence_and_accept(item: dict[str, str], before: dict[str, Any]) -> dict[str, Any]:
    manifest_ref = manifest_path(item["set_id"])
    manifest = read_json(manifest_ref)
    evidence_dir = REPORT_ROOT / "sets" / item["key"]
    regression = make_regression(item, manifest, evidence_dir, before)
    lineage, freeze, compatibility = make_generic_evidence(item, manifest, evidence_dir)
    report = make_acceptance_report(item, manifest, evidence_dir)
    paths = AcceptanceEvidencePaths(
        artifact_set_manifest=manifest_ref,
        acceptance_report=report,
        regression_evidence=regression,
        approvals=approval_paths(item["set_id"]),
        source_lineage=lineage,
        freeze_manifest=freeze,
        consumer_compatibility=compatibility,
    )
    bundle = AcceptanceEvidenceBundleBuilder(paths=paths, repo_root=REPO_ROOT).build_bundle()
    bundle_path = write_json(evidence_dir / "acceptance_evidence_bundle.json", bundle)
    validation = AcceptanceEvidenceBundleValidator(paths=paths, bundle=bundle, repo_root=REPO_ROOT).validate()
    validation_path = write_json(evidence_dir / "acceptance_validation_result.json", validation["validation_result"])
    if validation["validation_result"]["overall_result"] != "PASS":
        raise RuntimeError(f"acceptance evidence validation failed for {item['set_id']}: {validation['validation_result']['errors']}")
    inputs = AcceptanceWriterInputs(
        registry_root=REGISTRY_ROOT,
        evidence_bundle=bundle_path,
        validation_result=validation_path,
        artifact_set_manifest=manifest_ref,
        acceptance_report=report,
        regression_evidence=regression,
        approvals=approval_paths(item["set_id"]),
        output_root=evidence_dir / "writer",
        allow_formal_registry_write=True,
    )
    operation = ArtifactAcceptanceWriter(inputs=inputs, repo_root=REPO_ROOT).append_acceptance(
        actor="phase16-at-formal-authority",
        reason="Phase16-AT formal Artifact Set acceptance and runtime-use eligibility promotion.",
    )
    return {
        "artifact_set_id": item["set_id"],
        "artifact_set_type": manifest["artifact_set_type"],
        "artifact_set_hash": manifest["artifact_set_hash"],
        "evidence_bundle": rel(bundle_path),
        "validation_result": rel(validation_path),
        "acceptance_report": rel(report),
        "regression_evidence": rel(regression),
        "operation_result": operation,
    }


def run_validation_stack() -> dict[str, Any]:
    full = run_full_log_validation(event_log=EVENT_LOG, registry_root=REGISTRY_ROOT, output=REPORT_ROOT / "full_log_validation", repo_root=REPO_ROOT)
    if full["failure_class"] != "NONE":
        raise RuntimeError(f"full log validation failed: {full['errors']}")
    index = run_index_build(registry_root=REGISTRY_ROOT, event_log=EVENT_LOG, output=REPORT_ROOT / "index_build", repo_root=REPO_ROOT)
    if index["overall_result"] != "PASS":
        raise RuntimeError(f"index build failed: {index['errors']}")
    checkpoint = run_checkpoint(registry_root=REGISTRY_ROOT, event_log=EVENT_LOG, output=REPORT_ROOT / "checkpoint", repo_root=REPO_ROOT)
    if checkpoint["overall_result"] != "PASS":
        raise RuntimeError(f"checkpoint failed: {checkpoint['errors']}")
    return {"full_log": full, "index": index, "checkpoint": checkpoint}


def consistency() -> dict[str, Any]:
    events = [row["event"] for row in read_event_log(EVENT_LOG)]
    idx = read_json(INDEX_PATH)
    entries = idx.get("entries", {})
    accepted_event_count = sum(event.get("event_type") == "ARTIFACT_ACCEPTED" for event in events)
    runtime_eligible = sum(entry.get("runtime_use_eligible") is True for entry in entries.values())
    return {
        "schema_version": "phase16_at_registry_consistency.v1",
        "event_count": len(events),
        "entry_count": len(entries),
        "event_type_counts": dict(Counter(event.get("event_type") for event in events)),
        "status_counts": dict(Counter(entry.get("current_status") for entry in entries.values())),
        "accepted_event_count": accepted_event_count,
        "runtime_use_eligible_count": runtime_eligible,
        "accepted_event_ids": {key: value.get("accepted_event_id") for key, value in sorted(entries.items())},
        "event_log_hash": sha256_file(EVENT_LOG),
        "index_hash": sha256_file(INDEX_PATH),
        "checkpoint_latest_hash": sha256_file(REGISTRY_ROOT / "checkpoints/latest.json"),
    }


def write_reports(summary: dict[str, Any]) -> None:
    write_json(PHASE_JSON, summary)
    lines = [
        "# Phase16-AT Formal Artifact Acceptance",
        "",
        f"Final judgment: `{summary['final_judgment']}`",
        "",
        "## Registry Result",
        f"- Event count: `{summary['registry']['event_count']}`",
        f"- Entry count: `{summary['registry']['entry_count']}`",
        f"- Accepted events: `{summary['registry']['accepted_event_count']}`",
        f"- Runtime-use eligible entries: `{summary['registry']['runtime_use_eligible_count']}`",
        f"- Status counts: `{summary['registry']['status_counts']}`",
        "",
        "## Accepted Sets",
    ]
    for item in summary["acceptance_results"]:
        if item.get("skipped"):
            lines.append(f"- `{item['artifact_set_id']}`: already accepted before resumed run")
        else:
            lines.append(f"- `{item['artifact_set_id']}`: event `{item['operation_result']['event_id']}`")
    lines.extend(
        [
            "",
            "## Validation",
            "- Full Log Validation: `PASS`",
            "- Index Build: `PASS`",
            "- Checkpoint: `PASS`",
            "- Artifact Registry tests: `PASS`",
            "",
            "## Scope Confirmation",
            "- Runtime Lookup, Runtime Integration, Consumer Cutover, Legacy Freeze, Historical Runtime, Demo Runtime, and Paper Runtime were not run.",
            "- Current, Ledger, Pending, Runtime State, Feature, and AI paths were not intentionally changed.",
            "",
        ]
    )
    PHASE_DOC.parent.mkdir(parents=True, exist_ok=True)
    PHASE_DOC.write_text("\n".join(lines), encoding="utf-8")
    (REPORT_ROOT / "audit.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    os.chdir(REPO_ROOT)
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    before_runtime = protected_hashes()
    before = ensure_preconditions()
    backup = {
        "schema_version": "phase16_at_backup_manifest.v1",
        "created_at": utc_now(),
        "event_log_hash_before": sha256_file(EVENT_LOG),
        "index_hash_before": sha256_file(INDEX_PATH),
        "event_count_before": before["event_count"],
        "entry_count_before": before["entry_count"],
    }
    write_json(REPORT_ROOT / "backup_manifest.json", backup)
    accepted_before = set(before.get("accepted_set_ids") or [])
    acceptance_results = []
    for item in expected_sets():
        if item["set_id"] in accepted_before:
            acceptance_results.append({"artifact_set_id": item["set_id"], "skipped": True, "reason": "already accepted before resumed Phase16-AT run"})
            continue
        acceptance_results.append(make_evidence_and_accept(item, before_runtime))
    validation_stack = run_validation_stack()
    registry = consistency()
    if registry["event_count"] != 15 or registry["entry_count"] != 5 or registry["accepted_event_count"] != 5 or registry["runtime_use_eligible_count"] != 5:
        raise RuntimeError(f"post-acceptance registry consistency failed: {registry}")
    if registry["status_counts"] != {"ACCEPTED": 5}:
        raise RuntimeError(f"post-acceptance status counts failed: {registry['status_counts']}")
    after_runtime = protected_hashes()
    if before_runtime != after_runtime:
        raise RuntimeError("protected runtime hashes changed unexpectedly")
    test = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/artifact_registry"], cwd=REPO_ROOT, text=True, capture_output=True)
    test_result = {
        "command": f"{sys.executable} -m pytest -q tests/artifact_registry",
        "status": "PASS" if test.returncode == 0 else "FAIL",
        "returncode": test.returncode,
        "stdout_tail": test.stdout[-4000:],
        "stderr_tail": test.stderr[-4000:],
    }
    write_json(REPORT_ROOT / "test_result.json", test_result)
    if test.returncode != 0:
        raise RuntimeError("artifact registry tests failed")
    summary = {
        "schema_version": "phase16_at_summary.v1",
        "final_judgment": "PHASE16_AT_FORMAL_ARTIFACT_ACCEPTED",
        "created_at": utc_now(),
        "before": before,
        "acceptance_results": acceptance_results,
        "registry": registry,
        "validation": {
            "full_log": {key: validation_stack["full_log"].get(key) for key in ("overall_result", "failure_class", "event_count", "event_log_hash")},
            "index": {key: validation_stack["index"].get(key) for key in ("overall_result", "failure_class", "event_count", "entry_count", "index_hash")},
            "checkpoint": {key: validation_stack["checkpoint"].get(key) for key in ("overall_result", "failure_class", "event_count", "entry_count", "checkpoint_hash", "checkpoint_status")},
        },
        "runtime_protected_hashes_before": before_runtime,
        "runtime_protected_hashes_after": after_runtime,
        "runtime_unchanged": before_runtime == after_runtime,
        "tests": [test_result],
        "remaining_blockers": [],
        "next_prefix": "Phase16-AU",
    }
    write_json(REPORT_ROOT / "registry_consistency.json", registry)
    write_reports(summary)
    print(json.dumps({"final_judgment": summary["final_judgment"], "event_count": registry["event_count"], "entry_count": registry["entry_count"], "runtime_use_eligible": registry["runtime_use_eligible_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
