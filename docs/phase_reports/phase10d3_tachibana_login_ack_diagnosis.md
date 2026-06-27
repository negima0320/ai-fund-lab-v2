# Phase10-D3 Tachibana Login Ack Result Error Diagnosis

作成日: 2026-06-27

## 1. Summary

Phase10-D3 では、Phase10-D2 の `login_ack_result_error` を、秘密情報・raw ack・virtual URL を保存せずに診断した。

今回の対象は demo login diagnosis のみ。

account / positions / orders / executions / quotes は取得していない。発注、訂正、取消、第二暗証番号、`unlock_trade` 相当処理も実装・実行していない。

## 2. Implemented Diagnosis

追加した診断:

- login ack sanitized classifier
- request shape sanitizer
- private key file metadata classifier
- result code normalization
- result text classification
- virtual URL key presence check

保存しないもの:

- raw response
- raw login ack
- virtual URL value
- decrypted URL
- auth id value
- private key content

## 3. Official Check

公開仕様で確認した成功条件:

```text
sCLMID=CLMAuthLoginAck
sResultCode=0
sResultText=""
```

既存実装は `sResultCode` の型差、空文字、ゼロ埋め、全角ゼロを許容するようにした。

公開サンプルの v4r9 request layer は、送信前に request parameter を compress し、応答後に uncompress している。

## 4. Default Smoke

明示フラグなしの default smoke を確認した。

結果:

```text
status=SKIPPED
executed=false
```

保存先:

```text
reports/phase_reports/phase10d3_tachibana_login_diagnosis_default_result.json
```

default smoke では実 API 接続は行われていない。

## 5. Explicit Diagnosis

明示フラグ付き demo login diagnosis を 1 回だけ実行した。

結果:

```text
status=FAILED_CONFIGURATION
executed=true
environment=demo
failure_classification=response_compression_or_unexpand_error
failure_stage=login_ack_unexpanded_compressed_shape
```

保存先:

```text
reports/phase_reports/phase10d3_tachibana_login_diagnosis_result.json
```

sanitized diagnosis で確認できたこと:

- auth endpoint は demo の `/e_api_v4r9/auth/`
- method は POST
- `sCLMID=CLMAuthLoginRequest`
- `p_no` あり
- `p_sd_date` あり
- credential は存在
- private key file は存在
- private key format は `der`
- login ack として期待する `sCLMID` は確認できない
- `sResultCode` は確認できない
- virtual URL key は確認できない
- response object の key 名が数値だけの shape

## 6. Diagnosis Conclusion

原因候補は 1 つに絞った。

```text
v4r9 compression / uncompression layer mismatch
```

理由:

- Phase10-D の `response_decode_error` は cp932 / shift_jis fallback で解消。
- Phase10-D2 の login ack result error は、D3 診断では `sCLMID` / `sResultCode` の通常 login ack shape ではなく、数値 key のみの応答 shape と判明。
- 公開 v4r9 サンプルは request を compress し、response を uncompress する。
- 現行 transport は JSON POST のみで、v4r9 compress / uncompress を実装していない。

残る補助候補:

```text
request compression missing
response uncompression missing
```

これは同一原因の送信側 / 受信側の実装面であり、Phase10-D4 で公式サンプル互換の圧縮層を設計する。

## 7. Verification

対象テスト:

```text
python3 -m pytest tests/broker/test_tachibana_phase10c_session_foundation.py tests/broker/test_tachibana_client_mock.py tests/broker/test_mock_transport.py
```

結果:

```text
31 passed
```

JSON validation:

- `reports/phase_reports/phase10d3_tachibana_login_ack_diagnosis.json`
- `reports/phase_reports/phase10d3_tachibana_login_diagnosis_result.json`

secret canary:

```text
PASS
```

no forbidden CLMID audit:

```text
PASS
```

## 8. Phase10-D4 Handoff

Phase10-D4 は、公式サンプル互換の v4r9 compress / uncompress layer を設計・実装する。

Phase10-D4 で扱う範囲:

- compress / uncompress の仕様確認
- mock fixture に数値 key response を追加
- raw response を保存しない変換層
- login ack normalizer 前に uncompress を通す transport
- demo login/logout smoke を 1 回だけ再実行

Phase10-E account read-only live smoke にはまだ進まない。
