# OCMono HRMS — Backend deployment (remote server)

Use **only the `backend/` folder** on your server. Do not upload `frontend/`.

Your mobile/web app connects via HTTP to:

```
https://YOUR-DOMAIN.com/api/v1
```

Example: if the API runs at `https://api.ocmono.com`, set your app base URL to `https://api.ocmono.com/api/v1`.

---

## What to upload

Upload these paths from the repo:

```
backend/
├── app/                 # Application code (required)
├── alembic/             # Database migrations (required)
├── scripts/             # Seed scripts (required for first setup)
├── storage/             # Create empty dir on server (uploads); do not copy test files
├── main.py
├── requirements.txt
├── alembic.ini
├── .env.example         # Copy to .env on server and edit
└── README.md            # Optional reference
```

### Do NOT upload

| Path | Reason |
|------|--------|
| `backend/.venv/` | Recreate on server with `pip install` |
| `backend/.pytest_cache/` | Local test cache |
| `backend/tests/` | Optional on production |
| `backend/storage/uploads/**` | Local dev uploads only |
| `backend/.env` | Create fresh on server (secrets) |

---

## Quick package (from your Mac)

From the project root:

```bash
chmod +x backend/scripts/package-backend.sh
./backend/scripts/package-backend.sh
```

This creates `backend/dist/ocmono-hrms-backend.zip` — upload that zip to your server and unzip.

---

## Server requirements

- **OS:** Linux (Ubuntu 22.04+ recommended)
- **Python:** 3.11 or 3.12
- **MySQL:** 8.0+
- **RAM:** 1 GB minimum (2 GB+ recommended)
- **Ports:** 8000 (internal) or 80/443 behind Nginx

---

## Step-by-step (production)

### 1. Upload and unzip

```bash
cd /var/www
unzip ocmono-hrms-backend.zip -d ocmono-hrms
cd ocmono-hrms/backend
```

### 2. Python virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. MySQL database

```sql
CREATE DATABASE ocmono_hrms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'hrms_user'@'localhost' IDENTIFIED BY 'STRONG_PASSWORD_HERE';
GRANT ALL PRIVILEGES ON ocmono_hrms.* TO 'hrms_user'@'localhost';
FLUSH PRIVILEGES;
```

### 4. Environment file

```bash
cp .env.example .env
nano .env
```

**Minimum production `.env`:**

```env
APP_NAME=OCMono HRMS API
APP_ENV=production
DEBUG=false
API_V1_PREFIX=/api/v1
HOST=0.0.0.0
PORT=8000

CORS_ORIGINS=https://your-app-domain.com,https://www.your-app-domain.com

DATABASE_URL=mysql+pymysql://hrms_user:STRONG_PASSWORD_HERE@localhost:3306/ocmono_hrms
JWT_SECRET_KEY=GENERATE_A_LONG_RANDOM_STRING_AT_LEAST_32_CHARS
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

PASSWORD_POLICY_ENABLED=true
RATE_LIMIT_ENABLED=true
REQUEST_LOGGING_ENABLED=true
AUDIT_MIDDLEWARE_ENABLED=true

SUPER_ADMIN_EMAIL=super@ocmono.com
SUPER_ADMIN_PASSWORD=CHANGE_ME_STRONG_PASSWORD

UPLOAD_ROOT=storage
MAX_UPLOAD_SIZE_MB=10
AI_PROVIDER=auto
OPENAI_API_KEY=

# Optional production integrations
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
REDIS_URL=
RATE_LIMIT_BACKEND=redis
WORKER_ENABLED=true
WORKER_USE_RQ=true
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_SMS_FROM=
```

Generate JWT secret:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 5. Storage directory

```bash
mkdir -p storage/uploads
chmod 755 storage storage/uploads
```

### 6. Migrations and seed

```bash
source .venv/bin/activate
alembic upgrade head
python -m scripts.seed_rbac
python -m scripts.seed_demo
```

### 7. Run (test)

```bash
uvicorn app.factory:create_app --factory --host 0.0.0.0 --port 8000
```

Verify:

- Health: `GET http://YOUR_SERVER:8000/api/v1/health`
- Docs: `http://YOUR_SERVER:8000/docs`
- Login: `POST http://YOUR_SERVER:8000/api/v1/auth/login`

```json
{
  "identifier": "admin@ocmono.com",
  "password": "password",
  "company_code": "OCMONO"
}
```

---

## Run as a service (systemd)

Create `/etc/systemd/system/ocmono-api.service`:

```ini
[Unit]
Description=OCMono HRMS API
After=network.target mysql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/ocmono-hrms/backend
Environment="PATH=/var/www/ocmono-hrms/backend/.venv/bin"
ExecStart=/var/www/ocmono-hrms/backend/.venv/bin/uvicorn app.factory:create_app --factory --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ocmono-api
sudo systemctl start ocmono-api
sudo systemctl status ocmono-api
```

