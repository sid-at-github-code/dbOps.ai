'use strict';

// ── DOM refs (shared desktop + mobile) ──────────────────────────────────────
const questionEl      = document.getElementById('question');
const rowLimitEl      = document.getElementById('rowLimit');
const runBtn          = document.getElementById('runBtn');
const copyBtn         = document.getElementById('copyBtn');
const sqlSection      = document.getElementById('sqlSection');
const sqlDisplay      = document.getElementById('sqlDisplay');
const metaSection     = document.getElementById('metaSection');
const validationBadge = document.getElementById('validationBadge');
const timingsEl       = document.getElementById('timingsEl');

const emptyState      = document.getElementById('emptyState');
const loadingState    = document.getElementById('loadingState');
const loadingMsg      = document.getElementById('loadingMsg');
const errorState      = document.getElementById('errorState');
const errorMsg        = document.getElementById('errorMsg');
const resultsState    = document.getElementById('resultsState');
const rowCountLabel   = document.getElementById('rowCountLabel');
const tableHead       = document.getElementById('tableHead');
const tableBody       = document.getElementById('tableBody');
const exportCsvBtn    = document.getElementById('exportCsvBtn');
const exportXlsxBtn   = document.getElementById('exportXlsxBtn');

const viewTableBtn    = document.getElementById('viewTableBtn');
const viewChartBtn    = document.getElementById('viewChartBtn');
const viewJsonBtn     = document.getElementById('viewJsonBtn');
const chartTypeSelect = document.getElementById('chartTypeSelect');
const exportPngBtn    = document.getElementById('exportPngBtn');
const tableScroll     = document.getElementById('tableScroll');
const chartContainer  = document.getElementById('chartContainer');
const chartNotPossible= document.getElementById('chartNotPossible');
const chartCanvasWrap = document.getElementById('chartCanvasWrap');
const chartCanvas     = document.getElementById('chartCanvas');
const jsonContainer   = document.getElementById('jsonContainer');
const jsonDisplay     = document.getElementById('jsonDisplay');

// ── Mobile-only DOM refs ─────────────────────────────────────────────────────
const appRootEl          = document.querySelector('.app');
const mobileMenuBtn      = document.getElementById('mobileMenuBtn');
const mobileExtras       = document.getElementById('mobileExtras');
const apiStatusMobileEl  = document.getElementById('apiStatusMobile');

const statsRefreshBtn    = document.getElementById('statsRefreshBtn');
const statTotalQueries   = document.getElementById('statTotalQueries');
const statSuccessRate    = document.getElementById('statSuccessRate');
const statAvgTime        = document.getElementById('statAvgTime');
const statLastRows       = document.getElementById('statLastRows');

const recentViewAllBtn   = document.getElementById('recentViewAllBtn');
const recentQueriesList  = document.getElementById('recentQueriesList');

const mobileBackBtn      = document.getElementById('mobileBackBtn');
const mobileDownloadBtn  = document.getElementById('mobileDownloadBtn');
const mobileShareBtn     = document.getElementById('mobileShareBtn');
const mobileFilterBtn    = document.getElementById('mobileFilterBtn');
const downloadMenu       = document.getElementById('downloadMenu');
const downloadCsvOpt     = document.getElementById('downloadCsvOpt');
const downloadXlsxOpt    = document.getElementById('downloadXlsxOpt');

const validationBadgeMobile = document.getElementById('validationBadgeMobile');
const mobileExecMeta      = document.getElementById('mobileExecMeta');
const mobileQuestionEcho  = document.getElementById('mobileQuestionEcho');
const mobilePagination    = document.getElementById('mobilePagination');

const queryDetailsCard   = document.getElementById('queryDetailsCard');
const detailExecutedAt   = document.getElementById('detailExecutedAt');
const detailRowLimit     = document.getElementById('detailRowLimit');
const detailRowsReturned = document.getElementById('detailRowsReturned');
const detailLlmTime      = document.getElementById('detailLlmTime');
const detailDbTime       = document.getElementById('detailDbTime');

const navHomeBtn         = document.getElementById('navHomeBtn');
const navHistoryBtn      = document.getElementById('navHistoryBtn');
const navSettingsBtn     = document.getElementById('navSettingsBtn');

const settingsBackdrop   = document.getElementById('settingsBackdrop');
const settingsSheet      = document.getElementById('settingsSheet');
const settingsApiBase    = document.getElementById('settingsApiBase');
const settingsRowLimit   = document.getElementById('settingsRowLimit');
const settingsSaveBtn    = document.getElementById('settingsSaveBtn');
const settingsClearHistoryBtn = document.getElementById('settingsClearHistoryBtn');
const settingsCloseBtn   = document.getElementById('settingsCloseBtn');

// ── State ─────────────────────────────────────────────────────────────────────
let rawSQL      = '';
let lastCols    = [];
let lastRows    = [];
let sortCol     = null;
let sortDir     = 'asc';   // 'asc' | 'desc'
let filters     = {};
let currentView = 'table'; // 'table' | 'chart' | 'json'
let chartInstance = null;

let lastQuestionRaw   = '';
let lastRowLimitUsed  = 10;
let recentExpanded    = false;
let mobilePage        = 1;
const MOBILE_PAGE_SIZE = 8;

const HISTORY_KEY = 'fetcherio_query_history';
const ROWLIMIT_KEY = 'fetcherio_default_row_limit';

function isMobile() {
  return window.matchMedia('(max-width: 768px)').matches;
}

// ── API health check (proves cross-origin CORS wiring is working) ──────────────
async function checkApiHealth() {
  try {
    const resp = await fetch(`${API_BASE}/health`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    apiStatusMobileEl.className = 'api-status-pill online';
  } catch (err) {
    apiStatusMobileEl.className = 'api-status-pill offline';
  }
}
checkApiHealth();

// ── Toast (mobile feedback) ─────────────────────────────────────────────────
function showToast(msg) {
  const t = document.createElement('div');
  t.className = 'mobile-toast';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 1800);
}

// ── Query history (localStorage) — powers Quick Stats + Recent Queries ──────
function loadHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveHistory(hist) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(hist));
}

function recordHistory(question, data, rowLimitUsed) {
  const entry = {
    id: Date.now().toString(36) + Math.random().toString(36).slice(2, 7),
    question,
    sql: data.sql || '',
    validated: !!data.validated,
    error: data.error || null,
    llm_time: data.llm_time || 0,
    db_time: data.db_time || 0,
    row_count: data.row_count || 0,
    rowLimit: rowLimitUsed,
    timestamp: Date.now(),
  };
  const hist = loadHistory();
  hist.unshift(entry);
  if (hist.length > 50) hist.length = 50;
  saveHistory(hist);
  renderStats();
  renderRecentQueries();
}

function timeAgo(ts) {
  const s = Math.max(1, Math.floor((Date.now() - ts) / 1000));
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ── Quick Stats ──────────────────────────────────────────────────────────────
function renderStats() {
  const hist = loadHistory();
  const total = hist.length;
  statTotalQueries.textContent = total.toLocaleString();

  if (!total) {
    statSuccessRate.textContent = '—';
    statAvgTime.textContent = '—';
    statLastRows.textContent = '—';
    return;
  }

  const successCount = hist.filter(h => h.validated && !h.error).length;
  statSuccessRate.textContent = `${Math.round((successCount / total) * 100)}%`;

  const avgTime = hist.reduce((sum, h) => sum + (h.llm_time || 0) + (h.db_time || 0), 0) / total;
  statAvgTime.textContent = `${avgTime.toFixed(2)}s`;

  statLastRows.textContent = hist[0].row_count.toLocaleString();
}

statsRefreshBtn.addEventListener('click', () => {
  renderStats();
  renderRecentQueries();
});

// ── Recent Queries ───────────────────────────────────────────────────────────
function renderRecentQueries() {
  const hist = loadHistory();
  recentQueriesList.innerHTML = '';

  if (!hist.length) {
    recentQueriesList.innerHTML = '<p class="recent-empty">No queries yet — run one above.</p>';
    return;
  }

  const shown = recentExpanded ? hist.slice(0, 15) : hist.slice(0, 4);
  shown.forEach(entry => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'recent-item';
    const totalTime = ((entry.llm_time || 0) + (entry.db_time || 0)).toFixed(2);
    btn.innerHTML = `
      <svg class="bolt" width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M13 2 3 14h7l-1 8 10-12h-7z"/></svg>
      <span class="recent-item-body">
        <span class="recent-item-q">${escapeHtml(entry.question)}</span>
        <span class="recent-item-meta">${entry.error ? 'Failed' : `${entry.row_count} rows`} · ${timeAgo(entry.timestamp)} · ${totalTime}s</span>
      </span>
    `;
    btn.addEventListener('click', () => {
      questionEl.value = entry.question;
      if (entry.rowLimit) rowLimitEl.value = entry.rowLimit;
      exitResultsView();
      questionEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      questionEl.focus();
    });
    recentQueriesList.appendChild(btn);
  });

  recentViewAllBtn.textContent = recentExpanded ? 'Show Less' : 'View All';
  recentViewAllBtn.classList.toggle('hidden', hist.length <= 4);
}

