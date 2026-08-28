"""Interview Agent — role-specific question bank + STAR answer scaffolds.

Reads state["human_feedback"]["roadmap"] which the HITL step may set:
  {"focus_topics": [str]}
"""

from __future__ import annotations

from app.graph.agents import tools
from app.graph.state import InterviewKit, InterviewQuestion
from app.services.skills import display_name

_BEHAVIOURAL = [
    "Tell me about a time you shipped something under a tight deadline.",
    "Describe a technical decision you got wrong and what you changed.",
    "How do you prioritise when everything is 'urgent'?",
]


def run(state: dict) -> dict:
    fb = (state.get("human_feedback") or {}).get("roadmap", {})
    focus = [s.lower() for s in fb.get("focus_topics", [])]

    gaps = state.get("skill_gaps") or []
    topics = focus or [g["skill"].lower() for g in gaps if g.get("importance") == "high"][:4]
    if not topics:
        topics = [g["skill"].lower() for g in gaps][:4] or ["python", "system design"]

    questions: list[InterviewQuestion] = []
    for t in topics:
        for q in tools.question_bank(display_name(t)):
            questions.append(InterviewQuestion(**q))
    questions.append(
        InterviewQuestion(
            topic="system design",
            question=f"Design a service that {('uses ' + display_name(topics[0])) if topics else 'serves ML predictions'} at 1k req/s.",
            kind="system-design",
        )
    )
    for b in _BEHAVIOURAL:
        questions.append(InterviewQuestion(topic="behavioural", question=b, kind="behavioural"))

    star = [
        tools.star_scaffolder("A project that shows " + display_name(topics[0]))
        if topics
        else tools.star_scaffolder("Your most impactful project"),
        tools.star_scaffolder("A time you improved reliability or performance"),
        tools.star_scaffolder("A time you learned a new tool fast to unblock the team"),
    ]

    kit = InterviewKit(questions=questions[:15], star_answers=star)
    return {
        "interview_kit": kit.model_dump(),
        "trace": [f"interview_agent (questions={len(kit.questions)})"],
    }
