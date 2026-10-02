from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_request_meta
from app.api.v1.routes.company_setup.crud_factory import require_tenant_scope
from app.core.config import get_settings
from app.core.database import get_db
from app.core.enums import PermissionAction, PermissionModule
from app.core.exceptions import ForbiddenError, ValidationError
from app.core.permissions import require_permission
from app.core.tenant import TenantContext
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.recruitment import (
    CandidateCreate,
    CandidateDocumentResponse,
    CandidateResponse,
    CandidateStartOnboardingResponse,
    CandidateUpdate,
    InterviewCreate,
    InterviewFeedbackCreate,
    InterviewFeedbackResponse,
    InterviewResponse,
    InterviewUpdate,
    JobBoardConnectionResponse,
    JobBoardConnectionUpsert,
    JobBoardPostingResponse,
    JobBoardPostRequest,
    JobBoardSyncResponse,
    JobOpeningCreate,
    JobOpeningResponse,
    JobOpeningUpdate,
    OfferApproveRequest,
    OfferLetterCreate,
    OfferLetterResponse,
    OfferLetterUpdate,
)
from app.services.recruitment_service import RecruitmentService
from app.services.tenant_setting_service import TenantSettingService
from app.schemas.company_settings import CareerPageResponse, CareerPageUpdate

router = APIRouter(prefix="/recruitment", tags=["Recruitment"])
settings = get_settings()


def check_recruitment_permission(ctx: TenantContext, current_user: User, action: PermissionAction, db: Session) -> None:
    if current_user.is_super_admin:
        return
    if not ctx.role:
        raise ForbiddenError("Role context missing from token")
    require_permission(ctx.role, PermissionModule.RECRUITMENT, action, db=db, role_id=ctx.role_id)


def get_service(db: Session = Depends(get_db)) -> RecruitmentService:
    return RecruitmentService(db)


