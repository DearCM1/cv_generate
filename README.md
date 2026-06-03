# cv_generate

Data-driven, print-ready CV generator. A Jinja2 HTML template is rendered against a
JSON profile and converted to A4 PDF via WeasyPrint. Designed to be the rendering
stage of a downstream RAG pipeline that produces tailored CVs.

## Structure

```
cv_generate/
├── templates/cv.html      Jinja2 HTML template
├── static/style.css       Print-optimised stylesheet (A4, pt units)
├── data/profile.json      Sample profile matching the template's variables
├── output/                Rendered PDFs (gitignored)
├── render.py              CLI: JSON → PDF
└── requirements.txt
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

WeasyPrint has native dependencies (Pango, cairo). On macOS:
`brew install pango`.

## Usage

Render the default profile:

```bash
python render.py
```

Render a custom profile to a custom path:

```bash
python render.py path/to/profile.json -o output/tailored.pdf
```

## Data shape

See `data/profile.json` for the full schema. Top-level keys consumed by the
template: `name`, `credential`, `contact`, `summary`, `education`, `experience`,
`publications_presentations`, `leadership`, `skills`. Fields ending in `text` /
`qualification` accept inline HTML (e.g. `<strong>`, `<a>`) and are passed
through the `| safe` filter.
