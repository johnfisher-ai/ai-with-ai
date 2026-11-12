import math
import random
import time

import anthropic


def _spend_cap_reached(error):
    body = getattr(error, "body", None)
    if not isinstance(body, dict):
        return False
    inner = body.get("error")
    if not isinstance(inner, dict):
        return False
    details = inner.get("details")
    return isinstance(details, dict) and details.get("error_code") == "enforced_spend_limit_reached"


def is_retryable(error):
    if isinstance(error, anthropic.APIConnectionError):
        return True
    if isinstance(error, anthropic.APIStatusError):
        status = error.status_code
        if status == 429 and _spend_cap_reached(error):
            return False
        return status in (408, 409, 429) or status >= 500
    return False


def retry_after(error):
    response = getattr(error, "response", None)
    if response is None:
        return None
    value = response.headers.get("retry-after")
    if value is None:
        return None
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(seconds) or seconds < 0:
        return None
    return seconds


def backoff_delay(attempt, base=1.0, cap=30.0, rng=random.random):
    return rng() * min(cap, base * 2 ** attempt)


def call_with_retries(fn, max_attempts=4, base=1.0, cap=30.0, sleep=time.sleep,
                      rng=random.random, on_retry=None):
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as error:
            if not is_retryable(error) or attempt + 1 >= max_attempts:
                raise
            delay = retry_after(error)
            if delay is None:
                delay = backoff_delay(attempt, base, cap, rng)
            if on_retry is not None:
                on_retry(attempt + 1, error, delay)
            sleep(delay)
            attempt += 1


def create_with_retries(client, request, **options):
    c = client.with_options(max_retries=0)
    return call_with_retries(lambda: c.messages.create(**request), **options)
