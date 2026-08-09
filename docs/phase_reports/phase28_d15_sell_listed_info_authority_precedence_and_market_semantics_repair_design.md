# Phase28-D15: SELL listed_info Authority Precedence and Market Semantics Repair Design

## 1. Executive Summary

Primary Judgment:

```text
PHASE28_D15_SELL_LISTED_INFO_AUTHORITY_PRECEDENCE_DESIGN_COMPLETE_PHASE28_D16_READY
```

Phase28-D16 Entry Decision:

```text
APPROVED
```

D15 confirms that the 2023-04-10 `43880` SELL planning halt is not a missing-canonical-data issue after D14. It is a D8 reconciliation equivalence-contract issue:

```text
existing Strategy SELL pending:
  listed_info_authority = canonical_pit_listed_issues
  market = グロース

new PM SELL item:
  basic PM SELL metadata
  market = 東証

D8 current comparison:
  exact dict-equivalence over code / market / product_category / security_type / current_listed
  -> market mismatch
  -> PENDING_SELL_LISTED_INFO_AUTHORITY_CONFLICT
```

Correct contract:

```text
Canonical PIT listed_info is the primary listed-issue fact authority.
PM SELL basic listed_info is secondary compatibility / identity evidence.
```

Recommended D16 repair:

```text
Option A: add listed_info Authority precedence to the D8 listed_info conflict evaluator only.
```

D15 performed no implementation, config, schema, threshold, resume, fresh run, or long historical run.

## 2. Scope

In scope:

- 2023-04-10 / 43880 SELL listed_info conflict diagnosis as design input
- market semantic audit
- listed_info source authority classification
- authority precedence contract
- core identity contract
- D8 equivalence contract update design
- D16 one-repair recommendation
- focused fixture and regression contract

Out of scope:

- Pending Composition implementation
- D14 Strategy Authority changes
- Sell Planning changes
- Submit Guard / Broker / Approval changes
- Portfolio Construction / Position Sizing / Runtime Planning changes
- Phase28-C / Phase28-D12 changes
- config / schema / threshold changes
- fresh 100BD / resume / long historical

## 3. Accepted Evidence

Run:

```text
run_id: runtime-test-historical-smoke-20260806T041925026284Z
start_date: 2023-04-03
halt_date: 2023-04-10
halt_stage: sell_planning
exit_code: 20
```

Runtime manifest reason:

```text
sell planning pipeline review required:
PENDING_SELL_LISTED_INFO_AUTHORITY_CONFLICT;
PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED
```

Pending continuity evidence:

```text
status: REVIEW_REQUIRED
reason: PENDING_SELL_LISTED_INFO_AUTHORITY_CONFLICT;PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED
pending_plan_id: pending-strategy-plan-historical-2023-04-10-0edeecd2e3ac3727
```

Relevant local evidence:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260806T041925026284Z/daily/2023-04-10/sell_planning/runtime_manifest.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260806T041925026284Z/daily/2023-04-10/sell_planning/pending_continuity_evidence.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260806T041925026284Z/daily/2023-04-10/strategy/input_manifest.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260806T041925026284Z/daily/2023-04-10/market_refresh/inputs/historical_asof/2023-04-10/raw/jquants/listed_issues/data.parquet
```

43880 canonical listed_issues row:

```text
Date: 2023-04-10
Code: 43880
CoName: エーアイ
Mkt: 0113
MktNm: グロース
ProdCat: 011
source hash: 719a9388677e1e770fc4048d8c3d08feb852a07b386d6d9746c8f1cf4b920b15
```

Accepted item comparison:

```text
existing Strategy pending:
  pending_item_id: strategy-48c2f0737936a341d096
  authority type: CANONICAL_PIT_LISTED_ISSUE_AUTHORITY
  market: グロース

new PM SELL item:
  pending_item_id: opi-sell-exit-pm-43880-001
  authority type: PM_BASIC_EXECUTION_METADATA
  market: 東証

matching fields:
  code = 43880
  product_category = 011
  security_type = 011
  current_listed = true
