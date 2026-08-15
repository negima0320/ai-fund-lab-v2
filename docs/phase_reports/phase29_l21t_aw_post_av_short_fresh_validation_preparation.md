# Phase29-L21T-AW — Post-AV Short Fresh Validation Preparation

## Task ID

Phase29-L21T-AW

## Primary Judgment

PHASE29_L21T_AW_POST_AV_SHORT_FRESH_VALIDATION_READY_READ_ONLY_PREPARATION_COMPLETE

Phase29 remains active. Phase30 was not entered.

## Scope

This is READ-ONLY / VALIDATION PREPARATION. Codex did not execute fresh-run,
resume, replay, recovery, or long Historical validation, and did not mutate
Runtime state.

## AV Implementation Presence

AV implementation report exists:

```text
docs/phase_reports/phase29_l21t_av_multi_horizon_momentum_trajectory_semantics_implementation.md
```

The implemented contract to validate is:

- `FADING_PRIOR_WINNER -> BUY_WAIT`
- `RECENT_ACCELERATION_OVERHEAT -> BUY_WAIT`
- `HEALTHY_CONTINUATION -> BUY_ELIGIBLE`
- `BUY_WAIT` creates no BUY Pending / Human Review Pending
- `BUY_WAIT` does not halt Runtime
- `BUY_WAIT` does not block SELL
- `BUY_WAIT` does not affect BUY_ADD / REENTRY / existing holdings

## Recommended Short Fresh Validation Window

Use 20 business days from `2022-08-10`.

Rationale:

- Covers the same calendar neighborhood where earlier Phase29 reports observed
  78780 / 53800-style momentum trajectory cases.
- Allows those symbols to be checked if they naturally recur in the post-AV
  actual runtime path.
- Remains a short validation window rather than long Historical

Old comparison run:

```text
runtime-test-historical-extended-smoke-20260814T054658313415Z
```

The old run's daily/runtime artifacts are deleted and are not an AW dependency.
AW does not require artifact-level comparison against this run. Earlier Phase29
AT / AS / AV reports may be used only as historical context; deleted runtime
artifacts must not be restored, regenerated, or inferred.

## User Fresh-Run Command

Codex must not run this command.

Do not add `--json`.

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2022-08-10 \
  --business-days 20 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Capture the printed `<NEW_RUN_ID>` for the inspection commands.

## Post-Run Read-Only Inspection Commands

Overview:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <NEW_RUN_ID> --scope overview
```

Performance / cash / exposure:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <NEW_RUN_ID> --scope performance
```

Positions and lifecycle:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <NEW_RUN_ID> --scope positions
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <NEW_RUN_ID> --scope lifecycle
```

Runner status:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run-status
```

BUY_WAIT / trajectory evidence scan:

```bash
RUN_ID=<NEW_RUN_ID> python3 - <<'PY'
import json
from collections import Counter, defaultdict
from pathlib import Path

run = Path("reports/runtime_tests/runs") / __import__("os").environ["RUN_ID"]
classes = Counter()
actions = Counter()
symbols = defaultdict(list)
pending_hits = []
runtime_states = Counter()

for path in run.rglob("*.json"):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        continue
    blob = json.dumps(data, ensure_ascii=False)
    if "momentum_trajectory_classification" in blob or "BUY_WAIT" in blob:
        def walk(obj):
            if isinstance(obj, dict):
                cls = obj.get("momentum_trajectory_classification")
                action = obj.get("quality_action") or obj.get("momentum_trajectory_action")
                sym = obj.get("symbol") or obj.get("security_code") or obj.get("code")
                date = obj.get("business_date") or obj.get("target_date") or obj.get("feature_date")
                if cls:
                    classes[str(cls)] += 1
                    if sym:
                        symbols[str(sym)].append((str(date), str(cls), str(action), str(path)))
                if action:
                    actions[str(action)] += 1
                for value in obj.values():
                    walk(value)
            elif isinstance(obj, list):
                for value in obj:
                    walk(value)
        walk(data)
    state = data.get("runtime_judgment") or data.get("final_judgment") or data.get("overall_status")
    if state:
        runtime_states[str(state)] += 1
    if "BUY_WAIT" in blob and ("pending" in str(path).lower() or "review" in blob):
        pending_hits.append(str(path))

print("trajectory_classes", dict(classes))
print("quality_actions", dict(actions))
for sym in ("78780", "53800"):
    print(sym, symbols.get(sym, []))
print("runtime_states", dict(runtime_states))
print("buy_wait_pending_or_review_paths", pending_hits[:20])
PY
```

