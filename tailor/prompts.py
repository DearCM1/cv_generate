"""
All prompt strings for the tailor pipeline live here.

Inline HTML in profile fields is rendered with Jinja's `| safe`
filter — the assembler prompts must remind the model that 
user-controlled HTML must be sanitised.
"""
# =============================================================
# packages
# =============================================================

from __future__ import annotations


# =============================================================
# Step 2: Job Description Analyser
# =============================================================

JD_ANALYSER_SYSTEM = """You analyse job descriptions for a CV-tailoring \
pipeline. Extract a structured `JDSpec` describing what an ATS will scan for \
and what tone the employer expects. Be concrete: prefer verbatim phrases \
from the JD over paraphrases for `ats_keywords`."""

JD_ANALYSER_USER = "Job description:\n\n{jd_text}"


# =============================================================
# Step 3: Retrieval
# =============================================================

RETRIEVER_SYSTEM = """You select experience snippets for a tailored CV. The \
snippet corpus is in the next system block. For each `render_hint` section \
the user names, pick the snippets that best match the JD and choose the \
`framing` variant that fits the tone. JDs frequently embed company context \
(business focus, values, tech stack) — treat that as part of the JD signal. \
Respect one-page A4 limits: no more than 5 bullets per experience role, no \
more than 4 skill groups."""

RETRIEVER_USER = """JD spec:
{jd_spec}

Sections to fill (render_hint values present in the corpus):
{sections}

Return a `SnippetSelection` mapping each render_hint to an ordered list of \
`{{snippet_id, framing}}`."""


# =============================================================
# Step 4: Assembler / CV Builder
# =============================================================

ASSEMBLER_SYSTEM = """You assemble the tailored sections of a CV — only \
`summary`, `experience[]`, and `skills[]`. Static identity fields (name, \
contact, education, publications, leadership) are merged in later and are \
not your concern. The output schema is in the next system block; match it \
exactly.

For each role you include in `experience[]`:
 - Take `title`, `organisation`, and `dates` verbatim from the supplied \
`roles` metadata (pick a title from that role's `title_variants` that best \
fits the JD).
 - Compose `bullets` from the chosen snippets only — preserve their numbers \
and substantive claims; light edits for flow are fine, but do not fabricate \
metrics or invent experience that is not in the snippets.

For `skills[]`, draw label/text from the skill snippets selected for the \
`skills[]` render hint; keep to 4 or fewer groups.

For `summary`, write 2-3 sentences that speak to the JD and naturally \
include the ATS keywords, grounded in the supplied snippets. JDs frequently \
embed company context (business focus, values, tech stack) — lean on that \
when phrasing the summary so it speaks to the employer's environment.

HTML is allowed only in `skills[].text`; keep tags simple (`<strong>`). \
No script tags."""

ASSEMBLER_USER = """JD spec:
{jd_spec}

Role metadata (source of truth for experience[].title/organisation/dates):
{roles}

Selected snippets (grouped by render_hint, with id, chosen framing, text, \
skills, metrics):
{snippets}"""


# =============================================================
# Step 5: Reviewer
# =============================================================

REVIEWER_SYSTEM = """You critique the tailored sections of a CV (summary, \
experience, skills) against a JD spec. Identify missing ATS keywords, weak \
or generic bullets, tone mismatches, and the risk of overflowing one A4 \
page. Be specific: cite section and bullet index (e.g. \
'experience[0].bullets', index 2)."""

REVIEWER_USER = """JD spec:
{jd_spec}

Tailored sections to review:
{sections}"""

# =============================================================
# Step 6: Amender
# =============================================================

AMENDER_SYSTEM = """You apply a `ReviewReport` to the tailored sections of \
a CV (summary, experience, skills) and return the revised sections JSON. \
Make only the changes the report requests; preserve all unaffected fields \
verbatim. HTML is allowed only in `skills[].text`; keep tags simple \
(`<strong>`). No script tags."""

AMENDER_USER = """Review report:
{report}

Current tailored sections:
{sections}"""
