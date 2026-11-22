import fs from 'node:fs';
import fsPromises from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';

let dbPath = path.join(process.cwd(), 'data', 'db.json');
let cache = { keys: [] };
let initialized = false;

export async function initStore(customPath) {
  if (customPath) {
    dbPath = customPath;
  }
  
  // If already initialized with the same path, skip re-reading
  if (initialized && customPath === dbPath) {
    return;
  }
  
  const dir = path.dirname(dbPath);
  await fsPromises.mkdir(dir, { recursive: true });
  try {
    const data = await fsPromises.readFile(dbPath, 'utf8');
    cache = JSON.parse(data);
    if (!Array.isArray(cache.keys)) {
      cache.keys = [];
    }
  } catch (err) {
    cache = { keys: [] };
    await saveStore();
  }
  initialized = true;
}

async function saveStore() {
  const dir = path.dirname(dbPath);
  await fsPromises.mkdir(dir, { recursive: true });
  const tempPath = `${dbPath}.${crypto.randomBytes(4).toString('hex')}.tmp`;
  await fsPromises.writeFile(tempPath, JSON.stringify(cache, null, 2), 'utf8');
  await fsPromises.rename(tempPath, dbPath);
}

export function getKeys(provider) {
  if (!provider) return cache.keys;
  return cache.keys.filter(k => k.provider === provider);
}

export function addKey({ provider, name, key }) {
  const newKey = {
    id: crypto.randomUUID(),
    provider,
    name: name || `${provider}-${Date.now()}`,
    key,
    status: 'active', // active, cooldown, disabled
    cooldownUntil: null,
    errorCount: 0,
    successCount: 0,
    lastUsed: null,
    createdAt: new Date().toISOString()
  };
  cache.keys.push(newKey);
  // synchronous save or fire-and-forget
  fs.writeFileSync(dbPath, JSON.stringify(cache, null, 2), 'utf8');
  return newKey;
}

export function updateKey(id, updates) {
  const keyObj = cache.keys.find(k => k.id === id);
  if (!keyObj) return null;
  Object.assign(keyObj, updates);
  fs.writeFileSync(dbPath, JSON.stringify(cache, null, 2), 'utf8');
  return keyObj;
}

export function deleteKey(id) {
  const index = cache.keys.findIndex(k => k.id === id);
  if (index === -1) return false;
  cache.keys.splice(index, 1);
  fs.writeFileSync(dbPath, JSON.stringify(cache, null, 2), 'utf8');
  return true;
}

export function getNextActiveKey(provider) {
  const now = Date.now();
  const providerKeys = cache.keys.filter(k => k.provider === provider);

  // Check and reset expired cooldowns
  for (const k of providerKeys) {
    if (k.status === 'cooldown' && k.cooldownUntil && now >= k.cooldownUntil) {
      k.status = 'active';
      k.cooldownUntil = null;
    }
  }

  // Find active keys
  const activeKeys = providerKeys.filter(k => k.status === 'active');
  if (activeKeys.length === 0) return null;

  // Simple round-robin / least recently used based on lastUsed
  activeKeys.sort((a, b) => (a.lastUsed || 0) - (b.lastUsed || 0));
  const selected = activeKeys[0];
  selected.lastUsed = now;
  fs.writeFileSync(dbPath, JSON.stringify(cache, null, 2), 'utf8');
  return selected;
}

export function markKeyCooldown(id, durationMs = 60000) {
  const keyObj = cache.keys.find(k => k.id === id);
  if (!keyObj) return null;
  keyObj.status = 'cooldown';
  keyObj.cooldownUntil = Date.now() + durationMs;
  keyObj.errorCount = (keyObj.errorCount || 0) + 1;
  fs.writeFileSync(dbPath, JSON.stringify(cache, null, 2), 'utf8');
  return keyObj;
}

export function markKeyDisabled(id, reason = 'disabled') {
  const keyObj = cache.keys.find(k => k.id === id);
  if (!keyObj) return null;
  keyObj.status = 'disabled';
  keyObj.disabledReason = reason;
  fs.writeFileSync(dbPath, JSON.stringify(cache, null, 2), 'utf8');
  return keyObj;
}
