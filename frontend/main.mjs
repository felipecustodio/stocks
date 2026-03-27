import { buildStockMap, buildTickerSets, loadBundle } from './js/data.mjs';
import { formatGeneratedAt } from './js/datetime.mjs';
import { intersectAndOr } from './js/intersections.mjs';
import {
  renderConsensusPicks,
  renderCompareStrategyList,
  renderIntersectionResults,
  renderStrategyIndex,
  renderStrategies,
} from './js/render.mjs';

const state = {
  bundle: null,
  visibleStrategies: [],
  selectedStrategies: new Set(),
  mode: 'AND',
  displayLimit: 30,
  sectorFilter: 'ALL',
  tickerSets: {},
  stockMap: new Map(),
  fullStockMap: new Map(),
  activeStrategyId: null,
};

const dom = {
  status: document.getElementById('status'),
  generatedAt: document.getElementById('generated-at'),
  universeCount: document.getElementById('universe-count'),
  sectorFilter: document.getElementById('sector-filter'),
  consensusPicks: document.getElementById('consensus-picks'),
  strategyIndex: document.getElementById('strategy-index'),
  strategies: document.getElementById('strategies'),
  compareDrawer: document.getElementById('compare-drawer'),
  compareList: document.getElementById('compare-strategy-list'),
  compareResults: document.getElementById('compare-results'),
  compareCount: document.getElementById('compare-count'),
  modeHelp: document.getElementById('mode-help'),
  modeBadge: document.getElementById('mode-badge'),
  resultsTitle: document.getElementById('results-title'),
  displayLimit: document.getElementById('display-limit'),
  mode: document.getElementById('mode-select'),
  closeCompare: document.getElementById('close-compare'),
};

function limitLabel() {
  return state.displayLimit === 'ALL' ? 'todos' : `top ${state.displayLimit}`;
}

function stockSector(stock) {
  const raw = stock?.Setor;
  if (typeof raw === 'string' && raw.trim()) return raw.trim();
  return 'Setor não informado';
}

function rebuildVisibleStrategies() {
  if (!state.bundle) {
    state.visibleStrategies = [];
    return;
  }

  state.visibleStrategies = state.bundle.strategies.map((strategy) => {
    const scopedStocks =
      state.sectorFilter === 'ALL'
        ? strategy.stocks
        : strategy.stocks.filter((stock) => stockSector(stock) === state.sectorFilter);
    return {
      ...strategy,
      stocks: scopedStocks,
    };
  });
}

function rebuildDerivedData() {
  state.tickerSets = buildTickerSets(state.visibleStrategies, state.displayLimit);
  state.stockMap = buildStockMap(state.visibleStrategies, state.displayLimit);
}

function rebuildViewData() {
  rebuildVisibleStrategies();
  rebuildDerivedData();
}

function renderSectorFilterOptions() {
  if (!dom.sectorFilter || !state.bundle) return;
  const sectors = new Set();
  for (const strategy of state.bundle.strategies) {
    for (const stock of strategy.stocks) {
      sectors.add(stockSector(stock));
    }
  }

  const options = ['ALL', ...[...sectors].sort((a, b) => a.localeCompare(b, 'pt-BR'))];
  dom.sectorFilter.innerHTML = '';
  for (const value of options) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value === 'ALL' ? 'Todos' : value;
    option.selected = value === state.sectorFilter;
    dom.sectorFilter.appendChild(option);
  }
}

async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const temp = document.createElement('textarea');
  temp.value = text;
  temp.setAttribute('readonly', '');
  temp.style.position = 'absolute';
  temp.style.left = '-9999px';
  document.body.appendChild(temp);
  temp.select();
  document.execCommand('copy');
  document.body.removeChild(temp);
}

function updateModeGuidance() {
  if (state.mode === 'AND') {
    dom.resultsTitle.textContent = 'Resultado da interseção';
    dom.modeHelp.innerHTML =
      '<strong>AND:</strong> retorna apenas ações presentes em <em>todas</em> as estratégias selecionadas.';
    dom.modeBadge.textContent = 'Modo atual: AND (somente ativos em comum)';
  } else {
    dom.resultsTitle.textContent = 'Resultado da união';
    dom.modeHelp.innerHTML =
      '<strong>OR:</strong> retorna ações presentes em <em>pelo menos uma</em> estratégia selecionada.';
    dom.modeBadge.textContent = 'Modo atual: OR (lista ampliada por união)';
  }
}

function refreshComparisonResults() {
  const ids = [...state.selectedStrategies];
  const sets = ids.map((id) => state.tickerSets[id]).filter(Boolean);
  const resultSet = intersectAndOr(state.mode, sets);
  const tickers = [...resultSet];

  renderIntersectionResults(dom.compareResults, tickers, state.stockMap, state.mode, ids.length);

  const total = state.stockMap.size || 1;
  const universeTotal = state.fullStockMap.size || total;
  const pct = ((tickers.length / universeTotal) * 100).toFixed(1);
  if (ids.length === 0) {
    dom.compareCount.textContent = 'Seleção vazia.';
  } else if (state.mode === 'AND') {
    dom.compareCount.textContent = `Interseção (${limitLabel()}): ${tickers.length} ativos (${pct}% do universo no bundle).`;
  } else {
    dom.compareCount.textContent = `União (${limitLabel()}): ${tickers.length} ativos (${pct}% do universo no bundle).`;
  }
}

function openCompareDrawer(defaultStrategyId = null) {
  if (defaultStrategyId) {
    state.selectedStrategies.add(defaultStrategyId);
  }

  dom.compareDrawer.classList.add('open');
  updateModeGuidance();
  renderCompareStrategyList(
    dom.compareList,
    state.bundle.strategies,
    state.selectedStrategies,
    (strategyId, checked) => {
      if (checked) {
        state.selectedStrategies.add(strategyId);
      } else {
        state.selectedStrategies.delete(strategyId);
      }
      refreshComparisonResults();
    }
  );

  refreshComparisonResults();
}

function closeCompareDrawer() {
  dom.compareDrawer.classList.remove('open');
}

function renderPage() {
  if (!state.bundle) return;

  const consensus = [...state.stockMap.values()]
    .map((entry) => ({
      ticker: entry.ticker,
      count: entry.strategies.length,
      strategies: entry.strategies,
      sample: entry.sample,
    }))
    .sort((a, b) => b.count - a.count || a.ticker.localeCompare(b.ticker))
    .slice(0, 12);
  renderConsensusPicks(dom.consensusPicks, consensus, state.bundle.strategies.length);

  renderStrategyIndex(dom.strategyIndex, state.bundle.strategies, state.activeStrategyId, (strategyId) => {
    const card = document.getElementById(`strategy-card-${strategyId}`);
    if (card) {
      card.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });

  renderStrategies(
    dom.strategies,
    state.visibleStrategies,
    state.activeStrategyId,
    state.displayLimit,
    (strategyId) => {
      state.activeStrategyId = state.activeStrategyId === strategyId ? null : strategyId;
      renderPage();
    },
    () => {
      state.activeStrategyId = null;
      renderPage();
    },
    (strategyId) => {
      if (!dom.compareDrawer.classList.contains('open')) {
        openCompareDrawer(strategyId);
        return;
      }

      if (state.selectedStrategies.has(strategyId)) {
        state.selectedStrategies.delete(strategyId);
      } else {
        state.selectedStrategies.add(strategyId);
      }

      if (state.selectedStrategies.size === 0) {
        closeCompareDrawer();
        return;
      }

      openCompareDrawer();
    },
    async (strategyId) => {
      const strategy = state.visibleStrategies.find((item) => item.strategy_id === strategyId);
      if (!strategy) return false;
      const maxRows = state.displayLimit === 'ALL' ? strategy.stocks.length : Number(state.displayLimit);
      const tickers = strategy.stocks
        .slice(0, maxRows)
        .map((stock) => stock?.Papel)
        .filter((ticker) => typeof ticker === 'string' && ticker.length > 0);

      if (!tickers.length) {
        dom.status.textContent = `Sem ativos para copiar em ${strategy.name} com o filtro atual.`;
        return false;
      }

      try {
        await copyText(tickers.join('\n'));
        dom.status.textContent = `${tickers.length} ticker(s) copiados de ${strategy.name}.`;
        return true;
      } catch {
        dom.status.textContent = `Falha ao copiar Top N de ${strategy.name}.`;
        return false;
      }
    }
  );
}

async function boot() {
  try {
    dom.status.textContent = 'Carregando bundle de estratégias...';
    const bundle = await loadBundle('./data/strategies.bundle.json');
    state.bundle = bundle;
    state.fullStockMap = buildStockMap(bundle.strategies, 'ALL');
    rebuildViewData();
    renderSectorFilterOptions();

    dom.generatedAt.textContent = formatGeneratedAt(bundle.generated_at);
    dom.universeCount.textContent = String(state.fullStockMap.size);
    dom.status.textContent = `${bundle.strategy_count ?? bundle.strategies.length} estratégias carregadas.`;
    renderPage();
  } catch (error) {
    dom.status.textContent = `Erro: ${error.message}. Rode \`just crawl\` para gerar o bundle.`;
  }
}

if (dom.mode) {
  dom.mode.addEventListener('change', (event) => {
    state.mode = event.target.value;
    updateModeGuidance();
    refreshComparisonResults();
  });
}

if (dom.displayLimit) {
  dom.displayLimit.value = String(state.displayLimit);
  dom.displayLimit.addEventListener('change', (event) => {
    const raw = event.target.value;
    state.displayLimit = raw === 'ALL' ? 'ALL' : Number(raw);
    rebuildDerivedData();
    dom.universeCount.textContent = String(state.fullStockMap.size);
    renderPage();
    refreshComparisonResults();
  });
}

if (dom.sectorFilter) {
  dom.sectorFilter.addEventListener('change', (event) => {
    state.sectorFilter = event.target.value;
    rebuildViewData();
    renderPage();
    refreshComparisonResults();
  });
}

dom.closeCompare?.addEventListener('click', closeCompareDrawer);

boot();
