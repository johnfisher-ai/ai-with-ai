# tokencost.py

A small module for budgeting calls to a language model. It turns the token counts a response reports into dollars, says whether a request fits a model's context window, and projects how the input of a conversation grows when every turn resends the history. Use only the Python standard library.

## PRICES, LONG_PROMPT_PRICES and PRICES_AS_OF

`PRICES_AS_OF` is the string `"2026-11"`, the month the prices were read from Anthropic's pricing page.

`PRICES` is a dict from model ID to a dict of rates in dollars per million tokens, with the keys `input`, `cache_write`, `cache_read` and `output`. `cache_write` is the price of a five-minute cache write.

| Model ID | input | cache_write | cache_read | output |
|---|---|---|---|---|
| `claude-haiku-5-5` | 0.10 | 0.125 | 0.01 | 0.50 |
| `claude-sonnet-5-5` | 2.00 | 2.50 | 0.10 | 10.00 |
| `claude-opus-5-5` | 4.00 | 5.00 | 0.20 | 20.00 |

Claude Haiku 5.5 charges more for a request whose prompt is over 100,000 tokens. `LONG_PROMPT_PRICES` is a dict from model ID to a pair `(threshold, rates)`, and holds one entry, `"claude-haiku-5-5": (100_000, {"input": 0.50, "cache_write": 0.625, "cache_read": 0.05, "output": 2.50})`.

## prompt_tokens(usage)

`usage` describes one response's token counts. It is either a mapping or an object with attributes, such as the `usage` of an Anthropic SDK response, and it may have the fields `input_tokens`, `output_tokens`, `cache_read_input_tokens` and `cache_creation_input_tokens`. A missing field, or one that is `None`, counts as 0.

Return the size of the prompt, which is `input_tokens + cache_read_input_tokens + cache_creation_input_tokens`. Raise `ValueError` if any field is negative.

## call_cost(usage, model)

Return the cost of one call in dollars, as a float that is not rounded. Multiply `input_tokens` by the `input` rate, `cache_creation_input_tokens` by `cache_write`, `cache_read_input_tokens` by `cache_read` and `output_tokens` by `output`, add the four, and divide by 1,000,000.

Use the rates in `PRICES`, unless the model is in `LONG_PROMPT_PRICES` and `prompt_tokens(usage)` is greater than its threshold. Then every one of the four counts is charged at the long-prompt rates, output included.

Raise `ValueError` if the model is not in `PRICES`, with the model ID in the message, and if any count is negative.

## context_check(prompt, max_tokens, window=1_000_000)

`prompt` is the number of tokens a request sends, `max_tokens` the most it may generate, and `window` the model's context window. Return one of three strings:

- `"fits"` when `prompt + max_tokens` is at most `window`
- `"may stop early"` when `prompt` is at most `window` but `prompt + max_tokens` is more, because the API accepts the request and stops the reply when the window is full
- `"too long"` when `prompt` is more than `window`, because the API rejects the request

Raise `ValueError` if `prompt` or `max_tokens` is negative, or `window` is not greater than 0.

## project_conversation(first_prompt, added_per_turn, output_per_turn, turns)

A conversation sends its whole history on every turn, so each turn's prompt is the previous turn's prompt plus the new user message and the previous reply. Return a list of `turns` dicts, one per turn, each with the keys `input_tokens` and `output_tokens`. Turn `k`, counting from 0, has `input_tokens` equal to `first_prompt + k * added_per_turn` and `output_tokens` equal to `output_per_turn`. Each dict can be passed to `call_cost` as a usage.

Raise `ValueError` if `turns` is less than 1 or any other argument is negative.
