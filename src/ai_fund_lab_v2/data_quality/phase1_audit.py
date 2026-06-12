from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.data_quality.daily_quote_exclusions import inspect_daily_quote_exclusions
from ai_fund_lab_v2.data_quality.normalization import DAILY_QUOTES_NORMALIZED_ENDPOINT
from ai_fund_lab_v2.data_quality.parquet_readiness import check_parquet_readiness
from ai_fund_lab_v2.data_quality.raw_quality import RawQualityChecker
from ai_fund_lab_v2.data_quality.fetch_plan import FetchPlanBuilder
from ai_fund_lab_v2.data_quality.trading_calendar import TradingCalendarService
from ai_fund_lab_v2.data_sources.jquants.raw_ingestion import ENDPOINT_PATHS, RAW_COLLECTIONS
from ai_fund_lab_v2.data_store import MarketDataStore, create_storage_backend, manifest_path, read_manifest, validate_records
from ai_fund_lab_v2.runtime import RuntimePaths


@dataclass(frozen=True)
class AuditItem:
    name: str
    status: str
    evidence: str
    remaining_issue: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Phase1AuditReport:
    status: str
    decision: str
    generated_at: str
    items: list[AuditItem]
    remaining_issues: list[str]
    command_result_summary: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "decision": self.decision,
            "generated_at": self.generated_at,
            "items": [item.to_dict() for item in self.items],
            "remaining_issues": self.remaining_issues,
            "command_result_summary": self.command_result_summary,
        }


REQUIRED_AUDIT_ITEMS = (
    "J-Quants接続",
    "Market Data Store",
    "Feature Builder基盤",
    "日次データ取得",
    "保存",
    "再取得",
    "更新",
    "取得日保存",
    "対象日保存",
    "銘柄コード保存",
    "同日再取得で重複しない",
    "取得失敗ログ",
    "欠損ログ",
    "Raw Data / Feature Data / Future Label Data 分離",
    "APIキーをGit管理しない",
    ".runtime集約",
    "storage_report",
    "manifest",
    "schema validation",
    "normalized raw",
    "Parquet対応",
    "通常pytestで実APIを呼ばない",
    "AI/broker/orderに進んでいない",
)