recentViewAllBtn.addEventListener('click', () => {
  recentExpanded = !recentExpanded;
  renderRecentQueries();
});

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Mobile screen navigation (form ⇄ results) ───────────────────────────────
function enterResultsView() {
  appRootEl.classList.add('results-active');
}

function exitResultsView() {
  appRootEl.classList.remove('results-active');
  setActiveNav('home');
}

function setActiveNav(name) {
  navHomeBtn.classList.toggle('active', name === 'home');
  navHistoryBtn.classList.toggle('active', name === 'history');
}

mobileBackBtn.addEventListener('click', exitResultsView);

navHomeBtn.addEventListener('click', () => {
  exitResultsView();
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

navHistoryBtn.addEventListener('click', () => {
  exitResultsView();
  setActiveNav('history');
  recentExpanded = true;
  renderRecentQueries();
  document.getElementById('recentQueriesCard').scrollIntoView({ behavior: 'smooth', block: 'start' });
});

mobileMenuBtn.addEventListener('click', () => {
  mobileExtras.classList.toggle('collapsed');
});

// ── Settings sheet ───────────────────────────────────────────────────────────
function openSettings() {
  settingsApiBase.value = localStorage.getItem('API_BASE') || '';
  settingsRowLimit.value = localStorage.getItem(ROWLIMIT_KEY) || rowLimitEl.value || 10;
  settingsBackdrop.classList.remove('hidden');
  settingsSheet.classList.remove('hidden');
}

function closeSettings() {
  settingsBackdrop.classList.add('hidden');
  settingsSheet.classList.add('hidden');
}

navSettingsBtn.addEventListener('click', openSettings);
settingsCloseBtn.addEventListener('click', closeSettings);
settingsBackdrop.addEventListener('click', closeSettings);

settingsSaveBtn.addEventListener('click', () => {
  const base = settingsApiBase.value.trim();
  if (base) localStorage.setItem('API_BASE', base);
  else localStorage.removeItem('API_BASE');

  const rl = parseInt(settingsRowLimit.value, 10);
  if (!isNaN(rl) && rl > 0) localStorage.setItem(ROWLIMIT_KEY, String(rl));

  location.reload();
});

settingsClearHistoryBtn.addEventListener('click', () => {
  localStorage.removeItem(HISTORY_KEY);
  renderStats();
  renderRecentQueries();
  showToast('Query history cleared');
});

// Prefill row limit from saved default, if any.
(() => {
  const saved = localStorage.getItem(ROWLIMIT_KEY);
  if (saved) rowLimitEl.value = saved;
})();

// ── Helpers ───────────────────────────────────────────────────────────────────

function showPanel(el) {
  [emptyState, loadingState, errorState, resultsState].forEach(s => s.classList.add('hidden'));
  el.classList.remove('hidden');
}

function setLoading(on) {
  runBtn.disabled = on;
  runBtn.querySelector('.btn-text').textContent = on ? 'Running…' : 'Run Query';
  if (on) showPanel(loadingState);
}

function esc(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** Very lightweight SQL keyword highlighter. */
const KW  = /\b(SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|FULL|CROSS|ON|AND|OR|NOT|IN|IS|NULL|AS|DISTINCT|ORDER|BY|GROUP|HAVING|LIMIT|OFFSET|BETWEEN|LIKE|ILIKE|UNION|ALL|CASE|WHEN|THEN|ELSE|END|EXISTS|WITH|RETURNING|OVER|PARTITION|INTERVAL|DATE)\b/g;
const FNS = /\b(COUNT|SUM|AVG|MIN|MAX|COALESCE|NULLIF|CAST|TO_DATE|TO_CHAR|CURRENT_DATE|CURRENT_TIMESTAMP|NOW|EXTRACT|DATE_PART|DATE_TRUNC|GREATEST|LEAST|ROUND|FLOOR|CEIL|ABS|LENGTH|LOWER|UPPER|TRIM|CONCAT|STRING_AGG|ARRAY_AGG|ROW_NUMBER|RANK|DENSE_RANK|LAG|LEAD|FIRST_VALUE|LAST_VALUE)\b/g;
const STR = /'([^']*)'/g;

function highlightSQL(sql) {
  let h = esc(sql);
  h = h.replace(STR, "<span class='str'>'$1'</span>");
  h = h.replace(FNS, "<span class='fn'>$&</span>");
  h = h.replace(KW,  "<span class='kw'>$&</span>");
  return h;
}

function isNumericVal(v) {
  if (v === null || v === undefined || v === '') return false;
  return !isNaN(Number(v));
}

function questionMentionsRowCount(q) {
  return /\b(top|first|last|limit|show me|return|fetch|get)\s+\d+\b/i.test(q) ||
         /\b\d+\s*(rows?|records?|results?|entries|items)\b/i.test(q);
}

// ── Main query flow ───────────────────────────────────────────────────────────
async function runQuery() {
  const question = questionEl.value.trim();
  if (!question) {
    questionEl.focus();
    return;
  }

  lastQuestionRaw = question;
  mobileQuestionEcho.textContent = question;
  enterResultsView();

  setLoading(true);
  loadingMsg.textContent = 'Generating SQL…';

  sqlSection.classList.add('hidden');
  metaSection.classList.add('hidden');

  const phaseTimer = setTimeout(() => {
    loadingMsg.textContent = 'Executing query…';
  }, 2500);

  try {
    const rowLimitRaw = rowLimitEl.value.trim();
    const rowLimit = rowLimitRaw !== '' ? parseInt(rowLimitRaw, 10) : 10;
    lastRowLimitUsed = rowLimit;
    const questionWithLimit = questionMentionsRowCount(question)
      ? question
      : `${question}\nReturn at most ${rowLimit} rows.`;

    const resp = await fetch(`${API_BASE}/api/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: questionWithLimit }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    handleResult(data);
  } catch (err) {
    showPanel(errorState);
    errorMsg.textContent = `Network error: ${err.message}`;
  } finally {
    clearTimeout(phaseTimer);
    setLoading(false);
  }
}

function setBadge(el, data) {
  if (data.validated) {
    el.className = 'badge ok';
    el.innerHTML = '&#10003;&nbsp; Validated &mdash; read only';
  } else if (data.sql) {
    el.className = 'badge err';
    el.innerHTML = '&#10005;&nbsp; Blocked';
  } else {
    el.className = 'badge';
    el.textContent = '';
  }
}

function handleResult(data) {
  if (data.sql) {
    rawSQL = data.sql;
    sqlDisplay.innerHTML = highlightSQL(data.sql);
    sqlSection.classList.remove('hidden');
  }

  setBadge(validationBadge, data);
  setBadge(validationBadgeMobile, data);

  const llm   = data.llm_time  ?? 0;
  const db    = data.db_time   ?? 0;
  const total = llm + db;
  timingsEl.innerHTML = `
    <div class="t-row">
      <span class="t-label">LLM</span>
      <span class="t-val">${llm.toFixed(2)} s</span>
    </div>
    ${db > 0 ? `
    <div class="t-row">
      <span class="t-label">Database</span>
      <span class="t-val">${db.toFixed(2)} s</span>
    </div>` : ''}
    <div class="t-row t-total">
      <span class="t-label">Total</span>
      <span class="t-val">${total.toFixed(2)} s</span>
    </div>
  `;
  metaSection.classList.remove('hidden');

  mobileExecMeta.textContent = `Executed in ${total.toFixed(2)}s · ${data.row_count ?? 0} rows`;

  detailExecutedAt.textContent = new Date().toLocaleString();
  detailRowLimit.textContent = String(lastRowLimitUsed);
  detailRowsReturned.textContent = String(data.row_count ?? 0);
  detailLlmTime.textContent = `${llm.toFixed(2)}s`;
  detailDbTime.textContent = `${db.toFixed(2)}s`;

  recordHistory(lastQuestionRaw, data, lastRowLimitUsed);

  if (data.error) {
    errorMsg.textContent = data.error;
    errorMsg.className = 'state-msg error';
    showPanel(errorState);
    return;
  }

  if (!data.rows || data.row_count === 0) {
    errorMsg.textContent = 'Query returned 0 rows.';
    errorMsg.className = 'state-msg';
    showPanel(errorState);
    return;
  }

  renderTable(data.columns, data.rows, data.row_count);
}

// ── Sort / filter helpers ─────────────────────────────────────────────────────

function getSortedFiltered() {
  const active = Object.entries(filters).filter(([, v]) => v.trim());
  let rows = active.length
    ? lastRows.filter(row => active.every(([col, term]) => {
        const v = row[col];
        if (v === null || v === undefined) return false;
        return String(v).toLowerCase().includes(term.toLowerCase());
      }))
    : lastRows;

  if (sortCol) {
    rows = [...rows].sort((a, b) => {
      const av = a[sortCol], bv = b[sortCol];
      if (av === null || av === undefined) return 1;
      if (bv === null || bv === undefined) return -1;
      const an = Number(av), bn = Number(bv);
      if (!isNaN(an) && !isNaN(bn)) return sortDir === 'asc' ? an - bn : bn - an;
      const as = String(av).toLowerCase(), bs = String(bv).toLowerCase();
      return sortDir === 'asc' ? as.localeCompare(bs) : bs.localeCompare(as);
    });
  }
  return rows;
}

function toggleSort(col) {
  if (sortCol === col) {
    if (sortDir === 'asc') { sortDir = 'desc'; }
    else { sortCol = null; sortDir = 'asc'; }
  } else {
    sortCol = col;
    sortDir = 'asc';
  }
  updateSortIndicators();
  applyTable();
}

function updateSortIndicators() {
  tableHead.querySelectorAll('th.sortable').forEach(th => {
    const col = th.dataset.col;
    const icon = th.querySelector('.sort-icon');
    if (col === sortCol) {
      icon.textContent = sortDir === 'asc' ? '↑' : '↓';
      th.classList.add('sorted');
    } else {
      icon.textContent = '';
      th.classList.remove('sorted');
    }
  });
}

function buildTableHeaders(cols) {
  const labelRow = document.createElement('tr');
  cols.forEach(col => {
    const th = document.createElement('th');
    th.className = 'sortable';
    th.dataset.col = col;
    th.innerHTML = `<span class="th-label" title="${esc(col)}">${esc(col)}</span><span class="sort-icon"></span>`;
    th.addEventListener('click', () => toggleSort(col));
    labelRow.appendChild(th);
  });

  const filterRow = document.createElement('tr');
  filterRow.className = 'filter-row';
  cols.forEach(col => {
    const th = document.createElement('th');
    const inp = document.createElement('input');
    inp.type = 'text';
    inp.className = 'col-filter';
    inp.placeholder = '…';
    inp.addEventListener('input', e => {
      filters[col] = e.target.value;
      mobilePage = 1;
      applyTable();
    });
    th.appendChild(inp);
    filterRow.appendChild(th);
  });

  tableHead.innerHTML = '';
  tableHead.appendChild(labelRow);
  tableHead.appendChild(filterRow);
  tableHead.classList.toggle('filters-hidden', isMobile());
}

function buildIsNum(cols, rows) {
  const isNum = {};
  cols.forEach(c => {
    const sample = rows.find(r => r[c] !== null && r[c] !== undefined);
    isNum[c] = sample ? isNumericVal(sample[c]) : false;
  });
  return isNum;
}

function renderRowsToBody(rows) {
  const isNum = buildIsNum(lastCols, lastRows);
  tableBody.innerHTML = rows.map(row =>
    '<tr>' + lastCols.map(c => {
      const raw = row[c];
      if (raw === null || raw === undefined)
        return '<td class="td-null" title="NULL">null</td>';
      if (typeof raw === 'boolean') {
        const label = raw ? 'true' : 'false';
        return `<td class="td-bool"><span class="bool-${label}">${label}</span></td>`;
      }
      if (typeof raw === 'object') {
        const s = JSON.stringify(raw);
        return `<td title="${esc(s)}">${esc(s)}</td>`;
      }
      const s = String(raw);
      if (isNum[c]) return `<td class="td-num" title="${esc(s)}">${esc(s)}</td>`;
      return `<td title="${esc(s)}">${esc(s)}</td>`;
    }).join('') + '</tr>'
  ).join('');
}

function applyTable() {
  const rows = getSortedFiltered();
  const total = lastRows.length;

  if (isMobile()) {
    const totalPages = Math.max(1, Math.ceil(rows.length / MOBILE_PAGE_SIZE));
    if (mobilePage > totalPages) mobilePage = totalPages;
    if (mobilePage < 1) mobilePage = 1;
    const start = (mobilePage - 1) * MOBILE_PAGE_SIZE;
    renderRowsToBody(rows.slice(start, start + MOBILE_PAGE_SIZE));
    renderMobilePagination(totalPages, rows.length);
  } else {
    renderRowsToBody(rows);
    mobilePagination.classList.add('hidden');
  }

  const shown = rows.length;
  rowCountLabel.textContent = shown < total
    ? `${shown.toLocaleString()} of ${total.toLocaleString()} rows`
    : `${total.toLocaleString()} row${total !== 1 ? 's' : ''} returned`;
}

// ── Mobile pagination ────────────────────────────────────────────────────────
function renderMobilePagination(totalPages, filteredCount) {
  if (currentView !== 'table' || totalPages <= 1) {
    mobilePagination.classList.add('hidden');
    mobilePagination.innerHTML = '';
    return;
  }
  mobilePagination.classList.remove('hidden');

  const pages = new Set([1, totalPages, mobilePage - 1, mobilePage, mobilePage + 1]);
  const sorted = [...pages].filter(p => p >= 1 && p <= totalPages).sort((a, b) => a - b);

  let html = `<button class="page-btn" id="pagePrev" ${mobilePage === 1 ? 'disabled' : ''}>‹ Prev</button>`;
  let prev = 0;
  sorted.forEach(p => {
    if (p - prev > 1) html += `<span class="page-ellipsis">…</span>`;
    html += `<button class="page-btn ${p === mobilePage ? 'active' : ''}" data-page="${p}">${p}</button>`;
    prev = p;
  });
  html += `<button class="page-btn" id="pageNext" ${mobilePage === totalPages ? 'disabled' : ''}>Next ›</button>`;

  mobilePagination.innerHTML = html;

  mobilePagination.querySelectorAll('[data-page]').forEach(btn => {
    btn.addEventListener('click', () => {
      mobilePage = parseInt(btn.dataset.page, 10);
      applyTable();
      tableScroll.scrollTo({ top: 0, behavior: 'smooth' });
    });
  });
  const prevBtn = document.getElementById('pagePrev');
  const nextBtn = document.getElementById('pageNext');
  if (prevBtn) prevBtn.addEventListener('click', () => {
    if (mobilePage > 1) { mobilePage--; applyTable(); tableScroll.scrollTo({ top: 0, behavior: 'smooth' }); }
  });
  if (nextBtn) nextBtn.addEventListener('click', () => {
    if (mobilePage < totalPages) { mobilePage++; applyTable(); tableScroll.scrollTo({ top: 0, behavior: 'smooth' }); }
  });
}

// ── Render (called once per new query result) ─────────────────────────────────

function renderTable(cols, rows, count) {
  lastCols = cols;
  lastRows = rows;
  sortCol  = null;
  sortDir  = 'asc';
  filters  = {};
  mobilePage = 1;

  buildTableHeaders(cols);
  applyTable();
  destroyChart();
  setView('table');
  showPanel(resultsState);
}

// ── Copy SQL ──────────────────────────────────────────────────────────────────
const _copyIcon = copyBtn.innerHTML;
const _checkIcon = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;

function _flashCopyBtn(ok) {
  copyBtn.innerHTML = ok ? _checkIcon : '✕';
  copyBtn.style.color = ok ? 'var(--accent, #4ade80)' : '#f87171';
  setTimeout(() => { copyBtn.innerHTML = _copyIcon; copyBtn.style.color = ''; }, 1600);
}

copyBtn.addEventListener('click', () => {
  if (!rawSQL) return;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(rawSQL)
      .then(() => _flashCopyBtn(true))
      .catch(() => {
        const ok = _execCommandCopy(rawSQL);
        _flashCopyBtn(ok);
      });
  } else {
    const ok = _execCommandCopy(rawSQL);
    _flashCopyBtn(ok);
  }
});

function _execCommandCopy(text) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.cssText = 'position:fixed;opacity:0;pointer-events:none';
  document.body.appendChild(ta);
  ta.select();
  const ok = document.execCommand('copy');
  document.body.removeChild(ta);
  return ok;
}

// ── Export helpers ────────────────────────────────────────────────────────────

function exportFilename(ext) {
  const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
  return `query-results-${ts}.${ext}`;
}

function exportCSV() {
  const rows = getSortedFiltered();
  if (!rows.length) return;

  const escape = v => {
    if (v === null || v === undefined) return '';
    const s = typeof v === 'object' ? JSON.stringify(v) : String(v);
    return s.includes(',') || s.includes('"') || s.includes('\n')
      ? `"${s.replace(/"/g, '""')}"` : s;
  };

  const header = lastCols.map(escape).join(',');
  const body   = rows.map(row => lastCols.map(c => escape(row[c])).join(','));
  const csv    = [header, ...body].join('\r\n');

  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);
  const a    = Object.assign(document.createElement('a'), { href: url, download: exportFilename('csv') });
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function exportExcel() {
  const rows = getSortedFiltered();
  if (!rows.length || typeof XLSX === 'undefined') return;

  const data = [lastCols, ...rows.map(row => lastCols.map(c => {
    const v = row[c];
    return (v === null || v === undefined) ? '' : (typeof v === 'object' ? JSON.stringify(v) : v);
  }))];

  const ws = XLSX.utils.aoa_to_sheet(data);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Results');
  XLSX.writeFile(wb, exportFilename('xlsx'));
}

