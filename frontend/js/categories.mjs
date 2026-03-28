export const CATEGORIES = [
  {
    id: 'todos',
    label: 'Todos',
    story: '',
    description: '',
    keyMetrics: '',
    idealFor: '',
    tip: '',
    icon: 'layout-grid',
    strategies: [],
  },
  {
    id: 'valor',
    label: 'Valor',
    story: 'Quero encontrar ações que o mercado está precificando abaixo do que valem',
    description:
      'Estratégias de valor buscam ações negociadas por menos do que seus fundamentos sugerem. ' +
      'Usam métricas como P/L, P/VP, EV/EBIT e Graham Number para identificar barganhas.',
    keyMetrics: 'P/L (preço/lucro), P/VP (preço/valor patrimonial), EV/EBIT (valor da firma/lucro operacional)',
    idealFor: 'Investidores pacientes, dispostos a esperar o mercado reconhecer o valor real da empresa.',
    tip: 'P/L e P/VP baixos podem indicar barganha, mas também empresa com problemas. Sempre verifique o motivo.',
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
    description:
      'Estratégias de qualidade priorizam empresas com alta rentabilidade, margens consistentes ' +
      'e balanço saudável. Focam em ROIC, ROE, margens e solidez financeira.',
    keyMetrics: 'ROIC (retorno sobre capital investido), ROE (retorno sobre patrimônio), Marg. Líquida, Marg. EBIT',
    idealFor: 'Quem busca segurança e previsibilidade. Empresas de qualidade tendem a cair menos em crises.',
    tip: 'ROIC acima de 15% de forma consistente é sinal de vantagem competitiva duradoura (moat).',
    icon: 'award',
    strategies: ['quality', 'dupont', 'buffett', 'assetlight', 'fortress', 'altman'],
  },
  {
    id: 'renda',
    label: 'Renda',
    story: 'Quero ações que pagam bons dividendos de forma consistente',
    description:
      'Estratégias de renda selecionam empresas que distribuem dividendos elevados de forma recorrente. ' +
      'Avaliam Dividend Yield, endividamento e sustentabilidade dos pagamentos.',
    keyMetrics: 'DY (Dividend Yield = dividendos/preço), Dív/PL (endividamento), Payout (% do lucro distribuído)',
    idealFor: 'Quem quer renda passiva ou está montando uma carteira para viver de dividendos.',
    tip: 'DY muito alto (acima de 12%) pode ser armadilha: o preço caiu por problemas, inflando o yield artificialmente.',
    icon: 'wallet',
    strategies: ['bazin', 'largecap_dividend', 'earnings_yield_spread', 'cashrich'],
  },
  {
    id: 'crescimento',
    label: 'Crescimento',
    story: 'Quero empresas que estão crescendo rápido sem pagar caro por isso',
    description:
      'Estratégias de crescimento buscam empresas com receita e lucro em aceleração, ' +
      'mas que ainda não estão caras demais. Combinam crescimento com valuation razoável.',
    keyMetrics: 'PEG (P/L dividido pelo crescimento), Cresc. Receita 5a, Momentum 12 meses',
    idealFor: 'Quem aceita mais volatilidade em troca de potencial de valorização. Horizonte de médio/longo prazo.',
    tip: 'PEG abaixo de 1 sugere crescimento barato. Acima de 2, o mercado já precificou boa parte do crescimento.',
    icon: 'trending-up',
    strategies: ['garp', 'earnings_accel', 'momentum_value', 'smallcap_value'],
  },
  {
    id: 'risco',
    label: 'Risco',
    story: 'Quero entender onde estão os riscos e oportunidades que outros ignoram',
    description:
      'Estratégias de risco analisam a saúde financeira, volatilidade e sinais de alerta. ' +
      'Incluem abordagens contrarian (apostar contra o consenso) e filtros de red flags.',
    keyMetrics: 'F-Score (Piotroski), Z-Score (Altman), Volatilidade 52w, Distância da mínima 52w',
    idealFor: 'Investidores experientes que sabem avaliar risco/retorno e buscam assimetrias.',
    tip: 'Ações perto da mínima de 52 semanas com fundamentos sólidos podem ser oportunidades contrarian.',
    icon: 'shield-alert',
    strategies: ['contrarian', 'piotroski', 'redflags', 'volatility_adjusted', 'margin_compression'],
  },
  {
    id: 'compostas',
    label: 'Compostas',
    story: 'Quero ver o que acontece quando cruzo múltiplas estratégias',
    description:
      'Estratégias compostas combinam vários fatores (valor + qualidade + crescimento + renda) ' +
      'ou cruzam os resultados de outras estratégias para encontrar convergência.',
    keyMetrics: 'Score multi-fator, número de aparições em outras estratégias, rank combinado',
    idealFor: 'Quem quer uma visão mais completa e equilibrada, sem depender de um único fator.',
    tip: 'Ações que aparecem em múltiplas estratégias independentes têm sinal mais robusto.',
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
