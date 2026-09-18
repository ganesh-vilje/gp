"""Gunicorn worker class for the production ASGI process (ADR-023).

Skeleton only for T-017 — full behaviour (parity checks, raw-peer client-IP
plumbing verification, SEC-T21 coverage) lands at T-025. This file exists now
because the Dockerfile's CMD and `.claude/project-config.md`'s `start:` line
both reference ``app.worker.RawPeerWorker`` as the gunicorn ``--worker-class``.

infrastructure.md §3 (rev 4, SEC-F1/ADR-023 rewritten): the stock
``uvicorn_worker.UvicornWorker`` defaults ``proxy_headers=True`` and lets
gunicorn's ``forwarded_allow_ips`` (default ``127.0.0.1``, overridable by the
``FORWARDED_ALLOW_IPS`` environment variable) install
``ProxyHeadersMiddleware``, which rewrites ``scope["client"]`` from
``X-Forwarded-For`` before the application runs. This subclass turns both
off so ``scope["client"][0]`` is always the raw TCP peer, which
``core/client_ip.py`` (the sole interpreter of ``Fly-Client-IP`` and
``X-Forwarded-For``) depends on.
"""

from uvicorn_worker import UvicornWorker


class RawPeerWorker(UvicornWorker):  # type: ignore[misc]
    """UvicornWorker with proxy-header trust disabled at the ASGI layer."""

    CONFIG_KWARGS = {"proxy_headers": False, "forwarded_allow_ips": []}
