import json
from pathlib import Path

from ai_fund_lab_v2.broker import (
    BrokerRuntimePaths,
    BrokerSettings,
    BrokerSnapshotWriter,
    BrokerSyncRunner,
    MockBrokerTransport,
    TachibanaReadOnlyClient,
    build_default_mock_transport,
    build_mock_broker_sync_runner,
)
from ai_fund_lab_v2.runtime import RuntimePaths


def test_mock_broker_sync_runs_read_only_flow_and_writes_snapshots(tmp_path: Path) -> None:
    paths = BrokerRuntimePaths(RuntimePaths(runtime_dir=tmp_path / ".runtime"))
    runner = build_mock_broker_sync_runner(BrokerSnapshotWriter(paths))

    result = runner.run()

    assert result.status == "success"
    assert result.balance_snapshot_count == 1
    assert result.position_snapshot_count == 1
    assert result.order_snapshot_count == 1
    assert len(result.snapshot_paths) == 3
    assert len(result.manifest_paths) == 3
    for file_path in result.snapshot_paths + result.manifest_paths:
        assert Path(file_path).is_file()
        assert str(file_path).startswith(str(paths.broker_root))


def test_mock_broker_sync_calls_expected_read_only_clmids_in_order(tmp_path: Path) -> None:
    transport = build_default_mock_transport()
    client = TachibanaReadOnlyClient(BrokerSettings(auth_id="mock-auth-id"), transport)
    paths = BrokerRuntimePaths(RuntimePaths(runtime_dir=tmp_path / ".runtime"))
    runner = BrokerSyncRunner(client=client, writer=BrokerSnapshotWriter(paths))

    result = runner.run()

    assert result.status == "success"
    assert [request["sCLMID"] for request in transport.requests] == [
        "CLMZanKaiSummary",
        "CLMZanKaiKanougaku",
        "CLMGenbutuKabuList",
        "CLMShinyouTategyokuList",
        "CLMOrderList",
    ]
    assert "CLMAuthLoginRequest" not in [request["sCLMID"] for request in transport.requests]
    assert "CLMAuthLogoutRequest" not in [request["sCLMID"] for request in transport.requests]


def test_mock_broker_sync_snapshot_output_contains_no_secret_values(tmp_path: Path) -> None:
    transport = MockBrokerTransport()
    transport.register_response(
        "CLMZanKaiSummary",
        {
            "sCLMID": "CLMZanKaiSummary",
            "sResultCode": "0",
            "sGenkinZandaka": "100000",
            "sGenbutuKabuKaituke": "90000",
            "sSyukkinKanougaku": "80000",
            "sHyokaGakuGoukei": "120000",
            "sWarningText": "token=secret-token https://example.invalid/session account_id=123456",
        },
    )
    transport.register_response("CLMZanKaiKanougaku", {"sCLMID": "CLMZanKaiKanougaku", "sResultCode": "0", "sKanougaku": "90000"})
    transport.register_response("CLMGenbutuKabuList", {"sCLMID": "CLMGenbutuKabuList", "sResultCode": "0", "positions": []})
    transport.register_response("CLMShinyouTategyokuList", {"sCLMID": "CLMShinyouTategyokuList", "sResultCode": "0", "positions": []})
    transport.register_response("CLMOrderList", {"sCLMID": "CLMOrderList", "sResultCode": "0", "orders": []})
    client = TachibanaReadOnlyClient(BrokerSettings(auth_id="mock-auth-id"), transport)
    paths = BrokerRuntimePaths(RuntimePaths(runtime_dir=tmp_path / ".runtime"))
    runner = BrokerSyncRunner(client=client, writer=BrokerSnapshotWriter(paths))

    result = runner.run()

    combined = "".join(Path(path).read_text(encoding="utf-8") for path in result.snapshot_paths + result.manifest_paths)
    result_json = json.dumps(result.to_dict(), ensure_ascii=True)
    assert "secret-token" not in combined
    assert "secret-token" not in result_json
    assert "https://example.invalid/session" not in combined
    assert "123456" not in combined
    assert "[REDACTED]" in combined
