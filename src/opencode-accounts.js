/**
 * Pure helpers for reading/rendering OpenCode credential metadata.
 * Never expose access/refresh tokens.
 */

const SENSITIVE_KEYS = new Set([
  'value', 'access', 'refresh', 'token', 'access_token', 'refresh_token',
  'secret', 'password', 'apiKey', 'authorization'
]);

export function parseCredentialValue(rawJson) {
  let obj;
  try {
    obj = JSON.parse(rawJson);
  } catch {
    obj = {};
  }

  const metadata = (obj && typeof obj.metadata === 'object' && obj.metadata !== null)
    ? obj.metadata
    : {};

  return {
    type: obj?.type ?? null,
    methodID: obj?.methodID ?? null,
    expires: obj?.expires ?? null,
    email: metadata.email ?? null,
    orgName: metadata.orgName ?? null,
    orgID: metadata.orgID ?? null,
    accountID: metadata.accountID ?? null,
    server: metadata.server ?? null
  };
}

export function sanitizeCredential(row) {
  const clean = {};
  for (const [key, value] of Object.entries(row)) {
    if (SENSITIVE_KEYS.has(key)) continue;
    clean[key] = value;
  }

  const parsed = parseCredentialValue(row.value);
  return { ...clean, ...parsed };
}

export function formatCredentialTable(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return 'Tidak ada akun tersimpan.';
  }

  const width = {
    label: Math.max(6, ...rows.map(r => String(r.label ?? '').length)),
    email: Math.max(5, ...rows.map(r => String(r.email ?? '-').length)),
    org: Math.max(3, ...rows.map(r => String(r.orgName ?? '-').length))
  };

  const header = [
    'LABEL'.padEnd(width.label),
    'EMAIL'.padEnd(width.email),
    'ORG'.padEnd(width.org),
    'STATUS',
    'ID'
  ].join('  ');

  const lines = rows.map(r => [
    String(r.label ?? '-').padEnd(width.label),
    String(r.email ?? '-').padEnd(width.email),
    String(r.orgName ?? '-').padEnd(width.org),
    r.active ? 'AKTIF' : '-',
    String(r.id ?? '-')
  ].join('  '));

  return [header, ...lines].join('\n');
}
