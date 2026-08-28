"""Deterministic tools shared by the agents. Pure functions, no LLM, unit-testable."""

from __future__ import annotations

import re

from app.services import catalog
from app.services.skills import display_name, extract_skills, gap_analysis

_QUANT_RE = re.compile(r"(\d+%|\$\d[\d,]*|\b\d[\d,]{1,}\+?\b)")
_BULLET_RE = re.compile(r"^\s*([-*•]|\d+[.)])\s+(.*)$", re.MULTILINE)
_WEAK_STARTS = ("responsible for", "worked on", "helped with", "involved in", "tasked with")
_ACTION_VERBS = (
    "Built",
    "Led",
    "Designed",
    "Shipped",
    "Reduced",
    "Improved",
    "Automated",
    "Scaled",
)


def readability_scorer(resume_text: str) -> dict:
    words = resume_text.split()
    bullets = _BULLET_RE.findall(resume_text)
    quantified = len(_QUANT_RE.findall(resume_text))
    long_sentences = sum(1 for s in re.split(r"[.!?\n]", resume_text) if len(s.split()) > 34)
    return {
        "word_count": len(words),
        "bullet_count": len(bullets),
        "quantified_bullets": quantified,
        "overlong_sentences": long_sentences,
    }


def quantification_checker(resume_text: str) -> dict:
    lines = [m[1].strip() for m in _BULLET_RE.findall(resume_text)]
    weak = [ln for ln in lines if ln.lower().startswith(_WEAK_STARTS)]
    no_metric = [ln for ln in lines if not _QUANT_RE.search(ln)]
    return {
        "weak_openers": weak[:6],
        "bullets_without_metrics": no_metric[:8],
        "total_bullets": len(lines),
    }


def bullet_rewriter(resume_text: str) -> list[str]:
    """Deterministic 'stronger bullet' suggestions from the weakest existing lines."""
    lines = [m[1].strip() for m in _BULLET_RE.findall(resume_text)]
    weak = [ln for ln in lines if ln.lower().startswith(_WEAK_STARTS) or not _QUANT_RE.search(ln)]
    out = []
    for i, ln in enumerate(weak[:5]):
        verb = _ACTION_VERBS[i % len(_ACTION_VERBS)]
        core = re.sub(
            r"^(responsible for|worked on|helped with|involved in|tasked with)\s+",
            "",
            ln,
            flags=re.I,
        )
        out.append(f"{verb} {core.rstrip('.')} — add a metric (%, count, time saved, $).")
    return out


def jd_keyword_extractor(role_name: str) -> list[str]:
    return catalog.required_skills(role_name)


def skill_matcher(resume_text: str, required: list[str]) -> dict:
    matched, missing = gap_analysis(resume_text, required)
    return {
        "matched": [display_name(s) for s in matched],
        "missing": [display_name(s) for s in missing],
        "matched_canon": matched,
        "missing_canon": missing,
        "coverage": round(len(matched) / len(required) * 100) if required else 0,
    }


def role_catalog_lookup(resume_text: str, exclude: list[str] | None = None) -> list[dict]:
    """Rank catalog roles by how well the resume already covers their core skills."""
    exclude_l = {e.lower() for e in (exclude or [])}
    have = extract_skills(resume_text)
    ranked = []
    for role in catalog.roles():
        if role["role"].lower() in exclude_l:
            continue
        core = role["core_skills"]
        covered = [s for s in core if s in have]
        score = round(len(covered) / len(core) * 100) if core else 0
        missing = [display_name(s) for s in core if s not in have]
        ranked.append({"role": role["role"], "match_score": score, "key_missing": missing[:4]})
    ranked.sort(key=lambda r: r["match_score"], reverse=True)
    return ranked


def effort_estimator(skill: str) -> int:
    """Rough weeks to job-ready for a skill at ~6 h/week."""
    heavy = {
        "kubernetes",
        "pytorch",
        "spark",
        "machine learning",
        "deep learning",
        "terraform",
        "langgraph",
    }
    light = {"git", "bash", "html", "css", "rest apis", "prompt engineering", "github actions"}
    s = skill.lower()
    return 4 if s in heavy else 1 if s in light else 2


def resource_catalog(skill: str) -> list[str]:
    return catalog.resources_for(skill)


def question_bank(skill: str) -> list[dict]:
    generic = [
        {
            "topic": skill,
            "question": f"Walk me through a project where you used {skill}. What was hard?",
            "kind": "technical",
        },
        {
            "topic": skill,
            "question": f"How would you debug a production issue involving {skill}?",
            "kind": "technical",
        },
    ]
    return generic


def star_scaffolder(theme: str) -> str:
    return (
        f"**{theme}**\n"
        f"- Situation: <team/product context, 1 sentence>\n"
        f"- Task: <what you specifically owned>\n"
        f"- Action: <2-3 concrete steps you took, name the tools>\n"
        f"- Result: <quantified outcome — %, latency, cost, adoption>"
    )
