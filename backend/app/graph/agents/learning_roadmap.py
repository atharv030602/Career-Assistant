"""Learning Roadmap Agent — phased plan from the (human-approved) skill gaps.

Reads state["human_feedback"]["skill_gap"] which the HITL step may set:
  {"weekly_hours": int, "priority_skills": [str], "drop_skills": [str]}
"""

from __future__ import annotations

from app.graph.agents import tools
from app.graph.state import Roadmap, RoadmapPhase
from app.services.skills import SKILL_ALIASES, display_name

_PHASE_NAMES = ["Foundations", "Core build", "Depth & portfolio", "Interview polish"]


def _canon(name: str) -> str:
    n = name.strip().lower()
    if n in SKILL_ALIASES:
        return n
    for canon, aliases in SKILL_ALIASES.items():
        if n == canon or n in aliases or display_name(canon).lower() == n:
            return canon
    return n


def run(state: dict) -> dict:
    fb = (state.get("human_feedback") or {}).get("skill_gap", {})
    weekly_hours = int(fb.get("weekly_hours") or 6)
    drop = {_canon(s) for s in fb.get("drop_skills", [])}
    priority = [_canon(s) for s in fb.get("priority_skills", [])]

    gaps = state.get("skill_gaps") or []
    ordered = priority + [
        _canon(g["skill"])
        for g in gaps
        if _canon(g["skill"]) not in priority and g.get("importance") in ("high", "medium")
    ]
    skills = [s for s in dict.fromkeys(ordered) if s not in drop][:8]
    if not skills:
        skills = [_canon(g["skill"]) for g in gaps][:4] or ["langgraph", "rag"]

    # chunk skills into up to 3 build phases (+ a fixed polish phase)
    build_phases = min(3, max(1, (len(skills) + 1) // 2))
    per = max(1, len(skills) // build_phases)
    phases: list[RoadmapPhase] = []
    idx = 0
    for p in range(build_phases):
        chunk = skills[idx : idx + per] if p < build_phases - 1 else skills[idx:]
        idx += per
        if not chunk:
            continue
        weeks = max(tools.effort_estimator(s) for s in chunk)
        res: list[str] = []
        for s in chunk:
            res += tools.resource_catalog(s)[:1]
        phases.append(
            RoadmapPhase(
                name=_PHASE_NAMES[min(p, 2)],
                weeks=weeks,
                focus_skills=[display_name(s) for s in chunk],
                resources=res,
                milestone=f"Ship a small project using {', '.join(display_name(s) for s in chunk)}.",
            )
        )

    phases.append(
        RoadmapPhase(
            name=_PHASE_NAMES[3],
            weeks=1,
            focus_skills=["mock interviews", "system design"],
            resources=["Pramp / Exercism mock interviews", "System Design Primer (GitHub)"],
            milestone="Do 3 mock interviews; rewrite resume bullets with new metrics.",
        )
    )

    roadmap = Roadmap(
        total_weeks=sum(p.weeks for p in phases),
        weekly_hours=weekly_hours,
        phases=phases,
    )
    return {
        "roadmap": roadmap.model_dump(),
        "trace": [
            f"learning_roadmap_agent (skills={len(skills)}, "
            f"weeks={roadmap.total_weeks}, hrs/wk={weekly_hours})"
        ],
    }
