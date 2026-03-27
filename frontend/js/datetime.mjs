function pad2(value) {
  return String(value).padStart(2, '0');
}

function normalizeIsoTimestamp(raw) {
  if (typeof raw !== 'string') return null;
  const value = raw.trim();
  if (!value) return null;

  return value.replace(/(\.\d{3})\d+(?=(Z|[+-]\d{2}:\d{2})$)/, '$1');
}

export function formatGeneratedAt(raw) {
  const normalized = normalizeIsoTimestamp(raw);
  if (!normalized) return raw;

  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return raw;

  const day = pad2(date.getUTCDate());
  const month = pad2(date.getUTCMonth() + 1);
  const year = date.getUTCFullYear();
  const hour = pad2(date.getUTCHours());
  const minute = pad2(date.getUTCMinutes());

  return `${day}/${month}/${year} ${hour}:${minute}`;
}
