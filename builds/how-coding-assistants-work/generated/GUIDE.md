# supportdesk guide

`supportdesk/` answers a support ticket in three steps: it sorts the ticket into a category, drafts a reply, and prices that reply.

## Modules

- `__init__.py` holds only a docstring; the package has no import-time code.
- `desk.py` is the entry point. `handle()` runs one ticket end to end and `main()` is the command line wrapper. It also holds the `SYSTEM` prompt for replies.
- `triage.py` sorts a ticket into one of `CATEGORIES` (billing, login, shipping, other). It defines `triage.triage()`, `triage.parse_category()`, `triage.normalize_label()` and its own `triage.answer_text()`.
- `ask.py` builds and sends plain requests. `ask.build_request()` validates the prompt, history and token limit and returns the request dict. `ask.answer_text()` joins the text blocks of a message, `ask.format_usage()` renders token counts, `ask.chat()` runs a multi-turn loop, and `ask.main()` is its own command line.
- `retry.py` wraps calls in retries. `retry.is_retryable()` decides whether an error is worth retrying, `retry.retry_after()` reads the `retry-after` header, `retry.backoff_delay()` computes a jittered exponential wait, `retry.call_with_retries()` is the loop, and `retry.create_with_retries()` applies it to `messages.create`.
- `tokencost.py` prices usage from the `PRICES` table. `tokencost.call_cost()` returns dollars, `tokencost.prompt_tokens()` totals the input side, `tokencost.context_check()` compares a prompt with the context window, and `tokencost.project_conversation()` lists usage for a growing conversation.

## How a ticket flows

1. `desk.handle()` receives the client and the ticket text.
2. It calls `triage.triage()`, which rejects an empty ticket, sends one `messages.create` request with the triage system prompt, and turns the reply into a category through `triage.answer_text()` and `triage.parse_category()`. The category is one of the four labels, or `unrecognized`.
3. `ask.build_request()` builds the drafting request from a prompt containing the category and ticket, with the `SYSTEM` prompt and the default model.
4. `retry.create_with_retries()` sends it using a client with the SDK's own retries turned off, and passes the call to `retry.call_with_retries()`, which retries errors that `retry.is_retryable()` accepts.
5. `tokencost.call_cost()` prices the message's usage for the request's model.
6. `ask.answer_text()` extracts the reply text, and `desk.handle()` returns a dict with `category`, `reply` and `cost`.

## Running it

```
export ANTHROPIC_API_KEY=your-key
python3 -m supportdesk.desk "My order arrived with a cracked screen."
```

The `anthropic` client reads the key from the `ANTHROPIC_API_KEY` environment variable. If no ticket is given as an argument, `desk.main()` reads it from standard input. It prints the category, the reply and the cost in dollars.

## Gaps and risks

- `triage.py`: `triage.normalize_label()` is never called, and it maps unknown labels to `other` while `triage.parse_category()` returns `unrecognized`. The two disagree, and `desk.py` puts `unrecognized` into the drafting prompt.
- `desk.py`: the triage call is not retried; only the drafting call goes through `retry.py`, so a transient error during triage fails the ticket.
- `desk.py`: `desk.main()` has no handling for an empty ticket or API errors, and the ticket text is placed directly into the prompt.
- `ask.py`: `ask.answer_text()` duplicates `triage.answer_text()` with slightly different behaviour, and the model name is repeated in `ask.py` and `triage.py`.
- `tokencost.py`: prices are hard-coded (`PRICES_AS_OF` is 2026-11) and only some models have long-prompt rates; `tokencost.call_cost()` raises for any model not in the table.
- `retry.py`: the retry loop sleeps in-process with no overall time limit beyond the attempt count.
