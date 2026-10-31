import threading
from contextlib import contextmanager
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from modules.admin_panel.models import Job, CSRProject, CSROpportunity, Company

_tls = threading.local()


def are_signals_paused() -> bool:
    return getattr(_tls, 'paused', False)


@contextmanager
def pause_snapshot_signals():
    """
    Context manager to pause snapshot synchronization signals during bulk operations
    (e.g., crawler ingestion, data imports, bulk updates).
    Accumulates modified company_ids and recomputes CompanyMetrics exactly ONCE per company at exit.
    """
    prev_paused = getattr(_tls, 'paused', False)
    prev_companies = getattr(_tls, 'modified_companies', None)
    _tls.paused = True
    _tls.modified_companies = set()
    try:
        yield _tls.modified_companies
    finally:
        companies_to_sync = _tls.modified_companies
        _tls.paused = prev_paused
        _tls.modified_companies = prev_companies
        if not prev_paused and companies_to_sync:
            from modules.admin_panel.snapshot_service import sync_company_metrics_event
            for cid in companies_to_sync:
                try:
                    sync_company_metrics_event(cid)
                except Exception:
                    pass


@receiver(post_save, sender=Job)
@receiver(post_delete, sender=Job)
def on_job_changed(sender, instance, **kwargs):
    if are_signals_paused():
        if instance.company_id and hasattr(_tls, 'modified_companies') and _tls.modified_companies is not None:
            _tls.modified_companies.add(instance.company_id)
        return
    try:
        from modules.admin_panel.snapshot_service import sync_company_metrics_event
        if instance.company_id:
            sync_company_metrics_event(instance.company_id)
    except Exception:
        pass


@receiver(post_save, sender=CSRProject)
@receiver(post_delete, sender=CSRProject)
def on_csr_project_changed(sender, instance, **kwargs):
    if are_signals_paused():
        if instance.company_id and hasattr(_tls, 'modified_companies') and _tls.modified_companies is not None:
            _tls.modified_companies.add(instance.company_id)
        return
    try:
        from modules.admin_panel.snapshot_service import sync_company_metrics_event
        if instance.company_id:
            sync_company_metrics_event(instance.company_id)
    except Exception:
        pass


@receiver(post_save, sender=CSROpportunity)
@receiver(post_delete, sender=CSROpportunity)
def on_opportunity_changed(sender, instance, **kwargs):
    if are_signals_paused():
        if instance.company_id and hasattr(_tls, 'modified_companies') and _tls.modified_companies is not None:
            _tls.modified_companies.add(instance.company_id)
        return
    try:
        from modules.admin_panel.snapshot_service import sync_company_metrics_event
        if instance.company_id:
            sync_company_metrics_event(instance.company_id)
    except Exception:
        pass


@receiver(post_save, sender=Company)
def on_company_changed(sender, instance, **kwargs):
    if are_signals_paused():
        if instance.company_id and hasattr(_tls, 'modified_companies') and _tls.modified_companies is not None:
            _tls.modified_companies.add(instance.company_id)
        return
    try:
        from modules.admin_panel.snapshot_service import sync_company_metrics_event
        if instance.company_id:
            sync_company_metrics_event(instance.company_id)
    except Exception:
        pass
