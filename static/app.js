'use strict';

const THEME_META = {
  renewable_opportunity: { label: '재생에너지', color: '#1f7a5c', cls: 'score-renewable' },
  fossil_pressure: { label: '화석연료 압력', color: '#9a5b18', cls: 'score-fossil' },
  grid_infrastructure: { label: '전력망/전기화', color: '#315f9f', cls: 'score-grid' },
  climate_risk: { label: '기후 리스크', color: '#a33b32', cls: 'score-climate' },
};

const MARKET_LABELS = {
  ET_SPREAD: 'ET Spread',
  ICLN: 'ICLN',
  XLE: 'XLE',
  NEE: 'NEE',
  XOM: 'XOM',
  ETN: 'ETN',
};

const THEME_LABELS = Object.fromEntries(Object.entries(THEME_META).map(([key, meta]) => [key, meta.label]));

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
      if (!res.ok) throw new Error(data.detail || '분석에 실패했습니다.');
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

  if (state === 'loading') {
    btnText.textContent = '분석 중';
    btnSpinner.classList.remove('hidden');
    btnAnalyze.disabled = true;
    showPanel('loading');
    return;
  }

  btnText.textContent = '분석 실행';
  btnSpinner.classList.add('hidden');
  btnAnalyze.disabled = false;
}

function showPanel(which) {
  ['result-empty', 'result-loading', 'result-content', 'result-error'].forEach(id => {
    document.getElementById(id).classList.toggle('hidden', id !== `result-${which}`);
  });
}

function showError(message) {
  document.getElementById('error-msg').textContent = message;
  showPanel('error');
}

function renderResults(data) {
  renderScoreCards(data.scores);
  renderChart(data.scores);
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
    { label: '전환 신호', cls: 'score-signal', value: scores.transition_signal, raw: true },
  ];

  container.innerHTML = items.map(({ label, cls, value, raw }) => {
    const pct = raw ? Math.min(Math.abs(value / 3) * 100, 100) : Math.min(value * 100, 100);
    return `
      <div class="score-card ${cls}">
        <span class="sc-label">${escapeHtml(label)}</span>
        <span class="sc-value">${Number(value).toFixed(3)}</span>
        <div class="sc-bar"><div class="sc-bar-fill" style="width:${pct.toFixed(1)}%"></div></div>
      </div>`;
  }).join('');
}

function renderChart(scores) {
  const canvas = document.getElementById('score-chart');
  if (scoreChart) scoreChart.destroy();
  scoreChart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: Object.values(THEME_META).map(meta => meta.label),
      datasets: [{
        data: Object.keys(THEME_META).map(key => scores[key]),
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
  const topThemeLabel = THEME_LABELS[conf.top_theme] || conf.top_theme;
  const secondThemeLabel = THEME_LABELS[conf.second_theme] || conf.second_theme;
  const mixedLine = conf.mixed_signal
    ? `<span>복합 신호: ${escapeHtml(topThemeLabel)} + ${escapeHtml(secondThemeLabel)}</span>`
    : '';
  const confColor = { 높음: '#1f7a5c', 보통: '#9a5b18', 낮음: '#a33b32' }[conf.level] || '#667085';
  box.innerHTML = `
    <strong>${escapeHtml(scores.asset_hint)}</strong>
    <span>상위 테마: ${escapeHtml(topThemeLabel)}</span>
    ${mixedLine}
    <span>확신도: <b style="color:${confColor}">${escapeHtml(conf.level)}</b></span>
    <span>점수 차이: ${Number(conf.margin).toFixed(3)}</span>`;
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
  const displayLimit = Math.min(topK, 5);

  tabsEl.innerHTML = keys.map((key, index) =>
    `<button class="ev-tab ${index === 0 ? 'active' : ''}" data-key="${key}">${THEME_META[key].label}</button>`
  ).join('');

  contentEl.innerHTML = keys.map((key, index) => {
    const rows = (evidence[key] || []).slice(0, displayLimit).map(item => `
      <div class="ev-item">
        <div class="ev-meta">
          <span>p.${item.page}</span>
          <span>#${item.rank}</span>
          <span class="ev-score">${Number(item.score).toFixed(3)}</span>
        </div>
        <div class="ev-text">${highlightKeywords(item.paragraph)}</div>
      </div>`).join('');
    return `<div class="ev-list ${index === 0 ? 'active' : ''}" data-key="${key}">${rows || '<p class="note">근거 문단 없음</p>'}</div>`;
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
    box.innerHTML = '<p class="note">기준일에 연결할 수 있는 수익률 데이터가 없습니다.</p>';
    return;
  }

  const fwdGroups = {};
  Object.keys(returns).filter(key => key.startsWith('forward_')).forEach(key => {
    const match = key.match(/^forward_(\d+)w_(.+)$/);
    if (match) (fwdGroups[match[1]] = fwdGroups[match[1]] || {})[match[2]] = returns[key];
  });

  const cols = Object.keys(MARKET_LABELS);
  const periods = [];
  if (cols.some(col => returns[`pre_4w_${col}`] !== undefined)) periods.push({ label: '이전 4주', prefix: 'pre_4w_' });
  Object.keys(fwdGroups).sort((a, b) => Number(a) - Number(b)).forEach(weeks => {
    periods.push({ label: `이후 ${weeks}주`, group: fwdGroups[weeks] });
  });

  const chartId = `returns-chart-${Date.now()}`;
  const fmtCell = value => {
    if (value === undefined || value === null) return '<td>-</td>';
    const cls = value > 0.005 ? 'pos' : value < -0.005 ? 'neg' : '';
    return `<td class="${cls}">${value > 0 ? '+' : ''}${(value * 100).toFixed(2)}%</td>`;
  };

  let html = `<div class="chart-wrap returns-chart-wrap"><canvas id="${chartId}" height="170"></canvas></div>`;
  html += `<div class="table-wrap"><table class="data-table compact-table">
    <thead><tr><th>기간</th>${cols.map(col => `<th>${MARKET_LABELS[col]}</th>`).join('')}</tr></thead><tbody>`;
  periods.forEach(period => {
    html += `<tr><td>${period.label}</td>${cols.map(col => fmtCell(period.prefix ? returns[`${period.prefix}${col}`] : period.group[col])).join('')}</tr>`;
  });
  html += '</tbody></table></div>';
  box.innerHTML = html;

  const graphCols = ['ET_SPREAD', 'ICLN', 'XLE', 'ETN'];
  const chartData = periods.map(period => graphCols.map(col => period.prefix ? returns[`${period.prefix}${col}`] ?? null : period.group[col] ?? null));
  renderReturnsChart(chartId, periods.map(period => period.label), graphCols, chartData, false);
}

function renderReturnsChart(canvasId, labels, columns, valuesByPeriod, dashboardMode) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const palette = { ET_SPREAD: '#364152', ICLN: '#1f7a5c', XLE: '#9a5b18', ETN: '#315f9f', NEE: '#667085', XOM: '#a33b32' };
  const datasets = columns.map((col, index) => ({
    label: MARKET_LABELS[col] || col,
    data: valuesByPeriod.map(row => row[index] === null ? null : row[index] * 100),
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
    `추출 페이지 <strong>${stats.pages}</strong>`,
    `분석 문단 <strong>${stats.paragraphs}</strong>`,
    `근거 문단 <strong>${stats.evidence_count}</strong>`,
  ].map(item => `<span class="stat-item">${item}</span>`).join('');
}

async function loadDashboard() {
  if (dashboardLoaded) return;
  dashboardLoaded = true;

  try {
    const res = await fetch('/api/dashboard');
    const data = await res.json();
    renderSignalsTable(data.signals);
    renderNewsBridgeTable(data.news_bridge);
    renderLinkTable(data.stock_link);
    renderActualEvidenceTables(data);
    renderValidationTable(data.validation);
  } catch (err) {
    document.getElementById('signals-table-wrap').innerHTML = '<p class="note">데이터를 불러오지 못했습니다.</p>';
  }
}

function renderActualEvidenceTables(data) {
  renderGenericTable('actual-climate-news-wrap', data.actual_climate_news, {
    signal: '신호', target: '대상', lag_months: 'Lag(월)', n: 'n', r: 'r', p_value: 'p-value',
  });
  renderGenericTable('actual-news-stock-wrap', data.actual_news_stock, {
    target: '대상', lag_weeks: 'Best lag(주)', n: 'n', r: 'r', p_value: 'p-value',
  });
  renderGenericTable('pdf-metrics-wrap', data.pdf_metrics, {
    n: 'n', accuracy: 'Accuracy', macro_f1: 'Macro-F1', weighted_f1: 'Weighted-F1',
  });
  renderGenericTable('failure-analysis-wrap', data.failure_analysis, {
    title: 'PDF', expected_hint: 'Expected', predicted_hint: 'Predicted', failure_interpretation: '해석',
  });
  renderGenericTable('gemini-check-wrap', data.gemini_check, {
    title: 'PDF', expected_theme: '테마', human_check_result: '점검', manual_evidence_alignment: '근거 일치', unsupported_investment_or_prediction: '위험 문구',
  });
  renderGenericTable('ood-test-wrap', data.out_of_domain, {
    title: 'OOD PDF', asset_hint: '모델 신호', top_theme: '상위 테마', score_margin: '점수 차이', ood_decision: '판정',
  });
  renderGenericTable('zero-shot-wrap', data.zero_shot_vs_few_shot, {
    title: 'PDF', expected_hint: 'Expected', zero_shot_hint: 'Zero-shot', few_shot_hint: 'Few-shot', zero_shot_matched: 'Zero match', few_shot_matched: 'Few match', zero_shot_margin: 'Zero margin', few_shot_margin: 'Few margin',
  });
}

function renderGenericTable(id, rows, headers) {
  const wrap = document.getElementById(id);
  if (!wrap) return;
  if (!rows || !rows.length) {
    wrap.innerHTML = '<p class="note">데이터 없음</p>';
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
    title: '보고서',
    date: '날짜',
    asset_hint: 'PDF 신호',
    news_context_available: '뉴스',
    news_window_mean: '4주 평균',
    news_window_trend: '4주 추세',
  });
}

function renderValidationTable(rows) {
  renderGenericTable('validation-table-wrap', rows, {
    title: '검증 PDF',
    expected_hint: '기대 방향',
    predicted_hint: '모델 결과',
    matched: '일치',
  });
}

function renderSignalsTable(signals) {
  renderGenericTable('signals-table-wrap', signals, {
    title: '보고서',
    date: '날짜',
    renewable_opportunity: '재생',
    fossil_pressure: '화석',
    grid_infrastructure: '전력망',
    climate_risk: '기후',
    transition_signal: '전환',
    asset_hint: '자산 힌트',
  });
}

function renderLinkTable(link) {
  const wrap = document.getElementById('link-table-wrap');
  if (!link || !link.length) {
    wrap.innerHTML = '<p class="note">데이터 없음</p>';
    return;
  }

  const graphCols = ['forward_4w_ET_SPREAD', 'forward_4w_ICLN', 'forward_4w_XLE', 'forward_4w_ETN'];
  const labels = link.map(row => shortenTitle(row.title || row.report_id || 'Report'));
  const valuesByPeriod = link.map(row => graphCols.map(col => row[col] ?? null));
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
  if (typeof value === 'boolean') return `<td class="${value ? 'match' : 'neg'}">${value ? '일치' : '불일치'}</td>`;
  if (typeof value === 'number') {
    const cls = value > 0.005 ? 'pos' : value < -0.005 ? 'neg' : '';
    if (col.includes('forward_') || col.includes('pre_')) return `<td class="${cls}">${value > 0 ? '+' : ''}${(value * 100).toFixed(2)}%</td>`;
    return `<td class="${cls}">${Math.abs(value) < 10 ? value.toFixed(3) : value.toFixed(0)}</td>`;
  }
  const text = String(value ?? '');
  return `<td>${escapeHtml(text.length > 110 ? `${text.slice(0, 110)}...` : text)}</td>`;
}

function prettyHeader(col) {
  return col
    .replace('forward_4w_', '4w ')
    .replace('transition_signal', '전환')
    .replace('asset_hint', '자산 힌트')
    .replace('title', '보고서');
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
