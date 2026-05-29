'use strict';

/* ── Constants ─────────────────────────────────── */
const THEME_META = {
  renewable_opportunity: { label: '재생에너지',   color: '#12805c', cls: 'score-renewable' },
  fossil_pressure:       { label: '화석연료 압력', color: '#a15c10', cls: 'score-fossil'    },
  grid_infrastructure:   { label: '전력망/전기화', color: '#2563eb', cls: 'score-grid'      },
  climate_risk:          { label: '기후 리스크',   color: '#b42318', cls: 'score-climate'   },
};
const MARKET_LABELS = { ET_SPREAD: 'ET Spread', ICLN: 'ICLN', XLE: 'XLE', NEE: 'NEE', XOM: 'XOM', ETN: 'ETN' };
const THEME_LABELS = Object.fromEntries(Object.entries(THEME_META).map(([key, meta]) => [key, meta.label]));

/* ── State ─────────────────────────────────────── */
let scoreChart = null;
let returnsChart = null;
let dashboardReturnsChart = null;
let lastResult = null;

/* ── Tab Switching ─────────────────────────────── */
function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.dataset.tab;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b === btn));
      document.querySelectorAll('.tab-section').forEach(s => {
        s.classList.toggle('active', s.id === `tab-${id}`);
        s.classList.toggle('hidden', s.id !== `tab-${id}`);
      });
      if (id === 'dashboard') loadDashboard();
    });
  });
}

/* ── Dropzone & File Selection ─────────────────── */
function initUpload() {
  const dropzone  = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const fileName  = document.getElementById('file-name');
  const btnAnalyze = document.getElementById('btn-analyze');

  dropzone.addEventListener('click', () => fileInput.click());
  dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('dragover'); });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
  dropzone.addEventListener('drop', e => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    const f = e.dataTransfer.files[0];
    if (f && f.name.endsWith('.pdf')) setFile(f);
  });
  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) setFile(fileInput.files[0]);
  });

  function setFile(f) {
    fileInput._selectedFile = f;
    fileName.textContent = f.name;
    btnAnalyze.disabled = false;
  }
}

/* ── Range Slider Labels ───────────────────────── */
function initSliders() {
  document.getElementById('inp-pages').addEventListener('input', e => {
    document.getElementById('pages-val').textContent = e.target.value;
  });
  document.getElementById('inp-topk').addEventListener('input', e => {
    document.getElementById('topk-val').textContent = e.target.value;
  });
}

