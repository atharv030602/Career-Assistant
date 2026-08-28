import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
try:
    API = st.secrets.get("API_BASE_URL", os.environ.get("API_BASE_URL", "http://localhost:8000/api"))
except Exception:
    API = os.environ.get("API_BASE_URL", "http://localhost:8000/api")

INK, PANEL, LINE = "#12181b", "#1a2226", "#2a353b"
TEAL, AMBER, RED, MUTED = "#6fe7c4", "#e8a94c", "#e2685c", "#8fa3a6"

st.set_page_config(page_title="Career Assistant", page_icon="🧭", layout="centered")
st.markdown(
    f"""<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
    .stApp {{ background:{INK}; color:#e9eeee; }}
    .block-container {{ max-width: 820px; padding-top: 2.5rem; }}
    .eyebrow {{ font-family:'IBM Plex Mono',monospace; font-size:12px; letter-spacing:.14em; color:{TEAL}; }}
    .headline {{ font-family:'Space Grotesk',sans-serif; font-size:32px; font-weight:600; margin:8px 0; }}
    .sub {{ color:{MUTED}; font-size:15px; margin-bottom:18px; }}
    .chip {{ display:inline-block; font-family:'IBM Plex Mono',monospace; font-size:12px; padding:4px 9px;
        border-radius:3px; margin:3px 4px 3px 0; border:1px solid; }}
    .h {{ color:{RED}; border-color:{RED}; }} .m {{ color:{AMBER}; border-color:{AMBER}; }}
    .l {{ color:{MUTED}; border-color:{MUTED}; }}
    .step {{ font-family:'IBM Plex Mono',monospace; font-size:12px; letter-spacing:.08em; color:{MUTED}; }}
    </style>""",
    unsafe_allow_html=True,
)

ss = st.session_state
ss.setdefault("snap", None)
ss.setdefault("tid", None)


def post_resume(feedback: dict) -> None:
    try:
        r = requests.post(f"{API}/sessions/{ss.tid}/resume", json={"feedback": feedback}, timeout=180)
        r.raise_for_status()
        ss.snap = r.json()
        st.rerun()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed: {e}")


def chips(gaps: list[dict]) -> str:
    order = {"high": "h", "medium": "m", "low": "l"}
    return "".join(
        f'<span class="chip {order.get(g["importance"], "l")}">{g["skill"]} · {g["importance"]}</span>'
        for g in gaps
    )


st.markdown(
    '<div class="eyebrow">CAREER ASSISTANT — LANGGRAPH · 5 AGENTS · HUMAN-IN-THE-LOOP</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="headline">A multi-agent plan from resume to offer.</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub">Resume Review → Skill Gap → (Job Match) → Learning Roadmap → Interview Prep. '
    "You approve the skill gaps and pick the timeline; the graph pauses for you at each checkpoint.</div>",
    unsafe_allow_html=True,
)

# ── Start ────────────────────────────────────────────────────────────────
if ss.snap is None:
    resume_text = st.text_area("Resume", height=260, placeholder="Paste your resume…")
    roles = st.text_input("Target role(s) — comma separated", value="GenAI Engineer")
    if st.button("Run the agents", type="primary", use_container_width=True, disabled=len(resume_text) < 30):
        with st.spinner("intake → resume_review → skill_gap …"):
            try:
                r = requests.post(
                    f"{API}/sessions",
                    json={
                        "resume_text": resume_text,
                        "target_roles": [x.strip() for x in roles.split(",") if x.strip()],
                    },
                    timeout=180,
                )
                r.raise_for_status()
                ss.snap = r.json()
                ss.tid = ss.snap["thread_id"]
                st.rerun()
            except requests.exceptions.RequestException as e:
                st.error(f"Failed: {e}")