```

## 4. Documents Reviewed

```text
docs/phase_reports/phase28_d14_strategy_sell_canonical_listed_info_authority_implementation.md
docs/phase_reports/phase28_d13_strategy_executable_sell_non_opportunity_listed_info_authority_repair_design.md
docs/phase_reports/phase28_d8_compatible_sell_pending_required_authority_merge_implementation.md
docs/phase_reports/phase28_d7_sell_pending_required_authority_merge_repair_design.md
docs/phase_reports/phase28_d12_pm_add_strategy_position_management_adapter_repair_implementation.md
docs/02_architecture/runtime_architecture_v2.md
docs/02_architecture/strategy_architecture_v1.md
docs/01_requirements/phase_roadmap.md
```

## 5. Current Defect

Current D8 evaluator:

```text
_equivalent_listed_info(left, right)
  keys = code, market, product_category, security_type, current_listed
  require exact string equality for all keys
```

Code evidence:

```text
src/ai_fund_lab_v2/runtime_v2/pending/composition.py:640-657
src/ai_fund_lab_v2/runtime_v2/pending/composition.py:720-724
```

Defect:

```text
The D8 compatible SELL merge compares Canonical PIT market segment and PM basic execution venue as the same semantic field with equal authority.
```

This causes a false conflict:

```text
グロース != 東証
-> CONFLICTING_LISTED_INFO
-> REVIEW_REQUIRED
```

## 6. Market Semantics Audit

Canonical `market`:

```text
source: J-Quants listed_issues MktNm
semantic: listed market segment / market name in listed-issue master
examples in 2023-04-10 snapshot: プライム, スタンダード, グロース, TOKYO PRO MARKET, その他
PIT status: Strategy Source Authority PASS
Production/Historical semantic: same logical listed_issues source, historical uses run-scoped as-of snapshot
```

PM SELL `market`:

```text
source: src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py
value: fixed "東証"
semantic: execution venue / broker-compatible exchange-level metadata
PIT authority: no listed-issue fact authority
classification: PM_BASIC_EXECUTION_METADATA
```

Broker normalizer:

```text
src/ai_fund_lab_v2/broker/issue_code_normalizer.py
accepts: プライム, スタンダード, グロース, 東証, 東京証券取引所, Tokyo Stock Exchange, TSE
maps all accepted TSE names to broker_market_code = 00
```

Consumer meaning:

```text
D8 currently uses market as an equality field.
Broker uses market as exchange/broker-market-code mappability.
Submit Guard consumes pending_item.listed_info for broker normalization.
Approval does not interpret market semantics.
Pending schema requires listed_info presence but does not split exchange and market segment.
```

## 7. listed_info Authority Classification

Authority classes:

```text
CANONICAL_PIT_LISTED_ISSUE_AUTHORITY
OPPORTUNITY_EMBEDDED_CANONICAL_EVIDENCE
PM_BASIC_EXECUTION_METADATA
CURRENT_POSITION_IDENTITY_EVIDENCE
CAMPAIGN_IDENTITY_EVIDENCE
UNKNOWN_AUTHORITY
```

43880 classification:

```text
existing Strategy pending: CANONICAL_PIT_LISTED_ISSUE_AUTHORITY
new PM SELL item: PM_BASIC_EXECUTION_METADATA
```

## 8. Authority Precedence

Precedence:

```text
CANONICAL_PIT_LISTED_ISSUE_AUTHORITY
>
OPPORTUNITY_EMBEDDED_CANONICAL_EVIDENCE
>
PM_BASIC_EXECUTION_METADATA
>
CURRENT_POSITION_IDENTITY_EVIDENCE / CAMPAIGN_IDENTITY_EVIDENCE
>
UNKNOWN_AUTHORITY
```

For D8 compatible SELL reconciliation:

```text
existing canonical valid + new basic valid + core identity match + market-only semantic granularity difference
-> PRESERVE_EXISTING_CANONICAL
-> no REVIEW_REQUIRED
```

Canonical listed_info must never be overwritten by PM basic metadata.

## 9. Core Identity Fields

Authority precedence may be applied only after exact-match core identity validation passes:

```text
normalized symbol
listed_info.code
side
business_date
target_session_date
product_category
security_type
current_listed
compatible SELL lineage
accepted generation when present
position campaign when available
pending state not committed/submitting/post-send
partial fill absent
```

If any of these fail, D8 must fail closed regardless of market semantics.

## 10. Market Semantic Model

Options considered:

```text
Option A: Authority precedence only
Option B: schema-level market split into exchange / market_segment
Option C: explicit compatibility mapping for 東証 vs プライム/スタンダード/グロース
```

Primary recommendation:

```text
Option A
```

Reason:

- It is the minimal D16 repair.
- It preserves D14 Canonical PIT Authority.
- It does not require schema or consumer changes.
- It solves 43880 directly.
- It still treats canonical-vs-canonical market mismatch as a true conflict.

Option B is semantically clean but too broad for D16 because it implies schema and consumer migration. Option C risks embedding a new fixed mapping authority and should be avoided unless future non-TSE venues require explicit compatibility tables.

## 11. listed_info Equivalence

Field-level contract:

| Field | Rule |
|---|---|
| code | REQUIRE_EXACT_MATCH |
| product_category | REQUIRE_EXACT_MATCH |
| security_type | REQUIRE_EXACT_MATCH |
| current_listed | REQUIRE_EXACT_MATCH |
| market | AUTHORITY_PRECEDENCE / SEMANTIC_CLASSIFICATION |
| lineage metadata | SOURCE-SPECIFIC / NOT CROSS-SOURCE VALUE CONFLICT |
| source hash/path | NOT CROSS-SOURCE EQUIVALENCE FIELD |

Canonical lineage metadata missing from a PM basic item is not a conflict.

## 12. True Conflict Contract

Remain REVIEW_REQUIRED:

```text
code mismatch
symbol mismatch
side mismatch
product_category mismatch
security_type mismatch
current_listed mismatch
business date mismatch
target session mismatch
accepted generation mismatch
incompatible SELL lineage
position campaign mismatch when both present
canonical vs canonical market mismatch
canonical source hash mismatch
canonical authority status not PASS
multiple canonical rows
unknown listed_info authority
submitted / submitting / post-send pending
partial fill evidence
```

Market mismatch remains true conflict when both sides are canonical or when either side has unknown authority.

## 13. Non-conflict Contract

Non-conflict:

```text
existing Canonical PIT listed_info
+ new PM basic listed_info
+ code/product_category/security_type/current_listed match
+ symbol/date/session/lineage/generation/state gates pass
+ only market differs because canonical market segment is compared to PM exchange-level value
-> PRESERVE_EXISTING_CANONICAL
```

43880 expected result:

```text
existing listed_info preserved:
  market = グロース
