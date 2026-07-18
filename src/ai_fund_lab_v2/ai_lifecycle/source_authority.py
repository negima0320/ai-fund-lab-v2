from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


REQUIRED_SOURCE_AUTHORITIES = (
    "canonical_normalized_quotes",
    "trading_calendar",
    "listed_issues",
    "candidate_source",
    "opportunity_source",
    "candidate_lineage",
)


@dataclass(frozen=True)
class SourceAuthorityEvidence:
    logical_name: str
    source_ref: str
    content_hash: str
    schema_hash: str
    row_count: int | None
    min_target_date: str | None
    max_target_date: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SourceAuthorityBundle:
    authorities: dict[str, SourceAuthorityEvidence]

    def to_dict(self) -> dict[str, Any]:
        return {name: evidence.to_dict() for name, evidence in sorted(self.authorities.items())}


def resolve_source_authority(
    *,
    source_paths: Mapping[str, Path | str] | None = None,
    source_frames: Mapping[str, pd.DataFrame] | None = None,
    root: Path | str | None = None,
) -> SourceAuthorityBundle:
    paths = {key: Path(value) for key, value in (source_paths or {}).items()}
    frames = dict(source_frames or {})
    names = sorted(set(paths) | set(frames))
    missing = sorted(name for name in REQUIRED_SOURCE_AUTHORITIES if name not in names)
    if missing:
        raise ValueError(f"missing source authority evidence: {', '.join(missing)}")

    authorities: dict[str, SourceAuthorityEvidence] = {}
    for name in names:
        frame = frames.get(name)
        path = paths.get(name)
        if frame is None and path is not None and path.is_file():
            frame = _read_frame(path)
        source_ref = _source_ref(name, path=path, root=Path(root) if root else None)
        content_hash = _file_hash(path) if path is not None else _frame_content_hash(frame)
        schema_hash = _schema_hash(frame) if frame is not None else _file_schema_hash(path)
        row_count, min_date, max_date = _date_stats(frame)
        authorities[name] = SourceAuthorityEvidence(
            logical_name=name,
            source_ref=source_ref,
            content_hash=content_hash,
            schema_hash=schema_hash,
            row_count=row_count,
            min_target_date=min_date,
            max_target_date=max_date,
        )
    return SourceAuthorityBundle(authorities=authorities)


def stable_identity_ref(*, component: str, dataset_hash: str, dataset_version: str) -> str:
    prefix = dataset_hash[:16] if dataset_hash else "unknown"
    return f"{component}:{dataset_version}:{prefix}"


def _source_ref(name: str, *, path: Path | None, root: Path | None) -> str:
    if path is None:
        return f"frame:{name}"
    candidate = path
    if root is not None:
        try:
            candidate = path.resolve().relative_to(root.resolve())
        except ValueError:
            candidate = Path(path.name)
    value = str(candidate).replace("\\", "/")
    return f"artifact:{value}"


def _read_frame(path: Path) -> pd.DataFrame:
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    if path.suffix == ".csv":
        return pd.read_csv(path, dtype={"code": str, "Code": str})
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return pd.DataFrame(payload)
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        return pd.DataFrame(payload["rows"])
    return pd.DataFrame([payload])


def _file_hash(path: Path | None) -> str:
    if path is None or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_schema_hash(path: Path | None) -> str:
    if path is None or not path.is_file():
        return ""
    try:
        return _schema_hash(_read_frame(path))
    except Exception:
        return ""


def _frame_content_hash(frame: pd.DataFrame | None) -> str:
    if frame is None:
        return ""
    stable = frame.copy()
    stable.columns = [str(column) for column in stable.columns]
    stable = stable.reindex(sorted(stable.columns), axis=1)
    if {"target_date", "code"}.issubset(stable.columns):
        stable = stable.sort_values(["target_date", "code"]).reset_index(drop=True)
    else:
        stable = stable.sort_values(sorted(stable.columns)).reset_index(drop=True)
    payload = stable.astype(object).where(pd.notna(stable), None).to_json(
        orient="records", date_format="iso", force_ascii=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _schema_hash(frame: pd.DataFrame | None) -> str:
    if frame is None:
        return ""
    payload = [
        {"name": str(column), "dtype": str(dtype)}
        for column, dtype in zip(frame.columns, frame.dtypes)
    ]
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _date_stats(frame: pd.DataFrame | None) -> tuple[int | None, str | None, str | None]:
    if frame is None:
        return None, None, None
    date_column = next((column for column in ("target_date", "Date", "date", "as_of_date") if column in frame.columns), None)
    if date_column is None or frame.empty:
        return int(len(frame)), None, None
    dates = sorted(frame[date_column].dropna().astype(str).unique().tolist())
    return int(len(frame)), (dates[0] if dates else None), (dates[-1] if dates else None)
