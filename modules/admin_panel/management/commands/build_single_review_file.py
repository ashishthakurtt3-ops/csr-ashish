import os
import csv
from datetime import datetime
from typing import Dict, Any, List, Set, Optional

from django.core.management.base import BaseCommand, CommandError

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.formatting.rule import CellIsRule
except ImportError:
    openpyxl = None


class Command(BaseCommand):
    help = (
        "Builds ONE single consolidated review workbook (company_review_single.xlsx) "
        "from an existing crawl_review run folder in strictly read-only mode."
    )

    REQUIRED_PAGE_CATEGORIES = ["JOBS", "CSR", "SUSTAINABILITY", "ANNUAL_REPORT", "NGO_PARTNERSHIP"]

    def add_arguments(self, parser):
        parser.add_argument(
            "--run",
            type=str,
            required=True,
            help="Path to the crawl_review run folder (e.g. exports/crawl_review/20261023_112755)",
        )

    def handle(self, *args, **options):
        if openpyxl is None:
            raise CommandError("openpyxl is required to generate the review workbook. Please install openpyxl.")

        run_dir = options["run"]
        if not os.path.isabs(run_dir):
            run_dir = os.path.abspath(run_dir)

        if not os.path.isdir(run_dir):
            raise CommandError(f"Run directory does not exist: {run_dir}")

        companies_csv = os.path.join(run_dir, "Companies.csv")
        if not os.path.exists(companies_csv):
            raise CommandError(f"Missing required Companies.csv in run directory: {run_dir}")

        # ----------------------------------------------------------------------
        # 1. Read files strictly from the run directory
        # ----------------------------------------------------------------------
        companies_data = self._read_csv_dicts(companies_csv)
        pages_data = self._read_csv_dicts(os.path.join(run_dir, "Pages.csv"))
        jobs_data = self._read_csv_dicts(os.path.join(run_dir, "Jobs.csv"))
        csr_data = self._read_csv_dicts(os.path.join(run_dir, "CSR.csv"))
        contacts_data = self._read_csv_dicts(os.path.join(run_dir, "Contacts.csv"))
        warnings_data = self._read_csv_dicts(os.path.join(run_dir, "Warnings.csv"))
        readme_info = self._read_readme_info(os.path.join(run_dir, "README.csv"), os.path.join(run_dir, "run_log.txt"), run_dir)

        # ----------------------------------------------------------------------
        # 2. Build rows company by company in order
        # Order: COMPANY, PAGE, JOB, CSR, CONTACT, WARNING
        # ----------------------------------------------------------------------
        review_rows = []
        counts_summary = {
            "COMPANY": 0,
            "PAGE": 0,
            "JOB": 0,
            "CSR": 0,
            "CONTACT": 0,
            "WARNING": 0,
        }
        company_stats_list = []
        verify_this_count = 0

        # Group data by company_id preserving run order
        pages_by_company = self._group_by_company(pages_data)
        jobs_by_company = self._group_by_company(jobs_data)
        csr_by_company = self._group_by_company(csr_data)
        contacts_by_company = self._group_by_company(contacts_data)
        warnings_by_company = self._group_by_company(warnings_data)

        # Pre-scan jobs for generic listing link warnings
        generic_listing_urls_by_company: Dict[str, Set[str]] = {}
        for comp_id, c_warnings in warnings_by_company.items():
            generic_listing_urls_by_company[comp_id] = {
                (w.get("url") or "").strip().rstrip("/")
                for w in c_warnings
                if w.get("warning_type") == "GENERIC_LISTING_LINK" and w.get("url")
            }

        for comp_idx, comp in enumerate(companies_data, 1):
            comp_id = (comp.get("company_id") or "").strip()
            comp_name = (comp.get("company_name") or "").strip()
            website_url = (comp.get("website_url") or "").strip()

            c_pages = pages_by_company.get(comp_id, [])
            c_jobs = jobs_by_company.get(comp_id, [])
            c_csr = csr_by_company.get(comp_id, [])
            c_contacts = contacts_by_company.get(comp_id, [])
            c_warnings = warnings_by_company.get(comp_id, [])

            c_generic_urls = generic_listing_urls_by_company.get(comp_id, set())

            # ------------------------------------------------------------------
            # (A) COMPANY Row
            # ------------------------------------------------------------------
            crawl_res = comp.get("crawl_result", "")
            partial_reason = comp.get("reason", "")
            time_taken = comp.get("time_taken_seconds", "")
            ai_calls = comp.get("ai_calls", "0")
            cache_hits = comp.get("cache_hits", "0")
            classifier_name = readme_info.get("classifier", "TwoStagePageClassifier")

            # Determine real vs generic jobs count
            real_jobs_count = 0
            generic_jobs_count = 0
            for j in c_jobs:
                j_url = (j.get("apply_source_url") or "").strip().rstrip("/")
                is_gen = False
                if j_url and j_url in c_generic_urls:
                    is_gen = True
                elif j_url and j_url == website_url.rstrip("/"):
                    is_gen = True
                if is_gen:
                    generic_jobs_count += 1
                else:
                    real_jobs_count += 1

            summary_title = (
                f"Result: {crawl_res} | Pages: {len(c_pages)} | "
                f"Real Jobs: {real_jobs_count} | Generic Jobs: {generic_jobs_count} | "
                f"CSR: {len(c_csr)}"
            )
            detail_snippet = (
                f"Crawl Result: {crawl_res} in {time_taken}s | "
                f"Reason: {partial_reason} | "
                f"Pages Found: {len(c_pages)} | Real Jobs: {real_jobs_count} | Generic Links: {generic_jobs_count} | "
                f"CSR Items: {len(c_csr)} | Contacts: {len(c_contacts)} | Warnings: {len(c_warnings)} | "
                f"AI Calls: {ai_calls} | Cache Hits: {cache_hits} | "
                f"Classifier: {classifier_name}"
            )

            company_row = {
                "company_no": comp_idx,
                "company_id": comp_id,
                "company_name": comp_name,
                "website_url": website_url,
                "record_type": "COMPANY",
                "category": "",
                "title_or_name": summary_title,
                "url": website_url,
                "how_found": "",
                "ats_platform_or_doc_type": "",
                "location_or_geography": "",
                "department_or_theme": "",
                "experience_or_FY": "",
                "id_or_budget": "",
                "ai_confidence_and_reason": "",
                "evidence_snippet": detail_snippet[:300],
                "warning": "",
                "VERIFY_THIS": "",
                "CHECK": "",
                "CORRECT_VALUE": "",
                "NOTES": "",
            }
            review_rows.append(company_row)
            counts_summary["COMPANY"] += 1

            # ------------------------------------------------------------------
            # (B) PAGE Rows
            # ------------------------------------------------------------------
            # Build map of existing categories for this company
            found_categories = set()
            for p in c_pages:
                cat = (p.get("category") or "").strip().upper()
                found_categories.add(cat)
                
                # Format AI confidence & reason
                ai_conf = (p.get("ai_confidence") or "").strip()
                ai_reas = (p.get("ai_reason") or "").strip()
                if ai_conf or ai_reas:
                    ai_conf_reason = f"[{ai_conf}] {ai_reas}".strip()
                else:
                    ai_conf_reason = "rules only"

                p_evidence = (p.get("menu_path") or p.get("link_text") or "").strip()
                p_url = (p.get("chosen_url") or "").strip()

                page_row = {
                    "company_no": comp_idx,
                    "company_id": comp_id,
                    "company_name": comp_name,
                    "website_url": website_url,
                    "record_type": "PAGE",
                    "category": cat,
                    "title_or_name": p.get("link_text") or p.get("category") or "",
                    "url": p_url,
                    "how_found": p.get("how_found") or "",
                    "ats_platform_or_doc_type": p.get("ats_platform") or "",
                    "location_or_geography": "",
                    "department_or_theme": "",
                    "experience_or_FY": "",
                    "id_or_budget": "",
                    "ai_confidence_and_reason": ai_conf_reason,
                    "evidence_snippet": p_evidence[:300],
                    "warning": "",
                    "VERIFY_THIS": "YES",
                    "CHECK": "",
                    "CORRECT_VALUE": "",
                    "NOTES": "",
                }
                review_rows.append(page_row)
                counts_summary["PAGE"] += 1
                verify_this_count += 1

            # Check for NOT FOUND page categories
            for req_cat in self.REQUIRED_PAGE_CATEGORIES:
                if req_cat not in found_categories:
                    not_found_row = {
                        "company_no": comp_idx,
                        "company_id": comp_id,
                        "company_name": comp_name,
                        "website_url": website_url,
                        "record_type": "PAGE",
                        "category": req_cat,
                        "title_or_name": "NOT FOUND",
                        "url": "",
                        "how_found": "",
                        "ats_platform_or_doc_type": "",
                        "location_or_geography": "",
                        "department_or_theme": "",
                        "experience_or_FY": "",
                        "id_or_budget": "",
                        "ai_confidence_and_reason": "rules only",
                        "evidence_snippet": f"No {req_cat} portal link identified during crawl.",
                        "warning": "PORTAL_NOT_FOUND",
                        "VERIFY_THIS": "YES",
                        "CHECK": "",
                        "CORRECT_VALUE": "",
                        "NOTES": "",
                    }
                    review_rows.append(not_found_row)
                    counts_summary["PAGE"] += 1
                    verify_this_count += 1

            # ------------------------------------------------------------------
            # (C) JOB Rows
            # ------------------------------------------------------------------
            for job_idx, j in enumerate(c_jobs):
                j_url = (j.get("apply_source_url") or "").strip()
                j_norm_url = j_url.rstrip("/")

                # Determine if generic listing link
                warning_label = ""
                if j_norm_url and (j_norm_url in c_generic_urls or j_norm_url == website_url.rstrip("/")):
                    warning_label = "GENERIC_LISTING_LINK"

                # Priority sample: first 5 jobs + any job with a warning
                is_verify_sample = (job_idx < 5) or bool(warning_label)
                verify_val = "YES" if is_verify_sample else ""
                if is_verify_sample:
                    verify_this_count += 1

                job_row = {
                    "company_no": comp_idx,
                    "company_id": comp_id,
                    "company_name": comp_name,
                    "website_url": website_url,
                    "record_type": "JOB",
                    "category": j.get("department") or "",
                    "title_or_name": j.get("job_title") or "",
                    "url": j_url,
                    "how_found": j.get("extraction_strategy_used") or "",
                    "ats_platform_or_doc_type": j.get("ats_platform") or "",
                    "location_or_geography": j.get("location") or "",
                    "department_or_theme": j.get("department") or "",
                    "experience_or_FY": j.get("experience") or "",
                    "id_or_budget": j.get("external_job_id") or "",
                    "ai_confidence_and_reason": "",
                    "evidence_snippet": (j.get("description_snippet") or "")[:300],
                    "warning": warning_label,
                    "VERIFY_THIS": verify_val,
                    "CHECK": "",
                    "CORRECT_VALUE": "",
                    "NOTES": "",
                }
                review_rows.append(job_row)
                counts_summary["JOB"] += 1

            # ------------------------------------------------------------------
            # (D) CSR Rows
            # ------------------------------------------------------------------
            for csr_item in c_csr:
                doc_type = (csr_item.get("document_type") or "").strip()
                page_no = (csr_item.get("page_number") or "").strip()
                if doc_type and page_no:
                    ats_or_doc = f"{doc_type} (p. {page_no})"
                else:
                    ats_or_doc = doc_type

                csr_row = {
                    "company_no": comp_idx,
                    "company_id": comp_id,
                    "company_name": comp_name,
                    "website_url": website_url,
                    "record_type": "CSR",
                    "category": csr_item.get("theme") or "",
                    "title_or_name": csr_item.get("project_or_disclosure_name") or "",
                    "url": csr_item.get("source_url") or "",
                    "how_found": "extraction",
                    "ats_platform_or_doc_type": ats_or_doc,
                    "location_or_geography": csr_item.get("geography") or "",
                    "department_or_theme": csr_item.get("theme") or "",
                    "experience_or_FY": csr_item.get("financial_year") or "",
                    "id_or_budget": csr_item.get("budget") or "",
                    "ai_confidence_and_reason": "",
                    "evidence_snippet": (csr_item.get("evidence_snippet") or "")[:300],
                    "warning": "",
                    "VERIFY_THIS": "YES",
                    "CHECK": "",
                    "CORRECT_VALUE": "",
                    "NOTES": "",
                }
                review_rows.append(csr_row)
                counts_summary["CSR"] += 1
                verify_this_count += 1

            # ------------------------------------------------------------------
            # (E) CONTACT Rows
            # ------------------------------------------------------------------
            for contact in c_contacts:
                c_dept = (contact.get("department") or "").strip()
                # Categorize category as CSR / CAREERS / OTHER
                c_dept_lower = c_dept.lower()
                if "csr" in c_dept_lower or "sustainability" in c_dept_lower:
                    cat_val = "CSR"
                elif "career" in c_dept_lower or "talent" in c_dept_lower or "hr" in c_dept_lower or "recruit" in c_dept_lower:
                    cat_val = "CAREERS"
                else:
                    cat_val = "OTHER"

                contact_val = contact.get("value") or ""
                contact_type = contact.get("contact_type") or ""
                contact_title = f"{contact_type.upper()}: {contact_val}".strip(": ")

                contact_row = {
                    "company_no": comp_idx,
                    "company_id": comp_id,
                    "company_name": comp_name,
                    "website_url": website_url,
                    "record_type": "CONTACT",
                    "category": cat_val,
                    "title_or_name": contact_title,
                    "url": contact.get("source_url") or "",
                    "how_found": "html_contact_extractor",
                    "ats_platform_or_doc_type": "",
                    "location_or_geography": "",
                    "department_or_theme": c_dept,
                    "experience_or_FY": "",
                    "id_or_budget": "",
                    "ai_confidence_and_reason": "",
                    "evidence_snippet": (contact.get("evidence_snippet") or "")[:300],
                    "warning": "",
                    "VERIFY_THIS": "YES",
                    "CHECK": "",
                    "CORRECT_VALUE": "",
                    "NOTES": "",
                }
                review_rows.append(contact_row)
                counts_summary["CONTACT"] += 1
                verify_this_count += 1

            # ------------------------------------------------------------------
            # (F) WARNING Rows
            # Standalone warnings not already represented on JOB or CSR rows
            # ------------------------------------------------------------------
            for warn in c_warnings:
                w_type = warn.get("warning_type", "")
                if w_type == "GENERIC_LISTING_LINK":
                    # Already marked on JOB row
                    continue

                warn_row = {
                    "company_no": comp_idx,
                    "company_id": comp_id,
                    "company_name": comp_name,
                    "website_url": website_url,
                    "record_type": "WARNING",
                    "category": "CRAWL_WARNING",
                    "title_or_name": w_type,
                    "url": warn.get("url") or "",
                    "how_found": "system_guard",
                    "ats_platform_or_doc_type": "",
                    "location_or_geography": "",
                    "department_or_theme": "",
                    "experience_or_FY": "",
                    "id_or_budget": "",
                    "ai_confidence_and_reason": "",
                    "evidence_snippet": (warn.get("details") or warn.get("evidence_snippet") or "")[:300],
                    "warning": w_type,
                    "VERIFY_THIS": "YES",
                    "CHECK": "",
                    "CORRECT_VALUE": "",
                    "NOTES": "",
                }
                review_rows.append(warn_row)
                counts_summary["WARNING"] += 1
                verify_this_count += 1

            company_stats_list.append({
                "company_id": comp_id,
                "company_name": comp_name,
                "pages": len(c_pages),
                "real_jobs": real_jobs_count,
                "generic_jobs": generic_jobs_count,
                "csr": len(c_csr),
                "contacts": len(c_contacts),
                "warnings": len(c_warnings),
            })

        # ----------------------------------------------------------------------
        # 3. Build Excel Workbook
        # ----------------------------------------------------------------------
        out_excel_path = os.path.join(run_dir, "company_review_single.xlsx")
        self._generate_workbook(out_excel_path, review_rows, readme_info, company_stats_list)

        # ----------------------------------------------------------------------
        # 4. Print Terminal Summary
        # ----------------------------------------------------------------------
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 70))
        self.stdout.write(self.style.SUCCESS("ImpactBridge Single Consolidated Review Workbook Generated"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(f"Run Folder:        {run_dir}")
        self.stdout.write(f"Workbook Output:   {out_excel_path}")
        self.stdout.write("-" * 70)
        self.stdout.write("Rows by Record Type:")
        for r_type, count in counts_summary.items():
            self.stdout.write(f"  - {r_type:<10}: {count} rows")
        self.stdout.write(f"  - TOTAL ROWS: {len(review_rows)} rows")
        self.stdout.write("-" * 70)
        self.stdout.write(self.style.WARNING(f"VERIFY_THIS Sample Size: {verify_this_count} rows marked 'YES'"))
        self.stdout.write(self.style.SUCCESS("=" * 70 + "\n"))

    def _read_csv_dicts(self, file_path: str) -> List[Dict[str, str]]:
        if not os.path.exists(file_path):
            return []
        rows = []
        with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)
        return rows

    def _group_by_company(self, rows: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
        grouped = {}
        for r in rows:
            cid = (r.get("company_id") or "").strip()
            if cid:
                if cid not in grouped:
                    grouped[cid] = []
                grouped[cid].append(r)
        return grouped

    def _read_readme_info(self, readme_csv_path: str, run_log_path: str, run_dir: str) -> Dict[str, str]:
        info = {
            "crawl_date": "2026-10-23 UTC",
            "classifier": "TwoStagePageClassifier (OpenRouter Free / Deterministic Fallback + Evidence Gate)",
            "run_folder": os.path.basename(run_dir),
        }
        if os.path.exists(readme_csv_path):
            try:
                with open(readme_csv_path, "r", encoding="utf-8-sig", errors="replace") as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) >= 2:
                            k = row[0].strip()
                            v = row[1].strip()
                            if "Crawl Date" in k:
                                info["crawl_date"] = v
                            elif "Page Classifier" in k:
                                info["classifier"] = v
            except Exception:
                pass
        return info

    def _generate_workbook(
        self,
        excel_path: str,
        review_rows: List[Dict[str, Any]],
        readme_info: Dict[str, str],
        company_stats_list: List[Dict[str, Any]],
    ):
        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # Remove default active sheet

        # Color schemes & Styles
        header_fill = PatternFill(start_color="0B2545", end_color="0B2545", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        link_font = Font(name="Calibri", size=10, color="1D4ED8", underline="single")
        regular_font = Font(name="Calibri", size=10)
        bold_font = Font(name="Calibri", size=10, bold=True)
        wrap_align = Alignment(vertical="top", wrap_text=True)
        center_align = Alignment(horizontal="center", vertical="top")

        thin_side = Side(border_style="thin", color="E2E8F0")
        row_border = Border(top=thin_side, bottom=thin_side, left=thin_side, right=thin_side)

        # Row shading fills
        company_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")  # Shaded dark
        company_font = Font(name="Calibri", size=10, bold=True, color="F8FAFC")
        company_link_font = Font(name="Calibri", size=10, bold=True, color="60A5FA", underline="single")

        page_fill = PatternFill(start_color="F0F9FF", end_color="F0F9FF", fill_type="solid")     # Light blue
        job_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")       # White
        csr_fill = PatternFill(start_color="F0FDF4", end_color="F0FDF4", fill_type="solid")       # Light green
        contact_fill = PatternFill(start_color="FEFCE8", end_color="FEFCE8", fill_type="solid")   # Light yellow
        warning_fill = PatternFill(start_color="FEF2F2", end_color="FEF2F2", fill_type="solid")   # Light red

        columns = [
            "company_no",
            "company_id",
            "company_name",
            "website_url",
            "record_type",
            "category",
            "title_or_name",
            "url",
            "how_found",
            "ats_platform_or_doc_type",
            "location_or_geography",
            "department_or_theme",
            "experience_or_FY",
            "id_or_budget",
            "ai_confidence_and_reason",
            "evidence_snippet",
            "warning",
            "VERIFY_THIS",
            "CHECK",
            "CORRECT_VALUE",
            "NOTES",
        ]

        # ----------------------------------------------------------------------
        # 1. Review Sheet
        # ----------------------------------------------------------------------
        ws_review = wb.create_sheet(title="Review")
        ws_review.append(columns)

        # Freeze Header Row
        ws_review.freeze_panes = "A2"

        # Format Header
        ws_review.row_dimensions[1].height = 28
        for col_idx, col_name in enumerate(columns, 1):
            cell = ws_review.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = row_border

        # Data Validation Dropdown for CHECK
        check_validation = DataValidation(
            type="list",
            formula1='"Correct,Wrong,Missing,Not sure"',
            allow_blank=True,
        )
        check_validation.error ='Your entry is not in the list'
        check_validation.errorTitle = 'Invalid Entry'
        check_validation.prompt = 'Select verification result'
        check_validation.promptTitle = 'Manual Audit'
        ws_review.add_data_validation(check_validation)

        # Append Data Rows
        for r_idx, row_dict in enumerate(review_rows, 2):
            rec_type = row_dict.get("record_type", "")
            ws_review.append([row_dict.get(c, "") for c in columns])

            # Select row fill & styling
            if rec_type == "COMPANY":
                curr_fill = company_fill
                curr_font = company_font
                curr_link_font = company_link_font
                ws_review.row_dimensions[r_idx].height = 24
            elif rec_type == "PAGE":
                curr_fill = page_fill
                curr_font = regular_font
                curr_link_font = link_font
                ws_review.row_dimensions[r_idx].height = 22
            elif rec_type == "JOB":
                curr_fill = job_fill
                curr_font = regular_font
                curr_link_font = link_font
                ws_review.row_dimensions[r_idx].height = 20
            elif rec_type == "CSR":
                curr_fill = csr_fill
                curr_font = regular_font
                curr_link_font = link_font
                ws_review.row_dimensions[r_idx].height = 20
            elif rec_type == "CONTACT":
                curr_fill = contact_fill
                curr_font = regular_font
                curr_link_font = link_font
                ws_review.row_dimensions[r_idx].height = 20
            elif rec_type == "WARNING":
                curr_fill = warning_fill
                curr_font = regular_font
                curr_link_font = link_font
                ws_review.row_dimensions[r_idx].height = 20
            else:
                curr_fill = job_fill
                curr_font = regular_font
                curr_link_font = link_font

            for col_idx, col_name in enumerate(columns, 1):
                cell = ws_review.cell(row=r_idx, column=col_idx)
                cell.fill = curr_fill
                cell.font = curr_font
                cell.border = row_border

                if col_name in ("title_or_name", "evidence_snippet", "ai_confidence_and_reason"):
                    cell.alignment = wrap_align
                elif col_name in ("company_no", "record_type", "category", "VERIFY_THIS", "CHECK"):
                    cell.alignment = center_align
                else:
                    cell.alignment = wrap_align

                # Hyperlinks for url and website_url
                val_str = str(cell.value or "").strip()
                if col_name in ("url", "website_url") and (val_str.startswith("http://") or val_str.startswith("https://")):
                    cell.hyperlink = val_str
                    cell.font = curr_link_font

                # Attach dropdown validation on CHECK (except COMPANY rows)
                if col_name == "CHECK" and rec_type != "COMPANY":
                    check_validation.add(cell)

                # Bold VERIFY_THIS
                if col_name == "VERIFY_THIS" and val_str == "YES":
                    cell.font = Font(name="Calibri", size=10, bold=True, color="DC2626" if rec_type == "COMPANY" else "B91C1C")

        # Set Auto-Filter
        if ws_review.max_row > 1:
            ws_review.auto_filter.ref = f"A1:{get_column_letter(len(columns))}{ws_review.max_row}"

        # Column widths
        column_widths = {
            "company_no": 12,
            "company_id": 18,
            "company_name": 32,
            "website_url": 30,
            "record_type": 14,
            "category": 18,
            "title_or_name": 36,
            "url": 42,
            "how_found": 18,
            "ats_platform_or_doc_type": 22,
            "location_or_geography": 20,
            "department_or_theme": 24,
            "experience_or_FY": 16,
            "id_or_budget": 16,
            "ai_confidence_and_reason": 34,
            "evidence_snippet": 45,
            "warning": 22,
            "VERIFY_THIS": 14,
            "CHECK": 16,
            "CORRECT_VALUE": 32,
            "NOTES": 30,
        }
        for col_idx, col_name in enumerate(columns, 1):
            letter = get_column_letter(col_idx)
            ws_review.column_dimensions[letter].width = column_widths.get(col_name, 18)

        # Conditional formatting on CHECK column:
        # Correct (Green), Wrong (Red), Missing (Orange), Not sure (Grey)
        check_col_letter = get_column_letter(columns.index("CHECK") + 1)
        check_range = f"{check_col_letter}2:{check_col_letter}{ws_review.max_row}"

        green_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
        green_font = Font(color="15803D", bold=True)
        red_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
        red_font = Font(color="B91C1C", bold=True)
        orange_fill = PatternFill(start_color="FFEDD5", end_color="FFEDD5", fill_type="solid")
        orange_font = Font(color="C2410C", bold=True)
        grey_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        grey_font = Font(color="475569", bold=True)

        ws_review.conditional_formatting.add(check_range, CellIsRule(operator="equal", formula=['"Correct"'], fill=green_fill, font=green_font))
        ws_review.conditional_formatting.add(check_range, CellIsRule(operator="equal", formula=['"Wrong"'], fill=red_fill, font=red_font))
        ws_review.conditional_formatting.add(check_range, CellIsRule(operator="equal", formula=['"Missing"'], fill=orange_fill, font=orange_font))
        ws_review.conditional_formatting.add(check_range, CellIsRule(operator="equal", formula=['"Not sure"'], fill=grey_fill, font=grey_font))

        # Page Setup for Printing: Landscape, fit 1 page wide, repeated header row
        ws_review.page_setup.orientation = ws_review.ORIENTATION_LANDSCAPE
        ws_review.page_setup.paperSize = ws_review.PAPERSIZE_A4
        ws_review.sheet_properties.pageSetUpPr.fitToPage = True
        ws_review.page_setup.fitToWidth = 1
        ws_review.page_setup.fitToHeight = 0
        ws_review.print_title_rows = "1:1"

        # ----------------------------------------------------------------------
        # 2. README Sheet
        # ----------------------------------------------------------------------
        ws_readme = wb.create_sheet(title="README")
        ws_readme.column_dimensions["A"].width = 28
        ws_readme.column_dimensions["B"].width = 85

        readme_header_font = Font(name="Calibri", size=14, bold=True, color="0B2545")
        section_font = Font(name="Calibri", size=12, bold=True, color="1E3A8A")

        title_cell = ws_readme.cell(row=1, column=1, value="ImpactBridge™ Crawl Review Master Verification File")
        title_cell.font = readme_header_font

        metadata_lines = [
            ("Run Folder", readme_info.get("run_folder", "")),
            ("Crawl Date & Time", readme_info.get("crawl_date", "")),
            ("Page Classifier", readme_info.get("classifier", "")),
            ("Workbook Type", "Single Flat Consolidated Verification File"),
            ("", ""),
            ("Purpose & How to Use", "This workbook consolidates all crawl results into one single table."),
            ("How to Fill CHECK", "Select 'Correct', 'Wrong', 'Missing', or 'Not sure' from the dropdown in column S."),
            ("How to Fill CORRECT_VALUE", "If a portal link or extracted field is Wrong or Missing, enter the corrected URL/value in column T."),
            ("Notes Column", "Add optional audit comments in column U for subsequent gold verification ingestion."),
            ("", ""),
            ("Guide: How to Verify Each Record Type", ""),
            ("1. PAGE Rows", "Open the link. Verify whether it is the authentic, dedicated corporate page for that category. If 'NOT FOUND', verify whether the company truly lacks that portal or enter the correct URL."),
            ("2. JOB Rows", "Open the link. Confirm it is ONE specific job vacancy with matching title and ID (not a generic landing/search page)."),
            ("3. CSR Rows", "Open the source link. Confirm the web page or PDF snippet really demonstrates this statutory project, grant, or budget figure."),
            ("4. CONTACT Rows", "Confirm the corporate email or phone number is displayed directly on the official company website."),
            ("5. WARNING Rows", "Inspect the crawler diagnostic note (e.g. generic listing fallback, unresolved tenant) and take corrective action if needed."),
            ("", ""),
            ("Crawl Extraction Counts Per Company:", ""),
        ]

        curr_r = 3
        for k, v in metadata_lines:
            ws_readme.cell(row=curr_r, column=1, value=k).font = bold_font if k else regular_font
            ws_readme.cell(row=curr_r, column=2, value=v).font = regular_font
            if k.startswith("Guide:") or k.startswith("Crawl Extraction"):
                ws_readme.cell(row=curr_r, column=1).font = section_font
            curr_r += 1

        # Append company stats table in README
        curr_r += 1
        stats_headers = ["Company ID", "Company Name", "Pages", "Real Jobs", "Generic Jobs", "CSR Items", "Contacts", "Warnings"]
        for c_i, h in enumerate(stats_headers, 1):
            c_cell = ws_readme.cell(row=curr_r, column=c_i, value=h)
            c_cell.font = header_font
            c_cell.fill = header_fill
            c_cell.alignment = center_align

        ws_readme.column_dimensions["C"].width = 12
        ws_readme.column_dimensions["D"].width = 14
        ws_readme.column_dimensions["E"].width = 14
        ws_readme.column_dimensions["F"].width = 14
        ws_readme.column_dimensions["G"].width = 12
        ws_readme.column_dimensions["H"].width = 12

        curr_r += 1
        for s in company_stats_list:
            ws_readme.cell(row=curr_r, column=1, value=s["company_id"]).alignment = center_align
            ws_readme.cell(row=curr_r, column=2, value=s["company_name"])
            ws_readme.cell(row=curr_r, column=3, value=s["pages"]).alignment = center_align
            ws_readme.cell(row=curr_r, column=4, value=s["real_jobs"]).alignment = center_align
            ws_readme.cell(row=curr_r, column=5, value=s["generic_jobs"]).alignment = center_align
            ws_readme.cell(row=curr_r, column=6, value=s["csr"]).alignment = center_align
            ws_readme.cell(row=curr_r, column=7, value=s["contacts"]).alignment = center_align
            ws_readme.cell(row=curr_r, column=8, value=s["warnings"]).alignment = center_align
            curr_r += 1

        # Save workbook to destination
        wb.save(excel_path)
