from app.graph.agents import interview, job_match, learning_roadmap, resume_review, skill_gap, tools
from app.services import catalog
from app.services.skills import extract_skills, gap_analysis


def test_extract_skills(resume):
    found = extract_skills(resume)
    assert {"python", "fastapi", "docker", "ci/cd", "github actions"} <= found
    assert "langgraph" not in found


def test_gap_analysis():
    matched, missing = gap_analysis("I know python and docker", ["python", "docker", "kubernetes"])
    assert matched == ["python", "docker"]
    assert missing == ["kubernetes"]


def test_role_catalog_has_genai_engineer():
    r = catalog.find_role("GenAI Engineer")
    assert r and "langgraph" in r["core_skills"]


def test_resume_review_agent(resume):
    out = resume_review.run({"resume_text": resume, "ai_powered": False})
    rr = out["resume_review"]
    assert rr["red_flags"]  # weak openers present in the fixture
    assert rr["rewritten_bullets"]
    assert out["trace"][0].startswith("resume_review_agent")


def test_skill_gap_agent_scores_and_ranks(resume):
    out = skill_gap.run({"resume_text": resume, "target_roles": ["GenAI Engineer"]})
    assert 0 <= out["fit_score"] <= 100
    skills = [g["skill"] for g in out["skill_gaps"]]
    assert any(s.lower() in ("langgraph", "langchain", "rag") for s in skills)
    # high-importance gaps come first
    assert out["skill_gaps"][0]["importance"] == "high"


def test_job_match_agent(resume):
    out = job_match.run({"resume_text": resume, "target_roles": ["GenAI Engineer"], "revisions": 0})
    assert out["revisions"] == 1
    assert out["job_matches"]
    assert out["job_matches"][0]["match_score"] >= out["job_matches"][-1]["match_score"]


def test_learning_roadmap_respects_feedback():
    state = {
        "skill_gaps": [
            {"skill": "LangGraph", "importance": "high"},
            {"skill": "RAG", "importance": "high"},
            {"skill": "Kubernetes", "importance": "medium"},
        ],
        "human_feedback": {"skill_gap": {"weekly_hours": 10, "drop_skills": ["Kubernetes"]}},
    }
    out = learning_roadmap.run(state)
    rm = out["roadmap"]
    assert rm["weekly_hours"] == 10
    all_focus = [s.lower() for p in rm["phases"] for s in p["focus_skills"]]
    assert "kubernetes" not in all_focus
    assert rm["total_weeks"] > 0


def test_interview_agent_uses_high_gaps():
    out = interview.run(
        {"skill_gaps": [{"skill": "LangGraph", "importance": "high"}], "human_feedback": {}}
    )
    kit = out["interview_kit"]
    assert kit["questions"]
    assert any(q["kind"] == "behavioural" for q in kit["questions"])
    assert kit["star_answers"]


def test_effort_estimator_bounds():
    assert tools.effort_estimator("kubernetes") == 4
    assert tools.effort_estimator("git") == 1
