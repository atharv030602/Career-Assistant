from fastapi import APIRouter

from app.schemas import ReportResponse, ResumeStepRequest, SessionState, StartRequest
from app.services import session_service

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionState)
def start(req: StartRequest):
    snap = session_service.start(req.resume_text, req.target_roles)
    return SessionState.from_snapshot(snap)


@router.get("/{thread_id}", response_model=SessionState)
def get_status(thread_id: str):
    return SessionState.from_snapshot(session_service.status(thread_id))


@router.post("/{thread_id}/resume", response_model=SessionState)
def resume_step(thread_id: str, req: ResumeStepRequest):
    return SessionState.from_snapshot(session_service.resume(thread_id, req.feedback))


@router.get("/{thread_id}/report", response_model=ReportResponse)
def get_report(thread_id: str):
    snap = session_service.status(thread_id)
    return ReportResponse(
        thread_id=thread_id,
        status=snap["status"],
        report_markdown=session_service.report(thread_id),
    )
