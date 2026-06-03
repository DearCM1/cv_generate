"""
End-to-end orchestrator. Stages are imported lazily so partial scaffolds
of the package remain importable while individual stages are being built.
"""
# =============================================================
# packages
# =============================================================

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .inputs import load_text
from .schemas import Profile


# =============================================================
# paths
# =============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SNIPPETS_PATH = PROJECT_ROOT / "snippets" / "experience.json"
BASE_PROFILE_PATH = PROJECT_ROOT / "render_pdf" / "data" / "profile.json"
OUTPUT_ROOT = PROJECT_ROOT / "output"


# =============================================================
# functions
# =============================================================

def _create_run_dir() -> Path:
    """
    Creates new subdirectory to save the output file and
    debugging within the output directory.
    """
    time_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = OUTPUT_ROOT / f"run_{time_stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    return run_dir


def tailor(jd_path: Path, company_path: Path, out_path: Path) -> Path:
    """
    Run the full pipeline:
    1. Load data
    2. Analyse job spec
    3. Research company
    4. Retrieve snippets (RAG)
    5. Generate CV
    6. Review CV
    7. Amend CV
    8. Finish

    Intermediate stage outputs are dumped under `output/run_<time_stamp>/` so each
    stage can be inspected in isolation when debugging.
    """
    from render_pdf import render

    from . import (
        amender,
        assembler,
        company_researcher,
        jd_analyzer,
        retriever,
        reviewer
    )

    run_dir = _create_run_dir()
    jd_text = load_text(jd_path)
    company_text = load_text(company_path)

    jd_spec = jd_analyzer.analyze_jd(jd_text)
    (run_dir / "jd_spec.json").write_text(jd_spec.model_dump_json(indent=2))

    company = company_researcher.research_company(company_text)
    (run_dir / "company.json").write_text(company.model_dump_json(indent=2))

    snippets = json.loads(SNIPPETS_PATH.read_text())
    selection = retriever.select_snippets(snippets, jd_spec, company)
    (run_dir / "selection.json").write_text(selection.model_dump_json(indent=2))

    base = Profile.model_validate_json(BASE_PROFILE_PATH.read_text())
    profile = assembler.assemble_profile(selection, jd_spec, company, base, snippets)
    (run_dir / "profile_draft.json").write_text(profile.model_dump_json(indent=2))

    report = reviewer.review(profile, jd_spec)
    (run_dir / "review.json").write_text(report.model_dump_json(indent=2))

    final = amender.amend(profile, report)
    final_path = run_dir / "profile.json"
    final_path.write_text(final.model_dump_json(indent=2))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    return render(final_path, out_path)
