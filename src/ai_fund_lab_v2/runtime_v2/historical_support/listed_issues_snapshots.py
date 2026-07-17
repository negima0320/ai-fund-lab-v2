from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable

from ai_fund_lab_v2.data_sources.jquants.client import JQUANTS_LISTED_ISSUES_ENDPOINT, JQuantsClientError
from ai_fund_lab_v2.data_store.schema import validate_records

SNAPSHOT_STORE_SCHEMA_VERSION = "historical_listed_issues_snapshot_store_v1"
SNAPSHOT_RESOLVER_SCHEMA_VERSION = "historical_listed_issues_snapshot_resolver_v1"
SELECTION_POLICY = "latest_snapshot_not_after_business_date"
DEFAULT_MAX_SNAPSHOT_AGE_DAYS = 10
RETENTION_START_DATE = "2021-07-16"


@dataclass(frozen=True)
class SnapshotWriteResult:
    status: str
    classification: str
    requested_date: str
    snapshot_date: str
    provider_effective_date: str
    row_count: int
    storage_path: str
    manifest_path: str
    content_hash: str
    schema_hash: str
    validation_status: str
    duplicate_key_count: int
    reason: str

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ListedIssuesSnapshotResolution:
    status: str
    reason: str
    mode: str
    business_date: str
    snapshot_root: str
    selected_snapshot_date: str
    selected_snapshot_path: str
    selected_manifest_path: str
    selected_content_hash: str
    selected_schema_hash: str
    snapshot_age_days: int | None
    selection_policy: str = SELECTION_POLICY
    future_snapshot_used: bool = False
    content_hash_verified: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": SNAPSHOT_RESOLVER_SCHEMA_VERSION,
            **asdict(self),
        }


def snapshot_data_path(snapshot_root: Path | str, snapshot_date: str, storage_format: str = "parquet") -> Path:
    return Path(snapshot_root) / "snapshots" / snapshot_date / f"data.{storage_format}"


def snapshot_manifest_path(snapshot_root: Path | str, snapshot_date: str) -> Path:
    return Path(snapshot_root) / "snapshots" / snapshot_date / "manifest.json"


def index_path(snapshot_root: Path | str) -> Path:
    return Path(snapshot_root) / "index.json"


def acquisition_manifest_path(snapshot_root: Path | str) -> Path:
    return Path(snapshot_root) / "acquisition_manifest.json"


def latest_path(snapshot_root: Path | str) -> Path:
    return Path(snapshot_root) / "latest.json"


