# Strategy Architecture Consolidation Review

## Status

This document records the Phase23-AP read-only consolidation audit. It does not change the Strategy Architecture v1 contract. Contract changes require a later implementation/design task.

## Current Effective Architecture

Current Strategy Runtime behavior is a two-layer path.

```text
Strategy artifact generation
  -> Strategy Runtime Shadow artifacts
  -> Runtime Planning artifact
  -> Phase23-I Strategy Planning Authority consumer
  -> order_plan / pending_order_plan
```

The Strategy producers are implemented as common code and are invoked from `strategy.shadow_runtime.generate_strategy_shadow_for_day()`. The morning runtime path can then call `runtime_v2.planning.strategy_authority.activate_strategy_planning_authority()` to consume `runtime_planning.json` and `position_sizing.json`.

Existing Phase23-AO short validation is not a fresh Runtime run. Existing runs from 2026-07-29 predate AO runtime validation and must not be treated as AO production proof.

## Canonical Authorities After Phase23-AO

| Value | Current canonical owner | Review |
| --- | --- | --- |
| market regime | Market Context | KEEP |
| corporate event facts | Corporate Event Authority | KEEP |
| opportunity ranking | Opportunity AI / Buy AI producer | KEEP |
| target position count | Dynamic Position Count | MERGE into Portfolio Policy recommended |
| target gross exposure | Dynamic Cash / Exposure | MERGE into Portfolio Policy recommended |
| target membership | Portfolio Construction | KEEP |
| target weight | Portfolio Construction | KEEP |
| target notional | Position Sizing | KEEP |
| quantity candidate / delta | Position Sizing | KEEP |
| planning intent / side | Runtime Planning | MODIFY to pure mapper |
| pending materialization | Strategy Planning Authority | MODIFY to pure consumer/materializer |

## Identified Duplication

- Portfolio Policy declares Strategy target posture, while Dynamic Position Count and Dynamic Cash / Exposure generate concrete target count and exposure as standalone artifacts.
- Capital Deployment is generated after Position Sizing, while Position Sizing receives a placeholder saying Capital Deployment is downstream. This indicates an order and responsibility tension.
- Runtime Planning and Strategy Planning Authority both filter unresolved/no-action/quantity cases. The boundary should be simplified so Runtime Planning maps canonical strategy intent and Strategy Planning Authority only materializes pending/order-plan evidence.
- Candidate / Opportunity Compatibility is a foundation-era standalone compatibility layer and is not part of the active runtime call path.
- `quality_score`, `allocation_quality_score`, and legacy aliases are now noncanonical observability after Phase23-AO and should not remain decision-facing.

## KEEP / MODIFY / MERGE / REMOVE

KEEP:

- Market Context
- Corporate Event Authority
- Portfolio Construction after Phase23-AO
- Position Sizing after Phase23-AO
- Strategy Runtime Shadow generation as run-scoped artifact materialization
- Strategy Input Materialization
- Strategy Status Contract

MODIFY:

- Portfolio Policy: clarify whether it owns concrete targets or only posture.
- Position Management: merge base and regime/event producer modes into one PM authority path.
- Runtime Planning: reduce to pure intent mapper.
- Strategy Planning Authority: reduce to validation and pending materialization.
- Strategy Observability: ensure warnings do not become HALT unless the contract says so.

MERGE:

- Dynamic Position Count into Portfolio Policy concrete target-count resolver.
- Dynamic Cash / Exposure into Portfolio Policy concrete exposure/cash resolver.
- Capital Deployment execution feasibility into Runtime Planning / Strategy Planning Authority.

REMOVE candidates:

- Candidate / Opportunity Compatibility standalone layer after tests migrate to direct producer/consumer validation.
- Legacy `quality_score` decision aliases after deprecation evidence.
- Legacy Morning AI planning path after Strategy Planning Authority is accepted and rollback gates pass.

## Recommended Simplified Architecture

```text
Market Context
Corporate Event Authority
  -> Portfolio Policy with target count / exposure resolvers
  -> Candidate / Opportunity Ranking
  -> Position Management
  -> Portfolio Construction target_weight authority
  -> Position Sizing notional / quantity candidate
  -> Runtime Planning pure intent mapper
  -> Strategy Planning Authority pending materializer
```

No new component is required for this simplification. The recommended work is consolidation, merge, and retirement of duplicated paths.

## Rebuild Decision

```text
CONSOLIDATE_CURRENT_STRATEGY_ARCHITECTURE
```

Limited rebuild is not recommended. The main problems are authority split, artifact proliferation, and legacy path leakage, not an irreparable component model.

## Implementation Sequence

1. Freeze Phase23-AO target weight boundary as canonical.
2. Merge Dynamic Position Count and Dynamic Cash / Exposure into Portfolio Policy internals or a single Portfolio Policy concrete-target artifact.
3. Merge Capital Deployment execution feasibility into Runtime Planning / Strategy Planning Authority.
4. Simplify Runtime Planning to pure intent mapping.
5. Retire Candidate / Opportunity Compatibility and legacy score aliases after regression evidence.
6. Only then consider fresh Runtime validation.

## Phase23-AQ / AR Implementation Update

Phase23-AQ implemented step 2 by making Portfolio Policy the canonical owner for `target_position_count`, `target_gross_exposure`, and `cash_reserve`. Dynamic Position Count and Dynamic Cash / Exposure are no longer standalone Strategy decision authorities in the Runtime call path.

Phase23-AR implements steps 3 and 4 for the planning chain. Capital Deployment is no longer a canonical standalone public decision stage. Any retained Capital Deployment artifact is classified as `NON_CANONICAL_OBSERVABILITY` or delayed-retirement evidence and does not affect Runtime Planning output. Runtime Planning consumes Position Sizing `target_quantity_candidate`, `quantity_delta_candidate`, and `quantity_status`, then maps them to `planning_intent`, `order_side_intent`, `planned_quantity`, `no_order_reason`, and `planning_reason`.

Strategy Planning Authority is the pending materializer. It validates artifact presence, schema, temporal authority, lineage/hash, symbol-level plan, execution feasibility, and `planned_quantity`; it does not recompute allocation, target notional, lot rounding, or quantity from price.
