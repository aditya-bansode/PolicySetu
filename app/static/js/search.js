/**
 * PolicySetu — Policy List & Explorer JavaScript
 * Handles search, status tabs (All / New / Updated), filtering, sorting,
 * URL synchronization, and pagination.
 */

const policyExplorer = {
  currentPage: 1,
  perPage: 12,
  filters: {
    q: '',
    category: '',
    type: '',
    state: '',
    sort: 'date_desc',
    status: 'all',
  },
  total: 0,
  loading: false,
};

document.addEventListener('DOMContentLoaded', () => {
  initPolicyExplorer();
});

function initPolicyExplorer() {
  const grid = document.getElementById('policyGrid');
  if (!grid) return;

  // 1. Read URL params into filters
  const params = new URLSearchParams(window.location.search);
  policyExplorer.filters.q        = params.get('q')        || '';
  policyExplorer.filters.category = params.get('category') || '';
  policyExplorer.filters.type     = params.get('type')     || '';
  policyExplorer.filters.state    = params.get('state')    || '';
  policyExplorer.filters.sort     = params.get('sort')     || 'date_desc';

  // Read status from status, is_new, or is_modified query params
  const rawStatus = (params.get('status') || '').toLowerCase();
  const isNew = params.get('is_new');
  const isModified = params.get('is_modified');

  if (rawStatus === 'new' || isNew === '1' || isNew === 'true') {
    policyExplorer.filters.status = 'new';
  } else if (rawStatus === 'updated' || isModified === '1' || isModified === 'true') {
    policyExplorer.filters.status = 'updated';
  } else {
    policyExplorer.filters.status = 'all';
  }

  // 2. Set filter UI control values
  setFilterValue('filterSearch',   policyExplorer.filters.q);
  setFilterValue('filterCategory', policyExplorer.filters.category);
  setFilterValue('filterType',     policyExplorer.filters.type);
  setFilterValue('filterState',    policyExplorer.filters.state);
  setFilterValue('filterSort',     policyExplorer.filters.sort);

  // 3. Highlight initial status tab and navigation links
  updateActiveTabUI(policyExplorer.filters.status);

  // 4. Bind Status Tab clicks
  document.querySelectorAll('.policy-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const targetStatus = tab.getAttribute('data-status') || 'all';
      if (policyExplorer.filters.status === targetStatus) return;

      policyExplorer.filters.status = targetStatus;
      policyExplorer.currentPage = 1;
      updateActiveTabUI(targetStatus);
      syncUrlParams();
      loadPolicies();
    });
  });

  // 5. Search input with debounce
  const searchInput = document.getElementById('filterSearch');
  if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        policyExplorer.filters.q = searchInput.value.trim();
        policyExplorer.currentPage = 1;
        syncUrlParams();
        loadPolicies();
      }, 350);
    });

    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        clearTimeout(debounceTimer);
        policyExplorer.filters.q = searchInput.value.trim();
        policyExplorer.currentPage = 1;
        syncUrlParams();
        loadPolicies();
      }
    });
  }

  // 6. Dropdown filter changes
  ['filterCategory', 'filterType', 'filterState', 'filterSort'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('change', () => {
      const key = id.replace('filter', '').toLowerCase();
      policyExplorer.filters[key] = el.value;
      policyExplorer.currentPage = 1;
      syncUrlParams();
      loadPolicies();
    });
  });

  // 7. Clear filters button
  document.getElementById('clearFilters')?.addEventListener('click', () => {
    policyExplorer.filters.q = '';
    policyExplorer.filters.category = '';
    policyExplorer.filters.type = '';
    policyExplorer.filters.state = '';
    policyExplorer.filters.sort = 'date_desc';
    // Retain or reset status tab: reset to all
    policyExplorer.filters.status = 'all';

    ['filterSearch', 'filterCategory', 'filterType', 'filterState'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    setFilterValue('filterSort', 'date_desc');
    updateActiveTabUI('all');
    policyExplorer.currentPage = 1;
    syncUrlParams();
    loadPolicies();
  });

  // 8. Fetch live counts for tabs
  loadTabCounts();

  // 9. Initial load
  loadPolicies();
}

function updateActiveTabUI(status) {
  document.querySelectorAll('.policy-tab').forEach(tab => {
    const tabStatus = tab.getAttribute('data-status');
    const isActive = tabStatus === status;
    tab.classList.toggle('active', isActive);
    tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
  });

  // Sync sidebar active indicator
  document.querySelectorAll('.sidebar .nav-link').forEach(link => {
    const href = link.getAttribute('href') || '';
    if (href.includes('is_new=1') || href.includes('status=new')) {
      link.classList.toggle('active', status === 'new');
    } else if (href.includes('is_modified=1') || href.includes('status=updated')) {
      link.classList.toggle('active', status === 'updated');
    } else if (href === '/policies' || href === '/policies?status=all') {
      link.classList.toggle('active', status === 'all');
    }
  });
}

function syncUrlParams() {
  const url = new URL(window.location);
  const f = policyExplorer.filters;

  if (f.status && f.status !== 'all') {
    url.searchParams.set('status', f.status);
    url.searchParams.delete('is_new');
    url.searchParams.delete('is_modified');
  } else {
    url.searchParams.delete('status');
    url.searchParams.delete('is_new');
    url.searchParams.delete('is_modified');
  }

  if (f.q) url.searchParams.set('q', f.q); else url.searchParams.delete('q');
  if (f.category) url.searchParams.set('category', f.category); else url.searchParams.delete('category');
  if (f.type) url.searchParams.set('type', f.type); else url.searchParams.delete('type');
  if (f.state) url.searchParams.set('state', f.state); else url.searchParams.delete('state');
  if (f.sort && f.sort !== 'date_desc') url.searchParams.set('sort', f.sort); else url.searchParams.delete('sort');

  window.history.replaceState({}, '', url.toString());
}

