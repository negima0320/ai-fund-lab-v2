# Phase32-FH - Aggressive Risk-On / Investment Philosophy Alignment Characterization Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260903T213011268067Z`
- Primary period: `2023-03-01` through `2023-05-08`
- Current source identity: `04ded4ca66a9a6308be2bc395c0e26ba1a98b8bf`
- Required references read: Phase32-FE, Phase32-FF, Phase32-FG, Phase32-FC, current Risk Pacing / Market-Candidate-Cash SoT, Portfolio Construction / MCV SoT, and current source.
- Production changed: NO
- SHADOW changed: NO
- Config/schema changed: NO
- Target run mutated: NO
- Runtime state mutated: NO
- fresh-run/resume/replay/recover executed: NO
- Future return/PnL/MFE/MAE/final outcome used for Production judgment: NO

## Executive Summary

The central separation is confirmed:

- Question A: Fast redeployment into genuinely strong opportunities after risk-off is aligned with AI Fund Lab v2's momentum-oriented, opportunity-first philosophy.
- Question B: Broad positive allocation to `COMPARABLE_MARGINAL` rows during `CAUTIOUS_DEPLOYMENT` / `GRADUAL_REDEPLOYMENT`, especially when Cash interaction says `CASH_PREFERRED`, is not required by the philosophy and appears broader than the intended semantic.

This is not a case for fixed cooldown or a blanket exposure ramp ceiling. Those would conflict with the system's core preference for current PIT opportunity evidence over calendar waiting. The better next design direction is:

`B. DESIGN_FAST_STRONG_SELECTIVE_MARGINAL`

Selected judgment:

`B. FAST_RISK_ON_IS_CORE_STRENGTH_KEEP_MARGINAL_BINDING_REFINEMENT_JUSTIFIED`

## Investment Philosophy Contract

Extracted current contract:

| Topic | Philosophy / SoT reading | Current behavior alignment |
| --- | --- | --- |
| Recovery capital deployment | Do not wait mechanically merely because a recovery is young; current PIT opportunity can justify deployment. | Aligned for strong opportunities. |
| `NORMAL_DEPLOYMENT` | Ordinary capital competition when market quality and opportunity evidence are healthy. | Aligned. |
| `CAUTIOUS_DEPLOYMENT` | Marginal deployment requires stronger contemporaneous evidence; SELL/Safety independence remains unchanged. | Partially aligned; current path accepts `ELIGIBLE_COMPARABLE`, including `COMPARABLE_MARGINAL`, too broadly. |
| `GRADUAL_REDEPLOYMENT` | Redeployment may occur through confirmed competitors, not forced abrupt exposure restoration. | Partially aligned; actual fills include many marginal/Cash-preferred rows. |
| Cash optionality | Cash is a first-class allocation, not merely leftover budget. | Partially aligned; Cash evidence exists but is weak at final binding. |
| Strong opportunity | Momentum-oriented strategy should fund strong current evidence quickly. | Aligned and should be kept. |
| Marginal opportunity | Valid but close to Cash; can participate, but should not become automatic deployment during cautious/recovery states. | Current effective binding is too wide. |
| Momentum confirmation | Current confirmation matters more than old relationship labels or fixed holding periods. | Aligned upstream; compressed at effective MCV/Risk Pacing binding. |
| BUY independence | BUY should not be artificially suppressed because SELL/risk-off happened recently. | Aligned; keep this. |
| Risk Pacing | Expresses willingness to deploy marginal capital; not fixed exposure, fixed BUY count, or direct quantity authority. | Aligned architecturally; refinement should stay at candidate/Cash binding, not cooldown. |

## Risk-Off vs Risk-On Asymmetry

