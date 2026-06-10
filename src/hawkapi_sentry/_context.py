"""Request context helpers for Sentry event enrichment."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

_REDACT_HEADER_NAMES = frozenset(
    [
        "authorization",
        "cookie",
        "x-api-key",
        "x-auth-token",
        "proxy-authorization",
    ]
)

_SENSITIVE_QUERY_PARAMS: frozenset[str] = frozenset(
    {
        "token",
        "key",
        "api_key",
        "password",
        "secret",
        "access_token",
        "refresh_token",
    }
)

_FILTERED = "[Filtered]"
_REDACTED_VALUE = "***"


def redact_headers(headers: Any) -> dict[str, str]:
    """Return a dict of headers with sensitive values masked.

    Accepts any iterable of (key, value) pairs or an object with an .items()
    method — covers both HawkAPI Headers (__iter__ yields tuples) and plain dicts.
    """
    result: dict[str, str] = {}
    items: Any = headers.items() if hasattr(headers, "items") else headers
    for key, value in items:
        if key.lower() in _REDACT_HEADER_NAMES:
            result[key] = _FILTERED
        else:
            result[key] = value
    return result


def redact_query_string(qs: str, sensitive: frozenset[str] | None = None) -> str:
    """Return *qs* with values for sensitive keys replaced by ``***``.

    The ``***`` sentinel is emitted verbatim — `urlencode` would otherwise
    percent-encode the asterisks and obscure the intent of the redaction
    in Sentry's UI.
    """
    if not qs:
        return qs
    targets = sensitive if sensitive is not None else _SENSITIVE_QUERY_PARAMS
    targets = frozenset(t.lower() for t in targets)
    pairs = parse_qsl(qs, keep_blank_values=True)
    parts: list[str] = []
    for k, v in pairs:
        key = urlencode([(k, "")]).rstrip("=")
        if k.lower() in targets:
            parts.append(f"{key}={_REDACTED_VALUE}")
        else:
            parts.append(f"{key}={quote(v, safe='')}")
    return "&".join(parts)


def status_class(status_code: int) -> str:
    """Map an HTTP status code to an OTel/Sentry transaction status string."""
    if status_code < 400:
        return "ok"
    if status_code < 500:
        return "invalid_argument"
    return "internal_error"


def request_context(
    request: Any,
    *,
    sensitive_query_params: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Build a Sentry request context dict from a HawkAPI Request.

    Sensitive values in the ``query_string`` field are masked with ``***`` so
    they never reach Sentry's UI (CWE-200).
    """
    url: str = request.url
    qs_raw: Any = request.query_string
    qs: str = qs_raw.decode("latin-1") if hasattr(qs_raw, "decode") else str(qs_raw)
    qs = redact_query_string(qs, sensitive_query_params)
    # The full URL carries its own query (e.g. ?token=...); redact it too so the
    # url field doesn't leak what query_string already masks (CWE-200).
    url_parts = urlsplit(url)
    if url_parts.query:
        url = urlunsplit(
            url_parts._replace(
                query=redact_query_string(url_parts.query, sensitive_query_params)
            )
        )
    return {
        "method": request.method,
        "url": url,
        "headers": redact_headers(request.headers),
        "query_string": qs,
    }


# Keep underscore aliases so tests that import _redact_headers etc. still work
_redact_headers = redact_headers
_status_class = status_class
_request_context = request_context