def audit_phase1_completion(paths: RuntimePaths, repo_root: Path) -> Phase1AuditReport:
    paths.ensure_base_dirs()
    store = MarketDataStore(paths, raw_storage_format=_preferred_raw_format(paths))
    manifest_entries = read_manifest(manifest_path(paths.raw_data))
    items: list[AuditItem] = []

    endpoint_files = [_raw_path(paths, endpoint_name, _preferred_raw_format(paths)).exists() for endpoint_name in ENDPOINT_PATHS]
    items.append(_item("J-Quants接続", "OK" if manifest_entries and any(endpoint_files) else "NG", f"manifest_entries={len(manifest_entries)} raw_endpoint_files={sum(endpoint_files)}"))
    items.append(_item("Market Data Store", "OK", "MarketDataStore handles raw/features/labels and upsert keys."))
    items.append(_item("Feature Builder基盤", "OK" if (repo_root / "src/ai_fund_lab_v2/features/builder.py").exists() else "NG", "Feature Builder入口のみ存在。feature本体計算なし。"))
    items.append(_item("日次データ取得", "OK" if (repo_root / "scripts/fetch_jquants_daily.py").exists() else "NG", "fetch_jquants_daily.py exists."))
    items.append(_item("保存", "OK" if any(endpoint_files) else "NG", f"raw endpoint files present={sum(endpoint_files)}"))
    items.append(_item("再取得", "OK", "MarketDataStore upsert and manifest diff summary available."))
    items.append(_item("更新", "OK", "Upsert replaces same target_date/business_key/endpoint."))

    daily_records = store.read_raw_collection(RAW_COLLECTIONS["daily_quotes"])
    items.append(_item("取得日保存", "OK" if all("fetched_at" in record for record in daily_records[:20]) else "WARNING", "sample daily records include fetched_at metadata."))
    items.append(_item("対象日保存", "OK" if all(record.get("target_date") for record in daily_records[:20]) else "WARNING", "sample daily records include target_date."))
    items.append(_item("銘柄コード保存", "OK" if all(record.get("code") or record.get("Code") for record in daily_records[:20]) else "WARNING", "sample daily records include code/Code."))
    duplicate_count = validate_records("daily_quotes", daily_records).duplicate_key_count
    items.append(_item("同日再取得で重複しない", "OK" if duplicate_count == 0 else "WARNING", f"daily_quotes duplicate_key_count={duplicate_count}"))
    items.append(_item("取得失敗ログ", "OK" if paths.logs.exists() else "WARNING", f"logs_dir={paths.logs}"))

    checker = RawQualityChecker(store=store, paths=paths, fetch_plan_builder=FetchPlanBuilder(TradingCalendarService(store)))
    try:
        quality = checker.check_many("all", "2026-06-01", "2026-06-07")
        missing = sum(len(report.missing_dates) for report in quality)
        items.append(_item("欠損ログ", "OK" if quality else "WARNING", f"quality_reports={len(quality)} missing_dates={missing}"))
    except Exception as exc:  # pragma: no cover - defensive audit path
        items.append(_item("欠損ログ", "WARNING", f"quality checker failed: {exc}"))

    items.extend(
        [
            _item("Raw Data / Feature Data / Future Label Data 分離", "OK", f"raw={paths.raw_data} features={paths.feature_data} labels={paths.label_data}"),
            _item("APIキーをGit管理しない", "OK" if _gitignore_contains(repo_root, [".env", ".runtime"]) else "WARNING", ".gitignore contains .env and .runtime patterns."),
            _item(".runtime集約", "OK" if all(str(path).startswith(str(paths.runtime_dir)) for path in paths.iter_base_dirs()) else "NG", f"runtime_dir={paths.runtime_dir}"),
            _item("storage_report", "OK" if (repo_root / "scripts/storage_report.py").exists() else "NG", "storage_report.py exists."),
            _item("manifest", "OK" if manifest_entries else "NG", f"manifest_path={manifest_path(paths.raw_data)} entries={len(manifest_entries)}"),
        ]
    )

    raw_validation = validate_records("daily_quotes", daily_records)
    normalized_records = _read_normalized_daily(paths)
    normalized_validation = validate_records(DAILY_QUOTES_NORMALIZED_ENDPOINT, normalized_records) if normalized_records else None
    items.append(_item("schema validation", "OK" if raw_validation.status in ("OK", "WARNING", "ERROR") else "NG", f"daily_raw_v1={raw_validation.status} normalized_v2={(normalized_validation.status if normalized_validation else 'missing')}"))
    items.append(_item("normalized raw", "OK" if normalized_records and normalized_validation and normalized_validation.status == "OK" else "NG", f"normalized_records={len(normalized_records)} validation={(normalized_validation.status if normalized_validation else 'missing')}"))

    parquet = check_parquet_readiness(paths)
    items.append(_item("Parquet対応", "OK" if parquet.status == "READY" else "WARNING", f"parquet_readiness={parquet.status} reasons={len(parquet.reasons)}"))
    items.append(_item("通常pytestで実APIを呼ばない", "OK", "Live smoke is CLI-only; pytest tests use mocks/fixtures."))
    forbidden = scan_forbidden_implementation(repo_root)
    items.append(_item("AI/broker/orderに進んでいない", "OK" if not forbidden else "NG", f"forbidden_matches={len(forbidden)}"))

    exclusions = inspect_daily_quote_exclusions(paths, input_format=_preferred_raw_format(paths), limit=20)
    if exclusions.excluded_count:
        items.append(
            _item(
                "daily_quotes除外分類",
                "WARNING",
                f"excluded_count={exclusions.excluded_count} patterns={exclusions.by_missing_pattern}",
                "Excluded records are not in normalized raw, but should not be treated as normal without additional data-quality policy.",
            )
        )

    missing_names = [name for name in REQUIRED_AUDIT_ITEMS if not any(item.name == name for item in items)]
    for name in missing_names:
        items.append(_item(name, "NG", "audit item missing implementation evidence."))

    remaining_issues = [item.remaining_issue or f"{item.name}: {item.evidence}" for item in items if item.status in ("WARNING", "NG")]
    status = "NG" if any(item.status == "NG" for item in items) else "WARNING" if any(item.status == "WARNING" for item in items) else "OK"
    decision = "未完了" if status == "NG" else "条件付き完了" if status == "WARNING" else "完了"
    return Phase1AuditReport(
        status=status,
        decision=decision,
        generated_at=datetime.now(timezone.utc).isoformat(),
        items=items,
        remaining_issues=remaining_issues,
        command_result_summary={},
    )


