"""Regression baseline collection for historical Runtime readiness."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.historical_support.common import file_ref, read_json, sha256_file


BASELINE_FILES: dict[str, str] = {
    "registry_event_log": "artifact_registry/events/registry_events.jsonl",
    "registry_index_file": "artifact_registry/index/registry_index.json",
    "registry_latest_checkpoint_file": "artifact_registry/checkpoints/latest.json",
    "current_ledger_state": "persistent_ledger/state.json",
    "pending_order_plan": "pending_order_plan/pending_order_plan.json",
    "runtime_state": "runtime_state/current_state.json",
    "market_state_latest": "runtime_state/market/latest.json",
    "canonical_normalized_ohlcv": "phase9/canonical_data/normalized_daily_quotes/data.parquet",
    "runtime_trading_calendar": "operations/jquants/raw/jquants/trading_calendar/data.parquet",
    "runtime_listed_issues": "operations/jquants/raw/jquants/listed_issues/data.parquet",
}


def collect_regression_baseline(*, runtime_root: Path | str, repo_root: Path | str = ".") -> dict[str, Any]:
    """Collect a read-only hash baseline for historical test readiness."""

    root = Path(runtime_root)
    repo = Path(repo_root)
    git_commit = _git_commit(repo)
    files = {name: file_ref(root / rel, root=root) for name, rel in BASELINE_FILES.items()}
    registry = _registry_summary(root)
    pm_adapter = _pm_adapter_summary(root=root, repo=repo)
    return {
        "schema_version": "runtime_historical_regression_baseline_v1",
        "git_commit": git_commit,
        "runtime_version": "runtime_v2",
        "runtime_root": str(root),
        "files": files,
        "registry": registry,
        "pm_adapter_authority": pm_adapter,
        "collection_mode": "READ_ONLY",
    }


def _git_commit(repo: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    except Exception:
        return "UNKNOWN"


def _registry_summary(root: Path) -> dict[str, Any]:
    index_path = root / "artifact_registry" / "index" / "registry_index.json"
    checkpoint_path = root / "artifact_registry" / "checkpoints" / "latest.json"
    summary: dict[str, Any] = {
        "index_exists": index_path.exists(),
        "checkpoint_exists": checkpoint_path.exists(),
        "accepted_sets": [],
    }
    if index_path.exists():
        index = read_json(index_path)
        entries = index.get("entries") or {}
        if isinstance(entries, dict):
            summary["accepted_sets"] = [
                {
                    "logical_id": key,
                    "status": value.get("status"),
                    "runtime_use_eligible": value.get("runtime_use_eligible"),
                    "content_hash": value.get("content_hash"),
                    "schema_hash": value.get("schema_hash"),
                }
                for key, value in sorted(entries.items())
                if isinstance(value, dict)
            ]
        summary["event_log_hash"] = index.get("event_log_hash")
        summary["index_hash"] = index.get("index_hash")
        summary["event_count"] = index.get("event_count")
    if checkpoint_path.exists():
        checkpoint = read_json(checkpoint_path)
        summary["checkpoint_id"] = checkpoint.get("checkpoint_id")
        summary["checkpoint_hash"] = checkpoint.get("checkpoint_hash")
        summary["materialized_index_hash"] = checkpoint.get("materialized_index_hash")
    return summary


def _pm_adapter_summary(*, root: Path, repo: Path) -> dict[str, Any]:
    current_source = repo / "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py"
    accepted = root / "artifacts/control/position_management/runtime_adapter/default/sha256-6ffa7da2b91f5fd5/runtime_adapter.py"
    current_hash = sha256_file(current_source) if current_source.exists() else ""
    accepted_hash = sha256_file(accepted) if accepted.exists() else ""
    status = "PASS" if current_hash and current_hash == accepted_hash else "ARCHITECTURE_REVIEW_REQUIRED"
    return {
        "status": status,
        "classification": "ARTIFACT_AUTHORITY_GAP" if status != "PASS" else "PASS",
        "current_source": str(current_source),
        "current_source_hash": current_hash,
        "accepted_adapter_path": str(accepted),
        "accepted_adapter_hash": accepted_hash,
        "byte_identical": current_hash == accepted_hash and bool(current_hash),
    }
