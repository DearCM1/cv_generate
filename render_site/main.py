"""
Render a public run page from a pipeline `metrics.json` using Jinja2.

One run -> one self-contained `cv/<uuid7>/index.html` inside the `website/`
repo (deployed to Cloudflare Pages as static files, no build step). The page
showcases a single RAG CV-tailoring run: cost, token economics, per-stage
timing, the extracted job spec, and the snippet selection.
"""

# =============================================================
# packages
# =============================================================

from __future__ import annotations

import argparse
import os
import re
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from tailor.pricing import PRICING
from tailor.schemas import Metrics

# =============================================================
# config
# =============================================================

PKG_DIR = Path(__file__).parent
PROJECT_ROOT = PKG_DIR.parent  # cv_generate/
TEMPLATES_DIR = PKG_DIR / "templates"
OUTPUT_ROOT = PROJECT_ROOT / "output"

WEBSITE_ROOT = Path(
    os.environ.get("WEBSITE_REPO", PROJECT_ROOT.parent / "website")
)

BASE_URL = "https://calumdear.dev"

# Keep in sync with the call order in tailor/orchestrator.py.
STAGE_NAMES = [
    "JD Analysis",
    "Snippet Retrieval",
    "Section Assembly",
    "Review",
    "Amendment",
]

# Keep in sync with models used in tailor/client.py.
MODEL_LABELS = {
    "claude-sonnet-4-6": "Sonnet 4.6",
    "claude-haiku-4-5-20251001": "Haiku 4.5",
}


# =============================================================
# helpers
# =============================================================

def page_url_for(run_id: str) -> str:
    """Canonical public URL for a run page."""
    return f"{BASE_URL}/cv/{run_id}"


def _model_label(model: str) -> str:
    return MODEL_LABELS.get(model, model)


def _hint_display(render_hint: str) -> str:
    """
    Turn a render_hint like `experience[prime_appliances].bullets` into a
    human label like `Prime Appliances`. Falls back to the raw hint.
    """
    match = re.search(r"\[([^\]]+)\]", render_hint)
    key = match.group(1) if match else render_hint
    return key.replace("_", " ").title()


def _fmt_generated(start: datetime) -> str:
    """e.g. `11 June 2026, 16:44 UTC` (no leading-zero day, cross-platform)."""
    return f"{start.day} {start:%B %Y, %H:%M} UTC"


def _pct(part: float, whole: float) -> float:
    return round(part / whole * 100, 1) if whole else 0.0


# =============================================================
# view model
# =============================================================

