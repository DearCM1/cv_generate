"""
Step 3 of the tailor pipeline: snippet retrieval.

Given a `JDSpec`, ask Sonnet to pick the experience snippets (and the
framing variant of each) that best fit the role, grouped by the
`render_hint` field that determines which section of `profile.json`
they ultimately render into.

The snippet corpus is passed in a cached system block so the same content
can be re-used by later stages without re-billing the full corpus tokens.
"""
# =============================================================
# packages
# =============================================================

from __future__ import annotations

import json

from anthropic import APIError

from .client import SONNET, cached_text_block, client
from .prompts import RETRIEVER_SYSTEM, RETRIEVER_USER
from .schemas import JDSpec, SnippetSelection
from .tool_response import parse_forced_tool_response


# =============================================================
# config
# =============================================================

TOOL_NAME = "record_snippet_selection"
RETRIEVER_MAX_TOKENS = 4096


# =============================================================
# functions
# =============================================================

def _tool_definition() -> dict:
    """
    Build the Anthropic client tool definition for the recording step,
    derived from the `SnippetSelection` Pydantic schema.
    """
    return {
        "name": TOOL_NAME,
        "description": (
            "Record the chosen snippet IDs and framings, grouped by "
            "render_hint. Each pick must reference an `id` that exists "
            "in the snippet corpus, and a `framing` that matches either "
            "the canonical `framing` or one of the `variants[].framing` "
            "values for that snippet."
        ),
        "input_schema": SnippetSelection.model_json_schema(),
    }


def _enumerate_render_hints(snippets: dict) -> list[str]:
    """
    Distinct `render_hint` values present in the corpus, preserving the
    order they first appear so the model sees them deterministically.
    """
    seen: list[str] = []

    for snippet in snippets.get("snippets", []):
        hint = snippet.get("render_hint")
        if hint and hint not in seen:
            seen.append(hint)

    return seen


def _serialise_corpus(snippets: dict) -> str:
    """
    Stable JSON serialisation of the snippet corpus for the cached
    system block — sorted keys keep the cache key consistent across
    pipeline runs.
    """
    return json.dumps(snippets, indent=2, sort_keys=True)


def select_snippets(
    snippets: dict,
    jd_spec: JDSpec,
) -> SnippetSelection:
    """
    Ask the model to choose snippets per `render_hint` section, forcing
    a structured response via the `record_snippet_selection` tool.
    """
    sections = _enumerate_render_hints(snippets)
    sections_block = "\n".join(f"- {hint}" for hint in sections)

    try:
        response = client().messages.create(
            model=SONNET,
            max_tokens=RETRIEVER_MAX_TOKENS,
            system=[
                {"type": "text", "text": RETRIEVER_SYSTEM},
                cached_text_block(
                    "Snippet corpus (canonical):\n" + _serialise_corpus(snippets)
                ),
            ],
            tools=[_tool_definition()],
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=[
                {
                    "role": "user",
                    "content": RETRIEVER_USER.format(
                        jd_spec=jd_spec.model_dump_json(indent=2),
                        sections=sections_block,
                    ),
                }
            ],
        )
    except APIError as e:
        raise APIError(
            f"Retriever API call failed: {type(e).__name__}: {e}"
        ) from e

    return parse_forced_tool_response(
        response=response,
        model=SnippetSelection,
        tool_name=TOOL_NAME,
        stage="Retriever",
        max_tokens=RETRIEVER_MAX_TOKENS,
        max_tokens_name="RETRIEVER_MAX_TOKENS",
    )
