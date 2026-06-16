#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.paper_trading.market_data_readiness import READY as MARKET_READY
from ai_fund_lab_v2.paper_trading.market_data_readiness import check_market_data_readiness
from ai_fund_lab_v2.paper_trading.model_eligibility import check_model_eligibility


DECISION_FOR = "2026-06-16"
READY_FOR_PHASE9_DAILY_OPERATION = "READY_FOR_PHASE9_DAILY_OPERATION"
DATA_UPDATE_REQUIRED = "DATA_UPDATE_REQUIRED"
FEATURE_GENERATION_REQUIRED = "FEATURE_GENERATION_REQUIRED"
MODEL_RETRAIN_OR_ELIGIBILITY_REVIEW_REQUIRED = "MODEL_RETRAIN_OR_ELIGIBILITY_REVIEW_REQUIRED"
INITIAL_LEDGER_REQUIRED = "INITIAL_LEDGER_REQUIRED"
NOT_READY = "NOT_READY"

DATE_KEYS = ("date", "Date", "target_date", "as_of_date", "data_until", "decision_for", "run_date", "end_date")
CODE_KEYS = ("code", "Code", "issue_code", "symbol", "LocalCode")
OHLCV_ALIASES = {
    "open": ("open", "Open", "O", "AdjO"),
    "high": ("high", "High", "H", "AdjH"),
    "low": ("low", "Low", "L", "AdjL"),
    "close": ("close", "Close", "C", "AdjC"),
    "volume": ("volume", "Volume", "Vo", "AdjVo"),
}
MODEL_KEYS = (
    "model_version",
    "policy_version",
    "policy_id",
    "active_policy",
    "train_until",
    "data_until",
    "label_horizon",
    "feature_schema_hash",
    "leakage_audit_status",
    "model_artifact_path",
    "artifact_path",
    "training_manifest_path",
    "retrain_mode",
    "last_trained_at",
    "calibrated_at",
)
AI_NAMES = {
    "candidate_ai": ("Candidate AI", (".runtime/candidate_ai", "reports/candidate_ai")),
    "opportunity_ai": ("Opportunity AI", (".runtime/opportunity_ai", "reports/opportunity_ai")),
    "position_management_ai": ("Position Management AI", (".runtime/position_management_ai", "reports/position_management_ai")),
    "capital_allocation_ai": ("Capital Allocation AI / policy", (".runtime/capital_allocation_ai", "reports/capital_allocation_ai")),
}


@dataclass(frozen=True)
class TableSummary:
    path: str
    status: str
    latest_date: str = ""
    row_count: int = 0
    columns: tuple[str, ...] = ()
    missing_columns: tuple[str, ...] = ()
    future_row_count: int = 0
    zero_or_negative_price_count: int = 0
    duplicate_date_code_count: int = 0
    schema_hash: str = ""
    warning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "status": self.status,
            "latest_date": self.latest_date,
            "row_count": self.row_count,
            "columns": list(self.columns),
            "missing_columns": list(self.missing_columns),
            "future_row_count": self.future_row_count,
            "zero_or_negative_price_count": self.zero_or_negative_price_count,
            "duplicate_date_code_count": self.duplicate_date_code_count,
            "schema_hash": self.schema_hash,
            "warning": self.warning,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase9-H preflight data/model freshness audit.")
    parser.add_argument("--decision-for", default=DECISION_FOR)
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--reports-root", default="reports")
    parser.add_argument("--docs-output", default="docs/phase_reports/phase9h_preflight_data_model_freshness_audit.md")
    parser.add_argument("--json-output", default="reports/phase_reports/phase9h_preflight_data_model_freshness_audit.json")
    args = parser.parse_args()

    decision_for = args.decision_for
    audit = build_audit(decision_for=decision_for, runtime_dir=Path(args.runtime_dir), reports_root=Path(args.reports_root))
    docs_path = Path(args.docs_output)
    json_path = Path(args.json_output)
    docs_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    docs_path.write_text(render_markdown(audit), encoding="utf-8")
    print(json.dumps({"phase": "Phase9-H", "status": audit["judgment"], "markdown": str(docs_path), "json": str(json_path)}, ensure_ascii=False, sort_keys=True))
    return 0


