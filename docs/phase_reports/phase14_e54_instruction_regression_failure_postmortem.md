# Phase14-E54 Runtime v2 Instruction / Regression Failure Postmortem

## Summary

Phase14-E54 is a postmortem for repeated Runtime v2 regressions, contract mismatches, and review failures during Phase14.

Final judgment: **PHASE14E54_POSTMORTEM_COMPLETE**

This phase was documentation-only.

No code was changed. No new implementation was added. No Submit, Broker Write, Production order, Notification real send, launchd change, or Current direct edit was performed.

## Core Problem

Phase14 repeatedly treated "component exists" and "tests pass" as sufficient, while Runtime v2 is an operational system whose correctness depends on:

```text
Design Contract
-> Input
-> Output
-> Consumer
-> Regular CLI Path
-> Broker / Current / Report Evidence
```

The most recent example is the Submit Guard regression:

- `run_submit_pipeline(...)` kept `max_order_amount=100000.0` as a hidden fixed cap.
- The cap applied to BUY and SELL identically.
- Capital Allocation / 100万円 evaluation-capital design implies dynamic or policy-derived sizing, not a hidden fixed 100,000円 per-order cap.
- Existing regression tests did not detect this because fixtures stayed under 100,000円 or bypassed the regular CLI path.

## Major Regressions / Misjudgments

### 1. Legacy Runtime / Legacy Submit Boundary Mixed Into Phase14-D

Phase:
- D / D2 / D3 / D4

What happened:
- Demo BUY was accepted, but the path still used legacy `OrderCommand` / `RuntimeMode` at the broker submit boundary.

Why review missed it:
- The review focused on whether the Runtime v2 harness existed.
- The actual import/call graph from script to broker adapter was not audited before acceptance.
- "Accepted by Demo Broker" was over-weighted relative to "Runtime v2 pure path."

Correct rule:
- A Broker acceptance is not Runtime v2 acceptance unless the call graph proves the regular Runtime v2 path.

### 2. Pending -> Submit Was CHECKPOINT-only

Phase:
- E17

What happened:
- Morning generated Pending, but Submit job only recorded a checkpoint and did not submit.

Why review missed it:
- Manifest `exit_code=0` was treated as success.
- The review did not require `demo_submit_executed`, `submitted_count`, `ledger_order_record_ids`, and Pending consume evidence.

Correct rule:
- CHECKPOINT-only is never PASS for an operational job that is supposed to perform work.

### 3. Broker Issue Code Normalization Missing

Phase:
- E18 / E19

What happened:
- Runtime v2 Submit sent J-Quants/internal 5-character codes directly to Tachibana `sIssueCode`.
- Broker rejected all orders.

Why review missed it:
- The review checked symbols at OrderPlan / Pending level but not Broker request boundary units.
- Existing normalizer existed but was not connected.
- Tests verified pipeline submission with fake adapter without checking Tachibana request fields.

Correct rule:
- Every boundary must verify units and schema:
  - internal 5-character code
  - Broker 4-character issue code
  - shares
  - lots
  - JPY/share
  - order notional

### 4. Execution Detail API Was Treated As Mandatory Despite Policy

Phase:
- D9 / D10 / D11 / E23

What happened:
- CLMOrderListDetail failure caused REVIEW_REQUIRED even when OrderList + Position + Cash evidence were sufficient.

Why review missed it:
- Implementation accepted one API shape as canonical before the evidence policy was settled.
- "More detailed evidence" was mistaken for "required evidence."

Correct rule:
- Evidence requirement must be stated as a policy, then implementation must follow it.
- Optional evidence failure must be warning, not fatal, if required evidence is complete.

### 5. Position Response Mapping Gap

Phase:
- D12 / D13

What happened:
- Broker Position API returned rows, but normalizer mapped issue_code to empty string and quantity to zero.

Why review missed it:
- ReadOnly fetch PASS was treated as semantic PASS.
- Raw row presence was not paired with normalized semantic key checks.

