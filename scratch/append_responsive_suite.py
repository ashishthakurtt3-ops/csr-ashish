import sys
sys.stdout.reconfigure(encoding='utf-8')

responsive_css = """

/* ==========================================================================
   DAANVEDA BULLETPROOF MULTI-DEVICE RESPONSIVE SUITE (DESKTOP, TABLET, MOBILE)
   ========================================================================== */

/* Universal Reset & Zero-Overflow Contract */
html, body {
  width: 100% !important;
  max-width: 100vw !important;
  overflow-x: hidden !important;
}

*, *::before, *::after {
  box-sizing: border-box;
}

/* Tablet & Mobile Header/Nav Handling (< 1024px) */
@media (max-width: 1023px) {
  .header-inner {
    display: none !important;
  }
  .mobile-header-bar {
    display: flex !important;
  }
  .mobile-bottom-nav {
    display: flex !important;
  }
  .app-bg-glows {
    display: none !important;
  }
  body {
    padding-bottom: 84px !important;
  }
}

/* Tablet & Mobile Views (< 768px) */
@media (max-width: 768px) {
  /* Dashboard Header Clean Wrap */
  .dashboard-header-clean {
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 12px !important;
  }
  .dashboard-header-title {
    width: 100% !important;
    min-width: 0 !important;
  }
  .dashboard-header-actions {
    flex-wrap: wrap !important;
    width: 100% !important;
    justify-content: space-between !important;
    gap: 8px !important;
  }
  .live-data-fetch-card {
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 10px !important;
  }
  .freshness-ticker-bar {
    overflow-x: auto !important;
    max-width: 100% !important;
    -webkit-overflow-scrolling: touch !important;
  }

  /* Horizontal Scrolling Touch Bars */
  .cause-pill-bar,
  .job-category-pills,
  .jobs-nav-pills {
    display: flex !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
    max-width: 100% !important;
    width: 100% !important;
    scrollbar-width: none !important;
    padding-bottom: 6px !important;
  }
  .cause-pill-bar::-webkit-scrollbar,
  .job-category-pills::-webkit-scrollbar,
  .jobs-nav-pills::-webkit-scrollbar {
    display: none !important;
  }

  /* Pricing Section Mobile */
  .pricing-hero {
    margin-bottom: 24px !important;
    padding: 0 8px !important;
  }
  .pricing-headline {
    font-size: 28px !important;
    line-height: 1.2 !important;
    letter-spacing: -0.8px !important;
  }
  .pricing-subtext {
    font-size: 14px !important;
    line-height: 1.5 !important;
    margin-bottom: 20px !important;
  }
  .billing-toggle-pill {
    max-width: 100% !important;
    width: 100% !important;
    justify-content: center !important;
  }
  .cycle-btn {
    flex: 1 !important;
    padding: 8px 10px !important;
    font-size: 12.5px !important;
    justify-content: center !important;
  }

  /* Demo Testing Wallet Card Mobile */
  .portal-wallet-section-card {
    padding: 20px 16px !important;
    border-radius: 20px !important;
  }
  .portal-wallet-section-card > div:first-child {
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 14px !important;
  }
  .portal-wallet-section-card > div:first-child > div:last-child {
    width: 100% !important;
    min-width: 0 !important;
    text-align: center !important;
  }
  .portal-wallet-section-card > div:nth-child(2) {
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 12px !important;
  }
  .portal-wallet-section-card > div:nth-child(2) > div:first-child {
    max-width: 100% !important;
    width: 100% !important;
    min-width: 0 !important;
  }
  .portal-wallet-section-card #btn-inline-recharge {
    width: 100% !important;
    justify-content: center !important;
    height: 44px !important;
  }
  .portal-wallet-section-card > div:nth-child(2) > div:last-child {
    margin-left: 0 !important;
    width: 100% !important;
  }
  .portal-wallet-section-card > div:nth-child(2) > div:last-child button {
    width: 100% !important;
    justify-content: center !important;
    height: 42px !important;
  }

  /* Active Subscription Status Banner Mobile */
  .active-subscription-card {
    padding: 18px 16px !important;
    border-radius: 18px !important;
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 14px !important;
  }
  .active-sub-right {
    width: 100% !important;
    flex-direction: column !important;
    gap: 8px !important;
  }
  .active-sub-right button {
    width: 100% !important;
    justify-content: center !important;
    height: 44px !important;
  }

  /* Pricing Cards Grid on Mobile */
  .pricing-grid {
    grid-template-columns: 1fr !important;
    gap: 20px !important;
    max-width: 100% !important;
    margin-bottom: 32px !important;
  }
  .pricing-card {
    padding: 28px 20px !important;
    border-radius: 24px !important;
  }
  .plan-name {
    font-size: 20px !important;
  }
  .plan-desc {
    font-size: 13px !important;
    min-height: auto !important;
    margin-bottom: 16px !important;
  }
  .plan-price .amount {
    font-size: 38px !important;
  }
  .plan-features {
    font-size: 13px !important;
    gap: 10px !important;
    margin-bottom: 22px !important;
    padding-top: 16px !important;
  }

  /* Plan Comparison Table on Mobile */
  #pricing-comparison-container > div {
    margin-top: 40px !important;
    padding-top: 28px !important;
  }
  #pricing-comparison-container h3 {
    font-size: 22px !important;
  }
  #pricing-comparison-container div[style*="overflow-x:auto"] {
    border-radius: 18px !important;
    -webkit-overflow-scrolling: touch !important;
  }
  #pricing-comparison-container table {
    min-width: 580px !important;
    font-size: 12px !important;
  }
  #pricing-comparison-container th,
  #pricing-comparison-container td {
    padding: 12px 10px !important;
  }
  #pricing-comparison-container tfoot td button {
    padding: 8px 10px !important;
    font-size: 11.5px !important;
    width: 100% !important;
  }

  /* Filter Inputs & Controls on Mobile */
  .search-input-pill,
  input[type="text"].search-box,
  .filter-select-pill,
  select {
    width: 100% !important;
    max-width: 100% !important;
    height: 44px !important;
  }
  .filter-bar,
  .control-bar {
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 10px !important;
  }
}
"""

with open('static/css/style.css', 'r', encoding='utf-8') as f:
    css = f.read()

css += "\n" + responsive_css

with open('static/css/style.css', 'w', encoding='utf-8') as f:
    f.write(css)

print("Appended responsive suite to static/css/style.css successfully!")

