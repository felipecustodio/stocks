const RULES = {
  liquidez_baixa: { score: 2 },
  endividamento_alto: { score: 2 },
  margem_ebit_fraca: { score: 2 },
  volatilidade_12m_alta: { score: 1 },
  sinais_incompletos: { score: 1 },
};

function getNested(stock, section, key) {
  const sec = stock?.[section];
  if (!sec || typeof sec !== 'object') {
    return null;
  }
  return sec[key] ?? null;
}

export function evaluateRisk(stock) {
  const flags = [];
  let score = 0;

  const liq = stock?.['Liq.2meses'];
  const debt = getNested(stock, 'Oscilações', 'Div Br/ Patrim');
  const ebitMargin = getNested(stock, 'Oscilações', 'Marg. EBIT');
  const m12 = getNested(stock, 'Oscilações', '12 meses');

  if (typeof liq !== 'number' || typeof debt !== 'number' || typeof ebitMargin !== 'number' || typeof m12 !== 'number') {
    flags.push('sinais_incompletos');
    score += RULES.sinais_incompletos.score;
  }

  if (typeof liq === 'number' && liq < 200000) {
    flags.push('liquidez_baixa');
    score += RULES.liquidez_baixa.score;
  }

  if (typeof debt === 'number' && debt > 1.5) {
    flags.push('endividamento_alto');
    score += RULES.endividamento_alto.score;
  }

  if (typeof ebitMargin === 'number' && ebitMargin <= 0.05) {
    flags.push('margem_ebit_fraca');
    score += RULES.margem_ebit_fraca.score;
  }

  if (typeof m12 === 'number' && Math.abs(m12) >= 0.4) {
    flags.push('volatilidade_12m_alta');
    score += RULES.volatilidade_12m_alta.score;
  }

  let level = 'BAIXO';
  if (score >= 4) {
    level = 'ALTO';
  } else if (score >= 2) {
    level = 'MÉDIO';
  }

  return {
    risk_level: level,
    risk_score: score,
    risk_flags: flags,
  };
}
