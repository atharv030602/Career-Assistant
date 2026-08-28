"""Deterministic skill vocabulary + resume/role matching.

Small, focused vocabulary (tech + GenAI roles). Aliases map surface forms to a
canonical skill name; matching is word-boundary regex.
"""

from __future__ import annotations

import re

SKILL_ALIASES: dict[str, list[str]] = {
    "python": ["python"],
    "javascript": ["javascript", "js"],
    "typescript": ["typescript", "ts"],
    "java": ["java"],
    "go": ["golang", "go lang"],
    "sql": ["sql"],
    "html": ["html", "html5"],
    "css": ["css", "css3"],
    "bash": ["bash", "shell scripting"],
    "react": ["react", "react.js", "reactjs"],
    "next.js": ["next.js", "nextjs"],
    "node.js": ["node.js", "nodejs", "node js"],
    "fastapi": ["fastapi"],
    "flask": ["flask"],
    "django": ["django"],
    "rest apis": ["rest api", "rest apis", "restful api"],
    "graphql": ["graphql"],
    "grpc": ["grpc"],
    "microservices": ["microservices", "microservice architecture"],
    "postgresql": ["postgresql", "postgres"],
    "mysql": ["mysql"],
    "mongodb": ["mongodb", "mongo"],
    "redis": ["redis"],
    "kafka": ["kafka"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "terraform": ["terraform"],
    "ansible": ["ansible"],
    "ci/cd": ["ci/cd", "ci cd", "continuous integration"],
    "github actions": ["github actions"],
    "aws": ["aws", "amazon web services"],
    "gcp": ["gcp", "google cloud"],
    "azure": ["azure"],
    "linux": ["linux"],
    "networking": ["networking", "tcp/ip"],
    "git": ["git", "version control"],
    "prometheus": ["prometheus"],
    "grafana": ["grafana"],
    "monitoring": ["monitoring", "alerting"],
    "observability": ["observability", "opentelemetry", "otel"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "pytorch": ["pytorch", "torch"],
    "tensorflow": ["tensorflow"],
    "statistics": ["statistics", "statistical"],
    "machine learning": ["machine learning", "ml"],
    "deep learning": ["deep learning"],
    "nlp": ["nlp", "natural language processing"],
    "data visualization": ["data visualization", "data viz", "matplotlib", "seaborn"],
    "spark": ["spark", "pyspark"],
    "airflow": ["airflow"],
    "etl": ["etl", "elt"],
    "data warehousing": ["data warehouse", "data warehousing", "snowflake", "bigquery"],
    "dbt": ["dbt"],
    "mlops": ["mlops"],
    "mlflow": ["mlflow"],
    "model deployment": ["model deployment", "model serving"],
    "feature stores": ["feature store", "feast"],
    "a/b testing": ["a/b testing", "ab testing", "experimentation"],
    "llm": ["llm", "large language model", "gpt", "generative ai", "genai"],
    "langchain": ["langchain"],
    "langgraph": ["langgraph"],
    "langsmith": ["langsmith"],
    "rag": ["rag", "retrieval augmented generation", "retrieval-augmented"],
    "embeddings": ["embeddings", "embedding model", "vector embeddings"],
    "vector databases": [
        "vector database",
        "vector db",
        "chromadb",
        "chroma",
        "pinecone",
        "faiss",
        "weaviate",
        "qdrant",
    ],
    "prompt engineering": ["prompt engineering", "prompting"],
    "tool calling": ["tool calling", "function calling", "tool use"],
    "agent evaluation": ["agent evaluation", "agent eval", "ragas", "llm-as-judge", "llm as judge"],
    "ai governance": ["ai governance", "responsible ai", "guardrails", "prompt injection"],
    "kubeflow": ["kubeflow"],
    "argocd": ["argocd", "argo cd"],
    "helm": ["helm"],
}

_DISPLAY = {
    "rest apis": "REST APIs",
    "ci/cd": "CI/CD",
    "github actions": "GitHub Actions",
    "aws": "AWS",
    "gcp": "GCP",
    "sql": "SQL",
    "html": "HTML",
    "css": "CSS",
    "nlp": "NLP",
    "llm": "LLM",
    "rag": "RAG",
    "mlops": "MLOps",
    "etl": "ETL",
    "a/b testing": "A/B testing",
    "node.js": "Node.js",
    "next.js": "Next.js",
    "fastapi": "FastAPI",
    "langchain": "LangChain",
    "langgraph": "LangGraph",
    "langsmith": "LangSmith",
    "ai governance": "AI governance",
}

_COMPILED = {
    canon: [re.compile(rf"(?<![a-z0-9]){re.escape(a)}(?![a-z0-9])", re.I) for a in aliases]
    for canon, aliases in SKILL_ALIASES.items()
}


def display_name(canon: str) -> str:
    return _DISPLAY.get(
        canon, canon.title() if canon.islower() and " " not in canon else canon.capitalize()
    )


def extract_skills(text: str) -> set[str]:
    low = text.lower()
    return {canon for canon, pats in _COMPILED.items() if any(p.search(low) for p in pats)}


def gap_analysis(resume_text: str, required: list[str]) -> tuple[list[str], list[str]]:
    """Return (matched, missing) canonical skill names for `required` vs the resume."""
    have = extract_skills(resume_text)
    matched = [s for s in required if s in have]
    missing = [s for s in required if s not in have]
    return matched, missing
