"""
Step 2 of the tailor pipeline: turn raw job-description text into a
structured `JDSpec` (must-have skills, ATS keywords, tone signals, framing).
"""
# =============================================================
# packages
# =============================================================

from __future__ import annotations

from anthropic import APIError

from .client import DEFAULT_MAX_TOKENS, HAIKU, client
from .prompts import JD_ANALYSER_SYSTEM, JD_ANALYSER_USER
from .schemas import JDSpec
from .tool_response import parse_forced_tool_response


# =============================================================
# config
# =============================================================

TOOL_NAME = "record_jd_spec"


# =============================================================
# functions
# =============================================================

def _tool_definition() -> dict:
    """
    Build the Anthropic tool-use definition from the `JDSpec` Pydantic
    schema, so the model is forced to emit a structurally valid object.
    """
    return {
        "name": TOOL_NAME,
        "description": (
            "Record the structured job-description spec. The pipeline uses "
            "this to drive snippet retrieval and CV assembly."
        ),
        "input_schema": JDSpec.model_json_schema(),
    }


def analyse_jd(jd_text: str) -> JDSpec:
    """
    Call Claude with the JD text and force it to emit a `JDSpec` via a
    single tool call. Returns the validated Pydantic model.
    """
    try:
        response = client().messages.create(
            model=HAIKU,
            max_tokens=DEFAULT_MAX_TOKENS,
            system=JD_ANALYSER_SYSTEM,
            tools=[_tool_definition()],
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=[
                {
                    "role": "user",
                    "content": JD_ANALYSER_USER.format(jd_text=jd_text),
                }
            ],
        )
    except APIError as e:
        raise APIError(
            f"JD Analyser API call failed: {type(e).__name__}: {e}"
        ) from e

    return parse_forced_tool_response(
        response=response,
        model=JDSpec,
        tool_name=TOOL_NAME,
        stage="JD analyser",
        max_tokens=DEFAULT_MAX_TOKENS,
        max_tokens_name="DEFAULT_MAX_TOKENS",
    )
