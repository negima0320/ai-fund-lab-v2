from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"


def test_phase23_bi_portfolio_construction_imports_with_pythonpath_src_only() -> None:
    result = _run_pythonpath_src(
        "from ai_fund_lab_v2.strategy import portfolio_construction; "
        "print(portfolio_construction.build_portfolio_construction_payload.__name__)"
    )

    assert result.returncode == 0, result.stderr
    assert "build_portfolio_construction_payload" in result.stdout


def test_phase23_bi_opportunity_eligibility_import_does_not_load_producer_or_scripts() -> None:
    code = """
import sys
from ai_fund_lab_v2.runtime_v2.buy_ai.opportunity_eligibility import opportunity_no_buy_reason_blocks_buy
assert opportunity_no_buy_reason_blocks_buy("high_downside_risk_score") is True
assert "ai_fund_lab_v2.runtime_v2.buy_ai.producer" not in sys.modules
assert "scripts.run_phase4bg_formal_candidate_inference" not in sys.modules
print("ok")
"""
    result = _run_pythonpath_src(code)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_phase23_bi_buy_ai_producer_has_no_repository_scripts_dependency() -> None:
    producer_source = (SRC / "ai_fund_lab_v2/runtime_v2/buy_ai/producer.py").read_text(encoding="utf-8")

    assert "from scripts." not in producer_source
    assert "import scripts." not in producer_source


def test_phase23_bi_buy_ai_producer_imports_with_pythonpath_src_only() -> None:
    result = _run_pythonpath_src(
        "from ai_fund_lab_v2.runtime_v2.buy_ai import produce_buy_ai_decisions; "
        "print(produce_buy_ai_decisions.__name__)"
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "produce_buy_ai_decisions"


def test_phase23_bi_formal_candidate_script_uses_src_canonical_helpers() -> None:
    import ai_fund_lab_v2.candidate_ai.formal_inference as canonical
    import scripts.run_phase4bg_formal_candidate_inference as script

    assert script.audit_inference_features is canonical.audit_inference_features
    assert script.build_scored_candidates is canonical.build_scored_candidates
    assert script.validate_candidate_output is canonical.validate_candidate_output


def test_phase23_bi_runtime_test_help_imports_with_pythonpath_src() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    env["PYTHONPYCACHEPREFIX"] = "/private/tmp/pycache_phase23_bi"
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/runtime_test.py"), "--help"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "fresh-run" in result.stdout


def _run_pythonpath_src(code: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    env["PYTHONPYCACHEPREFIX"] = "/private/tmp/pycache_phase23_bi"
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd="/private/tmp",
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )
