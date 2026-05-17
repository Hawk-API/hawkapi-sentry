# hawkapi-sentry

[![PyPI](https://img.shields.io/pypi/v/hawkapi-sentry)](https://pypi.org/project/hawkapi-sentry/)
[![Python](https://img.shields.io/pypi/pyversions/hawkapi-sentry)](https://pypi.org/project/hawkapi-sentry/)
[![License](https://img.shields.io/pypi/l/hawkapi-sentry)](LICENSE)
[![CI](https://github.com/Hawk-API/hawkapi-sentry/actions/workflows/ci.yml/badge.svg)](https://github.com/Hawk-API/hawkapi-sentry/actions/workflows/ci.yml)
[![Downloads](https://img.shields.io/pypi/dm/hawkapi-sentry)](https://pypi.org/project/hawkapi-sentry/)

Sentry integration for [HawkAPI](https://github.com/Hawk-API/HawkAPI) — a plugin that initialises the Sentry SDK on startup and captures unhandled exceptions, plus a middleware that creates a performance transaction per request.

---

## Quickstart

```bash
pip install hawkapi-sentry
```

```python
from hawkapi import HawkAPI
from hawkapi_sentry import SentryPlugin, SentryMiddleware

app = HawkAPI()

app.add_plugin(
    SentryPlugin(
        dsn="https://key@sentry.io/123",
        environment="production",
        traces_sample_rate=0.1,
    )
)
app.add_middleware(SentryMiddleware)
```

That's it. Every unhandled exception is captured with full request context; every request gets a Sentry performance transaction.

---

## `SentryPlugin` parameter reference

| Parameter | Type | Default | Description |
|---|---|---|---|
| `dsn` | `str \| None` | `None` | Sentry DSN. Empty/`None` = no-op mode (safe for local dev). |
| `environment` | `str` | `"production"` | Sentry environment tag. |
| `release` | `str \| None` | `None` | Release string. `None` = not set. |
| `traces_sample_rate` | `float` | `0.0` | Fraction of transactions to sample for performance monitoring. |
| `profiles_sample_rate` | `float` | `0.0` | Fraction of sampled transactions to profile. |
| `include_user_data` | `bool` | `False` | When `True`, attach `request.state.user` dict to Sentry events. |
| `user_getter` | `Callable[[Request], dict] \| None` | `None` | Custom callable to extract user data from the request. Takes priority over `include_user_data`. |
| `before_send` | `Callable \| None` | `None` | Passed directly to `sentry_sdk.init`. Return `None` to drop an event. |
| `tags` | `dict[str, str] \| None` | `None` | Global tags applied to every captured event. |
| `ignore_status_codes` | `tuple[int, ...]` | `(404, 401, 403)` | HTTP status codes for which exceptions are **not** sent to Sentry. |

---

## Migration from `sentry-sdk[fastapi]`

| FastAPI / starlette-sentry | hawkapi-sentry |
|---|---|
| `sentry_sdk.init(integrations=[StarletteIntegration(), FastApiIntegration()])` | `app.add_plugin(SentryPlugin(dsn=...))` |
| `SentryAsgiMiddleware(app)` | `app.add_middleware(SentryMiddleware)` |
| `before_send` kwarg to `sentry_sdk.init` | `SentryPlugin(before_send=...)` |
| Manual `with sentry_sdk.push_scope() as scope: scope.set_user(...)` | `SentryPlugin(user_getter=lambda req: {...})` |

The main difference: HawkAPI plugins own the SDK lifecycle, so you never call `sentry_sdk.init()` yourself — `SentryPlugin.on_startup()` does it.

---

## Development

```bash
# Clone and install in editable mode with dev extras
git clone https://github.com/Hawk-API/hawkapi-sentry.git
cd hawkapi-sentry
uv sync --extra dev

# Run tests
uv run pytest tests/ -q

# Lint
uv run ruff check .
uv run ruff format .

# Type-check
uv run pyright src/
```

---

## License

[MIT](LICENSE) — Copyright (c) 2026 HawkAPI Contributors.
