"""The eval harness itself must run (deterministic path, no keys)."""

from eval import metrics
from eval.cases import load_cases
from eval.harness import run_case
from eval.run_eval import evaluate


def test_dataset_loads():
    cases = load_cases()
    assert len(cases) >= 10
    assert all(c.resume_text and c.target_roles for c in cases)


def test_harness_completes_a_case():
    c = load_cases()[0]
    run = run_case(c.resume_text, c.target_roles, c.id)
    assert run.ok
    assert run.state["final_report"].startswith("# Career Assistant")
    assert not run.pending


def test_metrics_bounds():
    c = next(x for x in load_cases() if x.expect_job_match)
    run = run_case(c.resume_text, c.target_roles, c.id)
    assert metrics.routing_correct(run.state, c.expect_job_match) is True
    r = metrics.skill_gap_recall(run.state, c.expected_missing)
    assert r is None or 0.0 <= r <= 1.0
    assert 0.0 <= metrics.node_coverage(run.state) <= 1.0


def test_full_eval_report_shape():
    report = evaluate(use_judge=False)
    agg = report["aggregate"]
    assert agg["cases"] >= 10
    assert agg["completion_rate"] == 1.0
    assert 0.0 <= agg["mean_skill_gap_recall"] <= 1.0
    assert len(report["cases_detail"]) == agg["cases"]
