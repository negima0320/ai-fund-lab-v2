# Phase27-A3 Re-entry Causality and Selection Validity Diagnosis

## Judgment

```text
PHASE27_A3_REENTRY_PARTIALLY_EXPLAINED
```

Task classification:

```text
Phase: Phase27
Task ID: Phase27-A3
Task Type: Observability Only / Read-only Performance Diagnosis
Parent Task: Phase27-A
Predecessor: Phase27-A1, Phase27-A2
Implementation Changed: false
Historical Test: NOT EXECUTED
```

This task diagnosed why A2-confirmed re-entry losses occurred. It did not
change Strategy, BUY Quality, Opportunity, Candidate, Portfolio Policy,
Position Sizing, Planning, Submit, Safety, PM, Exit, or Re-entry logic. It did
not execute fresh-run, resume, Historical, 100BD, or long regression.

## Inputs

Baseline:

```text
run_id: runtime-test-historical-smoke-20260804T074611098414Z
period: 2023-01-04 through 2023-05-31
```

Primary inputs:

```text
reports/phase27_a2_100bd_baseline_attribution_and_hypothesis_evidence_extraction/
reports/runtime_tests/runs/runtime-test-historical-smoke-20260804T074611098414Z/
```

Generator:

```text
tools/phase27_analysis/phase27_a3_reentry_diagnosis.py
```

Generator boundary:

```text
Observability Only
Post-hoc Human Review Only
Not a Strategy Input
Run-scoped Evidence Only
No .runtime Read
```

## Outputs

Output directory:

```text
reports/phase27_a3_reentry_causality_and_selection_validity_diagnosis/
```

Generated files:

```text
campaign_timelines.json
initial_vs_reentry.json
candidate_competition.json
exit_reentry_interaction.json
reentry_classification.json
root_cause_separation.json
summary.json
test_results.json
```

## Executive Finding

A3 does not prove that "re-entry logic is wrong" as a single cause.

The evidence instead supports a mixed explanation:

- Some re-entries were valid within the observed Quality/PC funnel.
- Most re-entries were not the highest-ranked available opportunity within the
  Quality/PC funnel.
- Several loss-making re-entries occurred immediately after an exit, consistent
  with whipsaw behavior.
- BUY Quality, Opportunity Rank, Portfolio Construction, and Exit timing
  interacted; no single component alone explains all losses.

Overall:

```text
REENTRY_PARTIALLY_EXPLAINED_BY_WHIPSAW_AND_SELECTION
```

## Campaign Coverage

Observed campaign count:

```text
All campaigns: 25
Re-entry campaigns: 11
```

Re-entry classification:

| Classification | Count |
|---|---:|
| VALID_REENTRY | 1 |
| QUESTIONABLE_REENTRY | 6 |
| LIKELY_WHIPSAW | 3 |
| INSUFFICIENT_EVIDENCE | 1 |

## Hypothesis A-D

| Hypothesis | Judgment | Evidence |
|---|---|---|
| A: Re-entry decisions were appropriate, losses were subsequent market movement | PARTIALLY_SUPPORTED | 93180 `0004` was Rank 1, Quality 0.801402, and profitable. Some fast re-entries were also profitable. |
| B: Re-entry decisions were not superior opportunities | PARTIALLY_SUPPORTED | 10 of 11 re-entry campaigns were not highest-ranked within the Quality/PC funnel. Full candidate universe remains insufficient. |
| C: Exit behavior caused valid re-entry to become loss-making | PARTIALLY_SUPPORTED | 3 campaigns were classified `LIKELY_WHIPSAW`, with 1BD exit-to-re-entry interval and subsequent loss. |
| D: Opportunity / Quality / PC interaction caused repeated poor entries | PARTIALLY_SUPPORTED | Both FULL and REDUCED re-entries include winners and losers; selected re-entry sometimes had better-ranked available alternatives excluded by PC/sizing/no-action reasons. |

## Re-entry Campaign Classification

