'use strict';

const THEME_META = {
  renewable_opportunity: { label: 'Renewables', color: '#1f7a5c', cls: 'score-renewable' },
  fossil_pressure: { label: 'Fossil pressure', color: '#9a5b18', cls: 'score-fossil' },
  grid_infrastructure: { label: 'Grid infrastructure', color: '#315f9f', cls: 'score-grid' },
  climate_risk: { label: 'Climate risk', color: '#a33b32', cls: 'score-climate' },
};

const MARKET_LABELS = {
  ET_SPREAD: 'ET Spread',
  ICLN: 'ICLN',
  XLE: 'XLE',
  NEE: 'NEE',
  XOM: 'XOM',
  ETN: 'ETN',
};

const SAMPLE_RESULT = {
  status: 'success',
  demo: true,
  scores: {
    renewable_opportunity: 1.0,
    fossil_pressure: 0.499,
    grid_infrastructure: 0.718,
    climate_risk: 0.0,
    transition_signal: 1.219,
    asset_hint: 'ICLN/NEE',
    energy_relevance: 0.94,
    ood_decision: 'in_domain',
    top_theme: 'renewable_opportunity',
    second_theme: 'grid_infrastructure',
    score_margin: 0.282,
    mixed_signal: true,
  },
  confidence: {
    level: 'High',
    margin: 0.282,
    top_theme: 'renewable_opportunity',
    second_theme: 'grid_infrastructure',
    mixed_signal: true,
    energy_relevance: 0.94,
    ood_decision: 'in_domain',
  },
  summary: {
    korean: 'Sample report preview: the retrieved evidence emphasizes renewable capacity growth, grid connection constraints, and investment needs. The signal is strongest for clean-energy opportunity with a secondary grid-infrastructure component. Market data below is a historical context window anchored to the report date, not a forecast.',
    bullets: 'Renewable capacity expansion is the dominant theme | Grid integration and transmission constraints appear as supporting evidence | Fossil exposure is present but secondary | Historical returns are shown only as downstream context',
    generative: {
      enabled: true,
      model: 'fallback-demo-summary',
      summary: 'Evidence chunks support a mixed renewable-and-grid transition signal. The market window illustrates how clean-energy and energy-sector assets moved after the report date, without implying prediction.',
    },
  },
  evidence: {
    renewable_opportunity: [
      { page: 12, rank: 1, score: 0.912, paragraph: 'Renewable electricity capacity additions are expected to accelerate, led by solar PV and wind projects across major markets.' },
      { page: 18, rank: 2, score: 0.874, paragraph: 'Clean energy investment remains central to meeting electricity demand while reducing emissions intensity.' },
      { page: 31, rank: 3, score: 0.831, paragraph: 'Policy support and lower technology costs improve the economics of renewable deployment.' },
    ],
    fossil_pressure: [
      { page: 44, rank: 1, score: 0.761, paragraph: 'Oil and gas producers face pressure to lower methane emissions and manage transition-related capital allocation.' },
      { page: 47, rank: 2, score: 0.692, paragraph: 'Fossil fuel demand remains material in the near term, but the transition changes long-run exposure.' },
    ],
    grid_infrastructure: [
      { page: 22, rank: 1, score: 0.887, paragraph: 'Transmission expansion and grid connection queues are critical constraints for renewable integration.' },
      { page: 26, rank: 2, score: 0.842, paragraph: 'Distribution networks require investment to support electrification, storage, and flexible demand.' },
    ],
    climate_risk: [
      { page: 55, rank: 1, score: 0.583, paragraph: 'Climate risk and extreme weather can affect asset reliability, demand patterns, and resilience planning.' },
    ],
  },
  returns: {
    report_date: '2024-01-11',
    pre_4w_ET_SPREAD: -0.012,
    pre_4w_ICLN: -0.034,
    pre_4w_XLE: 0.018,
    pre_4w_NEE: -0.026,
    pre_4w_XOM: 0.011,
    pre_4w_ETN: 0.041,
    forward_1w_ET_SPREAD: 0.028,
    forward_1w_ICLN: 0.013,
    forward_1w_XLE: -0.009,
    forward_1w_NEE: 0.021,
    forward_1w_XOM: -0.004,
    forward_1w_ETN: 0.036,
    forward_4w_ET_SPREAD: -0.044,
    forward_4w_ICLN: -0.055,
    forward_4w_XLE: -0.014,
    forward_4w_NEE: -0.063,
    forward_4w_XOM: -0.006,
    forward_4w_ETN: 0.150,
    forward_8w_ET_SPREAD: 0.032,
    forward_8w_ICLN: 0.018,
    forward_8w_XLE: 0.022,
    forward_8w_NEE: -0.011,
    forward_8w_XOM: 0.018,
    forward_8w_ETN: 0.191,
  },
  stats: { pages: 88, paragraphs: 412, evidence_count: 40 },
};

const FALLBACK_DASHBOARD = {
  signals: [
    { title: 'IEA Renewables 2023', date: '2024-01-11', renewable_opportunity: 1.0, fossil_pressure: 0.499, grid_infrastructure: 0.718, climate_risk: 0.0, transition_signal: 1.219, asset_hint: 'ICLN/NEE' },
    { title: 'IEA World Energy Outlook 2023', date: '2023-10-24', renewable_opportunity: 1.0, fossil_pressure: 0.023, grid_infrastructure: 0.0, climate_risk: 0.002, transition_signal: 0.978, asset_hint: 'ICLN/NEE' },
    { title: 'IEA Oil and Gas Industry in Net Zero Transitions', date: '2023-11-23', renewable_opportunity: 0.650, fossil_pressure: 1.0, grid_infrastructure: 0.448, climate_risk: 0.0, transition_signal: 0.098, asset_hint: 'XLE/XOM transition pressure' },
  ],
  pdf_metrics: [{ n: 50, accuracy: 0.72, macro_f1: 0.704, weighted_f1: 0.718 }],
  validation: [
    { title: 'IRENA Global Renewables Outlook 2020', expected_hint: 'ICLN/NEE', predicted_hint: 'ICLN/NEE', matched: true },
    { title: 'EIA Annual Energy Outlook 2023', expected_hint: 'XLE/XOM transition pressure', predicted_hint: 'XLE/XOM transition pressure', matched: true },
    { title: 'Mixed utility transition report', expected_hint: 'Mixed/grid', predicted_hint: 'ICLN/NEE', matched: false },
  ],
  zero_shot_vs_few_shot: [
    { title: 'IRENA Renewables', expected_hint: 'ICLN/NEE', zero_shot_hint: 'Climate risk', few_shot_hint: 'ICLN/NEE', zero_shot_matched: false, few_shot_matched: true, zero_shot_margin: 0.081, few_shot_margin: 0.314 },
    { title: 'Oil and gas net-zero transition', expected_hint: 'XLE/XOM transition pressure', zero_shot_hint: 'XLE/XOM', few_shot_hint: 'XLE/XOM transition pressure', zero_shot_matched: true, few_shot_matched: true, zero_shot_margin: 0.164, few_shot_margin: 0.276 },
  ],
  news_bridge: [
    { title: 'IEA Renewables 2023', date: '2024-01-11', asset_hint: 'ICLN/NEE', news_context_available: true, news_window_mean: -0.031, news_window_trend: 0.018 },
    { title: 'IEA WEO 2023', date: '2023-10-24', asset_hint: 'ICLN/NEE', news_context_available: true, news_window_mean: -0.012, news_window_trend: 0.044 },
  ],
  stock_link: [
    { title: 'IEA Renewables 2023', asset_hint: 'ICLN/NEE', transition_signal: 1.219, forward_4w_ET_SPREAD: -0.044, forward_4w_ICLN: -0.055, forward_4w_XLE: -0.014, forward_4w_ETN: 0.150 },
    { title: 'IEA WEO 2023', asset_hint: 'ICLN/NEE', transition_signal: 0.978, forward_4w_ET_SPREAD: 0.121, forward_4w_ICLN: 0.052, forward_4w_XLE: -0.062, forward_4w_ETN: 0.179 },
    { title: 'Oil and Gas Net Zero', asset_hint: 'XLE/XOM transition pressure', transition_signal: 0.098, forward_4w_ET_SPREAD: 0.100, forward_4w_ICLN: 0.094, forward_4w_XLE: -0.005, forward_4w_ETN: 0.042 },
  ],
  actual_climate_news: [
    { signal: 'temperature anomaly', target: 'GDELT energy tone', lag_months: 1, n: 72, r: -0.214, p_value: 0.071 },
    { signal: 'temperature anomaly', target: 'climate-policy tone', lag_months: 2, n: 71, r: -0.182, p_value: 0.128 },
  ],
  actual_news_stock: [
    { target: 'ET spread', lag_weeks: 2, n: 312, r: 0.087, p_value: 0.124 },
    { target: 'ICLN', lag_weeks: 4, n: 312, r: -0.063, p_value: 0.266 },
  ],
  failure_analysis: [
    { title: 'Mixed utility transition report', expected_hint: 'Mixed/grid', predicted_hint: 'ICLN/NEE', failure_interpretation: 'Renewable language dominated grid-risk evidence.' },
    { title: 'Climate adaptation finance PDF', expected_hint: 'Climate risk', predicted_hint: 'ICLN/NEE', failure_interpretation: 'Finance terms overlapped with clean-energy investment examples.' },
  ],
  out_of_domain: [
    { title: 'General AI governance paper', asset_hint: 'Out of domain', top_theme: 'none', score_margin: 0.012, ood_decision: 'reject' },
    { title: 'Consumer retail trend report', asset_hint: 'Out of domain', top_theme: 'none', score_margin: 0.018, ood_decision: 'reject' },
  ],
  gemini_check: [
    { title: 'IEA Renewables 2023', expected_theme: 'renewables/grid', human_check_result: 'pass', manual_evidence_alignment: 'supported', unsupported_investment_or_prediction: false },
    { title: 'Oil and Gas Net Zero', expected_theme: 'fossil pressure', human_check_result: 'pass', manual_evidence_alignment: 'supported', unsupported_investment_or_prediction: false },
  ],
};

let scoreChart = null;
let returnsChart = null;
let dashboardReturnsChart = null;
let dashboardLoaded = false;

function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.dataset.tab;
      document.querySelectorAll('.tab-btn').forEach(item => item.classList.toggle('active', item === btn));
      document.querySelectorAll('.tab-section').forEach(section => {
        section.classList.toggle('active', section.id === `tab-${id}`);
        section.classList.toggle('hidden', section.id !== `tab-${id}`);
      });
      if (id === 'dashboard') loadDashboard();
    });
  });
}

function initUpload() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const fileName = document.getElementById('file-name');
  const btnAnalyze = document.getElementById('btn-analyze');

  dropzone.addEventListener('click', () => fileInput.click());
  dropzone.addEventListener('dragover', event => {
    event.preventDefault();
    dropzone.classList.add('dragover');
  });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
  dropzone.addEventListener('drop', event => {
    event.preventDefault();
    dropzone.classList.remove('dragover');
    const file = event.dataTransfer.files[0];
    if (file && file.name.toLowerCase().endsWith('.pdf')) setFile(file);
  });
  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) setFile(fileInput.files[0]);
  });

  function setFile(file) {
    fileInput._selectedFile = file;
    fileName.textContent = file.name;
    btnAnalyze.disabled = false;
  }
}

function initSliders() {
  document.getElementById('inp-pages').addEventListener('input', event => {
    document.getElementById('pages-val').textContent = event.target.value;
  });
  document.getElementById('inp-topk').addEventListener('input', event => {
    document.getElementById('topk-val').textContent = event.target.value;
  });
}

function initForm() {
  const sampleBtn = document.getElementById('btn-sample');
  if (sampleBtn) {
    sampleBtn.addEventListener('click', () => {
      renderResults(SAMPLE_RESULT);
      setAnalyzeState('idle');
    });
  }

  document.getElementById('btn-analyze').addEventListener('click', async () => {
    const fileInput = document.getElementById('file-input');
    const file = fileInput._selectedFile;
    if (!file) return;

    const horizons = [...document.querySelectorAll('.checkbox-group input:checked')]
      .map(checkbox => checkbox.value)
      .join(',');

    const fd = new FormData();
    fd.append('file', file);
    fd.append('title', document.getElementById('inp-title').value);
    fd.append('issuer', document.getElementById('inp-issuer').value);
    fd.append('report_date', document.getElementById('inp-date').value);
    fd.append('max_pages', document.getElementById('inp-pages').value);
    fd.append('top_k', document.getElementById('inp-topk').value);
    fd.append('horizons', horizons || '4');

    setAnalyzeState('loading');
    try {
      const res = await fetch('/api/analyze', { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Analysis failed.');
      renderResults(data);
      setAnalyzeState('done');
    } catch (err) {
      showError(err.message);
      setAnalyzeState('idle');
    }
  });
}

function setAnalyzeState(state) {
  const btnText = document.getElementById('btn-text');
  const btnSpinner = document.getElementById('btn-spinner');
  const btnAnalyze = document.getElementById('btn-analyze');
  const hasFile = Boolean(document.getElementById('file-input')._selectedFile);

  if (state === 'loading') {
    btnText.textContent = 'Analyzing';
    btnSpinner.classList.remove('hidden');
    btnAnalyze.disabled = true;
    showPanel('loading');
    return;
  }

  btnText.textContent = state === 'done' ? 'Analyze another PDF' : 'Analyze evidence';
  btnSpinner.classList.add('hidden');
  btnAnalyze.disabled = !hasFile;
}

function showPanel(which) {
  ['result-empty', 'result-loading', 'result-content', 'result-error'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.toggle('hidden', id !== `result-${which}`);
  });
}

function showError(message) {
  document.getElementById('error-msg').textContent = message;
  showPanel('error');
}

function renderResults(data) {
  renderScoreCards(data.scores);
  renderScoreChart(data.scores);
  renderConfidence(data.scores, data.confidence);
  renderSummary(data.summary);
  renderEvidence(data.evidence, parseInt(document.getElementById('inp-topk').value, 10));
  renderReturns(data.returns);
  renderStats(data.stats);
  showPanel('content');
}

function renderScoreCards(scores) {
  const container = document.getElementById('score-cards');
  const items = [
    ...Object.entries(THEME_META).map(([key, meta]) => ({ label: meta.label, cls: meta.cls, value: scores[key] })),
    { label: 'Transition signal', cls: 'score-signal', value: scores.transition_signal, raw: true },
  ];

  container.innerHTML = items.map(({ label, cls, value, raw }) => {
    const numericValue = Number(value || 0);
    const pct = raw ? Math.min(Math.abs(numericValue / 1.5) * 100, 100) : Math.min(numericValue * 100, 100);
    return `
      <div class="score-card ${cls}">
        <span class="sc-label">${escapeHtml(label)}</span>
        <span class="sc-value">${numericValue.toFixed(3)}</span>
        <div class="sc-bar"><div class="sc-bar-fill" style="width:${pct.toFixed(1)}%"></div></div>
      </div>`;
  }).join('');
}

function renderScoreChart(scores) {
  const canvas = document.getElementById('score-chart');
  if (!canvas || typeof Chart === 'undefined') return;
  if (scoreChart) scoreChart.destroy();
  scoreChart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: Object.values(THEME_META).map(meta => meta.label),
      datasets: [{
        data: Object.keys(THEME_META).map(key => scores[key] || 0),
        backgroundColor: Object.values(THEME_META).map(meta => `${meta.color}cc`),
        borderColor: Object.values(THEME_META).map(meta => meta.color),
        borderWidth: 1,
        borderRadius: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { min: 0, max: 1, grid: { color: '#e6e9ee' }, ticks: { color: '#667085' } },
        x: { grid: { display: false }, ticks: { color: '#667085' } },
      },
    },
  });
}

function renderConfidence(scores, conf) {
  const box = document.getElementById('confidence-box');
  const topThemeLabel = themeLabel(conf.top_theme);
  const secondThemeLabel = themeLabel(conf.second_theme);
  const mixedLine = conf.mixed_signal
    ? `<span>Mixed signal: ${escapeHtml(topThemeLabel)} + ${escapeHtml(secondThemeLabel)}</span>`
    : '';
  const confColor = { High: '#1f7a5c', Medium: '#9a5b18', Low: '#a33b32' }[conf.level] || '#667085';
  box.innerHTML = `
    <strong>${escapeHtml(scores.asset_hint || 'Research signal')}</strong>
    <span>Top theme: ${escapeHtml(topThemeLabel)}</span>
    ${mixedLine}
    <span>Confidence: <b style="color:${confColor}">${escapeHtml(conf.level || 'Review')}</b></span>
    <span>Score margin: ${Number(conf.margin || 0).toFixed(3)}</span>`;
}

function renderSummary(summary) {
  const box = document.getElementById('summary-box');
  const bullets = String(summary.bullets || '')
    .split(' | ')
    .filter(Boolean)
    .slice(0, 4)
    .map(item => `<li>${escapeHtml(item)}</li>`)
    .join('');
  const gen = summary.generative && summary.generative.summary
    ? `<p class="generated-summary">${escapeHtml(summary.generative.summary)}</p>`
    : '';
  box.innerHTML = `<p>${escapeHtml(summary.korean || '')}</p><ul class="summary-bullets">${bullets}</ul>${gen}`;
}

function renderEvidence(evidence, topK) {
  const tabsEl = document.getElementById('evidence-tabs');
  const contentEl = document.getElementById('evidence-content');
  const keys = Object.keys(THEME_META);
  const displayLimit = Math.min(topK || 5, 5);

  tabsEl.innerHTML = keys.map((key, index) =>
    `<button class="ev-tab ${index === 0 ? 'active' : ''}" data-key="${key}">${THEME_META[key].label}</button>`
  ).join('');

  contentEl.innerHTML = keys.map((key, index) => {
    const rows = (evidence[key] || []).slice(0, displayLimit).map(item => `
      <div class="ev-item">
        <div class="ev-meta">
          <span>p.${escapeHtml(item.page === undefined || item.page === null ? '-' : item.page)}</span>
          <span>#${escapeHtml(item.rank === undefined || item.rank === null ? '-' : item.rank)}</span>
          <span class="ev-score">${Number(item.score || 0).toFixed(3)}</span>
        </div>
        <div class="ev-text">${highlightKeywords(item.paragraph || '')}</div>
      </div>`).join('');
    return `<div class="ev-list ${index === 0 ? 'active' : ''}" data-key="${key}">${rows || '<p class="note">No evidence fragment for this theme.</p>'}</div>`;
  }).join('');

  tabsEl.onclick = event => {
    const btn = event.target.closest('.ev-tab');
    if (!btn) return;
    tabsEl.querySelectorAll('.ev-tab').forEach(tab => tab.classList.toggle('active', tab === btn));
    contentEl.querySelectorAll('.ev-list').forEach(list => list.classList.toggle('active', list.dataset.key === btn.dataset.key));
  };
}

function renderReturns(returns) {
  const box = document.getElementById('returns-box');
  if (!returns || Object.keys(returns).length === 0) {
    box.innerHTML = '<p class="note">No historical return window is available for this report date.</p>';
    return;
  }

  const fwdGroups = {};
  Object.keys(returns).filter(key => key.startsWith('forward_')).forEach(key => {
    const match = key.match(/^forward_(\d+)w_(.+)$/);
    if (match) (fwdGroups[match[1]] = fwdGroups[match[1]] || {})[match[2]] = returns[key];
  });

  const cols = Object.keys(MARKET_LABELS);
  const periods = [];
  if (cols.some(col => returns[`pre_4w_${col}`] !== undefined)) periods.push({ label: 'Pre 4w', prefix: 'pre_4w_' });
  Object.keys(fwdGroups).sort((a, b) => Number(a) - Number(b)).forEach(weeks => {
    periods.push({ label: `Post ${weeks}w`, group: fwdGroups[weeks] });
  });

  const chartId = `returns-chart-${Date.now()}`;
  const fmtCell = value => {
    if (value === undefined || value === null) return '<td>-</td>';
    const cls = value > 0.005 ? 'pos' : value < -0.005 ? 'neg' : '';
    return `<td class="${cls}">${value > 0 ? '+' : ''}${(value * 100).toFixed(2)}%</td>`;
  };

  let html = `<div class="chart-wrap returns-chart-wrap"><canvas id="${chartId}" height="170"></canvas></div>`;
  html += `<div class="table-wrap"><table class="data-table compact-table">
    <thead><tr><th>Window</th>${cols.map(col => `<th>${MARKET_LABELS[col]}</th>`).join('')}</tr></thead><tbody>`;
  periods.forEach(period => {
    html += `<tr><td>${period.label}</td>${cols.map(col => fmtCell(period.prefix ? returns[`${period.prefix}${col}`] : period.group[col])).join('')}</tr>`;
  });
  html += '</tbody></table></div>';
  box.innerHTML = html;

  const graphCols = ['ET_SPREAD', 'ICLN', 'XLE', 'ETN'];
  const chartData = periods.map(period => graphCols.map(col => {
    const value = period.prefix ? returns[`${period.prefix}${col}`] : period.group[col];
    return value === undefined ? null : value;
  }));
  renderReturnsChart(chartId, periods.map(period => period.label), graphCols, chartData, false);
}

