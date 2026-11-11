# triage.py

A module that sorts a customer support ticket for an online store into one category by asking a language
model. It is one component of a larger program, so it takes the API client as an argument and never creates
one. Use only the Python standard library, and don't import the `anthropic` package.

## Constants

- `CATEGORIES` is the tuple `("billing", "login", "shipping", "other")`.
- `MODEL` is `"claude-sonnet-5-5"`.
- `SYSTEM_PROMPT` is exactly
  `"You sort customer support tickets for an online store. Reply with exactly one word from this list: billing, login, shipping, other."`

## answer_text(reply)

`reply` has a `content` list of blocks, and each block has a `type`. Return the `text` of every block whose
type is `"text"`, joined with nothing between them. Ignore every other block: a reply can carry `thinking`
blocks, whose text is empty.

## parse_category(text)

Strip surrounding whitespace and lowercase the result. Return it if it is one of `CATEGORIES`, and otherwise
return the string `"unrecognized"`. Do no other cleanup, so `"Billing."` is `"unrecognized"`.

## normalize_label(raw)

A tolerant alternative to `parse_category`, for a caller that wants every reply forced into a category.
Lowercase `raw`, then remove every whitespace and punctuation character (Python's `string.whitespace` and
`string.punctuation`) from both ends. Return the result if it is one of `CATEGORIES`, and otherwise return
`"other"`.

## triage(client, ticket, model=MODEL)

Raise `ValueError` if `ticket` is empty or only whitespace, without calling the client. Otherwise call
`client.messages.create` with exactly these keyword arguments and no others:

    model=model, max_tokens=1024, system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": ticket}]

Pass the ticket unchanged. Return `parse_category(answer_text(reply))`.