Correct rule:
- Fetch success is not semantic success.
- Normalized output must be checked against expected symbol, quantity, account, market, price, and value fields.

### 6. Current Path Contract Gap

Phase:
- D19 / D20 / D21 / D22

What happened:
- D15/D16 E2E artifacts lived under per-run paths, while canonical Current SoT `.runtime/persistent_ledger/state.json` was missing or not used as the real Current path.

Why review missed it:
- Per-run artifact PASS was mistaken for Current SoT PASS.
- "Report generated" was mistaken for "Current persisted."

Correct rule:
- Current is only canonical fixed Current path.
- Phase/run artifacts are History/Evidence/Derived, never Current.

### 7. Execution -> Current Projection Not Connected

Phase:
- E25 / E31 / E44 / E46 / E47

What happened:
- Execution wrote Ledger records and execution-equivalent evidence, but the regular execution job did not call `runtime_owned_fill_projection`.
- Current remained 100万円 / positions=0 after BUY execution.

Why review missed it:
- Component tests proved the projection component.
- Execution tests proved Ledger evidence.
- No test proved regular CLI Execution -> Projection -> Current.

Correct rule:
- Component PASS does not prove runtime connection.
- Level3 acceptance must prove Broker/Execution evidence changes Current SoT through the regular CLI path.

### 8. Planning Price Source Fallback

Phase:
- E26 / E27 / E28

What happened:
- Planning used fallback `estimated_price=1000` / quantity logic when candidate features had no reliable price.
- Orders were generated without an executable sizing price contract.

Why review missed it:
- OrderPlan schema had price-looking fields, so the value was accepted as meaningful.
- Tests checked that Pending existed, not that price_source was reliable.

Correct rule:
- A numeric field is not valid unless source, unit, date, confidence, and fallback policy are explicit.

### 9. Report Scope Mixed Current / Today / Run / Ledger History

Phase:
- E27 / E30

What happened:
- Public Report could show cumulative Ledger counts in a way that looked like today's operation result.

Why review missed it:
- Report existence and redaction were checked, but semantic scope was not.
- Humans could misread cumulative reject history as current-day reject.

Correct rule:
- Report must separate:
  - Current Portfolio
  - Today's Operation
  - Current Run
  - Ledger History
  - Pending / Approval
  - Warnings

### 10. Notification Component Was Incomplete

Phase:
- E14 / E34

What happened:
- Payload existed, but sender / queue / result / audit connection was incomplete.

Why review missed it:
- Payload READY was close to being interpreted as Notification READY.
- Flow review did not distinguish payload generation from delivery lifecycle.

Correct rule:
- Notification has separate levels:
  - Payload
  - Queue
  - Sender interface
  - Delivery result
  - Audit
  - Actual send

### 11. Market Refresh Was CHECKPOINT-only

Phase:
- E35 / E36 / E41

What happened:
- Market Refresh job initially recorded checkpoint stages without generating feature artifacts.
- Later, J-Quants URL/network errors were classified too coarsely.

Why review missed it:
- Job exit code and manifest stages were accepted before verifying output artifacts and next Morning consumer behavior.

Correct rule:
- Market Refresh PASS requires actual feature artifacts or explicit BLOCK/REVIEW with freshness contract.
- "feature_input_missing" is not NO_SIGNAL; it is operation-data failure.

### 12. SELL Daily Runtime Was Component-only, Not Runtime-connected

Phase:
- E32 / E33 / E50

What happened:
- SELL component existed, but no regular CLI `sell_planning` job existed until E50.

Why review missed it:
- Component/fake adapter tests were over-classified as flow completion.
- Review level was not explicit.

Correct rule:
- Level 1 component PASS must never be reported as Level 2/3 Runtime Flow PASS.

### 13. SELL Submit Guard Regression

Phase:
- E51 / E52 / E53

What happened:
- SELL Planning generated valid Runtime-owned SELL Pending.
- Submit preflight blocked all 5 SELLs because the hidden `max_order_amount=100000` cap applies to SELL.

