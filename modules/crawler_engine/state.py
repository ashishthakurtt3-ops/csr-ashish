from django.utils import timezone

CRAWL_TASK_STATE = {
    "is_running": False,
    "start_time": None,
    "stats": {
        "companies_requested": 0,
        "companies_crawled": 0,
        "fetch_failures": 0,
        "blocked": 0,
        "dns_failures": 0,
        "jobs_discovered": 0,
        "new_jobs": 0,
        "updated_jobs": 0,
        "expired_jobs": 0,
        "csr_pages_found": 0,
        "csr_pdfs": 0,
        "csr_projects": 0,
        "csr_opportunities": 0,
        "contacts_found": 0
    },
    "current_company": None,
    "events": []
}

def log_event(category, status_badge, msg, company_id=None, company_name=None, action="CRAWLING"):
    event = {
        'company_id': company_id or 'SYSTEM',
        'company_name': company_name or 'System Event',
        'nse_symbol': '—',
        'sector': '—',
        'target_url': '',
        'action': action,
        'http_status': 'N/A',
        'response_time_ms': 0,
        'timestamp': timezone.now().isoformat(),
        'extracted_summary': msg,
        'category': category,
        'status_badge': status_badge
    }
    CRAWL_TASK_STATE["events"].insert(0, event)
    # Keep only the latest 30 events in memory
    CRAWL_TASK_STATE["events"] = CRAWL_TASK_STATE["events"][:30]
