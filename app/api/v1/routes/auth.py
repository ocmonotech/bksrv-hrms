from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, Request
from uuid import UUID

from app.api.deps import get_auth_service, get_current_user, get_request_meta
from app.models.user import User
from app.schemas.auth import (
    CompanyOption,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MessageResponse,
    RefreshTokenRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from app.utils.password_policy import validate_password
from app.schemas.common import APIResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=APIResponse[LoginResponse])
def login(
    payload: LoginRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> APIResponse[LoginResponse]:
    meta = get_request_meta(request)
    result = service.login(
        payload.identifier,
        payload.password,
        payload.company_code,
        remember_me=payload.remember_me,
        ip_address=meta["ip_address"],
        user_agent=meta["user_agent"],
    )
    return APIResponse(data=result, message="Login successful")


@router.post("/refresh", response_model=APIResponse[TokenResponse])
def refresh_token(
    payload: RefreshTokenRequest,
    service: AuthService = Depends(get_auth_service),
) -> APIResponse[TokenResponse]:
    tokens = service.refresh(payload.refresh_token)
    return APIResponse(data=tokens, message="Token refreshed")


@router.post("/logout", response_model=APIResponse[MessageResponse])
def logout(
    payload: LogoutRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> APIResponse[MessageResponse]:
    meta = get_request_meta(request)
    service.logout(
        current_user,
        payload.refresh_token,
        ip_address=meta["ip_address"],
        user_agent=meta["user_agent"],
    )
    return APIResponse(data=MessageResponse(message="Logged out successfully"))


@router.get("/me", response_model=APIResponse[UserResponse])
def get_me(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
    x_tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-Id"),
    x_company_id: Optional[str] = Header(default=None, alias="X-Company-Id"),
) -> APIResponse[UserResponse]:
    tenant_id = UUID(x_tenant_id) if x_tenant_id else None
    company_id = UUID(x_company_id) if x_company_id else None
    profile = service.get_current_user_profile(
        current_user,
        tenant_id=tenant_id,
        company_id=company_id,
    )
    return APIResponse(data=profile)


@router.get("/my-companies", response_model=APIResponse[list[CompanyOption]])
def my_companies(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> APIResponse[list[CompanyOption]]:
    companies = service.list_user_companies(current_user)
    return APIResponse(data=companies)


@router.post("/forgot-password", response_model=APIResponse[MessageResponse])
def forgot_password(
    payload: ForgotPasswordRequest,
    service: AuthService = Depends(get_auth_service),
) -> APIResponse[MessageResponse]:
    service.forgot_password(str(payload.identifier))
    return APIResponse(
        data=MessageResponse(message="If an account exists, a password reset link has been sent.")
    )


@router.post("/reset-password", response_model=APIResponse[MessageResponse])
def reset_password(
    payload: ResetPasswordRequest,
    service: AuthService = Depends(get_auth_service),
) -> APIResponse[MessageResponse]:
    validate_password(payload.password)
    service.reset_password(payload.token, payload.password)
    return APIResponse(data=MessageResponse(message="Password has been reset successfully"))


@router.post("/verify-otp", response_model=APIResponse[VerifyOtpResponse])
def verify_otp(
    payload: VerifyOtpRequest,
    service: AuthService = Depends(get_auth_service),
) -> APIResponse[VerifyOtpResponse]:
    tokens = service.verify_otp(payload.otp, payload.session_token, remember_me=payload.remember_me)
    return APIResponse(
        data=VerifyOtpResponse(message="OTP verified successfully", tokens=tokens),
    )
