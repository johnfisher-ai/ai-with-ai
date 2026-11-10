"""The Anthropic client every notebook in Building AI with AI uses, in one of three modes.

    from book_client import make_client
    client = make_client("your-first-model-call")              # replay, the default
    client = make_client("your-first-model-call", mode="live")  # the real API, with your own key

The client is the Anthropic SDK's own `anthropic.Anthropic`, so every call in a notebook is the code a
reader would write. Only the transport underneath it changes with the mode.

replay  Each request is answered from the notebook's recording, `recordings/<notebook>.json`, kept in
        the book's repository. No key and no network are needed, and every run prints the same thing.
        A request with no recording fails with a message that names it, never with an invented answer.
live    The real API, with the reader's key from Colab's secrets panel (or the ANTHROPIC_API_KEY
        environment variable elsewhere). Nothing is written. Answers will differ from the recorded ones.
record  For the book's own sessions. The real API, and every exchange is written to the recording,
        with the model, the date and the SDK version, and with every response header dropped except
        the content type, so no request ID or organization ID is kept.

The mode can also be set with the BOOK_MODE environment variable, which the book's sessions use to
record. A request is matched to its recording by its method, path, query and body, so a notebook's
calls must be the same as when they were recorded. When a notebook makes the same request more than
once, the recorded answers are served in order, starting again from the first when a cell is re-run. Code: MIT license. Recordings: see LICENSES.md.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import pathlib
from collections import defaultdict

import anthropic
import httpx2

FORMAT = 1
MODES = ("replay", "live", "record")
REPLAY_KEY = "replay-mode-needs-no-key"   # the SDK wants a key; replay never sends one anywhere


def request_key(method: str, path: str, query: str, body) -> str:
    """A short, stable name for a request: the same request always gets the same key."""
    canonical = json.dumps({"method": method, "path": path, "query": query, "body": body},
                           sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _describe(request: httpx2.Request):
    content = request.read()
    body = json.loads(content) if content else None
    return request.method, request.url.path, request.url.query.decode("ascii"), body


def _content_type(response: httpx2.Response) -> str:
    return response.headers.get("content-type", "application/json")


class Recording:
    """One notebook's recorded exchanges, as stored in recordings/<notebook>.json."""

    def __init__(self, notebook: str, folder: pathlib.Path):
        self.notebook = notebook
        self.path = pathlib.Path(folder) / f"{notebook}.json"
        self.exchanges: list[dict] = []

    def load(self) -> "Recording":
        if not self.path.exists():
            raise FileNotFoundError(
                f"book_client: no recording at {self.path}. Run the notebook from the folder that holds "
                f"its recordings/ folder, or set LIVE = True in Setup and use your own key.")
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("format") != FORMAT or data.get("notebook") != self.notebook:
            raise ValueError(f"book_client: {self.path} is not a format-{FORMAT} recording of {self.notebook}")
        self.exchanges = data["exchanges"]
        return self

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"notebook": self.notebook, "format": FORMAT, "exchanges": self.exchanges}
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(self.path)

    def models(self) -> list[str]:
        return sorted({e["model"] for e in self.exchanges if e.get("model")})

    def dates(self) -> list[str]:
        return sorted({e["recorded"] for e in self.exchanges})


class ReplayTransport(httpx2.BaseTransport):
    """Answers each request from a recording, in the order the answers were recorded."""

    def __init__(self, recording: Recording):
        self.recording = recording
        self.answers = defaultdict(list)
        for e in recording.exchanges:
            self.answers[e["key"]].append(e)
        self.calls = defaultdict(int)

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        key = request_key(*_describe(request))
        answers = self.answers.get(key)
        if not answers:
            message = (f"book_client: no recorded response for this request (key {key}) in "
                       f"{self.recording.path}. The request differs from the one the notebook recorded. "
                       f"Restore the cell's original code, or set LIVE = True in Setup and use your own key.")
            return httpx2.Response(404, request=request, json={
                "type": "error", "error": {"type": "not_found_error", "message": message}})
        answer = answers[self.calls[key] % len(answers)]
        self.calls[key] += 1
        response = answer["response"]
        content = (json.dumps(response["body"]).encode("utf-8") if "body" in response
                   else response["text"].encode("utf-8"))
        return httpx2.Response(response["status"], request=request, content=content,
                               headers={"content-type": response["content_type"]})


