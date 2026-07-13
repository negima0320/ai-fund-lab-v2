from __future__ import annotations

import errno
import fcntl
import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.artifact_registry.inventory import stable_json_hash
from ai_fund_lab_v2.artifact_registry.validator import load_schemas, validate_registry_event


REGISTRY_SCHEMA_VERSION = "artifact_registry_event_log_writer.v1"
DEFAULT_REGISTRY_ROOT = Path(".runtime/artifact_registry")
EVENT_LOG_RELATIVE_PATH = Path("events/registry_events.jsonl")
LOCK_RELATIVE_PATH = Path("locks/registry.lock")
ALLOWED_WRITER_STATUSES = {"DRAFT", "VALIDATED"}


class RegistryEventWriterError(RuntimeError):
    pass


class RegistryEventValidationError(RegistryEventWriterError):
    pass


class RegistryDuplicateEventError(RegistryEventWriterError):
    pass


class RegistryLogCorruptionError(RegistryEventWriterError):
    pass


class RegistryLockError(RegistryEventWriterError):
    pass


@dataclass(frozen=True)
class RegistryAppendResult:
    schema_version: str
    status: str
    event_id: str
    fingerprint: str
    event_log_path: str
    event_count_after_append: int
    bytes_appended: int


class RegistryEventLogWriter:
    def __init__(self, registry_root: Path | str = DEFAULT_REGISTRY_ROOT, *, repo_root: Path | str | None = None, lock_timeout_seconds: float = 10.0) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else Path.cwd()
        self.registry_root = Path(registry_root)
        if not self.registry_root.is_absolute():
            self.registry_root = self.repo_root / self.registry_root
        self.lock_timeout_seconds = lock_timeout_seconds

    @property
    def event_log_path(self) -> Path:
        return self.registry_root / EVENT_LOG_RELATIVE_PATH

    @property
    def lock_path(self) -> Path:
        return self.registry_root / LOCK_RELATIVE_PATH

    def initialize_storage(self) -> None:
        (self.registry_root / "events").mkdir(parents=True, exist_ok=True)
        (self.registry_root / "locks").mkdir(parents=True, exist_ok=True)
        (self.registry_root / "schema").mkdir(parents=True, exist_ok=True)
        (self.registry_root / "checkpoints").mkdir(parents=True, exist_ok=True)
        self.event_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.event_log_path.touch(exist_ok=True)
        self.lock_path.touch(exist_ok=True)

    def append_event(self, event: dict[str, Any]) -> RegistryAppendResult:
        self.initialize_storage()
        event_to_append = dict(event)
        fingerprint = event_fingerprint(event_to_append)
        event_to_append["event_id"] = event_to_append.get("event_id") or event_id_for_fingerprint(fingerprint)

        validation = validate_registry_event(
            event_to_append,
            schemas=load_schemas(self.repo_root / "docs/02_architecture/schemas"),
            repo_root=self.repo_root,
            subject_ref=event_to_append["event_id"],
        )
        if validation["overall_result"] != "PASS" or validation["failure_class"] != "NONE":
            raise RegistryEventValidationError("registry event validation did not PASS")
        if event_to_append.get("new_status") not in ALLOWED_WRITER_STATUSES:
            raise RegistryEventValidationError(f"writer only supports DRAFT/VALIDATED events: {event_to_append.get('new_status')}")
        if event_to_append.get("runtime_use_eligible") is True:
            raise RegistryEventValidationError("writer must not append runtime-use eligible events")

        line = json.dumps(event_to_append, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8") + b"\n"
        with self._exclusive_lock():
            existing = read_event_log(self.event_log_path)
            if any(row["event"].get("event_id") == event_to_append["event_id"] for row in existing):
                raise RegistryDuplicateEventError(f"duplicate event_id: {event_to_append['event_id']}")
            if any(row["fingerprint"] == fingerprint for row in existing):
                raise RegistryDuplicateEventError(f"duplicate fingerprint: {fingerprint}")
            append_line_atomic(self.event_log_path, line)
            return RegistryAppendResult(
                schema_version=REGISTRY_SCHEMA_VERSION,
                status="APPENDED",
                event_id=event_to_append["event_id"],
                fingerprint=fingerprint,
                event_log_path=str(self.event_log_path),
                event_count_after_append=len(existing) + 1,
                bytes_appended=len(line),
            )

    def _exclusive_lock(self) -> "_LockedFile":
        return _LockedFile(self.lock_path, timeout_seconds=self.lock_timeout_seconds)


class _LockedFile:
    def __init__(self, path: Path, *, timeout_seconds: float) -> None:
        self.path = path
        self.timeout_seconds = timeout_seconds
        self._fh: Any | None = None

    def __enter__(self) -> "_LockedFile":
        self._fh = self.path.open("a+b")
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except BlockingIOError as exc:
                if time.monotonic() >= deadline:
                    raise RegistryLockError(f"could not acquire registry lock: {self.path}") from exc
                time.sleep(0.01)

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._fh is not None:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            self._fh.close()


def event_fingerprint(event: dict[str, Any]) -> str:
    payload = {
        "event_type": event.get("event_type"),
        "logical_artifact_id": event.get("logical_artifact_id"),
        "artifact_instance_id": event.get("artifact_instance_id"),
        "new_status": event.get("new_status"),
        "content_hash": event.get("content_hash"),
        "schema_hash": event.get("schema_hash"),
        "authority_ref": event.get("authority_ref"),
        "acceptance_report_ref": event.get("acceptance_report_ref"),
    }
    return stable_json_hash(payload)


def event_id_for_fingerprint(fingerprint: str) -> str:
    return f"event-{uuid.uuid4()}-{fingerprint[:16]}"


def read_event_log(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("rb") as fh:
        for line_number, raw in enumerate(fh, start=1):
            if not raw.endswith(b"\n"):
                raise RegistryLogCorruptionError(f"partial event line at {path}:{line_number}")
            if not raw.strip():
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise RegistryLogCorruptionError(f"invalid JSON event at {path}:{line_number}") from exc
            if not isinstance(event, dict):
                raise RegistryLogCorruptionError(f"event is not an object at {path}:{line_number}")
            rows.append({"event": event, "fingerprint": event_fingerprint(event)})
    return rows


def append_line_atomic(path: Path, line: bytes) -> None:
    if not line.endswith(b"\n"):
        raise ValueError("event log append line must end with newline")
    flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
    fd = os.open(path, flags, 0o644)
    try:
        view = memoryview(line)
        total = 0
        while total < len(line):
            try:
                written = os.write(fd, view[total:])
            except OSError as exc:
                if exc.errno == errno.EINTR:
                    continue
                raise
            if written == 0:
                raise OSError("zero-byte write during registry event append")
            total += written
        os.fsync(fd)
    finally:
        os.close(fd)
