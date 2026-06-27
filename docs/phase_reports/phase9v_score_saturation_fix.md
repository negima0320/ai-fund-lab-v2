# Phase9-V Score Saturation Fix

- status: PASS
- decision_for: 2026-06-24
- data_until: 2026-06-24

## Root Cause

Candidate and Opportunity rankings used clipped 0-100 scores, so many rows tied at 100 and fell through to code ascending order.

## Fix

- Candidate rank: rank_score from raw_score_preclip
- Opportunity rank: rank_score from opportunity raw_score_preclip using candidate_rank_score
- Tie breaker: rank_score desc, liquidity desc, code asc
- Public score: public confidence is bounded 0-100 for display and is separate from rank_score

## Before / After Distribution

- Candidate before score unique_count: 50 min=97.353834 max=299.893366
- Candidate after rank_score unique_count: 50 min=97.353834 max=299.893366
- Opportunity before score unique_count: 20 min=158.634256 max=339.09711
- Opportunity after rank_score unique_count: 20 min=158.634256 max=339.09711
- expected_edge before unique_count: 20 top10=[1.0, 0.775923, 0.43677, 0.387661, 0.365742, 0.318114, 0.292642, 0.210795, 0.16075, 0.149946]
- expected_edge after unique_count: 20 top10=[1.0, 0.775923, 0.43677, 0.387661, 0.365742, 0.318114, 0.292642, 0.210795, 0.16075, 0.149946]

## Top10 Before

Candidate:
- rank 1: 92560 {'rank': 1, 'code': '92560', 'score': 299.893366, 'raw_score_preclip': 299.893366, 'rank_score': 299.893366, 'score_clipped': 100.0, 'rank_liquidity': 255555.0}
- rank 2: 68970 {'rank': 2, 'code': '68970', 'score': 294.948123, 'raw_score_preclip': 294.948123, 'rank_score': 294.948123, 'score_clipped': 100.0, 'rank_liquidity': 88675.0}
- rank 3: 35440 {'rank': 3, 'code': '35440', 'score': 195.127703, 'raw_score_preclip': 195.127703, 'rank_score': 195.127703, 'score_clipped': 100.0, 'rank_liquidity': 82215.0}
- rank 4: 53670 {'rank': 4, 'code': '53670', 'score': 194.731615, 'raw_score_preclip': 194.731615, 'rank_score': 194.731615, 'score_clipped': 100.0, 'rank_liquidity': 2430535.0}
- rank 5: 72450 {'rank': 5, 'code': '72450', 'score': 175.891105, 'raw_score_preclip': 175.891105, 'rank_score': 175.891105, 'score_clipped': 100.0, 'rank_liquidity': 957310.0}
- rank 6: 65220 {'rank': 6, 'code': '65220', 'score': 175.864941, 'raw_score_preclip': 175.864941, 'rank_score': 175.864941, 'score_clipped': 100.0, 'rank_liquidity': 1127035.0}
- rank 7: 23930 {'rank': 7, 'code': '23930', 'score': 174.491829, 'raw_score_preclip': 174.491829, 'rank_score': 174.491829, 'score_clipped': 100.0, 'rank_liquidity': 53890.0}
- rank 8: 63360 {'rank': 8, 'code': '63360', 'score': 166.794301, 'raw_score_preclip': 166.794301, 'rank_score': 166.794301, 'score_clipped': 100.0, 'rank_liquidity': 393190.0}
- rank 9: 30860 {'rank': 9, 'code': '30860', 'score': 152.747514, 'raw_score_preclip': 152.747514, 'rank_score': 152.747514, 'score_clipped': 100.0, 'rank_liquidity': 2811960.0}
- rank 10: 49680 {'rank': 10, 'code': '49680', 'score': 151.980426, 'raw_score_preclip': 151.980426, 'rank_score': 151.980426, 'score_clipped': 100.0, 'rank_liquidity': 301485.0}

