import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { buildTickerIndex } from '../js/data.mjs';

describe('buildTickerIndex', () => {
  const strategies = [
    {
      strategy_id: 'magic',
      name: 'Magic Formula',
      stocks: [
        { Papel: 'WEGE3', Empresa: 'WEG S.A.', Setor: 'Máquinas', Fontes: { F: 'http://f' } },
        { Papel: 'VALE3', Empresa: 'Vale S.A.', Setor: 'Mineração' },
      ],
    },
    {
      strategy_id: 'quality',
      name: 'Quality',
      stocks: [
        { Papel: 'WEGE3', Empresa: 'WEG S.A.', Setor: 'Máquinas' },
      ],
    },
  ];

  it('builds index with ticker as key', () => {
    const index = buildTickerIndex(strategies);
    assert.ok(index.has('WEGE3'));
    assert.ok(index.has('VALE3'));
    assert.equal(index.size, 2);
  });

  it('tracks all strategy appearances with rank', () => {
    const index = buildTickerIndex(strategies);
    const wege = index.get('WEGE3');
    assert.equal(wege.appearances.length, 2);
    assert.equal(wege.appearances[0].strategy_id, 'magic');
    assert.equal(wege.appearances[0].rank, 1);
    assert.equal(wege.appearances[1].strategy_id, 'quality');
    assert.equal(wege.appearances[1].rank, 1);
  });

  it('keeps company and sector from first appearance', () => {
    const index = buildTickerIndex(strategies);
    const wege = index.get('WEGE3');
    assert.equal(wege.company, 'WEG S.A.');
    assert.equal(wege.sector, 'Máquinas');
  });

  it('merges fontes from all appearances', () => {
    const index = buildTickerIndex(strategies);
    const wege = index.get('WEGE3');
    assert.deepEqual(wege.fontes, { F: 'http://f' });
  });
});
