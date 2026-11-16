/**
 * PolicySetu — Global Application JavaScript
 * Bridging Government Policies & People.
 */

// ─── App State ───────────────────────────────────────────────────────────────
const PS = {
  lang: localStorage.getItem('ps_lang') || document.documentElement.lang || 'en',
  theme: localStorage.getItem('ps_theme') || 'light',
  sidebarCollapsed: localStorage.getItem('ps_sidebar_collapsed') === 'true',
  baseUrl: window.location.origin,
};

// ─── DOM Ready ───────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initSidebar();
  initLanguageSwitcher();
  initMobileMenu();
  initToasts();
  initActiveNav();
});

// ═══════════════════════════════════════════════════════════════════════════
// SIDEBAR
// ═══════════════════════════════════════════════════════════════════════════
function initSidebar() {
  const sidebar = document.getElementById('sidebar');
  const toggleBtn = document.getElementById('sidebarToggle');

  if (!sidebar) return;

  function updateToggleState() {
    const isCollapsed = sidebar.classList.contains('collapsed');
    PS.sidebarCollapsed = isCollapsed;
    localStorage.setItem('ps_sidebar_collapsed', isCollapsed);

    if (toggleBtn) {
      toggleBtn.setAttribute('title', isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar');
      toggleBtn.setAttribute('aria-label', isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar');
    }
  }

  // Restore persisted state on desktop
  if (PS.sidebarCollapsed && window.innerWidth > 768) {
    sidebar.classList.add('collapsed');
  }
  updateToggleState();

  if (toggleBtn) {
    toggleBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      sidebar.classList.toggle('collapsed');
      updateToggleState();
    });
  }

  // Tooltip on collapsed items
  const navLinks = sidebar.querySelectorAll('.nav-link');
  navLinks.forEach(link => {
    link.addEventListener('mouseenter', () => {
      if (sidebar.classList.contains('collapsed') && window.innerWidth > 768) {
        const label = link.querySelector('.nav-label')?.textContent?.trim();
        if (label) showTooltip(link, label);
      }
    });
    link.addEventListener('mouseleave', hideTooltip);

    // Close mobile drawer when user taps any nav link
    link.addEventListener('click', () => {
      if (window.innerWidth <= 768) {
        closeMobileMenu();
      }
    });
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// MOBILE MENU & DRAWER NAVIGATION
// ═══════════════════════════════════════════════════════════════════════════
function closeMobileMenu() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  const mobileBtn = document.getElementById('mobileMenuBtn');

  sidebar?.classList.remove('mobile-open');
  overlay?.classList.remove('visible');
  document.body.classList.remove('mobile-nav-open');
  document.body.style.overflow = '';

  mobileBtn?.setAttribute('aria-expanded', 'false');
  sidebar?.setAttribute('aria-hidden', 'true');
}

function openMobileMenu() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  const mobileBtn = document.getElementById('mobileMenuBtn');
  const closeBtn = document.getElementById('mobileDrawerClose');

  sidebar?.classList.add('mobile-open');
  overlay?.classList.add('visible');
  document.body.classList.add('mobile-nav-open');
  document.body.style.overflow = 'hidden';

  mobileBtn?.setAttribute('aria-expanded', 'true');
  sidebar?.setAttribute('aria-hidden', 'false');

  // Focus close button for keyboard accessibility
  setTimeout(() => {
    closeBtn?.focus();
  }, 100);
}

function initMobileMenu() {
  const mobileBtn = document.getElementById('mobileMenuBtn');
  const closeBtn = document.getElementById('mobileDrawerClose');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');

  if (mobileBtn) {
    mobileBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      if (sidebar?.classList.contains('mobile-open')) {
        closeMobileMenu();
      } else {
        openMobileMenu();
      }
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      closeMobileMenu();
      mobileBtn?.focus();
    });
  }

  overlay?.addEventListener('click', () => {
    closeMobileMenu();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && sidebar?.classList.contains('mobile-open')) {
      closeMobileMenu();
      mobileBtn?.focus();
    }
  });

  // Automatically reset mobile drawer if viewport expands to desktop
  window.addEventListener('resize', () => {
    if (window.innerWidth > 768 && sidebar?.classList.contains('mobile-open')) {
      closeMobileMenu();
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// THEME SWITCHER (LIGHT & DARK)
// ═══════════════════════════════════════════════════════════════════════════
function applyTheme(theme) {
  PS.theme = theme;
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('ps_theme', theme);

  // Sync settings page toggle button if present
  const settingsToggle = document.getElementById('settingsThemeToggle');
  if (settingsToggle) {
    if (theme === 'dark') {
      settingsToggle.classList.add('on');
      settingsToggle.innerText = 'Dark Theme';
    } else {
      settingsToggle.classList.remove('on');
      settingsToggle.innerText = 'Light Theme (Default)';
    }
  }
}

function initTheme() {
  applyTheme(PS.theme);

  const themeBtn = document.getElementById('themeToggleBtn');
  if (themeBtn) {
    themeBtn.addEventListener('click', () => {
      const newTheme = PS.theme === 'dark' ? 'light' : 'dark';
      applyTheme(newTheme);
      showToast(newTheme === 'dark' ? 'Dark theme enabled' : 'Light theme enabled', 'info', 2500);
    });
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// LANGUAGE DROPDOWN & SWITCHER
// ═══════════════════════════════════════════════════════════════════════════
function initLanguageSwitcher() {
  const langNames = {
    en: 'English',
    hi: 'हिन्दी (Hindi)',
    mr: 'मराठी (Marathi)'
  };

  const dropdownBtn = document.getElementById('langDropdownBtn');
  const dropdownMenu = document.getElementById('langDropdownMenu');

  if (dropdownBtn && dropdownMenu) {
    dropdownBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = dropdownMenu.classList.toggle('show');
      dropdownBtn.setAttribute('aria-expanded', isOpen);
    });

    document.addEventListener('click', (e) => {
      if (!dropdownBtn.contains(e.target) && !dropdownMenu.contains(e.target)) {
        dropdownMenu.classList.remove('show');
        dropdownBtn.setAttribute('aria-expanded', 'false');
      }
    });
  }

  const items = document.querySelectorAll('.lang-dropdown-item[data-lang]');
  items.forEach(btn => {
    btn.addEventListener('click', () => {
      const lang = btn.dataset.lang;
      if (!lang) return;

      dropdownMenu?.classList.remove('show');

      if (lang === PS.lang) return;

      PS.lang = lang;
      localStorage.setItem('ps_lang', lang);
      document.documentElement.lang = lang;

      showToast(`Language switched to ${langNames[lang] || lang}. More regional Indian languages coming soon!`, 'info', 3500);

      const url = new URL(window.location.href);
      url.searchParams.set('lang', lang);
      setTimeout(() => {
        window.location.href = url.toString();
      }, 350);
    });
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// ACTIVE NAV ITEM
// ═══════════════════════════════════════════════════════════════════════════
function initActiveNav() {
  const path = window.location.pathname;
  const navLinks = document.querySelectorAll('#sidebar .nav-link');

  navLinks.forEach(link => {
    const href = link.getAttribute('href');
    if (!href) return;
    link.classList.remove('active');
    if (href === '/' && path === '/') {
      link.classList.add('active');
    } else if (href !== '/' && path.startsWith(href)) {
      link.classList.add('active');
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// TOAST SYSTEM
// ═══════════════════════════════════════════════════════════════════════════
let toastContainer;

function initToasts() {
  toastContainer = document.getElementById('toastContainer');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container';
    toastContainer.id = 'toastContainer';
    document.body.appendChild(toastContainer);
  }
}

function showToast(message, type = 'info', duration = 4000) {
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `<span style="font-weight:600;">[${type.toUpperCase()}]</span> <span>${message}</span>`;
  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'slideIn 0.3s ease reverse';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ═══════════════════════════════════════════════════════════════════════════
// TOOLTIP (for collapsed sidebar)
// ═══════════════════════════════════════════════════════════════════════════
let activeTooltip = null;

function showTooltip(anchor, text) {
  hideTooltip();
  const tip = document.createElement('div');
  tip.className = 'sidebar-tooltip';
  tip.textContent = text;
  tip.style.cssText = `
    position: fixed;
    background: #1E293B;
    color: white;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    pointer-events: none;
    z-index: 9999;
    white-space: nowrap;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  `;

  document.body.appendChild(tip);

  const rect = anchor.getBoundingClientRect();
  tip.style.left = (rect.right + 10) + 'px';
  tip.style.top  = (rect.top + rect.height / 2 - tip.offsetHeight / 2) + 'px';

  activeTooltip = tip;
}

function hideTooltip() {
  activeTooltip?.remove();
  activeTooltip = null;
}

// ═══════════════════════════════════════════════════════════════════════════
// API HELPER
// ═══════════════════════════════════════════════════════════════════════════
async function apiGet(endpoint, params = {}) {
  let path = endpoint;
  if (!path.startsWith('/api')) {
    path = `/api${path}`;
  }
  const url = new URL(path, PS.baseUrl);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== '') url.searchParams.set(k, v);
  });

  const res = await fetch(url.toString(), {
    headers: { 'Accept': 'application/json' }
  });

  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

async function apiPost(endpoint, body = {}) {
  let path = endpoint;
  if (!path.startsWith('/api')) {
    path = `/api${path}`;
  }
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

// ═══════════════════════════════════════════════════════════════════════════
// DATE FORMATTING
// ═══════════════════════════════════════════════════════════════════════════
function formatDate(dateStr) {
  if (!dateStr) return '—';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch { return dateStr; }
}

function timeAgo(dateStr) {
  if (!dateStr) return '—';
  try {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now - d;
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1)   return 'Just now';
    if (diffMins < 60)  return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins/60)}h ago`;
    return `${Math.floor(diffMins/1440)}d ago`;
  } catch { return dateStr; }
}

// ═══════════════════════════════════════════════════════════════════════════
// POLICY CARD RENDERER
// ═══════════════════════════════════════════════════════════════════════════
function renderPolicyCard(policy) {
  const isScholarship = policy.is_scholarship || policy.academic_year || (policy.type === 'scheme' && policy.jurisdiction === 'Maharashtra');
  const newBadge = PS.lang === 'hi' ? 'नया' : (PS.lang === 'mr' ? 'नवीन' : 'New');
  const updatedBadge = PS.lang === 'hi' ? 'संशोधित' : (PS.lang === 'mr' ? 'सुधारित' : 'Updated');
  const badges = [];

  if (policy.is_new)      badges.push(`<span class="badge badge-new">${newBadge}</span>`);
  if (policy.is_modified) badges.push(`<span class="badge badge-updated">${updatedBadge}</span>`);
  if (policy.category)    badges.push(`<span class="badge badge-category">${escHtml(policy.category)}</span>`);
  if (isScholarship && policy.academic_year) {
    badges.push(`<span class="badge" style="background:rgba(37,99,235,0.12);color:#1d4ed8;font-weight:600">AY: ${escHtml(policy.academic_year)}</span>`);
  }
  if (isScholarship && policy.application_status) {
    badges.push(`<span class="badge" style="background:rgba(16,185,129,0.12);color:#059669;font-weight:600">${escHtml(policy.application_status)}</span>`);
  }

  const jurisClass = policy.jurisdiction === 'Central Government' ? 'badge-central' : 'badge-state';
  const jurisLabel = (policy.jurisdiction === 'Central Government')
    ? (PS.lang === 'hi' ? 'केंद्र सरकार' : (PS.lang === 'mr' ? 'केंद्र शासन' : 'Central Government'))
    : policy.jurisdiction;
  const stakeholderChips = (policy.stakeholders || []).slice(0, 3).map(
    s => `<span class="stakeholder-chip">${escHtml(s)}</span>`
  ).join('');

  let title = policy.scheme_name || policy.title;
  let summary = policy.eligibility_summary || policy.summary || '';
  if (PS.lang === 'hi') {
    if (policy.title_hi) title = policy.title_hi;
    if (policy.summary_hi) summary = policy.summary_hi;
  } else if (PS.lang === 'mr') {
    if (policy.title_mr) title = policy.title_mr;
    if (policy.summary_mr) summary = policy.summary_mr;
  }

  const detailsLabel = PS.lang === 'hi' ? 'विवरण देखें' : (PS.lang === 'mr' ? 'तपशील पहा' : 'View Details');
  const sourceLabel = isScholarship ? 'Official Website' : (PS.lang === 'hi' ? 'आधिकारिक स्रोत' : (PS.lang === 'mr' ? 'अधिकृत स्रोत' : 'Official Source'));
  const publishedLabel = PS.lang === 'hi' ? 'प्रकाशित' : (PS.lang === 'mr' ? 'प्रसिद्ध' : 'Published');
  const detectedLabel = isScholarship
    ? (PS.lang === 'hi' ? 'सत्यापित' : (PS.lang === 'mr' ? 'पडताळणी' : 'Last Verified'))
    : (PS.lang === 'hi' ? 'पहचाना गया' : (PS.lang === 'mr' ? 'नोंदवलेली तारीख' : 'Detected'));

  const verifiedDateVal = policy.last_verified_at || policy.detected_date;

  return `
    <div class="policy-card" onclick="window.location='/policies/${policy.id}'" role="article" tabindex="0"
         onkeydown="if(event.key==='Enter')window.location='/policies/${policy.id}'">
      <div class="policy-card-header">
        <div class="policy-card-badges">
          ${badges.join('')}
        </div>
        <span class="policy-card-type">${escHtml(isScholarship ? 'Scholarship Scheme' : (policy.type || 'Policy'))}</span>
      </div>

      <h3 class="policy-card-title">${escHtml(title)}</h3>

      <div class="policy-card-ministry">
        <span>${escHtml(policy.department || policy.ministry || policy.source_name || '')}</span>
        <span class="badge ${jurisClass}" style="margin-left:auto">${escHtml(jurisLabel || '')}</span>
      </div>

      <p class="policy-card-summary">${escHtml(summary)}</p>

      <div class="policy-card-meta">
        <span class="meta-item">${publishedLabel}: ${formatDate(policy.published_date)}</span>
        <span class="meta-item">${detectedLabel}: ${formatDate(verifiedDateVal)}</span>
      </div>

      ${stakeholderChips ? `<div class="policy-card-stakeholders">${stakeholderChips}</div>` : ''}

      <div class="policy-card-actions">
        <a href="/policies/${policy.id}" class="btn btn-primary btn-sm" onclick="event.stopPropagation()">
          ${detailsLabel}
        </a>
        ${policy.official_url_available && policy.official_url ? `
          <a href="${escHtml(policy.official_url)}" target="_blank" rel="noopener noreferrer"
             class="btn btn-outline btn-sm" onclick="event.stopPropagation()">
            ${sourceLabel} &rarr;
          </a>
        ` : (policy.official_scheme_url ? `
          <a href="${escHtml(policy.official_scheme_url)}" target="_blank" rel="noopener noreferrer"
             class="btn btn-outline btn-sm" onclick="event.stopPropagation()">
            ${sourceLabel} &rarr;
          </a>
        ` : (policy.source_listing_url ? `
          <a href="${escHtml(policy.source_listing_url)}" target="_blank" rel="noopener noreferrer"
             class="btn btn-outline btn-sm" onclick="event.stopPropagation()">
            Source Portal &rarr;
          </a>
        ` : `
          <span class="btn btn-outline btn-sm" style="opacity:0.6;pointer-events:none" onclick="event.stopPropagation()">
            Link Unavailable
          </span>
        `))}
        ${isScholarship && policy.official_guidelines_url ? `
          <a href="${escHtml(policy.official_guidelines_url)}" target="_blank" rel="noopener noreferrer"
             class="btn btn-outline btn-sm" onclick="event.stopPropagation()" style="border-color:#2563eb;color:#1d4ed8">
            Guidelines &rarr;
          </a>
        ` : ''}
      </div>
    </div>
  `;
}

// ═══════════════════════════════════════════════════════════════════════════
// PAGINATION RENDERER
// ═══════════════════════════════════════════════════════════════════════════
function renderPagination(meta, onPageChange) {
  if (!meta || meta.total_pages <= 1) return '';

  const { page, total_pages } = meta;
  const pages = [];

  for (let i = 1; i <= total_pages; i++) {
    if (
      i === 1 || i === total_pages ||
      (i >= page - 1 && i <= page + 1)
    ) {
      pages.push(i);
    } else if (pages[pages.length - 1] !== '...') {
      pages.push('...');
    }
  }

  const btns = pages.map(p => {
    if (p === '...') return `<span class="page-btn" disabled>&hellip;</span>`;
    return `<button class="page-btn ${p === page ? 'active' : ''}"
      onclick="(${onPageChange.toString()})(${p})">${p}</button>`;
  }).join('');

  const prev = page > 1 ? `<button class="page-btn" onclick="(${onPageChange.toString()})(${page-1})">&larr;</button>` : '';
  const next = page < total_pages ? `<button class="page-btn" onclick="(${onPageChange.toString()})(${page+1})">&rarr;</button>` : '';

  return `<div class="pagination">${prev}${btns}${next}</div>`;
}

// ═══════════════════════════════════════════════════════════════════════════
// SECURITY: HTML ESCAPE
// ═══════════════════════════════════════════════════════════════════════════
function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ═══════════════════════════════════════════════════════════════════════════
// EXPOSE GLOBALS
// ═══════════════════════════════════════════════════════════════════════════
window.PS = PS;
window.apiGet = apiGet;
window.apiPost = apiPost;
window.formatDate = formatDate;
window.timeAgo = timeAgo;
window.renderPolicyCard = renderPolicyCard;
window.renderPagination = renderPagination;
window.showToast = showToast;
window.escHtml = escHtml;