// ── Mobile header actions: download menu + share + filter toggle ───────────

mobileDownloadBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  downloadMenu.classList.toggle('hidden');
});
downloadCsvOpt.addEventListener('click', () => { exportCSV(); downloadMenu.classList.add('hidden'); });
downloadXlsxOpt.addEventListener('click', () => { exportExcel(); downloadMenu.classList.add('hidden'); });
document.addEventListener('click', (e) => {
  if (!downloadMenu.classList.contains('hidden') && !downloadMenu.contains(e.target) && e.target !== mobileDownloadBtn) {
    downloadMenu.classList.add('hidden');
  }
});

mobileFilterBtn.addEventListener('click', () => {
  tableHead.classList.toggle('filters-hidden');
});

mobileShareBtn.addEventListener('click', async () => {
  const shareText = `${mobileQuestionEcho.textContent}\n\n${rawSQL}`;
  if (navigator.share) {
    try {
      await navigator.share({ title: 'Fetcher.io Query', text: shareText, url: location.href });
    } catch {
      /* user cancelled — no-op */
    }
    return;
  }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    await navigator.clipboard.writeText(shareText);
    showToast('Copied query + SQL to clipboard');
  } else {
    showToast('Sharing not supported on this browser');
  }
});

// ── Chart ─────────────────────────────────────────────────────────────────────

