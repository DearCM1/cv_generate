# cv_generate

Data-driven, print-ready CV generator. A Jinja2 HTML template is rendered against
a JSON profile and converted to A4 PDF via WeasyPrint. This is the rendering
stage of a planned RAG pipeline that produces tailored CVs from a job
description + company profile (see `CLAUDE.md`).

## Structure

```
cv_generate/
├── render_pdf/             Rendering package (JSON → PDF)
│   ├── __init__.py         Exposes `render(data_path, output_path)`
│   ├── main.py             CLI entry point
│   ├── templates/cv.html   Jinja2 HTML template
│   ├── static/style.css    Print-optimised stylesheet (A4, pt units)
│   └── data/profile.json   Sample profile / schema example
├── output/                 Rendered PDFs (gitignored)
├── requirements.txt
├── README.md
└── CLAUDE.md
```

A root-level orchestrator `.py` will sit alongside `render_pdf/` and import
`render` from it.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

WeasyPrint has native dependencies (Pango, cairo). On macOS: `brew install pango`.

## Usage

CLI (defaults to the sample profile):

```bash
python -m render_pdf.main
python -m render_pdf.main path/to/profile.json -o output/tailored.pdf
```

As a library:

```python
from pathlib import Path
from render_pdf import render

render(Path("data.json"), Path("output/cv.pdf"))
```

## Data shape

See `render_pdf/data/profile.json` for the full schema. Top-level keys consumed
by the template: `name`, `credential`, `contact`, `summary`, `education`,
`experience`, `publications_presentations`, `leadership`, `skills`. Fields
ending in `text` / `qualification` accept inline HTML (e.g. `<strong>`, `<a>`)
and are passed through the `| safe` filter.
