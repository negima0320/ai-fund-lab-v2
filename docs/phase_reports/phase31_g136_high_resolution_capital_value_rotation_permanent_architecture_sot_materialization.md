# Phase31-G136 - High-Resolution Capital Value / Rotation Permanent Architecture SoT Materialization

## Final Decision

`G136_HIGH_RESOLUTION_CAPITAL_VALUE_ROTATION_PERMANENT_ARCHITECTURE_SOT_ACCEPTED`

G136 materialized the Phase31 G132-G135 capital value / rotation findings into
permanent architecture documentation under `docs/02_architecture/`.

This was a documentation / architecture-only task. No implementation, schema,
consumer, Strategy behavior, Runtime behavior, parameter, threshold, weight,
model, fresh-run, resume, replay, long Historical, or run mutation was
performed.

## Source Basis

Primary Phase31 evidence read and preserved:

- `docs/phase_reports/phase31_g135_high_resolution_marginal_value_portfolio_rotation_design_readiness_audit.md`
- `docs/phase_reports/phase31_g134_capital_value_resolution_loss_root_cause_localization_audit.md`
- `docs/phase_reports/phase31_g133_bull_internal_opportunity_quality_capital_allocation_behavior_audit.md`
- `docs/phase_reports/phase31_g132_unified_capital_frontier_decision_time_value_quality_characterization.md`
- `docs/phase_reports/phase31_g131_unified_add_new_cash_marginal_capital_authority_design_acceptance.md`
- `docs/phase_reports/phase31_g130_post_g129_buy_add_vs_buy_new_decision_time_capital_competition_audit.md`
- `docs/phase_reports/phase31_g129_buy_add_actual_path_narrow_repair.md`

Relevant prior G112-G128 reports and architecture SoT were inspected for ADD
marginal competition, BUY_ADD materialization, campaign lifecycle, PM action
ownership, PC/PS/Runtime boundaries, Market Quality / Risk Pacing, Cash, and
PIT safety.

## Files Created

- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/phase_reports/phase31_g136_high_resolution_capital_value_rotation_permanent_architecture_sot_materialization.md`

## Files Updated

- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`

## Authoritative SoT Location

Primary enduring contract:

```text
docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md
```

Phase reports remain provenance only. Future readers should not need to
reconstruct the architecture contract from G132-G135 reports.

## Cross-Reference Locations

Targeted cross-references were added to adjacent SoT files:

| File | Purpose |
| --- | --- |
| `portfolio_construction_and_position_sizing_contract.md` | PC ownership, current NEW/ADD/Cash baseline, future high-resolution value and HOLD rotation boundary |
| `dual_path_market_quality_and_capital_competition_contract.md` | Cash, Market Quality, Risk Pacing, and no Runtime redecision preservation |
| `strategy_architecture_v1.md` | Candidate AI / PM / PC boundary and no direct rotation sell authority |
| `strategy_intelligence_architecture_v1.md` | evidence-producer boundary and PIT / anti-leakage preservation |
| `momentum_follow_position_lifecycle_and_canonical_decision_architecture.md` | PM-owned HOLD / REDUCE / EXIT and anti-churn rotation boundary |
| `runtime_architecture_v2.md` | Runtime consume-only boundary |

## Contracts Added

Permanent SoT now documents two separated future capabilities:

1. `HIGH_RESOLUTION_MARGINAL_CAPITAL_VALUE`
2. `PORTFOLIO_WIDE_CAPITAL_ROTATION`

Key additions:

- Current system already performs NEW_BUY / BUY_ADD / Cash competition.
- Current limitation is resolution / semantics, not absence of competition.
- BULL amplifies a general capital value resolution limitation; it is not a
  BULL-specific bug.
- Candidate AI is not replaced.
- PM remains existing-position action authority.
- PC-owned Capital Value Authority is the recommended future owner of
  high-resolution next-executable-increment comparison.
- Cash remains first-class.
- Risk Pacing remains deployment intensity and must not become security ranking.
- Safety remains hard constraint authority.
- Position Sizing remains discrete quantity owner.
- Runtime must not re-decide ranking, Cash preference, target weight, quantity,
  or rotation.
