"""hawkapi-sentry — Sentry integration for HawkAPI."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from hawkapi_sentry._middleware import SentryMiddleware
from hawkapi_sentry._plugin import SentryPlugin

try:
    __version__ = version("hawkapi-sentry")
except PackageNotFoundError:  # pragma: no cover - running from a source tree without install
    __version__ = "0.0.0"

__all__ = [
    "SentryMiddleware",
    "SentryPlugin",
    "__version__",
]
