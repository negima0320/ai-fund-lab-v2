# Phase31-G131 — Unified ADD / NEW_BUY / Cash Marginal Capital Authority Design Acceptance

## Final Decision

`G131_UNIFIED_ADD_NEW_CASH_CAPITAL_AUTHORITY_DESIGN_CONFIRMED_NO_REPAIR`

## Scope

Task type: READ-ONLY DESIGN / CONTRACT ACCEPTANCE AUDIT.

No code, config, threshold, weight, model, fresh-run, resume, replay, long Historical, or run mutation was performed.

G131 decides the intended contract only. It does not judge ADD decisions from later return or old-run performance.

## Source Basis

Read first:

- `docs/phase_reports/phase31_g130_post_g129_buy_add_vs_buy_new_decision_time_capital_competition_audit.md`
- `docs/phase_reports/phase31_g129_buy_add_actual_path_narrow_repair.md`
- `docs/phase_reports/phase31_g115_add_marginal_competition_staged_authoritative_binding.md`
- `docs/phase_reports/phase31_g114_add_marginal_competition_authoritative_binding_design_review.md`
- `docs/phase_reports/phase31_g113_add_marginal_capital_competition_shadow_implementation.md`
- `docs/phase_reports/phase31_g112_repeated_add_marginal_capital_competition_contract_audit.md`

Architecture SoT inspected:

- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/runtime_architecture_v2.md`

Current implementation inspected read-only:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`

## Executive Conclusion

Current architecture requires a unified marginal capital frontier containing `NEW_BUY`, `BUY_ADD`, eligible re-entry-as-NEW_BUY, Cash, and residual optionality. However, it does not require a strict single-winner rule where every positive security increment must prove it absolutely beats Cash.

The permanent Phase31 architecture is hybrid multi-allocation:

```text
Portfolio Policy budget envelope
-> Portfolio Construction unified security/Cash frontier
-> PC participation-vs-deferral resolution
-> multiple security allocations plus explicit Cash may coexist
-> Position Sizing discrete quantity
-> Runtime consumer only
```

Therefore G130's finding that many ADD fills used:

```text
CASH_PREFERRED_PARTICIPATION_VALID_IS_NOT_ADD_BEATS_CASH
```

is not by itself a repair-triggering architecture mismatch. It means those increments were authorized by the intended reduced/shoulder participation contract, not by an explicit "ADD beats Cash" dominance proof.

## Investment Philosophy Contract

CASH_IS_FIRST_CLASS_INVESTMENT_ALTERNATIVE = `YES`

Documentary basis:

- `dual_path_market_quality_and_capital_competition_contract.md` defines canonical competitors as `NEW_BUY`, `ADD`, and `CASH / OPTIONALITY`.
- It states Cash remains valid when deployment is not justified or safely executable.
- It states Cash may win before candidate failure.
- `portfolio_construction_and_position_sizing_contract.md` states Cash is a first-class competitor and `CASH_PREFERRED_PARTICIPATION_VALID` is not equivalent to `ADD_MARGINAL_CAPITAL_BEATS_CASH`.

ADD_AND_NEW_ARE_PEERS_IN_CAPITAL_COMPETITION = `YES`

Documentary basis:

- The dual-path SoT states ADD participates in the same capital competition as NEW_BUY and Cash.
- Neither ADD nor NEW_BUY has automatic priority.
- G115 preserves PM as ADD intent owner and PC as ADD marginal frontier owner.

NEXT_LOT_MUST_BEAT_CASH_TO_BE_AUTHORIZED = `PARTIAL`

Strictly preferred ADD increments must beat Cash. But `COMPARABLE_MARGINAL` may receive controlled residual/shoulder participation when the PC participation-vs-deferral resolver authorizes reduced security allocation while preserving Cash as a coexisting allocation.

PARTICIPATION_SHOULDER_ALLOWED_WHEN_CASH_PREFERRED = `YES`

Documentary basis:

- G114 defines `COMPARABLE_MARGINAL` as conditional residual/shoulder participation.
- G115 acceptance explicitly records `COMPARABLE_MARGINAL_RESIDUAL_SHOULDER_PARTICIPATION = YES`.
- Phase31-G81/G86/G90 SoT states `CASH_PREFERRED` passes through PC participation-vs-deferral resolution, where `CASH_PREFERRED_PARTICIPATION_VALID` may preserve reduced security allocation with explicit lineage.

## Unified Frontier Requirement

UNIFIED_ADD_NEW_CASH_MARGINAL_FRONTIER_REQUIRED = `YES`

Invariant:

For every incremental allocation, Portfolio Construction must evaluate eligible security increments and Cash / residual optionality in one canonical PC-owned frontier. The selected security increment must not bypass superior same-date security increments or a terminal Cash-defer decision.

Refined invariant, matching current SoT:

```text
If classification = ADD_MARGINAL_PREFERRED:
  next ADD increment is the preferred marginal security/Cash use for one executable lot.

If classification = COMPARABLE_MARGINAL:
  one executable increment may be authorized only through PC's reduced/residual
  participation shoulder, with Cash preserved as first-class residual /
  co-allocation and recomputation required before another increment.

If classification = CASH_MARGINAL_PREFERRED / CASH_PREFERRED_DEFER:
  the security increment must not be authorized.
```

Do not add a numerical Cash score, performance-fitted threshold, or fixed exposure rule.

## G115 Participation Shoulder Intent

G115_PARTICIPATION_SHOULDER_DESIGN_STATUS = `PERMANENT`

Evidence:

- G114 says `COMPARABLE_MARGINAL` is non-terminal and may receive controlled residual / shoulder participation.
- G114 says the authoritative binding should be staged and that comparable marginal increments may participate only after strictly preferred alternatives and Cash semantics are respected.
- G115 implemented and accepted `COMPARABLE_MARGINAL_RESIDUAL_SHOULDER_PARTICIPATION = YES`.
- SoT section "Phase31-G115 ADD Marginal Capital Competition Authority" now records that `COMPARABLE_MARGINAL` may receive residual/shoulder participation through the same staged one-increment boundary.

It is staged, but not merely temporary. "Staged" means one executable increment at a time with recomputation, not "temporary until strict Cash dominance exists."

## Meaning of Cash Preferred

CASH_PREFERRED_SEMANTICS = `COMPOSITE`

Current meaning:

`CASH_PREFERRED` does not mean only "Cash has higher expected alpha." It is a composite PC interaction result derived from Market Quality / Risk Pacing, opportunity quality, evidence completeness, portfolio state, exposure, Cash optionality, lot/residual feasibility, and same-date competitor context.

Specific terms:

| Term | Meaning |
| --- | --- |
| `CASH_PREFERRED` | Cash / optionality is favored by the market-candidate-cash interaction, but final action still requires PC participation-vs-deferral resolution after G81/G86. |
| `CASH_PREFERRED_PARTICIPATION_VALID` | Reduced security participation is valid with explicit lineage while Cash remains a first-class co-allocation/residual destination. It is not proof that the security increment strictly beats Cash. |
| `SECURITY_PREFERRED` | Security deployment is preferred by the current interaction/frontier. It may support stronger security allocation subject to PC/PS/Safety constraints. |
| `SECURITY_FRONTIER_COMPARABLE_WITH_STRONGER_OR_EQUAL_ALTERNATIVE` | The security remains comparable in the security frontier, but the evidence does not by itself establish strict dominance over all alternatives. |

`CASH_PREFERRED_PARTICIPATION_VALID` must not be reinterpreted as `ADD_MARGINAL_CAPITAL_BEATS_CASH`.

## Risk Pacing Separation

ECONOMIC_CAPITAL_PRIORITY_AND_RISK_PACING_SEPARATED = `YES`

Reason:

- Market Context / Market Quality produces context.
- Portfolio Policy owns Risk Pacing and the incremental capital budget envelope.
- Portfolio Construction owns security/Cash allocation of that envelope.
- Position Sizing owns discrete quantity.
- Runtime consumes PS output and must not re-decide priority.

