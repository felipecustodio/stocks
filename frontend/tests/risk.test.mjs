import test from 'node:test';
import assert from 'node:assert/strict';

import { evaluateRisk } from '../js/risk.mjs';

test('high debt and low liquidity maps to ALTO', () => {
  const stock = {
    'Liq.2meses': 100000,
    Oscilações: {
      'Marg. EBIT': 0.03,
      'Div Br/ Patrim': 2.1,
      '12 meses': -0.5,
    },
  };

  const risk = evaluateRisk(stock);

  assert.equal(risk.risk_level, 'ALTO');
  assert.ok(risk.risk_flags.includes('liquidez_baixa'));
  assert.ok(risk.risk_flags.includes('endividamento_alto'));
});

test('healthy inputs maps to BAIXO', () => {
  const stock = {
    'Liq.2meses': 600000,
    Oscilações: {
      'Marg. EBIT': 0.2,
      'Div Br/ Patrim': 0.4,
      '12 meses': 0.12,
    },
  };

  const risk = evaluateRisk(stock);
  assert.equal(risk.risk_level, 'BAIXO');
  assert.equal(risk.risk_flags.length, 0);
});
