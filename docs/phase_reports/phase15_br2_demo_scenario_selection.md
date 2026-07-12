# Phase15-BR2 Fresh Demo Scenario Selection

## Summary

Phase15-BR2 selected a fresh Demo Broker Write Acceptance scenario using only Phase15-BQ-R2 Fresh Broker Evidence.

Final judgment:

```text
DEMO_SCENARIO_SELECTED_WITH_CONDITIONS
```

Selected scenario:

| Field | Value |
| --- | --- |
| Side | `SELL` |
| Issue Code | `6501` |
| Quantity candidate | `100` |
| Position origin | `DEMO_PRELOADED_POSITION` |
| Runtime-owned | `false` |
| Acceptance-only | `true` |
| Production equivalent | `false` |
| Order type | `MARKET` |
| Price condition | `MARKET` |
| Limit price | `null` |
| Time in force | `DAY` |
| Target session | `2026-07-13` |

This is a scenario selection only. It is not user authorization, not Human Approval, not Pending generation, not Submit, and not Broker Write.

## Read Documents

- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/02_architecture/runtime_submit_order_condition_authority_contract.md`
- `docs/phase_reports/phase15_bq_r2_demo_environment_reinitialization.md`
- `docs/phase_reports/phase15_bo_isolated_normal_submit_acceptance_simulation.md`
- `docs/phase_reports/phase15_bp_explicit_demo_broker_write_review.md`
- `src/ai_fund_lab_v2/runtime_v2/broker_adapter/capability.py`

## Safety Boundary

| Action | Result |
| --- | --- |
| Broker Write | Not performed |
| Submit | Not executed |
| Execution processing | Not performed |
| Current Apply | Not performed |
| Notification Send | Not performed |
| Existing `.runtime` mutation | Not performed |
| Previous `6522` scenario reuse | Not performed |
| Human Approval artifact generation | Not performed |
| Pending generation | Not performed |
| Request Hash generation | Not performed |
| User Authorization artifact generation | Not performed |

## Fresh Broker Evidence

Source of Truth:

```text
.runtime_acceptance_phase15_demo_reinit
```

Evidence:

```text
reports/phase_reports/phase15_bq_r2/broker_environment_inventory.json
.runtime_acceptance_phase15_demo_reinit/runtime_state/broker_readonly/2026-07-13/tachibana_snapshot.json
.runtime_acceptance_phase15_demo_reinit/runtime_state/broker_readonly/2026-07-13/snapshot_report.json
.runtime_acceptance_phase15_demo_reinit/runtime_state/run_manifest/2026-07-13/runtime-v2-broker_readonly_refresh-2026-07-13-20260711T234421.772078+0000.json
reports/phase_reports/phase15_br2/scenario_selection_evidence.json
```

| Field | Value |
| --- | --- |
| Data origin | `BROKER_API` |
| Fixture used | `false` |
| Mock used | `false` |
| Snapshot status | `PASS_WITH_WARNINGS` |
| Refresh status | `READY` |
| Snapshot generated_at | `2026-07-11T23:44:24.193132+00:00` |
| Business date | `2026-07-13` |
| Open orders | `0` |
| Executions | `0` |
| Cash available | `18,070,600 JPY` |
| Buying power | `20,000,000 JPY` |

## BUY / SELL Comparison

| View | SELL | BUY |
| --- | --- | --- |
| Selection | `PREFERRED` | `DEFERRED` |
| Existing Acceptance continuity | Continues the Phase15 SELL Review / Approval / Pending / Submit chain. | Requires a fresh explicit BUY acceptance fixture or user-chosen issue. |
| Account impact | Decreases a demo preloaded position. | Increases exposure and consumes buying power. |
| Guard value | Validates available quantity and open order guards with Fresh Broker Evidence. | Validates buying power, exposure, and position-limit guards, but fresh policy/safety inputs are not generated in BR2. |
| Fill / Current verification | Existing positive cash position can be checked after execution if later authorized. | Requires issue selection, BUY safety permission, exposure policy, and target issue fixture. |
| Production equivalence | Demo-only exception, `production_equivalent=false`. | Not selected in BR2. |

BUY was not selected because Codex must not choose a BUY issue as an investment decision, and BR2 does not generate fresh BUY Safety, Exposure Policy, Position Limit, or explicit BUY acceptance fixture evidence.

## SELL Candidate Comparison

| Issue Code | Quantity | Available | Market Value | Estimated Unit Price | Quantity Candidate | Estimated Notional | Result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `6501` | `200` | `200` | `940,000 JPY` | `4,700 JPY` | `100` | `470,000 JPY` | `SELECTED` |
| `6502` | `2000` | `2000` | `0 JPY` | `0 JPY` | `100` | `0 JPY` | `NOT_SELECTED` |
| `9984` | `400` | `400` | `2,548,000 JPY` | `6,370 JPY` | `100` | `637,000 JPY` | `NOT_SELECTED` |

Selection reason:

```text
6501 has positive market value evidence, available quantity 200, open orders 0,
and the smallest positive estimated account impact among valid SELL candidates.
```

This is not an investment judgment or price forecast.

## Position Origin

The selected position is:

```text
DEMO_PRELOADED_POSITION
runtime_owned=false
acceptance_only=true
production_equivalent=false
```

This is a Demo-only Acceptance exception. It must not be promoted into a Production rule.

## Quantity Candidate

Selected candidate:

```text
100 shares
```

Evidence:

- Fresh available quantity for `6501` is `200`.
- Fresh open orders count is `0`.
- Candidate quantity is below available quantity.
- Final quantity still requires Human Approval and User Authorization.

## Order Conditions

Candidate order conditions:

| Field | Value |
| --- | --- |
| `order_type` | `MARKET` |
| `price_condition` | `MARKET` |
| `limit_price` | `null` |
| `time_in_force` | `DAY` |
| `target_session` | `2026-07-13` |

Under the Runtime Submit Order Condition Authority Contract, these are candidate conditions only. Submit Runtime must not infer or default them. They must be explicitly approved and frozen into Authoritative Pending in the next phase before any Submit path can be considered.

## Target Session

| Field | Value |
| --- | --- |
| Runtime business date | `2026-07-13` |
| Target session | `2026-07-13` |
| Market open status in BQ-R2 manifest | `true` |
| Open orders | `0` |
| Past session reuse | Rejected |

Before any Request Review or User Authorization, the target session and broker send window must be revalidated using fresh evidence.

## Demo Account Impact

If fully filled:

- `6501` demo preloaded cash position decreases from `200` shares to `100` shares.
- Estimated notional is `470,000 JPY` based on Fresh Broker Evidence market value divided by quantity.
- Cash or buying power may increase after broker/account update, but exact accounting must be confirmed from fresh post-submit ReadOnly evidence.

Residual risks:

- Market order fill is not guaranteed in the acceptance window.
- Partial fill or unfilled order may require explicit cancel/reconcile policy.
- The selected position is not Runtime-owned and is not Production-equivalent.

## Fresh Acceptance Chain Plan

For Phase15-BS and later:

1. Fresh Safety Decision for `target_session=2026-07-13`.
2. Human Approval Candidate for `SELL 6501`, quantity, and exact order conditions.
3. Promotion Candidate from approved review into submit scope.
4. Apply Candidate for Authoritative Submit Pending.
5. Authoritative Pending with exact approved conditions.
6. No-send Submit Preflight.
7. Request Hash.
8. User Authorization.

Broker Write remains blocked until explicit user authorization is present in the correct phase.

## User Authorization Items

The final authorization prompt must include:

- Demo environment confirmation.
- Issue code `6501`.
- Side `SELL`.
- Quantity.
- Order type `MARKET`.
- Price condition `MARKET`.
- Time in force `DAY`.
- Target session `2026-07-13`.
- Demo account impact.
- Unfilled order policy.
- Partial fill policy.
- Execution confirmation method.
- Explicit Broker Write authorization.

## Regression

| Check | Result |
| --- | --- |
| Previous scenario not reused | `PASS` |
| Fresh Broker Evidence only | `PASS` |
| Demo preloaded classification maintained | `PASS` |
| BUY and SELL both compared | `PASS` |
| Open order conflict checked | `PASS` |
| Quantity overage rejected | `PASS` |
| Past session rejected | `PASS` |
| Broker capability prechecked | `PASS_WITH_CONDITION_FORMAL_ARTIFACT_REQUIRED` |
| User Authorizationなしでsend不可 | `PASS` |
| Broker Writeなし | `PASS` |

Regression command:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase15br2_demo_scenario_selection.py
```

## Remaining Conditions

- Fresh Safety / Approval / Pending / No-send Submit Preflight / Request Hash / User Authorization are not generated in BR2.
- Broker capability must be materialized as fresh evidence before any send.
- Target session and broker send window must be revalidated before Request Review and User Authorization.
- Demo preloaded position exception must not be applied to Production.

## Final Judgment

```text
DEMO_SCENARIO_SELECTED_WITH_CONDITIONS
```

## Next Prefix

```text
Phase15-BS Demo Broker Write Preconditions Finalization
```
