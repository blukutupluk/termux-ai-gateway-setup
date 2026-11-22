import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';
import { sanitizeCredential, formatCredentialTable } from './opencode-accounts.js';

const DEFAULT_DB = path.join(os.homedir(), '.local', 'share', 'opencode', 'opencode.db');
const INTEGRATION = 'opencode';

function usage() {
  return `opencode-account — kelola akun OpenCode Console

Pemakaian:
  opencode-account add                  Tambah akun baru (login device flow)
  opencode-account add-import <file>    Import akun dari backup JSON
  opencode-account list                 Lihat akun + email + status aktif
  opencode-account switch [label]       Ganti akun aktif (picker kalau kosong)
  opencode-account export [file]        Backup credential (izin 0600)
  opencode-account remove <label>       Hapus akun

Contoh:
  opencode-account add
  opencode-account list
  opencode-account switch adpram01
  opencode-account export ~/opencode-accounts-backup.json`;
}

function dbPath() {
  return process.env.OPENCODE_DB || DEFAULT_DB;
}

function readCredentials() {
  const db = dbPath();
  if (!fs.existsSync(db)) return [];

  const py = `
import sqlite3, json, sys
try:
    con = sqlite3.connect('file:' + sys.argv[1] + '?mode=ro', uri=True)
    rows = con.execute("SELECT id, integration_id, label, value, active FROM credential").fetchall()
    print(json.dumps([{'id':r[0],'integration_id':r[1],'label':r[2],'value':r[3],'active':r[4]} for r in rows]))
except Exception as e:
    print(json.dumps([]))
`;
  try {
    const res = spawnSync('python3', ['-c', py, db], { encoding: 'utf8' });
    if (res.status !== 0 || !res.stdout.trim()) return [];
    const rows = JSON.parse(res.stdout);
    return Array.isArray(rows) ? rows : [];
  } catch {
    return [];
  }
}

function runAuth(args) {
  const res = spawnSync('opencode', ['auth', ...args], { stdio: 'inherit' });
  if (res.error) {
    console.error(`Gagal menjalankan opencode auth: ${res.error.message}`);
    return 1;
  }
  return res.status ?? 1;
}

function resolveCredential(labelOrId) {
  const rows = readCredentials().filter(r => r.integration_id === INTEGRATION);
  if (!labelOrId) return null;
  return rows.find(r => r.id === labelOrId || r.label === labelOrId) || null;
}

function cmdList() {
  const rows = readCredentials()
    .filter(r => r.integration_id === INTEGRATION)
    .map(sanitizeCredential);
  console.log(formatCredentialTable(rows));
  return 0;
}

function cmdAdd() {
  console.log('Membuka proses login OpenCode Console...\n');
  return runAuth(['login', INTEGRATION]);
}

function cmdImport(file) {
  if (!file) {
    console.error('Usage: opencode-account add-import <file.json>');
    return 1;
  }
  if (!fs.existsSync(file)) {
    console.error(`File tidak ditemukan: ${file}`);
    return 1;
  }
  return runAuth(['import', file]);
}

function cmdSwitch(label) {
  if (!label) {
    return runAuth(['switch', INTEGRATION]);
  }
  const cred = resolveCredential(label);
  if (!cred) {
    console.error(`Akun tidak ditemukan: ${label}`);
    console.log('\nDaftar akun:');
    cmdList();
    return 1;
  }
  console.log(`Beralih ke akun: ${cred.label}`);
  return runAuth(['switch', INTEGRATION, cred.id]);
}

function cmdExport(dest) {
  const target = dest || path.join(os.homedir(), `opencode-accounts-${Date.now()}.json`);
  const res = spawnSync('opencode', ['auth', 'export', INTEGRATION], { encoding: 'utf8' });
  if (res.status !== 0) {
    console.error(res.stderr || 'Gagal export credential');
    return 1;
  }
  const fd = fs.openSync(target, 'w', 0o600);
  try {
    fs.writeFileSync(fd, res.stdout);
  } finally {
    fs.closeSync(fd);
  }
  fs.chmodSync(target, 0o600);
  console.log(`Backup tersimpan: ${target} (izin 0600)`);
  console.log('Jangan bagikan file ini — berisi token akses.');
  return 0;
}

function cmdRemove(label) {
  if (!label) {
    console.error('Usage: opencode-account remove <label>');
    return 1;
  }
  const cred = resolveCredential(label);
  if (!cred) {
    console.error(`Akun tidak ditemukan: ${label}`);
    return 1;
  }
  return runAuth(['logout', INTEGRATION, cred.id]);
}

export function main(argv = process.argv.slice(2)) {
  const [command, ...rest] = argv;

  if (!command || command === '--help' || command === '-h' || command === 'help') {
    console.log(usage());
    return 0;
  }

  switch (command) {
    case 'add': return cmdAdd();
    case 'add-import': return cmdImport(rest[0]);
    case 'list': return cmdList();
    case 'switch': return cmdSwitch(rest[0]);
    case 'export': return cmdExport(rest[0]);
    case 'remove': return cmdRemove(rest[0]);
    default:
      console.error(`Perintah tidak dikenal: ${command}`);
      console.error('');
      console.error(usage());
      return 1;
  }
}

if (process.argv[1] && import.meta.url === `file://${process.argv[1]}`) {
  process.exit(main());
}