| Dimension | Risk-off | Risk-on | Judgment |
| --- | --- | --- | --- |
| Trigger evidence | Market deterioration plus PM/security deterioration; examples include `SHORT_TERM_BREADTH_BREAKDOWN`, `BEAR`, `CORRECTION`, and security-level SELLs. | Market improvement, recovery, or still-cautious environments with deployable PIT candidates. | Valid asymmetry in principle. |
| Confirmation requirement | Risk-off can act quickly on deterioration. | Strong opportunities can act quickly; marginal opportunities should need stronger current confirmation than they currently do. | Asymmetry valid, marginal gate weak. |
| Reaction speed | FE observed 0-1BD response to explicit risk-off signals. | FE observed pre-confirmation/aggressive re-risking on 3/22 and 4/11-4/12. | Speed itself is not the defect. |
| Candidate requirement | SELL/REDUCE relies on PM/current position evidence. | BUY relies on Candidate/BQ/Entry/MCV/PC/Cash. | Separation intact. |
| Cash interaction | Risk-off can raise Cash by SELL and target gross/cash reserve. | Cash may be preferred but still loses final binding for many marginal rows. | Cash binding refinement justified. |
| Target gross | Risk-off sometimes lowers target gross/reserve; not always the only exposure driver. | Target gross can return to 0.90/1.00 quickly. | Not a correctness defect; fixed ceiling not justified. |

## Aggressive Recovery Capture Characterization

Actual BUY fills, `2023-03-01` through `2023-05-08`:

| Risk intent / quality | BUY_NEW | BUY_ADD | Notional | Share of all BUY notional |
| --- | ---: | ---: | ---: | ---: |
| CAUTIOUS `STRONG` | 1 | 0 | 24,300 | 0.4% |
| CAUTIOUS `COMPARABLE_HIGH` | 2 | 0 | 174,300 | 2.8% |
| CAUTIOUS `COMPARABLE_MARGINAL` | 34 | 2 | 2,839,530 | 45.3% |
| GRADUAL `STRONG` | 1 | 0 | 57,000 | 0.9% |
| GRADUAL `COMPARABLE_HIGH` | 2 | 0 | 91,930 | 1.5% |
| GRADUAL `COMPARABLE_MARGINAL` | 12 | 0 | 1,351,330 | 21.6% |
| NORMAL `COMPARABLE_HIGH` | 1 | 0 | 144,900 | 2.3% |
| NORMAL `COMPARABLE_MARGINAL` | 20 | 0 | 1,586,830 | 25.3% |

Totals:

- All BUY fills: 75, notional `6,270,120`.
- All `COMPARABLE_MARGINAL`: 68 fills, notional `5,777,690`, 92.1% of all BUY notional.
- CAUTIOUS/GRADUAL `COMPARABLE_MARGINAL`: 48 fills, notional `4,190,860`, 66.8% of all BUY notional.
- CAUTIOUS/GRADUAL strong/high: 6 fills, notional `347,530`, 5.5% of all BUY notional.

Interpretation: aggressive recovery capture in the observed period depends materially on `COMPARABLE_MARGINAL` participation, not just on abundant `STRONG` / `COMPARABLE_HIGH` opportunities.

## Strong Opportunity Immediate Deployment

Actual-path examples show the system can deploy quickly to stronger candidates even during cautious/gradual states:

- `2023-03-22` `67750`: `STRONG`, `ELIGIBLE_STRONG`, `SELECTIVE_COMPETITION`, healthy continuation, robust tick trend, BUY_NEW `24,300`.
- `2023-04-11` `27210`: `COMPARABLE_HIGH`, `ELIGIBLE_STRONG`, healthy continuation, robust tick trend, BUY_NEW `43,500`.
- `2023-04-11` `45980`: `COMPARABLE_HIGH`, `ELIGIBLE_STRONG`, healthy continuation, robust tick trend, BUY_NEW `130,800`.
- `2023-04-24` `69270`: `STRONG`, `ELIGIBLE_STRONG`, `DEPLOY_ELIGIBLE`, healthy continuation, robust tick trend, BUY_NEW `57,000`.

Judgment:

`STRONG_OPPORTUNITY_IMMEDIATE_DEPLOYMENT_SHOULD_BE_KEPT = YES`

`COMPARABLE_HIGH_IMMEDIATE_DEPLOYMENT_SHOULD_BE_KEPT = YES_WITH_CURRENT_CONFIRMATION`

Fast strong/high deployment is a core strength. It preserves the momentum philosophy and avoids artificial recovery waiting.

## Marginal Deployment Necessity

