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

from uuid import UUID
from uuid6 import uuid7

from .inputs import load_text
from .schemas import (
    Identity,
    Metrics,
    Profile,
    RunTimeMetrics,
    TailoredSections,
)


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

def _create_run_dir(run_id: UUID) -> Path:
    """
    Create the per-run subdirectory under `output/`, named after the
    run's uuid7 so the directory name doubles as the public
    `calumdear.dev/cv/<uuid7>` URL slug.
    """
    run_dir = OUTPUT_ROOT / f"run_{run_id}"
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
    Run the full RAG CV-tailoring pipeline end-to-end.

    Steps 1–9 below (and in the code) correspond to the architecture described
    in README.md, which documents five LLM stages (each a forced tool call,
    Sonnet + Haiku) plus merging and rendering.

    1. Load inputs: JD text, static identity, run ID, timestamps.
    2. LLM stage 1: JD Analysis (Haiku). Extract keywords, skills, tone.
    3. LLM stage 2: Snippet Retrieval (Sonnet). RAG: pick experience bullets.
    4. LLM stage 3: Section Assembly (Sonnet). Weave snippets into CV profile.
    5. LLM stage 4: Review (Sonnet). Critique vs job spec.
    6. LLM stage 5: Amendment (Sonnet). Apply feedback, finalize profile.
    7. Metrics aggregation. Capture timing, tokens, cost across all stages.
    8. Output: Merge identity with tailored sections; render PDF.
    9. Render audit: Generate public run page, publish to website repo.

    All intermediate outputs (jd_spec, selection, sections_draft, review,
    sections, profile) are written to `output/run_<uuid7>/` for inspection.
    A master `metrics.json` records per-call timing, token usage, and cost.

    See README.md for architecture overview and rationale.
    """
    from render_pdf import render
    from render_site import (
        WEBSITE_ROOT,
        landing_url_for,
        publish_run,
        render_run_page,
    )

    from . import (
        amender,
        assembler,
        jd_analyser,
        retriever,
        reviewer,
    )

    # --- Step 1: Load inputs ---
    run_id = uuid7()
    run_start = datetime.now(timezone.utc)
    run_dir = _create_run_dir(run_id)
    jd_text = load_text(jd_path)
    identity = Identity.model_validate_json(IDENTITY_PATH.read_text())

    # --- Step 2: LLM stage 1 — JD Analysis (Haiku) ---
    jd_spec, jd_metrics = jd_analyser.analyse_jd(jd_text)
    (run_dir / "jd_spec.json").write_text(jd_spec.model_dump_json(indent=2))

    # --- Step 3: LLM stage 2 — Snippet Retrieval (Sonnet) ---
    snippets = json.loads(SNIPPETS_PATH.read_text())
    selection, sel_metrics = retriever.select_snippets(snippets, jd_spec)
    (run_dir / "selection.json").write_text(selection.model_dump_json(indent=2))

    # --- Step 4: LLM stage 3 — Section Assembly (Sonnet) ---
    sections, asm_metrics = assembler.assemble_profile(
        selection, jd_spec, snippets,
    )
    (run_dir / "sections_draft.json").write_text(
        sections.model_dump_json(indent=2)
    )

    # --- Step 5: LLM stage 4 — Review (Sonnet) ---
    report, rev_metrics = reviewer.review(sections, jd_spec)
    (run_dir / "review.json").write_text(report.model_dump_json(indent=2))

    # --- Step 6: LLM stage 5 — Amendment (Sonnet) ---
    sections, amd_metrics = amender.amend(sections, report)
    (run_dir / "sections.json").write_text(sections.model_dump_json(indent=2))

    # --- Step 7: Metrics aggregation ---
    run_finish = datetime.now(timezone.utc)
    metrics = Metrics(
        id=run_id,
        runtime=RunTimeMetrics(
            start=run_start,
            finish=run_finish,
            elapsed=run_finish - run_start,
        ),
        model_metrics=[
            jd_metrics,
            sel_metrics,
            asm_metrics,
            rev_metrics,
            amd_metrics,
        ],
        job_spec=jd_spec,
        snippet_selection=selection,
    )
    (run_dir / "metrics.json").write_text(metrics.model_dump_json(indent=2))

    # --- Step 8: Output — merge identity & render PDF ---
    page_url = landing_url_for(
        str(run_id),
        company=jd_spec.company,
        role=jd_spec.role_title,
    )
    final = _merge_identity(identity, sections)
    final_path = run_dir / "profile.json"
    final_path.write_text(final.model_dump_json(indent=2))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path = render(final_path, out_path, page_url=page_url)

    # --- Step 9: Render audit page & publish ---
    render_run_page(metrics)
    publish_run(str(run_id), WEBSITE_ROOT)

    return pdf_path
