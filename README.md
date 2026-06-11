# cv_generate

Generate tailored, print-ready CVs from a job description and company
profile. A RAG pipeline (`tailor/`) selects experience snippets, picks the
framing that matches the role, assembles them into a profile JSON, and
hands off to a Jinja2 + WeasyPrint renderer (`render_pdf/`) that produces a
single-page A4 PDF.

## Structure

```
cv_generate/
├── tailor/                     RAG + LLM tailoring pipeline
│   ├── orchestrator.py         Wires the six pipeline stages
│   ├── jd_analyser.py          Step 2 — JD → JDSpec (ATS keywords, tone)
│   ├── company_researcher.py   Step 3 — uses hosted web_search
│   ├── retriever.py            Step 4 — picks snippets per render_hint
│   ├── assembler.py            Step 5 — builds the tailored Profile
│   ├── reviewer.py             Step 6 — critiques vs the JD
│   ├── amender.py              Step 7 — applies the review
│   ├── schemas.py              Pydantic models (Profile mirrors render_pdf)
│   ├── prompts.py              All prompt strings, grouped by step
│   ├── client.py               Shared Anthropic client + cache helpers
│   └── inputs.py               File loader (md / txt / pdf)
├── tailor.py                   CLI entrypoint for the pipeline
├── render_pdf/                 Rendering package (JSON → PDF)
│   ├── __init__.py             Exposes `render(data_path, output_path)`
│   ├── main.py                 CLI for the renderer in isolation
│   ├── templates/cv.html       Jinja2 HTML template
│   ├── static/style.css        Print-optimised stylesheet (A4, pt units)
│   └── data/profile.json       Sample profile + schema example
├── snippets/                   RAG snippet store
│   └── experience.json         Role chunks with canonical + variant framings
├── examples/                   Sample JD + company profile
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
export ANTHROPIC_API_KEY=...
```

WeasyPrint has native dependencies (Pango, cairo). On macOS:
`brew install pango`.

## Usage

End-to-end tailoring:

```bash
python tailor.py examples/jd.md examples/company.md
python tailor.py path/to/jd.md path/to/company.md -o cv.pdf
```

The orchestrator dumps each stage's structured output under
`output/run_<time_stamp>/` (`jd_spec.json`, `company.json`,
`selection.json`, `profile_draft.json`, `review.json`, `profile.json`)
so individual stages can be inspected and debugged in isolation.

Rendering on its own (skip the LLM stages — hand it a `profile.json`):

```bash
python -m render_pdf.main
python -m render_pdf.main path/to/profile.json -o output/tailored.pdf
```

As a library:

```python
from pathlib import Path

from tailor import tailor
tailor(Path("jd.md"), Path("company.md"), Path("output/cv.pdf"))

# or, render-only:
from render_pdf import render
render(Path("data.json"), Path("output/cv.pdf"))
```

## Pipeline at a glance

Each stage is a single forced tool call against Claude (Haiku for the
cheap JD extraction, Sonnet for everything else). Tool input schemas are
generated from Pydantic models so the model is structurally constrained
to emit valid JSON.

```
jd.md ─►  jd_analyser     ─►  JDSpec
company.md ─►  company_researcher (+web_search) ─►  CompanyContext
snippets ─►  retriever     ─►  SnippetSelection
            assembler     ─►  Profile (draft)
            reviewer      ─►  ReviewReport
            amender       ─►  Profile (final) ─► render_pdf ─► cv.pdf
```

## Data shape

See `render_pdf/data/profile.json` for the full schema; the
`tailor.schemas.Profile` Pydantic model mirrors it exactly. Top-level
keys consumed by the template: `name`, `credential`, `contact`,
`summary`, `education`, `experience`, `publications_presentations`,
`leadership`, `skills`. Fields ending in `text` / `qualification` accept
inline HTML (e.g. `<strong>`, `<a>`) and are passed through the `| safe`
filter — sanitise upstream when accepting LLM-generated content.