Why `COMPARABLE_MARGINAL` receives capital during CAUTIOUS/GRADUAL:

| Cause | Present? | Evidence |
| --- | --- | --- |
| A. Recovery capture intentional aggressiveness | PARTIAL | Risk Pacing allows redeployment; no fixed cooldown exists. |
| B. Opportunity-first participation | YES | SoT allows reduced participation; `CASH_PREFERRED` is not blanket zero. |
| C. Legacy compatibility compression | YES | `COMPARABLE_MARGINAL -> ELIGIBLE_COMPARABLE`; PC Risk Pacing treats `ELIGIBLE_COMPARABLE` as sufficient. |
| D. Cash participation resolver side effect | YES | 125 Cash-preferred marginal positive rows and 48 fills remained positive. |
| E. unintended semantic widening | YES | CAUTIOUS/GRADUAL semantics say stronger/confirmed evidence, but effective binding allows broad marginal deployment. |

Conclusion:

`MARGINAL_DEPLOYMENT_IS_REQUIRED_FOR_PHILOSOPHY = PARTIAL`

Some marginal participation can be philosophy-consistent when current PIT evidence is strong enough and Cash optionality is explicitly preserved. Broad marginal deployment is not required.

## Historical Performance Characterization

This section is descriptive only and was not used to select any Production rule.

| Episode | Equity / exposure movement | Behavior characterization |
| --- | --- | --- |
| `2023-03-08 -> 2023-03-17` | Equity `1,297,290 -> 1,242,700`; exposure `93.7% -> 68.0%`. | Risk-off response reduced exposure materially. |
| `2023-03-20 -> 2023-03-22` | Exposure `67.3% -> 91.8%`; 3/22 BUY notional included `284,200` marginal rows. | Fast pre-confirmation risk-on under CAUTIOUS. |
| `2023-03-24 -> 2023-03-27` | Exposure `77.0% -> 91.4%`; 3/27 marginal BUY_NEW `178,400`. | GRADUAL label, but actual redeployment can be abrupt if fills are feasible. |
| `2023-04-04 -> 2023-04-10` | Exposure `94.7% -> 62.0%`; cash `77,100 -> 563,640`. | Risk-off / security-level reductions raised Cash. |
| `2023-04-10 -> 2023-04-12` | Exposure `62.0% -> 93.3%`; BUY_NEW notional `520,530`; existing holding price effect negative. | Ramp was driven by new deployment, starting under CAUTIOUS before BULL/NORMAL. |
| `2023-04-24 -> 2023-05-01` | Exposure `56.0% -> 90.7%`; 5/01 marginal BUY_NEW `370,400`. | Recovery redeployment again depended heavily on marginal/Cash-preferred rows. |

Characterization: current aggressiveness can capture upside quickly, but it also re-exposes the portfolio quickly through marginal evidence. That is a structural property, not a PnL-based judgment.

## Recovery Capture Source Attribution

For observed BUY notional in the primary period:

- `STRONG`: `81,300` / `6,270,120` = 1.3%.
- `COMPARABLE_HIGH`: `411,130` / `6,270,120` = 6.6%.
- `COMPARABLE_MARGINAL`: `5,777,690` / `6,270,120` = 92.1%.
- BUY_ADD inside CAUTIOUS/GRADUAL marginal: `208,700`.

Therefore:

`AGGRESSIVE_RECOVERY_CAPTURE_DEPENDS_MATERIALLY_ON_MARGINAL = YES`

## Aggressiveness Source

| Source | Contribution |
| --- | --- |
| A. STRONG/HIGH opportunity abundance | Limited in observed notional; important for philosophy but not main notional driver. |
| B. `COMPARABLE_MARGINAL` participation | Primary driver. |
| C. Cash binding weakness | Material; Cash-preferred rows still received positive fills. |
| D. target gross jump | Material secondary, especially 4/11 target gross 0.90 and 4/12 1.00. |
| E. existing holdings retention | Secondary/path dependent; 4/10-4/12 ramp was not driven by holding appreciation. |
| F. ADD | Small sample but real: 2 fills, `208,700`. |
| G. combination | YES: target gross capacity plus marginal/Cash-preferred participation produces the fast ramp. |

