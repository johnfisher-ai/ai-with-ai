# GUIDE.md

`supportdesk/` is a small Python package that answers support tickets. Read it and write `GUIDE.md` at the top of this folder, a guide for an engineer who joins the project tomorrow and has to change it. Change no other file.

## What the guide covers

The guide starts with a `# ` title line, then has these four sections, with these headings, in this order.

- `## Modules` describes every Python file in `supportdesk/`, one bullet per file, starting with the file name in backticks, such as `` `desk.py` ``.
- `## How a ticket flows` follows one ticket through the code, from the call that starts the work to the value it returns, naming each function in the order the code calls it.
- `## Running it` says how to run the package from a shell, with the command in a fenced code block, and which environment variable it reads the key from.
- `## Gaps and risks` lists, as bullets, at least three things a careful reviewer would want fixed or checked, each pointing to the file it concerns.

## How to name code

Write every function's name in backticks with empty parentheses, such as `` `handle()` ``, and name only functions that exist in `supportdesk/`. Name a function in a module other than the one it is defined in as `module.function()`, such as `` `triage.triage()` ``, whenever the bare name would be ambiguous.

Describe what the code does, and keep opinions to the gaps section. Keep the whole guide under 900 words.
