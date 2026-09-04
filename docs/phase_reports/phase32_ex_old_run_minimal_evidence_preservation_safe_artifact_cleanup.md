# Phase32-EX — Old Historical Run Minimal Evidence Preservation and Safe Artifact Cleanup

## Scope

- Target run: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Run id: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Profile: `historical-extended-smoke`
- Start date: `2022-10-03`
- Planned business days: `650`
- Initial cash: `1000000.0`
- Run lifecycle: abandoned after operator stop from prior HALT state.
- Mutation boundary: only the target run's `daily/` tree and root `.DS_Store` were deleted after preservation. No source, config, accepted generation, registry, current runtime state, Pending, or Ledger semantics were changed.

## Preserved Evidence

Permanent preservation directory:

`docs/phase_reports/phase32_ex_preserved_old_run_evidence/`

Preserved artifacts:

- `old_run_full_inventory_before_cleanup.csv`
  - Full pre-cleanup file/directory inventory.
  - Rows: `89754`
  - Includes `path`, `type`, `size_bytes`, `purpose`, and `classification`.
  - SHA-256: `8c39d70b388059ed562199439c037f8c01ad89c4dda76d792da270e46ea69aca`
- `old_run_daily_metrics.csv`
  - Daily summary for `2022-10-03` through `2025-01-09`.
  - Rows: `558` including header.
  - Preserves date/regime/equity/daily PnL/return/cash/exposure/position count and selected capitalization/history metrics.
  - SHA-256: `c6227e9d881cb979c24635a330cef7407bf2a6714ba26416e65e55cf1e61a564`
- `old_run_reentry_history_bias_minimal_evidence.json`
  - Minimal evidence for the pre-EW REENTRY long-lived history bias and run-age dependency.
  - SHA-256: `15b69b5ad1a80d7a12b2746a0356347262fd0edfbc91c4f4efa6b9a71775ddfd`
- `old_run_minimal_evidence_summary.json`
  - Machine-readable summary of run identity, period summaries, deletion scope, preserved paths, and before-cleanup size/count.
  - SHA-256: `6b16ad6ea4ab7f69e665fed67467e89f3c5a477f34bf5e67eba4cce42b98ed75`

Kept in the target run directory:

- `run_state.json`
- `plan.json`
- `historical_evaluation_authority.json`
- `fresh_run_summary.json`
- `final_summary.json`
- `abandonment.json`
- `strategy_shadow_manifest.json`
- `strategy_shadow_summary.json`
- `final_state_snapshot/`
- `recovery/`
- `source_transitions/`

These retained run-level artifacts preserve lifecycle/status, authority, final snapshot, recovery evidence, and source transition context.

## Inventory Classification

Pre-cleanup classification summary:

- `KEEP`: `123`
- `PRESERVE_SUMMARY`: `89629`
- `DELETE`: `1`

Classification policy:

- `KEEP`: small or canonical run-level evidence retained in place.
- `PRESERVE_SUMMARY`: large daily intermediate artifacts summarized into permanent EX evidence before deletion.
- `DELETE`: non-canonical filesystem metadata only.

The full classification is preserved in:

`docs/phase_reports/phase32_ex_preserved_old_run_evidence/old_run_full_inventory_before_cleanup.csv`

## Key Preserved Metrics

Daily coverage:

- First daily date: `2022-10-03`
- Last daily date: `2025-01-09`
- Daily date count: `557`

Period comparison preserved:

| Period | Days | Avg equity | Avg exposure | Avg cash | Avg PC capitalized members | Avg REENTRY suppressed | Avg old >120BD REENTRY suppressed | Avg elapsed seconds/day | Avg daily artifact size |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023 strong growth (`2023-03-01` to `2023-06-30`) | 84 | 1,450,135.48 | 0.87045 | 272,919.17 | 13.05 | 21.98 | 2.20 | 143.28 | 138,332,093 bytes |
| 2024 post-March (`2024-03-18` to `2024-12-31`) | 196 | 1,483,097.04 | 0.71213 | 864,688.14 | 8.91 | 37.02 | 16.71 | 264.86 | 231,195,838 bytes |
| 2024 late stagnation (`2024-07-01` to `2024-12-31`) | 125 | 1,460,416.96 | 0.69753 | 839,238.48 | 8.84 | 36.76 | 18.50 | 277.84 | 241,177,755 bytes |

