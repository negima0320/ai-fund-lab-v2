# Phase24-IN Phase24 Runtime Test Findings and Remaining Gaps

## Phase24 Task Timeline

Full machine inventory:

`reports/phase24_in_phase21_to_phase24_cross_phase_review/phase_task_inventory.json`

Condensed Phase24 timeline:

| Task | Focus | Result / finding |
|---|---|---|
| A0 / A0R1 / A0R2 | Phase24 entry and source readiness | close/runtime revalidation and fresh-run gates prepared |
| A | Performance Evaluation Contract | metrics, benchmark, baseline, experiment, attribution contracts defined |
| B | Zero Deployment | BUY_ELIGIBLE but planned quantity zero traced through policy/deployment/sizing |
| C-D | Low opportunity / exploratory entry | opportunity capacity and market-weak entry policy investigated/implemented |
| E1/E3/E5 | Pending / safety authority | no-order and SELL pending safety authority repaired |
| F | Opportunity ranking attribution | entry quality and ranking semantics audited |
| G-H | Performance accounting | cost-basis authority gap found and repaired |
| HR-HS-HT | Exposure / submit feasibility | planning preflight contract and implementation added |
| HU-HV | BUY review / SELL continuation | item-scoped review and SELL continuation contract repaired |
| HX-HY-IA | Rank authority | opportunity rank consumer alignment and observability repaired |
| IC-ID-IE-IF | Submit / execution / aggregate feasibility | partial submit, post-fill reconciliation, aggregate feasibility, gross exposure issues reviewed/repaired |
| IG-IH-IJ | Resume / failed pending | materialized feature entry gate, failed-stage rollback, same-day recontamination repaired |
| II | Position sizing precision | aggregate exposure precision and planning authority repaired |
| IK | Corporate Action Guard | AdjFactor impact exposed; fail-closed confirmed |
| IL | Corporate Action Adjustment Authority | quantity/current/pending reconciliation authority designed and implemented |
| IM | Authority materialization and consumer wiring | producer/materialization added; Submit Guard and Adapter consistency repaired |
| IN | Cross-phase review | closure review package and Phase25 plan prepared |

## Resume Defects

Findings:

- completed / failed / future day classification was not strict enough
- plan expectation could be confused with materialized authority
- run-scoped materialized feature evidence was required
- failed-stage artifacts needed quarantine and retry eligibility checks

Status:

- entry gate and materialized contract consistency repaired
- same-day failed attempt recontamination repaired
- long-run resume remains operator-owned

## Pending Defects

Findings:

- failed attempt Pending could contaminate persistent Pending
- Pending slot reuse lacked sufficient attempt identity
- review Pending could re-enter retry paths incorrectly
- atomic commit semantics were needed

Status:

- failed-stage rollback and same-day recontamination repairs completed
- Review resolution operator flow remains missing

## Safety Defects

Findings:

- historical neutral safety needed temporal binding
- stale latest safety decision could be misread
- Pending safety authority had to be bound to the target date/run evidence

Status:

- historical neutral safety and pending safety binding repaired
- Safety Guard was not weakened

## Position Sizing Defects

Findings:

- target gross exposure and aggregate target weights could overflow through precision/rounding
- downstream quantity authority could overstate feasible exposure

Status:

- precision tolerance and Strategy Planning Authority propagation repaired
- Phase25 must still evaluate capital efficiency and cash drag

## Planning Authority Defects

Findings:

- Position Sizing artifact and Runtime Planning authority needed consistent propagation
- existing position mapping and BUY quantity authority needed scoped review semantics
- Planning could advance items that Submit would deterministically reject

Status:

- Planning Submit Feasibility and aggregate reservation added
- Runtime Planning remains separate from Submit permission

## Corporate Action Defects

Findings:

- raw PIT `AdjFactor` impact was detected on `2023-10-04 / 65730`
- event type authority was missing
- current / ledger / pending quantity adjustment could not be proven
- Submit Guard initially said `NOT_DETECTED/PASS` while Historical Adapter said `IMPACT_DETECTED/REVIEW_REQUIRED`

Status:

- Corporate Action Guard fail-closed preserved
- detailed AdjFactor evidence added
- Corporate Action Adjustment Authority added
- authority producer/materialization added
- Submit Guard / Adapter consistency repaired

Remaining:

- Corporate Action Human Review CLI / approval workflow
- resolved event-type source authority for impacted items
- continuation policy after review resolution

## Runtime Performance

Observed concern:

- some runs are around 2m30s per business day

Phase25 should profile:

- job/stage duration
- market refresh and feature generation
- candidate / opportunity / PM / strategy artifacts
- planning / submit / fill / ledger / snapshot
- evidence copy overhead
- repeated file I/O and Parquet/model load cost

## Test Evidence

2023 run:

- `ABANDONED`
- completed `186` days through `2023-10-03`
- halted at `2023-10-04 submit`
- not reusable as clean performance acceptance baseline

2024 run:

- `PASS`
- completed `10` business days
- lifecycle consistency `PASS`
- final equity `1,067,660`

## Unresolved Items

- Phase24 closure decision
- full performance metrics
- benchmark comparison
- drawdown / volatility / Sharpe / Sortino / Calmar
- cash/exposure time-series
- compound reinvestment authority
- Corporate Action review/approve/reject commands
- review item isolation after next business day continuation
- production operations runbook
- speed profiling and optimization plan

## Operator Review Policy

Manual operation must bind authority artifacts and must not bypass Submit Guard, Safety Guard, Planning Authority, Corporate Action Guard, or Broker boundary.

## Corporate Action Continuation Policy

Unknown event type, unknown already-applied status, mixed pre/post quantity basis, future data use, or double-adjustment risk must remain fail-closed. Resume after review should require a canonical authority artifact and audit reason.
