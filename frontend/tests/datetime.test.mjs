import test from 'node:test';
import assert from 'node:assert/strict';

import { formatGeneratedAt } from '../js/datetime.mjs';

test('formats ISO timestamp into concise pt-BR display', () => {
  const result = formatGeneratedAt('2026-03-27T20:11:03.890527+00:00');
  assert.equal(result, '27/03/2026 20:11');
});

test('keeps original value when timestamp is invalid', () => {
  const raw = 'invalid-date';
  assert.equal(formatGeneratedAt(raw), raw);
});
