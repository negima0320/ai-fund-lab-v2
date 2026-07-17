import ast
from pathlib import Path


RUNTIME_ROOT = Path("src/ai_fund_lab_v2/runtime_v2")

FORBIDDEN_IMPORT_PREFIXES = (
    "ai_fund_lab_v2.runtime",
    "ai_fund_lab_v2.workflow",
    "ai_fund_lab_v2.entrypoint",
)

FORBIDDEN_IMPORT_EXACT = {
    "ai_fund_lab_v2.operations",
    "ai_fund_lab_v2.broker",
}

FORBIDDEN_TEXT_SNIPPETS = (
    "demo_ledger",
    "legacy resolver",
    "legacy_resolver",
    "legacy workflow",
    "legacy_workflow",
    "legacy submit",
    "legacy_submit",
)


def test_runtime_v2_has_no_legacy_runtime_imports():
    for path in sorted(RUNTIME_ROOT.rglob("*.py")):
        for imported in _extract_imports(path):
            assert not any(
                imported == prefix or imported.startswith(f"{prefix}.")
                for prefix in FORBIDDEN_IMPORT_PREFIXES
            ), f"{path} imports legacy dependency {imported}"
            assert imported not in FORBIDDEN_IMPORT_EXACT, f"{path} imports legacy dependency {imported}"


def test_runtime_v2_has_no_legacy_entrypoint_or_resolver_references():
    for path in sorted(RUNTIME_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for snippet in FORBIDDEN_TEXT_SNIPPETS:
            assert snippet not in lowered, f"{path} contains {snippet!r}"


def test_runtime_v2_does_not_reference_legacy_submit_or_report_paths():
    forbidden = (
        "legacy_submit",
        "legacy_report",
        "resolve_latest_order_plan",
        "resolve_current_from_date_dir",
        "resolve_current_from_phase_dir",
    )

    for path in sorted(RUNTIME_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        for snippet in forbidden:
            assert snippet not in source, f"{path} contains {snippet!r}"


def _extract_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports
