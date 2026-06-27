# Phase10-D8 Tachibana Login Ack Virtual URL Field Mapping Fix

作成日: 2026-06-27

## 1. Summary

Phase10-D8 では、Phase10-D7 で残った `decrypted plaintext に http/https URL 候補が存在しない` 問題を、login ack virtual URL field mapping / v4r9 numeric key mapping に絞って確認した。

今回の対象は login ack のフィールド対応確認と非秘密診断のみ。

account / positions / orders / executions / quotes は取得していない。発注、訂正、取消、第二暗証番号、`unlock_trade` 相当処理も実装・実行していない。

## 2. Official Mapping Check

公式サンプル HTML:

```text
https://www.e-shiten.jp/e_api/mfds_json_api_sample.html
```

公式 v4r9 圧縮辞書:

```text
https://www.e-shiten.jp/e_api/mfds_json_api_compress_v4r9.js
```

公式サンプルでは login ack 成功後、以下を `decrypt_url` に渡している。

```text
sUrlRequest
sUrlMaster
sUrlPrice
sUrlEvent
sUrlEventWebSocket
```

公式 v4r9 辞書の numeric key mapping:

```text
sUrlEvent=869
sUrlEventWebSocket=870
sUrlMaster=871
sUrlPrice=872
sUrlRequest=873
```

この範囲では、既存の `tachibana_codec.py` mapping は公式辞書と一致していた。

## 3. Implemented

追加・修正:

- login ack 用の v4r9 mapping subset を明示定義。
- request / response mapping の混同を避けるため、`TACHIBANA_V4R9_LOGIN_ACK_COLUMNS` を追加。
- virtual URL 候補フィールド診断を追加。
- 診断は値を保存せず、field present / ciphertext length / base64 classification / decrypt attempted / decrypt success / plaintext contains http(s) / validation passed のみを記録する。
- 共通 sanitizer で `sUrl*` key が過剰 redaction されないよう、候補診断を list 形式に修正。

保存しないもの:

- raw response
- raw login ack
- raw virtual URL value
- ciphertext value
- decrypted URL
- decrypted plaintext
- auth id value
- private key content

## 4. Default Smoke

明示フラグなしの default smoke を確認した。

結果:

```text
status=SKIPPED
executed=false
```

保存先:

```text
reports/phase_reports/phase10d8_tachibana_demo_login_default_result.json
```

## 5. Explicit Live Smoke

明示フラグ付き demo login/logout smoke を 1 回だけ実行した。

結果:

```text
status=FAILED_CONFIGURATION
executed=true
environment=demo
failure_classification=decrypted_url_validation_error
```

保存先:

```text
reports/phase_reports/phase10d8_tachibana_demo_login_smoke_result.json
```

sanitized diagnosis:

- login ack は正常。
- v4r9 codec は正常。
- 公式 virtual URL key mapping は一致。
- RSA-OAEP 復号 backend は D7 同様に `openssl_cli` fallback で成功。
- `sUrlRequest` 復号後 plaintext は引き続き URL 候補なし。
- session は未確定。
- logout は未実行。

注意:

D8 live 実行時点の `virtual_url_candidates` は、共通 sanitizer が `sUrl*` key を機密扱いしたため、レポート上では `[REDACTED]` になった。live は 1 回だけという制約を守るため再実行していない。実行後、同じ問題が再発しないよう candidate 診断を list 形式に修正し、mock test で固定した。

## 6. Diagnosis Conclusion

D8 で以下を確認した。

```text
CLMAuthLoginAck virtual URL numeric mapping は公式 v4r9 辞書と一致している
```

したがって、今回の失敗原因は login ack virtual URL numeric key mapping ではない可能性が高い。

次フェーズでは、以下のどちらかに絞る。

```text
Phase10-D9: auth ID と private key の組み合わせ、または demo 認証設定の整合性診断
```

または:

```text
Phase10-D9: 公式 JS と Python 復号後 plaintext の非値分類差分診断
```

Phase10-E account read-only live smoke にはまだ進まない。

## 7. Verification

対象テスト:

```text
PYTHONPATH=src python3 -m pytest tests/broker/test_tachibana_phase10c_session_foundation.py tests/broker/test_tachibana_client_mock.py -q
```

結果:

```text
47 passed
```

JSON validation:

- `reports/phase_reports/phase10d8_tachibana_login_ack_virtual_url_mapping_fix.json`
- `reports/phase_reports/phase10d8_tachibana_demo_login_smoke_result.json`

secret canary:

```text
PASS
```

no forbidden CLMID audit:

```text
PASS
```
