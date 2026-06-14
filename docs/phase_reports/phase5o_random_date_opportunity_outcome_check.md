# Phase5-O Random Date Opportunity Outcome Check

## 1. Purpose

This report checks, on randomly sampled historical target dates, whether OpportunityTop5 improved 5bd / 10bd / 20bd outcomes versus CandidateTop50 and CandidateScoreTop5.

This is an offline outcome check. It is not live trading, Paper Trading, Broker API use, order placement, promotion, or capital allocation.

## 2. Sampling

- random seed: `42`
- years: `[2021, 2022, 2023, 2024, 2025]`
- samples per year: `1`
- sampled target dates: `['2021-09-30', '2022-01-13', '2023-10-10', '2024-04-17', '2025-04-08']`

## 3. By-Date Metrics

| target_date | selection_group | selected_count | mean_return_5bd | mean_return_10bd | mean_return_20bd | win_rate_5bd | win_rate_10bd | win_rate_20bd | positive_count_5bd | positive_count_10bd | positive_count_20bd | avg_max_return_20bd | avg_max_drawdown_20bd | top_n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-09-30 | CandidateScoreTop5 | 5 | -0.10721 | -0.168117 | -0.175922 | 0.0 | 0.0 | 0.0 | 0 | 0 | 0 | -0.031264 | -0.195633 | 5 |
| 2021-09-30 | CandidateTop50 | 50 | -0.045478 | -0.005612 | 0.056714 | 0.18 | 0.38 | 0.54 | 9 | 19 | 27 | 0.154169 | -0.102039 | 5 |
| 2021-09-30 | OpportunityTop5 | 5 | -0.007867 | 0.202665 | 0.605621 | 0.6 | 0.6 | 0.6 | 3 | 3 | 3 | 0.733864 | -0.025975 | 5 |
| 2022-01-13 | CandidateScoreTop5 | 5 | -0.079837 | -0.158992 | 0.033592 | 0.2 | 0.0 | 0.4 | 1 | 0 | 2 | 0.056735 | -0.169412 | 5 |
| 2022-01-13 | CandidateTop50 | 50 | -0.100689 | -0.187133 | -0.100815 | 0.1 | 0.04 | 0.2 | 5 | 2 | 10 | 0.043671 | -0.214932 | 5 |
| 2022-01-13 | OpportunityTop5 | 5 | -0.122583 | -0.234098 | -0.14451 | 0.0 | 0.0 | 0.0 | 0 | 0 | 0 | -0.030398 | -0.24597 | 5 |
| 2023-10-10 | CandidateScoreTop5 | 5 | -0.020314 | -0.035333 | 0.095634 | 0.2 | 0.2 | 0.8 | 1 | 1 | 4 | 0.171517 | -0.101221 | 5 |
| 2023-10-10 | CandidateTop50 | 50 | -0.047589 | -0.079353 | -0.038081 | 0.18 | 0.16 | 0.36 | 9 | 8 | 18 | 0.068755 | -0.14514 | 5 |
| 2023-10-10 | OpportunityTop5 | 5 | -0.003448 | -0.02506 | -0.015707 | 0.4 | 0.4 | 0.4 | 2 | 2 | 2 | 0.08505 | -0.082179 | 5 |
| 2024-04-17 | CandidateScoreTop5 | 5 | -0.007127 | -0.000479 | 0.107243 | 0.4 | 0.6 | 0.8 | 2 | 3 | 4 | 0.127876 | -0.099876 | 5 |
| 2024-04-17 | CandidateTop50 | 50 | 0.011211 | 0.00969 | 0.070052 | 0.62 | 0.58 | 0.56 | 31 | 29 | 28 | 0.155714 | -0.078793 | 5 |
| 2024-04-17 | OpportunityTop5 | 5 | 0.019512 | 0.029101 | 0.209453 | 0.6 | 0.6 | 0.8 | 3 | 3 | 4 | 0.350398 | -0.047566 | 5 |
| 2025-04-08 | CandidateScoreTop5 | 5 | 0.113823 | 0.090876 | 0.23406 | 1.0 | 1.0 | 1.0 | 5 | 5 | 5 | 0.302814 | -0.040693 | 5 |
| 2025-04-08 | CandidateTop50 | 50 | 0.068974 | 0.078055 | 0.166097 | 0.96 | 0.84 | 0.94 | 48 | 42 | 47 | 0.205839 | -0.052013 | 5 |
| 2025-04-08 | OpportunityTop5 | 5 | 0.082694 | 0.106473 | 0.240228 | 1.0 | 0.8 | 1.0 | 5 | 4 | 5 | 0.25888 | -0.051873 | 5 |

## 4. OpportunityTop5 By Date

### 2021-09-30

