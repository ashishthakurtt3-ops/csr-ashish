# CSR & Job Intelligence — Django Enterprise Platform

A production-grade web intelligence platform for **India's Top-200 NSE-listed
corporations**. A single Django 5.x monolith ingests corporate master records,
serves a dynamic enterprise web portal, exposes versioned JSON REST APIs with
server-side pagination, and ships a custom enterprise admin console —
backed by MySQL (the one and only primary database), with 200 companies,
3000+ verified jobs, 502 CSR projects, 400 contacts and 135 open CSR
opportunities out of the box.

> **Architecture notes**
> - Single backend: **Django**. The retired FastAPI + Streamlit prototype
>   (`app/`, Streamlit workspace, uvicorn) has been fully removed.
> - Single database: **MySQL** (`MYSQL_DB`, default `csr_intelligence_django`).
>   There is no SQLite file and no fallback engine — everything else was
>   migrated into MySQL and deleted.

---

## Quick Start

### 1. Create the environment (first run only)

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

### 2. Launch (Windows)

Double-click **`run_server.bat`** — it uses `.venv` when present,
frees port 8000, and starts the Django server. Or run manually:

```powershell
.\.venv\Scripts\activate
python manage.py runserver 127.0.0.1:8000
```

### 3. Live URLs

- **Primary Enterprise Portal:** <http://localhost:8000>
- **Custom Admin Portal:** <http://localhost:8000/admin-portal/>
- **Django Admin Panel:** <http://localhost:8000/django-admin/>
- Admin login: user `admin`; set its password with `python manage.py changepassword admin` (no default password is shipped)

---

## Features

- **Dynamic Web Portal** (`/`) — zero-reload company explorer, social-impact
  job board, opportunity radar, live crawler telemetry; client-side CSV export.
- **REST APIs with server-side pagination** — envelope
  `{items, total, page, page_size, total_pages, has_next, has_prev}`;
  flat JSON arrays when `page` is omitted (backward compatible).
  Endpoints: `/health`, `/stats`, `/search`, `/companies`,
  `/companies/{id}`, `/companies/{id}/dossier`, `/recommendations`,
  `/csr/projects`, `/csr/opportunities`, `/jobs`, `/jobs/summary`,
  `/ngo/matches`, `/prospects`, `/api/crawler/logs`,
  `/api/crawler/recheck/{id}`, `/api/subscription/*`.
- **Verified official links** — live HTTP domain probing; only genuine
  official/ATS pages are marked `VERIFIED_HTTP_200`.
- **Custom enterprise admin console** (`/admin-portal/`) — companies, jobs,
  opportunities/projects, documents, users, subscriptions/invoices/promos,
  verification queue, audit trail, crawler status.
- **NGO matching engine** — 7-criteria opportunity scoring plus thematic,
  geographic and scale alignment between NGOs and corporations.

---

## Project Structure

```text
./
├── config/                  # Django project (settings, root URLs, WSGI/ASGI)
├── modules/
│   ├── admin_panel/         # Core intelligence: models, admin console views/URLs,
│   │                        #   middleware, management commands (import_existing_data)
│   └── website/             # Public portal: API/page views, URL namespaces,
│                            #   utils (pagination, scoring, subscriptions, email), tests
├── templates/               # Django templates (website/*, admin/*, emails/*)
├── static/                  # Portal assets (css/style.css, js/app.js, exports/*.csv)
├── static_admin/            # Custom admin-console static assets
├── media/                   # User/document uploads (documents/, uploads/)
├── data/                    # Seed assets: verified Top-200 company master CSV,
│                            #   verified-company-links cache, db_backup_*.json
├── docs/                    # FOLDER_STRUCTURE.md, PAGINATION_GUIDE.md
├── .env                     # Runtime configuration (SECRET_KEY, DEBUG, MYSQL_*…)
├── manage.py                # Django management CLI
├── requirements.txt         # Django-only Python dependencies
├── run_server.bat           # One-click Django launcher (Windows)
└── test_django_suite.py     # End-to-end acceptance suite (48 checks)
```

## Database (MySQL only)

`.env` → `MYSQL_*` (host/port/user/password/db) configures the single
primary database; `config/__init__.py` registers PyMySQL as the driver.

```powershell
# (Re)create an empty MySQL schema — drops & re-runs all migrations
python manage.py create_mysql_schema

# Load data: db_backup_*.json fixture + legacy csr_intelligence gap-fill
#             + Top-200 master CSV (Django rows always win on conflict)
python manage.py migrate_to_mysql

# Export a fresh snapshot of every record (before schema/data changes)
python manage.py backup_database

# Seed users + top-200 companies from CSV / legacy MySQL
python manage.py import_existing_data
```

Shipped dataset in `csr_intelligence_django`: 200 companies, 3000+ jobs,
502 CSR projects, 400 contacts, 322 NGO collaborations, 200 scores,
809 page records, 135 opportunities, 7 prospects, 2 users,
1 subscription + 2 invoices + 5 promo codes.

## Testing

```powershell
# Django unit/integration suite (portal APIs, pagination, scoring)
python manage.py test modules.website.tests

# End-to-end acceptance suite against the populated database
python test_django_suite.py
```

## Data integrity rules (enforced in code)

- **MySQL only.** `config/settings.py` has no SQLite fallback; if MySQL is down the server stops. All secrets come from `.env` (see `.env.example`).
- **Only verified jobs are public** (`modules/admin_panel/verification.py`): status ACTIVE + verified + `link_status = VERIFIED_HTTP_200` (live HTTP check, same requisition id / title) + exactly one owning company.
- **No guessing.** Missing values are shown as *Not available on the company website*; sections a company only shows after login are shown as *Available only after login on the company website* (set per company in Admin -> Companies -> Edit, or `manage.py set_company_access`).
- Shared ATS portals (Adani Oracle, Unilever Workday) are configured in `config/shared_tenants.json`; a posting that cannot be tied to one company is never published.

### Rollout order
```
python manage.py migrate
python manage.py backup_database
python manage.py purge_fake_data --apply            # REQ-* jobs, guessed contacts
python manage.py normalize_job_data --apply         # ISO dates, enums, country, ownership; hides all jobs until verified
python manage.py verify_job_links                   # needs internet; publishes only proven links
python manage.py set_company_access --detect        # flags login-walled careers pages (confirm in admin)
python manage.py expire_jobs --with-links           # schedule daily
```
Run `python -m unittest discover -s tests_pure` for the Django-free unit tests.
