"""Job Match Agent — when fit is low, surface better-fit roles from the catalog."""

from __future__ import annotations

from app.graph.agents import tools
from app.graph.state import JobMatch


def run(state: dict) -> dict:
    resume_text = state["resume_text"]
    targets = state.get("target_roles") or []
    ranked = tools.role_catalog_lookup(resume_text, exclude=targets)[:5]

    matches = [
        JobMatch(
            role=r["role"],
            match_score=r["match_score"],
            key_missing=r["key_missing"],
            rationale=(
                f"Your resume already covers ~{r['match_score']}% of this role's core skills"
                + (f"; still missing {', '.join(r['key_missing'])}." if r["key_missing"] else ".")
            ),
        )
        for r in ranked
        if r["match_score"] > 0
    ]

    return {
        "job_matches": [m.model_dump() for m in matches],
        "revisions": state.get("revisions", 0) + 1,
        "trace": [f"job_match_agent (suggested={len(matches)})"],
    }
