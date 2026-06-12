from __future__ import annotations

import argparse
import json
import sys
from dataclasses import fields
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping  # noqa: E402
from ai_fund_lab_v2.safety import (  # noqa: E402
    BrokerState,
    PortfolioState,
    ReconciliationResult,
    SafetyReport,
    SafetyStatus,
    TradingLock,
    UnlockApproval,
    UnlockApplyResult,
    UnlockRequest,
    build_mock_portfolio_state_from_broker_state,
    build_safety_report,
    build_trading_lock,
    broker_snapshot_to_state,
    can_apply_unlock,
    can_request_unlock,
    check_operation_allowed_by_current_state,
    load_latest_lock_state,
    reconcile_states,
    resolve_current_lock_state,
    run_safety_dry_run,
    write_safety_audit_log,
    write_safety_report,
    write_trading_lock,
)


PHASE = "Phase3"
PYTEST_HINT = "python3 -m pytest tests/safety -q && python3 -m pytest -q"

DOC_PATHS = (
    "docs/01_requirements/phase_roadmap.md",
    "docs/02_architecture/safety_guard_design.md",
    "docs/02_architecture/safety_foundation_phase3_design.md",
    "docs/02_architecture/safety_manual_review_flow.md",
    "docs/02_architecture/safety_manual_unlock_flow.md",
    "docs/02_architecture/safety_manual_unlock_apply_flow.md",
    "docs/02_architecture/safety_operation_guard_lock_state_flow.md",
    "docs/02_architecture/broker_integration_design.md",
)

SAFETY_MODULES = (
    "src/ai_fund_lab_v2/safety/models.py",
    "src/ai_fund_lab_v2/safety/reconciliation.py",
    "src/ai_fund_lab_v2/safety/trading_lock.py",
    "src/ai_fund_lab_v2/safety/report.py",
    "src/ai_fund_lab_v2/safety/report_writer.py",
    "src/ai_fund_lab_v2/safety/broker_state_adapter.py",
    "src/ai_fund_lab_v2/safety/dry_run.py",
    "src/ai_fund_lab_v2/safety/audit_writer.py",
    "src/ai_fund_lab_v2/safety/manual_unlock.py",
    "src/ai_fund_lab_v2/safety/unlock_models.py",
    "src/ai_fund_lab_v2/safety/unlock_policy.py",
    "src/ai_fund_lab_v2/safety/unlock_writer.py",
    "src/ai_fund_lab_v2/safety/manual_unlock_apply.py",
    "src/ai_fund_lab_v2/safety/unlock_apply_policy.py",
    "src/ai_fund_lab_v2/safety/lock_state_resolver.py",
    "src/ai_fund_lab_v2/safety/operation_guard.py",
)

TEST_PATHS = (
    "tests/safety/test_reconciliation.py",
    "tests/safety/test_trading_lock.py",
    "tests/safety/test_safety_report_writer.py",
    "tests/safety/test_broker_state_adapter.py",
    "tests/safety/test_safety_dry_run.py",
    "tests/safety/test_manual_unlock.py",
    "tests/safety/test_manual_unlock_apply.py",
    "tests/safety/test_operation_guard_lock_state.py",
)

SENSITIVE_CANARIES = (
    "secret-auth-id",
    "https://example.invalid/request",
    "https://example.invalid/session",
    "account_id=123456",
    "secret-password",
    "secret-second-password",
    "secret-token",
    "secret-cookie",
)


