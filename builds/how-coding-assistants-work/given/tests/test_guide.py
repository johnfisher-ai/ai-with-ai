import ast
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "supportdesk"
GUIDE = ROOT / "GUIDE.md"
HEADINGS = ["## Modules", "## How a ticket flows", "## Running it", "## Gaps and risks"]


def functions():
    """Every top-level function in the package, as {name: module}, with duplicates kept as a set of modules."""
    found = {}
    for path in PACKAGE.glob("*.py"):
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, ast.FunctionDef):
                found.setdefault(node.name, set()).add(path.stem)
    return found


@pytest.fixture(scope="module")
def guide():
    assert GUIDE.exists(), "GUIDE.md is missing"
    return GUIDE.read_text()


def section(text, heading):
    """The text between a heading and the next of the four headings."""
    start = text.index(heading + "\n") + len(heading)
    later = [text.find(h + "\n", start) for h in HEADINGS]
    return text[start:min([i for i in later if i != -1] + [len(text)])]


def named_functions(text):
    """Every `name()` or `module.name()` in backticks, as (module or None, name)."""
    return [(m.group(1), m.group(2)) for m in re.finditer(r"`(?:([a-z_]+)\.)?([A-Za-z_][A-Za-z0-9_]*)\(\)`", text)]


def test_title_and_sections_in_order(guide):
    assert guide.startswith("# ")
    positions = [guide.find(h + "\n") for h in HEADINGS]
    assert -1 not in positions, f"missing a section: {HEADINGS}"
    assert positions == sorted(positions)


def test_every_module_has_a_bullet(guide):
    modules = section(guide, "## Modules")
    for path in sorted(PACKAGE.glob("*.py")):
        assert re.search(rf"^[-*] `{re.escape(path.name)}`", modules, re.M), f"no bullet for {path.name}"


def test_every_public_function_is_named(guide):
    named = {name for _, name in named_functions(guide)}
    public = {name for name in functions() if not name.startswith("_")}
    assert public - named == set()


def test_no_function_is_invented(guide):
    found = functions()
    for module, name in named_functions(guide):
        assert name in found, f"{name}() is not defined in supportdesk/"
        if module is not None:
            assert module in found[name], f"{module}.{name}() is not where {name}() is defined"


def test_the_flow_follows_the_code(guide):
    flow = [name for _, name in named_functions(section(guide, "## How a ticket flows"))]
    order = ["handle", "triage", "build_request", "create_with_retries", "call_cost"]
    firsts = [flow.index(name) for name in order if name in flow]
    assert len(firsts) == len(order), f"the flow should name {order}"
    assert firsts == sorted(firsts), "the flow names the functions out of order"


def test_running_it_gives_a_command_and_the_key(guide):
    running = section(guide, "## Running it")
    assert "```" in running and "python3 -m supportdesk.desk" in running
    assert "ANTHROPIC_API_KEY" in running


def test_at_least_three_gaps_each_naming_a_file(guide):
    gaps = [line for line in section(guide, "## Gaps and risks").splitlines() if re.match(r"^[-*] ", line)]
    assert len(gaps) >= 3
    for line in gaps:
        assert re.search(r"[a-z_]+\.py", line), f"this gap names no file: {line}"


def test_the_guide_is_short(guide):
    assert len(guide.split()) < 900


def test_the_package_is_unchanged():
    # the sizes of the files the book gave, so a guide written by editing the code fails
    sizes = {p.name: len(p.read_bytes()) for p in PACKAGE.glob("*.py")}
    assert sizes == SIZES


SIZES = {'__init__.py': 99, 'ask.py': 3717, 'desk.py': 1209, 'retry.py': 2134, 'tokencost.py': 2360, 'triage.py': 994}