## Philosophy Counterfactuals

| Model | Momentum philosophy alignment | Opportunity capture | Cash optionality | Artificial suppression risk | False-recovery exposure risk | Complexity |
| --- | --- | --- | --- | --- | --- | --- |
| A. Current | High for fast action, partial for Cash discipline | High | Partial | Low | Higher for marginal rows | Existing |
| B. Slow Everything | Low/medium; fixed waiting conflicts with opportunity-first | Lower | High | High | Lower | Low |
| C. Fast Strong / Selective Marginal | Highest alignment | High for strong/high; selective for marginal | High | Low/medium | Lower than current | Moderate |
| D. Cash-Dominant Recovery | Medium/low; may overprotect Cash | Lower | Very high | Medium/high | Low | Moderate |

Preferred next direction:

`NEXT_DESIGN_DIRECTION = B. DESIGN_FAST_STRONG_SELECTIVE_MARGINAL`

Do not choose a model by Historical PnL. The choice follows Architecture/SoT semantics.

## Fixed Cooldown / Ramp Ceiling Reassessment

`FIXED_COOLDOWN_SHOULD_BE_ADDED = NO`

Reason: AI Fund Lab v2 is not designed to wait mechanically after recovery/risk-off. Current PIT opportunity evidence should be able to override calendar hesitation.

`FIXED_EXPOSURE_RAMP_CEILING_SHOULD_BE_ADDED = NO_NOT_YET`

Reason: Risk Pacing should express willingness to deploy marginal capital, not impose a fixed exposure path. A ceiling may become a later portfolio-risk design, but FH does not justify it.

## COMPARABLE_MARGINAL Semantic Meaning

Architecture-consistent meaning:

`COMPARABLE_MARGINAL` means valid but close to Cash optionality. In normal markets it may be investable. In CAUTIOUS/GRADUAL states, it should not automatically imply sufficient deployment; it needs current confirmation and explicit PC/Cash participation evidence.

It does not mean:

- invalid candidate,
- blanket exclusion,
- always investable during CAUTIOUS/GRADUAL,
- stronger than Cash by default.

Current effective binding extends the semantic too broadly because compatibility class `ELIGIBLE_COMPARABLE` is treated as sufficient by the Risk Pacing gate even when canonical Cash interaction says `CASH_PREFERRED`.

`MARGINAL_DEPLOYMENT_CURRENTLY_TOO_BROAD = YES`

## Cash Philosophy Alignment

`CASH_PREFERRED` means the candidate-vs-Cash interaction favors optional Cash at that decision time. SoT also says it is not an automatic hard zero and must pass PC-owned participation-vs-deferral resolution.

Therefore:

`CASH_PREFERRED_SECURITY_PARTICIPATION_ALIGNS_WITH_PHILOSOPHY = PARTIAL`

Reduced participation can align with the philosophy when current row evidence is credible and Cash remains a first-class allocation. But material broad participation by marginal rows under CAUTIOUS/GRADUAL, despite `CASH_PREFERRED`, is not fully aligned.

## BUY_ADD Philosophy

BUY_ADD during recovery is philosophy-consistent when the existing holding is a Winner or continuation candidate with current incremental evidence, headroom, and opportunity-cost support. It should not be blocked merely because the market is in CAUTIOUS/GRADUAL.

However, ADD and BUY_NEW should share the same capital competition contract. The evidence differs, but the marginal capital unit must still compete against Cash and other opportunities. G129 order-increment semantics must remain intact.

`BUY_ADD_RECOVERY_DEPLOYMENT_ALIGNS_WITH_PHILOSOPHY = YES_IF_CURRENT_INCREMENTAL_EVIDENCE_BEATS_CASH`

## KEEP / REFINE / REMOVE Classification