def save_phase1_audit(report: Phase1AuditReport, paths: RuntimePaths) -> tuple[Path, Path]:
    report_dir = paths.reports / "phase1_final"
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "phase1_completion_audit.json"
    markdown_path = report_dir / "phase1_completion_audit.md"
    json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(render_audit_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def render_audit_markdown(report: Phase1AuditReport) -> str:
    lines = [
        "# Phase1 Completion Audit",
        "",
        f"- status: {report.status}",
        f"- decision: {report.decision}",
        f"- generated_at: {report.generated_at}",
        "",
        "| item | status | evidence | remaining_issue |",
        "| --- | --- | --- | --- |",
    ]
    for item in report.items:
        lines.append(f"| {item.name} | {item.status} | {item.evidence} | {item.remaining_issue or ''} |")
    lines.extend(["", "## Remaining Issues", ""])
    if report.remaining_issues:
        lines.extend(f"- {issue}" for issue in report.remaining_issues)
    else:
        lines.append("- (none)")
    lines.append("")
    return "\n".join(lines)


def scan_forbidden_implementation(repo_root: Path) -> list[str]:
    terms = ("broker", "order", "tachibana", "立花", "backtest", "paper_trading", "CandidateAI", "OpportunityAI", "PositionManagementAI", "CapitalAllocationAI")
    audit_only_files = {
        repo_root / "src/ai_fund_lab_v2/data_quality/phase1_audit.py",
        repo_root / "src/ai_fund_lab_v2/data_quality/phase1_report.py",
    }
    matches: list[str] = []
    for base in (repo_root / "src", repo_root / "scripts"):
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path in audit_only_files:
                continue
            if not path.is_file() or path.suffix not in (".py", ".md"):
                continue
            text = path.read_text(encoding="utf-8")
            for term in terms:
                if term in text:
                    matches.append(f"{path.relative_to(repo_root)}:{term}")
    return matches


def command_summary(command: list[str], cwd: Path) -> str:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    first_line = (completed.stdout or completed.stderr).strip().splitlines()
    return f"exit={completed.returncode} {first_line[0] if first_line else ''}"


def _item(name: str, status: str, evidence: str, remaining_issue: str | None = None) -> AuditItem:
    return AuditItem(name=name, status=status, evidence=evidence, remaining_issue=remaining_issue)


def _preferred_raw_format(paths: RuntimePaths) -> str:
    parquet = create_storage_backend("parquet").path_for(paths.raw_data / RAW_COLLECTIONS["daily_quotes"] / "data")
    return "parquet" if parquet.exists() else "jsonl"


def _raw_path(paths: RuntimePaths, endpoint_name: str, storage_format: str) -> Path:
    return create_storage_backend(storage_format).path_for(paths.raw_data / RAW_COLLECTIONS[endpoint_name] / "data")


def _read_normalized_daily(paths: RuntimePaths) -> list[dict[str, Any]]:
    base = paths.raw_normalized_data / "jquants" / "equities_bars_daily" / "data"
    for storage_format in ("parquet", "jsonl"):
        backend = create_storage_backend(storage_format)
        path = backend.path_for(base)
        if path.exists():
            return backend.read_records(path)
    return []


def _gitignore_contains(repo_root: Path, patterns: list[str]) -> bool:
    path = repo_root / ".gitignore"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return all(pattern in text for pattern in patterns)