def build_audit(*, decision_for: str, runtime_dir: Path, reports_root: Path) -> dict[str, Any]:
    raw_daily_path = first_existing(
        [
            runtime_dir / "data/raw/jquants/equities_bars_daily/data.parquet",
            runtime_dir / "data/raw/jquants/equities_bars_daily/data.jsonl",
            Path("data/raw/jquants/equities_bars_daily/data.parquet"),
            Path("data/raw/jquants/equities_bars_daily/data.jsonl"),
        ]
    )
    normalized_daily_path = first_existing(
        [
            Path("data/normalized/daily_quotes.csv"),
            runtime_dir / "data/raw_normalized/jquants/equities_bars_daily/data.parquet",
            runtime_dir / "data/raw_normalized/jquants/equities_bars_daily/data.jsonl",
            runtime_dir / "data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet",
        ]
    )
    listed_info_path = first_existing(
        [
            Path("data/normalized/listed_info.csv"),
            runtime_dir / "data/raw/jquants/listed_issues/data.parquet",
            runtime_dir / "data/raw/jquants/listed_issues/data.jsonl",
        ]
    )
    trading_calendar_path = first_existing(
        [
            Path("data/normalized/trading_calendar.csv"),
            runtime_dir / "data/raw/jquants/trading_calendar/data.parquet",
            runtime_dir / "data/raw/jquants/trading_calendar/data.jsonl",
        ]
    )

    market = {
        "raw_daily_quote_response_latest_date": latest_response_date(runtime_dir / "data/raw/jquants/equities_bars_daily/responses"),
        "raw_daily_quotes": summarize_table(raw_daily_path, decision_for=decision_for, require_ohlcv=True, check_duplicates=True),
        "normalized_daily_quotes": summarize_table(normalized_daily_path, decision_for=decision_for, require_ohlcv=True, check_duplicates=True),
        "listed_info": summarize_table(listed_info_path, decision_for=decision_for, require_ohlcv=False, check_duplicates=False),
        "trading_calendar": summarize_table(trading_calendar_path, decision_for=decision_for, require_ohlcv=False, check_duplicates=False),
    }
    daily_latest = market["normalized_daily_quotes"]["latest_date"] or market["raw_daily_quotes"]["latest_date"]
    listed_latest = market["listed_info"]["latest_date"]
    data_until_candidates = [item for item in (daily_latest, listed_latest) if item]
    data_until = min(data_until_candidates) if data_until_candidates else ""
    market["data_until_candidate"] = data_until
    market["data_until_meets_decision_for"] = bool(data_until and data_until >= decision_for)
    market_readiness = run_market_readiness_probe(
        decision_for=decision_for,
        runtime_dir=runtime_dir,
        daily_quotes_path=normalized_daily_path,
        listed_info_path=listed_info_path,
    )
    market["market_data_readiness_checker"] = market_readiness

    features = {key: summarize_feature_artifacts(key, display, roots, decision_for) for key, (display, roots) in AI_NAMES.items()}
    models = {key: summarize_model_manifest(key, display, roots, decision_for) for key, (display, roots) in AI_NAMES.items()}
    phase9 = summarize_phase9_readiness(
        decision_for=decision_for,
        runtime_dir=runtime_dir,
        reports_root=reports_root,
        normalized_daily_path=normalized_daily_path,
        listed_info_path=listed_info_path,
    )
    judgment, next_actions = judge_audit(
        decision_for=decision_for,
        market=market,
        features=features,
        models=models,
        phase9=phase9,
    )
    return {
        "phase": "Phase9-H",
        "audit_type": "preflight_data_model_freshness",
        "decision_for": decision_for,
        "judgment": judgment,
        "next_actions": next_actions,
        "market_data": market,
        "feature_artifacts": features,
        "models_and_policies": models,
        "phase9_operation_readiness": phase9,
        "prohibited_actions": {
            "jquants_api_fetch_executed": False,
            "feature_generation_executed": False,
            "model_retraining_executed": False,
            "inference_executed": False,
            "paper_ledger_fill_executed": False,
            "virtual_fill_executed": False,
            "broker_order_api_called": False,
            "open_d_started": False,
            "unlock_trade_called": False,
            "live_order_allowed": False,
            "scheduler_auto_registered": False,
            "full_backtest_executed": False,
        },
    }


