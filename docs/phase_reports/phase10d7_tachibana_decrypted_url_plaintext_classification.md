# Phase10-D7 Tachibana Decrypted URL Plaintext Classification

作成日: 2026-06-27

## 1. Summary

Phase10-D7 では、Phase10-D6 で残った `decrypted_url_validation_error` を、復号後 plaintext の値を保存・表示せずに分類した。

今回の対象は復号後文字列の非秘密分類と URL validation の最小修正のみ。

account / positions / orders / executions / quotes は取得していない。発注、訂正、取消、第二暗証番号、`unlock_trade` 相当処理も実装・実行していない。

## 2. Official Check

公式 JS の virtual URL 復号は、WebCrypto `RSA-OAEP` / `SHA-256` で復号後、`TextDecoder().decode(p_buf)` で文字列化している。

公式 JS 上では、復号後文字列に対する trim、null 終端除去、URL validation の明示処理は確認できなかった。

## 3. Implemented

追加・修正:

- decrypted plaintext classifier を追加。
- 復号 bytes の utf-8 / cp932 / latin1 fallback 分類を追加。
- plaintext value を保存せず、長さ・URL候補有無・制御文字有無だけを記録。
- URL validation を安全に見直し。
- 前後空白 trim を許可。
- 端の null byte 除去を許可。
- 中間 null byte、制御文字、非ASCII、非HTTPS、非demo e-shiten host は fail closed。
- session repr の URL redaction を維持。

保存しないもの:

- raw response
- compressed raw payload
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
reports/phase_reports/phase10d7_tachibana_demo_login_default_result.json
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
reports/phase_reports/phase10d7_tachibana_demo_login_smoke_result.json
```

sanitized diagnosis:

- login ack は正常。
- v4r9 codec は正常。
- virtual URL key は存在。
- ciphertext は standard base64。
- decoded ciphertext length は 256 bytes。
- DER primary decrypt は失敗。
- PEM fallback decrypt は OpenSSL CLI で成功。
- `utf8_decode_success=true`
- `cp932_decode_success=true`
- `latin1_fallback_used=false`
- `plaintext_length=84`
- `stripped_length=83`
- `starts_with_https=false`
- `starts_with_http=false`
- `contains_https=false`
- `contains_http=false`
- `url_candidate_count=0`
- `url_validation_failure_reason=no_url_candidate`
- session は未確定。
- logout は未実行。

## 6. Diagnosis Conclusion

D7 で原因は 1 点に絞れた。

```text
復号後 plaintext に http:// または https:// の URL 候補が存在しない
```

trim、末尾空白、端の null byte、HTTPS validation の差分ではない。

次の Phase10-D8 では、復号対象となっている virtual URL フィールド、または v4r9 codec の URL フィールド key mapping が公式 JS と一致しているかを 1 点集中で確認する。

## 7. Verification

対象テスト:

```text
PYTHONPATH=src python3 -m pytest tests/broker/test_tachibana_phase10c_session_foundation.py tests/broker/test_tachibana_client_mock.py -q
```

結果:

```text
45 passed
```

JSON validation:

- `reports/phase_reports/phase10d7_tachibana_decrypted_url_plaintext_classification.json`
- `reports/phase_reports/phase10d7_tachibana_demo_login_smoke_result.json`

secret canary:

```text
PASS
```

no forbidden CLMID audit:

```text
PASS
```

## 8. Phase10-D8 Handoff

Phase10-D8 は、公式 JS の login ack URL フィールド対応と `tachibana_codec.py` の numeric key mapping を確認し、復号対象フィールドの差分に絞って修正する。

Phase10-E account read-only live smoke にはまだ進まない。
