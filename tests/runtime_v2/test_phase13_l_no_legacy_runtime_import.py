from pathlib import Path


FORBIDDEN_IMPORT_SNIPPETS = (
    "from ai_fund_lab_v2.runtime ",
    "from ai_fund_lab_v2.runtime.",
    "import ai_fund_lab_v2.runtime",
    "from ai_fund_lab_v2.operations ",
    "import ai_fund_lab_v2.operations",
    "from ai_fund_lab_v2.broker ",
    "import ai_fund_lab_v2.broker",
)


def test_runtime_v2_does_not_import_legacy_workflow_or_entrypoint():
    runtime_v2_root = Path("src/ai_fund_lab_v2/runtime_v2")
    python_files = sorted(runtime_v2_root.rglob("*.py"))

    assert python_files
    for path in python_files:
        source = path.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_IMPORT_SNIPPETS:
            assert forbidden not in source, f"{path} contains {forbidden!r}"
