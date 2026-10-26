# Project File & Folder Architecture Guide (Django)

Django-only monolith. There is no FastAPI service, no Streamlit
workspace, and no `app/` package.

## 1. High-Level Directory Tree

```text
./
|-- config/            # settings.py, urls.py, wsgi.py/asgi.py, keywords.json
|-- modules/
|   |-- admin_panel/  # ORM models, migrations, admin-console views/urls,
|   |                  #   middleware, admin.py, import_existing_data command
|   `-- website/      # portal + API views, urls, utils (pagination, scoring,
|                      #   subscriptions, email), tests.py, context_processors.py
|-- templates/        # website/*, admin/*, emails/*
|-- static/           # css/style.css, js/app.js, exports/*.csv
|-- static_admin/     # custom admin-console assets (css/, js/)
|-- media/            # uploads (documents/, uploads/)
|-- data/             # Top-200 master CSV + verified_company_links.json
|-- docs/             # FOLDER_STRUCTURE.md (this file), PAGINATION_GUIDE.md
|-- .env              # runtime config (SECRET_KEY, DEBUG, MYSQL_* credentials)
|-- manage.py         # Django management CLI
|-- requirements.txt  # Django-only dependencies
|-- run_server.bat    # one-click Django launcher (Windows)
`-- test_django_suite.py  # end-to-end acceptance suite (48 checks)
```

## 2. Directory Details

### `config/`
- **`settings.py`**: installed apps (`admin_panel`, `website`), custom user
  model (`admin_panel.User`), **MySQL-only `DATABASES`** (`MYSQL_*` env
  vars), `LEGACY_MYSQL` read-only source settings, static/media roots,
  email backend.
- **`__init__.py`**: registers PyMySQL as the MySQLdb driver used by
  Django's MySQL backend.
- **`urls.py`**: `/django-admin/` (built-in), `/admin-portal/*` (custom
  console), `''` (public portal + REST APIs).

### `modules/admin_panel/` (intelligence core)
ORM models (`User`, `Company`, `Job`, `CSRProject`, `CSROpportunity`,
`Contact`, `NGOCollaboration`, `PageRecord`, `AuditTrail`, `Prospect`,
`Document`, subscriptions/invoices/promos, `ServiceCatalog`), migrations,
admin-console page views + URL namespaces, role middleware, and the
database management commands:

| Command | Purpose |
| :--- | :--- |
| `create_mysql_schema` | drop + recreate the MySQL database and run migrations (no data) |
| `migrate_to_mysql` | load `data/db_backup_*.json`, gap-fill from legacy MySQL, then Top-200 CSV |
| `backup_database` | export every record to a new `data/db_backup_<timestamp>.json` |
| `import_existing_data` | seed users + companies (legacy MySQL/CSV) |

### `modules/website/` (public portal & APIs)
Page + JSON API views, URL namespaces and shared utilities:
- **`utils/pagination.py`** — `paginate_queryset`: envelope
  `{items, total, page, page_size, total_pages, has_next, has_prev}` when
  `page` is given, flat list otherwise (backward compatible).
- **`utils/scoring_service.py`** — 7-criteria `score_company` and
  NGO-to-company `calculate_ngo_match`.
- **`tests.py`** — regression suite: pagination contracts, jobs API +
  absolute-URL invariant, NGO matching, prospects CRM, scoring bounds,
  portal smoke.

### `templates/`, `static/`, `static_admin/`, `media/`
Django templates; static assets via the staticfiles app (`STATICFILES_DIRS`
= `static/`, `static_admin/`); uploads under `media/` (`MEDIA_ROOT`).

### `data/`
Verified Top-200 master CSV (seed source for `import_existing_data`), the
`verified_company_links.json` link-verification cache and the versioned
`db_backup_*.json` fixture used by `migrate_to_mysql`.

## 3. Request Flow

```text
[ Browser ] -> GET / (templates/website/index.html + static css/js)
[ app.js  ] -> async GET /companies?page=1&page_size=12&q=Tata
[ Django  ] -> validates params, ORM LIMIT/OFFSET slice + COUNT(*)
[ MySQL   ] -> rows (csr_intelligence_django)
[ Django  ] -> JsonResponse { items, total, page, page_size,
                              total_pages, has_next, has_prev }
[ Browser ] -> renders pagination bar, skeletons, toasts
```
