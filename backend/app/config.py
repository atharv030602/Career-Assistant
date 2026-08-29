"""Settings. Every AI feature is optional: with no provider key the graph
still runs end-to-end on deterministic agent logic."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Career Assistant"
    app_version: str = "0.1.0"
    environment: str = "local"
    log_level: str = "INFO"
    log_json: bool = False
    cors_origins: str = "http://localhost:8501"
    cors_origin_regex: str = r"https://.*\.streamlit\.app"

    # LLM provider — gemini | openai (openai covers OpenAI-compatible gateways
    # such as OpenRouter via OPENAI_BASE_URL).
    llm_provider: str = "openai"
    google_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = ""
    gemini_chat_model: str = "gemini-1.5-flash"
    openai_chat_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.2
    llm_timeout_seconds: int = 45

    # Graph checkpointer. "memory" is the default (SQLite needs
    # requirements-sqlite.txt, whose releases currently lag langgraph 1.x).
    checkpoint_backend: str = "memory"  # memory | sqlite
    checkpoint_db: str = ".careergraph.sqlite"

    # Observability
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "career-assistant"
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def active_api_key(self) -> str:
        return self.google_api_key if self.llm_provider.lower() == "gemini" else self.openai_api_key

    @property
    def ai_enabled(self) -> bool:
        return bool(self.active_api_key)


settings = Settings()
