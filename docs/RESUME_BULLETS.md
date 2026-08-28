# Resume bullets — Multi-Agent Career Assistant

Pick 3–4:

> **Multi-Agent Career Assistant** · *Python, LangGraph, LangChain, FastAPI, Streamlit, Docker, GitHub Actions*

- Built a **5-agent LangGraph application** (resume review, skill gap, job match, learning roadmap, interview prep) over a typed shared-state machine with conditional routing and a bounded revision loop.
- Implemented **human-in-the-loop checkpoints** using LangGraph `interrupt_before` + a checkpointer, exposed as a `thread_id`-keyed pause/resume REST lifecycle (`POST /sessions/{id}/resume`).
- Designed each agent with a **deterministic tool pipeline + optional LLM enrichment** that degrades gracefully — the full graph runs and is CI-tested with **zero API keys**.
- Added a **provider-agnostic LLM layer** (Gemini / OpenAI / OpenRouter via `OPENAI_BASE_URL`) and a checkpointer that falls back SQLite → in-memory.
- Shipped with **Docker Compose, GitHub Actions CI** (ruff + 15 pytest + image builds), structured request-id logging, and **LangSmith** tracing; deployable on Render + Streamlit Cloud.
- Modelled a **weighted skill-fit score** (core skills 2×) across multiple target roles and generated a phased, effort-estimated learning roadmap from human-approved gaps.

**Keywords earned:** LangGraph · multi-agent orchestration · state management ·
human-in-the-loop · tool calling · agent memory (checkpointer) · FastAPI ·
Streamlit · Docker · CI/CD · GitHub Actions · LangSmith · Python.

**Still to add (see PLAN.md):** `eval/` harness with LangSmith datasets +
LLM-as-judge metrics → unlocks the "agent evaluation" keyword as evidence.
