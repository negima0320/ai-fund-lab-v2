# Phase28-D13: Strategy Executable SELL Non-Opportunity listed_info Authority Repair Design

## 1. Executive Summary

Primary Judgment:

```text
PHASE28_D13_NON_OPPORTUNITY_LISTED_INFO_AUTHORITY_DESIGN_COMPLETE_PHASE28_D14_READY
```

Phase28-D14 Entry Decision:

```text
APPROVED
```

D13 designed the missing non-Opportunity `listed_info` Authority for executable Strategy SELL pending items.

The final design is:

```text
Primary Authority:
Canonical PIT Listed Issues / Listed Info Artifact via Strategy Source Authority

D14 primary repair:
Strategy SELL Producer canonical listed-info lookup
```

No implementation, config, schema, threshold, resume, fresh run, or long historical was performed.

## 2. Scope

D13 scope:

```text
Design only
Opportunity-independent listed_info Authority for executable Strategy SELL pending
Target class: 2023-06-14 / 30410 / SELL_EXIT / listed_info_missing
```

Out of scope:

```text
Strategy Authority implementation
Pending Composition implementation
Approval / Submit / Broker changes
Phase28-D12 PM ADD propagation
Phase28-C ADD bridge
Performance conditions
Historical-only fallback
```

## 3. Accepted Evidence

Accepted as input:

```text
run_id: runtime-test-historical-smoke-20260806T005408544432Z
halt date: 2023-06-14
halt stage: submit
symbol: 30410
side: SELL
intent: SELL_EXIT
pending_item_id: strategy-5886464c6597722728b4
direct reason: sell broker available quantity missing
underlying reason: listed_info_missing
```

Accepted D6/D7 fact:

```text
strategy_authority._listed_info_from_opportunity_authority returns None
when Opportunity Authority is absent.
```

## 4. Documents Reviewed

```text
docs/phase_reports/phase28_d12_pm_add_strategy_position_management_adapter_repair_implementation.md
docs/phase_reports/phase28_d8_compatible_sell_pending_required_authority_merge_implementation.md
docs/phase_reports/phase28_d7_sell_pending_required_authority_merge_repair_design.md
docs/phase_reports/phase28_d6_sell_pending_listed_info_authority_trace.md
docs/phase_reports/phase28_d5_20230410_submit_halt_root_cause.md
docs/02_architecture/runtime_architecture_v2.md
docs/02_architecture/strategy_architecture_v1.md
docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md
docs/02_architecture/position_management_decision_trace_contract.md
docs/01_requirements/phase_roadmap.md
```

## 5. Current Defect

Current Strategy producer behavior:

```text
_pending_item_from_strategy_plan(...)
  -> PendingOrderItem(listed_info=_listed_info_from_opportunity_authority(...))
```

Code evidence:

```text
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:473-488
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:903-922
```

Defect:

```text
Opportunity Authority absent
↓
listed_info = None
↓
Submit Guard broker issue-code normalization fails
```

Correct principle:

```text
Opportunity ranking absent != listed_info unknown
```

## 6. Authority Candidate Inventory

Primary candidate:

```text
Canonical PIT Listed Issues / Listed Info Artifact
```

30410 evidence:

```text
path:
reports/runtime_tests/runs/runtime-test-historical-smoke-20260806T005408544432Z/daily/2023-06-14/market_refresh/inputs/historical_asof/2023-06-14/raw/jquants/listed_issues/data.parquet

row:
Date=2023-06-14
Code=30410
MktNm=スタンダード
ProdCat=011

hash:
e4af094fb0d1a034ac325473c4c34d179f0b82021c16f0b25927e70dac84d0e0
```

Historical as-of Authority:

```text
status: PASS
selected_snapshot_date: 2023-06-14
selection_policy: latest_snapshot_not_after_business_date
snapshot_age_days: 0
content_hash_verified: true
```

Rejected as primary:

```text
Opportunity embedded listed_info: absent for the failure class
Current / campaign metadata: identity lineage, not listed-issue fact authority
Sell Planning basic listed_info: fixed metadata, not canonical PIT
Broker normalizer: consumer, not producer
Submit Guard: final defense, not enrichment producer
```

## 7. listed_info Required Contract

Required fields:

```text
code
market
product_category
security_type
current_listed
```

Consumer evidence:

```text
src/ai_fund_lab_v2/broker/issue_code_normalizer.py:50-81
src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:1312-1414
src/ai_fund_lab_v2/runtime_v2/pending/composition.py:690-703
```

Recommended lineage fields:

```text
listed_info_authority
listed_info_source_artifact
listed_info_source_hash
listed_info_source_business_date
listed_info_source_as_of
listed_info_source_row_id
listed_info_source_row_hash
listed_info_resolution_status
listed_info_resolution_reason
```

## 8. Canonical Authority Selection

Selected:

```text
Canonical PIT Listed Issues / Listed Info Artifact
```

Carrier:

```text
Strategy Source Authority / Market Refresh historical_asof_view
```

Reason:

```text
It is Opportunity-independent, PIT-bound, hash-backed, Production/Demo/Historical-common,
and directly contains the broker normalization facts.
```

## 9. Authority Priority

Priority:

```text
1. canonical PIT listed-issue metadata
2. Opportunity Authority embedded listed_info as consistency evidence
3. validated Current / Position Campaign metadata as identity cross-check
4. validated PM SELL item listed_info for D8 compatible merge only
5. fail-closed
```

Canonical is above Opportunity because listed issue metadata is a broader fact authority than Opportunity ranking.

## 10. Strategy SELL Producer Contract

Expected D14 flow:

```text
SELL plan generated
↓
canonical PIT listed-info lookup by symbol and business_date
↓
Authority validation
↓
Opportunity embedded listed_info comparison if present
↓
PendingOrderItem.listed_info materialized
↓
pending write / Approval
```

If canonical listed-info fails:

```text
Do not create executable pending.
REVIEW_REQUIRED before Approval.
```

## 11. Temporal / PIT Contract

Requirements:

```text
source business date <= evaluation business_date
future-dated metadata prohibited
historical mode uses run-scoped historical_asof snapshot
production/demo use accepted current Strategy Source Authority
latest-path implicit fallback prohibited
source artifact hash required
source authority binding required
```

D13 does not introduce stale fallback.

## 12. Symbol Normalization

Contract:

```text
input symbol = Runtime Planning security_code / PendingOrderItem.symbol
listed_info.code = J-Quants listed issues Code
broker issue code = Broker normalizer result after validation
```

Fail closed on:

```text
symbol mismatch
multiple rows
no row
unsupported code shape
unknown market
missing required field
```

## 13. Delisting / Current Listed

```text
current_listed=true
  -> executable candidate if all other checks pass

current_listed=false
  -> REVIEW_REQUIRED / execution prohibited by default

current_listed missing
  -> REVIEW_REQUIRED
```

No final-sale-before-delisting exception is designed in D13. If needed, it requires a separate Authority Contract.

## 14. Conflict Contract

Fail closed on:

```text
canonical vs Opportunity code mismatch
market mismatch
product_category mismatch
security_type mismatch
current_listed mismatch
source business date mismatch
accepted/source authority mismatch
symbol normalization mismatch
multiple canonical rows
no canonical row
future-dated row
stale beyond contract
source artifact hash unknown
source Authority unknown
```

Behavior:

```text
pending executableization prohibited
REVIEW_REQUIRED before Approval
original evidence preserved
Submit Guard remains final defense
```

## 15. Missing Authority Contract

```text
Opportunity absent + canonical present
  -> PASS

Opportunity absent + canonical absent
  -> REVIEW_REQUIRED before Approval

Opportunity present + canonical absent
  -> REVIEW_REQUIRED for executable SELL

Both present and equivalent
  -> PASS

Both present and conflicting
  -> REVIEW_REQUIRED
```

## 16. Approval Prevalidation

State contract:

```text
DRAFT:
missing listed_info may be recorded

EXECUTABLE_PENDING:
listed_info required

APPROVED:
listed_info required

SUBMIT:
defensive fail-closed only
```

Primary validation point:

```text
Strategy pending materialization before write_pending_order_plan
```

Secondary validation point:

```text
Approval input / Pending promotion may reject missing listed_info,
but should not become primary listed_info producer.
```

## 17. D8 Conformance

D8 remains valid.

Preserve:

```text
compatible SELL pending identity preservation
listed_info safe merge from new compatible PM SELL item
conflict fail-closed
D8 focused regression
```

D13/D14 must not delete D8. It remains a defense for incomplete compatible pending.

## 18. D12 Conformance

D12 is unrelated and must remain unchanged:

```text
decision_type
pm_decision_id
Strategy PM adapter
Portfolio Construction ADD path
Position Sizing ADD path
BUY_ADD mapping
```

D14 short regression must rerun D12 focused chain.

## 19. D14 Option Comparison

Option A:

```text
Strategy SELL Producer canonical listed-info lookup
```

Judgment:

```text
Recommended
```

Reason:

```text
The first producer creates a complete executable pending item.
```

Option B:

```text
Pending Composition pre-approval enrichment
```

Judgment:

```text
Not primary for D14
```

Option C:

```text
Approval prevalidation enrichment
```

Judgment:

```text
Reject as primary
```

Option D:

```text
Submit Guard late enrichment
```

Judgment:

```text
Reject
```

## 20. D14 Minimal Repair Recommendation

D14 single repair:

```text
Strategy SELL Producer canonical listed-info lookup
```

Primary file candidate:

```text
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py
```

Likely implementation points:

```text
_pending_item_from_strategy_plan
new helper: resolve_canonical_listed_info_for_strategy_pending
```

Do not change:

```text
submit/pipeline.py
broker/issue_code_normalizer.py
portfolio_construction.py
position_sizing.py
position_management.py
pending/composition.py
Phase28-C
Phase28-D12
```

## 21. Focused Fixture Contract

Direct 30410 reproduction:

```text
existing position: 30410
SELL_EXIT plan
Opportunity Authority absent
canonical PIT listed-info present
```

