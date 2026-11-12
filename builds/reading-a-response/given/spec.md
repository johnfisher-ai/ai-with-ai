# retry.py

Retries for calls to the Messages API. It decides which errors are worth another attempt, how long to wait before it, and runs a call until it succeeds, fails for a reason no retry can fix, or runs out of attempts. It uses the standard library and Anthropic's Python SDK, whose exception classes it reads.

## is_retryable(error)

Return `True` for an error that a later attempt of the same request may not hit, and `False` for every other error.

- `anthropic.APIConnectionError`, which includes `anthropic.APITimeoutError`, is retryable.
- `anthropic.APIStatusError` is retryable when its `status_code` is 408, 409 or 429, or 500 or more, which covers 529, the status Anthropic's API returns when it is overloaded.
- One 429 is not retryable. When the organization has reached its spend cap, the error's `body` is a dict whose `error.details.error_code` is `"enforced_spend_limit_reached"`, and retries fail until access resumes.
- Any other exception, including a status error such as 400, 401, 403 or 404, is not retryable.

## retry_after(error)

Return how many seconds the API asked the client to wait, as a float, from the `retry-after` header of a status error's `response`. Return `None` when the error has no response, the header is missing, or its value is not a number of seconds that is 0 or more.

## backoff_delay(attempt, base=1.0, cap=30.0, rng=random.random)

Return the delay before the next attempt with exponential backoff and full jitter. `attempt` counts the attempts that have failed so far, starting from 0 for the first. The delay is `rng()` multiplied by the smaller of `cap` and `base * 2 ** attempt`, so it lies between 0 and that ceiling. `rng` returns a float in [0, 1), and tests pass their own.

## call_with_retries(fn, max_attempts=4, base=1.0, cap=30.0, sleep=time.sleep, rng=random.random, on_retry=None)

Call `fn()` with no arguments and return what it returns. If it raises a retryable error and attempts remain, wait and call it again. `max_attempts` counts every call, the first included, and must be at least 1, or `ValueError` is raised before `fn` is called.

The wait is `retry_after(error)` when that is not `None`, because the API knows when capacity returns, and `backoff_delay(attempt, base, cap, rng)` otherwise. Before each wait, call `on_retry(number, error, delay)` when it is given, where `number` is the attempt that just failed, counting from 1. Then call `sleep(delay)`.

A non-retryable error is raised at once, unchanged. When the last attempt fails, raise its error unchanged, so the caller handles the same exception the SDK raised.

## create_with_retries(client, request, **options)

Send `client.messages.create(**request)` through `call_with_retries`, passing `options` on to it, and return the response. The SDK's client retries on its own, twice by default, and retries stacked on retries multiply the attempts. So send the request through `client.with_options(max_retries=0)`, which leaves the retrying to this module.
