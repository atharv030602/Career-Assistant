"""Resume Review Agent — strengths, red flags, stronger bullets."""

from __future__ import annotations

from app.core.llm import ai_enabled, llm_json
from app.graph.agents import tools
from app.graph.state import ResumeReview

_SYS = (
    "You are a senior technical recruiter. Give specific, honest resume feedback. "
    "Never invent experience. Return STRICT JSON only."
)


def _deterministic(resume_text: str) -> ResumeReview:
    r = tools.readability_scorer(resume_text)
    q = tools.quantification_checker(resume_text)
    strengths, flags = [], []

    if r["bullet_count"] >= 6:
        strengths.append("Uses bullet points for experience — ATS-parseable structure.")
    if r["quantified_bullets"] >= 3:
        strengths.append(f"{r['quantified_bullets']} bullets carry metrics — good impact signal.")
    if 350 <= r["word_count"] <= 950:
        strengths.append("Length is in the recruiter-friendly 350-950 word band.")

    if q["weak_openers"]:
        flags.append(
            f"{len(q['weak_openers'])} bullets open with weak phrasing (e.g. 'responsible for')."
        )
    if len(q["bullets_without_metrics"]) >= 3:
        flags.append(
            f"{len(q['bullets_without_metrics'])} bullets have no number — add %, counts, time or $."
        )
    if r["overlong_sentences"]:
        flags.append(f"{r['overlong_sentences']} very long sentences — split for scannability.")
    if r["word_count"] < 300:
        flags.append("Resume is short — likely under-selling scope and impact.")

    return ResumeReview(
        strengths=strengths or ["No structural strengths detected — see red flags."],
        red_flags=flags or ["No major red flags in structure/quantification."],
        rewritten_bullets=tools.bullet_rewriter(resume_text),
        readability_note=(
            f"{r['word_count']} words, {r['bullet_count']} bullets, "
            f"{r['quantified_bullets']} quantified."
        ),
    )


def run(state: dict) -> dict:
    resume_text = state["resume_text"]
    review = _deterministic(resume_text)
    ai_powered = False

    if ai_enabled():
        data = llm_json(
            _SYS,
            f'Resume:\n"""{resume_text[:6000]}"""\n\n'
            'Return JSON: {"strengths": [..], "red_flags": [..], '
            '"rewritten_bullets": ["<=5 concrete rewrites"]}',
        )
        if isinstance(data, dict) and data.get("strengths"):
            review = ResumeReview(
                strengths=[str(x) for x in data.get("strengths", [])][:6] or review.strengths,
                red_flags=[str(x) for x in data.get("red_flags", [])][:6] or review.red_flags,
                rewritten_bullets=[str(x) for x in data.get("rewritten_bullets", [])][:6]
                or review.rewritten_bullets,
                readability_note=review.readability_note,
            )
            ai_powered = True

    return {
        "resume_review": review.model_dump(),
        "ai_powered": state.get("ai_powered", False) or ai_powered,
        "trace": [f"resume_review_agent (ai={ai_powered})"],
    }
