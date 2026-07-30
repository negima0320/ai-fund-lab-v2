#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_fund_lab_v2.config import load_settings
from ai_fund_lab_v2.data_sources.jquants.raw_ingestion import ENDPOINT_PATHS, RAW_COLLECTIONS
from ai_fund_lab_v2.data_store import create_storage_backend, manifest_path, validate_records

ENDPOINT_CHOICES = ("fins_summary",)
REPAIRED_PREFIX = "fins_summary:"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.endpoint != "fins_summary":
        raise ValueError("Only fins_summary business-key repair is supported.")
    if not args.dry_run and not args.confirm:
        print("ERROR live cleanup requires --confirm. Re-run with --dry-run first.", file=sys.stderr)
        return 2

    settings = load_settings()
    paths = settings.runtime_paths
    if args.runtime_dir:
        paths = replace(paths, runtime_dir=args.runtime_dir)
    backend = create_storage_backend("parquet")
    data_path = backend.path_for(paths.raw_data / RAW_COLLECTIONS[args.endpoint] / "data")
    manifest = manifest_path(paths.raw_data)

    records = backend.read_records(data_path)
    inventory = build_inventory(records, from_date=args.from_date, to_date=args.to_date)
    kept_records = [record for record, item in zip(records, inventory["row_classifications"]) if not item["delete_candidate"]]
    post_summary = summarize_records(kept_records, from_date=args.from_date, to_date=args.to_date)
    result = {
        "endpoint_name": args.endpoint,
        "endpoint": ENDPOINT_PATHS[args.endpoint],
        "from_date": args.from_date,
        "to_date": args.to_date,
        "data_path": str(data_path),
        "manifest_path": str(manifest),
        "dry_run": bool(args.dry_run),
        "pre_hash": sha256_file(data_path) if data_path.is_file() else "",
        "pre_summary": inventory["summary"],
        "post_summary": post_summary,
        "legacy_rows_removed": inventory["summary"]["target_range_legacy_rows"],
        "unknown_rows_removed": 0,
        "manifest_mutation": "none",
        "status": "DRY_RUN" if args.dry_run else "PLANNED",
    }

    if args.dry_run:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if result["legacy_rows_removed"] == 0:
        result.update({"status": "NO_CHANGE", "post_hash": result["pre_hash"]})
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = args.backup_dir or (paths.runtime_dir / "backups" / "phase23_x_fins_summary_legacy_key_cleanup")
    backup_dir = backup_root / timestamp
    backup_dir.mkdir(parents=True, exist_ok=False)
    backup_files(data_path=data_path, manifest_path=manifest, backup_dir=backup_dir, pre_summary=inventory["summary"])

    temp_path = data_path.with_name(f".{data_path.name}.phase23_x_tmp")
    try:
        backend.write_records(temp_path, kept_records)
        written = backend.read_records(temp_path)
        if len(written) != len(kept_records):
            raise RuntimeError(f"repair write count mismatch: expected={len(kept_records)} actual={len(written)}")
        validation = validate_records(args.endpoint, written)
        post_quality = summarize_records(written, from_date=args.from_date, to_date=args.to_date)
        if validation.status != "OK":
            raise RuntimeError(f"post-cleanup validation failed: {validation.status} {validation.messages}")
        Path(temp_path).replace(data_path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise

    result.update(
        {
            "dry_run": False,
            "status": "REPAIRED",
            "backup_dir": str(backup_dir),
            "post_hash": sha256_file(data_path),
            "post_validation": validation.to_dict(),
            "post_summary": post_quality,
        }
    )
    evidence_path = backup_dir / "repair_result.json"
    evidence_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def build_inventory(records: list[dict[str, Any]], *, from_date: str, to_date: str) -> dict[str, Any]:
    classifications: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        key_format = classify_key(record)
        in_range = is_target_range(record, from_date=from_date, to_date=to_date)
        is_fins = str(record.get("endpoint") or "") == ENDPOINT_PATHS["fins_summary"]
        delete_candidate = bool(is_fins and in_range and key_format == "LEGACY_CODE_ONLY")
        classifications.append(
            {
                "index": index,
                "target_date": record_date(record),
                "code": str(record.get("Code") or record.get("code") or ""),
                "business_key": str(record.get("business_key") or ""),
                "key_format": key_format,
                "in_target_range": in_range,
                "endpoint_match": is_fins,
                "delete_candidate": delete_candidate,
            }
        )
    return {"summary": summarize_classifications(classifications), "row_classifications": classifications}


def summarize_records(records: list[dict[str, Any]], *, from_date: str, to_date: str) -> dict[str, Any]:
    return summarize_classifications(
        [
            {
                "key_format": classify_key(record),
                "in_target_range": is_target_range(record, from_date=from_date, to_date=to_date),
                "delete_candidate": False,
                "endpoint_match": str(record.get("endpoint") or "") == ENDPOINT_PATHS["fins_summary"],
            }
            for record in records
        ],
        total_rows=len(records),
    )


def summarize_classifications(classifications: list[dict[str, Any]], total_rows: int | None = None) -> dict[str, Any]:
    summary = {
        "total_rows": len(classifications) if total_rows is None else total_rows,
        "legacy_rows_total": 0,
        "repaired_rows_total": 0,
        "unknown_rows_total": 0,
        "target_range_legacy_rows": 0,
        "target_range_repaired_rows": 0,
        "target_range_unknown_rows": 0,
        "outside_range_legacy_rows": 0,
        "outside_range_repaired_rows": 0,
        "outside_range_unknown_rows": 0,
        "delete_candidate_rows": 0,
        "kept_rows": 0,
    }
    for item in classifications:
        key_format = item["key_format"]
        in_range = bool(item["in_target_range"])
        if key_format == "LEGACY_CODE_ONLY":
            summary["legacy_rows_total"] += 1
            summary["target_range_legacy_rows" if in_range else "outside_range_legacy_rows"] += 1
        elif key_format == "REPAIRED_DISCLOSURE_IDENTITY":
            summary["repaired_rows_total"] += 1
            summary["target_range_repaired_rows" if in_range else "outside_range_repaired_rows"] += 1
        else:
            summary["unknown_rows_total"] += 1
            summary["target_range_unknown_rows" if in_range else "outside_range_unknown_rows"] += 1
        if item.get("delete_candidate"):
            summary["delete_candidate_rows"] += 1
        else:
            summary["kept_rows"] += 1
    return summary


def classify_key(record: dict[str, Any]) -> str:
    business_key = str(record.get("business_key") or "")
    code = str(record.get("Code") or record.get("code") or record.get("LocalCode") or "")
    if business_key.startswith(REPAIRED_PREFIX):
        return "REPAIRED_DISCLOSURE_IDENTITY"
    if business_key and code and business_key == code:
        return "LEGACY_CODE_ONLY"
    return "UNKNOWN_KEY_FORMAT"


def is_target_range(record: dict[str, Any], *, from_date: str, to_date: str) -> bool:
    value = record_date(record)
    return bool(value and from_date <= value <= to_date)


def record_date(record: dict[str, Any]) -> str:
    return str(record.get("DiscDate") or record.get("target_date") or "")[:10]


def backup_files(*, data_path: Path, manifest_path: Path, backup_dir: Path, pre_summary: dict[str, Any]) -> None:
    shutil.copy2(data_path, backup_dir / "data.parquet")
    if manifest_path.is_file():
        shutil.copy2(manifest_path, backup_dir / "manifest.jsonl")
    (backup_dir / "pre_cleanup_summary.json").write_text(
        json.dumps(pre_summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    hashes = {"data.parquet": sha256_file(data_path), "manifest.jsonl": sha256_file(manifest_path) if manifest_path.is_file() else ""}
    (backup_dir / "pre_cleanup_hashes.json").write_text(
        json.dumps(hashes, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Repair J-Quants raw business-key migrations.")
    parser.add_argument("--endpoint", choices=ENDPOINT_CHOICES, required=True)
    parser.add_argument("--from-date", required=True)
    parser.add_argument("--to-date", required=True)
    parser.add_argument("--runtime-dir", type=Path)
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
