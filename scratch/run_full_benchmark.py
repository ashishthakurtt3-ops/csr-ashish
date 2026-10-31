import os
import sys
import time
import json
import statistics
import urllib.request
import urllib.error
import gzip

def measure_real_http():
    print("=" * 80)
    print(" 1. REAL HTTP MEASUREMENTS AGAINST LIVE WAITRESS (10 RUNS PER ENDPOINT)")
    print("=" * 80)

    base_url = "http://127.0.0.1:8000"
    endpoints = [
        ("/", "/"),
        ("/stats", "/stats"),
        ("/companies?page=1&page_size=12", "/companies?page=1&page_size=12"),
        ("/companies?limit=5000", "/companies?limit=5000"),
        ("/companies/COMP_TOP200_154/dossier", "/companies/COMP_TOP200_154/dossier"),
        ("/jobs?page=1&page_size=12", "/jobs?page=1&page_size=12"),
        ("/jobs", "/jobs"),
        ("/jobs/6524", "/jobs/6524"),
        ("/csr/projects?page=1&page_size=12", "/csr/projects?page=1&page_size=12"),
        ("/csr/projects?page=1", "/csr/projects?page=1"),
        ("/ngo/matches", "/ngo/matches"),
        ("/static/js/app.min.js", "/static/js/app.min.js"),
        ("/static/css/style.min.css", "/static/css/style.min.css"),
    ]

    http_results = []
    headers = {
        "Accept-Encoding": "gzip, deflate, br",
        "User-Agent": "Mozilla/5.0 Benchmark",
    }

    print(f"{'Endpoint':<36} | {'Min (ms)':<9} | {'Median':<9} | {'Max (ms)':<9} | {'Size KB':<9} | {'Gzip':<6} | {'Status'}")
    print("-" * 92)

    for name, path in endpoints:
        url = base_url + path
        timings = []
        status_code = None
        content_length = 0
        is_gzip = False

        for i in range(10):
            req = urllib.request.Request(url, headers=headers)
            t0 = time.perf_counter()
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    raw_data = resp.read()
                    duration_ms = (time.perf_counter() - t0) * 1000.0
                    timings.append(duration_ms)
                    status_code = resp.status
                    content_length = len(raw_data)
                    ce = resp.headers.get("Content-Encoding", "").lower()
                    is_gzip = "gzip" in ce or "br" in ce
            except Exception as e:
                print(f"Error requesting {url}: {e}")
                timings.append(9999.0)
                status_code = getattr(e, "code", 500)

        min_ms = min(timings)
        med_ms = statistics.median(timings)
        max_ms = max(timings)
        size_kb = content_length / 1024.0

        print(f"{name:<36} | {min_ms:<9.2f} | {med_ms:<9.2f} | {max_ms:<9.2f} | {size_kb:<9.2f} | {('YES' if is_gzip else 'NO'):<6} | {status_code}")

        http_results.append({
            "endpoint": name,
            "min_ms": round(min_ms, 2),
            "median_ms": round(med_ms, 2),
            "max_ms": round(max_ms, 2),
            "size_kb": round(size_kb, 2),
            "gzip": is_gzip,
            "status_code": status_code,
        })

    return http_results

