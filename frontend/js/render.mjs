import { evaluateRisk } from './risk.mjs';

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
  };

  return byStrategy[strategyId] ?? defaults;
}

function createDetailPanel(strategy, displayLimit) {
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

      return `
        <tr>
          <td>${index + 1}/${strategy.result_size}</td>
          <td>
            <div class="ticker-cell">
              ${logoMarkup(stock.Papel ?? '-')}
              <span>${stock.Papel ?? '-'}</span>
            </div>
          </td>
          <td>${company}</td>
          <td>${sector}</td>
          <td>${metricText}</td>
          <td><span class="risk-badge ${riskClass(risk.risk_level)}">${risk.risk_level}</span></td>
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
  onCopyTopN
) {
  container.innerHTML = '';

  for (const strategy of strategies) {
    const card = document.createElement('article');
    card.className = 'strategy-card swiss-grid-pattern';
    card.id = `strategy-card-${strategy.strategy_id}`;
    card.dataset.strategyId = strategy.strategy_id;

    const picks = topPicks(strategy.stocks, 5);

    card.innerHTML = `
      <header class="card-head">
        <p class="section-label">ESTRATÉGIA</p>
        <h2>${strategy.name}</h2>
        <p class="card-desc">${strategy.description}</p>
      </header>
      <div class="card-meta">
        <p><strong>Filtradas:</strong> ${strategy.filtered_size} | <strong>Rankeadas:</strong> ${strategy.result_size}</p>
        <p><strong>Exibindo:</strong> ${displayLimit === 'ALL' ? strategy.result_size : Math.min(strategy.result_size, displayLimit)} de ${strategy.result_size}</p>
        <p class="top-picks-line">
          <strong>Top 5:</strong>
          <span class="top-picks-list">${topPickPillsMarkup(picks)}</span>
        </p>
      </div>
      <footer class="card-actions">
        <button class="btn btn-accent" data-action="detail" data-id="${strategy.strategy_id}">
          <i data-lucide="table-properties"></i> Ver detalhes
        </button>
        <button class="btn" data-action="compare" data-id="${strategy.strategy_id}">
          <i data-lucide="git-merge"></i> Interseção
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
      const panel = createDetailPanel(strategy, displayLimit);
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

export function renderStrategyIndex(container, strategies, activeStrategyId, onNavigate) {
  container.innerHTML = '';

  for (const strategy of strategies) {
    const button = document.createElement('button');
    const isActive = strategy.strategy_id === activeStrategyId;
    button.className = `strategy-index-item${isActive ? ' active' : ''}`;
    button.type = 'button';
    button.innerHTML = `
      <i data-lucide="navigation"></i>
      <span>${strategy.name}</span>
    `;
    button.addEventListener('click', () => {
      onNavigate(strategy.strategy_id);
    });
    container.appendChild(button);
  }

  ensureUiEnhancements(container);
}

export function renderCompareStrategyList(container, strategies, selected, onToggle) {
  container.innerHTML = '';

  for (const strategy of strategies) {
    const id = `strategy-${strategy.strategy_id}`;
    const row = document.createElement('label');
    row.className = 'check-row';
    row.innerHTML = `
      <input type="checkbox" id="${id}" ${selected.has(strategy.strategy_id) ? 'checked' : ''}>
      <span>${strategy.name}</span>
    `;

    row.querySelector('input')?.addEventListener('change', (event) => {
      onToggle(strategy.strategy_id, event.target.checked);
    });

    container.appendChild(row);
  }
}

export function renderConsensusPicks(container, picks, strategyCount) {
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

    card.innerHTML = `
      <h3 class="ticker-title">
        ${logoMarkup(pick.ticker)}
        <span>${pick.ticker}</span>
      </h3>
      <p class="muted">${sector}</p>
      <p><strong>${pick.count}</strong> estratégias (${coverage}% do total)</p>
      <p class="muted">Presente em: ${topStrategies}${pick.strategies.length > 4 ? '…' : ''}</p>
    `;

    container.appendChild(card);
  }

  ensureUiEnhancements(container);
}

export function renderIntersectionResults(container, tickers, stockMap, mode, selectedCount) {
  container.innerHTML = '';
  const modeLabel = mode === 'AND' ? 'interseção (AND)' : 'união (OR)';

  if (selectedCount === 0) {
    container.innerHTML =
      '<p class="muted">Selecione pelo menos uma estratégia para calcular a interseção/união.</p>';
    return;
  }

  if (mode === 'AND' && selectedCount < 2) {
    container.innerHTML =
      '<p class="muted">No modo AND, selecione 2+ estratégias para ver a interseção real.</p>';
    return;
  }

  if (tickers.length === 0) {
    container.innerHTML = `<p class="muted">Nenhum ativo encontrado para ${modeLabel} com a seleção atual.</p>`;
    return;
  }

  for (const ticker of tickers) {
    const stockEntry = stockMap.get(ticker);
    if (!stockEntry) continue;

    const risk = evaluateRisk(stockEntry.sample);
    const card = document.createElement('article');
    card.className = 'stock-row';

    card.innerHTML = `
      <div>
        <h3 class="ticker-title">
          ${logoMarkup(ticker)}
          <span>${ticker}</span>
        </h3>
        <p class="muted">Estratégias: ${stockEntry.strategies.join(', ')}</p>
      </div>
      <div class="stock-actions">
        <span class="risk-badge ${riskClass(risk.risk_level)}">${risk.risk_level}</span>
      </div>
    `;

    container.appendChild(card);
  }

  ensureUiEnhancements(container);
}
