# OCMono HRMS — Backend API

Python FastAPI backend for the OCMono HRMS platform with multi-tenant SaaS architecture, JWT authentication, and role-based access control.

## Tech stack

- **FastAPI** — HTTP API framework
- **SQLAlchemy 2.x** — ORM
- **Alembic** — Database migrations
- **MySQL** — Primary database
- **Pydantic v2** — Request/response validation
- **python-jose** — JWT tokens
- **passlib + bcrypt** — Password hashing

## Architecture

```
backend/
├── app/
│   ├── api/              # Routes & FastAPI dependencies
│   │   └── v1/routes/    # Versioned endpoints
│   ├── core/             # Config, DB, security, permissions, tenant
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic DTOs
│   ├── services/         # Business logic
│   ├── repositories/     # Data access layer
│   ├── middleware/       # Request ID, tenant context, logging, audit, rate limit
│   ├── utils/            # Shared helpers
│   ├── workers/          # Background jobs (placeholder)
│   └── ai/               # AI integrations (placeholder)
├── alembic/              # Migrations
├── scripts/              # Seed & maintenance scripts
├── tests/
├── main.py
└── requirements.txt
```

### Layering rules

| Layer | Responsibility |
|-------|----------------|
| **Routes** | HTTP parsing, status codes, dependency injection |
| **Services** | Business rules, orchestration, transactions |
| **Repositories** | SQLAlchemy queries, no business logic |
| **Models** | Database schema |
| **Schemas** | API contracts (Pydantic) |

### Multi-tenancy

- **Super Admin** — Platform user (`users.is_super_admin=True`). No tenant membership required. May optionally pass `X-Tenant-Id` / `X-Company-Id` to operate in a tenant context.
- **Company users** — Authenticate via `users` but access is scoped through `tenant_memberships` with `tenant_id` on all company-level tables.

Required headers for tenant-scoped endpoints:

```
Authorization: Bearer <access_token>
X-Tenant-Id: <uuid>
X-Company-Id: <uuid>   # optional where company scope is needed
```

## Quick start

### 1. Prerequisites

- Python 3.11+
- MySQL 8.0+

### 2. Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 3. Create database

```sql
CREATE DATABASE ocmono_hrms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'hrms_user'@'localhost' IDENTIFIED BY 'hrms_password';
GRANT ALL PRIVILEGES ON ocmono_hrms.* TO 'hrms_user'@'localhost';
FLUSH PRIVILEGES;
```

### 4. Run migrations

```bash
alembic upgrade head
```

### 5. Seed demo data

```bash
# RBAC catalog + system roles only
python -m scripts.seed_rbac

# Demo tenant, company, and users (includes RBAC + super admin)
python -m scripts.seed_demo

# Convenience wrapper (same as seed_demo)
python -m scripts.seed
```

Creates:
- Platform Super Admin (`super@ocmono.com`)
- Demo tenant `ocmono` + company `OCMONO`
- Demo users:
  - `admin@ocmono.com` / `password` (company_admin)
  - `hr@ocmono.com` / `password` (hr_admin)
  - `employee@ocmono.com` / `password` (employee)

### 6. Start server

```bash
python main.py
# or
uvicorn app.factory:create_app --factory --reload --host 0.0.0.0 --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Environment variables

See `.env.example` for all options. Key variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | MySQL connection string |
| `TEST_DATABASE_URL` | Test DB URL (default in-memory SQLite) |
| `JWT_SECRET_KEY` | Signing key for JWT tokens |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins |
| `LOG_LEVEL` | Application log level (`INFO`, `DEBUG`, etc.) |
| `REQUEST_LOGGING_ENABLED` | Enable structured HTTP request logs |
| `AUDIT_MIDDLEWARE_ENABLED` | Persist HTTP audit entries for mutating requests |
| `RATE_LIMIT_ENABLED` | Enable in-memory rate limiting placeholder |
| `PASSWORD_POLICY_ENABLED` | Enforce password complexity rules |
| `DATABASE_POOL_SIZE` | SQLAlchemy connection pool size |
| `DATABASE_POOL_RECYCLE` | Recycle pooled connections (seconds) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL |

## Production readiness

| Feature | Location |
|---------|----------|
| Global exception handling | `app/middleware/error_handler.py` |
| Validation error formatting | `app/utils/validation_errors.py` |
| Request logging | `app/middleware/request_logging.py` |
| Audit middleware | `app/middleware/audit_logging.py` |
| Tenant middleware | `app/middleware/tenant_context.py` |
| Permission dependency | `app/api/deps.py` → `require_permission_dep` |
| Rate limit placeholder | `app/middleware/rate_limit.py` |
| Password policy | `app/utils/password_policy.py` |
| DB pooling | `app/core/database.py` |
| ORM mixins | `app/models/mixins.py` |
| Pagination / search helpers | `app/utils/pagination.py`, `app/utils/search_filter.py` |

Recommended production settings:

```env
APP_ENV=production
DEBUG=false
JWT_SECRET_KEY=<long-random-secret>
PASSWORD_POLICY_ENABLED=true
RATE_LIMIT_ENABLED=true
CORS_ORIGINS=https://your-frontend.example.com
```

## API endpoints (v1)

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/login` | Super admin or company user login |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | Logout (revokes refresh token) |
| GET | `/api/v1/auth/me` | Current user profile + permissions |
| GET | `/api/v1/auth/my-companies` | Multi-company access list |
| POST | `/api/v1/auth/forgot-password` | Password reset request (stub) |
| POST | `/api/v1/auth/reset-password` | Password reset confirm (stub) |

