import os
import csv
from urllib.parse import urlparse
from django.core.management.base import BaseCommand
from modules.admin_panel.models import Company, Job


def strip_url(url: str) -> str:
    """Strips query parameters, fragment, and trailing slash, returning lowercased base URL."""
    if not url:
        return ""
    parsed = urlparse(url.strip())
    # Rebuild scheme + netloc + path
    clean_path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{clean_path}".lower()


def detect_ats_type(company: Company, sample_urls: list) -> str:
    """Infers ATS type from company profile or job URLs."""
    if company.ats_platform:
        return company.ats_platform
    combined = " ".join([company.careers_url or "", company.website_url or ""] + sample_urls).lower()
    if "lever.co" in combined:
        return "Lever"
    if "greenhouse.io" in combined:
        return "Greenhouse"
    if "myworkdayjobs.com" in combined or "workday" in combined:
        return "Workday"
    if "darwinbox" in combined:
        return "Darwinbox"
    if any(k in combined for k in ["successfactors", "mahindracareers.com", "tatamotorscareers"]):
        return "SuccessFactors"
    if "smartrecruiters.com" in combined:
        return "SmartRecruiters"
    if "oraclecloud.com" in combined or "taleo.net" in combined:
        return "Oracle HCM"
    if "keka.com" in combined:
        return "Keka"
    if "zohorecruit" in combined:
        return "Zoho Recruit"
    if "icims.com" in combined:
        return "iCIMS"
    if "ashbyhq.com" in combined:
        return "Ashby"
    return "Custom / None"


class Command(BaseCommand):
    help = "Audit baseline link quality across all companies: Direct vs Listing-Like URLs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Path to CSV output file (defaults to reports/audit_link_quality_baseline.csv)",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting Link Quality Audit across all companies..."))

        reports_dir = os.path.join(os.getcwd(), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        csv_path = options["output"] or os.path.join(reports_dir, "audit_link_quality_baseline.csv")

        companies = Company.objects.all().prefetch_related("jobs").order_by("company_name")
        rows = []

        total_active_jobs_all = 0
        total_direct_all = 0
        total_listing_like_all = 0

        for comp in companies:
            active_jobs = list(comp.jobs.filter(status="ACTIVE"))
            total_jobs = len(active_jobs)
            if total_jobs == 0:
                continue

            total_active_jobs_all += total_jobs

            stripped_careers = strip_url(comp.careers_url)
            stripped_website = strip_url(comp.website_url)

            # Map stripped URL -> count of jobs sharing that stripped URL
            url_counts = {}
            for j in active_jobs:
                s_url = strip_url(j.application_url)
                url_counts[s_url] = url_counts.get(s_url, 0) + 1

            direct_count = 0
            listing_like_count = 0
            sample_urls = []

            for j in active_jobs:
                raw_url = (j.application_url or "").strip()
                if raw_url:
                    sample_urls.append(raw_url)
                s_url = strip_url(raw_url)

                is_listing_like = False
                # Rule 1: Empty or equals company careers/website URL
                if not s_url or s_url == stripped_careers or (stripped_website and s_url == stripped_website):
                    is_listing_like = True
                # Rule 2: Shared by 2+ jobs of this company
                elif url_counts.get(s_url, 0) >= 2:
                    is_listing_like = True
                # Rule 3: Contains Chrome yellow-highlight fragment
                elif "#:~:text=" in raw_url:
                    is_listing_like = True

                if is_listing_like:
                    listing_like_count += 1
                else:
                    direct_count += 1

            total_direct_all += direct_count
            total_listing_like_all += listing_like_count

            pct_direct = (direct_count / total_jobs * 100.0) if total_jobs > 0 else 0.0
            ats_type = detect_ats_type(comp, sample_urls[:10])

            rows.append({
                "company_id": comp.company_id,
                "company_name": comp.company_name,
                "ats_type": ats_type,
                "total_jobs": total_jobs,
                "direct_jobs": direct_count,
                "listing_like_jobs": listing_like_count,
                "pct_direct": pct_direct,
            })

        # Sort worst first (lowest % direct), then highest total jobs
        rows.sort(key=lambda r: (r["pct_direct"], -r["total_jobs"]))

        # Output table to terminal
        self.stdout.write("\n" + "=" * 110)
        self.stdout.write(f"{'Company Name':<38} | {'ATS Type':<16} | {'Total':<6} | {'Direct':<6} | {'Listing':<7} | {'% Direct':<8}")
        self.stdout.write("-" * 110)

        for r in rows:
            cname = r["company_name"][:36]
            self.stdout.write(
                f"{cname:<38} | {r['ats_type']:<16} | {r['total_jobs']:<6} | {r['direct_jobs']:<6} | {r['listing_like_jobs']:<7} | {r['pct_direct']:>7.1f}%"
            )

        self.stdout.write("=" * 110)

        # Print Totals
        overall_pct = (total_direct_all / total_active_jobs_all * 100.0) if total_active_jobs_all > 0 else 0.0
        self.stdout.write(self.style.SUCCESS(f"\nAUDIT BASELINE TOTALS:"))
        self.stdout.write(f"Total Companies with Active Jobs: {len(rows)}")
        self.stdout.write(f"Total Active Jobs:                {total_active_jobs_all}")
        self.stdout.write(f"Total Direct-Looking Jobs:        {total_direct_all}")
        self.stdout.write(f"Total Listing-Like Jobs:          {total_listing_like_all}")
        self.stdout.write(f"Overall Direct Percentage:        {overall_pct:.2f}%\n")

        # Write CSV
        with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Company ID", "Company Name", "ATS Type", "Total Active Jobs",
                "Direct Looking Jobs", "Listing Like Jobs", "Percent Direct"
            ])
            for r in rows:
                writer.writerow([
                    r["company_id"], r["company_name"], r["ats_type"],
                    r["total_jobs"], r["direct_jobs"], r["listing_like_jobs"],
                    f"{r['pct_direct']:.2f}%"
                ])

        self.stdout.write(self.style.SUCCESS(f"Saved audit report CSV to: {csv_path}\n"))