def summarize_table(
    path: Path | None,
    *,
    decision_for: str,
    require_ohlcv: bool,
    check_duplicates: bool,
) -> dict[str, Any]:
    if path is None:
        return TableSummary(path="", status="MISSING", warning="path_not_found").to_dict()
    try:
        rows, columns = read_table(path)
    except Exception as exc:  # pragma: no cover - defensive audit path
        return TableSummary(path=str(path), status="UNREADABLE", warning=type(exc).__name__).to_dict()
    latest = latest_date(rows)
    missing = required_missing(columns, require_ohlcv=require_ohlcv)
    future = sum(1 for row in rows if row_date(row) > decision_for)
    nonpositive = count_nonpositive_ohlcv(rows) if require_ohlcv else 0
    duplicates = count_duplicate_date_code(rows) if check_duplicates else 0
    status = "OK"
    if missing:
        status = "INVALID_SCHEMA"
    elif future:
        status = "FUTURE_ROWS_DETECTED"
    elif nonpositive:
        status = "PRICE_ANOMALY_DETECTED"
    return TableSummary(
        path=str(path),
        status=status,
        latest_date=latest,
        row_count=len(rows),
        columns=tuple(columns),
        missing_columns=tuple(missing),
        future_row_count=future,
        zero_or_negative_price_count=nonpositive,
        duplicate_date_code_count=duplicates,
        schema_hash=schema_hash(columns),
    ).to_dict()


def summarize_feature_artifacts(key: str, display: str, roots: tuple[str, ...], decision_for: str) -> dict[str, Any]:
    paths = discover_feature_paths(key, roots)
    inspected: list[dict[str, Any]] = []
    for path in paths[:160]:
        summary = summarize_table(path, decision_for=decision_for, require_ohlcv=False, check_duplicates=False)
        if summary["row_count"] or summary["latest_date"] or summary["status"] != "UNREADABLE":
            inspected.append(summary)
    latest_item = max(inspected, key=lambda item: (item.get("latest_date") or "", item.get("path") or ""), default=None)
    required_missing = []
    if latest_item:
        columns = set(latest_item.get("columns") or [])
        if not any(column in columns for column in DATE_KEYS):
            required_missing.append("date_or_data_until")
        if key != "capital_allocation_ai" and not any(column in columns for column in CODE_KEYS):
            required_missing.append("code_or_symbol")
        if not any(column not in set(DATE_KEYS + CODE_KEYS) for column in columns):
            required_missing.append("feature_columns")
    feature_data_until = latest_item.get("latest_date", "") if latest_item else ""
    return {
        "name": display,
        "artifact_path": latest_item.get("path", "") if latest_item else "",
        "latest_date": feature_data_until,
        "feature_data_until": feature_data_until,
        "row_count": latest_item.get("row_count", 0) if latest_item else 0,
        "feature_schema_hash": latest_item.get("schema_hash", "") if latest_item else "",
        "future_leakage_suspected": bool(latest_item and latest_item.get("future_row_count", 0)),
        "missing_required_feature_columns": required_missing,
        "candidate_artifact_count": len(paths),
        "inspected_artifact_count": len(inspected),
        "status": "AVAILABLE" if latest_item and not required_missing else "MISSING_OR_INCOMPLETE",
    }