const CHART_PALETTE = [
  '#6366f1', '#34d399', '#fb923c', '#f87171', '#a5b4fc',
  '#818cf8', '#facc15', '#22d3ee', '#f472b6', '#4ade80',
];

const chartBgPlugin = {
  id: 'solidBg',
  beforeDraw(chart) {
    const { ctx, width, height } = chart;
    ctx.save();
    ctx.globalCompositeOperation = 'destination-over';
    ctx.fillStyle = '#12131b';
    ctx.fillRect(0, 0, width, height);
    ctx.restore();
  },
};

function getChartSpec() {
  if (lastCols.length !== 2) {
    return {
      ok: false,
      reason:
        `Graph not possible — it needs exactly 2 columns, but this result has ${lastCols.length}. ` +
        `Ask for just a label and a number (e.g. "product name and total sales").`,
    };
  }
  const isNum = buildIsNum(lastCols, lastRows);
  const [c0, c1] = lastCols;
  if (isNum[c1])      return { ok: true, labelCol: c0, valueCol: c1 };
  if (isNum[c0])      return { ok: true, labelCol: c1, valueCol: c0 };
  return {
    ok: false,
    reason: 'Graph not possible — neither column is numeric, so there is nothing to plot.',
  };
}

function destroyChart() {
  if (chartInstance) { chartInstance.destroy(); chartInstance = null; }
}

