import argparse
import sys

DEFAULT_MODEL = "claude-sonnet-5-5"
DEFAULT_MAX_TOKENS = 1024


def build_request(prompt, history=None, system=None, model=DEFAULT_MODEL,
                  max_tokens=DEFAULT_MAX_TOKENS):
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt is empty")
    if max_tokens < 1:
        raise ValueError("max_tokens must be at least 1")
    history = list(history) if history else []
    for i, m in enumerate(history):
        expected = "user" if i % 2 == 0 else "assistant"
        role = m.get("role") if isinstance(m, dict) else None
        if role != expected:
            raise ValueError("invalid history")
    if history and history[-1]["role"] != "assistant":
        raise ValueError("history must end with an assistant message")
    request = {"model": model, "max_tokens": max_tokens,
               "messages": history + [{"role": "user", "content": prompt}]}
    if system:
        request["system"] = system
    return request


def answer_text(message):
    return "".join(b.text for b in message.content if getattr(b, "type", None) == "text")


def format_usage(usage):
    s = f"{usage.input_tokens} tokens in, {usage.output_tokens} out"
    details = getattr(usage, "output_tokens_details", None)
    thinking = getattr(details, "thinking_tokens", None) if details is not None else None
    if thinking and thinking > 0:
        s += f", {thinking} of them thinking"
    return s


def chat(client, lines, out, system=None, model=DEFAULT_MODEL,
         max_tokens=DEFAULT_MAX_TOKENS, show_usage=False, history=None):
    history = list(history) if history else []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line == "/quit":
            break
        request = build_request(line, history=history, system=system, model=model,
                                max_tokens=max_tokens)
        message = client.messages.create(**request)
        out.write(answer_text(message) + "\n")
        if show_usage:
            out.write(f"[{format_usage(message.usage)}]\n")
        out.write("\n")
        history = history + [{"role": "user", "content": line},
                             {"role": "assistant", "content": message.content}]
    return history


def main(argv=None, client=None, stdin=None, out=None):
    parser = argparse.ArgumentParser(prog="ask.py")
    parser.add_argument("prompt", nargs="?")
    parser.add_argument("--system")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--usage", action="store_true")
    parser.add_argument("--chat", action="store_true")
    args = parser.parse_args(argv)
    stdin = sys.stdin if stdin is None else stdin
    out = sys.stdout if out is None else out
    if client is None:
        import anthropic
        client = anthropic.Anthropic()

    if args.chat:
        lines = stdin
        if args.prompt:
            lines = [args.prompt] + list(stdin)
        chat(client, lines, out, system=args.system, model=args.model,
             max_tokens=args.max_tokens, show_usage=args.usage)
        return 0

    question = args.prompt if args.prompt else stdin.read()
    if not question or not question.strip():
        print("ask.py: no question given", file=sys.stderr)
        return 2
    message = client.messages.create(**build_request(
        question, system=args.system, model=args.model, max_tokens=args.max_tokens))
    out.write(answer_text(message) + "\n")
    if args.usage:
        out.write(f"[{format_usage(message.usage)}]\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
