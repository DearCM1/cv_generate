# cv_generate

Generate tailored, print-ready CVs from a job description. A RAG pipeline
(`tailor/`) selects experience snippets, picks the framing that matches the
role, assembles them into a profile JSON, and hands off to a Jinja2 +
WeasyPrint renderer (`render_pdf/`) that produces a single-page A4 PDF.

Company context isn't researched separately — JDs typically embed the
business / tech / values signals the downstream stages need, and the
prompts are written to lean on that embedded context.

## Structure

```
cv_generate/
├── tailor/                     RAG + LLM tailoring pipeline
│   ├── orchestrator.py         Wires the pipeline stages
│   ├── jd_analyser.py          Step 2 — JD → JDSpec (ATS keywords, tone)
│   ├── retriever.py            Step 3 — picks snippets per render_hint
│   ├── assembler.py            Step 4 — builds the tailored sections
│   ├── reviewer.py             Step 5 — critiques vs the JD
│   ├── amender.py              Step 6 — applies the review
│   ├── schemas.py              Pydantic models (Profile mirrors render_pdf)
│   ├── prompts.py              All prompt strings, grouped by step
│   ├── client.py               Shared Anthropic client + cache helpers
│   ├── inputs.py               File loader (md / txt / pdf)
│   └── data/identity.json      Static identity merged client-side
├── tailor.py                   CLI entrypoint for the pipeline
├── render_pdf/                 Rendering package (JSON → PDF)
│   ├── __init__.py             Exposes `render(data_path, output_path)`
│   ├── main.py                 CLI for the renderer in isolation
│   ├── templates/cv.html       Jinja2 HTML template
│   ├── static/style.css        Print-optimised stylesheet (A4, pt units)
│   └── data/profile.json       Sample profile + schema example
├── snippets/                   RAG snippet store
│   └── experience.json         Role chunks with canonical + variant framings
├── examples/                   Sample JD
├── output/                     Rendered PDFs + per-run stage dumps (gitignored)
├── reference/                  Source reference CVs (gitignored)
├── requirements.txt
└── README.md
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

WeasyPrint has native dependencies (Pango, cairo). On macOS:
`brew install pango`.

This project uses python-dotenv>=1.2.2 to inject the Anthropic API key into the environment. Write `ANTHROPIC_API_KEY="..."` within a .env file within the repo root.

## Usage

End-to-end tailoring:

```bash
python tailor.py examples/jd.md
python tailor.py path/to/jd.md -o cv.pdf
```

The orchestrator dumps each stage's structured output under
`output/run_<uuid7>/` (`jd_spec.json`, `selection.json`,
`sections_draft.json`, `review.json`, `sections.json`, `profile.json`)
so individual stages can be inspected and debugged in isolation. The
same directory also receives a `metrics.json` capturing per-call
timing, token usage, and dollar cost for the public-facing run page.

Rendering on its own (skip the LLM stages — hand it a `profile.json`):

```bash
python -m render_pdf.main
python -m render_pdf.main path/to/profile.json -o output/tailored.pdf
```

As a library:

```python
from pathlib import Path

from tailor import tailor
tailor(Path("jd.md"), Path("output/cv.pdf"))

# or, render-only:
from render_pdf import render
render(Path("data.json"), Path("output/cv.pdf"))
```

## Orchestration

The `tailor()` function in `tailor/orchestrator.py` runs nine sequential steps.
This is the canonical reference; code comments in `orchestrator.py` mark each step.

1. **Load inputs**: Parse JD text; load static identity; generate run ID and timestamps.
2. **LLM stage 1 — JD Analysis** (Haiku): `jd_analyser.analyse_jd()` extracts keywords,
   must-haves, tone signals, and a framing hint → `JDSpec`.
3. **LLM stage 2 — Snippet Retrieval** (Sonnet): `retriever.select_snippets()` picks
   experience bullets per render-hint section (full corpus cached) → `SnippetSelection`.
4. **LLM stage 3 — Section Assembly** (Sonnet): `assembler.assemble_profile()` weaves
   selected snippets into CV sections → `TailoredSections` (draft).
5. **LLM stage 4 — Review** (Sonnet): `reviewer.review()` critiques the draft against
   the job spec → `ReviewReport`.
6. **LLM stage 5 — Amendment** (Sonnet): `amender.amend()` applies the review feedback
   → `TailoredSections` (final).
7. **Metrics aggregation**: Collect timing, token counts, and cost from all five stages
   into a master `Metrics` object.
8. **Output**: Merge `identity` with the final tailored sections (client-side, LLM-free)
   → `Profile`; render to PDF via `render_pdf`.
9. **Audit & publish**: Generate a public run page (`render_site`) and optionally publish
   it to the website repo (Cloudflare Pages).

Steps 2–6 are LLM stages, each a single forced tool call. Step 7 aggregates the
captured metrics. Steps 8–9 are post-processing (no LLM, no API calls).

## Pipeline at a glance

Each LLM stage (steps 2–6) uses a single forced tool call against Claude (Haiku
for cheap JD extraction, Sonnet for everything else). Tool input schemas are
generated from Pydantic models so the model is constrained to emit valid JSON.

```
jd.md     ─►  jd_analyser  ─►  JDSpec
snippets  ─►  retriever    ─►  SnippetSelection
              assembler    ─►  TailoredSections (draft)
              reviewer     ─►  ReviewReport
              amender      ─►  TailoredSections (final)
identity ─┬──────────────────► Profile ─► render_pdf ─► cv.pdf
sections ─┘
```

## Data shape

See `render_pdf/data/profile.json` for the full schema; the
`tailor.schemas.Profile` Pydantic model mirrors it exactly. Top-level
keys consumed by the template: `name`, `credential`, `contact`,
`summary`, `education`, `experience`, `publications_presentations`,
`leadership`, `skills`. Fields ending in `text` / `qualification` accept
inline HTML (e.g. `<strong>`, `<a>`) and are passed through the `| safe`
filter — sanitise upstream when accepting LLM-generated content.
