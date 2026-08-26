# Strategy Intelligence Data Contract v1

Created: 2026-08-16

## 1. Scope

This document defines the data, schema, freshness, provenance, missingness, and
leakage contracts for Strategy Intelligence.

It is subordinate to:

- [Strategy Architecture v1](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/strategy_architecture_v1.md)
- [Strategy Intelligence Architecture v1](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/strategy_intelligence_architecture_v1.md)

No implementation is authorized by this document.

## 2. Production-Eligible PIT Inputs

Production-eligible inputs must be knowable as of the business date being
evaluated.

| Input family | Status | Contract |
|---|---|---|
| Adjusted OHLCV | available | PIT bars only, no latest fallback |
| Volume / traded value | available | PIT only; missing degrades sufficiency |
| Listed/product state | available basic authority | fact gate where authoritative |
| Corporate actions | partial | fact authority when available; missing coverage recorded |
| Alert/supervision/delisting warning | incomplete | data foundation dependency unless authoritative source exists |
| TOB/material event | incomplete | data foundation dependency unless authoritative source exists |
| Market context/regime | available | PIT regime only, no future regime |
| Sector / relative strength | partial/opaque | explicit status required; do not fabricate sector data |
| Candidate / opportunity model score | available | uncalibrated relative model evidence only |
| Current / Ledger / Campaign state | available | only current and past observed state |

## 3. Prohibited Runtime Inputs

Runtime / Production Strategy must never consume:

```text
future return
future price
future MFE
future MAE
final campaign outcome
Historical result
Paper Ledger performance
selected/bought future outcome
future regime
audit judgment
test result
final return
```

Offline research labels must be physically and semantically separated from
production inputs.

## 4. Canonical Artifact

First migration target:

```text
strategy/strategy_intelligence.json
```

Required top-level shape:

```text
{
  "schema_version": "strategy_intelligence.v1",
  "semantic_version": "1.2.0",
  "as_of_business_date": "YYYY-MM-DD",
  "generated_at": "...",
  "producer": "...",
  "pit_boundary": {
    "market_data_as_of": "YYYY-MM-DD",
    "current_state_as_of": "YYYY-MM-DD",
    "future_information_used": false
  },
  "source_evidence": {},
  "run_level_sufficiency": {},
  "eligibility_event_facts": {},
  "symbol_intelligence": {},
  "shadow_decision_comparison": {}
}
```

## 5. Symbol-Level Contract

Each symbol should expose:

```text
symbol_intelligence:
  <symbol>:
    eligibility:
      status
      disqualifying_facts
      review_required_facts
      event_coverage_status
      missing_required_authorities
    continuation_quality:
      status
      trend_health
      persistence
      acceleration_state
      exhaustion_risk
      participation_quality
      relative_strength
      regime_compatibility
      evidence_sufficiency
      confidence
    downside_risk:
      status
      reversal_risk
      volatility_risk
      exhaustion_risk
      participation_risk
      microstructure_risk
      regime_risk
      event_uncertainty
      evidence_sufficiency
      confidence
    expected_edge:
      status
      edge_contract
      calibration_status
      continuation_opportunity
      payoff_asymmetry
      downside_distribution_proxy
      opportunity_cost_context
      turnover_consideration
      incremental_edge_for_add
      relative_edge_for_hold_vs_replacement
    lifecycle_context:
      current_position_state
      semantic_position_state
      position_campaign_id
      campaign_opened_date
      campaign_closed_date
      campaign_status
      current_position_authority_status
      campaign_identity_authority_status
      current_authority_owner
      campaign_authority_owner
      semantic_entry_type
      current_quantity
      current_market_value
      quantity_basis
      valuation_price_basis
      observed_campaign_mfe
      observed_giveback
      buy_history_summary
      add_history_summary
      reduce_history_summary
      sell_history_summary
    current_decision:
      buy_quality_action
      portfolio_membership_intent
      pm_action
      runtime_planning_action
      current_decision_authority_unchanged
    profit_protection_evidence:
      status
      embedded_return_observed
      observed_campaign_mfe
      observed_giveback
      continuation_deterioration_connection
      downside_risk_rise_connection
      future_mfe_used
      future_peak_used
      not_action_authority
    strategy_intelligence_interpretation:
      state
      lifecycle_context_type
      current_action_preserved
      shared_intelligence_became_action_authority
      shadow_output_connected_to_production_action_authority
    provenance:
      feature_refs
      model_generation_refs
      current_refs
      event_refs
      missing_inputs
      future_information_used
```

## 6. Status Vocabulary

Allowed high-level evidence status vocabulary:

```text
PASS
REVIEW_REQUIRED
INSUFFICIENT_EVIDENCE
MISSING_REQUIRED_AUTHORITY
NOT_APPLICABLE
SHADOW_ONLY
```

Dimension-level semantic vocabulary should use interpretable states such as:

```text
SUPPORTIVE
MIXED
WEAK
ELEVATED_RISK
HIGH_RISK
UNKNOWN
INSUFFICIENT
```