| Component | Classification | Reason |
| --- | --- | --- |
| fast strong-opportunity deployment | KEEP | Core momentum/opportunity-first strength. |
| `COMPARABLE_HIGH` immediate competition | KEEP | Keep when current confirmation is sufficient. |
| `COMPARABLE_MARGINAL` participation | REFINE | Not blanket remove; require stronger current/Cash comparison in CAUTIOUS/GRADUAL. |
| `CASH_PREFERRED` participation | REFINE | Participation may exist, but current final binding is too permissive. |
| `GRADUAL_REDEPLOYMENT` | REFINE | Concept good; actual intensity often not gradual/selective enough. |
| `CAUTIOUS_DEPLOYMENT` | REFINE | Concept good; effective marginal sufficiency too broad. |
| fixed cooldown absence | KEEP | Avoid artificial calendar suppression. |
| fixed Exposure ceiling absence | KEEP_FOR_NOW | No architecture proof for fixed ceiling. |
| BUY_ADD during recovery | KEEP_WITH_COMMON_CASH_COMPETITION | Aligns when current incremental evidence is strong and Cash competition is respected. |

## Production Repair Necessity

- `RISK_ON_SPEED_REPAIR_JUSTIFIED = NO`
- `MARGINAL_BINDING_REFINEMENT_JUSTIFIED = YES`
- `CASH_BINDING_REFINEMENT_JUSTIFIED = YES`
- `PRODUCTION_REPAIR_JUSTIFIED = NO_NOT_YET`

Reason: FH establishes a design refinement need, but it does not select a concrete Production rule/threshold/weight. Production repair should wait for a design phase that preserves fast strong deployment while making marginal-vs-Cash binding PIT-only and non-tuned.

## Required Answers

- `FAST_RISK_ON_ALIGNS_WITH_INVESTMENT_PHILOSOPHY = YES`
- `STRONG_OPPORTUNITY_IMMEDIATE_DEPLOYMENT_SHOULD_BE_KEPT = YES`
- `COMPARABLE_HIGH_IMMEDIATE_DEPLOYMENT_SHOULD_BE_KEPT = YES_WITH_CURRENT_CONFIRMATION`
- `MARGINAL_DEPLOYMENT_IS_REQUIRED_FOR_PHILOSOPHY = PARTIAL`
- `MARGINAL_DEPLOYMENT_CURRENTLY_TOO_BROAD = YES`
- `CASH_PREFERRED_SECURITY_PARTICIPATION_ALIGNS_WITH_PHILOSOPHY = PARTIAL`
- `AGGRESSIVE_RECOVERY_CAPTURE_IS_INTENTIONAL = YES_BUT_CURRENT_MARGINAL_WIDTH_EXCEEDS_INTENT`
- `AGGRESSIVE_RECOVERY_CAPTURE_DEPENDS_MATERIALLY_ON_MARGINAL = YES`
- `BUY_ADD_RECOVERY_DEPLOYMENT_ALIGNS_WITH_PHILOSOPHY = YES_IF_CURRENT_INCREMENTAL_EVIDENCE_BEATS_CASH`
- `FIXED_COOLDOWN_SHOULD_BE_ADDED = NO`
- `FIXED_EXPOSURE_RAMP_CEILING_SHOULD_BE_ADDED = NO_NOT_YET`
- `RISK_ON_SPEED_REPAIR_JUSTIFIED = NO`
- `MARGINAL_BINDING_REFINEMENT_JUSTIFIED = YES`
- `CASH_BINDING_REFINEMENT_JUSTIFIED = YES`
- `PRODUCTION_REPAIR_JUSTIFIED = NO_NOT_YET`
- `NEXT_DESIGN_DIRECTION = B. DESIGN_FAST_STRONG_SELECTIVE_MARGINAL`
- `LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE = YES`

## Judgment

Selected:

`B. FAST_RISK_ON_IS_CORE_STRENGTH_KEEP_MARGINAL_BINDING_REFINEMENT_JUSTIFIED`

Supporting classification:

`G. MIXED`

The current aggressiveness is not globally misaligned. The core strength is fast funding of strong/currently confirmed opportunities. The refinement target is narrower: `COMPARABLE_MARGINAL` and `CASH_PREFERRED` final binding during CAUTIOUS/GRADUAL.

## Final Judgment

`PHASE32_FH_FAST_RISK_ON_CORE_STRENGTH_KEEP_MARGINAL_AND_CASH_BINDING_REFINEMENT_DESIGN_JUSTIFIED_PRODUCTION_REPAIR_NOT_YET`
