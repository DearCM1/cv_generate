"""
Step 6 of the tailor pipeline: critique the assembled profile against
the `JDSpec` and emit a structured `ReviewReport`.

The reviewer is a single forced tool call — no web search, no retrieval.
It checks for missing ATS keywords, weak/generic bullets, tone mismatch,
and the risk of overflowing one A4 page. Output is consumed by the
amender stage immediately downstream.
"""
# =============================================================
# packages
# =============================================================

from __future__ import annotations

from anthropic import APIError

from .client import DEFAULT_MAX_TOKENS, SONNET, client
from .prompts import REVIEWER_SYSTEM, REVIEWER_USER
from .schemas import JDSpec, ReviewReport, TailoredSections
from .tool_response import parse_forced_tool_response


# =============================================================
# config
# =============================================================

TOOL_NAME = "record_review_report"


# =============================================================
# functions
# =============================================================

def _tool_definition() -> dict:
    """
    Build the Anthropic client tool definition for the recording step,
    derived from the `ReviewReport` Pydantic schema.
    """
    return {
        "name": TOOL_NAME,
        "description": (
            "Record the structured review report. `weak_bullets` must "
            "cite section name (e.g. 'experience[0].bullets') and index "
            "so the amender can act precisely."
        ),
        "input_schema": ReviewReport.model_json_schema(),
    }


def review(sections: TailoredSections, jd_spec: JDSpec) -> ReviewReport:
    """
    Call Sonnet to audit the freshly assembled tailored sections against
    the JD, forcing a structured `ReviewReport` via a single tool call.
    """
    try:
        response = client().messages.create(
            model=SONNET,
            max_tokens=DEFAULT_MAX_TOKENS,
            system=REVIEWER_SYSTEM,
            tools=[_tool_definition()],
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=[
                {
                    "role": "user",
                    "content": REVIEWER_USER.format(
                        jd_spec=jd_spec.model_dump_json(indent=2),
                        sections=sections.model_dump_json(indent=2),
                    ),
                }
            ],
        )
    except APIError as e:
        raise APIError(
            f"Reviewer API call failed: {type(e).__name__}: {e}"
        ) from e

    return parse_forced_tool_response(
        response=response,
        model=ReviewReport,
        tool_name=TOOL_NAME,
        stage="Reviewer",
        max_tokens=DEFAULT_MAX_TOKENS,
        max_tokens_name="DEFAULT_MAX_TOKENS",
    )
