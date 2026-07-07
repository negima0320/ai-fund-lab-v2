import ast
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.orchestrator.models import RuntimeRunRequest
from ai_fund_lab_v2.runtime_v2.orchestrator.orchestrator import RuntimeOrchestrator


FORBIDDEN_IMPORT_PREFIXES = (
    "ai_fund_lab_v2.broker",
    "ai_fund_lab_v2.operations.notifications",
    "ai_fund_lab_v2.operations.operations",
    "ai_fund_lab_v2.operations.market_refresh",
    "ai_fund_lab_v2.runtime",
)

FORBIDDEN_CALL_NAMES = {
    "submit",
    "send",
    "unlink",
    "remove",
    "rmdir",
}


def test_orchestrator_does_not_import_side_effect_modules():
    tree = _orchestrator_ast()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not _matches_forbidden_import(alias.name)
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not _matches_forbidden_import(node.module)


def test_orchestrator_does_not_call_submit_send_launchd_plist_or_delete_helpers():
    tree = _orchestrator_ast()

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _call_name(node.func)
            assert name not in FORBIDDEN_CALL_NAMES
            assert "launchctl" not in name
            assert "plist" not in name


def test_run_preflight_reports_no_side_effects(tmp_path):
    result = RuntimeOrchestrator(base_dir=tmp_path).run_preflight(
        RuntimeRunRequest(
            mode="demo",
            environment="demo",
            business_date="2026-07-07",
        )
    )

    assert result.side_effect_executed is False


def _orchestrator_ast():
    source = Path(
        "src/ai_fund_lab_v2/runtime_v2/orchestrator/orchestrator.py"
    ).read_text(encoding="utf-8")
    return ast.parse(source)


def _call_name(func) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _matches_forbidden_import(module_name: str) -> bool:
    return any(
        module_name == prefix or module_name.startswith(f"{prefix}.")
        for prefix in FORBIDDEN_IMPORT_PREFIXES
    )