class RecordingTransport(httpx2.BaseTransport):
    """Sends each request to the real API and writes the exchange to the recording."""

    def __init__(self, recording: Recording, inner: httpx2.BaseTransport | None = None):
        self.recording = recording
        self.inner = inner or httpx2.HTTPTransport()
        self.seen = defaultdict(int)
        self.recording.exchanges = []          # a recording run replaces the notebook's recording

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        method, path, query, body = _describe(request)
        key = request_key(method, path, query, body)
        response = self.inner.handle_request(request)
        content = response.read()
        content_type = _content_type(response)
        stored = {"status": response.status_code, "content_type": content_type}
        if content_type.startswith("application/json"):
            stored["body"] = json.loads(content)
            model = stored["body"].get("model") if isinstance(stored["body"], dict) else None
        else:
            stored["text"] = content.decode("utf-8")
            model = (body or {}).get("model")
        self.seen[key] += 1
        self.recording.exchanges.append({
            "key": key, "call": self.seen[key],
            "request": {"method": method, "path": path, "query": query, "body": body},
            "response": stored,
            "model": model or (body or {}).get("model"),
            "recorded": datetime.date.today().isoformat(),
            "sdk": anthropic.__version__,
        })
        self.recording.save()
        # the response the SDK reads carries only the content type, as a replay will
        return httpx2.Response(response.status_code, request=request, content=content,
                               headers={"content-type": content_type})

    def close(self) -> None:
        self.inner.close()


def _reader_key() -> str:
    try:
        from google.colab import userdata          # Colab's secrets panel
        key = userdata.get("ANTHROPIC_API_KEY")
    except Exception:
        key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("book_client: live mode needs your Anthropic API key. In Colab, add it in the "
                           "secrets panel (the key icon) as ANTHROPIC_API_KEY and allow this notebook to "
                           "read it. Elsewhere, set the ANTHROPIC_API_KEY environment variable.")
    return key


def make_client(notebook: str, mode: str | None = None, folder="recordings",
                transport: httpx2.BaseTransport | None = None, quiet: bool = False) -> anthropic.Anthropic:
    """The notebook's Anthropic client. `transport` replaces the real network, for the helper's tests."""
    mode = mode or os.environ.get("BOOK_MODE", "replay")
    if mode not in MODES:
        raise ValueError(f"book_client: mode must be one of {MODES}, not {mode!r}")
    recording = Recording(notebook, pathlib.Path(folder))
    if mode == "live":
        if not quiet:
            print("Live mode: requests go to the Anthropic API with your key, and answers will differ "
                  "from the recorded ones.")
        http = anthropic.DefaultHttpxClient(transport=transport) if transport else None
        return anthropic.Anthropic(api_key=_reader_key(), http_client=http)
    if mode == "record":
        key = _reader_key()
        http = anthropic.DefaultHttpxClient(transport=RecordingTransport(recording, transport))
        if not quiet:
            print(f"Record mode: every exchange is written to {recording.path}.")
        return anthropic.Anthropic(api_key=key, http_client=http, max_retries=0)
    recording.load()
    if not quiet:
        n = len(recording.exchanges)
        print(f"Replaying {n} recorded response{'' if n == 1 else 's'} from {', '.join(recording.models())}, "
              f"recorded {', '.join(recording.dates())}. Set LIVE = True in Setup to call the API yourself.")
        sdks = sorted({e["sdk"] for e in recording.exchanges})
        if sdks != [anthropic.__version__]:
            print(f"Note: recorded with SDK {', '.join(sdks)}; this runtime has {anthropic.__version__}.")
    http = anthropic.DefaultHttpxClient(transport=ReplayTransport(recording))
    return anthropic.Anthropic(api_key=REPLAY_KEY, http_client=http, max_retries=0)
