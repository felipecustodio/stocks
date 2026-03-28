import { evaluateRisk } from './risk.mjs';
import { categoryForStrategy, categoryMetrics } from './categories.mjs';

function riskClass(level) {
  if (level === 'ALTO') return 'risk-high';
  if (level === 'MÉDIO') return 'risk-medium';
  return 'risk-low';
}

function ensureUiEnhancements(root = document) {
  if (window.lucide?.createIcons) {
    window.lucide.createIcons();
  }
  if (window.MathJax?.typesetPromise) {
    window.MathJax.typesetPromise([root]).catch(() => {});
  }
}

function flashCopyButton(button, copied) {
  if (!button) return;
  const label = button.querySelector('.copy-btn-label');
  if (!label) return;
  const nextLabel = copied ? 'Copiado' : 'Falhou';

  button.classList.remove('copy-success', 'copy-fail');
  button.classList.add(copied ? 'copy-success' : 'copy-fail', 'copy-animating');
  label.textContent = nextLabel;

  window.setTimeout(() => {
    button.classList.remove('copy-success', 'copy-fail', 'copy-animating');
    label.textContent = 'Copiar Top N';
  }, 1400);
}

function topPicks(stocks, max = 5) {
  return stocks.slice(0, max).map((stock) => stock.Papel).filter(Boolean);
}

function asNumber(value, fallback = null) {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const cleaned = value.replace(/[^\d,.-]/g, '').replace(/\.(?=\d{3}(?:\D|$))/g, '').replace(',', '.');
    const parsed = Number(cleaned);
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallback;
}

function logoUrlForTicker(ticker) {
  const safeTicker = String(ticker ?? '').trim().toUpperCase();
  return `https://raw.githubusercontent.com/thefintz/icones-b3/main/icones/${safeTicker}.png`;
}

function logoMarkup(ticker, logoClass = 'ticker-logo', fallbackClass = 'ticker-fallback') {
  const safeTicker = String(ticker ?? '').trim().toUpperCase();
  const url = logoUrlForTicker(safeTicker);
  return `
    <img
      class="${logoClass}"
      src="${url}"
      alt="Logo ${safeTicker}"
      loading="lazy"
      onerror="this.style.display='none'; this.nextElementSibling.style.display='inline-flex';"
    />
    <span class="${fallbackClass}" style="display:none;">${safeTicker.slice(0, 1) || '?'}</span>
  `;
}

function topPickPillsMarkup(picks) {
  if (!picks.length) return '<span class="muted">Sem picks</span>';
  return picks
    .map(
      (ticker) => `
        <span class="top-pick-pill">
          ${logoMarkup(ticker, 'top-pick-logo', 'top-pick-fallback')}
          <span>${ticker}</span>
        </span>
      `
    )
    .join('');
}

function getPathValue(obj, path) {
  if (!obj || typeof obj !== 'object') return null;
  let current = obj;
  for (const key of path) {
    if (!current || typeof current !== 'object' || !(key in current)) {
      return null;
    }
    current = current[key];
  }
  return current;
}

function readMetric(stock, metric) {
  const raw = getPathValue(stock, metric.path);
  if (raw === null || raw === undefined || raw === '') {
    return `${metric.label}: N/D`;
  }
  if (typeof raw === 'number') {
    return `${metric.label}: ${Number.isInteger(raw) ? raw : raw.toFixed(2)}`;
  }
  return `${metric.label}: ${String(raw)}`;
}

function metricNumericValue(stock, metric) {
  const raw = getPathValue(stock, metric.path);
  return asNumber(raw, null);
}

function inferMetricPreference(metric) {
  const label = String(metric?.label ?? '').toLowerCase();
  if (label.includes('rank')) return 'lower';
  if (label.includes('ev/') || label.includes('p/l') || label.includes('p/vp')) return 'lower';
  if (label.includes('peg') || label.includes('dív/pl')) return 'lower';
  return 'higher';
}

function percentile(value, sortedValues) {
  if (!Number.isFinite(value) || sortedValues.length === 0) return null;
  let left = 0;
  let right = sortedValues.length - 1;
  while (left <= right) {
    const mid = Math.floor((left + right) / 2);
    if (sortedValues[mid] <= value) {
      left = mid + 1;
    } else {
      right = mid - 1;
    }
  }
  return right / Math.max(1, sortedValues.length - 1);
}

function computeRiskProfile(stocks) {
  const counts = { BAIXO: 0, 'MÉDIO': 0, ALTO: 0 };
  for (const stock of stocks) {
    const level = evaluateRisk(stock).risk_level;
    counts[level] += 1;
  }
  const total = stocks.length || 1;
  const weighted = (counts.BAIXO * 1 + counts['MÉDIO'] * 2 + counts.ALTO * 3) / total;
  if (weighted <= 1.4) return { counts, profile: 'Conservador', volatilityBand: [10, 18], drawdownBand: [8, 15] };
  if (weighted <= 1.9) return { counts, profile: 'Moderado', volatilityBand: [16, 28], drawdownBand: [12, 24] };
  return { counts, profile: 'Agressivo', volatilityBand: [24, 40], drawdownBand: [20, 35] };
}

function renderStrategyRiskVisual(panel, strategy, displayLimit) {
  if (!window.Chart) return;
  const visibleCount = displayLimit === 'ALL' ? strategy.stocks.length : Math.min(strategy.stocks.length, displayLimit);
  const scopeStocks = strategy.stocks.slice(0, visibleCount);
  const profile = computeRiskProfile(scopeStocks);
  const riskCanvas = panel.querySelector('.risk-mix-chart');
  const bandCanvas = panel.querySelector('.risk-band-chart');
  if (!riskCanvas || !bandCanvas) return;

  const riskCtx = riskCanvas.getContext('2d');
  const bandCtx = bandCanvas.getContext('2d');
  if (!riskCtx || !bandCtx) return;

  new window.Chart(riskCtx, {
    type: 'doughnut',
    data: {
      labels: ['Baixo', 'Médio', 'Alto'],
      datasets: [
        {
          data: [profile.counts.BAIXO, profile.counts['MÉDIO'], profile.counts.ALTO],
          backgroundColor: ['#ffffff', '#cfcfcf', '#ff3000'],
          borderColor: '#000000',
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: true } },
      cutout: '55%',
      radius: '88%',
    },
  });

  const [volMin, volMax] = profile.volatilityBand;
  const [ddMin, ddMax] = profile.drawdownBand;
  new window.Chart(bandCtx, {
    type: 'bar',
    data: {
      labels: ['Vol anual', 'Drawdown'],
      datasets: [
        { data: [volMin, ddMin], backgroundColor: 'transparent', stack: 'range' },
        {
          data: [volMax - volMin, ddMax - ddMin],
          backgroundColor: ['#000000', '#ff3000'],
          borderColor: '#000000',
          borderWidth: 1,
          stack: 'range',
        },
      ],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      scales: {
        x: { stacked: true, beginAtZero: true, max: 45, ticks: { callback: (v) => `${v}%` } },
        y: { stacked: true },
      },
    },
  });

  const text = panel.querySelector('.risk-band-text');
  if (text) {
    text.textContent = `Perfil ${profile.profile} com base em ${scopeStocks.length} papel(is) exibidos. Volatilidade esperada: ${volMin}%-${volMax}% a.a.; drawdown esperado: ${ddMin}%-${ddMax}% (heurístico).`;
  }
}

function renderStrategyQuantVisual(panel, strategy, displayLimit) {
  if (!window.Chart) return;

  const maxRows = displayLimit === 'ALL' ? strategy.stocks.length : Number(displayLimit);
  const visibleStocks = strategy.stocks.slice(0, maxRows);
  if (!visibleStocks.length) return;

  const metrics = metricConfigFor(strategy.strategy_id).slice(0, 3);
  if (!metrics.length) return;

  const scatterCanvas = panel.querySelector('.quant-scatter-chart');
  const contributionCanvas = panel.querySelector('.quant-contrib-chart');
  const heatmapHead = panel.querySelector('.quant-heatmap-head');
  const heatmapBody = panel.querySelector('.quant-heatmap-body');
  const picker = panel.querySelector('.quant-stock-picker');
  const contributionText = panel.querySelector('.quant-contrib-text');
  if (!scatterCanvas || !contributionCanvas || !heatmapHead || !heatmapBody || !picker || !contributionText) return;

  const rowData = visibleStocks.map((stock, index) => {
    const risk = evaluateRisk(stock).risk_level;
    const metricValues = metrics.map((metric) => metricNumericValue(stock, metric));
    return {
      ticker: stock.Papel ?? `#${index + 1}`,
      rank: index + 1,
      risk,
      metricValues,
    };
  });

  const riskColor = (level) => {
    if (level === 'ALTO') return '#ff3000';
    if (level === 'MÉDIO') return '#7a7a7a';
    return '#000000';
  };

  const primaryMetric = metrics[0];
  const scatterPoints = rowData
    .map((row) => ({
      x: row.rank,
      y: row.metricValues[0],
      ticker: row.ticker,
      risk: row.risk,
    }))
    .filter((point) => Number.isFinite(point.y));

  const scatterCtx = scatterCanvas.getContext('2d');
  if (!scatterCtx) return;
  new window.Chart(scatterCtx, {
    type: 'scatter',
    data: {
      datasets: [
        {
          label: `${primaryMetric.label} por rank`,
          data: scatterPoints,
          backgroundColor: scatterPoints.map((point) => riskColor(point.risk)),
          borderColor: '#000000',
          borderWidth: 1,
          pointRadius: 4,
          pointHoverRadius: 5,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const item = ctx.raw ?? {};
              return `${item.ticker} · rank ${item.x} · ${primaryMetric.label}: ${Number(item.y).toFixed(2)}`;
            },
          },
        },
      },
      scales: {
        x: { title: { display: true, text: 'Rank (1 = melhor)' }, ticks: { precision: 0 } },
        y: { title: { display: true, text: primaryMetric.label } },
      },
    },
  });

  const metricSorted = metrics.map((metric, metricIndex) => {
    const values = rowData.map((row) => row.metricValues[metricIndex]).filter((value) => Number.isFinite(value));
    return { metric, values: values.sort((a, b) => a - b) };
  });

  heatmapHead.innerHTML = `
    <tr>
      <th>Rank</th>
      <th>Ticker</th>
      ${metrics.map((metric) => `<th>${metric.label}</th>`).join('')}
    </tr>
  `;

  heatmapBody.innerHTML = rowData
    .map((row) => {
      const cells = row.metricValues
        .map((value, metricIndex) => {
          if (!Number.isFinite(value)) {
            return '<td class="quant-cell quant-cell-empty">N/D</td>';
          }
          const { metric, values } = metricSorted[metricIndex];
          const base = percentile(value, values);
          const oriented = inferMetricPreference(metric) === 'lower' ? 1 - base : base;
          const opacity = 0.15 + oriented * 0.75;
          return `<td class="quant-cell" style="--intensity:${opacity.toFixed(2)}">${value.toFixed(2)}</td>`;
        })
        .join('');
      return `<tr><td>${row.rank}</td><td>${row.ticker}</td>${cells}</tr>`;
    })
    .join('');

  const pickerOptions = rowData
    .slice(0, Math.min(rowData.length, 30))
    .map((row) => `<option value="${row.ticker}">#${row.rank} · ${row.ticker}</option>`)
    .join('');
  picker.innerHTML = pickerOptions;

  let contributionChart = null;
  const renderContribution = (ticker) => {
    const selected = rowData.find((row) => row.ticker === ticker) ?? rowData[0];
    if (!selected) return;
    const scores = selected.metricValues.map((value, metricIndex) => {
      if (!Number.isFinite(value)) return 0;
      const { metric, values } = metricSorted[metricIndex];
      const base = percentile(value, values);
      const oriented = inferMetricPreference(metric) === 'lower' ? 1 - base : base;
      return Math.max(0, Math.min(1, oriented));
    });

    if (contributionChart) {
      contributionChart.destroy();
    }
    const contribCtx = contributionCanvas.getContext('2d');
    if (!contribCtx) return;
    contributionChart = new window.Chart(contribCtx, {
      type: 'bar',
      data: {
        labels: metrics.map((metric) => metric.label),
        datasets: [
          {
            data: scores.map((score) => score * 100),
            backgroundColor: ['#111111', '#6e6e6e', '#ff3000'],
            borderColor: '#000000',
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, max: 100, ticks: { callback: (v) => `${v}%` } },
        },
      },
    });

    const meanScore = scores.reduce((acc, value) => acc + value, 0) / Math.max(1, scores.length);
    contributionText.textContent = `${selected.ticker}: força média ${Math.round(meanScore * 100)}% nas métricas da estratégia (normalizado no universo exibido).`;
  };

  picker.addEventListener('change', (event) => {
    renderContribution(event.target.value);
  });
  renderContribution(rowData[0].ticker);
}

function metricConfigFor(strategyId) {
  const defaults = [
    { label: 'EV/EBIT', path: ['Indicadores fundamentalistas', 'EV / EBIT'] },
    { label: 'ROIC', path: ['Oscilações', 'ROIC'] },
    { label: 'DY', path: ['Indicadores fundamentalistas', 'Div. Yield'] },
  ];

  const byStrategy = {
    acquirers: [
      { label: 'EV/EBITDA', path: ['Indicadores fundamentalistas', 'EV / EBITDA'] },
      { label: 'Dív/PL', path: ['Dív.Brut/ Patrim.'] },
      { label: 'Rank', path: ["Rank Acquirer's Multiple"] },
    ],
    bazin: [
      { label: 'DY', path: ['Indicadores fundamentalistas', 'Div. Yield'] },
      { label: 'Dív/PL', path: ['Dív.Brut/ Patrim.'] },
      { label: 'Rank', path: ['Rank Bazin'] },
    ],
    cashrich: [
      { label: 'Caixa/MktCap', path: ['Cash / Market Cap'] },
      { label: 'Dív/PL', path: ['Dív.Brut/ Patrim.'] },
      { label: 'Rank', path: ['Rank Cash-Rich'] },
    ],
    cdv: [
      { label: 'EV/EBIT', path: ['Indicadores fundamentalistas', 'EV / EBIT'] },
      { label: 'Marg. EBIT', path: ['Oscilações', 'Marg. EBIT'] },
      { label: 'Rank', path: ['Rank EV / EBIT'] },
    ],
    contrarian: [
      { label: 'Dist. mínima 52w', path: ['Above 52w Low'] },
      { label: 'DY', path: ['Indicadores fundamentalistas', 'Div. Yield'] },
      { label: 'Rank', path: ['Rank Contrarian'] },
    ],
    deepvalue: [
      { label: 'P/L', path: ['Indicadores fundamentalistas', 'P/L'] },
      { label: 'P/VP', path: ['Indicadores fundamentalistas', 'P/VP'] },
      { label: 'Rank', path: ['Rank Deep Value'] },
    ],
    garp: [
      { label: 'PEG', path: ['PEG Ratio'] },
      { label: 'Cresc. 5a', path: ['Oscilações', 'Cres. Rec (5a)'] },
      { label: 'Rank', path: ['Rank GARP'] },
    ],
    graham: [
      { label: 'Graham Number', path: ['Graham Number'] },
      { label: 'Margem de segurança', path: ['Margin of Safety'] },
      { label: 'P/L', path: ['Indicadores fundamentalistas', 'P/L'] },
    ],
    intersection: [
      { label: 'Rank EV/EBIT', path: ['Rank EV / EBIT'] },
      { label: 'ROIC', path: ['Oscilações', 'ROIC'] },
      { label: 'DY', path: ['Indicadores fundamentalistas', 'Div. Yield'] },
    ],
    magicformula: [
      { label: 'EV/EBIT rank', path: ['Rank EV / EBIT'] },
      { label: 'ROIC rank', path: ['Rank ROIC'] },
      { label: 'Score', path: ['Rank Magic Formula'] },
    ],
    momentum_value: [
      { label: 'Momentum rank', path: ['Rank Momentum'] },
      { label: 'P/VP rank', path: ['Rank P/VP'] },
      { label: 'Score', path: ['Rank Momentum+Value'] },
    ],
    multifactor: [
      { label: 'Rank Value', path: ['Rank Value'] },
      { label: 'Rank Quality', path: ['Rank Quality'] },
      { label: 'Score', path: ['Rank Multi-Factor'] },
    ],
    netnet: [
      { label: 'NCAV/ação', path: ['NCAV per Share'] },
      { label: 'Desconto NCAV', path: ['NCAV Discount'] },
      { label: 'P/VP', path: ['Indicadores fundamentalistas', 'P/VP'] },
    ],
    piotroski: [
      { label: 'F-Score', path: ['F-Score'] },
      { label: 'ROE', path: ['Oscilações', 'ROE'] },
      { label: 'Rank', path: ['Rank Piotroski'] },
    ],
    quality: [
      { label: 'ROIC rank', path: ['Rank ROIC'] },
      { label: 'Marg. líq rank', path: ['Rank Marg. Líquida'] },
      { label: 'Score', path: ['Rank Quality'] },
    ],
    buffett: [
      { label: 'ROE', path: ['ROE'] },
      { label: 'Marg. Líquida', path: ['Marg. Líquida'] },
      { label: 'Rank', path: ['Rank Buffett'] },
    ],
    consensus: [
      { label: 'Aparições', path: ['Appearances'] },
      { label: 'Total estratégias', path: ['Strategy Count'] },
      { label: 'Rank', path: ['Rank Consensus'] },
    ],
    earnings_yield_spread: [
      { label: 'EY', path: ['Earnings Yield'] },
      { label: 'Spread', path: ['EY Spread'] },
      { label: 'Rank', path: ['Rank EY Spread'] },
    ],
    fortress: [
      { label: 'Liq. Corrente', path: ['Liquidez Corr'] },
      { label: 'Dív/PL', path: ['Div Br/ Patrim'] },
      { label: 'Rank', path: ['Rank Fortress'] },
    ],
    margin_compression: [
      { label: 'Marg. Bruta', path: ['Marg. Bruta'] },
      { label: 'Marg. EBIT', path: ['Marg. EBIT'] },
      { label: 'Gap', path: ['Margin Gap'] },
    ],
    redflags: [
      { label: 'Red Flags', path: ['Red Flags'] },
      { label: 'Rank', path: ['Rank Red Flags'] },
      { label: 'DY', path: ['Indicadores fundamentalistas', 'Div. Yield'] },
    ],
    volatility_adjusted: [
      { label: 'EV/EBIT', path: ['EV/EBIT'] },
      { label: 'Volatilidade 52w', path: ['52w Volatility'] },
      { label: 'VA Score', path: ['VA Score'] },
    ],
    working_capital: [
      { label: 'P/Cap. Giro', path: ['P/Cap. Giro'] },
      { label: 'P/Ativ Circ Liq', path: ['P/Ativ Circ Liq'] },
      { label: 'Rank', path: ['Rank Working Capital'] },
    ],
    altman: [
      { label: 'Z-Score', path: ['Z-Score'] },
      { label: 'Rank', path: ['Rank Altman Z'] },
      { label: 'EV/EBIT', path: ['Indicadores fundamentalistas', 'EV / EBIT'] },
    ],
    assetlight: [
      { label: 'ROIC', path: ['Oscilações', 'ROIC'] },
      { label: 'Giro Ativos', path: ['Oscilações', 'Giro Ativos'] },
      { label: 'Rank', path: ['Rank Asset-Light'] },
    ],
    bookvalue: [
      { label: 'P/VP', path: ['P/VP'] },
      { label: 'Desconto', path: ['Book Value Discount'] },
      { label: 'Rank', path: ['Rank Book Value'] },
    ],
    dupont: [
      { label: 'Marg. Líquida', path: ['Marg. Líquida'] },
      { label: 'Giro Ativos', path: ['Giro Ativos'] },
      { label: 'Rank', path: ['Rank DuPont'] },
    ],
    earnings_accel: [
      { label: 'EA Ratio', path: ['EA Ratio'] },
      { label: 'Rank', path: ['Rank EA'] },
      { label: 'ROIC', path: ['Oscilações', 'ROIC'] },
    ],
    largecap_dividend: [
      { label: 'DY', path: ['Indicadores fundamentalistas', 'Div. Yield'] },
      { label: 'Valor de mercado', path: ['Valor de mercado'] },
      { label: 'Rank', path: ['Rank Large-Cap DY'] },
    ],
    sector_relative: [
      { label: 'EV/EBIT', path: ['Indicadores fundamentalistas', 'EV / EBIT'] },
      { label: 'Setor', path: ['Setor'] },
      { label: 'Rank setor', path: ['Rank Sector Relative'] },
    ],
    smallcap_value: [
      { label: 'EV/EBIT', path: ['Indicadores fundamentalistas', 'EV / EBIT'] },
      { label: 'Valor de mercado', path: ['Valor de mercado'] },
      { label: 'Rank', path: ['Rank Small-Cap Value'] },
    ],
  };

  return byStrategy[strategyId] ?? defaults;
}

export function renderIntelligence(section, statsEl, highBody, allBody, intelligence) {
  if (!intelligence?.anomalies) {
    section.style.display = 'none';
    return;
  }

  section.style.display = '';
  const a = intelligence.anomalies;

  statsEl.innerHTML = `
    <div class="intel-stat">
      <span class="intel-stat-num">${a.total}</span>
      <span class="intel-stat-label">Anomalias detectadas</span>
    </div>
    <div class="intel-stat intel-stat-high">
      <span class="intel-stat-num">${a.severity_counts?.high ?? 0}</span>
      <span class="intel-stat-label">Alta severidade</span>
    </div>
    <div class="intel-stat intel-stat-medium">
      <span class="intel-stat-num">${a.severity_counts?.medium ?? 0}</span>
      <span class="intel-stat-label">Média severidade</span>
    </div>
    <div class="intel-stat intel-stat-low">
      <span class="intel-stat-num">${a.severity_counts?.low ?? 0}</span>
      <span class="intel-stat-label">Baixa severidade</span>
    </div>
  `;

  const renderAnomalyRow = (ticker, entry) => {
    const sev = entry.severity;
    const sevClass = sev === 'high' ? 'anomaly-high' : sev === 'medium' ? 'anomaly-medium' : 'anomaly-low';
    const details = entry.flags
      .slice(0, 4)
      .map((f) => {
        const value = f.value !== undefined ? ` (${typeof f.value === 'number' ? f.value.toFixed(4) : f.value})` : '';
        return `${f.description || f.metric}${value}`;
      })
      .join('; ');
    const extra = entry.flags.length > 4 ? ` +${entry.flags.length - 4} mais` : '';
    const fontes = entry.fontes || {};
    return `
      <tr>
        <td>
          <div class="ticker-cell">
            ${logoMarkup(ticker)}
            <span>${ticker}</span>
          </div>
        </td>
        <td>${entry.sector ?? '-'}</td>
        <td><span class="anomaly-badge ${sevClass}">${sev.toUpperCase()}</span></td>
        <td>${entry.flag_count}</td>
        <td class="anomaly-details">${details}${extra}</td>
        <td class="source-links-cell">${sourceLinksMarkup(fontes)}</td>
      </tr>
    `;
  };

  const entries = Object.entries(a.by_ticker);

  const highEntries = entries.filter(([, e]) => e.severity === 'high');
  highBody.innerHTML = highEntries.map(([ticker, e]) => renderAnomalyRow(ticker, e)).join('');

  const restEntries = entries.filter(([, e]) => e.severity !== 'high');
  allBody.innerHTML = restEntries.map(([ticker, e]) => renderAnomalyRow(ticker, e)).join('');

  const wrapEl = highBody.closest('.intel-table-wrap');
  if (wrapEl) wrapEl.style.display = '';

  ensureUiEnhancements(section);
}

function sourceLinksMarkup(fontes) {
  if (!fontes || typeof fontes !== 'object') return '';
  const icons = {
    Fundamentus: 'F',
    StatusInvest: 'SI',
    Investidor10: 'I10',
    'Yahoo Finance': 'Y',
    'Google Finance': 'G',
    TradingView: 'TV',
  };
  return Object.entries(fontes)
    .map(([name, url]) => {
      const short = icons[name] ?? name.slice(0, 2);
      return `<a href="${url}" target="_blank" rel="noopener" class="source-link" title="${name}">${short}</a>`;
    })
    .join(' ');
}

function anomalyBadge(ticker, intelligence) {
  if (!intelligence?.anomalies?.by_ticker) return '';
  const entry = intelligence.anomalies.by_ticker[ticker];
  if (!entry) return '';
  const cls =
    entry.severity === 'high'
      ? 'anomaly-high'
      : entry.severity === 'medium'
        ? 'anomaly-medium'
        : 'anomaly-low';
  const title = entry.flags
    .slice(0, 3)
    .map((f) => f.description || f.metric)
    .join('; ');
  return `<span class="anomaly-badge ${cls}" title="${title}">${entry.flag_count}<i data-lucide="alert-triangle"></i></span>`;
}

function createDetailPanel(strategy, displayLimit, intelligence) {
  const panel = document.createElement('section');
  panel.className = 'strategy-detail-panel';
  const metricSet = metricConfigFor(strategy.strategy_id);
  const formulaLatex = strategy.formula_latex ?? '\\text{Fórmula indisponível para esta estratégia.}';
  const maxRows = displayLimit === 'ALL' ? strategy.stocks.length : Number(displayLimit);
  const visibleStocks = strategy.stocks.slice(0, maxRows);

  const rows = visibleStocks
    .map((stock, index) => {
      const risk = evaluateRisk(stock);
      const company = stock.Empresa ?? '-';
      const sector = stock.Setor ?? '-';
      const metricText = metricSet.map((metric) => readMetric(stock, metric)).join(' | ');
      const ticker = stock.Papel ?? '-';

      return `
        <tr>
          <td>${index + 1}/${strategy.result_size}</td>
          <td>
            <div class="ticker-cell">
              ${logoMarkup(ticker)}
              <span>${ticker}</span>
              ${anomalyBadge(ticker, intelligence)}
            </div>
          </td>
          <td>${company}</td>
          <td>${sector}</td>
          <td>${metricText}</td>
          <td><span class="risk-badge ${riskClass(risk.risk_level)}">${risk.risk_level}</span></td>
          <td class="source-links-cell">${sourceLinksMarkup(stock.Fontes)}</td>
        </tr>
      `;
    })
    .join('');

  panel.innerHTML = `
    <div class="detail-header">
      <h3><i data-lucide="layout-panel-top"></i> ${strategy.name}</h3>
      <button class="btn" data-action="close-detail"><i data-lucide="x"></i> Fechar</button>
    </div>
    <div class="detail-split">
      <aside class="detail-context swiss-grid-pattern">
        <p class="section-label">03. CONTEXTO</p>
        <p><i data-lucide="info"></i> ${strategy.description}</p>
        <p><i data-lucide="list-filter"></i> ${strategy.methodology_summary}</p>
        <div class="formula-box">
          <p class="formula-title"><i data-lucide="sigma"></i> Fórmula da estratégia</p>
          <div class="formula-latex">\\[${formulaLatex}\\]</div>
        </div>
        <p><strong>Filtradas:</strong> ${strategy.filtered_size} | <strong>Rankeadas:</strong> ${strategy.result_size}</p>
        <p><strong>Exibindo:</strong> ${visibleStocks.length} de ${strategy.result_size}</p>
        <p><strong>Quando usar:</strong> ${strategy.use_cases.join(' · ')}</p>
        <p><strong>Caveats:</strong> ${strategy.caveats.join(' · ')}</p>
      </aside>
      <section class="detail-table-wrap">
        <p class="section-label">04. TOP PICKS</p>
        <div class="table-scroll">
          <table class="stocks-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Ticker</th>
                <th>Empresa</th>
                <th>Setor</th>
                <th>Métricas-chave</th>
                <th>Risco</th>
                <th>Fontes</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </section>
    </div>
    <section class="risk-visual-box risk-visual-wide is-collapsed">
      <div class="risk-visual-head">
        <p class="formula-title"><i data-lucide="shield-alert"></i> Faixas de risco esperadas</p>
        <button class="btn risk-toggle-btn" data-action="toggle-risk" aria-expanded="false">
          <i data-lucide="pie-chart"></i>
          <span class="risk-toggle-label">Mostrar gráficos</span>
          <i class="risk-toggle-chevron" data-lucide="chevron-down"></i>
        </button>
      </div>
      <div class="risk-charts">
        <div class="risk-chart-pane risk-chart-pane-pie">
          <canvas class="risk-mix-chart" aria-label="Mix de risco da estratégia"></canvas>
        </div>
        <div class="risk-chart-pane risk-chart-pane-band">
          <canvas class="risk-band-chart" aria-label="Faixa de risco estimada"></canvas>
        </div>
      </div>
      <p class="muted risk-band-text"></p>
    </section>
    <section class="quant-visual-box is-collapsed">
      <div class="quant-head">
        <p class="formula-title"><i data-lucide="chart-scatter"></i> Análise quantitativa por rank</p>
        <button class="btn quant-toggle-btn" data-action="toggle-quant" aria-expanded="false">
          <i data-lucide="chart-column"></i>
          <span class="quant-toggle-label">Mostrar análise</span>
          <i class="quant-toggle-chevron" data-lucide="chevron-down"></i>
        </button>
      </div>
      <div class="quant-grid">
        <article class="quant-panel">
          <p class="quant-title">Rank vs métrica principal</p>
          <div class="quant-canvas-wrap">
            <canvas class="quant-scatter-chart" aria-label="Dispersão rank por métrica"></canvas>
          </div>
        </article>
        <article class="quant-panel">
          <div class="quant-title-row">
            <p class="quant-title">Contribuição relativa por ação</p>
            <select class="quant-stock-picker" aria-label="Selecionar ação para contribuição"></select>
          </div>
          <div class="quant-canvas-wrap">
            <canvas class="quant-contrib-chart" aria-label="Contribuições da ação"></canvas>
          </div>
          <p class="muted quant-contrib-text"></p>
        </article>
      </div>
      <article class="quant-panel quant-heatmap-panel">
        <p class="quant-title"><i data-lucide="table"></i> Heatmap de métricas (ordenado por rank)</p>
        <div class="table-scroll quant-scroll">
          <table class="stocks-table quant-heatmap-table">
            <thead class="quant-heatmap-head"></thead>
            <tbody class="quant-heatmap-body"></tbody>
          </table>
        </div>
      </article>
    </section>
  `;

  return panel;
}

export function renderStrategies(
  container,
  strategies,
  activeStrategyId,
  displayLimit,
  onOpenDetail,
  onCloseDetail,
  onCompare,
  onCopyTopN,
  intelligence,
  comparedStrategies,
  onTickerClick
) {
  container.innerHTML = '';

  for (const strategy of strategies) {
    const card = document.createElement('article');
    card.className = 'strategy-card swiss-grid-pattern';
    card.id = `strategy-card-${strategy.strategy_id}`;
    card.dataset.strategyId = strategy.strategy_id;

    const picks = topPicks(strategy.stocks, 5);

    // Compute card stats
    const catId = categoryForStrategy(strategy.strategy_id);
    const metrics = catId ? categoryMetrics(catId) : categoryMetrics('compostas');
    const visibleCount = displayLimit === 'ALL' ? strategy.stocks.length : Math.min(strategy.stocks.length, Number(displayLimit));
    const visibleStocks = strategy.stocks.slice(0, visibleCount);

    const avgMetrics = metrics.map((metric) => {
      const values = visibleStocks
        .map((stock) => {
          const raw = getPathValue(stock, metric.path);
          return asNumber(raw, null);
        })
        .filter((v) => v !== null && Number.isFinite(v));
      const avg = values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : null;
      return { label: metric.label, avg };
    });

    const riskProfile = computeRiskProfile(visibleStocks);
    const total = visibleStocks.length || 1;
    const lowPct = ((riskProfile.counts.BAIXO / total) * 100).toFixed(0);
    const medPct = ((riskProfile.counts['MÉDIO'] / total) * 100).toFixed(0);
    const highPct = ((riskProfile.counts.ALTO / total) * 100).toFixed(0);

    const avgMetricsHtml = avgMetrics
      .map((m) => {
        const val = m.avg !== null ? m.avg.toFixed(2) : 'N/D';
        return `<span class="card-stat"><span class="card-stat-value">${val}</span> <span class="card-stat-label">${m.label}</span></span>`;
      })
      .join('');

    const isCompared = comparedStrategies?.has(strategy.strategy_id);
    const compareBtnClass = isCompared ? 'btn active' : 'btn';

    const topPicksHtml = onTickerClick
      ? picks
          .map(
            (ticker) => `
            <span class="top-pick-pill ticker-link" data-ticker="${ticker}">
              ${logoMarkup(ticker, 'top-pick-logo', 'top-pick-fallback')}
              <span>${ticker}</span>
            </span>
          `
          )
          .join('')
      : topPickPillsMarkup(picks);

    card.innerHTML = `
      <header class="card-head">
        <p class="section-label">ESTRATÉGIA</p>
        <h2>${strategy.name}</h2>
        <p class="card-desc">${strategy.description}</p>
      </header>
      <div class="card-stats">
        <span class="card-stat"><span class="card-stat-value">${visibleCount}</span> <span class="card-stat-label">ações</span></span>
        ${avgMetricsHtml}
        <span class="card-stat">
          <div class="card-risk-bar">
            <div class="bar-low" style="flex:${lowPct}"></div>
            <div class="bar-med" style="flex:${medPct}"></div>
            <div class="bar-high" style="flex:${highPct}"></div>
          </div>
          <span class="card-stat-label">${riskProfile.profile}</span>
        </span>
      </div>
      <div class="card-meta">
        <p><strong>Filtradas:</strong> ${strategy.filtered_size} | <strong>Rankeadas:</strong> ${strategy.result_size}</p>
        <p><strong>Exibindo:</strong> ${displayLimit === 'ALL' ? strategy.result_size : Math.min(strategy.result_size, displayLimit)} de ${strategy.result_size}</p>
        <p class="top-picks-line">
          <strong>Top 5:</strong>
          <span class="top-picks-list">${topPicksHtml}</span>
        </p>
      </div>
      <footer class="card-actions">
        <button class="btn btn-accent" data-action="detail" data-id="${strategy.strategy_id}">
          <i data-lucide="table-properties"></i> Ver detalhes
        </button>
        <button class="${compareBtnClass}" data-action="compare" data-id="${strategy.strategy_id}">
          <i data-lucide="git-merge"></i> Comparar
        </button>
        <button class="btn" data-action="copy-topn" data-id="${strategy.strategy_id}">
          <i class="copy-icon copy-icon-default" data-lucide="copy"></i>
          <i class="copy-icon copy-icon-success" data-lucide="check"></i>
          <i class="copy-icon copy-icon-fail" data-lucide="x"></i>
          <span class="copy-btn-label">Copiar Top N</span>
        </button>
      </footer>
    `;

    card.addEventListener('click', () => {
      onOpenDetail(strategy.strategy_id);
    });

    // Make top pick pills clickable
    if (onTickerClick) {
      card.querySelectorAll('.top-pick-pill.ticker-link').forEach((el) => {
        el.addEventListener('click', (event) => {
          event.stopPropagation();
          onTickerClick(el.dataset.ticker);
        });
      });
    }

    card.querySelector('[data-action="detail"]')?.addEventListener('click', (event) => {
      event.stopPropagation();
      onOpenDetail(strategy.strategy_id);
    });

    card.querySelector('[data-action="compare"]')?.addEventListener('click', (event) => {
      event.stopPropagation();
      onCompare(strategy.strategy_id);
    });
    card.querySelector('[data-action="copy-topn"]')?.addEventListener('click', (event) => {
      event.stopPropagation();
      const button = event.currentTarget;
      Promise.resolve(onCopyTopN(strategy.strategy_id))
        .then((copied) => {
          flashCopyButton(button, Boolean(copied));
        })
        .catch(() => {
          flashCopyButton(button, false);
        });
    });

    container.appendChild(card);

    if (activeStrategyId === strategy.strategy_id) {
      const panel = createDetailPanel(strategy, displayLimit, intelligence);
      panel.querySelector('[data-action="close-detail"]')?.addEventListener('click', () => {
        onCloseDetail();
      });
      panel.querySelector('[data-action="toggle-risk"]')?.addEventListener('click', (event) => {
        const button = event.currentTarget;
        const section = panel.querySelector('.risk-visual-wide');
        const label = panel.querySelector('.risk-toggle-label');
        if (!button || !section || !label) return;

        const isExpanded = button.getAttribute('aria-expanded') === 'true';
        const nextExpanded = !isExpanded;
        button.setAttribute('aria-expanded', String(nextExpanded));
        label.textContent = nextExpanded ? 'Ocultar gráficos' : 'Mostrar gráficos';
        section.classList.toggle('is-collapsed', !nextExpanded);

        if (nextExpanded && panel.dataset.riskRendered !== 'true') {
          renderStrategyRiskVisual(panel, strategy, displayLimit);
          panel.dataset.riskRendered = 'true';
        }
      });
      panel.querySelector('[data-action="toggle-quant"]')?.addEventListener('click', (event) => {
        const button = event.currentTarget;
        const section = panel.querySelector('.quant-visual-box');
        const label = panel.querySelector('.quant-toggle-label');
        if (!button || !section || !label) return;

        const isExpanded = button.getAttribute('aria-expanded') === 'true';
        const nextExpanded = !isExpanded;
        button.setAttribute('aria-expanded', String(nextExpanded));
        label.textContent = nextExpanded ? 'Ocultar análise' : 'Mostrar análise';
        section.classList.toggle('is-collapsed', !nextExpanded);

        if (nextExpanded && panel.dataset.quantRendered !== 'true') {
          renderStrategyQuantVisual(panel, strategy, displayLimit);
          panel.dataset.quantRendered = 'true';
        }
      });
      container.appendChild(panel);
    }
  }

  ensureUiEnhancements(container);
}


