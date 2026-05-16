"""hawkapi-sentry — Sentry integration for HawkAPI."""

from __future__ import annotations

from hawkapi_sentry._middleware import SentryMiddleware
from hawkapi_sentry._plugin import SentryPlugin

__version__ = "0.2.0"

__all__ = [
    "SentryMiddleware",
    "SentryPlugin",
    "__version__",
]
