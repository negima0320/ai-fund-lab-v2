# Phase28-D50: Broker Eligibility Listed-Info Runtime Propagation Root Cause

## Primary Judgment

```text
D49_GATE_CORRECT_BUT_REQUIRED_AUTHORITY_NOT_PROPAGATED
```

D50 was read-only diagnosis. No implementation, config, schema, threshold, resume, fresh run, long historical run, or runtime mutation was executed.

## Target

```text
run_id = runtime-test-historical-smoke-20260807T202512386120Z
business_date = 2023-05-29
symbol = 93990
```

Observed active Portfolio Construction row:

```text
security_code = 93990
membership_intent = ADD_CANDIDATE
target_membership = true
target_weight = 0.085179
listed_info = null
product_category = null
security_type = null
broker_eligibility = null
```

## Canonical Listed-Info Availability

Canonical listed-info is available for 93990 on 2023-05-29.

First source:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260807T202512386120Z/daily/2023-05-29/market_refresh/inputs/historical_asof/2023-05-29/raw/jquants/listed_issues/data.parquet
```

Values:

```text
Code = 93990
Date = 2023-05-29
ProdCat = 021
MktNm = スタンダード
```

The target run does not contain an explicit `security_type` field in this raw source. The expected `security_type = 021` is the same ProdCat-derived listed-info materialization used by the D48 normalizer coercion path.

Candidate feature input also has the authority data:

```text
.runtime/operations/feature_artifacts/2023-05-29/candidate_features.parquet

code = 93990
product_category = 021
market_name = スタンダード
is_current_listed = true
is_allowed_product = true
universe_eligible = true
```

Evidence:

```text
reports/phase28_d50_broker_eligibility_listed_info_runtime_propagation_root_cause/93990_listed_info_lineage.json
```

## Lineage Result

```text
Canonical PIT Listed Issues
PASS: ProdCat=021, MktNm=スタンダード

Candidate feature input
PASS: product_category=021, market_name=スタンダード

Candidate decision artifact
LOSS: product_category=null, market=null, listed_info=null

Opportunity feature input
ABSENT: no product/market/listed-info fields

Opportunity ranking artifact
ABSENT: product_category=null, market=null, listed_info=null

Buy Quality
ABSENT: product_category=null, market=null, listed_info=null

Portfolio Construction input/member
ABSENT: product_category=null, market=null, listed_info=null, broker_eligibility=null
```

First loss point:

```text
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py
_candidate_payload(...)
```

Code path:

```text
produce candidate rows
↓
build_scored_candidates(latest.to_dict("records"), ...)
↓
_candidate_payload(rows=...)
↓
decisions = [
  business_date
  target_date
  feature_date
  runtime_id
  model_version
  code
  symbol
  candidate_score
  candidate_rank
  candidate_reason
  reason
  confidence
]
```

The candidate feature row contains `product_category` and `market_name`, but `_candidate_payload` projects candidate output rows to score/rank identity fields and omits listed-info-compatible metadata.

Evidence:

```text
reports/phase28_d50_broker_eligibility_listed_info_runtime_propagation_root_cause/first_loss_point.json
reports/phase28_d50_broker_eligibility_listed_info_runtime_propagation_root_cause/candidate_to_opportunity_trace.json
```

## Mandatory Questions

1. Where does 93990 canonical listed-info exist on 2023-05-29?

```text
J-Quants PIT listed_issues parquet under market_refresh/inputs/historical_asof.
```

2. Which artifact first contains product_category=021, security_type=021, market=スタンダード?

```text
product_category/market first appear in listed_issues parquet.
security_type is not explicit in the target run source; it is expected as ProdCat-derived 021.
```

3. Does Candidate contain it?

```text
Candidate feature input: YES.
candidate_decisions.json row: NO.
```

4. Does Opportunity ranking contain it?

```text
NO.
```

5. Does Buy Quality contain it?

```text
NO.
```

6. Does Portfolio Construction input manifest contain it?

```text
It contains listed_info_source path/hash authority.
It does not contain the 93990 row values copied into PC input rows.
```

7. Which adapter converts upstream candidate/opportunity rows into Portfolio Construction members?

```text
src/ai_fund_lab_v2/strategy/shadow_runtime.py::_pc_summary
src/ai_fund_lab_v2/strategy/portfolio_construction.py::_reconcile_members -> _member
```

8. Does that adapter drop listed_info?

```text
NO. The adapter preserves row fields; the fields are already absent from candidate/opportunity rows.
```

9. Is product_category available under a different nested field/path?

```text
YES:
.runtime/operations/feature_artifacts/2023-05-29/candidate_features.parquet.product_category
input_manifest.strategy_source_authority.paths.listed_issues
```

10. Is D49 reading the wrong field/path?

```text
NO. D49 reads listed_info, product_category/ProdCat, market/MktNm/market_name from member source rows. The runtime rows do not carry those fields into PC.
```

11. Are there separate shadow vs active Strategy paths?

```text
YES: daily/2023-05-29/strategy and daily/2023-05-29/strategy_eod_shadow.
```

12. Does strategy_eod_shadow contain listed_info while active strategy does not?

```text
NO. Both active and shadow PC member rows lack listed_info/product_category.
```

13. Is canonical listed-info available in input_manifest/source_manifest but not copied into member rows?

```text
YES. The source authority path is present; row metadata is not propagated into candidate/opportunity/PC rows.
```

14. Is this a schema omission, adapter omission, or wrong source selection?

```text
Schema/output projection omission at candidate runtime artifact materialization.
Not wrong source selection.
Not D49 field-path error.
```

15. Which Production-common producer should own propagation?

```text
Runtime v2 BUY AI candidate producer:
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py
```

## Active vs Shadow

Active:

```text
path = daily/2023-05-29/strategy/portfolio_construction.json
current_position = false
membership_intent = ADD_CANDIDATE
target_membership = true
target_weight = 0.085179
broker_eligibility_gating_owner = PORTFOLIO_CONSTRUCTION
broker_eligibility = null
listed_info = null
```

Shadow:

```text
path = daily/2023-05-29/strategy_eod_shadow/portfolio_construction.json
current_position = true
membership_intent = UNRESOLVED
target_membership = false
target_weight = 0.0
broker_eligibility_gating_owner = PORTFOLIO_CONSTRUCTION
broker_eligibility = null
listed_info = null
```

Classification:

```text
The path divergence is position-state timing: active creates BUY_NEW exposure, while eod_shadow sees 93990 as an existing position after execution state.