/* ── Analyze Form Submit ───────────────────────── */
function initForm() {
  document.getElementById('btn-analyze').addEventListener('click', async () => {
    const fileInput = document.getElementById('file-input');
    const file = fileInput._selectedFile;
    if (!file) return;

    const horizons = [...document.querySelectorAll('.checkbox-group input:checked')]
      .map(cb => cb.value).join(',');

    const fd = new FormData();
    fd.append('file',        file);
    fd.append('title',       document.getElementById('inp-title').value);
    fd.append('issuer',      document.getElementById('inp-issuer').value);
    fd.append('report_date', document.getElementById('inp-date').value);
    fd.append('max_pages',   document.getElementById('inp-pages').value);
    fd.append('top_k',       document.getElementById('inp-topk').value);
    fd.append('horizons',    horizons || '4');

    setAnalyzeState('loading');

    try {
      const res = await fetch('/api/analyze', { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '분석 실패');
      lastResult = data;
      renderResults(data);
      setAnalyzeState('done');
    } catch (err) {
      showError(err.message);
      setAnalyzeState('idle');
    }
  });
}

function setAnalyzeState(state) {
  const btnText    = document.getElementById('btn-text');
  const btnSpinner = document.getElementById('btn-spinner');
  const btnAnalyze = document.getElementById('btn-analyze');

  if (state === 'loading') {
    btnText.textContent = '분석 중…';
    btnSpinner.classList.remove('hidden');
    btnAnalyze.disabled = true;
    showPanel('loading');
  } else if (state === 'done') {
    btnText.textContent = 'PDF 분석 실행';
    btnSpinner.classList.add('hidden');
    btnAnalyze.disabled = false;
  } else {
    btnText.textContent = 'PDF 분석 실행';
    btnSpinner.classList.add('hidden');
    btnAnalyze.disabled = false;
  }
}

function showPanel(which) {
  ['result-empty','result-loading','result-content','result-error'].forEach(id => {
    document.getElementById(id).classList.toggle('hidden', id !== `result-${which}`);
  });
}

function showError(msg) {
  document.getElementById('error-msg').textContent = msg;
  showPanel('error');
}

/* ── Render All Results ────────────────────────── */
function renderResults(data) {
  renderScoreCards(data.scores);
  renderChart(data.scores);
  renderConfidence(data.scores, data.confidence);
  renderSummary(data.summary);
  renderEvidence(data.evidence, parseInt(document.getElementById('inp-topk').value));
  renderReturns(data.returns);
  renderStats(data.stats);
  setupDownloads(data);
  showPanel('content');
}

/* ── Score Cards ───────────────────────────────── */
function renderScoreCards(scores) {
  const container = document.getElementById('score-cards');
  const items = [
    ...Object.entries(THEME_META).map(([k, m]) => ({ key: k, label: m.label, cls: m.cls, value: scores[k] })),
    { key: 'transition_signal', label: '전환 신호', cls: 'score-signal', value: scores.transition_signal, raw: true },
  ];
  container.innerHTML = items.map(({ label, cls, value, raw }) => {
    const pct = raw ? Math.abs(value / 2) * 100 : value * 100;
    return `
      <div class="score-card ${cls}">
        <span class="sc-label">${label}</span>
        <span class="sc-value">${value.toFixed(3)}</span>
        <div class="sc-bar"><div class="sc-bar-fill" style="width:${Math.min(pct,100).toFixed(1)}%"></div></div>
      </div>`;
  }).join('');
}

/* ── Chart.js Bar Chart ────────────────────────── */
function renderChart(scores) {
  const canvas = document.getElementById('score-chart');
  if (scoreChart) scoreChart.destroy();
  scoreChart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: Object.values(THEME_META).map(m => m.label),
      datasets: [{
        data: Object.keys(THEME_META).map(k => scores[k]),
        backgroundColor: Object.values(THEME_META).map(m => m.color + 'cc'),
        borderColor:     Object.values(THEME_META).map(m => m.color),
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: { legend: { display: false } },
      scales: {
        y: {
          min: 0, max: 1,
          grid: { color: '#e4eaf0' },
          ticks: { color: '#667085', font: { size: 11 } },
        },
        x: {
          grid: { display: false },
          ticks: { color: '#667085', font: { size: 11 } },
        },
      },
    },
  });
}

/* ── Confidence Box ────────────────────────────── */
function renderConfidence(scores, conf) {
  const box = document.getElementById('confidence-box');
  const hint = scores.asset_hint;
  const topThemeLabel = THEME_LABELS[conf.top_theme] || conf.top_theme;
  const confColor = { '높음': '#10b981', '보통': '#f59e0b', '낮음': '#ef4444' }[conf.level] || '#94a3b8';
  box.innerHTML = `
    가장 강한 자산 힌트: <strong>${hint}</strong> &nbsp;|&nbsp;
    1등 주제: <strong>${topThemeLabel}</strong> &nbsp;|&nbsp;
    모델 확신도: <strong style="color:${confColor}">${conf.level}</strong>
    (점수 차이 ${conf.margin.toFixed(3)})
    &nbsp;— 투자 추천이 아닌 의미 분류 결과입니다.`;
}

/* ── Summary Box ───────────────────────────────── */
function renderSummary(summary) {
  const box = document.getElementById('summary-box');
  const bullets = summary.bullets.split(' | ').map(b => `<li>${b}</li>`).join('');
  box.innerHTML = `
    <p>${summary.korean}</p>
    <ul class="summary-bullets">${bullets}</ul>`;
}

/* ── Evidence Tabs ─────────────────────────────── */
function renderEvidence(evidence, topK) {
  const tabsEl    = document.getElementById('evidence-tabs');
  const contentEl = document.getElementById('evidence-content');
  const keys      = Object.keys(THEME_META);

  tabsEl.innerHTML = keys.map((k, i) =>
    `<button class="ev-tab ${i === 0 ? 'active' : ''}" data-key="${k}">${THEME_META[k].label}</button>`
  ).join('');

  contentEl.innerHTML = keys.map((k, i) => {
    const items = (evidence[k] || []).slice(0, topK);
    const rows  = items.map(item => `
      <div class="ev-item">
        <div class="ev-meta">
          <span>페이지 ${item.page}</span>
          <span>순위 #${item.rank}</span>
          <span class="ev-score">관련도 ${item.score.toFixed(3)}</span>
        </div>
        <div class="ev-text">${highlightKeywords(item.paragraph)}</div>
      </div>`).join('');
    return `<div class="ev-list ${i === 0 ? 'active' : ''}" data-key="${k}">${rows || '<p style="color:var(--text-muted);font-size:.82rem">문단 없음</p>'}</div>`;
  }).join('');

  tabsEl.addEventListener('click', e => {
    const btn = e.target.closest('.ev-tab');
    if (!btn) return;
    tabsEl.querySelectorAll('.ev-tab').forEach(b => b.classList.toggle('active', b === btn));
    contentEl.querySelectorAll('.ev-list').forEach(l => l.classList.toggle('active', l.dataset.key === btn.dataset.key));
  });
}

/* ── Returns Table ─────────────────────────────── */
function renderReturns(returns) {
  const box = document.getElementById('returns-box');
  if (!returns || Object.keys(returns).length === 0) {
    box.innerHTML = '<p class="note">주가 데이터 범위 밖이거나 데이터가 부족해 수익률을 계산하지 못했습니다.</p>';
    return;
  }

  const preKeys = Object.keys(returns).filter(k => k.startsWith('pre_4w_'));
  const fwdGroups = {};
  Object.keys(returns).filter(k => k.startsWith('forward_')).forEach(k => {
    const [, w, col] = k.match(/^forward_(\d+)w_(.+)$/) || [];
    if (w && col) { (fwdGroups[w] = fwdGroups[w] || {})[col] = returns[k]; }
  });

  const cols = Object.keys(MARKET_LABELS);
  const periods = [];
  if (preKeys.length) {
    periods.push({ label: '이전 4주', prefix: 'pre_4w_' });
  }
  Object.keys(fwdGroups).sort((a, b) => +a - +b).forEach(w => {
    periods.push({ label: `이후 ${w}주`, group: fwdGroups[w] });
  });

  const graphCols = ['ET_SPREAD', 'ICLN', 'XLE', 'ETN'];
  const chartId = `returns-chart-${Date.now()}`;
  let html = `<div class="chart-wrap returns-chart-wrap"><canvas id="${chartId}" height="170"></canvas></div>`;

  const fmtCell = v => {
    if (v === undefined || v === null) return '<td>—</td>';
    const cls = v > 0.005 ? 'pos' : v < -0.005 ? 'neg' : '';
    const sign = v > 0 ? '+' : '';
    return `<td class="${cls}">${sign}${(v * 100).toFixed(2)}%</td>`;
  };

  html += `<div class="table-wrap"><table class="data-table">
    <thead><tr><th>기간</th>${cols.map(c => `<th>${MARKET_LABELS[c]}</th>`).join('')}</tr></thead><tbody>`;

  if (preKeys.length) {
    html += `<tr><td>이전 4주</td>${cols.map(c => fmtCell(returns[`pre_4w_${c}`])).join('')}</tr>`;
  }
  Object.keys(fwdGroups).sort((a, b) => +a - +b).forEach(w => {
    html += `<tr><td>이후 ${w}주</td>${cols.map(c => fmtCell(fwdGroups[w][c])).join('')}</tr>`;
  });

  html += '</tbody></table></div>';
  box.innerHTML = html;

  const chartData = periods.map(period => {
    if (period.prefix) {
      return graphCols.map(col => returns[`${period.prefix}${col}`] ?? null);
    }
    return graphCols.map(col => period.group[col] ?? null);
  });
  renderReturnsChart(chartId, periods.map(p => p.label), graphCols, chartData, false);
}

