PRICES_AS_OF = "2026-11"

PRICES = {
    "claude-haiku-5-5": {"input": 0.10, "cache_write": 0.125, "cache_read": 0.01, "output": 0.50},
    "claude-sonnet-5-5": {"input": 2.00, "cache_write": 2.50, "cache_read": 0.10, "output": 10.00},
    "claude-opus-5-5": {"input": 4.00, "cache_write": 5.00, "cache_read": 0.20, "output": 20.00},
}

LONG_PROMPT_PRICES = {
    "claude-haiku-5-5": (
        100_000,
        {"input": 0.50, "cache_write": 0.625, "cache_read": 0.05, "output": 2.50},
    ),
}

_FIELDS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")


def _counts(usage):
    out = {}
    for f in _FIELDS:
        if isinstance(usage, dict) or hasattr(usage, "get") and not hasattr(usage, f):
            v = usage.get(f)
        else:
            v = getattr(usage, f, None)
        v = 0 if v is None else v
        if v < 0:
            raise ValueError(f"{f} must not be negative")
        out[f] = v
    return out


def prompt_tokens(usage):
    c = _counts(usage)
    return c["input_tokens"] + c["cache_read_input_tokens"] + c["cache_creation_input_tokens"]


def call_cost(usage, model):
    if model not in PRICES:
        raise ValueError(f"unknown model: {model}")
    c = _counts(usage)
    rates = PRICES[model]
    if model in LONG_PROMPT_PRICES:
        threshold, long_rates = LONG_PROMPT_PRICES[model]
        if prompt_tokens(usage) > threshold:
            rates = long_rates
    total = (
        c["input_tokens"] * rates["input"]
        + c["cache_creation_input_tokens"] * rates["cache_write"]
        + c["cache_read_input_tokens"] * rates["cache_read"]
        + c["output_tokens"] * rates["output"]
    )
    return total / 1_000_000


def context_check(prompt, max_tokens, window=1_000_000):
    if prompt < 0 or max_tokens < 0 or window <= 0:
        raise ValueError("invalid arguments")
    if prompt > window:
        return "too long"
    if prompt + max_tokens <= window:
        return "fits"
    return "may stop early"


def project_conversation(first_prompt, added_per_turn, output_per_turn, turns):
    if turns < 1 or first_prompt < 0 or added_per_turn < 0 or output_per_turn < 0:
        raise ValueError("invalid arguments")
    return [
        {"input_tokens": first_prompt + k * added_per_turn, "output_tokens": output_per_turn}
        for k in range(turns)
    ]
