"""Tests for _context helpers: _redact_headers, _status_class, _request_context."""

from __future__ import annotations

from hawkapi_sentry._context import _redact_headers, _request_context, _status_class

# ---------------------------------------------------------------------------
# _redact_headers
# ---------------------------------------------------------------------------


def test_redact_authorization() -> None:
    headers = {"Authorization": "Bearer secret", "Content-Type": "application/json"}
    result = _redact_headers(headers)
    assert result["Authorization"] == "[Filtered]"
    assert result["Content-Type"] == "application/json"


def test_redact_cookie() -> None:
    headers = {"cookie": "session=abc123", "accept": "text/html"}
    result = _redact_headers(headers)
    assert result["cookie"] == "[Filtered]"
    assert result["accept"] == "text/html"


def test_redact_x_api_key() -> None:
    headers = {"X-Api-Key": "my-key"}
    assert _redact_headers(headers)["X-Api-Key"] == "[Filtered]"


def test_redact_x_auth_token() -> None:
    headers = {"x-auth-token": "tok"}
    assert _redact_headers(headers)["x-auth-token"] == "[Filtered]"


def test_redact_proxy_authorization() -> None:
    headers = {"Proxy-Authorization": "Basic xyz"}
    assert _redact_headers(headers)["Proxy-Authorization"] == "[Filtered]"


def test_redact_case_insensitive() -> None:
    headers = {"AUTHORIZATION": "secret"}
    assert _redact_headers(headers)["AUTHORIZATION"] == "[Filtered]"


def test_no_sensitive_headers_unchanged() -> None:
    headers = {"host": "localhost", "content-length": "42"}
    result = _redact_headers(headers)
    assert result == headers


# ---------------------------------------------------------------------------
# _status_class
# ---------------------------------------------------------------------------


def test_status_class_2xx() -> None:
    assert _status_class(200) == "ok"
    assert _status_class(201) == "ok"
    assert _status_class(204) == "ok"


def test_status_class_4xx() -> None:
    assert _status_class(400) == "invalid_argument"
    assert _status_class(404) == "invalid_argument"
    assert _status_class(422) == "invalid_argument"


def test_status_class_5xx() -> None:
    assert _status_class(500) == "internal_error"
    assert _status_class(503) == "internal_error"


# ---------------------------------------------------------------------------
# _request_context
# ---------------------------------------------------------------------------


class _FakeHeaders:
    def __init__(self, data: dict[str, str]) -> None:
        self._data = data

    def items(self) -> list[tuple[str, str]]:
        return list(self._data.items())

    def get(self, key: str, default: str | None = None) -> str | None:
        return self._data.get(key, default)


class _FakeRequest:
    def __init__(self, method: str, url: str, headers: dict[str, str], qs: bytes = b"") -> None:
        self.method = method
        self.url = url
        self.headers = _FakeHeaders(headers)
        self.query_string = qs


def test_request_context_basic() -> None:
    req = _FakeRequest("GET", "http://localhost/items", {"host": "localhost"})
    ctx = _request_context(req)
    assert ctx["method"] == "GET"
    assert ctx["url"] == "http://localhost/items"
    assert ctx["query_string"] == ""


def test_request_context_redacts_auth() -> None:
    req = _FakeRequest(
        "POST",
        "http://localhost/login",
        {"authorization": "Bearer tok", "content-type": "application/json"},
    )
    ctx = _request_context(req)
    assert ctx["headers"]["authorization"] == "[Filtered]"
    assert ctx["headers"]["content-type"] == "application/json"


def test_request_context_query_string() -> None:
    req = _FakeRequest("GET", "http://localhost/search?q=hello", {}, b"q=hello")
    ctx = _request_context(req)
    assert ctx["query_string"] == "q=hello"


def test_request_context_redacts_url_query() -> None:
    """The url field must redact sensitive query params, not just query_string."""
    req = _FakeRequest(
        "GET",
        "http://localhost/cb?token=s3cret&q=hello",
        {},
        b"token=s3cret&q=hello",
    )
    ctx = _request_context(req)
    assert "s3cret" not in ctx["url"]
    assert ctx["url"] == "http://localhost/cb?token=***&q=hello"
    assert ctx["query_string"] == "token=***&q=hello"