@router.post("/jobs", response_model=APIResponse[JobOpeningResponse], status_code=201)
def create_job(
    request: Request,
    payload: JobOpeningCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_job(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Job opening created")


@router.get("/jobs", response_model=PaginatedResponse[JobOpeningResponse])
def list_jobs(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_jobs(ctx.tenant_id, page=page, page_size=page_size, search=search, status=status, is_active=is_active)


@router.get("/jobs/{job_id}", response_model=APIResponse[JobOpeningResponse])
def get_job(
    job_id: UUID,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=service.get_job(ctx.tenant_id, job_id))


@router.put("/jobs/{job_id}", response_model=APIResponse[JobOpeningResponse])
def update_job(
    job_id: UUID,
    request: Request,
    payload: JobOpeningUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_job(ctx.tenant_id, job_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Job opening updated")


@router.post("/candidates", response_model=APIResponse[CandidateResponse], status_code=201)
def create_candidate(
    request: Request,
    payload: CandidateCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_candidate(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Candidate created")


@router.get("/candidates", response_model=PaginatedResponse[CandidateResponse])
def list_candidates(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    job_opening_id: Optional[UUID] = Query(default=None),
    current_stage: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_candidates(
        ctx.tenant_id,
        page=page,
        page_size=page_size,
        search=search,
        job_opening_id=job_opening_id,
        current_stage=current_stage,
        status=status,
    )


@router.put("/candidates/{candidate_id}", response_model=APIResponse[CandidateResponse])
def update_candidate(
    candidate_id: UUID,
    request: Request,
    payload: CandidateUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_candidate(
        ctx.tenant_id, candidate_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Candidate updated")


@router.post(
    "/candidates/{candidate_id}/start-onboarding",
    response_model=APIResponse[CandidateStartOnboardingResponse],
    status_code=201,
)
def start_candidate_onboarding(
    candidate_id: UUID,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.MANAGE, db)
    data = service.start_onboarding(
        ctx.tenant_id, candidate_id, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Onboarding started")


@router.post("/candidates/{candidate_id}/documents", response_model=APIResponse[CandidateDocumentResponse], status_code=201)
async def upload_candidate_document(
    candidate_id: UUID,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
    file: UploadFile = File(...),
    document_type: str = Form(..., min_length=1, max_length=100),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.CREATE, db)
    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise ValidationError(f"File size exceeds {settings.max_upload_size_mb}MB limit")
    data = service.upload_candidate_document(
        ctx.tenant_id,
        candidate_id,
        document_type=document_type,
        file_name=file.filename or "document",
        content=content,
        actor_id=current_user.id,
        meta=get_request_meta(request),
    )
    return APIResponse(data=data, message="Document uploaded")


@router.post("/interviews", response_model=APIResponse[InterviewResponse], status_code=201)
def create_interview(
    request: Request,
    payload: InterviewCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_interview(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Interview scheduled")


@router.get("/interviews", response_model=PaginatedResponse[InterviewResponse])
def list_interviews(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    candidate_id: Optional[UUID] = Query(default=None),
    job_opening_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_interviews(
        ctx.tenant_id,
        page=page,
        page_size=page_size,
        candidate_id=candidate_id,
        job_opening_id=job_opening_id,
        status=status,
    )


@router.put("/interviews/{interview_id}", response_model=APIResponse[InterviewResponse])
def update_interview(
    interview_id: UUID,
    request: Request,
    payload: InterviewUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.update_interview(
        ctx.tenant_id, interview_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Interview updated")


@router.post("/offers", response_model=APIResponse[OfferLetterResponse], status_code=201)
def create_offer(
    request: Request,
    payload: OfferLetterCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.create_offer(ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Offer letter created")


@router.get("/offers", response_model=PaginatedResponse[OfferLetterResponse])
def list_offers(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    candidate_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.VIEW, db)
    return service.list_offers(ctx.tenant_id, page=page, page_size=page_size, candidate_id=candidate_id, status=status)


@router.put("/offers/{offer_id}/approve", response_model=APIResponse[OfferLetterResponse])
def approve_offer(
    offer_id: UUID,
    request: Request,
    payload: OfferApproveRequest = OfferApproveRequest(),
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.APPROVE, db)
    data = service.approve_offer(
        ctx.tenant_id, offer_id, actor_id=current_user.id, payload=payload, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Offer approved")


@router.get("/career-page", response_model=APIResponse[CareerPageResponse])
def get_career_page(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=TenantSettingService(db).get_career_page(ctx.tenant_id))


@router.put("/career-page", response_model=APIResponse[CareerPageResponse])
def update_career_page(
    payload: CareerPageUpdate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = TenantSettingService(db).update_career_page(ctx.tenant_id, payload)
    return APIResponse(data=data, message="Career page updated")


@router.get("/interview-feedbacks", response_model=APIResponse[list[InterviewFeedbackResponse]])
def list_interview_feedbacks(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=service.list_interview_feedbacks(ctx.tenant_id))


@router.post(
    "/interviews/{interview_id}/feedback",
    response_model=APIResponse[InterviewFeedbackResponse],
    status_code=201,
)
def submit_interview_feedback(
    interview_id: UUID,
    request: Request,
    payload: InterviewFeedbackCreate,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.submit_interview_feedback(
        ctx.tenant_id,
        interview_id,
        payload,
        actor_id=current_user.id,
        meta=get_request_meta(request),
    )
    return APIResponse(data=data, message="Feedback submitted")


@router.put("/offers/{offer_id}/send", response_model=APIResponse[OfferLetterResponse])
def send_offer(
    offer_id: UUID,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.send_offer(
        ctx.tenant_id, offer_id, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Offer sent")


@router.get("/job-boards/connections", response_model=APIResponse[list[JobBoardConnectionResponse]])
def list_job_board_connections(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(data=service.list_job_board_connections(ctx.tenant_id))


@router.put(
    "/job-boards/connections/{platform}",
    response_model=APIResponse[JobBoardConnectionResponse],
)
def upsert_job_board_connection(
    platform: str,
    request: Request,
    payload: JobBoardConnectionUpsert,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.MANAGE, db)
    data = service.upsert_job_board_connection(
        ctx.tenant_id,
        platform,
        payload,
        actor_id=current_user.id,
        meta=get_request_meta(request),
    )
    return APIResponse(data=data, message="Job board connection saved")


@router.post(
    "/job-boards/connections/{platform}/disconnect",
    response_model=APIResponse[JobBoardConnectionResponse],
)
def disconnect_job_board(
    platform: str,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.MANAGE, db)
    data = service.disconnect_job_board(
        ctx.tenant_id, platform, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Job board disconnected")


@router.get("/job-boards/postings", response_model=APIResponse[list[JobBoardPostingResponse]])
def list_job_board_postings(
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
    platform: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    job_opening_id: Optional[UUID] = Query(default=None),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.VIEW, db)
    return APIResponse(
        data=service.list_job_board_postings(
            ctx.tenant_id,
            platform=platform,
            status=status,
            job_opening_id=job_opening_id,
        )
    )


@router.post("/job-boards/postings", response_model=APIResponse[list[JobBoardPostingResponse]], status_code=201)
def post_job_to_boards(
    request: Request,
    payload: JobBoardPostRequest,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.CREATE, db)
    data = service.post_job_to_boards(
        ctx.tenant_id, payload, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Job posted to selected boards")


@router.post("/job-boards/sync", response_model=APIResponse[JobBoardSyncResponse])
def sync_job_boards(
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.MANAGE, db)
    data = service.sync_job_boards(ctx.tenant_id, actor_id=current_user.id, meta=get_request_meta(request))
    return APIResponse(data=data, message="Job boards synced")


@router.put("/job-boards/postings/{posting_id}/close", response_model=APIResponse[JobBoardPostingResponse])
def close_job_board_posting(
    posting_id: UUID,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_scope),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RecruitmentService = Depends(get_service),
):
    check_recruitment_permission(ctx, current_user, PermissionAction.EDIT, db)
    data = service.close_job_board_posting(
        ctx.tenant_id, posting_id, actor_id=current_user.id, meta=get_request_meta(request)
    )
    return APIResponse(data=data, message="Job board posting closed")
