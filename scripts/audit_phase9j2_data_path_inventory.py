#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.canonical_data_source import (  # noqa: E402
    CANONICAL_KEYS,
    DEFAULT_CONFIG_PATH,
    resolve_phase9_data_sources,
)


DEFAULT_SCAN_DIRS = ("data", ".runtime", "reports", "models", "artifacts", "cache", "src")
EXTENSIONS = {".parquet", ".csv", ".json", ".jsonl", ".pkl", ".joblib"}
JSON_SIZE_LIMIT = 5_000_000


@dataclass(frozen=True)
class InventoryItem:
    path: str
    artifact_type: str
    inferred_source: str
    row_count: int = 0
    min_date: str = ""
    max_date: str = ""
    code_count: int = 0
    columns: tuple[str, ...] = ()
    file_size: int = 0
    modified_at: str = ""
    source_manifest_ref: str = ""
    likely_jquants_derived: bool = False
    phase: str = ""
    freshness_score: float = 0.0
    usable_for_phase9: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["columns"] = list(self.columns)
        return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase9-J2 data path inventory.")
    parser.add_argument("--config-path", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--markdown-report-path", default="docs/phase_reports/phase9j2_data_path_inventory_and_canonical_source.md")
    parser.add_argument("--json-report-path", default="reports/phase_reports/phase9j2_data_path_inventory_and_canonical_source.json")
    args = parser.parse_args()
    report = build_inventory_report(config_path=Path(args.config_path))
    _write_outputs(report, markdown_path=Path(args.markdown_report_path), json_path=Path(args.json_report_path))
    print(json.dumps({"judgment": report["judgment"], "json_report": args.json_report_path}, ensure_ascii=False, sort_keys=True))
    return 0


def build_inventory_report(*, config_path: Path = DEFAULT_CONFIG_PATH, root: Path = ROOT) -> dict[str, Any]:
    items = discover_inventory(root=root)
    canonical = resolve_phase9_data_sources(config_path=config_path, allow_fallback=False)
    fallback_candidates = resolve_phase9_data_sources(config_path=config_path, allow_fallback=True)
    current_phase9_path = ".runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet"
    long_raw = _best_item(items, artifact_type="raw_daily_quotes_response_dir")
    short_normalized = _find_path(items, current_phase9_path)
    long_normalized = _best_long_normalized(items)
    cause = _lookback_cause(short_normalized=short_normalized, long_raw=long_raw, long_normalized=long_normalized)
    adopted = {key: ref.to_dict() for key, ref in canonical.items()}
    inventory_limit = 500
    report = {
        "phase": "Phase9-J2",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "judgment": "CANONICAL_NORMALIZED_MISSING" if not adopted["normalized_daily_quotes"]["usable_for_phase9"] else "CANONICAL_READY",
        "phase9_previous_normalized_path": current_phase9_path,
        "inventory_count": len(items),
        "inventory_truncated": len(items) > inventory_limit,
        "inventory_limit": inventory_limit,
        "inventory": [item.to_dict() for item in items[:inventory_limit]],
        "raw_daily_quotes_candidates": [item.to_dict() for item in items if item.artifact_type.startswith("raw_daily_quotes")][:200],
        "normalized_daily_quotes_candidates": [item.to_dict() for item in items if item.artifact_type == "normalized_daily_quotes"][:40],
        "listed_info_candidates": [item.to_dict() for item in items if item.artifact_type == "listed_info"][:40],
        "trading_calendar_candidates": [item.to_dict() for item in items if item.artifact_type == "trading_calendar"][:40],
        "feature_candidates": [item.to_dict() for item in items if "feature" in item.artifact_type or "policy_input" in item.artifact_type][:200],
        "model_candidates": [item.to_dict() for item in items if item.artifact_type in {"model_artifact", "model_manifest", "training_manifest"}][:100],
        "canonical_config_path": str(config_path),
        "canonical_sources": adopted,
        "fallback_resolution_candidates": {key: ref.to_dict() for key, ref in fallback_candidates.items()},
        "adopted_canonical_paths": {
            "raw_daily_quotes": adopted["raw_daily_quotes"]["path"],
            "normalized_daily_quotes": adopted["normalized_daily_quotes"]["path"],
            "listed_info": adopted["listed_info"]["path"],
            "trading_calendar": adopted["trading_calendar"]["path"],
        },
        "lookback_shortfall_cause": cause,
        "config_update_summary": {
            "raw_daily_quotes": "long raw response directory selected",
            "normalized_daily_quotes": "null until long normalized rebuild is completed",
            "listed_info": "current J-Quants listed issues parquet",
            "trading_calendar": "current J-Quants trading calendar parquet",
        },
        "prohibited_actions": {
            "broker_order_api_called": False,
            "open_d_started": False,
            "unlock_trade_called": False,
            "paper_ledger_fill_executed": False,
            "virtual_fill_executed": False,
            "model_retraining_executed": False,
            "inference_executed": False,
            "order_plan_generation_executed": False,
            "full_backtest_executed": False,
        },
    }
    return report


def discover_inventory(*, root: Path = ROOT, scan_dirs: tuple[str, ...] = DEFAULT_SCAN_DIRS) -> list[InventoryItem]:
    items: list[InventoryItem] = []
    response_dir = root / ".runtime/data/raw/jquants/equities_bars_daily/responses"
    if response_dir.is_dir():
        items.append(_inspect_response_dir(response_dir, root=root))
    for directory_name in scan_dirs:
        directory = root / directory_name
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
                continue
            if _skip_file(path):
                continue
            item = inspect_artifact(path, root=root)
            if item is not None:
                items.append(item)
    return sorted(items, key=lambda item: (-item.freshness_score, item.path))


def inspect_artifact(path: Path, *, root: Path = ROOT) -> InventoryItem | None:
    artifact_type = _artifact_type(path)
    if artifact_type == "unknown":
        return None
    stat = path.stat()
    columns: tuple[str, ...] = ()
    row_count = 0
    min_date = ""
    max_date = ""
    code_count = 0
    if path.suffix.lower() in {".parquet", ".csv", ".json", ".jsonl"}:
        try:
            frame = _read_frame(path)
            row_count = int(len(frame))
            columns = tuple(str(column) for column in frame.columns[:80])
            min_date, max_date = _date_range(frame)
            code_count = _code_count(frame)
        except Exception:
            pass
    likely = _likely_jquants(path, columns)
    usable, reason = _usable_for_phase9(path=path, artifact_type=artifact_type, likely_jquants=likely)
    rel = _rel(path, root)
    return InventoryItem(
        path=rel,
        artifact_type=artifact_type,
        inferred_source="jquants" if likely else _infer_source(path),
        row_count=row_count,
        min_date=min_date,
        max_date=max_date,
        code_count=code_count,
        columns=columns,
        file_size=stat.st_size,
        modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat(),
        source_manifest_ref=_manifest_ref(path, root=root),
        likely_jquants_derived=likely,
        phase=_phase(path),
        freshness_score=_freshness_score(row_count=row_count, max_date=max_date, code_count=code_count),
        usable_for_phase9=usable,
        reason=reason,
    )


def _inspect_response_dir(path: Path, *, root: Path) -> InventoryItem:
    files = sorted(path.glob("*.json"))
    dates = sorted({file.name[:10] for file in files if len(file.name) >= 10 and file.name[:4].isdigit()})
    latest = dates[-1] if dates else ""
    earliest = dates[0] if dates else ""
    return InventoryItem(
        path=_rel(path, root),
        artifact_type="raw_daily_quotes_response_dir",
        inferred_source="jquants",
        row_count=len(files),
        min_date=earliest,
        max_date=latest,
        code_count=0,
        columns=(),
        file_size=sum(file.stat().st_size for file in files[:200]),
        modified_at=datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat(),
        likely_jquants_derived=True,
        phase="Phase1/Phase4",
        freshness_score=_freshness_score(row_count=len(files), max_date=latest, code_count=0),
        usable_for_phase9=True,
        reason="long_raw_responses_available_requires_normalization",
    )


def _read_frame(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path, nrows=200_000)
    if suffix == ".jsonl":
        if path.stat().st_size > JSON_SIZE_LIMIT:
            rows = []
            with path.open("r", encoding="utf-8") as handle:
                for index, line in enumerate(handle):
                    if index >= 10_000:
                        break
                    if line.strip():
                        rows.append(json.loads(line))
            return pd.DataFrame(rows)
        return pd.read_json(path, lines=True)
    if suffix == ".json":
        if path.stat().st_size > JSON_SIZE_LIMIT:
            return pd.DataFrame()
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return pd.DataFrame(payload)
        if isinstance(payload, dict):
            for key in ("rows", "items", "data", "candidates", "decisions"):
                if isinstance(payload.get(key), list):
                    return pd.DataFrame(payload[key])
            return pd.DataFrame([payload])
    return pd.DataFrame()


def _artifact_type(path: Path) -> str:
    text = str(path).lower()
    name = path.name.lower()
    if "equities_bars_daily" in text and "raw_normalized" in text:
        return "normalized_daily_quotes"
    if "equities_bars_daily" in text and "raw/jquants" in text:
        return "raw_daily_quotes"
    if "listed_issues" in text or "equities/master" in text:
        return "listed_info"
    if "trading_calendar" in text or "markets/calendar" in text:
        return "trading_calendar"
    if "candidate" in text and "feature" in text:
        return "candidate_features"
    if "opportunity" in text and ("feature" in text or "dataset" in text):
        return "opportunity_features"
    if "position" in text and "feature" in text:
        return "position_features"
    if "capital" in text and ("policy" in text or "allocation" in text or "input" in text):
        return "capital_policy_inputs"
    if path.suffix.lower() in {".pkl", ".joblib"} or "model" in name:
        return "model_artifact"
    if "training" in text and "json" in name:
        return "training_manifest"
    if "manifest" in name:
        return "model_manifest"
    return "unknown"


def _date_range(frame: pd.DataFrame) -> tuple[str, str]:
    for column in ("target_date", "Date", "date", "as_of_date", "data_until", "run_date"):
        if column in frame.columns:
            values = frame[column].dropna().astype(str)
            values = values[values.str.match(r"^\d{4}-\d{2}-\d{2}$")]
            if not values.empty:
                return str(values.min()), str(values.max())
    return "", ""


def _code_count(frame: pd.DataFrame) -> int:
    for column in ("code", "Code", "LocalCode", "issue_code"):
        if column in frame.columns:
            return int(frame[column].dropna().astype(str).nunique())
    return 0


def _likely_jquants(path: Path, columns: tuple[str, ...]) -> bool:
    text = str(path).lower()
    if "jquants" in text:
        return True
    cols = {column.lower() for column in columns}
    return bool({"source", "endpoint"} & cols and any("jquants" in column for column in cols))


def _usable_for_phase9(*, path: Path, artifact_type: str, likely_jquants: bool) -> tuple[bool, str]:
    text = str(path).lower()
    prohibited = ("paper_ledger", "broker", "backtest", "trade_ledger", "equity_curve", "public", "blog")
    if any(term in text for term in prohibited):
        return False, "prohibited_source"
    if artifact_type in {"raw_daily_quotes", "raw_daily_quotes_response_dir", "normalized_daily_quotes", "listed_info", "trading_calendar"}:
        return likely_jquants, "jquants_derived" if likely_jquants else "not_jquants_derived"
    if text.startswith("reports/"):
        return False, "reports_are_not_phase9_feature_sources"
    return likely_jquants or ".runtime/phase9/features" in text, "phase9_generated_or_jquants_derived"


def _skip_file(path: Path) -> bool:
    text = str(path)
    if "/.git/" in text or "__pycache__" in text:
        return True
    if path.name.startswith("."):
        return True
    return False


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _infer_source(path: Path) -> str:
    text = str(path).lower()
    if "report" in text:
        return "report"
    if "model" in text:
        return "model"
    return "unknown"


def _phase(path: Path) -> str:
    text = str(path).lower()
    for phase in ("phase9", "phase8", "phase7", "phase6", "phase5", "phase4", "phase1"):
        if phase in text:
            return phase.title().replace("Phase", "Phase")
    return ""


def _freshness_score(*, row_count: int, max_date: str, code_count: int) -> float:
    date_score = int(max_date.replace("-", "") or 0) if max_date else 0
    return float(date_score) + min(row_count, 1_000_000) / 1_000_000 + min(code_count, 10_000) / 10_000


def _manifest_ref(path: Path, *, root: Path) -> str:
    candidates = (path.parent / "manifest.json", path.parent / "manifest.jsonl", path.parent.parent / "manifest.json")
    for candidate in candidates:
        if candidate.exists():
            return _rel(candidate, root)
    return ""


def _best_item(items: list[InventoryItem], *, artifact_type: str) -> InventoryItem | None:
    matches = [item for item in items if item.artifact_type == artifact_type]
    return max(matches, key=lambda item: item.freshness_score, default=None)


def _find_path(items: list[InventoryItem], path: str) -> InventoryItem | None:
    return next((item for item in items if item.path == path), None)


def _best_long_normalized(items: list[InventoryItem]) -> InventoryItem | None:
    matches = [item for item in items if item.artifact_type == "normalized_daily_quotes" and item.min_date and item.max_date]
    long_matches = [item for item in matches if item.min_date < "2026-05-15" and item.max_date >= "2026-06-15"]
    return max(long_matches, key=lambda item: item.freshness_score, default=None)


def _lookback_cause(*, short_normalized: InventoryItem | None, long_raw: InventoryItem | None, long_normalized: InventoryItem | None) -> str:
    if long_normalized:
        return "REFERENCE_PATH_MISMATCH_LONG_NORMALIZED_EXISTS"
    if long_raw and short_normalized:
        return "REFERENCE_PATH_MISMATCH_LONG_RAW_EXISTS_BUT_CANONICAL_NORMALIZED_MISSING"
    if short_normalized:
        return "NORMALIZED_HISTORY_TOO_SHORT"
    return "DATA_SOURCE_NOT_FOUND"


def _write_outputs(report: dict[str, Any], *, markdown_path: Path, json_path: Path) -> None:
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(_render_markdown(report), encoding="utf-8")


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Phase9-J2 Data Path Inventory and Canonical Source",
        "",
        f"- judgment: {report['judgment']}",
        f"- phase9_previous_normalized_path: `{report['phase9_previous_normalized_path']}`",
        f"- lookback_shortfall_cause: {report['lookback_shortfall_cause']}",
        f"- canonical_config_path: `{report['canonical_config_path']}`",
        "",
        "## Adopted Canonical Paths",
        "",
    ]
    for key, value in report["adopted_canonical_paths"].items():
        lines.append(f"- {key}: `{value or 'null'}`")
    lines.extend(["", "## Key Candidates", "", "### Raw Daily Quotes", ""])
    lines.extend(_table(report["raw_daily_quotes_candidates"][:12]))
    lines.extend(["", "### Normalized Daily Quotes", ""])
    lines.extend(_table(report["normalized_daily_quotes_candidates"][:12]))
    lines.extend(["", "### Listed Info", ""])
    lines.extend(_table(report["listed_info_candidates"][:8]))
    lines.extend(["", "### Trading Calendar", ""])
    lines.extend(_table(report["trading_calendar_candidates"][:8]))
    lines.extend(["", "## Canonical Sources", ""])
    for key in CANONICAL_KEYS:
        ref = report["canonical_sources"][key]
        lines.append(f"- {key}: source={ref['source']} usable={ref['usable_for_phase9']} path=`{ref['path'] or 'null'}`")
    lines.extend(["", "## Prohibited Actions", ""])
    for key, value in report["prohibited_actions"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    return "\n".join(lines)


def _table(items: list[dict[str, Any]]) -> list[str]:
    if not items:
        return ["- none"]
    lines = [
        "| path | type | rows | min_date | max_date | codes | usable | reason |",
        "| --- | --- | ---: | --- | --- | ---: | --- | --- |",
    ]
    for item in items:
        lines.append(
            f"| `{item['path']}` | {item['artifact_type']} | {item['row_count']} | {item['min_date']} | "
            f"{item['max_date']} | {item['code_count']} | {item['usable_for_phase9']} | {item['reason']} |"
        )
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