| Symbol | Campaign | Entry Date | Rank | Quality | Interval BD | PnL | Competition | Exit Interaction | Classification |
|---:|---|---|---:|---:|---:|---:|---|---|---|
| 76470 | `pc-66d9ba285c89ec9b-76470-0002` | 2023-04-26 | 4 | 0.764331 | 64 | 0 | NO_NOT_HIGHEST_WITHIN_QUALITY_PC_FUNNEL | VALID_TREND_REENTRY | INSUFFICIENT_EVIDENCE |
| 93180 | `pc-66d9ba285c89ec9b-93180-0002` | 2023-01-31 | 3 | 0.741708 | 1 | 11,300 | NO_NOT_HIGHEST_WITHIN_QUALITY_PC_FUNNEL | VALID_TREND_REENTRY_OR_FAST_RECOVERY | QUESTIONABLE_REENTRY |
| 93180 | `pc-66d9ba285c89ec9b-93180-0003` | 2023-02-06 | 2 | 0.746618 | 1 | -60,900 | NO_NOT_HIGHEST_WITHIN_QUALITY_PC_FUNNEL | LIKELY_WHIPSAW | LIKELY_WHIPSAW |
| 93180 | `pc-66d9ba285c89ec9b-93180-0004` | 2023-02-16 | 1 | 0.801402 | 5 | 38,900 | YES_WITHIN_QUALITY_PC_FUNNEL | VALID_TREND_REENTRY | VALID_REENTRY |
| 93180 | `pc-66d9ba285c89ec9b-93180-0005` | 2023-03-02 | 2 | 0.791396 | 3 | -15,000 | NO_NOT_HIGHEST_WITHIN_QUALITY_PC_FUNNEL | QUESTIONABLE_REENTRY | QUESTIONABLE_REENTRY |
| 93180 | `pc-66d9ba285c89ec9b-93180-0006` | 2023-03-29 | 6 | 0.695869 | 1 | -80,000 | NO_NOT_HIGHEST_WITHIN_QUALITY_PC_FUNNEL | LIKELY_WHIPSAW | LIKELY_WHIPSAW |
| 77760 | `pc-66d9ba285c89ec9b-77760-0002` | 2023-04-11 | 6 | 0.743136 | 31 | -4,600 | NO_NOT_HIGHEST_WITHIN_QUALITY_PC_FUNNEL | QUESTIONABLE_REENTRY | QUESTIONABLE_REENTRY |
| 76920 | `pc-66d9ba285c89ec9b-76920-0002` | 2023-03-02 | 6 | 0.707118 | 1 | 9,990 | NO_NOT_HIGHEST_WITHIN_QUALITY_PC_FUNNEL | VALID_TREND_REENTRY_OR_FAST_RECOVERY | QUESTIONABLE_REENTRY |
| 76920 | `pc-66d9ba285c89ec9b-76920-0003` | 2023-03-06 | 2 | 0.737342 | 1 | -4,770 | NO_NOT_HIGHEST_WITHIN_QUALITY_PC_FUNNEL | LIKELY_WHIPSAW | LIKELY_WHIPSAW |
| 43880 | `pc-66d9ba285c89ec9b-43880-0002` | 2023-03-31 | 3 | 0.765936 | 2 | 5,600 | NO_NOT_HIGHEST_WITHIN_QUALITY_PC_FUNNEL | VALID_TREND_REENTRY_OR_FAST_RECOVERY | QUESTIONABLE_REENTRY |
| 30410 | `pc-66d9ba285c89ec9b-30410-0002` | 2023-05-22 | 2 | 0.796419 | 4 | -8,600 | NO_NOT_HIGHEST_WITHIN_QUALITY_PC_FUNNEL | QUESTIONABLE_REENTRY | QUESTIONABLE_REENTRY |

Important limitation:

```text
Candidate full universe: INSUFFICIENT_EVIDENCE
```

The candidate competition judgment is limited to Quality / Portfolio
Construction funnel rows. It does not prove full candidate-universe superiority
or infer from missing evidence.

## 93180 and 76920 Typicality

93180:

```text
Entry count: 6
Re-entry count: 5
Total campaign PnL: -120,600
Re-entry-only PnL: -105,700
Typicality: OUTLIER
```

