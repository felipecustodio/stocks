export function intersectAndOr(operator, sets) {
  if (!Array.isArray(sets) || sets.length === 0) {
    return new Set();
  }

  if (operator === 'AND') {
    let current = new Set(sets[0]);
    for (const s of sets.slice(1)) {
      current = new Set([...current].filter((item) => s.has(item)));
    }
    return new Set([...current].sort());
  }

  const union = new Set();
  for (const s of sets) {
    for (const item of s) {
      union.add(item);
    }
  }
  return new Set([...union].sort());
}
