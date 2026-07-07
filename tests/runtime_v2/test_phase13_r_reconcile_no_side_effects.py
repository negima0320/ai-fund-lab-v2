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
    "write_current_asset_state",
    "write_pending_order_plan",
    "read_pending_order_plan",
)

FORBIDDEN_CALL_NAMES = {
    "submit",
    "send",
    "unlink",
    "remove",
    "rmdir",
}


def test_reconcile_runtime_does_not_import_side_effect_modules():
    for path in _reconcile_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not _matches_forbidden_import(alias.name), path
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not _matches_forbidden_import(node.module), path


def test_reconcile_runtime_does_not_call_side_effect_helpers():
    for path in _reconcile_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                assert _call_name(node.func) not in FORBIDDEN_CALL_NAMES, path


def test_reconcile_runtime_does_not_reference_current_or_asset_writers():
    for path in _reconcile_files():
        text = path.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_TEXT:
            assert forbidden not in text, f"{path} references {forbidden}"


def _reconcile_files():
    return sorted(Path("src/ai_fund_lab_v2/runtime_v2/reconcile").rglob("*.py"))


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