def summarize_model_manifest(key: str, display: str, roots: tuple[str, ...], decision_for: str) -> dict[str, Any]:
    paths = discover_model_manifest_paths(key, roots)
    best_payload: dict[str, Any] = {}
    best_path = ""
    best_score: tuple[str, int] = ("", -1)
    for path in paths[:500]:
        payload = read_json_object(path)
        if not payload:
            continue
        extracted = {field: extract_value(payload, field) for field in MODEL_KEYS}
        explicit_count = sum(1 for value in extracted.values() if value not in (None, ""))
        date_score = max((str(extracted.get(item) or "") for item in ("data_until", "train_until", "calibrated_at", "last_trained_at")), default="")
        if (date_score, explicit_count) > best_score:
            best_payload = {key: value for key, value in extracted.items() if value not in (None, "")}
            best_path = str(path)
            best_score = (date_score, explicit_count)
    if key == "capital_allocation_ai":
        best_payload.setdefault("model_version", best_payload.get("policy_id") or best_payload.get("active_policy") or "CAP5")
        best_payload.setdefault("policy_version", best_payload.get("policy_id") or best_payload.get("active_policy") or "CAP5")
    manifest_for_eligibility = {
        "model_version": best_payload.get("model_version") or best_payload.get("policy_version") or best_payload.get("policy_id") or "",
        "train_until": best_payload.get("train_until") or "",
        "data_until": best_payload.get("data_until") or "",
        "feature_schema_hash": best_payload.get("feature_schema_hash") or "",
        "leakage_audit_status": best_payload.get("leakage_audit_status") or "",
        "artifact_path": best_payload.get("artifact_path") or best_payload.get("model_artifact_path") or "",
        "training_sources": ["J-Quants"],
    }
    eligibility = check_model_eligibility(manifest_for_eligibility, decision_for=decision_for).to_dict()
    return {
        "name": display,
        "active_manifest_path": best_path,
        "model_version": manifest_for_eligibility["model_version"],
        "policy_version": best_payload.get("policy_version") or best_payload.get("policy_id") or best_payload.get("active_policy") or "",
        "model_artifact_path": best_payload.get("model_artifact_path") or best_payload.get("artifact_path") or "",
        "training_manifest_path": best_payload.get("training_manifest_path") or best_path,
        "train_until": manifest_for_eligibility["train_until"],
        "data_until": manifest_for_eligibility["data_until"],
        "label_horizon": best_payload.get("label_horizon") or "",
        "feature_schema_hash": manifest_for_eligibility["feature_schema_hash"],
        "leakage_audit_status": manifest_for_eligibility["leakage_audit_status"],
        "retrain_mode": best_payload.get("retrain_mode") or "",
        "last_trained_or_calibrated_at": best_payload.get("last_trained_at") or best_payload.get("calibrated_at") or "",
        "eligibility": eligibility,
        "can_use_for_decision_for": eligibility["status"] == "ELIGIBLE",
        "candidate_manifest_count": len(paths),
    }


def summarize_phase9_readiness(
    *,
    decision_for: str,
    runtime_dir: Path,
    reports_root: Path,
    normalized_daily_path: Path | None,
    listed_info_path: Path | None,
) -> dict[str, Any]:
    runner_importable = True
    runner_import_error = ""
    try:
        from ai_fund_lab_v2.paper_trading.daily_operation_runner import OPERATION_MODES  # noqa: F401
    except Exception as exc:  # pragma: no cover - defensive audit path
        runner_importable = False
        runner_import_error = type(exc).__name__
    report_probe = reports_root / "phase9"
    report_probe.mkdir(parents=True, exist_ok=True)
    latest_ledger = runtime_dir / "phase9/ledger/latest.json"
    return {
        "daily_operation_runner_importable": runner_importable,
        "daily_operation_runner_import_error": runner_import_error,
        "daily_operation_dry_run_executed": False,
        "daily_operation_dry_run_execution_skipped_reason": "Phase9-H audit forbids inference and only checks static executability.",
        "market_data_readiness_checker_ready": run_market_readiness_probe(
            decision_for=decision_for,
            runtime_dir=runtime_dir,
            daily_quotes_path=normalized_daily_path,
            listed_info_path=listed_info_path,
        )["status"] == MARKET_READY,
        "model_eligibility_checker_available": True,
        "daily_report_output_root_creatable": report_probe.exists(),
        "paper_ledger_latest_exists": latest_ledger.exists(),
        "paper_ledger_latest_path": str(latest_ledger) if latest_ledger.exists() else "",
        "initial_ledger_required": not latest_ledger.exists(),
    }


