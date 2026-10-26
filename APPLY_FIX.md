# How to Apply This Complete Data-Integrity & 200+ Scalable Crawler Fix

1. Unzip `csr_fix_overlay.zip` **ON TOP** of your project folder (replacing existing files).
2. Copy `.env.example` -> `.env` and fill in your real MySQL and Django credentials (`SECRET_KEY`, `MYSQL_DB`, `MYSQL_USER`, `MYSQL_PASSWORD`).
   - **MySQL only:** There is zero SQLite fallback. The server fails loudly if MySQL is unreachable or if any secret is missing from `.env`.
3. Run the automated project cleanup & code-loophole patcher:
   ```bash
   python scripts/apply_project_fixes.py
   ```
4. Run the database migrations, clean existing data, and crawl all 200 companies (and any additional companies as you scale up):
   ```bash
   python manage.py migrate
   python manage.py backup_database
   python manage.py purge_fake_data --apply            # Deletes fake REQ-* jobs & pattern contacts; demotes unproven opportunities, page-title CSR projects & generic info@/webmaster@ contacts
   python manage.py normalize_job_data --apply         # Normalises ISO dates, enums, country, SmartRecruiters URLs, shared ATS ownership
   python manage.py crawl_all_companies --workers 4 --verify-links
   ```
5. **Scaling Beyond 200 Companies Later**:
   - Whenever you want to increase the number of companies (e.g. from 200 to 300, 500, or 1,000+), simply pass your new companies CSV to `crawl_all_companies`:
     ```bash
     python manage.py crawl_all_companies --import-csv data/more_companies.csv --only-pending --workers 4 --verify-links
     ```
   - All APIs, pagination bars, and Admin/Public directories dynamically scale with the total number of companies in MySQL (no hardcoded 200-company limit).
6. **Dedicated Login-Required Companies Section**:
   - Any company whose website requires login to view Jobs, CSR, or Contacts is automatically flagged during crawling (or via `python manage.py set_company_access --detect` / Admin -> Companies -> Edit) and displayed in the **Separate Login-Required Companies Section** on both the Public Website and the Admin Panel with the message: *"You need to login on the company website to view the data"*.
