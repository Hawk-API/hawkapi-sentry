# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-05-16

### Security

- Fix distributed-trace continuation to use the modern
  `sentry_sdk.continue_trace` API instead of the broken
  `transaction.continuing_trace` call.
- Mask sensitive query parameters (`token`, `key`, `api_key`, `password`,
  `secret`, `access_token`, `refresh_token`) in the Sentry request context
  (CWE-200). `request_context` now takes an optional
  `sensitive_query_params` argument.
- `send_default_pii` is explicitly defaulted to `False` in
  `sentry_sdk.init`.

### Changed

- After routing matches, the transaction is renamed to the route template
  (e.g. `GET /users/{id}`) with `source="route"` so transactions group
  correctly in Sentry.
- Removed the unused private `_redact_headers_helper` method.

## [0.1.1] - 2026-04-19

### Changed

- Bump `Development Status` classifier to `5 - Production/Stable`.

## [0.1.0] - 2026-04-19

### Added

- `SentryPlugin` — HawkAPI `Plugin` subclass that initialises `sentry_sdk` on startup,
  flushes on shutdown, and captures unhandled exceptions via `on_exception`.
- `SentryMiddleware` — HawkAPI `Middleware` subclass that starts a Sentry performance
  transaction per request and attaches `http.*` tags on response.
- No-op mode: when `dsn` is `None` or empty string, `SentryPlugin.on_startup` does
  nothing — safe to use in local/test environments without a real DSN.
- `ignore_status_codes` parameter (default `(404, 401, 403)`) to suppress Sentry events
  for expected HTTP errors.
- `user_getter` callable and `include_user_data` flag for attaching user context to events.
- `before_send` passthrough to `sentry_sdk.init` for full event filtering control.
- Global `tags` dict applied to every captured event.
- `traces_sample_rate` and `profiles_sample_rate` wiring.
- Header redaction for `Authorization`, `Cookie`, `X-Api-Key`, `X-Auth-Token`,
  `Proxy-Authorization` in request context attached to Sentry events.
- `traceparent` header propagation into Sentry transaction `trace_id`.
- Full test suite (15 tests) covering plugin lifecycle, middleware behaviour,
  header redaction, user context, tag propagation, and integration with a real
  HawkAPI app via `httpx.AsyncClient`.
- CI workflow: lint (`ruff`), typecheck (`pyright`), test matrix (Python 3.12 + 3.13).
- Release workflow: build with `uv build`, publish via PyPI trusted publishing.

[Unreleased]: https://github.com/Hawk-API/hawkapi-sentry/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Hawk-API/hawkapi-sentry/releases/tag/v0.1.0
