"""
Phase 1 data migration: mark all existing CSROpportunity rows that were
synthetically cloned from CSRProject records as INVALID_SYNTHETIC.

Criteria for "synthetic" (all three must be true):
  - status == 'OPEN'
  - submission_deadline is NULL or empty  (real opportunities always have a deadline)
  - opportunity_type in known synthetic labels OR title starts with "CSR Initiative:" / "CSR Statutory Partnership:"

These rows were created by the crawler to "mirror" every CSRProject as an
opportunity, which is factually wrong — a company's CSR budget allocation is
NOT an open call for NGO applications unless it explicitly says so.

After this migration, these rows will be:
  - Hidden from all public views (public_jobs / public_csr_opportunities filters)
  - Excluded from the prune guard counts
  - Never recreated by the crawler (code removed in Phase 1)
"""

from django.db import migrations


SYNTHETIC_OPP_TYPES = {
    "CSR Project Partnership",
    "CSR Grant / Program",
}

SYNTHETIC_TITLE_PREFIXES = (
    "CSR Initiative:",
    "CSR Statutory Partnership:",
)


def mark_synthetic_opportunities(apps, schema_editor):
    CSROpportunity = apps.get_model("admin_panel", "CSROpportunity")

    qs = CSROpportunity.objects.filter(status="OPEN")

    # Batch-update only the rows that clearly match the synthetic pattern.
    # We use Python-side filtering to be explicit about which rows are touched.
    synthetic_ids = []
    for opp in qs.only("opp_id", "title", "opportunity_type", "submission_deadline"):
        is_synthetic = False

        # Check opportunity_type
        if opp.opportunity_type in SYNTHETIC_OPP_TYPES:
            is_synthetic = True

        # Check title prefix
        if not is_synthetic and opp.title:
            for prefix in SYNTHETIC_TITLE_PREFIXES:
                if opp.title.startswith(prefix):
                    is_synthetic = True
                    break

        # Double-guard: must have no real deadline (synthetic rows never had one)
        if is_synthetic and opp.submission_deadline:
            # Has a real deadline — this might be a genuine opportunity; skip it
            is_synthetic = False

        if is_synthetic:
            synthetic_ids.append(opp.opp_id)

    if synthetic_ids:
        CSROpportunity.objects.filter(opp_id__in=synthetic_ids).update(
            status="INVALID_SYNTHETIC"
        )

    # Log count (visible in --verbosity 2)
    print(f"  [0013] Marked {len(synthetic_ids)} synthetic CSROpportunity rows as INVALID_SYNTHETIC.")


def reverse_mark_synthetic(apps, schema_editor):
    """Reverse: restore INVALID_SYNTHETIC rows back to OPEN (best-effort)."""
    CSROpportunity = apps.get_model("admin_panel", "CSROpportunity")
    CSROpportunity.objects.filter(status="INVALID_SYNTHETIC").update(status="OPEN")


class Migration(migrations.Migration):

    dependencies = [
        ("admin_panel", "0012_companycrawlsummary_direct_percentage_and_more"),
    ]

    operations = [
        migrations.RunPython(
            mark_synthetic_opportunities,
            reverse_code=reverse_mark_synthetic,
        ),
    ]
