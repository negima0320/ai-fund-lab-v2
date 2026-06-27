# Phase10-D5 Tachibana Virtual URL Decrypt Compatibility Fix

作成日: 2026-06-27

## 1. Summary

Phase10-D5 では、Phase10-D4 で到達した `virtual_url_decrypt_error` に対して、private key format と RSA-OAEP / SHA-256 互換性を確認・修正した。

今回の対象は virtual URL 復号のみ。

account / positions / orders / executions / quotes は取得していない。発注、訂正、取消、第二暗証番号、`unlock_trade` 相当処理も実装・実行していない。

## 2. Implemented

修正:

- OpenSSL `pkeyutl` に `rsa_mgf1_md:sha256` を追加。
- encrypted URL 文字列の whitespace 除去と base64 padding 補正を追加。
- DER 指定時に同じ local config directory の PEM key へ安全に fallback する経路を追加。
- private key metadata classifier を強化。
- 復号 mock tests を追加。

保存しないもの:

- raw response
- compressed raw payload
- raw login ack
- raw virtual URL value
- decrypted URL
- auth id value
- private key content

## 3. Key Metadata Diagnosis

ローカル鍵ファイルは内容を表示せず、メタデータのみ確認した。

DER:

```text
extension=der
size_bytes=1645
openssl_no_pass_readable=false
appears_encrypted=true
```

PEM:

```text
extension=pem
size_bytes=1674
openssl_no_pass_readable=true
appears_encrypted=false
```

このため D5 実装では DER を先に試し、失敗時に PEM fallback を試すようにした。

## 4. Default Smoke

明示フラグなしの default smoke を確認した。

結果:

```text
status=SKIPPED
executed=false
```

保存先:

```text
reports/phase_reports/phase10d5_tachibana_demo_login_default_result.json
```

## 5. Explicit Live Smoke

明示フラグ付き demo login/logout smoke を 1 回だけ実行した。

結果:

```text
status=FAILED_CONFIGURATION
executed=true
environment=demo
failure_classification=virtual_url_decrypt_error
```

保存先:

```text
reports/phase_reports/phase10d5_tachibana_demo_login_smoke_result.json
```

sanitized diagnosis で確認できたこと:

- login ack は正常。
- `sCLMID=CLMAuthLoginAck`
- `sResultCode=0`
- `sResultText=""`
- virtual URL key は存在。
- virtual URL decrypt は試行済み。
- virtual URL decrypt は未成功。
- session は未確定。
- logout は未実行。

## 6. Diagnosis Conclusion

`virtual_url_decrypt_error` はまだ解消していない。

原因候補は 1 つに絞った。

```text
OpenSSL pkeyutl と公式 WebCrypto RSA-OAEP/SHA-256 復号手順の差分
```

D5 で除外・前進したもの:

- DER key は no-pass OpenSSL read できない。
- PEM key は no-pass OpenSSL read できる。
- OAEP hash は SHA-256 指定済み。
- MGF1 hash も SHA-256 指定済み。
- encrypted URL の base64 preprocessing は追加済み。

Phase10-D6 で確認する候補:

- OpenSSL `pkeyutl` ではなく `openssl rsautl` / `pkeyutl` option差分の再確認。
- OAEP label の有無。
- PEM key が公式JSで使う PKCS8 DER と同一materialか、公開鍵fingerprintで確認。
- WebCrypto相当のPython実装を標準ライブラリ以外で入れるべきかの判断。

## 7. Verification

対象テスト:

```text
python3 -m pytest tests/broker/test_tachibana_phase10c_session_foundation.py tests/broker/test_tachibana_client_mock.py tests/broker/test_mock_transport.py
```

結果:

```text
40 passed
```

JSON validation:

- `reports/phase_reports/phase10d5_tachibana_virtual_url_decrypt_fix.json`
- `reports/phase_reports/phase10d5_tachibana_demo_login_smoke_result.json`

secret canary:

```text
PASS
```

no forbidden CLMID audit:

```text
PASS
```

## 8. Phase10-D6 Handoff

Phase10-D6 は、公式JSとの差分を以下 1 点に絞る。

```text
OpenSSL pkeyutl based RSA-OAEP decrypt compatibility
```

Phase10-D6 でも Phase10-E account read-only live smoke にはまだ進まない。
