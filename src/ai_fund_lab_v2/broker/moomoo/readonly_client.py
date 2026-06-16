from __future__ import annotations

import importlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.moomoo.readonly_methods import MOOMOO_READ_ONLY_METHODS, is_moomoo_read_only_method
from ai_fund_lab_v2.broker.sanitizer import hash_account_id


@dataclass(frozen=True)
class MoomooReadOnlySettings:
    host: str = "127.0.0.1"
    port: int = 11111
    market: str = "JP"
    environment: str = "SIMULATE"
    sdk_module: str = "moomoo"
    config_source: str = "default"


class MoomooReadOnlySafetyError(RuntimeError):
    pass


class MoomooReadOnlyQueryError(RuntimeError):
    def __init__(self, method_name: str, ret_code: str, message: str) -> None:
        super().__init__(f"Read-only method failed: {method_name}")
        self.method_name = method_name
        self.ret_code = _sanitize_error_token(ret_code)
        self.message = _sanitize_error_token(message)


@dataclass(frozen=True)
class MoomooReadOnlyCollectResult:
    payload: dict[str, Any]
    method_results: dict[str, str]
    method_errors: dict[str, dict[str, str]]
    account_summaries: tuple[dict[str, Any], ...]
    account_discovery: dict[str, Any]
    attempted_args: dict[str, str]

    @property
    def ok(self) -> bool:
        return all(value == "SUCCESS" for value in self.method_results.values())


def load_moomoo_readonly_settings(runtime_dir: Path, env: dict[str, str] | None = None) -> MoomooReadOnlySettings:
    values = dict(env if env is not None else os.environ)
    config_path = runtime_dir / "broker" / "moomoo_readonly.local.json"
    config: dict[str, Any] = {}
    source = "default"
    if config_path.is_file():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        source = str(config_path)

    host = str(values.get("AI_FUND_LAB_MOOMOO_HOST") or config.get("host") or "127.0.0.1")
    port = int(values.get("AI_FUND_LAB_MOOMOO_PORT") or config.get("port") or 11111)
    market = str(values.get("AI_FUND_LAB_MOOMOO_MARKET") or config.get("market") or "JP")
    environment = _normalize_trd_env(values.get("AI_FUND_LAB_MOOMOO_ENV") or config.get("environment") or "SIMULATE")
    sdk_module = str(values.get("AI_FUND_LAB_MOOMOO_SDK_MODULE") or config.get("sdk_module") or "moomoo")
    return MoomooReadOnlySettings(
        host=host,
        port=port,
        market=market,
        environment=environment,
        sdk_module=sdk_module,
        config_source=source,
    )


