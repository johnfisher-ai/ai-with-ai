import string

CATEGORIES = ("billing", "login", "shipping", "other")
MODEL = "claude-sonnet-5-5"
SYSTEM_PROMPT = (
    "You sort customer support tickets for an online store. "
    "Reply with exactly one word from this list: billing, login, shipping, other."
)


def answer_text(reply):
    return "".join(
        getattr(b, "text", "") for b in reply.content if b.type == "text"
    )


def parse_category(text):
    t = text.strip().lower()
    return t if t in CATEGORIES else "unrecognized"


def normalize_label(raw):
    t = raw.lower().strip(string.whitespace + string.punctuation)
    return t if t in CATEGORIES else "other"


def triage(client, ticket, model=MODEL):
    if not ticket or not ticket.strip():
        raise ValueError("ticket must not be empty")
    reply = client.messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": ticket}],
    )
    return parse_category(answer_text(reply))
