from __future__ import annotations
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "OCMono HRMS API"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    host: str = "0.0.0.0"
    port: int = 8000

    log_level: str = "INFO"
    request_logging_enabled: bool = True
    audit_middleware_enabled: bool = True

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    database_url: str = "mysql+pymysql://hrms_user:hrms_password@localhost:3306/ocmono_hrms"
    test_database_url: str = "sqlite://"
    database_echo: bool = False
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_recycle: int = 3600
    database_pool_timeout: int = 30

    jwt_secret_key: str = "change-me-to-a-long-random-secret-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    remember_me_refresh_token_expire_days: int = 30

    super_admin_email: str = "super@ocmono.com"
    super_admin_password: str = "change-me"

    password_policy_enabled: bool = False
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digit: bool = True
    password_require_special: bool = True

    rate_limit_enabled: bool = False
    rate_limit_max_requests: int = 120
    rate_limit_window_seconds: int = 60

    upload_root: str = "storage"
    max_upload_size_mb: int = 10

    ai_provider: str = "auto"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    ai_monthly_limit_per_tenant: int = 1000
    ai_temperature: float = 0.3
    ai_max_tokens: int = 1500

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True

    app_base_url: str = "http://localhost:5173"

    redis_url: str = ""
    rate_limit_backend: str = "memory"

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_sms_from: str = ""
    twilio_whatsapp_from: str = "whatsapp:+14155238886"

    worker_enabled: bool = False
    worker_use_rq: bool = False
    worker_queue_name: str = "hrms-default"

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
