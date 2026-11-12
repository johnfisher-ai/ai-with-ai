"""Tests for chapters/notebooks/book_client.py, the replay, live and record client the notebooks share.

    python3 -m pytest tests/

No test reaches the network. A fake API (an httpx2.MockTransport) stands in for Anthropic's, and its
responses are fixtures written for these tests, in the shape the Messages API documents. Their text
says so, and no chapter quotes them.
"""
import json
import pathlib
import sys

import anthropic
import httpx2
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "chapters" / "notebooks"))
import book_client  # noqa: E402

MODEL = "claude-opus-5-5"
FIXTURE_TEXT = "Fixture text written for the helper's tests, not a model's answer."


def message(text=FIXTURE_TEXT, mid="msg_fixture_1"):
    return {"id": mid, "type": "message", "role": "assistant", "model": MODEL,
            "content": [{"type": "text", "text": text}], "stop_reason": "end_turn",
            "stop_sequence": None, "usage": {"input_tokens": 12, "output_tokens": 14}}


def sse(*pieces):
    """A Messages API event stream, written for the tests, that spells out the pieces."""
    events = [("message_start", {"type": "message_start", "message": {**message(""), "content": [],
                                                                      "stop_reason": None}}),
              ("content_block_start", {"type": "content_block_start", "index": 0,
                                       "content_block": {"type": "text", "text": ""}})]
    events += [("content_block_delta", {"type": "content_block_delta", "index": 0,
                                        "delta": {"type": "text_delta", "text": p}}) for p in pieces]
    events += [("content_block_stop", {"type": "content_block_stop", "index": 0}),
               ("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn",
                                  "stop_sequence": None}, "usage": {"output_tokens": 3}}),
               ("message_stop", {"type": "message_stop"})]
    return "".join(f"event: {name}\ndata: {json.dumps(data)}\n\n" for name, data in events)