function renderChart() {
  destroyChart();
  const spec = getChartSpec();

  if (!spec.ok) {
    chartNotPossible.textContent = spec.reason;
    chartNotPossible.classList.remove('hidden');
    chartCanvasWrap.classList.add('hidden');
    exportPngBtn.classList.add('hidden');
    return;
  }
  chartNotPossible.classList.add('hidden');
  chartCanvasWrap.classList.remove('hidden');
  exportPngBtn.classList.remove('hidden');

  const rows = getSortedFiltered();
  const labels = rows.map(r => {
    const v = r[spec.labelCol];
    return (v === null || v === undefined) ? '∅' : String(v);
  });
  const values = rows.map(r => {
    const v = r[spec.valueCol];
    return (v === null || v === undefined || v === '') ? null : Number(v);
  });

  const type = chartTypeSelect.value || 'bar';
  const isPie = type === 'pie';
  const tick = '#525878';
  const grid = 'rgba(42,45,74,0.5)';

  chartInstance = new Chart(chartCanvas, {
    type,
    data: {
      labels,
      datasets: [{
        label: spec.valueCol,
        data: values,
        backgroundColor: isPie
          ? values.map((_, i) => CHART_PALETTE[i % CHART_PALETTE.length])
          : 'rgba(99,102,241,0.65)',
        borderColor: isPie ? '#12131b' : '#6366f1',
        borderWidth: isPie ? 2 : 1.5,
        fill: type === 'line' ? false : true,
        tension: 0.25,
        pointRadius: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 250 },
      plugins: {
        legend: { display: isPie, position: 'right', labels: { color: '#dde1f0', font: { size: 11 } } },
        title: { display: true, text: `${spec.valueCol} by ${spec.labelCol}`, color: '#dde1f0', font: { size: 13, weight: '500' } },
      },
      scales: isPie ? {} : {
        x: { ticks: { color: tick, maxRotation: 60, font: { size: 10 } }, grid: { color: grid } },
        y: { ticks: { color: tick, font: { size: 10 } }, grid: { color: grid }, beginAtZero: true },
      },
    },
    plugins: [chartBgPlugin],
  });
}

// ── JSON view ─────────────────────────────────────────────────────────────────
function renderJson() {
  jsonDisplay.textContent = JSON.stringify(getSortedFiltered(), null, 2);
}

function setView(view) {
  currentView = view;
  viewTableBtn.classList.toggle('active', view === 'table');
  viewChartBtn.classList.toggle('active', view === 'chart');
  viewJsonBtn.classList.toggle('active', view === 'json');

  tableScroll.classList.toggle('hidden', view !== 'table');
  chartContainer.classList.toggle('hidden', view !== 'chart');
  jsonContainer.classList.toggle('hidden', view !== 'json');
  chartTypeSelect.classList.toggle('hidden', view !== 'chart');

  if (view === 'chart') {
    renderChart();
  } else {
    exportPngBtn.classList.add('hidden');
  }
  if (view === 'json') renderJson();

  if (view === 'table' && isMobile()) {
    applyTable();
  } else {
    mobilePagination.classList.add('hidden');
  }
}

function exportPNG() {
  if (!chartInstance) return;
  const url = chartInstance.toBase64Image('image/png', 1);
  const a = Object.assign(document.createElement('a'), { href: url, download: exportFilename('png') });
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

// ── Event listeners ───────────────────────────────────────────────────────────
runBtn.addEventListener('click', runQuery);

questionEl.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault();
    runQuery();
  }
});

exportCsvBtn.addEventListener('click', exportCSV);
exportXlsxBtn.addEventListener('click', exportExcel);

viewTableBtn.addEventListener('click', () => setView('table'));
viewChartBtn.addEventListener('click', () => setView('chart'));
viewJsonBtn.addEventListener('click', () => setView('json'));
chartTypeSelect.addEventListener('change', () => { if (currentView === 'chart') renderChart(); });
exportPngBtn.addEventListener('click', exportPNG);

window.addEventListener('resize', () => {
  if (resultsState.classList.contains('hidden')) return;
  if (currentView === 'table') applyTable();
});

// ── Boot ─────────────────────────────────────────────────────────────────────
renderStats();
renderRecentQueries();

// Auto-focus on load (desktop only — avoids popping the mobile keyboard on load)
if (!isMobile()) questionEl.focus();