Phase30-I freezes no optimized numeric thresholds.

## 7. Missingness Contract

Missing data must be explicit.

| Missing class | Behavior |
|---|---|
| Missing required fact authority | fail closed or review required |
| Missing optional evidence | degrade confidence / sufficiency |
| Missing event coverage source | event uncertainty, not safe |
| Missing sector data | relative strength data foundation insufficient |
| Missing current/ledger state for held symbol | fail closed |
| Missing valuation basis | fail closed under valuation/basis contract |

Phase30-L clarifies relative strength authority:

- Stock-vs-market relative strength may be `PARTIALLY_CONNECTED` only when PIT
  symbol returns and PIT market equal-weight returns are both present.
- Rank, opportunity score, and BUY Quality relative-opportunity score must not
  be re-labeled as relative strength.
- Stock-vs-sector and sector-vs-market require explicit sector authority and a
  symbol-sector join. Until then the final classification is not `CONNECTED`.

## 8. Freshness Contract

Every symbol-level section must declare:

- source date,
- generated date/time,
- as-of business date,
- accepted generation id where model evidence is used,
- whether previous-day evidence was reused,
- whether latest fallback was used.

Latest fallback for Strategy Intelligence is not allowed unless a separate
Architecture contract authorizes it. If current-day evidence is unavailable,
the section must be insufficient or review-required.

## 9. Lineage Contract

Every production dimension must be traceable:

```text
Source
  -> PIT Authority
  -> Feature
  -> Strategy Intelligence Artifact
  -> Consumer
  -> Decision influence
```

Completion is not satisfied by a producer alone. Completion requires:

```text
producer
-> artifact
-> schema
-> adapter
-> consumer
-> decision influence
-> persistence if required
-> next-day consumer
```

This protects against the Phase30-G failure mode where useful intelligence
existed but had zero effective decision weight.

## 10. Research Labels

Allowed offline labels:

- forward return,
- MFE,
- MAE,
- severe loss flag,
- healthy Winner flag,
- missed Winner flag,
- final campaign outcome.

They must never appear in `strategy/strategy_intelligence.json` except inside
explicit offline research artifacts outside Runtime production input paths.

## 11. Current / Persistence Boundary

Market-derived CQ and Downside Risk are recomputed daily. Current is not the
authority for fresh market intelligence.

Persistable campaign-relative state:

- entry thesis metadata with provenance,
- observed high-water mark using past/current prices only,
- observed MFE and giveback,
- ADD history,
- prior intelligence descriptor for transition analysis.

Phase30-N clarifies Current and Campaign ownership:

- Current owns current position state: current quantity, current market value,
  average price, quantity basis, valuation price basis, and valuation-facing
  state.
- The canonical campaign identity authority is
  `positions/position_campaigns.json`.
- Strategy Intelligence may join Current and Campaign state by symbol plus the
  canonical active/open campaign state.
- If a campaign is closed by an EXIT event on the same business date, Strategy
  Intelligence may use that same-day closed canonical campaign as EXIT-day
  lifecycle context. The next day it must not be treated as an open current
  holding.
- Strategy Intelligence must not invent a duplicate campaign identifier.
- If canonical campaign identity is absent or conflicting, lifecycle context
  must report explicit missingness or `CAMPAIGN_AUTHORITY_CONFLICT`; it must
  not silently fall back to a heuristic identity.
- Runtime-owned BUY fills that have already materialized into decision-time
  Current and an exactly matching canonical OPEN row in
  `positions/position_campaigns.json` must propagate that row's
  `position_campaign_id`, opened business date, and `campaign_status` into
  Strategy Intelligence lifecycle context. Missing, ambiguous, CLOSED-only,
  symbol-mismatched, or quantity-conflicting campaign evidence remains
  fail-closed; Strategy Intelligence must not synthesize campaign identity from
  symbol/date heuristics.

## 12. Phase30-P Production Interpretation Boundary

`strategy_intelligence_interpretation` is lifecycle-aware Production evidence.
It must not replace the current action authority owned by Portfolio
Construction, Position Sizing, Position Management, or Runtime Planning.

The legacy `proposed_decision_if_authorized` field is retired. Production
consumers must read `strategy_intelligence_interpretation` and the underlying
eligibility / CQ / risk / edge / lifecycle evidence directly.

Lifecycle-specific interpretation must preserve these distinctions:

- `BUY_WAIT` is interpreted as BUY_WAIT context, not BUY_NEW evidence.
- `ADD` / `BUY_ADD` is interpreted as incremental ADD-worthiness, not ordinary
  HOLD-worthiness.
- PM `REDUCE` and `EXIT` are interpreted as current PM authority evidence, not
  as HOLD.
- Profit Protection evidence may connect observed embedded return, observed
  MFE/giveback, CQ deterioration, and downside-risk rise, but it must not use
  future MFE, future peaks, final campaign outcomes, or fixed optimized profit
  thresholds.

Persistence requires owner, update rule, idempotency, schema migration, and
next-day consumer tests.
