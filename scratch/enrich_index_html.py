# scratch/enrich_index_html.py
# Reads existing templates/admin/ai_config/index.html and injects the new tabs, sections, CSS, and JS

with open('templates/admin/ai_config/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update tabs bar HTML
old_tabs_bar = '''<!-- Main Tab Switching (AI Providers vs Usage & Limits) -->
<div class="ai-main-tabs-bar" role="tablist" aria-label="Configuration Sections">
    <button type="button" role="tab" id="tab-providers" aria-selected="true" aria-controls="viewProvidersSection" class="ai-tab-item is-active" onclick="switchMainTab('providers')">
        AI Providers
    </button>
    <button type="button" role="tab" id="tab-usage" aria-selected="false" aria-controls="viewUsageSection" class="ai-tab-item" onclick="switchMainTab('usage')">
        Usage &amp; Limits
    </button>
</div>'''

new_tabs_bar = '''<!-- Main Enterprise SaaS Control Center Tabs -->
<div class="ai-main-tabs-bar" role="tablist" aria-label="Control Center Sections">
    <button type="button" role="tab" id="tab-providers" aria-selected="true" aria-controls="viewProvidersSection" class="ai-tab-item is-active" onclick="switchMainTab('providers')">
        <i class="fas fa-server" style="margin-right:6px;"></i>AI Providers &amp; Routing
    </button>
    <button type="button" role="tab" id="tab-catalog" aria-selected="false" aria-controls="viewCatalogSection" class="ai-tab-item" onclick="switchMainTab('catalog')">
        <i class="fas fa-layer-group" style="margin-right:6px;"></i>Dynamic Model Catalog
    </button>
    <button type="button" role="tab" id="tab-diagnostics" aria-selected="false" aria-controls="viewDiagnosticsSection" class="ai-tab-item" onclick="switchMainTab('diagnostics')">
        <i class="fas fa-microscope" style="margin-right:6px;"></i>Company AI Diagnostics
    </button>
    <button type="button" role="tab" id="tab-testing" aria-selected="false" aria-controls="viewTestingSection" class="ai-tab-item" onclick="switchMainTab('testing')">
        <i class="fas fa-vial" style="margin-right:6px;"></i>Connection &amp; Failover Testing
    </button>
    <button type="button" role="tab" id="tab-usage" aria-selected="false" aria-controls="viewUsageSection" class="ai-tab-item" onclick="switchMainTab('usage')">
        <i class="fas fa-chart-line" style="margin-right:6px;"></i>Usage &amp; Cost Telemetry
    </button>
    <button type="button" role="tab" id="tab-audit" aria-selected="false" aria-controls="viewAuditSection" class="ai-tab-item" onclick="switchMainTab('audit')">
        <i class="fas fa-history" style="margin-right:6px;"></i>Audit Trail
    </button>
</div>'''

assert old_tabs_bar in content, "old_tabs_bar not found in content"
content = content.replace(old_tabs_bar, new_tabs_bar)

# 2. Add extra CSS for the new tabs and views
extra_css = '''
    /* ==========================================================================
       Enterprise Control Center Extensions: Diagnostics, Catalog, Testing
       ========================================================================== */
    .control-center-panel {
        background: var(--ai-surface);
        border: 1px solid var(--ai-border);
        border-radius: var(--ai-radius);
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: var(--ai-shadow-card);
    }
    .panel-header-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 18px;
        flex-wrap: wrap;
        gap: 12px;
    }
    .panel-title {
        font-size: 17px;
        font-weight: 700;
        color: var(--ai-text-main);
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .panel-subtitle {
        font-size: 13px;
        color: var(--ai-text-muted);
        margin-top: 4px;
    }
    .company-search-box {
        position: relative;
        width: 100%;
        max-width: 480px;
    }
    .company-dropdown-results {
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: var(--ai-surface);
        border: 1px solid var(--ai-border-strong);
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        max-height: 280px;
        overflow-y: auto;
        z-index: 1000;
        display: none;
    }
    .company-dropdown-item {
        padding: 10px 14px;
        cursor: pointer;
        border-bottom: 1px solid var(--ai-border);
        font-size: 13px;
        transition: var(--ai-transition);
    }
    .company-dropdown-item:hover {
        background: var(--ai-surface-subtle);
    }
    .company-dropdown-item:last-child {
        border-bottom: none;
    }
    .diag-selected-company-card {
        background: var(--ai-surface-subtle);
        border: 1px solid var(--ai-border);
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 18px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
    }
    .diag-evidence-box {
        background: #0F172A;
        color: #E2E8F0;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 12.5px;
        line-height: 1.5;
        padding: 14px 16px;
        border-radius: 8px;
        max-height: 220px;
        overflow-y: auto;
        white-space: pre-wrap;
        word-break: break-all;
        margin-top: 8px;
    }
    .catalog-search-bar {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin-bottom: 16px;
    }
    .trace-step-item {
        border-left: 3px solid var(--ai-border);
        padding-left: 16px;
        margin-bottom: 16px;
        position: relative;
    }
    .trace-step-item.is-success {
        border-left-color: var(--ai-success);
    }
    .trace-step-item.is-blocked {
        border-left-color: var(--ai-warning);
    }
    .trace-step-item.is-failed {
        border-left-color: var(--ai-danger);
    }
</style>
'''

content = content.replace('</style>', extra_css)

# 3. Add the HTML for Catalog, Diagnostics, Testing, and Audit views right after viewUsageSection
insertion_point = '<!-- Add Custom Provider Modal'
idx = content.find(insertion_point)
assert idx != -1, "Modal insertion point not found"

new_sections_html = '''
<!-- VIEW 2: DYNAMIC MODEL CATALOG -->
<div id="viewCatalogSection" style="display:none;" role="region" aria-labelledby="tab-catalog">
    <div class="control-center-panel">
        <div class="panel-header-row">
            <div>
                <div class="panel-title"><i class="fas fa-layer-group" style="color:var(--ai-navy);"></i> Authorized Model Catalog &amp; Rate Cards</div>
                <div class="panel-subtitle">Dynamic, verifiable catalog across all registered AI providers. Filter by capability, free-tier status, or pricing.</div>
            </div>
            <div>
                <button type="button" class="btn-ai btn-ai-primary" onclick="loadDynamicModelCatalog(true)" id="btnRefreshCatalog">
                    <i class="fas fa-sync-alt" style="margin-right:6px;"></i>Refresh All Catalogs
                </button>
            </div>
        </div>

        <div class="catalog-search-bar">
            <input type="text" id="catalogSearchInput" class="form-control-ai" placeholder="Search models by name or identifier..." style="max-width:320px;" oninput="filterModelCatalogUI()">
            <select id="catalogProviderFilter" class="form-control-ai" style="max-width:200px;" onchange="filterModelCatalogUI()">
                <option value="all">All Providers</option>
                <option value="gemini">Google Gemini</option>
                <option value="openrouter">OpenRouter</option>
                <option value="grok">xAI Grok</option>
                <option value="groq">Groq Cloud</option>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic Claude</option>
                <option value="deepseek">DeepSeek AI</option>
                <option value="mistral">Mistral AI</option>
                <option value="ollama">Ollama Local</option>
            </select>
            <select id="catalogPricingFilter" class="form-control-ai" style="max-width:180px;" onchange="filterModelCatalogUI()">
                <option value="all">All Tiers (Free &amp; Paid)</option>
                <option value="free">Free Tier Only ($0.00)</option>
                <option value="paid">Paid Models Only</option>
            </select>
        </div>

        <div style="overflow-x:auto;">
            <table class="ai-table" id="modelCatalogTable" style="width:100%; font-size:13px;">
                <thead>
                    <tr>
                        <th>Provider</th>
                        <th>Model Identifier</th>
                        <th>Display Name</th>
                        <th>Context Window</th>
                        <th>Tier</th>
                        <th>Input Price / 1M</th>
                        <th>Output Price / 1M</th>
                        <th>Role</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="modelCatalogTableBody">
                    <tr><td colspan="9" style="text-align:center; padding:24px; color:var(--ai-text-muted);"><i class="fas fa-spinner fa-spin"></i> Loading catalog models...</td></tr>
                </tbody>
            </table>
        </div>
    </div>
</div>

<!-- VIEW 3: COMPANY-SPECIFIC AI DIAGNOSTICS -->
<div id="viewDiagnosticsSection" style="display:none;" role="region" aria-labelledby="tab-diagnostics">
    <div class="control-center-panel">
        <div class="panel-header-row">
            <div>
                <div class="panel-title"><i class="fas fa-microscope" style="color:var(--ai-navy);"></i> Company-Specific AI Diagnostics Engine</div>
                <div class="panel-subtitle">Select any real company record to test content classification, careers discovery, job extraction, or statutory CSR detection using live website evidence.</div>
            </div>
            <div style="font-size:12px; color:var(--ai-success); font-weight:600; background:var(--ai-success-bg); padding:6px 12px; border-radius:6px; border:1px solid var(--ai-success-border);">
                <i class="fas fa-shield-alt"></i> STRICT READ-ONLY: 0 Database Writes
            </div>
        </div>

        <!-- Searchable Company Selector -->
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-bottom:16px;">
            <div>
                <label class="form-label-ai">Target Company Selection</label>
                <div class="company-search-box">
                    <input type="text" id="diagCompanySearch" class="form-control-ai" placeholder="Search company by name or ID (e.g. Reliance, HDFC, TCS)..." autocomplete="off" oninput="onDiagCompanySearchInput(this.value)">
                    <div id="diagCompanyDropdown" class="company-dropdown-results"></div>
                </div>
                <div class="hint-ai">Queries real records from MySQL <code>admin_panel_company</code>.</div>
            </div>

            <div>
                <label class="form-label-ai">Diagnostic Pipeline Task</label>
                <select id="diagTaskSelect" class="form-control-ai">
                    <option value="homepage_classification">1. Homepage Content Classification (Entity type &amp; structure)</option>
                    <option value="careers_discovery">2. Careers Page &amp; ATS Discovery (Workday/SAP sourcing)</option>
                    <option value="job_extraction">3. Job Vacancy Schema Extraction (JSON-LD &amp; DOM)</option>
                    <option value="csr_identification">4. CSR Statutory Disclosure Analysis (Section 135)</option>
                    <option value="csr_project_extraction">5. CSR Project Candidate Discovery (Schedule VII)</option>
                    <option value="opportunity_classification">6. Procurement &amp; Tender Opportunity Detection (RFP/EOI)</option>
                    <option value="routing_test">7. AI Routing &amp; Policy Verification</option>
                    <option value="fallback_test">8. Failover Fail-Safe Verification</option>
                </select>
            </div>
        </div>

        <!-- Selected Company Banner -->
        <div id="diagSelectedCompanyCard" class="diag-selected-company-card" style="display:none;">
            <div>
                <div style="font-weight:700; font-size:15px; color:var(--ai-text-main);" id="diagTargetName">-</div>
                <div style="font-size:12.5px; color:var(--ai-text-muted); margin-top:2px;">
                    ID: <code id="diagTargetId">-</code> &bull; Sector: <span id="diagTargetIndustry">-</span> &bull; URL: <a id="diagTargetUrlLink" href="#" target="_blank" rel="noopener" style="color:var(--ai-navy); text-decoration:underline;">-</a>
                </div>
            </div>
            <div>
                <button type="button" class="btn-ai btn-ai-primary" id="btnExecuteDiagnostic" onclick="executeCompanyDiagnostic()">
                    <i class="fas fa-play" style="margin-right:6px;"></i>Run Live Diagnostic
                </button>
            </div>
        </div>

        <!-- Diagnostic Execution Output -->
        <div id="diagResultsContainer" style="display:none; margin-top:24px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <div style="font-size:15px; font-weight:700; color:var(--ai-text-main);">
                    Diagnostic Output Trace &bull; <span id="diagStatusBadge" class="status-pill status-active">SUCCESS</span>
                </div>
                <div style="font-size:12px; color:var(--ai-text-muted);">
                    Latency: <strong id="diagLatencyVal">-</strong> ms &bull; Tokens: <strong id="diagTokensVal">-</strong> &bull; Method: <code id="diagMethodVal">ESTIMATED</code>
                </div>
            </div>

            <!-- DOM Evidence Excerpt -->
            <div style="margin-bottom:14px;">
                <label style="font-size:12px; font-weight:700; color:var(--ai-text-muted); text-transform:uppercase;">Source DOM Text Excerpt (Real Web Evidence)</label>
                <div id="diagEvidenceBox" class="diag-evidence-box">Loading evidence...</div>
            </div>

            <!-- Structured Findings -->
            <div>
                <label style="font-size:12px; font-weight:700; color:var(--ai-text-muted); text-transform:uppercase;">Validated Structured Diagnostic Findings</label>
                <pre id="diagStructuredJson" class="diag-evidence-box" style="background:#1E293B; max-height:260px;"></pre>
            </div>
        </div>

        <!-- Historical Diagnostcs for Selected Company -->
        <div id="diagHistoryContainer" style="display:none; margin-top:28px;">
            <div style="font-size:14px; font-weight:700; color:var(--ai-text-main); margin-bottom:10px;">
                Prior Invocations &amp; Diagnostics for this Company
            </div>
            <table class="ai-table" style="width:100%; font-size:12.5px;">
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Task</th>
                        <th>Provider &amp; Model</th>
                        <th>Status</th>
                        <th>Latency</th>
                        <th>Tokens</th>
                        <th>Verdict</th>
                    </tr>
                </thead>
                <tbody id="diagHistoryTableBody">
                    <tr><td colspan="7" style="text-align:center; color:var(--ai-text-muted);">No prior invocations recorded.</td></tr>
                </tbody>
            </table>
        </div>
    </div>
</div>

<!-- VIEW 4: CONNECTION & FAILOVER TESTING CENTER -->
<div id="viewTestingSection" style="display:none;" role="region" aria-labelledby="tab-testing">
    <div class="control-center-panel">
        <div class="panel-header-row">
            <div>
                <div class="panel-title"><i class="fas fa-vial" style="color:var(--ai-navy);"></i> Connection, Model &amp; Failover Testing Center</div>
                <div class="panel-subtitle">Execute verified bounded probes to validate credentials, model inference, and automatic failover fail-safes.</div>
            </div>
        </div>

        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:18px; margin-bottom:24px;">
            <!-- Test Card 1: Primary Connection Ping -->
            <div class="control-center-panel" style="margin-bottom:0;">
                <div style="font-size:14px; font-weight:700; color:var(--ai-text-main); margin-bottom:6px;">1. Primary Provider Ping</div>
                <div style="font-size:12px; color:var(--ai-text-muted); margin-bottom:12px;">Validates endpoint reachability and API key authentication for active primary.</div>
                <button type="button" class="btn-ai btn-ai-outline" style="width:100%;" onclick="runPrimaryPingTest()" id="btnPrimaryPing">
                    <i class="fas fa-network-wired" style="margin-right:6px;"></i>Ping Primary Connection
                </button>
                <div id="primaryPingResult" style="margin-top:10px; font-size:12px; display:none;"></div>
            </div>

            <!-- Test Card 2: Routing & Failover Simulation -->
            <div class="control-center-panel" style="margin-bottom:0;">
                <div style="font-size:14px; font-weight:700; color:var(--ai-text-main); margin-bottom:6px;">2. Routing &amp; Failover Test</div>
                <div style="font-size:12px; color:var(--ai-text-muted); margin-bottom:12px;">Simulates transient rate limit failure on primary and verifies failover to secondary.</div>
                <button type="button" class="btn-ai btn-ai-outline" style="width:100%;" onclick="runRoutingFailoverTest()" id="btnRoutingTest">
                    <i class="fas fa-random" style="margin-right:6px;"></i>Simulate Failover
                </button>
                <div id="routingTestResult" style="margin-top:10px; font-size:12px; display:none;"></div>
            </div>

            <!-- Test Card 3: Batch Test All Providers -->
            <div class="control-center-panel" style="margin-bottom:0;">
                <div style="font-size:14px; font-weight:700; color:var(--ai-text-main); margin-bottom:6px;">3. Test All Configured Providers</div>
                <div style="font-size:12px; color:var(--ai-text-muted); margin-bottom:12px;">Sequential bounded health checks across all registered provider cards.</div>
                <button type="button" class="btn-ai btn-ai-primary" style="width:100%;" onclick="runBatchTestAll()" id="btnBatchTestAll">
                    <i class="fas fa-clipboard-check" style="margin-right:6px;"></i>Run All Checks
                </button>
            </div>
        </div>

        <!-- Failover Simulation Trace Output -->
        <div id="failoverTraceContainer" style="display:none; background:var(--ai-surface-subtle); border:1px solid var(--ai-border); border-radius:8px; padding:18px; margin-top:16px;">
            <div style="font-size:14px; font-weight:700; color:var(--ai-text-main); margin-bottom:12px;">
                Routing &amp; Failover Step-by-Step Trace
            </div>
            <div id="failoverTraceSteps"></div>
        </div>

        <!-- Batch Results Matrix -->
        <div id="batchTestResultsMatrix" style="display:none; margin-top:20px;">
            <div style="font-size:14px; font-weight:700; color:var(--ai-text-main); margin-bottom:10px;">
                Provider Test Matrix Results
            </div>
            <table class="ai-table" style="width:100%; font-size:13px;">
                <thead>
                    <tr>
                        <th>Provider</th>
                        <th>Effective Model</th>
                        <th>Status</th>
                        <th>Latency</th>
                        <th>Outcome Message</th>
                    </tr>
                </thead>
                <tbody id="batchTestTableBody"></tbody>
            </table>
        </div>
    </div>
</div>

<!-- VIEW 5: AUDIT TRAIL TAB -->
<div id="viewAuditSection" style="display:none;" role="region" aria-labelledby="tab-audit">
    <div class="control-center-panel">
        <div class="panel-header-row">
            <div>
                <div class="panel-title"><i class="fas fa-history" style="color:var(--ai-navy);"></i> Immutable AI Configuration &amp; Invocation Audit Trail</div>
                <div class="panel-subtitle">Tamper-evident logs of all credential adjustments, model catalog updates, live tests, and diagnostic invocations.</div>
            </div>
        </div>

        <table class="ai-table" style="width:100%; font-size:13px;">
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Action</th>
                    <th>Provider / Model</th>
                    <th>Status</th>
                    <th>Performed By</th>
                    <th>IP Address</th>
                    <th>Message &amp; Latency</th>
                </tr>
            </thead>
            <tbody>
                {% for log in recent_audits %}
                <tr>
                    <td style="white-space:nowrap;">{{ log.timestamp|date:"Y-m-d H:i:s" }}</td>
                    <td><span class="badge" style="background:var(--ai-surface-subtle); border:1px solid var(--ai-border);">{{ log.action }}</span></td>
                    <td><strong>{{ log.provider|default:"-" }}</strong><br><small style="color:var(--ai-text-muted);">{{ log.model_name|default:"-" }}</small></td>
                    <td>
                        {% if log.status == 'SUCCESS' %}
                            <span class="status-pill status-active">SUCCESS</span>
                        {% elif log.status == 'BLOCKED' %}
                            <span class="status-pill status-warning">BLOCKED</span>
                        {% else %}
                            <span class="status-pill status-error">{{ log.status }}</span>
                        {% endif %}
                    </td>
                    <td>{{ log.performed_by.username|default:"SYSTEM" }}</td>
                    <td><code>{{ log.ip_address|default:"127.0.0.1" }}</code></td>
                    <td>
                        {{ log.message }}
                        {% if log.latency_ms %}<span style="color:var(--ai-text-muted); font-size:11px;">({{ log.latency_ms }} ms)</span>{% endif %}
                    </td>
                </tr>
                {% empty %}
                <tr><td colspan="7" style="text-align:center; padding:24px; color:var(--ai-text-muted);">No audit events recorded yet.</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
'''

content = content[:idx] + new_sections_html + content[idx:]

# 4. Update JavaScript switchMainTab function to handle all 6 tabs
old_switch_fn = '''function switchMainTab(tab) {
        const tabProviders = document.getElementById('tab-providers');
        const tabUsage = document.getElementById('tab-usage');
        const viewProviders = document.getElementById('viewProvidersSection');
        const viewUsage = document.getElementById('viewUsageSection');

        if (tab === 'providers') {
            tabProviders.classList.add('is-active');
            tabProviders.setAttribute('aria-selected', 'true');
            tabUsage.classList.remove('is-active');
            tabUsage.setAttribute('aria-selected', 'false');
            viewProviders.style.display = 'block';
            viewUsage.style.display = 'none';
        } else {
            tabUsage.classList.add('is-active');
            tabUsage.setAttribute('aria-selected', 'true');
            tabProviders.classList.remove('is-active');
            tabProviders.setAttribute('aria-selected', 'false');
            viewProviders.style.display = 'none';
            viewUsage.style.display = 'block';
        }
    }'''

new_switch_fn = '''function switchMainTab(tab) {
        const tabs = ['providers', 'catalog', 'diagnostics', 'testing', 'usage', 'audit'];
        tabs.forEach(t => {
            const tabBtn = document.getElementById('tab-' + t);
            const viewSec = document.getElementById('view' + t.charAt(0).toUpperCase() + t.slice(1) + 'Section');
            if (tabBtn) {
                if (t === tab) {
                    tabBtn.classList.add('is-active');
                    tabBtn.setAttribute('aria-selected', 'true');
                } else {
                    tabBtn.classList.remove('is-active');
                    tabBtn.setAttribute('aria-selected', 'false');
                }
            }
            if (viewSec) {
                viewSec.style.display = (t === tab) ? 'block' : 'none';
            }
        });

        // Auto-load catalog or usage data when switched
        if (tab === 'catalog') {
            loadDynamicModelCatalog();
        } else if (tab === 'usage') {
            loadLiveTelemetryData();
        }
    }

    // =========================================================================
    // Dynamic Model Catalog Client
    // =========================================================================
    let cachedCatalogModels = [];

    async function loadDynamicModelCatalog(forceRefresh = false) {
        const tbody = document.getElementById('modelCatalogTableBody');
        const btn = document.getElementById('btnRefreshCatalog');
        if (btn) btn.disabled = true;

        try {
            const res = await fetch('/admin-portal/ai-config/models/catalog/?provider=all');
            const data = await res.json();
            if (data.success && data.catalog) {
                cachedCatalogModels = data.catalog;
                renderModelCatalogTable(cachedCatalogModels);
                if (forceRefresh) showToast("Dynamic model catalog refreshed successfully.", "success");
            } else {
                tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; color:var(--ai-danger);">Failed to load model catalog.</td></tr>';
            }
        } catch (e) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; color:var(--ai-danger);">Error fetching catalog: ' + e.message + '</td></tr>';
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    function renderModelCatalogTable(models) {
        const tbody = document.getElementById('modelCatalogTableBody');
        if (!models || models.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; color:var(--ai-text-muted); padding:20px;">No models match the filter.</td></tr>';
            return;
        }

        tbody.innerHTML = models.map(m => `
            <tr>
                <td><strong>${m.provider_display}</strong></td>
                <td><code>${m.model_id}</code></td>
                <td>${m.display_name}</td>
                <td><span class="badge" style="background:var(--ai-surface-subtle);">${m.context_window}</span></td>
                <td>
                    ${m.is_free ? '<span class="status-pill status-active">FREE TIER</span>' : '<span class="status-pill status-warning">PAID TIER</span>'}
                </td>
                <td>$${m.input_price_per_1m.toFixed(4)}</td>
                <td>$${m.output_price_per_1m.toFixed(4)}</td>
                <td>
                    ${m.is_selected ? '<span style="color:var(--ai-success); font-weight:700;"><i class="fas fa-check-circle"></i> Active</span>' : '<span style="color:var(--ai-text-muted);">Available</span>'}
                </td>
                <td>
                    <button type="button" class="btn-ai btn-ai-outline" style="padding:4px 8px; font-size:11.5px;" onclick="selectModelFromCatalog('${m.provider}', '${m.model_id}')">
                        Select
                    </button>
                </td>
            </tr>
        `).join('');
    }

    function filterModelCatalogUI() {
        const query = (document.getElementById('catalogSearchInput').value || '').toLowerCase().trim();
        const provFilter = document.getElementById('catalogProviderFilter').value;
        const tierFilter = document.getElementById('catalogPricingFilter').value;

        const filtered = cachedCatalogModels.filter(m => {
            const matchesQuery = !query || m.model_id.toLowerCase().includes(query) || m.display_name.toLowerCase().includes(query);
            const matchesProv = (provFilter === 'all') || (m.provider === provFilter);
            const matchesTier = (tierFilter === 'all') || (tierFilter === 'free' && m.is_free) || (tierFilter === 'paid' && !m.is_free);
            return matchesQuery && matchesProv && matchesTier;
        });

        renderModelCatalogTable(filtered);
    }

    function selectModelFromCatalog(provider, modelId) {
        selectProvider(provider);
        switchMainTab('providers');
        const modelSelect = document.getElementById('cfgSelectedModel');
        if (modelSelect) {
            modelSelect.value = modelId;
            markUnsaved();
            showToast(`Selected model '${modelId}' for provider '${provider}'. Save configuration to apply.`, "info");
        }
    }

    // =========================================================================
    // Company AI Diagnostics Client
    // =========================================================================
    let currentSelectedCompany = null;
    let companySearchTimeout = null;

    function onDiagCompanySearchInput(val) {
        clearTimeout(companySearchTimeout);
        const dropdown = document.getElementById('diagCompanyDropdown');
        if (!val || val.length < 2) {
            dropdown.style.display = 'none';
            return;
        }

        companySearchTimeout = setTimeout(async () => {
            try {
                const res = await fetch(`/admin-portal/ai-config/company/search/?q=${encodeURIComponent(val)}`);
                const data = await res.json();
                if (data.success && data.companies && data.companies.length > 0) {
                    dropdown.innerHTML = data.companies.map(c => `
                        <div class="company-dropdown-item" onclick="onSelectCompanyForDiag('${c.id}', '${escape(c.name)}', '${escape(c.website_url)}', '${escape(c.industry)}')">
                            <strong>${c.name}</strong> <span style="color:var(--ai-text-muted); font-size:11px;">(${c.id})</span><br>
                            <span style="color:var(--ai-navy); font-size:11px;">${c.website_url}</span>
                        </div>
                    `).join('');
                    dropdown.style.display = 'block';
                } else {
                    dropdown.innerHTML = '<div style="padding:10px; color:var(--ai-text-muted); font-size:12px;">No matching companies found.</div>';
                    dropdown.style.display = 'block';
                }
            } catch (e) {
                dropdown.style.display = 'none';
            }
        }, 250);
    }

    function onSelectCompanyForDiag(id, name, url, industry) {
        currentSelectedCompany = {
            id: id,
            name: unescape(name),
            url: unescape(url),
            industry: unescape(industry)
        };

        document.getElementById('diagCompanyDropdown').style.display = 'none';
        document.getElementById('diagCompanySearch').value = currentSelectedCompany.name;
        document.getElementById('diagTargetName').textContent = currentSelectedCompany.name;
        document.getElementById('diagTargetId').textContent = currentSelectedCompany.id;
        document.getElementById('diagTargetIndustry').textContent = currentSelectedCompany.industry;
        const link = document.getElementById('diagTargetUrlLink');
        link.textContent = currentSelectedCompany.url;
        link.href = currentSelectedCompany.url;

        document.getElementById('diagSelectedCompanyCard').style.display = 'flex';
        document.getElementById('diagResultsContainer').style.display = 'none';

        loadCompanyDiagnosticHistory(id);
    }

    async function loadCompanyDiagnosticHistory(companyId) {
        const histContainer = document.getElementById('diagHistoryContainer');
        const histTbody = document.getElementById('diagHistoryTableBody');

        try {
            const res = await fetch(`/admin-portal/ai-config/company/${companyId}/history/`);
            const data = await res.json();
            if (data.success && data.history && data.history.length > 0) {
                histTbody.innerHTML = data.history.map(h => `
                    <tr>
                        <td>${h.timestamp.replace('T', ' ').substring(0, 19)}</td>
                        <td><code>${h.task}</code></td>
                        <td>${h.provider} / ${h.model}</td>
                        <td><span class="status-pill status-${h.status === 'SUCCESS' ? 'active' : 'warning'}">${h.status}</span></td>
                        <td>${h.latency_ms} ms</td>
                        <td>${h.total_tokens}</td>
                        <td><span class="badge" style="background:var(--ai-surface-subtle);">${h.validation_result || 'PASSED'}</span></td>
                    </tr>
                `).join('');
                histContainer.style.display = 'block';
            } else {
                histContainer.style.display = 'none';
            }
        } catch (e) {
            histContainer.style.display = 'none';
        }
    }

    async function executeCompanyDiagnostic() {
        if (!currentSelectedCompany) {
            showToast("Please select a target company first.", "warning");
            return;
        }

        const task = document.getElementById('diagTaskSelect').value;
        const btn = document.getElementById('btnExecuteDiagnostic');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Running Diagnostic...';

        try {
            const res = await fetch('/admin-portal/ai-config/company/diagnostic/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    company_id: currentSelectedCompany.id,
                    task: task
                })
            });

            const data = await res.json();
            if (data.success) {
                document.getElementById('diagStatusBadge').textContent = data.status;
                document.getElementById('diagStatusBadge').className = 'status-pill status-active';
                document.getElementById('diagLatencyVal').textContent = data.duration_ms;
                document.getElementById('diagTokensVal').textContent = data.tokens.total;
                document.getElementById('diagMethodVal').textContent = data.tokens.method;
                document.getElementById('diagEvidenceBox').textContent = data.evidence_excerpt || "No raw text excerpt returned.";
                document.getElementById('diagStructuredJson').textContent = JSON.stringify(data.diagnostic_result, null, 2);

                document.getElementById('diagResultsContainer').style.display = 'block';
                showToast(`Diagnostic for ${currentSelectedCompany.name} completed successfully.`, "success");
                loadCompanyDiagnosticHistory(currentSelectedCompany.id);
            } else {
                showToast(data.message || data.error || "Diagnostic failed.", "danger");
            }
        } catch (e) {
            showToast("Error running diagnostic: " + e.message, "danger");
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-play" style="margin-right:6px;"></i>Run Live Diagnostic';
        }
    }

    // =========================================================================
    // Failover & Routing Simulation Client
    // =========================================================================
    async function runPrimaryPingTest() {
        const btn = document.getElementById('btnPrimaryPing');
        const resBox = document.getElementById('primaryPingResult');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing Primary...';
        resBox.style.display = 'none';

        try {
            // Find current primary provider
            const primProv = "{{ settings.primary_provider|default:'gemini' }}";
            const res = await fetch(`/admin-portal/ai-config/provider/${primProv}/test/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({})
            });
            const data = await res.json();
            resBox.style.display = 'block';
            if (data.success) {
                resBox.innerHTML = `<span style="color:var(--ai-success); font-weight:700;"><i class="fas fa-check-circle"></i> Connected (${data.latency_ms || 0} ms)</span> &bull; ${data.message || 'Authentication verified.'}`;
            } else {
                resBox.innerHTML = `<span style="color:var(--ai-danger); font-weight:700;"><i class="fas fa-times-circle"></i> Failed:</span> ${data.message || data.error}`;
            }
        } catch (e) {
            resBox.style.display = 'block';
            resBox.innerHTML = `<span style="color:var(--ai-danger);">Error: ${e.message}</span>`;
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-network-wired" style="margin-right:6px;"></i>Ping Primary Connection';
        }
    }

    async function runRoutingFailoverTest() {
        const btn = document.getElementById('btnRoutingTest');
        const traceContainer = document.getElementById('failoverTraceContainer');
        const traceSteps = document.getElementById('failoverTraceSteps');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Simulating Failover...';
        traceContainer.style.display = 'none';

        try {
            const res = await fetch('/admin-portal/ai-config/test-routing/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({})
            });
            const data = await res.json();
            traceContainer.style.display = 'block';

            if (data.trace && data.trace.length > 0) {
                traceSteps.innerHTML = data.trace.map(s => `
                    <div class="trace-step-item ${s.status === 'SUCCESS' ? 'is-success' : (s.status === 'BLOCKED' ? 'is-blocked' : '')}">
                        <div style="font-size:13px; font-weight:700; color:var(--ai-text-main);">
                            Step ${s.step}: ${s.phase} &bull; <span class="badge" style="background:var(--ai-surface);">${s.status || 'OK'}</span>
                        </div>
                        <div style="font-size:12px; color:var(--ai-text-muted); margin-top:3px;">
                            Provider: <strong>${s.provider || '-'}</strong> | Model: <code>${s.model || '-'}</code>
                        </div>
                        <div style="font-size:12px; color:var(--ai-text-main); margin-top:2px;">
                            ${s.message || s.reason || 'Phase executed.'}
                        </div>
                    </div>
                `).join('');
            }
            showToast("Routing and failover simulation completed.", "info");
        } catch (e) {
            showToast("Error testing failover: " + e.message, "danger");
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-random" style="margin-right:6px;"></i>Simulate Failover';
        }
    }

    async function runBatchTestAll() {
        const btn = document.getElementById('btnBatchTestAll');
        const matrix = document.getElementById('batchTestResultsMatrix');
        const tbody = document.getElementById('batchTestTableBody');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Running All Tests...';
        matrix.style.display = 'none';

        try {
            const res = await fetch('/admin-portal/ai-config/test-all/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({})
            });
            const data = await res.json();
            matrix.style.display = 'block';

            if (data.results && data.results.length > 0) {
                tbody.innerHTML = data.results.map(r => `
                    <tr>
                        <td><strong>${r.display_name}</strong> (<code>${r.provider}</code>)</td>
                        <td><code>${r.effective_model || '-'}</code></td>
                        <td>
                            ${r.success ? '<span class="status-pill status-active">VERIFIED</span>' : (r.status === 'UNCONFIGURED' ? '<span class="status-pill status-warning">UNCONFIGURED</span>' : '<span class="status-pill status-error">' + r.status + '</span>')}
                        </td>
                        <td>${r.latency_ms || 0} ms</td>
                        <td>${r.message || '-'}</td>
                    </tr>
                `).join('');
            }
            showToast("Batch provider testing complete.", "success");
        } catch (e) {
            showToast("Error running batch test: " + e.message, "danger");
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-clipboard-check" style="margin-right:6px;"></i>Run All Checks';
        }
    }

    async function loadLiveTelemetryData() {
        try {
            const res = await fetch('/admin-portal/ai-config/usage/summary/?days=30');
            const data = await res.json();
            if (data.success && data.summary) {
                const s = data.summary;
                const cachedEl = document.getElementById('usageTotalCached');
                if (cachedEl && s.total_calls > 0) {
                    cachedEl.textContent = s.total_calls + " calls";
                }
            }
        } catch (e) {
            // silent catch
        }
    }
'''

assert old_switch_fn in content, "old_switch_fn not found in content"
content = content.replace(old_switch_fn, new_switch_fn)

with open('templates/admin/ai_config/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated index.html successfully! New lines count:", len(content.splitlines()))
