from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TRANSACTION_STATES = (
    "PREPARED",
    "VALIDATED",
    "WRITING_EVENT",
    "WRITING_INDEX",
    "WRITING_CHECKPOINT",
    "POST_VALIDATING",
    "COMMITTED",
    "ROLLING_BACK",
    "RESTORED",
    "RESTORE_FAILED",
    "CRITICAL",
)
RESTORE_FAILURES = {
    "restore_event_failure": "event_restore_failure",
    "restore_index_failure": "index_restore_failure",
    "restore_checkpoint_failure": "checkpoint_restore_failure",
    "temporary_cleanup_failure": "temporary_cleanup_failure",
    "restore_validation_failure": "restore_validation_failure",
}


@dataclass(frozen=True)
class RegistryRehearsalRequest:
    request_id: str
    operation: str
    authority_decision: str
    target_artifact_set_id: str
    previous_artifact_set_id: str | None
    reason: str


@dataclass(frozen=True)
class RegistryRehearsalResult:
    status: str
    transaction_id: str
    operation: str
    registry_accepted_event_written: bool
    runtime_switch_performed: bool
    buy_restart_performed: bool
    evidence_path: str
    transaction_hash: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AtomicRollbackRequest:
    request_id: str
    requested_bundle: str
    rollback_target: str
    reason: str
    requester: str
    authority_decision: str
    expected_current_state_hash: str
    target_state_hash: str
    idempotency_key: str


@dataclass(frozen=True)
class AtomicRevokeRequest:
    request_id: str
    artifact_identity: str
    reason: str
    requester: str
    authority_decision: str
    fallback_target: str
    expected_current_state_hash: str
    idempotency_key: str


def rehearse_rollback_or_revoke(request: RegistryRehearsalRequest, *, output_dir: Path) -> RegistryRehearsalResult:
    if request.operation not in {"ROLLBACK", "REVOKE"}:
        raise ValueError("operation must be ROLLBACK or REVOKE")
    if request.authority_decision not in {"APPROVED", "REJECTED"}:
        raise ValueError("authority_decision must be APPROVED or REJECTED")
    status = "REJECTED" if request.authority_decision == "REJECTED" else "REHEARSED"
    payload = {
        "schema_version": "ai_lifecycle_registry_rollback_revoke_rehearsal.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "request": asdict(request),
        "status": status,
        "registry_accepted_event_written": False,
        "runtime_switch_performed": False,
        "buy_restart_performed": False,
        "previous_state_preserved": True,
        "next_job_discovery_required": request.authority_decision == "APPROVED",
    }
    tx_hash = _stable_hash(payload)
    payload["transaction_hash"] = tx_hash
    path = output_dir / f"{request.request_id}_{request.operation.lower()}_rehearsal.json"
    _atomic_write_json(path, payload)
    return RegistryRehearsalResult(
        status=status,
        transaction_id=request.request_id,
        operation=request.operation,
        registry_accepted_event_written=False,
        runtime_switch_performed=False,
        buy_restart_performed=False,
        evidence_path=str(path),
        transaction_hash=tx_hash,
        reason=request.reason,
    )