def run_audit(
    runtime_dir: Path | str = ".runtime",
    json_report_path: Path | str = "reports/phase_reports/phase3_safety_foundation_completion_audit.json",
    markdown_report_path: Path | str = "docs/phase_reports/phase3_safety_foundation_completion_audit.md",
) -> dict[str, Any]:
    root = ROOT
    checks = {
        "safety_models": _safety_models_present(),
        "reconciliation": _reconciliation_present(),
        "trading_lock": _trading_lock_present(),
        "safety_report": _safety_report_present(),
        "broker_snapshot_integration": callable(broker_snapshot_to_state),
        "dry_run": callable(run_safety_dry_run),
        "manual_review": _docs_exist(root, ("docs/02_architecture/safety_manual_review_flow.md",)),
        "manual_unlock": _manual_unlock_present(),
        "manual_unlock_apply": _manual_unlock_apply_present(),
        "operation_guard_lock_state": _operation_guard_lock_state_present(),
        "fail_closed": _file_contains(root / "src/ai_fund_lab_v2/safety/lock_state_resolver.py", "source\": \"corrupt\"")
        and _file_contains(root / "docs/02_architecture/safety_operation_guard_lock_state_flow.md", "fail-closed"),
        "runtime_safety_paths": _runtime_safety_paths_present(),
        "no_live_mode": _no_live_mode_entrypoints(),
        "no_real_api": _no_real_api_usage(),
        "no_ordering": _no_ordering_implementation(),
        "no_ai_integration": _no_ai_integration(),
        "no_auto_recovery": _no_auto_recovery(),
        "tests_present": _docs_exist(root, TEST_PATHS),
    }
    status = "complete" if all(checks.values()) else "incomplete"
    result = sanitize_mapping(
        {
            "phase": PHASE,
            "status": status,
            "checks": checks,
            "pytest_hint": PYTEST_HINT,
            "reports": {
                "json": str(json_report_path),
                "markdown": str(markdown_report_path),
            },
        }
    )
    _write_json(Path(json_report_path), result)
    _write_markdown(Path(markdown_report_path), result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase3 Safety Foundation completion criteria.")
    parser.add_argument("--runtime-dir", default=".runtime", help="Runtime directory reference for audit context.")
    parser.add_argument(
        "--json-report",
        default="reports/phase_reports/phase3_safety_foundation_completion_audit.json",
        help="JSON report output path.",
    )
    parser.add_argument(
        "--markdown-report",
        default="docs/phase_reports/phase3_safety_foundation_completion_audit.md",
        help="Markdown report output path.",
    )
    args = parser.parse_args(argv)
    result = run_audit(
        runtime_dir=Path(args.runtime_dir),
        json_report_path=Path(args.json_report),
        markdown_report_path=Path(args.markdown_report),
    )
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def _safety_models_present() -> bool:
    return (
        SafetyStatus.OK.value == "OK"
        and SafetyStatus.WARNING.value == "WARNING"
        and SafetyStatus.HALT.value == "HALT"
        and {"cash", "buying_power", "positions", "open_orders"}.issubset(_field_names(PortfolioState))
        and {"cash", "buying_power", "positions", "open_orders", "source_snapshot_id"}.issubset(_field_names(BrokerState))
        and {"status", "issues", "checked_at"}.issubset(_field_names(ReconciliationResult))
    )


def _reconciliation_present() -> bool:
    return callable(reconcile_states) and _file_contains(ROOT / "src/ai_fund_lab_v2/safety/reconciliation.py", "position_quantity_mismatch")


def _trading_lock_present() -> bool:
    return callable(build_trading_lock) and {"is_locked", "reason", "status", "issues"}.issubset(_field_names(TradingLock))


def _safety_report_present() -> bool:
    return (
        callable(build_safety_report)
        and callable(write_safety_report)
        and callable(write_trading_lock)
        and callable(write_safety_audit_log)
        and {"status", "checked_at", "broker_snapshot_id", "issue_count", "issues", "trading_locked"}.issubset(
            _field_names(SafetyReport)
        )
    )


def _manual_unlock_present() -> bool:
    return (
        callable(can_request_unlock)
        and {"request_id", "requested_by", "reason", "latest_report_path"}.issubset(_field_names(UnlockRequest))
        and {"request_id", "approved_by", "approval_reason", "reconciliation_status"}.issubset(_field_names(UnlockApproval))
    )


def _manual_unlock_apply_present() -> bool:
    return callable(can_apply_unlock) and {"applied", "status", "applied_by", "latest_report_status", "message"}.issubset(
        _field_names(UnlockApplyResult)
    )


def _operation_guard_lock_state_present() -> bool:
    return callable(load_latest_lock_state) and callable(resolve_current_lock_state) and callable(check_operation_allowed_by_current_state)


def _runtime_safety_paths_present() -> bool:
    expected = (
        'runtime_dir) / "safety" / "reports"',
        'runtime_dir) / "safety" / "locks"',
        'runtime_dir) / "safety" / "audit"',
        'runtime_dir) / "safety" / "unlock"',
    )
    source_text = _concat_files(ROOT / "src/ai_fund_lab_v2/safety", "*.py")
    docs_text = _concat_paths(root=ROOT, paths=DOC_PATHS)
    return all(item in source_text for item in expected[:3]) and ".runtime/safety/" in docs_text


def _no_live_mode_entrypoints() -> bool:
    script_path = ROOT / "scripts/safety/run_safety_dry_run.py"
    source_text = script_path.read_text(encoding="utf-8") if script_path.is_file() else ""
    blocked_args = ("--live", "--api", "--base-url", "--auth", "--login", "--logout")
    return "mock-only" in source_text and all(arg not in source_text for arg in blocked_args)


def _no_real_api_usage() -> bool:
    source_text = _concat_files(ROOT / "src/ai_fund_lab_v2/safety", "*.py") + _concat_files(ROOT / "scripts/safety", "*.py")
    blocked = ("requests.", "urllib.request", "http.client", "socket.", "TACHIBANA_API_BASE_URL")
    return all(item not in source_text for item in blocked)


def _no_ordering_implementation() -> bool:
    source_text = _concat_files(ROOT / "src/ai_fund_lab_v2/safety", "*.py")
    blocked = ("CLMKabuNewOrder", "CLMKabuCorrectOrder", "CLMKabuCancelOrder", "place_order", "submit_order")
    return all(item not in source_text for item in blocked)


def _no_ai_integration() -> bool:
    source_text = _concat_files(ROOT / "src/ai_fund_lab_v2/safety", "*.py")
    blocked = ("candidate_ai", "opportunity_ai", "position_management", "capital_allocation")
    return all(item not in source_text for item in blocked)


def _no_auto_recovery() -> bool:
    source_text = _concat_files(ROOT / "src/ai_fund_lab_v2/safety", "*.py")
    docs_text = _concat_paths(root=ROOT, paths=DOC_PATHS)
    blocked = ("auto_recover", "automatic_recover", "auto_unlock")
    return all(item not in source_text for item in blocked) and "自動復旧は禁止" in docs_text


def _docs_exist(root: Path, paths: tuple[str, ...]) -> bool:
    return all((root / path).is_file() for path in paths)


def _field_names(model: type[Any]) -> set[str]:
    return {field.name for field in fields(model)}


def _file_contains(path: Path, needle: str) -> bool:
    return path.is_file() and needle in path.read_text(encoding="utf-8")


def _concat_paths(root: Path, paths: tuple[str, ...]) -> str:
    return "\n".join((root / path).read_text(encoding="utf-8") for path in paths if (root / path).is_file())


def _concat_files(directory: Path, pattern: str) -> str:
    if not directory.is_dir():
        return ""
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(directory.glob(pattern)))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_build_markdown(payload), encoding="utf-8")


