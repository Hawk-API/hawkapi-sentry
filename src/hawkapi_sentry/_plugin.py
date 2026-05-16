"""SentryPlugin — HawkAPI Plugin that initialises and drives the Sentry SDK."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import sentry_sdk
from hawkapi.plugins import Plugin

from hawkapi_sentry._context import request_context

logger = logging.getLogger("hawkapi_sentry")

_DEFAULT_IGNORE: tuple[int, ...] = (404, 401, 403)


class SentryPlugin(Plugin):
    """HawkAPI plugin that wires Sentry error and performance monitoring."""

    def __init__(
        self,
        *,
        dsn: str | None = None,
        environment: str = "production",
        release: str | None = None,
        traces_sample_rate: float = 0.0,
        profiles_sample_rate: float = 0.0,
        include_user_data: bool = False,
        user_getter: Callable[[Any], dict[str, Any]] | None = None,
        before_send: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any] | None]
        | None = None,
        tags: dict[str, str] | None = None,
        ignore_status_codes: tuple[int, ...] = _DEFAULT_IGNORE,
        transport: Any = None,
    ) -> None:
        self._dsn = dsn
        self._environment = environment
        self._release = release
        self._traces_sample_rate = traces_sample_rate
        self._profiles_sample_rate = profiles_sample_rate
        self._include_user_data = include_user_data
        self._user_getter = user_getter
        self._before_send = before_send
        self._tags: dict[str, str] = tags or {}
        self._ignore_status_codes = ignore_status_codes
        self._transport = transport
        self._initialised = False

    # ------------------------------------------------------------------
    # Plugin hooks
    # ------------------------------------------------------------------

    def on_startup(self) -> None:
        """Initialise the Sentry SDK. No-op when dsn is empty or None.

        ``send_default_pii`` is forced off by default so the SDK does not
        attach IP addresses, cookies, or other PII to every event. Pass
        ``before_send`` to opt back in selectively.
        """
        if not self._dsn:
            logger.info("hawkapi_sentry: no DSN provided — Sentry disabled (no-op mode)")
            return

        init_kwargs: dict[str, Any] = {
            "dsn": self._dsn,
            "environment": self._environment,
            "traces_sample_rate": self._traces_sample_rate,
            "profiles_sample_rate": self._profiles_sample_rate,
        }
        init_kwargs.setdefault("send_default_pii", False)
        if self._release is not None:
            init_kwargs["release"] = self._release
        if self._before_send is not None:
            init_kwargs["before_send"] = self._before_send
        if self._transport is not None:
            init_kwargs["transport"] = self._transport

        sentry_sdk.init(**init_kwargs)
        self._initialised = True

        logger.info(
            "hawkapi_sentry: Sentry initialised (environment=%s, traces_sample_rate=%s)",
            self._environment,
            self._traces_sample_rate,
        )

    def on_shutdown(self) -> None:
        """Flush pending Sentry events before the process exits."""
        sentry_sdk.flush(timeout=2.0)

    def on_exception(self, request: Any, exc: Exception) -> None:
        """Capture an unhandled exception in Sentry, enriched with request context."""
        status_code = getattr(exc, "status_code", 500)
        if status_code in self._ignore_status_codes:
            return

        with sentry_sdk.new_scope() as scope:
            scope.set_context("request", request_context(request))

            user_data = self._resolve_user(request)
            if user_data:
                scope.set_user(user_data)

            for tag_key, tag_val in self._tags.items():
                scope.set_tag(tag_key, tag_val)

            sentry_sdk.capture_exception(exc)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_user(self, request: Any) -> dict[str, Any] | None:
        """Return user dict from user_getter or request.state.user, or None."""
        if self._user_getter is not None:
            try:
                return self._user_getter(request)
            except Exception:
                logger.debug("hawkapi_sentry: user_getter raised — skipping user context")
                return None
        if self._include_user_data:
            state = getattr(request, "state", None)
            if state is not None:
                user = getattr(state, "user", None)
                if isinstance(user, dict):
                    return user  # type: ignore[return-value]
        return None
