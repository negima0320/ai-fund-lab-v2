# Phase9-A Daily Paper Trading Operation Design

## 1. Purpose

This document defines the Phase9 daily operation design before implementation.

Phase9 is:

```text
Daily Paper Trading Validation
```

Phase9 validates whether AI Fund Lab can run every business day, produce reviewable decisions, update the internal Paper Ledger, and generate understandable daily reports.

Phase9 is not broker order testing.

Prohibited:

```text
live order
auto order
REAL order
Broker API order submit
Broker API order cancel
Broker API order modify
moomoo SIMULATE order
Tachibana order
OpenD automatic startup
unlock_trade
trade unlock
full historical backtest
```

Permitted:

```text
J-Quants market data update
AI training / inference from J-Quants-derived data only
internal Paper Ledger virtual order / virtual execution records
Human Review
Safety report
moomoo REAL read-only Broker Snapshot reference
Broker snapshot vs Paper Ledger reconciliation
```

## 2. Sources Reviewed

Documents:

```text
docs/01_requirements/phase_roadmap.md
docs/phase_reports/phase8_to_phase9_handoff.md
docs/phase_reports/phase8h_completion_audit.md
```

Source areas:

```text
src/ai_fund_lab_v2/order_manager/
src/ai_fund_lab_v2/broker/
src/ai_fund_lab_v2/safety/
src/ai_fund_lab_v2/candidate_ai/
src/ai_fund_lab_v2/opportunity_ai/
src/ai_fund_lab_v2/position_management_ai/
src/ai_fund_lab_v2/capital_allocation_ai/
```

Important existing invariants:

```text
OrderPlan.executable = false
OrderPlan.live_order_allowed = false
OrderPlan.requires_human_review = true
Approval does not allow live order
Paper Ledger and Broker Snapshot are stored separately
moomoo REAL is read-only reference only
Safety locked state allows review-only diagnostics only
```

## 3. Date Definitions

Phase9 uses explicit date fields to avoid future leakage.

```text
data_until
```

Latest market data date allowed for features, training, and inference. No row after `data_until` may be used.

```text
train_until
```

Latest label / training data date allowed for model training. `train_until` must be less than or equal to `data_until`, and must also respect each model's label horizon. For a 20-business-day future label, `train_until` must be at least 20 business days before the latest source data needed to compute that label.

```text
decision_for
```

The business day for which the AI decision is produced. Phase9 daily decisions are produced after the market close, so the normal relationship is:

```text
decision_for = data_until
```

```text
virtual_order_date
```

The next business day after `decision_for`. Human-approved OrderPlan items become virtual paper orders for this date.

```text
virtual_execution_date
```

The date used for virtual fills. Initial Phase9 policy uses:

```text
virtual_execution_date = virtual_order_date
fill_price = virtual_execution_date open price
```

Normal daily relationship:

```text
data_until <= decision_for < virtual_order_date = virtual_execution_date
train_until <= data_until
```

Example:

```text
2026-06-16 18:30 JST:
  data_until = 2026-06-16
  decision_for = 2026-06-16
  virtual_order_date = next JP business day
  virtual_execution_date = next JP business day
```

The next day's open price is not available at decision time. Therefore the daily run creates reviewable virtual orders first, and a later execution step fills only approved items after the next business day's market data is available.

## 4. Daily Time Schedule

All times are Japan Standard Time.

The schedule is an operational target, not a guarantee. If J-Quants data availability is delayed, the system waits or halts closed.

Initial Phase9 operation schedule:

```text
16:30 Market close / market data availability watch
17:00 J-Quants data update confirmation
18:00 Feature generation
19:00 Daily inference execution
20:00 Internal Daily Operation Report generation
20:05 Public Daily Report / Blog Draft generation
20:10 Human Review
20:20 Approved virtual order registration
Next business day: Paper Trading virtual fill processing after open price data is available
```

Daily mandatory work:

```text
J-Quants data update
feature generation
inference
report generation
Human Review workflow
Safety check
```

Daily non-mandatory work:

```text
model retraining
model promotion
model replacement
full model audit
```

Phase9 must not confuse "daily AI operation" with "daily model rebuild." The operational goal is to verify that the daily cycle runs, produces decisions, and remains auditable. Rebuilding every model every business day is a separate policy choice.

### 4.1 Morning Reference Check

```text
08:00 - 08:30
```

Tasks:

```text
Check previous run status
Check unresolved Human Review items
Check Safety lock state
Optionally refresh moomoo REAL read-only Broker Snapshot manually
Compare Broker Snapshot and Paper Ledger exposure for diagnostics
```

Allowed broker methods remain read-only:

```text
get_acc_list
accinfo_query
position_list_query
order_list_query
history_order_list_query
```

If Safety is locked:

```text
Do not generate normal trading plan
Generate review-only diagnostics
Do not create Paper Ledger virtual orders
Do not process virtual fills
```

### 4.2 Market Session

```text
09:00 - 15:30
```

Tasks:

```text
No automatic trading
No Broker API order call
No Paper Ledger intraday fill by default
Operational monitoring only
```

Phase9 does not simulate intraday decisions. Initial fill policy uses next business day open once data is available.

### 4.3 J-Quants Data Update

```text
16:30 - 17:30
```

Tasks:

```text
Fetch / confirm daily_quotes for decision_for
Fetch / confirm listed_info for decision_for
Fetch / confirm trading_calendar when needed
Normalize daily_quotes
Write raw / normalized manifests
Compute data_until
Check coverage and missing data
```

Daily quotes checks:

```text
daily_quotes contains decision_for rows
row count is non-zero for a JP business day
Open / High / Low / Close / Volume are present after normalization
adjusted values are preferred where complete
duplicate date-code keys are rejected or quarantined
abnormal zero price / zero volume rows are warned or excluded
```

Listed info checks:

```text
listed info exists for decision_for or latest valid listed master date
tradable universe can be derived
delisted / suspended / unsupported symbols are excluded
code normalization is stable
```

`data_until` rule:

```text
data_until = min(
  latest complete normalized daily_quotes business date,
  latest usable listed info date adjusted to decision universe freshness
)
```

If `data_until < decision_for`, Phase9 halts closed unless the operator explicitly runs a catch-up decision for `decision_for = data_until`.

Missing data halt conditions:

```text
daily_quotes missing for a JP business day
listed info missing or unreadable
trading calendar cannot identify next business day
normalized daily_quotes validation status is ERROR
feature builder detects future rows after data_until
feature row coverage below operational threshold
required input artifact missing
```

Halt output:

```text
No OrderPlan for normal execution
Safety status = INVALID_INPUT or REVIEW_ONLY_RECONCILIATION_HALT
Daily Report explains missing input and next action
Paper Ledger remains unchanged except for snapshot / audit metadata
```

### 4.4 AI Training Decision

```text
17:30 - 18:00
```

Phase9 separates daily inference from model training.

Mandatory every business day:

```text
data update
feature generation
inference
model eligibility check
training manifest reference check
```

Not mandatory every business day:

```text
model retraining
model promotion
model artifact replacement
```

Reasons:

```text
One additional business day of data may not materially improve model quality.
Daily retraining increases the risk of training failure.
Daily retraining increases runtime and operational load.
Daily model replacement increases the risk of accidental promotion.
Phase9 validates whether daily AI operation works; it does not require rebuilding models every day.
```

Initial retrain mode:

```text
WEEKLY_RETRAIN_DAILY_INFERENCE
```

Supported retrain modes:

```text
INFERENCE_ONLY_DAILY
WEEKLY_RETRAIN_DAILY_INFERENCE
DAILY_RETRAIN_EXPERIMENTAL
```

Mode definitions:

```text
INFERENCE_ONLY_DAILY:
  Update data, generate features, run inference, and report every business day.
  Retraining is manual only.

WEEKLY_RETRAIN_DAILY_INFERENCE:
  Update data, generate features, run inference, and report every business day.
  Run light retraining on a weekly schedule when manifests and data checks pass.
  This is the initial Phase9 mode.

DAILY_RETRAIN_EXPERIMENTAL:
  Update data, generate features, run inference, and optionally retrain every business day.
  This mode is not the initial default.
  It may be tested only after training runtime and stability are measured in Phase9.
```

Daily retrain may be considered only if:

```text
training runtime is consistently short, roughly 5-10 minutes per required AI
training manifests are stable
leakage audits pass
model promotion is explicit and reversible
daily inference remains reliable
no operational failures are introduced
```

If training takes one hour or more, weekly or monthly retraining remains the default.

Default policy:

```text
Candidate AI: no daily model retraining by default
Opportunity AI: no daily model retraining by default
Position Management AI: no daily model retraining by default
Capital Allocation AI: no training; rule / policy engine
```

Daily required action:

```text
Record active model_version
Record train_until
Record data_until
Record feature_schema_hash
Record training_manifest reference
Verify model artifacts are allowed for decision_for
```

Retraining may be scheduled, but not automatically forced every day.

Recommended retraining cadence:

```text
Candidate AI: retrain only when candidate model design requires promotion, feature schema changes, or monthly/weekly retraining is explicitly approved
Opportunity AI: periodic retraining, initially weekly or manual, because Phase5-E model training uses historical labels and must protect label horizon
Position Management AI: no daily retraining in current Phase6-A policy-style implementation; recalibration may be periodic/manual
Capital Allocation AI: no AI training; use CAP5 primary policy and CAP4/POLICY_Y shadows
```