SELL continuation scan:

```bash
RUN_ID=<NEW_RUN_ID> python3 - <<'PY'
import json
from collections import Counter
from pathlib import Path
import os

run = Path("reports/runtime_tests/runs") / os.environ["RUN_ID"]
sell = Counter()
for path in run.rglob("*.json"):
    if "sell" not in str(path).lower() and "planning" not in str(path).lower():
        continue
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        continue
    blob = json.dumps(data)
    if "SELL" in blob or "REDUCE" in blob or "EXIT" in blob or "NO_SIGNAL" in blob:
        if "NO_SIGNAL" in blob:
            sell["NO_SIGNAL"] += 1
        if "SELL" in blob:
            sell["SELL"] += 1
        if "REDUCE" in blob:
            sell["REDUCE"] += 1
        if "EXIT" in blob:
            sell["EXIT"] += 1
print(dict(sell))
PY
```

## Required Observation Points

Observe these fields in the new post-AV fresh run:

- BUY_NEW count
- BUY_WAIT count
- trajectory class counts
- Cash
- Gross Exposure
- Positions
- Pending existence / state
- Runtime Judgment
- SELL continuation evidence

## Symbol Checks

78780:

- If a comparable 78780 case naturally appears during the fresh validation
  window, it must not proceed as ordinary BUY_NEW solely on prior 20BD strength
  when 1BD / 3BD / 5BD trajectory is fading.
- Expected AV behavior: `FADING_PRIOR_WINNER -> BUY_WAIT`.
- Expected Pending behavior: no BUY Pending / Human Review Pending from WAIT.
- Absence of a comparable 78780 case is not a validation failure.

53800:

- If a comparable 53800 case naturally appears during the fresh validation
  window, it must not proceed as ordinary BUY_NEW when recent trajectory is
  fading.
- Expected AV behavior: `FADING_PRIOR_WINNER -> BUY_WAIT`.
- Expected Pending behavior: no BUY Pending / Human Review Pending from WAIT.
- Absence of a comparable 53800 case is not a validation failure.

HEALTHY_CONTINUATION:

- At least one `HEALTHY_CONTINUATION` candidate should remain BUY-eligible and
  continue through the existing BUY Quality / PC / PS / Safety chain when other
  authorities allow.
- No automatic boost is expected.

SELL Independence:

- SELL Planning should continue to produce `NO_SIGNAL`, `SELL`, `REDUCE`, or
  `EXIT` evidence independently of BUY_WAIT.
- BUY_WAIT must not create a batch-level Runtime halt.

## Acceptance

The short fresh validation is acceptable when:

- AV feature facts materialize in the actual Production-common fresh runtime
  path.
- Momentum trajectory classification reaches the actual BUY Quality / PC / PS
  path.
- `FADING_PRIOR_WINNER` and `RECENT_ACCELERATION_OVERHEAT` become BUY_WAIT when
  such cases naturally occur.
- `HEALTHY_CONTINUATION` remains BUY-eligible when other authorities pass.
- Cash, Exposure, BUY_NEW, and BUY_WAIT are observable.
- BUY_WAIT does not create Pending / Human Review Pending.
- Runtime does not halt solely because of BUY_WAIT.
- SELL evidence continues.
- BUY_ADD / REENTRY / existing holdings are not blocked by BUY_WAIT.

The validation does not require deleted old-run artifact comparison and does not
fail solely because 78780 / 53800 do not naturally recur in the short window.

## Runtime Mutation Statement

Codex did not mutate Runtime. The user fresh-run command is intentionally
operator-executed and mutating inside the isolated Runtime Test flow.

## Recommended Next Action

Operator runs the short fresh validation command, then provides `<NEW_RUN_ID>` so
Codex can perform read-only post-run inspection. If AW passes, proceed to
post-AV 4-year fresh Historical validation as a separate operator-owned task.