export function renderConsensusPicks(container, picks, strategyCount, intelligence, onTickerClick) {
  container.innerHTML = '';

  if (!picks.length) {
    container.innerHTML = '<p class="muted">Sem consenso relevante com os filtros atuais.</p>';
    return;
  }

  for (const pick of picks) {
    const card = document.createElement('article');
    card.className = 'consensus-card';
    const coverage = ((pick.count / strategyCount) * 100).toFixed(0);
    const topStrategies = pick.strategies.slice(0, 4).join(', ');
    const sector = pick.sample?.Setor ?? 'Setor não informado';

    const fontes = pick.sample?.Fontes;

    const tickerHtml = onTickerClick
      ? `<span class="ticker-link" data-ticker="${pick.ticker}">${pick.ticker}</span>`
      : `<span>${pick.ticker}</span>`;

    card.innerHTML = `
      <h3 class="ticker-title">
        ${logoMarkup(pick.ticker)}
        ${tickerHtml}
        ${anomalyBadge(pick.ticker, intelligence)}
      </h3>
      <p class="muted">${sector}</p>
      <p><strong>${pick.count}</strong> estratégias (${coverage}% do total)</p>
      <p class="muted">Presente em: ${topStrategies}${pick.strategies.length > 4 ? '…' : ''}</p>
      <div class="consensus-sources">${sourceLinksMarkup(fontes)}</div>
    `;

    if (onTickerClick) {
      card.querySelector('.ticker-link')?.addEventListener('click', (event) => {
        event.stopPropagation();
        onTickerClick(pick.ticker);
      });
    }

    container.appendChild(card);
  }

  ensureUiEnhancements(container);
}

export function renderComparison(
  container,
  strategies,
  mode,
  resultTickers,
  stockMap,
  fullStockMap,
  displayLimit,
  onModeChange,
  onClose,
  onTickerClick
) {
  container.innerHTML = '';

  // Collect all ticker sets for overlap detection
  const allTickerSets = strategies.map((s) => {
    const max = displayLimit === 'ALL' ? s.stocks.length : Number(displayLimit);
    return new Set(s.stocks.slice(0, max).map((st) => st.Papel).filter(Boolean));
  });

  // Header
  const header = document.createElement('div');
  header.className = 'comparison-header';
  header.innerHTML = `
    <h2><i data-lucide="git-merge"></i> Comparação de Estratégias</h2>
    <button class="btn" data-action="close-comparison"><i data-lucide="x"></i> Fechar</button>
  `;
  header.querySelector('[data-action="close-comparison"]')?.addEventListener('click', onClose);
  container.appendChild(header);

  // Strategy columns
  const columns = document.createElement('div');
  columns.className = 'comparison-columns';

  for (const strategy of strategies) {
    const col = document.createElement('div');
    col.className = 'comparison-col';
    const catId = categoryForStrategy(strategy.strategy_id);
    const catLabel = catId ?? 'outro';

    const max = displayLimit === 'ALL' ? strategy.stocks.length : Number(displayLimit);
    const visible = strategy.stocks.slice(0, max);

    // Avg metrics
    const dyValues = visible.map((s) => asNumber(getPathValue(s, ['Indicadores fundamentalistas', 'Div. Yield']), null)).filter((v) => v !== null && Number.isFinite(v));
    const plValues = visible.map((s) => asNumber(getPathValue(s, ['Indicadores fundamentalistas', 'P/L']), null)).filter((v) => v !== null && Number.isFinite(v));
    const roicValues = visible.map((s) => asNumber(getPathValue(s, ['Oscilações', 'ROIC']), null)).filter((v) => v !== null && Number.isFinite(v));
    const avgDY = dyValues.length ? (dyValues.reduce((a, b) => a + b, 0) / dyValues.length).toFixed(2) : 'N/D';
    const avgPL = plValues.length ? (plValues.reduce((a, b) => a + b, 0) / plValues.length).toFixed(2) : 'N/D';
    const avgROIC = roicValues.length ? (roicValues.reduce((a, b) => a + b, 0) / roicValues.length).toFixed(2) : 'N/D';

    // Risk bar
    const riskProfile = computeRiskProfile(visible);
    const total = visible.length || 1;
    const lowPct = ((riskProfile.counts.BAIXO / total) * 100).toFixed(0);
    const medPct = ((riskProfile.counts['MÉDIO'] / total) * 100).toFixed(0);
    const highPct = ((riskProfile.counts.ALTO / total) * 100).toFixed(0);

    // Top 5 tickers with overlap markers
    const top5 = visible.slice(0, 5).map((s) => s.Papel).filter(Boolean);
    const top5Html = top5.map((ticker) => {
      const inOtherStrategies = allTickerSets.filter((set) => set.has(ticker)).length;
      const isOverlap = inOtherStrategies > 1;
      const cls = isOverlap ? 'comparison-ticker overlap ticker-link' : 'comparison-ticker ticker-link';
      return `<span class="${cls}" data-ticker="${ticker}">${ticker}</span>`;
    }).join('');

    col.innerHTML = `
      <h3>${strategy.name}</h3>
      <p class="comparison-category">${catLabel}</p>
      <div class="comparison-stat"><span>Ações</span><span class="comparison-stat-value">${visible.length}</span></div>
      <div class="comparison-stat"><span>DY médio</span><span class="comparison-stat-value">${avgDY}</span></div>
      <div class="comparison-stat"><span>P/L médio</span><span class="comparison-stat-value">${avgPL}</span></div>
      <div class="comparison-stat"><span>ROIC médio</span><span class="comparison-stat-value">${avgROIC}</span></div>
      <div class="comparison-risk-bar">
        <div class="bar-low" style="flex:${lowPct}"></div>
        <div class="bar-med" style="flex:${medPct}"></div>
        <div class="bar-high" style="flex:${highPct}"></div>
      </div>
      <div style="margin-top:0.35rem">${top5Html}</div>
    `;

    if (onTickerClick) {
      col.querySelectorAll('.ticker-link').forEach((el) => {
        el.addEventListener('click', () => onTickerClick(el.dataset.ticker));
      });
    }

    columns.appendChild(col);
  }
  container.appendChild(columns);

  // Result section
  const result = document.createElement('div');
  result.className = 'comparison-result';

  const modeLabel = mode === 'AND' ? 'Interseção' : 'União';
  const resultTickerHtml = resultTickers.map((ticker) => {
    return `<span class="comparison-ticker ticker-link" data-ticker="${ticker}">${ticker}</span>`;
  }).join('');

  result.innerHTML = `
    <h3>${modeLabel}: ${resultTickers.length} ações</h3>
    <div class="comparison-controls">
      <label>Modo:</label>
      <select id="comparison-mode-select">
        <option value="AND" ${mode === 'AND' ? 'selected' : ''}>AND (interseção)</option>
        <option value="OR" ${mode === 'OR' ? 'selected' : ''}>OR (união)</option>
      </select>
    </div>
    <div>${resultTickerHtml || '<span class="muted">Nenhum ativo encontrado.</span>'}</div>
  `;

  result.querySelector('#comparison-mode-select')?.addEventListener('change', (event) => {
    onModeChange(event.target.value);
  });

  if (onTickerClick) {
    result.querySelectorAll('.ticker-link').forEach((el) => {
      el.addEventListener('click', () => onTickerClick(el.dataset.ticker));
    });
  }

  container.appendChild(result);
  ensureUiEnhancements(container);
}

