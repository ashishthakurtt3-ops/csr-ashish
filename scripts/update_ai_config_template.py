import os
import re

target_path = 'templates/admin/ai_config/index.html'
with open(target_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Normalize line endings to \n for editing
crlf_detected = '\r\n' in text
text = text.replace('\r\n', '\n')

# 1. Update body & admin-content in CSS
css_old = """    body {
        font-family: var(--ai-font-stack);
        background-color: var(--ai-surface-subtle);
        color: var(--ai-text-main);
        font-size: 14px;
        line-height: 1.5;
    }"""

css_new = """    body {
        font-family: var(--ai-font-stack);
        background-color: var(--ai-surface-subtle);
        color: var(--ai-text-main);
        font-size: 14px;
        line-height: 1.5;
    }

    /* Container Fluid Expansion for High-Density SaaS Gateway */
    .admin-content {
        max-width: 1680px !important;
        padding: 20px clamp(16px, 2vw, 36px) 60px !important;
    }"""

if css_old in text:
    text = text.replace(css_old, css_new, 1)
    print("1. Container expansion added.")

# 2. Update .ai-summary-grid and .ai-summary-card
grid_css_old = """    /* Summary Strip (3 KPI Cards) */
    .ai-summary-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
        margin-bottom: 20px;
    }

    .ai-summary-card {
        background: var(--ai-surface);
        border: 1px solid var(--ai-border);
        border-radius: var(--ai-radius);
        padding: 16px 20px;
        box-shadow: var(--ai-shadow-card);
    }"""

grid_css_new = """    /* Summary Strip (3 KPI Cards) */
    .ai-summary-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 16px;
        margin-bottom: 22px;
    }

    .ai-summary-card {
        background: var(--ai-surface);
        border: 1px solid var(--ai-border);
        border-radius: var(--ai-radius);
        padding: 16px 20px;
        box-shadow: var(--ai-shadow-card);
        transition: var(--ai-transition);
    }
    .ai-summary-card:hover {
        border-color: var(--ai-border-strong);
        box-shadow: 0 4px 12px rgba(0,0,0,0.04);
    }"""

if grid_css_old in text:
    text = text.replace(grid_css_old, grid_css_new, 1)
    print("2. Summary grid updated.")

# 3. Update .ai-workspace-grid
workspace_css_old = """    /* Main Workspace Grid (Left Table, Right Sticky Drawer) */
    .ai-workspace-grid {
        display: grid;
        grid-template-columns: minmax(0, 1fr) 390px;
        gap: 20px;
        align-items: start;
        margin-bottom: 24px;
    }"""

workspace_css_new = """    /* Main Workspace Grid (Left Table, Right Sticky Drawer) */
    .ai-workspace-grid {
        display: grid;
        grid-template-columns: minmax(0, 1fr) 410px;
        gap: 24px;
        align-items: start;
        margin-bottom: 28px;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .ai-workspace-grid.drawer-collapsed {
        grid-template-columns: minmax(0, 1fr);
    }
    .ai-workspace-grid.drawer-collapsed #configDrawer {
        display: none !important;
    }"""

if workspace_css_old in text:
    text = text.replace(workspace_css_old, workspace_css_new, 1)
    print("3. Workspace grid updated.")

# 4. Update table styling
table_css_old = """    /* Table Styles */
    .table-container {
        width: 100%;
        overflow-x: auto;
    }

    .providers-table {
        width: 100%;
        table-layout: fixed;
        border-collapse: collapse;
        font-size: 13px;
    }

    .providers-table th {
        text-align: left;
        padding: 12px 16px;
        font-size: 11px;
        font-weight: 700;
        color: var(--ai-text-muted);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border-bottom: 1px solid var(--ai-border);
        background: var(--ai-surface-subtle);
    }

    .provider-row {
        cursor: pointer;
        transition: background 0.12s ease;
        border-bottom: 1px solid var(--ai-border);
    }
    .provider-row:hover {
        background-color: var(--ai-surface-subtle);
    }
    .provider-row.is-active-editing {
        background-color: var(--ai-info-bg) !important;
        position: relative;
    }
    .provider-row.is-active-editing td:first-child {
        box-shadow: inset 4px 0 0 #2563EB;
    }

    .providers-table td {
        padding: 12px 16px;
        vertical-align: middle;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }"""

table_css_new = """    /* Table Styles */
    .table-container {
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }

    .providers-table {
        width: 100%;
        min-width: 680px;
        border-collapse: collapse;
        font-size: 13px;
    }

    .providers-table th {
        text-align: left;
        padding: 12px 16px;
        font-size: 11px;
        font-weight: 700;
        color: var(--ai-text-muted);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border-bottom: 1px solid var(--ai-border);
        background: var(--ai-surface-subtle);
        white-space: nowrap;
    }

    .provider-row {
        cursor: pointer;
        transition: background 0.12s ease;
        border-bottom: 1px solid var(--ai-border);
    }
    .provider-row:hover {
        background-color: var(--ai-surface-subtle);
    }
    .provider-row.is-active-editing {
        background-color: var(--ai-info-bg) !important;
        position: relative;
    }
    .provider-row.is-active-editing td:first-child {
        box-shadow: inset 4px 0 0 #2563EB;
    }

    .providers-table td {
        padding: 12px 16px;
        vertical-align: middle;
        white-space: nowrap;
    }"""

if table_css_old in text:
    text = text.replace(table_css_old, table_css_new, 1)
    print("4. Table styles updated.")

# 5. Update Drawer CSS
drawer_css_old = """    /* Right: Sticky Configuration Drawer */
    .config-drawer {
        background: var(--ai-surface);
        border: 1px solid var(--ai-border);
        border-radius: var(--ai-radius);
        box-shadow: var(--ai-shadow-card);
        padding: 22px;
        position: sticky;
        top: 20px;
    }

    .drawer-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 14px;
    }"""

drawer_css_new = """    /* Right: Sticky Configuration Drawer */
    .config-drawer {
        background: var(--ai-surface);
        border: 1px solid var(--ai-border);
        border-radius: var(--ai-radius);
        box-shadow: 0 4px 24px -2px rgba(15, 23, 42, 0.08);
        padding: 22px;
        position: sticky;
        top: 20px;
        max-height: calc(100vh - 40px);
        overflow-y: auto;
        scrollbar-width: thin;
    }

    .drawer-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 14px;
    }
    .drawer-header-left {
        display: flex;
        align-items: center;
        gap: 12px;
        min-width: 0;
    }
    .drawer-close-btn {
        background: transparent;
        border: 1px solid var(--ai-border);
        color: var(--ai-text-muted);
        width: 32px;
        height: 32px;
        border-radius: 6px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        font-size: 18px;
        line-height: 1;
        transition: var(--ai-transition);
        flex-shrink: 0;
    }
    .drawer-close-btn:hover {
        background: var(--ai-surface-subtle);
        color: var(--ai-text-main);
        border-color: var(--ai-border-strong);
    }
    .btn-drawer-toggle-subtle {
        background: var(--ai-surface-subtle);
        border: 1px solid var(--ai-border);
        color: var(--ai-text-muted);
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        transition: var(--ai-transition);
    }
    .btn-drawer-toggle-subtle:hover {
        background: var(--ai-border);
        color: var(--ai-text-main);
    }"""

if drawer_css_old in text:
    text = text.replace(drawer_css_old, drawer_css_new, 1)
    print("5. Drawer styles updated.")

# 6. Update Role selector CSS to modern segmented control
role_css_old = """    /* Role Radio Selector Fieldset */
    .role-options-group {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-top: 6px;
    }

    .role-option-card {
        border: 1px solid var(--ai-border);
        border-radius: var(--ai-radius-sm);
        padding: 8px 12px;
        cursor: pointer;
        transition: var(--ai-transition);
        display: flex;
        align-items: flex-start;
        gap: 10px;
    }
    .role-option-card:hover {
        background: var(--ai-surface-subtle);
    }
    .role-option-card input[type="radio"] {
        margin-top: 3px;
        cursor: pointer;
        accent-color: var(--ai-navy);
    }
    .role-option-card.is-selected {
        border-color: #2563EB;
        background: var(--ai-info-bg);
    }
    .role-label-title {
        font-size: 12.5px;
        font-weight: 700;
        color: var(--ai-text-main);
    }
    .role-label-desc {
        font-size: 11px;
        color: var(--ai-text-muted);
        line-height: 1.35;
    }"""

role_css_new = """    /* Role Radio Selector Fieldset — Modern Segmented Control */
    .role-segmented-control {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 6px;
        background: var(--ai-surface-subtle);
        padding: 4px;
        border: 1px solid var(--ai-border);
        border-radius: 8px;
        margin-top: 6px;
    }
    .role-segment-item {
        position: relative;
        cursor: pointer;
        margin: 0;
        text-align: center;
    }
    .role-segment-item input[type="radio"] {
        position: absolute;
        opacity: 0;
        pointer-events: none;
    }
    .role-segment-pill {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 3px;
        padding: 8px 4px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        color: var(--ai-text-muted);
        transition: var(--ai-transition);
        border: 1px solid transparent;
    }
    .role-segment-pill:hover {
        color: var(--ai-text-main);
    }
    .role-segment-item.is-selected .role-segment-pill {
        background: var(--ai-surface);
        color: #2563EB;
        font-weight: 700;
        border-color: rgba(37, 99, 235, 0.2);
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
    }
    [data-theme="dark"] .role-segment-item.is-selected .role-segment-pill {
        background: #334155;
        color: #60A5FA;
        border-color: rgba(96, 165, 250, 0.3);
    }
    .role-segment-icon {
        font-size: 14px;
    }
    .role-segment-text {
        font-size: 11.5px;
    }
    .role-active-desc {
        font-size: 11.5px;
        color: var(--ai-text-muted);
        margin-top: 8px;
        line-height: 1.4;
        padding: 8px 12px;
        background: var(--ai-surface-subtle);
        border-radius: 6px;
        border-left: 3px solid #2563EB;
        transition: var(--ai-transition);
    }"""

if role_css_old in text:
    text = text.replace(role_css_old, role_css_new, 1)
    print("6. Role segmented CSS updated.")

# 7. Update Media Queries
media_css_old = """    /* Narrow Width Responsive Layout (<768px) */
    @media (max-width: 768px) {
        .ai-summary-grid {
            grid-template-columns: 1fr;
        }
        .ai-workspace-grid {
            grid-template-columns: 1fr;
        }
        .config-drawer {
            position: static;
        }
        .providers-card-header {
            flex-direction: column;
            align-items: flex-start;
        }
        .search-input-ai {
            width: 100%;
        }
        .header-actions {
            width: 100%;
            justify-content: space-between;
        }
    }"""

media_css_new = """    /* Responsive Breakpoints (<1200px and <900px) */
    @media (max-width: 1200px) {
        .ai-workspace-grid {
            grid-template-columns: 1fr;
            gap: 20px;
        }
        .config-drawer {
            position: static !important;
            max-height: none !important;
            order: 2;
        }
    }

    @media (max-width: 900px) {
        .ai-summary-grid {
            grid-template-columns: 1fr;
            gap: 12px;
        }
        .providers-card-header {
            flex-direction: column;
            align-items: stretch;
            gap: 12px;
        }
        .search-filter-wrap {
            flex-direction: column;
            align-items: stretch;
        }
        .search-input-ai {
            width: 100%;
        }
        .filter-pills-group {
            overflow-x: auto;
            padding-bottom: 4px;
        }
        .header-actions {
            width: 100%;
            justify-content: flex-start;
        }
    }"""

if media_css_old in text:
    text = text.replace(media_css_old, media_css_new, 1)
    print("7. Media queries updated.")

# 8. HTML: Remove redundant sub-header dark mode button
header_actions_old = """    <div class="header-actions">
        <button type="button" class="btn-header-outline" id="themeToggleBtn" onclick="toggleDarkMode()" title="Toggle Light / Dark mode">
            <span id="themeToggleIcon">🌙</span> <span id="themeToggleText">Dark Mode</span>
        </button>
        <button type="button" class="btn-header-outline" onclick="testAllConnectionsLive()" id="btnTestAllConnections">
            <span>Test all connections</span>
        </button>
        <button type="button" class="btn-header-primary" onclick="openAddProviderModal()" id="btnAddProvider">
            <span>+ Add custom provider</span>
        </button>
    </div>"""

header_actions_new = """    <div class="header-actions">
        <button type="button" class="btn-header-outline" onclick="testAllConnectionsLive()" id="btnTestAllConnections">
            <i class="fas fa-vial" style="margin-right:6px;"></i><span>Test all connections</span>
        </button>
        <button type="button" class="btn-header-primary" onclick="openAddProviderModal()" id="btnAddProvider">
            <span>+ Add custom provider</span>
        </button>
    </div>"""

if header_actions_old in text:
    text = text.replace(header_actions_old, header_actions_new, 1)
    print("8. Redundant dark mode button removed.")

# 9. HTML: Add id to ai-workspace-grid
grid_html_old = """    <!-- 2. Main Workspace (Table on Left, Sticky Drawer on Right) -->
    <div class="ai-workspace-grid">"""

grid_html_new = """    <!-- 2. Main Workspace (Table on Left, Sticky Drawer on Right) -->
    <div class="ai-workspace-grid" id="aiWorkspaceGrid">"""

if grid_html_old in text:
    text = text.replace(grid_html_old, grid_html_new, 1)
    print("9. Grid id added.")

# 10. HTML: Providers Card Header with Drawer Toggle Button
card_header_old = """            <div class="providers-card-header">
                <h3 class="providers-card-title">Providers</h3>
                <div class="search-filter-wrap">"""

card_header_new = """            <div class="providers-card-header">
                <div style="display:flex; align-items:center; gap:12px;">
                    <h3 class="providers-card-title">Providers</h3>
                    <button type="button" class="btn-drawer-toggle-subtle" onclick="toggleDrawerCollapse()" id="btnToggleDrawer" title="Toggle configuration drawer view">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="15" y1="3" x2="15" y2="21"></line></svg>
                        <span>Panel</span>
                    </button>
                </div>
                <div class="search-filter-wrap">"""

if card_header_old in text:
    text = text.replace(card_header_old, card_header_new, 1)
    print("10. Card header updated.")

# 11. HTML: Providers Table Head with responsive min-widths
thead_old = """                    <thead>
                        <tr>
                            <th style="width:30%;">PROVIDER</th>
                            <th style="width:30%;">MODEL</th>
                            <th style="width:20%;">STATUS</th>
                            <th style="width:10%;">KEY</th>
                            <th style="width:10%; text-align:right;"></th>
                        </tr>
                    </thead>"""

thead_new = """                    <thead>
                        <tr>
                            <th style="width:28%; min-width:180px;">PROVIDER</th>
                            <th style="width:28%; min-width:190px;">MODEL</th>
                            <th style="width:18%; min-width:130px;">STATUS</th>
                            <th style="width:14%; min-width:90px;">KEY</th>
                            <th style="width:12%; min-width:90px; text-align:right;">ACTION</th>
                        </tr>
                    </thead>"""

if thead_old in text:
    text = text.replace(thead_old, thead_new, 1)
    print("11. Table headers updated with min-widths.")

# 12. HTML: Drawer Header with Close Button
drawer_header_old = """            <!-- Header -->
            <div class="drawer-header">
                <div class="drawer-avatar" id="drawerAvatar" style="background-color: {{ providers.0.color }};">
                    {{ providers.0.display_name|slice:":1" }}
                </div>
                <div class="drawer-title-wrap">
                    <div class="drawer-prov-title" id="drawerTitle">{{ providers.0.display_name }}</div>
                    <div class="drawer-prov-role" id="drawerRole">
                        {% if providers.0.is_primary %}Primary provider (1st)
                        {% elif providers.0.is_fallback %}Failover provider (2nd)
                        {% else %}Secondary provider (Not used in routing){% endif %}
                    </div>
                </div>
            </div>"""

drawer_header_new = """            <!-- Header with Close Button -->
            <div class="drawer-header">
                <div class="drawer-header-left">
                    <div class="drawer-avatar" id="drawerAvatar" style="background-color: {{ providers.0.color }};">
                        {{ providers.0.display_name|slice:":1" }}
                    </div>
                    <div class="drawer-title-wrap">
                        <div class="drawer-prov-title" id="drawerTitle">{{ providers.0.display_name }}</div>
                        <div class="drawer-prov-role" id="drawerRole">
                            {% if providers.0.is_primary %}Primary provider (1st)
                            {% elif providers.0.is_fallback %}Failover provider (2nd)
                            {% else %}Secondary provider (Not used in routing){% endif %}
                        </div>
                    </div>
                </div>
                <button type="button" class="drawer-close-btn" onclick="toggleDrawerCollapse(true)" title="Collapse configuration drawer" aria-label="Close configuration drawer">
                    &times;
                </button>
            </div>"""

if drawer_header_old in text:
    text = text.replace(drawer_header_old, drawer_header_new, 1)
    print("12. Drawer header updated with close button.")

# 13. HTML: Role Selector Segmented Control
role_selector_old = """                <!-- Role Selector (Primary / Failover / Not used) -->
                <fieldset class="form-group-ai">
                    <legend class="label-ai">Crawler Routing Role</legend>
                    <div class="role-options-group">
                        <label class="role-option-card {% if providers.0.role == 'primary' %}is-selected{% endif %}" id="roleCardPrimary">
                            <input type="radio" name="providerRole" value="primary" {% if providers.0.role == 'primary' %}checked{% endif %} onchange="onRoleChange('primary')">
                            <div>
                                <div class="role-label-title">Primary (1st in routing)</div>
                                <div class="role-label-desc">Always called first for company page classification and intelligence extraction.</div>
                            </div>
                        </label>

                        <label class="role-option-card {% if providers.0.role == 'failover' %}is-selected{% endif %}" id="roleCardFailover">
                            <input type="radio" name="providerRole" value="failover" {% if providers.0.role == 'failover' %}checked{% endif %} onchange="onRoleChange('failover')">
                            <div>
                                <div class="role-label-title">Failover (2nd in routing)</div>
                                <div class="role-label-desc">Takes over automatically if Primary fails, rate-limits, or exhausts quota.</div>
                            </div>
                        </label>

                        <label class="role-option-card {% if providers.0.role == 'not_used' %}is-selected{% endif %}" id="roleCardNotUsed">
                            <input type="radio" name="providerRole" value="not_used" {% if providers.0.role == 'not_used' %}checked{% endif %} onchange="onRoleChange('not_used')">
                            <div>
                                <div class="role-label-title">Not used</div>
                                <div class="role-label-desc">Excluded from automated crawler routing. Available for manual tests.</div>
                            </div>
                        </label>
                    </div>
                </fieldset>"""

role_selector_new = """                <!-- Role Selector (Primary / Failover / Inactive) Segmented Control -->
                <fieldset class="form-group-ai">
                    <legend class="label-ai">Crawler Routing Role</legend>
                    <div class="role-segmented-control" role="radiogroup" aria-label="Crawler Routing Role">
                        <label class="role-segment-item {% if providers.0.role == 'primary' %}is-selected{% endif %}" id="roleCardPrimary" title="Always called first for company intelligence extraction">
                            <input type="radio" name="providerRole" value="primary" {% if providers.0.role == 'primary' %}checked{% endif %} onchange="onRoleChange('primary')">
                            <span class="role-segment-pill">
                                <span class="role-segment-icon">🥇</span>
                                <span class="role-segment-text">Primary</span>
                            </span>
                        </label>

                        <label class="role-segment-item {% if providers.0.role == 'failover' %}is-selected{% endif %}" id="roleCardFailover" title="Takes over if primary fails, rate-limits, or exhausts quota">
                            <input type="radio" name="providerRole" value="failover" {% if providers.0.role == 'failover' %}checked{% endif %} onchange="onRoleChange('failover')">
                            <span class="role-segment-pill">
                                <span class="role-segment-icon">🛡️</span>
                                <span class="role-segment-text">Failover</span>
                            </span>
                        </label>

                        <label class="role-segment-item {% if providers.0.role == 'not_used' %}is-selected{% endif %}" id="roleCardNotUsed" title="Excluded from automated routing">
                            <input type="radio" name="providerRole" value="not_used" {% if providers.0.role == 'not_used' %}checked{% endif %} onchange="onRoleChange('not_used')">
                            <span class="role-segment-pill">
                                <span class="role-segment-icon">⏸️</span>
                                <span class="role-segment-text">Inactive</span>
                            </span>
                        </label>
                    </div>
                    <div class="role-active-desc" id="roleActiveDesc">
                        {% if providers.0.role == 'primary' %}
                            Primary: Always called first for company page classification and intelligence extraction.
                        {% elif providers.0.role == 'failover' %}
                            Failover: Automatically takes over if Primary fails, rate-limits, or exhausts quota.
                        {% else %}
                            Inactive: Excluded from automated crawler routing. Available for manual tests.
                        {% endif %}
                    </div>
                </fieldset>"""

if role_selector_old in text:
    text = text.replace(role_selector_old, role_selector_new, 1)
    print("13. Role selector updated to modern segmented control.")

# 14. JavaScript: updateRoleRadioUI & toggleDrawerCollapse
js_role_old = """    function updateRoleRadioUI(roleValue) {
        document.querySelectorAll("input[name='providerRole']").forEach(radio => {
            radio.checked = (radio.value === roleValue);
        });
        document.getElementById("roleCardPrimary").classList.toggle("is-selected", roleValue === 'primary');
        document.getElementById("roleCardFailover").classList.toggle("is-selected", roleValue === 'failover');
        document.getElementById("roleCardNotUsed").classList.toggle("is-selected", roleValue === 'not_used');
    }"""

js_role_new = """    function toggleDrawerCollapse(forceCollapse) {
        const grid = document.getElementById('aiWorkspaceGrid');
        if (!grid) return;
        if (typeof forceCollapse === 'boolean') {
            if (forceCollapse) {
                grid.classList.add('drawer-collapsed');
            } else {
                grid.classList.remove('drawer-collapsed');
            }
        } else {
            grid.classList.toggle('drawer-collapsed');
        }
    }

    function updateRoleRadioUI(roleValue) {
        document.querySelectorAll("input[name='providerRole']").forEach(radio => {
            radio.checked = (radio.value === roleValue);
        });
        document.getElementById("roleCardPrimary").classList.toggle("is-selected", roleValue === 'primary');
        document.getElementById("roleCardFailover").classList.toggle("is-selected", roleValue === 'failover');
        document.getElementById("roleCardNotUsed").classList.toggle("is-selected", roleValue === 'not_used');

        const descEl = document.getElementById("roleActiveDesc");
        if (descEl) {
            if (roleValue === 'primary') {
                descEl.textContent = "Primary: Always called first for company page classification and intelligence extraction.";
                descEl.style.borderLeftColor = "#2563EB";
            } else if (roleValue === 'failover') {
                descEl.textContent = "Failover: Automatically takes over if Primary fails, rate-limits, or exhausts quota.";
                descEl.style.borderLeftColor = "var(--ai-warning)";
            } else {
                descEl.textContent = "Inactive: Excluded from automated crawler routing. Available for manual tests.";
                descEl.style.borderLeftColor = "var(--ai-border-strong)";
            }
        }
    }"""

if js_role_old in text:
    text = text.replace(js_role_old, js_role_new, 1)
    print("14. JS updateRoleRadioUI and toggleDrawerCollapse added.")

# 15. JS: expand drawer on selectProvider if collapsed
select_prov_old = """    function selectProvider(provId, force = false) {
        const p = PROVIDERS_MAP[provId];
        if (!p) return;

        currentSelectedProviderId = provId;
        hasUnsavedChanges = false;"""

select_prov_new = """    function selectProvider(provId, force = false) {
        const p = PROVIDERS_MAP[provId];
        if (!p) return;

        currentSelectedProviderId = provId;
        hasUnsavedChanges = false;

        // Auto-expand drawer if collapsed
        toggleDrawerCollapse(false);
        if (!force && window.innerWidth < 1200) {
            const drawer = document.getElementById('configDrawer');
            if (drawer) {
                drawer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }"""

if select_prov_old in text:
    text = text.replace(select_prov_old, select_prov_new, 1)
    print("15. JS selectProvider auto-expand added.")

# Restore CRLF if previously present
if crlf_detected:
    text = text.replace('\n', '\r\n')

with open(target_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("SUCCESS: All ai_config redesign updates successfully applied!")