### 4.4.1 Retrain Policy by AI

Candidate AI:

```text
default_retrain_frequency: weekly light retrain if Candidate model training is enabled; monthly full retrain / model audit
manual_retrain_allowed: yes
force_retrain_conditions:
  feature schema changes
  candidate model code changes
  major universe / listed info handling changes
  repeated candidate quality degradation
  explicit operator request
skip_retrain_conditions:
  J-Quants data update incomplete
  feature generation failed
  leakage audit failed
  previous model remains eligible and no force condition exists
  retrain runtime budget exceeded
required_manifest_fields:
  training_run_id
  model_name
  model_version
  train_until
  data_until
  feature_schema_version
  feature_schema_hash
  source_data_manifest_refs
  dataset_row_count
  leakage_audit_status
  model_artifact_path
  metrics_path
  audit_path
```

Opportunity AI:

```text
default_retrain_frequency: weekly light retrain; monthly full retrain / model audit
manual_retrain_allowed: yes
force_retrain_conditions:
  feature schema changes
  model code changes
  label generation changes
  sustained ranking quality degradation
  large market regime shift observed in validation reports
  explicit operator request
skip_retrain_conditions:
  label horizon is not fully observable for train_until
  training dataset missing or stale
  leakage audit failed
  model artifact from previous run remains eligible
  retrain runtime budget exceeded
required_manifest_fields:
  training_run_id
  model_name
  model_version
  target_label
  label_horizon
  train_until
  data_until
  feature_schema_version
  feature_schema_hash
  feature_columns
  dataset_path
  train_rows
  validation_rows
  test_rows
  leakage_audit_status
  forbidden_feature_audit
  model_artifact_path
  metrics_path
  audit_path
```

Position Management AI:

```text
default_retrain_frequency: monthly recalibration / policy audit; weekly light recalibration only if Phase6 modelized training is introduced
manual_retrain_allowed: yes
force_retrain_conditions:
  position feature schema changes
  position policy code changes
  repeated poor EXIT / REDUCE / HOLD review outcomes
  holding period behavior becomes unstable
  explicit operator request
skip_retrain_conditions:
  current Phase6-A policy implementation has no trainable model artifact
  holding snapshot is missing
  opportunity inference artifact missing
  leakage audit failed
  retrain runtime budget exceeded
required_manifest_fields:
  training_run_id or calibration_run_id
  model_or_policy_name
  model_or_policy_version
  train_until
  data_until
  feature_schema_version
  feature_schema_hash
  holding_input_schema
  opportunity_input_ref
  leakage_audit_status
  calibration_metrics_path
  audit_path
```

Capital Allocation AI:

```text
default_retrain_frequency: none; monthly policy audit only
manual_retrain_allowed: no model retrain; manual policy audit allowed
force_retrain_conditions:
  not applicable for model retraining
  policy parameter change requires explicit design/audit
  CAP5/CAP4/POLICY_Y comparison indicates policy review need
skip_retrain_conditions:
  always skip model retraining because Capital Allocation is policy/rule based in Phase9
required_manifest_fields:
  policy_name
  policy_version
  primary_policy = CAP5
  shadow_policies = CAP4, POLICY_Y_CAP4_EDGE08_CONF5
  config_hash
  data_until
  decision_for
  audit_path
  broker_api_executed = false
  live_order_executed = false
```

### 4.4.2 Training Effectiveness Measurement

Training runtime measurement answers:

```text
How long did retraining take?
```

Training Effectiveness Measurement answers:

```text
Was retraining worth doing?
```

Purpose:

```text
Measure whether retraining improves daily decisions enough to justify operational cost.
Compare weekly retrain and daily retrain experimental behavior.
Decide in the second half of Phase9 whether DAILY_RETRAIN_EXPERIMENTAL deserves a limited trial.
```

Comparison design:

```text
Model A:
  retrain_mode = WEEKLY_RETRAIN_DAILY_INFERENCE
  role = official
  Paper Ledger update allowed after Human Review approval

Model B:
  retrain_mode = DAILY_RETRAIN_EXPERIMENTAL
  role = shadow / experimental
  Paper Ledger update prohibited
```

Initial Phase9 policy:

```text
Model A is the official model path.
Model B is shadow evaluation only.
Model B decisions must not create virtual orders.
Model B decisions must not update the official Paper Ledger.
Model B may produce comparison artifacts and reports only.
```

Measurement fields:

```text
model_id
retrain_mode
role
train_until
data_until
feature_schema_hash
model_artifact_hash
training_runtime_seconds
inference_runtime_seconds
prediction_count
decision_count
buy_candidate_overlap_rate
sell_candidate_overlap_rate
top_rank_overlap_rate
confidence_delta
virtual_pnl_delta
win_rate_delta
pf_delta
max_drawdown_delta
stability_score
degradation_flag
ledger_update_allowed
ledger_update_executed
```

