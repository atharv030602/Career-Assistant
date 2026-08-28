from fastapi import APIRouter

from app.config import settings
from app.graph.build import active_checkpointer_name
from app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        version=settings.app_version,
        environment=settings.environment,
        ai_enabled=settings.ai_enabled,
        llm_provider=settings.llm_provider,
        checkpoint_backend=active_checkpointer_name(),
    )