Risk Pacing influences willingness to deploy; it does not directly set fixed exposure, BUY count, security admission, or quantity. The Cash interaction is therefore not a pure expected-return comparison, but the ownership boundaries remain separated and explicit.

Boundary to preserve:

```text
Portfolio Policy = deployment intensity / budget envelope
Portfolio Construction = NEW_BUY / ADD / Cash allocation frontier and participation-vs-deferral
```

## G130 Fact Reconciliation

Confirmed G130 facts:

- ADD vs NEW_BUY full frontier = YES
- ADD vs ADD full frontier = YES
- repeated ADD fresh reevaluation = YES
- BUY_NEW structurally disadvantaged = NO
- ADD vs Cash explicit PASS = 0/5 in focus-window fills
- many actual ADD fills use `CASH_PREFERRED_PARTICIPATION_VALID_IS_NOT_ADD_BEATS_CASH`

G131 interpretation:

These facts show the design is not a strict "selected security must explicitly beat Cash every time" system. It is a multi-allocation system where Cash can remain preferred/co-allocated while a limited, PC-authorized, one-lot `COMPARABLE_MARGINAL` security participation proceeds.

This is design-conformant if and only if:

- the row is not `CASH_PREFERRED_DEFER`;
- the row is not `CASH_MARGINAL_PREFERRED`;
- the row has PM ADD / ADD evidence PASS;
- the row has same-date opportunity-cost PASS;
- PC emits staged one-increment authority;
- Cash remains explicit residual/co-allocation;
- PS and Runtime consume without re-ranking;
- the next increment recomputes rather than reusing full-block authority.

G130 observed those properties for the focus-window ADD fills except that one `2022-12-01` Runtime ADD did not materialize as a same-day fill. That materialization observation is not a capital contract defect in G131.

## Required Answers

CASH_IS_FIRST_CLASS_INVESTMENT_ALTERNATIVE = `YES`

ADD_AND_NEW_ARE_PEERS_IN_CAPITAL_COMPETITION = `YES`

NEXT_LOT_MUST_BEAT_CASH_TO_BE_AUTHORIZED = `PARTIAL`

PARTICIPATION_SHOULDER_ALLOWED_WHEN_CASH_PREFERRED = `YES`

UNIFIED_ADD_NEW_CASH_MARGINAL_FRONTIER_REQUIRED = `YES`

G115_PARTICIPATION_SHOULDER_DESIGN_STATUS = `PERMANENT`

CASH_PREFERRED_SEMANTICS = `COMPOSITE`

ECONOMIC_CAPITAL_PRIORITY_AND_RISK_PACING_SEPARATED = `YES`

HISTORICAL_PERFORMANCE_USED_TO_SELECT_CONTRACT = `NO`

## Repair Decision

MANDATORY_REPAIR_FOUND = `NO`

REPAIR_BOUNDARY = `NOT_APPLICABLE`

G132 is not required for a repair. A future task may still improve observability by renaming or surfacing the distinction more clearly:

```text
COMPARABLE_MARGINAL_RESIDUAL_SHOULDER_ONE_INCREMENT_AUTHORIZED
!=
ADD_MARGINAL_CAPITAL_BEATS_CASH
```

But the design contract itself already contains that distinction and accepts reduced participation.

## Prohibited Interpretations

Do not infer:

- "ADD was bad because later performance was weaker."
- "Cash preferred means zero security by definition."
- "Participation valid means ADD beat Cash."
- "BUY_NEW must lose whenever ADD evidence is positive."
- "ADD must receive repeated full-block allocation once a campaign is open."

All of those contradict current SoT.

## Required Flags

CODE_CHANGED = `NO`

CONFIG_CHANGED = `NO`

THRESHOLD_CHANGED = `NO`

WEIGHT_CHANGED = `NO`

MODEL_CHANGED = `NO`

FRESH_RUN_EXECUTED = `NO`

RESUME_EXECUTED = `NO`

REPLAY_EXECUTED = `NO`

LONG_HISTORICAL_EXECUTED = `NO`

RUN_MUTATED = `NO`

PHASE_ADVANCED = `NO`
