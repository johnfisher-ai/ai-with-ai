import anthropic
import httpx2
import pytest

from retry import backoff_delay, call_with_retries, create_with_retries, is_retryable, retry_after

REQUEST = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
CLASSES = {400: anthropic.BadRequestError, 401: anthropic.AuthenticationError,
           403: anthropic.PermissionDeniedError, 404: anthropic.NotFoundError, 408: anthropic.APIStatusError,
           409: anthropic.ConflictError, 429: anthropic.RateLimitError, 500: anthropic.InternalServerError,
           503: anthropic.ServiceUnavailableError, 529: anthropic.OverloadedError}


def api_error(status, headers=None, error=None):
    """A status error built the way the SDK builds one, from a response written for these tests."""
    body = {"type": "error", "error": error or {"type": "fixture_error", "message": "Fixture error."}}
    response = httpx2.Response(status, request=REQUEST, headers=headers or {}, json=body)
    return CLASSES.get(status, anthropic.APIStatusError)("Fixture error.", response=response, body=body)


class Flaky:
    """A call that raises the given errors in turn, then returns "done"."""

    def __init__(self, *errors):
        self.errors = list(errors)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return "done"


@pytest.mark.parametrize("status", [408, 409, 429, 500, 503, 529])
def test_transient_statuses_are_retryable(status):
    assert is_retryable(api_error(status)) is True


@pytest.mark.parametrize("status", [400, 401, 403, 404, 413])
def test_request_errors_are_not_retryable(status):
    assert is_retryable(api_error(status)) is False


def test_connection_errors_and_timeouts_are_retryable():
    assert is_retryable(anthropic.APIConnectionError(request=REQUEST)) is True
    assert is_retryable(anthropic.APITimeoutError(REQUEST)) is True


def test_other_exceptions_are_not_retryable():
    assert is_retryable(ValueError("not from the API")) is False


def test_a_spend_cap_429_is_not_retryable():
    error = api_error(429, error={"type": "rate_limit_error", "message": "Fixture spend cap.",
                                  "details": {"error_code": "enforced_spend_limit_reached"}})
    assert is_retryable(error) is False


@pytest.mark.parametrize("value, expected", [("2", 2.0), ("1.5", 1.5), ("0", 0.0), ("soon", None), ("-1", None)])
def test_retry_after_reads_the_header(value, expected):
    assert retry_after(api_error(429, headers={"retry-after": value})) == expected


def test_retry_after_without_a_header_or_a_response():
    assert retry_after(api_error(429)) is None
    assert retry_after(anthropic.APIConnectionError(request=REQUEST)) is None


def test_backoff_doubles_and_stops_at_the_cap():
    assert [backoff_delay(a, rng=lambda: 1.0) for a in range(6)] == [1, 2, 4, 8, 16, 30]
    assert backoff_delay(2, base=0.5, cap=10.0, rng=lambda: 0.5) == 1.0
    assert backoff_delay(3, rng=lambda: 0.0) == 0.0


def test_a_call_that_succeeds_is_not_retried():
    slept = []
    assert call_with_retries(Flaky(), sleep=slept.append) == "done"
    assert slept == []


def test_rate_limits_wait_as_long_as_retry_after_says():
    fn, slept = Flaky(api_error(429, {"retry-after": "3"}), api_error(429, {"retry-after": "3"})), []
    assert call_with_retries(fn, sleep=slept.append) == "done"
    assert fn.calls == 3 and slept == [3.0, 3.0]


def test_without_retry_after_the_wait_is_exponential_backoff():
    fn, slept = Flaky(api_error(529), api_error(500), api_error(503)), []
    assert call_with_retries(fn, base=0.5, sleep=slept.append, rng=lambda: 1.0) == "done"
    assert slept == [0.5, 1.0, 2.0]


def test_a_request_error_is_raised_at_once():
    error = api_error(400)
    fn, slept = Flaky(error), []
    with pytest.raises(anthropic.BadRequestError) as raised:
        call_with_retries(fn, sleep=slept.append)
    assert raised.value is error and fn.calls == 1 and slept == []


def test_the_last_error_is_raised_when_attempts_run_out():
    errors = [api_error(529), api_error(529), api_error(529)]
    fn, slept = Flaky(*errors), []
    with pytest.raises(anthropic.OverloadedError) as raised:
        call_with_retries(fn, max_attempts=3, sleep=slept.append, rng=lambda: 0.0)
    assert raised.value is errors[2] and fn.calls == 3 and len(slept) == 2


def test_on_retry_hears_about_each_failed_attempt():
    first, second = api_error(429, {"retry-after": "1"}), anthropic.APIConnectionError(request=REQUEST)
    heard = []
    call_with_retries(Flaky(first, second), sleep=lambda s: None, rng=lambda: 1.0,
                      on_retry=lambda n, e, d: heard.append((n, e, d)))
    assert heard == [(1, first, 1.0), (2, second, 2.0)]


def test_max_attempts_must_be_at_least_one():
    fn = Flaky()
    with pytest.raises(ValueError):
        call_with_retries(fn, max_attempts=0)
    assert fn.calls == 0
    with pytest.raises(anthropic.RateLimitError):
        call_with_retries(Flaky(api_error(429)), max_attempts=1, sleep=lambda s: None)


class FakeClient:
    """Records with_options and create calls, and fails once before answering."""

    def __init__(self):
        self.options, self.requests = [], []
        self.messages = self

    def with_options(self, **options):
        self.options.append(options)
        return self

    def create(self, **request):
        self.requests.append(request)
        if len(self.requests) == 1:
            raise api_error(529)
        return "a message"


def test_create_with_retries_turns_off_the_sdks_own_retries():
    client, slept = FakeClient(), []
    request = {"model": "claude-sonnet-5-5", "max_tokens": 64, "messages": [{"role": "user", "content": "Hi"}]}
    assert create_with_retries(client, request, sleep=slept.append, rng=lambda: 1.0) == "a message"
    assert {"max_retries": 0} in client.options and client.requests == [request, request]
    assert slept == [1.0]
