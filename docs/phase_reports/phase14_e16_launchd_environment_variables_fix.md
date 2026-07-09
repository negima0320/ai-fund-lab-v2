# Phase14-E16 Runtime v2 launchd EnvironmentVariables Fix

作成日: 2026-07-08

## 最終判定

**PHASE14E16_LAUNCHD_ENV_FIX_COMPLETE**

## 目的

Phase14-E15で、`PYTHONPATH=src` なしでは `python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation` が `ModuleNotFoundError` になることを確認した。

E16では、Runtime v2の正式launchd plist 4件に `EnvironmentVariables` を追加し、launchd実行時にもRuntime v2正規CLIをimportできる状態にした。

今回、Submit、Broker API Write、Production注文、Notification実送信、launchd bootout/bootstrap/load/unloadは行っていない。

## 対象plist

- `tools/launchd/com.aifundlab.runtime_v2.morning.plist`
- `tools/launchd/com.aifundlab.runtime_v2.submit.plist`
- `tools/launchd/com.aifundlab.runtime_v2.execution.plist`
- `tools/launchd/com.aifundlab.runtime_v2.market_refresh.plist`

## 追加したEnvironmentVariables

4 plistすべてに以下を追加した。

```xml
<key>EnvironmentVariables</key>
<dict>
  <key>PYTHONPATH</key>
  <string>/Users/negishi/work/ai-fund-lab-v2/src</string>
  <key>TACHIBANA_API_ENV</key>
  <string>demo</string>
</dict>
```

## 確認結果

### plist構文

実行:

```text
plutil -lint tools/launchd/com.aifundlab.runtime_v2.morning.plist \
  tools/launchd/com.aifundlab.runtime_v2.submit.plist \
  tools/launchd/com.aifundlab.runtime_v2.execution.plist \
  tools/launchd/com.aifundlab.runtime_v2.market_refresh.plist
```

結果:

```text
tools/launchd/com.aifundlab.runtime_v2.morning.plist: OK
tools/launchd/com.aifundlab.runtime_v2.submit.plist: OK
tools/launchd/com.aifundlab.runtime_v2.execution.plist: OK
tools/launchd/com.aifundlab.runtime_v2.market_refresh.plist: OK
```

### EnvironmentVariables読戻し

4 plistすべてで以下を確認した。

- `PYTHONPATH=/Users/negishi/work/ai-fund-lab-v2/src`
- `TACHIBANA_API_ENV=demo`

### Python import確認

実行:

```text
env PYTHONPATH=/Users/negishi/work/ai-fund-lab-v2/src \
  TACHIBANA_API_ENV=demo \
  /usr/bin/python3 -c "import ai_fund_lab_v2.runtime_v2.cli.run_daily_operation as m; print(m.__name__)"
```

結果:

```text
ai_fund_lab_v2.runtime_v2.cli.run_daily_operation
```

これにより、launchdがplistの `EnvironmentVariables` を適用する状態であれば、E15で確認したimport errorは解消できる設計になった。

## launchctl反映手順

E16ではlaunchd登録変更を実行していない。

既に登録済みJobへplist変更を反映する場合は、以下の手順で行う。

```text
launchctl bootout gui/$(id -u) /Users/negishi/work/ai-fund-lab-v2/tools/launchd/com.aifundlab.runtime_v2.morning.plist
launchctl bootout gui/$(id -u) /Users/negishi/work/ai-fund-lab-v2/tools/launchd/com.aifundlab.runtime_v2.submit.plist
launchctl bootout gui/$(id -u) /Users/negishi/work/ai-fund-lab-v2/tools/launchd/com.aifundlab.runtime_v2.execution.plist
launchctl bootout gui/$(id -u) /Users/negishi/work/ai-fund-lab-v2/tools/launchd/com.aifundlab.runtime_v2.market_refresh.plist
```

```text
launchctl bootstrap gui/$(id -u) /Users/negishi/work/ai-fund-lab-v2/tools/launchd/com.aifundlab.runtime_v2.morning.plist
launchctl bootstrap gui/$(id -u) /Users/negishi/work/ai-fund-lab-v2/tools/launchd/com.aifundlab.runtime_v2.submit.plist
launchctl bootstrap gui/$(id -u) /Users/negishi/work/ai-fund-lab-v2/tools/launchd/com.aifundlab.runtime_v2.execution.plist
launchctl bootstrap gui/$(id -u) /Users/negishi/work/ai-fund-lab-v2/tools/launchd/com.aifundlab.runtime_v2.market_refresh.plist
```

反映後の確認:

```text
launchctl print gui/$(id -u)/com.aifundlab.runtime_v2.morning
launchctl print gui/$(id -u)/com.aifundlab.runtime_v2.submit
launchctl print gui/$(id -u)/com.aifundlab.runtime_v2.execution
launchctl print gui/$(id -u)/com.aifundlab.runtime_v2.market_refresh
```

`environment` または `EnvironmentVariables` 相当の出力に、以下が含まれることを確認する。

- `PYTHONPATH => /Users/negishi/work/ai-fund-lab-v2/src`
- `TACHIBANA_API_ENV => demo`

## Tests

実行:

```text
python3 -m pytest tests/runtime_v2
```

結果:

```text
314 passed
```

## Acceptance

| Criteria | Result |
| --- | --- |
| 4 plistすべてにPYTHONPATHあり | PASS |
| 4 plistすべてにTACHIBANA_API_ENV=demoあり | PASS |
| plist構文PASS | PASS |
| launchctl printで環境変数が確認できる状態にできる | PASS: 反映手順を明記 |
| python import errorが起きない設計 | PASS |
| tests/runtime_v2 PASS | PASS |
| Submitしていない | PASS |
| Broker API Writeしていない | PASS |
| Production注文していない | PASS |
| Notification実送信していない | PASS |
| launchd bootout/bootstrap/load/unloadしていない | PASS |
