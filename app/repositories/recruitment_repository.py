from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.recruitment import (
    Candidate,
    Interview,
    InterviewFeedback,
    JobBoardConnection,
    JobBoardPosting,
    JobOpening,
    OfferLetter,
)
from app.repositories.tenant_scoped_repository import TenantScopedRepository


class JobOpeningRepository(TenantScopedRepository[JobOpening]):
    search_fields = ("title", "code")

    def __init__(self, db: Session) -> None:
        super().__init__(db, JobOpening, search_fields=self.search_fields)


class CandidateRepository(TenantScopedRepository[Candidate]):
    search_fields = ("first_name", "last_name", "email")

    def __init__(self, db: Session) -> None:
        super().__init__(db, Candidate, search_fields=self.search_fields)

    def list_filtered(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        job_opening_id: Optional[UUID] = None,
        current_stage: Optional[str] = None,
        status: Optional[str] = None,
    ):
        extra = []
        if job_opening_id:
            extra.append(Candidate.job_opening_id == str(job_opening_id))
        if current_stage:
            extra.append(Candidate.current_stage == current_stage)
        if status:
            extra.append(Candidate.status == status)
        return self.list_paginated(tenant_id, page=page, page_size=page_size, search=search, extra_filters=extra or None)

    def exists_for_job(self, tenant_id: UUID, job_opening_id: UUID, email: str) -> bool:
        from sqlalchemy import select

        stmt = select(Candidate.id).where(
            Candidate.tenant_id == str(tenant_id),
            Candidate.job_opening_id == str(job_opening_id),
            Candidate.email == email.lower(),
            Candidate.deleted_at.is_(None),
        )
        return self.db.scalar(stmt) is not None


class InterviewRepository(TenantScopedRepository[Interview]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Interview)

    def list_filtered(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        candidate_id: Optional[UUID] = None,
        job_opening_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ):
        extra = []
        if candidate_id:
            extra.append(Interview.candidate_id == str(candidate_id))
        if job_opening_id:
            extra.append(Interview.job_opening_id == str(job_opening_id))
        if status:
            extra.append(Interview.status == status)
        return self.list_paginated(tenant_id, page=page, page_size=page_size, extra_filters=extra or None)


class OfferLetterRepository(TenantScopedRepository[OfferLetter]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, OfferLetter)

    def list_filtered(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        candidate_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ):
        extra = []
        if candidate_id:
            extra.append(OfferLetter.candidate_id == str(candidate_id))
        if status:
            extra.append(OfferLetter.status == status)
        return self.list_paginated(tenant_id, page=page, page_size=page_size, extra_filters=extra or None)


class InterviewFeedbackRepository(TenantScopedRepository[InterviewFeedback]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, InterviewFeedback)

    def list_for_tenant(self, tenant_id: UUID):
        return (
            self.db.query(InterviewFeedback)
            .filter(
                InterviewFeedback.tenant_id == str(tenant_id),
                InterviewFeedback.deleted_at.is_(None),
            )
            .order_by(InterviewFeedback.created_at.desc())
            .all()
        )

    def get_by_interview(self, tenant_id: UUID, interview_id: UUID) -> Optional[InterviewFeedback]:
        return (
            self.db.query(InterviewFeedback)
            .filter(
                InterviewFeedback.tenant_id == str(tenant_id),
                InterviewFeedback.interview_id == str(interview_id),
                InterviewFeedback.deleted_at.is_(None),
            )
            .first()
        )


class JobBoardConnectionRepository(TenantScopedRepository[JobBoardConnection]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, JobBoardConnection)

    def get_by_platform(self, tenant_id: UUID, platform: str) -> Optional[JobBoardConnection]:
        return (
            self.db.query(JobBoardConnection)
            .filter(
                JobBoardConnection.tenant_id == str(tenant_id),
                JobBoardConnection.platform == platform,
                JobBoardConnection.deleted_at.is_(None),
            )
            .first()
        )

    def list_for_tenant(self, tenant_id: UUID):
        return (
            self.db.query(JobBoardConnection)
            .filter(
                JobBoardConnection.tenant_id == str(tenant_id),
                JobBoardConnection.deleted_at.is_(None),
            )
            .all()
        )


class JobBoardPostingRepository(TenantScopedRepository[JobBoardPosting]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, JobBoardPosting)

    def list_filtered(
        self,
        tenant_id: UUID,
        *,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        job_opening_id: Optional[UUID] = None,
    ):
        query = self.db.query(JobBoardPosting).filter(
            JobBoardPosting.tenant_id == str(tenant_id),
            JobBoardPosting.deleted_at.is_(None),
        )
        if platform:
            query = query.filter(JobBoardPosting.platform == platform)
        if status:
            query = query.filter(JobBoardPosting.status == status)
        if job_opening_id:
            query = query.filter(JobBoardPosting.job_opening_id == str(job_opening_id))
        return query.order_by(JobBoardPosting.created_at.desc()).all()

    def get_by_job_and_platform(
        self, tenant_id: UUID, job_opening_id: UUID, platform: str
    ) -> Optional[JobBoardPosting]:
        return (
            self.db.query(JobBoardPosting)
            .filter(
                JobBoardPosting.tenant_id == str(tenant_id),
                JobBoardPosting.job_opening_id == str(job_opening_id),
                JobBoardPosting.platform == platform,
                JobBoardPosting.deleted_at.is_(None),
            )
            .first()
        )
