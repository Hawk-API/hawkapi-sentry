"""SentryMiddleware — per-request Sentry transaction and breadcrumb."""

from __future__ import annotations

import contextlib
from typing import Any

import sentry_sdk
from hawkapi.middleware.base import Middleware
from hawkapi.requests.request import Request
from hawkapi.responses.json_response import JSONResponse
from hawkapi.responses.response import Response

from hawkapi_sentry._context import status_class


def _start_transaction(method: str, path: str, traceparent: str | None) -> Any:
    """Return a started Sentry transaction.

    If ``traceparent`` is provided we continue the upstream trace; otherwise
    we start a new root transaction. ``sentry_sdk.continue_trace`` is the
    modern v2 SDK API; older callers may not have it, in which case we fall
    back to ``Transaction.continue_from_headers``.
    """
    if traceparent:
        if hasattr(sentry_sdk, "continue_trace"):
            return sentry_sdk.continue_trace(
                environ_or_headers={"sentry-trace": traceparent},
                op="http.server",
                name=f"{method} {path}",
            )
        # Pre-2.x SDK fallback.
        from sentry_sdk.tracing import Transaction  # noqa: PLC0415

        return Transaction.continue_from_headers(
            {"sentry-trace": traceparent},
            op="http.server",
            name=f"{method} {path}",
        )
    return sentry_sdk.start_transaction(
        op="http.server",
        name=f"{method} {path}",
        source="url",
    )


class SentryMiddleware(Middleware):
    """Starts a Sentry performance transaction for every HTTP request."""

    async def before_request(self, request: Request) -> Request | Response | JSONResponse | None:
        """Start a Sentry transaction and add a breadcrumb."""
        method: str = request.method
        path: str = request.path

        traceparent = request.headers.get("sentry-trace") or request.headers.get("traceparent")
        transaction = _start_transaction(method, path, traceparent)
        if (
            traceparent
            and hasattr(sentry_sdk, "start_transaction")
            and not hasattr(transaction, "__enter__")
        ):
            # ``continue_trace`` returns a Transaction object that still needs
            # to be started via ``start_transaction`` in newer SDKs.
            transaction = sentry_sdk.start_transaction(transaction)

        request.state._sentry_tx = transaction  # type: ignore[attr-defined]
        transaction.__enter__()  # type: ignore[attr-defined]

        sentry_sdk.add_breadcrumb(
            category="request",
            message=f"{method} {path}",
            level="info",
        )

        return None

    async def after_response(
        self, request: Request, response: Response | JSONResponse
    ) -> Response | JSONResponse | None:
        """Finish the Sentry transaction with HTTP metadata."""
        tx: Any = getattr(getattr(request, "state", None), "_sentry_tx", None)
        if tx is None:
            return None

        status_code: int = response.status_code
        # Once routing has run we know the matched template (e.g.
        # ``/users/{id}``), which groups individual requests in Sentry's
        # transaction list.
        route_template = self._extract_route_template(request)
        if route_template:
            tx.name = f"{request.method} {route_template}"
            with contextlib.suppress(Exception):
                tx.source = "route"  # type: ignore[attr-defined]
        tx.set_tag("http.method", request.method)
        tx.set_tag("http.status_code", str(status_code))
        tx.set_tag("http.target", request.path)
        tx.set_status(status_class(status_code))
        tx.__exit__(None, None, None)  # type: ignore[attr-defined]

        return None

    @staticmethod
    def _extract_route_template(request: Request) -> str | None:
        # HawkAPI exposes the matched route on ``request.scope`` (``route``)
        # and/or ``request.scope["path_template"]`` depending on version.
        scope_obj: Any = getattr(request, "scope", None) or {}
        if not isinstance(scope_obj, dict):
            return None
        scope: dict[str, Any] = dict(scope_obj)  # type: ignore[arg-type]
        for key in ("route", "path_template", "endpoint_path"):
            value: Any = scope.get(key)
            if isinstance(value, str) and value:
                return value
            template: Any = getattr(value, "path", None) if value is not None else None
            if isinstance(template, str) and template:
                return template
        return None
