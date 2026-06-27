# Phase10-D9 Tachibana Login Ack URL Candidate Diagnosis

作成日: 2026-06-27

## 1. Summary

Phase10-D9 では、Phase10-D8 で公式 numeric mapping が正しいことを確認した後、`CLMAuthLoginAck` 内の5つの `sUrl*` 候補を個別に非値分類した。

今回の対象は login ack / virtual URL 候補診断のみ。

account / positions / orders / executions / quotes は取得していない。発注、訂正、取消、第二暗証番号、`unlock_trade` 相当処理も実装・実行していない。

## 2. Implemented

追加・修正:

- `sKinsyouhouMidokuFlg=519` を通常 v4r9 response mapping に追加。
- `classify_login_ack` に `sKinsyouhouMidokuFlg` の非秘密分類を追加。
- `normalize_login_ack` に `sKinsyouhouMidokuFlg != "0"` の fail closed guard を追加。
- 5つの `sUrl*` 候補について、値を保存せず個別診断を追加。

候補ごとに保存する情報:

- field present
- ciphertext length
- base64 classification
- decoded byte length
- decrypt attempted
- decrypt success
- plaintext length
- plaintext contains http / https
- starts with http / https
- control char present
- null byte present
- validation passed
- failure classification

保存しないもの:

- raw response
- raw login ack
- raw virtual URL
- ciphertext value
- decrypted plaintext
- decrypted URL
- auth id value
- private key content

## 3. Official Difference Recheck

公式 sample の確認済み事項:

- `sKinsyouhouMidokuFlg == "0"` の後に URL 復号へ進む。
- `sUrlRequest / sUrlMaster / sUrlPrice / sUrlEvent / sUrlEventWebSocket` の5つ全てを同じ `decrypt_url` 関数へ渡している。
- `decrypt_url` は private key 文字列の whitespace を除去し、base64 decode 後に WebCrypto `importKey("pkcs8")` を行う。
- ciphertext も base64 decode し、RSA-OAEP / SHA-256 / labelなしで復号する。
- 復号後は `TextDecoder().decode(p_buf)` を返す。

## 4. Default Smoke

明示フラグなしの default smoke を確認した。

結果:

```text
status=SKIPPED
executed=false
```

保存先:

```text
reports/phase_reports/phase10d9_tachibana_demo_login_default_result.json
```

## 5. Explicit Live Diagnosis

明示フラグ付き demo login diagnosis を 1 回だけ実行した。

結果:

```text
status=FAILED_CONFIGURATION
executed=true
environment=demo
failure_classification=decrypted_url_validation_error
```

保存先:

```text
reports/phase_reports/phase10d9_tachibana_demo_login_diagnosis_result.json
```

## 6. Findings

`sKinsyouhouMidokuFlg`:

```text
present=true
value=0
is_zero=true
```

5つの virtual URL 候補:

```text
sUrlRequest:
  decrypt_success=true
  starts_with_https=true
  validation_passed=true

sUrlMaster:
  decrypt_success=true
  starts_with_https=true
  validation_passed=true

sUrlPrice:
  decrypt_success=true
  starts_with_https=true
  validation_passed=true

sUrlEvent:
  decrypt_success=true
  starts_with_https=true
  validation_passed=true

sUrlEventWebSocket:
  decrypt_success=true
  starts_with_https=false
  contains_https=false
  validation_passed=false
  failure_classification=no_url_candidate
```

## 7. Diagnosis Conclusion

D9 で原因は以下に絞れた。

```text
sUrlEventWebSocket の復号 plaintext だけが、現在の HTTP(S) URL validation を通らない
```

`sUrlRequest / sUrlMaster / sUrlPrice / sUrlEvent` は復号・validation ともに成功しているため、auth ID / private key の組み合わせ全体が誤っている可能性は低くなった。

次に確認すべき点:

```text
Phase10-D10: sUrlEventWebSocket の公式期待形式を確認し、wss/ws など WebSocket URL としての非値分類と validation を追加する
```

Phase10-E account/balance read-only には、session 確定と logout cleanup 成功後に進む。

## 8. Verification

対象テスト:

```text
PYTHONPATH=src python3 -m pytest tests/broker/test_tachibana_phase10c_session_foundation.py tests/broker/test_tachibana_client_mock.py -q
```

結果:

```text
50 passed
```

JSON validation:

- `reports/phase_reports/phase10d9_tachibana_login_ack_url_candidate_diagnosis.json`
- `reports/phase_reports/phase10d9_tachibana_demo_login_diagnosis_result.json`

secret canary:

```text
PASS
```

no forbidden CLMID audit:

```text
PASS
```