class FakeAPI(httpx2.BaseTransport):
    """Stands in for the API. Answers in turn from a list, and sends headers a recording must drop."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.requests = []

    def handle_request(self, request):
        self.requests.append(request)
        status, body = self.answers.pop(0)
        headers = {"request-id": "fixture-request-id", "x-fixture-header": "dropped",
                   "content-type": "text/event-stream" if isinstance(body, str) else "application/json"}
        content = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        return httpx2.Response(status, headers=headers, content=content)


def sent_key(request):
    """The key a request carried, in whichever header this SDK version sends it."""
    auth = request.headers.get("authorization", "")
    return auth.split(" ", 1)[1] if " " in auth else request.headers.get("x-api-key")


def ask(client, text="Say hello."):
    return client.messages.create(model=MODEL, max_tokens=64, messages=[{"role": "user", "content": text}])


@pytest.fixture
def folder(tmp_path, monkeypatch):
    monkeypatch.setenv("AIWAI_RECORDING_KEY", "fixture-key-for-record-mode")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("BOOK_MODE", raising=False)
    return tmp_path


def record(folder, answers, calls):
    fake = FakeAPI(answers)
    client = book_client.make_client("demo", mode="record", folder=folder, transport=fake, quiet=True)
    for call in calls:
        call(client)
    return fake, json.loads((folder / "demo.json").read_text())


def test_record_then_replay_twice_gives_the_same_message(folder):
    fake, saved = record(folder, [(200, message())], [ask])
    assert len(fake.requests) == 1
    for _ in range(2):
        client = book_client.make_client("demo", folder=folder, quiet=True)
        reply = ask(client)
        assert isinstance(reply, anthropic.types.Message)
        assert reply.content[0].text == FIXTURE_TEXT
        assert reply.usage.output_tokens == 14


def test_a_recording_keeps_the_content_type_and_no_other_header(folder):
    _, saved = record(folder, [(200, message())], [ask])
    assert saved["notebook"] == "demo" and saved["format"] == book_client.FORMAT
    (exchange,) = saved["exchanges"]
    assert set(exchange["response"]) == {"status", "content_type", "body"}
    assert exchange["response"]["content_type"] == "application/json"
    assert "fixture-request-id" not in json.dumps(saved) and "dropped" not in json.dumps(saved)
    assert "fixture-key-for-record-mode" not in json.dumps(saved)


def test_a_recording_names_its_model_date_and_sdk(folder):
    _, saved = record(folder, [(200, message())], [ask])
    (exchange,) = saved["exchanges"]
    assert exchange["model"] == MODEL
    assert len(exchange["recorded"]) == 10 and exchange["recorded"][4] == "-"
    assert exchange["sdk"] == anthropic.__version__
    req = exchange["request"]
    assert exchange["key"] == book_client.request_key(req["method"], req["path"], req["query"], req["body"])


def test_a_model_description_is_recorded_under_its_own_model(folder):
    described = {"type": "model", "id": MODEL, "display_name": "Fixture model description",
                 "max_input_tokens": 1000, "max_tokens": 100}
    _, saved = record(folder, [(200, described)], [lambda c: c.models.retrieve(MODEL)])
    (exchange,) = saved["exchanges"]
    assert exchange["request"]["method"] == "GET" and exchange["request"]["body"] is None
    assert exchange["model"] == MODEL
    replayed = book_client.make_client("demo", folder=folder, quiet=True).models.retrieve(MODEL)
    assert replayed.max_input_tokens == 1000


def test_a_request_that_was_never_recorded_fails_with_a_clear_message(folder):
    record(folder, [(200, message())], [ask])
    client = book_client.make_client("demo", folder=folder, quiet=True)
    with pytest.raises(anthropic.NotFoundError) as raised:
        ask(client, "A question the notebook never asked.")
    assert "book_client: no recorded response" in str(raised.value)


def test_the_same_request_twice_replays_both_answers_in_order_then_repeats(folder):
    record(folder, [(200, message("First fixture answer.")), (200, message("Second fixture answer."))],
           [ask, ask])
    client = book_client.make_client("demo", folder=folder, quiet=True)
    assert [ask(client).content[0].text for _ in range(3)] == [
        "First fixture answer.", "Second fixture answer.", "First fixture answer."]


def test_the_order_of_keys_in_a_request_does_not_change_its_key():
    a = book_client.request_key("POST", "/v1/messages", "", {"model": MODEL, "max_tokens": 5})
    b = book_client.request_key("POST", "/v1/messages", "", {"max_tokens": 5, "model": MODEL})
    c = book_client.request_key("POST", "/v1/messages", "", {"max_tokens": 6, "model": MODEL})
    assert a == b != c


def test_a_streamed_response_records_and_replays(folder):
    def stream(client):
        with client.messages.stream(model=MODEL, max_tokens=64,
                                    messages=[{"role": "user", "content": "Stream it."}]) as s:
            return s.get_final_message()
    _, saved = record(folder, [(200, sse("Fixture ", "stream."))], [stream])
    (exchange,) = saved["exchanges"]
    assert exchange["response"]["content_type"].startswith("text/event-stream")
    assert exchange["model"] == MODEL
    for _ in range(2):
        client = book_client.make_client("demo", folder=folder, quiet=True)
        assert stream(client).content[0].text == "Fixture stream."


def test_an_error_response_is_recorded_and_replayed_as_the_same_error(folder):
    error = {"type": "error", "error": {"type": "invalid_request_error", "message": "Fixture error."}}
    record(folder, [(400, error)], [lambda c: pytest.raises(anthropic.BadRequestError, ask, c)])
    client = book_client.make_client("demo", folder=folder, quiet=True)
    with pytest.raises(anthropic.BadRequestError, match="Fixture error."):
        ask(client)


def test_an_error_body_is_recorded_without_its_request_id(folder, monkeypatch):
    error = {"type": "error", "error": {"type": "invalid_request_error", "message": "Fixture error."},
             "request_id": "req_fixture_9"}
    _, saved = record(folder, [(400, error)], [lambda c: pytest.raises(anthropic.BadRequestError, ask, c)])
    assert "request_id" not in json.dumps(saved) and "req_fixture_9" not in json.dumps(saved)
    with pytest.raises(anthropic.BadRequestError) as raised:
        ask(book_client.make_client("demo", folder=folder, quiet=True))
    assert "req_fixture_9" not in str(raised.value)
    # the recording check rejects a body that still holds one
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
    import check_recordings
    monkeypatch.setattr(check_recordings, "NOTEBOOKS", folder.parent)
    path = folder / "demo.json"
    data = json.loads(path.read_text())
    data["exchanges"][0]["response"]["body"]["request_id"] = "req_fixture_9"
    path.write_text(json.dumps(data))
    assert any("request_id" in p for p in check_recordings.check(path))


def test_replay_needs_no_key_and_reports_what_it_replays(folder, monkeypatch, capsys):
    record(folder, [(200, message())], [ask])
    monkeypatch.delenv("AIWAI_RECORDING_KEY")
    client = book_client.make_client("demo", folder=folder)
    out = capsys.readouterr().out
    assert f"Replaying 1 recorded response from {MODEL}, recorded " in out
    assert ask(client).content[0].text == FIXTURE_TEXT


def test_live_mode_without_a_key_says_how_to_add_one(folder):
    with pytest.raises(RuntimeError, match="secrets panel"):
        book_client.make_client("demo", mode="live", folder=folder, quiet=True)


def test_live_mode_never_uses_the_books_recording_key(folder):
    # AIWAI_RECORDING_KEY is set by the fixture and ANTHROPIC_API_KEY is not: live mode must refuse
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        book_client.make_client("demo", mode="live", folder=folder, quiet=True)


def test_live_mode_sends_the_readers_key(folder, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fixture-reader-key")
    fake = FakeAPI([(200, message())])
    ask(book_client.make_client("demo", mode="live", folder=folder, transport=fake, quiet=True))
    assert sent_key(fake.requests[0]) == "fixture-reader-key"
    assert not (folder / "demo.json").exists()


def test_record_mode_sends_only_the_recording_key(folder, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fixture-reader-key")
    fake = FakeAPI([(200, message())])
    ask(book_client.make_client("demo", mode="record", folder=folder, transport=fake, quiet=True))
    assert sent_key(fake.requests[0]) == "fixture-key-for-record-mode"


def test_record_mode_refuses_a_readers_key_alone(folder, monkeypatch):
    monkeypatch.delenv("AIWAI_RECORDING_KEY")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fixture-reader-key")
    with pytest.raises(RuntimeError, match="AIWAI_RECORDING_KEY"):
        book_client.make_client("demo", mode="record", folder=folder, quiet=True)


def test_a_missing_recording_and_an_unknown_mode_fail_clearly(folder):
    with pytest.raises(FileNotFoundError, match="no recording at"):
        book_client.make_client("never-recorded", folder=folder, quiet=True)
    with pytest.raises(ValueError, match="mode must be one of"):
        book_client.make_client("demo", mode="recrod", folder=folder, quiet=True)


def test_book_mode_sets_the_mode(folder, monkeypatch):
    monkeypatch.setenv("BOOK_MODE", "record")
    fake = FakeAPI([(200, message())])
    ask(book_client.make_client("demo", folder=folder, transport=fake, quiet=True))
    assert len(fake.requests) == 1 and (folder / "demo.json").exists()


sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import check_recordings  # noqa: E402


def test_the_recording_check_computes_the_same_keys_as_the_helper():
    for body in ({"model": MODEL}, {"messages": [{"role": "user", "content": "é"}]}, None):
        assert check_recordings.request_key("POST", "/v1/messages", "beta=true", body) == \
            book_client.request_key("POST", "/v1/messages", "beta=true", body)


def test_the_recording_check_passes_a_recording_and_catches_tampering(folder, monkeypatch):
    record(folder, [(200, message())], [ask])
    (folder / "demo.ipynb").write_text("{}")
    monkeypatch.setattr(check_recordings, "NOTEBOOKS", folder)
    path = folder / "demo.json"
    assert check_recordings.check(path) == []
    data = json.loads(path.read_text())
    data["exchanges"][0]["response"]["headers"] = {"request-id": "fixture"}
    data["exchanges"][0]["request"]["body"]["max_tokens"] = 65
    del data["exchanges"][0]["model"]
    path.write_text(json.dumps(data))
    problems = " ".join(check_recordings.check(path))
    assert "fields" in problems
    data["exchanges"][0]["model"] = MODEL
    path.write_text(json.dumps(data))
    problems = " ".join(check_recordings.check(path))
    assert "response fields" in problems and "key does not match" in problems


def test_record_mode_sends_the_key_only_to_anthropics_api(folder, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://example.invalid/somewhere-else")
    fake = FakeAPI([(200, message())])
    ask(book_client.make_client("demo", mode="record", folder=folder, transport=fake, quiet=True))
    assert fake.requests[0].url.host == "api.anthropic.com"
