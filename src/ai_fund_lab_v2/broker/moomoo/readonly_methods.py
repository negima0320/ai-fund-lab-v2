from __future__ import annotations

MOOMOO_READ_ONLY_METHODS: frozenset[str] = frozenset(
    {
        "get_acc_list",
        "accinfo_query",
        "position_list_query",
        "order_list_query",
        "history_order_list_query",
    }
)


def is_moomoo_read_only_method(method_name: str | None) -> bool:
    return bool(method_name and method_name in MOOMOO_READ_ONLY_METHODS)

