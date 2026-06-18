# Phase9-V Score Saturation Fix

- status: PASS
- decision_for: 2026-06-16
- data_until: 2026-06-16

## Root Cause

Candidate and Opportunity rankings used clipped 0-100 scores, so many rows tied at 100 and fell through to code ascending order.

## Fix

- Candidate rank: rank_score from raw_score_preclip
- Opportunity rank: rank_score from opportunity raw_score_preclip using candidate_rank_score
- Tie breaker: rank_score desc, liquidity desc, code asc
- Public score: public confidence is bounded 0-100 for display and is separate from rank_score

## Before / After Distribution

- Candidate before score unique_count: 1 min=100.0 max=100.0
- Candidate after rank_score unique_count: 50 min=101.776327 max=354.498235
- Opportunity before score unique_count: 1 min=100.0 max=100.0
- Opportunity after rank_score unique_count: 20 min=151.795325 max=408.265578
- expected_edge before unique_count: 1 top10=[1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
- expected_edge after unique_count: 20 top10=[1.0, 0.794669, 0.494459, 0.465795, 0.380858, 0.337099, 0.151518, 0.141637, 0.131158, 0.127645]

## Top10 Before

Candidate:
- rank 1: 166A0 {'rank': 1, 'code': '166A0', 'score': 100.0, 'rank_liquidity': None}
- rank 2: 19480 {'rank': 2, 'code': '19480', 'score': 100.0, 'rank_liquidity': None}
- rank 3: 212A0 {'rank': 3, 'code': '212A0', 'score': 100.0, 'rank_liquidity': None}
- rank 4: 215A0 {'rank': 4, 'code': '215A0', 'score': 100.0, 'rank_liquidity': None}
- rank 5: 23930 {'rank': 5, 'code': '23930', 'score': 100.0, 'rank_liquidity': None}
- rank 6: 285A0 {'rank': 6, 'code': '285A0', 'score': 100.0, 'rank_liquidity': None}
- rank 7: 30630 {'rank': 7, 'code': '30630', 'score': 100.0, 'rank_liquidity': None}
- rank 8: 34360 {'rank': 8, 'code': '34360', 'score': 100.0, 'rank_liquidity': None}
- rank 9: 34410 {'rank': 9, 'code': '34410', 'score': 100.0, 'rank_liquidity': None}
- rank 10: 34800 {'rank': 10, 'code': '34800', 'score': 100.0, 'rank_liquidity': None}

Opportunity:
- rank 1: 166A0 {'rank': 1, 'code': '166A0', 'opportunity_score': 100.0, 'expected_edge_score': 1.0, 'rank_liquidity': None}
- rank 2: 19480 {'rank': 2, 'code': '19480', 'opportunity_score': 100.0, 'expected_edge_score': 1.0, 'rank_liquidity': None}
- rank 3: 212A0 {'rank': 3, 'code': '212A0', 'opportunity_score': 100.0, 'expected_edge_score': 1.0, 'rank_liquidity': None}
- rank 4: 215A0 {'rank': 4, 'code': '215A0', 'opportunity_score': 100.0, 'expected_edge_score': 1.0, 'rank_liquidity': None}
- rank 5: 23930 {'rank': 5, 'code': '23930', 'opportunity_score': 100.0, 'expected_edge_score': 1.0, 'rank_liquidity': None}
- rank 6: 285A0 {'rank': 6, 'code': '285A0', 'opportunity_score': 100.0, 'expected_edge_score': 1.0, 'rank_liquidity': None}
- rank 7: 30630 {'rank': 7, 'code': '30630', 'opportunity_score': 100.0, 'expected_edge_score': 1.0, 'rank_liquidity': None}
- rank 8: 34360 {'rank': 8, 'code': '34360', 'opportunity_score': 100.0, 'expected_edge_score': 1.0, 'rank_liquidity': None}
- rank 9: 34410 {'rank': 9, 'code': '34410', 'opportunity_score': 100.0, 'expected_edge_score': 1.0, 'rank_liquidity': None}
- rank 10: 34800 {'rank': 10, 'code': '34800', 'opportunity_score': 100.0, 'expected_edge_score': 1.0, 'rank_liquidity': None}

## Top10 After

Candidate:
- rank 1: 41790 {'rank': 1, 'code': '41790', 'rank_score': 354.498235, 'raw_score_preclip': 354.498235, 'score_clipped': 100.0, 'public_confidence_score': 100, 'rank_liquidity': 435125.0}
- rank 2: 69760 {'rank': 2, 'code': '69760', 'rank_score': 279.662567, 'raw_score_preclip': 279.662567, 'score_clipped': 100.0, 'public_confidence_score': 82, 'rank_liquidity': 22926145.0}
- rank 3: 78780 {'rank': 3, 'code': '78780', 'rank_score': 242.320056, 'raw_score_preclip': 242.320056, 'score_clipped': 100.0, 'public_confidence_score': 73, 'rank_liquidity': 21440.0}
- rank 4: 23930 {'rank': 4, 'code': '23930', 'rank_score': 213.302712, 'raw_score_preclip': 213.302712, 'score_clipped': 100.0, 'public_confidence_score': 66, 'rank_liquidity': 49150.0}
- rank 5: 285A0 {'rank': 5, 'code': '285A0', 'rank_score': 203.458664, 'raw_score_preclip': 203.458664, 'score_clipped': 100.0, 'public_confidence_score': 64, 'rank_liquidity': 39232925.0}
- rank 6: 34800 {'rank': 6, 'code': '34800', 'rank_score': 196.37753, 'raw_score_preclip': 196.37753, 'score_clipped': 100.0, 'public_confidence_score': 62, 'rank_liquidity': 211770.0}
- rank 7: 69660 {'rank': 7, 'code': '69660', 'rank_score': 162.215995, 'raw_score_preclip': 162.215995, 'score_clipped': 100.0, 'public_confidence_score': 54, 'rank_liquidity': 3498815.0}
- rank 8: 63270 {'rank': 8, 'code': '63270', 'rank_score': 158.986257, 'raw_score_preclip': 158.986257, 'score_clipped': 100.0, 'public_confidence_score': 54, 'rank_liquidity': 886045.0}
- rank 9: 63870 {'rank': 9, 'code': '63870', 'rank_score': 153.937272, 'raw_score_preclip': 153.937272, 'score_clipped': 100.0, 'public_confidence_score': 52, 'rank_liquidity': 164970.0}
- rank 10: 69810 {'rank': 10, 'code': '69810', 'rank_score': 148.602681, 'raw_score_preclip': 148.602681, 'score_clipped': 100.0, 'public_confidence_score': 51, 'rank_liquidity': 40089040.0}

Opportunity:
- rank 1: 41790 {'rank': 1, 'code': '41790', 'rank_score': 408.265578, 'raw_score_preclip': 408.265578, 'candidate_rank_score': 354.498235, 'expected_edge_score': 1.0, 'public_confidence_score': 100, 'rank_liquidity': 435125.0}
- rank 2: 69760 {'rank': 2, 'code': '69760', 'rank_score': 355.604389, 'raw_score_preclip': 355.604389, 'candidate_rank_score': 279.662567, 'expected_edge_score': 0.794669, 'public_confidence_score': 88, 'rank_liquidity': 22926145.0}
- rank 3: 78780 {'rank': 3, 'code': '78780', 'rank_score': 278.609461, 'raw_score_preclip': 278.609461, 'candidate_rank_score': 242.320056, 'expected_edge_score': 0.494459, 'public_confidence_score': 70, 'rank_liquidity': 21440.0}
- rank 4: 23930 {'rank': 4, 'code': '23930', 'rank_score': 271.257883, 'raw_score_preclip': 271.257883, 'candidate_rank_score': 213.302712, 'expected_edge_score': 0.465795, 'public_confidence_score': 68, 'rank_liquidity': 49150.0}
- rank 5: 285A0 {'rank': 5, 'code': '285A0', 'rank_score': 249.474012, 'raw_score_preclip': 249.474012, 'candidate_rank_score': 203.458664, 'expected_edge_score': 0.380858, 'public_confidence_score': 63, 'rank_liquidity': 39232925.0}
- rank 6: 34800 {'rank': 6, 'code': '34800', 'rank_score': 238.25108, 'raw_score_preclip': 238.25108, 'candidate_rank_score': 196.37753, 'expected_edge_score': 0.337099, 'public_confidence_score': 60, 'rank_liquidity': 211770.0}
- rank 7: 63270 {'rank': 7, 'code': '63270', 'rank_score': 190.655062, 'raw_score_preclip': 190.655062, 'candidate_rank_score': 158.986257, 'expected_edge_score': 0.151518, 'public_confidence_score': 49, 'rank_liquidity': 886045.0}
- rank 8: 69660 {'rank': 8, 'code': '69660', 'rank_score': 188.121022, 'raw_score_preclip': 188.121022, 'candidate_rank_score': 162.215995, 'expected_edge_score': 0.141637, 'public_confidence_score': 48, 'rank_liquidity': 3498815.0}
- rank 9: 19480 {'rank': 9, 'code': '19480', 'rank_score': 185.433558, 'raw_score_preclip': 185.433558, 'candidate_rank_score': 143.720281, 'expected_edge_score': 0.131158, 'public_confidence_score': 48, 'rank_liquidity': 127260.0}
- rank 10: 69810 {'rank': 10, 'code': '69810', 'rank_score': 184.532528, 'raw_score_preclip': 184.532528, 'candidate_rank_score': 148.602681, 'expected_edge_score': 0.127645, 'public_confidence_score': 48, 'rank_liquidity': 40089040.0}

## 3063 J Group Holdings

- before candidate: {'rank': 7, 'code': '30630', 'score': 100.0, 'public_confidence_score': 100}
- after candidate: {'rank': 40, 'code': '30630', 'score': 108.529382, 'raw_score_preclip': 108.529382, 'rank_score': 108.529382, 'score_clipped': 100.0, 'public_confidence_score': 42, 'score_saturation_flag': True}
- before opportunity: {'rank': 7, 'code': '30630', 'opportunity_score': 100.0, 'expected_edge_score': 1.0, 'public_confidence_score': 100}
- after opportunity: None
- after allocation: None
- new decision: NOT_ALLOCATED_NOT_IN_OPPORTUNITY_TOP20

## Allocation After Fix

- rank None: 38250 {'rank': None, 'code': '38250', 'planned_quantity': 100, 'planned_amount': '24600', 'public_confidence_score': 40, 'rank_liquidity': None}

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
