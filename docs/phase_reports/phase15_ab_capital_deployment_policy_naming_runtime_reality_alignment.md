# Phase15-AB Capital Deployment Policy Naming / Runtime Reality Alignment

Date: 2026-07-10

## Objective

Phase15-AB aligns Capital Deployment Policy naming and references with the Phase15-X Runtime Reality Rule before continuing Demo Runtime Acceptance.

This phase does not run Demo Runtime, Morning, Submit, Execution, Broker Write, orders, notification real send, launchd/plist changes, Current edits, or Runtime bypasses.

## Why This Was Needed

Phase15-X defined:

```text
Runtimeは常にProduction Realityを基準として設計する。

Demo環境の制約はRuntime仕様ではなく、
Broker Environment / Broker Capability / Broker Evidenceとして扱う。

Demo専用Runtime、Phase専用Runtime、Fake Runtime、
Demo専用Current、Demo専用Ledger、Demo専用Policyは作らない。
```

The existing policy path:

```text
configs/runtime_v2/capital_deployment_demo.json
```

looked like a Demo-only Policy. Static review showed that its content is not actually Demo-specific. It is a general Capital Deployment Contract that was named with `demo` during earlier implementation.

To avoid violating or confusing the Runtime Reality Rule, Acceptance policy references now use a production-baseline name.

## Policy Path Change

Old path:

```text
configs/runtime_v2/capital_deployment_demo.json
```

New Acceptance path:

```text
configs/runtime_v2/capital_deployment.json
```

The new file contains the same policy contract values, with `policy_source` updated:

```json
"policy_source": "configs/runtime_v2/capital_deployment.json"
```

## Old File Handling

`configs/runtime_v2/capital_deployment_demo.json` remains for historical/backward compatibility only.

Classification:

```text
DEPRECATED_COMPATIBILITY_FILE
```

Acceptance rule:

```text
Do not use configs/runtime_v2/capital_deployment_demo.json for Runtime Acceptance.
```

Runtime Acceptance must use:

```text
configs/runtime_v2/capital_deployment.json
```

## Reference Updates

Updated normal Acceptance references:

| File | Action |
|---|---|
| `docs/phase_reports/phase15_u_demo_runtime_review_plan.md` | Replaced normal policy path with `configs/runtime_v2/capital_deployment.json`. |
| `docs/phase_reports/phase15_v_purpose_level_runtime_acceptance_meta_review.md` | Replaced normal policy path with `configs/runtime_v2/capital_deployment.json`. |

No Runtime Core code was changed to assume a Demo-only Policy.

## Static Scan Result

Command equivalent:

```bash
rg -n "capital_deployment_demo\\.json" configs src tests docs
```

| Finding | Classification | Action |
|---|---|---|
| `configs/runtime_v2/capital_deployment_demo.json` | OK_IF_DOCUMENTED | Kept as deprecated compatibility file; do not use for Runtime Acceptance. |
| `tests/runtime_v2/test_phase15ab_capital_deployment_policy_naming.py` | OK_TEST_ASSERTION | Test constant verifies old path is not used by Runtime Core or Acceptance docs. |
| `docs/phase_reports/phase15_h_capital_deployment_policy_implementation.md` | OK_HISTORY | Historical Phase15-H report; left unchanged as original implementation history. |

No `capital_deployment_demo.json` reference remains in the Phase15-U/V/W/X/Y/AA Acceptance normal-use docs.

## Regression

Added:

```text
tests/runtime_v2/test_phase15ab_capital_deployment_policy_naming.py
```

Coverage:

- New policy loads through `load_capital_deployment_policy`.
- Loaded `policy_source` is `configs/runtime_v2/capital_deployment.json`.
- Acceptance docs do not use `capital_deployment_demo.json` as normal policy.
- Runtime Core / existing Runtime v2 tests do not hardcode the old Demo policy path.

Executed:

```text
python3 -m pytest -q tests/runtime_v2/test_phase15ab_capital_deployment_policy_naming.py
python3 -m pytest -q tests/runtime_v2/test_phase15h_capital_deployment_policy.py
python3 -m json.tool configs/runtime_v2/capital_deployment.json
```

Results:

```text
3 passed
5 passed
JSON valid
```

## Acceptance Impact

Phase15-AA found a Policy Evidence gap because no active Phase15 Acceptance policy path was established in the Runtime root at that time.

Phase15-AB resolves the naming and canonical Acceptance path portion of that gap:

```text
configs/runtime_v2/capital_deployment.json
```

This does not by itself make Step0 PASS. Step0 still requires operator evidence that this policy is the active policy for the target Acceptance run and that its source/version/hash appear in Runtime evidence.

## Prohibited Actions Confirmation

This phase did not perform:

- Demo Runtime execution
- Broker Write
- Demo order
- Production order
- Notification real send
- launchd/plist change
- Current edit
- Runtime bypass creation
- Demo-only Policy creation
- Phase-only Policy creation

## Final Judgment

```text
PHASE15AB_CAPITAL_DEPLOYMENT_POLICY_NAMING_RUNTIME_REALITY_ALIGNMENT_COMPLETE
```