def measure_browser_metrics():
    print("\n" + "=" * 80)
    print(" 2. HEADLESS CHROMIUM PLAYWRIGHT MEASUREMENTS")
    print("=" * 80)

    from playwright.sync_api import sync_playwright

    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 2a. Cold visit (empty browser cache)
        print("--> Running Cold Visit (empty cache)...")
        context_cold = browser.new_context()
        page_cold = context_cold.new_page()

        requests_cold = []
        page_cold.on("request", lambda r: requests_cold.append({
            "url": r.url,
            "method": r.method,
            "resource_type": r.resource_type,
        }))

        t0 = time.perf_counter()
        page_cold.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        # Wait until first data render (stats counter or hero numbers)
        page_cold.wait_for_selector("#statCompanies", timeout=10000)
        time_to_first_data_render_cold = (time.perf_counter() - t0) * 1000.0

        # Tab switches in cold session
        tabs = ["#tab-companies", "#tab-jobs", "#tab-csr", "#tab-matches"]
        for tab_sel in tabs:
            if page_cold.locator(tab_sel).count() > 0:
                page_cold.click(tab_sel)
                page_cold.wait_for_timeout(300)

        # Verify whether /companies?limit=5000 was called
        limit_5000_called = any("limit=5000" in r["url"] for r in requests_cold)
        api_data_requests = [r["url"] for r in requests_cold if any(ep in r["url"] for ep in ["/stats", "/companies", "/jobs", "/csr"])]

        print(f"  Cold Time to First Data Render: {time_to_first_data_render_cold:.2f} ms")
        print(f"  Total Requests on Load: {len(requests_cold)}")
        print(f"  Data Requests on Initial Tab: {len(api_data_requests)} (limit=5000 called: {limit_5000_called})")
        context_cold.close()

        # 2b. Warm visit (repeat visit with browser cache)
        print("\n--> Running Warm Visit (repeat visit)...")
        context_warm = browser.new_context()
        page_warm = context_warm.new_page()

        # Prime cache by visiting once
        page_warm.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        page_warm.wait_for_selector("#statCompanies", timeout=10000)

        # Now measure repeat visit
        requests_warm = []
        page_warm.on("request", lambda r: requests_warm.append({
            "url": r.url,
            "method": r.method,
        }))

        t0_warm = time.perf_counter()
        page_warm.reload(wait_until="networkidle")
        page_warm.wait_for_selector("#statCompanies", timeout=10000)
        time_to_first_data_render_warm = (time.perf_counter() - t0_warm) * 1000.0

        print(f"  Warm Time to First Data Render: {time_to_first_data_render_warm:.2f} ms")
        print(f"  Total Requests on Repeat Load: {len(requests_warm)}")

        context_warm.close()
        browser.close()

        results = {
            "cold_render_ms": round(time_to_first_data_render_cold, 2),
            "cold_requests_count": len(requests_cold),
            "warm_render_ms": round(time_to_first_data_render_warm, 2),
            "warm_requests_count": len(requests_warm),
            "limit_5000_called": limit_5000_called,
        }

    return results

def verify_accuracy_parity():
    print("\n" + "=" * 80)
    print(" 3. ACCURACY RULE & METRIC PARITY CHECK OVER REAL HTTP")
    print("=" * 80)
    base_url = "http://127.0.0.1:8000"

    with urllib.request.urlopen(f"{base_url}/stats") as r:
        stats = json.loads(r.read().decode())

    with urllib.request.urlopen(f"{base_url}/jobs?page=1&page_size=12") as r:
        jobs_list = json.loads(r.read().decode())

    with urllib.request.urlopen(f"{base_url}/") as r:
        html = r.read().decode()

    jobs_tracked_stats = stats.get("jobs_tracked")
    jobs_total_list = jobs_list.get("total")

    # In index.html, check server-rendered values or attributes
    print(f"  /stats jobs_tracked : {jobs_tracked_stats}")
    print(f"  /jobs list total    : {jobs_total_list}")
    parity_ok = (jobs_tracked_stats == jobs_total_list)
    print(f"  Exact Parity (/stats == /jobs): {parity_ok}")

    return {
        "jobs_tracked_stats": jobs_tracked_stats,
        "jobs_total_list": jobs_total_list,
        "parity_ok": parity_ok,
    }

if __name__ == "__main__":
    http_data = measure_real_http()
    browser_data = measure_browser_metrics()
    parity_data = verify_accuracy_parity()

    summary = {
        "http_endpoints": http_data,
        "browser": browser_data,
        "parity": parity_data,
    }

    with open("scratch/real_benchmark_results.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("\n[OK] Full real-HTTP benchmark complete and saved to scratch/real_benchmark_results.json")
