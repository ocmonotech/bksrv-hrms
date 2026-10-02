from __future__ import annotations
import enum


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    COMPANY_ADMIN = "company_admin"
    HR_ADMIN = "hr_admin"
    PAYROLL_ADMIN = "payroll_admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"
    RECRUITER = "recruiter"
    FINANCE = "finance"
    AUDITOR = "auditor"


class PermissionAction(str, enum.Enum):
    VIEW = "view"
    CREATE = "create"
    EDIT = "edit"
    DELETE = "delete"
    APPROVE = "approve"
    EXPORT = "export"
    MANAGE = "manage"


class PermissionModule(str, enum.Enum):
    DASHBOARD = "dashboard"
    COMPANY = "company"
    EMPLOYEES = "employees"
    ATTENDANCE = "attendance"
    LEAVE = "leave"
    PAYROLL = "payroll"
    RECRUITMENT = "recruitment"
    ONBOARDING = "onboarding"
    PERFORMANCE = "performance"
    EXPENSES = "expenses"
    ASSETS = "assets"
    HELPDESK = "helpdesk"
    DOCUMENTS = "documents"
    REPORTS = "reports"
    AI = "ai"
    SETTINGS = "settings"
    TIMESHEETS = "timesheets"
    TRAINING = "training"
    SURVEYS = "surveys"


class EmploymentType(str, enum.Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERN = "intern"


class EmployeeStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROBATION = "probation"
    ON_NOTICE = "on_notice"
    TERMINATED = "terminated"


class ProfileUpdateRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class TimelineEventType(str, enum.Enum):
    CREATED = "created"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"
    PROMOTED = "promoted"
    TRANSFERRED = "transferred"
    DOCUMENT_UPLOADED = "document_uploaded"
    PROFILE_UPDATE_REQUESTED = "profile_update_requested"
    PROFILE_UPDATE_APPROVED = "profile_update_approved"
    SALARY_UPDATED = "salary_updated"


class PunchType(str, enum.Enum):
    IN = "in"
    OUT = "out"


class PunchSource(str, enum.Enum):
    WEB = "web"
    MOBILE = "mobile"
    BIOMETRIC = "biometric"


class AttendanceDayStatus(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    HALF_DAY = "half_day"
    LATE = "late"
    ON_LEAVE = "on_leave"
    HOLIDAY = "holiday"
    WEEK_OFF = "week_off"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class LeaveTransactionType(str, enum.Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    ADJUSTMENT = "adjustment"
    ACCRUAL = "accrual"
    LOP = "lop"


class PayrollRunStatus(str, enum.Enum):
    DRAFT = "draft"
    PREVIEW = "preview"
    APPROVED = "approved"
    LOCKED = "locked"


class SalaryComponentType(str, enum.Enum):
    EARNING = "earning"
    DEDUCTION = "deduction"
