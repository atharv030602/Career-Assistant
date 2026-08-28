"""Non-agent graph nodes: intake, router, synthesize."""

from __future__ import annotations

from app.graph.report import render

FIT_THRESHOLD = 55


def intake(state: dict) -> dict:
    roles = [r.strip() for r in (state.get("target_roles") or []) if r.strip()]
    roles = list(dict.fromkeys(roles)) or ["GenAI Engineer"]
    resume = (state.get("resume_text") or "").strip()
    return {
        "target_roles": roles,
        "resume_text": resume,
        "trace": [f"intake (roles={roles})"],
    }


def route_after_gap(state: dict) -> str:
    """Conditional edge: low fit and not yet revised -> job_match; else -> roadmap."""
    if state.get("fit_score", 0) < FIT_THRESHOLD and state.get("revisions", 0) == 0:
        return "job_match"
    return "learning_roadmap"


def synthesize(state: dict) -> dict:
    return {"final_report": render(state), "trace": ["synthesize (report rendered)"]}