async function loadTabCounts() {
  try {
    const res = await apiGet('/dashboard/stats');
    if (res && res.data) {
      const { total_policies, new_this_week, modified_policies } = res.data;
      const elAll = document.getElementById('countAll');
      const elNew = document.getElementById('countNew');
      const elUpdated = document.getElementById('countUpdated');
      if (elAll && total_policies !== undefined) elAll.textContent = total_policies;
      if (elNew && new_this_week !== undefined) elNew.textContent = new_this_week;
      if (elUpdated && modified_policies !== undefined) elUpdated.textContent = modified_policies;
    }
  } catch (err) {
    console.warn('Could not load tab counts:', err);
  }
}

async function loadPolicies() {
  if (policyExplorer.loading) return;
  policyExplorer.loading = true;

  const grid = document.getElementById('policyGrid');
  const paginationEl = document.getElementById('pagination');
  const resultsInfo = document.getElementById('resultsInfo');

  if (grid) {
    grid.innerHTML = renderLoadingCards(6);
  }

  try {
    const queryParams = {
      page:     policyExplorer.currentPage,
      per_page: policyExplorer.perPage,
      status:   policyExplorer.filters.status,
      q:        policyExplorer.filters.q,
      category: policyExplorer.filters.category,
      type:     policyExplorer.filters.type,
      state:    policyExplorer.filters.state,
      sort:     policyExplorer.filters.sort,
    };

    const res = await apiGet('/policies', queryParams);
    const { data: policies, meta } = res;
    policyExplorer.total = meta ? meta.total : 0;

    // Update active tab count with filtered total if matching status
    const currentTabCountEl = (policyExplorer.filters.status === 'new')
      ? document.getElementById('countNew')
      : ((policyExplorer.filters.status === 'updated')
        ? document.getElementById('countUpdated')
        : document.getElementById('countAll'));

    if (currentTabCountEl && !policyExplorer.filters.q && !policyExplorer.filters.category && !policyExplorer.filters.type && !policyExplorer.filters.state) {
      currentTabCountEl.textContent = policyExplorer.total;
    }

    if (!policies || policies.length === 0) {
      const emptyTitle = (PS.lang === 'hi')
        ? 'कोई नीति नहीं मिली'
        : ((PS.lang === 'mr') ? 'कोणतेही धोरण आढळले नाही' : 'No policies found');
      const emptyDesc = (PS.lang === 'hi')
        ? 'वर्तमान फ़िल्टर या खोज शर्तों के साथ कोई दस्तावेज उपलब्ध नहीं है।'
        : ((PS.lang === 'mr')
          ? 'सध्याच्या फिल्टर किंवा शोध अटींसह कोणतेही दस्तऐवज उपलब्ध नाहीत.'
          : 'Try adjusting your search terms or selecting another status tab.');
      grid.innerHTML = `
        <div class="empty-state" style="grid-column:1/-1">
          <h3 class="empty-title">${emptyTitle}</h3>
          <p class="empty-text">${emptyDesc}</p>
        </div>
      `;
      if (paginationEl) paginationEl.innerHTML = '';
    } else {
      grid.innerHTML = policies.map(renderPolicyCard).join('');
      if (paginationEl && meta) {
        paginationEl.innerHTML = renderPagination(meta, (page) => {
          policyExplorer.currentPage = page;
          loadPolicies();
          window.scrollTo({ top: 0, behavior: 'smooth' });
        });
      }
    }

    if (resultsInfo && meta) {
      const start = meta.total > 0 ? (meta.page - 1) * meta.per_page + 1 : 0;
      const end   = Math.min(meta.page * meta.per_page, meta.total);
      if (PS.lang === 'hi') {
        resultsInfo.textContent = meta.total > 0
          ? `${meta.total} में से ${start}–${end} नीतियां प्रदर्शित`
          : '0 नीतियां मिलीं';
      } else if (PS.lang === 'mr') {
        resultsInfo.textContent = meta.total > 0
          ? `${meta.total} पैकी ${start}–${end} धोरणे दर्शवित आहे`
          : '0 धोरणे आढळली';
      } else {
        resultsInfo.textContent = meta.total > 0
          ? `Showing ${start}–${end} of ${meta.total} policies`
          : '0 policies found';
      }
    }

  } catch (err) {
    console.error('Failed to load policies:', err);
    if (grid) {
      grid.innerHTML = `
        <div class="empty-state" style="grid-column:1/-1">
          <h3 class="empty-title">Failed to load policies</h3>
          <p class="empty-text">Please verify your connection and try again.</p>
        </div>
      `;
    }
    if (typeof showToast === 'function') {
      showToast('Failed to load policies', 'error');
    }
  } finally {
    policyExplorer.loading = false;
  }
}

function renderLoadingCards(count) {
  return Array.from({ length: count }, () => `
    <div class="policy-card" style="pointer-events:none">
      <div class="skeleton" style="height:20px;width:60%;margin-bottom:12px"></div>
      <div class="skeleton" style="height:16px;width:90%;margin-bottom:8px"></div>
      <div class="skeleton" style="height:16px;width:70%;margin-bottom:16px"></div>
      <div class="skeleton" style="height:60px;margin-bottom:12px"></div>
      <div class="skeleton" style="height:14px;width:40%"></div>
    </div>
  `).join('');
}

function setFilterValue(id, value) {
  const el = document.getElementById(id);
  if (el) el.value = value;
}
