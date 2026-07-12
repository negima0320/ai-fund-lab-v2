#!/bin/bash

echo "========== BROKER SNAPSHOT =========="
jq '{
  provider,
  source,
  data_origin,
  mock_used,
  fixture_used,
  authenticity_status,
  account_alignment_status,
  read_only
}' .runtime/runtime_state/broker_readonly/2026-07-10/tachibana_snapshot.json

echo
echo "========== BROKER POSITIONS =========="
jq '.positions[] | {
  issue_code,
  quantity,
  source,
  account_type,
  raw_clmid
}' .runtime/runtime_state/broker_readonly/2026-07-10/tachibana_snapshot.json

echo
echo "========== RUNTIME CURRENT =========="
jq '.positions[] | {
  symbol,
  quantity,
  average_price
}' .runtime/persistent_ledger/state.json

echo
echo "========== MOCK REFERENCES =========="
grep -R -n 'source="mock"\|source: str = "mock"\|mock_used\|data_origin' \
src/ai_fund_lab_v2 \
2>/dev/null

echo
echo "========== BROKER READONLY =========="
grep -R -n 'broker_readonly_refresh\|RuntimeV2ReadonlyAdapter' \
src/ai_fund_lab_v2 \
2>/dev/null

