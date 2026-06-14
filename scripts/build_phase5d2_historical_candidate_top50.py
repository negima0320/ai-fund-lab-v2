#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.opportunity_ai.historical_candidates import build_historical_candidate_top50  # noqa: E402

PHASE4BF_SUMMARY = Path("reports/candidate_ai/full_range/phase4bf_formal_lightgbm_training_summary.json")
PHASE4BC_SUMMARY = Path("reports/candidate_ai/full_range/phase4bc_long_history_feature_regeneration_summary.json")
PHASE4BD_SUMMARY = Path("reports/candidate_ai/full_range/phase4bd_long_history_label_regeneration_summary.json")
DEFAULT_OUTPUT_DIR = Path("reports/opportunity_ai/phase5d2")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Phase5-D2 historical Candidate Top50 snapshots.")
    parser.add_argument("--model-path", default=None)
    parser.add_argument("--feature-path", default=None)
    parser.add_argument("--label-path", default=None)
    parser.add_argument("--phase4bf-summary", default=str(PHASE4BF_SUMMARY))
    parser.add_argument("--phase4bc-summary", default=str(PHASE4BC_SUMMARY))
    parser.add_argument("--phase4bd-summary", default=str(PHASE4BD_SUMMARY))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--frequency", choices=("monthly", "weekly", "all"), default="monthly")
    parser.add_argument("--top-n", type=int, default=50)
    parser.add_argument("--max-dates", type=int, default=None)
    args = parser.parse_args(argv)

    bf = _read_json(Path(args.phase4bf_summary))
    bc = _read_json(Path(args.phase4bc_summary))
    bd = _read_json(Path(args.phase4bd_summary))
    summary = build_historical_candidate_top50(
        model_path=Path(args.model_path or bf.get("model_artifact_path") or ""),
        feature_path=Path(args.feature_path or bc.get("feature_output_path") or ""),
        label_path=Path(args.label_path or bd.get("label_output_path") or ""),
        output_dir=Path(args.output_dir),
        frequency=args.frequency,
        top_n=args.top_n,
        max_dates=args.max_dates,
    )
    summary["frequency"] = args.frequency
    summary["top_n"] = args.top_n
    summary_path = Path(summary["summary_path"])
    summary_path.write_text(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
