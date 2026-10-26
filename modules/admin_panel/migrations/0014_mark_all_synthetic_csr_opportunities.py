"""
Phase 1 data migration: mark all remaining CSROpportunity rows that lack
a genuine submission deadline or application mechanism as INVALID_SYNTHETIC.

Criteria for INVALID_SYNTHETIC:
  - status == 'OPEN'
  - submission_deadline is NULL or empty (genuine calls for proposal/RFP always specify a submission deadline)
"""

from django.db import migrations


def mark_all_synthetic_opportunities(apps, schema_editor):
    CSROpportunity = apps.get_model("admin_panel", "CSROpportunity")

    # Target all OPEN opportunities without a genuine deadline
    qs = CSROpportunity.objects.filter(status="OPEN")
    synthetic_ids = []
    for opp in qs.only("opp_id", "submission_deadline"):
        dl = (opp.submission_deadline or "").strip()
        if not dl:
            synthetic_ids.append(opp.opp_id)

    if synthetic_ids:
        updated = CSROpportunity.objects.filter(opp_id__in=synthetic_ids).update(
            status="INVALID_SYNTHETIC"
        )
        print(f"  [0014] Marked {updated} synthetic CSROpportunity rows as INVALID_SYNTHETIC.")


def reverse_mark(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("admin_panel", "0013_mark_synthetic_csr_opportunities"),
    ]

    operations = [
        migrations.RunPython(
            mark_all_synthetic_opportunities,
            reverse_code=reverse_mark,
        ),
    ]
