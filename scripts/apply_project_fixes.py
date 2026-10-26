#!/usr/bin/env python3
"""
Automated project-wide integrity patcher.

Run from your project root after extracting `csr_fix_overlay.zip`:
    python scripts/apply_project_fixes.py

What this script does:
1. Deletes all legacy seed, backup, export, and quarantine files listed in DELETED_FILES.txt
   (including glob patterns like data/db_backup_*.json and static/exports/*.csv).
2. Patches `data_exchange.py` (if present in modules/admin_panel/) to:
   - Remove hardcoded passwords (`Impact@2026!`, `Admin@12345`).
   - Disable the "Master Sync" backup re-import endpoint.
   - Make crawled entities (jobs, contacts, csr_projects, csr_opportunities, companies) strictly EXPORT-ONLY.
3. Patches `job_views.py` (if present in modules/admin_panel/) so manual job editing can only
   CLOSE/deactivate a job (`CLOSED` / `INACTIVE`) and can never force `status = 'ACTIVE'` by hand.
4. Patches any remaining view files that include `'EXTRACTED'` in verified status lists.
"""
import glob
import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def delete_legacy_files():
    deleted_list_file = ROOT / "DELETED_FILES.txt"
    patterns = [
        "seed.py",
        "seed_data.json",
        "seed_database.py",
        "scripts/activate_all_200_company_jobs.py",
        "scripts/quarantine_legacy_seed_jobs.py",
        "scripts/rollback_requarantine_seed_jobs.py",
        "scripts/sync_seed_fixtures.py",
        "scripts/test_quarantine_rollback_regression.py",
        "scratch/inspect_seed.py",
        "scratch/populate_sqlite.py",
        "data/db_backup_*.json",
        "static/exports/*.csv",
    ]
    if deleted_list_file.exists():
        for line in deleted_list_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and line not in patterns:
                patterns.append(line)

    removed = 0
    for pat in patterns:
        for match in glob.glob(str(ROOT / pat)):
            p = Path(match)
            try:
                if p.is_dir():
                    shutil.rmtree(p)
                elif p.exists():
                    p.unlink()
                print(f"[DELETED] {p.relative_to(ROOT)}")
                removed += 1
            except Exception as exc:
                print(f"[WARN] Could not delete {p}: {exc}")

    scratch_dir = ROOT / "scratch"
    if scratch_dir.exists() and scratch_dir.is_dir():
        try:
            shutil.rmtree(scratch_dir)
            print("[DELETED] scratch/")
            removed += 1
        except Exception as exc:
            print(f"[WARN] Could not remove scratch/: {exc}")
    print(f"--> Removed {removed} legacy seed/backup/export files.")


def patch_data_exchange():
    candidates = list(ROOT.glob("modules/admin_panel/**/data_exchange*.py"))
    for path in candidates:
        src = path.read_text(encoding="utf-8")
        orig = src

        # 1. Remove hardcoded passwords like Impact@2026! or Admin@12345
        src = re.sub(
            r"['\"]Impact@2026!['\"]",
            "os.environ.get('ADMIN_EXCHANGE_PASSWORD', '')",
            src,
        )
        src = re.sub(
            r"['\"]Admin@12345['\"]",
            "os.environ.get('ADMIN_INITIAL_PASSWORD', '')",
            src,
        )
        if "os.environ.get(" in src and "import os" not in src:
            src = "import os\n" + src

        # 2. Guard import & master_sync views so crawled data is export-only and Master Sync is blocked
        guard_marker = "# [STRICT_EXPORT_ONLY_GUARD]"
        if guard_marker not in src:
            src = re.sub(
                r"(def\s+\w*import\w*\s*\(\s*request\b[^)]*\)\s*:)",
                r"\1\n    " + guard_marker + "\n"
                r"    from django.http import HttpResponseForbidden\n"
                r"    return HttpResponseForbidden('CSV/JSON import for crawled records is disabled. All records must come from verified live crawls.')",
                src,
            )
            src = re.sub(
                r"(def\s+\w*master_sync\w*\s*\(\s*request\b[^)]*\)\s*:)",
                r"\1\n    " + guard_marker + "\n"
                r"    from django.http import HttpResponseForbidden\n"
                r"    return HttpResponseForbidden('Master Sync backup re-import is permanently disabled to protect database integrity.')",
                src,
            )

        if src != orig:
            path.write_text(src, encoding="utf-8")
            print(f"[PATCHED] {path.relative_to(ROOT)} (removed hardcoded password, disabled Master Sync & CSV/JSON import)")


def patch_job_views():
    candidates = list(ROOT.glob("modules/admin_panel/**/job*views*.py"))
    for path in candidates:
        src = path.read_text(encoding="utf-8")
        orig = src

        # Prevent setting status='ACTIVE' by hand in admin job edit POST handlers; allow only CLOSED / INACTIVE
        guard_marker = "# [CLOSE_ONLY_JOB_EDIT_GUARD]"
        if guard_marker not in src and "request.POST" in src:
            src = re.sub(
                r"(request\.POST\.get\(\s*['\"]status['\"][^)]*\))",
                r"('CLOSED' if \1 in ('CLOSED', 'INACTIVE', 'EXPIRED') else 'INACTIVE')  " + guard_marker,
                src,
            )
        # Replace any verification_status__in lists that include EXTRACTED
        src = re.sub(
            r"\[\s*'PUBLISHED'\s*,\s*'SOURCE_CONFIRMED'\s*,\s*'EXTRACTED'\s*\]",
            "['PUBLISHED', 'SOURCE_CONFIRMED']",
            src,
        )
        if src != orig:
            path.write_text(src, encoding="utf-8")
            print(f"[PATCHED] {path.relative_to(ROOT)} (enforced close-only job edit & verified status rule)")


def patch_extracted_status_in_views():
    for path in list(ROOT.glob("modules/**/*.py")):
        if path.name in ("verification_service.py", "purge_fake_data.py", "crawler.py"):
            continue
        src = path.read_text(encoding="utf-8")
        orig = src
        src = re.sub(
            r"\[\s*'PUBLISHED'\s*,\s*'SOURCE_CONFIRMED'\s*,\s*'EXTRACTED'\s*\]",
            "['PUBLISHED', 'SOURCE_CONFIRMED']",
            src,
        )
        if src != orig:
            path.write_text(src, encoding="utf-8")
            print(f"[PATCHED] {path.relative_to(ROOT)} (removed EXTRACTED from verified filter)")


if __name__ == "__main__":
    delete_legacy_files()
    patch_data_exchange()
    patch_job_views()
    patch_extracted_status_in_views()
    print("[OK] Project-wide integrity patches applied.")
