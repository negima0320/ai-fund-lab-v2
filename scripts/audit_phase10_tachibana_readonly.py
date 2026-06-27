from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PHASE10_RESULT_FILES = {
    "login_session_logout": "reports/phase_reports/phase10d10_tachibana_demo_login_smoke_result.json",
    "account_balance": "reports/phase_reports/phase10e_tachibana_account_balance_smoke_result.json",
    "positions": "reports/phase_reports/phase10f_tachibana_positions_smoke_result.json",
    "orders": "reports/phase_reports/phase10g_tachibana_orders_smoke_result.json",
    "executions_history": "reports/phase_reports/phase10h_tachibana_executions_history_smoke_result.json",
    "realtime_quote": "reports/phase_reports/phase10i_tachibana_realtime_quote_smoke_result.json",
    "broker_snapshot": "reports/phase_reports/phase10j_tachibana_broker_snapshot_integration.json",
}
SNAPSHOT_PATH = Path(".runtime/broker/tachibana/demo/latest_broker_snapshot.json")
REPORT_PATH = Path("reports/phase_reports/phase10k_tachibana_readonly_completion_audit.json")

FORBIDDEN_CLMIDS = (
    "CLMKabuNewOrder",
    "CLMKabuCorrectOrder",
    "CLMKabuCancelOrder",
    "CLMKabuCancelOrderAll",
    "CLMAuthCheckSecondPassword",
    "CLMAuthStkLoginRequest",
)
READ_ONLY_CLMIDS = (
    "CLMAuthLoginRequest",
    "CLMAuthLogoutRequest",
    "CLMZanKaiSummary",
    "CLMZanKaiKanougaku",
    "CLMGenbutuKabuList",
    "CLMShinyouTategyokuList",
    "CLMOrderList",
    "CLMOrderListDetail",
    "CLMMfdsGetMarketPrice",
    "CLMMfdsGetMarketPriceHistory",
)
SECRET_PATTERNS = (
    r"BEGIN .*PRIVATE KEY",
    r"END .*PRIVATE KEY",
    r"sUrl(Request|Master|Price|Event|EventWebSocket).*://[A-Za-z0-9]",
    r"ciphertext[=:][A-Za-z0-9+/_-]{20,}",
    r"decrypted.*(https://|wss://|ws://)",
    r"auth[_ -]?id.*[A-Za-z0-9]{20,}",
    r"customer-secret",
    r"account-secret",
    r"ORDER-SECRET",
    r"https://demo-kabuka\.e-shiten\.jp/e_api_v4r9/[A-Za-z0-9_/?=&%.-]{20,}",
    r"wss://[A-Za-z0-9._/?=&%:-]{20,}",
)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: dict[str, Any]


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.root)
    report_path = root / args.output
    payload = run_audit(root=root)
    _write_json(report_path, payload)
    print(json.dumps({"status": payload["status"], "report_path": str(report_path), "phase10_complete": payload["phase10_complete"]}, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


def run_audit(*, root: Path) -> dict[str, Any]:
    checks = [
        _check_readonly_results(root),
        _check_snapshot(root),
        _check_allowlist(root),
        _check_forbidden_clmid_locations(root),
        _check_secret_canary(root),
        _check_paper_trading_separation(root),
        _check_env_and_gitignore(root),
    ]
    status = "PASS" if all(check.status == "PASS" for check in checks) else "FAIL"
    return {
        "status": status,
        "phase10_complete": status == "PASS",
        "broker": "tachibana",
        "environment": "demo",
        "checks": {check.name: {"status": check.status, **check.detail} for check in checks},
        "completion_judgement": {
            "result": "Phase10 Complete" if status == "PASS" else "Phase10 Incomplete",
            "next_phase": "Phase11 Safety Layer" if status == "PASS" else "Fix Phase10 audit findings",
        },
    }


def _check_readonly_results(root: Path) -> Check:
    expected = {
        "login_session_logout": {"PASS"},
        "account_balance": {"PASS"},
        "positions": {"PASS"},
        "orders": {"PASS"},
        "executions_history": {"PASS", "PASS_WITH_EMPTY_RESULT", "SKIPPED_NO_ORDERS"},
        "realtime_quote": {"PASS", "PASS_WITH_EMPTY_RESULT", "MARKET_CLOSED"},
        "broker_snapshot": {"PASS", "PASS_WITH_WARNINGS"},
    }
    observed: dict[str, Any] = {}
    failures: list[str] = []
    for name, rel_path in PHASE10_RESULT_FILES.items():
        path = root / rel_path
        data = _read_json(path)
        status = str(data.get("status", ""))
        observed[name] = {"path": rel_path, "status": status, "executed": data.get("executed"), "environment": data.get("environment")}
        if status not in expected[name]:
            failures.append(f"{name}:unexpected_status:{status}")
        if data.get("environment") != "demo":
            failures.append(f"{name}:not_demo")
        if name != "broker_snapshot" and data.get("executed") is not True:
            failures.append(f"{name}:not_executed")
    return Check("read_only_api_reachability", "PASS" if not failures else "FAIL", {"observed": observed, "failures": failures})


def _check_snapshot(root: Path) -> Check:
    path = root / SNAPSHOT_PATH
    failures: list[str] = []
    data = _read_json(path)
    if not path.is_file():
        failures.append("snapshot_missing")
    if data.get("schema_version") != "tachibana_broker_snapshot_v1":
        failures.append("unexpected_schema_version")
    if data.get("environment") != "demo":
        failures.append("snapshot_not_demo")
    if data.get("session_status") != "PASS":
        failures.append("session_not_pass")
    redaction = data.get("redaction_status", {})
    for key, value in redaction.items():
        if value is not False:
            failures.append(f"redaction_not_false:{key}")
    return Check(
        "broker_snapshot_runtime_file",
        "PASS" if not failures else "FAIL",
        {
            "path": str(SNAPSHOT_PATH),
            "exists": path.is_file(),
            "schema_version": data.get("schema_version"),
            "health": data.get("health", {}),
            "redaction_status": redaction,
            "failures": failures,
        },
    )


def _check_allowlist(root: Path) -> Check:
    allowlist_path = root / "src/ai_fund_lab_v2/broker/allowlist.py"
    text = allowlist_path.read_text(encoding="utf-8")
    failures: list[str] = []
    for clmid in READ_ONLY_CLMIDS:
        if clmid not in text:
            failures.append(f"missing_readonly:{clmid}")
    for clmid in FORBIDDEN_CLMIDS:
        if clmid not in text:
            failures.append(f"missing_forbidden:{clmid}")
    if "clmid not in READ_ONLY_CLMIDS" not in text:
        failures.append("unknown_clmid_deny_by_default_not_detected")
    return Check("allowlist_denylist", "PASS" if not failures else "FAIL", {"failures": failures})


def _check_forbidden_clmid_locations(root: Path) -> Check:
    scan_roots = [root / "src/ai_fund_lab_v2/broker", root / "src/ai_fund_lab_v2/cli", root / "tests/broker"]
    allowed_suffixes = {
        "src/ai_fund_lab_v2/broker/allowlist.py",
        "tests/broker/test_broker_allowlist.py",
        "tests/broker/test_mock_transport.py",
        "tests/broker/test_tachibana_request_builder.py",
    }
    findings: list[dict[str, Any]] = []
    for path in _iter_text_files(scan_roots):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        for clmid in FORBIDDEN_CLMIDS:
            if clmid in text and rel not in allowed_suffixes:
                findings.append({"path": rel, "clmid": clmid})
        if "unlock_trade" in text and rel not in allowed_suffixes:
            findings.append({"path": rel, "clmid": "unlock_trade"})
    return Check("no_live_order_audit", "PASS" if not findings else "FAIL", {"unexpected_findings": findings})


def _check_secret_canary(root: Path) -> Check:
    paths = [
        *(root / "docs/phase_reports").glob("phase10*.md"),
        *(root / "reports/phase_reports").glob("phase10*.json"),
        root / SNAPSHOT_PATH,
        root / ".env.example",
    ]
    findings: list[dict[str, Any]] = []
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in SECRET_PATTERNS]
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in compiled:
            match = pattern.search(text)
            if match:
                findings.append({"path": path.relative_to(root).as_posix(), "pattern": pattern.pattern})
    return Check("secret_redaction_canary", "PASS" if not findings else "FAIL", {"unexpected_findings": findings})


def _check_paper_trading_separation(root: Path) -> Check:
    report = _read_json(root / "reports/phase_reports/phase10j_tachibana_broker_snapshot_integration.json")
    failures: list[str] = []
    if report.get("paper_ledger_updated") is not False:
        failures.append("paper_ledger_updated_not_false")
    if report.get("ai_learning_updated") is not False:
        failures.append("ai_learning_updated_not_false")
    if report.get("raw_response_saved") is not False:
        failures.append("raw_response_saved_not_false")
    return Check("paper_trading_separation", "PASS" if not failures else "FAIL", {"failures": failures})


def _check_env_and_gitignore(root: Path) -> Check:
    env_text = (root / ".env.example").read_text(encoding="utf-8")
    gitignore_text = (root / ".gitignore").read_text(encoding="utf-8")
    failures: list[str] = []
    if "TACHIBANA_API_AUTH_ID=" not in env_text:
        failures.append("env_example_missing_auth_id_placeholder")
    if "TACHIBANA_API_PRIVATE_KEY_FILE=" not in env_text:
        failures.append("env_example_missing_private_key_placeholder")
    if ".env" not in gitignore_text or ".runtime/" not in gitignore_text or "reports/" not in gitignore_text:
        failures.append("gitignore_missing_runtime_or_secret_patterns")
    return Check("file_runtime_safety", "PASS" if not failures else "FAIL", {"failures": failures})


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _iter_text_files(roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if root.is_file():
            files.append(root)
        elif root.is_dir():
            files.extend(path for path in root.rglob("*") if path.is_file() and path.suffix in {".py", ".md", ".json", ".txt"})
    return sorted(files)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit Phase10 Tachibana demo read-only completion without live API calls.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--output", default=str(REPORT_PATH), help="Audit report JSON path.")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