class IsolatedRegistryRollbackRevokeOperator:
    def __init__(self, *, registry_root: Path | str) -> None:
        self.registry_root = Path(registry_root)
        self.registry_root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.registry_root / "accepted_state.json"
        self.event_log_path = self.registry_root / "events.jsonl"
        self.index_path = self.registry_root / "index.json"
        self.checkpoint_path = self.registry_root / "checkpoint.json"
        self.audit_dir = self.registry_root / "audit"

    def initialize(self, *, accepted_state: dict[str, Any]) -> dict[str, Any]:
        payload = {"schema_version": "isolated_registry_state.v1", "accepted": accepted_state}
        payload["state_hash"] = _stable_hash(payload["accepted"])
        self._commit(payload, {"event_type": "INITIALIZED", "state_hash": payload["state_hash"]})
        return payload

    def atomic_rollback(self, request: AtomicRollbackRequest, *, targets: dict[str, dict[str, Any]], fail_at: str | None = None) -> dict[str, Any]:
        return self._transaction(
            request_id=request.request_id,
            idempotency_key=request.idempotency_key,
            authority_decision=request.authority_decision,
            expected_current_state_hash=request.expected_current_state_hash,
            target_identity=request.rollback_target,
            target_state_hash=request.target_state_hash,
            targets=targets,
            event_type="ROLLBACK_REHEARSED",
            reason=request.reason,
            fail_at=fail_at,
        )

    def atomic_revoke(self, request: AtomicRevokeRequest, *, targets: dict[str, dict[str, Any]], fail_at: str | None = None) -> dict[str, Any]:
        return self._transaction(
            request_id=request.request_id,
            idempotency_key=request.idempotency_key,
            authority_decision=request.authority_decision,
            expected_current_state_hash=request.expected_current_state_hash,
            target_identity=request.fallback_target,
            target_state_hash=_stable_hash(targets.get(request.fallback_target, {})),
            targets=targets,
            event_type="REVOKE_REHEARSED",
            reason=request.reason,
            fail_at=fail_at,
        )

    def _transaction(self, *, request_id: str, idempotency_key: str, authority_decision: str, expected_current_state_hash: str, target_identity: str, target_state_hash: str, targets: dict[str, dict[str, Any]], event_type: str, reason: str, fail_at: str | None) -> dict[str, Any]:
        audit_path = self.audit_dir / f"{idempotency_key}.json"
        if audit_path.exists():
            return json.loads(audit_path.read_text(encoding="utf-8"))
        before = self._read_state()
        before_hashes = self._registry_hashes()
        if authority_decision != "APPROVED":
            result = self._audit(request_id, idempotency_key, event_type, "REJECTED", reason, before, before)
            _atomic_write_json(audit_path, result)
            return result
        if before.get("state_hash") != expected_current_state_hash:
            result = self._audit(request_id, idempotency_key, event_type, "FAILED", "current_state_mismatch", before, before)
            _atomic_write_json(audit_path, result)
            return result
        if target_identity not in targets:
            result = self._audit(request_id, idempotency_key, event_type, "FAILED", "target_missing", before, before)
            _atomic_write_json(audit_path, result)
            return result
        target_state = {"schema_version": "isolated_registry_state.v1", "accepted": targets[target_identity]}
        target_state["state_hash"] = _stable_hash(target_state["accepted"])
        if target_state_hash and target_state["state_hash"] != target_state_hash:
            result = self._audit(request_id, idempotency_key, event_type, "FAILED", "target_hash_mismatch", before, before)
            _atomic_write_json(audit_path, result)
            return result
        if fail_at == "before_commit":
            result = self._audit(request_id, idempotency_key, event_type, "FAILED", "partial_transaction_failure_rehearsed", before, before)
            _atomic_write_json(audit_path, result)
            return result
        try:
            self._commit(target_state, {"event_type": event_type, "request_id": request_id, "reason": reason, "previous_state_hash": before["state_hash"], "new_state_hash": target_state["state_hash"]}, fail_at=fail_at)
        except RuntimeError as exc:
            after_failure = self._read_state()
            restore_failed = str(exc).startswith("restore_failed:")
            result = self._audit(
                request_id,
                idempotency_key,
                event_type,
                "CRITICAL" if restore_failed else "FAILED",
                str(exc).removeprefix("restore_failed:"),
                before,
                after_failure,
            )
            after_hashes = self._registry_hashes()
            result.update(
                {
                    "transaction_state": "CRITICAL" if restore_failed else "RESTORED",
                    "transaction_states": ["PREPARED", "VALIDATED", "WRITING_EVENT", "ROLLING_BACK", "RESTORE_FAILED", "CRITICAL"]
                    if restore_failed
                    else ["PREPARED", "VALIDATED", "WRITING_EVENT", "ROLLING_BACK", "RESTORED"],
                    "restore_status": "RESTORE_FAILED" if restore_failed else "RESTORED",
                    "manual_recovery_required": bool(restore_failed),
                    "accepted_state_unchanged": before.get("state_hash") == after_failure.get("state_hash"),
                    "registry_hash_unchanged": before_hashes == after_hashes,
                    "registry_hashes_before": before_hashes,
                    "registry_hashes_after": after_hashes,
                    "partial_state": before.get("state_hash") != after_failure.get("state_hash"),
                    "partial_event": before_hashes.get("event_log") != after_hashes.get("event_log"),
                    "partial_index": before_hashes.get("index") != after_hashes.get("index"),
                    "partial_checkpoint": before_hashes.get("checkpoint") != after_hashes.get("checkpoint"),
                }
            )
            result["audit_hash"] = _stable_hash({k: v for k, v in result.items() if k != "audit_hash"})
            _atomic_write_json(audit_path, result)
            return result
        after = self._read_state()
        result = self._audit(request_id, idempotency_key, event_type, "PASS", reason, before, after)
        result.update({"transaction_state": "COMMITTED", "transaction_states": ["PREPARED", "VALIDATED", "WRITING_EVENT", "WRITING_INDEX", "WRITING_CHECKPOINT", "POST_VALIDATING", "COMMITTED"], "restore_status": "NOT_REQUIRED", "manual_recovery_required": False})
        result["audit_hash"] = _stable_hash({k: v for k, v in result.items() if k != "audit_hash"})
        _atomic_write_json(audit_path, result)
        return result

    def _read_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return self.initialize(accepted_state={})
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _commit(self, state: dict[str, Any], event: dict[str, Any], *, fail_at: str | None = None) -> None:
        event = {"created_at": datetime.now(timezone.utc).isoformat(), **event}
        old_log = self.event_log_path.read_text(encoding="utf-8") if self.event_log_path.exists() else ""
        new_log = old_log + json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
        index = {"schema_version": "isolated_registry_index.v1", "state_hash": state["state_hash"], "event_count": len(new_log.splitlines())}
        checkpoint = {"schema_version": "isolated_registry_checkpoint.v1", "state_hash": state["state_hash"], "index_hash": _stable_hash(index), "event_log_hash": hashlib.sha256(new_log.encode("utf-8")).hexdigest()}
        snapshots = self._snapshot_files()
        effective_fail_at = self._effective_write_failure(fail_at)
        try:
            _atomic_write_json(self.state_path, state)
            if effective_fail_at == "event_write":
                raise RuntimeError("event_log_write_failure")
            _atomic_write_text(self.event_log_path, new_log)
            if effective_fail_at == "event_replace":
                raise RuntimeError("event_log_atomic_replace_failure")
            if effective_fail_at == "index_write":
                raise RuntimeError("index_write_failure")
            _atomic_write_json(self.index_path, index)
            if effective_fail_at == "checkpoint_write":
                raise RuntimeError("checkpoint_write_failure")
            _atomic_write_json(self.checkpoint_path, checkpoint)
            if effective_fail_at == "post_validation":
                raise RuntimeError("post_write_validation_failure")
            self._validate_consistency(state, new_log, index, checkpoint)
        except Exception as exc:
            try:
                self._restore_files(snapshots, fail_at=fail_at)
            except RuntimeError as restore_exc:
                raise RuntimeError(f"restore_failed:{restore_exc}") from restore_exc
            if isinstance(exc, RuntimeError):
                raise
            raise RuntimeError(str(exc)) from exc

    def _effective_write_failure(self, fail_at: str | None) -> str | None:
        if fail_at == "restore_event_failure":
            return "event_replace"
        if fail_at == "restore_index_failure":
            return "index_write"
        if fail_at == "restore_checkpoint_failure":
            return "checkpoint_write"
        if fail_at in {"temporary_cleanup_failure", "restore_validation_failure"}:
            return "post_validation"
        return fail_at

    def _snapshot_files(self) -> dict[Path, bytes | None]:
        return {
            path: path.read_bytes() if path.exists() else None
            for path in (self.state_path, self.event_log_path, self.index_path, self.checkpoint_path)
        }

    def _restore_files(self, snapshots: dict[Path, bytes | None], *, fail_at: str | None = None) -> None:
        for path, payload in snapshots.items():
            if payload is None:
                if path.exists():
                    path.unlink()
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        if fail_at in RESTORE_FAILURES:
            raise RuntimeError(RESTORE_FAILURES[fail_at])
        self._validate_restored_snapshots(snapshots)

    def _validate_restored_snapshots(self, snapshots: dict[Path, bytes | None]) -> None:
        for path, payload in snapshots.items():
            if payload is None and path.exists():
                raise RuntimeError(f"restore_validation_unexpected_file:{path.name}")
            if payload is not None and (not path.exists() or path.read_bytes() != payload):
                raise RuntimeError(f"restore_validation_mismatch:{path.name}")

    def _registry_hashes(self) -> dict[str, str]:
        return {
            "accepted_state": _file_hash(self.state_path),
            "event_log": _file_hash(self.event_log_path),
            "index": _file_hash(self.index_path),
            "checkpoint": _file_hash(self.checkpoint_path),
        }

    def _validate_consistency(self, state: dict[str, Any], event_log: str, index: dict[str, Any], checkpoint: dict[str, Any]) -> None:
        if index["state_hash"] != state["state_hash"]:
            raise RuntimeError("index_state_hash_mismatch")
        if checkpoint["state_hash"] != state["state_hash"]:
            raise RuntimeError("checkpoint_state_hash_mismatch")
        if checkpoint["index_hash"] != _stable_hash(index):
            raise RuntimeError("checkpoint_index_hash_mismatch")
        if checkpoint["event_log_hash"] != hashlib.sha256(event_log.encode("utf-8")).hexdigest():
            raise RuntimeError("checkpoint_event_log_hash_mismatch")

    def _audit(self, request_id: str, idempotency_key: str, event_type: str, status: str, reason: str, before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "schema_version": "isolated_registry_rollback_revoke_audit.v1",
            "request_id": request_id,
            "idempotency_key": idempotency_key,
            "event_type": event_type,
            "status": status,
            "reason": reason,
            "transaction_state": status,
            "transaction_states": ["PREPARED"],
            "known_transaction_states": list(TRANSACTION_STATES),
            "restore_status": "NOT_REQUIRED",
            "manual_recovery_required": False,
            "before_state_hash": before.get("state_hash"),
            "after_state_hash": after.get("state_hash"),
            "partial_state": False,
            "partial_event": False,
            "partial_index": False,
            "partial_checkpoint": False,
            "event_log_path": str(self.event_log_path),
            "index_path": str(self.index_path),
            "checkpoint_path": str(self.checkpoint_path),
            "audit_hash": "",
        }
        payload["audit_hash"] = _stable_hash(payload)
        return payload


def _stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _atomic_write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
