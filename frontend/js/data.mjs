const REQUIRED_STRATEGY_KEYS = [
  'strategy_id',
  'name',
  'description',
  'methodology_summary',
  'formula_latex',
  'use_cases',
  'caveats',
  'generated_at',
  'universe_size',
  'filtered_size',
  'result_size',
  'stocks',
];

export async function loadBundle(path = './data/strategies.bundle.json') {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Falha ao carregar bundle: HTTP ${response.status}`);
  }

  const bundle = await response.json();
  validateBundle(bundle);
  return bundle;
}

export function validateBundle(bundle) {
  if (!bundle || typeof bundle !== 'object') {
    throw new Error('Bundle inválido: objeto esperado.');
  }

  if (!Array.isArray(bundle.strategies)) {
    throw new Error('Bundle inválido: campo strategies ausente.');
  }

  for (const strategy of bundle.strategies) {
    for (const key of REQUIRED_STRATEGY_KEYS) {
      if (!(key in strategy)) {
        throw new Error(`Estratégia inválida: campo obrigatório ausente (${key}).`);
      }
    }
  }
}

function normalizeLimit(limit) {
  if (limit === 'ALL') return Number.POSITIVE_INFINITY;
  const parsed = Number(limit);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return Number.POSITIVE_INFINITY;
  }
  return parsed;
}

export function buildTickerSets(strategies, limit = Number.POSITIVE_INFINITY) {
  const max = normalizeLimit(limit);
  return strategies.reduce((acc, strategy) => {
    const tickers = new Set(
      strategy.stocks
        .slice(0, max)
        .map((stock) => stock?.Papel)
        .filter((ticker) => typeof ticker === 'string' && ticker.length > 0)
    );

    acc[strategy.strategy_id] = tickers;
    return acc;
  }, {});
}

export function buildStockMap(strategies, limit = Number.POSITIVE_INFINITY) {
  const max = normalizeLimit(limit);
  const map = new Map();
  for (const strategy of strategies) {
    for (const stock of strategy.stocks.slice(0, max)) {
      if (!stock || typeof stock !== 'object' || !stock.Papel) {
        continue;
      }

      if (!map.has(stock.Papel)) {
        map.set(stock.Papel, {
          ticker: stock.Papel,
          sample: stock,
          strategies: [],
        });
      }

      const item = map.get(stock.Papel);
      item.strategies.push(strategy.strategy_id);
    }
  }
  return map;
}
