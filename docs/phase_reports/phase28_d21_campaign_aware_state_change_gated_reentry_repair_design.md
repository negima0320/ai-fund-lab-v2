# Phase28-D21: Campaign-Aware State-Change Gated Re-entry Repair Design

## Primary Judgment

```text
PHASE28_D21_CAMPAIGN_AWARE_STATE_CHANGE_REENTRY_DESIGN_COMPLETE_IMPLEMENTATION_READY
```

Implementation Entry Decision:

```text
READY
```

D21 is design-only and read-only. No implementation, config change, schema change, threshold change, resume, fresh run, long historical run, or runtime mutation was performed.

## Canonical Definition

Re-entry means:

```text
same-symbol previous CLOSED campaign
↓
candidate BUY_NEW opens a new campaign
```

Not re-entry:

```text
OPEN campaign -> BUY_ADD
REDUCE followed by ADD
partial SELL followed by BUY_ADD
pending cancellation
no-fill
same-campaign ADD
```

## Previous Campaign Authority

Primary authority:

```text
Position Campaign history / persistent ledger
```

Required previous campaign context:

```text
previous_campaign_id
previous_close_date
previous_exit_reason
previous_realized_pnl
previous_exit_rank
previous_exit_score
previous_market_context
previous_expected_edge
business_days_since_exit
recent_loss_state
```

Required current candidate context:

```text
current_rank
current_score
current_market_context
current_expected_edge
buy_quality_status
opportunity_status
```

If no previous closed campaign exists, the candidate remains normal BUY_NEW eligibility.

If a previous closed campaign exists, re-entry eligibility evaluation is required.

## State-Change Gate

Re-entry is allowed only when the current candidate has meaningful positive state change versus the previous exit state.

State-change evidence candidates:

```text
momentum recovery
rank recovery
expected edge improvement
market context improvement
exit reason resolution
```

Not sufficient by itself:

```text
next-day candidate recurrence
BUY Quality PASS alone
available cash
absence of current position
ordinary Opportunity eligibility
```

## Recent-Loss Behavior

If:

```text
previous_realized_pnl < 0
```

then stronger state-change evidence is required.

For short-delay recent loss, D21 contract blocks re-entry when no meaningful momentum recovery exists:

```text
previous loss
+
<=5BD re-entry
+
no meaningful momentum recovery
↓
REENTRY_BLOCKED_RECENT_LOSS
```

This is not a symbol ban, not a never-buy-after-loss rule, and not fixed cooldown-only logic.

## Time Role

Time is supporting evidence, not primary authority.

| Delay | Contract |
|---|---|
| <=1BD | very strong state-change evidence required |
| 2-3BD | strong state-change evidence required |
| 4-5BD | state-change evidence required |
| >5BD | normal re-entry evaluation still required |

D21 does not optimize numeric thresholds on D20 outcomes.

## Classification Contract

| Class | Behavior |
|---|---|
| FIRST_ENTRY | normal BUY_NEW eligibility |
| VALID_REENTRY_STATE_CHANGED | allow if all other authorities pass |
| VALID_REENTRY_MOMENTUM_RECOVERY | allow if all other authorities pass |
| VALID_REENTRY_MARKET_RECOVERY | allow or review depending on symbol evidence completeness |
| REENTRY_BLOCKED_NO_MEANINGFUL_CHANGE | block BUY_NEW target membership |
| REENTRY_BLOCKED_RECENT_LOSS | block BUY_NEW target membership |
| REENTRY_REVIEW_REQUIRED_INSUFFICIENT_CONTEXT | fail closed; no ordinary BUY_NEW fallback |

Fail-closed behavior:

```text
previous campaign exists + required context missing
↓
REVIEW_REQUIRED
↓
no executable BUY_NEW fallback
```

The downstream effect should be target membership blocked or target weight zero with reason evidence. Runtime Planning must not recover an implicit BUY_NEW from missing re-entry context.

## BUY_ADD Separation

The re-entry gate applies only to:

```text
CLOSED campaign -> BUY_NEW
```

It does not apply to:

```text
OPEN campaign -> BUY_ADD
```

D19 BUY_ADD wiring remains unchanged.