Why review missed it:
- Prior tests used small amounts or direct harness overrides.
- No regression test compared Capital Allocation / SELL liquidation amount with regular CLI Submit guard.
- No manifest surfaced the active max amount policy.

Correct rule:
- Submit guard must be contract-aligned with Capital Allocation and side-specific SELL liquidation policy.

## Why Existing Review Failed

Review failures fell into recurring patterns:

1. **Component existence bias**
   - "There is a module" was treated as "Runtime path is connected."

2. **Test pass bias**
   - Tests used friendly fixtures that did not represent real operating amounts, request schemas, or CLI paths.

3. **Manifest exit-code bias**
   - `exit_code=0` was accepted without checking whether the job actually performed the intended operation.

4. **Fake adapter overconfidence**
   - Fake adapter tests proved shape, not real Broker request correctness.

5. **Per-phase artifact confusion**
   - Per-run artifacts were confused with Current SoT.

6. **Boundary schema blindness**
   - Internal symbol/price/quantity units were not verified at every consumer boundary.

7. **Scope ambiguity**
   - Report, Notification, and Audit artifacts were considered generated, without verifying their business meaning.

8. **Review level ambiguity**
   - Level 1 Component Review, Level 2 Flow Review, and Level 3 Full Runtime Review were not consistently labeled.

## Forbidden Instruction / Implementation Patterns

The following patterns are prohibited unless explicitly requested for an isolated experiment and clearly labeled as non-runtime:

1. Test-only Runtime module
2. Test-only CLI
3. Phase-only Runtime branch
4. Demo-only Runtime branch outside BrokerCapability / adapter boundary
5. Runtime bypass
6. Submit bypass
7. SELL bypass
8. Fake adapter in mainline operation proof
9. Current direct edit to make acceptance pass
10. Report / Blog / Audit as Submit source
11. Per-run artifact as Current source
12. `.runtime/demo/...` Current path revival
13. Legacy Runtime / Phase9 Runtime as Runtime v2 regular path
14. Legacy OrderCommand / RuntimeMode as Submit authority
15. Uncritical reuse of old processing just because it worked before
16. "tests pass" as sole acceptance
17. "manifest exists" as sole acceptance
18. "Broker accepted" as Runtime v2 acceptance without call graph proof
19. "Payload generated" as Notification delivery readiness
20. Any fix that does not cite the relevant design contract

## Required Design Contract Checklists

### Submit Guard Checklist

Before accepting any Submit-related phase:

- Submit source is exactly `.runtime/pending_order_plan/pending_order_plan.json`.
- Pending state is APPROVED.
- Approval hash / approved item IDs match.
- Duplicate / consumed / post_send_unknown guards pass.
- Environment and production guards pass.
- BrokerCapability is mode-derived, not user-configured ad hoc.
- Active max amount policy is explicit in manifest.
- BUY and SELL amount guards are side-specific or explicitly same-contract.
- Estimated amount source is traceable to Planning / price source.
- Internal symbol and Broker issue code boundary is verified.
- Broker request safe summary has expected fields.
- Raw request / response / secrets are not persisted.

### Capital Allocation Checklist

- Evaluation capital source is explicit.
- Broker demo 2,000万円 is not used as Runtime evaluation capital.
- Cash / buying_power / exposure basis is explicit.
- Per-order budget and total exposure are derived from policy.
- Price source is reliable and recorded.
- 100-share lot rounding is verified.
- If a desired order exceeds a guard, the layer responsible for that decision is explicit.
- Submit guard does not silently replace Capital Allocation policy.

### Current Projection Checklist

- Execution evidence exists.
- Ledger records are written.
- Runtime-owned fills are identified.
- Broker-only positions are excluded.
- Demo broker cash is not copied wholesale.
- `runtime_owned_fill_projection` runs through the regular execution job.
- `.runtime/persistent_ledger/state.json` changes as expected.
- Current before/after summary appears in manifest.
- Report and Next Planning read the new Current.

### SELL Checklist

