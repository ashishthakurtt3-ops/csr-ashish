import re

google_css = """
/* ==========================================================================
   GOOGLE MATERIAL DESIGN 3 / CLOUD CONSOLE ENTERPRISE HEADER
   ========================================================================== */
.header-nav {
  position: sticky !important;
  top: 0 !important;
  z-index: 1000 !important;
  background: #ffffff !important;
  border-bottom: 1px solid #dadce0 !important;
  box-shadow: 0 1px 2px 0 rgba(60, 64, 67, 0.08), 0 1px 3px 1px rgba(60, 64, 67, 0.04) !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
}

.g-header-container {
  width: 100% !important;
  max-width: 1440px !important;
  margin: 0 auto !important;
  padding: 0 24px !important;
  box-sizing: border-box !important;
}

/* Row 1: Google Top Bar */
.g-top-bar {
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  height: 60px !important;
  border-bottom: 1px solid #f1f3f4 !important;
}

.g-brand-section {
  display: flex !important;
  align-items: center !important;
  gap: 12px !important;
}

.g-brand-link {
  display: flex !important;
  align-items: center !important;
  gap: 10px !important;
  text-decoration: none !important;
}

.g-brand-logo {
  width: 32px !important;
  height: 32px !important;
  border-radius: 8px !important;
  background: #1a73e8 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  color: #ffffff !important;
  box-shadow: 0 1px 3px rgba(26, 115, 232, 0.3) !important;
  flex-shrink: 0 !important;
}
.g-brand-logo svg {
  width: 18px !important;
  height: 18px !important;
  color: #ffffff !important;
}

.g-brand-link .brand-title {
  font-family: -apple-system, BlinkMacSystemFont, "Google Sans", "Segoe UI", Roboto, sans-serif !important;
  font-size: 18px !important;
  font-weight: 600 !important;
  color: #202124 !important;
  letter-spacing: -0.2px !important;
  line-height: 1.2 !important;
}

.g-brand-link .brand-tagline {
  font-size: 11px !important;
  color: #5f6368 !important;
  font-weight: 400 !important;
  letter-spacing: 0 !important;
}

.g-header-badge {
  font-size: 11px !important;
  font-weight: 500 !important;
  color: #1a73e8 !important;
  background: #e8f0fe !important;
  padding: 2px 8px !important;
  border-radius: 4px !important;
  border: 1px solid #d2e3fc !important;
  letter-spacing: 0.2px !important;
  white-space: nowrap !important;
}

.g-v-sep {
  width: 1px !important;
  height: 24px !important;
  background: #dadce0 !important;
  margin: 0 4px !important;
}

/* Google Cloud Style Status / Telemetry */
.g-status-pill {
  display: inline-flex !important;
  align-items: center !important;
  gap: 8px !important;
  padding: 5px 12px !important;
  background: #f8fafd !important;
  border: 1px solid #dadce0 !important;
  border-radius: 18px !important;
  font-size: 12px !important;
  color: #3c4043 !important;
  cursor: pointer !important;
  transition: all 0.15s ease !important;
  white-space: nowrap !important;
}
.g-status-pill:hover {
  background: #f1f3f4 !important;
  border-color: #c6c6c6 !important;
}
.g-status-dot {
  width: 7px !important;
  height: 7px !important;
  border-radius: 50% !important;
  background: #1e8e3e !important;
  box-shadow: 0 0 0 2px rgba(30, 142, 62, 0.2) !important;
  display: inline-block !important;
  flex-shrink: 0 !important;
}
.g-status-text {
  color: #202124 !important;
}
.g-status-text strong {
  font-weight: 600 !important;
}
.g-status-divider {
  color: #bdc1c6 !important;
  font-size: 11px !important;
}
.g-status-subtext {
  color: #1e8e3e !important;
  font-weight: 500 !important;
}
.g-chevron-icon {
  width: 12px !important;
  height: 12px !important;
  color: #5f6368 !important;
}

/* Actions Section */
.g-actions-section {
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
}

/* Google Clean Chip (Wallet & Plan) */
.g-header-chip {
  display: inline-flex !important;
  align-items: center !important;
  gap: 7px !important;
  padding: 4px 12px !important;
  background: #ffffff !important;
  border: 1px solid #dadce0 !important;
  border-radius: 18px !important;
  font-size: 12.5px !important;
  color: #3c4043 !important;
  cursor: pointer !important;
  transition: all 0.15s ease !important;
  height: 34px !important;
  box-sizing: border-box !important;
}
.g-header-chip:hover {
  background: #f8fafd !important;
  border-color: #c6c6c6 !important;
}
.g-header-chip svg {
  width: 15px !important;
  height: 15px !important;
  color: #5f6368 !important;
  flex-shrink: 0 !important;
}
.g-chip-label {
  color: #5f6368 !important;
  font-weight: 500 !important;
  font-size: 12px !important;
}
.g-chip-val {
  color: #202124 !important;
  font-weight: 600 !important;
  font-size: 12.5px !important;
}
.g-chip-action-pill {
  font-size: 11px !important;
  font-weight: 600 !important;
  color: #1a73e8 !important;
  background: #e8f0fe !important;
  padding: 1px 7px !important;
  border-radius: 10px !important;
}

/* Plan Tier Chip */
.g-tier-dot {
  width: 6px !important;
  height: 6px !important;
  border-radius: 50% !important;
  background: #1a73e8 !important;
  display: inline-block !important;
  flex-shrink: 0 !important;
}
.g-tier-name {
  font-weight: 500 !important;
  color: #3c4043 !important;
  font-size: 12.5px !important;
}
.g-tier-link-btn {
  background: transparent !important;
  border: none !important;
  color: #1a73e8 !important;
  font-weight: 600 !important;
  font-size: 11.5px !important;
  cursor: pointer !important;
  padding: 0 !important;
  margin-left: 2px !important;
}
.g-tier-link-btn:hover {
  text-decoration: underline !important;
}

/* Material 3 Circular Icon Action Buttons */
.g-icon-btn {
  width: 36px !important;
  height: 36px !important;
  border-radius: 50% !important;
  border: 1px solid transparent !important;
  background: transparent !important;
  color: #5f6368 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  cursor: pointer !important;
  position: relative !important;
  transition: background 0.15s ease, color 0.15s ease !important;
  flex-shrink: 0 !important;
}
.g-icon-btn:hover {
  background: #f1f3f4 !important;
  color: #202124 !important;
}
.g-icon-btn svg {
  width: 18px !important;
  height: 18px !important;
  color: #5f6368 !important;
}
.g-icon-btn:hover svg {
  color: #202124 !important;
}
.g-icon-badge {
  position: absolute !important;
  top: 2px !important;
  right: 2px !important;
  min-width: 15px !important;
  height: 15px !important;
  padding: 0 4px !important;
  border-radius: 8px !important;
  background: #1a73e8 !important;
  color: #ffffff !important;
  font-size: 10px !important;
  font-weight: 700 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  line-height: 1 !important;
}

/* Google Cloud Admin Console Launcher */
.g-admin-btn {
  display: inline-flex !important;
  align-items: center !important;
  gap: 6px !important;
  padding: 5px 12px !important;
  background: #f8fafd !important;
  border: 1px solid #c2e7ff !important;
  border-radius: 18px !important;
  color: #0b57d0 !important;
  font-size: 12px !important;
  font-weight: 500 !important;
  text-decoration: none !important;
  transition: all 0.15s ease !important;
  height: 34px !important;
  box-sizing: border-box !important;
  white-space: nowrap !important;
}
.g-admin-btn:hover {
  background: #e8f0fe !important;
  border-color: #7cacf8 !important;
}
.g-admin-btn svg {
  width: 14px !important;
  height: 14px !important;
  color: #0b57d0 !important;
}
.g-arrow {
  font-size: 11px !important;
  color: #0b57d0 !important;
}

/* Google Account Avatar Chip */
.g-account-chip {
  display: inline-flex !important;
  align-items: center !important;
  gap: 8px !important;
  padding: 3px 10px 3px 3px !important;
  background: #ffffff !important;
  border: 1px solid #dadce0 !important;
  border-radius: 20px !important;
  text-decoration: none !important;
  cursor: pointer !important;
  transition: all 0.15s ease !important;
  height: 34px !important;
  box-sizing: border-box !important;
}
.g-account-chip:hover {
  background: #f8fafd !important;
  border-color: #c6c6c6 !important;
}
.g-avatar-circle {
  width: 26px !important;
  height: 26px !important;
  border-radius: 50% !important;
  background: #1a73e8 !important;
  color: #ffffff !important;
  font-size: 12px !important;
  font-weight: 700 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  text-transform: uppercase !important;
}
.g-account-name {
  font-size: 12.5px !important;
  font-weight: 500 !important;
  color: #3c4043 !important;
}

/* Clean Google Sign Out */
.g-signout-btn {
  background: transparent !important;
  color: #5f6368 !important;
  border: 1px solid #dadce0 !important;
  border-radius: 18px !important;
  padding: 5px 12px !important;
  font-size: 12px !important;
  font-weight: 500 !important;
  cursor: pointer !important;
  transition: all 0.15s ease !important;
  height: 34px !important;
  box-sizing: border-box !important;
  white-space: nowrap !important;
}
.g-signout-btn:hover {
  background: #f1f3f4 !important;
  color: #202124 !important;
  border-color: #c6c6c6 !important;
}

/* Public Visitor Buttons */
.g-nav-text-btn {
  background: transparent !important;
  border: none !important;
  color: #5f6368 !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  cursor: pointer !important;
  padding: 6px 12px !important;
}
.g-nav-text-btn:hover {
  color: #202124 !important;
}
.g-signin-btn {
  background: transparent !important;
  color: #1a73e8 !important;
  border: 1px solid #dadce0 !important;
  border-radius: 4px !important;
  padding: 6px 14px !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  text-decoration: none !important;
  transition: all 0.15s ease !important;
}
.g-signin-btn:hover {
  background: #f8fafd !important;
  border-color: #c2e7ff !important;
}
.g-cta-primary-btn {
  background: #1a73e8 !important;
  color: #ffffff !important;
  border: none !important;
  border-radius: 4px !important;
  padding: 6px 16px !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  text-decoration: none !important;
  box-shadow: 0 1px 2px rgba(60, 64, 67, 0.3) !important;
  transition: all 0.15s ease !important;
}
.g-cta-primary-btn:hover {
  background: #1765cc !important;
  box-shadow: 0 1px 3px 1px rgba(60, 64, 67, 0.15) !important;
}

/* Row 2: Underline Material Navigation Tabs */
.g-tabs-bar {
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  height: 46px !important;
  background: #ffffff !important;
  overflow-x: auto !important;
}

.g-nav-tabs {
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  width: 100% !important;
}

.g-tabs-left {
  display: flex !important;
  align-items: center !important;
  gap: 2px !important;
}

.g-tab-btn {
  display: inline-flex !important;
  align-items: center !important;
  gap: 7px !important;
  padding: 12px 14px !important;
  border: none !important;
  border-bottom: 3px solid transparent !important;
  background: transparent !important;
  color: #5f6368 !important;
  font-size: 13.5px !important;
  font-weight: 500 !important;
  cursor: pointer !important;
  text-decoration: none !important;
  white-space: nowrap !important;
  transition: color 0.15s ease, border-color 0.15s ease, background-color 0.15s ease !important;
  border-radius: 4px 4px 0 0 !important;
  box-shadow: none !important;
}
.g-tab-btn:hover {
  color: #202124 !important;
  background: rgba(60, 64, 67, 0.04) !important;
}
.g-tab-btn svg {
  width: 16px !important;
  height: 16px !important;
  color: inherit !important;
}

/* Active Material Tab */
.g-tab-btn.active {
  color: #1a73e8 !important;
  font-weight: 600 !important;
  border-bottom: 3px solid #1a73e8 !important;
  background: transparent !important;
  box-shadow: none !important;
}
.g-tab-btn.active svg {
  color: #1a73e8 !important;
}

/* Tab Counts / Chips */
.g-tab-count {
  font-size: 11px !important;
  font-weight: 500 !important;
  padding: 1px 7px !important;
  border-radius: 10px !important;
  background: #f1f3f4 !important;
  color: #5f6368 !important;
}
.g-tab-btn.active .g-tab-count {
  background: #e8f0fe !important;
  color: #1967d2 !important;
  font-weight: 600 !important;
}
.g-tab-count-audit {
  background: #f1f3f4 !important;
  color: #5f6368 !important;
}
.g-tab-count-live {
  background: #e6f4ea !important;
  color: #137333 !important;
}

.g-tabs-divider {
  width: 1px !important;
  height: 18px !important;
  background: #dadce0 !important;
  margin: 0 8px !important;
  align-self: center !important;
}

/* Google Blue CTA Button on Tabs Row */
.g-plans-cta-btn {
  background: #1a73e8 !important;
  color: #ffffff !important;
  border: none !important;
  border-radius: 4px !important;
  padding: 6px 16px !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  display: inline-flex !important;
  align-items: center !important;
  gap: 6px !important;
  box-shadow: 0 1px 2px rgba(60, 64, 67, 0.3), 0 1px 3px 1px rgba(60, 64, 67, 0.15) !important;
  cursor: pointer !important;
  transition: background 0.15s ease, box-shadow 0.15s ease !important;
  white-space: nowrap !important;
}
.g-plans-cta-btn:hover {
  background: #1765cc !important;
  box-shadow: 0 2px 4px rgba(60, 64, 67, 0.3), 0 3px 6px 2px rgba(60, 64, 67, 0.15) !important;
}

/* Dark Mode Overrides for Google Header */
html.dark-mode .header-nav,
[data-theme="dark"] .header-nav {
  background: #1f1f1f !important;
  border-bottom: 1px solid #3c4043 !important;
}
html.dark-mode .g-top-bar,
[data-theme="dark"] .g-top-bar {
  border-bottom-color: #2d2e30 !important;
}
html.dark-mode .g-brand-link .brand-title,
[data-theme="dark"] .g-brand-link .brand-title {
  color: #e8eaed !important;
}
html.dark-mode .g-header-badge,
[data-theme="dark"] .g-header-badge {
  background: #041e49 !important;
  color: #a8c7fa !important;
  border-color: #0842a0 !important;
}
html.dark-mode .g-status-pill,
[data-theme="dark"] .g-status-pill {
  background: #282a2c !important;
  border-color: #3c4043 !important;
  color: #e8eaed !important;
}
html.dark-mode .g-header-chip,
[data-theme="dark"] .g-header-chip {
  background: #282a2c !important;
  border-color: #3c4043 !important;
  color: #e8eaed !important;
}
html.dark-mode .g-chip-label,
[data-theme="dark"] .g-chip-label {
  color: #9aa0a6 !important;
}
html.dark-mode .g-chip-val,
[data-theme="dark"] .g-chip-val {
  color: #e8eaed !important;
}
html.dark-mode .g-chip-action-pill,
[data-theme="dark"] .g-chip-action-pill {
  background: #041e49 !important;
  color: #a8c7fa !important;
}
html.dark-mode .g-tier-name,
[data-theme="dark"] .g-tier-name {
  color: #e8eaed !important;
}
html.dark-mode .g-account-chip,
[data-theme="dark"] .g-account-chip {
  background: #282a2c !important;
  border-color: #3c4043 !important;
}
html.dark-mode .g-account-name,
[data-theme="dark"] .g-account-name {
  color: #e8eaed !important;
}
html.dark-mode .g-signout-btn,
[data-theme="dark"] .g-signout-btn {
  border-color: #3c4043 !important;
  color: #9aa0a6 !important;
}
html.dark-mode .g-signout-btn:hover,
[data-theme="dark"] .g-signout-btn:hover {
  background: #282a2c !important;
  color: #e8eaed !important;
}
html.dark-mode .g-admin-btn,
[data-theme="dark"] .g-admin-btn {
  background: #041e49 !important;
  border-color: #0842a0 !important;
  color: #a8c7fa !important;
}
html.dark-mode .g-admin-btn svg,
html.dark-mode .g-admin-btn .g-arrow,
[data-theme="dark"] .g-admin-btn svg,
[data-theme="dark"] .g-admin-btn .g-arrow {
  color: #a8c7fa !important;
}
html.dark-mode .g-tabs-bar,
[data-theme="dark"] .g-tabs-bar {
  background: #1f1f1f !important;
}
html.dark-mode .g-tab-btn,
[data-theme="dark"] .g-tab-btn {
  color: #9aa0a6 !important;
}
html.dark-mode .g-tab-btn:hover,
[data-theme="dark"] .g-tab-btn:hover {
  color: #e8eaed !important;
  background: rgba(255, 255, 255, 0.04) !important;
}
html.dark-mode .g-tab-btn.active,
[data-theme="dark"] .g-tab-btn.active {
  color: #8ab4f8 !important;
  border-bottom-color: #8ab4f8 !important;
}
html.dark-mode .g-tab-count,
[data-theme="dark"] .g-tab-count {
  background: #282a2c !important;
  color: #9aa0a6 !important;
}
html.dark-mode .g-tab-btn.active .g-tab-count,
[data-theme="dark"] .g-tab-btn.active .g-tab-count {
  background: #041e49 !important;
  color: #a8c7fa !important;
}
html.dark-mode .g-v-sep,
html.dark-mode .g-tabs-divider,
[data-theme="dark"] .g-v-sep,
[data-theme="dark"] .g-tabs-divider {
  background: #3c4043 !important;
}
"""

with open('static/css/style.css', 'r', encoding='utf-8') as f:
    content = f.read()

# Check if google_css is already in content
if 'GOOGLE MATERIAL DESIGN 3 / CLOUD CONSOLE ENTERPRISE HEADER' not in content:
    with open('static/css/style.css', 'a', encoding='utf-8') as f:
        f.write('\n' + google_css + '\n')
    print("Successfully appended Google Material Design 3 header CSS.")
else:
    print("Google header CSS already present.")
