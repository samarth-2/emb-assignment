import time
from collections.abc import Callable
from typing import TypeVar

from google import genai
from google.genai import errors as genai_errors

from app.config import get_settings

settings = get_settings()

_client: genai.Client | None = None

_RETRY_ATTEMPTS = 2
_RETRY_DELAY_SECONDS = 1.5

T = TypeVar("T")


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.google_api_key)
    return _client


def call_with_retry(fn: Callable[..., T], *args: object, **kwargs: object) -> T:
    """Retries once on a transient ServerError (e.g. Gemini's "model overloaded" 503)."""
    last_exc: genai_errors.ServerError | None = None
    for attempt in range(_RETRY_ATTEMPTS):
        try:
            return fn(*args, **kwargs)
        except genai_errors.ServerError as exc:
            last_exc = exc
            if attempt < _RETRY_ATTEMPTS - 1:
                time.sleep(_RETRY_DELAY_SECONDS)
    assert last_exc is not None
    raise last_exc