def run_market_readiness_probe(
    *,
    decision_for: str,
    runtime_dir: Path,
    daily_quotes_path: Path | None,
    listed_info_path: Path | None,
) -> dict[str, Any]:
    try:
        return check_market_data_readiness(
            decision_for=decision_for,
            runtime_dir=runtime_dir,
            daily_quotes_path=daily_quotes_path,
            listed_info_path=listed_info_path,
        ).to_dict()
    except Exception as exc:  # pragma: no cover - defensive audit path
        return {"status": "ERROR", "blocked_reasons": [type(exc).__name__], "data_until": "", "row_count": 0}


def judge_audit(
    *,
    decision_for: str,
    market: Mapping[str, Any],
    features: Mapping[str, Any],
    models: Mapping[str, Any],
    phase9: Mapping[str, Any],
) -> tuple[str, list[str]]:
    actions: list[str] = []
    market_fresh = bool(market.get("data_until_meets_decision_for"))
    if not market_fresh:
        actions.append("J-Quants daily_quotes/listed_info を更新し、normalized data を decision_for 以上まで再生成する。")
    feature_ready = all(item.get("status") == "AVAILABLE" and str(item.get("feature_data_until") or "") >= decision_for for item in features.values())
    if market_fresh and not feature_ready:
        actions.append("最新 market data に対して Candidate/Opportunity/Position/Allocation の feature artifact を生成する。")
    elif not feature_ready:
        actions.append("market data 更新後に feature artifact を生成し、feature data_until を揃える。")
    model_ready = all(item.get("can_use_for_decision_for") for item in models.values())
    if not model_ready:
        actions.append("active model / policy manifest の train_until, data_until, feature_schema_hash, leakage_audit_status, artifact path を確認し、必要なら再学習または eligibility review を行う。")
    if phase9.get("initial_ledger_required"):
        actions.append("Phase9運用開始用の initial Paper Ledger を作成し latest.json として保存する。")
    if not phase9.get("daily_operation_runner_importable") or not phase9.get("daily_report_output_root_creatable"):
        actions.append("Daily Operation Runner と report 出力先の実行環境を修正する。")
    if not actions:
        actions.append("Phase9 Daily Operationを dry-run で開始できる。")
        return READY_FOR_PHASE9_DAILY_OPERATION, actions
    if len(actions) > 1:
        if not market_fresh:
            return DATA_UPDATE_REQUIRED, actions
        return NOT_READY, actions
    if not market_fresh:
        return DATA_UPDATE_REQUIRED, actions
    if not feature_ready:
        return FEATURE_GENERATION_REQUIRED, actions
    if not model_ready:
        return MODEL_RETRAIN_OR_ELIGIBILITY_REVIEW_REQUIRED, actions
    if phase9.get("initial_ledger_required"):
        return INITIAL_LEDGER_REQUIRED, actions
    return NOT_READY, actions


def read_table(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        import pandas as pd

        frame = pd.read_parquet(path)
        columns = [str(column) for column in frame.columns]
        rows = frame.astype(object).where(pd.notna(frame), None).to_dict(orient="records")
        return rows, columns
    if suffix == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = [dict(row) for row in reader]
            return rows, list(reader.fieldnames or [])
    payload = json.loads(path.read_text(encoding="utf-8")) if suffix == ".json" else None
    if suffix == ".jsonl":
        rows = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))
        columns = sorted({str(key) for row in rows if isinstance(row, dict) for key in row})
        return rows, columns
    if isinstance(payload, list):
        rows = [dict(item) for item in payload if isinstance(item, dict)]
    elif isinstance(payload, dict):
        rows = []
        for key in ("rows", "features", "candidates", "decisions", "items", "data"):
            if isinstance(payload.get(key), list):
                rows = [dict(item) for item in payload[key] if isinstance(item, dict)]
                break
        if not rows:
            rows = [payload]
    else:
        rows = []
    columns = sorted({str(key) for row in rows if isinstance(row, dict) for key in row})
    return rows, columns


