"""Answers one support ticket: sorts it into a category, drafts a reply and reports what the reply cost.

    python3 -m supportdesk.desk "My order arrived with a cracked screen."

Reads the key from the ANTHROPIC_API_KEY environment variable.
"""
import sys

from . import ask, retry, tokencost, triage

SYSTEM = "You are a support assistant for an online electronics store. Reply in two or three sentences."


def handle(client, ticket):
    """Triage the ticket, draft a reply with retries, and price the reply."""
    category = triage.triage(client, ticket)
    request = ask.build_request(f"Draft a reply to this {category} ticket:\n\n{ticket}", system=SYSTEM)
    message = retry.create_with_retries(client, request)
    cost = tokencost.call_cost(message.usage, request["model"])
    return {"category": category, "reply": ask.answer_text(message), "cost": cost}


def main(argv=None):
    import anthropic
    ticket = " ".join(sys.argv[1:] if argv is None else argv) or sys.stdin.read()
    result = handle(anthropic.Anthropic(), ticket)
    print(f"[{result['category']}] {result['reply']}\n(reply cost {result['cost']:.6f} dollars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
