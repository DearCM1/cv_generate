"""
Pydantic schemas for inter-stage data and structured LLM outputs.
Also includes metrics tracking for website audit output.

Field names must comply with with the Jinja template at:
    render_pdf/templates/cv.html.
"""
# =============================================================
# packages
# =============================================================

from __future__ import annotations

from datetime import timedelta
from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field
from uuid import UUID
from uuid6 import uuid7


# =============================================================
# taxonomy
# =============================================================

# Job-role / field framing for RAG
Framing = Literal[
    "commercial",
    "data-engineer",
    "data-scientist",
    "physics-research",
    "strategy",
]


# =============================================================
# pipeline schemas
# =============================================================

class JDSpec(BaseModel):
    """
    Main data object for the Job Description, includes keywords
    and skills for CV ATS grading optimisation.
    """
    role_title: str
    seniority: str
    must_have_skills: list[str]
    nice_to_have_skills: list[str]
    ats_keywords: list[str] = Field(
        description="Verbatim phrases an ATS keyword-match will look for."
    )
    tone_signals: list[str]
    framing_hint: Framing


class SnippetPick(BaseModel):
    snippet_id: str
    framing: Framing


class SnippetSelection(BaseModel):
    """
    Per-render_hint ordered list of chosen snippets + variant framing.
    """
    picks_by_render_hint: dict[str, list[SnippetPick]]


class LinkedIn(BaseModel):
    label: str
    url: str


class Email(BaseModel):
    label: str
    url: str


class Contact(BaseModel):
    location: str
    phone: str
    email: Email
    linkedin: LinkedIn


class Education(BaseModel):
    institution: str
    qualification: str
    dates: str


class ExperienceEntry(BaseModel):
    title: str
    organisation: str
    dates: str
    bullets: list[str]


class PublicationPresentation(BaseModel):
    label: str
    text: str


class Skill(BaseModel):
    label: str
    text: str


class Identity(BaseModel):
    """
    Static identity fields that are constant across every tailored
    render. Loaded from `tailor/data/identity.json` and merged
    client-side into the final `Profile` — the LLM never sees these.
    """
    name: str
    credential: str
    contact: Contact
    education: list[Education]
    publications_presentations: list[PublicationPresentation]
    leadership: str


class TailoredSections(BaseModel):
    """
    The only fields the LLM produces. The assembler emits this from
    the JD spec and the retrieved snippets; the reviewer and amender
    operate on it; the orchestrator merges it with `Identity` to form
    the final `Profile`.
    """
    summary: str
    experience: list[ExperienceEntry]
    skills: list[Skill]


class Profile(BaseModel):
    """
    Main data object which renders into Jinja template.
    """
    name: str
    credential: str
    contact: Contact
    summary: str
    education: list[Education]
    experience: list[ExperienceEntry]
    publications_presentations: list[PublicationPresentation]
    leadership: str
    skills: list[Skill]


class WeakBullet(BaseModel):
    section: str
    index: int
    reason: str


class ReviewReport(BaseModel):
    missing_keywords: list[str]
    weak_bullets: list[WeakBullet]
    tone_issues: list[str]
    length_risk: Literal["low", "medium", "high"]


# =============================================================
# metric schemas
# =============================================================

#TODO Review whether this is best data structure for metrics

class CallTimeMetrics(BaseModel):
    """
    Time taken per LLM call.
    """
    start: AwareDatetime
    finish: AwareDatetime
    elapsed: timedelta

class RunTimeMetrics(BaseModel):
    """
    Overall runtime of orchestrator.py.
    """
    start: AwareDatetime
    finish: AwareDatetime
    elapsed: timedelta


class TokenCost(BaseModel):
    """
    Token cost breakdown per LLM call.
    """
    tokens_total: int
    tokens_in: int
    tokens_out: int
    tokens_reasoning: int


class ModelCost(BaseModel):
    """
    LLM total cost in dollars and tokens.
    """
    dollars: float
    tokens: TokenCost


class ModelMetrics(BaseModel):
    """
    Tracking key metrics for individual LLM call usage.
    """
    model: str
    runtime: CallTimeMetrics
    cost: ModelCost


class Metrics(BaseModel):
    """
    Master metrics object to push to website output.
    """
    id: UUID = Field(default_factory=uuid7)
    runtime: RunTimeMetrics
    model_metrics: list[ModelMetrics]
    job_spec: JDSpec
    snippet_selection: SnippetSelection