def write_listed_issues_snapshot(
    *,
    snapshot_root: Path | str,
    requested_date: str,
    records: list[dict[str, Any]],
    storage_format: str = "parquet",
    fetched_at: str,
    pagination_metadata: dict[str, Any] | None = None,
    previous_manifest: dict[str, Any] | None = None,
    overwrite: bool = False,
) -> SnapshotWriteResult:
    if storage_format != "parquet":
        raise ValueError("historical listed issues production snapshot store currently requires parquet")
    root = Path(snapshot_root)
    response_dates = sorted({str(record.get("Date")) for record in records if record.get("Date") not in (None, "")})
    snapshot_date = response_dates[0] if len(response_dates) == 1 else requested_date
    data_path = snapshot_data_path(root, snapshot_date, storage_format)
    manifest_path = snapshot_manifest_path(root, snapshot_date)
    validation = validate_records("listed_issues", records)
    schema = schema_fingerprint(records)
    duplicate_key_count = duplicate_date_code_count(records)
    classification = classify_fetch_result(requested_date=requested_date, response_dates=response_dates, row_count=len(records))

    import pandas as pd

    data_path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(records)
    temp_path = data_path.with_suffix(".tmp.parquet")
    frame.to_parquet(temp_path, index=False, engine="pyarrow")
    content_hash = file_hash(temp_path)

    if manifest_path.is_file() and not overwrite:
        existing = read_json(manifest_path)
        existing_hash = str(existing.get("content_hash") or "")
        if existing_hash == content_hash:
            temp_path.unlink(missing_ok=True)
            return SnapshotWriteResult(
                status="SKIPPED",
                classification="VERIFIED_EXISTING",
                requested_date=requested_date,
                snapshot_date=snapshot_date,
                provider_effective_date=snapshot_date,
                row_count=int(existing.get("row_count") or len(records)),
                storage_path=str(data_path),
                manifest_path=str(manifest_path),
                content_hash=content_hash,
                schema_hash=str(existing.get("schema_hash") or schema["schema_hash"]),
                validation_status=str(existing.get("validation_status") or validation.status),
                duplicate_key_count=int(existing.get("duplicate_key_count") or 0),
                reason="existing_snapshot_hash_matches",
            )
        conflict_path = data_path.parent / f"conflict-{hashlib.sha256(content_hash.encode()).hexdigest()[:12]}.parquet"
        temp_path.replace(conflict_path)
        return SnapshotWriteResult(
            status="HALT",
            classification="CONTENT_HASH_CONFLICT",
            requested_date=requested_date,
            snapshot_date=snapshot_date,
            provider_effective_date=snapshot_date,
            row_count=len(records),
            storage_path=str(conflict_path),
            manifest_path=str(manifest_path),
            content_hash=content_hash,
            schema_hash=schema["schema_hash"],
            validation_status=validation.status,
            duplicate_key_count=duplicate_key_count,
            reason="same_snapshot_date_content_hash_differs",
        )

    temp_path.replace(data_path)
    manifest = {
        "schema_version": SNAPSHOT_STORE_SCHEMA_VERSION,
        "requested_date": requested_date,
        "provider_effective_date": snapshot_date,
        "snapshot_date": snapshot_date,
        "row_count": len(records),
        "schema_columns": schema["columns"],
        "schema_hash": schema["schema_hash"],
        "content_hash": content_hash,
        "source_endpoint": JQUANTS_LISTED_ISSUES_ENDPOINT,
        "fetched_at": fetched_at,
        "pagination_metadata": dict(pagination_metadata or {}),
        "storage_format": storage_format,
        "storage_path": str(data_path),
        "duplicate_key_count": duplicate_key_count,
        "validation_status": validation.status,
        "validation_messages": validation.messages,
        "request_result_classification": classification,
        "previous_snapshot_diff_summary": diff_summary(previous_manifest, len(records), content_hash),
        "future_snapshot_used": snapshot_date > requested_date,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    status = "PASS"
    reason = "snapshot_written"
    if validation.status == "ERROR":
        status = "HALT"
        reason = "schema_validation_error"
    elif duplicate_key_count:
        status = "HALT"
        reason = "duplicate_business_key"
    elif manifest["future_snapshot_used"]:
        status = "HALT"
        reason = "future_snapshot_rejected"
    return SnapshotWriteResult(
        status=status,
        classification=classification,
        requested_date=requested_date,
        snapshot_date=snapshot_date,
        provider_effective_date=snapshot_date,
        row_count=len(records),
        storage_path=str(data_path),
        manifest_path=str(manifest_path),
        content_hash=content_hash,
        schema_hash=schema["schema_hash"],
        validation_status=validation.status,
        duplicate_key_count=duplicate_key_count,
        reason=reason,
    )


def rebuild_snapshot_index(snapshot_root: Path | str) -> dict[str, Any]:
    root = Path(snapshot_root)
    manifests = []
    seen: dict[str, str] = {}
    duplicate_identities = []
    for manifest in sorted((root / "snapshots").glob("*/manifest.json")):
        payload = read_json(manifest)
        snapshot_date = str(payload.get("snapshot_date") or manifest.parent.name)
        content_hash = str(payload.get("content_hash") or "")
        if snapshot_date in seen and seen[snapshot_date] != content_hash:
            duplicate_identities.append(snapshot_date)
        seen[snapshot_date] = content_hash
        manifests.append(
            {
                "snapshot_date": snapshot_date,
                "manifest_path": str(manifest),
                "storage_path": str(payload.get("storage_path") or snapshot_data_path(root, snapshot_date)),
                "content_hash": content_hash,
                "schema_hash": str(payload.get("schema_hash") or ""),
                "row_count": int(payload.get("row_count") or 0),
                "validation_status": str(payload.get("validation_status") or ""),
            }
        )
    status = "PASS" if manifests and not duplicate_identities else "HALT"
    payload = {
        "schema_version": SNAPSHOT_STORE_SCHEMA_VERSION,
        "status": status,
        "reason": "snapshot_index_ready" if status == "PASS" else "snapshot_index_invalid",
        "selection_policy": SELECTION_POLICY,
        "snapshot_count": len(manifests),
        "oldest_snapshot_date": manifests[0]["snapshot_date"] if manifests else "",
        "latest_snapshot_date": manifests[-1]["snapshot_date"] if manifests else "",
        "duplicate_snapshot_identities": duplicate_identities,
        "snapshots": manifests,
    }
    root.mkdir(parents=True, exist_ok=True)
    index_path(root).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    latest_path(root).write_text(json.dumps(manifests[-1] if manifests else {}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def resolve_listed_issues_snapshot(
    *,
    snapshot_root: Path | str,
    business_date: str,
    mode: str = "historical",
    max_snapshot_age_days: int = DEFAULT_MAX_SNAPSHOT_AGE_DAYS,
) -> ListedIssuesSnapshotResolution:
    root = Path(snapshot_root)
    if mode != "historical":
        return _resolution_halt(root, business_date, mode, "historical_snapshot_resolver_not_available_for_mode")
    path = index_path(root)
    if not path.is_file():
        return _resolution_halt(root, business_date, mode, "snapshot_index_missing")
    try:
        index = read_json(path)
    except Exception:
        return _resolution_halt(root, business_date, mode, "snapshot_index_unreadable")
    if index.get("status") != "PASS":
        return _resolution_halt(root, business_date, mode, "snapshot_index_invalid")
    snapshots = list(index.get("snapshots") or [])
    if not snapshots:
        return _resolution_halt(root, business_date, mode, "snapshot_store_empty")
    duplicates = index.get("duplicate_snapshot_identities") or []
    if duplicates:
        return _resolution_halt(root, business_date, mode, "duplicate_snapshot_identity")
    eligible = [item for item in snapshots if str(item.get("snapshot_date") or "") <= business_date]
    if not eligible:
        return _resolution_halt(root, business_date, mode, "no_snapshot_not_after_business_date")
    selected = max(eligible, key=lambda item: str(item.get("snapshot_date") or ""))
    snapshot_date = str(selected.get("snapshot_date") or "")
    age = (date.fromisoformat(business_date) - date.fromisoformat(snapshot_date)).days
    if snapshot_date > business_date:
        return _resolution_halt(root, business_date, mode, "future_snapshot_selected")
    if age > max_snapshot_age_days:
        return _resolution_halt(root, business_date, mode, "snapshot_age_exceeds_limit")
    data_path = Path(str(selected.get("storage_path") or ""))
    manifest_path = Path(str(selected.get("manifest_path") or ""))
    if not data_path.is_file() or not manifest_path.is_file():
        return _resolution_halt(root, business_date, mode, "snapshot_artifact_missing")
    expected_hash = str(selected.get("content_hash") or "")
    actual_hash = file_hash(data_path)
    if not expected_hash or actual_hash != expected_hash:
        return _resolution_halt(root, business_date, mode, "snapshot_content_hash_mismatch")
    manifest = read_json(manifest_path)
    if str(manifest.get("snapshot_date") or "") != snapshot_date:
        return _resolution_halt(root, business_date, mode, "snapshot_manifest_date_mismatch")
    if bool(manifest.get("future_snapshot_used")):
        return _resolution_halt(root, business_date, mode, "snapshot_manifest_future_leakage")
    return ListedIssuesSnapshotResolution(
        status="PASS",
        reason="historical_listed_issues_snapshot_resolved",
        mode=mode,
        business_date=business_date,
        snapshot_root=str(root),
        selected_snapshot_date=snapshot_date,
        selected_snapshot_path=str(data_path),
        selected_manifest_path=str(manifest_path),
        selected_content_hash=actual_hash,
        selected_schema_hash=str(selected.get("schema_hash") or ""),
        snapshot_age_days=age,
        future_snapshot_used=False,
        content_hash_verified=True,
    )


def acquire_snapshots(
    *,
    client: Any,
    snapshot_root: Path | str,
    target_dates: list[str],
    storage_format: str = "parquet",
    max_pages: int = 100,
    sleep_seconds: float = 1.0,
    retry_count: int = 3,
    skip_verified_existing: bool = True,
    progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    root = Path(snapshot_root)
    root.mkdir(parents=True, exist_ok=True)
    results = []
    for target_date in target_dates:
        manifest = snapshot_manifest_path(root, target_date)
        if skip_verified_existing and manifest.is_file():
            existing = read_json(manifest)
            data_path = Path(str(existing.get("storage_path") or snapshot_data_path(root, target_date, storage_format)))
            if data_path.is_file() and file_hash(data_path) == str(existing.get("content_hash") or ""):
                result = {
                    "status": "SKIPPED",
                    "classification": "VERIFIED_EXISTING",
                    "requested_date": target_date,
                    "snapshot_date": str(existing.get("snapshot_date") or target_date),
                    "reason": "skip_verified_existing",
                }
                results.append(result)
                if progress:
                    progress(result)
                continue
        result_payload = _fetch_with_retry(
            client=client,
            target_date=target_date,
            snapshot_root=root,
            storage_format=storage_format,
            max_pages=max_pages,
            retry_count=retry_count,
        )
        results.append(result_payload)
        if progress:
            progress(result_payload)
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
    index = rebuild_snapshot_index(root)
    payload = {
        "schema_version": SNAPSHOT_STORE_SCHEMA_VERSION,
        "status": "PASS" if all(item.get("status") in {"PASS", "SKIPPED"} for item in results) and index.get("status") == "PASS" else "PARTIAL",
        "target_count": len(target_dates),
        "success_count": sum(1 for item in results if item.get("status") == "PASS"),
        "skipped_count": sum(1 for item in results if item.get("status") == "SKIPPED"),
        "failed_count": sum(1 for item in results if item.get("status") not in {"PASS", "SKIPPED"}),
        "results": results,
        "index": index,
    }
    acquisition_manifest_path(root).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _fetch_with_retry(
    *,
    client: Any,
    target_date: str,
    snapshot_root: Path,
    storage_format: str,
    max_pages: int,
    retry_count: int,
) -> dict[str, Any]:
    last_error: dict[str, Any] | None = None
    for attempt in range(1, retry_count + 1):
        try:
            records = client.fetch_all_listed_issues(date=target_date, max_pages=max_pages)
            result = write_listed_issues_snapshot(
                snapshot_root=snapshot_root,
                requested_date=target_date,
                records=records,
                storage_format=storage_format,
                fetched_at=now_utc(),
                pagination_metadata={"max_pages": max_pages, "attempt": attempt},
            )
            return result.to_payload()
        except JQuantsClientError as exc:
            diagnostic = dict(exc.diagnostic)
            last_error = {
                "status": "FAILED",
                "classification": classify_error(diagnostic),
                "requested_date": target_date,
                "snapshot_date": "",
                "reason": str(exc),
                "diagnostic": sanitize_diagnostic(diagnostic),
                "attempt": attempt,
            }
            if classify_error(diagnostic) not in {"API_RATE_LIMIT", "API_ERROR"}:
                return last_error
            time.sleep(min(2**attempt, 30))
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "FAILED",
                "classification": "RUNTIME_ERROR",
                "requested_date": target_date,
                "snapshot_date": "",
                "reason": f"{exc.__class__.__name__}: {exc}",
            }
    return last_error or {
        "status": "FAILED",
        "classification": "UNKNOWN",
        "requested_date": target_date,
        "snapshot_date": "",
        "reason": "retry_exhausted",
    }


def classify_fetch_result(*, requested_date: str, response_dates: list[str], row_count: int) -> str:
    if row_count == 0:
        return "NO_DATA_FOR_DATE"
    if response_dates == [requested_date]:
        return "FETCH_SUPPORTED_EXACT_DATE"
    if response_dates:
        return "FETCH_SUPPORTED_WITH_PROVIDER_DATE_NORMALIZATION"
    return "AMBIGUOUS"


def classify_error(diagnostic: dict[str, Any]) -> str:
    status = diagnostic.get("http_status")
    error_class = str(diagnostic.get("error_class") or "")
    if status in (401, 403) or error_class == "API_AUTH_ERROR":
        return "AUTHORIZATION_OR_PLAN_LIMIT"
    if status == 400:
        return "DATE_OUT_OF_RETENTION"
    if status == 429 or error_class == "API_RATE_LIMIT":
        return "API_RATE_LIMIT"
    if error_class:
        return "API_ERROR"
    return "AMBIGUOUS"


def schema_fingerprint(records: list[dict[str, Any]]) -> dict[str, Any]:
    columns = sorted({key for record in records for key in record})
    types: dict[str, list[str]] = {}
    for column in columns:
        values = {type(record.get(column)).__name__ for record in records if record.get(column) is not None}
        types[column] = sorted(values) if values else ["null"]
    payload = {"columns": columns, "types": types}
    return {
        "columns": columns,
        "types": types,
        "schema_hash": hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest(),
    }


def duplicate_date_code_count(records: list[dict[str, Any]]) -> int:
    counts: dict[tuple[str, str], int] = {}
    for record in records:
        key = (str(record.get("Date") or ""), str(record.get("Code") or ""))
        counts[key] = counts.get(key, 0) + 1
    return sum(count - 1 for count in counts.values() if count > 1)


def diff_summary(previous_manifest: dict[str, Any] | None, row_count: int, content_hash: str) -> dict[str, Any]:
    if not previous_manifest:
        return {"previous_snapshot_present": False, "row_count_delta": None, "content_hash_changed": None}
    previous_count = int(previous_manifest.get("row_count") or 0)
    previous_hash = str(previous_manifest.get("content_hash") or "")
    return {
        "previous_snapshot_present": True,
        "previous_snapshot_date": previous_manifest.get("snapshot_date") or "",
        "row_count_delta": row_count - previous_count,
        "content_hash_changed": bool(previous_hash and previous_hash != content_hash),
    }


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sanitize_diagnostic(diagnostic: dict[str, Any]) -> dict[str, Any]:
    blocked = {"api_key", "token", "authorization", "x-api-key", "password", "id_token", "refresh_token", "secret"}
    return {key: value for key, value in diagnostic.items() if key.lower() not in blocked}


def now_utc() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _resolution_halt(root: Path, business_date: str, mode: str, reason: str) -> ListedIssuesSnapshotResolution:
    return ListedIssuesSnapshotResolution(
        status="HALT",
        reason=reason,
        mode=mode,
        business_date=business_date,
        snapshot_root=str(root),
        selected_snapshot_date="",
        selected_snapshot_path="",
        selected_manifest_path="",
        selected_content_hash="",
        selected_schema_hash="",
        snapshot_age_days=None,
    )
