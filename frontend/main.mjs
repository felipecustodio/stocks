import { buildStockMap, buildTickerSets, buildTickerIndex, loadBundle } from './js/data.mjs';
import { CATEGORIES, categoryForStrategy, categoryMetrics } from './js/categories.mjs';
import { formatGeneratedAt } from './js/datetime.mjs';
import { intersectAndOr } from './js/intersections.mjs';
import {
  renderConsensusPicks,
  renderIntelligence,
  renderStrategies,
  renderComparison,
  renderTickerProfile,
} from './js/render.mjs';

const state = {
  bundle: null,
  visibleStrategies: [],
  activeCategory: 'todos',
  comparedStrategies: new Set(),
  comparisonMode: 'AND',
  displayLimit: 30,
  sectorFilter: 'ALL',
  tickerSets: {},
  stockMap: new Map(),
  fullStockMap: new Map(),
  tickerIndex: new Map(),
  activeStrategyId: null,
  activeTickerProfile: null,
};

const dom = {
  status: document.getElementById('status'),
  generatedAt: document.getElementById('generated-at'),
  universeCount: document.getElementById('universe-count'),
  sectorFilter: document.getElementById('sector-filter'),
  displayLimit: document.getElementById('display-limit'),
  categoryTabs: document.getElementById('category-tabs'),
  categoryStory: document.getElementById('category-story'),
  tickerSearch: document.getElementById('ticker-search'),
  searchResults: document.getElementById('search-results'),
  tickerProfile: document.getElementById('ticker-profile'),
  comparisonView: document.getElementById('comparison-view'),
  consensusPicks: document.getElementById('consensus-picks'),
  strategies: document.getElementById('strategies'),
  intelSection: document.getElementById('intelligence-section'),
  intelStats: document.getElementById('intel-stats'),
  intelHighBody: document.getElementById('intel-anomalies-body'),
  intelAllBody: document.getElementById('intel-all-body'),
  intelToggleAll: document.getElementById('intel-toggle-all'),
  intelAllWrap: document.getElementById('intel-all-wrap'),
  intelAnomaliesWrap: document.getElementById('intel-anomalies-wrap'),
};

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

  const catDef = CATEGORIES.find((c) => c.id === state.activeCategory);
  const allowedIds = catDef && catDef.strategies.length > 0 ? new Set(catDef.strategies) : null;

  state.visibleStrategies = state.bundle.strategies
    .filter((strategy) => !allowedIds || allowedIds.has(strategy.strategy_id))
    .map((strategy) => {
      const scopedStocks =
        state.sectorFilter === 'ALL'
          ? strategy.stocks
          : strategy.stocks.filter((stock) => stockSector(stock) === state.sectorFilter);
      return { ...strategy, stocks: scopedStocks };
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

function limitLabel() {
  return state.displayLimit === 'ALL' ? 'todos' : `top ${state.displayLimit}`;
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

function renderCategoryTabs() {
  if (!dom.categoryTabs) return;
  dom.categoryTabs.innerHTML = '';
  for (const cat of CATEGORIES) {
    const btn = document.createElement('button');
    btn.className = `category-tab${cat.id === state.activeCategory ? ' active' : ''}`;
    btn.dataset.categoryId = cat.id;
    btn.innerHTML = `<i data-lucide="${cat.icon}"></i> ${cat.label}`;
    btn.addEventListener('click', () => {
      state.activeCategory = cat.id;
      renderCategoryTabs();
      rebuildViewData();
      renderPage();
    });
    dom.categoryTabs.appendChild(btn);
  }

  if (dom.categoryStory) {
    const catDef = CATEGORIES.find((c) => c.id === state.activeCategory);
    dom.categoryStory.textContent = catDef?.story || '';
    dom.categoryStory.style.display = catDef?.story ? '' : 'none';
  }

  if (window.lucide?.createIcons) window.lucide.createIcons();
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

function openTickerProfile(ticker) {
  if (!dom.tickerProfile || !state.tickerIndex.has(ticker)) return;
  state.activeTickerProfile = ticker;
  dom.tickerProfile.style.display = '';
  renderTickerProfile(
    dom.tickerProfile,
    state.tickerIndex.get(ticker),
    state.bundle?.intelligence,
    () => closeTickerProfile(),
    (t) => openTickerProfile(t)
  );
}

function closeTickerProfile() {
  state.activeTickerProfile = null;
  if (dom.tickerProfile) {
    dom.tickerProfile.style.display = 'none';
    dom.tickerProfile.innerHTML = '';
  }
}

function handleSearch() {
  const query = dom.tickerSearch.value.trim().toUpperCase();
  if (query.length < 1) {
    dom.searchResults.classList.remove('open');
    return;
  }

  const matches = [];
  for (const [ticker, entry] of state.tickerIndex) {
    if (matches.length >= 12) break;
    if (ticker.includes(query) || entry.company.toUpperCase().includes(query)) {
      matches.push(entry);
    }
  }

  if (matches.length === 0) {
    dom.searchResults.classList.remove('open');
    return;
  }

  dom.searchResults.innerHTML = matches
    .map(
      (entry) => `
      <div class="search-item" data-ticker="${entry.ticker}">
        <img
          class="search-item-logo"
          src="https://raw.githubusercontent.com/thefintz/icones-b3/main/icones/${entry.ticker}.png"
          alt=""
          loading="lazy"
          onerror="this.style.display='none'; this.nextElementSibling.style.display='inline-flex';"
        />
        <span class="search-item-fallback" style="display:none;">${entry.ticker.slice(0, 1)}</span>
        <span>${entry.ticker}</span>
        <span class="search-company">${entry.company}</span>
        <span class="search-count">${entry.appearances.length} estratégias</span>
      </div>
    `
    )
    .join('');
  dom.searchResults.classList.add('open');

  dom.searchResults.querySelectorAll('.search-item').forEach((el) => {
    el.addEventListener('click', () => {
      openTickerProfile(el.dataset.ticker);
      dom.searchResults.classList.remove('open');
      dom.tickerSearch.value = '';
    });
  });
}

function openComparison() {
  if (!dom.comparisonView) return;
  dom.comparisonView.style.display = '';
  refreshComparison();
}

function closeComparison() {
  state.comparedStrategies.clear();
  if (dom.comparisonView) {
    dom.comparisonView.style.display = 'none';
    dom.comparisonView.innerHTML = '';
  }
}

function refreshComparison() {
  if (!dom.comparisonView || state.comparedStrategies.size === 0) return;

  const ids = [...state.comparedStrategies];
  const strategies = ids
    .map((id) => state.visibleStrategies.find((s) => s.strategy_id === id))
    .filter(Boolean);

  const sets = ids.map((id) => state.tickerSets[id]).filter(Boolean);
  const resultSet = intersectAndOr(state.comparisonMode, sets);
  const resultTickers = [...resultSet];

  renderComparison(
    dom.comparisonView,
    strategies,
    state.comparisonMode,
    resultTickers,
    state.stockMap,
    state.fullStockMap,
    state.displayLimit,
    (newMode) => {
      state.comparisonMode = newMode;
      refreshComparison();
    },
    () => closeComparison(),
    (ticker) => openTickerProfile(ticker)
  );
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
  renderConsensusPicks(
    dom.consensusPicks,
    consensus,
    state.bundle.strategies.length,
    state.bundle?.intelligence,
    (ticker) => openTickerProfile(ticker)
  );

  if (dom.intelSection && state.bundle?.intelligence) {
    renderIntelligence(dom.intelSection, dom.intelStats, dom.intelHighBody, dom.intelAllBody, state.bundle.intelligence);
  }

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
      if (state.comparedStrategies.has(strategyId)) {
        state.comparedStrategies.delete(strategyId);
      } else if (state.comparedStrategies.size < 4) {
        state.comparedStrategies.add(strategyId);
      }
      if (state.comparedStrategies.size === 0) {
        closeComparison();
      } else {
        openComparison();
      }
      renderPage();
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
    },
    state.bundle?.intelligence,
    state.comparedStrategies,
    (ticker) => openTickerProfile(ticker)
  );
}

async function boot() {
  try {
    dom.status.textContent = 'Carregando...';
    const bundle = await loadBundle('./data/strategies.bundle.json');
    state.bundle = bundle;
    state.fullStockMap = buildStockMap(bundle.strategies, 'ALL');
    state.tickerIndex = buildTickerIndex(bundle.strategies);
    rebuildViewData();
    renderSectorFilterOptions();
    renderCategoryTabs();

    dom.generatedAt.textContent = formatGeneratedAt(bundle.generated_at);
    dom.universeCount.textContent = String(state.fullStockMap.size);
    dom.status.textContent = `${bundle.strategy_count ?? bundle.strategies.length} estratégias carregadas.`;
    renderPage();
  } catch (error) {
    dom.status.textContent = `Erro: ${error.message}. Rode \`just crawl\` para gerar o bundle.`;
  }
}

if (dom.displayLimit) {
  dom.displayLimit.value = String(state.displayLimit);
  dom.displayLimit.addEventListener('change', (event) => {
    const raw = event.target.value;
    state.displayLimit = raw === 'ALL' ? 'ALL' : Number(raw);
    rebuildDerivedData();
    dom.universeCount.textContent = String(state.fullStockMap.size);
    renderPage();
    if (state.comparedStrategies.size > 0) refreshComparison();
  });
}

if (dom.sectorFilter) {
  dom.sectorFilter.addEventListener('change', (event) => {
    state.sectorFilter = event.target.value;
    rebuildViewData();
    renderPage();
    if (state.comparedStrategies.size > 0) refreshComparison();
  });
}

if (dom.tickerSearch) {
  dom.tickerSearch.addEventListener('input', handleSearch);
  dom.tickerSearch.addEventListener('focus', handleSearch);
  document.addEventListener('click', (event) => {
    if (!dom.tickerSearch.contains(event.target) && !dom.searchResults.contains(event.target)) {
      dom.searchResults.classList.remove('open');
    }
  });
}

if (dom.intelToggleAll) {
  dom.intelToggleAll.addEventListener('click', () => {
    const wrap = dom.intelAllWrap;
    if (!wrap) return;
    const isHidden = wrap.style.display === 'none';
    wrap.style.display = isHidden ? '' : 'none';
    const label = dom.intelToggleAll.querySelector('span');
    if (label) label.textContent = isHidden ? 'Ocultar médias e baixas' : 'Mostrar médias e baixas';
  });
}

boot();
