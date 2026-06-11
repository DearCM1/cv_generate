"""
Step 4 of the tailor pipeline: assemble the tailored CV sections.

The retriever has already chosen which snippets to use and the framing
variant of each. Here we:

1. Resolve each `(snippet_id, framing)` pick into its actual bullet text
   client-side (deterministic — no LLM call needed for lookups).
2. Hand the resolved bullets, the snippet `roles` metadata (title /
   organisation / dates), and the `JDSpec` to the configured model and
   ask it to weave them into a `TailoredSections` JSON via a forced tool call.

The LLM produces only `summary`, `experience[]`, and `skills[]`. Static
identity fields (name, contact, education, publications, leadership)
are merged in by the orchestrator after the pipeline completes — they
are deliberately kept out of the LLM's context so they cannot leak into
or be rewritten by the tailored output.
"""
# =============================================================
# packages
# =============================================================

from __future__ import annotations

import json
import sys

from anthropic import APIError

from .client import SONNET, cached_text_block, call_model
from .prompts import ASSEMBLER_SYSTEM, ASSEMBLER_USER
from .schemas import JDSpec, ModelMetrics, SnippetSelection, TailoredSections
from .tool_response import parse_forced_tool_response


# =============================================================
# config
# =============================================================

TOOL_NAME = "record_tailored_sections"
ASSEMBLER_MAX_TOKENS = 8192


# =============================================================
# functions
# =============================================================

def _tool_definition() -> dict:
    """
    Build the Anthropic client tool definition for the recording step,
    derived from the `TailoredSections` Pydantic schema so the model's
    output is guaranteed structurally valid.
    """
    return {
        "name": TOOL_NAME,
        "description": (
            "Record the tailored CV sections JSON (summary, experience, "
            "skills). Must match the `TailoredSections` schema exactly. "
            "Identity fields are merged in later; do not produce them."
        ),
        "input_schema": TailoredSections.model_json_schema(),
    }


def _resolve_text(snippet: dict, framing: str) -> str:
    """
    Return the snippet text for the requested framing. Falls back to the
    canonical `text` if no matching variant exists, emitting a stderr
    warning so the orchestrator log shows the mismatch.
    """
    if snippet.get("framing") == framing:
        return snippet["text"]

    for variant in snippet.get("variants", []):
        if variant.get("framing") == framing:
            return variant["text"]

    print(
        f"warn: framing '{framing}' not found on snippet "
        f"'{snippet.get('id')}'; falling back to canonical text",
        file=sys.stderr,
    )
    return snippet["text"]


def _resolve_picks(
    snippets: dict,
    selection: SnippetSelection,
) -> dict[str, list[dict]]:
    """
    Turn `SnippetSelection` into ready-to-use bullet material grouped
    by `render_hint`. Each entry carries the chosen text plus the
    snippet's skills and metrics, which the model uses to keep
    claims grounded.
    """
    index = {s["id"]: s for s in snippets.get("snippets", [])}
    resolved: dict[str, list[dict]] = {}

    for hint, picks in selection.picks_by_render_hint.items():
        bucket: list[dict] = []

        for pick in picks:
            snippet = index.get(pick.snippet_id)
            if snippet is None:
                raise KeyError(
                    f"snippet id '{pick.snippet_id}' is not in the corpus"
                )

            bucket.append(
                {
                    "snippet_id": pick.snippet_id,
                    "framing": pick.framing,
                    "text": _resolve_text(snippet, pick.framing),
                    "skills": snippet.get("skills", []),
                    "metrics": snippet.get("metrics", []),
                }
            )

        resolved[hint] = bucket

    return resolved


def assemble_profile(
    selection: SnippetSelection,
    jd_spec: JDSpec,
    snippets: dict,
) -> tuple[TailoredSections, ModelMetrics]:
    """
    Compose the tailored CV sections. Schema is enforced both by the
    forced tool call (input_schema) and by Pydantic validation of the
    returned object. Returns the validated sections alongside this
    call's `ModelMetrics`.
    """
    resolved = _resolve_picks(snippets, selection)
    roles = snippets.get("roles", {})

    try:
        response, metrics = call_model(
            model=SONNET,
            max_tokens=ASSEMBLER_MAX_TOKENS,
            system=[
                {"type": "text", "text": ASSEMBLER_SYSTEM},
                cached_text_block(
                    "TailoredSections schema (must match exactly):\n"
                    + json.dumps(TailoredSections.model_json_schema(), indent=2)
                ),
            ],
            tools=[_tool_definition()],
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=[
                {
                    "role": "user",
                    "content": ASSEMBLER_USER.format(
                        jd_spec=jd_spec.model_dump_json(indent=2),
                        roles=json.dumps(roles, indent=2),
                        snippets=json.dumps(resolved, indent=2),
                    ),
                }
            ],
        )
    except APIError as e:
        raise APIError(
            f"Assembler API call failed: {type(e).__name__}: {e}"
        ) from e

    sections = parse_forced_tool_response(
        response=response,
        model=TailoredSections,
        tool_name=TOOL_NAME,
        stage="Assembler",
        max_tokens=ASSEMBLER_MAX_TOKENS,
        max_tokens_name="ASSEMBLER_MAX_TOKENS",
    )

    return sections, metrics