Opportunity:
- rank 1: 68970 {'rank': 1, 'code': '68970', 'opportunity_score': 339.09711, 'raw_score_preclip': 339.09711, 'rank_score': 339.09711, 'expected_edge_score': 1.0, 'rank_liquidity': 88675.0}
- rank 2: 92560 {'rank': 2, 'code': '92560', 'opportunity_score': 298.659493, 'raw_score_preclip': 298.659493, 'rank_score': 298.659493, 'expected_edge_score': 0.775923, 'rank_liquidity': 255555.0}
- rank 3: 53670 {'rank': 3, 'code': '53670', 'opportunity_score': 237.455025, 'raw_score_preclip': 237.455025, 'rank_score': 237.455025, 'expected_edge_score': 0.43677, 'rank_liquidity': 2430535.0}
- rank 4: 35440 {'rank': 4, 'code': '35440', 'opportunity_score': 228.592707, 'raw_score_preclip': 228.592707, 'rank_score': 228.592707, 'expected_edge_score': 0.387661, 'rank_liquidity': 82215.0}
- rank 5: 23930 {'rank': 5, 'code': '23930', 'opportunity_score': 224.637079, 'raw_score_preclip': 224.637079, 'rank_score': 224.637079, 'expected_edge_score': 0.365742, 'rank_liquidity': 53890.0}
- rank 6: 72450 {'rank': 6, 'code': '72450', 'opportunity_score': 216.042068, 'raw_score_preclip': 216.042068, 'rank_score': 216.042068, 'expected_edge_score': 0.318114, 'rank_liquidity': 957310.0}
- rank 7: 63360 {'rank': 7, 'code': '63360', 'opportunity_score': 211.445226, 'raw_score_preclip': 211.445226, 'rank_score': 211.445226, 'expected_edge_score': 0.292642, 'rank_liquidity': 393190.0}
- rank 8: 65220 {'rank': 8, 'code': '65220', 'opportunity_score': 196.674932, 'raw_score_preclip': 196.674932, 'rank_score': 196.674932, 'expected_edge_score': 0.210795, 'rank_liquidity': 1127035.0}
- rank 9: 49680 {'rank': 9, 'code': '49680', 'opportunity_score': 187.643637, 'raw_score_preclip': 187.643637, 'rank_score': 187.643637, 'expected_edge_score': 0.16075, 'rank_liquidity': 301485.0}
- rank 10: 460A0 {'rank': 10, 'code': '460A0', 'opportunity_score': 185.693901, 'raw_score_preclip': 185.693901, 'rank_score': 185.693901, 'expected_edge_score': 0.149946, 'rank_liquidity': 47735.0}

## Top10 After

Candidate:
- rank 1: 92560 {'rank': 1, 'code': '92560', 'rank_score': 299.893366, 'raw_score_preclip': 299.893366, 'score_clipped': 100.0, 'public_confidence_score': 100, 'rank_liquidity': 255555.0}
- rank 2: 68970 {'rank': 2, 'code': '68970', 'rank_score': 294.948123, 'raw_score_preclip': 294.948123, 'score_clipped': 100.0, 'public_confidence_score': 99, 'rank_liquidity': 88675.0}
- rank 3: 35440 {'rank': 3, 'code': '35440', 'rank_score': 195.127703, 'raw_score_preclip': 195.127703, 'score_clipped': 100.0, 'public_confidence_score': 69, 'rank_liquidity': 82215.0}
- rank 4: 53670 {'rank': 4, 'code': '53670', 'rank_score': 194.731615, 'raw_score_preclip': 194.731615, 'score_clipped': 100.0, 'public_confidence_score': 69, 'rank_liquidity': 2430535.0}
- rank 5: 72450 {'rank': 5, 'code': '72450', 'rank_score': 175.891105, 'raw_score_preclip': 175.891105, 'score_clipped': 100.0, 'public_confidence_score': 63, 'rank_liquidity': 957310.0}
- rank 6: 65220 {'rank': 6, 'code': '65220', 'rank_score': 175.864941, 'raw_score_preclip': 175.864941, 'score_clipped': 100.0, 'public_confidence_score': 63, 'rank_liquidity': 1127035.0}
- rank 7: 23930 {'rank': 7, 'code': '23930', 'rank_score': 174.491829, 'raw_score_preclip': 174.491829, 'score_clipped': 100.0, 'public_confidence_score': 63, 'rank_liquidity': 53890.0}
- rank 8: 63360 {'rank': 8, 'code': '63360', 'rank_score': 166.794301, 'raw_score_preclip': 166.794301, 'score_clipped': 100.0, 'public_confidence_score': 61, 'rank_liquidity': 393190.0}
- rank 9: 30860 {'rank': 9, 'code': '30860', 'rank_score': 152.747514, 'raw_score_preclip': 152.747514, 'score_clipped': 100.0, 'public_confidence_score': 56, 'rank_liquidity': 2811960.0}
- rank 10: 49680 {'rank': 10, 'code': '49680', 'rank_score': 151.980426, 'raw_score_preclip': 151.980426, 'score_clipped': 100.0, 'public_confidence_score': 56, 'rank_liquidity': 301485.0}

