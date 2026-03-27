import { evaluateRisk } from './risk.mjs';

function riskClass(level) {
  if (level === 'ALTO') return 'risk-high';
  if (level === 'MÉDIO') return 'risk-medium';
  return 'risk-low';
}

export function renderStrategies(container, strategies, onCompare) {
  container.innerHTML = '';

  for (const strategy of strategies) {
    const card = document.createElement('article');
    card.className = 'strategy-card swiss-grid-pattern';

    card.innerHTML = `
      <header class="card-head">
        <p class="section-label">ESTRATÉGIA</p>
        <h2>${strategy.name}</h2>
        <p class="card-desc">${strategy.description}</p>
      </header>
      <div class="card-meta">
        <p><strong>Quando usar:</strong> ${strategy.use_cases.join(' · ')}</p>
        <p><strong>Caveats:</strong> ${strategy.caveats.join(' · ')}</p>
        <p><strong>Resultados:</strong> ${strategy.result_size}</p>
      </div>
      <footer class="card-actions">
        <button class="btn btn-accent" data-action="compare" data-id="${strategy.strategy_id}">Comparar</button>
      </footer>
    `;

    card.querySelector('[data-action="compare"]')?.addEventListener('click', () => {
      onCompare(strategy.strategy_id);
    });

    container.appendChild(card);
  }
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

export function renderIntersectionResults(container, tickers, stockMap, onOpenDetail) {
  container.innerHTML = '';

  if (tickers.length === 0) {
    container.innerHTML = '<p class="muted">Sem interseção para a seleção atual.</p>';
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
        <h3>${ticker}</h3>
        <p class="muted">Estratégias: ${stockEntry.strategies.join(', ')}</p>
      </div>
      <div class="stock-actions">
        <span class="risk-badge ${riskClass(risk.risk_level)}">${risk.risk_level}</span>
        <button class="btn" data-action="detail">Risco</button>
      </div>
    `;

    card.querySelector('[data-action="detail"]')?.addEventListener('click', () => {
      onOpenDetail(ticker, stockEntry, risk);
    });

    container.appendChild(card);
  }
}

export function renderRiskDetail(container, ticker, stockEntry, risk) {
  const price = stockEntry.sample?.['Cotação'];
  const priceText = typeof price === 'number' ? `R$ ${price.toFixed(2)}` : 'N/D';
  const flags = risk.risk_flags.length ? risk.risk_flags : ['sem_alertas'];

  container.innerHTML = `
    <h3>${ticker}</h3>
    <p><strong>Cotação:</strong> ${priceText}</p>
    <p><strong>Nível:</strong> <span class="risk-badge ${riskClass(risk.risk_level)}">${risk.risk_level}</span></p>
    <p><strong>Score:</strong> ${risk.risk_score}</p>
    <p><strong>Flags:</strong> ${flags.join(', ')}</p>
  `;
}