Comparison metrics:

```text
buy_candidate_overlap_rate:
  overlap between official BUY candidates and shadow BUY candidates

sell_candidate_overlap_rate:
  overlap between official SELL candidates and shadow SELL candidates

top_rank_overlap_rate:
  overlap of top-ranked Opportunity candidates

confidence_delta:
  difference between official public_confidence_score and shadow public_confidence_score

virtual_pnl_delta:
  shadow paper-performance estimate minus official paper-performance estimate

stability_score:
  decision stability score based on candidate overlap, rank overlap, and score volatility

degradation_flag:
  true when shadow retrain worsens stability, drawdown, PF, or validation quality beyond thresholds
```

Decision rule:

```text
DAILY_RETRAIN_EXPERIMENTAL remains unavailable for official Paper Ledger updates unless runtime, stability, and quality all improve or remain acceptable.
Daily retrain must show repeatable value, not one lucky day.
Operator approval is required before any retrain mode promotion.
Mode promotion requires a new audit note.
```

Output artifacts:

```text
reports/phase_reports/phase9_training_effectiveness_measurement.json
docs/phase_reports/phase9_training_effectiveness_measurement.md
reports/phase_reports/phase9_model_comparison_report.json
docs/phase_reports/phase9_model_comparison_report.md
```

Training manifest must include:

```text
training_run_id
model_name
model_version
created_at
train_until
data_until
label_horizon
feature_schema_version
feature_schema_hash
feature_columns
dataset_path
dataset_row_count
train_rows
validation_rows
test_rows
leakage_audit_status
forbidden_feature_audit
source_data_manifest_refs
model_artifact_path
metrics_path
audit_path
promotion_status
paper_trading_executed = false
broker_api_executed = false
live_order_executed = false
```

Model eligibility rule:

```text
model.train_until <= decision_for
model.data_until <= decision_for
feature_schema_hash == inference_feature_schema_hash
leakage_audit_status == OK
model artifact exists and is readable
model was not trained on Paper Ledger, Broker Snapshot, realized PnL, selected symbols, bought symbols, cash, portfolio value, backtest results, or PM multiplier imitation
```

If any model eligibility check fails:

```text
Phase9 daily run status = INVALID_INPUT
No Paper Ledger update
Daily Report includes blocked model and manifest reason
```

### 4.5 Daily Inference

```text
18:00 - 18:45
```

The normal inference flow is:

```text
Candidate AI
  -> Opportunity AI
  -> Position Management AI
  -> Capital Allocation AI
  -> Order Manager
```

Candidate AI:

```text
Input: normalized J-Quants daily_quotes up to data_until, listed universe, trading calendar
Output: candidate symbols for decision_for
Required metadata: data_until, feature_version, feature_schema_hash, source_manifest_refs
Leakage rule: no row after data_until
```

Opportunity AI:

```text
Input: Candidate output, current feature artifact, active Opportunity model
Output: ranked buy candidates with expected_edge_score, buy_rank, downside_risk_score, reasons
Required metadata: model_version, train_until, data_until, inference_run_id
Leakage rule: no labels or future outcome columns at inference
```

Position Management AI:

```text
Input: Paper Ledger holdings, mark-to-market prices up to data_until, Opportunity output, features
Output: HOLD / REDUCE / EXIT / ADD-style signals and reasons
Required metadata: model_version or policy_version, data_until, holding_days
Leakage rule: holdings are Paper Ledger state only; no realized PnL learning signal
```

Capital Allocation AI:

```text
Input: Opportunity output, Position Management output, Paper Ledger portfolio snapshot
Primary policy: CAP5
Shadow policies: CAP4, POLICY_Y_CAP4_EDGE08_CONF5
Output: allocation decisions
Constraints: 100-share lot, 5% cash buffer, max 20% position weight, conservative T+2 cash unavailable, SELL_FIRST_BUY_AFTER_FILL
```

Order Manager:

```text
Input: allocation decisions, Paper Ledger, optional moomoo REAL read-only Broker Snapshot, Safety state
Output: non-executable OrderPlan and Human Review report
```

OrderPlan remains:

```text
executable = false
live_order_allowed = false
requires_human_review = true
```

### 4.6 Human Review

```text
18:45 - 19:15
```

Human Review decisions:

```text
approved
rejected
needs_change
```

Rules:

```text
OrderPlan is never automatically executed
approved only permits internal Paper Ledger virtual order processing
approved does not permit live order
rejected does not update Paper Ledger
needs_change does not update Paper Ledger
unreviewed does not update Paper Ledger
```

Review checklist:

```text
Safety status is not locked for normal plan
data_until / decision_for / virtual_execution_date are clear
BUY / SELL / HOLD recommendations are understandable
SELL_FIRST_BUY_AFTER_FILL dependencies are visible
cash buffer and lot size are respected
missing price or halted symbol warnings are visible
OrderPlan remains non-executable
```

### 4.7 Paper Ledger Virtual Order Creation

```text
19:15 - 19:30
```

If Human Review decision is `approved`, Phase9 records virtual paper orders for the next business day.

The approved plan creates:

```text
virtual_order_date = next JP business day after decision_for
virtual_execution_date = virtual_order_date
status = PENDING_VIRTUAL_FILL
fill_policy = next_business_day_open_v1
```

No actual Broker API call is made.

If Human Review is `rejected` or `needs_change`:

```text
No Paper Ledger order is created
Daily Report records review decision
OrderPlan remains archived for audit
```

### 4.8 Virtual Fill Processing

```text
Next business day after J-Quants open price data is available
```

Initial fill policy:

```text
BUY fill price = virtual_execution_date normalized open price
SELL fill price = virtual_execution_date normalized open price
slippage = 0 initially, separately reported as assumption
commission = 0 initially, separately reported as assumption
partial fill = not supported initially
cash availability = conservative T+2 cash unavailable for planning; Paper Ledger cash changes at virtual fill time for accounting
```

Fill order:

```text
1. SELL virtual fills
2. BUY virtual fills whose sell dependency is filled
3. BUY virtual fills without dependency
```

Unfilled conditions:

```text
open price missing
open price <= 0
daily quote row missing
symbol absent from listed/tradable universe
symbol marked suspended / halted by available data
abnormal price movement beyond configured guard threshold
quantity not aligned to 100-share lot
cash insufficient after SELL_FIRST_BUY_AFTER_FILL processing
Safety lock blocks fill processing
```

No Fill reason codes:

```text
OPEN_PRICE_MISSING -> NO_FILL
TRADING_HALTED -> NO_FILL
LIMIT_UP_BUY -> NO_FILL
LIMIT_DOWN_SELL -> NO_FILL
PRICE_ABNORMAL -> NO_FILL
DAILY_QUOTE_MISSING -> NO_FILL
LISTED_INFO_NOT_TRADABLE -> NO_FILL
LOT_SIZE_INVALID -> NO_FILL
CASH_INSUFFICIENT -> NO_FILL
SELL_DEPENDENCY_NOT_FILLED -> NO_FILL
SAFETY_LOCKED -> NO_FILL
```

Unfilled behavior:

```text
Do not estimate with future close
Do not fill using broker price
Do not backfill from later dates automatically
Paper Ledger is not executed for that item
Record status = no_fill, rejected, or pending according to the virtual order state
Record reason_code
Carry or expire pending order according to configured Phase9 policy
Daily Report includes the no-fill reason
```

Initial pending order expiry:

```text
Expire unfilled virtual orders at end of virtual_execution_date.
Do not carry to the next day unless Phase9-B explicitly adds a carry policy.
```

## 5. Report Design

Phase9 produces internal reports for operation and public-facing reports for blog / note / X publication.

The public report is derived from the internal report, but sensitive implementation details are removed.

### 5.1 Daily Operation Report

Daily Operation Report is internal.

Outputs:

```text
Markdown: reports/phase_reports/phase9_daily/YYYY-MM-DD_daily_paper_trading_report.md
JSON: reports/phase_reports/phase9_daily/YYYY-MM-DD_daily_paper_trading_report.json
```

Required report fields:

```text
run_id
run_date
data_until
train_until by model
decision_for
virtual_order_date
virtual_execution_date
market data status
Safety status
Broker Snapshot reference status
Paper Ledger id
OrderPlan id
Human Review status
```

Recommendation sections:

```text
today's BUY candidates
today's SELL candidates
today's HOLD candidates
decision rationale
SELL_FIRST_BUY_AFTER_FILL dependencies
blocked / waiting items
```

Paper Trading sections:

```text
virtual fill policy
approved / rejected / needs_change status
filled orders
unfilled orders and reasons
buy-if-executed outcome
sell-if-executed outcome
ledger diff
```

Performance sections:

```text
paper total equity
cash
buying_power
positions
position count
gross exposure
realized PnL
unrealized PnL
daily return
cumulative return
win rate
average win
average loss
profit factor
max drawdown
trade count
turnover
holding days
```

Safety sections:

```text
live order prohibited confirmation
Broker submit/cancel/modify prohibited confirmation
moomoo REAL read-only confirmation
Paper Ledger vs Broker Snapshot separation confirmation
review-only status when locked
warnings
tomorrow checklist
```

Internal-only content:

```text
detailed scores
AI decision internals
cash
positions
risk state
safety details
ledger diff
model eligibility checks
training manifest references
feature schema hashes
```

### 5.2 Public Daily Report / Blog Draft

Public Daily Report is for blog / note / X-oriented publication drafts.

Outputs:

```text
Markdown: reports/public/phase9_daily/YYYY-MM-DD_public_daily_report.md
JSON: reports/public/phase9_daily/YYYY-MM-DD_public_daily_report.json
Blog Draft: reports/public/phase9_daily/YYYY-MM-DD_blog_draft.md
```

Public report content:

```text
AI's daily market view
what the AI decided today
today's notable symbols
buy / sell / hold summary in plain language
public_confidence_score
public_confidence_label
short_reason
caution_note
paper asset trend
major portfolio movement
commentary / operator note
next business day's focus points
```

Do not publish:

```text
detailed scores
internal features
model structure
risk management logic details
safety device internal design
raw manifests
account identifiers
broker snapshot details
unmasked operational paths
```

Public report rule:

```text
Public Daily Report must be generated after the Internal Daily Operation Report.
Public content must be redacted from internal JSON/Markdown, not produced from raw internal artifacts directly.
Public Report publication is manual; Phase9 does not auto-post to blog, note, or X.
```

Public wording rule:

```text
Use "virtual operation", "under validation", and "self-directed investment decision" caution language.
Do not write "must buy", "will rise", "guaranteed", or equivalent definitive expressions.
Do not present the report as investment advice.
Do not expose internal logic, detailed features, model internals, or safety internals.
```

Required disclaimer:

```text
This report is generated from an internal paper trading validation system.
It is a virtual operation / research record, not investment advice.
Actual investment decisions are the reader's own responsibility.
```

### 5.2.1 Public Confidence Score

Public Confidence Score is a reader-facing explanation score for Public Daily Report / Blog Draft.

It is not the raw model score.

Purpose:

```text
Make AI decisions understandable for public readers.
Avoid saying "the AI says buy" as a directive.
Enable later validation such as "what happened when public_confidence_score >= 80."
```

Internal scores:

```text
raw model score
opportunity score
position score
allocation score
risk score
safety state
```

Public fields:

```text
public_confidence_score
public_confidence_label
short_reason
caution_note
```

Mapping policy:

```text
Public Confidence Score is derived from internal signals through a redacted mapper.
The mapper may use internal scores, risk flags, Safety state, liquidity checks, and No Fill risk.
The mapper must not reveal raw internal score values, feature values, model structure, or safety internals.
```

Label bands:

```text
90-100: very strong / 非常に強い
75-89: strong / 強い
60-74: slightly strong / やや強い
40-59: neutral / 中立
25-39: weak / 弱い
0-24: watch only / 見送り
```

Example public expression:

```text
本日のAI総合判断:
やや強気
信頼度 72/100

買い候補:
7203 トヨタ自動車
AI信頼度 81/100
短評: 需給とトレンドが比較的良好。ただし仮想運用での検証中。
```

Prohibited public expression:

```text
必ず上がる
買うべき
確実
保証
損しない
```

Public Confidence Score audit fields:

```text
symbol
decision_side
public_confidence_score
public_confidence_label
short_reason
caution_note
redaction_status
disclaimer_present
source_order_plan_id
source_report_id
```

### 5.3 Report Generation Timing

Initial report generation schedule:

```text
16:30 Market close
17:00 Data update confirmation
18:00 Feature generation
19:00 Inference execution
20:00 Internal Daily Operation Report generation
20:05 Public Daily Report / Blog Draft generation
20:10 Human Review
Next business day: Paper Trading virtual fill processing
```

Report generation failure policy:

```text
Internal Daily Operation Report generation must succeed for every run, including halt runs.
Public Daily Report may be skipped if internal report generation fails.
Public Daily Report must show "not publication-ready" if required redaction checks fail.
```

### 5.4 Weekly Report

Weekly Report is generated after the final business day of each week.

Content:

```text
weekly performance
best symbols
worst symbols
trade count
AI decision review
Human Review summary
Safety events
Paper Ledger integrity summary
next week's notable symbols
```

### 5.5 Monthly Report

Monthly Report is generated after the final business day of each month.

Content:

```text
monthly performance
TOPIX comparison
win rate
profit factor
max drawdown
best trade
worst trade
turnover
average holding days
AI improvement points
model / policy audit notes
```

### 5.6 Public Report

Public Report is a sanitized reader-facing version for blog, note, or X.

Content:

```text
AI's judgment today
notable symbols
asset trend
short commentary
next business day's focus
weekly or monthly summary when applicable
```

Public Report must not include:

```text
detailed scores
internal feature values
model structure
model parameters
risk management logic details
safety internals
broker account details
```