Opportunity:
- rank 1: 68970 {'rank': 1, 'code': '68970', 'rank_score': 339.09711, 'raw_score_preclip': 339.09711, 'candidate_rank_score': 294.948123, 'expected_edge_score': 1.0, 'public_confidence_score': 100, 'rank_liquidity': 88675.0}
- rank 2: 92560 {'rank': 2, 'code': '92560', 'rank_score': 298.659493, 'raw_score_preclip': 298.659493, 'candidate_rank_score': 299.893366, 'expected_edge_score': 0.775923, 'public_confidence_score': 87, 'rank_liquidity': 255555.0}
- rank 3: 53670 {'rank': 3, 'code': '53670', 'rank_score': 237.455025, 'raw_score_preclip': 237.455025, 'candidate_rank_score': 194.731615, 'expected_edge_score': 0.43677, 'public_confidence_score': 66, 'rank_liquidity': 2430535.0}
- rank 4: 35440 {'rank': 4, 'code': '35440', 'rank_score': 228.592707, 'raw_score_preclip': 228.592707, 'candidate_rank_score': 195.127703, 'expected_edge_score': 0.387661, 'public_confidence_score': 63, 'rank_liquidity': 82215.0}
- rank 5: 23930 {'rank': 5, 'code': '23930', 'rank_score': 224.637079, 'raw_score_preclip': 224.637079, 'candidate_rank_score': 174.491829, 'expected_edge_score': 0.365742, 'public_confidence_score': 62, 'rank_liquidity': 53890.0}
- rank 6: 72450 {'rank': 6, 'code': '72450', 'rank_score': 216.042068, 'raw_score_preclip': 216.042068, 'candidate_rank_score': 175.891105, 'expected_edge_score': 0.318114, 'public_confidence_score': 59, 'rank_liquidity': 957310.0}
- rank 7: 63360 {'rank': 7, 'code': '63360', 'rank_score': 211.445226, 'raw_score_preclip': 211.445226, 'candidate_rank_score': 166.794301, 'expected_edge_score': 0.292642, 'public_confidence_score': 58, 'rank_liquidity': 393190.0}
- rank 8: 65220 {'rank': 8, 'code': '65220', 'rank_score': 196.674932, 'raw_score_preclip': 196.674932, 'candidate_rank_score': 175.864941, 'expected_edge_score': 0.210795, 'public_confidence_score': 53, 'rank_liquidity': 1127035.0}
- rank 9: 49680 {'rank': 9, 'code': '49680', 'rank_score': 187.643637, 'raw_score_preclip': 187.643637, 'candidate_rank_score': 151.980426, 'expected_edge_score': 0.16075, 'public_confidence_score': 50, 'rank_liquidity': 301485.0}
- rank 10: 460A0 {'rank': 10, 'code': '460A0', 'rank_score': 185.693901, 'raw_score_preclip': 185.693901, 'candidate_rank_score': 150.180709, 'expected_edge_score': 0.149946, 'public_confidence_score': 49, 'rank_liquidity': 47735.0}

## 3063 J Group Holdings

- before candidate: None
- after candidate: None
- before opportunity: None
- after opportunity: None
- after allocation: None
- new decision: NOT_ALLOCATED

## Allocation After Fix

- rank None: 61810 {'rank': None, 'code': '61810', 'planned_quantity': 200, 'planned_amount': '20000', 'public_confidence_score': 42, 'rank_liquidity': None}

## Checks

- PASS: inference_ready INFERENCE_READY
- PASS: candidate_raw_rank_clipped_present
- PASS: opportunity_raw_rank_clipped_present
- PASS: candidate_rank_desc
- PASS: opportunity_rank_desc
- PASS: expected_edge_not_all_1
- PASS: public_confidence_not_all_100
- PASS: candidate_rank_not_code_asc
- PASS: opportunity_uses_candidate_rank_score
- PASS: ledger_not_changed
- PASS: broker_scheduler_prohibited_flags_false

## Safety

- ledger hash unchanged: True
- Broker order / OpenD / unlock_trade / real trade / scheduler changes were not executed.
