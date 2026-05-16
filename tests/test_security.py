"""Regression tests for 0.2.0 hardening fixes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from hawkapi_sentry._context import redact_query_string, request_context
from hawkapi_sentry._middleware import SentryMiddleware


class _FakeHeaders:
    def __init__(self, data: dict[str, str] | None = None) -> None:
        self._data = data or {}

    def get(self, key: str, default: str | None = None) -> str | None:
        return self._data.get(key, default)

    def items(self) -> list[tuple[str, str]]:
        return list(self._data.items())


class _FakeState:
    pass


class _FakeRequest:
    def __init__(self, headers: dict[str, str] | None = None) -> None:
        self.method = "POST"
        self.path = "/api/items"
        self.headers = _FakeHeaders(headers or {})
        self.state = _FakeState()
        self.scope = {}


@pytest.mark.asyncio
async def test_traceparent_continues_trace() -> None:
    """A request carrying ``sentry-trace`` must reach ``continue_trace``."""
    mock_tx = MagicMock()
    mock_tx.__enter__ = MagicMock(return_value=mock_tx)
    mock_tx.__exit__ = MagicMock(return_value=False)

    mw = SentryMiddleware(app=MagicMock())  # type: ignore[arg-type]
    parent = "0123456789abcdef0123456789abcdef-aabbccddeeff0011-1"
    req = _FakeRequest(headers={"sentry-trace": parent})

    with (
        patch("hawkapi_sentry._middleware.sentry_sdk.continue_trace") as m_cont,
        patch(
            "hawkapi_sentry._middleware.sentry_sdk.start_transaction",
            return_value=mock_tx,
        ),
        patch("sentry_sdk.add_breadcrumb"),
    ):
        m_cont.return_value = mock_tx
        await mw.before_request(req)  # type: ignore[arg-type]
        m_cont.assert_called_once()
        called_kwargs = m_cont.call_args.kwargs
        assert called_kwargs["environ_or_headers"] == {"sentry-trace": parent}


def test_query_param_redaction_in_request_context() -> None:
    """Sensitive query params must not reach Sentry's request context."""

    class R:
        method = "GET"
        url = "https://example.com/x?token=abc&page=2"
        query_string = b"token=abc&page=2&api_key=zzz"
        headers = _FakeHeaders({})

    ctx = request_context(R())
    assert "token=***" in ctx["query_string"]
    assert "api_key=***" in ctx["query_string"]
    assert "abc" not in ctx["query_string"]
    assert "page=2" in ctx["query_string"]


def test_redact_query_string_custom_set() -> None:
    """Callers can extend the redaction set."""
    out = redact_query_string("token=a&shared=b", frozenset({"shared"}))
    assert "shared=***" in out
    assert "token=a" in out