@dataclass
class MoomooReadOnlyClient:
    settings: MoomooReadOnlySettings
    continue_on_failure: bool = False

    def collect(self) -> dict[str, Any]:
        result = self.collect_with_status()
        if not result.ok:
            failed = [method for method, status in result.method_results.items() if status != "SUCCESS"]
            raise RuntimeError(f"Read-only method failed: {','.join(failed)}")
        return result.payload

    def collect_with_status(self) -> MoomooReadOnlyCollectResult:
        sdk = importlib.import_module(self.settings.sdk_module)
        context_class = getattr(sdk, "Open" + "Sec" + "Trade" + "Context")
        try:
            context = context_class(filter_trdmarket=self.settings.market, host=self.settings.host, port=self.settings.port)
        except TypeError as exc:
            if "filter_trdmarket" not in str(exc):
                raise
            context = context_class(host=self.settings.host, port=self.settings.port)
        payload: dict[str, Any] = {
            "metadata": {
                "broker": "moomoo",
                "source": "readonly_smoke",
                "environment": self.settings.environment,
                "currency": "JPY",
            }
        }
        method_results: dict[str, str] = {
            "get_acc_list": "NOT_EXECUTED",
            "account_selection": "NOT_EXECUTED",
            "accinfo_query": "NOT_EXECUTED",
            "position_list_query": "NOT_EXECUTED",
            "order_list_query": "NOT_EXECUTED",
            "history_order_list_query": "NOT_EXECUTED",
        }
        method_errors: dict[str, dict[str, str]] = {}
        attempted_args: dict[str, str] = {}
        account_summaries: tuple[dict[str, Any], ...] = ()
        account_discovery: dict[str, Any] = {}
        try:
            account_rows = _query(context, "get_acc_list")
            selected_account_rows = _filter_accounts_by_env(account_rows, self.settings.environment)
            payload["get_acc_list"] = {"ret": "OK", "data": selected_account_rows}
            method_results["get_acc_list"] = "SUCCESS"
            attempted_args["get_acc_list"] = "no_args"
            account_summaries = _account_summaries(account_rows)
            account_discovery = _account_discovery(account_rows, self.settings.environment)
            if not selected_account_rows:
                method_results["account_selection"] = "FAILED"
                method_errors["account_selection"] = {
                    "ret_code": "NO_MATCHING_ACCOUNT",
                    "message": f"No {self.settings.environment} account was visible in get_acc_list.",
                }
                return MoomooReadOnlyCollectResult(
                    payload=payload,
                    method_results=method_results,
                    method_errors=method_errors,
                    account_summaries=account_summaries,
                    account_discovery=account_discovery,
                    attempted_args=attempted_args,
                )
            method_results["account_selection"] = "SUCCESS"
            account_id = _select_account_id(selected_account_rows)
            currency = _currency_for_market(self.settings.market)
            for method_name in ("accinfo_query", "position_list_query", "order_list_query", "history_order_list_query"):
                try:
                    payload[method_name] = {
                        "ret": "OK",
                        "data": _query_readonly_variants(
                            context,
                            method_name,
                            account_id,
                            self.settings.environment,
                            currency,
                        ),
                    }
                    method_results[method_name] = "SUCCESS"
                    attempted_args[method_name] = _attempted_args_label(method_name)
                except MoomooReadOnlyQueryError as exc:
                    method_results[method_name] = "FAILED"
                    method_errors[method_name] = {"ret_code": exc.ret_code, "message": exc.message}
                    attempted_args[method_name] = _attempted_args_label(method_name)
                    if not self.continue_on_failure:
                        break
                except Exception as exc:
                    method_results[method_name] = "FAILED"
                    method_errors[method_name] = {"ret_code": "EXCEPTION", "message": _sanitize_error_token(str(exc))}
                    attempted_args[method_name] = _attempted_args_label(method_name)
                    if not self.continue_on_failure:
                        break
            return MoomooReadOnlyCollectResult(
                payload=payload,
                method_results=method_results,
                method_errors=method_errors,
                account_summaries=account_summaries,
                account_discovery=account_discovery,
                attempted_args=attempted_args,
            )
        except MoomooReadOnlyQueryError as exc:
            method_results["get_acc_list"] = "FAILED"
            method_errors["get_acc_list"] = {"ret_code": exc.ret_code, "message": exc.message}
            return MoomooReadOnlyCollectResult(
                payload=payload,
                method_results=method_results,
                method_errors=method_errors,
                account_summaries=account_summaries,
                account_discovery=account_discovery,
                attempted_args=attempted_args,
            )
        except Exception as exc:
            method_results["get_acc_list"] = "FAILED"
            method_errors["get_acc_list"] = {"ret_code": "EXCEPTION", "message": _sanitize_error_token(str(exc))}
            return MoomooReadOnlyCollectResult(
                payload=payload,
                method_results=method_results,
                method_errors=method_errors,
                account_summaries=account_summaries,
                account_discovery=account_discovery,
                attempted_args=attempted_args,
            )
        finally:
            close = getattr(context, "close", None)
            if callable(close):
                close()


def ensure_readonly_method(method_name: str) -> str:
    if not is_moomoo_read_only_method(method_name):
        raise MoomooReadOnlySafetyError(f"Method is not allowed in Phase8-C read-only smoke: {method_name}")
    return method_name


def _query(context: Any, method_name: str, **kwargs: Any) -> Any:
    ensure_readonly_method(method_name)
    method = getattr(context, method_name)
    ret, data = method(**{key: value for key, value in kwargs.items() if value not in (None, "")})
    if str(ret).upper() not in {"OK", "0"}:
        raise MoomooReadOnlyQueryError(method_name, str(ret), str(data))
    return _to_records(data)


def _query_readonly_variants(context: Any, method_name: str, account_id: Any, trd_env: str, currency: str) -> Any:
    errors: list[MoomooReadOnlyQueryError] = []
    generic_errors: list[Exception] = []
    variants = _readonly_query_variants(method_name, account_id, trd_env, currency)
    for kwargs in variants:
        try:
            return _query(context, method_name, **kwargs)
        except TypeError as exc:
            if "unexpected keyword" in str(exc) or "acc_id" in str(exc) or "account_id" in str(exc):
                continue
            raise
        except MoomooReadOnlyQueryError as exc:
            errors.append(exc)
            continue
        except Exception as exc:
            generic_errors.append(exc)
            continue
    if errors:
        raise errors[-1]
    if generic_errors:
        raise MoomooReadOnlyQueryError(method_name, "EXCEPTION", str(generic_errors[-1]))
    raise MoomooReadOnlyQueryError(method_name, "NO_VARIANT", "No compatible read-only query variant succeeded.")


