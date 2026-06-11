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

ASSEMBLER_SYSTEM = """You assemble the tailored sections of a CV, only \
`summary`, `experience[]`, and `skills[]`. Static identity fields (name, \
contact, education, publications, leadership) are merged in later and are \
not your concern. The output schema is in the next system block; match it \
exactly.

For each role you include in `experience[]`:
 - Take `title`, `organisation`, and `dates` verbatim from the supplied \
`roles` metadata (pick a title from that role's `title_variants` that best \
fits the JD).
 - Output no more than 4 bullets.
 - Treat the chosen snippets as relevant context, not mandatory text to fully \
 exhaust. Use only the points that best support the JD and omit anything that \
 does not strengthen the role.
 - Compose `bullets` from the chosen snippets only; preserve their numbers \
 and substantive claims. Light edits for flow are fine, but do not fabricate \
 metrics or invent experience that is not in the snippets.
 - You may use reasonably synonymous wording or directly implied adjacent \
 experience when it is a normal operational consequence of the snippet evidence. \
 For example, experience deploying AWS Lambda functions can reasonably imply \
 familiarity with surrounding AWS tooling such as IAM, EventBridge, the AWS \
 Console, or SAM CLI. Do not stretch this into unrelated or speculative claims.

For `skills[]`, draw label/text from the skill snippets selected for the \
`skills[]` render hint; keep to 4 or fewer groups. Do not add skills that are \
unsupported by the snippets, except where a skill is reasonably synonymous with \
or directly implied by the evidenced work.

For `summary`, write no more than 2 sentences that speak to the JD and \
naturally \
include the ATS keywords, grounded in the supplied snippets. JDs frequently \
embed company context (business focus, values, tech stack), lean on that \
when phrasing the summary so it speaks to the employer's environment.

HTML is allowed only where needed for safe text rendering or notation, such as \
escaped symbols and, if genuinely necessary, `<sup>` or `<sub>`. Do not use \
HTML for visual formatting such as bold, strong, italic, or emphasis tags. No \
script tags. Avoid em dashes and en dashes; use commas, full stops, or plain \
hyphens only when essential."""

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
'experience[0].bullets', index 2). Treat these as hard constraints: summary \
must be no more than 2 sentences, each experience role must have no more than \
4 bullets, and em dashes or en dashes should be avoided."""

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
verbatim. HTML is allowed only where needed for safe text rendering or \
notation, such as escaped symbols and, if genuinely necessary, `<sup>` or \
`<sub>`. Do not use HTML for visual formatting such as bold, strong, italic, \
or emphasis tags. No script tags. Preserve these constraints in the revised \
output: summary must be no more than 2 sentences, each experience role must \
have no more than 4 bullets, chosen snippets are relevant context rather than \
text that must all be used, and em dashes or en dashes should be avoided. Do \
not add unsupported skills or experience, but reasonably synonymous wording or \
directly implied adjacent experience is allowed where the snippet evidence \
clearly supports it, such as AWS Lambda work implying nearby AWS operational \
tooling."""

AMENDER_USER = """Review report:
{report}

Current tailored sections:
{sections}"""
