import test from 'node:test';
import assert from 'node:assert/strict';

import { intersectAndOr } from '../js/intersections.mjs';

test('AND returns only common tickers', () => {
  const result = intersectAndOr('AND', [
    new Set(['PETR4', 'VALE3']),
    new Set(['PETR4', 'BBDC4']),
  ]);

  assert.deepEqual([...result], ['PETR4']);
});

test('OR returns union of tickers sorted', () => {
  const result = intersectAndOr('OR', [
    new Set(['VALE3']),
    new Set(['PETR4', 'VALE3']),
  ]);

  assert.deepEqual([...result], ['PETR4', 'VALE3']);
});
