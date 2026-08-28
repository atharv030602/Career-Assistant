def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    b = r.json()
    assert b["status"] == "ok"
    assert b["ai_enabled"] is False
    assert b["checkpoint_backend"] == "memory"


def test_session_lifecycle(client, resume):
    # start
    r = client.post(
        "/api/sessions", json={"resume_text": resume, "target_roles": ["GenAI Engineer"]}
    )
    assert r.status_code == 200
    s = r.json()
    tid = s["thread_id"]
    assert s["status"] == "interrupted"
    assert s["waiting_for"] == "learning_roadmap"
    assert s["feedback_key"] == "skill_gap"
    assert s["skill_gaps"]

    # status echoes the same
    assert client.get(f"/api/sessions/{tid}").json()["status"] == "interrupted"

    # resume past 1st HITL
    r = client.post(
        f"/api/sessions/{tid}/resume",
        json={"feedback": {"weekly_hours": 9, "drop_skills": []}},
    )
    s = r.json()
    assert s["status"] == "interrupted"
    assert s["waiting_for"] == "interview"
    assert s["roadmap"]["weekly_hours"] == 9

    # resume past 2nd HITL -> done
    s = client.post(
        f"/api/sessions/{tid}/resume", json={"feedback": {"focus_topics": ["LangGraph"]}}
    ).json()
    assert s["status"] == "done"
    assert s["interview_kit"]["questions"]

    # report
    rep = client.get(f"/api/sessions/{tid}/report").json()
    assert rep["status"] == "done"
    assert rep["report_markdown"].startswith("# Career Assistant")


def test_resume_before_start_is_404(client):
    r = client.post("/api/sessions/does-not-exist/resume", json={"feedback": {}})
    assert r.status_code == 404
    assert r.json()["error"]["type"] == "not_found"


def test_start_validation_error(client):
    r = client.post("/api/sessions", json={"resume_text": "too short", "target_roles": []})
    assert r.status_code == 422
