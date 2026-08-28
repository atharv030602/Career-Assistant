"""End-to-end graph run: start → HITL interrupt → resume → HITL → resume → done."""

import uuid

from app.graph.build import get_graph
from app.graph.state import initial_state


def _cfg(tid):
    return {"configurable": {"thread_id": tid}}


def test_full_run_with_two_hitl_stops(resume):
    graph = get_graph()
    tid = uuid.uuid4().hex
    graph.invoke(initial_state(tid, resume, ["GenAI Engineer"]), _cfg(tid))

    # 1st interrupt: before learning_roadmap
    snap = graph.get_state(_cfg(tid))
    assert "learning_roadmap" in snap.next
    assert snap.values["resume_review"] is not None
    assert snap.values["skill_gaps"]

    # approve gaps + set hours
    graph.update_state(_cfg(tid), {"human_feedback": {"skill_gap": {"weekly_hours": 8}}})
    graph.invoke(None, _cfg(tid))

    # 2nd interrupt: before interview
    snap = graph.get_state(_cfg(tid))
    assert "interview" in snap.next
    assert snap.values["roadmap"] is not None
    assert snap.values["roadmap"]["weekly_hours"] == 8

    graph.invoke(None, _cfg(tid))

    # done
    snap = graph.get_state(_cfg(tid))
    assert not snap.next
    assert snap.values["interview_kit"] is not None
    assert snap.values["final_report"].startswith("# Career Assistant")
    assert "resume_review_agent" in " ".join(snap.values["trace"])


def test_low_fit_routes_through_job_match():
    graph = get_graph()
    tid = uuid.uuid4().hex
    thin_resume = "I know Microsoft Word and Excel. I did a college project in HTML." * 2
    graph.invoke(initial_state(tid, thin_resume, ["GenAI Engineer"]), _cfg(tid))

    snap = graph.get_state(_cfg(tid))
    assert snap.values["fit_score"] < 55
    assert snap.values["job_matches"]  # job_match ran before the interrupt
    assert "learning_roadmap" in snap.next