def first_existing(paths: Iterable[Path]) -> Path | None:
    for path in paths:
        if path.exists() and path.is_file():
            return path
    return None


def latest_response_date(response_dir: Path) -> str:
    if not response_dir.exists():
        return ""
    dates = [normalize_date(path.name) for path in response_dir.glob("*.json")]
    return max((date for date in dates if date), default="")


def discover_feature_paths(key: str, roots: tuple[str, ...]) -> list[Path]:
    includes = {
        "candidate_ai": ("feature", "candidate"),
        "opportunity_ai": ("feature", "dataset", "inference", "opportunity"),
        "position_management_ai": ("feature", "position", "signal"),
        "capital_allocation_ai": ("allocation", "decision", "policy"),
    }[key]
    return discover_paths(roots, includes=includes, suffixes=(".json", ".jsonl", ".csv", ".parquet"))


def discover_model_manifest_paths(key: str, roots: tuple[str, ...]) -> list[Path]:
    includes = {
        "candidate_ai": ("model", "manifest", "training", "summary", "audit"),
        "opportunity_ai": ("model", "manifest", "training", "summary", "audit", "calibration", "policy"),
        "position_management_ai": ("model", "manifest", "training", "summary", "audit", "calibration", "policy"),
        "capital_allocation_ai": ("policy", "summary", "audit", "validation", "final"),
    }[key]
    return discover_paths(roots, includes=includes, suffixes=(".json",))


def discover_paths(roots: tuple[str, ...], *, includes: tuple[str, ...], suffixes: tuple[str, ...]) -> list[Path]:
    paths: list[Path] = []
    for root_text in roots:
        root = Path(root_text)
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            text = str(path).lower()
            if any(include in text for include in includes):
                paths.append(path)
    return sorted(paths, key=lambda item: item.stat().st_mtime, reverse=True)


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def extract_value(payload: Any, target_key: str) -> Any:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == target_key:
                return value
        for value in payload.values():
            found = extract_value(value, target_key)
            if found not in (None, ""):
                return found
    elif isinstance(payload, list):
        for value in payload[:50]:
            found = extract_value(value, target_key)
            if found not in (None, ""):
                return found
    return None


def latest_date(rows: list[Mapping[str, Any]]) -> str:
    values = [row_date(row) for row in rows]
    return max((value for value in values if value), default="")


def row_date(row: Mapping[str, Any]) -> str:
    for key in DATE_KEYS:
        value = row.get(key)
        normalized = normalize_date(value)
        if normalized:
            return normalized
    return ""


def normalize_date(value: Any) -> str:
    if value in (None, ""):
        return ""
    text = str(value)
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group(0)
    match = re.search(r"\d{8}", text)
    if match:
        raw = match.group(0)
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    return ""


def required_missing(columns: list[str], *, require_ohlcv: bool) -> list[str]:
    missing: list[str] = []
    column_set = set(columns)
    if not any(key in column_set for key in DATE_KEYS):
        missing.append("date")
    if require_ohlcv:
        if not any(key in column_set for key in CODE_KEYS):
            missing.append("code")
        for normalized, aliases in OHLCV_ALIASES.items():
            if not any(alias in column_set for alias in aliases):
                missing.append(normalized)
    return missing


def count_nonpositive_ohlcv(rows: list[Mapping[str, Any]]) -> int:
    count = 0
    for row in rows:
        for aliases in OHLCV_ALIASES.values():
            value = first_value(row, aliases)
            if value in (None, ""):
                count += 1
                break
            try:
                if float(str(value).replace(",", "")) <= 0:
                    count += 1
                    break
            except ValueError:
                count += 1
                break
    return count


def count_duplicate_date_code(rows: list[Mapping[str, Any]]) -> int:
    seen: set[tuple[str, str]] = set()
    duplicates = 0
    for row in rows:
        date = row_date(row)
        code = str(first_value(row, CODE_KEYS) or "")
        if not date or not code:
            continue
        key = (date, code)
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
    return duplicates


