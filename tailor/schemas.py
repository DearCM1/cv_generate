"""
Pydantic schemas for inter-stage data and structured LLM outputs.

Field names must comply with with the Jinja template at:
    render_pdf/templates/cv.html.
"""
# =============================================================
# packages
# =============================================================

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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
# schemas
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


class CompanyContext(BaseModel):
    name: str
    business_focus: str
    tech_signals: list[str]
    values: list[str]
    recent_initiatives: list[str]
    sources: list[str] = Field(
        default_factory=list,
        description="URLs surfaced by web_search that informed this context.",
    )


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


class Contact(BaseModel):
    location: str
    phone: str
    email: str
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
