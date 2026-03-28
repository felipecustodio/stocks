import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

describe('render module', () => {
  it('exports all required functions', async () => {
    const mod = await import('../js/render.mjs');
    assert.equal(typeof mod.renderStrategies, 'function');
    assert.equal(typeof mod.renderConsensusPicks, 'function');
    assert.equal(typeof mod.renderIntelligence, 'function');
    assert.equal(typeof mod.renderComparison, 'function');
    assert.equal(typeof mod.renderTickerProfile, 'function');
  });
});