# ── Running session ─────────────────────────────────────────────────────
else:
    snap = ss.snap
    st.caption(
        f"Session {ss.tid[:12]} · status: **{snap['status']}** · "
        f"fit score: **{snap['fit_score']}/100** · AI: {snap['ai_powered']}"
    )
    st.markdown("**Agent trace:** " + " → ".join(snap.get("trace", [])))

    rr = snap.get("resume_review")
    if rr:
        with st.expander("1 · Resume Review"):
            st.markdown("**Strengths**\n" + "\n".join(f"- {s}" for s in rr["strengths"]))
            st.markdown("**Red flags**\n" + "\n".join(f"- {s}" for s in rr["red_flags"]))
            if rr.get("rewritten_bullets"):
                st.markdown("**Stronger bullets**\n" + "\n".join(f"- {b}" for b in rr["rewritten_bullets"]))

    if snap.get("skill_gaps"):
        with st.expander("2 · Skill Gaps", expanded=snap["waiting_for"] == "learning_roadmap"):
            st.markdown(chips(snap["skill_gaps"]), unsafe_allow_html=True)

    if snap.get("job_matches"):
        with st.expander("2b · Better-fit roles"):
            for m in snap["job_matches"]:
                st.markdown(f"- **{m['role']}** — {m['match_score']}% · {m['rationale']}")

    rm = snap.get("roadmap")
    if rm:
        with st.expander("3 · Learning Roadmap", expanded=snap["waiting_for"] == "interview"):
            st.caption(f"{rm['total_weeks']} weeks @ {rm['weekly_hours']} h/week")
            for i, p in enumerate(rm["phases"], 1):
                st.markdown(
                    f"**Phase {i}: {p['name']} ({p['weeks']} wk)** — {', '.join(p['focus_skills'])}"
                )
                for res in p["resources"]:
                    st.markdown(f"  - {res}")
                st.markdown(f"  - _Milestone:_ {p['milestone']}")

    kit = snap.get("interview_kit")
    if kit:
        with st.expander("4 · Interview Prep", expanded=snap["status"] == "done"):
            for q in kit["questions"]:
                st.markdown(f"- _({q['kind']})_ {q['question']}")
            for a in kit.get("star_answers", []):
                st.markdown(a)

    if snap["status"] == "interrupted" and snap["waiting_for"] == "learning_roadmap":
        st.markdown('<div class="step">CHECKPOINT — approve skill gaps & set your pace</div>', unsafe_allow_html=True)
        hrs = st.slider("Hours per week", 2, 20, 6)
        all_skills = [g["skill"] for g in snap["skill_gaps"]]
        drop = st.multiselect("Drop any of these skills", all_skills)
        prio = st.multiselect("Prioritise first", all_skills)
        if st.button("Approve → build roadmap", type="primary", use_container_width=True):
            post_resume({"weekly_hours": hrs, "drop_skills": drop, "priority_skills": prio})

    elif snap["status"] == "interrupted" and snap["waiting_for"] == "interview":
        st.markdown('<div class="step">CHECKPOINT — pick interview focus topics</div>', unsafe_allow_html=True)
        topics = st.multiselect(
            "Focus topics",
            [g["skill"] for g in snap["skill_gaps"]],
            default=[g["skill"] for g in snap["skill_gaps"] if g["importance"] == "high"][:3],
        )
        if st.button("Continue → interview kit", type="primary", use_container_width=True):
            post_resume({"focus_topics": topics})

    elif snap["status"] == "done":
        try:
            rep = requests.get(f"{API}/sessions/{ss.tid}/report", timeout=60).json()
            st.download_button(
                "Download report (.md)", rep["report_markdown"], "career_report.md",
                use_container_width=True,
            )
            with st.expander("Full report", expanded=True):
                st.markdown(rep["report_markdown"])
        except requests.exceptions.RequestException as e:
            st.error(f"Report failed: {e}")

    if st.button("Start over"):
        ss.snap = None
        ss.tid = None
        st.rerun()

st.markdown(
    f'<div style="text-align:center;margin-top:40px;font-family:\'IBM Plex Mono\',monospace;'
    f'font-size:11px;color:{MUTED};">Built by Atharv — LangGraph · FastAPI · Streamlit</div>',
    unsafe_allow_html=True,
)