### Tenants & RBAC
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/tenants` | Create tenant (super admin) |
| GET | `/api/v1/tenants` | List tenants |
| GET | `/api/v1/roles` | List system + tenant roles |
| POST | `/api/v1/roles` | Create custom role |
| GET | `/api/v1/roles/{role_id}` | Role with permission matrix |
| PUT | `/api/v1/roles/{role_id}/permissions` | Update role permissions |
| GET | `/api/v1/permissions` | Permission catalog |

### System
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/ready` | Readiness probe |

## RBAC models

| Model | Purpose |
|-------|---------|
| `Tenant` | SaaS tenant boundary |
| `User` | Platform account (`is_super_admin` for SaaS admin) |
| `Role` | System or tenant-scoped role |
| `Permission` | Global module+action catalog |
| `RolePermission` | Role ↔ permission mapping |
| `UserTenantAccess` | User ↔ tenant ↔ company ↔ role |
| `RefreshToken` | Refresh token revocation |
| `AuditLog` | Login and permission change audit |

Default system roles: Super Admin, Company Admin, HR Admin, Payroll Admin, Manager, Employee, Recruiter, Finance, Auditor.

Run `alembic upgrade head` then `python -m scripts.seed` to seed permissions, roles, and demo data.

## Company Setup (v1)

All endpoints require `Authorization`, `X-Tenant-Id`, and company module permissions.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/company/profile` | Get tenant company profile |
| PUT | `/api/v1/company/profile` | Create/update company profile |
| CRUD | `/api/v1/branches` | Branches |
| CRUD | `/api/v1/departments` | Departments |
| CRUD | `/api/v1/designations` | Designations |
| CRUD | `/api/v1/grades` | Grades |
| CRUD | `/api/v1/cost-centers` | Cost centers |
| CRUD | `/api/v1/holidays` | Holiday calendar |
| CRUD | `/api/v1/policies` | HR policies |
| CRUD | `/api/v1/approval-workflows` | Approval workflows (+ nested steps) |

List endpoints support `?page=1&page_size=20&search=...&is_active=true`. All records are tenant-scoped with soft delete and audit logging.

## Employee Master (v1)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/employees` | Create employee (auto-generates code if omitted) |
| GET | `/api/v1/employees` | List with filters: branch, department, status, employment_type |
| GET | `/api/v1/employees/{id}` | Full profile with nested details |
| PUT | `/api/v1/employees/{id}` | Update employee |
| DELETE | `/api/v1/employees/{id}` | Soft delete |
| PUT | `/api/v1/employees/{id}/status` | Status change with timeline |
| POST | `/api/v1/employees/{id}/documents` | Upload document (multipart) |
| GET | `/api/v1/employees/{id}/timeline` | Paginated activity timeline |

Document storage path: `uploads/{tenant_id}/employees/{employee_id}/documents/{type}/{file}`

Run `alembic upgrade head` to apply migration `004_employee_master`.

## Testing

```bash
pytest tests/ -v
```

Tests use `TEST_DATABASE_URL` (default: in-memory SQLite). Configure in `.env` or environment for alternate test databases.

## Adding a new module

1. Create model in `app/models/` with `TenantScopedMixin` for company data
2. Add Pydantic schemas in `app/schemas/`
3. Add repository in `app/repositories/`
4. Add service in `app/services/`
5. Add route in `app/api/v1/routes/` and register in `router.py`
6. Generate migration: `alembic revision --autogenerate -m "add module"`

## Frontend integration

Set in frontend `.env`:

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_USE_MOCK_API=false
```

The frontend sends `Authorization`, `X-Tenant-Id`, and `X-Company-Id` headers automatically via the API client.

## License

Proprietary — OCMono Technologies
