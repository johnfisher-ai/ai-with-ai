import inspect
from types import SimpleNamespace

import pytest

import triage as module
from triage import CATEGORIES, MODEL, SYSTEM_PROMPT, answer_text, parse_category, triage


class FakeClient:
    """Stands in for the API client: records each request and answers with the blocks it was given."""

    def __init__(self, *texts, blocks=None):
        self.calls = []
        self.blocks = blocks if blocks is not None else [SimpleNamespace(type="text", text=t) for t in texts]
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(content=self.blocks)


def test_constants():
    assert CATEGORIES == ("billing", "login", "shipping", "other")
    assert MODEL == "claude-sonnet-5-5"
    assert SYSTEM_PROMPT == ("You sort customer support tickets for an online store. "
                             "Reply with exactly one word from this list: billing, login, shipping, other.")


def test_the_request_is_exactly_the_one_the_spec_gives():
    client = FakeClient("billing")
    triage(client, "I was charged twice.")
    assert client.calls == [{"model": "claude-sonnet-5-5", "max_tokens": 1024, "system": SYSTEM_PROMPT,
                             "messages": [{"role": "user", "content": "I was charged twice."}]}]


def test_the_ticket_is_passed_unchanged_and_the_model_can_be_chosen():
    client = FakeClient("login")
    triage(client, "  I can't sign in.  ", model="claude-haiku-5-5")
    assert client.calls[0]["model"] == "claude-haiku-5-5"
    assert client.calls[0]["messages"][0]["content"] == "  I can't sign in.  "


@pytest.mark.parametrize("reply, expected", [("billing", "billing"), (" Login\n", "login"), ("SHIPPING", "shipping"),
                                             ("other", "other"), ("Billing.", "billing"), ("shipping!", "shipping"),
                                             ("refund", "unrecognized"), ("I think billing", "unrecognized"),
                                             ("billing and login", "unrecognized"), ("", "unrecognized")])
def test_replies_become_categories_or_unrecognized(reply, expected):
    assert triage(FakeClient(reply), "a ticket") == expected


def test_thinking_blocks_are_ignored_and_text_blocks_joined():
    blocks = [SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text="ship"),
              SimpleNamespace(type="text", text="ping")]
    assert answer_text(SimpleNamespace(content=blocks)) == "shipping"
    assert triage(FakeClient(blocks=blocks), "a ticket") == "shipping"


@pytest.mark.parametrize("ticket", ["", "   ", "\n"])
def test_an_empty_ticket_is_refused_before_any_call(ticket):
    client = FakeClient("billing")
    with pytest.raises(ValueError):
        triage(client, ticket)
    assert client.calls == []


def test_the_module_does_not_import_the_sdk():
    assert "anthropic" not in inspect.getsource(module)


# The six cases the chapter wrote before any code existed, and one for a space before the final period
@pytest.mark.parametrize("raw, expected", [(" Billing.\n", "billing"), ("LOGIN", "login"), ("shipping!", "shipping"),
                                           ("other", "other"), ("refund", "unrecognized"), ("", "unrecognized"),
                                           ("billing .", "billing")])
def test_parse_category(raw, expected):
    assert parse_category(raw) == expected


def test_parse_category_flags_a_sentence():
    assert parse_category("I think this is a login problem.") == "unrecognized"


def test_the_module_has_one_function_for_reading_a_reply():
    assert not hasattr(module, "normalize_label")