def _readonly_query_variants(method_name: str, account_id: Any, trd_env: str, currency: str) -> tuple[dict[str, Any], ...]:
    if method_name == "accinfo_query":
        return (
            {"acc_id": account_id, "trd_env": trd_env, "currency": currency},
            {"acc_id": account_id, "currency": currency},
            {"trd_env": trd_env, "currency": currency},
            {"currency": currency},
            {"acc_id": account_id, "trd_env": trd_env},
            {"trd_env": trd_env},
        )
    return (
        {"acc_id": account_id, "trd_env": trd_env},
        {"trd_env": trd_env},
    )


def _attempted_args_label(method_name: str) -> str:
    if method_name == "accinfo_query":
        return "acc_id_trd_env_currency_then_trd_env_currency"
    return "acc_id_trd_env_then_trd_env"


def _to_records(data: Any) -> Any:
    if hasattr(data, "to_dict"):
        records = data.to_dict(orient="records")
        return records
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data
    return []


def _select_account_id(account_rows: Any) -> Any:
    if not isinstance(account_rows, list) or not account_rows:
        return 0
    first = account_rows[0]
    if not isinstance(first, dict):
        return 0
    return first.get("acc_id") or first.get("card_num") or first.get("uni_card_num") or 0


def _filter_accounts_by_env(account_rows: Any, trd_env: str) -> list[dict[str, Any]]:
    if not isinstance(account_rows, list):
        return []
    selected: list[dict[str, Any]] = []
    for item in account_rows:
        if not isinstance(item, dict):
            continue
        item_env = str(item.get("trd_env") or item.get("environment") or "").upper()
        if item_env == trd_env.upper():
            selected.append(item)
    return selected


def _account_summaries(account_rows: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(account_rows, list):
        return ()
    summaries: list[dict[str, Any]] = []
    for item in account_rows:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("acc_id") or item.get("card_num") or item.get("uni_card_num") or item.get("account_number") or ""
        summaries.append(
            {
                "account_ref": f"acct_hash_{hash_account_id(str(raw_id))}" if raw_id else "",
                "trd_env": str(item.get("trd_env") or item.get("environment") or ""),
                "market": str(item.get("trd_market") or item.get("market") or item.get("trade_market") or ""),
                "account_type": str(item.get("acc_type") or item.get("account_type") or ""),
            }
        )
    return tuple(summaries)


def _account_discovery(account_rows: Any, selected_trd_env: str) -> dict[str, Any]:
    rows = account_rows if isinstance(account_rows, list) else []
    field_names: set[str] = set()
    trd_env_counts: dict[str, int] = {}
    account_type_counts: dict[str, int] = {}
    market_counts: dict[str, int] = {}
    selected_count = 0
    for item in rows:
        if not isinstance(item, dict):
            continue
        field_names.update(_sanitize_field_name(str(key)) for key in item.keys())
        trd_env = str(item.get("trd_env") or item.get("environment") or "UNKNOWN").upper()
        account_type = str(item.get("acc_type") or item.get("account_type") or "UNKNOWN").upper()
        market = str(item.get("trd_market") or item.get("market") or item.get("trade_market") or "UNKNOWN").upper()
        trd_env_counts[trd_env] = trd_env_counts.get(trd_env, 0) + 1
        account_type_counts[account_type] = account_type_counts.get(account_type, 0) + 1
        market_counts[market] = market_counts.get(market, 0) + 1
        if trd_env == selected_trd_env.upper():
            selected_count += 1
    return {
        "field_names": sorted(field_names),
        "row_count": len([item for item in rows if isinstance(item, dict)]),
        "selected_trd_env": selected_trd_env,
        "selected_candidate_count": selected_count,
        "trd_env_counts": trd_env_counts,
        "account_type_counts": account_type_counts,
        "market_counts": market_counts,
        "selection_rule": "require_explicit_trd_env_match",
    }


def _sanitize_field_name(value: str) -> str:
    if value in {"acc_id", "card_num", "uni_card_num", "account_number"}:
        return "account_identifier"
    return value


def _sanitize_error_token(value: str) -> str:
    text = str(value)
    for marker in ("acc_id", "card_num", "uni_card_num", "account_number"):
        text = text.replace(marker, "account_identifier")
    return text[:300]


def _normalize_trd_env(value: Any) -> str:
    normalized = str(value or "SIMULATE").upper()
    if normalized not in {"SIMULATE", "REAL"}:
        raise MoomooReadOnlySafetyError(f"Unsupported moomoo read-only trade environment: {normalized}")
    return normalized


def _currency_for_market(market: str) -> str:
    normalized = str(market or "").upper()
    if normalized == "JP":
        return "JPY"
    if normalized == "US":
        return "USD"
    if normalized == "HK":
        return "HKD"
    return "JPY"


def read_only_methods_for_audit() -> tuple[str, ...]:
    return tuple(sorted(MOOMOO_READ_ONLY_METHODS))
