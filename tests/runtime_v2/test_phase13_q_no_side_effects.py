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
    "raw_request",
    "raw_response",
    "secret",
    "session",
    "account_id",
)

FORBIDDEN_CALL_NAMES = {
    "submit",
    "send",
    "unlink",
    "remove",
    "rmdir",
    "write_current_asset_state",
    "build_current_asset_state",
}


def test_broker_readonly_execution_do_not_import_side_effect_modules():
    for path in _phase_q_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not _matches_forbidden_import(alias.name), path
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not _matches_forbidden_import(node.module), path


def test_broker_readonly_execution_do_not_call_submit_or_asset_update_helpers():
    for path in _phase_q_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                assert _call_name(node.func) not in FORBIDDEN_CALL_NAMES, path


def test_broker_readonly_execution_do_not_reference_forbidden_text():
    for path in _phase_q_files():
        text = path.read_text(encoding="utf-8")
        text = text.replace("raw_response_origin", "")
        text = text.replace("private_secret_saved", "")
        text = text.replace("session_environment", "")
        text = text.replace("session_status", "")
        text = text.replace("session_pass", "")
        text = text.replace("target_session_date", "")
        text = text.replace("account_id_redacted", "")
        text = text.replace("account_identity_status", "")
        text = text.replace("account_identity_hash", "")
        text = text.replace("account_alignment_status", "")
        text = text.replace("broker_account_identity_unknown", "")
        text = text.replace("broker_account_alignment_review_required", "")
        for forbidden in FORBIDDEN_TEXT:
            assert forbidden not in text, f"{path} references {forbidden}"


def _phase_q_files():
    roots = (
        Path("src/ai_fund_lab_v2/runtime_v2/broker_readonly"),
        Path("src/ai_fund_lab_v2/runtime_v2/execution"),
    )
    files = []
    for root in roots:
        files.extend(sorted(root.rglob("*.py")))
    return files


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
