"""Render the final markdown report from graph state."""

from __future__ import annotations


def render(state: dict) -> str:
    roles = ", ".join(state.get("target_roles") or []) or "—"
    lines = [
        "# Career Assistant — Report",
        "",
        f"**Target role(s):** {roles}  ",
        f"**Fit score:** {state.get('fit_score', 0)}/100  ",
        f"**AI-powered:** {'yes' if state.get('ai_powered') else 'no (deterministic mode)'}",
        "",
    ]

    rr = state.get("resume_review") or {}
    if rr:
        lines += ["## 1. Resume review", ""]
        lines += ["**Strengths**"] + [f"- {s}" for s in rr.get("strengths", [])] + [""]
        lines += ["**Red flags**"] + [f"- {s}" for s in rr.get("red_flags", [])] + [""]
        if rr.get("rewritten_bullets"):
            lines += ["**Stronger bullets**"] + [f"- {b}" for b in rr["rewritten_bullets"]] + [""]

    gaps = state.get("skill_gaps") or []
    if gaps:
        lines += ["## 2. Skill gaps", ""]
        for g in gaps:
            lines.append(f"- **{g['skill']}** ({g['importance']}) — {g['recommendation']}")
        lines.append("")

    jm = state.get("job_matches") or []
    if jm:
        lines += ["## 3. Better-fit roles to consider", ""]
        for m in jm:
            lines.append(f"- **{m['role']}** — {m['match_score']}% match. {m['rationale']}")
        lines.append("")

    rm = state.get("roadmap") or {}
    if rm:
        lines += [
            "## 4. Learning roadmap",
            "",
            f"_{rm.get('total_weeks', 0)} weeks @ {rm.get('weekly_hours', 6)} h/week_",
            "",
        ]
        for i, p in enumerate(rm.get("phases", []), 1):
            lines.append(f"### Phase {i}: {p['name']} ({p['weeks']} wk)")
            lines.append(f"- Focus: {', '.join(p['focus_skills'])}")
            for r in p.get("resources", []):
                lines.append(f"- Resource: {r}")
            lines.append(f"- Milestone: {p['milestone']}")
            lines.append("")

    kit = state.get("interview_kit") or {}
    if kit:
        lines += ["## 5. Interview prep", "", "**Questions**"]
        for q in kit.get("questions", []):
            lines.append(f"- _({q['kind']})_ {q['question']}")
        lines.append("")
        if kit.get("star_answers"):
            lines += ["**STAR scaffolds**", ""] + [a + "\n" for a in kit["star_answers"]]

    if state.get("trace"):
        lines += ["---", "", "**Agent trace:** " + " → ".join(state["trace"])]

    return "\n".join(lines)