93180 is an outlier. Its re-entry sequence contains the largest re-entry loss:

```text
2023-03-29
campaign: pc-66d9ba285c89ec9b-93180-0006
rank: 6
quality_score: 0.695869
interval: 1BD
PnL: -80,000
classification: LIKELY_WHIPSAW
```

76920:

```text
Entry count: 3
Re-entry count: 2
Total campaign PnL: -28,290
Re-entry-only PnL: +5,220
Typicality: TYPICAL_OR_MIXED
```

76920's total symbol loss is driven by the initial campaign loss. Its
re-entry-only result is mixed-positive, but one of its two re-entries is
classified as `LIKELY_WHIPSAW`.

## Re-entry Trigger Quality

Evidence-supported facts:

- Re-entry Quality was often high enough for BUY admission.
- Re-entry ranks varied materially, from Rank 1 to Rank 6.
- Market Context was mixed across BULL and RANGE regimes.
- The highest-quality valid re-entry example was 93180 `0004`: Rank 1,
  Quality 0.801402, interval 5BD, PnL +38,900.

Evidence-supported inference:

- Re-entry was not uniformly unjustified.
- Re-entry was also not consistently reserved for the strongest available
  opportunities.
- Conditions were often similar enough after recent exits that whipsaw is a
  plausible explanation for several losses.

## Exit Interaction

Likely whipsaw examples:

| Symbol | Campaign | Prior Exit | Re-entry | Interval | PnL |
|---:|---|---|---|---:|---:|
| 93180 | `pc-66d9ba285c89ec9b-93180-0003` | 2023-02-03 | 2023-02-06 | 1BD | -60,900 |
| 93180 | `pc-66d9ba285c89ec9b-93180-0006` | 2023-03-28 | 2023-03-29 | 1BD | -80,000 |
| 76920 | `pc-66d9ba285c89ec9b-76920-0003` | 2023-03-03 | 2023-03-06 | 1BD | -4,770 |

This supports Exit/Re-entry interaction as a partial factor. It does not prove
that Exit timing alone is primary, because MFE/MAE and exact PM intent are not
available.

## Root Cause Separation

| Cause Area | Judgment | Evidence |
|---|---|---|
| Re-entry Selection | PARTIAL_FACTOR | 10 of 11 re-entry campaigns were not highest-ranked within the Quality/PC funnel. |
| Exit Timing | PARTIAL_FACTOR | 3 campaigns show 1BD exit-to-re-entry loss pattern. |
| Opportunity Ranking | PARTIAL_FACTOR | Re-entry rank quality was mixed; full candidate universe remains insufficient. |
| BUY Quality | PARTIAL_FACTOR | FULL and REDUCED re-entries both include winners and losers. |
| Market Context | MIXED_EVIDENCE | Re-entries occurred across BULL/RANGE; not sufficient alone. |
| Position Sizing | NOT_PRIMARY_CAUSE_IN_A3 | Loss causality is more directly tied to selection/exit/outcome than sizing mechanics. |

Architecture repair required:

```text
false
```

## Final Diagnosis

Observed re-entry losses were not explained by a single clean cause.

Most supported explanation:

```text
Poor outcomes came from an interaction of:
1. re-entry selection not always being top-ranked within the Quality/PC funnel,
2. rapid exit-to-re-entry whipsaw in several campaigns,
3. mixed Opportunity / Quality discrimination,
4. symbol-level concentration of losses, especially 93180.
```

Not supported:

```text
Re-entry decisions were always valid and losses were only bad luck.
Re-entry logic alone is proven wrong.
Exit timing alone is proven primary.
Position Sizing is the primary re-entry loss cause.
```

## Validation

```text
py_compile: PASS
generator execution: PASS
JSON output validation: PASS
fresh-run / resume / Historical / long regression: NOT EXECUTED
```

## Final Decision

Phase27-A3 is complete as a read-only diagnosis.

The correct next step is review of A3 evidence. This task does not authorize
cooldown, symbol bans, re-entry restrictions, Quality threshold changes, Rank
cutoffs, Exit changes, or sizing changes.
