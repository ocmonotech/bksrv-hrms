from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SurveyCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    survey_type: str = Field(default="engagement", pattern="^(engagement|wellbeing|pulse|custom)$")
    is_anonymous: bool = True
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class SurveyUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    survey_type: Optional[str] = Field(default=None, pattern="^(engagement|wellbeing|pulse|custom)$")
    status: Optional[str] = Field(default=None, pattern="^(draft|active|closed)$")
    is_anonymous: Optional[bool] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class SurveyResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    title: str
    description: Optional[str] = None
    survey_type: str
    status: str
    is_anonymous: bool
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SurveyQuestionCreate(BaseModel):
    question_text: str = Field(..., min_length=1)
    question_type: str = Field(default="rating", pattern="^(rating|text|choice)$")
    options_json: Optional[str] = None
    order_index: int = 0


class SurveyQuestionResponse(BaseModel):
    id: UUID
    survey_id: UUID
    question_text: str
    question_type: str
    options_json: Optional[str] = None
    order_index: int

    model_config = {"from_attributes": True}


class SurveyAnswerSubmit(BaseModel):
    question_id: UUID
    response_value: str = Field(..., min_length=1)


class SurveySubmissionCreate(BaseModel):
    answers: list[SurveyAnswerSubmit] = Field(..., min_length=1)


class SurveyDashboardStats(BaseModel):
    active_surveys: int
    total_responses: int
    avg_engagement_score: float
    wellbeing_index: float