It is not a listed-info propagation divergence. Both paths lack listed_info at PC member level.
```

Evidence:

```text
reports/phase28_d50_broker_eligibility_listed_info_runtime_propagation_root_cause/active_strategy_93990_trace.json
reports/phase28_d50_broker_eligibility_listed_info_runtime_propagation_root_cause/shadow_strategy_93990_trace.json
```

## D49 Causality

```text
D49 gate called = YES
D49 classification called for 93990 = NO
```

Reason:

```text
_apply_broker_eligibility_to_new_exposure
↓
_broker_eligibility_payload(member)
↓
member.broker_listed_info absent
↓
return None
↓
classify_broker_security(...) not called
```

This confirms:

```text
D49_GATE_CORRECT_BUT_REQUIRED_AUTHORITY_NOT_PROPAGATED
```

Evidence:

```text
reports/phase28_d50_broker_eligibility_listed_info_runtime_propagation_root_cause/d49_causality.json
```

## Minimal D51 Scope

Exactly one repair scope:

```text
Propagate canonical listed-info-compatible fields from candidate feature rows
into runtime candidate_decisions row materialization.
```

Owner:

```text
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py
_candidate_payload / candidate row materialization
```

Minimum propagated fields:

```text
code
market / market_name
product_category
security_type derived from product_category when no explicit SecType exists
current_listed
listed_info authority/source metadata from existing strategy source authority when available
```

Do not:

```text
duplicate broker classification mapping
inject historical-only metadata
change D48 broker normalizer
change D49 classification logic
```

Evidence:

```text
reports/phase28_d50_broker_eligibility_listed_info_runtime_propagation_root_cause/minimal_repair_scope.json
reports/phase28_d50_broker_eligibility_listed_info_runtime_propagation_root_cause/next_phase_contract.json
```

## Final Judgment

```text
Primary Judgment = D49_GATE_CORRECT_BUT_REQUIRED_AUTHORITY_NOT_PROPAGATED
Canonical listed-info available = YES
93990 canonical product_category = 021
Candidate value = feature input has 021; candidate_decisions row null
Opportunity value = null
Buy Quality value = null
PC input value = null
First loss point = runtime_v2.buy_ai.producer._candidate_payload
Active vs shadow difference = position-state timing only; both lack listed_info
D49 gate called = YES
D49 classification called for 93990 = NO
Root Cause = candidate artifact row projection drops listed-info authority
Repair Required = YES
Minimal D51 Scope = candidate row listed-info metadata propagation
Implementation changed = false
Config changed = false
Schema changed = false
Threshold changed = false
Resume executed = false
Fresh executed = false
Long Historical executed = false
Runtime mutated = false
Next Phase = Phase28-D51
```

## Deliverables

```text
docs/phase_reports/phase28_d50_broker_eligibility_listed_info_runtime_propagation_root_cause.md
reports/phase_reports/phase28_d50_broker_eligibility_listed_info_runtime_propagation_root_cause.json
reports/phase28_d50_broker_eligibility_listed_info_runtime_propagation_root_cause/
```
