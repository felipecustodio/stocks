export const CATEGORIES = [
  {
    id: 'todos',
    label: 'Todos',
    story: '',
    icon: 'layout-grid',
    strategies: [],
  },
  {
    id: 'valor',
    label: 'Valor',
    story: 'Quero encontrar ações que o mercado está precificando abaixo do que valem',
    icon: 'search',
    strategies: [
      'magicformula', 'graham', 'deepvalue', 'acquirers',
      'netnet', 'bookvalue', 'working_capital', 'sector_relative',
    ],
  },
  {
    id: 'qualidade',
    label: 'Qualidade',
    story: 'Quero empresas lucrativas, bem geridas e com balanço sólido',
    icon: 'award',
    strategies: ['quality', 'dupont', 'buffett', 'assetlight', 'fortress', 'altman'],
  },
  {
    id: 'renda',
    label: 'Renda',
    story: 'Quero ações que pagam bons dividendos de forma consistente',
    icon: 'wallet',
    strategies: ['bazin', 'largecap_dividend', 'earnings_yield_spread', 'cashrich'],
  },
  {
    id: 'crescimento',
    label: 'Crescimento',
    story: 'Quero empresas que estão crescendo rápido sem pagar caro por isso',
    icon: 'trending-up',
    strategies: ['garp', 'earnings_accel', 'momentum_value', 'smallcap_value'],
  },
  {
    id: 'risco',
    label: 'Risco',
    story: 'Quero entender onde estão os riscos e oportunidades que outros ignoram',
    icon: 'shield-alert',
    strategies: ['contrarian', 'piotroski', 'redflags', 'volatility_adjusted', 'margin_compression'],
  },
  {
    id: 'compostas',
    label: 'Compostas',
    story: 'Quero ver o que acontece quando cruzo múltiplas estratégias',
    icon: 'layers',
    strategies: ['multifactor', 'cdv', 'intersection', 'consensus'],
  },
];

const _strategyToCategory = new Map();
for (const cat of CATEGORIES) {
  for (const sid of cat.strategies) {
    _strategyToCategory.set(sid, cat.id);
  }
}

export function categoryForStrategy(strategyId) {
  return _strategyToCategory.get(strategyId) ?? null;
}

const _categoryMetrics = {
  valor: [
    { label: 'P/L médio', path: ['Indicadores fundamentalistas', 'P/L'] },
    { label: 'P/VP médio', path: ['Indicadores fundamentalistas', 'P/VP'] },
  ],
  qualidade: [
    { label: 'ROIC médio', path: ['Oscilações', 'ROIC'] },
    { label: 'Marg. Líq. média', path: ['Oscilações', 'Marg. Líquida'] },
  ],
  renda: [
    { label: 'DY médio', path: ['Indicadores fundamentalistas', 'Div. Yield'] },
    { label: 'Dív/PL médio', path: ['Oscilações', 'Div Br/ Patrim'] },
  ],
  crescimento: [
    { label: 'P/L médio', path: ['Indicadores fundamentalistas', 'P/L'] },
    { label: 'DY médio', path: ['Indicadores fundamentalistas', 'Div. Yield'] },
  ],
  risco: [
    { label: 'P/L médio', path: ['Indicadores fundamentalistas', 'P/L'] },
    { label: 'DY médio', path: ['Indicadores fundamentalistas', 'Div. Yield'] },
  ],
  compostas: [
    { label: 'P/L médio', path: ['Indicadores fundamentalistas', 'P/L'] },
    { label: 'DY médio', path: ['Indicadores fundamentalistas', 'Div. Yield'] },
  ],
};

export function categoryMetrics(categoryId) {
  return _categoryMetrics[categoryId] ?? _categoryMetrics.compostas;
}