---

## Nginx reverse proxy (HTTPS)

```nginx
server {
    listen 443 ssl http2;
    server_name api.your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/api.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.your-domain.com/privkey.pem;

    client_max_body_size 12M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Your app base URL: `https://api.your-domain.com/api/v1`

---

## API contract for your app

### Auth headers (after login)

```
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_uuid>
X-Company-Id: <company_uuid>
Content-Type: application/json
```

### Login request

`POST /api/v1/auth/login`

```json
{
  "identifier": "admin@ocmono.com",
  "password": "password",
  "company_code": "OCMONO"
}
```

### Success response shape

```json
{
  "success": true,
  "data": { ... },
  "message": "..."
}
```

### Error response shape

```json
{
  "success": false,
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "details": { "errors": [{ "field": "password", "message": "...", "type": "..." }] }
  },
  "request_id": "..."
}
```

### Refresh token

`POST /api/v1/auth/refresh`

```json
{ "refresh_token": "<refresh_token>" }
```

---

## Demo users (after seed)

| Email | Password | Role |
|-------|----------|------|
| `super@ocmono.com` | from `SUPER_ADMIN_PASSWORD` in `.env` | Super Admin |
| `admin@ocmono.com` | `password` | Company Admin |
| `hr@ocmono.com` | `password` | HR Admin |
| `employee@ocmono.com` | `password` | Employee |
| `2fa@ocmono.com` | `password` | Company Admin (2FA enabled — OTP logged to console in dev) |

Company code: **OCMONO**

Change all passwords before going live.

---

## Main API modules (all under `/api/v1`)

| Prefix | Module |
|--------|--------|
| `/auth` | Login, refresh, me, my-companies |
| `/tenants` | Tenant management (super admin) |
| `/roles`, `/permissions` | RBAC |
| `/company/profile` | Company profile |
| `/branches`, `/departments`, `/designations`, `/grades` | Company setup |
| `/cost-centers`, `/holidays`, `/policies`, `/approval-workflows` | Company setup |
| `/employees` | Employee CRUD, documents, timeline |
| `/attendance` | Punch, daily, monthly, regularization |
| `/shifts`, `/rosters`, `/shift-swap-requests` | Shifts |
| `/leaves` | Apply, requests, balance, calendar, comp-off |
| `/payroll` | Components, structures, run, payslips, FNF |
| `/recruitment` | Jobs, candidates, interviews, offers |
| `/onboarding` | Onboarding tasks |
| `/performance` | Reviews, OKRs, goals |
| `/documents` | Employee & company documents |
| `/helpdesk` | Tickets |
| `/reports` | Headcount, attendance, payroll reports, live analytics |
| `/timesheets` | Project timesheets, entries, submit/approve |
| `/training` | Courses, enrollments, L&D progress |
| `/surveys` | Engagement, well-being, pulse surveys |
| `/ai` | AI chat, insights, resume scoring (`AI_PROVIDER=auto` uses OpenAI when key set) |
| `/communication` | Announcements, templates, SMS/WhatsApp/email logs |
| `/expenses`, `/travel`, `/assets`, `/exit` | Extended HR modules |
| `/health`, `/ready` | Health checks |

### Production integrations (optional)

| Feature | Env vars | Notes |
|---------|----------|-------|
| Email (reset, announcements) | `SMTP_*` | Console fallback when unset |
| SMS / WhatsApp | `TWILIO_*` | Console fallback when unset |
| Background jobs | `REDIS_URL`, `WORKER_USE_RQ=true` | Thread pool fallback |
| Rate limiting (multi-instance) | `REDIS_URL`, `RATE_LIMIT_BACKEND=redis` | In-memory for single node |
| Real AI | `OPENAI_API_KEY`, `AI_PROVIDER=auto` | Mock when no key |

Full interactive docs: `https://YOUR-DOMAIN/docs`

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Can't connect to MySQL` | Check `DATABASE_URL`, MySQL running, user grants |
| CORS errors from app | Add your app origin to `CORS_ORIGINS` in `.env`, restart API |
| 401 on all routes | Send `Authorization: Bearer ...` + `X-Tenant-Id` |
| 403 Forbidden | User role lacks permission; check RBAC seed |
| Upload fails | Ensure `storage/uploads` exists and is writable |
| Migrations fail | Run `alembic upgrade head` on empty DB first |

---

## Security checklist before go-live

- [ ] Change `JWT_SECRET_KEY` and `SUPER_ADMIN_PASSWORD`
- [ ] Set `DEBUG=false`, `APP_ENV=production`
- [ ] Enable `PASSWORD_POLICY_ENABLED=true`
- [ ] Restrict `CORS_ORIGINS` to your real app domains
- [ ] Use HTTPS (Nginx + Let's Encrypt)
- [ ] Firewall: expose only 80/443, not 8000 publicly
- [ ] Change demo user passwords or disable demo seed in production
