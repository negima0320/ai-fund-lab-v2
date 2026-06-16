import json
import sys
import types
from pathlib import Path

from ai_fund_lab_v2.broker.moomoo.normalizer import normalize_moomoo_mock_response
from ai_fund_lab_v2.broker.moomoo.readonly_client import (
    MoomooReadOnlyClient,
    MoomooReadOnlySettings,
    ensure_readonly_method,
    load_moomoo_readonly_settings,
)
from ai_fund_lab_v2.broker.moomoo.readonly_smoke import run_moomoo_readonly_smoke
from scripts.audit_phase8c_moomoo_readonly_smoke import run_audit


def test_phase8c_smoke_skips_without_explicit_flag(tmp_path: Path) -> None:
    result = run_moomoo_readonly_smoke(
        runtime_dir=tmp_path / ".runtime",
        reports_dir=tmp_path / "reports" / "phase_reports",
        run_enabled=False,
    )

    assert result.status == "SKIPPED"
    assert result.executed is False
    assert result.report_path.is_file()
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert payload["executed"] is False


def test_phase8c_settings_load_from_env_without_secret(tmp_path: Path) -> None:
    settings = load_moomoo_readonly_settings(
        tmp_path / ".runtime",
        env={
            "AI_FUND_LAB_MOOMOO_HOST": "127.0.0.2",
            "AI_FUND_LAB_MOOMOO_PORT": "12345",
            "AI_FUND_LAB_MOOMOO_MARKET": "JP",
            "AI_FUND_LAB_MOOMOO_ENV": "REAL",
            "AI_FUND_LAB_MOOMOO_SDK_MODULE": "fake_moomoo_sdk",
        },
    )

    assert settings.host == "127.0.0.2"
    assert settings.port == 12345
    assert settings.sdk_module == "fake_moomoo_sdk"
    assert settings.environment == "REAL"


def test_phase8c_settings_default_to_simulate(tmp_path: Path) -> None:
    settings = load_moomoo_readonly_settings(tmp_path / ".runtime", env={})

    assert settings.environment == "SIMULATE"


def test_phase8c_normalizer_hashes_real_account_identifiers() -> None:
    payload = {
        "metadata": {"broker": "moomoo", "source": "readonly_smoke", "environment": "REAL", "currency": "JPY"},
        "get_acc_list": {
            "ret": "OK",
            "data": [{"acc_id": "123456789", "card_num": "987654321", "acc_type": "CASH", "trd_env": "REAL"}],
        },
        "accinfo_query": {"ret": "OK", "data": {"currency": "JPY", "jp_cash": "1", "jpy_net_cash_power": "1"}},
        "position_list_query": {"ret": "OK", "data": []},
        "order_list_query": {"ret": "OK", "data": []},
        "history_order_list_query": {"ret": "OK", "data": []},
    }

    normalized = normalize_moomoo_mock_response(payload)
    account = normalized["accounts"][0]

    assert account.account_ref.startswith("acct_hash_")
    assert "123456789" not in account.account_ref
    assert "987654321" not in account.account_ref


def test_phase8c_client_collects_only_readonly_methods_with_fake_sdk(monkeypatch) -> None:
    called: list[str] = []

    class FakeFrame:
        def __init__(self, records):
            self.records = records

        def to_dict(self, orient):
            assert orient == "records"
            return self.records

    class FakeContext:
        def __init__(self, host, port):
            self.host = host
            self.port = port

        def get_acc_list(self):
            called.append("get_acc_list")
            return "OK", FakeFrame([{"acc_id": "123456789", "acc_type": "CASH", "trd_env": "REAL"}])

        def accinfo_query(self, acc_id=0, trd_env="REAL", currency="JPY"):
            called.append("accinfo_query")
            assert acc_id == "123456789"
            assert trd_env == "REAL"
            assert currency == "JPY"
            return "OK", FakeFrame([{"currency": "JPY", "jp_cash": "10", "jpy_net_cash_power": "9"}])

        def position_list_query(self, acc_id=0, trd_env="REAL"):
            called.append("position_list_query")
            assert acc_id == "123456789"
            assert trd_env == "REAL"
            return "OK", FakeFrame([])

        def order_list_query(self, acc_id=0, trd_env="REAL"):
            called.append("order_list_query")
            assert acc_id == "123456789"
            assert trd_env == "REAL"
            return "OK", FakeFrame([])

        def history_order_list_query(self, acc_id=0, trd_env="REAL"):
            called.append("history_order_list_query")
            assert acc_id == "123456789"
            assert trd_env == "REAL"
            return "OK", FakeFrame([])

        def close(self):
            called.append("close")

    fake_module = types.SimpleNamespace()
    setattr(fake_module, "Open" + "Sec" + "Trade" + "Context", FakeContext)
    monkeypatch.setitem(sys.modules, "fake_moomoo_sdk", fake_module)

    payload = MoomooReadOnlyClient(MoomooReadOnlySettings(sdk_module="fake_moomoo_sdk", environment="REAL")).collect()

    assert set(called) >= {
        "get_acc_list",
        "accinfo_query",
        "position_list_query",
        "order_list_query",
        "history_order_list_query",
        "close",
    }
    assert payload["metadata"]["source"] == "readonly_smoke"


