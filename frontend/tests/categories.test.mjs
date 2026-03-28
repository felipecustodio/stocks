import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { CATEGORIES, categoryForStrategy } from '../js/categories.mjs';

describe('categories', () => {
  it('maps magicformula to valor', () => {
    assert.equal(categoryForStrategy('magicformula'), 'valor');
  });

  it('maps bazin to renda', () => {
    assert.equal(categoryForStrategy('bazin'), 'renda');
  });

  it('maps unknown strategy to null', () => {
    assert.equal(categoryForStrategy('nonexistent'), null);
  });

  it('every category has a label, story, and strategies array', () => {
    for (const cat of CATEGORIES) {
      assert.ok(cat.id, 'missing id');
      assert.ok(cat.label, 'missing label');
      assert.ok(typeof cat.story === 'string', 'missing story');
      assert.ok(Array.isArray(cat.strategies), 'missing strategies');
    }
  });

  it('has a todos entry that contains no strategies', () => {
    const todos = CATEGORIES.find((c) => c.id === 'todos');
    assert.ok(todos);
    assert.equal(todos.strategies.length, 0);
  });

  it('categoryMetrics returns 2 metrics for each category', async () => {
    const { categoryMetrics } = await import('../js/categories.mjs');
    for (const cat of CATEGORIES) {
      if (cat.id === 'todos') continue;
      const metrics = categoryMetrics(cat.id);
      assert.equal(metrics.length, 2, `${cat.id} should have 2 metrics`);
      assert.ok(metrics[0].label, `${cat.id} metric 0 missing label`);
      assert.ok(metrics[0].path, `${cat.id} metric 0 missing path`);
    }
  });
});
