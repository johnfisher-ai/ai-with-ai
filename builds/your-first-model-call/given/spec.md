# ask.py

A command-line client for the Messages API. It sends one question, or a conversation typed line by line, to a Claude model through Anthropic's Python SDK and prints the reply. Apart from the standard library it needs only the SDK, and it imports the SDK only when `main` has to build a client itself, so the functions can be tested with a stand-in client and no key.

## DEFAULT_MODEL and DEFAULT_MAX_TOKENS

`DEFAULT_MODEL` is `"claude-sonnet-5-5"` and `DEFAULT_MAX_TOKENS` is `1024`.

## build_request(prompt, history=None, system=None, model=DEFAULT_MODEL, max_tokens=DEFAULT_MAX_TOKENS)

Return the keyword arguments for `client.messages.create`, as a dict with the keys `model`, `max_tokens` and `messages`, and the key `system` only when `system` is given and not empty. `messages` is a new list holding the messages of `history`, in order, followed by `{"role": "user", "content": prompt}`. Never change the list passed as `history`.

Raise `ValueError` if `prompt` is empty or only whitespace, if `max_tokens` is less than 1, or if `history` is not a valid conversation to add a question to. A valid history is empty, or starts with a `"user"` message, alternates between `"user"` and `"assistant"`, and ends with an `"assistant"` message. A message with any other role is invalid.

## answer_text(message)

Return the text of a response. Join the `text` of every content block whose `type` is `"text"`, in order and with no separator, and skip blocks of every other type, such as `"thinking"`. Return `""` when there are none.

## format_usage(usage)

Return a short description of a response's `usage`, such as `"20 tokens in, 57 out"`. When `usage.output_tokens_details.thinking_tokens` exists and is greater than 0, add how many of the output tokens were thinking, as in `"166 tokens in, 249 out, 103 of them thinking"`.

## chat(client, lines, out, system=None, model=DEFAULT_MODEL, max_tokens=DEFAULT_MAX_TOKENS, show_usage=False, history=None)

Run a conversation. For each string in the iterable `lines`, strip it, skip it if it is empty, and stop at a line that is exactly `/quit`. Send it with `client.messages.create(**build_request(...))`, passing the conversation so far as the history. Write the reply's text to `out`, then the usage line as `[<format_usage>]` when `show_usage` is true, then an empty line, each followed by a newline. Then add the question and the reply to the history, the reply as `{"role": "assistant", "content": message.content}`, so its content blocks go back to the API unchanged.

`history` starts the conversation from earlier messages and is not changed. Return the conversation as a new list of messages.

## main(argv=None, client=None, stdin=None, out=None)

Parse `argv` (the program's arguments when `None`) with `argparse`:

- an optional positional `prompt`
- `--system TEXT`, the system prompt
- `--model NAME`, defaulting to `DEFAULT_MODEL`
- `--max-tokens N`, an integer defaulting to `DEFAULT_MAX_TOKENS`
- `--usage`, which adds the usage line after each reply
- `--chat`, which reads a conversation from standard input, one line per message

`stdin` and `out` default to `sys.stdin` and `sys.stdout`. When `client` is `None`, import `anthropic` and use `anthropic.Anthropic()`, which reads the key from the `ANTHROPIC_API_KEY` environment variable.

With `--chat`, run `chat` over the lines of `stdin`, with `prompt`, when given, sent first. Without it, send one question. The question is `prompt`, or all of `stdin` when no `prompt` is given. If that is empty, write `ask.py: no question given` to `sys.stderr` and return 2. Otherwise write the reply's text to `out` followed by a newline, then the usage line in square brackets when `--usage` is given.

Return 0 when the replies were written. Let errors raised by the client propagate. Chapter 5 handles them.

Running `python3 ask.py ...` calls `main` and exits with its return value.
