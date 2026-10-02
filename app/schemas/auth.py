from __future__ import annotations

from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel
from app.schemas.role import PermissionMatrixItem


class LoginRequest(BaseModel):
    identifier: str = Field(..., min_length=3, description="Email or mobile number")
    password: str = Field(..., min_length=6)
    company_code: Optional[str] = Field(default=None, description="Filter login to a specific company")
    remember_me: bool = Field(default=False, description="Issue a longer-lived refresh token")


class SelectCompanyRequest(BaseModel):
    company_id: UUID


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10)


class UserResponse(ORMModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    is_super_admin: bool
    is_active: bool = True
    role: Optional[str] = None
    role_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    company_id: Optional[UUID] = None
    company_name: Optional[str] = None
    permissions: Optional[List[PermissionMatrixItem]] = None


class LoginResponse(BaseModel):
    user: Optional[UserResponse] = None
    tokens: Optional[TokenResponse] = None
    requires_2fa: bool = False
    session_token: Optional[str] = None


class CompanyOption(ORMModel):
    id: UUID
    name: str
    code: str
    tenant_id: UUID
    tenant_name: str
    role: str
    role_id: UUID
    is_default: bool = False


class ForgotPasswordRequest(BaseModel):
    identifier: Union[EmailStr, str] = Field(..., min_length=3)


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10)
    password: str = Field(..., min_length=8)


class VerifyOtpRequest(BaseModel):
    otp: str = Field(..., min_length=4, max_length=10)
    session_token: str = Field(..., min_length=10)
    remember_me: bool = Field(default=False, description="Issue a longer-lived refresh token")


class VerifyOtpResponse(BaseModel):
    message: str
    tokens: Optional[TokenResponse] = None


class MessageResponse(BaseModel):
    message: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None
