# Phase10-D8 Tachibana Official Reference Review

作成日: 2026-06-27

## 1. Scope

Phase10-D8 の実装前レビューとして、公式 API リファレンスと公式サンプルから `CLMAuthLoginAck` の virtual URL 関連仕様を確認した。

今回は調査レポートのみ作成した。実API接続、login/logout、account / positions / orders / quotes 取得、発注・取消系 API は実行していない。

## 2. Official Sources

確認対象:

- https://www.e-shiten.jp/e_api/mfds_json_api_refference.html
- https://www.e-shiten.jp/e_api/mfds_json_api_sample.html
- https://www.e-shiten.jp/e_api/mfds_json_api_com.js
- https://www.e-shiten.jp/e_api/mfds_json_api_request_post.js

補助的に、公式 sample HTML から参照される v4r9 圧縮辞書も確認した。

- https://www.e-shiten.jp/e_api/mfds_json_api_compress_v4r9.js

## 3. Official Login Flow

公式 `mfds_json_api_com.js` の login request は以下の項目を作成する。

```text
p_no
p_sd_date
sCLMID=CLMAuthLoginRequest
sAuthId
```

公式 `mfds_json_api_request_post.js` は v4r8 / v4r9 で request を compress し、response を uncompress してから caller に返す。

公式 sample HTML は login 応答後、以下の条件を満たす場合に virtual URL を復号している。

```text
sResultCode == "0"
sKinsyouhouMidokuFlg == "0"
```

復号対象フィールド:

```text
sUrlRequest
sUrlMaster
sUrlPrice
sUrlEvent
sUrlEventWebSocket
```

## 4. Official Decrypt Flow

公式 `mfds_json_api_com.js` の `decrypt_url` は以下の流れ。

```text
private key:
  whitespace removal
  base64 decode
  WebCrypto importKey("pkcs8", RSA-OAEP/SHA-256)

ciphertext:
  base64 decode

decrypt:
  RSA-OAEP / SHA-256
  labelなし

plaintext:
  TextDecoder().decode(p_buf)
```

公式サンプル上では、復号後 plaintext の trim、null 終端除去、host validation は確認できなかった。

## 5. Official Numeric Key Mapping

公式 `mfds_json_api_compress_v4r9.js` は `_pa_col` 配列の index + 1 を numeric key として使う。

確認した `CLMAuthLoginAck` 関連 mapping:

```text
CLMAuthLoginAck=2
CLMAuthLoginRequest=3
p_no=288
p_sd_date=290
sAuthId=317
sCLMID=333
sKinsyouhouMidokuFlg=519
sResultCode=688
sResultText=689
sUrlEvent=869
sUrlEventWebSocket=870
sUrlMaster=871
sUrlPrice=872
sUrlRequest=873
```

結論:

```text
sUrlRequest / sUrlMaster / sUrlPrice / sUrlEvent / sUrlEventWebSocket の numeric key mapping は、現在の tachibana_codec.py と一致している。
```

## 6. Current Code Diff Review

### tachibana_codec.py

一致:

- `sUrlEvent=869`
- `sUrlEventWebSocket=870`
- `sUrlMaster=871`
- `sUrlPrice=872`
- `sUrlRequest=873`
- request / response の compress / uncompress は公式と同じ key 置換モデル。

注意:

- 現在の mapping は必要 subset の手動定義であり、公式 `_pa_col` 全体ではない。
- unknown numeric key は key 名を保持する実装で、値の保存や表示はしていない。

### session.py

一致:

- `CLMAuthLoginAck` を期待する。
- `sResultCode` 成功後に5つの `sUrl*` を復号し、session URL として保持する。
- repr では URL を redaction する。

差分:

- 公式 sample は `sKinsyouhouMidokuFlg == "0"` を確認してから復号するが、現在の `normalize_login_ack` はこの field を必須チェックしていない。
- 公式 sample は復号後 plaintext をそのまま表示するが、現在の `session.py` は `https://`、ASCII、demo host を検証する。
- 現在の demo host guard は fail closed として妥当だが、公式挙動との差分ではある。

### crypto.py

一致:

- RSA-OAEP / SHA-256。
- MGF1 SHA-256。
- label なし。
- base64 ciphertext decode。
- DER / PEM key handling を診断可能。

差分:

- 公式 sample は private key 文字列から whitespace を除去して base64 decode し、pkcs8 として import する。
- 現在の Python 実装は local key file を読み、`cryptography` backend または OpenSSL CLI fallback で復号する。
- 現在の Python 実装は plaintext classification を行うが、値は保存しない。

## 7. Diagnosis Implication

Phase10-D7 の `decrypted plaintext に http/https URL 候補が存在しない` 問題について、公式 mapping 確認からは以下が言える。

```text
login ack virtual URL numeric key mapping の誤りが主因である可能性は低い。
```

次に確認すべき候補:

- `sKinsyouhouMidokuFlg` 未確認による契約文書未読・利用状態差分。
- auth ID と private key の組み合わせ整合性。
- 公式 JS の private key 入力形式と Python file loader の差分。
- Python/OpenSSL 復号結果の非値分類を、5つの `sUrl*` 全候補で比較する診断。

## 8. Security Notes

本レビューでは以下を実施していない。

- 実API接続
- login/logout
- account / positions / orders / quotes 取得
- 発注・取消系 API
- auth id 値表示
- private key 内容表示
- raw login ack 表示
- raw virtual URL 表示
- ciphertext 表示
- 復号後 plaintext 表示

## 9. Recommended Next Step

実装前の次アクションは、`sKinsyouhouMidokuFlg` を login ack normalizer / diagnosis に明示的に反映する設計確認。

その後、live retry を行う場合は、5つの `sUrl*` 候補を値なしで個別分類できる形にしてから、明示フラグ付きで1回だけ実行する。
