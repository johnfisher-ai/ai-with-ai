# Licensing

This repository holds four kinds of material, and they are licensed differently.

| What | License | Covers |
|---|---|---|
| **The book** | [CC BY 4.0](LICENSE) | `chapters/*.html`, `index.html`, `toc.html`, `introduction.html`, `404.html`, `templates/`, `assets/` |
| **The datasets** | [CC BY 4.0](LICENSE) | `data/` |
| **The recorded model responses** | [CC BY 4.0](LICENSE), as far as any rights in them are mine | the recordings the notebooks replay, in `chapters/notebooks/recordings/` |
| **The Claude Code builds** | [CC BY 4.0](LICENSE) for the prompts, specs and transcripts, and [MIT](LICENSE-CODE) for the tests and the generated code | `builds/` |
| **The code** | [MIT](LICENSE-CODE) | `chapters/notebooks/*.ipynb` and `chapters/notebooks/book_client.py`, `scripts/`, `tests/`, `.github/workflows/`, and code shown inside a chapter page |

## What that means in practice

**You may use any of it, including commercially, as long as you credit me.** Teach from
it, translate it, quote it, build on it, put a chapter in front of a class or a team.

A reasonable credit:

> John Fisher, *Building AI with AI: A Visual Handbook*.
> https://johnfisher-ai.github.io/ai-with-ai/

For code, the MIT license asks only that the notice travels with any substantial
portion. Copying a few lines out of a notebook into your own work needs nothing.

## The datasets

Every dataset in `data/` is written for this book. The support tickets, documents,
conversations and other records a chapter works on are scenarios made up so that a method
has something honest to work on, and some are dirtied on purpose so a chapter can show the
cleaning as well as the result. None of them is drawn from a real organization or person.

## The recorded model responses

The notebooks call a language model through Anthropic's API. So that they run without a key
and print the same thing every time, each notebook replays responses recorded from the API,
and each recording names the model and the date it came from. They are outputs of
Anthropic's models, kept so readers can see what a model returned. A notebook run with its
live switch calls the API with your own key, under your own agreement with Anthropic, and
its answers will differ from the recorded ones.

## What this does not cover

Trademarks and the visual identity, the banner and the page styling, are not licensed for
reuse as marks. Use the material, not the branding, to represent your own work. Product
names mentioned in the book belong to their owners.
