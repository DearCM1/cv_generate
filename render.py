"""Render a CV PDF from a JSON profile using Jinja2 + WeasyPrint."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

ROOT = Path(__file__).parent
TEMPLATES_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"
OUTPUT_DIR = ROOT / "output"
DEFAULT_DATA = ROOT / "data" / "profile.json"
DEFAULT_OUTPUT = OUTPUT_DIR / "cv.pdf"


def render(data_path: Path, output_path: Path) -> Path:
    with data_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("cv.html")
    html_str = template.render(**data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html_str, base_url=str(ROOT)).write_pdf(
        target=str(output_path),
        stylesheets=[str(STATIC_DIR / "style.css")],
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a CV PDF from a JSON profile.")
    parser.add_argument(
        "data",
        nargs="?",
        type=Path,
        default=DEFAULT_DATA,
        help=f"Path to a JSON profile (default: {DEFAULT_DATA.relative_to(ROOT)})",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output PDF path (default: {DEFAULT_OUTPUT.relative_to(ROOT)})",
    )
    args = parser.parse_args()
    out = render(args.data, args.output)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