- Existing HOLD capital is not merged into the current NEW_BUY / BUY_ADD / Cash
  execution frontier.
- Portfolio Rotation depends on High-Resolution Marginal Capital Value and must
  provide PM with external opportunity-cost evidence rather than directly
  selling securities.
- Future artifact placeholders are recorded as `NOT_IMPLEMENTED`:
  - `canonical_high_resolution_marginal_capital_value.v1`
  - `canonical_portfolio_rotation_opportunity_cost.v1`
- Initial future deployment should be `SHADOW_NON_AUTHORITATIVE`.
- Explicit non-goals prohibit fixed Top-N, fixed position count, mandatory full
  investment, unconditional ADD/NEW preference, BULL-specific multipliers,
  BEAR-specific suppression, Historical-return weighting, and automatic HOLD
  replacement.

## Conflicts Found / Resolved

No architecture conflict requiring repair was found.

The only boundary requiring explicit wording was the relationship between:

```text
current PC NEW_BUY / BUY_ADD / Cash capital competition
```

and:

```text
future portfolio-wide rotation of already deployed HOLD capital
```

Resolution:

- current PC competition remains valid and unchanged;
- existing HOLD capital remains incumbent allocated state;
- portfolio-wide rotation is documented as a future staged capability that
  depends on high-resolution marginal capital value and PM action authority.

## Implementation Deferred

The following were intentionally not implemented:

- `canonical_high_resolution_marginal_capital_value.v1`
- `canonical_portfolio_rotation_opportunity_cost.v1`
- any JSON schema;
- any producer;
- any consumer;
- any PS / Runtime binding;
- any PM rotation consumer;
- any Strategy threshold, weight, or model change.

## Future Sequencing Recorded

The permanent SoT records this future sequence:

1. High-Resolution Marginal Capital Value design.
2. `SHADOW_NON_AUTHORITATIVE` materialization.
3. Decision-time evidence validation and lineage validation.
4. Authoritative NEW_BUY / BUY_ADD / Cash integration only after acceptance.
5. Portfolio Rotation opportunity-cost design.
6. Shadow Portfolio Rotation evidence.
7. PM consumption design.
8. Authoritative rotation only after focused acceptance.

Phase31 was not advanced.

## Required Judgments

PERMANENT_ARCHITECTURE_SOT_MATERIALIZED = `YES`

HIGH_RESOLUTION_MARGINAL_VALUE_CONTRACT_DOCUMENTED = `YES`

PORTFOLIO_ROTATION_CONTRACT_DOCUMENTED = `YES`

CURRENT_VS_FUTURE_AUTHORITY_BOUNDARY_CLEAR = `YES`

BULL_LIMITATION_CORRECTLY_FRAMED_AS_GENERAL_RESOLUTION_LIMIT = `YES`

CANDIDATE_AI_REPLACEMENT_REQUIRED = `NO`

PM_ACTION_AUTHORITY_PRESERVED = `YES`

PC_CAPITAL_ALLOCATION_AUTHORITY_PRESERVED = `YES`

PS_QUANTITY_AUTHORITY_PRESERVED = `YES`

RUNTIME_REDECISION_PROHIBITED = `YES`

CASH_FIRST_CLASS_PRESERVED = `YES`

RISK_PACING_SEPARATION_PRESERVED = `YES`

PIT_ANTI_LEAKAGE_CONTRACT_PRESERVED = `YES`

IMPLEMENTATION_PERFORMED = `NO`

PHASE_ADVANCED = `NO`

## Validation

GIT_DIFF_CHECK = `PASS`

No code or config validation was required because G136 is architecture
documentation only.

## Next-Phase Design Entry Readiness

NEXT_PHASE_DESIGN_ENTRY_READY = `YES`

The next task may design `canonical_high_resolution_marginal_capital_value.v1`
as a shadow, non-authoritative capability. Portfolio Rotation should remain
deferred until high-resolution marginal capital value has design and
decision-time evidence validation.
