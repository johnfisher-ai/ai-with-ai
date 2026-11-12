import copy
import io
from types import SimpleNamespace

import pytest

from ask import DEFAULT_MAX_TOKENS, DEFAULT_MODEL, answer_text, build_request, chat, format_usage, main


def reply(text, tokens_in=20, tokens_out=57, thinking=0):
    """A stand-in for an SDK response: a thinking block, a text block and usage."""
    return SimpleNamespace(
        content=[SimpleNamespace(type="thinking", thinking="", signature="fixture"),
                 SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=tokens_in, output_tokens=tokens_out,
                              output_tokens_details=SimpleNamespace(thinking_tokens=thinking)))


class FakeClient:
    """Records every request and answers from a list of replies, in order."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.requests = []
        self.messages = self

    def create(self, **request):
        self.requests.append(copy.deepcopy(request))
        return self.replies.pop(0)


def test_defaults():
    assert DEFAULT_MODEL == "claude-sonnet-5-5" and DEFAULT_MAX_TOKENS == 1024


def test_the_smallest_request():
    assert build_request("Hi") == {"model": "claude-sonnet-5-5", "max_tokens": 1024,
                                   "messages": [{"role": "user", "content": "Hi"}]}


def test_a_system_prompt_is_sent_only_when_given():
    assert build_request("Hi", system="Be brief.")["system"] == "Be brief."
    assert "system" not in build_request("Hi", system="")
    assert "system" not in build_request("Hi", system=None)


def test_model_and_max_tokens_are_passed_through():
    request = build_request("Hi", model="claude-haiku-5-5", max_tokens=64)
    assert request["model"] == "claude-haiku-5-5" and request["max_tokens"] == 64


def test_history_comes_first_and_is_not_changed():
    history = [{"role": "user", "content": "My order is 48213."},
               {"role": "assistant", "content": "Thanks."}]
    before = copy.deepcopy(history)
    request = build_request("What's my order number?", history=history)
    assert request["messages"] == before + [{"role": "user", "content": "What's my order number?"}]
    assert history == before


@pytest.mark.parametrize("prompt, history, max_tokens", [
    ("", None, 1024),
    ("   \n", None, 1024),
    ("Hi", None, 0),
    ("Hi", [{"role": "assistant", "content": "Hello."}], 1024),
    ("Hi", [{"role": "user", "content": "A"}, {"role": "user", "content": "B"}], 1024),
    ("Hi", [{"role": "user", "content": "A"}], 1024),
    ("Hi", [{"role": "system", "content": "A"}, {"role": "assistant", "content": "B"}], 1024),
])
def test_build_request_rejects_what_the_api_would_refuse(prompt, history, max_tokens):
    with pytest.raises(ValueError):
        build_request(prompt, history=history, max_tokens=max_tokens)


def test_answer_text_skips_thinking_and_joins_text_blocks():
    message = SimpleNamespace(content=[SimpleNamespace(type="thinking", thinking=""),
                                       SimpleNamespace(type="text", text="Part one. "),
                                       SimpleNamespace(type="text", text="Part two.")])
    assert answer_text(message) == "Part one. Part two."
    assert answer_text(SimpleNamespace(content=[])) == ""


def test_format_usage():
    assert format_usage(reply("x").usage) == "20 tokens in, 57 out"
    assert format_usage(reply("x", 166, 249, 103).usage) == "166 tokens in, 249 out, 103 of them thinking"
    assert format_usage(SimpleNamespace(input_tokens=9, output_tokens=3)) == "9 tokens in, 3 out"


def test_main_sends_one_question_and_prints_the_answer():
    client, out = FakeClient(reply("A context window is ...")), io.StringIO()
    assert main(["What is a context window?"], client=client, out=out) == 0
    assert out.getvalue() == "A context window is ...\n"
    assert client.requests == [build_request("What is a context window?")]


def test_main_passes_the_options_through():
    client, out = FakeClient(reply("Short.")), io.StringIO()
    main(["--system", "Answer in one sentence.", "--model", "claude-opus-5-5", "--max-tokens", "200", "Why?"],
         client=client, out=out)
    assert client.requests == [{"model": "claude-opus-5-5", "max_tokens": 200, "system": "Answer in one sentence.",
                                "messages": [{"role": "user", "content": "Why?"}]}]


def test_main_prints_usage_when_asked():
    out = io.StringIO()
    main(["--usage", "Hi"], client=FakeClient(reply("Hello.", 166, 249, 103)), out=out)
    assert out.getvalue() == "Hello.\n[166 tokens in, 249 out, 103 of them thinking]\n"


def test_main_reads_the_question_from_stdin():
    client, out = FakeClient(reply("Read it.")), io.StringIO()
    main([], client=client, stdin=io.StringIO("Summarize this ticket.\n"), out=out)
    assert client.requests[0]["messages"][0]["content"].strip() == "Summarize this ticket."
    assert out.getvalue() == "Read it.\n"


def test_main_without_a_question_returns_2(capsys):
    client = FakeClient()
    assert main([], client=client, stdin=io.StringIO(""), out=io.StringIO()) == 2
    assert "ask.py: no question given" in capsys.readouterr().err
    assert client.requests == []


def test_chat_sends_the_history_with_each_question():
    first, second = reply("Sorry to hear that."), reply("Order 48213.")
    client, out = FakeClient(first, second), io.StringIO()
    history = chat(client, ["My screen arrived cracked.\n", "\n", "What was my order number?\n"], out)
    assert len(client.requests) == 2
    assert client.requests[1]["messages"] == [
        {"role": "user", "content": "My screen arrived cracked."},
        {"role": "assistant", "content": first.content},
        {"role": "user", "content": "What was my order number?"}]
    assert out.getvalue() == "Sorry to hear that.\n\nOrder 48213.\n\n"
    assert len(history) == 4 and history[3] == {"role": "assistant", "content": second.content}


def test_chat_stops_at_quit_and_can_show_usage():
    client, out = FakeClient(reply("One.")), io.StringIO()
    chat(client, ["First", "/quit", "Never sent"], out, show_usage=True)
    assert len(client.requests) == 1
    assert out.getvalue() == "One.\n[20 tokens in, 57 out]\n\n"


def test_chat_starts_from_a_history_without_changing_it():
    earlier = [{"role": "user", "content": "A"}, {"role": "assistant", "content": "B"}]
    client = FakeClient(reply("C"))
    history = chat(client, ["Next"], io.StringIO(), system="Be brief.", history=earlier)
    assert client.requests[0]["system"] == "Be brief."
    assert client.requests[0]["messages"][:2] == earlier and len(earlier) == 2
    assert len(history) == 4


def test_main_chat_sends_the_prompt_first():
    client, out = FakeClient(reply("Hello."), reply("Fine.")), io.StringIO()
    assert main(["--chat", "Hi"], client=client, stdin=io.StringIO("How are you?\n"), out=out) == 0
    assert [r["messages"][-1]["content"] for r in client.requests] == ["Hi", "How are you?"]
    assert out.getvalue() == "Hello.\n\nFine.\n\n"
