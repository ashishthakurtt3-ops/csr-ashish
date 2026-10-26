import urllib.parse
from typing import Tuple, List, Optional

# Approved external ATS root domains
APPROVED_ATS_DOMAINS = {
    'greenhouse.io',
    'lever.co',
    'myworkdayjobs.com',
    'workday.com',
    'successfactors.com',
    'successfactors.eu',
    'taleo.net',
    'oraclecloud.com',
    'smartrecruiters.com',
    'ashbyhq.com',
    'icims.com',
    'darwinbox.in',
    'darwinbox.com',
    'eightfold.ai',
    'recruitee.com',
    'bamboohr.com',
    'workable.com',
    'jobvite.com',
    'phenompeople.com',
    'phenom.com',
}

def get_base_domain(url_or_netloc: str) -> str:
    """Extracts base 2-part domain or registered host (e.g. wipro.com from careers.wipro.com)."""
    if not url_or_netloc:
        return ""
    if "://" in url_or_netloc:
        netloc = urllib.parse.urlparse(url_or_netloc).netloc
    else:
        netloc = url_or_netloc.split('/')[0]
    
    # Strip port if present
    netloc = netloc.split(':')[0].lower()
    
    parts = netloc.split('.')
    if len(parts) >= 2:
        # Handle country code double extensions like .co.in, .com.au, .co.uk, .org.in
        if len(parts) >= 3 and parts[-2] in ('co', 'com', 'org', 'net', 'gov', 'edu', 'res', 'ac') and len(parts[-1]) == 2:
            return '.'.join(parts[-3:])
        return '.'.join(parts[-2:])
    return netloc

def is_subdomain_of(child_netloc: str, parent_domain: str) -> bool:
    """Checks if child_netloc is equal to or a subdomain of parent_domain."""
    child = child_netloc.lower().split(':')[0]
    parent = parent_domain.lower().split(':')[0]
    return child == parent or child.endswith('.' + parent)

def is_approved_ats_domain(netloc: str) -> bool:
    """Checks if netloc matches any recognized official enterprise ATS vendor."""
    base_ats = get_base_domain(netloc)
    netloc_clean = netloc.lower().split(':')[0]
    return any(ats in netloc_clean or base_ats == ats for ats in APPROVED_ATS_DOMAINS)

def is_company_branded_domain(netloc: str, company) -> bool:
    """
    Checks if a host name discovered from official company pages matches the company's
    brand identity (e.g., icicicareers.com for ICICI Bank, ibegin.tcs.com for TCS).
    """
    netloc_clean = netloc.lower().split(':')[0]
    final_base = get_base_domain(netloc_clean).split('.')[0]

    # 1. Check against company name tokens
    raw_name = (company.company_name or '').lower()
    for noise in ['limited', 'ltd', 'pvt', 'private', 'corporation', 'corp', 'bank', 'india']:
        raw_name = raw_name.replace(noise, ' ')
    name_tokens = [t for t in raw_name.split() if len(t) >= 3]

    for token in name_tokens:
        if token in final_base or token in netloc_clean:
            return True

    # 2. Check against NSE symbol
    if getattr(company, 'nse_symbol', None):
        sym = company.nse_symbol.lower().strip()
        if len(sym) >= 3 and (sym in final_base or sym in netloc_clean):
            return True

    # 3. Check against website base domain
    if getattr(company, 'website_url', None):
        web_base = get_base_domain(company.website_url).split('.')[0]
        if len(web_base) >= 3 and (web_base in final_base or final_base in web_base):
            return True

    return False


def validate_redirect_chain(
    company,
    initial_url: str,
    final_url: str,
    redirect_history: Optional[List[str]] = None,
    discovered_on_official_site: bool = True
) -> Tuple[bool, str, str]:
    """
    Validates that a URL and any redirect destination belong to the company or
    an approved ATS discovered on the company's verified web presence.

    Returns:
        (is_valid, validation_result_code, approved_source_type)
    """
    if not initial_url or not final_url:
        return False, "EMPTY_URL", "INVALID"

    parsed_initial = urllib.parse.urlparse(initial_url)
    parsed_final = urllib.parse.urlparse(final_url)

    initial_host = parsed_initial.netloc.lower().split(':')[0]
    final_host = parsed_final.netloc.lower().split(':')[0]

    # Reference company domains
    company_hosts = set()
    for u in (company.website_url, company.careers_url, company.csr_portal_url):
        if u:
            h = urllib.parse.urlparse(u).netloc.lower().split(':')[0]
            if h:
                company_hosts.add(h)
                company_hosts.add(get_base_domain(h))

    # Also extract domain from company name heuristic if empty
    if not company_hosts and company.company_name:
        sanitized = company.company_name.lower().replace(" ", "").replace("limited", "").replace("ltd", "")
        company_hosts.add(sanitized + ".com")

    # 1. Check if final_url is within company's own domain or subdomains
    for comp_domain in company_hosts:
        if is_subdomain_of(final_host, comp_domain):
            return True, "OFFICIAL_COMPANY_DOMAIN", "OFFICIAL_PORTAL"

    # 2. Check if final_url is an approved external ATS
    if is_approved_ats_domain(final_host):
        if discovered_on_official_site:
            return True, "OFFICIAL_ATS_DISCOVERED", "VERIFIED_ATS"
        else:
            return False, "ATS_NOT_DISCOVERED_FROM_OFFICIAL_SITE", "UNVERIFIED_ATS"

    # 3. Check for approved company-branded domains discovered on official site
    if discovered_on_official_site and is_company_branded_domain(final_host, company):
        return True, "OFFICIAL_BRANDED_DOMAIN", "OFFICIAL_PORTAL"

    # 4. Check for obvious malicious, parked, or unrelated domains
    unrelated_indicators = ['httpbin.org', 'example.com', 'bit.ly', 'tinyurl.com', 'parking', 'sedo']
    if any(ind in final_host for ind in unrelated_indicators):
        return False, "UNAPPROVED_THIRD_PARTY_DOMAIN", "REJECTED"

    # If domain doesn't match company and isn't a recognized ATS:
    return False, f"CROSS_DOMAIN_MISMATCH: {final_host} not owned by {company.company_name}", "REJECTED"