def first_value(row: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in row:
            return row.get(key)
    return None


def schema_hash(columns: Iterable[str]) -> str:
    payload = "|".join(sorted(str(column) for column in columns))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16] if payload else ""


def render_markdown(audit: Mapping[str, Any]) -> str:
    market = audit["market_data"]
    features = audit["feature_artifacts"]
    models = audit["models_and_policies"]
    phase9 = audit["phase9_operation_readiness"]
    lines = [
        "# Phase9-H Preflight Data / Model Freshness Audit",
        "",
        f"- decision_for: {audit['decision_for']}",
        f"- judgment: {audit['judgment']}",
        "",
        "## Summary",
        "",
        f"- raw daily_quotes response latest: {market.get('raw_daily_quote_response_latest_date') or 'MISSING'}",
        f"- raw daily_quotes table latest: {market['raw_daily_quotes'].get('latest_date') or 'MISSING'}",
        f"- normalized daily_quotes latest: {market['normalized_daily_quotes'].get('latest_date') or 'MISSING'}",
        f"- listed_info latest: {market['listed_info'].get('latest_date') or 'MISSING'}",
        f"- trading_calendar latest: {market['trading_calendar'].get('latest_date') or 'MISSING'}",
        f"- data_until candidate: {market.get('data_until_candidate') or 'MISSING'}",
        f"- Paper Ledger latest: {'FOUND' if phase9.get('paper_ledger_latest_exists') else 'MISSING'}",
        "",
        "## Market Data",
        "",
        "| target | status | latest_date | rows | path |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for key in ("raw_daily_quotes", "normalized_daily_quotes", "listed_info", "trading_calendar"):
        item = market[key]
        lines.append(f"| {key} | {item.get('status')} | {item.get('latest_date') or ''} | {item.get('row_count')} | `{item.get('path')}` |")
    lines.extend(
        [
            "",
            "## Feature Artifacts",
            "",
            "| AI | status | feature_data_until | rows | feature_schema_hash | path |",
            "| --- | --- | ---: | ---: | --- | --- |",
        ]
    )
    for item in features.values():
        lines.append(
            f"| {item.get('name')} | {item.get('status')} | {item.get('feature_data_until') or ''} | {item.get('row_count')} | {item.get('feature_schema_hash') or ''} | `{item.get('artifact_path')}` |"
        )
    lines.extend(
        [
            "",
            "## Models / Policies",
            "",
            "| AI | model_version / policy | train_until | data_until | leakage | eligibility | manifest |",
            "| --- | --- | ---: | ---: | --- | --- | --- |",
        ]
    )
    for item in models.values():
        version = item.get("model_version") or item.get("policy_version") or ""
        lines.append(
            f"| {item.get('name')} | {version} | {item.get('train_until') or ''} | {item.get('data_until') or ''} | {item.get('leakage_audit_status') or ''} | {item.get('eligibility', {}).get('status')} | `{item.get('active_manifest_path')}` |"
        )
    lines.extend(
        [
            "",
            "## Phase9 Operation Readiness",
            "",
            f"- Daily Operation Runner importable: {phase9.get('daily_operation_runner_importable')}",
            f"- Daily operation dry-run executed by this audit: {phase9.get('daily_operation_dry_run_executed')}",
            f"- dry-run execution skipped reason: {phase9.get('daily_operation_dry_run_execution_skipped_reason')}",
            f"- Market Data Readiness Checker READY: {phase9.get('market_data_readiness_checker_ready')}",
            f"- Model Eligibility Checker available: {phase9.get('model_eligibility_checker_available')}",
            f"- Daily Report output root creatable: {phase9.get('daily_report_output_root_creatable')}",
            f"- Paper Ledger latest exists: {phase9.get('paper_ledger_latest_exists')}",
            "",
            "## Next Actions",
            "",
        ]
    )
    lines.extend(f"- {action}" for action in audit["next_actions"])
    lines.extend(
        [
            "",
            "## Prohibited Actions",
            "",
        ]
    )
    for key, value in audit["prohibited_actions"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
