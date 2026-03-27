import { buildStockMap, buildTickerSets, loadBundle } from './js/data.mjs';
import { intersectAndOr } from './js/intersections.mjs';
import {
  renderCompareStrategyList,
  renderIntersectionResults,
  renderRiskDetail,
  renderStrategies,
} from './js/render.mjs';

const state = {
  bundle: null,
  selectedStrategies: new Set(),
  mode: 'AND',
  tickerSets: {},
  stockMap: new Map(),
};

const dom = {
  status: document.getElementById('status'),
  generatedAt: document.getElementById('generated-at'),
  strategies: document.getElementById('strategies'),
  compareDrawer: document.getElementById('compare-drawer'),
  detailDrawer: document.getElementById('detail-drawer'),
  compareList: document.getElementById('compare-strategy-list'),
  compareResults: document.getElementById('compare-results'),
  compareCount: document.getElementById('compare-count'),
  mode: document.getElementById('mode-select'),
  detailContent: document.getElementById('detail-content'),
  closeCompare: document.getElementById('close-compare'),
  closeDetail: document.getElementById('close-detail'),
};

function refreshComparisonResults() {
  const ids = [...state.selectedStrategies];
  const sets = ids.map((id) => state.tickerSets[id]).filter(Boolean);
  const resultSet = intersectAndOr(state.mode, sets);
  const tickers = [...resultSet];

  renderIntersectionResults(dom.compareResults, tickers, state.stockMap, (ticker, stockEntry, risk) => {
    dom.detailDrawer.classList.add('open');
    renderRiskDetail(dom.detailContent, ticker, stockEntry, risk);
  });

  const total = state.stockMap.size || 1;
  const pct = ((tickers.length / total) * 100).toFixed(1);
  dom.compareCount.textContent = `${tickers.length} ativos (${pct}% do universo no bundle)`;
}

function openCompareDrawer(defaultStrategyId = null) {
  if (defaultStrategyId) {
    state.selectedStrategies.add(defaultStrategyId);
  }

  dom.compareDrawer.classList.add('open');
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

async function boot() {
  try {
    dom.status.textContent = 'Carregando bundle de estratégias...';
    const bundle = await loadBundle('./data/strategies.bundle.json');
    state.bundle = bundle;
    state.tickerSets = buildTickerSets(bundle.strategies);
    state.stockMap = buildStockMap(bundle.strategies);

    dom.generatedAt.textContent = bundle.generated_at;
    dom.status.textContent = `${bundle.strategy_count ?? bundle.strategies.length} estratégias carregadas.`;

    renderStrategies(dom.strategies, bundle.strategies, (strategyId) => {
      openCompareDrawer(strategyId);
    });
  } catch (error) {
    dom.status.textContent = `Erro: ${error.message}. Rode \`just crawl\` para gerar o bundle.`;
  }
}

if (dom.mode) {
  dom.mode.addEventListener('change', (event) => {
    state.mode = event.target.value;
    refreshComparisonResults();
  });
}

dom.closeCompare?.addEventListener('click', () => {
  dom.compareDrawer.classList.remove('open');
});

dom.closeDetail?.addEventListener('click', () => {
  dom.detailDrawer.classList.remove('open');
});

boot();
