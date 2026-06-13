"""
Step 6 of the tailor pipeline: apply the `ReviewReport` to the profile
and return the revised `Profile` JSON.

No iteration: a single amendment pass is the contract for v1. If the
reviewer flags issues again on a future run, that is a problem for the
next iteration of the pipeline, not for this stage.
"""
# =============================================================
# packages
# =============================================================

from __future__ import annotations

import json

from anthropic import APIError

from .client import call_model
from .pricing import SONNET
from .prompts import AMENDER_SYSTEM, AMENDER_USER
from .schemas import ModelMetrics, ReviewReport, TailoredSections
from .tool_response import parse_forced_tool_response


# =============================================================
# config
# =============================================================

TOOL_NAME = "record_amended_profile"
AMENDER_MAX_TOKENS = 8192


# =============================================================
# functions
# =============================================================

def _tool_definition() -> dict:
    """
    Build the Anthropic client tool definition for the recording step.
    The output schema is `TailoredSections` — identical to the
    assembler — so the amender's result remains a partial that the
    orchestrator can merge with `Identity` to form the final profile.
    """
    return {
        "name": TOOL_NAME,
        "description": (
            "Record the revised tailored sections JSON after applying "
            "the review report. Preserve all unaffected fields verbatim."
        ),
        "input_schema": TailoredSections.model_json_schema(),
    }


def amend(
    sections: TailoredSections,
    report: ReviewReport,
) -> tuple[TailoredSections, ModelMetrics]:
    """
    Apply the review report to the tailored sections in a single model call.
    Schema is enforced via the forced tool call and re-validated by Pydantic
    on the way out. Returns the amended sections alongside this call's
    `ModelMetrics`.
    """
    try:
        response, metrics = call_model(
            model=SONNET,
            max_tokens=AMENDER_MAX_TOKENS,
            system=[
                {"type": "text", "text": AMENDER_SYSTEM},
                {
                    "type": "text",
                    "text": (
                        "TailoredSections schema (must match exactly):\n"
                        + json.dumps(
                            TailoredSections.model_json_schema(), indent=2
                        )
                    ),
                },
            ],
            tools=[_tool_definition()],
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=[
                {
                    "role": "user",
                    "content": AMENDER_USER.format(
                        report=report.model_dump_json(indent=2),
                        sections=sections.model_dump_json(indent=2),
                    ),
                }
            ],
        )
    except APIError as e:
        raise APIError(
            f"Amender API call failed: {type(e).__name__}: {e}"
        ) from e

    amended = parse_forced_tool_response(
        response=response,
        model=TailoredSections,
        tool_name=TOOL_NAME,
        stage="Amender",
        max_tokens=AMENDER_MAX_TOKENS,
        max_tokens_name="AMENDER_MAX_TOKENS",
    )

    return amended, metrics