secondary PM value recorded:
  market = 東証
reason_code:
  PENDING_SELL_CANONICAL_LISTED_INFO_PRESERVED_OVER_BASIC_MARKET_METADATA
```

## 14. D8 Contract Update

D8 classifier structure remains:

```text
classify
-> preserve / merge / review
```

D16 target:

```text
listed_info equivalence / conflict evaluator only
```

Do not change:

```text
pending identity
compatible SELL lineage
no-signal overwrite guard
submitted / partial-fill fail-closed behavior
original pending preservation on review
BUY / SELL independence
```

Required evidence additions:

```text
existing_authority_type
new_authority_type
authority_precedence
market_existing_value
market_new_value
market_semantic_relation
core_identity_match_status
canonical_preserved
conflict_status
resolution_action
reason_code
```

## 15. D14 Conformance

D14 remains unchanged:

```text
Strategy SELL
-> Canonical PIT Listed Issues
-> listed_info materialized
```

D16 must preserve existing canonical listed_info and must not overwrite it with PM basic metadata.

## 16. D12 / Phase28-C Conformance

D12 PM ADD propagation remains unchanged.

Phase28-C ADD bridge remains unchanged.

D16 validation should include focused D12 and Phase28-C regressions only.

## 17. D16 Option Comparison

Option A:

```text
D8 listed_info conflict evaluator adds Authority precedence.
```

Judgment:

```text
PRIMARY_RECOMMENDATION
```

Option B:

```text
PM SELL producer also looks up canonical market.
```

Judgment:

```text
REJECT_FOR_D16_SCOPE
```

Option C:

```text
Schema split: exchange / market_segment.
```

Judgment:

```text
REJECT_FOR_D16_SCOPE
```

## 18. D16 Minimal Repair Recommendation

Single D16 repair:

```text
Add authority-aware listed_info comparison to Pending Composition D8 merge.
```

Suggested target:

```text
src/ai_fund_lab_v2/runtime_v2/pending/composition.py
```

Suggested helper boundary:

```text
_listed_info_authority_type(...)
_listed_info_conflict_or_precedence_resolution(...)
```

Expected action for 43880:

```text
PRESERVE_EXISTING_CANONICAL
```

## 19. Approval / Hash

Canonical preserve case:

```text
pending_item_id: preserved
existing item content: preserved
existing item hash: preserved
pending plan hash: preserved unless evidence artifact is separate
new PM item: secondary evidence only
approval: no post-approval mutation
plan hash race detection: unchanged
```

If future canonical enrichment is introduced, it must follow the existing D8 pre-approval hash contract.

## 20. Provenance

Minimum D16 provenance:

```text
existing_authority_type
new_authority_type
authority_precedence
market_existing_value
market_new_value
market_semantic_relation
secondary_market_value
secondary_authority_type
canonical_authority_preserved
core_identity_match_status
conflict_status
resolution_action
reason_code
```

## 21. Focused Fixture Contract

43880 reproduction fixture:

```text
existing:
  symbol: 43880
  side: SELL
  listed_info_authority: canonical_pit_listed_issues
  market: グロース

