import contextvars
import json
import logging
import sys
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))
logger.handlers = [_handler]
logger.propagate = False


def log_event(event: str, **fields: object) -> None:
    """Emit a single structured JSON log line."""
    payload = {
        "event": event,
        "request_id": _request_id_ctx.get(),
        "timestamp": time.time(),
        **fields,
    }
    logger.info(json.dumps(payload, default=str))


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assigns a request ID to every request and logs method/path/status/latency."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = _request_id_ctx.set(request_id)
        start = time.perf_counter()
        try:
            try:
                response = await call_next(request)
            except Exception as exc:
                log_event(
                    "request_error",
                    method=request.method,
                    path=request.url.path,
                    error=f"{type(exc).__name__}: {exc}",
                )
                raise

            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            log_event(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                latency_ms=latency_ms,
            )
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            _request_id_ctx.reset(token)


def get_request_id() -> str:
    return _request_id_ctx.get()