## 6. Safety Design

Phase9 safety rules:

```text
No live order path exists
No Broker submit/cancel/modify function may be called
No unlock_trade may be called
No OpenD automatic startup
No automatic login/logout
No secret persistence
No raw moomoo response persistence
No plain account id persistence
```

moomoo boundary:

```text
REAL = read-only reference only
SIMULATE = not used for orders in Phase9
```

Allowed moomoo methods:

```text
get_acc_list
accinfo_query
position_list_query
order_list_query
history_order_list_query
```

Broker Snapshot and Paper Ledger separation:

```text
Broker Snapshot is external reference / reconciliation input
Paper Ledger is the source of virtual trading state
Broker Snapshot never mutates Paper Ledger without explicit Phase9 reconciliation logic and Human Review
Paper Ledger never implies broker position ownership
```

Safety locked behavior:

```text
Order Manager returns REVIEW_ONLY_LOCKED
Daily Report is generated
Human Review may inspect diagnostics
No normal Paper Ledger order creation
No virtual fill processing
```

Reconciliation halt behavior:

```text
Order Manager returns REVIEW_ONLY_RECONCILIATION_HALT
No normal plan generation
No Paper Ledger update
Daily Report explains mismatch
```

## 7. Phase9 Run Manifest

Each daily run must write a manifest.

Recommended path:

```text
.runtime/phase9/daily_runs/YYYY-MM-DD/run_manifest.json
```

Required fields:

```text
run_id
schema_version
created_at
run_mode = dry_run | paper_trading
data_until
train_until
decision_for
virtual_order_date
virtual_execution_date
jquants_manifest_refs
normalized_data_refs
listed_info_ref
feature_artifact_refs
feature_schema_hashes
training_manifest_refs
model_versions
inference_artifact_refs
capital_allocation_artifact_refs
order_plan_ref
human_review_ref
paper_ledger_before_ref
paper_ledger_after_ref
broker_snapshot_ref
safety_report_ref
daily_report_ref
status
blocked_reasons
warnings
no_live_order_confirmed
broker_order_api_called = false
```

The manifest is the primary audit object for daily operation reproducibility.

## 8. Future Information Controls

Phase9 must not use:

```text
future quote after data_until for decision generation
future labels for inference
backtest result as training feature
Paper Ledger realized PnL as training feature
Broker account cash as training feature
portfolio value as training feature
selected symbols as training target
bought symbols as training target
PM multiplier imitation
```

Allowed operational state:

```text
Paper Ledger holdings for Position Management and Capital Allocation
Paper Ledger cash for allocation constraints
Paper Ledger executions for performance reporting
Broker Snapshot for read-only reconciliation report
```

These operational states may drive daily decisions, but must not be added to AI training data.

## 9. 30 Business Day Validation

Phase9 validation target:

```text
30 JP business days
```

Tracker fields:

```text
business_day_index
run_date
decision_for
data_until
run_status
market_data_status
model_status
safety_status
human_review_status
order_plan_status
paper_ledger_status
daily_report_status
blocked_reason
paper_total_equity
daily_return
cumulative_return
trade_count
win_rate
profit_factor
max_drawdown
notes
```

Phase9 KPI emphasizes operational stability before profit.

Operational KPI:

```text
daily pipeline success rate >= 95%
data update success rate >= 95%
feature generation success rate >= 95%
inference success rate >= 95%
internal report generation success rate = 100%
public report draft generation success rate >= 95% when internal report is available
Paper Ledger integrity = 100%
Human Review completion rate >= 90%
Safety halt correctness = 100%
no live order violation = 100%
Broker order API call count = 0
OpenD automatic startup count = 0
unlock_trade call count = 0
```

Model operation KPI:

```text
training manifest availability = 100% for active models
model eligibility check success rate >= 95%
feature schema hash recorded rate = 100%
training runtime measurement coverage = 100% for scheduled retrain runs
training effectiveness measurement coverage = 100% for shadow comparison days
shadow model comparison report generation rate >= 95% when shadow mode is enabled
unexpected model promotion count = 0
no shadow model ledger update violation rate = 100%
```

Public report KPI:

```text
public confidence score generation rate >= 95% when Public Daily Report is generated
public report disclaimer presence rate = 100%
public redaction checker pass rate = 100%
prohibited definitive expression count = 0
internal score leakage count = 0
```

Paper Trading KPI:

```text
virtual fill audit coverage = 100%
no-fill reason coverage = 100%
ledger diff generation success rate = 100%
unexplained cash discrepancy count = 0
unexplained position discrepancy count = 0
```

Performance metrics are tracked, but they are not the primary Phase9 success condition:

```text
paper total equity
daily return
cumulative return
win rate
profit factor
max drawdown
trade count
turnover
average holding days
```

