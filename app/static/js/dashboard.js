/**
 * PolicySetu — Dashboard Charts (Chart.js)
 * Loads API data and renders category, jurisdiction, and timeline charts.
 */

document.addEventListener('DOMContentLoaded', () => {
  initDashboardCharts();
});

// Brand colours for charts
const CHART_COLORS = {
  navy:    '#0B2A6F',
  saffron: '#F59E0B',
  deep:    '#B45309',
  slate:   '#475569',
  teal:    '#0D9488',
  purple:  '#7C3AED',
  rose:    '#E11D48',
  cyan:    '#0891B2',
  green:   '#059669',
  orange:  '#EA580C',
  indigo:  '#4F46E5',
  pink:    '#DB2777',
  lime:    '#65A30D',
  sky:     '#0284C7',
  fuchsia: '#C026D3',
};

const PALETTE = Object.values(CHART_COLORS);

// Global Chart.js defaults
if (window.Chart) {
  Chart.defaults.font.family = "'Inter', -apple-system, sans-serif";
  Chart.defaults.font.size = 12;
  Chart.defaults.color = '#475569';
  Chart.defaults.plugins.legend.display = true;
}

async function initDashboardCharts() {
  await Promise.allSettled([
    loadCategoryChart(),
    loadJurisdictionChart(),
    loadTimelineChart(),
  ]);
}

// ─── Category Doughnut Chart ─────────────────────────────────────────────────
async function loadCategoryChart() {
  const canvas = document.getElementById('categoryChart');
  if (!canvas) return;

  try {
    const res = await apiGet('/stats/categories');
    const data = res.data?.slice(0, 10) || [];

    new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: data.map(d => d.category),
        datasets: [{
          data: data.map(d => d.count),
          backgroundColor: PALETTE.slice(0, data.length),
          borderWidth: 2,
          borderColor: '#fff',
          hoverBorderWidth: 3,
          hoverOffset: 6,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '62%',
        plugins: {
          legend: {
            position: 'right',
            labels: {
              boxWidth: 12,
              padding: 10,
              font: { size: 11 },
              color: '#475569',
            }
          },
          tooltip: {
            callbacks: {
              label: ctx => ` ${ctx.label}: ${ctx.parsed} policies`
            }
          }
        }
      }
    });
  } catch (err) {
    console.warn('Category chart error:', err);
    renderChartError('categoryChart', 'Could not load category data');
  }
}

// ─── Jurisdiction Bar Chart ───────────────────────────────────────────────────
async function loadJurisdictionChart() {
  const canvas = document.getElementById('jurisdictionChart');
  if (!canvas) return;

  try {
    const res = await apiGet('/stats/jurisdictions');
    const data = res.data || [];

    new Chart(canvas, {
      type: 'bar',
      data: {
        labels: data.map(d => d.jurisdiction),
        datasets: [{
          label: 'Policies',
          data: data.map(d => d.count),
          backgroundColor: PALETTE.map(c => c + 'CC'),
          borderColor: PALETTE,
          borderWidth: 2,
          borderRadius: 6,
          borderSkipped: false,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => ` ${ctx.parsed.x} policies`
            }
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            grid: { color: '#F1F5F9' },
            ticks: { stepSize: 1 }
          },
          y: {
            grid: { display: false },
            ticks: { font: { size: 11 } }
          }
        }
      }
    });
  } catch (err) {
    console.warn('Jurisdiction chart error:', err);
  }
}

// ─── Timeline Line Chart ──────────────────────────────────────────────────────
async function loadTimelineChart() {
  const canvas = document.getElementById('timelineChart');
  if (!canvas) return;

  try {
    const res = await apiGet('/stats/timeline');
    const data = res.data || [];

    new Chart(canvas, {
      type: 'line',
      data: {
        labels: data.map(d => d.month),
        datasets: [{
          label: 'Policies Published',
          data: data.map(d => d.count),
          borderColor: CHART_COLORS.navy,
          backgroundColor: 'rgba(11,42,111,0.06)',
          borderWidth: 2.5,
          fill: true,
          tension: 0.4,
          pointBackgroundColor: CHART_COLORS.saffron,
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          pointRadius: 5,
          pointHoverRadius: 7,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => ` ${ctx.parsed.y} policies`
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { size: 11 } }
          },
          y: {
            beginAtZero: true,
            grid: { color: '#F1F5F9' },
            ticks: { stepSize: 1 }
          }
        }
      }
    });
  } catch (err) {
    console.warn('Timeline chart error:', err);
  }
}

// ─── Source Health Chart ──────────────────────────────────────────────────────
async function loadSourceChart() {
  const canvas = document.getElementById('sourceChart');
  if (!canvas) return;

  try {
    const res = await apiGet('/stats/sources');
    const data = res.data || [];
    const active   = data.filter(s => s.status === 'active').length;
    const degraded = data.filter(s => s.status === 'degraded').length;
    const failed   = data.filter(s => s.status === 'failed').length;

    new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: ['Active', 'Degraded', 'Failed'],
        datasets: [{
          data: [active, degraded, failed],
          backgroundColor: ['#059669', '#D97706', '#DC2626'],
          borderWidth: 2,
          borderColor: '#fff',
          hoverOffset: 6,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '70%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: { boxWidth: 12, padding: 12, font: { size: 11 } }
          }
        }
      }
    });
  } catch (err) {
    console.warn('Source chart error:', err);
  }
}

function renderChartError(canvasId, msg) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const wrapper = canvas.closest('.chart-container') || canvas.parentElement;
  wrapper.innerHTML = `<div class="empty-state" style="padding:var(--space-8)">
    <div class="empty-icon">📊</div>
    <p class="empty-text">${msg}</p>
  </div>`;
}

// Expose for monitor page
window.loadSourceChart = loadSourceChart;
