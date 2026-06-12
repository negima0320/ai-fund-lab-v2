from __future__ import annotations


class BrokerClientError(RuntimeError):
    """Base error for broker client skeleton operations."""


class BrokerResponseError(BrokerClientError):
    """Raised when a broker response envelope represents failure."""
