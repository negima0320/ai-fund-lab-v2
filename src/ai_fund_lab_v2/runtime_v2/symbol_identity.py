"""Symbol identity helpers for broker/exchange code variants."""

from __future__ import annotations


def symbol_aliases(symbol: str) -> set[str]:
    value = str(symbol or "").strip()
    if not value:
        return set()
    aliases = {value}
    if len(value) == 5 and value.endswith("0"):
        aliases.add(value[:4])
    if len(value) == 4 and value.isdigit():
        aliases.add(value + "0")
    return aliases


def same_symbol_identity(left: str, right: str) -> bool:
    return bool(symbol_aliases(left) & symbol_aliases(right))


def contains_symbol_identity(symbols: set[str] | frozenset[str], symbol: str) -> bool:
    aliases = symbol_aliases(symbol)
    return any(bool(symbol_aliases(existing) & aliases) for existing in symbols)
