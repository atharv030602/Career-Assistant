"""Optional: push the dataset to LangSmith and run `evaluate()` with the same
metric functions as custom evaluators, so results show in the LangSmith UI.

    LANGSMITH_API_KEY=... python -m eval.langsmith_eval

No-op with a clear message if `langsmith` isn't installed or no key is set.
"""

from __future__ import annotations

import os

from app.core.llm import ai_enabled
from eval import metrics
from eval.cases import load_cases
from eval.harness import run_case

DATASET_NAME = "career-assistant-eval"


def _target(inputs: dict) -> dict:
    run = run_case(inputs["resume_text"], inputs["target_roles"], inputs.get("id", ""))
    return {"state": run.state, "ok": run.ok, "latency_ms": run.latency_ms}


def _eval_recall(run, example) -> dict:
    val = metrics.skill_gap_recall(
        run.outputs["state"], example.outputs.get("expected_missing", [])
    )
    return {"key": "skill_gap_recall", "score": val}


def _eval_routing(run, example) -> dict:
    ok = metrics.routing_correct(
        run.outputs["state"], example.outputs.get("expect_job_match", False)
    )
    return {"key": "routing_correct", "score": int(ok)}


def _eval_completed(run, example) -> dict:
    return {"key": "completed", "score": int(run.outputs["ok"])}


def main() -> None:
    if not os.environ.get("LANGSMITH_API_KEY"):
        print("LANGSMITH_API_KEY not set — skipping. Use `python -m eval.run_eval` for local eval.")
        return
    try:
        from langsmith import Client
        from langsmith.evaluation import evaluate
    except ImportError:
        print("`langsmith` not installed (pip install -r requirements-ai.txt). Skipping.")
        return

    client = Client()
    cases = load_cases()
    if not client.has_dataset(dataset_name=DATASET_NAME):
        ds = client.create_dataset(DATASET_NAME, description="Career Assistant graph eval")
        client.create_examples(
            inputs=[
                {"id": c.id, "resume_text": c.resume_text, "target_roles": c.target_roles}
                for c in cases
            ],
            outputs=[
                {"expected_missing": c.expected_missing, "expect_job_match": c.expect_job_match}
                for c in cases
            ],
            dataset_id=ds.id,
        )
        print(f"created dataset '{DATASET_NAME}' with {len(cases)} examples")

    results = evaluate(
        _target,
        data=DATASET_NAME,
        evaluators=[_eval_completed, _eval_routing, _eval_recall],
        experiment_prefix="career-assistant" + ("-ai" if ai_enabled() else "-deterministic"),
    )
    print("done —", results)


if __name__ == "__main__":
    main()
