import os

css_path = r"D:\Projects\PolicySetu\app\static\css\main.css"
with open(css_path, "r", encoding="utf-8") as f:
    text = f.read()

marker = "/* ═══════════════════════════════════════════════════════════════════════════\n   2. RESET & BASE"
idx = text.find(marker)

dark_css = """
/* ─── DARK THEME OVERRIDES ──────────────────────────────────────────────── */
[data-theme="dark"] {
  --color-paper:        #151E32;
  --color-surface:      #151E32;
  --color-bg:           #0B1324;
  --color-bg-alt:       #19253F;
  --color-border:       #27375A;
  --color-border-light: #1F2D4A;
  --color-slate:        #94A3B8;
  --color-slate-light:  #CBD5E1;

  --shadow-xs:   0 1px 2px rgba(0,0,0,0.3);
  --shadow-sm:   0 1px 3px rgba(0,0,0,0.4);
  --shadow-card: 0 4px 16px rgba(0,0,0,0.4);
  --shadow-lg:   0 10px 25px rgba(0,0,0,0.5);
  --shadow-xl:   0 20px 30px rgba(0,0,0,0.6);
}

[data-theme="dark"] body { background-color: var(--color-bg); color: #E2E8F0; }
[data-theme="dark"] h1, [data-theme="dark"] h2, [data-theme="dark"] h3, [data-theme="dark"] h4, [data-theme="dark"] h5, [data-theme="dark"] h6 { color: #F8FAFC; }
[data-theme="dark"] .topbar { background: #111A2E; border-bottom-color: #27375A; }
[data-theme="dark"] .breadcrumb-current { color: #F1F5F9; }
[data-theme="dark"] .policy-card, [data-theme="dark"] .kpi-card, [data-theme="dark"] .chart-card, [data-theme="dark"] .detail-card, [data-theme="dark"] .version-panel, [data-theme="dark"] .filters-panel, [data-theme="dark"] .table-wrapper, [data-theme="dark"] .settings-section, [data-theme="dark"] .settings-nav, [data-theme="dark"] .impact-card, [data-theme="dark"] .about-card, [data-theme="dark"] .about-hero, [data-theme="dark"] .category-card { background: #151E32; border-color: #27375A; }
[data-theme="dark"] .policy-card-title, [data-theme="dark"] .chart-card-title, [data-theme="dark"] .about-card-title, [data-theme="dark"] .section-title, [data-theme="dark"] .settings-section-title, [data-theme="dark"] .source-name, [data-theme="dark"] .kpi-value, [data-theme="dark"] .meta-val, [data-theme="dark"] .toggle-label, [data-theme="dark"] .impact-group-name, [data-theme="dark"] .category-card-name { color: #F8FAFC; }
[data-theme="dark"] .data-table th { background: #101828; border-bottom-color: #27375A; color: #94A3B8; }
[data-theme="dark"] .data-table td { border-bottom-color: #1F2D4A; color: #CBD5E1; }
[data-theme="dark"] .data-table tr:hover td { background: #1A2640; }
[data-theme="dark"] .form-control { background: #101828; border-color: #27375A; color: #F8FAFC; }
[data-theme="dark"] .form-control:focus { border-color: var(--color-saffron); }
[data-theme="dark"] .chat-panel { background: #151E32; border-color: #27375A; }
[data-theme="dark"] .chat-bubble.ai { background: #19253F; border-color: #27375A; color: #E2E8F0; }
[data-theme="dark"] .chat-input-area { background: #101828; border-top-color: #27375A; }
[data-theme="dark"] .chat-input { background: #151E32; border-color: #27375A; color: #F8FAFC; }
[data-theme="dark"] .chat-source { background: #151E32; border-color: #27375A; color: #93C5FD; }
[data-theme="dark"] .suggested-q-btn { background: #151E32; border-color: #27375A; color: #CBD5E1; }
[data-theme="dark"] .suggested-q-btn:hover { background: #1E2D4A; color: var(--color-saffron-light); border-color: var(--color-saffron); }
[data-theme="dark"] .btn-outline { color: #E2E8F0; border-color: #384C72; }
[data-theme="dark"] .btn-outline:hover { background: #1E2D4A; border-color: var(--color-saffron); }
[data-theme="dark"] .btn-ghost:hover { background: #19253F; color: #F8FAFC; }
[data-theme="dark"] .topbar-brand-mobile .topbar-title { color: #F8FAFC; }
[data-theme="dark"] .lang-switcher { background: #101828; border-color: #27375A; }
[data-theme="dark"] .theme-toggle-btn { background: #101828; border-color: #27375A; color: #CBD5E1; }
[data-theme="dark"] .theme-toggle-btn:hover { background: #1A2640; color: var(--color-saffron); }
[data-theme="dark"] .stakeholder-chip { background: #1A2640; border-color: #27375A; color: #CBD5E1; }
[data-theme="dark"] .category-card-badge { background: #101828 !important; color: var(--color-saffron-light) !important; border-color: #27375A !important; }

/* ─── THEME TOGGLE BUTTON ─────────────────────────────────────────────── */
.theme-toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  cursor: pointer;
  color: var(--color-muted);
  transition: all var(--transition-fast);
  padding: 0;
}

.theme-toggle-btn:hover {
  border-color: var(--color-navy);
  color: var(--color-navy);
}

.theme-icon-dark { display: none; }
.theme-icon-light { display: block; }

[data-theme="dark"] .theme-icon-dark { display: block; }
[data-theme="dark"] .theme-icon-light { display: none; }

"""

if idx != -1:
    new_text = text[:idx] + dark_css + text[idx:]
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(new_text)
    print("Dark theme successfully added to main.css")
else:
    print("Marker not found in main.css")