REENTRY suppression age buckets preserved:

- `<=10`: `4283`
- `11-30`: `2265`
- `31-60`: `1638`
- `61-120`: `1979`
- `121-250`: `2846`
- `251-400`: `1582`
- `>400`: `735`

Top preserved REENTRY suppression reasons:

- `reentry_unknown_prior_context_independence_not_established`: `3505`
- `reentry_repeated_unresolved_churn`: `3349`
- `reentry_trend_recovery_not_satisfied`: `3248`
- `reentry_hard_stop_new_thesis_not_sufficient`: `2255`
- `reentry_entry_admission_not_allowed`: `1236`
- `reentry_recovery_qualified`: `711`
- `recoverable_prior_exit_context_defect`: `692`
- `reentry_momentum_recovery_not_satisfied`: `312`
- `reentry_capacity_unavailable`: `20`

These summaries preserve the minimum evidence needed to re-audit:

- 2023 strong-growth vs 2024 post-March stagnation.
- REENTRY long-lived history bias.
- run-age growth in daily artifact size.
- run-age growth in daily elapsed processing time.
- why Phase32-EW was needed before fresh validation.

## Deleted Paths

Deleted only after preservation and explicit user approval:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/daily`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z/.DS_Store`

Deleted categories:

- Regenerable daily intermediate runtime artifacts.
- Duplicated daily snapshots and repeated per-day evidence already summarized for EX.
- Non-canonical filesystem metadata.

No files outside the target run directory were deleted.

## Size And Count

- Size before: `100987275048` bytes (`94G` by `du -sh`)
- Size after: `185200166` bytes (`177M` by `du -sh`)
- Reclaimed size: `100802074882` bytes
- File count before: `70222`
- File count after: `86`
- Preserved EX summary artifact size: `21M`

Post-cleanup verification:

- `daily/` no longer exists.
- root `.DS_Store` no longer exists.
- run-level KEEP artifacts remain.
- final snapshot remains.
- recovery evidence remains.
- source transition evidence remains.
- permanent EX preservation artifacts remain.

## Future Audit Limitations

The individual raw daily artifact files for this old pre-EW run are no longer available in the target run directory. Future audits should use:

- the preserved full inventory CSV to identify what existed before cleanup;
- the preserved daily metrics CSV for date/regime/equity/PnL/return/cash/exposure/position/capitalization/history traces;
- the preserved REENTRY minimal evidence JSON for long-lived history bias and run-age dependency;
- retained run-level metadata, recovery evidence, source transition files, and final snapshot for canonical lifecycle context.

If a future audit requires arbitrary per-symbol nested details from an individual deleted daily artifact beyond the preserved summaries, that evidence would need to be regenerated from canonical inputs or a separate archived copy, if one exists.

## Confirmations

- PRESERVED_EVIDENCE_COMPLETE: YES
- OLD_RUN_DELETION_SAFE: YES
- PRODUCTION_STRATEGY_CHANGED: NO
- CONFIG_CHANGED: NO
- SCHEMA_CHANGED: NO
- ACCEPTED_GENERATION_CHANGED: NO
- CURRENT_RUNTIME_STATE_MUTATED: NO
- PENDING_SEMANTICS_CHANGED: NO
- LEDGER_SEMANTICS_CHANGED: NO
- FRESH_RUN_EXECUTED: NO
- RESUME_EXECUTED: NO
- REPLAY_EXECUTED: NO
- FUTURE_OUTCOME_USED_FOR_PRODUCTION_JUDGMENT: NO
- TARGET_RUN_MUTATED: YES, cleanup-only deletion of explicitly approved old-run artifacts.

## Final Judgment

`PHASE32_EX_OLD_RUN_MINIMAL_EVIDENCE_PRESERVED_SAFE_ARTIFACT_CLEANUP_COMPLETED_FRESH_VALIDATION_READY`
