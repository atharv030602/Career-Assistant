"""Skill Gap Agent — matched vs missing skills across target roles + a fit score."""

from __future__ import annotations

from app.graph.agents import tools
from app.graph.state import SkillGap
from app.services.catalog import find_role
from app.services.skills import display_name

_HIGH_WEIGHT = 2  # core skills count double toward the fit score


def run(state: dict) -> dict:
    resume_text = state["resume_text"]
    roles = state.get("target_roles") or ["GenAI Engineer"]

    per_role_cov: list[int] = []
    missing_importance: dict[str, str] = {}
    matched_any: set[str] = set()

    for role_name in roles:
        role = find_role(role_name)
        core = role["core_skills"] if role else []
        nice = role.get("nice_to_have", []) if role else []
        required = tools.jd_keyword_extractor(role_name) or core + nice

        res = tools.skill_matcher(resume_text, required)
        matched_any.update(res["matched"])

        # weighted coverage
        got = sum(_HIGH_WEIGHT if s in core else 1 for s in res["matched_canon"])
        total = sum(_HIGH_WEIGHT if s in core else 1 for s in required) or 1
        per_role_cov.append(round(got / total * 100))

        for s in res["missing_canon"]:
            imp = "high" if s in core else "medium" if s in nice else "low"
            # keep the strongest importance seen across roles
            if s not in missing_importance or _rank(imp) > _rank(missing_importance[s]):
                missing_importance[s] = imp

    fit_score = round(sum(per_role_cov) / len(per_role_cov)) if per_role_cov else 0

    gaps = [
        SkillGap(
            skill=display_name(s),
            importance=imp,
            present_in_resume=False,
            recommendation=f"Add '{display_name(s)}' via a project or role bullet, worded as the JD phrases it.",
        )
        for s, imp in sorted(missing_importance.items(), key=lambda kv: -_rank(kv[1]))
    ][:12]

    return {
        "skill_gaps": [g.model_dump() for g in gaps],
        "fit_score": fit_score,
        "trace": [f"skill_gap_agent (roles={len(roles)}, fit={fit_score}, gaps={len(gaps)})"],
    }


def _rank(importance: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(importance, 0)