def _build_markdown(payload: dict[str, Any]) -> str:
    checks = payload["checks"]
    check_lines = "\n".join(f"- `{name}`: {'OK' if passed else 'NG'}" for name, passed in sorted(checks.items()))
    status_label = "Phase3 Complete" if payload["status"] == "complete" else "Phase3 Incomplete"
    return (
        "# AI Fund Lab vNext Phase3 Safety Foundation Completion Audit\n\n"
        "## Phase3の目的\n\n"
        "Phase3 Safety Foundation は、Broker状態とPortfolio状態の照合、HALT判定、TradingLock、SafetyReport、"
        "手動レビュー、手動unlock監査、OperationGuardの許可判定を整備し、事故防止の土台を作る段階である。\n\n"
        "## 実装済みコンポーネント一覧\n\n"
        "- Safety model: PortfolioState / BrokerState / ReconciliationResult / TradingLock / SafetyReport\n"
        "- Reconciliation: cash / buying power / positions / open orders の照合\n"
        "- HALT / TradingLock: HALT issueがあればlockを有効化\n"
        "- SafetyReport writer: `.runtime/safety/reports/`\n"
        "- TradingLock writer: `.runtime/safety/locks/`\n"
        "- Audit writer: `.runtime/safety/audit/`\n"
        "- Broker snapshot adapter: Phase2 snapshotからBrokerStateを構築\n"
        "- Safety dry-run: mock PortfolioStateと照合しreport/lock/auditを保存\n"
        "- Manual review flow: HALT時の人間確認手順\n"
        "- Manual unlock request / approval / audit\n"
        "- Manual unlock apply: approvalと最新OK report必須\n"
        "- OperationGuard: 最新lock stateを読んだ許可判定\n\n"
        "## Reconciliation / HALT / TradingLock / SafetyReport概要\n\n"
        "Broker状態を正とし、Portfolio状態との不一致を検出する。cash、buying power、position数量、未知position、"
        "open order不一致や重複疑いはHALTとして扱い、TradingLockを有効化する。SafetyReportは照合結果とlock状態を"
        "監査可能なJSONとして保存する。\n\n"
        "## Broker snapshot連携概要\n\n"
        "Phase2のbalance / positions / orders snapshotをBrokerStateへ変換するadapterを用意している。"
        "Phase3では実API接続は行わず、snapshot入力をdry-runの材料に限定する。\n\n"
        "## Dry-run概要\n\n"
        "`scripts/safety/run_safety_dry_run.py` はmock専用で、live modeや実API引数を持たない。"
        "実行結果としてstatus、issue_count、trading_locked、report/lock/audit pathを出力する。\n\n"
        "## Manual Review概要\n\n"
        "HALT時はSafetyReport、TradingLock、Audit、Broker snapshot、PortfolioStateを人間が確認する。"
        "不明な場合はHALTを維持し、修正は別作業として人間が実施する。\n\n"
        "## Manual Unlock概要\n\n"
        "unlock request / approval / auditを保存する。承認にはSafetyReport OK、承認者、理由、再照合結果が必要で、"
        "Phase3では自動復旧として扱わない。\n\n"
        "## Unlock Apply概要\n\n"
        "承認済みUnlockApprovalと最新OK SafetyReportがある場合だけ、解除適用状態を新しいJSONとして保存する。"
        "既存lockファイルは削除しない。\n\n"
        "## OperationGuard概要\n\n"
        "`.runtime/safety/locks/` の最新状態を正とする。最新TradingLockがlockedなら危険操作は禁止し、"
        "最新UnlockApplyResultがappliedならunlocked扱いにする。破損状態はfail-closedでlocked扱いにする。\n\n"
        "## 禁止事項遵守\n\n"
        "実API、live mode、発注、訂正、取消、AI連携、Portfolio自動更新、自動復旧はPhase3-H監査時点で追加していない。\n\n"
        "## Audit Checks\n\n"
        f"{check_lines}\n\n"
        "## pytest結果欄\n\n"
        f"確認コマンド: `{payload['pytest_hint']}`\n\n"
        "## Phase3完了判定\n\n"
        f"`{status_label}`\n\n"
        "## Phase4へ進む前の注意\n\n"
        "Phase4以降でAIや注文系に進む場合も、Phase3のOperationGuardとTradingLockを必ず前段に置く。"
        "実API接続や発注機能を作る場合は、別途live接続監査、秘密情報監査、発注禁止テストから始める。\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