Expected:

```text
Strategy SELL pending generated
listed_info valid
Approval prevalidation PASS
broker issue-code normalization PASS
historical simulated available quantity resolution PASS
```

Additional fixtures:

```text
Opportunity absent / canonical present -> PASS
Opportunity present / canonical present equivalent -> PASS
Opportunity present / canonical conflict -> REVIEW_REQUIRED
Both absent -> REVIEW_REQUIRED before Approval
canonical future-dated -> REVIEW_REQUIRED
canonical stale beyond contract -> REVIEW_REQUIRED
current_listed=false -> REVIEW_REQUIRED
symbol mismatch -> REVIEW_REQUIRED
multiple rows -> REVIEW_REQUIRED
valid ordinary BUY pending -> unchanged
valid ordinary SELL with Opportunity authority -> unchanged
D8 merge fixture -> PASS
D12 PM ADD->BUY_ADD focused chain -> PASS
```

## 22. Short Regression Contract

D14 short validation should include:

```text
Strategy Authority focused listed_info fixtures
30410 Submit/Broker normalization focused fixture
D8 SELL pending authority merge regression
D12 PM ADD propagation focused chain
Phase28-C ADD bridge focused regression
Non-SELL BUY pending unchanged regression
compile
JSON validation
```

No long historical in D14 short validation.

## 23. Production Conformance

D13 design satisfies:

```text
Production / Demo / Historical common design
PIT metadata only
future data prohibited
test-only branch prohibited
fixed metadata fallback prohibited
broker write before Authority prohibited
Submit Guard final defense preserved
Corporate Action responsibility separated
Buy/Sell independence preserved
Pending identity ownership preserved
```

## 24. Risks

Risks for D14:

```text
J-Quants listed_issues lacks explicit security_type column in historical snapshot.
```

D13 resolution:

```text
Use SecType if present; otherwise security_type may be derived from ProdCat
only under an explicit listed-issue contract and with lineage/reason.
This is not symbol-only fixed inference.
```

Risk:

```text
Final sale after delisting may require a future exception.
```

D13 resolution:

```text
Do not implement exception in D14 unless separately designed.
```

## 25. Open Gaps

```text
D14 implementation not yet performed
Summary CLI PM ADD versus BUY_ADD funnel observability remains open
Final-sale-before-delisting exception contract remains future work if needed
```

## 26. Fresh 100BD Contract

Fresh 100BD now:

```text
false
```

Reason:

```text
D13 is design-only.
Fresh 100BD should wait until D14 implementation and short validation pass.
```

After D14:

```text
If D14 short validation passes and no new blocking gap remains,
user/operator may run fresh 100BD.
Do not resume the halted run.
```

## 27. Final Judgment

```text
Primary Judgment:
PHASE28_D13_NON_OPPORTUNITY_LISTED_INFO_AUTHORITY_DESIGN_COMPLETE_PHASE28_D14_READY

Current defect:
Strategy executable SELL pending relies on Opportunity-only listed_info production.

canonical listed_info Primary Authority:
Canonical PIT Listed Issues / Listed Info Artifact via Strategy Source Authority

Secondary Authority:
Opportunity embedded listed_info as consistency evidence only

Authority priority:
canonical PIT listed issues -> Opportunity consistency -> Current/Campaign identity cross-check -> D8 PM SELL merge defense -> fail-closed

PIT / business-date contract:
source business date <= evaluation business_date; no future rows; hash/source authority required

required listed_info fields:
code, market, product_category, security_type, current_listed

Strategy SELL producer responsibility:
materialize valid listed_info before pending write

Approval前validation point:
Strategy pending materialization before write_pending_order_plan

Conflict:
REVIEW_REQUIRED before Approval

Both Authority missing:
REVIEW_REQUIRED before Approval

current_listed=false:
REVIEW_REQUIRED / execution prohibited by default

D14唯一の推奨修理:
Strategy SELL Producer canonical listed-info lookup

Implementation changed:
false

Config / Schema / Threshold changed:
false / false / false

Resume / Fresh / Long Historical:
false / false / false
```

## 28. Phase28-D14 Entry Decision

```text
APPROVED
```

Entry basis:

```text
canonical listed-info Authority identified
Production / Demo / Historical availability confirmed at design level
PIT binding confirmed
required fields confirmed
symbol normalization contract defined
conflict contract defined
missing Authority fail-closed defined
current_listed handling defined
Approval-before-Submit validation defined
D8 merge preserved
D12 ADD chain preserved
D14 repair limited to one target
Submit Guard and Broker normalizer unchanged
Historical-only implementation not required
30410 focused fixture defined
fresh 100BD held until D14 short validation
```

Deliverables:

```text
docs/phase_reports/phase28_d13_strategy_executable_sell_non_opportunity_listed_info_authority_repair_design.md
reports/phase_reports/phase28_d13_strategy_executable_sell_non_opportunity_listed_info_authority_repair_design.json
reports/phase28_d13_strategy_executable_sell_non_opportunity_listed_info_authority_repair_design/
```
