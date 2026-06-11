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
from .schemas import Identity, Profile, TailoredSections


# =============================================================
# paths
# =============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PKG_DIR = Path(__file__).resolve().parent
SNIPPETS_PATH = PROJECT_ROOT / "snippets" / "experience.json"
IDENTITY_PATH = PKG_DIR / "data" / "identity.json"
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


def _merge_identity(
    identity: Identity,
    sections: TailoredSections,
) -> Profile:
    """
    Deterministically merge the static identity fields with the
    LLM-produced tailored sections to form the final `Profile`. The
    LLM never sees identity values, so this is the only place they
    enter the rendered output.
    """
    return Profile(
        name=identity.name,
        credential=identity.credential,
        contact=identity.contact,
        summary=sections.summary,
        education=identity.education,
        experience=sections.experience,
        publications_presentations=identity.publications_presentations,
        leadership=identity.leadership,
        skills=sections.skills,
    )


def tailor(jd_path: Path, out_path: Path) -> Path:
    """
    Run the full pipeline:
    1. Load data
    2. Analyse job spec
    3. Retrieve snippets (RAG)
    4. Generate CV
    5. Review CV
    6. Amend CV
    7. Finish

    Intermediate stage outputs are dumped under `output/run_<time_stamp>/` so each
    stage can be inspected in isolation when debugging.

    Company context is intentionally not researched — JDs typically embed
    the business / tech / values signals the downstream stages need.
    """
    from render_pdf import render

    from . import (
        amender,
        assembler,
        jd_analyser,
        retriever,
        reviewer,
    )

    # Step 1
    run_dir = _create_run_dir()
    jd_text = load_text(jd_path)
    identity = Identity.model_validate_json(IDENTITY_PATH.read_text())

    # Step 2
    jd_spec = jd_analyser.analyse_jd(jd_text)
    (run_dir / "jd_spec.json").write_text(jd_spec.model_dump_json(indent=2))

    # Step 3
    snippets = json.loads(SNIPPETS_PATH.read_text())
    selection = retriever.select_snippets(snippets, jd_spec)
    (run_dir / "selection.json").write_text(selection.model_dump_json(indent=2))

    # Step 4
    sections = assembler.assemble_profile(selection, jd_spec, snippets)
    (run_dir / "sections_draft.json").write_text(
        sections.model_dump_json(indent=2)
    )

    # Step 5
    report = reviewer.review(sections, jd_spec)
    (run_dir / "review.json").write_text(report.model_dump_json(indent=2))

    # Step 6
    sections = amender.amend(sections, report)
    (run_dir / "sections.json").write_text(sections.model_dump_json(indent=2))

    # Step 7
    final = _merge_identity(identity, sections)
    final_path = run_dir / "profile.json"
    final_path.write_text(final.model_dump_json(indent=2))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    return render(final_path, out_path)