## Runtime Integration Point

Selected:

```text
Portfolio Construction conflict policy
```

Reason:

```text
Portfolio Construction owns target membership and target weight.
Strategy Architecture v1 already assigns re-entry cooldown/conflict policy to Portfolio Construction.
```

Rejected:

| Option | Reason |
|---|---|
| Candidate / Opportunity stage | too early; lacks target portfolio and campaign conflict context |
| Runtime Planning | too late; target weight and quantity would already be produced |

## D20 Replay

D20 93-event post-hoc replay under the D21 design:

| Replay decision | Count | Historical PnL |
|---|---:|---:|
| ALLOW | 44 | -6,750 |
| BLOCK | 34 | -123,240 |
| REVIEW | 15 | +24,190 |

Classification counts:

| Classification | Count |
|---|---:|
| VALID_REENTRY_MOMENTUM_RECOVERY | 33 |
| VALID_REENTRY_STATE_CHANGED | 11 |
| REENTRY_BLOCKED_NO_MEANINGFUL_CHANGE | 31 |
| REENTRY_BLOCKED_RECENT_LOSS | 3 |
| REENTRY_REVIEW_REQUIRED_INSUFFICIENT_CONTEXT | 15 |

Special focus:

```text
loss -> <=5BD re-entry -> loss cases: 16
blocked by D21 replay: 12
allowed by D21 replay: 4
```

Contradictory Re-entry:

```text
D20 contradictory cases: 31
blocked by D21 replay: 31
```

Valid momentum recovery preservation:

```text
D20 valid momentum recovery cases: 33
preserved / allowed by D21 replay: 33
```

This replay is diagnostic only. It is not a performance optimization and does not feed D20 outcomes into runtime decisions.

## D22 Recommendation

Recommended implementation is exactly one repair:

```text
Campaign-aware re-entry eligibility resolver
```

Do not mix:

```text
Cash reserve
Target exposure
BUY_ADD allocation
ADD thresholds
Exit thresholds
Position count
BUY Quality thresholds
```

Fresh 100BD sequence recommendation:

```text
D21 implementation short validation
↓
D22 Capital Deployment / Cash Utilization Audit design or audit
↓
fresh100BD
```

Reason: re-entry suppression can reduce BUY_NEW count and increase cash. Cash Policy must remain separate so causal attribution stays clean.

## Focused Fixture Contract

Required fixtures for implementation:

```text
1. no prior campaign -> BUY_NEW allowed
2. prior profitable EXIT + strong momentum recovery -> allowed
3. prior loss + 1BD + no meaningful change -> blocked
4. prior loss + strong state recovery -> allowed or review depending on evidence completeness
5. prior EXIT + identical state -> blocked
6. prior EXIT + improved rank only but weak momentum -> review unless contract-defined sufficient evidence exists
7. campaign context missing -> fail closed
8. OPEN campaign ADD -> unaffected
9. D19 BUY_ADD chain -> PASS
10. D14/D16 SELL regression -> PASS
```

## Deliverables

```text
docs/phase_reports/phase28_d21_campaign_aware_state_change_gated_reentry_repair_design.md
reports/phase_reports/phase28_d21_campaign_aware_state_change_gated_reentry_repair_design.json
reports/phase28_d21_campaign_aware_state_change_gated_reentry_repair_design/
```

## Final Judgment

```text
Primary Judgment: PHASE28_D21_CAMPAIGN_AWARE_STATE_CHANGE_REENTRY_DESIGN_COMPLETE_IMPLEMENTATION_READY
Implementation Entry Decision: READY
Previous campaign authority: Position Campaign history / persistent ledger
State-change gate: required for same-symbol closed-campaign BUY_NEW
Recent-loss behavior: stricter, but not fixed cooldown-only
Fail-closed behavior: missing context => REVIEW_REQUIRED / no BUY_NEW fallback
BUY_ADD separation: OPEN campaign BUY_ADD unaffected
Runtime integration point: Portfolio Construction conflict policy
Minimal implementation scope: Campaign-aware re-entry eligibility resolver only
Next Phase: D21 implementation task or Phase28-D22, depending on phase numbering
```
