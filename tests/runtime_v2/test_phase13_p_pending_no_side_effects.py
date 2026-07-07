import ast
from pathlib import Path


FORBIDDEN_IMPORT_PREFIXES = (
    "ai_fund_lab_v2.broker",
    "ai_fund_lab_v2.operations.notifications",
    "ai_fund_lab_v2.operations.operations",
    "ai_fund_lab_v2.operations.demo_ledger",
    "ai_fund_lab_v2.runtime",
)

FORBIDDEN_TEXT = (
    "launchctl",
    ".plist",
    "demo_ledger",
    "resolve_latest_order_plan",
    "resolve_current_from_date_dir",
    "resolve_current_from_phase_dir",
)

FORBIDDEN_CALL_NAMES = {
    "submit",
    "send",
    "unlink",
    "remove",
    "rmdir",
}


def test_pending_runtime_does_not_import_side_effect_modules():
    for path in _pending_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not _matches_forbidden_import(alias.name), path
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not _matches_forbidden_import(node.module), path


def test_pending_runtime_does_not_call_side_effect_helpers():
    for path in _pending_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                assert _call_name(node.func) not in FORBIDDEN_CALL_NAMES, path


def test_pending_runtime_does_not_reference_forbidden_fallback_or_scheduler_text():
    for path in _pending_files():
        text = path.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_TEXT:
            assert forbidden not in text, f"{path} references {forbidden}"


def _pending_files():
    return sorted(Path("src/ai_fund_lab_v2/runtime_v2/pending").rglob("*.py"))


def _matches_forbidden_import(module_name: str) -> bool:
    return any(
        module_name == prefix or module_name.startswith(f"{prefix}.")
        for prefix in FORBIDDEN_IMPORT_PREFIXES
    )


def _call_name(func) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""

