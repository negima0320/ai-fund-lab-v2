# Phase10-D6 Tachibana RSA-OAEP WebCrypto Compatibility Fix

作成日: 2026-06-27

## 1. Summary

Phase10-D6 では、Phase10-D5 で残った `virtual_url_decrypt_error` を、OpenSSL `pkeyutl` と公式 WebCrypto RSA-OAEP / SHA-256 の差分に絞って修正・診断した。

今回の対象は virtual URL 復号互換性のみ。

account / positions / orders / executions / quotes は取得していない。発注、訂正、取消、第二暗証番号、`unlock_trade` 相当処理も実装・実行していない。

## 2. Official Check

公式 JS の復号手順:

```text
private key:
  WebCrypto importKey("pkcs8", key, RSA-OAEP/SHA-256)

ciphertext:
  base64 decode to ArrayBuffer

decrypt:
  RSA-OAEP / SHA-256
  OAEP labelなし
```

## 3. Implemented

修正:

- `cryptography` backend 優先の構造を追加。
- `cryptography` 未導入時は OpenSSL CLI fallback。
- ciphertext sanitizer を強化。
- base64 standard / urlsafe 分類を追加。
- padding補正有無と decoded byte length の記録を追加。
- OpenSSL / cryptography の backend attempt 診断を追加。
- 復号後文字列の分類を追加。

保存しないもの:

- raw response
- compressed raw payload
- raw login ack
- raw virtual URL value
- ciphertext value
- decrypted URL
- auth id value
- private key content

## 4. Environment Finding

`cryptography` は現在の環境に未導入。

```text
cryptography_available=false
```

そのため D6 live smoke では OpenSSL CLI fallback が使われた。

## 5. Default Smoke

明示フラグなしの default smoke を確認した。

結果:

```text
status=SKIPPED
executed=false
```

保存先:

```text
reports/phase_reports/phase10d6_tachibana_demo_login_default_result.json
```

## 6. Explicit Live Smoke

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
reports/phase_reports/phase10d6_tachibana_demo_login_smoke_result.json
```

sanitized diagnosis で確認できたこと:

- login ack は正常。
- `sCLMID=CLMAuthLoginAck`
- `sResultCode=0`
- `sResultText=""`
- v4r9 codec は正常。
- virtual URL key は存在。
- ciphertext は standard base64。
- decoded ciphertext length は 256 bytes。
- DER primary decrypt は失敗。
- PEM fallback decrypt は OpenSSL CLI で成功。
- ただし session URL validation に失敗。
- session は未確定。
- logout は未実行。

## 7. Diagnosis Conclusion

D6 で `virtual_url_decrypt_error` はさらに狭まり、残りは以下になった。

```text
decrypted_url_validation_error
```

つまり、OpenSSL CLI + PEM fallback で復号処理自体は成功しているが、復号後文字列が `https://` virtual URL として validation を通っていない。

原因候補は 1 点:

```text
復号後文字列の形式が公式JSの期待するURL文字列と異なる
```

Phase10-D7 では、復号後文字列そのものを保存せず、以下の分類だけを live で確認する。

- length
- starts_with_https
- starts_with_http
- starts_with_error_marker
- empty
- control_char_present
- leading/trailing whitespace 有無

## 8. Verification

対象テスト:

```text
python3 -m pytest tests/broker/test_tachibana_phase10c_session_foundation.py tests/broker/test_tachibana_client_mock.py tests/broker/test_mock_transport.py
```

結果:

```text
42 passed
```

JSON validation:

- `reports/phase_reports/phase10d6_tachibana_rsa_oaep_webcrypto_fix.json`
- `reports/phase_reports/phase10d6_tachibana_demo_login_smoke_result.json`

secret canary:

```text
PASS
```

no forbidden CLMID audit:

```text
PASS
```

## 9. Phase10-D7 Handoff

Phase10-D7 は、復号後URL値を保存せずに plaintext classification を live で取り、URL validation failure の原因を 1 点に絞る。

Phase10-E account read-only live smoke にはまだ進まない。