| code | buy_rank | expected_edge_score | return_5bd | return_10bd | return_20bd | max_return_20bd | max_drawdown_20bd |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 39360 | 1 | 0.033827 | 0.063919 | 0.787112 | 2.952518 | 3.169841 | 0.034438 |
| 15430 | 2 | -0.01944 | 0.023734 | 0.156646 | 0.063291 | 0.208861 | 0.011076 |
| 16750 | 3 | -0.020801 | 0.013191 | 0.14967 | 0.06139 | 0.191781 | 0.003551 |
| 89180 | 4 | -0.043484 | -0.083333 | 0.0 | 0.0 | 0.083333 | -0.083333 |
| 92740 | 5 | -0.044384 | -0.056848 | -0.080103 | -0.049096 | 0.015504 | -0.095607 |

### 2022-01-13

| code | buy_rank | expected_edge_score | return_5bd | return_10bd | return_20bd | max_return_20bd | max_drawdown_20bd |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 40200 | 1 | -0.001503 | -0.089253 | -0.209472 | -0.220856 | -0.033698 | -0.220856 |
| 38560 | 2 | -0.006578 | -0.12614 | -0.280255 | -0.149869 | -0.054577 | -0.280255 |
| 69660 | 3 | -0.007408 | -0.062699 | -0.180659 | -0.059511 | 0.024442 | -0.180659 |
| 93270 | 4 | -0.014538 | -0.156992 | -0.203166 | -0.102902 | -0.056728 | -0.203166 |
| 40170 | 5 | -0.019051 | -0.177833 | -0.29694 | -0.189413 | -0.031431 | -0.344913 |

### 2023-10-10

| code | buy_rank | expected_edge_score | return_5bd | return_10bd | return_20bd | max_return_20bd | max_drawdown_20bd |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 92250 | 1 | -0.000445 | -0.123064 | -0.087612 | -0.07661 | -0.007742 | -0.168297 |
| 72110 | 2 | -0.034285 | -0.048675 | -0.095098 | -0.150009 | 0.011433 | -0.164039 |
| 73690 | 3 | -0.03664 | 0.15132 | 0.127118 | 0.108332 | 0.294572 | -0.007376 |
| 59390 | 4 | -0.042503 | -0.035294 | -0.085294 | -0.002941 | 0.005882 | -0.086765 |
| 95010 | 5 | -0.045254 | 0.038474 | 0.015584 | 0.042695 | 0.121104 | 0.015584 |

### 2024-04-17

| code | buy_rank | expected_edge_score | return_5bd | return_10bd | return_20bd | max_return_20bd | max_drawdown_20bd |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 92350 | 1 | 0.064622 | 0.059772 | 0.204835 | 0.673606 | 1.145735 | -0.020819 |
| 36970 | 2 | -0.029563 | -0.051319 | -0.152156 | 0.106509 | 0.106509 | -0.154317 |
| 81360 | 3 | -0.032024 | -0.019334 | -0.011154 | -0.06953 | 0.044618 | -0.070459 |
| 37780 | 4 | -0.032277 | 0.097087 | 0.071845 | 0.099029 | 0.217476 | 0.007767 |
| 19800 | 5 | -0.032629 | 0.011355 | 0.032134 | 0.237652 | 0.237652 | 0.0 |

### 2025-04-08

| code | buy_rank | expected_edge_score | return_5bd | return_10bd | return_20bd | max_return_20bd | max_drawdown_20bd |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 49350 | 1 | 0.068599 | 0.050479 | 0.122715 | 0.126197 | 0.159269 | -0.042646 |
| 52500 | 2 | 0.024882 | 0.0978 | 0.293399 | 0.288509 | 0.316626 | -0.00978 |
| 58030 | 3 | 0.024765 | 0.096855 | 0.032425 | 0.396506 | 0.396506 | -0.065968 |
| 70120 | 4 | 0.021375 | 0.137426 | 0.126107 | 0.200551 | 0.232622 | -0.062981 |
| 68570 | 5 | 0.021127 | 0.030911 | -0.042281 | 0.189376 | 0.189376 | -0.077989 |

## 5. Comparison Summary

- Opportunity effective dates on 20bd mean return vs CandidateTop50: `['2021-09-30', '2023-10-10', '2024-04-17', '2025-04-08']`
- Opportunity ineffective dates on 20bd mean return vs CandidateTop50: `['2022-01-13']`
- initial conclusion: OpportunityTop5 beat CandidateTop50 on 20bd mean return for a majority of sampled dates.

## 6. Contributors And Draggers

- `2021-09-30`: top contributor `39360` return_20bd=2.952518; largest drag `92740` return_20bd=-0.049096
- `2022-01-13`: top contributor `69660` return_20bd=-0.059511; largest drag `40200` return_20bd=-0.220856
- `2023-10-10`: top contributor `73690` return_20bd=0.108332; largest drag `72110` return_20bd=-0.150009
- `2024-04-17`: top contributor `92350` return_20bd=0.673606; largest drag `81360` return_20bd=-0.06953
- `2025-04-08`: top contributor `58030` return_20bd=0.396506; largest drag `49350` return_20bd=0.126197

## 7. Caveats

- sample size is small
- Phase5 primary horizon is 20 business days
- 5bd / 10bd are auxiliary observations
- future outcome is evaluation-only
- this is not real trading, Paper Trading, Broker API, order placement, capital allocation, promotion, or reader switch