function renderReturnsChart(canvasId, labels, columns, valuesByPeriod, dashboardMode) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === 'undefined') return;
  const palette = { ET_SPREAD: '#364152', ICLN: '#1f7a5c', XLE: '#9a5b18', ETN: '#315f9f', NEE: '#667085', XOM: '#a33b32' };
  const datasets = columns.map((col, index) => ({
    label: MARKET_LABELS[col] || col,
    data: valuesByPeriod.map(row => row[index] === null || row[index] === undefined ? null : row[index] * 100),
    backgroundColor: `${palette[col] || '#667085'}cc`,
    borderColor: palette[col] || '#667085',
    borderWidth: 1,
    borderRadius: 3,
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
        legend: { position: 'bottom', labels: { color: '#667085', boxWidth: 12 } },
        tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y > 0 ? '+' : ''}${ctx.parsed.y.toFixed(2)}%` } },
      },
      scales: {
        y: { grid: { color: '#e6e9ee' }, ticks: { color: '#667085', callback: value => `${value}%` } },
        x: { grid: { display: false }, ticks: { color: '#667085' } },
      },
    },
  });

  if (dashboardMode) dashboardReturnsChart = chart;
  else returnsChart = chart;
}

function renderStats(stats) {
  document.getElementById('stats-row').innerHTML = [
    `Pages <strong>${escapeHtml(stats.pages)}</strong>`,
    `Paragraphs <strong>${escapeHtml(stats.paragraphs)}</strong>`,
    `Evidence chunks <strong>${escapeHtml(stats.evidence_count)}</strong>`,
  ].map(item => `<span class="stat-item">${item}</span>`).join('');
}

async function loadDashboard() {
  if (dashboardLoaded) return;
  dashboardLoaded = true;
  renderDashboard(FALLBACK_DASHBOARD);

  try {
    const res = await fetch('/api/dashboard');
    if (!res.ok) throw new Error('Dashboard API failed.');
    const data = await res.json();
    renderDashboard(mergeDashboardFallback(data));
  } catch (err) {
    renderDashboard(FALLBACK_DASHBOARD);
  }
}

function mergeDashboardFallback(data) {
  return Object.fromEntries(Object.entries(FALLBACK_DASHBOARD).map(([key, fallbackRows]) => {
    const rows = data && Array.isArray(data[key]) && data[key].length ? data[key] : fallbackRows;
    return [key, rows];
  }));
}

function renderDashboard(data) {
  renderSignalsTable(data.signals);
  renderNewsBridgeTable(data.news_bridge);
  renderLinkTable(data.stock_link);
  renderActualEvidenceTables(data);
  renderValidationTable(data.validation);
}

function renderActualEvidenceTables(data) {
  renderGenericTable('actual-climate-news-wrap', data.actual_climate_news, {
    signal: 'Signal', target: 'Target', lag_months: 'Lag', n: 'n', r: 'r', p_value: 'p-value',
  });
  renderGenericTable('actual-news-stock-wrap', data.actual_news_stock, {
    target: 'Target', lag_weeks: 'Best lag', n: 'n', r: 'r', p_value: 'p-value',
  });
  renderGenericTable('pdf-metrics-wrap', data.pdf_metrics, {
    n: 'n', accuracy: 'Accuracy', macro_f1: 'Macro-F1', weighted_f1: 'Weighted-F1',
  });
  renderGenericTable('failure-analysis-wrap', data.failure_analysis, {
    title: 'PDF', expected_hint: 'Expected', predicted_hint: 'Predicted', failure_interpretation: 'Interpretation',
  });
  renderGenericTable('gemini-check-wrap', data.gemini_check, {
    title: 'PDF', expected_theme: 'Theme', human_check_result: 'Human check', manual_evidence_alignment: 'Evidence alignment', unsupported_investment_or_prediction: 'Unsupported prediction',
  });
  renderGenericTable('ood-test-wrap', data.out_of_domain, {
    title: 'OOD PDF', asset_hint: 'Model signal', top_theme: 'Top theme', score_margin: 'Margin', ood_decision: 'Decision',
  });
  renderGenericTable('zero-shot-wrap', data.zero_shot_vs_few_shot, {
    title: 'PDF', expected_hint: 'Expected', zero_shot_hint: 'Zero-shot', few_shot_hint: 'Few-shot', zero_shot_matched: 'Zero match', few_shot_matched: 'Few match', zero_shot_margin: 'Zero margin', few_shot_margin: 'Few margin',
  });
}

function renderGenericTable(id, rows, headers) {
  const wrap = document.getElementById(id);
  if (!wrap) return;
  if (!rows || !rows.length) {
    wrap.innerHTML = '<p class="note">Preview data unavailable.</p>';
    return;
  }
  const cols = Object.keys(headers).filter(col => col in rows[0]);
  wrap.innerHTML = `<table class="data-table compact-table">
    <thead><tr>${cols.map(col => `<th>${headers[col]}</th>`).join('')}</tr></thead>
    <tbody>${rows.map(row => `<tr>${cols.map(col => formatTableCell(row[col], col)).join('')}</tr>`).join('')}</tbody>
  </table>`;
}

function renderNewsBridgeTable(rows) {
  renderGenericTable('news-bridge-wrap', rows, {
    title: 'Report',
    date: 'Date',
    asset_hint: 'PDF signal',
    news_context_available: 'News',
    news_window_mean: '4w mean',
    news_window_trend: '4w trend',
  });
}

function renderValidationTable(rows) {
  renderGenericTable('validation-table-wrap', rows, {
    title: 'Validation PDF',
    expected_hint: 'Expected',
    predicted_hint: 'Model result',
    matched: 'Match',
  });
}

function renderSignalsTable(signals) {
  renderGenericTable('signals-table-wrap', signals, {
    title: 'Report',
    date: 'Date',
    renewable_opportunity: 'Renewables',
    fossil_pressure: 'Fossil',
    grid_infrastructure: 'Grid',
    climate_risk: 'Climate',
    transition_signal: 'Transition',
    asset_hint: 'Asset hint',
  });
}

function renderLinkTable(link) {
  const wrap = document.getElementById('link-table-wrap');
  if (!link || !link.length) {
    wrap.innerHTML = '<p class="note">Preview data unavailable.</p>';
    return;
  }

  const graphCols = ['forward_4w_ET_SPREAD', 'forward_4w_ICLN', 'forward_4w_XLE', 'forward_4w_ETN'];
  const labels = link.map(row => shortenTitle(row.title || row.report_id || 'Report'));
  const valuesByPeriod = link.map(row => graphCols.map(col => row[col] === undefined ? null : row[col]));
  const cols = ['title', 'asset_hint', 'transition_signal', ...graphCols].filter(col => col in link[0]);

  wrap.innerHTML = `
    <div class="chart-wrap returns-chart-wrap dashboard-return-chart">
      <canvas id="dashboard-returns-chart" height="210"></canvas>
    </div>
    <table class="data-table compact-table">
      <thead><tr>${cols.map(col => `<th>${escapeHtml(prettyHeader(col))}</th>`).join('')}</tr></thead>
      <tbody>${link.map(row => `<tr>${cols.map(col => formatTableCell(row[col], col)).join('')}</tr>`).join('')}</tbody>
    </table>`;
  renderReturnsChart('dashboard-returns-chart', labels, ['ET_SPREAD', 'ICLN', 'XLE', 'ETN'], valuesByPeriod, true);
}

function formatTableCell(value, col) {
  if (typeof value === 'boolean') return `<td class="${value ? 'match' : 'neg'}">${value ? 'Match' : 'Miss'}</td>`;
  if (typeof value === 'number') {
    const cls = value > 0.005 ? 'pos' : value < -0.005 ? 'neg' : '';
    if (col.includes('forward_') || col.includes('pre_')) return `<td class="${cls}">${value > 0 ? '+' : ''}${(value * 100).toFixed(2)}%</td>`;
    return `<td class="${cls}">${Math.abs(value) < 10 ? value.toFixed(3) : value.toFixed(0)}</td>`;
  }
  const text = String(value === undefined || value === null ? '' : value);
  return `<td>${escapeHtml(text.length > 110 ? `${text.slice(0, 110)}...` : text)}</td>`;
}

function prettyHeader(col) {
  return col
    .replace('forward_4w_', '4w ')
    .replace('transition_signal', 'Transition')
    .replace('asset_hint', 'Asset hint')
    .replace('title', 'Report');
}

function themeLabel(key) {
  return THEME_META[key] ? THEME_META[key].label : key || 'Review';
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function highlightKeywords(str) {
  const keywords = [
    'renewable', 'solar', 'wind', 'clean energy', 'capacity',
    'oil', 'gas', 'fossil', 'methane', 'carbon', 'emissions',
    'grid', 'transmission', 'distribution', 'electricity', 'electrification', 'power',
    'climate', 'weather', 'heat', 'drought', 'risk', 'resilience',
    'investment', 'demand', 'policy', 'regulation', 'cost',
  ];
  const escaped = escapeHtml(str);
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

initTabs();
initUpload();
initSliders();
initForm();
renderResults(SAMPLE_RESULT);
