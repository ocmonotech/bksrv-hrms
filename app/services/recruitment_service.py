from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.recruitment import (
    Candidate,
    CandidateDocument,
    CandidateStageHistory,
    Interview,
    InterviewFeedback,
    JobBoardConnection,
    JobBoardPosting,
    JobOpening,
    OfferLetter,
    Referral,
)
from app.models.employee import Employee
from app.models.user import User
from app.models.onboarding import OnboardingChecklist, OnboardingTask, ProbationReview
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.onboarding_repository import OnboardingChecklistRepository, OnboardingTaskRepository
from app.repositories.recruitment_repository import (
    CandidateRepository,
    InterviewFeedbackRepository,
    InterviewRepository,
    JobBoardConnectionRepository,
    JobBoardPostingRepository,
    JobOpeningRepository,
    OfferLetterRepository,
)
from app.schemas.common import PaginatedResponse
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
from app.services.audit_service import AuditService
from app.services.company_setup.base import _coerce_payload
from app.utils.file_storage import candidate_document_relative_path, save_upload_file
from app.utils.pagination import total_pages

JOB_BOARD_PLATFORMS: dict[str, str] = {
    "naukri": "Naukri",
    "indeed": "Indeed",
    "linkedin": "LinkedIn",
    "career_page": "Career Page",
}

EXTERNAL_BOARD_URLS: dict[str, str] = {
    "naukri": "https://www.naukri.com/job-listings-",
    "indeed": "https://in.indeed.com/viewjob?jk=",
    "linkedin": "https://www.linkedin.com/jobs/view/",
}

DEFAULT_ONBOARDING_TASKS: list[tuple[str, str]] = [
    ("Welcome email & pre-joining kit", "Send welcome pack and joining instructions"),
    ("Collect joining documents", "ID proof, address proof, education certificates"),
    ("IT access & email setup", "Create email, SSO, and system access"),
    ("HR orientation session", "Policies, benefits, and payroll briefing"),
    ("Team introduction", "Introduce to manager and team members"),
    ("Probation goals setup", "Define 30-60-90 day objectives"),
]

MOCK_BOARD_APPLICANTS: dict[str, list[dict[str, str]]] = {
    "naukri": [
        {"first_name": "Arjun", "last_name": "Patel", "email": "arjun.patel.naukri@example.com", "mobile": "+919800001001"},
        {"first_name": "Divya", "last_name": "Sharma", "email": "divya.sharma.naukri@example.com", "mobile": "+919800001002"},
        {"first_name": "Karthik", "last_name": "Menon", "email": "karthik.menon.naukri@example.com", "mobile": "+919800001003"},
    ],
    "indeed": [
        {"first_name": "Sarah", "last_name": "Thomas", "email": "sarah.thomas.indeed@example.com", "mobile": "+919800002001"},
        {"first_name": "Imran", "last_name": "Khan", "email": "imran.khan.indeed@example.com", "mobile": "+919800002002"},
    ],
    "linkedin": [
        {"first_name": "Ananya", "last_name": "Rao", "email": "ananya.rao.linkedin@example.com", "mobile": "+919800003001"},
        {"first_name": "Michael", "last_name": "DSouza", "email": "michael.d.linkedin@example.com", "mobile": "+919800003002"},
    ],
    "career_page": [
        {"first_name": "Priya", "last_name": "Nambiar", "email": "priya.nambiar.careers@example.com", "mobile": "+919800004001"},
    ],
}


class RecruitmentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.job_repo = JobOpeningRepository(db)
        self.candidate_repo = CandidateRepository(db)
        self.interview_repo = InterviewRepository(db)
        self.feedback_repo = InterviewFeedbackRepository(db)
        self.offer_repo = OfferLetterRepository(db)
        self.job_board_conn_repo = JobBoardConnectionRepository(db)
        self.job_board_posting_repo = JobBoardPostingRepository(db)
        self.employee_repo = EmployeeRepository(db)
        self.checklist_repo = OnboardingChecklistRepository(db)
        self.task_repo = OnboardingTaskRepository(db)
        self.audit = AuditService(db)

    def create_job(
        self, tenant_id: UUID, payload: JobOpeningCreate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> JobOpeningResponse:
        if self.job_repo.get_by_code(tenant_id, payload.code.upper()):
            raise ConflictError(f"Job opening '{payload.code}' already exists")
        data = _coerce_payload(payload.model_dump())
        entity = JobOpening(
            tenant_id=str(tenant_id),
            code=data["code"].upper(),
            status="draft",
            created_by=str(actor_id),
            updated_by=str(actor_id),
            **{k: v for k, v in data.items() if k != "code"},
        )
        self.job_repo.add(entity)
        self._log("recruitment.job.create", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return JobOpeningResponse.model_validate(entity)

    def list_jobs(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> PaginatedResponse[JobOpeningResponse]:
        extra = [JobOpening.status == status] if status else None
        items, total = self.job_repo.list_paginated(
            tenant_id, page=page, page_size=page_size, search=search, is_active=is_active, extra_filters=extra
        )
        return PaginatedResponse(
            data=[JobOpeningResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def get_job(self, tenant_id: UUID, job_id: UUID) -> JobOpeningResponse:
        entity = self.job_repo.get_by_id(job_id, tenant_id)
        if not entity:
            raise NotFoundError("Job opening not found")
        return JobOpeningResponse.model_validate(entity)

    def update_job(
        self, tenant_id: UUID, job_id: UUID, payload: JobOpeningUpdate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> JobOpeningResponse:
        entity = self.job_repo.get_by_id(job_id, tenant_id)
        if not entity:
            raise NotFoundError("Job opening not found")
        data = payload.model_dump(exclude_unset=True)
        if data.get("status") == "open" and not entity.published_at:
            entity.published_at = datetime.now(timezone.utc)
        for key, value in data.items():
            setattr(entity, key, value)
        entity.updated_by = str(actor_id)
        self._log("recruitment.job.update", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return JobOpeningResponse.model_validate(entity)

    def create_candidate(
        self, tenant_id: UUID, payload: CandidateCreate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> CandidateResponse:
        if not self.job_repo.get_by_id(payload.job_opening_id, tenant_id):
            raise NotFoundError("Job opening not found")
        data = _coerce_payload(payload.model_dump())
        entity = Candidate(
            tenant_id=str(tenant_id),
            current_stage="applied",
            status="active",
            created_by=str(actor_id),
            updated_by=str(actor_id),
            **data,
        )
        self.candidate_repo.add(entity)
        self._record_stage(tenant_id, entity, None, "applied", actor_id)
        if payload.referred_by_employee_id:
            self.db.add(
                Referral(
                    tenant_id=str(tenant_id),
                    candidate_id=str(entity.id),
                    referrer_employee_id=str(payload.referred_by_employee_id),
                    created_by=str(actor_id),
                    updated_by=str(actor_id),
                )
            )
        self._log("recruitment.candidate.create", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return CandidateResponse.model_validate(entity)

    def list_candidates(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        job_opening_id: Optional[UUID] = None,
        current_stage: Optional[str] = None,
        status: Optional[str] = None,
    ) -> PaginatedResponse[CandidateResponse]:
        items, total = self.candidate_repo.list_filtered(
            tenant_id,
            page=page,
            page_size=page_size,
            search=search,
            job_opening_id=job_opening_id,
            current_stage=current_stage,
            status=status,
        )
        return PaginatedResponse(
            data=[CandidateResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def update_candidate(
        self, tenant_id: UUID, candidate_id: UUID, payload: CandidateUpdate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> CandidateResponse:
        entity = self.candidate_repo.get_by_id(candidate_id, tenant_id)
        if not entity:
            raise NotFoundError("Candidate not found")
        data = payload.model_dump(exclude_unset=True)
        old_stage = entity.current_stage
        if "current_stage" in data and data["current_stage"] != old_stage:
            self._record_stage(tenant_id, entity, old_stage, data["current_stage"], actor_id)
        for key, value in data.items():
            setattr(entity, key, value)
        entity.updated_by = str(actor_id)
        self._log("recruitment.candidate.update", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return CandidateResponse.model_validate(entity)

    def upload_candidate_document(
        self,
        tenant_id: UUID,
        candidate_id: UUID,
        *,
        document_type: str,
        file_name: str,
        content: bytes,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> CandidateDocumentResponse:
        candidate = self.candidate_repo.get_by_id(candidate_id, tenant_id)
        if not candidate:
            raise NotFoundError("Candidate not found")
        rel_path = candidate_document_relative_path(
            str(tenant_id), str(candidate_id), document_type, file_name
        )
        save_upload_file(rel_path, content)
        doc = CandidateDocument(
            tenant_id=str(tenant_id),
            candidate_id=str(candidate_id),
            document_type=document_type,
            file_name=file_name,
            file_path=rel_path,
            created_by=str(actor_id),
            updated_by=str(actor_id),
        )
        self.db.add(doc)
        if document_type.lower() == "resume":
            candidate.resume_path = rel_path
        self._log("recruitment.candidate.document", tenant_id, actor_id, str(candidate_id), meta)
        self.db.commit()
        self.db.refresh(doc)
        return CandidateDocumentResponse.model_validate(doc)

    def create_interview(
        self, tenant_id: UUID, payload: InterviewCreate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> InterviewResponse:
        if not self.candidate_repo.get_by_id(payload.candidate_id, tenant_id):
            raise NotFoundError("Candidate not found")
        data = _coerce_payload(payload.model_dump())
        entity = Interview(
            tenant_id=str(tenant_id),
            status="scheduled",
            created_by=str(actor_id),
            updated_by=str(actor_id),
            **data,
        )
        self.interview_repo.add(entity)
        self._log("recruitment.interview.create", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return InterviewResponse.model_validate(entity)

    def list_interviews(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        candidate_id: Optional[UUID] = None,
        job_opening_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> PaginatedResponse[InterviewResponse]:
        items, total = self.interview_repo.list_filtered(
            tenant_id, page=page, page_size=page_size, candidate_id=candidate_id, job_opening_id=job_opening_id, status=status
        )
        return PaginatedResponse(
            data=[InterviewResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def update_interview(
        self, tenant_id: UUID, interview_id: UUID, payload: InterviewUpdate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> InterviewResponse:
        entity = self.interview_repo.get_by_id(interview_id, tenant_id)
        if not entity:
            raise NotFoundError("Interview not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(entity, key, value)
        entity.updated_by = str(actor_id)
        self._log("recruitment.interview.update", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return InterviewResponse.model_validate(entity)

    def create_offer(
        self, tenant_id: UUID, payload: OfferLetterCreate, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> OfferLetterResponse:
        if not self.candidate_repo.get_by_id(payload.candidate_id, tenant_id):
            raise NotFoundError("Candidate not found")
        data = _coerce_payload(payload.model_dump())
        entity = OfferLetter(
            tenant_id=str(tenant_id),
            status="draft",
            created_by=str(actor_id),
            updated_by=str(actor_id),
            **data,
        )
        self.offer_repo.add(entity)
        self._log("recruitment.offer.create", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return OfferLetterResponse.model_validate(entity)

    def list_offers(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        candidate_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> PaginatedResponse[OfferLetterResponse]:
        items, total = self.offer_repo.list_filtered(
            tenant_id, page=page, page_size=page_size, candidate_id=candidate_id, status=status
        )
        return PaginatedResponse(
            data=[OfferLetterResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages(total, page_size),
        )

    def approve_offer(
        self,
        tenant_id: UUID,
        offer_id: UUID,
        *,
        actor_id: UUID,
        payload: Optional[OfferApproveRequest] = None,
        meta: Optional[dict] = None,
    ) -> OfferLetterResponse:
        entity = self.offer_repo.get_by_id(offer_id, tenant_id)
        if not entity:
            raise NotFoundError("Offer letter not found")
        if entity.status not in ("draft", "pending_approval"):
            raise ValidationError("Offer cannot be approved in current status")
        entity.status = "approved"
        entity.approver_id = str(actor_id)
        entity.approved_at = datetime.now(timezone.utc)
        entity.updated_by = str(actor_id)
        self._log("recruitment.offer.approve", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return OfferLetterResponse.model_validate(entity)

    def send_offer(
        self, tenant_id: UUID, offer_id: UUID, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> OfferLetterResponse:
        entity = self.offer_repo.get_by_id(offer_id, tenant_id)
        if not entity:
            raise NotFoundError("Offer letter not found")
        if entity.status != "approved":
            raise ValidationError("Only approved offers can be sent")
        entity.status = "sent"
        entity.sent_at = datetime.now(timezone.utc)
        entity.updated_by = str(actor_id)
        self._log("recruitment.offer.send", tenant_id, actor_id, str(entity.id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return OfferLetterResponse.model_validate(entity)

    def list_interview_feedbacks(self, tenant_id: UUID) -> list[InterviewFeedbackResponse]:
        items = self.feedback_repo.list_for_tenant(tenant_id)
        return [self._map_feedback(fb) for fb in items]

    def submit_interview_feedback(
        self,
        tenant_id: UUID,
        interview_id: UUID,
        payload: InterviewFeedbackCreate,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> InterviewFeedbackResponse:
        interview = self.interview_repo.get_by_id(interview_id, tenant_id)
        if not interview:
            raise NotFoundError("Interview not found")
        if self.feedback_repo.get_by_interview(tenant_id, interview_id):
            raise ConflictError("Feedback already submitted for this interview")

        feedback_payload = {
            "comments": payload.comments,
            "technical_skills": payload.technical_skills,
            "communication": payload.communication,
            "culture_fit": payload.culture_fit,
        }
        entity = InterviewFeedback(
            tenant_id=str(tenant_id),
            interview_id=str(interview_id),
            reviewer_id=str(actor_id),
            rating=payload.rating,
            recommendation=payload.recommendation,
            feedback=json.dumps(feedback_payload),
            status="submitted",
            created_by=str(actor_id),
            updated_by=str(actor_id),
        )
        self.feedback_repo.add(entity)
        if interview.status == "scheduled":
            interview.status = "completed"
            interview.updated_by = str(actor_id)
        self._log("recruitment.interview.feedback", tenant_id, actor_id, str(interview_id), meta)
        self.db.commit()
        self.db.refresh(entity)
        return self._map_feedback(entity)

    def list_job_board_connections(self, tenant_id: UUID) -> list[JobBoardConnectionResponse]:
        stored = {c.platform: c for c in self.job_board_conn_repo.list_for_tenant(tenant_id)}
        results: list[JobBoardConnectionResponse] = []
        for platform, label in JOB_BOARD_PLATFORMS.items():
            conn = stored.get(platform)
            if platform == "career_page" and not conn:
                results.append(
                    JobBoardConnectionResponse(
                        platform=platform,
                        label=label,
                        status="connected",
                        account_name="Internal career page",
                    )
                )
                continue
            if conn:
                results.append(
                    JobBoardConnectionResponse(
                        platform=conn.platform,
                        label=label,
                        status=conn.status,
                        account_name=conn.account_name,
                        api_key_hint=conn.api_key_hint,
                        last_synced_at=conn.last_synced_at,
                    )
                )
            else:
                results.append(
                    JobBoardConnectionResponse(platform=platform, label=label, status="disconnected")
                )
        return results

    def upsert_job_board_connection(
        self,
        tenant_id: UUID,
        platform: str,
        payload: JobBoardConnectionUpsert,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> JobBoardConnectionResponse:
        if platform not in JOB_BOARD_PLATFORMS:
            raise ValidationError(f"Unsupported platform: {platform}")
        if platform == "career_page":
            raise ValidationError("Career page connection is managed automatically")

        entity = self.job_board_conn_repo.get_by_platform(tenant_id, platform)
        if not entity:
            entity = JobBoardConnection(
                tenant_id=str(tenant_id),
                platform=platform,
                created_by=str(actor_id),
                updated_by=str(actor_id),
            )
            self.job_board_conn_repo.add(entity)

        entity.account_name = payload.account_name or entity.account_name
        if payload.api_key:
            entity.api_key_hint = f"...{payload.api_key[-4:]}" if len(payload.api_key) >= 4 else "****"
        entity.status = "connected" if entity.account_name else "pending"
        entity.updated_by = str(actor_id)
        self._log("recruitment.job_board.connect", tenant_id, actor_id, platform, meta)
        self.db.commit()
        self.db.refresh(entity)
        return JobBoardConnectionResponse(
            platform=entity.platform,
            label=JOB_BOARD_PLATFORMS[platform],
            status=entity.status,
            account_name=entity.account_name,
            api_key_hint=entity.api_key_hint,
            last_synced_at=entity.last_synced_at,
        )

    def disconnect_job_board(
        self, tenant_id: UUID, platform: str, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> JobBoardConnectionResponse:
        if platform not in JOB_BOARD_PLATFORMS or platform == "career_page":
            raise ValidationError("This platform cannot be disconnected")
        entity = self.job_board_conn_repo.get_by_platform(tenant_id, platform)
        if not entity:
            return JobBoardConnectionResponse(
                platform=platform, label=JOB_BOARD_PLATFORMS[platform], status="disconnected"
            )
        entity.status = "disconnected"
        entity.api_key_hint = None
        entity.updated_by = str(actor_id)
        self._log("recruitment.job_board.disconnect", tenant_id, actor_id, platform, meta)
        self.db.commit()
        self.db.refresh(entity)
        return JobBoardConnectionResponse(
            platform=entity.platform,
            label=JOB_BOARD_PLATFORMS[platform],
            status=entity.status,
            account_name=entity.account_name,
            last_synced_at=entity.last_synced_at,
        )

    def list_job_board_postings(
        self,
        tenant_id: UUID,
        *,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        job_opening_id: Optional[UUID] = None,
    ) -> list[JobBoardPostingResponse]:
        items = self.job_board_posting_repo.list_filtered(
            tenant_id, platform=platform, status=status, job_opening_id=job_opening_id
        )
        return [self._map_posting(tenant_id, item) for item in items]

    def post_job_to_boards(
        self,
        tenant_id: UUID,
        payload: JobBoardPostRequest,
        *,
        actor_id: UUID,
        meta: Optional[dict] = None,
    ) -> list[JobBoardPostingResponse]:
        job = self.job_repo.get_by_id(payload.job_opening_id, tenant_id)
        if not job:
            raise NotFoundError("Job opening not found")
        if job.status not in ("approved", "published"):
            raise ValidationError("Job must be approved or published before posting to job boards")

        now = datetime.now(timezone.utc)
        connections = {c.platform: c for c in self.job_board_conn_repo.list_for_tenant(tenant_id)}
        created_postings: list[JobBoardPosting] = []

        for platform in payload.platforms:
            if platform not in JOB_BOARD_PLATFORMS:
                raise ValidationError(f"Unsupported platform: {platform}")

            if platform != "career_page":
                conn = connections.get(platform)
                if not conn or conn.status != "connected":
                    raise ValidationError(f"{JOB_BOARD_PLATFORMS[platform]} is not connected")

            posting = self.job_board_posting_repo.get_by_job_and_platform(
                tenant_id, payload.job_opening_id, platform
            )
            if not posting:
                posting = JobBoardPosting(
                    tenant_id=str(tenant_id),
                    job_opening_id=str(payload.job_opening_id),
                    platform=platform,
                    created_by=str(actor_id),
                    updated_by=str(actor_id),
                )
                self.job_board_posting_repo.add(posting)

            external_id = posting.external_job_id or f"{platform[:2].upper()}-{uuid4().hex[:8]}"
            posting.external_job_id = external_id
            posting.status = "live"
            posting.posted_at = posting.posted_at or now
            posting.last_synced_at = now
            posting.error_message = None
            posting.updated_by = str(actor_id)

            if platform == "career_page":
                posting.external_url = None
            else:
                base = EXTERNAL_BOARD_URLS.get(platform, "")
                posting.external_url = f"{base}{external_id}"

            if job.status != "published" and platform == "career_page":
                job.status = "published"
                job.published_at = now
                job.updated_by = str(actor_id)

            created_postings.append(posting)

        self._log("recruitment.job_board.post", tenant_id, actor_id, str(payload.job_opening_id), meta)
        self.db.commit()
        return [self._map_posting(tenant_id, posting) for posting in created_postings]

    def sync_job_boards(
        self, tenant_id: UUID, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> JobBoardSyncResponse:
        now = datetime.now(timezone.utc)
        connections_updated = 0
        postings_updated = 0

        for conn in self.job_board_conn_repo.list_for_tenant(tenant_id):
            if conn.status == "connected":
                conn.last_synced_at = now
                conn.updated_by = str(actor_id)
                connections_updated += 1

        for posting in self.job_board_posting_repo.list_filtered(tenant_id, status="live"):
            posting.last_synced_at = now
            posting.updated_by = str(actor_id)
            postings_updated += 1

        applicants_imported = self._import_job_board_applicants(tenant_id, actor_id)

        self._log("recruitment.job_board.sync", tenant_id, actor_id, "all", meta)
        self.db.commit()
        return JobBoardSyncResponse(
            synced_at=now,
            connections_updated=connections_updated,
            postings_updated=postings_updated,
            applicants_imported=applicants_imported,
        )

    def start_onboarding(
        self, tenant_id: UUID, candidate_id: UUID, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> CandidateStartOnboardingResponse:
        candidate = self.candidate_repo.get_by_id(candidate_id, tenant_id)
        if not candidate:
            raise NotFoundError("Candidate not found")
        if candidate.current_stage not in ("selected", "offered", "joined"):
            raise ValidationError("Candidate must be selected or offered before starting onboarding")

        if candidate.employee_id:
            employee = self.employee_repo.get_by_id(UUID(str(candidate.employee_id)), tenant_id)
            if not employee:
                raise NotFoundError("Linked employee record not found")
            _, total = self.task_repo.list_filtered(
                tenant_id, employee_id=UUID(str(employee.id)), page_size=1
            )
            return CandidateStartOnboardingResponse(
                candidate_id=candidate_id,
                employee_id=UUID(str(employee.id)),
                employee_code=employee.employee_code,
                onboarding_tasks_created=total,
                message="Onboarding already started for this candidate",
            )

        if self.employee_repo.get_by_email(tenant_id, candidate.email):
            raise ConflictError("An employee with this email already exists")

        job = self.job_repo.get_by_id(UUID(str(candidate.job_opening_id)), tenant_id)
        joining_date = date.today()
        offers, _ = self.offer_repo.list_filtered(
            tenant_id, candidate_id=candidate_id, status="sent", page_size=1
        )
        if not offers:
            offers, _ = self.offer_repo.list_filtered(
                tenant_id, candidate_id=candidate_id, status="approved", page_size=1
            )
        if offers:
            joining_date = offers[0].joining_date

        employee = Employee(
            tenant_id=str(tenant_id),
            employee_code=self.employee_repo.next_employee_code(tenant_id),
            first_name=candidate.first_name,
            last_name=candidate.last_name,
            email=candidate.email.lower(),
            mobile=candidate.mobile,
            department_id=job.department_id if job else None,
            designation_id=job.designation_id if job else None,
            branch_id=job.branch_id if job else None,
            joining_date=joining_date,
            employment_type="full_time",
            status="active",
            created_by=str(actor_id),
            updated_by=str(actor_id),
        )
        self.employee_repo.add(employee)

        checklist = self._get_or_create_default_checklist(tenant_id, actor_id)
        tasks_created = 0
        due_base = joining_date or date.today()
        for idx, (task_name, description) in enumerate(DEFAULT_ONBOARDING_TASKS):
            self.task_repo.add(
                OnboardingTask(
                    tenant_id=str(tenant_id),
                    checklist_id=str(checklist.id),
                    employee_id=str(employee.id),
                    task_name=task_name,
                    description=description,
                    due_date=due_base + timedelta(days=7 + idx * 3),
                    sequence=idx,
                    status="pending",
                    created_by=str(actor_id),
                    updated_by=str(actor_id),
                )
            )
            tasks_created += 1

        probation_end = joining_date + timedelta(days=180) if joining_date else date.today() + timedelta(days=180)
        self.db.add(
            ProbationReview(
                tenant_id=str(tenant_id),
                employee_id=str(employee.id),
                review_date=probation_end,
                outcome="pending",
                status="draft",
                created_by=str(actor_id),
                updated_by=str(actor_id),
            )
        )

        old_stage = candidate.current_stage
        candidate.employee_id = str(employee.id)
        candidate.current_stage = "joined"
        candidate.updated_by = str(actor_id)
        if old_stage != "joined":
            self._record_stage(tenant_id, candidate, old_stage, "joined", actor_id)

        self._log("recruitment.candidate.start_onboarding", tenant_id, actor_id, str(candidate_id), meta)
        self.db.commit()
        self.db.refresh(employee)
        return CandidateStartOnboardingResponse(
            candidate_id=candidate_id,
            employee_id=UUID(str(employee.id)),
            employee_code=employee.employee_code,
            onboarding_tasks_created=tasks_created,
            message="Employee created and onboarding checklist initialized",
        )

    def _import_job_board_applicants(self, tenant_id: UUID, actor_id: UUID) -> int:
        imported = 0
        for posting in self.job_board_posting_repo.list_filtered(tenant_id, status="live"):
            if posting.platform == "career_page":
                source = "career_page"
            elif posting.platform in ("naukri", "indeed", "linkedin"):
                source = posting.platform
            else:
                source = "other"

            pool = MOCK_BOARD_APPLICANTS.get(posting.platform, [])
            if not pool:
                continue

            start_idx = posting.applicant_count % len(pool)
            applicant_data = pool[start_idx]
            email = applicant_data["email"].lower()
            job_id = UUID(str(posting.job_opening_id))

            if self.candidate_repo.exists_for_job(tenant_id, job_id, email):
                continue

            entity = Candidate(
                tenant_id=str(tenant_id),
                job_opening_id=str(posting.job_opening_id),
                first_name=applicant_data["first_name"],
                last_name=applicant_data["last_name"],
                email=email,
                mobile=applicant_data.get("mobile"),
                source=source,
                current_stage="applied",
                status="active",
                notes=f"Imported from {JOB_BOARD_PLATFORMS.get(posting.platform, posting.platform)} job board sync",
                created_by=str(actor_id),
                updated_by=str(actor_id),
            )
            self.candidate_repo.add(entity)
            self._record_stage(tenant_id, entity, None, "applied", actor_id)
            posting.applicant_count += 1
            imported += 1
        return imported

    def _get_or_create_default_checklist(self, tenant_id: UUID, actor_id: UUID) -> OnboardingChecklist:
        existing = self.checklist_repo.get_by_code(tenant_id, "STANDARD")
        if existing:
            return existing
        checklist = OnboardingChecklist(
            tenant_id=str(tenant_id),
            code="STANDARD",
            name="Standard Onboarding",
            description="Default onboarding checklist for new hires from recruitment",
            is_default=True,
            is_active=True,
            created_by=str(actor_id),
            updated_by=str(actor_id),
        )
        self.checklist_repo.add(checklist)
        return checklist

    def close_job_board_posting(
        self, tenant_id: UUID, posting_id: UUID, *, actor_id: UUID, meta: Optional[dict] = None
    ) -> JobBoardPostingResponse:
        posting = self.job_board_posting_repo.get_by_id(posting_id, tenant_id)
        if not posting:
            raise NotFoundError("Job board posting not found")
        posting.status = "closed"
        posting.updated_by = str(actor_id)
        self._log("recruitment.job_board.close", tenant_id, actor_id, str(posting_id), meta)
        self.db.commit()
        self.db.refresh(posting)
        return self._map_posting(tenant_id, posting)

    def _map_posting(self, tenant_id: UUID, posting: JobBoardPosting) -> JobBoardPostingResponse:
        job = self.job_repo.get_by_id(UUID(str(posting.job_opening_id)), tenant_id)
        job_title = job.title if job else "Unknown job"
        return JobBoardPostingResponse(
            id=UUID(str(posting.id)),
            job_opening_id=UUID(str(posting.job_opening_id)),
            job_title=job_title,
            platform=posting.platform,
            external_job_id=posting.external_job_id,
            external_url=posting.external_url,
            status=posting.status,
            applicant_count=posting.applicant_count,
            posted_at=posting.posted_at,
            last_synced_at=posting.last_synced_at,
            error_message=posting.error_message,
        )

    def _map_feedback(self, entity: InterviewFeedback) -> InterviewFeedbackResponse:
        interview = self.interview_repo.get_by_id(UUID(str(entity.interview_id)), UUID(str(entity.tenant_id)))
        candidate_name = "Unknown"
        candidate_id = UUID(str(entity.interview_id))
        if interview:
            candidate_id = UUID(str(interview.candidate_id))
            candidate = self.candidate_repo.get_by_id(candidate_id, UUID(str(entity.tenant_id)))
            if candidate:
                candidate_name = f"{candidate.first_name} {candidate.last_name}"

        interviewer_name = "Reviewer"
        if entity.reviewer_id:
            reviewer = self.db.query(User).filter(User.id == str(entity.reviewer_id)).first()
            if reviewer:
                interviewer_name = f"{reviewer.first_name} {reviewer.last_name}"

        comments = entity.feedback or ""
        technical_skills = None
        communication = None
        culture_fit = None
        if entity.feedback:
            try:
                parsed = json.loads(entity.feedback)
                if isinstance(parsed, dict):
                    comments = parsed.get("comments", comments)
                    technical_skills = parsed.get("technical_skills")
                    communication = parsed.get("communication")
                    culture_fit = parsed.get("culture_fit")
            except json.JSONDecodeError:
                comments = entity.feedback

        return InterviewFeedbackResponse(
            id=UUID(str(entity.id)),
            tenant_id=UUID(str(entity.tenant_id)),
            interview_id=UUID(str(entity.interview_id)),
            candidate_id=candidate_id,
            candidate_name=candidate_name,
            interviewer_name=interviewer_name,
            rating=entity.rating,
            recommendation=entity.recommendation,
            comments=comments,
            technical_skills=technical_skills,
            communication=communication,
            culture_fit=culture_fit,
            submitted_at=entity.created_at,
        )

    def _record_stage(
        self, tenant_id: UUID, candidate: Candidate, from_stage: Optional[str], to_stage: str, actor_id: UUID
    ) -> None:
        self.db.add(
            CandidateStageHistory(
                tenant_id=str(tenant_id),
                candidate_id=str(candidate.id),
                from_stage=from_stage,
                to_stage=to_stage,
                changed_by=str(actor_id),
            )
        )

    def _log(self, action: str, tenant_id: UUID, actor_id: UUID, resource_id: str, meta: Optional[dict]) -> None:
        self.audit.log(
            action,
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type="recruitment",
            resource_id=resource_id,
            ip_address=meta.get("ip_address") if meta else None,
            user_agent=meta.get("user_agent") if meta else None,
        )