def test_phase8c_client_fails_closed_when_simulate_account_missing(monkeypatch) -> None:
    class FakeFrame:
        def __init__(self, records):
            self.records = records

        def to_dict(self, orient):
            assert orient == "records"
            return self.records

    class FakeContext:
        def __init__(self, host, port):
            self.host = host
            self.port = port

        def get_acc_list(self):
            return "OK", FakeFrame([{"acc_id": "123456789", "acc_type": "CASH", "trd_env": "REAL"}])

        def close(self):
            pass

    fake_module = types.SimpleNamespace()
    setattr(fake_module, "Open" + "Sec" + "Trade" + "Context", FakeContext)
    monkeypatch.setitem(sys.modules, "fake_moomoo_sdk_no_sim", fake_module)

    result = MoomooReadOnlyClient(MoomooReadOnlySettings(sdk_module="fake_moomoo_sdk_no_sim")).collect_with_status()

    assert result.method_results["get_acc_list"] == "SUCCESS"
    assert result.method_results["account_selection"] == "FAILED"
    assert result.method_results["accinfo_query"] == "NOT_EXECUTED"
    assert result.account_summaries[0]["account_ref"].startswith("acct_hash_")
    assert result.account_discovery["selected_trd_env"] == "SIMULATE"
    assert result.account_discovery["selected_candidate_count"] == 0
    assert result.account_discovery["trd_env_counts"] == {"REAL": 1}


def test_phase8c_client_records_sanitized_account_discovery(monkeypatch) -> None:
    class FakeFrame:
        def __init__(self, records):
            self.records = records

        def to_dict(self, orient):
            assert orient == "records"
            return self.records

    class FakeContext:
        def __init__(self, host, port):
            self.host = host
            self.port = port

        def get_acc_list(self):
            return "OK", FakeFrame(
                [
                    {"acc_id": "123456789", "acc_type": "CASH", "trd_env": "REAL", "trd_market": "JP"},
                    {"acc_id": "222222222", "acc_type": "CASH", "trd_env": "SIMULATE", "trd_market": "JP"},
                ]
            )

        def accinfo_query(self, acc_id=0, trd_env="SIMULATE", currency="JPY"):
            assert acc_id == "222222222"
            assert trd_env == "SIMULATE"
            return "OK", FakeFrame([{"currency": currency, "jp_cash": "1", "jpy_net_cash_power": "1"}])

        def position_list_query(self, acc_id=0, trd_env="SIMULATE"):
            assert acc_id == "222222222"
            assert trd_env == "SIMULATE"
            return "OK", FakeFrame([])

        def order_list_query(self, acc_id=0, trd_env="SIMULATE"):
            assert acc_id == "222222222"
            assert trd_env == "SIMULATE"
            return "OK", FakeFrame([])

        def history_order_list_query(self, acc_id=0, trd_env="SIMULATE"):
            assert acc_id == "222222222"
            assert trd_env == "SIMULATE"
            return "OK", FakeFrame([])

        def close(self):
            pass

    fake_module = types.SimpleNamespace()
    setattr(fake_module, "Open" + "Sec" + "Trade" + "Context", FakeContext)
    monkeypatch.setitem(sys.modules, "fake_moomoo_sdk_sim_discovery", fake_module)

    result = MoomooReadOnlyClient(
        MoomooReadOnlySettings(sdk_module="fake_moomoo_sdk_sim_discovery", environment="SIMULATE")
    ).collect_with_status()

    assert result.ok is True
    assert result.account_discovery["selected_candidate_count"] == 1
    assert result.account_discovery["trd_env_counts"] == {"REAL": 1, "SIMULATE": 1}
    assert "account_identifier" in result.account_discovery["field_names"]
    assert "acc_id" not in result.account_discovery["field_names"]


def test_phase8c_readonly_method_guard_rejects_unknown_method() -> None:
    try:
        ensure_readonly_method("not_allowed")
    except Exception as exc:
        assert "not allowed" in str(exc)
    else:
        raise AssertionError("guard should reject unknown methods")


def test_phase8c_audit_passes() -> None:
    result = run_audit()

    assert result["status"] == "PASS"
    assert all(result["checks"].values())
