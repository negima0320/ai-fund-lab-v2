from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.broker.moomoo.readonly_methods import MOOMOO_READ_ONLY_METHODS

PHASE8C_SOURCE_PATHS = (
    REPO_ROOT / "src" / "ai_fund_lab_v2" / "broker" / "moomoo",
    REPO_ROOT / "scripts" / "smoke_moomoo_readonly_phase8c.py",
)

EXPECTED_READ_ONLY_METHODS = frozenset(
    {
        "get_acc_list",
        "accinfo_query",
        "position_list_query",
        "order_list_query",
        "history_order_list_query",
    }
)


def _forbidden_tokens() -> tuple[str, ...]:
    return (
        "place" + "_order",
        "place" + "_combo" + "_order",
        "modify" + "_order",
        "cancel" + "_order",
        "unlock" + "_trade",
        "Open" + "Sec" + "Trade" + "Context",
        "Open" + "Future" + "Trade" + "Context",
        "f" + "utu",
        "CLM" + "ID",
        "Tachi" + "bana",
    )


def run_audit() -> dict[str, object]:
    source_files = list(_iter_source_files(PHASE8C_SOURCE_PATHS))
    forbidden_hits = _find_tokens(source_files, _forbidden_tokens())
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in source_files)
    checks = {
        "phase8c_source_files_present": bool(source_files),
        "read_only_methods_exact": MOOMOO_READ_ONLY_METHODS == EXPECTED_READ_ONLY_METHODS,
        "forbidden_tokens_absent": not forbidden_hits,
        "no_raw_payload_writer_name": "raw_payload.write" not in source_text and "raw_payload_path" not in source_text,
        "smoke_script_requires_explicit_flag": "--run-readonly-smoke" in (REPO_ROOT / "scripts" / "smoke_moomoo_readonly_phase8c.py").read_text(
            encoding="utf-8"
        ),
        "smoke_script_requires_env_gate": "AI_FUND_LAB_MOOMOO_READONLY_SMOKE" in (
            REPO_ROOT / "scripts" / "smoke_moomoo_readonly_phase8c.py"
        ).read_text(encoding="utf-8"),
    }
    passed = all(checks.values())
    return {
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "forbidden_hits": forbidden_hits,
        "source_files": [str(path.relative_to(REPO_ROOT)) for path in source_files],
    }


def _iter_source_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            yield path
        elif path.is_dir():
            yield from sorted(child for child in path.rglob("*.py") if child.is_file())


def _find_tokens(files: list[Path], tokens: tuple[str, ...]) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        found = [token for token in tokens if _contains_token(text, token)]
        if found:
            hits[str(path.relative_to(REPO_ROOT))] = found
    return hits


def _contains_token(text: str, token: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])", text) is not None


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
