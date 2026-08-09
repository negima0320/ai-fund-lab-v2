# Phase28-D49: Broker Eligibility Upstream Planning / Universe Exclusion Repair

## Primary Judgment

```text
PHASE28_D49_BROKER_ELIGIBILITY_UPSTREAM_EXCLUSION_IMPLEMENTED_SHORT_VALIDATION_PASS
```

Supporting Judgment:

```text
PHASE28_D49_UNSUPPORTED_SECURITY_NEW_EXPOSURE_PREVENTED_FRESH_100BD_READY
```

Restart Entry:

```text
APPROVED
```

## Scope

D49 implemented the upstream broker eligibility gate for executable BUY exposure only.

Changed:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
tests/strategy/test_phase22_e_portfolio_construction.py
```

Not changed:

```text
Config
Schema
Threshold
Submit Guard
Broker normalizer
Runtime Planning
Position Sizing
BUY Quality
Model/rank semantics
```

No resume, no fresh run, no long historical run, and no runtime mutation were executed.

## Gating Owner

Selected authoritative owner:

```text
Portfolio Construction
```

Implementation hook:

```text
_reconcile_members
↓
_attach_buy_quality
↓
_apply_broker_eligibility_to_new_exposure
↓
_resolve_target_weight_contract
```

Reason:

Portfolio Construction is the first layer that owns executable target membership and target weight. Candidate, Opportunity, and BUY Quality remain ranking/evidence layers, so broker execution policy is not injected into model score, rank, or quality decisions. Runtime Planning is too late because executable target exposure has already been created.

Rejected owners:

```text
Universe:
too early; risks hiding existing unsupported holdings from PM/risk/EXIT visibility.

Candidate / Opportunity / BUY Quality:
would contaminate ranking and model quality semantics with broker execution policy.

Runtime Planning:
too late; target exposure and BUY deltas already exist.
```

Evidence:

```text
reports/phase28_d49_broker_eligibility_upstream_planning_universe_exclusion_repair/broker_eligibility_gating_owner.json
```

## Implemented Repair

D49 reuses the D48 single source of truth:

```text
ai_fund_lab_v2.broker.issue_code_normalizer.classify_broker_security(...)
```

No duplicate product-category mapping was added.

Behavior:

```text
New BUY / BUY_NEW
011 supported -> unchanged
021 unsupported -> EXCLUDE, target_weight=0
unknown category -> EXCLUDE, target_weight=0

Existing position / BUY_ADD
unsupported/unknown -> position remains visible, PM ADD evidence preserved, but ADD target increase is fail-closed

Existing HOLD / REDUCE / EXIT
unsupported/unknown -> PM lifecycle remains visible
```

D49 does not make unsupported securities broker-tradable. D48 remains the final Submit/Broker fail-closed defense for unsupported SELL/manual liquidation cases.

## 93990 Causality

Original entry evidence:

```text
run_id = runtime-test-historical-smoke-20260807T181131555434Z
business_date = 2023-05-29
symbol = 93990
source_decision_type = BUY_NEW
pending_item_id = strategy-e37a7fc4a04c32fd99f6
filled_quantity = 700
```

Portfolio Construction on 2023-05-29:

```text
membership_intent = ADD_CANDIDATE
target_membership = true
target_weight = 0.085179
input_opportunity_rank = 6
input_candidate_order = 5
runtime_opportunity_score = 0.10841531
quality_action = FULL_ALLOCATION_ELIGIBLE
```

D48 classification:

```text
canonical product_category = 021
security_type = 021
broker_security_type = UNSUPPORTED_FOREIGN_LISTED_STOCK
reason = BROKER_PRODUCT_CATEGORY_UNSUPPORTED
tradable = false
```

D49 would have prevented this holding by converting the Portfolio Construction member from:

```text
ADD_CANDIDATE
```

to:

```text
EXCLUDE
```

before target-weight allocation, Position Sizing quantity delta, Pending BUY, Submit BUY, and fill.

No counterfactual PnL claim is made. A next replacement cannot be deterministically claimed from existing artifacts because the original day already selected the other eligible new member, while lower-ranked rows after 93990 were rejected/excluded.

Evidence:

```text
reports/phase28_d49_broker_eligibility_upstream_planning_universe_exclusion_repair/93990_original_entry_trace.json
```

## Validation

Focused D49:

```text
3 passed
```

Portfolio Construction full file:

```text
46 passed
```

D48 normalizer / submit / historical SELL quantity:

```text
19 passed
```

D44 / D46 / D8 / D14 regressions:

```text
D44-D46 = 4 passed
D8 = 9 passed
D14 = 1 passed
```

D39 / D42 / Phase28-C:

```text
D39-D42 = 5 passed
Phase28-C = 4 passed
```

Compile and hygiene:

```text
py_compile = PASS
git diff --check = PASS
JSON validation = PASS
```

## Final Judgment Items

```text
Gating Owner = Portfolio Construction
93990 Original BUY Date = 2023-05-29
93990 Original Rank = 6
93990 Product Category = 021
BUY_NEW Eligibility = false
BUY_ADD Eligibility = false
Existing Holding Visibility = preserved
HOLD / REDUCE / EXIT Visibility = preserved
Model / Rank Contamination = no
D48 Classification Reused = yes
Runtime Authority Violation = no
Performance Change = no
Config / Schema / Threshold Change = no
Resume / Fresh / Long Historical = no
```

## Open Gaps

D49 only gates rows that carry listed_info/product_category into Portfolio Construction. Legacy or artificial rows without category remain non-evaluated to avoid a schema/config expansion in this phase.

Existing unsupported holdings remain visible; their actual broker liquidation remains fail-closed/manual-review under D48.

## Deliverables

```text
docs/phase_reports/phase28_d49_broker_eligibility_upstream_planning_universe_exclusion_repair.md
reports/phase_reports/phase28_d49_broker_eligibility_upstream_planning_universe_exclusion_repair.json
reports/phase28_d49_broker_eligibility_upstream_planning_universe_exclusion_repair/
```
