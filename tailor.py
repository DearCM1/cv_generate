"""
CLI entrypoint for the cv_generate tailoring pipeline.

Usage:

    python tailor.py <jd_path> <company_path> [-o output_path]

Defaults the output to `output/cv.pdf` at the project root so it lands
in the same gitignored render target as `python -m render_pdf.main`.
"""
# =============================================================
# packages
# =============================================================

from __future__ import annotations

import argparse
from pathlib import Path

from tailor import tailor as run_tailor


# =============================================================
# paths
# =============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "cv.pdf"


# =============================================================
# functions
# =============================================================

def main() -> None:
    """
    Parse args and invoke the pipeline. Stage outputs are dumped under
    `output/run_<time_stamp>/` by the orchestrator itself; the final
    rendered PDF is written to the `--output` path.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Generate a tailored CV PDF from a job description and "
            "company profile."
        ),
    )
    parser.add_argument(
        "jd_path",
        type=Path,
        help="Job description file (.md / .txt / .pdf)",
    )
    parser.add_argument(
        "company_path",
        type=Path,
        help="Company profile file (.md / .txt / .pdf)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output PDF path (default: {DEFAULT_OUTPUT})",
    )

    args = parser.parse_args()

    pdf_path = run_tailor(args.jd_path, args.company_path, args.output)
    print(f"wrote {pdf_path}")


# =============================================================
# entrypoint
# =============================================================

if __name__ == "__main__":
    main()