function renderReturnsChart(canvasId, labels, columns, valuesByPeriod, dashboardMode) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const palette = {
    ET_SPREAD: '#126c6a',
    ICLN: '#12805c',
    XLE: '#a15c10',
    ETN: '#2563eb',
    NEE: '#475467',
    XOM: '#b42318',
  };
  const datasets = columns.map((col, idx) => ({
    label: MARKET_LABELS[col] || col,
    data: valuesByPeriod.map(row => row[idx] === null ? null : row[idx] * 100),
    backgroundColor: (palette[col] || '#667085') + 'cc',
    borderColor: palette[col] || '#667085',
    borderWidth: 1,
    borderRadius: 4,
  }));

  if (dashboardMode && dashboardReturnsChart) dashboardReturnsChart.destroy();
  if (!dashboardMode && returnsChart) returnsChart.destroy();

  const chart = new Chart(canvas, {
    type: 'bar',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { color: '#667085', boxWidth: 14 } },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y > 0 ? '+' : ''}${ctx.parsed.y.toFixed(2)}%`,
          },
        },
      },
      scales: {
        y: {
          grid: { color: '#e4eaf0' },
          ticks: { color: '#667085', callback: value => `${value}%` },
        },
        x: {
          grid: { display: false },
          ticks: { color: '#667085' },
        },
      },
    },
  });

  if (dashboardMode) dashboardReturnsChart = chart;
  else returnsChart = chart;
}

/* ── Stats Row ─────────────────────────────────── */
function renderStats(stats) {
  const row = document.getElementById('stats-row');
  row.innerHTML = [
    `추출 페이지: <strong>${stats.pages}</strong>`,
    `분석 문단: <strong>${stats.paragraphs}</strong>`,
    `근거 문단: <strong>${stats.evidence_count}</strong>`,
  ].map(s => `<span class="stat-item">${s}</span>`).join('');
}

/* ── CSV Download ──────────────────────────────── */
function setupDownloads(data) {
  document.getElementById('btn-dl-scores').onclick = () => {
    const s = data.scores;
    const conf = data.confidence;
    const rows = [
      ['renewable_opportunity','fossil_pressure','grid_infrastructure','climate_risk','transition_signal','asset_hint','confidence_level','confidence_margin'],
      [s.renewable_opportunity, s.fossil_pressure, s.grid_infrastructure, s.climate_risk, s.transition_signal, s.asset_hint, conf.level, conf.margin],
    ];
    downloadCSV(rows, 'pdf_signal_scores.csv');
  };

  document.getElementById('btn-dl-evidence').onclick = () => {
    const header = ['theme','page','rank','retrieval_score','paragraph','korean_interpretation'];
    const rows = [header];
    Object.entries(data.evidence).forEach(([theme, items]) => {
      items.forEach(item => rows.push([theme, item.page, item.rank, item.score, item.paragraph, item.interpretation || '']));
    });
    downloadCSV(rows, 'pdf_signal_evidence.csv');
  };
}

function downloadCSV(rows, filename) {
  const escapeCsv = value => {
    const s = String(value ?? '');
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const content = rows.map(r => r.map(escapeCsv).join(',')).join('\n');
  const blob = new Blob(['﻿' + content], { type: 'text/csv;charset=utf-8;' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

/* ── Dashboard ─────────────────────────────────── */
let dashboardLoaded = false;
async function loadDashboard() {
  if (dashboardLoaded) return;
  dashboardLoaded = true;

  try {
    const res = await fetch('/api/dashboard');
    const data = await res.json();
    renderSignalsTable(data.signals);
    renderLinkTable(data.stock_link);
  } catch (e) {
    document.getElementById('signals-table-wrap').innerHTML = '<p class="note">데이터 로드 실패</p>';
  }
}

function renderSignalsTable(signals) {
  const wrap = document.getElementById('signals-table-wrap');
  if (!signals || !signals.length) { wrap.innerHTML = '<p class="note">데이터 없음</p>'; return; }

  const cols = ['title','date','renewable_opportunity','fossil_pressure','grid_infrastructure','climate_risk','transition_signal','asset_hint'];
  const headers = { title:'보고서', date:'날짜', renewable_opportunity:'재생에너지', fossil_pressure:'화석연료 압력', grid_infrastructure:'전력망', climate_risk:'기후 리스크', transition_signal:'전환 신호', asset_hint:'자산 힌트' };

  wrap.innerHTML = `<table class="data-table">
    <thead><tr>${cols.map(c => `<th>${headers[c]}</th>`).join('')}</tr></thead>
    <tbody>${signals.map(row => `<tr>${cols.map(c => {
      const v = row[c];
      if (typeof v === 'number') {
        const cls = c === 'transition_signal' ? (v > 0 ? 'pos' : 'neg') : '';
        return `<td class="${cls}">${v.toFixed(3)}</td>`;
      }
      return `<td>${escapeHtml(String(v ?? ''))}</td>`;
    }).join('')}</tr>`).join('')}</tbody>
  </table>`;
}

function renderLinkTable(link) {
  const wrap = document.getElementById('link-table-wrap');
  if (!link || !link.length) { wrap.innerHTML = '<p class="note">데이터 없음</p>'; return; }

  const cols = Object.keys(link[0]);
  const graphCols = ['forward_4w_ET_SPREAD', 'forward_4w_ICLN', 'forward_4w_XLE', 'forward_4w_ETN'];
  const labels = link.map(row => shortenTitle(row.title || row.report_id || 'Report'));
  const valuesByPeriod = link.map(row => graphCols.map(col => row[col] ?? null));
  wrap.innerHTML = `
  <div class="chart-wrap returns-chart-wrap dashboard-return-chart">
    <canvas id="dashboard-returns-chart" height="210"></canvas>
  </div>
  <table class="data-table">
    <thead><tr>${cols.map(c => `<th>${c}</th>`).join('')}</tr></thead>
    <tbody>${link.map(row => `<tr>${cols.map(c => {
      const v = row[c];
      if (typeof v === 'number' && c !== 'transition_signal') {
        const cls = v > 0.005 ? 'pos' : v < -0.005 ? 'neg' : '';
        return `<td class="${cls}">${v > 0 ? '+' : ''}${(v * 100).toFixed(2)}%</td>`;
      }
      if (typeof v === 'number') return `<td>${v.toFixed(3)}</td>`;
      return `<td>${escapeHtml(String(v ?? ''))}</td>`;
    }).join('')}</tr>`).join('')}</tbody>
  </table>`;
  renderReturnsChart('dashboard-returns-chart', labels, ['ET_SPREAD', 'ICLN', 'XLE', 'ETN'], valuesByPeriod, true);
}

/* ── Utility ───────────────────────────────────── */
function escapeHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function highlightKeywords(str) {
  const keywords = [
    'renewable', 'solar', 'wind', 'clean energy', 'capacity',
    'oil', 'gas', 'fossil', 'methane', 'carbon', 'emissions',
    'grid', 'transmission', 'distribution', 'electricity', 'electrification', 'power',
    'climate', 'weather', 'heat', 'drought', 'risk', 'resilience',
    'investment', 'demand', 'policy', 'regulation', 'cost',
  ];
  let escaped = escapeHtml(str);
  const pattern = new RegExp(`\\b(${keywords.map(escapeRegExp).join('|')})\\b`, 'gi');
  return escaped.replace(pattern, '<strong class="keyword-highlight">$1</strong>');
}

function escapeRegExp(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function shortenTitle(title) {
  return title
    .replace('ExxonMobil Advancing Climate Solutions 2023', 'Exxon ACS')
    .replace('IEA World Energy Outlook 2023', 'IEA WEO')
    .replace('IEA Oil and Gas Industry in Net Zero Transitions', 'IEA Oil/Gas NZ')
    .replace('IEA Renewables 2023', 'IEA Renewables')
    .replace('Eaton Annual Report 2023', 'Eaton Annual');
}

/* ── Init ──────────────────────────────────────── */
initTabs();
initUpload();
initSliders();
initForm();
