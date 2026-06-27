# Phase10-D4 Tachibana v4r9 Codec Login Smoke

作成日: 2026-06-27

## 1. Summary

Phase10-D4 では、Phase10-D3 で原因を絞った v4r9 compression / uncompression layer mismatch に対して、公式サンプル互換の最小 codec 層を実装した。

今回の対象は demo login / session / logout smoke のための codec 実装のみ。

account / positions / orders / executions / quotes は取得していない。発注、訂正、取消、第二暗証番号、`unlock_trade` 相当処理も実装・実行していない。

## 2. Implemented

追加:

- `src/ai_fund_lab_v2/broker/tachibana_codec.py`
- v4r9 request key compression
- v4r9 response key uncompression
- login/logout に必要な公式 column id mapping
- transport codec hook
- codec mock tests

公式サンプルで確認した仕様:

```text
request:
  column name -> numeric id

response:
  numeric id -> column name

scalar values:
  request compress stage converts values to strings
```

raw response、compressed raw payload、raw login ack、virtual URL value は保存していない。

## 3. Default Smoke

明示フラグなしの default smoke を確認した。

結果:

```text
status=SKIPPED
executed=false
```

保存先:

```text
reports/phase_reports/phase10d4_tachibana_demo_login_default_result.json
```

## 4. Explicit Live Smoke

明示フラグ付き demo live smoke を 1 回だけ実行した。

結果:

```text
status=FAILED_CONFIGURATION
executed=true
environment=demo
failure_classification=virtual_url_decrypt_error
```

保存先:

```text
reports/phase_reports/phase10d4_tachibana_demo_login_smoke_result.json
```

sanitized diagnosis で確認できたこと:

- `sCLMID=CLMAuthLoginAck` を確認
- `sResultCode=0` を確認
- `sResultText=""` を確認
- virtual URL key の存在を確認
- raw virtual URL value は保存していない
- session は未確定
- logout は未実行

## 5. Diagnosis Conclusion

Phase10-D3 の原因であった v4r9 compression / uncompression layer mismatch は解消した。

次の失敗箇所は 1 つに絞れた。

```text
virtual_url_decrypt_error
```

つまり、login ack は正常 shape まで到達しているが、仮想 URL 復号で fail closed している。

Phase10-D5 の焦点:

```text
private key format / OpenSSL RSA-OAEP decrypt compatibility
```

候補:

- DER key が PKCS8 かどうか
- PEM key を使うべきか
- OpenSSL command の padding / hash / keyform 指定差分
- 公式 JS は WebCrypto `RSA-OAEP` / `SHA-256` / `pkcs8` を使う

## 6. Verification

対象テスト:

```text
python3 -m pytest tests/broker/test_tachibana_phase10c_session_foundation.py tests/broker/test_tachibana_client_mock.py tests/broker/test_mock_transport.py
```

結果:

```text
37 passed
```

JSON validation:

- `reports/phase_reports/phase10d4_tachibana_v4r9_codec_login_smoke.json`
- `reports/phase_reports/phase10d4_tachibana_demo_login_smoke_result.json`

secret canary:

```text
PASS
```

no forbidden CLMID audit:

```text
PASS
```

## 7. Phase10-D5 Handoff

Phase10-D5 は virtual URL decrypt error を 1 点に絞って修正する。

Phase10-D5 で扱う範囲:

- private key metadata の追加診断
- DER / PEM 切替の mock tests
- OpenSSL decrypt command compatibility
- 復号後 URL を保存しない内部検証
- demo login/logout smoke を 1 回だけ再実行

Phase10-E account read-only live smoke にはまだ進まない。
