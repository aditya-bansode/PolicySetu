css_path = r"D:\Projects\PolicySetu\app\static\css\main.css"
with open(css_path, "r", encoding="utf-8") as f:
    text = f.read()

dropdown_css = """
/* ─── LANGUAGE DROPDOWN SELECTOR ─────────────────────────────────────── */
.lang-dropdown-wrapper {
  position: relative;
  display: inline-block;
}

.lang-dropdown-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.lang-dropdown-btn:hover {
  border-color: var(--color-navy);
  color: var(--color-navy);
}

[data-theme="dark"] .lang-dropdown-btn {
  background: #101828;
  border-color: #27375A;
  color: #CBD5E1;
}

[data-theme="dark"] .lang-dropdown-btn:hover {
  border-color: var(--color-saffron);
  color: #F8FAFC;
}

.lang-dropdown-menu {
  display: none;
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  background: var(--color-paper);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  min-width: 220px;
  z-index: 1000;
  overflow: hidden;
  padding: 6px 0;
}

.lang-dropdown-menu.show {
  display: block;
  animation: slideIn 0.2s ease;
}

[data-theme="dark"] .lang-dropdown-menu {
  background: #151E32;
  border-color: #27375A;
  box-shadow: 0 10px 30px rgba(0,0,0,0.6);
}

.lang-dropdown-header {
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--color-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 6px 14px 4px;
}

.lang-dropdown-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  font-size: var(--text-xs);
  color: #374151;
  cursor: pointer;
  width: 100%;
  border: none;
  background: none;
  text-align: left;
  font-family: inherit;
  transition: background var(--transition-fast);
}

.lang-dropdown-item:hover {
  background: var(--color-bg);
  color: var(--color-navy);
}

.lang-dropdown-item.active {
  background: rgba(11, 42, 111, 0.08);
  color: var(--color-navy);
  font-weight: 700;
}

[data-theme="dark"] .lang-dropdown-item {
  color: #CBD5E1;
}

[data-theme="dark"] .lang-dropdown-item:hover {
  background: #1E2D4A;
  color: #F8FAFC;
}

[data-theme="dark"] .lang-dropdown-item.active {
  background: rgba(245, 158, 11, 0.15);
  color: var(--color-saffron);
}

.lang-dropdown-item.disabled {
  opacity: 0.6;
  cursor: pointer;
  background: none !important;
}

.lang-dropdown-item.disabled:hover {
  background: rgba(0,0,0,0.02) !important;
}

.lang-badge-soon {
  font-size: 0.65rem;
  padding: 2px 6px;
  background: var(--color-bg-alt);
  color: var(--color-muted);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  font-weight: 500;
}

[data-theme="dark"] .lang-badge-soon {
  background: #101828;
  border-color: #27375A;
  color: #94A3B8;
}

.lang-dropdown-divider {
  height: 1px;
  background: var(--color-border);
  margin: 4px 0;
}

[data-theme="dark"] .lang-dropdown-divider {
  background: #27375A;
}
"""

with open(css_path, "a", encoding="utf-8") as f:
    f.write(dropdown_css)

print("Added dropdown CSS successfully!")
