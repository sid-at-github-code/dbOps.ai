'use strict';

// ── DOM refs ──────────────────────────────────────────────────────────────────
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
const chartTypeSelect = document.getElementById('chartTypeSelect');
const exportPngBtn    = document.getElementById('exportPngBtn');
const tableScroll     = document.getElementById('tableScroll');
const chartContainer  = document.getElementById('chartContainer');
const chartNotPossible= document.getElementById('chartNotPossible');
const chartCanvasWrap = document.getElementById('chartCanvasWrap');
const chartCanvas     = document.getElementById('chartCanvas');

// ── State ─────────────────────────────────────────────────────────────────────
let rawSQL      = '';
let lastCols    = [];
let lastRows    = [];
let sortCol     = null;
let sortDir     = 'asc';   // 'asc' | 'desc'
let filters     = {};
let currentView = 'table'; // 'table' | 'chart'
let chartInstance = null;

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
  // Escape HTML first, then wrap tokens (order matters: strings > fns > kw)
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

// Returns true if the question already contains an explicit row/record count so
// we don't append a redundant LIMIT instruction from the UI field.
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

  setLoading(true);
  loadingMsg.textContent = 'Generating SQL…';

  // Reset left panel
  sqlSection.classList.add('hidden');
  metaSection.classList.add('hidden');

  // After a short delay, update loading message to indicate DB phase
  const phaseTimer = setTimeout(() => {
    loadingMsg.textContent = 'Executing query…';
  }, 2500);

  try {
    const rowLimitRaw = rowLimitEl.value.trim();
    const rowLimit = rowLimitRaw !== '' ? parseInt(rowLimitRaw, 10) : 10;
    const questionWithLimit = questionMentionsRowCount(question)
      ? question
      : `${question}\nReturn at most ${rowLimit} rows.`;

    const resp = await fetch('/api/query', {
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

function handleResult(data) {
  // ── Left panel ──────────────────────────────────────────────────────────────
  if (data.sql) {
    rawSQL = data.sql;
    sqlDisplay.innerHTML = highlightSQL(data.sql);
    sqlSection.classList.remove('hidden');
  }

  // Validation badge
  if (data.validated) {
    validationBadge.className = 'badge ok';
    validationBadge.innerHTML = '&#10003;&nbsp; Validated &mdash; read only';
  } else if (data.sql) {
    validationBadge.className = 'badge err';
    validationBadge.innerHTML = '&#10005;&nbsp; Blocked';
  } else {
    validationBadge.className = 'badge';
    validationBadge.textContent = '';
  }

  // Timings
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

  // ── Right panel ─────────────────────────────────────────────────────────────
  if (data.error) {
    errorMsg.textContent = data.error;
    showPanel(errorState);
    return;
  }

  if (!data.rows || data.row_count === 0) {
    errorMsg.textContent = 'Query returned 0 rows.';
    errorMsg.className = 'state-msg';   // no red — not really an error
    showPanel(errorState);
    return;
  }

  renderTable(data.columns, data.rows, data.row_count);
}

// ── Sort / filter helpers ─────────────────────────────────────────────────────

function getSortedFiltered() {
  // Filter
  const active = Object.entries(filters).filter(([, v]) => v.trim());
  let rows = active.length
    ? lastRows.filter(row => active.every(([col, term]) => {
        const v = row[col];
        if (v === null || v === undefined) return false;
        return String(v).toLowerCase().includes(term.toLowerCase());
      }))
    : lastRows;

  // Sort
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
  // Row 1 — sortable column labels
  const labelRow = document.createElement('tr');
  cols.forEach(col => {
    const th = document.createElement('th');
    th.className = 'sortable';
    th.dataset.col = col;
    th.innerHTML = `<span class="th-label" title="${esc(col)}">${esc(col)}</span><span class="sort-icon"></span>`;
    th.addEventListener('click', () => toggleSort(col));
    labelRow.appendChild(th);
  });

  // Row 2 — filter inputs
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
      applyTable();
    });
    th.appendChild(inp);
    filterRow.appendChild(th);
  });

  tableHead.innerHTML = '';
  tableHead.appendChild(labelRow);
  tableHead.appendChild(filterRow);
}

// Detect numeric columns once per dataset (based on first non-null value)
function buildIsNum(cols, rows) {
  const isNum = {};
  cols.forEach(c => {
    const sample = rows.find(r => r[c] !== null && r[c] !== undefined);
    isNum[c] = sample ? isNumericVal(sample[c]) : false;
  });
  return isNum;
}

function applyTable() {
  const rows  = getSortedFiltered();
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

  const total = lastRows.length, shown = rows.length;
  rowCountLabel.textContent = shown < total
    ? `${shown.toLocaleString()} of ${total.toLocaleString()} rows`
    : `${total.toLocaleString()} row${total !== 1 ? 's' : ''} returned`;
}

// ── Render (called once per new query result) ─────────────────────────────────

function renderTable(cols, rows, count) {
  lastCols = cols;
  lastRows = rows;
  sortCol  = null;
  sortDir  = 'asc';
  filters  = {};

  buildTableHeaders(cols);
  applyTable();
  destroyChart();
  setView('table');   // every new result starts in table view
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

// ── Chart ─────────────────────────────────────────────────────────────────────

const CHART_PALETTE = [
  '#6366f1', '#34d399', '#fb923c', '#f87171', '#a5b4fc',
  '#818cf8', '#facc15', '#22d3ee', '#f472b6', '#4ade80',
];

// Paints a solid background behind the chart so exported PNGs aren't transparent.
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

// Decide whether the current result can be charted, and which column is which.
// Rule: exactly 2 columns, and at least one of them numeric (used as the value).
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

function setView(view) {
  currentView = view;
  const chart = view === 'chart';
  viewTableBtn.classList.toggle('active', !chart);
  viewChartBtn.classList.toggle('active', chart);
  tableScroll.classList.toggle('hidden', chart);
  chartContainer.classList.toggle('hidden', !chart);
  chartTypeSelect.classList.toggle('hidden', !chart);
  if (chart) {
    renderChart();
  } else {
    exportPngBtn.classList.add('hidden');
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
chartTypeSelect.addEventListener('change', () => { if (currentView === 'chart') renderChart(); });
exportPngBtn.addEventListener('click', exportPNG);

// Auto-focus on load
questionEl.focus();