def build_view_model(metrics: Metrics) -> dict:
    """
    Derive everything the template needs from the typed `Metrics` object.
    All arithmetic/formatting happens here so the Jinja template stays a
    thin loop-and-print layer (mirrors render_pdf's `template.render(**data)`).
    """
    run_id = str(metrics.id)
    run_seconds = metrics.runtime.elapsed.total_seconds()

    stages = []
    for i, m in enumerate(metrics.model_metrics):
        tok = m.cost.tokens
        offset = (m.runtime.start - metrics.runtime.start).total_seconds()
        elapsed = m.runtime.elapsed.total_seconds()
        stages.append(
            {
                "name": STAGE_NAMES[i] if i < len(STAGE_NAMES) else f"Stage {i + 1}",
                "model": m.model,
                "model_label": _model_label(m.model),
                "elapsed_seconds": round(elapsed, 2),
                "pct_of_run": _pct(elapsed, run_seconds),
                "offset_pct": _pct(offset, run_seconds),
                "tokens_in": tok.tokens_in,
                "tokens_out": tok.tokens_out,
                "tokens_cache_creation": tok.tokens_cache_creation,
                "tokens_cache_read": tok.tokens_cache_read,
                "tokens_total": tok.tokens_total,
                "dollars": m.cost.dollars,
            }
        )

    totals = {
        "cost": sum(m.cost.dollars for m in metrics.model_metrics),
        "tokens_total": sum(s["tokens_total"] for s in stages),
        "tokens_in": sum(s["tokens_in"] for s in stages),
        "tokens_out": sum(s["tokens_out"] for s in stages),
        "tokens_cache_creation": sum(s["tokens_cache_creation"] for s in stages),
        "tokens_cache_read": sum(s["tokens_cache_read"] for s in stages),
        "elapsed_seconds": round(run_seconds, 2),
        "n_calls": len(stages),
    }

    # --- Cost-breakdown pies -----------------------------------------
    # Token mix, each type split by the stage that produced it.
    token_segments = [
        ("Input", "tokens_in"),
        ("Output", "tokens_out"),
        ("Cache write", "tokens_cache_creation"),
        # Cache read omitted: ~always 0, which renders no slice.
    ]

    tokens_chart = {
        "id": "tokens",
        "title": "Tokens by type",
        "format": "int",
        "centerLabel": "tokens",
        "segments": [
            {
                "label": label,
                "value": totals[key],
                "breakdown": [
                    {"label": s["name"], "value": s[key]} for s in stages
                ],
            }
            for label, key in token_segments
        ],
    }

    cost_components = [
        ("Input", "tokens_in", "input"),
        ("Output", "tokens_out", "output"),
        ("Cache write", "tokens_cache_creation", "cache_write_5m"),
        ("Cache read", "tokens_cache_read", "cache_read"),
    ]

    cost_segments = []
    for s in stages:
        rates = PRICING[s["model"]]
        cost_segments.append(
            {
                "label": s["name"],
                "model": s["model_label"],
                "value": s["dollars"],
                "breakdown": [
                    {"label": label, "value": s[tok_key] * rates[rate_key] / 1_000_000}
                    for label, tok_key, rate_key in cost_components
                ],
            }
        )
    
    cost_chart = {
        "id": "cost",
        "title": "Cost by stage",
        "format": "usd",
        "centerLabel": "total cost",
        "segments": cost_segments,
    }

    cost_charts = [tokens_chart, cost_chart]

    selection = []
    for hint, picks in metrics.snippet_selection.picks_by_render_hint.items():
        selection.append(
            {
                "render_hint": hint,
                "display_name": _hint_display(hint),
                "count": len(picks),
                "picks": [
                    {"snippet_id": p.snippet_id, "framing": p.framing}
                    for p in picks
                ],
            }
        )

    # Distinct friendly model names, preserving first-seen order.
    models_used = list(dict.fromkeys(s["model_label"] for s in stages))

    return {
        "run_id": run_id,
        "page_url": page_url_for(run_id),
        "generated_at": _fmt_generated(metrics.runtime.start),
        "generated_at_iso": metrics.runtime.start.isoformat(),
        "totals": totals,
        "cost_charts": cost_charts,
        "stages": stages,
        "job_spec": metrics.job_spec,
        "selection": selection,
        "models_used": models_used,
    }


# =============================================================
# render
# =============================================================

def render_run_page(metrics: Metrics, website_root: Path = WEBSITE_ROOT) -> Path:
    """
    Render `WEBSITE_ROOT/cv/<uuid7>/index.html` (and a sibling copy of the
    raw `metrics.json`) for a single run. Shared CSS and JavaScript are owned
    by `website_root/assets/` and referenced by the rendered page. Returns the
    path to the written index.html.
    """
    run_id = str(metrics.id)
    out_dir = website_root / "cv" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["commas"] = lambda n: f"{int(n):,}"
    template = env.get_template("run.html")
    html_str = template.render(**build_view_model(metrics))

    index_path = out_dir / "index.html"
    index_path.write_text(html_str, encoding="utf-8")
    (out_dir / "metrics.json").write_text(
        metrics.model_dump_json(indent=2), encoding="utf-8"
    )

    return index_path


# =============================================================
# cli
# =============================================================

def _latest_metrics_path() -> Path | None:
    """
    Most recent `output/run_*/metrics.json` (uuid7 dir names sort by time).
    """
    candidates = sorted(OUTPUT_ROOT.glob("run_*/metrics.json"))
    return candidates[-1] if candidates else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a public run page from a pipeline metrics.json.",
    )
    parser.add_argument(
        "metrics",
        nargs="?",
        type=Path,
        default=None,
        help="Path to a run's metrics.json (default: latest under output/).",
    )
    parser.add_argument(
        "--website-root",
        type=Path,
        default=WEBSITE_ROOT,
        help=f"Target website repo (default: {WEBSITE_ROOT}).",
    )
    args = parser.parse_args()

    metrics_path = args.metrics or _latest_metrics_path()
    if metrics_path is None:
        parser.error("no metrics.json given and none found under output/.")

    metrics = Metrics.model_validate_json(Path(metrics_path).read_text())
    out = render_run_page(metrics, website_root=args.website_root)
    print(f"Wrote {out}")


# =============================================================
# main
# =============================================================

if __name__ == "__main__":
    main()
