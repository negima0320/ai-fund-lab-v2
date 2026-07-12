# Phase15-BE Clean Acceptance Runtime Root Plan

## Summary

Classification:

```text
CLEAN_RUNTIME_ROOT_RECOMMENDED
```

The existing `.runtime` root should not be deleted or moved during BE. It contains valuable BB-BE evidence, retry manifests, and blocker diagnostics. However, Step1 Morning acceptance should preferably start from a clean acceptance runtime root after Broker authenticity and account alignment are resolved.

## Recommended Root

Recommended clean root:

```text
.runtime_acceptance_phase15
```

This root was not created in BE.

## Existing Runtime Handling

Do not delete or overwrite:

```text
.runtime
```

If archiving is needed later, use an explicit operator-approved move such as:

```text
.runtime -> .runtime_archive/phase15_pre_acceptance_<timestamp>
```

No archive action was performed in BE.

## Carry-In Policy

Allowed carry-in:

- Configuration files.
- Capital Deployment Policy.
- Immutable model artifacts.
- Canonical market data only after freshness verification.
- Credential references, without copying secrets.
- Explicit Current seed only if acceptance continuity requires it and the account alignment contract is satisfied.

Excluded carry-in:

- Old Pending slot state.
- Old run manifests.
- Old Safety decisions.
- Old Data Readiness artifacts.
- Old Broker snapshots.
- Stale valuation evidence.
- Retry-only temporary artifacts.

## Current Seed Decision

Do not silently carry the existing Runtime Current into a clean acceptance root while Broker account alignment is mismatched.

Two acceptable future paths:

1. Fresh lifecycle: initialize an explicit empty / seed Current state and prove Broker account alignment for that account.
2. Continuity lifecycle: migrate the current five positions through an approved, account-aligned Current seed contract.

## Next Action

Resolve Broker authenticity and account alignment first. After that, initialize the clean root and re-run Step0 evidence before Step1 Morning.