- SELL source is Current SoT Runtime-owned positions only.
- Broker-only positions are not sold.
- Quantity <= Current position.
- Quantity <= Broker available quantity.
- Side-specific amount/liquidation policy is explicit.
- SELL notional above BUY cap is either allowed, split, or REVIEW_REQUIRED by contract.
- Submit uses regular submit job.
- Execution uses regular execution job.
- Current becomes reduced/zero after filled SELL.

### Notification Checklist

- Payload generated.
- Delivery queue record generated.
- Sender interface status explicit.
- Delivery result status explicit.
- Actual send enabled/disabled is explicit.
- Audit records notification state.
- Payload scope uses Current / Today / Run / Ledger History separation.

### Blog / Public Report Checklist

- Runtime v2 writer used, not Phase9 writer.
- Source is Current SoT / Runtime report, not Phase9 artifacts.
- Current Portfolio, Today's Operation, Current Run, Ledger History are separate.
- latest.md/latest.json updated.
- Redaction scan passes.
- Public output does not expose Broker raw IDs, secrets, raw request/response, stack traces, or internal paths beyond safe summaries.

## Redefined Acceptance Conditions

From E55 onward, acceptance must include all applicable items below.

### General

- Design contract cited.
- Input / Output / Consumer reviewed.
- Regular Runtime CLI path used when claiming runtime readiness.
- Review level explicitly stated:
  - Level 1 Component
  - Level 2 Flow
  - Level 3 Full Runtime
- `tests/runtime_v2` pass is required but not sufficient.
- No forbidden path or bypass.

### Runtime Operation

- Job performs real intended work, not CHECKPOINT-only.
- Manifest shows operation-specific evidence.
- Output artifact exists and is consumed by the next component.
- Current SoT is read/written only through canonical fixed path.

### Broker / Demo

- Demo Broker request evidence is available as safe summary.
- Broker Accepted / Rejected / Unknown counts are recorded.
- Broker ReadOnly evidence confirms post-submit state.
- No Production endpoint or credential path is reached.

### Current / Report

- Current SoT matches Runtime-owned evidence.
- Report matches Current.
- Public Report matches Current.
- Notification payload matches Current / Today Operation scopes.

### Failure

- Failures are classified as BLOCKED / REVIEW_REQUIRED / HALT.
- The stopped layer is identified to one edge:
  - Input -> Component
  - Component -> Output
  - Output -> Consumer
- Operator next_action is included.

## Required Regression Additions

Future regression suite must include:

1. BUY above 100,000 but within Capital Allocation policy.
2. SELL Runtime-owned liquidation above 100,000.
3. SELL broker-only position exclusion.
4. CLI submit path amount-policy regression.
5. Guard policy manifest fields.
6. Broker request safe summary unit checks.
7. Execution -> Current projection through CLI.
8. Report scope checks for Current / Today / Run / Ledger History.
9. Notification queue/result/audit checks.
10. Market Refresh artifact generation and Morning consumer check.

## E55+ Restart Conditions

E55 or later should not proceed to another Demo operation attempt until:

1. Submit amount guard contract is explicitly fixed or approved.
2. BUY max amount and SELL liquidation policy are separated or explicitly unified by design.
3. Regular CLI Submit manifest records active amount policy.
4. Regression tests cover above-cap BUY and SELL liquidation.
5. SELL cleanup path is re-run only through:
   - `sell_planning`
   - `submit`
   - `execution`
6. Current and Report acceptance criteria are written before the run.
7. No bypass, fake adapter, direct Current edit, or Phase-only branch is used.

## Working Rule For Codex

For subsequent phases, Codex must not close a Runtime phase with only:

```text
tests/runtime_v2 PASS
```

The final answer must also state:

- Review level.
- Design contract checked.
- Regular CLI path or component-only status.
- Whether Broker write occurred.
- Whether Current changed.
- Whether Report/Public Report/Notification reflect the same state.
- Any remaining gap without softening the wording.

## Final Judgment

**PHASE14E54_POSTMORTEM_COMPLETE**