export function renderTickerProfile(container, tickerEntry, intelligence, onClose, onTickerClick) {
  container.innerHTML = '';

  const { ticker, company, sector, sample, fontes, appearances } = tickerEntry;
  const risk = evaluateRisk(sample);

  // Metrics
  const pl = asNumber(getPathValue(sample, ['Indicadores fundamentalistas', 'P/L']), null);
  const pvp = asNumber(getPathValue(sample, ['Indicadores fundamentalistas', 'P/VP']), null);
  const dy = asNumber(getPathValue(sample, ['Indicadores fundamentalistas', 'Div. Yield']), null);
  const roic = asNumber(getPathValue(sample, ['Oscilações', 'ROIC']), null);
  const margEbit = asNumber(getPathValue(sample, ['Oscilações', 'Marg. EBIT']), null);

  const fmt = (v) => (v !== null && Number.isFinite(v) ? v.toFixed(2) : 'N/D');

  const metricsHtml = [
    { label: 'P/L', value: fmt(pl) },
    { label: 'P/VP', value: fmt(pvp) },
    { label: 'DY', value: fmt(dy) },
    { label: 'ROIC', value: fmt(roic) },
    { label: 'Marg. EBIT', value: fmt(margEbit) },
    { label: 'Risco', value: risk.risk_level },
  ].map((m) => `
    <div class="ticker-metric">
      <span class="ticker-metric-value">${m.value}</span>
      <span class="ticker-metric-label">${m.label}</span>
    </div>
  `).join('');

  // Strategy appearances table
  const strategyRows = appearances.map((app) => {
    const catId = categoryForStrategy(app.strategy_id);
    return `<tr>
      <td>${app.strategy_name}</td>
      <td>${app.rank}/${app.total}</td>
      <td>${catId ?? '-'}</td>
    </tr>`;
  }).join('');

  // Anomaly summary
  let anomalyHtml = '';
  if (intelligence?.anomalies?.by_ticker) {
    const entry = intelligence.anomalies.by_ticker[ticker];
    if (entry) {
      const details = entry.flags
        .slice(0, 6)
        .map((f) => {
          const value = f.value !== undefined ? ` (${typeof f.value === 'number' ? f.value.toFixed(4) : f.value})` : '';
          return `${f.description || f.metric}${value}`;
        })
        .join('; ');
      anomalyHtml = `
        <div class="ticker-anomaly-summary">
          ${anomalyBadge(ticker, intelligence)}
          <span> ${entry.flag_count} anomalia(s): ${details}</span>
        </div>
      `;
    } else {
      anomalyHtml = `<div class="ticker-anomaly-summary ticker-anomaly-clean">Nenhuma anomalia detectada.</div>`;
    }
  }

  container.innerHTML = `
    <div class="ticker-profile-header">
      <button class="btn ticker-profile-back" data-action="back"><i data-lucide="arrow-left"></i> Voltar</button>
      ${logoMarkup(ticker, 'ticker-logo', 'ticker-fallback')}
      <h2>${ticker}</h2>
      <p class="muted">${company} - ${sector}</p>
    </div>
    <div class="consensus-sources" style="margin-bottom:0.75rem">${sourceLinksMarkup(fontes)}</div>
    <div class="ticker-metrics-grid">${metricsHtml}</div>
    <div class="ticker-strategies-table">
      <table class="stocks-table">
        <thead>
          <tr>
            <th>Estratégia</th>
            <th>Rank</th>
            <th>Categoria</th>
          </tr>
        </thead>
        <tbody>${strategyRows}</tbody>
      </table>
    </div>
    ${anomalyHtml}
  `;

  container.querySelector('[data-action="back"]')?.addEventListener('click', onClose);
  ensureUiEnhancements(container);
}
