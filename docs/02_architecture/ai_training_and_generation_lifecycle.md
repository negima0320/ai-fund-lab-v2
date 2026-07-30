# AI Training and Generation Lifecycle

This document is a permanent Architecture Source of Truth for AI Fund Lab v2 training, generation, quality policy, acceptance, and runtime boundaries.

It complements:

```text
docs/02_architecture/autonomous_ai_operations_architecture.md
docs/02_architecture/runtime_architecture_v2.md
docs/02_architecture/ai_generation_artifact_contract.md
docs/01_requirements/phase_roadmap.md
```

Generation output artifact schemas, authority boundaries, runtime accepted-only eligibility, serialization compatibility, reproducibility, and prohibited artifact content are defined in:

```text
docs/02_architecture/ai_generation_artifact_contract.md
```

## Purpose

AI retraining is not primarily a search for better headline accuracy. Its first purpose is to create a reproducible AI Generation bound to formal Dataset Revision, approved Rolling Split, policy hashes, schema hashes, lineage hashes, label-safe authority, and validation evidence.

Legacy AI artifacts are not reused as new generation authority because they do not satisfy the current architecture contract:

- Dataset, Split, Policy, Schema, and Lineage bindings are incomplete or not unified.
- Candidate and Opportunity members are not assembled as one immutable generation.
- Runtime cannot safely promote them into Accepted Generation authority without new validation and acceptance evidence.

## AI Component Inventory

Candidate AI is the first-stage selection model. It evaluates the eligible equity universe and extracts investment candidates for later scoring.

Opportunity AI is the second-stage opportunity model. It evaluates Candidate outputs and ranks or scores them as buy opportunities with confidence or expected edge semantics.

Calibration is part of the generation, not a loose helper. If calibration includes learned or fitted parameters, its inputs, target model hashes, policy, output hash, and invalidation rules must be bound to the same Unified Generation. Opportunity model hash changes invalidate prior Opportunity calibration unless compatibility evidence explicitly permits reuse.

Validation checks the generation candidate for quality, schema compatibility, leakage, label safety, policy binding, calibration applicability, bias, drift, and runtime compatibility. Validation is not a process for using realized trading profit as training input.

Unified Generation binds these members into one immutable candidate:

```text
Dataset Revision
Versioned Split
Candidate Model
Opportunity Model
Calibration
Validation Result
Runtime Baseline
Policy Hashes
Schema / Lineage
```

Accepted Decision is the authority that promotes a validated Generation Candidate into an Accepted Generation that Runtime may consume.

Runtime does not train. Runtime does not read Dataset Revisions or Split artifacts directly. Runtime consumes only the Accepted Generation Resolver authority.

## Training and Non-Training Boundary

Training or regeneration targets:

```text
Candidate AI
Opportunity AI
Calibration artifact
Validation result
Unified Generation artifact
```

Non-training targets:

```text
Runtime State Machine
Safety Layer
BUY / SELL Guard
Order Planning
Submit
Execution
Broker Adapter
Ledger
Current / Pending
Accepted Generation Resolver
Lifecycle Gate
```

Non-training targets are implementation, rule, state, or authority components. They must not be changed by model training.

## Bootstrap Lifecycle

Bootstrap is the first generation flow when no Accepted Generation exists:

```text
J-Quants
-> Common PIT Dataset
-> Label-safe Dataset
-> Dataset Revision
-> Approved Versioned Split
-> Contract-only Training Resolver
-> Candidate Training
-> Opportunity Training
-> Calibration
-> Validation
-> Unified Generation Candidate
-> Human Review / Accepted Decision
-> Accepted Generation
-> Runtime Transition
```

Bootstrap uses:

```text
previous_generation_ref = null
previous revision delta not required
incremental business days not required
incremental rows not required
```

Bootstrap uses available approved history under the approved split policy. It must not silently switch into retraining mode.

## Retraining Lifecycle

Retraining occurs only after an Accepted Generation exists:

```text
New Dataset Revision
-> Retraining Trigger Decision
-> Approved Split
-> Candidate / Opportunity Training
-> Calibration
-> Validation
-> New Generation Candidate
-> Acceptance
-> Atomic Runtime Transition
```

Retraining trigger evidence may include:

```text
minimum incremental label-safe business days
minimum incremental rows
schema continuity
lineage continuity
data health
model drift
generation age
calendar-based trigger
```

Trigger values must be controlled by a versioned policy or Human Review. They must not be inferred from runtime profit, paper profit, broker state, or old defaults.

## Five-Year Window Semantics

The approved window type is:

```text
CAPPED_EXPANDING_HYBRID
```

Its meaning:

```text
Use available approved history.
While history is short, the training window expands.
Once enough history exists, cap the maximum history at approximately five years.
Calendar boundaries are derived from the formal Trading Calendar.
```

Approximately five years is not a fixed hardcoded business-day count. Candidate and Opportunity may have different train starts when their available approved histories differ.

## Dataset Update and AI Update Separation

Dataset freshness and AI Generation freshness are different.

Dataset update can produce a Dataset Revision without immediately producing a new AI Generation:

```text
Dataset update
-> Dataset Revision
-> Retraining Trigger not met
-> Current Accepted Generation continues
```

When triggers and policy allow:

```text
Dataset update
-> Retraining Trigger met
-> New Generation Candidate
-> Validation
-> Acceptance
-> Runtime Transition
```

New market data does not automatically mean a new model. Existing Accepted Generation may continue if freshness, drift, compatibility, and safety gates permit it.

## J-Quants to Runtime Dataflow

The full production lifecycle is:

```text
J-Quants Raw / Normalized Data
-> Common PIT Dataset
-> Label-safe Dataset
-> Dataset Revision
-> Approved Rolling Split
-> Contract-only Training Resolver
-> Candidate / Opportunity Training
-> Calibration
-> Validation
-> Unified Generation
-> Accepted Decision
-> Accepted Generation Resolver
-> Runtime Inference
-> Order Planning
-> Submit
-> Execution
```

Every boundary must record its authority and artifact identity. Training outputs do not become Runtime authority until accepted by the Accepted Decision process and committed through Runtime Transition.

## Latest Semantics

Runtime does not use the latest raw Dataset as model authority. Runtime uses the latest formal Accepted Generation reachable through the Accepted Generation Resolver.

Daily inference may use formally updated latest PIT market features as input to the accepted model, but this is different from replacing the accepted model.

These freshness concepts must remain separate:

```text
Training Dataset freshness
Inference Feature freshness
Accepted Generation freshness
Runtime State freshness
Broker State freshness
```

`latest` filesystem paths, mtime ordering, newest training directory, and newest Registry item are not authority.

## Phase23-P Historical Evaluation Authority Semantics

Production and Demo Runtime use date-local Accepted Generation authority. For a
Production/Demo business date, a Runtime-consumable Accepted Generation must
satisfy:

```text
accepted_at <= business_date
effective_from <= business_date
```

Historical Runtime performance evaluation has a separate run authority boundary:
at Historical run start, the runner fixes one current Human Accepted Generation
and records it as `historical_evaluation_authority.json`. Historical daily
inference consumes that fixed run authority for the entire run. It does not
compare the Accepted Generation `accepted_at` or `effective_from` to each
historical business date.

This does not make Accepted Generation historical-only. The model, scaler,
feature schema, lifecycle gate, AI consumer, Strategy, Planning, Safety, PM, and
Submit Decision remain Production-common. Only the daily input sources are
historical point-in-time sources.

Historical performance evaluation is distinct from strict out-of-sample AI
performance. The run summary must expose training cutoff, evaluation period,
training overlap, and evaluation mode. When overlap exists, the result must not
be labeled `STRICT_OOS`.

## Failure and Rollback Contract

If retraining, calibration, validation, or acceptance fails:

```text
Do not accept the new Generation.
Do not change the Runtime pointer.
Keep the current Accepted Generation.
BUY may continue only if current Accepted Generation gates still pass.
```

BUY must fail closed when:

```text
current Accepted Generation is invalid
compatibility is broken
policy is expired
critical data corruption is detected
Runtime accepted authority cannot be resolved
```

SELL, Current, Valuation, Safety, and Ledger are independently evaluated and may continue where their own dependencies are safe.

## Prohibited Training Inputs

Training and Model Quality Policy must not use:

```text
Backtest result
Backtest profit
Runtime result
Runtime PnL
Paper Trading result
Paper Ledger
Broker Snapshot
Broker position
cash
portfolio value
selected
bought
PM multiplier imitation
Test result
Audit result
Future information
Corporate Action event
Future adjustment
```

Allowed training input is limited to formally bound J-Quants-derived PIT / label-safe Dataset Features and Targets.

## Model Quality Policy Boundary

Model Quality Policy is separate from Dataset/Split sufficiency.

Dataset/Split sufficiency proves that the input artifacts are valid. Model Quality Policy decides whether the available rows, labels, issues, missingness, numeric validity, and feature coverage are sufficient for training and validation.

Model Quality thresholds must be versioned and approved before they are used to authorize training. Draft policy artifacts cannot authorize Candidate training, Opportunity training, Calibration, Unified Generation, Accepted Decision, Runtime Transition, BUY restart, or Broker write.

The Phase19-AD-U3-D approved policy is:

```text
.runtime/ai_lifecycle/policies/model_quality/phase19_ad_u3_d_model_quality_policy/model_quality_policy.json
```

Its approval authorizes future contract-bound training implementation only. It does not create Candidate training output, Opportunity training output, Calibration, Unified Generation, Accepted Decision, Runtime Transition, BUY restart, or Broker write.

## Feature Scaling Corrective Contract

When a corrective action approves feature scaling for SGD-family training, scaling becomes a formal preprocessing member of the Generation contract.

The required order is:

```text
Training Window raw features
-> train-window-only imputer fit
-> imputer transform
-> train-window-only scaler fit
-> scaler transform
-> model fit
```

Validation, Test, and Recent Holdout data must be transform-only for both imputer and scaler. Candidate and Opportunity scalers are independent; cross-component scaler reuse is prohibited.

Scaler artifacts must be hash-bound to Dataset Revision, Split, Model Quality Policy, Corrective Action Policy, feature order, fitted parameters, training config, training code, and environment. A model artifact that declares scaling must bind the matching scaler artifact id, scaler artifact hash, scaler method, scaled feature schema hash, and preprocessing pipeline hash.

Runtime inference, once later implemented, must use the scaler bound by the Accepted Generation. It must reject latest-scaler discovery, component mismatch, scaler hash mismatch, and feature order mismatch. This contract does not by itself create Calibration, Validation PASS, Unified Generation, Accepted Decision, Accepted Generation, Runtime Transition, BUY restart, or Broker write.

## Phase19-AO Recent Holdout De-scope

Human Architecture Decision `Phase19-AO` closes the Phase19 recent_holdout ambiguity:

```text
recent_holdout is reserved / unused in Phase19
recent_holdout is not an Accepted Generation Entry gate
recent_holdout is not an Accepted Decision input
recent_holdout is not an Accepted Generation Materialization input
recent_holdout is not a Runtime Transition input
recent_holdout is not a Runtime Readiness input
recent_holdout is not a Runtime Baseline source
```

This is a Phase19 scope decision, not a deletion of the split or a denial of future use. A future phase may reactivate Recent Holdout only through a new versioned contract amendment and Human Review.

Phase19 quality authority is:

```text
Formal Validation
+
Corrective Re-evaluation
+
Dual Gate
+
Independent Review
```

Recent Holdout must remain unaccessed and must not be used for training, fit, tuning, threshold selection, calibration fit, method selection, Corrective Re-evaluation, Formal Validation overwrite, Accepted Decision, Accepted Generation, or Runtime Baseline.

Phase19 Runtime Baseline must use Formal Validation / Corrective Re-evaluation test-window inference outputs and CandidateTop50 selection outputs. It is operational health and drift comparison evidence only, not a model quality gate replacement.
