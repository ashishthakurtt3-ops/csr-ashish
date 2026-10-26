# Server-Side Pagination & Dynamic UI Specification (Django)

Architecture, API contracts, frontend state and UX patterns for the
server-side pagination and dynamic web interface of the Django
ImpactBridge CSR & Job Intelligence Platform.

## 1. Overview & Goals

The platform serves 200 corporations, 502 CSR projects, 1800 jobs,
135 opportunities and 809 crawler log records. To keep renders fast and
the DOM lean:

1. **Server-side pagination** — ORM `LIMIT`/`OFFSET` slices.
2. **Dynamic UI** — no full reloads; `fetch()` in `static/js/app.js`.
3. **Smart pagination controls** — ellipsis numbering, First/Prev/Next/Last,
   per-page selectors, range counters.
4. **Live feedback** — debounced search, skeletons, live HTTP re-check
   probes, non-blocking toasts.
5. **Backward compatibility** — raw JSON array when `page` is omitted.

## 2. API Pagination Contract

Implemented by `modules/website/utils/pagination.py::paginate_queryset`
(used by every list API view):

- `page` (optional): 1-indexed. Omitted/invalid -> flat list
  (up to `limit`, default 200).
- `page_size` (optional, default 12, max 100): rows per page.
- Envelope: `{items, total, page, page_size, total_pages, has_next,
  has_prev}`.

Example: `GET /jobs?page=2&page_size=10&work_mode=Remote&sort=recent`

```json
{
  "items": [
    {
      "job_row_id": 42,
      "company_name": "Tata Consultancy Services Limited",
      "job_title": "CSR Impact Program Manager",
      "location": "Mumbai",
      "work_mode": "REMOTE",
      "application_url": "https://www.tcs.com/careers/...",
      "link_status": "VERIFIED_HTTP_200"
    }
  ],
  "total": 28,
  "page": 2,
  "page_size": 10,
  "total_pages": 3,
  "has_next": true,
  "has_prev": true
}
```

## 3. Paginated Endpoints Reference

| Endpoint | Filters | Default `page_size` |
| :--- | :--- | :--- |
| `GET /companies` | `q`, `sector`, `state`, `status`, `opp_only` | 12 |
| `GET /recommendations` | `q`, `sector`, `state`, `min_score` | 12 |
| `GET /jobs` | `q`, `category`, `department`, `location`, `state`, `work_mode`, `impact_only`, `company_id`, `sort` | 12 |
| `GET /csr/projects` | `q`, `category`, `state`, `fy` | 12 |
| `GET /csr/opportunities` | `q`, `category`, `opp_type` | 12 |
| `GET /prospects` | `stage` | 10 |
| `GET /api/crawler/logs` | — | 12 |

## 4. Dynamic Frontend (`static/js/app.js`)

- **Centralized state** per section (`companies`, `jobs`, `opps`, `crawler`):
  `{page, pageSize, total, totalPages}`.
- **Pagination bar**: summary (`Showing 16-30 of 1800 jobs`), First/Prev/
  Next/Last, smart ellipsis (`1 ... 9 [10] 11 ... 20`), per-page dropdown
  (10/15/25/50), resets to page 1 on filter change.
- **Debounced live search** — fires after typing pauses.
- **Live domain re-check** — `POST /api/crawler/recheck/{company_id}`;
  badge animates to `HTTP 200 OK (84ms)` + toast.
- **CSV export** — client-side generation from fetched API rows.

## 5. Verification & Automated Tests

Covered by `modules/website/tests.py` (run with
`python manage.py test modules.website.tests`):

- `PaginationEngineTests` — envelope keys, totals, last-page boundary,
  invalid-page fallback, `page_size` cap.
- `CompaniesApiTests` / `JobsApiTests` — envelope, slicing, filters
  (`q`, `sector`, `impact_only`, `work_mode`), `jobs/summary` contract,
  absolute-URL integrity invariant.
- `CSRAndMatchingApiTests` — projects/opportunities, scored+sorted
  `/ngo/matches`, prospects CRUD.
- Full production acceptance: `python test_django_suite.py` (48 checks).