Exit criteria:

```text
30 business days completed
daily reports are understandable
Paper Ledger remains internally consistent
Safety reports are reviewed
Human Review process is practical
OrderPlans remain non-executable
Broker order path remains absent
Phase9 operational KPI thresholds are met or every miss has an accepted root-cause note
```

## 10. Phase9-B and Later Implementation Units

Phase9-B:

```text
daily run manifest schema and writer
business date resolver for data_until / decision_for / virtual_execution_date
market data readiness checker
data update / feature generation / inference mandatory-step tracker
initial Paper Ledger creation CLI
```

Phase9-C:

```text
daily AI pipeline runner skeleton
Candidate / Opportunity / Position / Capital artifact connection
model eligibility checker
training manifest reader
feature schema hash recorder
retrain mode configuration: INFERENCE_ONLY_DAILY / WEEKLY_RETRAIN_DAILY_INFERENCE / DAILY_RETRAIN_EXPERIMENTAL
per-AI retrain_policy reader
training runtime measurement skeleton
training effectiveness measurement skeleton
shadow daily retrain evaluation
model comparison report writer
```

Training runtime measurement outputs:

```text
reports/phase_reports/phase9_training_runtime_measurement.json
docs/phase_reports/phase9_training_runtime_measurement.md
```

Training runtime measurement fields:

```text
ai_name
training_run_id
model_version
retrain_mode
started_at
finished_at
elapsed_seconds
status
data_until
train_until
dataset_row_count
feature_column_count
manifest_path
metrics_path
audit_path
runtime_bucket = under_10min | under_60min | over_60min
daily_retrain_candidate
recommended_retrain_frequency
```

Training effectiveness measurement outputs:

```text
reports/phase_reports/phase9_training_effectiveness_measurement.json
docs/phase_reports/phase9_training_effectiveness_measurement.md
reports/phase_reports/phase9_model_comparison_report.json
docs/phase_reports/phase9_model_comparison_report.md
```

Phase9-D:

```text
Order Manager daily integration
Human Review gate integration
approved-only virtual paper order creation
rejected / needs_change no-op path
```

Phase9-E:

```text
next-business-day open virtual fill processor
No Fill Policy and reason handling
Paper Ledger snapshot writer
Paper Ledger diff writer
```

Phase9-F:

```text
Daily Report markdown/json writer
Public Daily Report writer
Blog Draft writer
internal-to-public redaction checker
public confidence score mapper
public report disclaimer writer
public redaction checker extension
Weekly Report writer
Monthly Report writer
performance metrics calculator
30 business day tracker
Phase9 KPI calculator
primary vs shadow policy comparison placeholders
```

Phase9-G:

```text
Phase9 audit script
no broker order API audit
no external connection by default audit
Safety locked review-only tests
missing data halt tests
future leakage date relation tests
```

Recommended initial command shape:

```text
scripts/run_phase9a_daily_paper_trading.py --date YYYY-MM-DD --dry-run
```

Default behavior:

```text
no broker API order call
no OpenD startup
no login/logout
no live order
fail closed on missing inputs
produce reviewable reports
```

## 11. Phase9-A Completion Judgment

Phase9-A is complete when this design is accepted and Phase9-B can implement from it without changing safety scope.

Required confirmations:

```text
Daily schedule is defined
J-Quants daily_quotes / listed info / data_until checks are defined
Daily required work is data update / feature generation / inference, not mandatory retraining
AI retraining vs inference policy is defined
Initial retrain mode is WEEKLY_RETRAIN_DAILY_INFERENCE
Daily retrain remains DAILY_RETRAIN_EXPERIMENTAL, not the initial required mode
Retrain policy is defined for Candidate / Opportunity / Position Management / Capital Allocation
model_version / train_until / data_until / feature_schema_hash / training_manifest are defined
Candidate -> Opportunity -> Position -> Capital -> Order Manager flow is defined
decision_for / virtual_order_date / virtual_execution_date relationship is defined
future information is excluded
Human Review approved-only Paper Ledger reflection is defined
No Fill Policy is defined
Daily / Weekly / Monthly / Public Report content is defined
Public Daily Report and Blog Draft are Phase9 deliverables
Phase9 KPI thresholds are defined for 30 business day validation
training runtime measurement is assigned to Phase9-B or later implementation
Training Effectiveness Measurement is defined
weekly retrain official path and daily retrain shadow path comparison is defined
shadow DAILY_RETRAIN_EXPERIMENTAL cannot update the official Paper Ledger
Public Confidence Score is defined for Public Report / Blog Draft
internal scores and public scores are separated
public disclaimer, redaction, and definitive-expression restrictions are defined
Safety boundaries remain Phase8-compatible
Phase9-B and later implementation units are organized
```