new:
  symbol: 43880
  side: SELL
  PM basic listed_info
  market: 東証

matching:
  code/product_category/security_type/current_listed/symbol/date/lineage

expected:
  PASS
  existing identity preserved
  existing canonical listed_info preserved
  no REVIEW_REQUIRED
```

True conflict fixtures:

```text
code mismatch -> REVIEW_REQUIRED
product_category mismatch -> REVIEW_REQUIRED
security_type mismatch -> REVIEW_REQUIRED
current_listed mismatch -> REVIEW_REQUIRED
canonical vs canonical market mismatch -> REVIEW_REQUIRED
unknown authority -> REVIEW_REQUIRED
business date mismatch -> REVIEW_REQUIRED
submitted / partial fill -> REVIEW_REQUIRED
```

## 22. Short Regression

D16 short regression contract:

```text
D8 existing null / new valid -> FILL_MISSING_FROM_NEW
D8 both valid equivalent -> PRESERVE_EXISTING
D8 both null -> REVIEW_REQUIRED
D14 30410 canonical lookup -> PASS
D12 PM ADD propagation -> PASS
Phase28-C BUY_ADD chain -> PASS
ordinary BUY unchanged
ordinary SELL unchanged
compile
JSON validation
```

No fresh 100BD during D16 implementation validation unless explicitly requested after short validation.

## 23. Risks

Risks:

```text
If PM basic market later becomes a true listed-market authority, authority classification must be updated.
If non-TSE venues become active, Option C or schema split may become necessary.
If unknown authority is treated as basic, true conflicts could be missed.
```

Mitigation:

```text
Unknown authority remains REVIEW_REQUIRED.
Canonical-vs-canonical mismatch remains REVIEW_REQUIRED.
Core identity fields remain exact-match.
```

## 24. Open Gaps

Open gaps:

```text
None blocking D16.
```

Deferred:

```text
Schema split into exchange / market_segment may be a future architecture cleanup, not a D16 prerequisite.
```

## 25. Fresh 100BD Contract

Do not resume:

```text
runtime-test-historical-smoke-20260806T041925026284Z
```

D15 is design-only; no fresh 100BD was run.

After D16 implementation and short validation PASS:

```text
Run a new fresh 100BD restart from the selected start date.
```

## 26. Final Judgment

```text
Primary Judgment: PHASE28_D15_SELL_LISTED_INFO_AUTHORITY_PRECEDENCE_DESIGN_COMPLETE_PHASE28_D16_READY
Phase28-D16 Entry Decision: APPROVED
Current defect: D8 compares canonical market segment and PM execution venue as same-authority market values.
Canonical Authority classification: CANONICAL_PIT_LISTED_ISSUE_AUTHORITY
PM basic Authority classification: PM_BASIC_EXECUTION_METADATA
グロース semantic: J-Quants listed_issues MktNm, listed market segment/name.
東証 semantic: sell_pipeline fixed exchange-level broker-compatible metadata.
Authority precedence: Canonical PIT Listed Issues > PM basic metadata.
Canonical preservation action: PRESERVE_EXISTING_CANONICAL
D16唯一の推奨修理: D8 listed_info conflict evaluator authority precedence.
Implementation changed: false
Config changed: false
Schema changed: false
Threshold changed: false
Resume executed: false
Fresh run executed: false
Long Historical executed: false
```

## 27. Phase28-D16 Entry Decision

```text
APPROVED
```

All D16 entry conditions are met:

```text
Canonical / PM basic Authority classification complete
market semantics complete
Authority precedence complete
core identity exact-match fields complete
true conflict conditions complete
non-conflict conditions complete
canonical preserve contract complete
D8 classifier structure preserved
hash / approval contract complete
D14 unchanged
D12 / Phase28-C unchanged
D16 repair limited to one target
43880 fixture defined
true conflict fixtures defined
fresh 100BD restart requirement documented
Historical-specific implementation not required
```
